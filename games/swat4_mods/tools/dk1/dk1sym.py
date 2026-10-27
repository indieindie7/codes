"""Door Kickers 1 symbols from the shipped DoorKickers.pdb (via dbghelp, read only).

  py -3.13 -I dk1sym.py fn <mask>        functions/data matching mask (e.g. "Human::*AI*"), RVA + size
  py -3.13 -I dk1sym.py type <Name>      struct/class fields: offset, size, name, type
"""
import ctypes as C, ctypes.wintypes as W, sys, os

EXE = r"F:\SteamLibrary\steamapps\common\DoorKickers\DoorKickers.exe"
BASE = 0x10000000
d = C.WinDLL("dbghelp")
h = W.HANDLE(0x1234)
d.SymSetOptions(0x2 | 0x4 | 0x40000)  # UNDNAME | DEFERRED_LOADS | ... (no DEBUG output)
assert d.SymInitializeW(h, W.LPCWSTR(os.path.dirname(EXE)), False)
d.SymLoadModuleExW.restype = C.c_uint64
assert d.SymLoadModuleExW(h, None, W.LPCWSTR(EXE), None, C.c_uint64(BASE), 0x400000, None, 0)


class SYMBOL_INFO(C.Structure):
    _fields_ = [("SizeOfStruct", W.ULONG), ("TypeIndex", W.ULONG), ("Reserved", C.c_uint64 * 2),
                ("Index", W.ULONG), ("Size", W.ULONG), ("ModBase", C.c_uint64), ("Flags", W.ULONG),
                ("Value", C.c_uint64), ("Address", C.c_uint64), ("Register", W.ULONG), ("Scope", W.ULONG),
                ("Tag", W.ULONG), ("NameLen", W.ULONG), ("MaxNameLen", W.ULONG), ("Name", C.c_wchar * 1024)]


CB = C.WINFUNCTYPE(W.BOOL, C.POINTER(SYMBOL_INFO), W.ULONG, C.c_void_p)


def fn(mask):
    out = []
    def cb(p, size, _):
        s = p.contents
        out.append((s.Address - BASE, s.Size, s.Tag, s.Name))
        return True
    d.SymEnumSymbolsW(h, C.c_uint64(BASE), W.LPCWSTR(mask), CB(cb), None)
    for rva, sz, tag, name in sorted(out, key=lambda t: t[3]):
        print(f"{rva:08x} {sz:6d} {'F' if tag == 5 else 'D' if tag == 7 else tag} {name}")


# SymGetTypeInfo request ids
NAME, LEN, TYPE, TYPEID, BASETYPE, OFFSET, COUNT, CHILDCOUNT, FINDCHILDREN, TAG = 1, 2, 3, 4, 5, 10, 12, 13, 7, 0


def ti(tid, req, ctype=C.c_uint64):
    v = ctype()
    return v.value if d.SymGetTypeInfo(h, C.c_uint64(BASE), tid, req, C.byref(v)) else None


def tname(tid):
    p = C.c_wchar_p()
    if d.SymGetTypeInfo(h, C.c_uint64(BASE), tid, NAME, C.byref(p)) and p.value:
        return p.value
    tag = ti(tid, TAG, W.DWORD)
    sub = ti(tid, TYPE, W.DWORD)
    if tag == 14 and sub is not None:  # pointer
        return tname(sub) + "*"
    if tag == 15 and sub is not None:  # array
        return f"{tname(sub)}[{ti(tid, COUNT, W.DWORD)}]"
    if tag == 16:  # base type
        bt, ln = ti(tid, BASETYPE, W.DWORD), ti(tid, LEN)
        return {1: "void", 2: "char", 6: "int", 7: "uint", 8: "float", 10: "bool", 13: "long", 14: "ulong"}.get(bt, f"bt{bt}") + str(8 * (ln or 0))
    return {13: "func"}.get(tag, f"tag{tag}")


def typ(name):
    s = SYMBOL_INFO(); s.SizeOfStruct = 88; s.MaxNameLen = 1024
    if not d.SymGetTypeFromNameW(h, C.c_uint64(BASE), W.LPCWSTR(name), C.byref(s)):
        return print("no type", name)
    tid = s.TypeIndex
    n = ti(tid, CHILDCOUNT, W.DWORD) or 0
    print(f"{name} size {ti(tid, LEN)} children {n}")
    class FC(C.Structure):
        _fields_ = [("Count", W.ULONG), ("Start", W.ULONG), ("ChildId", W.ULONG * n)]
    fc = FC(n, 0)
    d.SymGetTypeInfo(h, C.c_uint64(BASE), tid, FINDCHILDREN, C.byref(fc))
    rows = []
    for c in fc.ChildId:
        tag = ti(c, TAG, W.DWORD)
        p = C.c_wchar_p(); d.SymGetTypeInfo(h, C.c_uint64(BASE), c, NAME, C.byref(p))
        if tag == 7 and ti(c, 8, W.DWORD) == 9:  # DataIsConstant: enum value (VARIANT, value at +8)
            v = (C.c_int32 * 6)()
            d.SymGetTypeInfo(h, C.c_uint64(BASE), c, 11, C.byref(v))
            rows.append((v[2], 0, p.value, "="))
        elif tag == 7:  # data member
            t = ti(c, TYPEID, W.DWORD)
            rows.append((ti(c, OFFSET, W.DWORD), ti(t, LEN), p.value, tname(t)))
        elif tag == 18:  # base class
            rows.append((ti(c, OFFSET, W.DWORD) or 0, ti(c, LEN), "<base>", p.value))
    for o, sz, nm, t in sorted(rows, key=lambda r: (r[0] or 0)):
        print(f"  +{o or 0:#06x} {sz or 0:5d} {nm} : {t}")


