"""U2Patches - small fixes for Unreal II: The Awakening + SOverhaul that no
mutator can make, applied as same-size byte patches to the compiled packages.

Patches (each can be applied / restored on its own):

  movement  Undo SOverhaul's movement changes.
            - U2Pawns.u  U2PlayerSP default GroundSpeed 1000.0 -> 263.0 (the
              original speed; Unreal resolves collision after the move, not
              predictively, so at ~3.8x speed the player snags and pops)
            - U2.u       HandleWalking: GetRunFlag() < 1 -> GetRunFlag() > 0
              (Shift walks again instead of sprinting)

  nolean    Remove leaning (Q/E and the lean-mode keys).
            - U2.u       PlayerWalking / PlayerSwimming / PlayerClimbing
              CanLean(): "Pawn.Physics == PHYS_x" -> "== 255", a physics mode
              that doesn't exist, so CanLean() is always false. Every way into
              a lean (ToggleLeanLeft/Right/Forward/Up) goes through CanLean().

    python u2patch.py                      show the state of every patch
    python u2patch.py apply   movement nolean
    python u2patch.py restore nolean

Close the game first. Before the first change each package is backed up to
System/<name>.u.before-u2patch. Patches are looked up inside their own class
or function via the package's export table and only applied when the expected
bytes match exactly once, so a different game/SOverhaul version is refused
instead of corrupted. Built against SOverhaul 1.1.0's packages.
"""
import os, shutil, struct, subprocess, sys

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"


# --- Unreal package reading --------------------------------------------------

def compact_index(v):
    out = bytearray()
    a = abs(v)
    out.append((0x80 if v < 0 else 0) | (a & 0x3F) | (0x40 if a >= 0x40 else 0))
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


class Package:
    def __init__(self, data):
        tag, ver, lic, flags, nc, no, ec, eo = struct.unpack_from("<IHHIiiii", data, 0)
        assert tag == 0x9E2A83C1, "not an Unreal package"
        self.names, p = [], no
        for _ in range(nc):
            n, p = read_ci(data, p)
            self.names.append(data[p:p + n - 1].decode("latin-1"))
            p += n + 4                              # string, flags
        self.exports, p = [], eo
        for _ in range(ec):
            cls, p = read_ci(data, p); sup, p = read_ci(data, p)
            outer = struct.unpack_from("<i", data, p)[0]; p += 4
            name, p = read_ci(data, p); p += 4      # object flags
            size, p = read_ci(data, p)
            off = 0
            if size > 0:
                off, p = read_ci(data, p)
            self.exports.append(dict(name=self.names[name], outer=outer, off=off, size=size))

    def name(self, n):
        return compact_index(self.names.index(n))

    def path(self, e):
        parts = [e["name"]]
        while e["outer"] > 0:
            e = self.exports[e["outer"] - 1]
            parts.insert(0, e["name"])
        return ".".join(parts)

    def range(self, path):
        """Byte range of the export at PATH, e.g. 'U2PlayerController.PlayerWalking.CanLean'."""
        for e in self.exports:
            if e["size"] > 0 and self.path(e) == path:
                return e["off"], e["off"] + e["size"]
        raise SystemExit(f"{path} not found")


# --- patch definitions -------------------------------------------------------
# each site: (package file, export path, soverhaul bytes, patched bytes)

def movement_sites():
    sites = []
    f = "U2Pawns.u"; p = Package(read(f))
    gs = p.name("GroundSpeed") + b"\x24"                # float property, 4 bytes
    sites.append((f, "U2PlayerSP", gs + struct.pack("<f", 1000.0), gs + struct.pack("<f", 263.0)))
    f = "U2.u"; p = Package(read(f))
    call = b"\x39\x3a\x1b" + p.name("GetRunFlag") + b"\x16"   # int(GetRunFlag())
    sites.append((f, "U2PlayerController.HandleWalking",
                  b"\x96" + call + b"\x26\x16",               # < 1
                  b"\x97" + call + b"\x25\x16"))              # > 0 (original)
    return sites


def nolean_sites():
    sites = []
    f = "U2.u"
    for state, phys in (("PlayerWalking", 0x01), ("PlayerSwimming", 0x03), ("PlayerClimbing", 0x0B)):
        # ... == byte(PHYS_x) ) ; return-end
        tail = b"\x39\x3a\x24%c\x16\x16\x04\x0b"
        sites.append((f, f"U2PlayerController.{state}.CanLean", tail % phys, tail % 0xFF))
    return sites


PATCHES = {
    "movement": ("undo SOverhaul's movement (speed 263, Shift walks)", movement_sites),
    "nolean": ("remove leaning", nolean_sites),
}


# --- applying ------------------------------------------------------------------

def read(f):
    return open(os.path.join(GAME, "System", f), "rb").read()


def site_state(f, path, old, new):
    data = read(f)
    a, b = Package(data).range(path)
    no, nn = data[a:b].count(old), data[a:b].count(new)
    if no == 1 and nn == 0:
        return "off"
    if nn == 1 and no == 0:
        return "on"
    return f"unknown ({old.hex()} x{no}, {new.hex()} x{nn})"


def patch_state(name):
    states = {site_state(*s) for s in PATCHES[name][1]()}
    return states.pop() if len(states) == 1 else "mixed: " + ", ".join(sorted(states))


def set_patch(name, on):
    for f, path, old, new in PATCHES[name][1]():
        st = site_state(f, path, old, new)
        if st == ("on" if on else "off"):
            continue
        if st.startswith("unknown"):
            raise SystemExit(f"{f} {path}: {st} - not patching (different SOverhaul/game version?)")
        full = os.path.join(GAME, "System", f)
        backups = [full + ".before-u2patch", full + ".before-movefix"]
        if not any(os.path.exists(b) for b in backups):
            shutil.copy2(full, backups[0])
        data = read(f)
        a, b = Package(data).range(path)
        frm, to = (old, new) if on else (new, old)
        open(full, "wb").write(data[:a] + data[a:b].replace(frm, to, 1) + data[b:])


def game_running():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return "unreal2.exe" in out
    except Exception:
        return False


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    names = args[1:]
    if cmd not in ("status", "apply", "restore") or any(n not in PATCHES for n in names) \
            or (cmd != "status" and not names):
        raise SystemExit(__doc__)
    if cmd != "status":
        if game_running():
            raise SystemExit("Unreal II is running - close it first.")
        for n in names:
            set_patch(n, cmd == "apply")
    for n, (what, _) in PATCHES.items():
        print(f"{n:9} {patch_state(n):4}  {what}")


if __name__ == "__main__":
    main()
