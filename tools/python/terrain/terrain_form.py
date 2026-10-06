"""Form a landscape from a sketch: uplift field -> stream power from a flat start (with PID
peak heights) -> strata, droplets, thermal -> fine detail -> pads -> masks and score.

    import terrain_form as tf_
    out = tf_.form(sketch, seed=1)                  # sketch: dict (terrain_sketch) or a .json path
    out["h"] metres; out["masks"]; out["score"]; plus everything terrain_erode.erode returns,
    out["uplift"], out["pads"] (bool: cells to keep fixed in later edits), out["formed"] (before detail)

Presets (sketch["preset"] or form(..., preset=)):
    hills    soft dendritic hills, grassy, soil everywhere (the TutA / Avalon case)
    alpine   Decima-style range: sharp arêtes, deep straight valleys, scree aprons, hard strata,
             snow on the tops; low diffusion so the valley network is fine, slope cap for arêtes
    canyon   MotorStorm-style desert: a flat floor with mesas and buttes whose hard caps keep
             their tables while the edges slump into cliffs and talus; terraced strata

k and diffusion: their ratio sets the valley spacing (k 1.0 carves a channel into every cell,
k 0.02 with diffusion 0.2 is a blob; 0.05 / 0.08 gives real hillslopes at 256 cells).
The stream-power stage is linear in (height, uplift) for n = 1, so it runs in normalised units
and the result is scaled to the sketch's `relief` (metres) afterwards; peak constraints are
enforced at the end by a smooth bump blend (the PID controller on the uplift is available,
pid=(Kp, Ki, Kd) in form_base, but off: with the slow dynamics of small k it oscillated).
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import terrain_flow as tflow      # noqa: E402
import terrain_erode as te        # noqa: E402
import terrain_noise as tn        # noqa: E402
import terrain_sketch as sk       # noqa: E402
import terrain_score as ts        # noqa: E402

PRESETS = {
    "hills": dict(
        k=0.05, diffusion=0.12, steps=400, cap_slope=None,
        hardness=dict(bands=3, hard_fraction=0.2, cap=False), hardness_scale=0.45,
        droplets=dict(count=40000), thermal=40, talus=(30.0, 55.0),
        terrace=None, detail=dict(kind="fft", beta=2.0, amp=0.002), relief=220.0),
    "alpine": dict(
        k=0.05, diffusion=0.08, steps=400, cap_slope=None,
        hardness=dict(bands=4, hard_fraction=0.3, cap=False), hardness_scale=0.45,
        droplets=dict(count=15000, deposit_speed=0.2, capacity=5.0), thermal=25, talus=(34.0, 72.0),
        terrace=None, detail=dict(kind="fft", beta=2.0, amp=0.003), relief=450.0),
    "canyon": dict(
        k=0.08, diffusion=0.03, steps=400, cap_slope=None,
        hardness=dict(bands=5, hard_fraction=0.55, cap=True), hardness_scale=1.0,
        droplets=dict(count=25000, deposit_speed=0.4), thermal=90, talus=(31.0, 80.0),
        terrace=dict(step=0.08, sharpness=0.7, strength=0.65), detail=dict(kind="fft", beta=2.2, amp=0.002), relief=320.0),
}


def _support(n, row, col, radius):
    rr, cc = np.mgrid[0:n, 0:n]
    d = np.hypot(rr - row, cc - col)
    return 1.0 - tn.smoothstep(d, radius * 0.4, radius)


def form_base(uplift, peaks, steps, k, diffusion, cap_slope=None, outlet=None, pid=None,
              chunk=10, relief_cells=None, seed=0, log=None):
    """Stream power from a nearly flat start under `uplift` (a little noise on the initial
    surface, or every channel runs along one of the eight grid directions). Returns h
    (normalised units), the unconstrained maximum M measured a third of the way through, and
    the final uplift (with the PID corrections). cap_slope is a tan in FINAL units
    (relief_cells = the sketch's relief in cells): it is converted once M is known."""
    n = uplift.shape[0]
    u = uplift.copy()
    umax = float(u.max())
    stage = {"M": None, "err": {}, "integ": {}, "supports": None}
    first = max(chunk, steps // 3)
    h0 = 0.02 * umax * np.abs(tn.fbm((n, n), freq=8.0, octaves=5, gain=0.6, seed=seed + 23)) * (u > 0)

    def hook(s, h, area):
        if s + 1 == first:
            stage["M"] = max(float(h.max()), 1e-9)
            # the support must beat the diffusion length or the bump smooths away as it builds
            stage["supports"] = [_support(n, p["row"], p["col"], max(p["radius"], 0.05 * n)) for p in peaks]
            stage["outside"] = np.ones((n, n), dtype=bool)
            for sup in stage["supports"]:
                stage["outside"] &= sup <= 0.0
            if log:
                log("unconstrained max after %d steps: %.3f (normalised)" % (first, stage["M"]))
            if cap_slope is not None and relief_cells:
                return {"cap_slope": cap_slope * stage["M"] / float(relief_cells)}
        if stage["M"] is None or not peaks or pid is None or (s + 1) % chunk != 0:
            return None
        Kp, Ki, Kd = pid
        du = np.zeros_like(u)
        # the field is still growing: targets follow the maximum of the UNCONSTRAINED ground
        # (outside every support, or peaks chase each other), a little above it for the summit
        top = max(float(h[stage["outside"]].max()), 1e-9) * 1.04
        for i, p in enumerate(peaks):
            target = p["height"] * top
            e = (target - float(h[p["row"], p["col"]])) / top
            integ = stage["integ"].get(i, 0.0) + e
            d = e - stage["err"].get(i, 0.0)
            stage["err"][i] = e; stage["integ"][i] = integ
            du += (Kp * e + Ki * integ + Kd * d) * umax * stage["supports"][i]
        np.clip(u + du, 0.0, 4.0 * umax, out=u)
        return u

    h, area = tflow.stream_power(h0, steps=steps, k=k, diffusion=diffusion, uplift=u,
                                 outlet=outlet, cap_slope=None, hook=hook, log=log)
    M = stage["M"] if stage["M"] is not None else max(float(h.max()), 1e-9)
    return h, M, u


def form(sketch, preset=None, seed=0, size=None, steps=None, log=print, detail=True):
    if isinstance(sketch, str):
        sketch = sk.load(sketch)
    sketch = dict(sketch)
    if size:
        sketch["size"] = int(size)
    name = preset or sketch.get("preset", "hills")
    P = dict(PRESETS[name])
    P.update(sketch.get("params", {}))
    if steps:
        P["steps"] = int(steps)
    n = int(sketch.get("size", 256))
    mpc = float(sketch.get("metres_per_cell", 10.24))
    relief_m = float(sketch.get("relief", P["relief"]))
    t0 = time.time()
    r = sk.rasterise(sketch, seed=seed)
    if log:
        log("sketch: %dx%d, %.1f m/cell, preset %s, relief %.0f m, %d peaks, %d pads" % (n, n, mpc, name, relief_m, len(r["peaks"]), len(r["pads"])))
    # 1. form (normalised units)
    kmap = P["k"] * (1.0 - r["resist"]) if r["resist"].any() else P["k"]
    hn, M, u_final = form_base(r["uplift"], r["peaks"], P["steps"], kmap, P["diffusion"], cap_slope=P["cap_slope"],
                               outlet=r["outlet"], relief_cells=relief_m / mpc, seed=seed, log=log)
    # cell units. With peaks: each peak lands exactly at height x relief (a smooth bump blend on
    # top of the PID's rough work) and the unconstrained ground scales to just under the
    # summit; without peaks the highest point is the relief.
    relief_c = relief_m / mpc
    if r["peaks"]:
        outside = np.ones((n, n), dtype=bool)
        sups = []
        for p in r["peaks"]:
            sup = _support(n, p["row"], p["col"], max(p["radius"], 0.05 * n))
            sups.append(sup); outside &= sup <= 0.0
        hmax_design = max(p["height"] for p in r["peaks"])
        hc = hn * (0.96 * hmax_design * relief_c / max(float(hn[outside].max()), 1e-9))
        for p, sup in zip(r["peaks"], sups):
            delta = p["height"] * relief_c - float(hc[p["row"], p["col"]])
            hc = hc + delta * sup
            if log:
                log("peak (%d,%d): %.0f m, blended by %+.0f m" % (p["row"], p["col"], p["height"] * relief_m, delta * mpc))
    else:
        hc = hn * (relief_c / max(float(hn.max()), 1e-9))
    formed = hc.copy()
    if not detail:
        return {"h": (hc * mpc).astype(np.float32), "formed": (formed * mpc).astype(np.float32), "uplift": r["uplift"], "pads": np.zeros((n, n), bool)}
    # 2. strata (canyon): shelves before the slumping turns them into cliff and talus
    if P.get("terrace"):
        T = P["terrace"]
        hc = tn.terrace(hc, step=T["step"] * relief_m / mpc, sharpness=T["sharpness"], strength=T["strength"])
    hard = te.banded_hardness(hc, seed=seed, **P["hardness"]) * P["hardness_scale"]
    # 3. gullies and slumping (the existing stages, in cell units)
    dk = dict(seed=seed, hardness=hard, log=log); dk.update(P["droplets"])
    dk["count"] = int(dk["count"] * (n * n) / (128 * 128) * 0.5)
    hc, deposit, wear, visits = te.droplets(hc, **dk)
    hc, debris = te.thermal(hc, iterations=P["thermal"], hardness=hard, talus=P["talus"], log=log)
    # 4. fine detail at the natural spectrum, kept off the wet floors
    D = P.get("detail")
    if D and D.get("amp", 0) > 0:
        if D["kind"] == "fft":
            nz = tn.fft_noise((n, n), beta=D.get("beta", 2.0), seed=seed + 5)
        else:
            nz = tn.fbm((n, n), freq=12.0, octaves=5, gain=0.7, seed=seed + 5, kind=D["kind"])
        filled = tflow.fill_depressions(hc, outlet=r["outlet"])
        recv, _ = tflow.d8_receivers(filled)
        flow = tflow.drainage_area(recv).reshape(n, n)
        wet = tn.smoothstep(np.log1p(flow) / max(np.log1p(flow).max(), 1e-9), 0.55, 0.8)
        steep = tn.smoothstep(np.degrees(np.arctan(te.slope_tan(hc))), 12.0, 30.0)
        hc = hc + D["amp"] * (relief_m / mpc) * nz * (1.0 - wet) * (0.25 + 0.75 * steep)
        # no new pits from the noise (real pits deeper than a cell may stay)
        filled = tflow.fill_depressions(hc, outlet=r["outlet"])
        hc = np.where(filled - hc < 1.0, filled, hc)
    # 5. pads: flat, with a smooth halo
    hc, pads = sk.flatten_pads(hc, r["pads"], outlet=r["outlet"])
    # final state for the masks
    filled = tflow.fill_depressions(hc, outlet=r["outlet"])
    recv, _ = tflow.d8_receivers(filled)
    flow = tflow.drainage_area(recv).reshape(n, n)
    out = {
        "h": (hc * mpc).astype(np.float32), "formed": (formed * mpc).astype(np.float32),
        "flow": flow.astype(np.float32), "visits": visits.astype(np.float32),
        "deposit": (deposit * mpc).astype(np.float32), "wear": (wear * mpc).astype(np.float32),
        "debris": (debris * mpc).astype(np.float32), "slope": te.slope_tan(hc).astype(np.float32),
        "hardness": hard.astype(np.float32), "uplift": r["uplift"].astype(np.float32),
        "uplift_final": u_final.astype(np.float32), "pads": pads, "outlet": r["outlet"],
        "metres_per_cell": mpc, "preset": name,
    }
    masks = te.layer_masks(out, water_level=sketch.get("water_level"))
    # the designed rivers stay wet whatever the flow threshold says
    if np.isfinite(r["valley_d"]).any():
        lf = np.log1p(flow); lf = lf / max(lf.max(), 1e-9)
        near = sk.soft_band(r["valley_d"], 0.03 * n, inner=0.3)
        masks["wet"] = np.maximum(masks["wet"], near * tn.smoothstep(lf, 0.4, 0.6))
    deg = np.degrees(np.arctan(out["slope"]))
    if name != "alpine":
        masks["snow"] = np.zeros_like(masks["snow"])
    if name in ("hills", "alpine"):
        lo, hi = (26, 36) if name == "alpine" else (22, 32)
        meadow = (1 - tn.smoothstep(deg, lo, hi)) * (1 - masks["snow"]) * (1 - masks["rock"]) * (1 - masks["wet"])
        masks["grass"] = np.maximum(masks["grass"], meadow)
    if name == "canyon":
        masks["sand"] = np.maximum(masks.get("sand", 0), (1 - tn.smoothstep(np.degrees(np.arctan(out["slope"])), 4, 9)) * (1 - masks["wet"]) * (1 - tn.smoothstep((hc - hc.min()) / max(np.ptp(hc), 1e-9), 0.3, 0.5)))
        masks["grass"] = masks["grass"] * 0.25
    out["masks"] = masks
    out["score"] = ts.score(out["h"].astype(np.float64), mpc)
    if log:
        log("formed in %.1f s" % (time.time() - t0))
        ts.report(out["score"], log)
    return out
