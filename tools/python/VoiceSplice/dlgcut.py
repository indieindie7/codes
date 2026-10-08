r"""Cut a voiced Unreal II dialogue line at its sentence pauses (no new recording, the actor's own take).

The dialogue research (games/research_notes/Dialogue heuristics, rules 5 and 12): trim from the start or the end at a
clean breath, never mid-word. A line's subtitle (LongText) is split into sentences; the audio's pauses are found from
the loudness; the sentences are matched to the pauses in order (the longest pauses nearest each sentence end's share
of the text); the kept span is cut in the middle of its pauses with short fades, written as a game-format Ogg under
<game>\Voice\U2Cut\<Group>\<Node>.ogg (a new file: the game's own voices are never touched), and checked by whisper
(the words heard vs the kept text - an honest check, not a guess).

    py -3.13 dlgcut.py show Sanctuary_20G_002                  the sentences and the pauses found
    py -3.13 dlgcut.py cut Sanctuary_20G_002 keep=2-           keep sentences 2.. (1-based; "2-3", "-2", "1,3" too)
    py -3.13 dlgcut.py cut Sanctuary_20G_002 keep=2- check=0   skip the whisper check

Prints one JSON line: {"node", "file" (the Pkg.Group.Name the game plays), "text", "secs", "heard", "match"}.
The Oggs it makes are derived from the game's audio: they stay on this PC (never committed or shared).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

import corpus
import vs_common as vc

SR = 44100
FRAME = 0.01


def find_node(name):
    for n in corpus.u2_nodes():
        if n["node"].lower() == name.lower():
            return n
    raise SystemExit("no such node: " + name)


def sentences(text):
    parts = re.findall(r"[^.!?]+(?:[.!?]+|$)", text.strip())
    return [p.strip() for p in parts if p.strip(" .")]


def pauses(x, min_len=0.09):
    """quiet runs: (start_s, end_s) where the 10 ms RMS stays under a level set from the line's own loudness"""
    n = int(FRAME * SR)
    fr = x[:len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((fr ** 2).mean(axis=1) + 1e-12)
    talk = rms[rms > np.percentile(rms, 30)]
    thr = max(np.median(talk) * 0.12, 1e-4) if len(talk) else 1e-4
    quiet = rms < thr
    out, s = [], None
    for i, q in enumerate(list(quiet) + [False]):
        if q and s is None:
            s = i
        elif not q and s is not None:
            if (i - s) * FRAME >= min_len:
                out.append((s * FRAME, i * FRAME))
            s = None
    # the head and tail silences are not sentence gaps
    lead = out[0][1] if out and out[0][0] == 0 else 0.0
    tail = out[-1][0] if out and out[-1][1] >= len(quiet) * FRAME - FRAME else len(x) / SR
    return [p for p in out if p[0] > 0 and p[1] < len(quiet) * FRAME - FRAME], lead, tail


def match(sents, gaps, lead, tail):
    """the k-1 sentence ends -> pauses, in order: maximise pause length minus the distance from where the text says
    the sentence should end (its share of the characters over the spoken span)"""
    k = len(sents)
    if k < 2:
        return []
    chars = np.cumsum([len(s) for s in sents])[:-1] / sum(len(s) for s in sents)
    want = lead + chars * (tail - lead)
    m = len(gaps)
    if m < k - 1:
        raise SystemExit("only %d pauses for %d sentence gaps - cut by hand" % (m, k - 1))
    mid = np.array([(a + b) / 2 for a, b in gaps])
    ln = np.array([b - a for a, b in gaps])
    NEG = -1e9
    best = np.full((k - 1, m), NEG)
    back = np.zeros((k - 1, m), int)
    for i in range(k - 1):
        for j in range(m):
            sc = ln[j] * 4 - abs(mid[j] - want[i]) / max(0.4, tail - lead) * 3
            if i == 0:
                best[i, j] = sc
            else:
                prev = best[i - 1, :j]
                if len(prev) and prev.max() > NEG:
                    back[i, j] = int(prev.argmax())
                    best[i, j] = prev.max() + sc
    j = int(best[k - 2].argmax())
    path = [j]
    for i in range(k - 2, 0, -1):
        j = back[i, j]
        path.append(j)
    return [gaps[j] for j in reversed(path)]


def keep_set(spec, k):
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        if "-" in part:
            lo, hi = int(a) if a else 1, int(b) if b else k
            out.update(range(lo, hi + 1))
        else:
            out.add(int(part))
    return sorted(i for i in out if 1 <= i <= k)


def spans(x, sents, gaps, lead, tail):
    """each sentence's (start, end) in seconds: from the middle of the pause before to the middle of the pause after"""
    cuts = [lead] + [(a + b) / 2 for a, b in gaps] + [tail]
    return [(max(0.0, cuts[i] - (0.04 if i == 0 else 0)), min(len(x) / SR, cuts[i + 1] + (0.06 if i == len(sents) - 1 else 0)))
            for i in range(len(sents))]


def heard(wav):
    if not os.path.exists(vc.WHISPER_PY):
        return None
    p = subprocess.run([vc.WHISPER_PY, os.path.join(vc.HERE, "align_words.py"), "--transcribe", wav],
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])[wav]
    except Exception:
        return None


