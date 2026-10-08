"""Text -> spliced voice line from a bank (TF2/VOX-style concatenation with unit selection).

    py -3.13 synth.py <bank> "New line of dialogue." [out=<path.wav>] [ogg=<path.ogg>]
                      [mode=hybrid|hybrid_raw|vcline|splice|tts|piper|phones] [vc_voice=<piper voice>]

Modes (stage 2, see say()): hybrid (default) keeps runs of words the speaker really said, renders new
words as one Piper phrase converted into his voice with kNN-VC (vc_knn.py, torch venv), and smooths
F0/energy across the joins with WORLD; when a line would be too choppy (> HYBRID_MAX_NEW new words or
> HYBRID_MAX_TIGHT pause-less joins between different recordings) it converts the whole line instead
(= vcline). splice/tts/phones are the stage-1 planners below.

Planning, cheapest first (costs in plan_line):
  1. runs of words that were spoken together in one source line (n-grams; joins inside are free);
  2. single recorded words, picked by sentence position, neighbours and pitch/energy at the joins;
  3. for words the bank never heard (oov=phones): a diphone chain over the word's eSpeak phonemes,
     cut mid-phone, source-consecutive runs preferred (phone_chain);
  4. oov=tts, or no unit for some phone: a Piper word, pitch-moved and loudness-matched toward the
     bank (the slot where real voice conversion goes, see design.md).
Joins: words get short fades and the line's punctuation pauses; diphone pieces get a 10 ms crossfade
at the best-correlating offset (WSOLA-style). Each unit is loudness-matched to the bank's median and
diphone pieces are pitch-flattened toward their own mean (resampling, small shifts only).
"""
import json
import os
import sys

import numpy as np

import vs_common as vc

SUBST = {"ɐ": ["ə", "ʌ"], "ᵻ": ["ɪ", "ə"], "ɾ": ["t", "d"], "ɚ": ["ɜ", "ə"], "ɜ": ["ɚ"], "ʔ": ["t"],
         "ɑ": ["ɔ", "ʌ"], "ɔ": ["ɑ"], "i": ["ɪ"], "ɪ": ["i", "ᵻ"], "u": ["ʊ"], "ʊ": ["u"], "ʲ": []}


class Bank:
    def __init__(self, name):
        d = vc.bank_dir(name)
        b = json.load(open(os.path.join(d, "bank.json"), encoding="utf-8"))
        self.__dict__.update(b)
        self.by_k, self.by_p, self.at = {}, {}, {}
        for i, w in enumerate(self.words):
            self.by_k.setdefault(w["k"], []).append(i)
            self.at[(w["clip"], w["li"])] = i
        for i, p in enumerate(self.phones):
            self.by_p.setdefault(p["p"], []).append(i)
        self._audio = {}

    def audio(self, clip):
        if clip not in self._audio:
            self._audio[clip] = vc.read_wav(self.clips[clip]["wav"])[0]
        return self._audio[clip]


def join_cost(f0a, ra, f0b, rb):
    c = 0.0
    if f0a > 0 and f0b > 0:
        c += min(abs(vc.semitones(f0a, f0b)), 8) / 4
    if ra > 0 and rb > 0:
        c += min(abs(np.log(ra / rb)), 3) * 0.3
    return c


# ---------------------------------------------------------------- phone chains

def _alts(p):
    return [p] + SUBST.get(p, [])


