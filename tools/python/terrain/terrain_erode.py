"""Terrain formation for generated maps: valleys from stream power, gullies from droplets,
cliffs and scree from thermal slumping under banded rock hardness, with every mask a
layer painter needs read off the simulation state. NumPy in, NumPy out.

    import terrain_erode as te
    out = te.erode(h, metres_per_cell, fixed=mask_of_cells_to_leave_alone, seed=1)
    out["h"]        the eroded heights (same units as h, metres recommended)
    out["flow"]     drainage area per cell (cells), log-scaled use: wet / dirt layer
    out["deposit"]  sediment laid down (height units): soil / grass layer
    out["wear"]     material carried away (height units): bare rock layer with slope
    out["debris"]   volume moved by slumping (height units): scree layer
    out["slope"]    tan of the slope angle
    out["hardness"] the rock hardness field 0..1 (banded by height)

Stages (research: games/reports/Terrain look for generated maps.md, section "ordered plan"):
  1. stream power + uplift (Braun-Willett implicit, m = 0.5, n = 1) with hillslope diffusion:
     the valley network, 200+ steps;
  2. batched droplets (Lague / Beyer defaults): gullies; forced deposition on flat ground;
  3. thermal slumping (Olsen, c = 0.5) with the talus angle from hardness (Jako): cliffs, scree.
Works on 128x128 to 512x512 in seconds to a minute (pure NumPy, no SciPy).

    py tools/python/terrain/terrain_erode.py --demo         writes demo PNGs next to this file
"""
import heapq
import math
import os
import sys

import numpy as np


# ------------------------------------------------------------------------------------------
# flow routing
# ------------------------------------------------------------------------------------------
D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
D8_LEN = np.array([math.sqrt(2), 1, math.sqrt(2), 1, 1, math.sqrt(2), 1, math.sqrt(2)])


def fill_depressions(h, eps=1e-4):
    """Priority-flood (Barnes 2014): every cell drains to the border; tiny epsilon slope so
    flow routing has a direction across filled lakes. Returns the filled copy."""
    n, m = h.shape
    out = h.copy()
    done = np.zeros_like(h, dtype=bool)
    heap = []
    for i in range(n):
        for j in (0, m - 1):
            heap.append((out[i, j], i, j)); done[i, j] = True
    for j in range(1, m - 1):
        for i in (0, n - 1):
            heap.append((out[i, j], i, j)); done[i, j] = True
    heapq.heapify(heap)
    while heap:
        z, i, j = heapq.heappop(heap)
        for di, dj in D8:
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < m and not done[a, b]:
                done[a, b] = True
                if out[a, b] < z + eps:
                    out[a, b] = z + eps
                heapq.heappush(heap, (out[a, b], a, b))
    return out


def d8_receivers(h):
    """Steepest-descent receiver per cell as flat index (self where none), and the slope to it."""
    n, m = h.shape
    best_slope = np.zeros_like(h)
    recv = np.arange(n * m).reshape(n, m)
    padded = np.pad(h, 1, mode="edge")
    for k, (di, dj) in enumerate(D8):
        nb = padded[1 + di:1 + di + n, 1 + dj:1 + dj + m]
        slope = (h - nb) / D8_LEN[k]
        better = slope > best_slope
        ii, jj = np.nonzero(better)
        a = np.clip(ii + di, 0, n - 1); b = np.clip(jj + dj, 0, m - 1)
        recv[ii, jj] = a * m + b
        best_slope[better] = slope[better]
    return recv.ravel(), best_slope


def drainage_area(h, recv):
    """Cells upstream of each cell (itself included), accumulated in height order."""
    order = np.argsort(h.ravel())[::-1]          # highest first
    area = np.ones(h.size)
    for c in order:
        r = recv[c]
        if r != c:
            area[r] += area[c]
    return area.reshape(h.shape), order