def words(t):
    return re.findall(r"[a-z']+", t.lower())


def main():
    a = sys.argv[1:]
    opts = dict(s.split("=", 1) for s in a if "=" in s)
    a = [s for s in a if "=" not in s]
    cmd, name = a[0], a[1]
    n = find_node(name)
    if not n["sound"]:
        raise SystemExit("node has no voice: " + name)
    x = vc.decode(corpus.ogg_path(n["sound"]), sr=SR)
    sents = sentences(n["text"])
    # fast talkers leave short breaths: lower the shortest pause until every sentence gap has one
    for min_len in (0.09, 0.06, 0.04, 0.025):
        gaps, lead, tail = pauses(x, min_len)
        if len(gaps) >= len(sents) - 1:
            break
    chosen = match(sents, gaps, lead, tail)
    sp = spans(x, sents, chosen, lead, tail)
    if cmd == "show":
        print("%s  %.2f s  voice %s" % (n["node"], len(x) / SR, n["sound"]))
        print("pauses: " + ", ".join("%.2f-%.2f" % g for g in gaps))
        for i, (s, (t0, t1)) in enumerate(zip(sents, sp), 1):
            print("  %d  %5.2f-%5.2f  %s" % (i, t0, t1, s))
        return
    keep = keep_set(opts.get("keep", "1-"), len(sents))
    if not keep:
        raise SystemExit("nothing kept")
    if keep != list(range(keep[0], keep[-1] + 1)):
        raise SystemExit("keep one run of sentences (a gap in the middle needs a splice, not a cut)")
    t0, t1 = sp[keep[0] - 1][0], sp[keep[-1] - 1][1]
    y = x[int(t0 * SR):int(t1 * SR)].copy()
    f = int(0.012 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    group = n["sound"].split(".")[1] if n["sound"].count(".") >= 2 else "Lines"
    game_name = "U2Cut.%s.%s" % (group, n["node"])
    out = os.path.join(vc.U2_GAME, "Voice", "U2Cut", group, n["node"] + ".ogg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    vc.write_ogg(out, y, sr=SR, out_sr=44100)
    text = "  ".join(sents[i - 1] for i in keep)
    res = {"node": n["node"], "file": game_name, "text": text, "secs": round(len(y) / SR, 2), "keep": opts.get("keep", "1-")}
    if opts.get("check", "1") != "0":
        wav = os.path.join(vc.HOME, "dlgcut", n["node"] + ".wav")
        vc.write_wav(wav, y, sr=SR)
        h = heard(wav)
        if h is not None:
            want, got = words(text), words(h)
            common = sum(1 for w in want if w in got)
            extra = [w for w in got if w not in want]
            res["heard"] = h
            res["match"] = round(common / max(1, len(want)), 2)
            res["extra_words"] = extra[:8]
    print(json.dumps(res))


if __name__ == "__main__":
    main()