def phone_chain(bank, phs, prev_k="", next_k=""):
    """Diphone Viterbi: units run from the middle of one phone to the middle of the next, so joins
    land in the steady part of a sound (the classic diphone-synthesis cut). Pairs the bank never
    heard together are faked from two separate phones (costly). Returns (cost, slices) where
    slices = ((clip, s, e), ...), or None if some phone has no unit at all."""
    P = bank.phones
    phs = [p for p in phs if not (p in SUBST and not SUBST[p])]
    if not phs or any(not any(bank.by_p.get(q) for q in _alts(p)) for p in phs):
        return None
    mid = lambda i: (P[i]["s"] + P[i]["e"]) / 2
    N = len(phs)

    def single(p, j):
        ids = [i for q in _alts(p) for i in bank.by_p.get(q, [])]
        def tc(i):
            u = P[i]
            c = 0.0 if u["p"] == p else 0.6
            c += 0.0 if (u["i"] == 0) == (j == 0) else 0.3
            c += 0.0 if (u["i"] == u["nw"] - 1) == (j == N - 1) else 0.3
            return c
        return sorted((tc(i), i) for i in ids)
    if N == 1:
        c, i = single(phs[0], 0)[0]
        return c, ((P[i]["clip"], P[i]["s"], P[i]["e"]),)
    steps = []
    for k in range(N - 1):
        X, Y = phs[k], phs[k + 1]
        cand = []
        for i in (i for q in _alts(X) for i in bank.by_p.get(q, [])):
            j = P[i].get("succ")
            if j is None or P[j]["p"] not in _alts(Y):
                continue
            c = (0.0 if P[i]["p"] == X else 0.4) + (0.0 if P[j]["p"] == Y else 0.4)
            c += 0.0 if (k > 0) or P[i]["i"] == 0 else 0.3
            c += 0.0 if (k < N - 2) or P[j]["i"] == P[j]["nw"] - 1 else 0.3
            cand.append((c, i, j))
        cand = sorted(cand)[:60]
        if not cand:                                   # fake the pair from two lone phones
            xs, ys = single(X, k)[:8], single(Y, k + 1)[:8]
            cand = [(1.5 + cx + cy, i, j) for cx, i in xs for cy, j in ys]
        steps.append(cand)
    V = [{(i, j): c for c, i, j in steps[0]}]
    back = [{}]
    for k in range(1, len(steps)):
        cur, bk = {}, {}
        for c, i, j in steps[k]:
            best, arg = 1e9, None
            for (pi, pj), pv in V[-1].items():
                jc = 0.0 if pj == i else 0.6 + join_cost(P[pj]["f0e"], P[pj]["re"], P[i]["f0s"], P[i]["rs"])
                if pv + jc < best:
                    best, arg = pv + jc, (pi, pj)
            cur[(i, j)], bk[(i, j)] = best + c, arg
        V.append(cur)
        back.append(bk)
    end = min(V[-1], key=V[-1].get)
    path = [end]
    for k in range(len(steps) - 1, 0, -1):
        path.append(back[k][path[-1]])
    path = path[::-1]
    slices = []
    for k, (i, j) in enumerate(path):
        s0 = P[i]["s"] if k == 0 else mid(i)
        e0 = P[j]["e"] if k == len(path) - 1 else mid(j)
        if P[i].get("succ") == j:
            parts = [(P[i]["clip"], s0, e0)]
        else:
            parts = [(P[i]["clip"], s0, P[i]["e"]), (P[j]["clip"], P[j]["s"], e0)]
        for part in parts:
            if slices and slices[-1][0] == part[0] and abs(slices[-1][2] - part[1]) < 1e-4:
                slices[-1] = (part[0], slices[-1][1], part[2])
            else:
                slices.append(part)
    return V[-1][end], tuple(slices)


# ---------------------------------------------------------------- plan

