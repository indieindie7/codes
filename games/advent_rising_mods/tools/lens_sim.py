"""Offline check of the blood drops on the lens (the d3d8 layer's lens.hpp, lens=1).

Mirrors the layer's maths: U2Lens::Splash (how many drops, where, how big, smears), NewFrame
(stick-slip sliding, the trail, the fade) and Fill (the registers), and the lens pixel shader
(per pixel the drop with the most liquid over it: a dome or the thinning trail above it; its
slope bends the sampling of the frame; tint at the thin edge, dark rim, highlight up-left;
blended "over" by its coverage). Over a sample frame: one splash at the edges (the screen-blood
event) and one at a spot (a lensat hit), shown at 0.1, 1, 2.5 and 4 s. Top row red, bottom purple.

    py tools/lens_sim.py [frame.png] [out.png] [strength reach life size]

The default frame is the top-right quarter of research/img/gi_clean.png (an in-game shot);
writes tools/lens_sim.png. Keep it in step with lens.hpp when either changes.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PARAMS = [1.0, 120.0, 4.5, 1.0]   # lensparams= strength reach life size
FX = [1.0, 1.0, 1.0, 1.0]         # lensfx= refraction tint highlight opacity
MAX_DROPS = 6


class Rng:
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def __call__(self):
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) / 16777216.0


def splash(drops, rnd, strength, kind, at=None):
    """U2Lens::Splash"""
    strength *= PARAMS[0]
    if strength <= 0.02:
        return
    strength = min(strength, 1.2)
    n = 1 + int(strength * 3.0 + rnd() * 1.5)
    for _ in range(min(n, 5)):
        pick, oldest = -1, -1.0
        for i, d in enumerate(drops):
            if d is None:
                pick = i
                break
            spent = d['age'] / max(d['life'], 0.1)
            if spent > oldest:
                oldest, pick = spent, i
        d = {}
        if at:
            d['x'] = at[0] + (rnd() - 0.5) * 0.3
            d['y'] = at[1] + (rnd() - 0.5) * 0.3
        else:
            d['x'] = 0.5 + (0.2 + 0.26 * rnd()) * (-1.0 if rnd() < 0.5 else 1.0)
            d['y'] = 0.12 + 0.7 * rnd()
        d['x'] = min(max(d['x'], 0.03), 0.97)
        d['y'] = min(max(d['y'], 0.03), 0.9)
        d['flat'] = rnd() < 0.3
        d['r'] = (0.018 + 0.032 * rnd()) * (0.65 + 0.5 * strength) * (1.5 if d['flat'] else 1.0) * PARAMS[3]
        d['age'] = 0.0
        d['life'] = PARAMS[2] * (0.7 + 0.6 * rnd())
        d['slide'] = 0.004 if d['flat'] else (0.008 + 0.02 * rnd()) * (d['r'] / 0.035)
        d['trail'] = 0.0
        d['str'] = min(strength, 1.0)
        d['phase'] = rnd() * 6.283
        d['kind'] = 2 if kind == 2 else 1
        drops[pick] = d


def step(drops, dt):
    """U2Lens::NewFrame"""
    for i, d in enumerate(drops):
        if d is None:
            continue
        d['age'] += dt
        if d['age'] >= d['life'] or d['y'] > 1.1:
            drops[i] = None
            continue
        go = math.sin(d['age'] * 2.3 + d['phase']) * 0.5 + math.sin(d['age'] * 5.1 + d['phase'] * 1.7) * 0.5
        v = d['slide'] * ((go - 0.2) * 2.5 if go > 0.2 else 0.0) * (1 - 0.6 * d['age'] / d['life'])
        d['y'] += v * dt
        d['trail'] = min(d['trail'] + v * dt, d['r'] * 5)


def registers(drops):
    """U2Lens::Fill: per drop (x, y, r, alpha) (trail in radii, purple, flat, seed)"""
    regs = []
    for d in drops:
        if d is None:
            regs.append(((-10, -10, 0.01, 0), (1, 0, 0, 0)))
            continue
        a_in = d['age'] / 0.06 if d['age'] < 0.06 else 1.0
        left = (d['life'] - d['age']) / (d['life'] * 0.4)
        a_out = min(max(left, 0), 1) if left < 1 else 1.0
        alpha = a_in * a_out * (0.55 + 0.45 * d['str'])
        trail = max(d['trail'], d['r'] * 0.01) / d['r']
        regs.append(((d['x'], d['y'], d['r'], alpha), (trail, 1.0 if d['kind'] == 2 else 0.0, 1.0 if d['flat'] else 0.0, d['phase'])))
    return regs


def sat(x):
    return np.clip(x, 0, 1)


def bilinear(img, u, v):
    h, w, _ = img.shape
    x = np.clip(u * w - 0.5, 0, w - 1)
    y = np.clip(v * h - 0.5, 0, h - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    top = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    bot = img[y1, x0] * (1 - fx) + img[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def shade(frame, regs):
    """the lens pixel shader, then the SRCALPHA / INVSRCALPHA blend"""
    h, w, _ = frame.shape
    aspect = w / h
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    U, V = (u + 0.5) / w, (v + 0.5) / h
    Px, Py = U * aspect, V
    cov = np.zeros((h, w)); H = np.zeros((h, w)); R = np.full((h, w), 0.01)
    Gx = np.zeros((h, w)); Gy = np.zeros((h, w)); Kx = np.zeros((h, w)); Ky = np.zeros((h, w))
    for A, B in regs:
        dx = (Px - A[0] * aspect) / A[2]
        dy = (Py - A[1]) / A[2]
        dx = dx * (1 - B[2] * 0.45)
        hh = 1 - (dx * dx + dy * dy)
        up = -dy / B[0]
        tw = 0.42 - 0.42 * sat(up)
        tr = (0.5 - 0.5 * dx * dx / (tw * tw + 0.0001)) * ((up > 0) & (up < 1))
        hv = np.maximum(hh, tr) * (1 - B[2] * 0.5)
        c = sat(hv * 8) * A[3]
        take = c > cov
        head = hh >= tr
        gx = np.where(head, dx, dx / (tw + 0.01) * 0.3)
        gy = np.where(head, dy, 0.0)
        cov = np.where(take, c, cov); H = np.where(take, hv, H)
        Gx = np.where(take, gx, Gx); Gy = np.where(take, gy, Gy)
        Kx = np.where(take, B[1], Kx); Ky = np.where(take, B[2], Ky); R = np.where(take, A[2], R)
    offx = -Gx * R * FX[0] * (1 - Ky * 0.7)
    offy = -Gy * R * FX[0] * (1 - Ky * 0.7)
    col = bilinear(frame, U + offx / aspect, V + offy)
    tint = np.where(Kx[..., None] > 0.5, np.array([0.62, 0.22, 0.85]), np.array([0.95, 0.12, 0.08]))
    edge = sat(1 - H * 2.2)
    t = (sat(0.3 + 0.6 * edge + Ky * 0.25) * FX[1])[..., None]
    col = col * (1 - t) + (col * tint * 1.6 + tint * 0.04) * t
    col = col * (1 - 0.4 * edge * edge * FX[1])[..., None]
    spec = sat((Gx * -0.55 + Gy * -0.75) * 2 - 1) * (1 - edge) * (1 - Ky) * 0.35 * FX[2]
    col = col + spec[..., None]
    a = (sat(cov * FX[3]) * (cov > 0.003))[..., None]
    return frame * (1 - a) + sat(col) * a


def main():
    args = sys.argv[1:]
    frame_path = args[0] if len(args) > 0 else None
    out = args[1] if len(args) > 1 else os.path.join(HERE, 'lens_sim.png')
    for i, x in enumerate(args[2:6]):
        PARAMS[i] = float(x)
    if frame_path:
        img = Image.open(frame_path).convert('RGB')
    else:
        img = Image.open(os.path.join(ROOT, 'research', 'img', 'gi_clean.png')).convert('RGB')
        W, H = img.size
        img = img.crop((W // 2, 0, W, H // 2))
    img = img.resize((640, 360), Image.BILINEAR)
    frame = np.asarray(img).astype(np.float64) / 255.0
    times = [0.1, 1.0, 2.5, 4.0]
    rows = []
    for kind in (1, 2):
        rnd = Rng(7 + kind * 101)
        drops = [None] * MAX_DROPS
        splash(drops, rnd, 0.75, kind)                 # "lens 0.75 kind": the screen-blood event
        splash(drops, rnd, 0.6, kind, at=(0.62, 0.55))  # "lensat": a hit by the camera, right of centre
        tiles, t, dt = [], 0.0, 1 / 60.0
        for target in times:
            while t < target - 1e-9:
                step(drops, dt)
                t += dt
            res = shade(frame, registers(drops))
            tile = Image.fromarray((res * 255 + 0.5).astype(np.uint8))
            ImageDraw.Draw(tile).text((8, 6), '%s  t=%.1f s' % ('red' if kind == 1 else 'purple', target), fill=(255, 255, 255))
            tiles.append(tile)
        rows.append(tiles)
    tw, th = rows[0][0].size
    sheet = Image.new('RGB', (tw * len(times) + tw, th * 2), (0, 0, 0))
    for r, tiles in enumerate(rows):
        sheet.paste(img, (0, r * th))
        ImageDraw.Draw(sheet).text((8, r * th + 6), 'frame', fill=(255, 255, 255))
        for c, tile in enumerate(tiles):
            sheet.paste(tile, (tw * (c + 1), r * th))
    sheet.save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
