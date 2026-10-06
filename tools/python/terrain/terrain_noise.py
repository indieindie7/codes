"""Noise for terrain: used only for roughness inside the uplift field and for detail after the
solver, never for the layout (report: Terrain generation methods for the pipeline, step 5).

    import terrain_noise as tn
    n = tn.fbm((256, 256), freq=4, octaves=7, gain=0.707, seed=1)        # beta ~ 2 at gain 0.707
    r = tn.fbm(shape, kind="ridged")                                       # ridged multifractal (Musgrave)
    s = tn.fbm(shape, kind="swiss", warp=0.15)                             # de Carpentier's swiss turbulence
    f = tn.fft_noise(shape, beta=2.0, seed=1)                              # exact spectral exponent
    t = tn.terrace(h, step=0.1, sharpness=0.7)                             # strata shelves

Gradient noise with analytic derivatives (quintic fade), domain rotated ~30 degrees per octave
so the lattice never lines up across octaves. Values roughly in -1..1 (fbm normalised).
Measured with terrain_score.psd_slope at 256 cells: fbm gain 0.5 reads beta 4.0, gain 0.707
reads 3.0, fft_noise(beta=2) reads 1.8 (the estimator is calibrated on spectral synthesis, so
use fft_noise when the exponent matters; fbm is for roughness with derivatives).
"""
import math

import numpy as np


def _hash(ix, iy, seed):
    """lattice hash to a gradient angle; uint32 arithmetic with wraparound"""
    ix = ix.astype(np.uint32); iy = iy.astype(np.uint32)
    h = ix * np.uint32(374761393) + iy * np.uint32(668265263) + np.uint32(seed * 1013904223 & 0xFFFFFFFF)
    h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
    h = h ^ (h >> np.uint32(16))
    return (h.astype(np.float64) / 4294967296.0) * 2.0 * math.pi


def gradient_noise(x, y, seed=0):
    """Perlin-style gradient noise at float coordinates x, y (arrays). Returns value, d/dx, d/dy."""
    ix = np.floor(x); iy = np.floor(y)
    fx = x - ix; fy = y - iy
    # quintic fade and its derivative
    ux = fx * fx * fx * (fx * (fx * 6 - 15) + 10); uy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    dux = 30 * fx * fx * (fx * (fx - 2) + 1); duy = 30 * fy * fy * (fy * (fy - 2) + 1)
    ix = ix.astype(np.int64); iy = iy.astype(np.int64)

    def corner(ox, oy):
        a = _hash(ix + ox, iy + oy, seed)
        gx = np.cos(a); gy = np.sin(a)
        dx = fx - ox; dy = fy - oy
        return gx * dx + gy * dy, gx, gy

    n00, g00x, g00y = corner(0, 0); n10, g10x, g10y = corner(1, 0)
    n01, g01x, g01y = corner(0, 1); n11, g11x, g11y = corner(1, 1)
    # bilinear in the faded coordinates
    a = n00; b = n10 - n00; c = n01 - n00; d = n11 - n10 - n01 + n00
    v = a + b * ux + c * uy + d * ux * uy
    # derivatives: d/dx of the dot products is the gradient x, plus the fade derivative terms
    dvx = (g00x + (g10x - g00x) * ux + (g01x - g00x) * uy + (g11x - g10x - g01x + g00x) * ux * uy) + dux * (b + d * uy)
    dvy = (g00y + (g10y - g00y) * ux + (g01y - g00y) * uy + (g11y - g10y - g01y + g00y) * ux * uy) + duy * (c + d * ux)
    return v * 1.4, dvx * 1.4, dvy * 1.4


def fbm(shape, freq=4.0, octaves=7, gain=0.707, lacunarity=2.0, seed=0, kind="fbm", rotate_deg=30.0,
        offset=1.0, warp=0.15, damp=0.5, normalise=True):
    """Fractional sum of gradient noise over `shape` cells.
    kind: fbm | billow (|n|) | ridged (Musgrave: (offset - |n|)^2 weighted by the previous octave)
          | swiss (de Carpentier: ridged, domain warped by the summed derivatives)
          | damped (iq: each octave scaled by 1 / (1 + damp * |grad so far|^2): smooth valleys)"""
    n, m = shape
    ys, xs = np.mgrid[0:n, 0:m]
    px = xs / float(m) * freq; py = ys / float(n) * freq
    total = np.zeros(shape); amp = 1.0; weight = np.ones(shape)
    dsx = np.zeros(shape); dsy = np.zeros(shape)
    ang = 0.0
    for o in range(octaves):
        c, s = math.cos(ang), math.sin(ang)
        qx = c * px - s * py; qy = s * px + c * py
        if kind == "swiss":
            qx = qx + warp * dsx; qy = qy + warp * dsy
        v, dx, dy = gradient_noise(qx + 7.3 * o, qy + 3.1 * o, seed + o)
        if kind == "billow":
            v = np.abs(v)
        elif kind in ("ridged", "swiss"):
            sign = np.sign(v)
            v = offset - np.abs(v); dx = -sign * dx; dy = -sign * dy
            v = v * v * weight
            weight = np.clip(v * 2.0, 0, 1)
        elif kind == "damped":
            dsx += dx; dsy += dy
            v = v / (1.0 + damp * (dsx * dsx + dsy * dsy))
        if kind == "swiss":
            dsx += amp * dx * 0.5; dsy += amp * dy * 0.5
        total += amp * v
        amp *= gain
        px *= lacunarity; py *= lacunarity
        ang += math.radians(rotate_deg)
    if normalise:
        total = (total - total.mean()) / max(total.std(), 1e-9)
    return total


def fft_noise(shape, beta=2.0, seed=0, kmin=1.0):
    """Gaussian random field with radial power spectrum P(k) ~ k^-beta (natural terrain: beta
    about 2). Normalised to unit standard deviation."""
    n, m = shape
    rng = np.random.default_rng(seed)
    white = np.fft.fft2(rng.standard_normal(shape))
    ky = np.fft.fftfreq(n)[:, None] * n; kx = np.fft.fftfreq(m)[None, :] * m
    k = np.hypot(kx, ky)
    filt = np.where(k >= kmin, np.power(np.maximum(k, kmin), -beta / 2.0), 0.0)
    f = np.real(np.fft.ifft2(white * filt))
    return (f - f.mean()) / max(f.std(), 1e-9)


def terrace(h, step, sharpness=0.6, strength=1.0):
    """Strata shelves: pull heights toward the nearest multiple of `step` (sharpness 0..1, the
    fraction of each step that is near-flat). strength blends the effect."""
    t = h / step
    f = t - np.floor(t)
    k = max(1e-3, 1.0 - sharpness)
    g = np.clip((f - 0.5 * (1 - k)) / k, 0, 1)
    g = g * g * (3 - 2 * g)
    shelved = (np.floor(t) + g) * step
    return h + strength * (shelved - h)


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / max(hi - lo, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)
