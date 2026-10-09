"""Fit the jiggle bones to the soft-body reference (JIGGLE.md, phase A.4).

    py -I tools/jiggle_fit.py <jiggle dir> [clip ...]

For every clip (sim_<clip>.npz from tools/jiggle_sim.py, anim_<clip>.npz from jiggle_rig.py skin)
and every jiggle bone (regions.json): per frame, the rotation of the bone about its pivot (the
parent's joint) that best moves the region's vertices from where the clip puts them to where the
soft body put them (weighted least squares on omega x r, small angles), giving a rotation-vector
curve theta(t) in the parent's frame. Then one damped spring per bone, driven by the inertial
force on the region's centre (the pendulum: theta'' = gain * (c x -a) / |c|^2 - k theta - d theta'),
fitted over all clips at once (Nelder-Mead on k, d, gain); the static sag (the mean of theta over
the idle clip) is taken out first, since the mesh is modelled sagged already.
Writes <clip>_jiggle.psa (the clip's 78 tracks plus the 10 fitted jiggle tracks, on the re-rigged
skeleton), jiggle_fit.json (per bone: k, d, gain, max amplitude, lever, parent; per clip errors)
and fit_report.md.
"""
import json
import math
import os
import struct
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jiggle_rig import read_psk  # noqa: E402


def skew(r):
    return np.array([[0, -r[2], r[1]], [r[2], 0, -r[0]], [-r[1], r[0], 0]])


MAX_ANGLE = math.radians(35)
REG = 0.5          # Tikhonov weight on omega (units^2 per rad^2): a small turn is preferred to a wild one


def fit_frame(RP, OP, goal, sim, verts, lever):
    """omega (rad, clamped) and the residuals: before, after the turn, after a turn plus a move
    (the diagnostic: what a bone that could also translate would explain); RMS units over the
    region's points. The turn is the robust one: the region's weighted centroid lags the clip by
    Delta (in the parent's frame); the bone turns so that the lever's tip moves by Delta's part
    across the lever: omega = c x Delta / |c|^2 (a weighted least-squares fit on every vertex
    went wild on the few loose vertices of a violent clip; the centroid is the mass that jiggles)."""
    idx = np.array([i for i, _ in verts])
    w = np.array([wt for _, wt in verts])
    r = (goal[idx] - OP) @ RP          # parent-local positions (rows: v R = R^T v)
    d = (sim[idx] - goal[idx]) @ RP
    A = np.concatenate([-w[k] * skew(r[k]) for k in range(len(idx))])
    b = d.ravel()
    n = len(idx)
    c = np.array(lever)
    delta = (d * w[:, None]).sum(0) / w.sum()
    omega = np.cross(c, delta) / float(c @ c)
    a = np.linalg.norm(omega)
    if a > MAX_ANGLE:
        omega *= MAX_ANGLE / a
    before = math.sqrt(np.mean(np.sum(d * d, axis=1)))
    res = (A @ omega - b).reshape(-1, 3)
    after = math.sqrt(np.mean(np.sum(res * res, axis=1)))
    # rotation + translation, unregularised
    At = np.concatenate([np.concatenate([-w[k] * skew(r[k]), w[k] * np.eye(3)], axis=1) for k in range(n)])
    x6, *_ = np.linalg.lstsq(At, b, rcond=None)
    res6 = (At @ x6 - b).reshape(-1, 3)
    after6 = math.sqrt(np.mean(np.sum(res6 * res6, axis=1)))
    return omega, before, after, after6


def exp_quat(theta):
    a = np.linalg.norm(theta)
    if a < 1e-9:
        return (0.0, 0.0, 0.0, 1.0)
    s = math.sin(a / 2) / a
    return (theta[0] * s, theta[1] * s, theta[2] * s, math.cos(a / 2))


def spring_run(drive, rate, k, d, gain, x0, v0=None):
    """theta'' = gain*drive - k theta - d theta', semi-implicit Euler, 4 substeps per frame"""
    n = len(drive)
    x = np.array(x0, dtype=np.float64)
    v = np.zeros(3) if v0 is None else np.array(v0)
    out = np.zeros((n, 3))
    h = 1.0 / rate / 4
    for f in range(n):
        for _ in range(4):
            v += (gain * drive[f] - k * x - d * v) * h
            x += v * h
        out[f] = x
    return out


