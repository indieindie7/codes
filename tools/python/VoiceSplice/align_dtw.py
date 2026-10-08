"""Sharper word edges: align each clip to a Piper reading of the same text with DTW.

    py -3.13 align_dtw.py <bank> [ref=en_US-john-medium]      -> <bank>/dtw.jsonl (same shape as asr.jsonl)

Whisper's word times are rough (20 ms steps, often 50-150 ms off, last word cut short). Here the known
line is synthesised word by word with Piper, so the reference's word edges are exact; MFCCs of both
(per-utterance mean/variance normalised, so the speaker matters less) are aligned with DTW and the
reference edges are carried over to the real clip. bank.py then keeps the DTW times only for words
whisper also heard (that drops lines where the actor strayed from the script).
"""
import os
import sys

import numpy as np

import vs_common as vc

STEP = 2          # use every 2nd 5 ms frame -> 10 ms DTW grid


def feats(x, sr):
    m = vc.mfcc(x, sr)[:, 1:]
    e = np.log(vc.rms_track(x, sr)[:len(m)] + 1e-4)[:, None]
    f = np.hstack([m, e * 2])
    f = (f - f.mean(axis=0)) / (f.std(axis=0) + 1e-6)
    return f[::STEP]


def dtw_path(A, B, band=0.3):
    n, m = len(A), len(B)
    C = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(axis=2))
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    w = max(int(band * max(n, m)), abs(n - m) + 5)
    for i in range(1, n + 1):
        jc = int(i * m / n)
        lo, hi = max(1, jc - w), min(m, jc + w)
        row, prev = D[i], D[i - 1]
        for j in range(lo, hi + 1):
            row[j] = C[i - 1, j - 1] + min(prev[j - 1], prev[j] + 0.5, row[j - 1] + 0.5)
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = np.argmin([D[i - 1, j - 1], D[i - 1, j] + 0.5, D[i, j - 1] + 0.5])
        i, j = (i - 1, j - 1) if k == 0 else (i - 1, j) if k == 1 else (i, j - 1)
    return path[::-1]


def main():
    a = [s for s in sys.argv[1:] if "=" not in s]
    o = dict(s.split("=", 1) for s in sys.argv[1:] if "=" in s)
    from piper import PiperVoice
    voice = PiperVoice.load(os.path.join(vc.PIPER_VOICES, o.get("ref", "en_US-john-medium") + ".onnx"))
    d = vc.bank_dir(a[0])
    rows = vc.jl_read(os.path.join(d, "lines.jsonl"))
    gap = np.zeros(int(0.03 * vc.SR), dtype=np.float32)
    out = []
    for n, r in enumerate(rows):
        toks = vc.tokenize(r["text"])
        ref, edges, t = [gap], [], len(gap)
        for k, punct in toks:
            y = np.concatenate([c.audio_float_array for c in voice.synthesize(k.replace("'", ""))])
            rr = vc.rms_track(y, vc.SR)
            on = np.where(rr > rr.max() * 0.04)[0]
            h = int(vc.HOP * vc.SR)
            if len(on):
                y = y[on[0] * h:(on[-1] + 1) * h]
            edges.append((t, t + len(y)))
            ref += [y, gap if not punct else np.zeros(int(0.2 * vc.SR), dtype=np.float32)]
            t += len(y) + len(ref[-1])
        R = np.concatenate(ref)
        x, sr = vc.read_wav(r["wav"])
        fa, fb = feats(R, vc.SR), feats(x, sr)
        path = dtw_path(fa, fb)
        fwd = {}
        for i, j in path:
            fwd.setdefault(i, []).append(j)
        dt = vc.HOP * STEP

        def carry(sample, take_first):
            i = min(len(fa) - 1, int(sample / vc.SR / dt))
            js = fwd.get(i) or [int(i * len(fb) / len(fa))]
            return (js[0] if take_first else js[-1]) * dt

        words = [{"w": k, "s": round(carry(s, True), 3), "e": round(carry(e, False) + dt, 3), "p": 1.0}
                 for (k, _), (s, e) in zip(toks, edges)]
        out.append({"id": r["id"], "words": words})
        print("\r%d/%d" % (n + 1, len(rows)), end="", file=sys.stderr)
    vc.jl_write(os.path.join(d, "dtw.jsonl"), out)
    print("\n" + os.path.join(d, "dtw.jsonl"))


if __name__ == "__main__":
    main()
