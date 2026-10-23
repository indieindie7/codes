"""tune.py: regressive tuner for the coarse lattice solver.

A fine run of our own solver (dx/4, 4x cells) is the reference. The coarse
sheet (the one the game runs, dx 20) is scored against it on a few scenes at a
few times: RMSE of the surface eta, plus volume drift and a small cost for
sub-steps. A fuzzy (1+lambda) evolution strategy perturbs the continuous
knobs (alpha, c_adapt, edge_damp, cfl) and flips recon, keeps the best and
narrows its steps when a generation brings nothing.

    python tests/tune.py [--gens 12] [--pop 12] [--seed 1] [--quick]

Writes tests/tune/log.jsonl (every eval) and tests/tune/best.json. Any later
agent (local LLM via autorun, or a chat) reads best.json and the log, never the
pngs. Nothing here touches the game.
"""
import argparse
import ctypes
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import harness as H

OUT = os.path.join(os.path.dirname(__file__), "tune")
FINE = 4                      # reference refinement
TIMES = (0.5, 1.0, 2.0, 3.0)  # seconds at which eta is compared
DT = 1 / 30

# knob: (lo, hi, initial sigma)
KNOBS = {
    "alpha":     (0.5, 1.0, 0.15),
    "c_adapt":   (0.02, 0.6, 0.12),
    "edge_damp": (0.3, 1.0, 0.15),
    "cfl":       (0.2, 0.5, 0.08),
}


class Sheet(H.Sheet):
    """harness Sheet with cfl and refinement."""
    def __init__(self, w, h, cfl=0.5, **opts):
        self.s = H.lib.hw_create(w, h, H.DX * opts.pop("dx_scale", 1.0), H.G, cfl)
        self.w, self.h = w, h
        self.stride = H.lib.hw_stride(self.s)
        o = H.Opts()
        o.displacement = o.capped_stamp = o.face_walls = o.clamps = o.recon = 1
        for k, v in opts.items():
            setattr(o, k, v)
        H.lib.hw_set_opts(self.s, ctypes.byref(o))
        self.steps = 0


