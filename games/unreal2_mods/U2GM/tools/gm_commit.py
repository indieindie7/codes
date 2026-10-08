r"""gm_commit - bake a U2GM session's journal into a real map with UnrealEd, then send the game there.

    py gm_commit.py                         commit the journal of the map the game asked for (or --family)
    py gm_commit.py --watch                 wait for "gm commit" in the game, commit, send the game over
    py gm_commit.py --dry-run [--ini F] [--heightmap F.bmp] [--out DIR]
                                            the plan only: editor commands, the T3D, terrain PNGs; no editor
  options: --family tuta  --map TutA_Live2 (the source map; default: CommitRequest's, else the newest
           <Map>_LiveN, else <Map>)  --out-map NAME  --no-ops (T3D copy/delete/re-import, no ops DLL)
           --full-light (LIGHT APPLY instead of CHANGED=1)  --bake (U2Bake pass, needs the ops DLL)
           --paths (PATHS BUILD)  --no-send (don't tell the game)  --ini/--section/--key (another journal,
           e.g. AvalonEditor's: --ini U2AvalonCards.ini --section U2AvalonCards.AvalonEditor)

The journal: <game>\System\U2GM.ini, [U2GM.GMMaster] Ops[k]="@family op ..." (read only: the game owns
the file and rewrites it from memory). Ops, in slot order:
    place NAME X Y Z YAW SCALE      the map's actor NAME moved (yaw in degrees, the rest of its rotation kept)
    hide NAME                       the map's actor NAME removed
    mesh PATH X Y Z YAW SCALE       a new StaticMeshActor
    terrain raise|lower|flatten|smooth X Y R H    the fork's brush (u2shaders.hpp gmterrain), same math
Draw lines (Draws[], "draw D<n> ...") are notes for the level team and never baked.

How it is baked (on a copy: the source map is loaded and saved under the next free <Map>_LiveN):
  * terrain: every TerrainInfo's heightmap is exported (OBJ EXPORT, a G16 BMP), the brush lines are run
    over it in numpy with the fork's exact math (float32, cosine falloff, original + every line in slot
    order), imported back under its own name (TEXTURE IMPORT MIPS=0) and the TerrainInfos are re-pasted
    (uedlib.replace_actors: a pasted TerrainInfo rebuilds from its heightmap). This is carve.py's and
    terrain_apply.py's route, tested; the alternative (SetHeightmap/Update through a new ops-DLL command)
    would keep the TerrainInfo objects but is new untested native code.
  * place: ops DLL !select + EDIT COPY (to read the actor) + !move (verified 2026-10-08); an actor whose
    DrawScale changed, or every one with --no-ops, goes the T3D way: copy, ACTOR DELETE, edited, re-imported.
  * hide: select + ACTOR DELETE.   * mesh: one MAP IMPORTADD of StaticMeshActor blocks (Group=U2GM).
  * light: !light on the moved and imported meshes, then LIGHT APPLY CHANGED=1 (the real incremental mode).
  * --bake: !meshverts -> U2Bake/bake.py --mode add -> !bakeload (untested chain).  --paths: PATHS BUILD.

Double apply: the baked lines must not replay on the baked map. The game is told, through
System\U2GMPanel.txt (q-lines in the watcher's own session, 2^30 and up), "gm baked STAMP K TEXT" for every
baked slot (GMMaster empties slot K only if it still says TEXT), then "gm committed STAMP MAP N" and
"gm travel MAP". Edits are refused in the game while a commit is pending, so the journal can't change under
the bake. Lines the bake could not apply (actor not found, bad line) are not reported and keep replaying.
"""
import argparse, json, math, os, re, shutil, struct, subprocess, sys, tempfile, time, zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.environ.get("U2_GAME", r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening")
SYS = os.path.join(GAME, "System")
MAPS = os.path.join(GAME, "Maps")
INI = os.path.join(SYS, "U2GM.ini")
PANEL = os.path.join(SYS, "U2GMPanel.txt")
STATUS = os.path.join(SYS, "U2GMCommit.status")
BRIDGE = r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge"
U2BAKE = r"C:\Users\john\Documents\github\codes\tools\python\U2Bake\bake.py"
STATE = os.path.join(HERE, ".gm_commit_state.json")
SECTION, KEY = "U2GM.GMMaster", "Ops"
WATCH_BASE = 1 << 30            # GMMaster: q-line sessions from here up are the watcher's

# carve.py's measured TutA island terrain (the dry run's default when no TerrainInfo is known)
TUTA_TERRAIN = {"Name": "TerrainInfo0", "Location": (-14487.546875, 4835.837891, -131.845703),
                "Scale": (512.0, 512.0, 128.0), "Map": "MyLevel.terrain_maps.island1"}


# ---------------------------------------------------------------------------------------------- the ini
def read_text(path):
    """an Unreal ini as text: UTF-16 (BOM or NULs) or 8-bit"""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw[1:2] == b"\x00" or (len(raw) > 64 and raw.count(b"\x00") > len(raw) // 4):
        return raw.decode("utf-16-le", "replace").lstrip("\ufeff")
    try:
        return raw.decode("utf-8").lstrip("\ufeff")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1].replace('\\"', '"')
    return v


def section(text, name):
    """{key: value} and {array key lower: {index: value}} of one [section] (later lines win)"""
    keys, arrays, inside = {}, {}, False
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        if s.startswith("["):
            inside = s.lower() == "[%s]" % name.lower()
            continue
        if not inside or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), unquote(v)
        m = re.match(r"^(\w+)\[(\d+)\]$", k)
        if m:
            arrays.setdefault(m.group(1).lower(), {})[int(m.group(2))] = v
        else:
            keys[k.lower()] = v
            arrays.setdefault(k.lower(), {}).setdefault(0, v)     # "Ops=x" is element 0
    return keys, arrays


