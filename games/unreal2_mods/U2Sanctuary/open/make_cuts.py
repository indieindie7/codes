r"""Build Sanctuary Open's dialogue cuts (cuts.json): the line clips are cut from the actors' own takes by
tools/python/VoiceSplice/dlgcut.py (at the line's pauses, checked by whisper) into <game>\Voice\U2Cut\; the result,
with what whisper heard, goes to cuts_built.json for import_m08.py (which writes OpenDirector's Cuts= lines).

    py make_cuts.py        (a clip whose whisper match is under 0.8 is reported and left out)
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DLGCUT = os.path.join(HERE, "..", "..", "..", "..", "tools", "python", "VoiceSplice", "dlgcut.py")


def main():
    C = json.load(open(os.path.join(HERE, "cuts.json")))["cuts"]
    out = []
    for c in C:
        if c["op"] != "clip":
            out.append(c)
            continue
        p = subprocess.run(["py", "-3.13", DLGCUT, "cut", c["node"], "keep=" + c["keep"]], capture_output=True, text=True,
                           cwd=os.path.dirname(DLGCUT))
        if p.returncode:
            print("FAILED", c["node"], p.stderr.strip()[-300:])
            continue
        r = json.loads(p.stdout.strip().splitlines()[-1])
        ok = r.get("match", 1.0) >= 0.8
        print("%-22s %s %.1f s  match %s  heard: %s" % (c["node"], "ok " if ok else "BAD", r["secs"], r.get("match"), r.get("heard", "-")))
        if ok:
            out.append(dict(c, **{k: r[k] for k in ("file", "text", "secs", "heard", "match") if k in r}))
    json.dump(out, open(os.path.join(HERE, "cuts_built.json"), "w"), indent=1)
    print("%d of %d cuts -> cuts_built.json" % (len(out), len(C)))


if __name__ == "__main__":
    main()
