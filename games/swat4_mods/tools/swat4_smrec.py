"""SwatMinds player recorder (SMRec) loader + director player model trainer.

The mutator (bRecordPlayer) writes SwatMinds/System/SMRec_<map>_<date>_<part>.txt while a human plays.
This tool joins the parts, turns every 0.25 s sample into features the player could know at that moment,
and trains a small logistic model that forecasts trouble for the player:
  hurt10 = the player takes damage within the next 10 s
  fight5 = the player fires within the next 5 s
The director can use the forecast as a stress estimate (spawn when low, cull when high). Weights are
exported as SwatMinds.ini lines (feature means/scales + weights) so UnrealScript can evaluate the same model.

  py -3.13 -I swat4_smrec.py stats  [--dir DIR]
  py -3.13 -I swat4_smrec.py train  [--dir DIR] [--out tools/smrec_model.json] [--ini]
"""
import argparse, json, math, re, sys
from collections import defaultdict
from pathlib import Path

import numpy as np

DEFAULT_DIR = Path(r"F:\gogGames\SWAT 4\SwatMinds\System")
NAME = re.compile(r"(SMRec_.+)_(\d+)\.txt$")
LINE = re.compile(r"t=([\d.]+) (\S+) ?(.*)")
KV = re.compile(r"(\w+)=(\S*)")

FEATURES = ["hp", "speed", "crouch", "lean", "zoom", "flash", "gas", "stung", "ammo0",
            "seeE", "seeEarmed", "seeEclose", "seeO", "seeH", "seeOhurt",
            "memO", "memOage", "memE",
            "hear5", "hearO5", "hearSpeech5", "hearE5", "shot5", "hurt10p", "firstE10"]
LABELS = {"hurt10": ("hurt", 10.0), "fight5": ("shot", 5.0)}


def sessions(d):
    """{base: [path parts in order]}"""
    out = defaultdict(list)
    for p in Path(d).glob("SMRec_*.txt"):
        m = NAME.search(p.name)
        if m:
            out[m.group(1)].append((int(m.group(2)), p))
    return {b: [p for _, p in sorted(v)] for b, v in sorted(out.items())}


def parse_pawns(s):
    """'K:Name:x,y,z:yaw:state[:hpN]' (see) or 'K:Name:age:x,y,z:state' (mem) -> list of dicts"""
    out = []
    for tok in s.split():
        f = tok.split(":")
        if len(f) < 4:
            continue
        out.append({"k": f[0], "name": f[1], "f": f[2:]})
    return out


def load(paths):
    """one session -> (samples, events). sample = dict; event = (t, kind, rest)"""
    samples, events = [], []
    for p in paths:
        for ln in p.read_text(encoding="latin-1", errors="replace").splitlines():
            m = LINE.match(ln)
            if not m:
                continue
            t, typ, rest = float(m.group(1)), m.group(2), m.group(3)
            if typ == "S":
                head, _, tail = rest.partition(" |see")
                see, _, mem = tail.partition(" |mem")
                s = {k: v for k, v in KV.findall(head)}
                s["t"] = t
                s["see"] = parse_pawns(see)
                s["mem"] = parse_pawns(mem)
                samples.append(s)
            elif typ == "ev":
                kind, _, r = rest.partition(" ")
                events.append((t, kind, r))
            else:  # hear / say
                events.append((t, typ, rest))
    return samples, events


def num(s, k, d=0.0):
    try:
        return float(s.get(k, d))
    except ValueError:
        return d


def xyz(v):
    a = v.split(",")
    return np.array([float(a[0]), float(a[1]), float(a[2])]) if len(a) == 3 else None


def times(ev, pred):
    return np.array(sorted(t for t, k, r in ev if pred(k, r)), float)


def count(ts, t0, t1):
    """events in (t0, t1]"""
    return int(np.searchsorted(ts, t1, "right") - np.searchsorted(ts, t0, "right"))


def speech(k, r):
    """a heard sound that is not a footstep (voice lines, shouts, gear)"""
    f = r.split()
    return k == "hear" and len(f) > 1 and "Foot" not in f[1]


def features(samples, events):
    """-> X (n, F), Y {label: (n,)}, valid mask (enough future left for the labels)"""
    X, Y = [], {k: [] for k in LABELS}
    tend = samples[-1]["t"] if samples else 0
    T = {"hear": times(events, lambda k, r: k == "hear" and "cat=Footsteps" not in r),
         "hearO": times(events, lambda k, r: k == "hear" and r.startswith("O:") and "cat=Footsteps" not in r),
         "speech": times(events, speech),
         "hearE": times(events, lambda k, r: k == "hear" and r.startswith("E:")),
         "shot": times(events, lambda k, r: k == "shot"),
         "hurt": times(events, lambda k, r: k == "hurt"),
         "firstE": times(events, lambda k, r: k == "firstseen" and r.startswith("E:"))}
    for s in samples:
        t = s["t"]
        me = xyz(s.get("p", ""))
        v = xyz(s.get("v", "0,0,0"))
        see, mem = s["see"], s["mem"]
        E = [p for p in see if p["k"] == "E"]
        O = [p for p in see if p["k"] == "O"]
        Ea = [p for p in E if "/" in p["f"][2] and p["f"][2][0] == "c"]   # free, item out
        close = 0
        for p in E:
            q = xyz(p["f"][0])
            if q is not None and me is not None and np.linalg.norm(q - me) < 600:
                close += 1
        Oh = [p for p in O if len(p["f"]) > 3 and p["f"][3].startswith("hp") and float(p["f"][3][2:] or 100) < 100]
        mO = [p for p in mem if p["k"] == "O"]
        row = {
            "hp": num(s, "hp") / 100, "speed": float(np.linalg.norm(v)) / 300 if v is not None else 0,
            "crouch": num(s, "crouch"), "lean": float(num(s, "lean") != 0), "zoom": float(num(s, "fov", 85) < 80),
            "flash": num(s, "flash"), "gas": num(s, "gas"), "stung": num(s, "stung"),
            "ammo0": float(num(s, "ammo", -1) == 0),
            "seeE": len(E), "seeEarmed": len(Ea), "seeEclose": close, "seeO": len(O),
            "seeH": sum(p["k"] == "H" for p in see), "seeOhurt": len(Oh),
            "memO": len(mO), "memOage": (sum(float(p["f"][0]) for p in mO) / len(mO)) if mO else 0,
            "memE": sum(p["k"] == "E" for p in mem),
            "hear5": count(T["hear"], t - 5, t), "hearO5": count(T["hearO"], t - 5, t),
            "hearSpeech5": count(T["speech"], t - 5, t), "hearE5": count(T["hearE"], t - 5, t),
            "shot5": count(T["shot"], t - 5, t), "hurt10p": count(T["hurt"], t - 10, t),
            "firstE10": count(T["firstE"], t - 10, t),
        }
        X.append([row[f] for f in FEATURES])
        for lab, (kind, w) in LABELS.items():
            Y[lab].append(float(count(T[kind], t, t + w) > 0) if t + w <= tend else np.nan)
    return np.array(X, float).reshape(-1, len(FEATURES)), {k: np.array(v, float) for k, v in Y.items()}