def family_of(name):
    m = name.lower()
    if "." in m:
        m = m.split(".")[0]
    i = m.find("_live")
    return m[:i] if i >= 0 else m


def journal(text, family, sect=SECTION, key=KEY):
    """[(slot, op text)] of this family, in slot order (terrain lines depend on it)"""
    _, arrays = section(text, sect)
    tag = "@" + family.lower()
    out = []
    for k, v in sorted(arrays.get(key.lower(), {}).items()):
        w = v.split(None, 1)
        if len(w) == 2 and w[0].lower() == tag:
            out.append((k, w[1].strip()))
    return out


def parse_op(text):
    """one journal line -> dict; ValueError when it isn't a line the bake knows"""
    w = text.split()
    if not w:
        raise ValueError("empty")
    kind = w[0].lower()
    f = lambda s: float(s)
    if kind == "place" and len(w) >= 6:
        return {"kind": "place", "name": w[1], "loc": (f(w[2]), f(w[3]), f(w[4])), "yaw": f(w[5]),
                "scale": f(w[6]) if len(w) > 6 else None}
    if kind == "hide" and len(w) >= 2:
        return {"kind": "hide", "name": w[1]}
    if kind == "mesh" and len(w) >= 6:
        return {"kind": "mesh", "path": w[1], "loc": (f(w[2]), f(w[3]), f(w[4])), "yaw": f(w[5]),
                "scale": f(w[6]) if len(w) > 6 else 1.0}
    if kind == "terrain" and len(w) >= 5:
        b = w[1].lower()
        if b not in ("raise", "lower", "flatten", "smooth"):
            raise ValueError("unknown brush " + b)
        x, y, r = f(w[2]), f(w[3]), f(w[4])
        h = f(w[5]) if len(w) > 5 else 0.0
        if not (0 < r <= 65536):
            raise ValueError("radius out of range")
        if b == "smooth" and h == 0:
            h = 1.0
        return {"kind": "terrain", "brush": b, "x": x, "y": y, "r": r, "h": h}
    if kind == "draw":
        raise ValueError("draw lines are notes, never baked")
    raise ValueError("unknown or short line")


def yaw_units(deg):
    """GMMaster.Apply: R.Yaw = int(deg * 65536 / 360) (truncated toward zero)"""
    return int(float(deg) * 65536.0 / 360.0)


# ---------------------------------------------------------------------------------------------- maps
def map_names():
    try:
        return [os.path.splitext(f)[0] for f in os.listdir(MAPS) if f.lower().endswith(".un2")]
    except OSError:
        return []


def live_number(name, family):
    m = re.match(r"^%s_live(\d+)$" % re.escape(family), name.lower())
    return int(m.group(1)) if m else None


def source_map(family, names=None):
    """the newest <Map>_LiveN of the family, else <Map> itself"""
    names = map_names() if names is None else names
    lives = [(live_number(n, family), n) for n in names if live_number(n, family) is not None]
    if lives:
        return max(lives)[1]
    for n in names:
        if n.lower() == family:
            return n
    raise SystemExit("no map of family %s in %s" % (family, MAPS))


def next_live(source, names=None):
    """the next free <Parent>_LiveN, as carve.py numbers them (a copy of a copy numbers on from the parent)"""
    names = {n.lower() for n in (map_names() if names is None else names)}
    parent = source[:source.lower().index("_live")] if "_live" in source.lower() else source
    n = 1
    while ("%s_live%d" % (parent, n)).lower() in names:
        n += 1
    return "%s_Live%d" % (parent, n)


# ---------------------------------------------------------------------------------------------- terrain
class Terrain:
    """heightmap (x, y, raw) <-> world: Location + ((x - W/2) SX, (y - H/2) SY, (raw - 32768) SZ/256), the
    relation carve.py measured on TutA (TerrainScale Z/256 per height step); affine as the fork assumes"""

    def __init__(self, name, loc, scale, texture, w, h):
        self.name, self.loc, self.scale, self.texture, self.w, self.h = name, loc, scale, texture, w, h
        self.O = np.array([loc[0] - w / 2 * scale[0], loc[1] - h / 2 * scale[1], loc[2] - 32768 * scale[2] / 256.0],
                          dtype=np.float32)
        self.AX = np.array([scale[0], 0, 0], dtype=np.float32)
        self.AY = np.array([0, scale[1], 0], dtype=np.float32)
        self.AZ = np.float32(scale[2] / 256.0)

    def world_z(self, raw):
        return self.O[2] + raw * self.AZ


