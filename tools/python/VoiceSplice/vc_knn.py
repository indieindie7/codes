"""kNN-VC voice conversion + WORLD join smoothing: the torch side of VoiceSplice.

Runs in the CPU-PyTorch venv (Documents\\Tools\\visualqa, python 3.11, torch + pyworld), not in py -3.13:

    <visualqa python> -I vc_knn.py matchset <bank_dir>        WavLM layer-6 features of every clip -> cache
    <visualqa python> -I vc_knn.py serve                      JSON-lines worker on stdin/stdout (synth.py starts it)
    <visualqa python> -I vc_knn.py convert <bank_dir> in.wav out.wav

kNN-VC (Baas, van Niekerk & Kamper 2023; bshall/knn-vc, MIT): every 20 ms WavLM frame of the source is
replaced by the mean of its k nearest frames (cosine) in the target speaker's recordings, then the
prematched HiFi-GAN vocodes the result at 16 kHz. No training; the "matching set" is the bank's clips.
Only wavlm/ and hifigan/models.py from the kNN-VC source are used (matcher.py needs torchaudio, which has
no build for torch 2.14; resampling here is scipy, VAD is a plain energy trim).

Worker ops (one JSON object per line, one reply per line):
  {"op": "convert", "bank_dir", "in", "out", "topk": 4}      in/out are 22.05 kHz mono WAV paths
  {"op": "smooth", "in", "out", "joins": [sec, ...]}         pyworld F0/energy ramps across each join
  {"op": "embed", "wavs": [...]}                             -> {"emb": {wav: [1024 floats]}} (speaker check)
  {"op": "bank_emb", "bank_dir"}                             -> centroid of the matching set
Model weights: VOICESPLICE_MODELS (default H:\\VoiceSplice\\models); caches: VOICESPLICE_CACHE (H:\\VoiceSplice\\cache).
"""
import glob
import json
import os
import sys
import time
import wave

import numpy as np