def auc(y, p):
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    r = np.argsort(np.argsort(np.concatenate([pos, neg]))) + 1
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def fit(X, y, l2=1e-2, iters=3000, lr=0.5):
    w, b = np.zeros(X.shape[1]), 0.0
    for _ in range(iters):
        z = 1 / (1 + np.exp(-(X @ w + b)))
        g = z - y
        w -= lr * (X.T @ g / len(y) + l2 * w)
        b -= lr * g.mean()
    return w, b


def build(d):
    per = []
    for base, parts in sessions(d).items():
        smp, ev = load(parts)
        if len(smp) < 20:
            continue
        X, Y = features(smp, ev)
        per.append((base, X, Y, ev))
    return per


def cmd_stats(a):
    for base, X, Y, ev in build(a.dir):
        kinds = defaultdict(int)
        for _, k, _ in ev:
            kinds[k] += 1
        pos = {k: int(np.nansum(v)) for k, v in Y.items()}
        print(f"{base}: samples={len(X)} min={len(X) * 0.25 / 60:.1f} events={dict(kinds)} positives={pos}")


def cmd_train(a):
    per = build(a.dir)
    if not per:
        sys.exit("no SMRec sessions")
    model = {"features": FEATURES, "sessions": [b for b, *_ in per], "labels": {}}
    Xall = np.vstack([X for _, X, _, _ in per])
    mu, sd = Xall.mean(0), Xall.std(0)
    sd[sd < 1e-3] = 1.0   # constant feature: no scaling (keeps the UnrealScript side from dividing by ~0)
    model["mean"], model["scale"] = mu.round(4).tolist(), sd.round(4).tolist()
    for lab in LABELS:
        # time split per session: first 80 % train, last 20 % test (no leakage across the label window)
        tr, te = [], []
        for _, X, Y, _ in per:
            ok = ~np.isnan(Y[lab])
            Xs, ys = (X[ok] - mu) / sd, Y[lab][ok]
            c = int(len(ys) * 0.8)
            tr.append((Xs[:c], ys[:c])); te.append((Xs[c:], ys[c:]))
        Xtr, ytr = np.vstack([x for x, _ in tr]), np.concatenate([y for _, y in tr])
        Xte, yte = np.vstack([x for x, _ in te]), np.concatenate([y for _, y in te])
        info = {"n_train": len(ytr), "pos_train": int(ytr.sum()), "n_test": len(yte), "pos_test": int(yte.sum())}
        if ytr.sum() < 5 or ytr.sum() > len(ytr) - 5:
            info["status"] = "too few positives/negatives, not trained (needs real play logs)"
            model["labels"][lab] = info
            print(lab, info)
            continue
        w, b = fit(Xtr, ytr)
        p = 1 / (1 + np.exp(-(Xte @ w + b)))
        info.update(status="ok", auc_test=round(auc(yte, p), 3), base_rate=round(float(ytr.mean()), 3),
                    bias=round(float(b), 4), weights=dict(zip(FEATURES, w.round(4).tolist())))
        model["labels"][lab] = info
        top = sorted(info["weights"].items(), key=lambda kv: -abs(kv[1]))[:6]
        print(lab, {k: info[k] for k in ("n_train", "pos_train", "auc_test", "base_rate")}, "top:", top)
    Path(a.out).write_text(json.dumps(model, indent=1), encoding="utf-8")
    print("model ->", a.out)
    if a.ini:
        print("[SwatMinds.SwatMindsMutator]")
        for i, f in enumerate(FEATURES):
            print(f"PMFeat[{i}]=(Name={f},Mean={mu[i]:.4f},Scale={sd[i]:.4f})")
        for lab, info in model["labels"].items():
            if info.get("status") == "ok":
                print(f"; {lab} bias={info['bias']}")
                for i, f in enumerate(FEATURES):
                    print(f"PM_{lab}[{i}]={info['weights'][f]:.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("stats", "train"):
        sp = sub.add_parser(c)
        sp.add_argument("--dir", default=str(DEFAULT_DIR))
        if c == "train":
            sp.add_argument("--out", default=str(Path(__file__).with_name("smrec_model.json")))
            sp.add_argument("--ini", action="store_true")
    a = ap.parse_args()
    {"stats": cmd_stats, "train": cmd_train}[a.cmd](a)
