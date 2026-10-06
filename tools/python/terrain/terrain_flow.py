"""Flow routing and the stream-power solver, vectorised (NumPy only, no per-cell Python loops).

    import terrain_flow as tf
    filled = tf.fill_depressions(h)                 # Planchon-Darboux sweeps: every cell drains to the border
    recv, slope = tf.d8_receivers(filled)           # steepest-descent receiver per cell (flat index, self = outlet)
    lvl = tf.levels(recv)                           # distance in hops from each cell's outlet
    area = tf.drainage_area(recv, lvl)              # cells upstream, itself included
    h, area = tf.stream_power(h, steps, uplift=u)   # Braun & Willett's implicit scheme, n = 1

The implicit stream-power update needs each receiver before its donors; grouping cells by
their hop distance from the outlet gives that order with one vectorised update per level,
which is what makes a 300-step flat-start run on 256 cells take seconds rather than minutes.
"""
import math

import numpy as np

D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
D8_LEN = np.array([math.sqrt(2), 1, math.sqrt(2), 1, 1, math.sqrt(2), 1, math.sqrt(2)])


def _sweep_axis0(W, h, eps, forward):
    """one Planchon-Darboux sweep along rows: each row sees the row before it (3 cells) and its
    own neighbours from the previous state; vectorised across the columns"""
    n, m = W.shape
    rows = range(1, n) if forward else range(n - 2, -1, -1)
    for i in rows:
        p = i - 1 if forward else i + 1
        prev = W[p]
        low = np.minimum(prev, np.minimum(np.concatenate(([prev[0]], prev[:-1])), np.concatenate((prev[1:], [prev[-1]]))))
        cur = W[i]
        side = np.minimum(np.concatenate(([cur[0]], cur[:-1])), np.concatenate((cur[1:], [cur[-1]])))
        low = np.minimum(low, side)
        W[i] = np.maximum(h[i], np.minimum(cur, low + eps))


