"""Build the unit bank: words + phones with times and prosody features.

    py -3.13 bank.py <bank> [dtw|asr]   (needs lines.jsonl from corpus.py, asr.jsonl from align_words.py,
                                         and for dtw (default, sharper) dtw.jsonl from align_dtw.py)

Steps per clip:
 1. match whisper's words to the known line text (difflib); only agreeing words become units;
 2. snap word edges to the quietest 5 ms frame nearby, trim silence;
 3. split each word into its eSpeak phonemes by optimal segmentation: N segments over the MFCC frames
    that minimise in-segment spectral spread plus a duration prior (a poor man's forced aligner;
    the real-data upgrade is Montreal Forced Aligner, see design.md);
 4. record f0 / loudness at every unit edge for join costs.
Writes VOICESPLICE_HOME\\banks\\<bank>\\bank.json.
"""
import difflib
import json
import os
import sys

import numpy as np

import vs_common as vc

FPS = int(1 / vc.HOP)


def match_words(text, asr):
    want = vc.tokenize(text)
    got = []                                   # (key, s, e, p)
    for w in asr:
        ks = [k for k, _ in vc.tokenize(w["w"])]
        if not ks:
            continue
        step = (w["e"] - w["s"]) / len(ks)
        for i, k in enumerate(ks):
            got.append((k, w["s"] + i * step, w["s"] + (i + 1) * step, w["p"] if len(ks) == 1 else w["p"] * 0.8))
    sm = difflib.SequenceMatcher(a=[k for k, _ in want], b=[g[0] for g in got], autojunk=False)
    out = [None] * len(want)
    for tag, a0, a1, b0, b1 in sm.get_opcodes():
        if tag == "equal":
            for i in range(a1 - a0):
                k, s, e, p = got[b0 + i]
                out[a0 + i] = {"k": want[a0 + i][0], "punct": want[a0 + i][1], "s": s, "e": e, "conf": p}
    return want, out


def snap(t, rms, lo, hi, win=0.06):
    a, b = max(lo, int((t - win) * FPS)), min(hi, int((t + win) * FPS))
    if b <= a:
        return t
    return (a + int(np.argmin(rms[a:b + 1]))) / FPS


def trim(s, e, rms, thr):
    a, b = int(s * FPS), int(e * FPS)
    while a < b - 4 and rms[a] < thr:
        a += 1
    while b > a + 4 and rms[min(b, len(rms) - 1)] < thr:
        b -= 1
    return a / FPS, b / FPS


def segment(feat, phs):
    """Optimal split of feat frames [T, D] into len(phs) segments. Returns boundaries (frame idx, len N+1)."""
    T, N = len(feat), len(phs)
    if N == 1 or T < N * 2:
        return list(np.linspace(0, T, N + 1).astype(int))
    c1 = np.vstack([np.zeros(feat.shape[1]), np.cumsum(feat, axis=0)])
    c2 = np.concatenate([[0.0], np.cumsum((feat ** 2).sum(axis=1))])
    exp = np.array([vc.expected_dur(p) for p in phs])
    exp = exp / exp.sum() * T

    INF = 1e18
    D = np.full((N + 1, T + 1), INF)
    B = np.zeros((N + 1, T + 1), dtype=int)
    D[0, 0] = 0
    for j in range(1, N + 1):
        for b in range(2 * j, T - 2 * (N - j) + 1):
            a = np.arange(max(2 * (j - 1), b - int(exp[j - 1] * 4) - 4), b - 1)
            if not len(a):
                continue
            n = b - a
            s = c1[b] - c1[a]
            spread = (c2[b] - c2[a]) - (s * s).sum(axis=1) / n
            v = D[j - 1, a] + spread + 1.5 * n * np.log(n / exp[j - 1]) ** 2
            k = int(np.argmin(v))
            D[j, b], B[j, b] = v[k], a[k]
    bounds, b = [T], T
    for j in range(N, 0, -1):
        b = B[j, b]
        bounds.append(b)
    return bounds[::-1]


def edge(track, t0, t1, at_start, span=0.03):
    a, b = int(t0 * FPS), max(int(t0 * FPS) + 1, int(t1 * FPS))
    seg = track[a:min(b, a + int(span * FPS))] if at_start else track[max(a, b - int(span * FPS)):b]
    v = seg[seg > 0] if len(seg) else seg
    return float(np.median(v)) if len(v) else 0.0


