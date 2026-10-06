"""Placeholder textures for the LIVE blood pools (blood-fluid plan step 2): eight 64x64 TGAs,
50% grey (= no change under the decal's x2 multiply) with a slot number written in a few
pixels so each has its own hash. The d3d8 layer recognises them by hash (bloodlive=HASH lines
in U2Shaders.ini, in slot order) and swaps in a texture it simulates on the CPU (blood.hpp).

    python tools/make_blood_live.py      writes Textures/blood_live0..7.tga and the ini lines
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tex_hash import tga_hash   # noqa: E402

TEX = os.path.join(HERE, "..", "AdventMod", "Textures")
INIS = [os.path.join(HERE, "..", "AdventMod", "System", "U2Shaders.ini"),
        r"H:\SteamLibrary\steamapps\common\Advent Rising\System\U2Shaders.ini"]
N = 64
SLOTS = 8


def write_tga(path, px):
    # bottom row first (descriptor 8), as the game's importer assumes whatever the flag says
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, N, N, 32, 0x08)
    body = bytearray()
    for y in range(N - 1, -1, -1):
        for r, g, b, a in px[y * N:(y + 1) * N]:
            body += bytes((b, g, r, a))
    open(path, "wb").write(hdr + body)


def main():
    rules = []
    for k in range(SLOTS):
        px = [(128, 128, 128, 0)] * (N * N)
        # the slot number in binary along the top row (grey 127 vs 129: invisible, distinct)
        for bit in range(4):
            v = 129 if (k >> bit) & 1 else 127
            for x in range(bit * 4, bit * 4 + 4):
                px[x] = (v, v, v, 0)
        path = os.path.join(TEX, "blood_live%d.tga" % k)
        write_tga(path, px)
        rules.append("bloodlive=%08x" % tga_hash(path))
    assert len(set(rules)) == SLOTS, "hashes collide"
    for ini in INIS:
        if not os.path.exists(ini):
            continue
        s = open(ini, encoding="ascii", errors="replace").read()
        nl = "\r\n" if "\r\n" in s else "\n"
        lines = [l for l in s.splitlines() if not l.startswith("bloodlive=") and l != "# live blood pools (tools/make_blood_live.py): slot order"]
        lines += ["# live blood pools (tools/make_blood_live.py): slot order"] + rules
        open(ini, "w", encoding="ascii", newline=nl).write("\n".join(lines) + "\n")
        print(ini, "updated")
    print("\n".join(rules))


if __name__ == "__main__":
    main()
