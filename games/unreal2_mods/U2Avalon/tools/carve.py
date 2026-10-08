r"""Carving while the user plays (option 1, the user's pick 2026-10-07): UnrealEd, in the background, edits
a copy of the map the user is in and saves it as the next TutA_LiveN; the running game is told
("avalon pending TutA_LiveN") and reloaded 5 s later by itself (auto=0: the user types "avalon reload") - they land where they
stood, with the session's cards and journal kept.

    py tools/carve.py pit X Y R DEPTH            terrain: a round pit (smooth sides)
    py tools/carve.py trench X1 Y1 X2 Y2 W DEPTH  terrain: a trench along a line
    py tools/carve.py mound X Y R HEIGHT          terrain: a mound (the opposite)
    py tools/carve.py flatten X Y R [Z]           terrain: a level pad (at the ground's mean, or Z)
    py tools/carve.py box X Y Z SX SY SZ [add]    level geometry (BSP): a subtract box (add = a solid one)
    py tools/carve.py rail [X1 Y1 Z1 X2 Y2 Z2]    a railing (stock waterfront rail, 1.5 m) from the user's last
                                                   two marks (look at the floor at each end), or the points
    py tools/carve.py drop ACTOR [SINK]           a floating static mesh (e.g. StaticMeshActor57) set down on
                                                   the terrain: resting on the highest ground under it, SINK (30) in
    options: base=<map> (default: the map the game last built on), send=0 (don't tell the game), auto=0
             (don't reload by itself: the user types "avalon reload"), mark
             in place of X Y uses the user's last "avalon mark"

Terrain carves edit the island heightmap (TutA: 128 x 128 cells of 512 units = 10 m, so nothing finer than
that), re-seat the static meshes standing on the changed ground, and light only the terrain: the tower's
baked lighting is untouched. A BSP box rebuilds the level geometry (MAP REBUILD), which may lose the
original baked lighting on brush surfaces - try it on a copy first.
"""
import math, os, re, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
import numpy as np
from uedlib import session  # noqa
import live  # noqa

GAME = live.GAME
os.environ.setdefault("U2ED_WITH_GAME", "1")      # carving happens while the user plays
MAPS = os.path.join(GAME, "Maps")
LOC, CELL, N, SEA_Z = (-14487.546875, 4835.837891, -131.845703), 512.0, 128, -4967.0
ENTRY_BRUSH = os.path.join(GAME, "U2Hover", "brushes", "Entry.u3d")     # a 512 cube


def current_map():
    text = open(live.LOG, "rb").read().decode("latin1", "replace") if os.path.exists(live.LOG) else ""
    m = re.findall(r"Cards: built \d+ things on (\S+)", text)
    return m[-1] if m else "TutA"


def next_name():
    n = 1
    while os.path.exists(os.path.join(MAPS, "TutA_Live%d.un2" % n)):
        n += 1
    return "TutA_Live%d" % n


def mark_point():
    text = open(live.LOG, "rb").read().decode("latin1", "replace")
    m = [l for l in text.splitlines() if "Cards: edit MARK" in l]
    w = re.search(r"looking-at (-?\d+) (-?\d+) (-?\d+)", m[-1])
    return float(w.group(1)), float(w.group(2)), float(w.group(3))


def mark_points(n):
    """the looking-at points of the user's last n marks, oldest first"""
    text = open(live.LOG, "rb").read().decode("latin1", "replace")
    m = [l for l in text.splitlines() if "Cards: edit MARK" in l][-n:]
    if len(m) < n:
        sys.exit("need %d marks in the game log" % n)
    return [tuple(float(v) for v in re.search(r"looking-at (-?\d+) (-?\d+) (-?\d+)", l).groups()) for l in m]


RAIL_MESH, RAIL_LEN = "MM_WaterfrontM.Interior.railing", 485.0      # X from -246 to 239, Z 0..76 (1.5 m)


