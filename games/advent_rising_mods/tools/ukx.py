"""Advent Rising package reader (UE2 build 2226, package version 146, licensee 0xF007).

Differences from stock UE2 found so far:
  - name table entries: int32 length (not a compact index), the string with its null,
    then int32 flags.
  - import entries: 14 bytes, fixed-size ints (no compact indices).
  - export entries: 26 bytes, fixed-size ints (see Package).
Both tables end exactly where the next part of the file starts (checked on humans.ukx).

    python ukx.py <package> [class filter]     lists the exports
"""
import struct, sys


class Reader:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]
        self.p += 2
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def idx(self):
        """FCompactIndex"""
        b0 = self.u8()
        neg = b0 & 0x80
        v = b0 & 0x3F
        if b0 & 0x40:
            shift = 6
            while True:
                b = self.u8()
                v |= (b & 0x7F) << shift
                shift += 7
                if not (b & 0x80):
                    break
        return -v if neg else v


class Package:
    def __init__(self, path):
        self.path = path
        self.d = open(path, "rb").read()
        r = Reader(self.d)
        self.tag = r.u32()
        self.ver = r.u16()
        self.lic = r.u16()
        self.flags = r.u32()
        nc, no, ec, eo, ic, io = (r.u32() for _ in range(6))
        self.names = []
        r.p = no
        for _ in range(nc):
            n = r.i32()
            s = self.d[r.p:r.p + n - 1].decode("latin-1")
            r.p += n
            r.u32()
            self.names.append(s)
        self.imports = []
        r.p = io
        for _ in range(ic):
            # 14 bytes: int32 class package, int32 class name, int16 outer, int32 name
            cpkg = r.i32()
            cls = r.i32()
            outer = struct.unpack_from("<h", self.d, r.p)[0]
            r.p += 2
            name = r.i32()
            self.imports.append((self.names[cpkg], self.names[cls], outer, self.names[name]))
        self.exports = []
        r.p = eo
        for _ in range(ec):
            # 26 bytes: int16 class, int16 super, int16 ?, int16 outer, int16 ?, int32 name,
            # uint32 flags, int32 size, int32 offset
            cls, sup, unk1, outer, unk2 = struct.unpack_from("<hhhhh", self.d, r.p)
            r.p += 10
            name = r.i32()
            oflags = r.u32()
            size = r.i32()
            off = r.i32()
            self.exports.append(dict(cls=cls, sup=sup, outer=outer, unk=(unk1, unk2), name=self.names[name], flags=oflags, size=size, off=off))
        self.end_exports = r.p

    def objname(self, ref):
        if ref < 0:
            return self.imports[-ref - 1][3]
        if ref > 0:
            return self.exports[ref - 1]["name"]
        return "Class"

    def cls(self, e):
        return self.objname(e["cls"])


def main():
    p = Package(sys.argv[1])
    flt = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    print("ver", p.ver, "lic", hex(p.lic), "names", len(p.names), "imports", len(p.imports), "exports", len(p.exports))
    bad = [e for e in p.exports if e["size"] and not (0 < e["off"] < len(p.d) and e["off"] + e["size"] <= len(p.d))]
    print("exports out of file:", len(bad))
    for e in p.exports:
        c = p.cls(e)
        if not flt or flt in c.lower():
            print("%-20s %-40s %8d @ %d" % (c, e["name"], e["size"], e["off"]))


if __name__ == "__main__":
    main()
