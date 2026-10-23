"""Shaped score-term check (10-23, gym enhancement 6): does adding a term to cand_score make the search's ranking predict
clears better? A term is only worth adding if it does, on stored games, so this decides from data, not taste.

Per map, candidates with >= 6 games (data.jsonl rows grouped by knobs) are split in two halves of their games: the
mean shaped score on even-numbered games ranks the candidates, the clear share on odd-numbered games is the outcome
(held out, so the clear bonus inside the score cannot just copy it). Metric = Spearman rho between the two, mean of
both split directions. Prints rho for the current score v2 and for v2 + w * term over a few weights.

Run:  py -3.13 -I tools/swat4_scoreterms.py [--out C:/Users/john/Documents/SwatMindsGym/autogym]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from swat4_gymrun import cand_score  # noqa: E402


def cmd_share(r, k):
    c = r.get("cmds") or {}
    n = sum(c.values())
    return c.get(k, 0) / n if n else 0.0


TERMS = {  # name: f(row) -> float; per-game features already stored in data.jsonl
    "endT_fast": lambda r: (1 - r["last"]["endT"] / r.get("secs", 600)) if r["last"].get("end") == "clear" else 0.0,  # early-exit games only
    "bang_share": lambda r: cmd_share(r, "BangAndClear") + cmd_share(r, "BreachBangAndClear"),
    "move_share": lambda r: cmd_share(r, "MoveAndClear"),
    "timeouts": lambda r: (r.get("cmds") or {}).get("timeout", 0),
    "comply": lambda r: r["last"].get("cwComply", 0),
    "tap": lambda r: r["last"].get("tap", 0),
    "dirFace": lambda r: r["last"].get("dirFace", 0),
    "hostSecured": lambda r: r["last"].get("hostSecured", 0),
}
WEIGHTS = [-1.0, -0.5, 0.5, 1.0, 2.0]


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for t in range(i, j + 1):
            r[o[t]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5; vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def clear(r):
    return r["last"]["offDown"] == 0 and r["last"]["susFree"] == 0


def rho(groups, f):
    out = []
    for a, b in ((0, 1), (1, 0)):
        x = [sum(f(r) for r in g[a::2]) / len(g[a::2]) for g in groups]
        y = [sum(clear(r) for r in g[b::2]) / len(g[b::2]) for g in groups]
        out.append(spearman(x, y))
    return sum(out) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="C:/Users/john/Documents/SwatMindsGym/autogym")
    a = ap.parse_args()
    for f in sorted(Path(a.out, "engine").glob("*/data.jsonl")):
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        by = {}
        for r in rows:
            if r.get("last"):
                by.setdefault(json.dumps(r["knobs"], sort_keys=True), []).append(r)
        groups = [g for g in by.values() if len(g) >= 6]
        if len(groups) < 5:
            print(f"{f.parent.name}: only {len(groups)} candidates with >= 6 games, skipped")
            continue
        base = rho(groups, lambda r: cand_score(r["last"]))
        print(f"{f.parent.name}: {len(groups)} candidates, {sum(map(len, groups))} games; score v2 rho {base:+.3f}")
        for name, t in TERMS.items():
            try:
                best = max(((rho(groups, lambda r, w=w: cand_score(r["last"]) + w * t(r)), w) for w in WEIGHTS))
            except (KeyError, ZeroDivisionError):
                continue
            mark = "  <- better" if best[0] > base + 0.02 else ""
            print(f"  + {best[1]:+.1f} * {name:12s} rho {best[0]:+.3f}{mark}")


if __name__ == "__main__":
    main()