def plan_line(bank, text, max_cands=30, force_phones=False, oov="phones"):
    toks = vc.tokenize(text)
    n = len(toks)
    final = lambda i: toks[i][1] in (".", "?") or i == n - 1
    opts_at = {i: [] for i in range(n + 1)}      # options ending at i: (start, kind, data, cost, f0s, rs, f0e, re)

    def word_tc(w, i):
        c = 0.5 * (1 - w["conf"])
        wf = w["punct"] in (".", "?") or w["li"] == w["n"] - 1
        c += 0.0 if wf == final(i) else 0.6
        c -= 0.25 if i > 0 and w["prevk"] == toks[i - 1][0] else 0
        c -= 0.25 if i + 1 < n and w["nextk"] == toks[i + 1][0] else 0
        return c

    for i, (k, _) in enumerate(toks):
        ws = [] if force_phones else sorted(bank.by_k.get(k, []), key=lambda wi: word_tc(bank.words[wi], i))[:max_cands]
        for wi in ws:
            w = bank.words[wi]
            opts_at[i + 1].append((i, "word", (wi,), 0.5 + word_tc(w, i), w["f0s"], w["rms"], w["f0e"], w["rms"]))
            run, L = [wi], 1                       # n-gram runs from the same source line
            while i + L < n and toks[i + L - 1][1] == "":
                nx = bank.at.get((w["clip"], bank.words[run[-1]]["li"] + 1))
                if nx is None or bank.words[nx]["k"] != toks[i + L][0]:
                    break
                run.append(nx)
                L += 1
                last = bank.words[nx]
                c = 0.2 * L + word_tc(w, i) + word_tc(last, i + L - 1)
                opts_at[i + L].append((i, "run", tuple(run), c, w["f0s"], w["rms"], last["f0e"], last["rms"]))
        if not ws:
            ch = phone_chain(bank, vc.phonemes(k), toks[i - 1][0] if i else "", toks[i + 1][0] if i + 1 < n else "")
            if ch and oov == "phones":
                c, sl = ch
                f0a = f0b = bank.stats["f0_median"]
                opts_at[i + 1].append((i, "phones", sl, 2.0 + c / max(1, len(sl)), f0a, 0, f0b, 0))
            elif oov == "vc":
                opts_at[i + 1].append((i, "vc", (k,), 3.0, 0, 0, 0, 0))
            else:
                opts_at[i + 1].append((i, "tts", (k,), 6.0, 0, 0, 0, 0))
    # outer Viterbi over options
    V = {0: {None: (0.0, None)}}                  # end -> {option: (cost, back)}
    for e in range(1, n + 1):
        V[e] = {}
        for o in opts_at[e]:
            s = o[0]
            best = (1e9, None)
            for po, (pc, _) in V.get(s, {}).items():
                jc = 0.0
                if po is not None and toks[s - 1][1] == "":
                    jc = join_cost(po[6], po[7], o[4], o[5]) * 0.5
                if pc + jc + o[3] < best[0]:
                    best = (pc + jc + o[3], po)
            if best[1] is not None or s == 0:
                V[e][o] = best
    end = min(V[n], key=lambda o: V[n][o][0])
    chain, o, e = [], end, n
    while o is not None:
        chain.append(o)
        prev = V[e][o][1]
        e = o[0]
        o = prev
    chain = chain[::-1]
    return toks, chain, V[n][end][0]


# ---------------------------------------------------------------- audio

