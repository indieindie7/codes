"""Preview renderer for the stage 7 look: our own sheet drawn with a refracted tiled floor,
sky reflection (fresnel), a sun glint, milky water where air is mixed in, foam as lace on the
surface and spray drops. Pure numpy + Pillow, no game assets. It is here to judge the foam and
bubble fields by eye before anything goes into the game's renderer.

render(sheet, spray, t) -> PIL image. The view looks down the +z axis tilted 35 degrees, the sun
low behind the camera on the right. Colours follow a dusk palette (violet sky, warm glint).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SCALE = 6                      # output pixels per cell
RELIEF = 3.0                   # slopes drawn this much steeper so small waves read at this size
CRATE = np.array([0.42, 0.28, 0.16])
DUSK_HI = np.array([0.20, 0.16, 0.42])   # sky overhead (violet)
DUSK_LO = np.array([0.98, 0.52, 0.48])   # sky at the horizon (pink-orange)
SUN = np.array([1.00, 0.80, 0.55])
DEEP = np.array([0.02, 0.10, 0.16])      # what deep water fades to
MILK = np.array([0.55, 0.86, 0.88])      # water full of bubbles
FOAM = np.array([0.96, 0.96, 0.98])
STONE = np.array([0.16, 0.15, 0.20])
SIGMA = np.array([0.030, 0.010, 0.007])  # absorption per unit depth (red goes first)

_rng = np.random.default_rng(7)
_noise_cache = {}


def _up(a, shape):
    """bicubic upsample of a float field to shape (h, w)"""
    img = Image.fromarray(a.astype(np.float32), mode="F")
    return np.asarray(img.resize((shape[1], shape[0]), Image.BICUBIC), dtype=np.float32)


def _value_noise(h, w, cell, seed):
    key = (h, w, cell, seed)
    if key not in _noise_cache:
        r = np.random.default_rng(seed)
        g = r.random((h // cell + 3, w // cell + 3)).astype(np.float32)
        _noise_cache[key] = _up(g, ((h // cell + 3) * cell, (w // cell + 3) * cell))
    return _noise_cache[key]


def _lace(h, w, t):
    """foam lace: two layers of cellular-looking noise drifting slowly against each other"""
    a = _value_noise(h, w, 5, 1)
    b = _value_noise(h, w, 11, 2)
    oa, ob = int(t * 9) % 5, int(t * 5) % 11
    n = 0.6 * a[oa:oa + h, oa:oa + w] + 0.4 * b[ob:ob + h, :w]
    n = np.abs(n - 0.5) * 2          # ridges: bright cell borders like real foam
    return 1 - n


def _floor(h, w):
    """tiled floor albedo with grout lines, in pixel space"""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    t = SCALE * 4
    gx, gy = (x % t) < 1.5, (y % t) < 1.5
    tile = 0.55 + 0.08 * ((np.floor(x / t) + np.floor(y / t)) % 2)
    alb = np.stack([tile * 0.78, tile * 0.80, tile * 0.86], -1)
    alb[gx | gy] *= 0.45
    return alb


def render(s, spray=None, t=0.0, wall=None):
    """s: harness Sheet with foam on; wall: optional bool (h, w) cell mask of walls"""
    dep = s.depth.copy()
    eta = s.eta.copy()
    foam = s.plane("hw_foam").copy()
    air = s.plane("hw_air").copy()
    H, W = dep.shape[0] * SCALE, dep.shape[1] * SCALE
    wet_c = (dep > 0.5).astype(np.float32)
    if wall is None:
        wall = np.zeros_like(dep, dtype=bool)
    # surface fields in pixel space
    E = _up(eta, (H, W))
    D = np.maximum(_up(dep, (H, W)), 0)
    WET = _up(wet_c, (H, W)) > 0.5
    F = np.clip(_up(foam, (H, W)), 0, 1)
    A = np.clip(_up(air, (H, W)), 0, 1)
    px = 20.0 / SCALE                                  # world units per pixel (dx = 20)
    gz, gx = np.gradient(E, px)
    n = np.stack([-gx * RELIEF, np.ones_like(E), -gz * RELIEF], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    v = np.array([0.0, np.cos(np.radians(35)), -np.sin(np.radians(35))])   # towards the camera
    cosv = np.clip((n * v).sum(-1), 0, 1)
    fres = 0.02 + 0.98 * (1 - cosv) ** 5
    # reflected sky
    r = 2 * cosv[..., None] * n - v
    elev = np.clip(r[..., 1], 0, 1)[..., None]
    sky = DUSK_LO + (DUSK_HI - DUSK_LO) * elev ** 0.6
    # sun glint
    l = np.array([0.45, 0.35, -0.82]); l /= np.linalg.norm(l)
    hv = l + v; hv /= np.linalg.norm(hv)
    spec = np.clip((n * hv).sum(-1), 0, 1) ** 400 * 6.0
    # refracted floor, shifted by the surface slope and depth
    alb = _floor(H, W)
    yy, xx = np.mgrid[0:H, 0:W]
    off = 0.35 * D / px
    sx = np.clip((xx - n[..., 0] * off).astype(int), 0, W - 1)
    sy = np.clip((yy - n[..., 2] * off).astype(int), 0, H - 1)
    floor_r = alb[sy, sx]
    lit = 0.35 + 0.65 * np.clip(n[..., 1], 0, 1)[..., None]
    # caustics: brighter where the surface focuses light (negative laplacian of eta)
    lap = np.gradient(gx, px, axis=1) + np.gradient(gz, px, axis=0)
    caus = np.clip(-lap * 40, -0.4, 1.2)[..., None]
    floor_r = floor_r * (lit + 0.5 * caus)
    # through the water: absorption by depth, bubbles turn it milky and shorten the path
    path = D[..., None] * (1 - 0.7 * A[..., None])
    trans = np.exp(-SIGMA * path)
    body = floor_r * trans + DEEP * (1 - trans)
    body = body * (1 - 0.65 * A[..., None]) + MILK * 0.65 * A[..., None] * (0.6 + 0.4 * lit)
    water = body * (1 - fres[..., None]) + sky * fres[..., None] + SUN * spec[..., None]
    # foam: lace whose coverage grows with f, shaded by the wave it sits on
    lace = _lace(H, W, t)
    cov = np.clip((F * 1.25 - (1 - lace)) / 0.18, 0, 1) * np.clip(F * 4, 0, 1)
    cov = np.maximum(cov, np.clip((F - 0.8) / 0.2, 0, 1))
    foam_c = FOAM * (0.55 + 0.45 * np.clip((n * l).sum(-1) * 0.5 + 0.6, 0, 1))[..., None]
    water = water * (1 - cov[..., None]) + foam_c * cov[..., None]
    # dry floor and walls
    img = np.where(WET[..., None], water, alb * 0.95)
    Wm = _up(wall.astype(np.float32), (H, W)) > 0.5
    img[Wm] = STONE
    body = s.plane("hw_body")
    if body.max() > 0:
        img[_up((body > 0).astype(np.float32), (H, W)) > 0.5] = CRATE
    img = np.clip(img, 0, 1) ** (1 / 1.1)
    out = Image.fromarray((img * 255).astype(np.uint8))
    if spray is not None and len(spray):
        lay = Image.new("RGBA", out.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        emean = float(eta[dep > 0.5].mean()) if (dep > 0.5).any() else 0.0
        for x, y, z, vx, vy, vz, age, size in spray:
            cx, cy = x / px, z / px - 0.6 * (y - emean) / px   # height shows as lift on screen
            rad = 0.8 + size * 1.2
            a = int(230 * max(0.0, 1 - age / 1.5))
            dr.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(250, 250, 255, a))
        lay = lay.filter(ImageFilter.GaussianBlur(0.6))
        out = Image.alpha_composite(out.convert("RGBA"), lay).convert("RGB")
    return out
