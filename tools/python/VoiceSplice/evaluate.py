"""Round-trip check: splice test lines, let whisper transcribe them, score word error rate (WER).

    py -3.13 evaluate.py <bank> [set=piper|u2] [modes=units,phones]

modes: units = the normal planner (unknown words as diphone chains); tts = unknown words from a Piper
voice moved toward the bank's pitch (fallback=<voice>, the voice-conversion stand-in); phones = every
word forced through diphone chains (shows what word-level units buy). Writes VOICESPLICE_HOME\\out\\<bank>\\eval\\*.wav and report.json.
Intelligibility to an ASR model is a floor, not a quality score: listen to the files too.
"""
import json
import os
import subprocess
import sys

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
    modes = o.get("modes", "units,tts,phones").split(",")
    outd = os.path.join(vc.HOME, "out", bank, "eval")
    rows = []
    for m in modes:
        for i, (tag, text) in enumerate(lines):
            wav = os.path.join(outd, "%s_%02d.wav" % (m, i))
            info = synth.say(bank, text, out=wav, quiet=True, force_phones=(m == "phones"),
                             oov="tts" if m == "tts" else "phones", fallback=o.get("fallback", "en_US-john-medium"))
            rows.append({"mode": m, "tag": tag, "text": text, "wav": wav, "kinds": info["words_by_kind"],
                         "seconds": info["seconds"]})
    p = subprocess.run([vc.WHISPER_PY, os.path.join(vc.HERE, "align_words.py"), "--transcribe"]
                       + [r["wav"] for r in rows], capture_output=True, text=True, encoding="utf-8", check=True)
    hyp = json.loads(p.stdout.strip().splitlines()[-1])
    for r in rows:
        r["heard"] = hyp[r["wav"]]
        r["wer"] = round(wer(r["text"], r["heard"]), 3)
    for m in modes:
        sel = [r for r in rows if r["mode"] == m]
        print("== %s: mean WER %.2f" % (m, sum(r["wer"] for r in sel) / len(sel)))
        for r in sel:
            print("  %.2f [%s] %s\n       heard: %s   %s" % (r["wer"], r["tag"], r["text"], r["heard"], r["kinds"]))
    json.dump(rows, open(os.path.join(outd, "report.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