def rail_t3d(p1, p2, mesh=RAIL_MESH, length=RAIL_LEN):
    """railing sections end to end from p1 to p2 (floor points the user marked), standing on the line,
    stretched a little so the run ends at the marks; Z follows the line"""
    dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    L = math.hypot(dx, dy)
    n = max(1, int(round(L / length)))
    yaw = int(math.degrees(math.atan2(dy, dx)) * 65536 / 360) % 65536
    scale = L / (n * length)                      # stretch slightly so the run ends at the marks
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        out.append("Begin Actor Class=StaticMeshActor Name=LiveRail%d\n    StaticMesh=StaticMesh'%s'\n"
                   "    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n    Rotation=(Yaw=%d)\n    DrawScale3D=(X=%.3f,Y=1.000000,Z=1.000000)\n"
                   "End Actor" % (i, mesh, p1[0] + dx * t, p1[1] + dy * t, p1[2] + dz * t, yaw, scale))
    print("rail: %d sections of %s over %.0f units" % (n, mesh, L))
    return "Begin Map\n" + "\n".join(out) + "\nEnd Map\n"


def read_bmp(path):
    raw = open(path, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    return raw[:off], H, h


def write_bmp(path, head, H, h):
    data = np.clip(np.round(H), 0, 65535).astype("<u2").tobytes()
    open(path, "wb").write(head + data)


def heights_world(path):
    head, H, h = read_bmp(path)
    return H[::-1] if h > 0 else H


def ground_at(H, x, y):
    fi, fj = (x - LOC[0]) / CELL + N / 2, (y - LOC[1]) / CELL + N / 2
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return None
    ti, tj = fi - i0, fj - j0
    v = H[j0, i0] * (1 - ti) * (1 - tj) + H[j0, i0 + 1] * ti * (1 - tj) + H[j0 + 1, i0] * (1 - ti) * tj + H[j0 + 1, i0 + 1] * ti * tj
    return LOC[2] + (v - 32768) * 0.5


def make_reseat(before, after):
    """every static mesh that stood on the changed ground (origin from 8 m under to 12 m over it) moves with
    it; one now under the sea is dropped (terrain_apply.reseat, for all meshes: the town's too)"""
    Hs, Hn = heights_world(before), heights_world(after)

    def reseat(t3d):
        out, moved, dropped = [], 0, 0
        for m in re.finditer(r"Begin Actor.*?End Actor", t3d, re.S):
            blk = m.group(0)
            loc = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)", blk)
            if loc:
                x, y, z = (float(v) for v in loc.groups())
                gs, gn = ground_at(Hs, x, y), ground_at(Hn, x, y)
                if gs is not None and gn is not None and -400 <= z - gs <= 600 and abs(gn - gs) > 10:
                    if gn <= SEA_Z + 20:
                        dropped += 1
                        continue
                    blk = blk.replace(loc.group(0), "Location=(X=%s,Y=%s,Z=%.3f)" % (loc.group(1), loc.group(2), z + gn - gs))
                    moved += 1
            out.append(blk)
        print("re-seated %d static meshes, dropped %d now under the sea" % (moved, dropped))
        return "Begin Map\n" + "\n".join(out) + "\nEnd Map\n"
    return reseat


def mesh_bounds(mesh):
    """Package.Group.Name -> (minX minY minZ maxX maxY maxZ) from the .usx (U2AvalonCards/tools/mesh_bounds.py)"""
    sys.path.insert(0, os.path.join(HERE, "..", "..", "U2AvalonCards", "tools"))
    import subprocess
    pkg = mesh.split(".")[0]
    out = os.path.join(tempfile.gettempdir(), "carve_bounds_%s.txt" % pkg)
    if not os.path.exists(out):
        subprocess.run([sys.executable, os.path.join(HERE, "..", "..", "U2AvalonCards", "tools", "mesh_bounds.py"), out,
                        os.path.join(GAME, "StaticMeshes", pkg + ".usx")], check=True, capture_output=True)
    for line in open(out):
        f = line.split()
        if f and f[0].lower() == mesh.lower():
            return [float(v) for v in f[1:7]]
    raise SystemExit("no bounds for " + mesh)


