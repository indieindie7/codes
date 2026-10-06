"""Dictionary amplification (Guerin et al. 2016, "Sparse representation of terrains"): the
detail a formed map lacks at 1 to 4 cells is borrowed from a real DEM of the same landform
class. Patch pairs (coarse 8x8, fine residual 16x16) are cut from the reference; every coarse
patch of the map finds its nearest dictionary atoms (orthogonal matching pursuit, sparsity 1
to 3) and the matching fine residuals are blended in with a Hann window.

    import terrain_amplify as ta
    h2 = ta.amplify(h, mpc, ref, ref_mpc, out_factor=1, sparsity=2, strength=1.0)
    # out_factor 1: same grid, the missing 1-2 cell band is added; 2: twice the cells

The reference is resampled to the map's cell size first (upsampling a 15 m DEM to 10 m adds
no real detail, so the honest band is the reference's own: that is what gets transferred).
The residual is scaled by the local slope ratio so flats stay flat and steep ground gets
the rough band. Pure NumPy / SciPy.
"""
import numpy as np
from scipy import ndimage


def _downsample(a, f):
    n, m = a.shape
    n2, m2 = n // f * f, m // f * f
    return a[:n2, :m2].reshape(n2 // f, f, m2 // f, f).mean(axis=(1, 3))


def _upsample(a, f, shape):
    z = ndimage.zoom(a, f, order=3)
    return z[:shape[0], :shape[1]]


def build_dictionary(ref, factor=2, patch=8, count=6000, seed=0):
    """(coarse patches normalised, their std, fine residual patches) from a reference DEM"""
    rng = np.random.default_rng(seed)
    ref = np.asarray(ref, dtype=np.float64)
    low = _downsample(ref, factor)
    high = ref[:low.shape[0] * factor, :low.shape[1] * factor] - _upsample(low, factor, (low.shape[0] * factor, low.shape[1] * factor))
    n, m = low.shape
    P = patch; F = patch * factor
    rs = rng.integers(0, n - P, count); cs = rng.integers(0, m - P, count)
    coarse = np.stack([low[r:r + P, c:c + P] for r, c in zip(rs, cs)])
    fine = np.stack([high[r * factor:r * factor + F, c * factor:c * factor + F] for r, c in zip(rs, cs)])
    mean = coarse.mean(axis=(1, 2), keepdims=True)
    std = coarse.std(axis=(1, 2)) + 1e-6
    coarse = (coarse - mean) / std[:, None, None]
    return coarse.reshape(count, -1), std, fine


def _omp(x, D, sparsity):
    """orthogonal matching pursuit of x on the rows of D (unit-normalised); returns indices and coefficients"""
    Dn = D / (np.linalg.norm(D, axis=1, keepdims=True) + 1e-9)
    resid = x.copy(); chosen = []
    for _ in range(sparsity):
        corr = Dn @ resid
        corr[chosen] = 0
        k = int(np.argmax(np.abs(corr)))
        chosen.append(k)
        A = Dn[chosen].T
        coef, *_ = np.linalg.lstsq(A, x, rcond=None)
        resid = x - A @ coef
    return chosen, coef


def amplify(h, mpc, ref, ref_mpc, out_factor=1, factor=2, patch=8, sparsity=2, strength=1.0, count=6000, seed=0, log=None):
    h = np.asarray(h, dtype=np.float64)
    ref = np.asarray(ref, dtype=np.float64)
    # the reference on the map's cell size
    ref_r = ndimage.zoom(ref, ref_mpc / mpc, order=3) if abs(ref_mpc / mpc - 1) > 0.05 else ref
    D, dstd, fine = build_dictionary(ref_r, factor, patch, count, seed)
    Dn = D / (np.linalg.norm(D, axis=1, keepdims=True) + 1e-9)
    target = ndimage.zoom(h, out_factor, order=3) if out_factor != 1 else h
    low = _downsample(target, factor)
    n, m = low.shape
    P = patch; F = patch * factor
    stride = max(1, P // 2)
    out = np.zeros((n * factor, m * factor)); wsum = np.zeros_like(out)
    win = np.hanning(F + 2)[1:-1]; win = win[:, None] * win[None, :]
    rows = range(0, n - P + 1, stride); cols = range(0, m - P + 1, stride)
    for r in rows:
        if log and r % (stride * 8) == 0:
            log("amplify row %d/%d" % (r, n))
        for c in cols:
            x = low[r:r + P, c:c + P]
            mu = x.mean(); sd = x.std() + 1e-6
            xn = ((x - mu) / sd).ravel()
            if sparsity == 1:
                k = int(np.argmax(Dn @ xn))
                res = fine[k] * (sd / dstd[k])
            else:
                chosen, coef = _omp(xn, D, sparsity)
                res = np.zeros((F, F))
                for k, a in zip(chosen, coef):
                    res += a * fine[k] * (sd / dstd[k])
            out[r * factor:r * factor + F, c * factor:c * factor + F] += res * win
            wsum[r * factor:r * factor + F, c * factor:c * factor + F] += win
    resid = np.where(wsum > 0, out / np.maximum(wsum, 1e-9), 0.0)
    full = np.zeros_like(target)
    full[:resid.shape[0], :resid.shape[1]] = resid
    full = ndimage.gaussian_filter(full, 0.6)
    return target + strength * full


def spectrum_gain(before, after, kmin=8, kmax=48):
    """how much the high band grew: ratio of radial power after / before over kmin..kmax (mean, for a report)"""
    def radial(a):
        n, m = a.shape
        w = np.hanning(n)[:, None] * np.hanning(m)[None, :]
        P = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))) ** 2
        ky, kx = np.mgrid[-n // 2:n // 2, -m // 2:m // 2]
        k = np.hypot(kx, ky).astype(int)
        return np.array([P[k == kk].mean() for kk in range(kmin, kmax)])
    return float(np.mean(radial(after) / np.maximum(radial(before), 1e-12)))