# ------------------------------------------------------------------------------------------
# stage 1: stream power with uplift (Braun & Willett 2013, implicit, n = 1)
# ------------------------------------------------------------------------------------------
def stream_power(h, steps=300, dt=1.0, k=0.02, m_exp=0.5, uplift=None, diffusion=0.05, fixed=None, log=None):
    """h in height units, cell size 1 (scale k for your units). uplift: array or scalar per
    step. Returns h and the final drainage area."""
    h = h.astype(np.float64).copy()
    n, mm = h.shape
    if uplift is None:
        uplift = 0.0
    area = None
    for s in range(steps):
        filled = fill_depressions(h)
        recv, _ = d8_receivers(filled)
        area, order = drainage_area(filled, recv)
        hf = h.ravel()
        up = np.broadcast_to(np.asarray(uplift, dtype=np.float64), h.shape).ravel()
        coef = dt * k * np.power(area.ravel(), m_exp)
        new = hf.copy()
        # from the outlets upward: receivers are already updated when a cell is processed
        for c in order[::-1]:
            r = recv[c]
            if r == c:
                new[c] = hf[c] + dt * up[c]
            else:
                new[c] = (hf[c] + dt * up[c] + coef[c] * new[r]) / (1 + coef[c])
        h = new.reshape(n, mm)
        if diffusion > 0:
            lap = (np.roll(h, 1, 0) + np.roll(h, -1, 0) + np.roll(h, 1, 1) + np.roll(h, -1, 1) - 4 * h)
            lap[0, :] = lap[-1, :] = lap[:, 0] = lap[:, -1] = 0
            h += dt * diffusion * lap
        if fixed is not None:
            h[fixed] = hf.reshape(n, mm)[fixed]
        if log and (s % 50 == 0 or s == steps - 1):
            log("stream power step %d/%d: relief %.1f, max area %d" % (s + 1, steps, h.max() - h.min(), int(area.max())))
    return h, area


