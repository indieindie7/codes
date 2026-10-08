"""Offline check of the body blood streaks (the d3d8 layer's streaks.hpp, streaks=1).

Mirrors the layer's maths: U2Streaks::Fill (a source's rivulets from its seed, their lengths
from its age, the drying colour) and the streak pixel shader (rivulets straight down in world
space below each source, wobbling, a bead at each front, the wound's splat, the gates across
and out of the body, the lit colour, the wet highlight, the premultiplied "over" blend). A
cylinder stands in for a body (radius 12, as tall as a soldier), seen from the front with a
light from the upper left; two bleeding points on it, shown at several ages. Two rows: red
(humans) and purple (Seekers).

    py tools/streaks_sim.py [out.png] [width length speed drysecs]

writes tools/streaks_sim.png by default. Keep it in step with streaks.hpp when either changes.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

# streakparams= width length speed drysecs, streakfx= gloss opacity gain reach (the layer's defaults)
PARAMS = [2.5, 40.0, 6.0, 50.0]
FX = [1.0, 0.92, 2.0, 25.0]
REACH_OUT, REACH_IN = 9.0, 14.0

FRESH = [(0.50, 0.03, 0.03), (0.32, 0.06, 0.42)]
DRIED = [(0.17, 0.045, 0.03), (0.12, 0.035, 0.14)]


class Lcg:
    """U2Streaks::Rand: R = R * 1664525 + 1013904223 (32 bits), (R >> 8) / 2^24."""

    def __init__(self, seed):
        self.r = (seed * 2654435761 + 12345) & 0xFFFFFFFF

    def __call__(self):
        self.r = (self.r * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.r >> 8) / 16777216.0


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def fill(src):
    """U2Streaks::Fill: the shader's five registers for one source (a 5x4 array)."""
    W, Len, Speed, Dry = PARAMS[0], PARAMS[1], PARAMS[2], max(PARAMS[3], 1.0)
    age = src["age"]
    strength = min(max(src["str"], 0.0), 1.5)
    str1 = min(strength, 1.0)
    wet = 1 - smooth(Dry * 0.2, Dry, age)
    k = 1 if src["kind"] == 2 else 0
    col = [DRIED[k][c] + (FRESH[k][c] - DRIED[k][c]) * wet for c in range(3)]
    C = np.zeros((5, 4))
    C[0, :3] = src["pos"]
    C[0, 3] = W * 0.9 * (0.6 + 0.4 * str1) * min(age * 4 + 0.3, 1.0)
    n = np.array(src["out"], float)
    n /= max(np.linalg.norm(n), 1e-3)
    C[1] = [n[0], n[1], min(strength * 2, 1.0), wet]
    rnd = Lcg(src["seed"])
    count = 2 if rnd() < 0.5 else 3
    for j in range(3):
        off = (rnd() - 0.5) * W * 0.6 if j == 0 else (rnd() - 0.5) * W * 3.6
        width = W * 0.5 * (0.45 + 0.55 * rnd()) * (0.7 + 0.3 * str1) * (1.3 if j == 0 else 1.0)  # half-width
        delay = j * 0.35 + rnd() * 0.4
        v = Speed * (0.55 + 0.6 * rnd()) * (0.6 + 0.4 * strength)
        mx = Len * (0.45 + 0.55 * rnd()) * (0.5 + 0.5 * strength)
        a = max(age - delay, 0.0)
        length = mx * (1 - math.exp(-v * a / mx)) if mx > 0.1 else 0.0
        if j >= count or a <= 0:
            width = 0.0
        C[2 + j] = [off, width, length, col[j]]
    return C


def sat(x):
    return np.clip(x, 0.0, 1.0)


def wave(x):
    z = np.abs(x - np.floor(x) - 0.5) * 2
    return z * z * (3 - 2 * z) - 0.5


