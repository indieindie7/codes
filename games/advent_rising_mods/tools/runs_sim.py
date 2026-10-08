# offline copy of runs.hpp's drop simulation, to look at the trails without the game
import math, random, sys
import numpy as np
from PIL import Image

N = 128
G = 90.0
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
T = np.zeros((N, N), np.float32)
drops = []
gx, gy = 0.0, 1.0


def dep(x, y, a):
    i, j = int(x), int(y)
    if 0 <= i < N and 0 <= j < N and a > 0:
        T[j, i] += a


def drip(u, v, amount):
    cx, cy = u * N, v * N
    r = 1.5 + 2.0 * amount
    for j in range(int(cy - r - 1), int(cy + r + 2)):
        for i in range(int(cx - r - 1), int(cx + r + 2)):
            d2 = (i + .5 - cx) ** 2 + (j + .5 - cy) ** 2
            if d2 < r * r:
                dep(i, j, 0.5 * amount * (1 - d2 / r / r))
    n = 1 + int(random.random() * min(3.0, 1 + amount * 2))
    for k in range(n):
        off = (random.random() - .5) * r * 1.4
        drops.append([cx + gx * r * .7 - gy * off, cy + gy * r * .7 + gx * off, 0.0, 0.0, amount * (.5 + .6 * random.random()) / n * 8.0, random.random() * 6.28])


def step(dt):
    for P in list(drops):
        x, y, along, side, mass, wob = P
        top = 0.8 + 3.0 * mass          # slower: a run plays out over several seconds
        along = min(top, along + G * dt * min(1, mass * 1.5))
        wob += dt * (3 + random.random() * 4)
        side *= 0.2 ** dt
        across = side + math.sin(wob) * 1.5 * mass
        dx = (gx * along - gy * across) * dt
        dy = (gy * along + gx * across) * dt
        dist = math.hypot(dx, dy)
        leave = min(mass, dist * (0.030 + 0.012 * mass))
        steps = 1 + int(dist)
        for s in range(steps):
            px, py = x + dx * (s + .5) / steps, y + dy * (s + .5) / steps
            w = 1.0 + 1.4 * min(1.0, mass)   # thicker: the trail is as wide as the drop
            lanes = 1 + int(w / 0.7)          # lanes 0.7 cells apart across the width, heavier in the middle
            tot = 0.0
            for k in range(-lanes, lanes + 1):
                tot += 1.0 - 0.6 * abs(k) / lanes
            for k in range(-lanes, lanes + 1):
                o = w * k / lanes
                dep(px - gy * o, py + gx * o, leave / steps * (1.0 - 0.6 * abs(k) / lanes) / tot)
        x += dx; y += dy; mass -= leave
        if mass > .45 and random.random() < dt * .35 * mass:
            part = mass * .35; mass -= part
            drops.append([x, y, 0.0, (-1 if random.random() < .5 else 1) * (1.5 + random.random() * 2.5), part, random.random() * 6.28])
        if mass < .06 or not (0 <= x < N and 0 <= y < N):
            for k in range(4):
                dep(x + (k & 1) * .7, y + (k >> 1) * .7, mass * .25)
            drops.remove(P)
            continue
        P[:] = [x, y, along, side, mass, wob]


def image(Tm):
    cov = np.clip((Tm - .004) / .02, 0, 1); cov = cov * cov * (3 - 2 * cov)
    deep = np.clip(Tm / .3, 0, 1); k = 1 - .55 * deep
    r = 128 * (1 - cov) + 86 * k * cov; g = 128 * (1 - cov) + 12 * k * cov; b = 128 * (1 - cov) + 10 * k * cov
    return np.dstack([r, g, b]).astype(np.uint8)


drip(0.5, 0.2, 1.0)
frames = []
for f in range(60 * 10):
    if f == 30: drip(0.45, 0.22, 0.6)
    step(1 / 60)
    if f + 1 in (60, 180, 300, 480, 600):
        frames.append(image(T.copy()))
img = np.concatenate(frames, 1)
print("max thickness", T.max(), "cells covered", (T > .015).sum(), "drops left", len(drops))
Image.fromarray(img).resize((img.shape[1] * 2, img.shape[0] * 2), Image.NEAREST).save(sys.argv[2] if len(sys.argv) > 2 else 'runs_sim.png')
