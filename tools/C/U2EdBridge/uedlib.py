r"""uedlib - recipes on top of u2ed.Editor: the things every U2 build script re-invented.

    from uedlib import Ed, short_path
    with Ed.start() as ed:
        ed.load("TutA")                                   # Maps\TutA.un2 (name or full path)
        ed.import_texture(r"C:\x\island1.bmp", "island1", "MyLevel", "terrain_maps", MIPS=0)
        infos = ed.actors("TerrainInfo")                  # placed actors as dicts (T3D round trip)
        ed.replace_actors("TerrainInfo", lambda t3d: t3d) # copy -> delete -> re-import (rebuilds terrain)
        ed.view(0, 0, 4000, pitch=-2000, yaw=16384)       # move the perspective camera
        ed.screenshot("view.png")                         # the editor window, viewport cropped
        ed.save("TutA_Liandri")

Every recipe raises CommandFailed when the editor logged a failure ("Can't ...", "Bad image format", ...)
instead of returning quietly, so a script stops at the real cause. Lessons encoded here (see README):
  * Unreal cannot take paths with spaces: short_path() turns any path into its 8.3 form.
  * TEXTURE IMPORT rejects RLE TGAs and non-8/24/32-bit TGAs; a G16 heightmap must be a 16-bit BMP.
  * Only the FIRST `BRUSH LOAD` of an editor session takes effect (load_brush() warns on a second one).
  * GET/SET work on class defaults only; placed actors are read through EDIT COPY (clipboard T3D).
  * `ACTOR SELECT NAME=` does not exist in this editor; select by class, then filter in Python.
  * SET <Class> on Info/ZoneInfo is class-wide; the bridge patch makes it safe, but it still edits every
    object of that class (the sea's TerrainInfo too).
"""
import ctypes, ctypes.wintypes as wt, os, re, struct, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u2ed  # noqa
from u2ed import Editor, EditorCrashed, BridgeError  # noqa

u32, g32, k32 = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.kernel32

# one regex per failure line UnrealEd logs (anchored at the line start: actor names and texture names
# contain words like Error/Missing, and "Matched Viewport ..." lines are noise)
FAIL_RE = re.compile(r"(?m)^(?:Can't |Can not |Cannot |Bad image format|Failed to |Unrecognized |Invalid |"
                     r"Error[: ]|Unknown command|Not found|No such|Couldn't |Could not )")


class CommandFailed(RuntimeError):
    def __init__(self, command, output):
        super().__init__("%s\n%s" % (command, output.strip()[-800:]))
        self.command, self.output = command, output


def short_path(p):
    """8.3 form of an existing path (Unreal's parser breaks on spaces and parentheses)"""
    p = os.path.abspath(p)
    buf = ctypes.create_unicode_buffer(1024)
    if k32.GetShortPathNameW(p, buf, 1024):
        return buf.value
    return p


def game_dir():
    return short_path(u2ed.GAME)


def check_tga(path):
    """raise before UnrealEd does: RLE or odd bit depth TGAs come back as 'Bad image format'"""
    h = open(path, "rb").read(18)
    if len(h) < 18:
        raise ValueError("%s: not a TGA" % path)
    typ, bpp = h[2], h[16]
    if typ in (9, 10, 11):
        raise ValueError("%s: RLE TGA, UnrealEd wants TARGA_RAW" % path)
    if bpp not in (8, 24, 32):
        raise ValueError("%s: %d-bit TGA, UnrealEd wants 8/24/32" % (path, bpp))
    w, hgt = struct.unpack_from("<HH", h, 12)
    for v in (w, hgt):
        if v & (v - 1):
            raise ValueError("%s: %dx%d is not a power of two" % (path, w, hgt))
    return w, hgt, bpp


def check_bmp(path):
    raw = open(path, "rb").read(30)
    if raw[:2] != b"BM":
        raise ValueError("%s: not a BMP" % path)
    w, hgt = struct.unpack_from("<ii", raw, 18)
    bpp = struct.unpack_from("<H", raw, 28)[0]
    return w, abs(hgt), bpp


# --- T3D ---------------------------------------------------------------------------------------------
_VEC = re.compile(r"(\w+)=(-?[\d.eE+-]+)")


