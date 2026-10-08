"""Writes terrain_detail.dds: the close-up detail for the terrain shader (terraindetail= in
U2Shaders.ini, read by terrain_src.hlsl on s6). Generated, no game pixels.

512x512, tiling, 32-bit with mips. Each channel is a brightness multiplier around 0.5 (0.5 =
no change), for a different world scale:
  R  fine: sand grain and grit, pebbles a few centimetres across, lit from the terrain relief's
     fixed low sun (terrain_src.hlsl: from (-0.55, -0.4) in world x/y) so they read as bumps;
  G  coarse: fist-sized stones, dried-mud cracks (Voronoi edges) and soft patches.
The shader reads R at the near scale and G at the far one and fades both out with distance.
"""
import os, struct
import numpy as np

N = 512
rng = np.random.default_rng(20261008)
here = os.path.dirname(os.path.abspath(__file__))
L = np.array([-0.55, -0.4, 0.73]); L /= np.linalg.norm(L)


def band_noise(lo, hi):
    """tiling noise with energy between wavelengths N/lo .. N/hi texels (FFT band-pass)"""
    w = rng.standard_normal((N, N))
    f = np.fft.fft2(w)
    ky = np.fft.fftfreq(N)[:, None] * N
    kx = np.fft.fftfreq(N)[None, :] * N
    k = np.sqrt(kx * kx + ky * ky)
    f *= (k >= lo) & (k <= hi)
    n = np.real(np.fft.ifft2(f))
    return (n - n.mean()) / (n.std() + 1e-9)


def stones(count, rmin, rmax):
    """a height field of dome-shaped stones (wrapping), and their footprint"""
    h = np.zeros((N, N))
    yy, xx = np.mgrid[0:N, 0:N]
    for _ in range(count):
        cx, cy = rng.uniform(0, N, 2)
        r = rng.uniform(rmin, rmax)
        sx, sy = rng.uniform(0.7, 1.3, 2)
        dx = (xx - cx + N / 2) % N - N / 2
        dy = (yy - cy + N / 2) % N - N / 2
        d2 = (dx / (r * sx)) ** 2 + (dy / (r * sy)) ** 2
        dome = np.sqrt(np.clip(1 - d2, 0, 1)) * r * 0.6
        h = np.maximum(h, dome)
    return h


def lit(h, gain):
    """the height field shaded by the fixed low sun (Lambert against flat ground = 1)"""
    gy, gx = np.gradient(h)
    n = np.stack([-gx * gain, -gy * gain, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n @ L) / L[2]


def cracks(cells):
    """dark lines along the edges of a wrapping Voronoi diagram"""
    pts = rng.uniform(0, N, (cells, 2))
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    d1 = np.full((N, N), 1e9)
    d2 = np.full((N, N), 1e9)
    for px, py in pts:
        dx = (xx - px + N / 2) % N - N / 2
        dy = (yy - py + N / 2) % N - N / 2
        d = np.sqrt(dx * dx + dy * dy)
        d2 = np.where(d < d1, d1, np.minimum(d2, d))
        d1 = np.minimum(d1, d)
    edge = d2 - d1                                  # 0 on an edge
    return np.exp(-(edge / 1.2) ** 2)


def channel(x, std):
    x = (x - x.mean()) / (x.std() + 1e-9)
    return np.clip(0.5 + x * std, 0, 1)


# R: grit + small pebbles, lit
grit = band_noise(90, 256)
small = stones(900, 2.0, 5.5)
r = 0.55 * grit + 1.6 * (lit(small, 1.2) - 1) + 0.25 * (small > 0)
R = channel(r, 0.11)

# G: stones, cracks, soft patches
big = stones(140, 6.0, 15.0)
cr = cracks(60) * (0.5 + 0.5 * (band_noise(3, 10) > -0.2))   # cracks only in some patches
patch = band_noise(2, 8)
g = 1.2 * (lit(big, 0.9) - 1) - 1.1 * cr + 0.35 * patch + 0.2 * band_noise(40, 120)
G = channel(g, 0.12)
B = np.full((N, N), 0.5)

img = np.stack([R, G, B], -1)


def mips(a):
    out = [a]
    while out[-1].shape[0] > 1:
        m = out[-1]
        m = 0.25 * (m[0::2, 0::2] + m[1::2, 0::2] + m[0::2, 1::2] + m[1::2, 1::2])
        out.append(m)
    return out


levels = mips(img)
hdr = [0] * 32
hdr[0] = 0x20534444
hdr[1] = 124
hdr[2] = 0x1 | 0x2 | 0x4 | 0x1000 | 0x8 | 0x20000      # caps height width pixelformat pitch mipcount
hdr[3] = N
hdr[4] = N
hdr[5] = N * 4
hdr[7] = len(levels)
hdr[19] = 32
hdr[20] = 0x40                                           # RGB
hdr[22] = 32
hdr[23], hdr[24], hdr[25], hdr[26] = 0xFF0000, 0xFF00, 0xFF, 0
hdr[27] = 0x1000 | 0x8 | 0x400000                        # texture, complex, mipmap
with open(os.path.join(here, 'terrain_detail.dds'), 'wb') as f:
    f.write(struct.pack('<32I', *hdr))
    for m in levels:
        b = (np.clip(m, 0, 1) * 255 + 0.5).astype(np.uint8)
        bgra = np.concatenate([b[..., 2:3], b[..., 1:2], b[..., 0:1], np.full(b.shape[:2] + (1,), 255, np.uint8)], -1)
        f.write(bgra.tobytes())
print('wrote terrain_detail.dds', N, 'x', N, len(levels), 'levels')
try:
    from PIL import Image
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(os.path.join(here, 'terrain_detail_preview.png'))
except ImportError:
    pass
