"""The gib card (ModGibCard): a flat quad that shows a tile of ModGibAtlas (a snapshot of settled
gibs taken from above) lying on the floor, and its soft-edged alpha mask.

    python tools/make_gib_card.py

Writes AdventMod/Meshes/gib_card.ase (a unit quad in the XY plane, both windings) and
AdventMod/Textures/gib_card_mask.tga (white, alpha 1 in the middle fading to 0 at the rim, a
little ragged so the card's edge doesn't read as a circle).

The quad's texture mapping follows the snapshot camera (looking straight down, yaw 0): the
picture's top is world +X and its right is world +Y, so a vertex at (x, y) gets
u = 0.5 + y, v = 0.5 - x.
"""
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_rubble  # noqa: E402

TEX = os.path.join(HERE, "..", "AdventMod", "Textures")


def main():
    n = 4
    verts, uvs, index = [], [], {}
    for j in range(n + 1):
        for i in range(n + 1):
            x, y = i / n - 0.5, j / n - 0.5
            index[(i, j)] = len(verts)
            verts.append((x, y, 0.0))
            uvs.append((0.5 + y, 0.5 - x))
    faces = []
    for j in range(n):
        for i in range(n):
            a, b, c, d = index[(i, j)], index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]
            faces += [(a, b, c), (a, c, d)]
    faces += [(a, c, b) for a, b, c in faces]
    make_rubble.write_ase("gib_card", verts, uvs, faces)

    rng = random.Random(9)
    N = 64
    harm = [(k, rng.uniform(0, 6.3), rng.uniform(0.03, 0.07)) for k in (3, 5, 7, 11)]
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, N, N, 32, 0x08)
    body = bytearray()
    for y in range(N - 1, -1, -1):
        for x in range(N):
            u, v = (x + 0.5) / N - 0.5, (y + 0.5) / N - 0.5
            r = math.hypot(u, v) * 2
            a = math.atan2(v, u)
            edge = 0.92 * (1 + sum(amp * math.sin(a * k + ph) for k, ph, amp in harm))
            t = max(0.0, min(1.0, (edge - r) / 0.35))
            t = t * t * (3 - 2 * t)
            body += bytes((255, 255, 255, int(255 * t)))
    open(os.path.join(TEX, "gib_card_mask.tga"), "wb").write(hdr + body)
    print("gib card mesh and mask written")


if __name__ == "__main__":
    main()