def t3d_actors(text):
    """[{'Class':..., 'Name':..., 'Location': (x,y,z), 'Rotation': (p,y,r), 'props': {k: v}, 'text': block}]"""
    out = []
    for m in re.finditer(r"Begin Actor (.*?)\n(.*?)^End Actor", text, re.S | re.M):
        head, body = m.group(1), m.group(2)
        a = {"props": {}, "text": m.group(0)}
        for k, v in re.findall(r"(\w+)=(\S+)", head):
            a[k] = v
        for line in body.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith(("Begin", "End")):
                k, v = line.split("=", 1)
                a["props"][k] = v
        for key in ("Location", "Rotation"):
            v = a["props"].get(key)
            if v:
                d = dict((k, float(x)) for k, x in _VEC.findall(v))
                a[key] = ((d.get("X", 0.0), d.get("Y", 0.0), d.get("Z", 0.0)) if key == "Location"
                          else (int(d.get("Pitch", 0)), int(d.get("Yaw", 0)), int(d.get("Roll", 0))))
        out.append(a)
    return out


def t3d_set(block, key, value):
    """set/replace one property line in an actor block"""
    line = "    %s=%s" % (key, value)
    if re.search(r"(?m)^\s*%s=" % re.escape(key), block):
        return re.sub(r"(?m)^\s*%s=.*$" % re.escape(key), line, block, count=1)
    return block.replace("\nEnd Actor", "\n%s\nEnd Actor" % line, 1)


def t3d_map(blocks):
    return "Begin Map\n" + "\n".join(b.strip("\n") for b in blocks) + "\nEnd Map\n"


def clipboard_text():
    for _ in range(20):
        if u32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise OSError("clipboard busy")
    try:
        u32.GetClipboardData.restype = ctypes.c_void_p
        h = u32.GetClipboardData(13)       # CF_UNICODETEXT
        if not h:
            return ""
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]
        k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        p = k32.GlobalLock(h)
        if not p:
            return ""
        try:
            return ctypes.wstring_at(p)
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()


# --- window capture (no PIL) -------------------------------------------------------------------------
def _png(w, h, bgra):
    raw = bytearray()
    for y in range(h):
        row = bgra[y * w * 4:(y + 1) * w * 4]
        raw.append(0)
        raw += bytes(b for i in range(0, len(row), 4) for b in (row[i + 2], row[i + 1], row[i]))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


class _BMI(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


def capture_window(hwnd, path, crop=None):
    """PrintWindow(PW_RENDERFULLCONTENT) of hwnd -> PNG; crop = (l, t, r, b) in window pixels"""
    u32.SetProcessDPIAware()
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)
    bi = _BMI(biSize=ctypes.sizeof(_BMI), biWidth=w, biHeight=-h, biPlanes=1, biBitCount=32)
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(hwnd, hdc)
    data = buf.raw
    if crop:
        l, t, rr, b = crop
        l, t = max(0, l), max(0, t)
        rr, b = min(w, rr), min(h, b)
        data = b"".join(data[(y * w + l) * 4:(y * w + rr) * 4] for y in range(t, b))
        w, h = rr - l, b - t
    with open(path, "wb") as f:
        f.write(_png(w, h, data))
    return w, h


def viewport_rects(hwnd):
    """the editor's viewport windows as {title: (l, t, r, b)} relative to the frame window. Titles seen on
    this editor: 'Viewport' (the perspective view), 'Overhead map', 'XZ map', 'YZ map'."""
    fr = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(fr))
    rects = {}

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(c, _):
        b = ctypes.create_unicode_buffer(128)
        u32.GetClassNameW(c, b, 128)
        if b.value.endswith("WindowsViewportWindow") and u32.IsWindowVisible(c):
            r = wt.RECT()
            u32.GetWindowRect(c, ctypes.byref(r))
            t = ctypes.create_unicode_buffer(128)
            u32.GetWindowTextW(c, t, 128)
            rects[t.value] = (r.left - fr.left, r.top - fr.top, r.right - fr.left, r.bottom - fr.top)
        return True
    u32.EnumChildWindows(hwnd, cb, 0)
    return rects


