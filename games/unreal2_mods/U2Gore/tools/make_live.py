"""U2Gore's placeholders for the d3d8 layer's live blood (fork gi-cascades, blood.hpp pools and runs.hpp wall runs),
and the U2Shaders.ini lines that name them. Ported from the Advent mod's make_blood_live.py / make_blood_runs.py
(ADVENT-GORE-HANDOFF.md): eight 64x64 TGAs per kind, 50% grey (no change under the decals' x2 multiply), with the
slot written in a few pixels so each has its own hash. The marks use different greys from Advent's (125/131 and
124/132) so the two games' hashes never meet.

    py tools/make_live.py            writes Source/U2Gore/Textures/BloodLive0..7.tga, BloodRun0..7.tga and
                                     System/U2Shaders.gore.ini (the lines to merge into the game's U2Shaders.ini)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "advent_rising_mods", "tools"))
from tex_hash import tga_hash                 # noqa: E402
from make_blood_live import write_tga, N      # noqa: E402

TEX = os.path.join(HERE, "..", "Source", "U2Gore", "Textures")
OUT = os.path.join(HERE, "..", "System", "U2Shaders.gore.ini")
SLOTS = 8


def sheet(k, row, lo, hi):
    px = [(128, 128, 128, 0)] * (N * N)
    for bit in range(4):
        v = hi if (k >> bit) & 1 else lo
        for x in range(bit * 4, bit * 4 + 4):
            px[row * N + x] = (v, v, v, 0)
    return px


def main():
    live, run, gloss = [], [], []
    for k in range(SLOTS):
        p = os.path.join(TEX, "BloodLive%d.tga" % k)
        write_tga(p, sheet(k, 0, 125, 131))
        live.append("bloodlive=%08x" % tga_hash(p))
        gloss.append("gloss=%08x blood_gloss.hlsl" % tga_hash(p))
        p = os.path.join(TEX, "BloodRun%d.tga" % k)
        write_tga(p, sheet(k, 1, 124, 132))
        run.append("bloodrun=%08x" % tga_hash(p))
        gloss.append("gloss=%08x blood_gloss.hlsl" % tga_hash(p))
    assert len(set(live + run)) == 2 * SLOTS, "hashes collide"
    lines = ["# U2Gore (tools/make_live.py): GoreLink commands, live pools and wall runs in slot order, wet gloss on them",
             "gorelink=1"] + live + run + gloss
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", newline="\r\n").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
