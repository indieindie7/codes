"""Word timestamps for a corpus with faster-whisper (runs in the whisper venv, not py -3.13).

    <whisper venv python> align_words.py <bank_dir> [model=small]      -> <bank_dir>/asr.jsonl
    <whisper venv python> align_words.py --transcribe a.wav b.wav ...  -> prints JSON {path: text}

The known line text goes in as the initial prompt, so names and spelling follow the script.
Matching the recognised words to the known text happens later in bank.py (plain Python 3.13).
"""
import json
import os
import sys
import wave

import numpy as np
from faster_whisper import WhisperModel


def load16k(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != 16000:
        t = np.arange(0, len(x) / sr, 1 / 16000)
        x = np.interp(t, np.arange(len(x)) / sr, x).astype(np.float32)
    return x


def main():
    a = sys.argv[1:]
    opts = dict(s.split("=", 1) for s in a if "=" in s)
    a = [s for s in a if "=" not in s]
    model = WhisperModel(opts.get("model", "small"), device="cpu", compute_type="int8",
                         cpu_threads=int(opts.get("threads", "8")))
    if a[0] == "--transcribe":
        out = {}
        for p in a[1:]:
            segs, _ = model.transcribe(load16k(p), language="en", beam_size=5, condition_on_previous_text=False)
            out[p] = " ".join(s.text.strip() for s in segs)
        print(json.dumps(out, ensure_ascii=False))
        return
    bank = a[0]
    rows = [json.loads(l) for l in open(os.path.join(bank, "lines.jsonl"), encoding="utf-8") if l.strip()]
    outp = os.path.join(bank, "asr.jsonl")
    done = {}
    if os.path.exists(outp):
        for l in open(outp, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                done[r["id"]] = r
    with open(outp, "a", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            if r["id"] in done:
                continue
            segs, _ = model.transcribe(load16k(r["wav"]), language="en", beam_size=5, word_timestamps=True,
                                       initial_prompt=r["text"], condition_on_previous_text=False,
                                       vad_filter=False)
            words = []
            for s in segs:
                for w in s.words or []:
                    words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3),
                                  "p": round(w.probability, 3)})
            f.write(json.dumps({"id": r["id"], "words": words}, ensure_ascii=False) + "\n")
            f.flush()
            print("\r%d/%d %s" % (i + 1, len(rows), r["id"]), end="", file=sys.stderr)
    print("\n" + outp)


if __name__ == "__main__":
    main()