def sig(name):
    """Function signature: return type, calling convention, this, args (types only; the PDB has no arg names here)."""
    s = SYMBOL_INFO(); s.SizeOfStruct = 88; s.MaxNameLen = 1024
    if not d.SymFromNameW(h, W.LPCWSTR(name), C.byref(s)):
        return print("no symbol", name)
    ft = s.TypeIndex
    n = ti(ft, CHILDCOUNT, W.DWORD) or 0
    class FC(C.Structure):
        _fields_ = [("Count", W.ULONG), ("Start", W.ULONG), ("ChildId", W.ULONG * n)]
    fc = FC(n, 0)
    d.SymGetTypeInfo(h, C.c_uint64(BASE), ft, FINDCHILDREN, C.byref(fc))
    cc = {0: "cdecl", 7: "stdcall", 11: "thiscall", 4: "fastcall"}.get(ti(ft, 22, W.DWORD))
    this = ti(ft, 23, W.DWORD)  # TI_GET_CLASSPARENTID
    args = [tname(ti(c, TYPE, W.DWORD)) for c in fc.ChildId]
    print(f"{s.Address - BASE:08x} {cc} {tname(ti(ft, TYPE, W.DWORD))} {name}({', '.join(args)})" + (" [this]" if this else ""))


def symat(rva):
    s = SYMBOL_INFO(); s.SizeOfStruct = 88; s.MaxNameLen = 1024
    disp = C.c_uint64()
    if d.SymFromAddrW(h, C.c_uint64(BASE + rva), C.byref(disp), C.byref(s)):
        return s.Name + (f"+{disp.value:#x}" if disp.value else "")
    return None


def dis(name):
    """Disassemble one function (capstone), call/jump targets and globals named from the PDB."""
    import capstone, re, struct
    s = SYMBOL_INFO(); s.SizeOfStruct = 88; s.MaxNameLen = 1024
    if name.startswith("0x"):  # RVA[:size]
        a = name.split(":")
        assert d.SymFromAddrW(h, C.c_uint64(BASE + int(a[0], 16)), C.byref(C.c_uint64()), C.byref(s))
        rva, size = int(a[0], 16), int(a[1], 0) if len(a) > 1 else s.Size - (int(a[0], 16) - (s.Address - BASE))
    else:
        assert d.SymFromNameW(h, W.LPCWSTR(name), C.byref(s)), name
        rva, size = s.Address - BASE, s.Size
    raw = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    nsec, opt = struct.unpack_from("<H", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    ib = struct.unpack_from("<I", raw, pe + 24 + 28)[0]
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vs, va, rs, ro = struct.unpack_from("<IIII", raw, o + 8)
        if va <= rva < va + vs:
            code = raw[ro + rva - va: ro + rva - va + size]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for ins in md.disasm(code, rva):
        note = ""
        for m in re.findall(r"0x[0-9a-f]{5,8}", ins.op_str):
            v = int(m, 16)
            r = v - ib if v >= ib else v
            nm = symat(r)
            if nm:
                note += " ; " + nm
        print(f"{ins.address:08x} {ins.mnemonic} {ins.op_str}{note}")


def xref(name):
    """Callers of one function: every call rel32 in the image that lands on it."""
    import struct
    s = SYMBOL_INFO(); s.SizeOfStruct = 88; s.MaxNameLen = 1024
    assert d.SymFromNameW(h, W.LPCWSTR(name), C.byref(s)), name
    target = s.Address - BASE
    raw = open(EXE, "rb").read()
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    nsec, opt = struct.unpack_from("<H", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vs, va, rs, ro = struct.unpack_from("<IIII", raw, o + 8)
        if not struct.unpack_from("<I", raw, o + 36)[0] & 0x20000000:  # executable sections only
            continue
        sec = raw[ro:ro + rs]
        p = sec.find(b"\xe8")
        while p != -1 and p + 5 <= len(sec):
            if va + p + 5 + struct.unpack_from("<i", sec, p + 1)[0] == target:
                print(f"{va + p:08x} {symat(va + p)}")
            p = sec.find(b"\xe8", p + 1)


if __name__ == "__main__":
    {"fn": fn, "type": typ, "sig": sig, "dis": dis, "xref": xref}[sys.argv[1]](sys.argv[2])
