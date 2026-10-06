"""Sketch to uplift: the designer's lines become the tectonic uplift field that the stream-power
solver turns into a landscape (Cordonnier 2016, Schott 2023), plus the exact-geometry tools
(Hnaidi-style harmonic fill) for plateaus, pads and cliffs after erosion.

A sketch is a JSON-able dict; coordinates are 0..1 across the map (x right, y down):

    {"size": 256, "metres_per_cell": 10.24, "relief": 500, "preset": "alpine",
     "outlet": "border" | "south" | "north" | "east" | "west" | ["south", "east"],
     "base": 0.35,                      # uplift everywhere, before the primitives (0..1)
     "roughness": 0.15,                 # noise on the uplift, as a fraction (0 = none)
     "items": [
       {"type": "ridge",   "points": [[0.1, 0.2], [0.5, 0.4], [0.9, 0.3]], "width": 0.08, "strength": 1.0},
       {"type": "valley",  "points": [[0.5, 1.0], [0.6, 0.5]], "width": 0.05, "depth": 0.85},
       {"type": "plateau", "polygon": [[0.1, 0.1], [0.4, 0.1], [0.4, 0.4]], "strength": 0.9, "edge": 0.03, "resist": 0.95},
       {"type": "basin",   "polygon": [...], "depth": 0.6},
       {"type": "peak",    "at": [0.5, 0.4], "height": 0.95, "radius": 0.03},      # exact height (PID)
       {"type": "pad",     "polygon": [...] | "at": [x, y], "radius": 0.03}           # flat after erosion
     ]}

    import terrain_sketch as sk
    r = sk.rasterise(sketch)          # r["uplift"] 0..1 field, r["peaks"], r["pads"], r["outlet"], r["valley_d"]
    h = sk.harmonic_fill(h, known)    # Laplace interpolation of the unknown cells (sparse solve)
"""
import json
import math

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.linalg import spsolve

import terrain_noise as tn


# ------------------------------------------------------------------------------------------
# rasterising lines and polygons
# ------------------------------------------------------------------------------------------
def to_cells(points, n):
    return [(float(p[1]) * (n - 1), float(p[0]) * (n - 1)) for p in points]    # (row, col)


def polyline_mask(n, pts_cells):
    """cells touched by the polyline (row, col) pairs, sampled every half cell"""
    mask = np.zeros((n, n), dtype=bool)
    for (r0, c0), (r1, c1) in zip(pts_cells[:-1], pts_cells[1:]):
        length = math.hypot(r1 - r0, c1 - c0)
        steps = max(2, int(length * 2) + 1)
        t = np.linspace(0, 1, steps)
        rr = np.clip(np.rint(r0 + (r1 - r0) * t).astype(int), 0, n - 1)
        cc = np.clip(np.rint(c0 + (c1 - c0) * t).astype(int), 0, n - 1)
        mask[rr, cc] = True
    return mask


def distance_to(mask):
    """distance in cells from every cell to the nearest True cell"""
    if not mask.any():
        return np.full(mask.shape, np.inf)
    return ndimage.distance_transform_edt(~mask)


def polygon_mask(n, poly_cells):
    """even-odd fill of a polygon given as (row, col) vertices"""
    rr, cc = np.mgrid[0:n, 0:n]
    inside = np.zeros((n, n), dtype=bool)
    k = len(poly_cells)
    for i in range(k):
        r0, c0 = poly_cells[i]; r1, c1 = poly_cells[(i + 1) % k]
        cond = (r0 > rr) != (r1 > rr)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = c0 + (rr - r0) * (c1 - c0) / (r1 - r0)
        inside ^= cond & (cc < xint)
    return inside


def soft_band(dist, width, inner=0.35):
    """1 inside `inner` x width of the line, smooth to 0 at width (cells)"""
    return 1.0 - tn.smoothstep(dist, width * inner, width)


def outlet_mask(n, spec):
    sides = [spec] if isinstance(spec, str) else list(spec)
    mask = np.zeros((n, n), dtype=bool)
    for s in sides:
        if s == "border":
            mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = True
        elif s == "north":
            mask[0, :] = True
        elif s == "south":
            mask[-1, :] = True
        elif s == "west":
            mask[:, 0] = True
        elif s == "east":
            mask[:, -1] = True
    if not mask.any():
        mask[-1, :] = True
    return mask


