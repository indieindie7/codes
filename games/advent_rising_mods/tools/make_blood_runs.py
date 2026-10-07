"""Placeholder textures for blood running down walls (the d3d8 layer's runs.hpp): eight 64x64 TGAs,
50% grey (= no change under the decal's x2 multiply) with the slot number written in a few
pixels of the second row (the live pools' placeholders use the first), so each has its own hash.
The layer recognises them by hash (bloodrun=HASH lines in U2Shaders.ini, in slot order) and
swaps in the sheet it simulates; gloss= lines give the trails the wet blood shader.

    python tools/make_blood_runs.py      writes Textures/blood_run0..7.tga and the ini lines
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tex_hash import tga_hash               # noqa: E402
from make_blood_live import write_tga, N, TEX, INIS   # noqa: E402

SLOTS = 8
HEAD = "# wall blood runs (tools/make_blood_runs.py): slot order, and the wet shader on them"


def main():
    rules, gloss = [], []
    for k in range(SLOTS):
        px = [(128, 128, 128, 0)] * (N * N)
        for bit in range(4):
            v = 130 if (k >> bit) & 1 else 126
            for x in range(bit * 4, bit * 4 + 4):
                px[N + x] = (v, v, v, 0)
        path = os.path.join(TEX, "blood_run%d.tga" % k)
        write_tga(path, px)
        h = tga_hash(path)
        rules.append("bloodrun=%08x" % h)
        gloss.append("gloss=%08x blood_gloss.hlsl" % h)
    assert len(set(rules)) == SLOTS, "hashes collide"
    for ini in INIS:
        if not os.path.exists(ini):
            continue
        s = open(ini, encoding="ascii", errors="replace").read()
        nl = "\r\n" if "\r\n" in s else "\n"
        keep = [l for l in s.splitlines() if not l.startswith("bloodrun=") and l != HEAD and l not in gloss]
        open(ini, "w", encoding="ascii", newline=nl).write("\n".join(keep + [HEAD] + rules + gloss) + "\n")
        print(ini, "updated")
    print("\n".join(rules))


if __name__ == "__main__":
    main()
