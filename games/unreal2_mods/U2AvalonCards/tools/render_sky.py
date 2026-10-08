r"""A baked storm sky for Avalon (Q34, 2026-10-08; games/research_notes/Realistic clouds and rain, action 1):
an equirectangular panorama of an overcast storm deck at dusk, raymarched offline with the cloud lighting
the research names - Beer-Lambert extinction, Henyey-Greenstein forward scattering (the silver lining toward
the sun), the powder darkening of thin sunward edges - plus dark rain cores, rain shafts hanging under the
deck, and a bright slot at the horizon where the low sun gets under the deck. The game shows it on a dome in
the sky zone while the storm is on (AvalonStorm), so the sky reads as one lit volume instead of grey blobs.

    py tools/render_sky.py <out.tga> [w=2048] [sun=250] [sunel=4] [seed=3] [preview=out.png]

w = width (height = w/4: the upper hemisphere, horizon at the bottom row); sun = the sun's compass yaw in
degrees (Unreal yaw, 0 = +X), sunel = its elevation in degrees.
"""
import os, sys, math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
OUT = sys.argv[1]
W = int(o.get("w", 2048))
H = W // 4
SUN_YAW = math.radians(float(o.get("sun", 250)))
SUN_EL = math.radians(float(o.get("sunel", 4)))
rng = np.random.default_rng(int(o.get("seed", 3)))

# ---- noise: tileable 3D value-noise grids sampled trilinearly (fast with map_coordinates)
G = 64
grids = [rng.random((G, G, G)).astype(np.float32) for _ in range(5)]


def noise3(p, k):
    c = np.stack([np.mod(p[..., i], G) for i in range(3)])
    return map_coordinates(grids[k], c.reshape(3, -1), order=1, mode="wrap").reshape(p.shape[:-1])


def fbm(p, octaves=5, k0=0):
    v, a, f, tot = 0.0, 0.5, 1.0, 0.0
    for i in range(octaves):
        v = v + a * noise3(p * f, (k0 + i) % len(grids))
        tot += a
        a *= 0.5
        f *= 2.03
    return v / tot


# ---- the deck: a slab between BASE and TOP (km), seen from the island (eye at 0.2 km)
BASE, TOP, EYE = 0.9, 2.4, 0.2
SCALE = 1.0 / 1.6                                  # noise cells per km
sun = np.array([math.cos(SUN_EL) * math.cos(SUN_YAW), math.cos(SUN_EL) * math.sin(SUN_YAW), math.sin(SUN_EL)])


def density(p):
    """storm deck density at points p (..., 3) in km"""
    q = p * SCALE
    # an undulating base: lumps and sags under the deck (what gives an overcast its texture from below)
    lump = fbm(q * 1.7 + 41.0, 4, 1)
    h = (p[..., 2] - BASE - (lump - 0.5) * 0.9) / (TOP - BASE)
    warp = fbm(q * 0.5 + 17.0, 3, 2)
    base = fbm(q + warp[..., None] * 2.0, 5, 0)
    # coverage: near-total overcast, thinning far toward the sun so a slot opens under the deck at the horizon
    hd = np.hypot(p[..., 0], p[..., 1])
    toward = (p[..., 0] * sun[0] + p[..., 1] * sun[1]) / np.maximum(hd, 1e-3)
    cover = 0.47 - 0.30 * np.clip((hd - 18) / 22, 0, 1) * np.clip(toward, 0, 1) ** 2
    d = np.clip((base - (1 - cover)) * 7.0, 0, 1)
    # rounded-off bottom, ragged top
    prof = np.clip(h * 6, 0, 1) * np.clip((1 - h) * 2.5, 0, 1)
    return d * prof


# ---- directions of every panorama pixel (upper hemisphere; row H-1 = horizon)
u = (np.arange(W) + 0.5) / W
v = (np.arange(H) + 0.5) / H
yaw = u * 2 * np.pi
el = (1 - v) * (np.pi / 2) * 0.999 + 0.0005
YAW, EL = np.meshgrid(yaw, el)
D = np.stack([np.cos(EL) * np.cos(YAW), np.cos(EL) * np.sin(YAW), np.sin(EL)], -1)