def main():
    jdir = sys.argv[1]
    reg = json.load(open(os.path.join(jdir, "regions.json")))
    m = read_psk(reg["psk"])
    bones = m["bones"]
    clips = sys.argv[2:] or [f[4:-4] for f in sorted(os.listdir(jdir)) if f.startswith("sim_") and f.endswith(".npz")]
    thetas = {}      # (clip, bone) -> (frames x 3)
    drives = {}
    errs = {}
    rates = {}
    for clip in clips:
        s = np.load(os.path.join(jdir, "sim_%s.npz" % clip))
        a = np.load(os.path.join(jdir, "anim_%s.npz" % clip))
        sim, goal, rate = s["sim"].astype(np.float64), s["goal"].astype(np.float64), float(s["rate"])
        bR, bO = a["bone_R"].astype(np.float64), a["bone_O"].astype(np.float64)
        rates[clip] = rate
        nf = len(sim)
        for r in reg["regions"]:
            pb = r["parent_index"]
            c = np.array(r["lever"])
            th = np.zeros((nf, 3))
            bef, aft, aft6 = [], [], []
            centre = np.zeros((nf, 3))
            for f in range(nf):
                om, b0, a0, a6 = fit_frame(bR[f][pb], bO[f][pb], goal[f], sim[f], r["verts"], c)
                th[f] = om
                bef.append(b0)
                aft.append(a0)
                aft6.append(a6)
                centre[f] = bO[f][pb] + bR[f][pb] @ c
            # the drive: the region centre's acceleration (mesh space, units/s^2), in the parent's
            # frame, as the inertial force on a pendulum of lever c
            acc = np.zeros((nf, 3))
            if nf >= 3:
                acc[1:-1] = (centre[2:] - 2 * centre[1:-1] + centre[:-2]) * rate * rate
                acc[0], acc[-1] = acc[1], acc[-2]
            drv = np.zeros((nf, 3))
            for f in range(nf):
                a_local = bR[f][pb].T @ acc[f]
                drv[f] = np.cross(c, -a_local) / float(c @ c)
            thetas[(clip, r["name"])] = th
            drives[(clip, r["name"])] = drv
            errs[(clip, r["name"])] = (float(np.mean(bef)), float(np.mean(aft)), float(np.degrees(np.max(np.linalg.norm(th, axis=1)))), float(np.mean(aft6)))
    # the static sag per bone: the idle clip's mean, else the mean over everything
    static = {}
    for r in reg["regions"]:
        idle = [c for c in clips if "idle" in c.lower()]
        src = idle if idle else clips
        static[r["name"]] = np.mean(np.concatenate([thetas[(c, r["name"])] for c in src]), axis=0)
    # the spring per bone
    fits = {}
    report = ["# Jiggle fit report", "",
              "Per frame: the rotation of each jiggle bone (about its parent's joint) that best explains the soft body's",
              "displacement of its region (least squares). RMS = root mean square displacement of the region's points,",
              "units; 'before' = soft body vs clip, 'after' = what the fitted bone leaves unexplained.", "",
              "'turn + move' = what a bone that could also translate would leave (a diagnostic: the live route only turns).", "",
              "| clip | bone | frames | RMS before | RMS after (turn) | explained | after (turn + move) | max angle |", "|---|---|---|---|---|---|---|---|"]
    for clip in clips:
        for r in reg["regions"]:
            b0, a0, mx, a6 = errs[(clip, r["name"])]
            report.append("| %s | %s | %d | %.2f | %.2f | %.0f%% | %.2f | %.1f deg |" % (clip, r["name"], len(thetas[(clip, r["name"])]), b0, a0, 100 * (1 - a0 / max(b0, 1e-6)), a6, mx))
    report += ["", "## Springs (one per bone, fitted over every clip at once)", "",
               "theta'' = gain * (c x -a)/|c|^2 - k theta - d theta', theta in the parent's frame (rad), a = the region centre's acceleration (units/s^2).", "",
               "| bone | parent | k | d | gain | f0 (Hz) | damping ratio | max amp (deg, 95th pct) | fit RMS / signal RMS per clip (deg, and units at the lever's tip) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in reg["regions"]:
        name = r["name"]
        series = [(clip, thetas[(clip, name)] - static[name], drives[(clip, name)], rates[clip]) for clip in clips]

        def cost(p):
            k, d, g = p
            if k <= 0 or d <= 0 or g < 0:
                return 1e9
            e = 0.0
            for clip, x, drv, rate in series:
                xm = spring_run(drv, rate, k, d, g, x[0])
                e += float(np.sum((xm - x) ** 2))
            return e
        best = None
        for k0 in (50.0, 200.0, 800.0):
            for d0 in (3.0, 15.0):
                for g0 in (0.3, 1.0):
                    res = minimize(cost, [k0, d0, g0], method="Nelder-Mead", options=dict(maxiter=400, xatol=1e-3, fatol=1e-6))
                    if best is None or res.fun < best.fun:
                        best = res
        k, d, g = best.x
        per_clip = []
        errjson = {}
        for clip, x, drv, rate in series:
            xm = spring_run(drv, rate, k, d, g, x[0])
            fit_rms = math.degrees(math.sqrt(np.mean(np.sum((xm - x) ** 2, axis=1))))
            sig_rms = math.degrees(math.sqrt(np.mean(np.sum(x * x, axis=1))))
            lev = np.linalg.norm(r["lever"])
            per_clip.append("%s %.1f/%.1f (%.1f/%.1f u)" % (clip, fit_rms, sig_rms, math.radians(fit_rms) * lev, math.radians(sig_rms) * lev))
            errjson[clip] = dict(fit_rms_deg=fit_rms, signal_rms_deg=sig_rms, region_rms_before=errs[(clip, name)][0], region_rms_after=errs[(clip, name)][1], region_rms_after_turn_move=errs[(clip, name)][3])
        amps = np.concatenate([np.linalg.norm(x, axis=1) for _, x, _, _ in series])
        maxamp = float(np.degrees(np.percentile(amps, 95)))
        f0 = math.sqrt(k) / (2 * math.pi)
        zeta = d / (2 * math.sqrt(k))
        fits[name] = dict(parent=r["parent"], k=float(k), d=float(d), gain=float(g), f0_hz=f0, damping_ratio=zeta, max_deg=maxamp, lever=r["lever"], static_deg=np.degrees(static[name]).tolist(), clips=errjson)
        report.append("| %s | %s | %.0f | %.1f | %.2f | %.1f | %.2f | %.1f | %s |" % (name, r["parent"], k, d, g, f0, zeta, maxamp, "; ".join(per_clip)))
    json.dump(dict(mesh=reg["mesh"], bones=fits, note="theta'' = gain*(c x -a)/|c|^2 - k*theta - d*theta', rad, parent frame; a = acceleration of the region centre (pivot + R_parent * lever), units/s^2"),
              open(os.path.join(jdir, "jiggle_fit.json"), "w"), indent=1)
    # the psa per clip: the clip's own tracks plus the jiggle bones' fitted rotations
    names = [b["name"].lower() for b in bones]
    for clip in clips:
        c = json.load(open(os.path.join(jdir, "clips", clip + ".json")))
        nf = len(c["frames"])
        keys = []
        for f in range(nf):
            row = c["frames"][f]
            for i, b in enumerate(bones):
                if i < len(row):
                    q, pos = row[i][0:4], row[i][4:7]
                else:
                    r = next(rr for rr in reg["regions"] if rr["index"] == i)
                    q = exp_quat(thetas[(clip, r["name"])][f])
                    q = (-q[0], -q[1], -q[2], q[3])      # ActorX: children conjugated
                    pos = (0.0, 0.0, 0.0)
                keys.append(struct.pack("<3f4ff", *pos, *q, 1.0))
        recs = [struct.pack("<64sIii4f3ff3f", b["name"].encode(), 0, b["children"], max(b["parent"], 0), 0, 0, 0, 1, *b["pos"], 0, 0, 0, 0) for b in bones]
        info = struct.pack("<64s64siiiifffiii", (clip + "_J").encode(), b"None", len(bones), 0, 0, len(keys), 0.0, float(nf), float(rates[clip]), 0, 0, nf)
        with open(os.path.join(jdir, clip + "_jiggle.psa"), "wb") as fh:
            for cid, size, items in (("ANIMHEAD", 0, []), ("BONENAMES", 120, recs), ("ANIMINFO", 168, [info]), ("ANIMKEYS", 32, keys)):
                fh.write(struct.pack("<20sIii", cid.encode(), 1999801, size, len(items)) + b"".join(items))
    report += ["", "Written: jiggle_fit.json, <clip>_jiggle.psa (%d bones) for %s" % (len(bones), ", ".join(clips))]
    open(os.path.join(jdir, "fit_report.md"), "w").write("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