# ------------------------------------------------------------------------------------------
# stage 2: droplets (Lague's port of Beyer), batched across droplets with NumPy
# ------------------------------------------------------------------------------------------
def droplets(h, count=60000, lifetime=30, radius=2, inertia=0.05, capacity=4.0, min_slope=0.01,
             erode_speed=0.3, deposit_speed=0.3, evaporate=0.01, gravity=4.0, hardness=None,
             flat_deposit_deg=2.5, fixed=None, seed=0, batch=4000, log=None):
    """Returns h, deposit map, wear map, visit map. Height units = cell units here; scale h
    before calling if cells are not unit-sized (the caller does that)."""
    rng = np.random.default_rng(seed)
    h = h.astype(np.float64).copy()
    n, m = h.shape
    deposit = np.zeros_like(h); wear = np.zeros_like(h); visits = np.zeros_like(h)
    soft = 1.0 if hardness is None else (1.0 - 0.85 * hardness)
    tan_flat = math.tan(math.radians(flat_deposit_deg))
    # brush offsets
    offs = [(di, dj, max(0.0, radius - math.hypot(di, dj))) for di in range(-radius, radius + 1) for dj in range(-radius, radius + 1)]
    offs = [(di, dj, w) for di, dj, w in offs if w > 0]
    wsum = sum(w for _, _, w in offs)
    brush = [(di, dj, w / wsum) for di, dj, w in offs]

    def grad_and_height(px, py):
        x0 = np.clip(px.astype(int), 0, m - 2); y0 = np.clip(py.astype(int), 0, n - 2)
        fx = px - x0; fy = py - y0
        h00 = h[y0, x0]; h10 = h[y0, x0 + 1]; h01 = h[y0 + 1, x0]; h11 = h[y0 + 1, x0 + 1]
        gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
        gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
        hh = h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy) + h01 * (1 - fx) * fy + h11 * fx * fy
        return gx, gy, hh, x0, y0, fx, fy

    for b0 in range(0, count, batch):
        nb = min(batch, count - b0)
        px = rng.uniform(1, m - 2, nb); py = rng.uniform(1, n - 2, nb)
        dx = np.zeros(nb); dy = np.zeros(nb)
        speed = np.ones(nb); water = np.ones(nb); sed = np.zeros(nb)
        alive = np.ones(nb, dtype=bool)
        for life in range(lifetime):
            gx, gy, hold, x0, y0, fx, fy = grad_and_height(px, py)
            dx = dx * inertia - gx * (1 - inertia); dy = dy * inertia - gy * (1 - inertia)
            ln = np.hypot(dx, dy)
            rnd = ln < 1e-9
            if rnd.any():
                ang = rng.uniform(0, 2 * math.pi, int(rnd.sum()))
                dx[rnd] = np.cos(ang); dy[rnd] = np.sin(ang); ln[rnd] = 1
            dx /= ln; dy /= ln
            nx = px + dx; ny = py + dy
            alive &= (nx >= 1) & (nx < m - 2) & (ny >= 1) & (ny < n - 2)
            if not alive.any():
                break
            _, _, hnew, _, _, _, _ = grad_and_height(np.clip(nx, 1, m - 2), np.clip(ny, 1, n - 2))
            dh = hnew - hold
            cap = np.maximum(-dh, min_slope) * speed * water * capacity
            # deposit: carrying too much, or going uphill, or on flat ground (valley floors)
            flat = np.hypot(gx, gy) < tan_flat
            dep_amt = np.where(dh > 0, np.minimum(dh, sed), (sed - cap) * deposit_speed)
            dep_amt = np.where(flat, np.maximum(dep_amt, sed * 0.5), dep_amt)
            dep_amt = np.clip(dep_amt, 0, sed)
            ero_amt = np.where((sed <= cap) & (dh <= 0), np.minimum((cap - sed) * erode_speed, -dh), 0.0)
            ero_amt *= alive
            dep_amt *= alive
            # deposit at the old cell (bilinear), erode with the brush
            iy = y0; ix = x0
            np.add.at(h, (iy, ix), dep_amt * (1 - fx) * (1 - fy)); np.add.at(h, (iy, ix + 1), dep_amt * fx * (1 - fy))
            np.add.at(h, (iy + 1, ix), dep_amt * (1 - fx) * fy); np.add.at(h, (iy + 1, ix + 1), dep_amt * fx * fy)
            np.add.at(deposit, (iy, ix), dep_amt)
            for di, dj, w in brush:
                yy = np.clip(iy + di, 0, n - 1); xx = np.clip(ix + dj, 0, m - 1)
                amt = ero_amt * w * (soft if np.isscalar(soft) else soft[yy, xx])
                if fixed is not None:
                    amt = np.where(fixed[yy, xx], 0.0, amt)
                np.add.at(h, (yy, xx), -amt)
                np.add.at(wear, (yy, xx), amt)
            np.add.at(visits, (iy, ix), water * alive)
            sed = sed + ero_amt - dep_amt
            speed = np.sqrt(np.maximum(speed * speed + dh * gravity, 0))
            water *= (1 - evaporate)
            px, py = nx, ny
        if log and (b0 // batch) % 5 == 0:
            log("droplets %d/%d" % (b0 + nb, count))
    return h, deposit, wear, visits


# ------------------------------------------------------------------------------------------
# stage 3: thermal slumping with a hardness field (Olsen 2004; Jako & Toth 2011)
# ------------------------------------------------------------------------------------------
def banded_hardness(h, bands=5, hard_fraction=0.3, cap=True, seed=0):
    """Hardness 0..1 as a function of height: thin hard bands (strata) and, with cap, a thick
    hard layer at the top (mesas keep their table)."""
    rng = np.random.default_rng(seed)
    z = (h - h.min()) / max(h.max() - h.min(), 1e-9)
    hard = np.full_like(h, 0.15)
    for b in range(bands):
        centre = (b + 0.5) / bands + rng.uniform(-0.04, 0.04)
        width = hard_fraction / bands
        hard = np.maximum(hard, 0.9 * np.exp(-((z - centre) / (width * 0.5)) ** 2))
    if cap:
        hard = np.maximum(hard, 0.85 * np.clip((z - 0.8) / 0.08, 0, 1))
    return hard


def thermal(h, iterations=50, c=0.5, hardness=None, fixed=None, log=None):
    """Olsen's rule: material above the talus angle moves to the lower neighbours. The talus
    angle follows hardness: 32 deg for loose material up to 70 deg for hard rock. Returns
    h and the debris (moved volume) map. Cell size 1."""
    h = h.astype(np.float64).copy()
    n, m = h.shape
    debris = np.zeros_like(h)
    R = np.zeros_like(h) if hardness is None else hardness
    # the angle of repose by hardness: loose material rests at ~32 deg, hard rock stands at ~70
    T = math.tan(math.radians(32)) + R * (math.tan(math.radians(70)) - math.tan(math.radians(32)))
    for it in range(iterations):
        padded = np.pad(h, 1, mode="edge")
        total = np.zeros_like(h); dmax = np.zeros_like(h)
        diffs = []
        for k, (di, dj) in enumerate(D8):
            nb = padded[1 + di:1 + di + n, 1 + dj:1 + dj + m]
            d = (h - nb) / D8_LEN[k]
            over = np.where(d > T, d - T, 0.0)
            diffs.append(over)
            total += over
            dmax = np.maximum(dmax, over)
        move = c * dmax * (1.0 - 0.7 * R)              # hard rock sheds little
        move = np.where(total > 0, move, 0.0)
        if fixed is not None:
            move[fixed] = 0.0
        h -= move
        debris += move
        for k, (di, dj) in enumerate(D8):
            share = np.where(total > 0, move * diffs[k] / np.maximum(total, 1e-12), 0.0)
            yy = np.clip(np.arange(n)[:, None] + di, 0, n - 1); xx = np.clip(np.arange(m)[None, :] + dj, 0, m - 1)
            np.add.at(h, (np.broadcast_to(yy, (n, m)), np.broadcast_to(xx, (n, m))), share)
        if log and (it % 25 == 0 or it == iterations - 1):
            log("thermal %d/%d: moved %.2f" % (it + 1, iterations, float(move.sum())))
    return h, debris


# ------------------------------------------------------------------------------------------
# the whole thing
# ------------------------------------------------------------------------------------------
def slope_tan(h):
    gy, gx = np.gradient(h)
    return np.hypot(gx, gy)


def erode(h, metres_per_cell=10.0, fixed=None, seed=0,
          sp_steps=250, sp_k=0.008, sp_diffusion=0.03, uplift=None,
          droplet_count=60000, droplet_kw=None,
          thermal_iterations=50, hardness_bands=5, keep_relief=True, log=print):
    """h: 2D float array in METRES (or any unit; metres_per_cell gives the cell size in the
    same unit). fixed: bool array of cells to leave untouched (building pads). Returns a dict
    (see the module docstring). The simulation runs in cell units (height / metres_per_cell).
    keep_relief: the result is stretched back to the input's height range (erosion carves the
    shape; a game map keeps the relief its designer gave it)."""
    h0 = np.asarray(h, dtype=np.float64)
    scale = float(metres_per_cell)
    hc = h0 / scale                                      # cell units: slope = tan directly
    if fixed is not None:
        fixed = np.asarray(fixed, dtype=bool)
    # 1. valleys
    hc, area = stream_power(hc, steps=sp_steps, k=sp_k, diffusion=sp_diffusion, uplift=None if uplift is None else np.asarray(uplift) / scale, fixed=fixed, log=log)
    hard = banded_hardness(hc, bands=hardness_bands, seed=seed)
    # 2. gullies
    kw = dict(count=droplet_count, seed=seed, hardness=hard, fixed=fixed, log=log)
    if droplet_kw:
        kw.update(droplet_kw)
    hc, deposit, wear, visits = droplets(hc, **kw)
    # 3. cliffs and scree
    hc, debris = thermal(hc, iterations=thermal_iterations, hardness=hard, fixed=fixed, log=log)
    if keep_relief:
        lo, hi = float(hc.min()), float(hc.max())
        lo0, hi0 = float((h0 / scale).min()), float((h0 / scale).max())
        if hi > lo:
            hc = lo0 + (hc - lo) * (hi0 - lo0) / (hi - lo)
    if fixed is not None:
        hc[fixed] = (h0 / scale)[fixed]
    filled = fill_depressions(hc)
    recv, _ = d8_receivers(filled)
    flow, _ = drainage_area(filled, recv)
    return {
        "h": (hc * scale).astype(np.float32),
        "flow": flow.astype(np.float32),
        "visits": visits.astype(np.float32),
        "deposit": (deposit * scale).astype(np.float32),
        "wear": (wear * scale).astype(np.float32),
        "debris": (debris * scale).astype(np.float32),
        "slope": slope_tan(hc).astype(np.float32),
        "hardness": hard.astype(np.float32),
    }


def layer_masks(out, water_level=None):
    """The painter's masks, 0..1 each, from erode()'s output (thresholds from the report's
    table). water_level in the same units as h, or None."""
    h = out["h"]; slope = out["slope"]; deg = np.degrees(np.arctan(slope))
    relief = max(float(h.max() - h.min()), 1e-6)
    z = (h - h.min()) / relief

    def smooth(x, lo, hi):
        t = np.clip((x - lo) / max(hi - lo, 1e-9), 0, 1)
        return t * t * (3 - 2 * t)

    flow = np.log1p(out["flow"]); flow = flow / max(flow.max(), 1e-9)
    dep = out["deposit"]; dep = dep / max(np.percentile(dep, 99), 1e-9)
    debris = out["debris"]; debris = debris / max(np.percentile(debris[debris > 0], 75) if (debris > 0).any() else 1, 1e-9)
    wear = out["wear"]; wear = wear / max(np.percentile(wear, 99), 1e-9)
    masks = {
        "grass": smooth(dep, 0.1, 0.5) * (1 - smooth(deg, 20, 30)),
        "wet": smooth(flow, 0.75, 0.9),
        "scree": smooth(debris, 0.3, 1.0) * smooth(deg, 25, 32) * (1 - smooth(deg, 40, 50)),
        "rock": np.maximum(smooth(deg, 32, 40) * smooth(wear, 0.2, 0.6), smooth(deg, 50, 58)),
        "snow": smooth(z, 0.82, 0.9) * (1 - smooth(deg, 40, 50)),
    }
    masks["rock"] = np.maximum(masks["rock"], out["hardness"] * smooth(deg, 30, 40))
    if water_level is not None:
        band = 0.02 * relief
        masks["sand"] = (1 - smooth(np.abs(h - water_level), band, 2 * band)) * (1 - smooth(deg, 3, 6))
    return masks


def _demo():
    here = os.path.dirname(os.path.abspath(__file__))
    rng = np.random.default_rng(3)
    n = 128
    # fBm base, 5 octaves
    def fbm(n, octaves=5, gain=0.5):
        acc = np.zeros((n, n)); amp = 1.0; freq = 4
        for o in range(octaves):
            g = rng.standard_normal((freq + 1, freq + 1))
            ys = np.linspace(0, freq, n); xs = np.linspace(0, freq, n)
            yi = np.clip(ys.astype(int), 0, freq - 1); xi = np.clip(xs.astype(int), 0, freq - 1)
            fy = (ys - yi)[:, None]; fx = (xs - xi)[None, :]
            fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
            v = (g[yi][:, xi] * (1 - fx) * (1 - fy) + g[yi][:, xi + 1] * fx * (1 - fy) + g[yi + 1][:, xi] * (1 - fx) * fy + g[yi + 1][:, xi + 1] * fx * fy)
            acc += amp * v; amp *= gain; freq *= 2
        return acc
    base = fbm(n)
    base = (base - base.min()) / (base.max() - base.min())
    base = np.power(base * 1.2, 1.8) * 300.0            # metres of relief
    yy, xx = np.mgrid[0:n, 0:n]
    base += 120.0 * np.exp(-(((yy - n * 0.55) ** 2 + (xx - n * 0.45) ** 2) / (2 * (n * 0.25) ** 2)))   # the range
    out = erode(base, metres_per_cell=10.0, seed=3, sp_steps=150, droplet_count=40000)
    masks = layer_masks(out)
    np.save(os.path.join(here, "demo_base.npy"), base.astype(np.float32))
    np.save(os.path.join(here, "demo_eroded.npy"), out["h"])
    try:
        from PIL import Image
        def save(name, a):
            a = np.asarray(a, dtype=np.float64)
            a = (a - a.min()) / max(a.max() - a.min(), 1e-9)
            Image.fromarray((a * 255).astype(np.uint8)).save(os.path.join(here, "demo_%s.png" % name))
        save("base", base); save("eroded", out["h"]); save("flow", np.log1p(out["flow"])); save("deposit", out["deposit"])
        save("wear", out["wear"]); save("debris", out["debris"])
        for k, v in masks.items():
            save("mask_" + k, v)
        print("demo PNGs written to", here)
    except ImportError:
        print("PIL missing: no PNGs, but erode() ran")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        print(__doc__)
