"""Blood pools that spread like a liquid: a shallow-water simulation run offline, baked into
a sequence of decal textures (Textures\blood_pool_fNN.tga and alien_pool_fNN.tga) that
ModBloodDecal steps through while a pool grows under a body.

The solver is the one Hydrophobia's water uses (games/hydrophobia-water-tech.md): depth +
momentum per cell, HLL fluxes with Toro's wave-speed estimate and Audusse's hydrostatic
reconstruction over an uneven floor, CFL sub-steps; plus a viscous damping so it behaves like
blood, not water. Blood pours in at the centre for the first part of the run, then spreads
and settles. The floor has a little noise and a few bumps, so the edge is irregular and the
pool finds low spots like a real one.

The textures multiply the floor x2 (50% grey = no change, see ModBloodDecal), and the d3d
layer's parallax rule reads darker as deeper: the deep middle of the pool sinks in a little.

    python tools/make_blood_pool.py            (about a minute; writes 2 x FRAMES textures)
"""
import math
import os
import random
import struct

N = 80            # simulation cells across (the texture is 128 px; upsampled)
TEX = 128
FRAMES = 12
G = 3.0           # gravity in sim units
DAMP = 0.5        # viscous damping of the momentum, per second
POUR_UNTIL = 2.6  # seconds of blood pouring in at the centre
POUR_RATE = 3.0   # depth per second added at the centre
DRY = 1e-4
T_END = 14.0
SEED = 7
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "AdventMod", "Textures")


def grid(v=0.0):
    return [[v] * N for _ in range(N)]


def make_bed():
    random.seed(SEED)
    bed = grid()
    # slow noise + a few bumps and a shallow dip, all small against the pool depth
    bumps = [(random.uniform(0.2, 0.8) * N, random.uniform(0.2, 0.8) * N, random.uniform(4, 9), random.uniform(-0.5, 0.7)) for _ in range(10)]
    for y in range(N):
        for x in range(N):
            v = 0.35 * math.sin(x * 0.19 + 1.1) * math.cos(y * 0.23 + 0.3) + 0.22 * math.sin((x + y) * 0.31) + 0.15 * math.sin(x * 0.53 - y * 0.41)
            for bx, by, r, hgt in bumps:
                d2 = (x - bx) ** 2 + (y - by) ** 2
                v += hgt * math.exp(-d2 / (2 * r * r))
            v += random.uniform(-0.02, 0.02)
            bed[y][x] = v
    return bed


def face_flux(hL, hR, uL, uR, vL, vR, bL, bR):
    """HLL flux through one face from state L to R (u is the normal velocity, v tangential)."""
    # hydrostatic reconstruction
    hLs = max(0.0, hL + min(bL - bR, 0.0))
    hRs = max(0.0, hR + min(bR - bL, 0.0))
    cL = math.sqrt(G * hLs)
    cR = math.sqrt(G * hRs)
    us = 0.5 * (uL + uR) + (cL - cR)
    cs = 0.5 * (cL + cR) + 0.25 * (uL - uR)
    sL = min(uL - cL, us - abs(cs), 0.0)
    sR = max(uR + cR, us + abs(cs), 0.0)
    fL = (hLs * uL, hLs * uL * uL + 0.5 * G * hLs * hLs, hLs * uL * vL)
    fR = (hRs * uR, hRs * uR * uR + 0.5 * G * hRs * hRs, hRs * uR * vR)
    qL = (hLs, hLs * uL, hLs * vL)
    qR = (hRs, hRs * uR, hRs * vR)
    den = max(sR - sL, 1e-10)
    f = tuple((sR * fL[i] - sL * fR[i] + sL * sR * (qR[i] - qL[i])) / den for i in range(3))
    # well-balancing source: each side keeps the pressure of the water it lost to the step
    srcL = 0.5 * G * (hL * hL - hLs * hLs)
    srcR = 0.5 * G * (hR * hR - hRs * hRs)
    return f, srcL, srcR