def build(name, align="dtw"):
    d = vc.bank_dir(name)
    lines = {r["id"]: r for r in vc.jl_read(os.path.join(d, "lines.jsonl"))}
    asr = {r["id"]: r for r in vc.jl_read(os.path.join(d, "asr.jsonl"))}
    dtwp = os.path.join(d, "dtw.jsonl")
    dtw = {r["id"]: r for r in vc.jl_read(dtwp)} if align == "dtw" and os.path.exists(dtwp) else {}
    clips, words, phones = {}, [], []
    kept = total = 0
    for cid, r in lines.items():
        if cid not in asr:
            continue
        x, sr = vc.read_wav(r["wav"])
        rms = vc.rms_track(x, sr)
        f0 = vc.f0_track(x, sr)
        mf = vc.mfcc(x, sr)
        mf = (mf - mf.mean(axis=0)) / (mf.std(axis=0) + 1e-6)
        thr = max(1e-3, float(np.percentile(rms, 95)) * 0.06)    # about -24 dB under the loud part
        want, got = match_words(r["text"], asr[cid]["words"])
        total += len(want)
        if cid in dtw and len(dtw[cid]["words"]) == len(want):     # whisper says WHICH words, DTW says WHERE
            for g, dw in zip(got, dtw[cid]["words"]):
                if g is not None:
                    g["s"], g["e"] = dw["s"], min(dw["e"], len(x) / sr)
        clips[cid] = {"wav": r["wav"], "dur": len(x) / sr, "text": r["text"], "src": r.get("src", "")}
        line_ph = []
        for i, g in enumerate(got):
            if g is None or g["conf"] < 0.3:
                continue
            nxt = got[i + 1] if i + 1 < len(got) else None
            prv = got[i - 1] if i > 0 else None
            s = snap(g["s"], rms, 0, len(rms) - 1) if prv else g["s"]
            e = snap(g["e"], rms, 0, len(rms) - 1) if nxt else g["e"]
            s, e = trim(s, min(e, len(x) / sr), rms, thr)
            if e - s < 0.06:
                continue
            phs = vc.phonemes(g["k"])
            if not phs:
                continue
            a, b = int(s * FPS), int(e * FPS)
            bnds = segment(mf[a:min(b, len(mf))], phs)
            wi = len(words)
            w = {"k": g["k"], "clip": cid, "s": round(s, 4), "e": round(e, 4), "li": i, "n": len(want),
                 "punct": g["punct"], "conf": g["conf"], "f0s": edge(f0, s, e, True), "f0e": edge(f0, s, e, False),
                 "f0m": float(np.median(f0[a:b][f0[a:b] > 0])) if (f0[a:b] > 0).any() else 0.0,
                 "rms": float(np.sqrt(np.mean(x[int(s * sr):int(e * sr)] ** 2))), "ph": [],
                 "prevk": prv["k"] if prv else "", "nextk": nxt["k"] if nxt else ""}
            for j, p in enumerate(phs):
                ps, pe = s + bnds[j] / FPS, s + bnds[j + 1] / FPS
                w["ph"].append(len(phones))
                phones.append({"p": p, "clip": cid, "s": round(ps, 4), "e": round(pe, 4), "w": wi, "i": j,
                               "nw": len(phs), "f0s": edge(f0, ps, pe, True, 0.015),
                               "f0e": edge(f0, ps, pe, False, 0.015),
                               "rs": float(rms[min(int(ps * FPS), len(rms) - 1)]),
                               "re": float(rms[min(max(int(pe * FPS) - 1, 0), len(rms) - 1)])})
                line_ph.append(len(phones) - 1)
            words.append(w)
            kept += 1
        for a_, b_ in zip(line_ph, line_ph[1:]):       # source neighbours: zero join cost when kept together
            if phones[b_]["s"] - phones[a_]["e"] < 0.02:
                phones[a_]["succ"] = b_
    vf = [w["f0m"] for w in words if w["f0m"] > 0]
    stats = {"f0_median": float(np.median(vf)) if vf else 120.0,
             "rms_median": float(np.median([w["rms"] for w in words])) if words else 0.05,
             "words_kept": kept, "words_total": total, "vocab": len({w["k"] for w in words}),
             "phone_types": sorted({p["p"] for p in phones})}
    json.dump({"name": name, "sr": vc.SR, "clips": clips, "words": words, "phones": phones, "stats": stats},
              open(os.path.join(d, "bank.json"), "w", encoding="utf-8"))
    print("%s: %d/%d words aligned, vocab %d, %d phones (%d types), f0 median %.0f Hz"
          % (name, kept, total, stats["vocab"], len(phones), len(stats["phone_types"]), stats["f0_median"]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "dtw")