# ray through the slab: from base to top (clamped to 45 km for low rays)
dz = np.maximum(D[..., 2], 0.012)
t0 = (BASE - EYE) / dz
t1 = np.minimum((TOP - EYE) / dz, t0 + 14.0)
far = np.minimum(t0, 60.0)
N = 28
Tr = np.ones((H, W), np.float32)               # transmittance so far
L = np.zeros((H, W), np.float32)               # in-scattered light (luminance)
cos_t = D @ sun
g1, g2 = 0.65, -0.25
hg = lambda g: (1 - g * g) / (4 * np.pi * (1 + g * g - 2 * g * cos_t) ** 1.5)
phase = 0.75 * hg(g1) + 0.25 * hg(g2)
SIGMA = 1.5                                    # extinction per km at density 1 (rain clouds: heavy)
seg = (t1 - t0) / N
for i in range(N):
    t = t0 + (i + 0.5) * seg
    p = D * t[..., None] + np.array([0, 0, EYE])
    dens = density(p)
    # light march toward the sun: 4 steps of 0.35 km
    od = np.zeros_like(dens)
    for j in range(1, 5):
        od += density(p + sun * 0.35 * j) * 0.35
    beer = np.exp(-SIGMA * od)
    powder = 1 - np.exp(-2 * SIGMA * dens * 0.6)
    hgt = np.clip((p[..., 2] - BASE) / (TOP - BASE), 0, 1)
    up = density(p + np.array([0, 0, 0.3])) + density(p + np.array([0, 0, 0.7]))
    amb = (0.18 + 0.40 * hgt) * np.exp(-1.2 * up)   # skylight, occluded by the cloud above
    lit = beer * powder * phase * 9.0 + amb
    ext = dens * SIGMA * seg
    L += Tr * (1 - np.exp(-ext)) * lit
    Tr *= np.exp(-ext)
    print("march %d/%d" % (i + 1, N), end="\r", flush=True)
print()

# ---- colours: dusk storm - blue-grey shadows, warm light; behind the deck a dusk gradient with a hot horizon slot
toward = np.clip(cos_t, -1, 1)
sky_low = np.array([1.00, 0.62, 0.30]) * 1.6
sky_mid = np.array([0.42, 0.40, 0.46])
sky_hi = np.array([0.16, 0.19, 0.27])
e = np.clip(EL / (np.pi / 2), 0, 1)[..., None]
glow = np.clip(toward, 0, 1)[..., None] ** 6
sky = (sky_hi * e + sky_mid * (1 - e)) * (1 - glow) + sky_low * glow
sky = sky * (1 + 2.5 * np.exp(-EL / 0.05)[..., None] * glow)
light_col = np.array([1.0, 0.70, 0.45])        # sun under the deck: warm
shadow_col = np.array([0.30, 0.34, 0.42])      # skylight: cold
warm = np.clip(phase * 6, 0, 1)[..., None]
cloud = L[..., None] * (light_col * warm + shadow_col * (1 - warm)) * 1.4
col = cloud + sky * Tr[..., None]
# atmospheric perspective: low rays sink into the haze (the zone fog's colour)
haze = np.array([0.33, 0.33, 0.37])
hz = np.exp(-EL / 0.07)[..., None] * (1 - glow * 0.6)
col = col * (1 - hz) + haze * hz
# rain shafts: soft vertical streaks hanging under the dark cores, near the horizon
dark = np.clip(1 - L * 3, 0, 1) * (1 - Tr)
shafts = fbm(np.stack([YAW * 30, np.zeros_like(YAW) + 5, np.zeros_like(YAW)], -1), 3, 3)
shafts = np.clip((shafts - 0.5) * 3, 0, 1) * np.exp(-EL / 0.12) * 0.35
col = col * (1 - shafts[..., None]) + haze * 0.7 * shafts[..., None]
col = col * float(o.get("exposure", 1.8))       # in game the storm's gloom darkens it again
col = col / (1 + col)                          # tone map
col = np.clip(col ** (1 / 1.1), 0, 1)
img = Image.fromarray((col * 255).astype("u1"), "RGB")
img.save(OUT)
if "preview" in o:
    img.resize((W // 2, H // 2)).save(o["preview"])
print("sky ->", OUT, img.size)
