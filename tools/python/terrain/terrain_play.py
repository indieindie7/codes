"""Shape for play: roads, arenas and playability metrics on a formed heightmap (report step 6).

    import terrain_play as tp_
    path = tp_.road_path(h, mpc, (r0, c0), (r1, c1), k_slope=30.0, k_turn=0.6)     # list of (row, col)
    h2, corridor = tp_.lay_road(h, mpc, path, width_cells=2.5, halo_cells=6, max_grade=0.18)
    h3, mask = tp_.arena(h, (r, c), radius_cells, kind="bowl" | "berm" | "pad", depth=0.3)
    tp_.reachable(h, mpc, (r, c), max_slope_deg=30)        # bool map and fraction
    tp_.isovist(h, mpc, (r, c), eye_m=1.7)                  # fraction of the map seen from a point
    tp_.grade_stats(h, mpc, path)                           # max / mean grade along a route

Roads: Dijkstra on (cell, heading) states over the 8-neighbour grid, cost = length x
(1 + k_slope x slope^2) + k_turn x |heading change| (the Wildlands recipe), then the
centreline profile is smoothed with the grade clamped and the terrain blended to it with a
cosine falloff; the corridor is returned as a mask to freeze.
"""
import math

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.csgraph import dijkstra

D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
D8_LEN = np.array([math.sqrt(2), 1, math.sqrt(2), 1, 1, math.sqrt(2), 1, math.sqrt(2)])
D8_ANG = np.array([math.atan2(dj, di) for di, dj in D8])


def road_path(h, mpc, start, end, k_slope=30.0, k_turn=0.6, blocked=None, existing=None):
    """Least-cost path (row, col) list. blocked: bool mask of cells a road may not enter.
    existing: bool mask of cells that already carry a road (near-zero cost, roads merge)."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    N = n * m
    idx = np.arange(N).reshape(n, m)
    rows = []; cols = []; costs = []
    for d, (di, dj) in enumerate(D8):
        src_r = np.arange(n)[:, None] + np.zeros(m, dtype=int)[None, :]
        src_c = np.zeros(n, dtype=int)[:, None] + np.arange(m)[None, :]
        dst_r = src_r + di; dst_c = src_c + dj
        ok = (dst_r >= 0) & (dst_r < n) & (dst_c >= 0) & (dst_c < m)
        s = idx[ok]; t = (dst_r * m + dst_c)[ok]
        dz = h.ravel()[t] - h.ravel()[s]
        length = D8_LEN[d] * mpc
        slope = dz / length
        c = length * (1.0 + k_slope * slope * slope)
        if blocked is not None:
            c = np.where(blocked.ravel()[t], 1e9, c)
        if existing is not None:
            c = np.where(existing.ravel()[t] & existing.ravel()[s], c * 0.05, c)
        # state = cell * 8 + heading; entering t with heading d from s with any heading e
        for e in range(8):
            turn = abs((D8_ANG[d] - D8_ANG[e] + math.pi) % (2 * math.pi) - math.pi)
            rows.append(s * 8 + e); cols.append(t * 8 + d); costs.append(c + k_turn * turn * mpc)
    G = sparse.csr_matrix((np.concatenate(costs), (np.concatenate(rows), np.concatenate(cols))), shape=(N * 8, N * 8))
    s0 = (start[0] * m + start[1]) * 8
    dist, pred, _ = dijkstra(G, directed=True, indices=[s0 + e for e in range(8)], return_predecessors=True, min_only=True)
    t0 = (end[0] * m + end[1]) * 8
    best = min(range(8), key=lambda e: dist[t0 + e])
    node = t0 + best
    path = []
    while node >= 0 and node != -9999:
        cell = node // 8
        path.append((cell // m, cell % m))
        if dist[node] == 0:
            break
        node = pred[node]
    path.reverse()
    # drop repeated cells (heading changes at the same cell)
    out = []
    for p in path:
        if not out or out[-1] != p:
            out.append(p)
    return out


def path_lengths(path, mpc):
    seg = [0.0]
    for (r0, c0), (r1, c1) in zip(path[:-1], path[1:]):
        seg.append(seg[-1] + math.hypot(r1 - r0, c1 - c0) * mpc)
    return np.array(seg)


def smooth_profile(h, mpc, path, max_grade=0.18, window=9, passes=3):
    """heights along the path: moving average, then the grade clamped forward and backward"""
    z = np.array([h[r, c] for r, c in path], dtype=np.float64)
    s = path_lengths(path, mpc)
    for _ in range(passes):
        k = np.ones(window) / window
        zp = np.pad(z, window // 2, mode="edge")
        z = np.convolve(zp, k, mode="valid")
    for i in range(1, len(z)):
        ds = s[i] - s[i - 1]
        z[i] = np.clip(z[i], z[i - 1] - max_grade * ds, z[i - 1] + max_grade * ds)
    for i in range(len(z) - 2, -1, -1):
        ds = s[i + 1] - s[i]
        z[i] = np.clip(z[i], z[i + 1] - max_grade * ds, z[i + 1] + max_grade * ds)
    return z


def lay_road(h, mpc, path, width_cells=2.5, halo_cells=6.0, max_grade=0.18):
    """Blend the terrain to the road profile: flat across the corridor, cosine falloff over
    the halo. Returns the new heights and the corridor mask (to freeze)."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    z = smooth_profile(h, mpc, path, max_grade)
    line = np.zeros((n, m), dtype=bool)
    pr = np.array([p[0] for p in path]); pc = np.array([p[1] for p in path])
    line[pr, pc] = True
    dist, (ir, ic) = ndimage.distance_transform_edt(~line, return_indices=True)
    # the profile height of the nearest centreline cell
    zmap = np.zeros((n, m)); zmap[pr, pc] = z
    target = zmap[ir, ic]
    w = np.where(dist <= width_cells, 1.0, 0.5 * (1 + np.cos(np.pi * np.clip((dist - width_cells) / max(halo_cells, 1e-6), 0, 1))))
    w = np.where(dist > width_cells + halo_cells, 0.0, w)
    h = h * (1 - w) + target * w
    return h, dist <= width_cells