# --- the recipes ---------------------------------------------------------------------------------------
class Ed(Editor):
    brush_loads = 0

    # -- plumbing --
    def ok(self, command, allow=()):
        """exec and raise CommandFailed when the editor logged a failure (allow = substrings that are fine)"""
        rc, out = self.exec_rc(command)
        bad = [m.group(0) for m in re.finditer(r"(?m)^.*$", out)
               if FAIL_RE.match(m.group(0)) and not any(a in m.group(0) for a in allow)]
        if bad:
            raise CommandFailed(command, out + "\n-- failure lines: " + " | ".join(b.strip() for b in bad[:5]))
        return out

    def quiet(self, command):
        return self.exec_rc(command)[1]

    def main_window(self):
        hs = [h for h in u2ed._windows(self.pid)]
        best, area = None, 0
        for h in hs:
            r = wt.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            a = (r.right - r.left) * (r.bottom - r.top)
            if a > area:
                best, area = h, a
        return best

    # -- maps --
    def map_path(self, name):
        if os.path.sep in name or name.lower().endswith(".un2"):
            return short_path(name) if os.path.exists(name) else name
        return r"%s\Maps\%s.un2" % (game_dir(), name)

    def load(self, name):
        return self.ok(r'MAP LOAD FILE="%s"' % self.map_path(name), allow=("Can't find file for package", "Can't find"))

    def save(self, name):
        p = self.map_path(name)
        out = self.ok(r'MAP SAVE FILE="%s"' % p)
        if not os.path.exists(p):
            raise CommandFailed("MAP SAVE", "file not written: " + p)
        return out

    def new(self):
        return self.ok("MAP NEW")

    def rebuild(self):
        return self.ok("MAP REBUILD", allow=("Can't", "Couldn't bring window"))

    def light(self, selected=False):
        """LIGHT APPLY. WARNING (decompile, 2026-10-07): Exec_Light parses SELECTED= but
        shadowIlluminateBsp never reads it, so SELECTED=1 is a FULL relight (BSP lightmaps reallocated
        and every static mesh relit). CHANGED=1 is the real incremental mode; for static meshes only use
        Ops.light(). See EDITOR_OPS.md / LIGHTING.md."""
        # "Couldn't bring window to foreground" is logged when another app has focus; harmless
        return self.ok("LIGHT APPLY" + (" SELECTED=1" if selected else ""), allow=("Couldn't bring window", "Can't find"))

    def paths(self, full=False):
        return self.ok("PATHS BUILD" if full else "PATHS DEFINE")

    def import_t3d(self, path, add=True):
        # "Invalid name: <Class>" is logged for every pasted actor whose name is taken and is harmless
        return self.ok(r'MAP %s FILE="%s"' % ("IMPORTADD" if add else "IMPORT", short_path(path)),
                       allow=("Can't find file for package", "Invalid name:"))

    def export_t3d(self, path=None):
        """the level as T3D text (what the editor really built: brushes with vertices, every actor)"""
        path = path or os.path.join(os.environ.get("TEMP", HERE), "u2ed_export.t3d")
        self.ok(r'MAP EXPORT FILE="%s"' % path)
        return open(path, encoding="utf-8", errors="replace").read()

    def load_package(self, path):
        return self.ok(r'OBJ LOAD FILE="%s"' % short_path(path))

    def save_package(self, package, path):
        return self.ok(r'OBJ SAVEPACKAGE PACKAGE="%s" FILE="%s"' % (package, path))

    # -- assets --
    def import_texture(self, path, name, package, group=None, **flags):
        """TEXTURE IMPORT with the file checked first; flags: MIPS=1 ALPHA=1 UCLAMPMODE=CLAMP ..."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".tga":
            check_tga(path)
        elif ext == ".bmp":
            check_bmp(path)
        f = " ".join("%s=%s" % kv for kv in flags.items())
        g = ' GROUP="%s"' % group if group else ""
        return self.ok(r'TEXTURE IMPORT FILE="%s" NAME="%s" PACKAGE="%s"%s %s' % (short_path(path), name, package, g, f))

    def import_staticmesh(self, path, package, group, name):
        return self.ok(r'NEW StaticMeshFactory PACKAGE="%s" GROUP="%s" NAME="%s" FILE="%s"'
                       % (package, group, name, short_path(path)))

    def load_brush(self, path):
        """the builder brush from a .u3d; only the first load per session takes effect (measured)"""
        Ed.brush_loads += 1
        if Ed.brush_loads > 1:
            print("uedlib: WARNING second BRUSH LOAD in this session is ignored by UnrealEd", file=sys.stderr)
        return self.ok(r'BRUSH LOAD FILE="%s"' % short_path(path))

    # -- actors --
    def select_class(self, cls, subclasses=False):
        self.quiet("ACTOR SELECT NONE")
        return self.ok("ACTOR SELECT %s CLASS=%s" % ("OFSUBCLASS" if subclasses else "OFCLASS", cls))

    def deselect(self):
        self.quiet("ACTOR SELECT NONE")

    def copy_selected(self):
        """EDIT COPY -> the clipboard T3D of the selected actors"""
        self.quiet("EDIT COPY")
        for _ in range(20):
            t = clipboard_text()
            if "Begin Actor" in t:
                return t
            time.sleep(0.1)
        return ""

    def actors(self, cls=None, subclasses=False):
        """placed actors (of one class, or all) as dicts; see t3d_actors()"""
        if cls:
            self.select_class(cls, subclasses)
            t = self.copy_selected()
            self.deselect()
        else:
            t = self.export_t3d()
        return t3d_actors(t)

    def replace_actors(self, cls, edit, subclasses=False):
        """copy every <cls> actor as T3D, delete them, run edit(t3d_text) -> new text, import it back.
        A pasted actor is rebuilt from its properties (a TerrainInfo re-reads its heightmap), which is
        the one way to re-run PostLoad-style work the editor otherwise skips."""
        self.select_class(cls, subclasses)
        t = self.copy_selected()
        if "Begin Actor" not in t:
            self.deselect()
            raise CommandFailed("EDIT COPY " + cls, "no %s actors copied" % cls)
        new = edit(t) if edit else t
        if new is None:
            self.deselect()
            return 0
        if "Begin Map" not in new:
            new = "Begin Map\n" + new + "\nEnd Map\n"
        path = os.path.join(os.environ.get("TEMP", HERE), "u2ed_replace_%s.t3d" % cls)
        open(path, "w", encoding="utf-8").write(new)
        self.ok("ACTOR DELETE")
        self.import_t3d(path, add=True)
        return new.count("Begin Actor")

    def set_default(self, cls, prop, value):
        """SET <class> <prop> <value>: class defaults AND every placed actor of that class"""
        return self.ok("SET %s %s %s" % (cls, prop, value))

    def hide_icons(self, classes=("Light", "Triggers", "Keypoint", "NavigationPoint", "AmbientSound", "PlayerStart")):
        for c in classes:
            self.quiet("SET %s bHiddenEd True" % c)

    # -- camera & pictures --
    def view(self, x, y, z, pitch=0, yaw=0, roll=0):
        """put the perspective camera at (x,y,z) looking (pitch,yaw) - UE rotation units, 65536 = turn"""
        for c in ("SET PlayerStart bHiddenEd False",
                  "SET PlayerStart Location (X=%d,Y=%d,Z=%d)" % (x, y, z),
                  "ACTOR SELECT NONE", "ACTOR SELECT OFCLASS CLASS=PlayerStart", "CAMERA ALIGN",
                  "ACTOR SELECT NONE", "SET PlayerStart bHiddenEd True",
                  "SET Camera Rotation (Pitch=%d,Yaw=%d,Roll=%d)" % (pitch, yaw, roll),
                  "ACTOR SELECT OFCLASS CLASS=SectorCommander", "ACTOR SELECT NONE"):
            self.quiet(c)
        time.sleep(0.4)

    def screenshot(self, path, viewport=True):
        """the editor's main window as PNG; viewport=True crops to the perspective view, a title
        ('Overhead map', 'XZ map', 'YZ map') picks another, False keeps the whole window"""
        h = self.main_window()
        if not h:
            raise BridgeError("no editor window")
        crop = None
        if viewport:
            rects = viewport_rects(h)
            if isinstance(viewport, str):
                crop = rects.get(viewport)
            elif rects:
                crop = rects.get("Viewport") or max(rects.values(), key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        return capture_window(h, path, crop)


# --- per-actor ops (bin\U2EdBridge_ops.dll, src/editor_ops.c; EDITOR_OPS.md) ------------------------------
OPS_PIPE = r"\\.\pipe\U2EdBridgeOps-%d"
OPS_DLL = os.path.join(u2ed.BIN, "U2EdBridge_ops.dll")


class Ops(Editor):
    """Client of the ops build, injected BESIDE the normal bridge (own pipe and window message):
        ops = Ops.attach_to(ed.pid)        # injects bin\\U2EdBridge_ops.dll once, then talks to it
        ops.select("StaticMeshActor12", "Tower*")
        ops.move("StaticMeshActor12", 100, 200, None, yaw=16384)    # None keeps a value
        ops.light("selected")              # static-mesh vertex lighting only; BSP lightmaps untouched
        print(ops.lights("StaticMeshActor12"))   # why is it dark: zone ambient + the lights it can get
    Its ! commands also run plain editor commands (same Exec), but use Ed for those."""

    @classmethod
    def attach_to(cls, pid, timeout=20):
        o = cls(pid)
        if not os.path.exists(OPS_PIPE % pid):
            exe = os.path.join(u2ed.BIN, "u2edinject.exe")
            import subprocess
            r = subprocess.run([exe, str(pid), OPS_DLL], capture_output=True, text=True)
            if r.returncode:
                raise BridgeError("ops injection failed: " + (r.stderr or r.stdout).strip())
        o.wait_ready(timeout)     # the DLL waits ~3 s after load before it listens
        return o

    def exec_rc(self, command):
        if self.pipe is None:
            self.pipe = open(OPS_PIPE % self.pid, "r+b", buffering=0)
        return super().exec_rc(command)

    def stop(self):               # never quits the editor: it belongs to the Ed session
        self.close()

    def _ok(self, command):
        rc, out = self.exec_rc(command)
        if not rc or FAIL_RE.search(out) or out.startswith("ops:"):
            raise CommandFailed(command, out)
        return out

    def select(self, *names, add=False):
        return self._ok("!select %s%s" % ("+ " if add else "", " ".join(names)))

    def deselect(self, *names):
        return self._ok("!deselect " + (" ".join(names) or "all"))

    def list(self, pattern="*", cls=None):
        """[(name, class, (x,y,z), (pitch,yaw,roll), selected)]"""
        out = self.exec("!list %s%s" % (pattern, " class=" + cls if cls else ""))
        rows = []
        for line in out.splitlines():
            m = re.match(r"(\S+) (\S+) \((.*?)\) \((.*?)\)( selected)?$", line)
            if m:
                loc = dict((k, float(v)) for k, v in _VEC.findall(m.group(3)))
                rot = dict((k, int(float(v))) for k, v in _VEC.findall(m.group(4)))
                rows.append((m.group(1), m.group(2), (loc.get("X", 0.0), loc.get("Y", 0.0), loc.get("Z", 0.0)),
                             (rot.get("Pitch", 0), rot.get("Yaw", 0), rot.get("Roll", 0)), bool(m.group(5))))
        return rows

    @staticmethod
    def _args(vals):
        return " ".join("-" if v is None else ("%g" % v) for v in vals)

    def move(self, name, x=None, y=None, z=None, pitch=None, yaw=None, roll=None):
        """absolute; name must match one actor (or 'selected' with one selected)"""
        rot = (pitch, yaw, roll)
        tail = (" " + self._args(rot)) if any(v is not None for v in rot) else ""
        return self._ok("!move %s %s%s" % (name, self._args((x, y, z)), tail))

    def move_by(self, pattern, dx=0, dy=0, dz=0, dpitch=0, dyaw=0, droll=0):
        tail = (" %d %d %d" % (dpitch, dyaw, droll)) if (dpitch or dyaw or droll) else ""
        return self._ok("!moveby %s %g %g %g%s" % (pattern, dx, dy, dz, tail))

    def light(self, *names):
        return self._ok("!light " + " ".join(names or ("selected",)))

    def lights(self, name):
        return self.exec("!lights " + name)

    def lights_at(self, x, y, z):
        return self.exec("!lightsat %g %g %g" % (x, y, z))


def park_windows(pid, x=-3000, y=0):
    """move the editor's top-level windows off the left edge of the desktop (no activation, no resize):
    a mouse passing over the viewport while a TerrainInfo rebuilds crashes UnrealEd
    (ATerrainInfo::LineCheckWithQuad <- MousePosition <- WM_MOUSEMOVE, seen 2026-10-07)"""
    found = []
    proto = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        p = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    u32.EnumWindows(proto(cb), 0)
    for h in found:
        u32.SetWindowPos(h, 0, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010)     # NOSIZE | NOZORDER | NOACTIVATE
    return len(found)


def session(fn, *a, **k):
    """run fn(ed) in a fresh editor and always stop it (dgVoodoo back), printing the crash text if any.
    The editor's windows are parked off-screen (U2ED_PARK=0 keeps them where they open)."""
    ed = Ed.start()
    if os.environ.get("U2ED_PARK", "1") != "0":
        park_windows(ed.pid)
    try:
        return fn(ed, *a, **k)
    except EditorCrashed as e:
        print("UnrealEd crashed:", e, file=sys.stderr)
        raise
    finally:
        ed.stop()


if __name__ == "__main__":
    # smoke test: load a map, list TerrainInfos, take one picture
    name = sys.argv[1] if len(sys.argv) > 1 else "TutA"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "shots", "uedlib_test.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    def test(ed):
        ed.load(name)
        for a in ed.actors("TerrainInfo"):
            print(a["Class"], a["Name"], a.get("Location"), a["props"].get("TerrainMap"), a["props"].get("TerrainScale"))
        starts = ed.actors("PlayerStart")
        print(len(starts), "PlayerStart(s)")
        ed.hide_icons()
        x, y, z = starts[0]["Location"] if starts else (0, 0, 0)
        ed.view(x, y, z + 40, pitch=-600, yaw=16384)
        print("shot", ed.screenshot(out), out)
    session(test)