def step(h, mx, my, bed, dt):
    # velocities and the CFL signal speed
    u, v = grid(), grid()
    smax = 1e-6
    for y in range(N):
        for x in range(N):
            d = h[y][x]
            if d > DRY:
                cap = 1000.0 * d
                mx[y][x] = max(-cap, min(cap, mx[y][x]))
                my[y][x] = max(-cap, min(cap, my[y][x]))
                u[y][x] = mx[y][x] / d
                v[y][x] = my[y][x] / d
                smax = max(smax, abs(u[y][x]) + abs(v[y][x]) + math.sqrt(G * d))
            else:
                u[y][x] = v[y][x] = 0.0
                mx[y][x] = my[y][x] = 0.0
    dt = min(dt, 0.45 / smax)
    dh, dmx, dmy = grid(), grid(), grid()
    for y in range(N):
        for x in range(N):
            if x + 1 < N:
                f, sL, sR = face_flux(h[y][x], h[y][x + 1], u[y][x], u[y][x + 1], v[y][x], v[y][x + 1], bed[y][x], bed[y][x + 1])
                dh[y][x] -= f[0]; dh[y][x + 1] += f[0]
                dmx[y][x] -= f[1] - sL; dmx[y][x + 1] += f[1] - sR
                dmy[y][x] -= f[2]; dmy[y][x + 1] += f[2]
            if y + 1 < N:
                f, sL, sR = face_flux(h[y][x], h[y + 1][x], v[y][x], v[y + 1][x], u[y][x], u[y + 1][x], bed[y][x], bed[y + 1][x])
                dh[y][x] -= f[0]; dh[y + 1][x] += f[0]
                dmy[y][x] -= f[1] - sL; dmy[y + 1][x] += f[1] - sR
                dmx[y][x] -= f[2]; dmx[y + 1][x] += f[2]
    damp = math.exp(-DAMP * dt)
    for y in range(N):
        for x in range(N):
            h[y][x] = max(0.0, h[y][x] + dt * dh[y][x])
            mx[y][x] = (mx[y][x] + dt * dmx[y][x]) * damp
            my[y][x] = (my[y][x] + dt * dmy[y][x]) * damp
    return dt


def pour(h, t, dt):
    c = N / 2.0
    for y in range(N):
        for x in range(N):
            d2 = (x - c + 0.5) ** 2 + (y - c + 0.5) ** 2
            if d2 < 25.0:
                h[y][x] += POUR_RATE * dt * (1.0 - d2 / 25.0)


def sample(h, fx, fy):
    """bilinear depth at sim coordinates"""
    x0 = max(0, min(N - 2, int(fx))); y0 = max(0, min(N - 2, int(fy)))
    tx = max(0.0, min(1.0, fx - x0)); ty = max(0.0, min(1.0, fy - y0))
    a = h[y0][x0] * (1 - tx) + h[y0][x0 + 1] * tx
    b = h[y0 + 1][x0] * (1 - tx) + h[y0 + 1][x0 + 1] * tx
    return a * (1 - ty) + b * ty


def write_tga(path, pixels):
    """pixels: TEX*TEX list of (r,g,b,a), top row first"""
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, TEX, TEX, 32, 0x28)
    body = bytearray()
    for r, g, b, a in pixels:
        body += bytes((b, g, r, a))
    with open(path, "wb") as f:
        f.write(hdr + body)


def bake(h, dmax, colour, path):
    """colour: the blood's rgb at its lightest (thin); it darkens with depth"""
    px = []
    scale = N / float(TEX)
    for ty in range(TEX):
        for tx in range(TEX):
            d = sample(h, (tx + 0.5) * scale - 0.5, (ty + 0.5) * scale - 0.5)
            cov = max(0.0, min(1.0, (d - 0.01) / 0.03))        # the edge: a thin rim fades in quickly
            cov = cov * cov * (3 - 2 * cov)
            deep = max(0.0, min(1.0, d / dmax))
            k = 1.0 - 0.45 * deep                                # deeper = darker (parallax reads it as depth)
            r = int(round(128 * (1 - cov) + colour[0] * k * cov))
            g = int(round(128 * (1 - cov) + colour[1] * k * cov))
            b = int(round(128 * (1 - cov) + colour[2] * k * cov))
            px.append((r, g, b, int(round(250 * cov))))
    write_tga(path, px)


def main():
    bed = make_bed()
    h, mx, my = grid(), grid(), grid()
    t = 0.0
    # frames spaced so the fast early growth gets as many as the slow settling
    times = [T_END * (i / (FRAMES - 1.0)) ** 1.6 for i in range(FRAMES)]
    times[0] = 0.15
    frames = []
    for i, tf in enumerate(times):
        while t < tf:
            dt = min(0.05, tf - t)
            if t < POUR_UNTIL:
                pour(h, t, dt)
            dt = step(h, mx, my, bed, dt)
            t += dt
        frames.append([row[:] for row in h])
        wet = sum(1 for row in h for d in row if d > 0.01)
        print("frame %2d t %.2f wet cells %4d (%.0f%% of the grid) max depth %.3f" % (i, t, wet, 100.0 * wet / (N * N), max(max(row) for row in h)))
    dmax = max(max(max(row) for row in f) for f in frames) * 0.8
    for i, f in enumerate(frames):
        bake(f, dmax, (76, 16, 13), os.path.join(OUT, "blood_pool_f%02d.tga" % i))
        bake(f, dmax, (70, 24, 108), os.path.join(OUT, "alien_pool_f%02d.tga" % i))
    print("wrote %d x 2 textures to %s" % (FRAMES, OUT))


if __name__ == "__main__":
    main()
