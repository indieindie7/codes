"""score_irl.py: score the solver's shipped defaults against measured references (tests/irl_refs.json).

Contract (autorun "postcheck" step, ops ideas.py): the LAST line printed is
    VERDICT {"gain": <score_now - score_baseline>, "rows": <measurements>, "score": <0..1>}
Baseline = tests/irl_baseline.json (rewritten only with --write-baseline, by an approved round).
Score per row = clip(1 - |x - mean| / half_band, 0, 1); score = mean over rows. gain > 0 = closer to the lab.
Rows: one per (reference, column height, wet threshold); ideas.py needs >= 20 rows to approve.
Only the solver (src/hydrowater.c, .h, bin/hydrowater.dll) is under test; this file, irl_refs.json and
irl_baseline.json are the target and are protected (never patched by a proposal).
Run: "C:/Users/john/Documents/Tools/kimodo/venv/Scripts/python.exe" tests/score_irl.py [--write-baseline] [--json]
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import tune as T
import harness as H

DEFAULTS = {"alpha": 1.0, "c_adapt": 0.2, "edge_damp": 0.7, "cfl": 0.5, "recon": 1}   # hydrowater.c defaults
REFS = os.path.join(HERE, "irl_refs.json")
BASE = os.path.join(HERE, "irl_baseline.json")


def front_speed(col, thr, t_window, p=DEFAULTS):
    """Dry-bed dam break, column height col (units), 20 cells long: least-squares front speed in sqrt(gH)."""
    w, h, L = 160, 8, 20
    s = T.Sheet(w, h, cfl=p["cfl"], alpha=p["alpha"], c_adapt=p["c_adapt"], edge_damp=p["edge_damp"], recon=int(p["recon"]))
    s.bed[:] = 0.0
    d = np.zeros((h, w)); d[:, :L] = col; s.depth[:] = d
    tscale = np.sqrt(col / H.G)
    ts, xs, t = [], [], 0.0
    while t < t_window[1] * tscale - 1e-6:
        s.step(T.DT); t += T.DT
        wet = np.where(s.depth.mean(axis=0) > thr * col)[0]
        ts.append(t / tscale)
        xs.append(((wet.max() + 1) - L) * H.DX / col if len(wet) else 0.0)
    s.close()
    ts, xs = np.array(ts), np.array(xs)
    m = (ts >= t_window[0]) & (ts <= t_window[1])
    return float(np.polyfit(ts[m], xs[m], 1)[0]) if m.sum() >= 3 else 0.0


def score_all(refs):
    rows = []
    for r in refs:
        half = (r["band_hi"] - r["band_lo"]) / 2
        if r["metric"] == "front_speed":
            for col in r["columns"]:
                for thr in r["wet_thresholds"]:
                    x = front_speed(col, thr, r["t_window"])
                    rows.append({"ref": r["name"], "col": col, "thr": thr, "x": round(x, 4),
                                 "score": round(float(np.clip(1 - abs(x - r["mean"]) / half, 0, 1)), 4)})
        else:
            print(f"unknown metric {r['metric']} in {r['name']}, skipped")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-baseline", action="store_true", help="store the current score as the baseline (approved rounds only)")
    ap.add_argument("--json", action="store_true", help="print every row")
    a = ap.parse_args()
    refs = json.load(open(REFS, encoding="utf-8"))
    rows = score_all(refs)
    score = float(np.mean([r["score"] for r in rows])) if rows else 0.0
    base = json.load(open(BASE, encoding="utf-8"))["score"] if os.path.exists(BASE) else None
    for r in rows:
        if a.json: print(json.dumps(r))
    print(f"refs {len(refs)} rows {len(rows)} score {score:.4f} baseline {base}")
    if a.write_baseline or base is None:
        json.dump({"score": round(score, 4), "rows": len(rows), "refs": [r["name"] for r in refs]}, open(BASE, "w", encoding="utf-8"), indent=1)
        print(f"baseline written to {BASE}")
        if base is None: base = score
    gain = round(score - base, 4)
    print("VERDICT " + json.dumps({"gain": gain, "rows": len(rows), "score": round(score, 4)}))


if __name__ == "__main__":
    main()