def arena(h, at, radius, kind="bowl", depth=0.3, rim=0.35, halo=0.6):
    """A fight space. bowl: a smooth depression (depth x radius cells deep) with a low rim;
    berm: a ring of cover at the radius; pad: flat. Returns heights and the arena mask."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    rr, cc = np.mgrid[0:n, 0:m]
    d = np.hypot(rr - at[0], cc - at[1]) / float(radius)
    inside = d <= 1.0 + halo
    level = float(h[d <= 1.0].mean())
    t = np.clip(d, 0, 1 + halo)
    if kind == "bowl":
        prof = level - depth * radius * (1 - t * t) + rim * radius * 0.25 * np.exp(-((t - 1.0) / 0.12) ** 2)
    elif kind == "berm":
        prof = level + rim * radius * 0.3 * np.exp(-((t - 0.85) / 0.08) ** 2)
    else:
        prof = np.full_like(d, level)
    w = np.where(d <= 1.0, 1.0, 0.5 * (1 + np.cos(np.pi * np.clip((d - 1.0) / halo, 0, 1))))
    h = np.where(inside, h * (1 - w) + prof * w, h)
    return h, d <= 1.0


def slope_deg(h, mpc):
    gy, gx = np.gradient(np.asarray(h, dtype=np.float64), mpc)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def reachable(h, mpc, start, max_slope_deg=30.0):
    """cells a walker can reach from start without crossing ground steeper than the limit"""
    ok = slope_deg(h, mpc) <= max_slope_deg
    lab, _ = ndimage.label(ok, structure=np.ones((3, 3)))
    region = lab == lab[start[0], start[1]] if ok[start[0], start[1]] else np.zeros_like(ok)
    return region, float(region.mean())


def isovist(h, mpc, at, eye_m=1.7, rays=180, step=1.0):
    """fraction of the map's cells visible from a point (ray-marched horizon test)"""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    seen = np.zeros((n, m), dtype=bool)
    z0 = h[at[0], at[1]] + eye_m
    for a in np.linspace(0, 2 * math.pi, rays, endpoint=False):
        dr, dc = math.sin(a), math.cos(a)
        best = -np.inf
        t = step
        while True:
            r = at[0] + dr * t; c = at[1] + dc * t
            if r < 0 or r >= n - 1 or c < 0 or c >= m - 1:
                break
            ri, ci = int(r), int(c)
            ang = (h[ri, ci] - z0) / (t * mpc)
            if ang >= best:
                best = ang
                seen[ri, ci] = True
            t += step
    return seen, float(seen.mean())


def grade_stats(h, mpc, path):
    z = np.array([h[r, c] for r, c in path], dtype=np.float64)
    s = path_lengths(path, mpc)
    g = np.abs(np.diff(z)) / np.maximum(np.diff(s), 1e-9)
    return {"length_m": float(s[-1]), "max_grade": float(g.max()) if g.size else 0.0, "mean_grade": float(g.mean()) if g.size else 0.0}