def fill_depressions(h, eps=1e-4, max_rounds=200, outlet=None):
    """Planchon & Darboux 2001: start with water everywhere, drain it through the border
    (or the `outlet` mask) by alternating directional sweeps until nothing changes. Returns
    the filled copy: every cell has a strictly lower neighbour on a path to an outlet."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    W = np.full_like(h, np.inf)
    if outlet is None:
        W[0, :] = h[0, :]; W[-1, :] = h[-1, :]; W[:, 0] = h[:, 0]; W[:, -1] = h[:, -1]
    else:
        W[outlet] = h[outlet]
    for r in range(max_rounds):
        before = W.copy()
        _sweep_axis0(W, h, eps, True)
        _sweep_axis0(W, h, eps, False)
        Wt = np.ascontiguousarray(W.T); ht = np.ascontiguousarray(h.T)
        _sweep_axis0(Wt, ht, eps, True)
        _sweep_axis0(Wt, ht, eps, False)
        W = np.ascontiguousarray(Wt.T)
        if np.array_equal(before, W):
            break
    return W


def d8_receivers(h):
    """Steepest-descent receiver per cell as a flat index (self where none) and the slope to it."""
    n, m = h.shape
    best = np.zeros_like(h)
    recv = np.arange(n * m).reshape(n, m)
    padded = np.pad(h, 1, mode="edge")
    for k, (di, dj) in enumerate(D8):
        nb = padded[1 + di:1 + di + n, 1 + dj:1 + dj + m]
        slope = (h - nb) / D8_LEN[k]
        better = slope > best
        ii, jj = np.nonzero(better)
        recv[ii, jj] = np.clip(ii + di, 0, n - 1) * m + np.clip(jj + dj, 0, m - 1)
        best[better] = slope[better]
    return recv.ravel(), best


def levels(recv):
    """hops from each cell to its outlet (outlets 0); vectorised fixed-point iteration"""
    lvl = np.full(recv.size, -1, dtype=np.int32)
    lvl[recv == np.arange(recv.size)] = 0
    for _ in range(recv.size):
        unknown = lvl < 0
        ready = unknown & (lvl[recv] >= 0)
        if not ready.any():
            break
        lvl[ready] = lvl[recv[ready]] + 1
    lvl[lvl < 0] = 0          # cycles cannot happen on a filled surface; be safe anyway
    return lvl


def level_groups(lvl):
    """cells grouped by level: list of index arrays, level 0 first"""
    order = np.argsort(lvl, kind="stable")
    counts = np.bincount(lvl)
    return np.split(order, np.cumsum(counts)[:-1])


def drainage_area(recv, lvl=None, weights=None):
    """Cells upstream of each cell, itself included (or the sum of `weights`), as a flat array."""
    if lvl is None:
        lvl = levels(recv)
    area = np.ones(recv.size) if weights is None else np.asarray(weights, dtype=np.float64).ravel().copy()
    groups = level_groups(lvl)
    for cells in reversed(groups[1:]):
        np.add.at(area, recv[cells], area[cells])
    return area


def stream_power(h, steps=300, dt=1.0, k=0.02, m_exp=0.5, uplift=None, diffusion=0.05, fixed=None,
                 outlet=None, cap_slope=None, log=None, hook=None):
    """dh/dt = U - k A^m S (n = 1), Braun & Willett 2013 implicit, plus linear hillslope
    diffusion. Cell size 1, h in cell units. k: scalar or per-cell array (erodibility: hard
    plateau tops resist incision). uplift: scalar or array per unit time (may be
    changed between steps through `hook(step, h, area)`, which can return a new uplift or a
    dict with "uplift" and/or "cap_slope").
    cap_slope: optional tan of a maximum slope (no cell higher than its receiver plus that
    slope: Cordonnier's slope cap, a cheap stand-in for thermal erosion inside the loop).
    Returns h and the final drainage area."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, mm = h.shape
    up = 0.0 if uplift is None else uplift
    area = None
    idx = np.arange(n * mm)
    for s in range(steps):
        filled = fill_depressions(h, outlet=outlet)
        recv, _ = d8_receivers(filled)
        lvl = levels(recv)
        area = drainage_area(recv, lvl)
        hf = h.ravel()
        uf = np.broadcast_to(np.asarray(up, dtype=np.float64), h.shape).ravel()
        kf = np.asarray(k, dtype=np.float64).ravel() if np.ndim(k) else k
        coef = dt * kf * np.power(area, m_exp)
        new = hf + dt * uf
        groups = level_groups(lvl)
        for cells in groups[1:]:
            r = recv[cells]
            new[cells] = (hf[cells] + dt * uf[cells] + coef[cells] * new[r]) / (1.0 + coef[cells])
        if cap_slope is not None:
            dist = np.hypot(idx // mm - recv // mm, idx % mm - recv % mm)
            for cells in groups[1:]:
                new[cells] = np.minimum(new[cells], new[recv[cells]] + cap_slope * dist[cells])
        h = new.reshape(n, mm)
        if diffusion > 0:
            lap = (np.roll(h, 1, 0) + np.roll(h, -1, 0) + np.roll(h, 1, 1) + np.roll(h, -1, 1) - 4 * h)
            lap[0, :] = lap[-1, :] = lap[:, 0] = lap[:, -1] = 0
            h += dt * diffusion * lap
        if fixed is not None:
            h[fixed] = hf.reshape(n, mm)[fixed]
        if hook is not None:
            r = hook(s, h, area.reshape(n, mm))
            if isinstance(r, dict):
                up = r.get("uplift", up)
                cap_slope = r.get("cap_slope", cap_slope)
            elif r is not None:
                up = r
        if log and (s % 50 == 0 or s == steps - 1):
            log("stream power step %d/%d: relief %.1f, max area %d" % (s + 1, steps, h.max() - h.min(), int(area.max())))
    return h, area.reshape(n, mm)