MODELS = os.environ.get("VOICESPLICE_MODELS", r"H:\VoiceSplice\models")
CACHE = os.environ.get("VOICESPLICE_CACHE", r"H:\VoiceSplice\cache")
KNN_SRC = os.path.join(MODELS, "knn-vc-src", "knn-vc-master")
SR_IO, SR_VC = 22050, 16000
LAYER = 6


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path, x, sr):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    y = np.clip(np.asarray(x, dtype=np.float32), -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def resample(x, a, b):
    from scipy.signal import resample_poly
    from math import gcd
    if a == b:
        return x.astype(np.float32)
    g = gcd(a, b)
    return resample_poly(x, b // g, a // g).astype(np.float32)


def trim_ends(x, sr, rel_db=-40):
    h = int(0.01 * sr)
    if len(x) < 4 * h:
        return x
    r = np.sqrt(np.convolve(x ** 2, np.ones(h) / h, mode="same") + 1e-12)
    on = np.where(r > r.max() * 10 ** (rel_db / 20))[0]
    if not len(on):
        return x
    return x[max(0, on[0] - h):on[-1] + h]


class KnnVC:
    def __init__(self):
        import torch
        sys.path.insert(0, KNN_SRC)
        from wavlm.WavLM import WavLM, WavLMConfig
        from hifigan.models import Generator
        from hifigan.utils import AttrDict
        torch.set_num_threads(max(1, (os.cpu_count() or 4) - 2))
        self.torch = torch
        t0 = time.time()
        ck = torch.load(os.path.join(MODELS, "WavLM-Large.pt"), map_location="cpu", weights_only=True)
        self.wavlm = WavLM(WavLMConfig(ck["cfg"]))
        self.wavlm.load_state_dict(ck["model"])
        self.wavlm.eval()
        with open(os.path.join(KNN_SRC, "hifigan", "config_v1_wavlm.json")) as f:
            h = AttrDict(json.load(f))
        self.hifigan = Generator(h)
        g = torch.load(os.path.join(MODELS, "prematch_g_02500000.pt"), map_location="cpu", weights_only=True)
        self.hifigan.load_state_dict(g["generator"])
        self.hifigan.eval()
        self.hifigan.remove_weight_norm()
        self.sets = {}
        log("kNN-VC loaded in %.1f s" % (time.time() - t0))

    def features(self, x16):
        """(T,) float32 at 16 kHz -> (frames, 1024) WavLM layer-6 features (20 ms hop)."""
        torch = self.torch
        with torch.inference_mode():
            t = torch.from_numpy(np.ascontiguousarray(x16, dtype=np.float32))[None]
            return self.wavlm.extract_features(t, output_layer=LAYER, ret_layer_results=False)[0].squeeze(0)

    def matching_set(self, bank_dir):
        name = os.path.basename(os.path.normpath(bank_dir))
        if name in self.sets:
            return self.sets[name]
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, "%s.wavlm%d.f16.npy" % (name, LAYER))
        if not os.path.exists(path):
            build_matchset(self, bank_dir, path)
        m = self.torch.from_numpy(np.load(path).astype(np.float32))
        self.sets[name] = m
        log("matching set %s: %d frames (%.1f min)" % (name, len(m), len(m) * 0.02 / 60))
        return m

    def convert(self, x22, bank_dir, topk=4):
        torch = self.torch
        m = self.matching_set(bank_dir)
        q = self.features(resample(x22, SR_IO, SR_VC))
        with torch.inference_mode():
            qn = torch.nn.functional.normalize(q, dim=-1)
            mn = self.sets.setdefault(os.path.basename(os.path.normpath(bank_dir)) + "#n",
                                      torch.nn.functional.normalize(m, dim=-1))
            best = (qn @ mn.T).topk(k=topk, dim=-1).indices
            out = m[best].mean(dim=1)
            y = self.hifigan(out[None]).squeeze().numpy()
        return resample(y, SR_VC, SR_IO)


def build_matchset(knn, bank_dir, path):
    wavs = sorted(glob.glob(os.path.join(bank_dir, "clips", "*.wav")))
    log("building matching set from %d clips -> %s" % (len(wavs), path))
    feats, t0 = [], time.time()
    for i, w in enumerate(wavs):
        x, sr = read_wav(w)
        x = trim_ends(resample(x, sr, SR_VC), SR_VC)
        if len(x) < SR_VC // 4:
            continue
        for s in range(0, len(x), SR_VC * 20):            # 20 s chunks keep attention memory small
            seg = x[s:s + SR_VC * 20]
            if len(seg) >= SR_VC // 4:
                feats.append(knn.features(seg).numpy().astype(np.float16))
        if i % 25 == 0:
            log("  %d/%d  %.0f s" % (i + 1, len(wavs), time.time() - t0))
    tmp = path[:-4] + ".part.npy"
    np.save(tmp, np.concatenate(feats))
    os.replace(tmp, path)


# ---------------------------------------------------------------- WORLD smoothing at joins

def smooth_joins(x, sr, joins, win=0.10, ctx=0.12, min_st=0.5):
    """Ramp log-F0 and log-energy so the two sides of each join meet halfway. Only the +-win region
    around a join is re-synthesised with WORLD; the rest stays the original audio (crossfaded in)."""
    import pyworld as pw
    xd = x.astype(np.float64)
    fp = 5.0
    f0, t = pw.dio(xd, sr, frame_period=fp)
    f0 = pw.stonemask(xd, f0, t, sr)
    sp = pw.cheaptrick(xd, f0, t, sr)
    ap = pw.d4c(xd, f0, t, sr)
    en = np.log(sp.sum(axis=1) + 1e-12)
    lf0 = np.where(f0 > 0, np.log(np.maximum(f0, 1)), 0.0)
    df0, den = np.zeros(len(t)), np.zeros(len(t))
    touched = []
    for tj in joins:
        b = (t >= tj - ctx) & (t < tj)
        a = (t > tj) & (t <= tj + ctx)
        w = np.clip(1 - np.abs(t - tj) / win, 0, 1)
        side = np.where(t < tj, 1.0, -1.0)
        changed = False
        vb, va = b & (f0 > 0), a & (f0 > 0)
        if vb.sum() >= 3 and va.sum() >= 3:
            d = np.median(lf0[va]) - np.median(lf0[vb])
            if abs(d) * 12 / np.log(2) >= min_st:
                df0 += side * w * d / 2
                changed = True
        sb, sa = b & (en > en.max() - 12), a & (en > en.max() - 12)
        if sb.sum() >= 3 and sa.sum() >= 3:
            d = np.median(en[sa]) - np.median(en[sb])
            d = float(np.clip(d, -np.log(10 ** 0.9), np.log(10 ** 0.9)))   # <= 9 dB per side
            if abs(d) > 0.23:                                              # ~1 dB
                den += side * w * d / 2
                changed = True
        if changed:
            touched.append(tj)
    if not touched:
        return x, 0
    f0n = np.where(f0 > 0, np.exp(lf0 + df0), 0.0)
    spn = sp * np.exp(den)[:, None]
    y = pw.synthesize(f0n, spn, ap, sr, fp)[:len(x)].astype(np.float32)
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    # mix: WORLD output only inside +-(win+fade) of the touched joins
    mask = np.zeros(len(x), dtype=np.float32)
    fade = int(0.015 * sr)
    for tj in touched:
        s, e = int((tj - win) * sr), int((tj + win) * sr)
        s0, e0 = max(0, s - fade), min(len(x), e + fade)
        ramp = np.ones(e0 - s0, dtype=np.float32)
        k = min(fade, len(ramp) // 2)
        if k:
            ramp[:k] = np.linspace(0, 1, k)
            ramp[-k:] = np.linspace(1, 0, k)
        mask[s0:e0] = np.maximum(mask[s0:e0], ramp)
    return x * (1 - mask) + y * mask, len(touched)


# ---------------------------------------------------------------- worker

def embed(knn, path):
    x, sr = read_wav(path)
    x = trim_ends(resample(x, sr, SR_VC), SR_VC)
    return knn.features(x).mean(dim=0).numpy().astype(float)


def handle(knn_box, r):
    op = r["op"]
    if op == "smooth":
        x, sr = read_wav(r["in"])
        y, n = smooth_joins(x, sr, r.get("joins", []))
        write_wav(r["out"], y, sr)
        return {"ok": True, "smoothed": n}
    if knn_box[0] is None:
        knn_box[0] = KnnVC()
    knn = knn_box[0]
    if op == "convert":
        x, sr = read_wav(r["in"])
        y = knn.convert(resample(x, sr, SR_IO), r["bank_dir"], int(r.get("topk", 4)))
        write_wav(r["out"], y, SR_IO)
        return {"ok": True, "seconds": round(len(y) / SR_IO, 3)}
    if op == "embed":
        return {"ok": True, "emb": {w: embed(knn, w).tolist() for w in r["wavs"]}}
    if op == "bank_emb":
        m = knn.matching_set(r["bank_dir"])
        return {"ok": True, "emb": m.mean(dim=0).numpy().astype(float).tolist()}
    return {"ok": False, "error": "unknown op " + op}


def serve():
    box = [None]
    out = sys.stdout
    sys.stdout = sys.stderr            # library prints (HiFi-GAN "Removing weight norm...") must not hit the pipe
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(box, json.loads(line))
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            reply = {"ok": False, "error": repr(e)}
        out.write(json.dumps(reply) + "\n")
        out.flush()


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["serve"]:
        serve()
    elif a[:1] == ["matchset"] and len(a) == 2:
        KnnVC().matching_set(a[1])
    elif a[:1] == ["convert"] and len(a) == 4:
        print(handle([None], {"op": "convert", "bank_dir": a[1], "in": a[2], "out": a[3]}))
    else:
        print(__doc__)