def fade(x, a, b):
    x = x.copy()
    na, nb = min(len(x) // 2, a), min(len(x) // 2, b)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


def pitch_shift(x, st):
    """Resample pitch shift (duration changes with it; fine for small moves)."""
    if abs(st) < 0.3 or len(x) < 4:
        return x
    r = 2 ** (st / 12)
    t = np.arange(0, len(x) - 1, r)
    return np.interp(t, np.arange(len(x)), x).astype(np.float32)


def xfade_join(a, b, sr, ms=10, search_ms=4):
    n, s = int(sr * ms / 1000), int(sr * search_ms / 1000)
    if len(a) < n + s or len(b) < n + 2 * s:
        return np.concatenate([a, b])
    tail = a[-n:]
    best, off = -1e9, 0
    for k in range(0, 2 * s):
        seg = b[k:k + n]
        c = float(np.dot(tail, seg)) / (np.linalg.norm(seg) * np.linalg.norm(tail) + 1e-9)
        if c > best:
            best, off = c, k
    b = b[off:]
    w = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    mid = tail * (1 - w) + b[:n] * w
    return np.concatenate([a[:-n], mid, b[n:]])


def slice_(bank, clip, s, e, pad=0.0):
    x = bank.audio(clip)
    return x[max(0, int((s - pad) * vc.SR)):min(len(x), int((e + pad) * vc.SR))].copy()


_TTS = {}


def tts_word(word, voice, f0_target):
    from piper import PiperVoice
    if voice not in _TTS:
        _TTS[voice] = PiperVoice.load(os.path.join(vc.PIPER_VOICES, voice + ".onnx"))
    x = np.concatenate([c.audio_float_array for c in _TTS[voice].synthesize(word)])
    r = vc.rms_track(x, vc.SR)
    on = np.where(r > r.max() * 0.05)[0]
    if len(on):
        x = x[on[0] * int(vc.HOP * vc.SR):(on[-1] + 1) * int(vc.HOP * vc.SR)]
    f0 = vc.f0_track(x, vc.SR)
    if (f0 > 0).any():
        x = pitch_shift(x, max(-6, min(6, vc.semitones(f0_target, float(np.median(f0[f0 > 0]))))))
    return x


def piper_text(text, voice):
    from piper import PiperVoice
    if voice not in _TTS:
        _TTS[voice] = PiperVoice.load(os.path.join(vc.PIPER_VOICES, voice + ".onnx"))
    return np.concatenate([c.audio_float_array for c in _TTS[voice].synthesize(text)]).astype(np.float32)


def trim_quiet(x, rel=0.04):
    r = vc.rms_track(x, vc.SR)
    on = np.where(r > r.max() * rel)[0]
    h = int(vc.HOP * vc.SR)
    return x[on[0] * h:(on[-1] + 1) * h] if len(on) else x


def to_bank_pitch(x, f0_target, limit=6):
    f0 = vc.f0_track(x, vc.SR)
    if (f0 > 0).any():
        x = pitch_shift(x, max(-limit, min(limit, vc.semitones(f0_target, float(np.median(f0[f0 > 0]))))))
    return x


class VCWorker:
    """kNN-VC + pyworld live in the torch venv (vc_knn.py); this keeps one worker process per run."""
    _proc = None

    @classmethod
    def call(cls, **req):
        import subprocess
        if cls._proc is None or cls._proc.poll() is not None:
            cls._proc = subprocess.Popen([vc.VC_PY, "-I", os.path.join(vc.HERE, "vc_knn.py"), "serve"],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                         encoding="utf-8", bufsize=1,
                                         env=dict(os.environ, VOICESPLICE_MODELS=vc.MODELS,
                                                  VOICESPLICE_CACHE=vc.CACHE))
        cls._proc.stdin.write(json.dumps(req) + "\n")
        cls._proc.stdin.flush()
        r = json.loads(cls._proc.stdout.readline())
        if not r.get("ok"):
            raise RuntimeError("vc_knn: %s" % r.get("error"))
        return r


def tmp_wav(tag):
    return os.path.join(vc.HOME, "out", "_tmp", "%s_%d.wav" % (tag, os.getpid()))


def knn_convert(bank, x):
    """Piper (or any) audio -> the bank speaker's voice with kNN-VC over the bank's own clips."""
    a, b = tmp_wav("vc_in"), tmp_wav("vc_out")
    vc.write_wav(a, x)
    VCWorker.call(op="convert", bank_dir=vc.bank_dir(bank.name), topk=VC_TOPK, **{"in": a, "out": b})
    return trim_quiet(vc.read_wav(b)[0], 0.03)


def world_smooth(x, joins):
    if not joins:
        return x, 0
    a, b = tmp_wav("sm_in"), tmp_wav("sm_out")
    vc.write_wav(a, x)
    r = VCWorker.call(op="smooth", joins=[j / vc.SR for j in joins], **{"in": a, "out": b})
    return vc.read_wav(b)[0], r["smoothed"]


def phrase_text(toks, s, e):
    return " ".join(k + p for k, p in toks[s:e])


def render(bank, toks, chain, fallback="en_US-lessac-medium", vc_voice="en_US-john-medium"):
    """Returns (audio, report, joins); joins = sample positions of word-to-word joins without a pause."""
    sr, target = vc.SR, bank.stats["rms_median"]
    out = np.zeros(int(0.08 * sr), dtype=np.float32)
    report, joins, last_gap = [], [], None
    groups, i = [], 0                       # consecutive "vc" words are converted as one Piper phrase
    while i < len(chain):
        if chain[i][1] == "vc":
            j = i
            while j + 1 < len(chain) and chain[j + 1][1] == "vc":
                j += 1
            groups.append((chain[i][0], "vc", (chain[i][0], chain[j][0] + 1)))
            i = j + 1
        else:
            groups.append(chain[i])
            i += 1
    for o in groups:
        s, kind, data = o[0], o[1], o[2]
        if kind == "vc":
            s, e = data
            x = to_bank_pitch(trim_quiet(piper_text(phrase_text(toks, s, e), vc_voice)), bank.stats["f0_median"])
            x = knn_convert(bank, x)
            x = fade(x, int(0.004 * sr), int(0.01 * sr))
            g = target / (np.sqrt(np.mean(x ** 2)) + 1e-6)
            src = "Piper %s -> kNN-VC" % vc_voice
        elif kind in ("word", "run"):
            a, b = bank.words[data[0]], bank.words[data[-1]]
            x = slice_(bank, a["clip"], a["s"], b["e"], pad=0.012)
            x = fade(x, int(0.004 * sr), int(0.008 * sr))
            g = target / (np.mean([bank.words[i]["rms"] for i in data]) + 1e-6)
            src = "%s %s" % (a["clip"], " ".join(bank.words[i]["k"] for i in data))
        elif kind == "phones":
            pieces = [slice_(bank, c, s0, e0, pad=0.004) for c, s0, e0 in data]
            f0s = []
            for y in pieces:
                f = vc.f0_track(y, sr) if len(y) > int(0.04 * sr) else np.zeros(1)
                f0s.append(float(np.median(f[f > 0])) if (f > 0).any() else 0.0)
            vf = [f for f in f0s if f > 0]
            mean_f0 = float(np.mean(vf)) if vf else 0.0
            x = None
            for y, f in zip(pieces, f0s):
                if f > 0 and mean_f0 > 0:
                    y = pitch_shift(y, max(-3, min(3, vc.semitones(mean_f0, f))))
                x = y if x is None else xfade_join(x, y, sr)
            x = fade(x, int(0.004 * sr), int(0.008 * sr))
            g = target / (np.sqrt(np.mean(x ** 2)) + 1e-6)
            src = "diphones from %d pieces: %s" % (len(data), ", ".join("%s %.2f-%.2f" % d for d in data))
        else:
            x = tts_word(data[0], fallback, bank.stats["f0_median"])
            x = fade(x, int(0.004 * sr), int(0.01 * sr))
            g = target / (np.sqrt(np.mean(x ** 2)) + 1e-6)
            src = "TTS " + fallback
        x = x * float(np.clip(g, 0.5, 2.0))
        if last_gap is not None and last_gap < 0.1:
            joins.append(len(out) - int(last_gap * sr / 2))
        out = np.concatenate([out, x])
        e = data[1] if kind == "vc" else s + (len(data) if kind == "run" else 1)
        p = toks[e - 1][1]
        gap = 0.38 if p in (".", "?") else 0.2 if p == "," else 0.025
        last_gap = gap
        out = np.concatenate([out, np.zeros(int(gap * sr), dtype=np.float32)])
        report.append({"words": " ".join(t for t, _ in toks[s:e]), "kind": kind, "from": src})
    peak = np.abs(out).max()
    if peak > 0.97:
        out *= 0.97 / peak
    return out, report, joins


def render_line(bank, text, voice, convert):
    """Whole line from Piper; convert=True puts it through kNN-VC into the bank speaker's voice."""
    x = trim_quiet(piper_text(text, voice))
    if convert:
        x = knn_convert(bank, to_bank_pitch(x, bank.stats["f0_median"]))
    x = x * float(np.clip(bank.stats["rms_median"] / (np.sqrt(np.mean(x ** 2)) + 1e-6), 0.3, 3.0))
    x = np.concatenate([np.zeros(int(0.08 * vc.SR), np.float32), x, np.zeros(int(0.3 * vc.SR), np.float32)])
    peak = np.abs(x).max()
    if peak > 0.97:
        x *= 0.97 / peak
    kind = "vcline" if convert else "piper"
    return x, [{"words": " ".join(k for k, _ in vc.tokenize(text)), "kind": kind,
                "from": "Piper %s%s" % (voice, " -> kNN-VC" if convert else "")}]


# hybrid falls back to a whole converted line when splicing would be too choppy
HYBRID_MAX_NEW = 0.5        # share of words the bank lacks
HYBRID_MAX_TIGHT = 0.6      # share of word-to-word joins with no pause that join two different recordings

MODES = ("hybrid", "hybrid_raw", "vcline", "splice", "tts", "piper", "phones")
DEFAULT_MODE = "hybrid"
VC_TOPK = 4                 # kNN-VC neighbours per frame (the paper's default)
VC_VOICE = "en_US-john-medium"   # Piper voice that kNN-VC converts from


_BANKS = {}


def say(bank_name, text, out=None, ogg=None, fallback="en_US-lessac-medium", quiet=False, force_phones=False,
        oov=None, mode=None, vc_voice=None):
    """mode: hybrid (default: recorded words + kNN-VC'd Piper for new words, WORLD-smoothed joins, or the
    whole line converted when splicing would be choppy), hybrid_raw (same, no WORLD pass), vcline (whole
    line Piper -> kNN-VC), splice (stage-1 units: new words as diphones), tts (stage-1: new words from
    pitch-moved Piper), piper (plain Piper line), phones (every word as diphones). oov= is the old name."""
    vc_voice = vc_voice or VC_VOICE
    if bank_name not in _BANKS:
        _BANKS[bank_name] = Bank(bank_name)
        _BANKS[bank_name].name = bank_name
    bank = _BANKS[bank_name]
    if mode is None:
        mode = {"phones": "splice", "tts": "tts", "vc": "hybrid"}.get(oov, "phones" if force_phones else DEFAULT_MODE)
    cost, smoothed, chosen = 0.0, 0, mode
    if mode in ("piper", "vcline"):
        x, report = render_line(bank, text, vc_voice, mode == "vcline")
    else:
        plan_oov = {"splice": "phones", "phones": "phones", "tts": "tts"}.get(mode, "vc")
        toks, chain, cost = plan_line(bank, text, force_phones=(mode == "phones"), oov=plan_oov)
        n = max(1, len(toks))
        new = sum(1 for o in chain if o[1] == "vc")
        ends = [o[0] + (len(o[2]) if o[1] == "run" else 1) for o, nx in zip(chain, chain[1:])
                if not (o[1] == nx[1] == "vc")]          # a run of new words is one Piper phrase
        tight = sum(1 for e in ends if toks[e - 1][1] == "") / max(1, n - 1)
        if mode.startswith("hybrid") and (new / n > HYBRID_MAX_NEW or (n >= 4 and tight > HYBRID_MAX_TIGHT)):
            chosen = "vcline"
            x, report = render_line(bank, text, vc_voice, True)
        else:
            x, report, joins = render(bank, toks, chain, fallback, vc_voice)
            if mode == "hybrid":
                x, smoothed = world_smooth(x, joins)
    out = out or os.path.join(vc.HOME, "out", bank_name, "line.wav")
    vc.write_wav(out, x)
    if ogg:
        vc.write_ogg(ogg, x)
    kinds = {}
    for r in report:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + len(r["words"].split())
    info = {"text": text, "wav": out, "ogg": ogg, "seconds": round(len(x) / vc.SR, 2), "cost": round(cost, 2),
            "mode": mode, "rendered_as": chosen, "joins_smoothed": smoothed, "words_by_kind": kinds, "plan": report}
    with open(os.path.splitext(out)[0] + ".plan.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    if not quiet:
        for r in report:
            print("  %-7s %-28s <- %s" % (r["kind"], r["words"], r["from"]))
        print("%s  (%.2f s, %s as %s, %s)" % (out, info["seconds"], mode, chosen, kinds))
    return info


if __name__ == "__main__":
    a = [s for s in sys.argv[1:] if "=" not in s]
    o = dict(s.split("=", 1) for s in sys.argv[1:] if "=" in s)
    if len(a) < 2:
        print(__doc__)
    else:
        say(a[0], a[1], o.get("out"), o.get("ogg"), o.get("fallback", "en_US-lessac-medium"), oov=o.get("oov"),
            mode=o.get("mode"), vc_voice=o.get("vc_voice"))