# ------------------------------------------------------------------------------------------
# the uplift field
# ------------------------------------------------------------------------------------------
def rasterise(sketch, seed=0):
    """Build the uplift field (0..1) from the sketch's primitives. Ridges raise uplift along a
    band, valleys multiply it down (low-uplift corridors become the rivers), plateaus set a
    block, basins lower a block, the outlet border fades to zero (water must leave somewhere),
    and gradient noise adds roughness. Also returns the peak constraints, pad masks and the
    distance-to-valley field (used to keep the designed rivers wet)."""
    n = int(sketch.get("size", 256))
    base = float(sketch.get("base", 0.35))
    u = np.full((n, n), base)
    peaks = []; pads = []
    valley_d = np.full((n, n), np.inf)
    resist = np.zeros((n, n))                 # plateau interiors: erodibility reduced (mesa tables)
    for it in sketch.get("items", []):
        t = it["type"]
        if t == "ridge":
            d = distance_to(polyline_mask(n, to_cells(it["points"], n)))
            band = soft_band(d, float(it.get("width", 0.06)) * n)
            u = np.maximum(u, base + (float(it.get("strength", 1.0)) - base) * band)
        elif t == "valley":
            d = distance_to(polyline_mask(n, to_cells(it["points"], n)))
            valley_d = np.minimum(valley_d, d)
            band = soft_band(d, float(it.get("width", 0.05)) * n, inner=0.2)
            u = u * (1.0 - float(it.get("depth", 0.85)) * band)
        elif t == "plateau":
            inside = polygon_mask(n, to_cells(it["polygon"], n))
            d = distance_to(inside)
            band = soft_band(d + 1e-9, max(1.0, float(it.get("edge", 0.02)) * n), inner=0.0)
            band[inside] = 1.0
            u = np.maximum(u, base + (float(it.get("strength", 0.9)) - base) * band)
            resist = np.maximum(resist, float(it.get("resist", 0.95)) * band)
        elif t == "basin":
            inside = polygon_mask(n, to_cells(it["polygon"], n))
            d = distance_to(inside)
            band = soft_band(d + 1e-9, max(1.0, float(it.get("edge", 0.03)) * n), inner=0.0)
            band[inside] = 1.0
            u = u * (1.0 - float(it.get("depth", 0.6)) * band)
        elif t == "peak":
            r, c = to_cells([it["at"]], n)[0]
            peaks.append({"row": int(round(r)), "col": int(round(c)), "height": float(it.get("height", 1.0)),
                          "radius": max(2.0, float(it.get("radius", 0.02)) * n)})
            rr, cc = np.mgrid[0:n, 0:n]
            d = np.hypot(rr - r, cc - c)
            # uplift above the ridges' 1.0 so the summit grows above its ridge on its own
            u = np.maximum(u, base + (1.6 * float(it.get("height", 1.0)) - base) * soft_band(d, max(4.0, float(it.get("radius", 0.02)) * n * 3.0)))
        elif t == "pad":
            if "polygon" in it:
                inside = polygon_mask(n, to_cells(it["polygon"], n))
            else:
                r, c = to_cells([it["at"]], n)[0]
                rr, cc = np.mgrid[0:n, 0:n]
                inside = np.hypot(rr - r, cc - c) <= float(it.get("radius", 0.03)) * n
            pads.append({"mask": inside, "height": it.get("height")})
    # roughness: gradient noise, multiplicative so flats stay flat-ish and ridges get texture
    rough = float(sketch.get("roughness", 0.15))
    if rough > 0:
        nz = tn.fbm((n, n), freq=6.0, octaves=5, gain=0.6, seed=seed + 11, kind=sketch.get("roughness_kind", "fbm"))
        u = u * (1.0 + rough * np.clip(nz, -2, 2) * 0.5)
    # outlet: uplift fades to zero at the outlet edge over `edge` cells; water leaves there
    outlet = outlet_mask(n, sketch.get("outlet", "border"))
    fade = float(sketch.get("edge_fade", 0.06)) * n
    d = distance_to(outlet)
    u = u * tn.smoothstep(d, 0.0, fade)
    u = np.clip(u, 0.0, None)
    return {"uplift": u, "peaks": peaks, "pads": pads, "outlet": outlet, "valley_d": valley_d, "resist": resist, "size": n}


# ------------------------------------------------------------------------------------------
# exact geometry: harmonic (Laplace) fill of unknown cells with Dirichlet knowns
# ------------------------------------------------------------------------------------------
def harmonic_fill(h, known, bias=None):
    """Replace the cells where known is False by the solution of Laplace's equation with the
    known cells as boundary values (Neumann at the map edge). bias: optional field added as a
    Poisson source (keeps some of the original shape: pass laplacian(h_old) * t)."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    unknown = ~np.asarray(known, dtype=bool)
    idx = np.full(h.size, -1, dtype=np.int64)
    cells = np.nonzero(unknown.ravel())[0]
    if cells.size == 0:
        return h.copy()
    idx[cells] = np.arange(cells.size)
    rows = []; cols = []; vals = []
    rhs = np.zeros(cells.size)
    if bias is not None:
        rhs -= np.asarray(bias, dtype=np.float64).ravel()[cells]
    ci = cells // m; cj = cells % m
    diag = np.zeros(cells.size)
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ni = ci + di; nj = cj + dj
        ok = (ni >= 0) & (ni < n) & (nj >= 0) & (nj < m)
        diag += ok
        nb = ni[ok] * m + nj[ok]
        src = np.nonzero(ok)[0]
        nb_unknown = idx[nb] >= 0
        rows.append(src[nb_unknown]); cols.append(idx[nb[nb_unknown]]); vals.append(-np.ones(int(nb_unknown.sum())))
        np.add.at(rhs, src[~nb_unknown], h.ravel()[nb[~nb_unknown]])
    rows.append(np.arange(cells.size)); cols.append(np.arange(cells.size)); vals.append(diag)
    A = sparse.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(cells.size, cells.size))
    x = spsolve(A, rhs)
    out = h.copy().ravel()
    out[cells] = x
    return out.reshape(n, m)


def flatten_pads(h, pads, halo=4, outlet=None):
    """Each pad becomes flat at its (given or mean) height; a halo of `halo` cells around it is
    re-solved harmonically so the join is smooth. Returns h and the pad mask (for `fixed`)."""
    h = np.asarray(h, dtype=np.float64).copy()
    allpads = np.zeros(h.shape, dtype=bool)
    for p in pads:
        inside = p["mask"]
        if not inside.any():
            continue
        level = float(p["height"]) if p.get("height") is not None else float(h[inside].mean())
        h[inside] = level
        allpads |= inside
    if allpads.any() and halo > 0:
        ring = ndimage.binary_dilation(allpads, iterations=halo) & ~allpads
        known = ~ring
        if outlet is not None:
            known |= outlet
        h = harmonic_fill(h, known)
    return h, allpads


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
