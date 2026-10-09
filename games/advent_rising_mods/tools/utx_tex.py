"""Advent Rising .utx reader: tagged properties (int32 name refs in this build), UTexture mips
(DXT1/3/5 and RGBA8/L8 through a DDS header for Pillow), and the HWSkinShader* material
graph (Diffuse, Specular = the chrome mask, Opacity/Unlit masks). Derived data only: the PNGs
it writes are game pixels and stay in the scratchpad.

    py -I utx_tex.py <package.utx> <material name> [<material name>...] <out dir>
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\games\advent_rising_mods\tools")
from ukx import Package  # noqa: E402
from PIL import Image  # noqa: E402

SIZES = {0: 1, 1: 2, 2: 4, 3: 12, 4: 16}
FORMATS = {0: "P8", 1: "RGBA7", 2: "RGB16", 3: "DXT1", 4: "RGB8", 5: "RGBA8", 6: "NODATA", 7: "DXT3", 8: "DXT5", 9: "L8", 10: "G16", 11: "RRRGGGBBB"}


def read_props(p, pos):
    """tagged properties -> list of (name, type, value); value is raw for structs/strings"""
    d = p.d
    out = []
    while True:
        name = struct.unpack_from("<i", d, pos)[0]
        pos += 4
        if name == 0:
            break
        info = d[pos]
        pos += 1
        ptype, scode, arr = info & 0xF, (info >> 4) & 7, info & 0x80
        sname = None
        if ptype == 10:
            sname = p.names[struct.unpack_from("<i", d, pos)[0]]
            pos += 4
        if scode in SIZES:
            size = SIZES[scode]
        elif scode == 5:
            size = d[pos]; pos += 1
        elif scode == 6:
            size = struct.unpack_from("<H", d, pos)[0]; pos += 2
        else:
            size = struct.unpack_from("<i", d, pos)[0]; pos += 4
        if ptype == 3:
            out.append((p.names[name], "bool", bool(arr)))   # the value is bit 7; the size byte is 0
            continue
        if arr:
            pos += 1  # array index (small)
        raw = d[pos:pos + size]
        pos += size
        if ptype == 1:
            v = raw[0]
        elif ptype == 2:
            v = struct.unpack("<i", raw)[0]
        elif ptype == 4:
            v = struct.unpack("<f", raw)[0]
        elif ptype == 5:
            v = ("obj", struct.unpack("<i", raw)[0])
        elif ptype == 6:
            v = ("name", p.names[struct.unpack("<i", raw)[0]])
        else:
            v = (sname or "raw", raw.hex())
        out.append((p.names[name], ptype, v))
    return out, pos


def objref(p, ref):
    if ref > 0:
        e = p.exports[ref - 1]
        return e["name"], p.cls(e), e
    if ref < 0:
        imp = p.imports[-ref - 1]
        return imp[3], imp[1], None
    return None, None, None


def export_by_name(p, name):
    for e in p.exports:
        if e["name"].lower() == name.lower():
            return e
    return None


def dds(fourcc, w, h, data, rgb=False, l8=False):
    """a DDS file in memory so Pillow decodes the block formats"""
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | (0x80000 if fourcc else 0x8)
    pf = struct.pack("<II4sIIIII", 32, 0x4 if fourcc else (0x41 if rgb else 0x20000), (fourcc or b"\0\0\0\0"), 0 if fourcc else (32 if rgb else 8),
                     0 if fourcc else (0x00ff0000 if rgb else 0xff), 0 if fourcc else (0x0000ff00 if rgb else 0), 0 if fourcc else (0x000000ff if rgb else 0), 0 if fourcc else (0xff000000 if rgb else 0))
    hdr = b"DDS " + struct.pack("<IIIIIII", 124, flags, h, w, len(data), 0, 0) + b"\0" * 44 + pf + struct.pack("<IIIII", 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + data))


def read_texture(p, e):
    props, pos = read_props(p, e["off"])
    pv = {n: v for n, t, v in props}
    fmt = pv.get("Format", 0)
    d = p.d
    nmips = struct.unpack_from("<i", d, pos)[0]
    pos += 4
    skip, count = struct.unpack_from("<ii", d, pos)
    data = d[pos + 8:pos + 8 + count]
    w, h = struct.unpack_from("<ii", d, skip)
    name = FORMATS.get(fmt, str(fmt))
    if name == "DXT1":
        im = dds(b"DXT1", w, h, data)
    elif name == "DXT3":
        im = dds(b"DXT3", w, h, data)
    elif name == "DXT5":
        im = dds(b"DXT5", w, h, data)
    elif name == "RGBA8":
        im = Image.frombytes("RGBA", (w, h), data, "raw", "BGRA")
    elif name == "L8":
        im = Image.frombytes("L", (w, h), data)
    elif name == "P8":
        im = Image.frombytes("L", (w, h), data)  # palette ignored: the index as grey
    else:
        im = None
    return props, name, w, h, nmips, im


def describe(p, mat, out, depth=0, seen=None):
    seen = seen or set()
    e = export_by_name(p, mat)
    ind = "  " * depth
    if e is None:
        print(ind + "%s: not an export here" % mat)
        return
    cls = p.cls(e)
    if cls == "Texture":
        props, fmt, w, h, nmips, im = read_texture(p, e)
        extra = ", ".join("%s=%s" % (n, v) for n, t, v in props if n not in ("Format", "USize", "VSize", "UBits", "VBits", "UClamp", "VClamp"))
        print(ind + "%s: Texture %s %dx%d, %d mips %s" % (mat, fmt, w, h, nmips, extra))
        if im is not None and out and mat not in seen:
            seen.add(mat)
            im.convert("RGBA").save(os.path.join(out, mat + ".png"))
            if im.mode == "RGBA" and fmt in ("DXT5", "DXT3", "RGBA8"):
                im.getchannel("A").save(os.path.join(out, mat + "_A.png"))
        return
    props, pos = read_props(p, e["off"])
    print(ind + "%s: %s" % (mat, cls))
    for n, t, v in props:
        if isinstance(v, tuple) and v[0] == "obj":
            nm, c, ex = objref(p, v[1])
            print(ind + "  %s -> %s (%s%s)" % (n, nm, c, "" if ex else ", imported"))
            if ex is not None and c in ("Texture", "Shader", "Combiner", "TexEnvMap") or (ex is not None and c.startswith("HWSkin")):
                describe(p, nm, out, depth + 2, seen)
        else:
            print(ind + "  %s = %s" % (n, v))


def main():
    pkg, mats, out = sys.argv[1], sys.argv[2:-1], sys.argv[-1]
    os.makedirs(out, exist_ok=True)
    p = Package(pkg)
    for m in mats:
        describe(p, m, out)
        print()


if __name__ == "__main__":
    main()
