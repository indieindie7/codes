"""How real does a heightmap look? Landform statistics with published reference ranges, so a
generator's parameters are tuned by measurement (games/reports/Terrain look for generated
maps.md, step 9). NumPy only.

    import terrain_score as ts
    s = ts.score(h, metres_per_cell)      # dict, see below
    ts.report(s)                           # one line per metric with its reference range

Metrics:
  ptrm           Rajasekaran et al.'s perceptual realism regression on the 10 geomorphon
                 fractions (R^2 0.72 vs a 70-person study): real terrain ~0.76, noise ~0.5
  geomorphons    the 10 landform fractions (flat, peak, ridge, shoulder, spur, slope, hollow,
                 footslope, valley, pit); real terrain has many valley/ridge/hollow cells
  psd_slope      radial power-spectrum exponent beta (natural ~1.9-2.1 with this estimator)
  slope_deg      mean / median / p90 slope in degrees and the 36-bin histogram
  horton_rb/rl   Strahler bifurcation and length ratios of the D8 network (3-5 and 1.6-2.4)
  hypsometric    hypsometric integral (0.3-0.6 mature hills)
  drainage_density  channel cells / all cells at the chosen accumulation threshold
and emd(a, b) for comparing two histograms (slopes or geomorphons) against a reference set.
"""
import math
import sys

import numpy as np

try:
    import terrain_erode as te
except ImportError:  # run from elsewhere
    sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")
    import terrain_erode as te

GEOMORPHON_NAMES = ["flat", "peak", "ridge", "shoulder", "spur", "slope", "hollow", "footslope", "valley", "pit"]
# PTRM: (-38.02 + 3.55 depression + 1.75 summit + 25.12 flat + 9.61 valley + 7.59 ridge + 6.71 hollow
#        + 9.02 spur + 7.31 shoulder + 28.95 slope + 7.63 footslope) / 69.96   (fractions 0..1)
PTRM_W = {"pit": 3.55, "peak": 1.75, "flat": 25.12, "valley": 9.61, "ridge": 7.59, "hollow": 6.71,
          "spur": 9.02, "shoulder": 7.31, "slope": 28.95, "footslope": 7.63}


def geomorphons(h, metres_per_cell=1.0, search=3, flat_deg=1.0):
    """Jasiewicz & Stepinski's landforms: per cell, in 8 directions, the zenith and nadir
    angles over `search` cells; each direction becomes +1 / 0 / -1 against the flatness
    threshold; the counts of pluses and minuses pick one of 10 classes (GRASS r.geomorphon
    lookup). Returns an int array of class ids (GEOMORPHON_NAMES order)."""
    n, m = h.shape
    hc = h / float(metres_per_cell)                   # heights in cell units
    flat = math.radians(flat_deg)
    plus = np.zeros((n, m), dtype=np.int8); minus = np.zeros((n, m), dtype=np.int8)
    padded = np.pad(hc, search, mode="edge")
    for di, dj in te.D8:
        zen = np.full((n, m), -np.inf); nad = np.full((n, m), np.inf)
        for L in range(1, search + 1):
            nb = padded[search + di * L:search + di * L + n, search + dj * L:search + dj * L + m]
            dist = L * math.hypot(di, dj)
            ang = np.arctan((nb - hc) / dist)
            zen = np.maximum(zen, ang); nad = np.minimum(nad, ang)
        # the "ternary" element: + if the horizon rises above flat, - if the nadir drops below
        up = zen > flat; down = (-nad) > flat
        plus += (up & ~(down & (-nad > zen))).astype(np.int8)
        minus += (down & ~(up & (zen >= -nad))).astype(np.int8)
    # the lookup table of r.geomorphon (rows: number of minuses 0..8, cols: number of pluses 0..8)
    FL, PK, RI, SH, SP, SL, HL, FS, VL, PT = range(10)
    table = [
        [FL, FL, FL, FS, FS, VL, VL, VL, PT],
        [FL, FL, FS, FS, FS, VL, VL, VL, -1],
        [FL, SH, SL, SL, HL, HL, VL, -1, -1],
        [SH, SH, SL, SL, SL, HL, -1, -1, -1],
        [SH, SH, SP, SL, SL, -1, -1, -1, -1],
        [RI, RI, SP, SP, -1, -1, -1, -1, -1],
        [RI, RI, RI, -1, -1, -1, -1, -1, -1],
        [RI, RI, -1, -1, -1, -1, -1, -1, -1],
        [PK, -1, -1, -1, -1, -1, -1, -1, -1],
    ]
    cls = np.zeros((n, m), dtype=np.int8)
    for mi in range(9):
        for pl in range(9 - mi):
            sel = (minus == mi) & (plus == pl)
            cls[sel] = table[mi][pl] if table[mi][pl] >= 0 else SL
    return cls