def make_drop(name, H, sink):
    """the actor NAME moved down (or up) so its footprint's lowest ground point meets the mesh's bottom"""
    def num(blk, key, default):
        m = re.search(r"\b%s=([-\d.]+)" % key, blk)
        return float(m.group(1)) if m else default

    def drop(t3d):
        out, done = [], False
        for m in re.finditer(r"Begin Actor.*?End Actor", t3d, re.S):
            blk = m.group(0)
            if re.search(r"\bName=%s\b" % re.escape(name), blk):
                loc = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)", blk)
                x, y, z = (float(v) for v in loc.groups())
                mesh = re.search(r"StaticMesh=StaticMesh'([^']+)'", blk).group(1)
                b = mesh_bounds(mesh)
                ds = num(blk, "DrawScale", 1.0)
                s3 = re.search(r"DrawScale3D=\(([^)]*)\)", blk)
                sx = sy = sz = 1.0
                if s3:
                    sx, sy, sz = num(s3.group(0), "X", 1.0), num(s3.group(0), "Y", 1.0), num(s3.group(0), "Z", 1.0)
                yaw = num(blk, "Yaw", 0.0) * 2 * math.pi / 65536
                c, s_ = math.cos(yaw), math.sin(yaw)
                grounds = []
                for u in np.linspace(b[0], b[3], 7):
                    for v in np.linspace(b[1], b[4], 7):
                        lx, ly = u * ds * sx, v * ds * sy
                        g = ground_at(H, x + lx * c - ly * s_, y + lx * s_ + ly * c)
                        if g is not None:
                            grounds.append(g)
                bottom = z + b[2] * ds * sz
                newz = z + (max(grounds) - sink) - bottom     # rests on the highest point it touches
                print("drop %s (%s): bottom %.0f, ground under it %.0f..%.0f -> Z %.0f (%+.0f)" % (
                    name, mesh, bottom, min(grounds), max(grounds), newz, newz - z))
                blk = blk.replace(loc.group(0), "Location=(X=%s,Y=%s,Z=%.3f)" % (loc.group(1), loc.group(2), newz))
                done = True
            out.append(blk)
        if not done:
            raise SystemExit("no actor named " + name)
        return "Begin Map\n" + "\n".join(out) + "\nEnd Map\n"
    return drop


def world_to_cells(x, y):
    return (x - LOC[0]) / CELL + N / 2, (y - LOC[1]) / CELL + N / 2


def carve_terrain(H, h, kind, a):
    """H is the BMP's rows as stored (bottom-up when h > 0); heights in units = (v - 32768) * 0.5 + LOC.z"""
    rows = H.shape[0]
    J, I = np.mgrid[0:rows, 0:H.shape[1]]
    Jw = (rows - 1 - J) if h > 0 else J                 # the world row index of each stored row
    WX = LOC[0] + (I - N / 2) * CELL
    WY = LOC[1] + (Jw - N / 2) * CELL
    units = (H - 32768) * 0.5 + LOC[2]
    if kind in ("pit", "mound", "flatten"):
        x, y, r = a[0], a[1], a[2]
        d = np.hypot(WX - x, WY - y)
        fall = np.clip(1 - (d - r * 0.6) / (r * 0.4 + 1e-6), 0, 1)       # flat middle, smooth sides
        fall = fall * fall * (3 - 2 * fall)
        if kind == "pit":
            units = units - a[3] * fall
        elif kind == "mound":
            units = units + a[3] * fall
        else:
            z = a[3] if len(a) > 3 else float(units[d < r].mean())
            units = units + (z - units) * fall
    elif kind == "trench":
        x1, y1, x2, y2, w, depth = a
        ux, uy = x2 - x1, y2 - y1
        L2 = ux * ux + uy * uy
        t = np.clip(((WX - x1) * ux + (WY - y1) * uy) / L2, 0, 1)
        d = np.hypot(WX - (x1 + t * ux), WY - (y1 + t * uy))
        fall = np.clip(1 - (d - w * 0.3) / (w * 0.7 + 1e-6), 0, 1)
        fall = fall * fall * (3 - 2 * fall)
        units = units - depth * fall
    changed = int((np.abs(units - ((H - 32768) * 0.5 + LOC[2])) > 1).sum())
    return (units - LOC[2]) / 0.5 + 32768, changed


