"""Round-trip check: render test lines, let whisper transcribe them, score word error rate (WER) and a
speaker-similarity score.

    py -3.13 evaluate.py <bank> [set=piper|u2] [modes=splice,tts,piper,vcline,hybrid_raw,hybrid] [spk=0]

modes (synth.MODES): splice = stage-1 planner (unknown words as diphone chains; was "units"); tts = unknown
words from Piper moved toward the bank's pitch; piper = plain Piper line; vcline = Piper line -> kNN-VC;
hybrid_raw = recorded words + kNN-VC'd Piper for new words (or vcline if choppy); hybrid = hybrid_raw +
WORLD F0/energy smoothing at the joins; phones = every word as diphones.

spk: WavLM layer-6 mean-pooled embedding of each output, centred on the midpoint between the bank
speaker's centroid (all his clips) and the plain-Piper outputs' centroid, then cosine to the speaker:
+1 = on the speaker's side, -1 = on the Piper source voice's side. Real clips of the speaker are scored
too as the ceiling. Cheap and crude (an axis between two voices, not a speaker-verification model).
Writes VOICESPLICE_HOME\\out\\<bank>\\eval\\*.wav and report.json. Listen to the files too.
"""
import numpy as np
import json
import os
import subprocess
import sys
import time

import vs_common as vc
import synth

# original test lines (not from any game); "in" = words likely in the bank, "new" = names/words it lacks
SETS = {
    "piper": [
        ("in", "The engines are running hot, captain."),
        ("in", "Check the cargo hold before the shuttle leaves."),
        ("in", "Keep your light on and stay off the ridge."),
        ("mix", "The marines found a strange signal under the reactor."),
        ("mix", "Bring the scanner to the hatch and wait for my call."),
        ("new", "Ne'Ban says the Skaarj are gathering near the hive."),
        ("new", "Isaak fixed the plasma coupling on the dropship."),
    ],
    "u2": [
        ("in", "Welcome back, boss. The ship is ready."),
        ("in", "I'll wait here. Take your time."),
        ("mix", "The idiots in supply sent the wrong parts again."),
        ("mix", "We picked up a signal from the old mining station."),
        ("mix", "Your armor is fixed. Try not to break it this time."),
        ("new", "Ne'Ban thinks the artifact is singing to him."),
        ("new", "The Skaarj are gathering near the colony gates."),
    ],
}


def wer(ref, hyp):
    r = [k for k, _ in vc.tokenize(ref)]
    h = [k for k, _ in vc.tokenize(hyp)]
    D = [[i + j if i * j == 0 else 0 for j in range(len(h) + 1)] for i in range(len(r) + 1)]
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return D[-1][-1] / max(1, len(r))


def main():
    a = [s for s in sys.argv[1:] if "=" not in s]
    o = dict(s.split("=", 1) for s in sys.argv[1:] if "=" in s)
    bank = a[0]
    lines = SETS[o.get("set", "u2" if not bank.startswith("piper") else "piper")]
    modes = o.get("modes", "splice,tts,piper,vcline,hybrid_raw,hybrid").split(",")
    modes = [{"units": "splice"}.get(m, m) for m in modes]
    synth.HYBRID_MAX_NEW = float(o.get("max_new", synth.HYBRID_MAX_NEW))
    synth.HYBRID_MAX_TIGHT = float(o.get("max_tight", synth.HYBRID_MAX_TIGHT))
    synth.VC_TOPK = int(o.get("topk", synth.VC_TOPK))
    synth.VC_VOICE = o.get("vc_voice", synth.VC_VOICE)
    outd = os.path.join(vc.HOME, "out", bank, o.get("tag", "eval"))
    rows = []
    for m in modes:
        for i, (tag, text) in enumerate(lines):
            wav = os.path.join(outd, "%s_%02d.wav" % (m, i))
            t0 = time.time()
            info = synth.say(bank, text, out=wav, quiet=True, mode=m, fallback=o.get("fallback", "en_US-john-medium"))
            rows.append({"mode": m, "tag": tag, "text": text, "wav": wav, "kinds": info["words_by_kind"],
                         "as": info["rendered_as"], "seconds": info["seconds"], "ms": int((time.time() - t0) * 1000)})
    p = subprocess.run([vc.WHISPER_PY, os.path.join(vc.HERE, "align_words.py"), "--transcribe"]
                       + [r["wav"] for r in rows], capture_output=True, text=True, encoding="utf-8", check=True)
    hyp = json.loads(p.stdout.strip().splitlines()[-1])
    for r in rows:
        r["heard"] = hyp[r["wav"]]
        r["wer"] = round(wer(r["text"], r["heard"]), 3)
    spk_ref = None
    if o.get("spk", "1") != "0" and not bank.startswith("piper"):
        spk_ref = speaker_scores(bank, rows)
    tags = sorted({t for t, _ in lines}, key=["in", "mix", "new"].index)
    print("\n| mode | " + " | ".join(tags) + " | all | spk | ms/line |")
    print("|---" * (len(tags) + 4) + "|")
    for m in modes:
        sel = [r for r in rows if r["mode"] == m]
        cells = ["%.2f" % np.mean([r["wer"] for r in sel if r["tag"] == t]) for t in tags]
        spk = "%.2f" % np.mean([r["spk"] for r in sel]) if "spk" in sel[0] else "-"
        print("| %s | %s | %.2f | %s | %d |" % (m, " | ".join(cells), np.mean([r["wer"] for r in sel]), spk,
                                               np.mean([r["ms"] for r in sel])))
    if spk_ref is not None:
        print("| real %s clips (ceiling) | | | | | %.2f | |" % (bank, spk_ref))
    for m in modes:
        print("\n== %s" % m)
        for r in [r for r in rows if r["mode"] == m]:
            print("  %.2f [%s] %s\n       heard: %s   %s %s" % (r["wer"], r["tag"], r["text"], r["heard"],
                                                             r["as"], r["kinds"]))
    json.dump(rows, open(os.path.join(outd, "report.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def speaker_scores(bank, rows, n_real=8):
    """Adds r["spk"] to each row; returns the mean score of real clips of the speaker."""
    d = vc.bank_dir(bank)
    real = sorted(os.path.join(d, "clips", f) for f in os.listdir(os.path.join(d, "clips")) if f.endswith(".wav"))
    real = real[::max(1, len(real) // n_real)][:n_real]
    refs = []                                  # fixed reference axis: plain Piper john reading the same lines
    for i, text in enumerate(sorted({r["text"] for r in rows})):
        w = os.path.join(vc.HOME, "out", bank, "spkref", "john_%02d.wav" % i)
        if not os.path.exists(w):
            vc.write_wav(w, synth.render_line(synth._BANKS[bank], text, "en_US-john-medium", False)[0])
        refs.append(w)
    emb = synth.VCWorker.call(op="embed", wavs=[r["wav"] for r in rows] + real + refs)["emb"]
    spk = np.array(synth.VCWorker.call(op="bank_emb", bank_dir=d)["emb"])
    piper = [np.array(emb[w]) for w in refs]
    mid = (spk + np.mean(piper, axis=0)) / 2
    axis = spk - mid
    score = lambda e: float(np.dot(np.array(e) - mid, axis) / (np.linalg.norm(np.array(e) - mid) * np.linalg.norm(axis) + 1e-9))
    for r in rows:
        r["spk"] = round(score(emb[r["wav"]]), 3)
    return float(np.mean([score(emb[w]) for w in real]))


if __name__ == "__main__":
    main()