def scene_dam(w, h, f):
    """Dam break onto stairs (same as harness test_dam, scaled by f)."""
    j, i = np.mgrid[0:h * f, 0:w * f]
    bed = np.where(i >= 40 * f, ((i - 40 * f) // (5 * f)) * 4.0, 0.0)
    depth = np.where(i < 30 * f, 40.0, 0.0)
    return bed, depth


def scene_drop(w, h, f):
    """A round mound of water collapsing into a shallow pool."""
    j, i = np.mgrid[0:h * f, 0:w * f]
    cx, cz, r = w * f / 2, h * f / 2, 8 * f
    mound = np.clip(1 - ((i - cx) ** 2 + (j - cz) ** 2) / r ** 2, 0, 1)
    return np.zeros((h * f, w * f)), 10.0 + 30.0 * mound


def scene_bump(w, h, f):
    """Flow over a submerged ridge: tests reconstruction and wet/dry damping."""
    j, i = np.mgrid[0:h * f, 0:w * f]
    bed = 12.0 * np.exp(-((i - w * f * 0.55) / (6.0 * f)) ** 2)
    depth = np.where(i < 25 * f, 30.0, 8.0) - bed
    return bed, np.maximum(depth, 0)


def scene_wade(w, h, f):
    """Still pool 25 deep; a disc body (r 15) wades through at 120 u/s (harness test_wading)."""
    return np.zeros((h * f, w * f)), np.full((h * f, w * f), 25.0)


def motion_wade(s, t, dt):
    r, speed, z = 15.0, 120.0, 15 * H.DX
    x = 10 * H.DX + speed * t
    s.bodies_begin()
    s.body_disc(x, z, r, 0.0, 75.0)
    s.stamp(x - speed * dt, z, x, z, r, 0.0, speed, 0.0, dt)


def scene_ritter(w, h, f):
    """Dam break on a flat dry bed: exact Ritter (1892) solution is the reference."""
    j, i = np.mgrid[0:h * f, 0:w * f]
    return np.zeros((h * f, w * f)), np.where(i < 40 * f, 40.0, 0.0)


def ritter_ref(w, h):
    x = (np.arange(w) + 0.5) * H.DX - 40 * H.DX
    h0, c0 = 40.0, np.sqrt(H.G * 40.0)
    out = []
    for t in TIMES:
        eta = np.where(x < -c0 * t, h0, np.where(x < 2 * c0 * t, (2 * c0 - x / t) ** 2 / (9 * H.G), 0.0))
        out.append(np.tile(eta, (h, 1)))
    return out


# name: (w, h, scene, per-step motion or None). c_adapt only acts on stamped bodies (wade).
SCENES = {"dam": (80, 16, scene_dam, None), "drop": (48, 48, scene_drop, None),
          "bump": (80, 16, scene_bump, None), "wade": (60, 30, scene_wade, motion_wade),
          "ritter": (160, 8, scene_ritter, None)}


def run(w, h, f, scene, cfl, motion=None, **opts):
    """Run one sheet, return eta snapshots (coarse-sampled) and volume drift."""
    s = Sheet(w * f, h * f, cfl=cfl, dx_scale=1.0 / f, **opts)
    bed, depth = scene(w, h, f)
    s.bed[:] = bed
    s.depth[:] = depth
    v0 = s.volume()
    snaps, t, k = [], 0.0, 0
    while k < len(TIMES):
        if motion:
            motion(s, t, DT)
        s.step(DT)
        t += DT
        if t + 1e-6 >= TIMES[k]:
            eta = s.eta.copy()
            if f > 1:
                eta = eta.reshape(h, f, w, f).mean(axis=(1, 3))
            snaps.append(eta)
            k += 1
    drift = abs(s.volume() - v0) / max(v0, 1e-9)
    steps = s.steps
    s.close()
    return snaps, drift, steps


_ref = {}
REF_OPTS = {}   # --ref min: fine run with least damping (c_adapt 0.02, edge_damp 1)


def reference(name):
    if name not in _ref:
        w, h, fn, mo = SCENES[name]
        _ref[name] = ritter_ref(w, h) if name == "ritter" else run(w, h, FINE, fn, 0.5, motion=mo, **REF_OPTS)[0]
    return _ref[name]


def score(p, scenes):
    """Lower is better. rmse in height units, drift and sub-step cost added."""
    total, parts = 0.0, {}
    for name in scenes:
        w, h, fn, mo = SCENES[name]
        ref = reference(name)
        snaps, drift, steps = run(w, h, 1, fn, p["cfl"], motion=mo, alpha=p["alpha"], c_adapt=p["c_adapt"],
                                  edge_damp=p["edge_damp"], recon=int(p["recon"]))
        rmse = float(np.mean([np.sqrt(np.mean((a - b) ** 2)) for a, b in zip(snaps, ref)]))
        cost = rmse + 50.0 * drift + 0.002 * steps
        parts[name] = {"rmse": round(rmse, 4), "drift": drift, "steps": steps}
        total += cost
    return total / len(scenes), parts


def clamp(p):
    for k, (lo, hi, _) in KNOBS.items():
        p[k] = float(min(hi, max(lo, p[k])))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=12)
    ap.add_argument("--pop", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--quick", action="store_true", help="dam scene only")
    ap.add_argument("--scenes", default="dam,drop,bump,wade")
    ap.add_argument("--ref", default="same", help="same: fine run with default knobs; min: least damping")
    ap.add_argument("--out", default="tune")
    a = ap.parse_args()
    global OUT
    OUT = os.path.join(os.path.dirname(__file__), a.out)
    if a.ref == "min":
        REF_OPTS.update(c_adapt=0.02, edge_damp=1.0)
    scenes = ["dam"] if a.quick else a.scenes.split(",")
    rng = np.random.default_rng(a.seed)
    os.makedirs(OUT, exist_ok=True)
    log = open(os.path.join(OUT, "log.jsonl"), "a", encoding="utf-8")

    def evaluate(p, gen, tag):
        t0 = time.time()
        total, parts = score(p, scenes)
        rec = {"gen": gen, "tag": tag, "params": p, "score": round(total, 5), "parts": parts,
               "secs": round(time.time() - t0, 2)}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        return total, rec

    best = {"alpha": 1.0, "c_adapt": 0.2, "edge_damp": 0.7, "cfl": 0.5, "recon": 1}
    best_s, best_rec = evaluate(best, 0, "default")
    base_s, _ = evaluate({"alpha": 1.0, "c_adapt": 0.2, "edge_damp": 0.7, "cfl": 0.5, "recon": 0}, 0, "no_recon")
    print("default %.4f  no_recon %.4f" % (best_s, base_s))
    sigma = {k: v[2] for k, v in KNOBS.items()}
    for gen in range(1, a.gens + 1):
        improved = False
        for n in range(a.pop):
            # fuzzy step: each knob moves by a normal sample scaled by its sigma,
            # with a 10 % chance per knob of a wide jump across the whole range
            cand = dict(best)
            for k, (lo, hi, _) in KNOBS.items():
                if rng.random() < 0.1:
                    cand[k] = rng.uniform(lo, hi)
                else:
                    cand[k] = best[k] + rng.normal(0, sigma[k])
            if rng.random() < 0.15:
                cand["recon"] = 1 - cand["recon"]
            clamp(cand)
            s, rec = evaluate(cand, gen, "cand")
            if s < best_s:
                best, best_s, best_rec, improved = cand, s, rec, True
        if improved:
            sigma = {k: min(KNOBS[k][2], v * 1.3) for k, v in sigma.items()}
        else:
            sigma = {k: v * 0.6 for k, v in sigma.items()}
        print("gen %d best %.4f %s" % (gen, best_s, json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in best.items()})))
        with open(os.path.join(OUT, "best.json"), "w", encoding="utf-8") as fh:
            json.dump({"best": best_rec, "default_score": best_rec["score"] if best_rec["tag"] == "default" else None,
                       "gens": gen, "scenes": scenes, "sigma": sigma}, fh, indent=1)
    log.close()


if __name__ == "__main__":
    main()
