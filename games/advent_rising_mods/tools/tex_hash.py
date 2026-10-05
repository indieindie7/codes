"""The hash the d3d8 layer (U2Shaders) gives a texture, from the .tga the mod imports it from:
FNV-1a over the first 16384 bytes of the top level as the game holds it (32-bit BGRA, top row
first), seeded with the size. Lets the build write U2Shaders.ini rules (decal=HASH file) for
our own textures without running the game to read the hash off a log.

    python tools/tex_hash.py <a.tga> [b.tga ...]
"""
import struct
import sys


def tga_hash(path):
    d = open(path, "rb").read()
    idlen, _, kind = d[0], d[1], d[2]
    w, h, bpp, desc = struct.unpack_from("<HHBB", d, 12)
    assert kind == 2 and bpp == 32, "uncompressed 32-bit TGAs only"
    px = d[18 + idlen:18 + idlen + w * h * 4]
    rows = [px[y * w * 4:(y + 1) * w * 4] for y in range(h)]
    if not desc & 0x20:
        rows.reverse()                     # stored bottom row first
    data = b"".join(rows)[:16384]
    hsh = (2166136261 ^ w ^ (h << 12)) & 0xFFFFFFFF
    for b in data:
        hsh = ((hsh ^ b) * 16777619) & 0xFFFFFFFF
    return hsh or 1


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("%08x %s" % (tga_hash(p), p))
