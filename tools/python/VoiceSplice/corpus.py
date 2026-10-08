"""Build a speaker corpus: clips/<id>.wav + lines.jsonl {id, text, wav, src}.

    py -3.13 corpus.py u2 Isaak                 # one Unreal II speaker, from the game's Dialog\\*.dlg + Voice\\*.ogg
    py -3.13 corpus.py u2 --list                # speakers and line counts
    py -3.13 corpus.py piper <bank> [voice]     # stand-in corpus spoken by Piper (proves the pipeline)

The game folder is only read. Clips and text go to VOICESPLICE_HOME\\banks\\<bank>, never into git.
"""
import glob
import os
import re
import sys
from collections import Counter

import vs_common as vc


def parse_dlg(path):
    """U2 .dlg = INI with repeated keys. Returns {section: {key_lower: [values]}}."""
    secs, cur = {}, None
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            m = re.match(r"^\[(.+)\]$", line)
            if m:
                cur = secs.setdefault(m.group(1), {})
                continue
            if cur is not None and "=" in line:
                k, v = line.split("=", 1)
                cur.setdefault(k.strip().lower(), []).append(v.strip())
    return secs


def ogg_path(soundfile):
    """What Dialog.GetOggFilename does: Pkg.Group.Name -> <game>\\Voice\\Pkg\\Group\\Name.ogg"""
    return os.path.join(vc.U2_GAME, "Voice", *soundfile.split(".")) + ".ogg"


def u2_nodes():
    for path in glob.glob(os.path.join(vc.U2_GAME, "Dialog", "**", "*.dlg"), recursive=True):
        for name, kv in parse_dlg(path).items():
            if "speaker" in kv:
                yield {"node": name, "dlg": os.path.relpath(path, vc.U2_GAME), "speaker": kv["speaker"][0],
                       "text": kv.get("longtext", [""])[0], "sound": kv.get("soundfile", [""])[0]}


def build_u2(speaker):
    d = vc.bank_dir(speaker)
    rows, missing = [], 0
    for n in u2_nodes():
        if n["speaker"].lower() != speaker.lower() or not n["sound"] or not n["text"].strip():
            continue
        src = ogg_path(n["sound"])
        if not os.path.exists(src):
            missing += 1
            continue
        wav = os.path.join(d, "clips", n["node"] + ".wav")
        if not os.path.exists(wav):
            vc.write_wav(wav, vc.decode(src))
        rows.append({"id": n["node"], "text": n["text"], "wav": wav, "src": n["sound"], "dlg": n["dlg"]})
    vc.jl_write(os.path.join(d, "lines.jsonl"), rows)
    print("%s: %d clips (%d .ogg missing) -> %s" % (speaker, len(rows), missing, d))


def build_piper(bank, voice):
    from piper import PiperVoice
    v = PiperVoice.load(os.path.join(vc.PIPER_VOICES, voice + ".onnx"))
    d = vc.bank_dir(bank)
    lines = [l.strip() for l in open(os.path.join(vc.HERE, "test_corpus.txt"), encoding="utf-8")
             if l.strip() and not l.startswith("#")]
    rows = []
    for i, text in enumerate(lines):
        audio = []
        sr = vc.SR
        for c in v.synthesize(text):
            audio.append(c.audio_float_array)
            sr = c.sample_rate
        x = __import__("numpy").concatenate(audio)
        wav = os.path.join(d, "clips", "L%03d.wav" % i)
        vc.write_wav(wav, x, sr)
        rows.append({"id": "L%03d" % i, "text": text, "wav": wav, "src": "piper:" + voice})
    vc.jl_write(os.path.join(d, "lines.jsonl"), rows)
    print("%s: %d Piper clips (%s) -> %s" % (bank, len(rows), voice, d))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["u2"] and a[1:2] == ["--list"]:
        c = Counter(n["speaker"] for n in u2_nodes() if n["sound"])
        for s, k in c.most_common(40):
            print("%5d %s" % (k, s))
    elif a[:1] == ["u2"] and len(a) > 1:
        build_u2(a[1])
    elif a[:1] == ["piper"] and len(a) > 1:
        build_piper(a[1], a[2] if len(a) > 2 else "en_US-hfc_male-medium")
    else:
        print(__doc__)
