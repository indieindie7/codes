"""U2MovementFix - undo SOverhaul's movement changes in Unreal II: The Awakening.

SOverhaul (SkacikPL) changes two things about how the player moves:
  1. U2PlayerSP.GroundSpeed 263 -> 1000 (the player runs ~3.8x faster). Unreal's
     collision is resolved after the move, not predicted, so at that speed the
     player overshoots, snags and pops against geometry.
  2. U2PlayerController.HandleWalking: "walk while Walking (Shift) is held"
     became "walk unless it's held" (Shift turned into a sprint key).

This puts both back to the original game's behaviour by patching the compiled
packages in place (same-size byte patches, nothing else in the files moves):
  System/U2Pawns.u  U2PlayerSP default GroundSpeed 1000.0 -> 263.0
  System/U2.u       HandleWalking  GetRunFlag() < 1  ->  GetRunFlag() > 0
Everything else SOverhaul does (shadows, recoil, HUD, restored weapons...) stays.

    python u2movefix.py            show the current state
    python u2movefix.py apply      patch (backs up to *.before-movefix first)
    python u2movefix.py restore    put SOverhaul's movement back

Close the game first. Saves keep working either way.
"""
import os, shutil, struct, sys

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
ORIGINAL_SPEED = 263.0     # LicenseePawn default, which U2PlayerSP inherited before SOverhaul
SOVERHAUL_SPEED = 1000.0


def compact_index(v):
    """Unreal's compact index encoding."""
    out = bytearray()
    a = abs(v)
    b0 = (0x80 if v < 0 else 0) | (a & 0x3F) | (0x40 if a >= 0x40 else 0)
    out.append(b0)
    a >>= 6
    while a:
        out.append((a & 0x7F) | (0x80 if a >= 0x80 else 0))
        a >>= 7
    return bytes(out)


def read_ci(b, p):
    b0 = b[p]; p += 1
    v = b0 & 0x3F
    if b0 & 0x40:
        shift = 6
        while True:
            bx = b[p]; p += 1
            v |= (bx & 0x7F) << shift; shift += 7
            if not bx & 0x80:
                break
    return (-v if b0 & 0x80 else v), p


def read_tables(data):
    """-> (names, exports) of an Unreal (v68+) package; exports are dicts."""
    tag, ver, lic, flags, nc, no, ec, eo = struct.unpack_from("<IHHIiiii", data, 0)
    assert tag == 0x9E2A83C1, "not an Unreal package"
    names, p = [], no
    for _ in range(nc):
        n, p = read_ci(data, p)
        names.append(data[p:p + n - 1].decode("latin-1"))
        p += n + 4                                  # string, flags
    exports, p = [], eo
    for _ in range(ec):
        cls, p = read_ci(data, p); sup, p = read_ci(data, p)
        outer = struct.unpack_from("<i", data, p)[0]; p += 4
        name, p = read_ci(data, p); p += 4          # object flags
        size, p = read_ci(data, p)
        off = 0
        if size > 0:
            off, p = read_ci(data, p)
        exports.append(dict(name=names[name], outer=outer, off=off, size=size))
    return names, exports


def export_range(data, name, outer):
    """Byte range of the export NAME inside OUTER (a class)."""
    names, exports = read_tables(data)
    for e in exports:
        if e["name"] == name and e["outer"] > 0 and exports[e["outer"] - 1]["name"] == outer:
            return e["off"], e["off"] + e["size"]
    raise SystemExit(f"{outer}.{name} not found")


def class_range(data, name):
    names, exports = read_tables(data)
    for e in exports:
        if e["name"] == name and e["outer"] == 0 and e["size"] > 0:
            return e["off"], e["off"] + e["size"]
    raise SystemExit(f"class {name} not found")


def name_index(data, name):
    names, _ = read_tables(data)
    return names.index(name)


def patches():
    """-> list of (file, (start, end), description, soverhaul_bytes, original_bytes)"""
    pawns = os.path.join(GAME, "System", "U2Pawns.u")
    u2 = os.path.join(GAME, "System", "U2.u")
    d = open(pawns, "rb").read()
    gs = compact_index(name_index(d, "GroundSpeed")) + b"\x24"      # float property, 4 bytes
    speed = (gs + struct.pack("<f", SOVERHAUL_SPEED), gs + struct.pack("<f", ORIGINAL_SPEED))
    speed_at = class_range(d, "U2PlayerSP")
    d = open(u2, "rb").read()
    walk_at = export_range(d, "HandleWalking", "U2PlayerController")
    call = b"\x39\x3a\x1b" + compact_index(name_index(d, "GetRunFlag")) + b"\x16"   # byte(GetRunFlag())
    walk = (b"\x96" + call + b"\x26\x16", b"\x97" + call + b"\x25\x16")             # < 1  vs  > 0
    return [(pawns, speed_at, "player speed (U2PlayerSP.GroundSpeed 1000 -> 263)", *speed),
            (u2, walk_at, "Shift = walk, not sprint (HandleWalking)", *walk)]


def state(data, sov, orig):
    ns, no = data.count(sov), data.count(orig)
    if ns == 1 and no == 0:
        return "soverhaul"
    if no == 1 and ns == 0:
        return "original"
    return f"unknown (soverhaul pattern x{ns}, original pattern x{no})"


def game_running():
    try:
        import subprocess
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return "unreal2.exe" in out
    except Exception:
        return False


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd not in ("status", "apply", "restore"):
        raise SystemExit(__doc__)
    if cmd != "status" and game_running():
        raise SystemExit("Unreal II is running - close it first.")
    for path, (a, b), what, sov, orig in patches():
        data = open(path, "rb").read()
        st = state(data[a:b], sov, orig)
        if cmd == "status":
            print(f"{os.path.basename(path):12} {what}: {st}")
            continue
        want, frm, to = ("original", sov, orig) if cmd == "apply" else ("soverhaul", orig, sov)
        if st == want:
            print(f"{os.path.basename(path):12} {what}: already {want}")
            continue
        if st.startswith("unknown"):
            raise SystemExit(f"{path}: {st} - not patching (different SOverhaul/game version?)")
        backup = path + ".before-movefix"
        if cmd == "apply" and not os.path.exists(backup):
            shutil.copy2(path, backup)
        open(path, "wb").write(data[:a] + data[a:b].replace(frm, to, 1) + data[b:])
        print(f"{os.path.basename(path):12} {what}: now {want}")


if __name__ == "__main__":
    main()