def main():
    a = [x for x in sys.argv[1:] if "=" not in x]
    o = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    kind = a[0]
    if kind == "drop":
        nums = [float(a[2]) if len(a) > 2 else 30.0]
    elif kind == "rail":
        nums = [v for p in mark_points(2) for v in p] if len(a) < 7 else [float(v) for v in a[1:7]]
    elif len(a) > 1 and a[1] == "mark":
        mx, my, mz = mark_point()
        nums = [mx, my] + ([mz] if kind == "box" else []) + [float(v) for v in a[2:] if v != "add"]
    else:
        nums = [float(v) for v in a[1:] if v != "add"]
    base = o.get("base") or current_map()
    out = next_name()
    tmp = tempfile.mkdtemp(prefix="carve_")
    print("carve %s %s on %s -> %s" % (kind, nums, base, out))

    def job(ed):
        ed.exec("!answer yes")
        ed.load(base)
        if kind == "rail":
            ed.load_package(os.path.join(GAME, "StaticMeshes", RAIL_MESH.split(".")[0] + ".usx"))
            path = os.path.join(tmp, "rail.t3d")
            open(path, "w").write(rail_t3d(nums[0:3], nums[3:6]))
            ed.deselect()
            ed.import_t3d(path, add=True)        # the new sections come in selected
            ed.light(selected=True)
            ed.deselect()
        elif kind == "drop":
            before = os.path.join(tmp, "before.bmp")
            ed.ok('OBJ EXPORT TYPE=Texture NAME="MyLevel.terrain_maps.island1" FILE="%s"' % before)
            ed.replace_actors("StaticMeshActor", make_drop(a[1], heights_world(before), nums[0]))
            ed.deselect()
            ed.ok("ACTOR SELECT OFCLASS CLASS=StaticMeshActor")
            ed.light(selected=True)
            ed.deselect()
        elif kind == "box":
            ed.load_brush(ENTRY_BRUSH)
            ed.ok("BRUSH SCALE X=%g Y=%g Z=%g" % (nums[3] / 512.0, nums[4] / 512.0, nums[5] / 512.0))
            ed.ok("BRUSH MOVETO X=%g Y=%g Z=%g" % (nums[0], nums[1], nums[2]))
            ed.ok("BRUSH ADD" if "add" in a else "BRUSH SUBTRACT")
            ed.ok("MAP REBUILD")
        else:
            before = os.path.join(tmp, "before.bmp")
            ed.ok('OBJ EXPORT TYPE=Texture NAME="MyLevel.terrain_maps.island1" FILE="%s"' % before)
            head, H, h = read_bmp(before)
            newH, changed = carve_terrain(H, h, kind, nums)
            after = os.path.join(tmp, "island1.bmp")
            write_bmp(after, head, newH, h)
            print("terrain: %d of %d heights changed" % (changed, H.size))
            ed.import_texture(after, "island1", "MyLevel", "terrain_maps", MIPS=0)
            ed.replace_actors("TerrainInfo", None)
            # the map's own meshes on the changed ground move with it (terrain_apply's re-seat)
            ed.replace_actors("StaticMeshActor", make_reseat(before, after))
            ed.deselect()
            # light the terrain and the static meshes (re-imported meshes lose their baked light: black),
            # never the BSP (a full LIGHT APPLY left the tower dark and blotchy)
            ed.ok("ACTOR SELECT OFCLASS CLASS=StaticMeshActor")
            ed.ok("ACTOR SELECT OFCLASS CLASS=TerrainInfo")
            ed.light(selected=True)
            ed.deselect()
        ed.save(out)
        print("saved", ed.map_path(out))

    session(job)
    if o.get("send", "1") != "0" and os.path.exists(os.path.join(MAPS, out + ".un2")):
        if o.get("auto", "1") == "0":
            live.send(["pending " + out, "say carved: %s (type avalon reload)" % kind], 20)
        else:
            # the user's call (2026-10-07): reload the level by itself after a change, with a short warning
            live.send(["pending " + out, "say carved: %s - reloading in 5 s, you come back where you stand" % kind], 20)
            import time
            time.sleep(5)
            live.send(["reload"], 30)


if __name__ == "__main__":
    main()