def apply_brushes(orig, t, brushes):
    """u2shaders.hpp GmRun, vectorised: Work = the original as float32, then every brush in order over the
    whole grid (the fork's bounding box only skips cells with D >= R anyway), clamped and rounded (+0.5)"""
    H, W = orig.shape
    work = orig.astype(np.float32)
    y, x = np.mgrid[0:H, 0:W]
    x = x.astype(np.float32)
    y = y.astype(np.float32)
    WX = t.O[0] + x * t.AX[0] + y * t.AY[0]
    WY = t.O[1] + x * t.AX[1] + y * t.AY[1]
    base = t.O[2] + x * t.AX[2] + y * t.AY[2]
    applied = 0
    for b in brushes:
        bx, by, R, Hh = np.float32(b["x"]), np.float32(b["y"]), np.float32(b["r"]), np.float32(b["h"])
        D = np.sqrt((WX - bx) * (WX - bx) + (WY - by) * (WY - by))
        inside = D < R
        if not inside.any():
            continue
        applied += 1
        fall = np.float32(0.5) * (np.float32(1.0) + np.cos(np.float32(3.14159265) * D / R).astype(np.float32))
        k = b["brush"][0]
        if k == "r":
            new = work + fall * Hh / t.AZ
        elif k == "l":
            new = work - fall * Hh / t.AZ
        elif k == "f":
            new = work + fall * ((Hh - base) / t.AZ - work)
        else:
            prev = work
            p = np.pad(prev, 1, mode="constant")
            ones = np.pad(np.ones_like(prev), 1, mode="constant")
            s = np.zeros_like(prev)
            n = np.zeros_like(prev)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    s = s + p[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
                    n = n + ones[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
            strength = np.float32(min(max(float(Hh), 0.0), 1.0))
            new = work + fall * strength * (s / n - work)
        work = np.where(inside, new.astype(np.float32), work)
    out = (np.clip(work, 0, 65535) + np.float32(0.5)).astype(np.uint16)
    return out, applied


def read_bmp16(path):
    """a G16 heightmap BMP (as OBJ EXPORT writes it) -> (header bytes, rows top-down y = heightmap y, h sign)"""
    raw = open(path, "rb").read()
    if raw[:2] != b"BM":
        raise ValueError(path + ": not a BMP")
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    bpp = struct.unpack_from("<H", raw, 28)[0]
    if bpp != 16:
        raise ValueError("%s: %d-bit, a G16 heightmap is 16-bit" % (path, bpp))
    a = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w)
    # carve.py: the BMP's rows are stored bottom-up when h > 0; heightmap row y = world row (heights_world)
    return raw[:off], (a[::-1] if h > 0 else a).copy(), h


def write_bmp16(path, head, hm, h):
    a = hm[::-1] if h > 0 else hm
    open(path, "wb").write(head + np.ascontiguousarray(a).astype("<u2").tobytes())


def make_bmp16(w, h, value=32768):
    """a fresh bottom-up 16-bit BMP header (the dry run's flat heightmap)"""
    size = w * h * 2
    head = b"BM" + struct.pack("<IHHI", 54 + size, 0, 0, 54) + struct.pack("<IiiHHIIiiII", 40, w, h, 1, 16, 0, size,
                                                                            2835, 2835, 0, 0)
    return head, np.full((h, w), value, dtype=np.uint16), h


def png(path, rgb):
    """rgb: HxWx3 uint8 (or HxW) -> PNG, no PIL"""
    a = np.asarray(rgb, dtype=np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    H, W = a.shape[:2]
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(H))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def terrain_pngs(stem, before, after):
    """<stem>.png: the result, grey, north (+Y) up; <stem>_diff.png: red raised, blue lowered"""
    lo, hi = float(min(before.min(), after.min())), float(max(before.max(), after.max()))
    g = ((after.astype(float) - lo) / max(1.0, hi - lo) * 255).astype(np.uint8)[::-1]
    d = after.astype(float) - before.astype(float)
    m = max(1.0, float(np.abs(d).max()))
    rgb = np.zeros(after.shape + (3,), np.uint8)
    rgb[..., 0] = np.clip(d / m * 255, 0, 255)
    rgb[..., 2] = np.clip(-d / m * 255, 0, 255)
    rgb[..., 1] = (g[::-1] // 4)
    png(stem + ".png", g)
    png(stem + "_diff.png", rgb[::-1])
    return stem + ".png", stem + "_diff.png"


# ---------------------------------------------------------------------------------------------- T3D
def t3d_props(block):
    props = {}
    for line in block.splitlines():
        s = line.strip()
        if "=" in s and not s.startswith(("Begin", "End")):
            k, v = s.split("=", 1)
            props.setdefault(k, v)
    return props


def t3d_set(block, key, value):
    line = "    %s=%s" % (key, value)
    if re.search(r"(?m)^\s*%s=" % re.escape(key), block):
        return re.sub(r"(?m)^\s*%s=.*$" % re.escape(key), line.replace("\\", "\\\\"), block, count=1)
    return re.sub(r"\n\s*End Actor", "\n%s\nEnd Actor" % line, block, count=1)


def vec(text, keys=("X", "Y", "Z"), default=0.0):
    d = dict((k, float(v)) for k, v in re.findall(r"(\w+)=(-?[\d.eE+-]+)", text or ""))
    return tuple(d.get(k, default) for k in keys)


def actor_block(t3d, name):
    for m in re.finditer(r"Begin Actor (.*?)\n.*?^\s*End Actor", t3d, re.S | re.M):
        if re.search(r"\bName=%s\b" % re.escape(name), m.group(1), re.I):
            return m.group(0)
    return None


def mesh_block(op, slot, stamp):
    x, y, z = op["loc"]
    return ("Begin Actor Class=StaticMeshActor Name=GMMesh%d_%d\n"
            "    StaticMesh=StaticMesh'%s'\n"
            "    Location=(X=%.3f,Y=%.3f,Z=%.3f)\n"
            "    Rotation=(Yaw=%d)\n"
            "    DrawScale=%.6f\n"
            "    Group=\"U2GM\"\n"
            "End Actor" % (stamp, slot, op["path"], x, y, z, yaw_units(op["yaw"]), op["scale"]))


def placed_block(block, op):
    """the actor's own block with the journal's place: location, yaw (pitch/roll kept), scale"""
    x, y, z = op["loc"]
    p, _, r = vec(t3d_props(block).get("Rotation"), ("Pitch", "Yaw", "Roll"))
    b = t3d_set(block, "Location", "(X=%.3f,Y=%.3f,Z=%.3f)" % (x, y, z))
    b = t3d_set(b, "Rotation", "(Pitch=%d,Yaw=%d,Roll=%d)" % (int(p), yaw_units(op["yaw"]), int(r)))
    if op.get("scale") is not None:
        b = t3d_set(b, "DrawScale", "%.6f" % op["scale"])
    return b


def texture_parts(ref):
    """Texture'MyLevel.terrain_maps.island1' -> (package, group or None, name)"""
    m = re.search(r"'([^']+)'", ref or "")
    full = m.group(1) if m else (ref or "").strip()
    parts = full.split(".")
    if len(parts) < 2:
        raise ValueError("can't read TerrainMap %r" % ref)
    return parts[0], (".".join(parts[1:-1]) or None), parts[-1]


# ---------------------------------------------------------------------------------------------- the dry editor
class DryEd:
    """records the commands the bake would run; gives back what the real editor would (from the journal,
    a --heightmap BMP, or carve.py's TutA terrain)"""

    def __init__(self, heightmap=None, terrain=None, log=print):
        self.cmds, self.log, self.pid = [], log, 0
        self.heightmap, self.terrain = heightmap, terrain or TUTA_TERRAIN
        self.selected = None
        self.files = {}

    def _c(self, c, **kw):
        self.cmds.append(c)
        self.log("  ed> " + c)
        return ""

    ok = quiet = exec = _c

    def load(self, name):
        return self._c('MAP LOAD FILE="%s"' % self.map_path(name))

    def save(self, name):
        return self._c('MAP SAVE FILE="%s"' % self.map_path(name))

    def map_path(self, name):
        return os.path.join(MAPS, name + ".un2")

    def load_package(self, path):
        return self._c('OBJ LOAD FILE="%s"' % path)

    def import_texture(self, path, name, package, group=None, **flags):
        f = " ".join("%s=%s" % kv for kv in flags.items())
        return self._c('TEXTURE IMPORT FILE="%s" NAME="%s" PACKAGE="%s"%s %s' % (
            path, name, package, ' GROUP="%s"' % group if group else "", f))

    def import_t3d(self, path, add=True):
        return self._c('MAP %s FILE="%s"' % ("IMPORTADD" if add else "IMPORT", path))

    def replace_actors(self, cls, edit):
        self._c("ACTOR SELECT OFCLASS CLASS=%s / EDIT COPY / ACTOR DELETE / MAP IMPORTADD (replace_actors)" % cls)
        return 1

    def deselect(self):
        self._c("ACTOR SELECT NONE")

    def actors(self, cls):
        self._c("ACTOR SELECT OFCLASS CLASS=%s / EDIT COPY (read)" % cls)
        if cls != "TerrainInfo":
            return []
        t = self.terrain
        return [{"Class": "TerrainInfo", "Name": t["Name"], "Location": t["Location"],
                 "props": {"TerrainMap": "Texture'%s'" % t["Map"],
                           "TerrainScale": "(X=%g,Y=%g,Z=%g)" % t["Scale"]}}]

    def export_texture(self, full, path):
        self._c('OBJ EXPORT TYPE=Texture NAME="%s" FILE="%s"' % (full, path))
        if self.heightmap:
            shutil.copyfile(self.heightmap, path)
        else:
            head, hm, h = make_bmp16(128, 128)
            write_bmp16(path, head, hm, h)

    def select_name(self, name, ops):
        self.selected = name
        self._c(("!select %s" if ops else "SELECTNAME NAME=%s") % name)

    def copy_selected(self):
        self._c("EDIT COPY")
        n = self.selected
        return ("Begin Map\nBegin Actor Class=StaticMeshActor Name=%s\n    StaticMesh=StaticMesh'Dry.Run.Mesh'\n"
                "    Location=(X=0.000000,Y=0.000000,Z=0.000000)\n    Rotation=(Pitch=0,Yaw=0,Roll=0)\nEnd Actor\nEnd Map\n" % n)

    def paths(self, full=False):
        return self._c("PATHS BUILD" if full else "PATHS DEFINE")


class DryOps:
    def __init__(self, ed):
        self.ed = ed

    def exec(self, c):
        return self.ed._c(c)

    def select(self, *names):
        return self.ed._c("!select " + " ".join(names))

    def move(self, name, x=None, y=None, z=None, pitch=None, yaw=None, roll=None):
        a = " ".join("-" if v is None else "%g" % v for v in (x, y, z, pitch, yaw, roll))
        return self.ed._c("!move %s %s" % (name, a))

    def light(self, *names):
        return self.ed._c("!light " + " ".join(names or ("selected",)))


# ---------------------------------------------------------------------------------------------- the bake
class Bake:
    """the journal lines of one commit applied to the editor's copy of the source map"""

    def __init__(self, lines, source, out, stamp, work, use_ops=True, full_light=False, bake=False, paths=False,
                 log=print):
        self.lines, self.source, self.out, self.stamp, self.work = lines, source, out, stamp, work
        self.use_ops, self.full_light, self.bake, self.paths = use_ops, full_light, bake, paths
        self.log = log
        self.baked, self.skipped = [], []           # [(slot, text)], [(slot, text, why)]
        self.pngs, self.t3d = [], ""
        self.ops_list = []
        for slot, text in lines:
            try:
                self.ops_list.append((slot, text, parse_op(text)))
            except ValueError as e:
                self.skipped.append((slot, text, str(e)))

    def of(self, kind):
        return [(s, t, o) for s, t, o in self.ops_list if o["kind"] == kind]

    def run(self, ed, ops=None):
        dry = isinstance(ed, DryEd)
        ed.exec("!answer yes")
        ed.load(self.source)
        if self.use_ops and ops is None:
            from uedlib import Ops
            ops = Ops.attach_to(ed.pid)
        self.terrain(ed)
        imports, moved = self.actors(ed, ops)
        if imports:
            ed.deselect()
            path = os.path.join(self.work, "gm_import.t3d")
            open(path, "w", encoding="utf-8").write(self.t3d)
            ed.import_t3d(path, add=True)                     # they come in selected
            if ops is not None:
                ops.light("selected")
            ed.deselect()
        if ops is not None and moved:
            ops.light(*moved)
        if self.ops_list:
            ed.ok("LIGHT APPLY" if self.full_light else "LIGHT APPLY CHANGED=1", allow=("Couldn't bring window", "Can't find"))
        if self.bake:
            self.u2bake(ed, ops, dry)
        if self.paths:
            ed.paths(full=True)
        ed.save(self.out)

    # -- terrain
    def terrain(self, ed):
        brushes = [(s, t, o) for s, t, o in self.of("terrain")]
        if not brushes:
            return
        infos = ed.actors("TerrainInfo")
        changed_any, used = False, set()
        for a in infos:
            p = a["props"]
            try:
                pkg, group, name = texture_parts(p.get("TerrainMap"))
            except ValueError as e:
                self.log("  terrain %s skipped: %s" % (a.get("Name"), e))
                continue
            full = ".".join(x for x in (pkg, group, name) if x)
            bmp = os.path.join(self.work, "%s_%s.bmp" % (a.get("Name", "terrain"), name))
            if hasattr(ed, "export_texture"):
                ed.export_texture(full, bmp)
            else:
                ed.ok('OBJ EXPORT TYPE=Texture NAME="%s" FILE="%s"' % (full, bmp))
            try:
                head, hm, hs = read_bmp16(bmp)
            except (OSError, ValueError) as e:
                self.log("  terrain %s skipped (only G16 heightmaps, as the fork): %s" % (a.get("Name"), e))
                continue
            loc = a.get("Location") or vec(p.get("Location"))
            scale = vec(p.get("TerrainScale"), default=64.0) if p.get("TerrainScale") else (64.0, 64.0, 64.0)
            t = Terrain(a.get("Name"), loc, scale, full, hm.shape[1], hm.shape[0])
            new, applied = apply_brushes(hm, t, [o for _, _, o in brushes])
            n = int((new != hm).sum())
            self.log("  terrain %s (%s, %dx%d, cell %g, step %g): %d brush line(s) reach it, %d height(s) changed"
                     % (t.name, full, t.w, t.h, scale[0], scale[2] / 256.0, applied, n))
            self.pngs += terrain_pngs(os.path.join(self.work, "%s_%s" % (self.out, t.name)), hm, new)
            if n == 0:
                continue
            if full.lower() in used:
                self.log("  WARNING two TerrainInfos share %s: the last one wins" % full)
            used.add(full.lower())
            out_bmp = os.path.join(self.work, name + ".bmp")
            write_bmp16(out_bmp, head, new, hs)
            ed.import_texture(out_bmp, name, pkg, group, MIPS=0)
            changed_any = True
        if changed_any:
            n = ed.replace_actors("TerrainInfo", None)       # a pasted TerrainInfo rebuilds from its heightmap
            self.log("  re-pasted %s TerrainInfo actor(s)" % n)
        # a brush line is baked when the terrain it was journalled on was processed (one that reached no
        # terrain did nothing in the game either)
        if infos:
            self.baked += [(s, t) for s, t, _ in brushes]
        else:
            self.skipped += [(s, t, "the map has no TerrainInfo") for s, t, _ in brushes]

    # -- actors
    def select(self, ed, ops, name):
        if hasattr(ed, "select_name"):
            ed.select_name(name, ops is not None)
        elif ops is not None:
            ops.select(name)
        else:
            ed.ok("SELECTNAME NAME=%s" % name)

    def read_actor(self, ed, ops, name):
        """the actor's T3D block, None when the map has no actor of that name"""
        try:
            self.select(ed, ops, name)
        except Exception as e:                       # the ops DLL refuses a name that matches nothing
            if type(e).__name__ == "EditorCrashed":
                raise
            self.log("  select %s: %s" % (name, str(e).splitlines()[-1] if str(e) else e))
            return None
        return actor_block(ed.copy_selected(), name)

    def actors(self, ed, ops):
        blocks, moved, packages = [], [], set()
        for slot, text, op in self.of("hide"):
            if not self.read_actor(ed, ops, op["name"]):
                self.skipped.append((slot, text, "no actor named %s on %s" % (op["name"], self.source)))
                continue
            ed.ok("ACTOR DELETE")
            self.baked.append((slot, text))
        for slot, text, op in self.of("place"):
            blk = self.read_actor(ed, ops, op["name"])
            if not blk:
                self.skipped.append((slot, text, "no actor named %s on %s" % (op["name"], self.source)))
                continue
            p = t3d_props(blk)
            had = float(p.get("DrawScale", "1") or 1)
            rescale = op["scale"] is not None and abs(op["scale"] - had) > 1e-4
            if ops is not None and not rescale:
                ops.move(op["name"], op["loc"][0], op["loc"][1], op["loc"][2], None, yaw_units(op["yaw"]), None)
                moved.append(op["name"])
            else:
                # the T3D way (no ops, or a new DrawScale): copied above, deleted, re-imported edited
                ed.ok("ACTOR DELETE")
                blocks.append(placed_block(blk, op))
            self.baked.append((slot, text))
        for slot, text, op in self.of("mesh"):
            pkg = op["path"].split(".")[0]
            if pkg.lower() != "mylevel" and pkg.lower() not in packages:
                packages.add(pkg.lower())
                f = os.path.join(GAME, "StaticMeshes", pkg + ".usx")
                if os.path.exists(f) or isinstance(ed, DryEd):
                    ed.load_package(f)
                else:
                    self.log("  WARNING %s not found: %s must already be loaded by the map" % (f, pkg))
            blocks.append(mesh_block(op, slot, self.stamp))
            self.baked.append((slot, text))
        if blocks:
            self.t3d = "Begin Map\n" + "\n".join(b.strip("\n") for b in blocks) + "\nEnd Map\n"
        return bool(blocks), moved

    def u2bake(self, ed, ops, dry):
        if ops is None:
            self.log("  --bake needs the ops DLL (not with --no-ops): skipped")
            return
        mv = os.path.join(self.work, "scene.u2mv")
        bk = os.path.join(self.work, "scene.u2bk")
        if not dry:
            from uedlib import short_path
            work = short_path(self.work)
            mv, bk = os.path.join(work, "scene.u2mv"), os.path.join(work, "scene.u2bk")
        ops.exec("!meshverts * " + mv)
        cmd = [sys.executable, U2BAKE, "--scene", mv, "--u2bk", bk, "--mode", "add", "--out", ""]
        self.log("  run> " + " ".join(cmd))
        if not dry:
            subprocess.run(cmd, check=True)
        ops.exec("!bakeload " + bk)


# ---------------------------------------------------------------------------------------------- talking to the game
def state_of(text):
    """PanelState's fields (the game's view: seq, wseq, commit=...)"""
    keys, _ = section(text, SECTION)
    st = {}
    for tok in keys.get("panelstate", "").split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            st[k] = v
    return keys, st


def q_lines(session, cmds, k0=1):
    return ["gm q %d %d %s" % (session, k0 + i, c) for i, c in enumerate(cmds)]


def panel_merge(ours, session, path=PANEL):
    """U2GMPanel.txt keeps every other session's lines (the fork's panel) plus ours, written whole"""
    keep = []
    try:
        for line in open(path, "r", encoding="latin-1").read().splitlines():
            if line.strip() and not line.startswith("gm q %d " % session):
                keep.append(line.rstrip())
    except OSError:
        pass
    text = "\r\n".join(keep + ours) + ("\r\n" if keep or ours else "")
    tmp = path + ".gmc.tmp"
    with open(tmp, "w", encoding="latin-1", newline="") as f:
        f.write(text)
    for _ in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:          # the game or the fork has it open
            time.sleep(0.1)
    raise OSError("couldn't write " + path)


def send(cmds, wait=120, log=print):
    """q-lines in a fresh watcher session; waits until PanelState's wseq says the game ran the last one,
    rewriting them if the panel's flush dropped them; then takes them out of the file"""
    session = WATCH_BASE + (int(time.time()) & 0x3fffffff)
    lines = q_lines(session, cmds)
    panel_merge(lines, session)
    log("sent %d line(s) to the game (session %d)" % (len(lines), session))
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(1.0)
        try:
            _, st = state_of(read_text(INI))
        except (OSError, UnicodeError):
            continue
        s, _, k = st.get("wseq", "0:0").partition(":")
        if s == str(session) and int(k or 0) >= len(lines):
            panel_merge([], session)
            log("the game took them")
            return True
        try:
            present = "gm q %d " % session in open(PANEL, encoding="latin-1").read()
        except OSError:
            present = False
        if not present:
            panel_merge(lines, session)
    log("the game didn't take the lines in %d s (is it running with U2GM?); they stay in %s" % (wait, PANEL))
    return False


def status(text):
    """System\\U2GMCommit.status: one line the panel shows"""
    try:
        with open(STATUS + ".tmp", "w", encoding="latin-1") as f:
            f.write(text.encode("latin-1", "replace").decode("latin-1")[:250] + "\r\n")
        os.replace(STATUS + ".tmp", STATUS)
    except OSError:
        pass


# ---------------------------------------------------------------------------------------------- the commit
def commit(family, source, lines, stamp=0, out=None, dry=False, use_ops=True, full_light=False, bake=False,
           paths=False, work=None, heightmap=None, terrain=None, log=print):
    out = out or next_live(source)
    work = work or os.path.join(tempfile.gettempdir(), "gm_commit", out)
    os.makedirs(work, exist_ok=True)
    b = Bake(lines, source, out, stamp, work, use_ops, full_light, bake, paths, log)
    log("commit %s: %d journal line(s) of @%s, %s -> %s%s" % (stamp, len(lines), family, source, out,
                                                               " (dry run)" if dry else ""))
    if dry:
        ed = DryEd(heightmap, terrain, log)
        b.run(ed, DryOps(ed) if use_ops else None)
    else:
        sys.path.insert(0, BRIDGE)
        os.environ.setdefault("U2ED_WITH_GAME", "1")      # the game runs beside it (carve.py's rule)
        from uedlib import session
        session(b.run)
        if not os.path.exists(os.path.join(MAPS, out + ".un2")):
            raise RuntimeError("UnrealEd didn't save " + out)
    if b.t3d:
        open(os.path.join(work, "gm_import.t3d"), "w", encoding="utf-8").write(b.t3d)
        log("--- T3D (%s) ---\n%s--- end T3D ---" % (os.path.join(work, "gm_import.t3d"), b.t3d))
    for s, t, why in b.skipped:
        log("  not baked, keeps replaying: line %d '%s' (%s)" % (s, t, why))
    for p in b.pngs:
        log("  terrain picture: " + p)
    rec = {"stamp": stamp, "family": family, "source": source, "out": out, "dry": dry,
           "baked": b.baked, "skipped": b.skipped, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(rec, open(os.path.join(work, "commit.json"), "w"), indent=1)
    return b, out, work


def answer(stamp, out, baked, log=print):
    cmds = ["baked %d %d %s" % (stamp, s, t) for s, t in sorted(baked)]
    cmds += ["committed %d %s %d" % (stamp, out, len(baked)), "travel " + out]
    return send(cmds, log=log)


def load_state():
    try:
        return json.load(open(STATE))
    except (OSError, ValueError):
        return {}


def watch(args):
    print("watching %s for 'gm commit' (Ctrl+C stops)" % INI)
    status("watcher up, waiting for gm commit")
    st = load_state()
    last_beat = 0
    while True:
        time.sleep(1.0)
        if time.time() - last_beat > 30:
            status("watcher up, waiting for gm commit")      # keeps the panel's "watcher" line fresh
            last_beat = time.time()
        try:
            text = read_text(INI)
        except (OSError, UnicodeError):
            continue
        keys, _ = state_of(text)
        req = keys.get("commitrequest", "").split()
        cst = keys.get("commitstatus", "").split()
        if len(req) < 3 or len(cst) < 2 or cst[1] != "pending" or cst[0] != req[1]:
            continue
        family, stamp, source = req[0], int(req[1]), req[2]
        if st.get("done", {}).get(family) == stamp:
            continue
        lines = journal(text, family, args.section, args.key)
        print("\n%s commit %d of %s on %s: %d line(s)" % (time.strftime("%H:%M:%S"), stamp, family, source, len(lines)))
        status("commit %d: baking %d line(s) of %s into the next %s copy..." % (stamp, len(lines), source, family))
        try:
            if not lines:
                raise RuntimeError("no journal lines for @" + family)
            b, out, work = commit(family, source, lines, stamp, use_ops=not args.no_ops, full_light=args.full_light,
                                  bake=args.bake, paths=args.paths)
            if not b.baked:
                raise RuntimeError("nothing could be baked (see the watcher's console)")
            status("commit %d: saved %s, sending the game there" % (stamp, out))
            answer(stamp, out, b.baked)
            status("commit %d done: %s (%d line(s) baked, %d kept live)" % (stamp, out, len(b.baked), len(b.skipped)))
        except Exception as e:                               # noqa: the game must hear about it
            why = re.sub(r"[^A-Za-z0-9 ._:,+-]", " ", str(e).splitlines()[0] if str(e) else type(e).__name__)[:120]
            print("commit failed:", e)
            status("commit %d failed: %s" % (stamp, why))
            send(["commitfail %d %s" % (stamp, why)])
        st.setdefault("done", {})[family] = stamp
        json.dump(st, open(STATE, "w"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ini", default=INI)
    ap.add_argument("--section", default=SECTION)
    ap.add_argument("--key", default=KEY)
    ap.add_argument("--family")
    ap.add_argument("--map", help="source map (default: the game's CommitRequest, else the newest _LiveN)")
    ap.add_argument("--out-map")
    ap.add_argument("--out", help="work folder (terrain BMPs/PNGs, the T3D, commit.json)")
    ap.add_argument("--heightmap", help="dry run: a G16 BMP standing in for the exported heightmap")
    ap.add_argument("--terrain", help="dry run: LOCX,LOCY,LOCZ,SX,SY,SZ of the TerrainInfo (default TutA's)")
    ap.add_argument("--no-ops", action="store_true")
    ap.add_argument("--full-light", action="store_true")
    ap.add_argument("--bake", action="store_true")
    ap.add_argument("--paths", action="store_true")
    ap.add_argument("--no-send", action="store_true")
    a = ap.parse_args(argv)
    if a.watch:
        return watch(a)
    if not os.path.exists(a.ini) and os.path.exists(os.path.join(SYS, a.ini)):
        a.ini = os.path.join(SYS, a.ini)              # a bare name: the game's System folder
    text = read_text(a.ini)
    keys, _ = section(text, a.section)
    req = keys.get("commitrequest", "").split()
    family = (a.family or (req[0] if req else None) or (family_of(a.map) if a.map else None))
    if not family:
        raise SystemExit("which map family? --family tuta (no CommitRequest in %s)" % a.ini)
    family = family.lower()
    stamp = int(req[1]) if len(req) > 1 and req[0] == family else 0
    if a.map:
        source = a.map
    elif len(req) > 2 and req[0] == family:
        source = req[2]
    else:
        names = map_names()
        source = source_map(family, names) if names else family
    lines = journal(text, family, a.section, a.key)
    terrain = None
    if a.terrain:
        v = [float(x) for x in a.terrain.split(",")]
        terrain = dict(TUTA_TERRAIN, Location=tuple(v[:3]), Scale=tuple(v[3:6]))
    names = map_names()
    out = a.out_map or next_live(source, names)
    work = a.out
    b, out, work = commit(family, source, lines, stamp, out, a.dry_run, not a.no_ops, a.full_light, a.bake, a.paths,
                          work, a.heightmap, terrain)
    print("baked %d line(s), %d kept live; work folder %s" % (len(b.baked), len(b.skipped), work))
    if a.dry_run:
        print("game lines that would follow:")
        for c in ["baked %d %d %s" % (stamp, s, t) for s, t in sorted(b.baked)] + \
                 ["committed %d %s %d" % (stamp, out, len(b.baked)), "travel " + out]:
            print("  gm q <watcher session> K " + c)
    elif not a.no_send and stamp:
        answer(stamp, out, b.baked)
    elif not a.no_send:
        print("no pending CommitRequest: the game isn't told (travel by hand: gm travel %s)" % out)


if __name__ == "__main__":
    main()
