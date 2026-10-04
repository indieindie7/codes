"""Where a crash happened, from a Windows minidump: the exception code and address,
and the module + offset it falls in (for disassembling that module there).

    python dumpinfo.py <file.dmp>
"""
import struct, sys


def main():
    d = open(sys.argv[1], "rb").read()
    sig, ver, nstreams, rva = struct.unpack_from("<IIII", d, 0)
    mods, exc = [], None
    for i in range(nstreams):
        t, size, off = struct.unpack_from("<III", d, rva + 12 * i)
        if t == 6:
            exc = off
        if t == 4:
            n = struct.unpack_from("<I", d, off)[0]
            for k in range(n):
                base, sz = struct.unpack_from("<QI", d, off + 4 + 108 * k)
                nrva = struct.unpack_from("<I", d, off + 4 + 108 * k + 20)[0]
                ln = struct.unpack_from("<I", d, nrva)[0]
                mods.append((base, sz, d[nrva + 4:nrva + 4 + ln].decode("utf-16le")))
    if exc is None:
        print("no exception stream")
        return
    tid, _, code, flags, rec, addr = struct.unpack_from("<IIIIQQ", d, exc)
    nparams = struct.unpack_from("<I", d, exc + 8 + 24)[0]
    params = struct.unpack_from("<%dQ" % min(nparams, 2), d, exc + 8 + 32) if nparams else ()
    print("code %s at %s params %s" % (hex(code), hex(addr), [hex(p) for p in params]))
    for b, s, n in mods:
        if b <= addr < b + s:
            print("in %s + %s" % (n.split(chr(92))[-1], hex(addr - b)))


if __name__ == "__main__":
    main()
