"""Shaded previews of a heightmap so a result can be judged by eye: hillshade from a low sun,
a second cool fill light from the opposite side, sky occlusion from slope, colour from the
layer masks (or a height tint when there are none).

    import terrain_preview as tp
    rgb = tp.render(h, metres_per_cell, masks=None, sun_az=315, sun_alt=30)   # uint8 (n, m, 3)
    tp.save_png(path, rgb)
    tp.save_png(path, tp.grey(field))                                        # any field, normalised
"""
import math

import numpy as np

COLOURS = {
    "grass": (96, 118, 52), "wet": (58, 62, 48), "scree": (128, 112, 94), "rock": (112, 102, 96),
    "snow": (236, 238, 242), "sand": (190, 170, 120), "soil": (124, 96, 66),
}


def normals(h, mpc):
    gy, gx = np.gradient(np.asarray(h, dtype=np.float64), mpc)
    nx = -gx; ny = -gy; nz = np.ones_like(gx)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / l, ny / l, nz / l


def hillshade(h, mpc, az=315.0, alt=30.0):
    nx, ny, nz = normals(h, mpc)
    a = math.radians(az); e = math.radians(alt)
    lx = math.cos(e) * math.sin(a); ly = -math.cos(e) * math.cos(a); lz = math.sin(e)
    return np.clip(nx * lx + ny * ly + nz * lz, 0, 1)


def cast_shadows(h, mpc, az=315.0, alt=30.0, steps=64):
    """crude ray-marched sun shadow (1 lit, 0 shadowed); steps along the light direction"""
    n, m = h.shape
    a = math.radians(az); e = math.radians(alt)
    dx = math.sin(a); dy = -math.cos(a)
    rise = math.tan(e) * mpc
    lit = np.ones((n, m))
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    hh = np.asarray(h, dtype=np.float64)
    for s in range(1, steps + 1):
        sx = xx + dx * s; sy = yy + dy * s
        ok = (sx >= 0) & (sx < m - 1) & (sy >= 0) & (sy < n - 1)
        x0 = np.clip(sx.astype(int), 0, m - 2); y0 = np.clip(sy.astype(int), 0, n - 2)
        fx = np.clip(sx - x0, 0, 1); fy = np.clip(sy - y0, 0, 1)
        hs = (hh[y0, x0] * (1 - fx) * (1 - fy) + hh[y0, x0 + 1] * fx * (1 - fy) + hh[y0 + 1, x0] * (1 - fx) * fy + hh[y0 + 1, x0 + 1] * fx * fy)
        blocked = ok & (hs > hh + rise * s + 0.01)
        lit = np.where(blocked, 0.0, lit)
    return lit


def grey(a):
    a = np.asarray(a, dtype=np.float64)
    a = (a - a.min()) / max(a.max() - a.min(), 1e-9)
    return (a * 255).astype(np.uint8)


def render(h, mpc, masks=None, sun_az=315.0, sun_alt=30.0, shadows=True, tint=None, zoom=3):
    """zoom: bicubic upsampling of the heights (and masks) before shading, for a readable preview"""
    h = np.asarray(h, dtype=np.float64)
    if zoom and zoom > 1:
        from scipy import ndimage
        h = ndimage.zoom(h, zoom, order=3); mpc = mpc / float(zoom)
        if masks:
            masks = {k: np.clip(ndimage.zoom(np.asarray(v, dtype=np.float64), zoom, order=1), 0, 1) for k, v in masks.items()}
        if tint is not None:
            tint = ndimage.zoom(np.asarray(tint, dtype=np.float64), zoom, order=1)
    n, m = h.shape
    z = (h - h.min()) / max(h.max() - h.min(), 1e-9)
    nx, ny, nz = normals(h, mpc)
    # albedo
    if masks:
        base = np.array(COLOURS["soil"], dtype=np.float64)
        col = np.broadcast_to(base, (n, m, 3)).copy()
        for name in ("grass", "scree", "rock", "wet", "sand", "snow"):
            if name in masks:
                w = np.clip(np.asarray(masks[name], dtype=np.float64), 0, 1)[..., None]
                col = col * (1 - w) + np.array(COLOURS[name], dtype=np.float64) * w
    else:
        low = np.array((88, 112, 56.0)); high = np.array((150, 140, 128.0)); top = np.array((232, 232, 236.0))
        col = low[None, None] * (1 - z[..., None]) + high[None, None] * z[..., None]
        col = col * (1 - np.clip((z[..., None] - 0.8) / 0.2, 0, 1)) + top[None, None] * np.clip((z[..., None] - 0.8) / 0.2, 0, 1)
    if tint is not None:
        col = col * tint[..., None]
    # light: warm sun + cool sky + a dim fill from behind
    sun = hillshade(h, mpc, sun_az, sun_alt)
    if shadows:
        sun = sun * cast_shadows(h, mpc, sun_az, sun_alt)
    sky = 0.5 + 0.5 * nz
    fill = hillshade(h, mpc, sun_az + 180.0, 20.0)
    light = (0.9 * sun[..., None] * np.array((1.05, 0.98, 0.88)) + 0.5 * sky[..., None] * np.array((0.78, 0.86, 1.0)) + 0.15 * fill[..., None] * np.array((0.8, 0.85, 1.0)))
    rgb = 255.0 * np.power(np.clip(col * light / 255.0, 0, 1), 1 / 1.3)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def save_png(path, rgb):
    from PIL import Image
    Image.fromarray(rgb).save(path)


def side_by_side(images, pad=4):
    hgt = max(im.shape[0] for im in images)
    out = []
    for im in images:
        if im.ndim == 2:
            im = np.stack([im] * 3, axis=-1)
        if im.shape[0] < hgt:
            im = np.pad(im, ((0, hgt - im.shape[0]), (0, 0), (0, 0)))
        out.append(im); out.append(np.full((hgt, pad, 3), 255, dtype=np.uint8))
    return np.concatenate(out[:-1], axis=1)