def geomorphon_fractions(cls):
    counts = np.bincount(cls.ravel(), minlength=10).astype(np.float64)
    return counts / counts.sum()


def ptrm(fractions):
    """Rajasekaran et al.'s regression, with the 10 fractions as percentages (the paper's
    scaling could not be reproduced exactly from the available text: treat the number as a
    RELATIVE score, higher = more landform structure, and compare terrains with each other
    and with reference DEMs scored the same way rather than against the paper's 0.76)."""
    f = dict(zip(GEOMORPHON_NAMES, fractions)) if not isinstance(fractions, dict) else fractions
    return (-38.02 + sum(PTRM_W[k] * f[k] * 100.0 for k in PTRM_W)) / 69.96 / 100.0


def landform_share(fractions):
    """valley + ridge + hollow + spur + shoulder + footslope: what real terrain has and noise
    lacks (the PTRM authors' finding); flat and plain slope excluded"""
    f = dict(zip(GEOMORPHON_NAMES, fractions)) if not isinstance(fractions, dict) else fractions
    return float(sum(f[k] for k in ("valley", "ridge", "hollow", "spur", "shoulder", "footslope")))


def psd_slope(h, kmin=4, kmax=None):
    """Radial power spectrum exponent: P(k) ~ k^-beta; natural terrain beta ~ 2."""
    n, m = h.shape
    w = np.hanning(n)[:, None] * np.hanning(m)[None, :]
    F = np.fft.fftshift(np.fft.fft2((h - h.mean()) * w))
    P = np.abs(F) ** 2
    ky, kx = np.mgrid[-n // 2:n // 2, -m // 2:m // 2]
    k = np.hypot(kx, ky).astype(int)
    if kmax is None:
        kmax = min(n, m) // 4
    ks = np.arange(kmin, kmax)
    radial = np.array([P[k == kk].mean() for kk in ks])
    good = radial > 0
    beta, _ = np.polyfit(np.log(ks[good]), np.log(radial[good]), 1)
    return -beta


def slope_stats(h, metres_per_cell):
    gy, gx = np.gradient(h, metres_per_cell)
    deg = np.degrees(np.arctan(np.hypot(gx, gy)))
    hist, _ = np.histogram(deg, bins=36, range=(0, 90))
    return {"mean": float(deg.mean()), "median": float(np.median(deg)), "p90": float(np.percentile(deg, 90)),
            "hist": hist / hist.sum()}


def strahler(h, area_threshold_frac=0.01):
    """Strahler orders over the D8 network of cells with drainage area above the threshold.
    Returns the Horton bifurcation ratio Rb, length ratio Rl, highest order, drainage density."""
    filled = te.fill_depressions(h)
    recv, _ = te.d8_receivers(filled)
    area, order = te.drainage_area(filled, recv)
    n, m = h.shape
    thr = area_threshold_frac * h.size
    chan = area.ravel() >= thr
    so = np.zeros(h.size, dtype=np.int32)              # Strahler order per channel cell
    inflow_max = np.zeros(h.size, dtype=np.int32); inflow_cnt = np.zeros(h.size, dtype=np.int32)
    for c in order:                                   # high to low: upstream first
        if not chan[c]:
            continue
        if inflow_cnt[c] == 0:
            so[c] = 1
        else:
            so[c] = inflow_max[c] + (1 if inflow_cnt[c] >= 2 else 0)
        r = recv[c]
        if r != c and chan[r]:
            if so[c] > inflow_max[r]:
                inflow_max[r] = so[c]; inflow_cnt[r] = 1
            elif so[c] == inflow_max[r]:
                inflow_cnt[r] += 1
    if so.max() < 2:
        return {"rb": float("nan"), "rl": float("nan"), "max_order": int(so.max()), "drainage_density": float(chan.mean())}
    # streams: count segments per order (a segment ends where the order increases), lengths
    counts = {}; lengths = {}
    for c in np.nonzero(chan)[0]:
        o = so[c]
        r = recv[c]
        end = (r == c) or (not chan[r]) or (so[r] != o)
        if end:
            counts[o] = counts.get(o, 0) + 1
        lengths[o] = lengths.get(o, 0.0) + 1.0
    orders = sorted(counts)
    if len(orders) < 2:
        return {"rb": float("nan"), "rl": float("nan"), "max_order": int(so.max()), "drainage_density": float(chan.mean())}
    N = np.array([counts[o] for o in orders], dtype=float)
    Lm = np.array([lengths[o] / counts[o] for o in orders], dtype=float)
    rb = math.exp(-np.polyfit(orders, np.log(N), 1)[0])
    rl = math.exp(np.polyfit(orders, np.log(Lm), 1)[0])
    return {"rb": float(rb), "rl": float(rl), "max_order": int(so.max()), "drainage_density": float(chan.mean())}


def hypsometric_integral(h):
    z = (h - h.min()) / max(h.max() - h.min(), 1e-9)
    return float(z.mean())


def emd(a, b):
    """earth mover's distance between two histograms (same bins), by cumulative sums"""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    a = a / a.sum(); b = b / b.sum()
    return float(np.abs(np.cumsum(a) - np.cumsum(b)).sum())


def score(h, metres_per_cell=1.0):
    h = np.asarray(h, dtype=np.float64)
    cls = geomorphons(h, metres_per_cell)
    frac = geomorphon_fractions(cls)
    s = {
        "ptrm": ptrm(frac),
        "landform_share": landform_share(frac),
        "geomorphons": dict(zip(GEOMORPHON_NAMES, [float(x) for x in frac])),
        "geomorphon_hist": frac,
        "psd_slope": float(psd_slope(h)),
        "slope_deg": slope_stats(h, metres_per_cell),
        "hypsometric": hypsometric_integral(h),
        "relief_m": float(h.max() - h.min()),
    }
    s.update({"horton_" + k if k in ("rb", "rl") else k: v for k, v in strahler(h).items()})
    return s


def report(s, log=print):
    g = s["geomorphons"]
    log("PTRM (relative)     %.2f   landform share %.2f  (valley+ridge+hollow+spur+shoulder+footslope; compare runs, higher = more real)" % (s["ptrm"], s["landform_share"]))
    log("geomorphons         valley %.2f ridge %.2f hollow %.2f spur %.2f slope %.2f flat %.2f shoulder %.2f footslope %.2f peak %.2f pit %.2f"
        % (g["valley"], g["ridge"], g["hollow"], g["spur"], g["slope"], g["flat"], g["shoulder"], g["footslope"], g["peak"], g["pit"]))
    log("spectrum slope      %.2f   (real 15 m DEMs read 3.7-4.4 with this estimator; fbm gain 0.5 reads 4)" % s["psd_slope"])
    sd = s["slope_deg"]
    log("slope deg           mean %.1f median %.1f p90 %.1f" % (sd["mean"], sd["median"], sd["p90"]))
    log("Horton Rb / Rl      %.2f / %.2f  (3-5 / 1.6-2.4), max order %d, drainage density %.3f" % (s["horton_rb"], s["horton_rl"], s["max_order"], s["drainage_density"]))
    log("hypsometric         %.2f   (0.3-0.6 mature hills)" % s["hypsometric"])
    log("relief              %.0f m" % s["relief_m"])


if __name__ == "__main__":
    print(__doc__)
