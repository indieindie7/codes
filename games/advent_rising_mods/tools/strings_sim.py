"""Offline check of the goo strings (the d3d8 layer's strings.hpp, strings=1).

Mirrors the layer's maths: U2Strings::Spring (the sag under gravity from the slack, the middle on
a damped spring after it), Whole (the curve, the stretch thinning with a neck, the blobs at the
ends, the thin middle letting light through), Halves (after the snap: each half whips back, falls
to hang, shortens to a stub, a bead swells at its tip and drops fall) and the pixel shader (a wet
cylinder by the across coordinate: body, specular stripe, rim, translucency), and ModGore's
snap rule (past rest x limit, or old). The stump end stays put; the severed piece is thrown off
it and lands on a floor, the string pulling on it (GooPull) as ModGore does, seen from the side.

    py tools/strings_sim.py [out.png] [thickness sag stretch life]

writes tools/strings_sim.png by default: a strip of frames over time (the time under each).
Keep it in step with strings.hpp and ModGore.SendGoo when either changes.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

PARAMS = [1.0, 1.0, 1.0, 1.0]        # stringparams= thickness sag stretch life
FX = [0.55, 1.0, 0.9, 0.5]           # stringfx= light gloss opacity rim
SEGS, BEAD_SEGS, GRAVITY = 16, 6, 950.0
RED = (0.46, 0.03, 0.03)

# the scene (world units): ModGore's defaults for one string from a stump to a thrown piece
REST, LIMIT, LIFE, THICK, PULL, DANGLE = 24.0, 2.4, 9.0, 0.9 * 1.1, 8.0, 3.2
THROW = np.array([90.0, 0.0, 60.0])
FLOOR = -60.0
TIMES = [0.0, 0.08, 0.16, 0.24, 0.32, 0.4, 0.5, 0.65, 0.85, 1.1, 1.5, 2.0, 2.6, 3.1]

SCALE, W, H = 3.0, 300, 330           # pixels per unit, one frame
ORIGIN = (70, 110)                    # where the stump end is drawn


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Goo:
    """One string as the layer keeps it (U2Strings::Str)."""

    def __init__(self, a, b, rest, thick):
        self.a, self.b, self.rest, self.thick = a, b, rest, thick
        self.init = self.snapped = False
        self.m = self.v = self.t = None
        self.half = [0.0, 0.0]
        self.dir = [None, None]

    def spring(self, dt):
        d = self.b - self.a
        chord = float(np.linalg.norm(d))
        u = d / chord if chord > 0.01 else np.array([1.0, 0, 0])
        mid = (self.a + self.b) * 0.5
        strand = self.rest * 1.08
        slack = max(strand - chord, 0.0)
        sag = math.sqrt(3 * chord * slack / 8 + slack * slack / 4)
        sag = min(sag, strand * 0.5)
        sag = max(sag, 0.03 * chord)
        sag *= PARAMS[1]
        g = np.array([u[2] * u[0], u[2] * u[1], -1 + u[2] * u[2]])
        tgt = mid + g * sag
        if not self.init:
            self.init = True
            self.m, self.v, self.t = tgt.copy(), np.zeros(3), tgt.copy()
            return chord, mid
        k, damp = 190.0, 5.0
        steps = int(math.ceil(dt / 0.0125)) if dt > 0.0125 else 1
        h = dt / steps
        tv = (tgt - self.t) / dt if dt > 1e-4 else np.zeros(3)
        for i in range(steps):
            f = (i + 1) / steps
            tc = self.t + (tgt - self.t) * f
            self.v = self.v + (k * (tc - self.m) - damp * (self.v - tv)) * h
            self.m = self.m + self.v * h
        self.t = tgt
        off = self.m - tgt
        lim, lo = chord * 0.5 + 4, float(np.linalg.norm(off))
        if lo > lim:
            self.m = tgt + off * lim / lo
            self.v = self.v * 0.5
        return chord, mid

    def whole(self, chord, mid, age):
        stretch = chord / self.rest
        r0 = self.thick * PARAMS[0] * (1 / math.sqrt(stretch) if stretch > 1 else 1.0)
        neck = min(max((stretch - 1) * 0.5 * PARAMS[2], 0.0), 0.8)
        bow = self.m - mid
        fade = min(max(age * 8, 0.0), 1.0)
        pts, rad, thin, alpha = [], [], [], []
        for i in range(SEGS + 1):
            t = i / SEGS
            w, sn = 4 * t * (1 - t), math.sin(math.pi * t)
            pts.append(self.a + (self.b - self.a) * t + bow * w)
            blob = 1 + 0.8 * math.exp(-(t / 0.06) ** 2) + 0.8 * math.exp(-((1 - t) / 0.06) ** 2)
            rad.append(r0 * (1 - neck * sn * sn) * blob)
            thin.append(min(max(0.15 + neck * sn * sn / 0.8, 0.0), 1.0))
            alpha.append(fade)
        return [(pts, rad, thin, alpha)]

    def halves(self, chord, s):
        r0 = self.thick * PARAMS[0]
        if not self.snapped:
            self.snapped = True
            hl = min(max(chord * 0.5, 2.0), self.rest * 0.9)
            for h, e in enumerate((self.a, self.b)):
                d = self.m - e
                l = float(np.linalg.norm(d))
                self.dir[h] = d / l if l > 0.01 else np.array([0, 0, -1.0])
                self.half[h] = hl
        life = max(PARAMS[3], 0.1)
        fade = 1 - smooth(2.5 * life, 3.0 * life, s)
        if fade <= 0:
            return []
        stub = 2 + 1.5 * r0
        bend = smooth(0, 0.4 * life, s)
        down = np.array([0, 0, -1.0])
        out = []
        for h, e in enumerate((self.a, self.b)):
            dr = self.dir[h]
            ln = stub + max(self.half[h] - stub, 0.0) * (1 - smooth(0, life, s))
            sw = np.array([-dr[1], dr[0], 0.0])
            swl = float(np.linalg.norm(sw))
            sw = sw / swl if swl > 1e-3 else np.array([1.0, 0, 0])
            swing = math.sin(s * 11 + h * 2.0) * math.exp(-s * 2.5) * 0.3
            pts, rad, thin, alpha = [], [], [], []
            for i in range(SEGS + 1):
                t = i / SEGS
                pts.append(e + ln * (dr * t * (1 - bend) + down * (bend * t + (1 - bend) * 0.35 * t * t) + sw * swing * t * t))
                rad.append(r0 * (1 - 0.55 * t) * (1 + 0.8 * math.exp(-(t / 0.08) ** 2)))
                thin.append(0.2 + 0.4 * t)
                alpha.append(fade)
            out.append((pts, rad, thin, alpha))
            tip = pts[-1]
            rb = r0 * 0.9
            start, period = 0.25 * life, 0.7 * life
            grow = 0.5
            if s > start:
                ph = (s - start) / period + h * 0.37
                f = ph - math.floor(ph)
                grow = f
                tf = f * period
                fall = 0.5 * GRAVITY * tf * tf
                if fall < 300:
                    rd = rb * 0.75
                    c = tip + np.array([0, 0, -rb - fall - rd])
                    out.append(drop(c, rd, 1.0 + min(max(GRAVITY * tf * 0.004, 0.0), 1.5), fade))
            rt = rb * (0.55 + 0.6 * grow)
            out.append(drop(tip + np.array([0, 0, -rt * 0.7]), rt, 1.15, fade))
        return out


def drop(c, r, stretch, alpha):
    pts, rad = [], []
    for k in range(BEAD_SEGS + 1):
        s = -1 + 2.0 * k / BEAD_SEGS
        pts.append(c + np.array([0, 0, -1.0]) * r * stretch * s)
        rad.append(r * math.sqrt(max(1 - s * s, 0.0)))
    return (pts, rad, [0.1] * (BEAD_SEGS + 1), [alpha] * (BEAD_SEGS + 1))


def shade(u, thin, alpha, col):
    """The pixel shader, per pixel (numpy arrays)."""
    u = np.clip(u, -1, 1)
    a = np.abs(u)
    n = np.sqrt(np.clip(1 - u * u, 0, 1))
    edge = np.clip((1 - a) * 5, 0, 1)
    lt = FX[0]
    col = np.array(col)[None, None, :]
    body = col * lt * (0.35 + 0.65 * n)[..., None] + col * lt * 0.8 * (thin * n)[..., None]
    spec = np.clip(1 - np.abs(u + 0.4) * 3, 0, 1) ** 4 * FX[1] * (0.4 + lt)
    rim = np.clip((a - 0.55) * 3, 0, 1) * edge * FX[3] * (0.3 + lt)
    rgb = body + spec[..., None] * np.array([1, 0.92, 0.88]) + rim[..., None] * (col * 2 + 0.15)
    al = FX[2] * (1 - 0.45 * thin) * edge * alpha
    al = np.clip(al + spec * 0.5 * edge * alpha, 0, 1)
    return rgb, al


def to_px(p):
    return ORIGIN[0] + p[0] * SCALE, ORIGIN[1] - p[2] * SCALE


def render(img, strips):
    """Draws ribbons seen from the side (the camera looks along +Y, so a ribbon is as wide as its
    radius across its own tangent): u by the distance from the centre line, as the strip's across
    coordinate, interpolated along each segment."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for pts, rad, thin, alpha in strips:
        P = [to_px(p) for p in pts]
        best_u = np.full((H, W), 9.0, np.float32)
        best_th = np.zeros((H, W), np.float32)
        best_al = np.zeros((H, W), np.float32)
        for i in range(len(P) - 1):
            (x0, y0), (x1, y1) = P[i], P[i + 1]
            dx, dy = x1 - x0, y1 - y0
            ll = dx * dx + dy * dy
            if ll < 1e-6:
                continue
            t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / ll, 0, 1)
            px, py = x0 + dx * t, y0 + dy * t
            # signed distance across (left negative)
            cr = ((xx - x0) * dy - (yy - y0) * dx) / math.sqrt(ll)
            dist = np.hypot(xx - px, yy - py) * np.sign(cr + 1e-9)
            r = (rad[i] + (rad[i + 1] - rad[i]) * t) * SCALE
            u = np.where(r > 1e-3, dist / np.maximum(r, 1e-3), 9.0)
            take = np.abs(u) < np.abs(best_u)
            best_u = np.where(take, u, best_u)
            best_th = np.where(take, thin[i] + (thin[i + 1] - thin[i]) * t, best_th)
            best_al = np.where(take, alpha[i] + (alpha[i + 1] - alpha[i]) * t, best_al)
        inside = np.abs(best_u) < 1
        rgb, al = shade(best_u, best_th, best_al, RED)
        al = np.where(inside, al, 0)[..., None]
        img[:] = img * (1 - al) + rgb * al