def shade(Wp, N, E, lit, regs):
    """The streak pixel shader over arrays of world positions/normals; returns (rgb premult, K)."""
    cov = np.zeros(Wp.shape[:-1])
    wet = np.zeros_like(cov)
    tot = np.zeros_like(cov)
    col = np.zeros(Wp.shape)
    for C in regs:
        S, A = C[0], C[1]
        D = Wp - S[:3]
        H = -D[..., 2]
        U = D[..., 0] * -A[1] + D[..., 1] * A[0]
        V = D[..., 0] * A[0] + D[..., 1] * A[1]
        gate = sat((FX[3] - np.abs(U)) * 0.25) * sat((V + REACH_IN) * 0.33) * sat((REACH_OUT - V) * 0.33)
        c = sat((S[3] - np.hypot(U, H * 0.8)) * 1.6)
        t = sat(H * 0.1)
        for j in range(3):
            R = C[2 + j]
            ph = R[0] * 0.37 + R[1] * 1.31
            X = U - R[0] * t - (wave(H * 0.045 + ph) * 1.2 + wave(H * 0.13 + ph * 1.7) * 0.5) * R[1] * t
            wd = R[1] * (1 - 0.35 * sat(H / max(R[2], 1.0)))
            line = sat((wd - np.abs(X)) * 1.8) * sat(H * 2 + 1) * sat((R[2] - H) * 2)
            bead = sat((R[1] * 1.25 - np.hypot(X, (H - R[2]) * 0.85)) * 1.8) * sat(R[2] - 0.5)
            c = np.maximum(c, np.maximum(line, bead))
        c = c * gate * A[2]
        cov = np.maximum(cov, c)
        col += c[..., None] * np.array([C[2, 3], C[3, 3], C[4, 3]])
        wet += c * A[3]
        tot += c
    col /= np.maximum(tot, 1e-3)[..., None]
    wet /= np.maximum(tot, 1e-3)
    up = np.array([0.0, 0.0, 1.0])
    Hh = E + up
    Hh /= np.linalg.norm(Hh)
    L = lit @ np.array([0.3, 0.5, 0.2])
    ndh = sat(N @ Hh)
    nde = sat(N @ E)
    spec = (ndh ** 40 * 0.8 + (1 - nde) ** 4 * 0.25) * wet * FX[0] * (L + 0.15)
    rgb = col * lit * FX[2] + spec[..., None]
    K = cov * FX[1]                          # (no fog in the mock)
    K = np.where(cov > 0.004, K, 0.0)        # clip()
    return rgb * K[..., None], K


def render(sources, ppu=6, radius=12.0, height=96.0):
    """The cylinder from the front (orthographic), its skin lit like the game would, streaks over it."""
    w, h = int(2 * (radius + 2) * ppu), int(height * ppu)
    xs = (np.arange(w) + 0.5) / ppu - (radius + 2)
    zs = height - (np.arange(h) + 0.5) / ppu
    X, Z = np.meshgrid(xs, zs)
    inside = np.abs(X) < radius
    Y = -np.sqrt(np.maximum(radius * radius - X * X, 0))
    Wp = np.stack([X, Y, Z], -1)
    N = np.stack([X / radius, Y / radius, np.zeros_like(X)], -1)
    E = np.array([0.0, -1.0, 0.0])
    light = np.array([-0.6, -0.6, 0.5])
    light /= np.linalg.norm(light)
    lam = sat(N @ light)
    lit = np.clip(0.28 + 0.62 * lam, 0, 1)[..., None] * np.array([1.0, 0.97, 0.92])
    # a soldier's uniform, drawn at double brightness like Advent's skins
    stripes = 0.92 + 0.08 * np.sign(np.sin(Z * 0.35))
    base = np.array([0.30, 0.31, 0.27]) * stripes[..., None]
    dest = np.clip(base * lit * 2, 0, 1)
    regs = [fill(s) for s in sources]
    add, K = shade(Wp, N, E, lit, regs)
    out = np.clip(dest * (1 - K[..., None]) + add, 0, 1)
    bg = np.array([0.08, 0.09, 0.1])
    out = np.where(inside[..., None], out, bg)
    return (out * 255 + 0.5).astype(np.uint8)


def sources_at(age, kind):
    # a torso wound on the front, and a shoulder hit round to the side (35 degrees), older by 1.5 s
    a = math.radians(35)
    return [
        {"pos": (0.0, -12.0, 62.0), "out": (0.0, -1.0), "kind": kind, "age": age, "str": 1.0, "seed": 4242 + kind},
        {"pos": (12 * math.sin(a), -12 * math.cos(a), 80.0), "out": (math.sin(a), -math.cos(a)), "kind": kind,
         "age": age + 1.5, "str": 0.6, "seed": 917 + kind},
    ]


def main():
    out = os.path.join(HERE, "streaks_sim.png")
    args = sys.argv[1:]
    if args and not args[0].replace(".", "").isdigit():
        out = args.pop(0)
    for i, a in enumerate(args[:4]):
        PARAMS[i] = float(a)
    ages = [0.3, 2, 6, 12, 30, 55]
    rows = []
    for kind in (1, 2):
        rows.append([render(sources_at(t, kind)) for t in ages])
    tw, th = rows[0][0].shape[1], rows[0][0].shape[0]
    pad, label = 8, 18
    img = Image.new("RGB", (len(ages) * (tw + pad) + pad, len(rows) * (th + pad + label) + pad), (20, 20, 22))
    d = ImageDraw.Draw(img)
    for r, row in enumerate(rows):
        for c, tile in enumerate(row):
            x, y = pad + c * (tw + pad), pad + r * (th + pad + label)
            d.text((x + 2, y), "%s %gs" % ("red" if r == 0 else "purple", ages[c]), fill=(220, 220, 220))
            img.paste(Image.fromarray(tile), (x, y + label))
    img.save(out)
    print("wrote", out, "(params %s)" % " ".join("%g" % p for p in PARAMS))


if __name__ == "__main__":
    main()
