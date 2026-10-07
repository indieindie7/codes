"""list a UE2 package's exports (names, classes, groups): py u2pkg.py <file> [filter]; import: u2pkg.load(path) -> [(class, path, size)]"""
import struct, sys


def compact(b, p):
    v = 0
    x = b[p]; p += 1
    neg = x & 0x80
    v = x & 0x3F
    if x & 0x40:
        sh = 6
        while True:
            x = b[p]; p += 1
            v |= (x & 0x7F) << sh
            sh += 7
            if not x & 0x80:
                break
    return (-v if neg else v), p


def load(fn):
    b = open(fn, "rb").read()
    tag, ver, lic, flags, nn, no, en, eo, im, io = struct.unpack_from("<IHHIIIIIII", b, 0)
    names = []
    p = no
    for _ in range(nn):
        if ver >= 64:
            ln, p = compact(b, p)
            s = b[p:p + ln - 1].decode("latin1"); p += ln
        else:
            e = b.index(b"\0", p); s = b[p:e].decode("latin1"); p = e + 1
        p += 4
        names.append(s)
    imps = []
    p = io
    for _ in range(im):
        cp, p = compact(b, p); cn, p = compact(b, p)
        pk = struct.unpack_from("<i", b, p)[0]; p += 4
        on, p = compact(b, p)
        imps.append((names[cn], names[on], pk))
    exps = []
    p = eo
    for _ in range(en):
        ci, p = compact(b, p); si, p = compact(b, p)
        pk = struct.unpack_from("<i", b, p)[0]; p += 4
        on, p = compact(b, p)
        p += 4
        sz, p = compact(b, p)
        if sz > 0:
            _, p = compact(b, p)
        exps.append((ci, names[on], pk, sz))

    def cname(ci):
        if ci < 0:
            return imps[-ci - 1][1]
        if ci > 0:
            return exps[ci - 1][1]
        return "Class"

    def path(i):
        parts = []
        pk = exps[i][2]
        while pk > 0:
            parts.append(exps[pk - 1][1]); pk = exps[pk - 1][2]
        return ".".join(reversed(parts + []))
    out = []
    for i, (ci, n, pk, sz) in enumerate(exps):
        g = path(i)
        out.append((cname(ci), (g + "." if g else "") + n, sz))
    return out


if __name__ == "__main__":
    flt = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    for c, n, sz in load(sys.argv[1]):
        if flt in c.lower() or flt in n.lower():
            print(c, n, sz)