def frame(t, goo, pieces, label):
    img = np.zeros((H, W, 3), np.float32)
    img[:] = np.linspace(0.20, 0.12, H)[:, None, None]          # a wall
    fy = int(ORIGIN[1] - FLOOR * SCALE)
    img[fy:, :] = 0.09                                          # the floor
    strips = []
    for g, chord, mid, age, snap in goo:
        if snap is None:
            strips += g.whole(chord, mid, age)
        else:
            strips += g.halves(chord, snap)
    render(img, strips)
    im = Image.fromarray((np.clip(img, 0, 1) ** (1 / 1.4) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    a, b = pieces
    ax, ay = to_px(a)
    bx, by = to_px(b)
    d.ellipse([ax - 9, ay - 9, ax + 9, ay + 9], outline=(150, 150, 150))   # the stump
    d.rectangle([bx - 7, by - 5, bx + 7, by + 5], outline=(150, 150, 150))  # the piece
    d.text((6, H - 16), label, fill=(220, 220, 220))
    return im


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "strings_sim.png")
    for i, v in enumerate(sys.argv[2:6]):
        PARAMS[i] = float(v)
    dt = 1 / 60.0
    a = np.array([0.0, 0, 0])
    b = np.array([4.0, 0, -2])
    vel = THROW.copy()
    g = Goo(a, b, max(float(np.linalg.norm(b - a)), REST), THICK)
    snap_at = None
    frames, t, k = [], 0.0, 0
    while k < len(TIMES):
        # the piece (ModGib: a parabola, it stops on the floor) and ModGore.SendGoo's pull and snap
        d = float(np.linalg.norm(b - a))
        if snap_at is None:
            if d > g.rest * LIMIT or t > LIFE:
                snap_at = t
            elif d > g.rest and b[2] > FLOOR:
                vel = vel + (a - b) / d * PULL * (d - g.rest) * dt
        if b[2] > FLOOR:
            vel = vel + np.array([0, 0, -GRAVITY]) * dt
            b = b + vel * dt
            if b[2] <= FLOOR:
                b[2] = FLOOR
                vel[:] = 0
        g.a, g.b = a, b
        chord, mid = g.spring(dt)
        if t + 1e-6 >= TIMES[k]:
            snap = None if snap_at is None else t - snap_at
            state = "whole" if snap is None else "snapped %.2fs" % snap
            label = "t %.2fs  %s  %.0f/%.0f" % (t, state, chord, g.rest)
            frames.append(frame(t, [(g, chord, mid, t, snap)], (a, b), label))
            k += 1
        t += dt
    cols = 7
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * H), (0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * W, (i // cols) * H))
    sheet.save(out)
    print("wrote", out, "(snapped at %.2f s)" % snap_at if snap_at is not None else "")


if __name__ == "__main__":
    main()
