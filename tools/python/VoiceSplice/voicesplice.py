"""VoiceSplice driver: build a bank, say a line, or serve edit requests (the game-side watcher prototype).

    py -3.13 voicesplice.py build u2 Isaak               corpus from the game files (read only) -> align -> bank
    py -3.13 voicesplice.py build piper piper_hfc [voice] stand-in corpus spoken by Piper
    py -3.13 voicesplice.py say <bank> "text" [ogg=path] [mode=hybrid|hybrid_raw|vcline|splice|tts|piper]
    py -3.13 voicesplice.py serve [voice_root=<dir>] [mode=...] [warm=Isaak]   watch requests, write Ogg files
    py -3.13 voicesplice.py matchset <bank>              cache the bank's WavLM features for kNN-VC (once)

mode defaults to synth.DEFAULT_MODE (hybrid); a request may carry its own "mode" (the old "oov" key works).

serve: every VOICESPLICE_HOME\\requests\\*.json  {"id": "e0007", "bank": "Isaak", "node": "Acheron_10_002",
"text": "..."} becomes <voice_root>\\VoiceSplice\\<id>.ogg plus a <id>.done.json reply next to the request
({"ok", "filename": "VoiceSplice.<id>", "seconds", "plan"}). "filename" is what the game would put in
DialogNode.Filename: GetOggFilename turns Pkg.Name into Voice\\Pkg\\Name.ogg. voice_root defaults to
VOICESPLICE_HOME\\voice_out; pointing it at <game>\\Voice is the install step (design.md, stage 3),
not done by this prototype.
"""
import json
import os
import subprocess
import sys
import time

import vs_common as vc


def build(kind, name, voice=None):
    py = sys.executable
    if kind == "u2":
        subprocess.run([py, os.path.join(vc.HERE, "corpus.py"), "u2", name], check=True)
    else:
        subprocess.run([py, os.path.join(vc.HERE, "corpus.py"), "piper", name] + ([voice] if voice else []), check=True)
    bank = vc.bank_dir(name)
    subprocess.run([vc.WHISPER_PY, os.path.join(vc.HERE, "align_words.py"), bank], check=True)
    subprocess.run([py, os.path.join(vc.HERE, "align_dtw.py"), name], check=True)
    subprocess.run([py, os.path.join(vc.HERE, "bank.py"), name], check=True)


def serve(voice_root, poll=0.25, mode=None, warm=None):
    import synth
    for b in (warm.split(",") if warm else []):          # load kNN-VC + the bank's matching set now (~10 s)
        synth.say(b, "Ready.", out=os.path.join(vc.HOME, "out", "serve", "_warm.wav"), quiet=True, mode="vcline")
    req = os.path.join(vc.HOME, "requests")
    os.makedirs(req, exist_ok=True)
    print("serving %s -> %s, mode %s (Ctrl+C stops)" % (req, voice_root, mode or synth.DEFAULT_MODE), flush=True)
    while True:
        for f in sorted(os.listdir(req)):
            if not f.endswith(".json") or f.endswith(".done.json"):
                continue
            p = os.path.join(req, f)
            done = p[:-5] + ".done.json"
            if os.path.exists(done):
                continue
            try:
                r = json.load(open(p, encoding="utf-8"))
                t0 = time.time()
                ogg = os.path.join(voice_root, "VoiceSplice", r["id"] + ".ogg")
                info = synth.say(r["bank"], r["text"], out=os.path.join(vc.HOME, "out", "serve", r["id"] + ".wav"),
                                 ogg=ogg, quiet=True, oov=r.get("oov"),
                                 mode=r.get("mode", mode))
                reply = {"ok": True, "id": r["id"], "node": r.get("node"), "filename": "VoiceSplice." + r["id"],
                         "ogg": ogg, "seconds": info["seconds"], "ms": int((time.time() - t0) * 1000),
                         "plan": info["words_by_kind"], "mode": info["mode"],
                         "rendered_as": info["rendered_as"]}
            except Exception as e:                       # the reply carries the failure; the game keeps the old line
                reply = {"ok": False, "id": f[:-5], "error": repr(e)}
            tmp = done + ".tmp"
            json.dump(reply, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(tmp, done)
            print(json.dumps(reply, ensure_ascii=False), flush=True)
        time.sleep(poll)


if __name__ == "__main__":
    a = [s for s in sys.argv[1:] if "=" not in s]
    o = dict(s.split("=", 1) for s in sys.argv[1:] if "=" in s)
    if a[:1] == ["build"] and len(a) >= 3:
        build(a[1], a[2], a[3] if len(a) > 3 else None)
    elif a[:1] == ["say"] and len(a) >= 3:
        import synth
        synth.say(a[1], a[2], o.get("out"), o.get("ogg"), o.get("fallback", "en_US-john-medium"), oov=o.get("oov"),
                  mode=o.get("mode"))
    elif a[:1] == ["serve"]:
        serve(o.get("voice_root", os.path.join(vc.HOME, "voice_out")), mode=o.get("mode"), warm=o.get("warm"))
    elif a[:1] == ["matchset"] and len(a) >= 2:
        subprocess.run([vc.VC_PY, "-I", os.path.join(vc.HERE, "vc_knn.py"), "matchset", vc.bank_dir(a[1])],
                       check=True, env=dict(os.environ, VOICESPLICE_MODELS=vc.MODELS, VOICESPLICE_CACHE=vc.CACHE))
    else:
        print(__doc__)
