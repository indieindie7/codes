r"""The Avalon remake's editor build (redesign 2026-10-09, plan s.7 Phase B), on top of a finished town.py run.

    py tools/remake_build.py <run folder> <map built by town.py> [out=TutA_Remake] [stage=t3d|mesh|map|paths|specs|bsp|patchin|arenas|patchlayers|all] [maps=A,B (bsp)]
                             [pkg=AvalonSM4] [entry=stair|hatch] [tower=0|1] [start=dock|tower]

town.py already builds the terrain, buildings, clutter, lighting and low sun into Maps\<map>. This adds what the
redesign needs and town.py doesn't do, without editing town.py (the Advent chat's file):
  mesh   the story parts (STORY_ASSETS.md s.1: drain, taps, hollow kit, process parts; 39 ASEs in Models/ase) as
         a package of their own, StaticMeshes\<pkg>.usx, with its own copy of Pal (same pixels, so the fork's
         world_detail rule hash d9fc7585 still matches); a package the game has loaded can't be replaced: bump pkg=
  t3d    (CPU only) <run>\remake_story.t3d   the drain + taps (story_export.py, pkg=<pkg>.Liandri)
                    <run>\remake_shells.t3d  the hollow shells (shells.py, pkg=<pkg>.Liandri); tower=1 adds the
                                              tower lobby shell (it overlaps TutA's own tower BSP)
                    <run>\remake_arenas.t3d  the greybox fights E1-E4 from L["arenas"] (anchors.py): full / half
                                              cover as B_k_slab boxes (top at the actor Z: 140 / 80 UU high), the
                                              spawns, high spots, entries and arrivals as PathNodes tagged
                                              Arena_<id>_<kind> (the encounter scripting finds them by tag)
                    <run>\remake_paths.t3d   isl_paths.t3d (pathlinks.py) as is: imported AFTER the lighting
  map    copy Maps\<map> -> Maps\<out>, load the package, remove the solid meshes the shells replace
         (hollow.json: Liandri building meshes within 6 m of the building's layout point), IMPORTADD the three T3Ds in chunks of <= 150 actors (one 850-actor import crashed UnrealEd),
         light the new actors, move the PlayerStart (start=dock: the dock, facing the spine, plan D6 for generated
         maps; start=tower: TutA's command room, pitch -15 = 62805, compose.PITCH_RU), save
  paths  load <out>, LevelInfo PathSizes = 3 sizes (pathsizes=), IMPORTADD remake_paths.t3d, PATHS DEFINE, save
         (paths after LIGHT APPLY: the Sanctuary gotcha)
Not automated (STORY_ASSETS.md s.3, by hand / U2GM): the drain grate's terrain hole (isl_story_notes.json has the
rectangle), the gallery movers, the drain lamps and beacon, interior lights, Door nav points. TutA.un2 is never
written; the swap is a separate, tested step.
"""
import json, math, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(HERE, "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
MAPS = os.path.join(GAME, "Maps")
M = 50.0

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
RUN, SRC_MAP = args[0], args[1]
OUT = o.get("out", "TutA_Remake")
STAGE = o.get("stage", "all")
PKG = o.get("pkg", "AvalonSM4")
LIB = PKG + ".Liandri"
L = json.load(open(os.path.join(RUN, "isl_layout.json")))


def run(cmd):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode:
        sys.exit("failed: %s" % cmd[1])


def story_parts():
    """the ASE names STORY_ASSETS.md s.1 lists (its table rows `B_name`)"""
    txt = open(os.path.join(TOOLS, "STORY_ASSETS.md"), encoding="utf-8").read()
    names = []
    for n in re.findall(r"^\| `(B_\w+)` \|", txt, re.M):
        if n not in names:
            names.append(n)
    return names


# ---- t3d ------------------------------------------------------------------------------------------------------
def slab_box(x, y, z_top, w, d, h, yaw_deg, label):
    """a greybox block from the kit slab (200 x 200 x 15 UU, top at the actor's Z)"""
    return ("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'%s.B_k_slab'\n"
            "    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n    Rotation=(Yaw=%d)\n    DrawScale3D=(X=%.3f,Y=%.3f,Z=%.3f)\n"
            "    Tag=%s\n    bStatic=True\nEnd Actor" % (LIB, x, y, z_top, int(round(yaw_deg * 65536 / 360)) % 65536,
                                                     w / 200.0, d / 200.0, h / 15.0, label))


def path_node(x, y, z, tag):
    return "Begin Actor Class=PathNode\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n    Tag=%s\nEnd Actor" % (x, y, z, tag)


def arena_actors():
    """cover on the ground under each piece (the arena floors are only partly level: roads re-grade through them),
    never below the sea; pieces over the sea are left out"""
    import story_export  # noqa
    ground = story_export.ground_fn(os.path.join(RUN, "isl_ec.bmp"))
    A, n, sea = [], {}, 0
    for aid, a in sorted((L.get("arenas") or {}).items()):
        if not a.get("placed"):
            print("  arena %s not placed: %s" % (aid, a.get("why")))
            continue
        for p in a["pieces"]:
            k = p["kind"]
            z = ground(p["x"], p["y"])
            if z <= -4967 + 40 and k in ("full", "half", "spawn", "high", "entry", "exit", "P"):
                sea += 1
                continue
            tag = re.sub(r"\W+", "_", "Arena_%s_%s" % (aid, k))
            if k in ("full", "half"):
                h = 140 if k == "full" else 80
                A.append(slab_box(p["x"], p["y"], z + h, p["w"], p["d"], h, p["yaw"], tag))
            elif k in ("spawn", "high", "entry", "exit", "P"):
                A.append(path_node(p["x"], p["y"], z + p.get("z_up", 0) + 60, tag))
            else:
                continue          # solid / pillar / water / terrace / deck: the real buildings and ground stand there
            n[aid] = n.get(aid, 0) + 1
    if sea:
        print("  arenas: %d pieces over the sea left out" % sea)
    print("  arenas:", n or "none in the layout (needs a run made after anchors.arenas, round 3)")
    return A


def write_t3d(path, actors):
    with open(path, "w", newline="\r\n") as f:
        f.write("Begin Map\n" + "\n".join(actors) + "\nEnd Map\n")
    print("  %s: %d actors" % (os.path.basename(path), len(actors)))


def stage_t3d():
    hm = os.path.join(RUN, "isl_ec.bmp")
    run(["py", os.path.join(TOOLS, "story_export.py"), os.path.join(RUN, "isl_layout.json"),
         "out=" + os.path.join(RUN, "remake_story.t3d"), "pkg=" + LIB, "entry=" + o.get("entry", "stair"), "heightmap=" + hm, "start=dock"])   # + remake_start.json
    run(["py", os.path.join(TOOLS, "shells.py"), RUN, "out=" + os.path.join(RUN, "remake_shells.t3d"), "pkg=" + LIB])
    if o.get("tower") != "1":
        tw = os.path.join(RUN, "remake_shells_tower.t3d")
        if os.path.exists(tw):
            print("  (tower lobby shell left out: tower=1 to import it over TutA's BSP)")
    write_t3d(os.path.join(RUN, "remake_arenas.t3d"), arena_actors())
    shutil.copyfile(os.path.join(RUN, "isl_paths.t3d"), os.path.join(RUN, "remake_paths.t3d"))


# ---- editor ---------------------------------------------------------------------------------------------------
def actors_of(path):
    txt = open(path).read()
    return re.findall(r"Begin Actor.*?End Actor", txt, re.S)


def chunks(path, size=150):
    """the T3D split into files of <= size actors (next to it: <name>_partN.t3d)"""
    A = actors_of(path)
    out = []
    for k in range(0, len(A), size):
        p = "%s_part%d.t3d" % (os.path.splitext(path)[0], k // size)
        write_t3d(p, A[k:k + size])
        out.append(p)
    return out


def ed_session(fn):
    sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
    from uedlib import session  # noqa
    session(fn)


def stage_mesh():
    from uedlib import short_path  # noqa
    pkgfile = os.path.join(GAME, "StaticMeshes", PKG + ".usx")
    if os.path.exists(pkgfile):
        print("  %s exists: meshes already imported (bump pkg= to re-import)" % pkgfile)
        return
    parts = story_parts()
    src = os.path.join(HERE, "Models", "ase")
    missing = [n for n in parts if not os.path.exists(os.path.join(src, n + ".ase"))]
    if missing:
        sys.exit("missing ASEs: %s" % missing)

    def job(ed):
        ed.exec("!answer yes")
        ed.ok('TEXTURE IMPORT FILE="%s" NAME="Pal" PACKAGE="%s" GROUP="Pal" MIPS=0' % (short_path(os.path.join(src, "Pal.tga")), PKG))
        for n in parts:
            ed.import_staticmesh(os.path.join(src, n + ".ase"), PKG, "Liandri", n)
        ed.save_package(PKG, short_path(os.path.dirname(pkgfile)) + "\\" + PKG + ".usx")
    print("  importing %d meshes into %s" % (len(parts), PKG))
    ed_session(job)


def stage_map():
    from uedlib import short_path  # noqa
    shutil.copyfile(os.path.join(MAPS, SRC_MAP + ".un2"), os.path.join(MAPS, OUT + ".un2"))
    hollow = set(json.load(open(os.path.join(RUN, "hollow.json"))).get("hollow", [])) if os.path.exists(os.path.join(RUN, "hollow.json")) else set()
    if o.get("tower") != "1":
        hollow.discard("tower")         # its shell is left out, so its solid stays
    files = []
    for name in ("remake_story", "remake_shells", "remake_arenas") + (("remake_shells_tower",) if o.get("tower") == "1" else ()):
        p = os.path.join(RUN, name + ".t3d")
        if os.path.exists(p) and actors_of(p):
            files += chunks(p)
    start = o.get("start", "dock")

    def job(ed):
        from uedlib import Ops  # noqa
        ed.exec("!answer yes")
        ed.load(OUT)
        ed.load_package(os.path.join(GAME, "StaticMeshes", PKG + ".usx"))
        SMA0 = ed.actors("StaticMeshActor") if hollow else []
        ops = Ops.attach_to(ed.pid)
        # the solid meshes the shells replace: StaticMeshActors tagged with a hollow building's id (export's Tag=)
        if hollow:
            # (export_mutator.py doesn't tag actors: a Liandri building mesh, not road/wall/cable, within 6 m of the
            # hollow building's layout point; a count: building's other instances are listed, check them)
            # every copy of a count: building (shells.instances, the same rule export used)
            import shells, binder  # noqa
            _, sheets = binder.load()
            spots = [(bid, p["x"], p["y"]) for bid in hollow if bid in L["buildings"] and bid in sheets
                     for p in shells.instances(bid, L["buildings"][bid], sheets[bid])]
            names = []
            SMA = SMA0                      # listed before the ops DLL is injected
            print("  %d StaticMeshActors in the map, %d building copies to hollow" % (len(SMA), len(spots)))
            for a in SMA:
                m = a["props"].get("StaticMesh", "")    # the editor writes AvalonSM.B_x (no group)
                if not re.search(r"AvalonSM\.(Liandri\.)?B_", m) or any(k in m for k in ("B_road", "B_wall", "B_cable", "B_k_")):
                    continue
                x, y = a["Location"][0], a["Location"][1]
                hit = [b for b, sx, sy in spots if math.hypot(sx - x, sy - y) < 300]
                if hit:
                    names.append(a["Name"])
                    print("   solid %s (%s) for %s" % (a["Name"], m, hit[0]))
            for k in range(0, len(names), 40):
                ops.select(*names[k:k + 40])
                ed.ok("ACTOR DELETE")
            print("  removed %d solid meshes of %s" % (len(names), sorted(hollow)))
        ed.deselect()
        for p in files:
            ed.import_t3d(p, add=True)
        ed.light(selected=True)
        ed.deselect()
        ps = ed.actors("PlayerStart")
        if ps:
            if start == "dock":
                # story_export.dock_start (e432e5b): the spine point nearest the dock, walked inland until the ground
                # is 40 UU over the sea, Z = ground + 54 + 30, yaw along the spine (remake_start.json)
                st = json.load(open(os.path.join(RUN, "remake_start.json")))
                ops.move(ps[0]["Name"], st["X"], st["Y"], st["Z"], pitch=0, yaw=int(st["Yaw"]) % 65536, roll=0)
            else:
                ops.move(ps[0]["Name"], pitch=62805)      # TutA's command room: compose.PITCH_RU (-15 deg)
        ops.stop()
        ed.save(OUT)
    ed_session(job)


def stage_paths():
    files = chunks(os.path.join(RUN, "remake_paths.t3d"))

    def job(ed):
        ed.exec("!answer yes")
        ed.load(OUT)
        # 3 path sizes instead of U2's 9 (research_notes/Lighter AI pathing for UE2): 28/54 the player-sized,
        # 34/70 the Skaarj, 60/96 the smallest that fits Pawn's default 34/78 (mercs, marines); each pair is walked
        # once per size, so this cuts the define ~3x. A bigger creature on Avalon needs its size added back.
        sizes = o.get("pathsizes", "(Height=54,Radius=28),(Height=70,Radius=34),(Height=96,Radius=60)")
        ed.ok("SET LevelInfo PathSizes (%s)" % sizes)
        li = ed.actors("LevelInfo")
        print("  LevelInfo PathSizes now:", [v for k, v in (li[0]["props"].items() if li else []) if k.startswith("PathSizes")])
        for p in files:
            ed.import_t3d(p, add=True)
        import time
        t0 = time.time()
        ed.paths()                         # PATHS DEFINE
        print("  PATHS DEFINE took %.0f s" % (time.time() - t0))
        ed.save(OUT)
    ed_session(job)


def stage_bsp():
    """TutA's own additive BSP (rocks, ledges, sheds) was sculpted to the OLD island: on the new ground several float
    3-40 m up (the dark floating blocks; the old Q65 floating rock). Delete every CSG_Add brush outside the tower
    complex whose origin is more than 150 UU over the new ground, then MAP REBUILD, LIGHT APPLY, PATHS DEFINE."""
    import story_export  # noqa
    from uedlib import Ops  # noqa
    gz = story_export.ground_fn(os.path.join(RUN, "isl_ec.bmp"))
    TOWER = (-2600, -200, 1200, 3600)            # x0, y0, x1, y1 of TutA's tower complex incl. Brush16, the tower body (its BSP stays)
    maps = o.get("maps", OUT).split(",")

    def job(ed):
        ed.exec("!answer yes")
        for m in maps:
            ed.load(m)
            gone = []
            for a in ed.actors("Brush"):
                x, y, z = a.get("Location", (0, 0, 0))
                if "CSG_Add" not in a["props"].get("CsgOper", "") or abs(x) > 60000 or abs(y) > 60000:
                    continue
                if TOWER[0] <= x <= TOWER[2] and TOWER[1] <= y <= TOWER[3]:
                    continue
                if z - gz(x, y) > 150:
                    gone.append(a["Name"])
            # the stock TutA meshes (not our Avalon* packages) placed for the old island: set onto the new ground
            seat = []
            for a in ed.actors("StaticMeshActor"):
                x, y, z = a["Location"]
                mesh = a["props"].get("StaticMesh", "")
                if "AvalonSM" in mesh or (TOWER[0] <= x <= TOWER[2] and TOWER[1] <= y <= TOWER[3]):
                    continue
                if z - gz(x, y) > 250:
                    seat.append((a["Name"], x, y, gz(x, y)))
            ops = Ops.attach_to(ed.pid)
            if gone:
                ops.select(*gone)
                ed.ok("ACTOR DELETE")
            for n, x, y, zg in seat:
                ops.move(n, x, y, zg)
            ops.stop()
            print("  %s: %d stock meshes set onto the new ground %s" % (m, len(seat), [s_[0] for s_ in seat][:12]))
            ed.ok("MAP REBUILD")
            ed.ok("LIGHT APPLY", allow=("Couldn't bring window", "Can't find"))
            ed.paths()
            ed.save(m)
            print("  %s: removed %d floating BSP brushes %s, rebuilt, lit, paths" % (m, len(gone), gone))
    ed_session(job)


def stage_specs():
    """Route A: the path nodes WITH their ReachSpecs (pathspecs.py -> isl_paths_specs.t3d) instead of PATHS DEFINE.
    UnrealEd crashes on one 610-node / 2178-spec import (300 / 1056 is fine). So: chunks of <= 300 nodes in order,
    every spec on its own Start node. A spec whose End is in a LATER chunk comes in with its End unresolved and gets
    it afterwards with !setprop SPEC End PathNode'MyLevel.NODE' (a carrier PathNode listing other nodes' specs crashed
    UnrealEd; a Note carrier imported nothing: the post-import garbage collection drops unreferenced objects). Then
    LevelInfo0.PathsRebuiltStamp back to the source map's value, or 4 (the import zeroes it; the game then refuses the
    map: 'Paths ... should be rebuilt'). Tag lines are dropped (they drew 'Invalid name' warnings on import)."""
    from uedlib import Ops, t3d_actors  # noqa
    run(["py", os.path.join(TOOLS, "pathspecs.py"), RUN])
    txt = open(os.path.join(RUN, "isl_paths_specs.t3d"), encoding="utf-8").read()
    acts = re.findall(r"(Begin Actor Class=(\w+) Name=(\w+)\n(.*?)\nEnd Actor)", txt, re.S)
    chunk_of = {name: k // 300 for k, (_, _, name, _) in enumerate(acts)}
    files, forward, plist = [], [], {}
    for c in range(max(chunk_of.values()) + 1):
        out = ["Begin Map"]
        for blk, cls, name, body in acts:
            if chunk_of[name] != c:
                continue
            head = [l for l in re.split(r"\n    Begin Object", "\n" + body)[0].splitlines()
                    if l.strip() and not l.strip().startswith("Tag=")]
            out += ["Begin Actor Class=%s Name=%s" % (cls, name)] + head
            specs = re.findall(r"    Begin Object Class=ReachSpec Name=(\w+)\n(.*?)\n    End Object", blk, re.S)
            for k, (sn, sbody) in enumerate(specs):
                end = re.search(r"End=(\w+)'MyLevel\.(\w+)'", sbody)
                if chunk_of.get(end.group(2), 99) > c:
                    forward.append((sn, end.group(1), end.group(2)))
                out += ["    Begin Object Class=ReachSpec Name=%s" % sn, sbody, "    End Object",
                        "    PathList(%d)=ReachSpec'MyLevel.%s'" % (k, sn)]
                plist.setdefault(name, []).append(sn)
            out.append("End Actor")
        p = os.path.join(RUN, "remake_specs_%d.t3d" % c)
        open(p, "w", newline="\r\n").write("\n".join(out + ["End Map"]) + "\n")
        files.append(p)
    stamp = o.get("stamp")

    def job(ed):
        ed.exec("!answer yes")
        ed.load(OUT)
        ops = Ops.attach_to(ed.pid)
        ops.select("LevelInfo0")
        st = (t3d_actors(ed.copy_selected()) or [{"props": {}}])[0]["props"].get("PathsRebuiltStamp")
        ed.deselect()
        for p in files:
            ed.import_t3d(p, add=True)
            ed.deselect()
        bad = 0
        for sn, ecls, end in forward:
            r = ops.exec("!setprop %s End %s'MyLevel.%s'" % (sn, ecls, end))
            if "Bad value" in r or "no property" in r or "not found" in r.lower():
                bad += 1
                if bad <= 3:
                    print("   setprop failed:", r.strip()[:160])
        print("  %d forward specs, End set on %d" % (len(forward), len(forward) - bad))
        mine = [a for a in ed.actors("PathNode") if re.match(r"Gen(Path|Story)", a.get("Name", ""))]
        refs = sum(1 for a in mine for k in a["props"] if k.startswith("PathList"))
        print("  %d nodes in %d chunks, %d PathList entries (of %d specs) (stamp before %s)"
              % (len(mine), len(files), refs, sum(len(v) for v in plist.values()), st))
        ops.exec("!setprop LevelInfo0 PathsRebuiltStamp %s" % (stamp or (st if st not in (None, "", "0") else 4)))
        ops.stop()
        ed.save(OUT)
    ed_session(job)


def stage_patchin():
    """Fold the tested pieces into OUT (2026-10-09, user: "patch them in"): the finer terrain patch (terrain_patch.py
    <run> <run>\\patch2 amp=120 mask=1: no rock detail under buildings), every PathNode / PlayerStart in the patch lifted
    by the patch's height over the island there, the interior lights (interior_lights.py), then LIGHT APPLY and PATHS
    DEFINE (fast since the stagger layout: the node moves invalidate the old specs anyway). OUT is backed up first as
    <OUT>_prepatch.un2."""
    import struct
    import numpy as np
    import story_export  # noqa
    from uedlib import Ops, t3d_set  # noqa
    prefix = os.path.join(RUN, o.get("patch", "patch2"))
    info = json.load(open(prefix + ".json"))
    raw = open(prefix + ".bmp", "rb").read()
    n = info["n"]
    PZ = np.frombuffer(raw[54:54 + n * n * 2], dtype="<u2").reshape(n, n)[::-1].astype(float)
    PZ = info["Location"][2] + (PZ - 32768) * info["TerrainScale"][2] / 256
    cell = info["TerrainScale"][0]
    gz = story_export.ground_fn(os.path.join(RUN, "isl_ec.bmp"))

    def lift(x, y):
        fi, fj = (x - info["Location"][0]) / cell + n / 2, (y - info["Location"][1]) / cell + n / 2
        if not (0 <= fi < n - 1 and 0 <= fj < n - 1):
            return 0.0
        i, j = int(fi), int(fj)
        u, v = fi - i, fj - j
        z = (PZ[j, i] * (1 - u) * (1 - v) + PZ[j, i + 1] * u * (1 - v) + PZ[j + 1, i] * (1 - u) * v + PZ[j + 1, i + 1] * u * v)
        return max(0.0, z - gz(x, y))

    lights = os.path.join(RUN, "remake_lights.t3d")
    run(["py", os.path.join(TOOLS, "interior_lights.py"), RUN, "out=" + lights])
    lfiles = chunks(lights)
    shutil.copyfile(os.path.join(MAPS, OUT + ".un2"), os.path.join(MAPS, OUT + "_prepatch.un2"))
    name = os.path.basename(prefix)
    k = 512.0 / cell

    def job(ed):
        ed.exec("!answer yes")
        ed.load(OUT)
        ed.import_texture(os.path.abspath(prefix + ".bmp"), name, "MyLevel", "terrain_maps", MIPS=0)
        isl = [a for a in ed.actors("TerrainInfo") if "island" in a["props"].get("TerrainMap", "")]
        if not isl:
            sys.exit("no island TerrainInfo in " + OUT)
        blk = re.sub(r"Name=\w+", "Name=TerrainPatch_" + name, isl[0]["text"], count=1)
        blk = t3d_set(blk, "TerrainMap", "Texture'MyLevel.terrain_maps.%s'" % name)
        blk = t3d_set(blk, "Location", "(X=%f,Y=%f,Z=%f)" % tuple(info["Location"]))
        blk = t3d_set(blk, "TerrainScale", "(X=%f,Y=%f,Z=%f)" % tuple(info["TerrainScale"]))
        keep = []
        for l in blk.splitlines():
            m = re.match(r"\s*Layers\((\d+)\)=(.*)", l)
            if m and m.group(1) != "0":
                continue
            if m:
                l = re.sub(r"AlphaMap=[^,)]+,?", "", l)
                l = re.sub(r"(UScale|VScale)=([-\d.]+)", lambda q: "%s=%f" % (q.group(1), float(q.group(2)) * k), l)
            keep.append(l)
        tp = prefix + "_terrain.t3d"
        open(tp, "w").write("Begin Map\n" + "\n".join(keep) + "\nEnd Map\n")
        ed.deselect()
        ed.import_t3d(tp, add=True)
        ed.deselect()
        moves = []
        for cls in ("PathNode", "PlayerStart"):
            for a in ed.actors(cls):
                x, y, z = a["Location"]
                d = lift(x, y)
                if d > 1:
                    moves.append((a["Name"], x, y, z + d))
        for p in lfiles:
            ed.import_t3d(p, add=True)
            ed.deselect()
        ops = Ops.attach_to(ed.pid)
        for nm, x, y, z in moves:
            ops.move(nm, x, y, z)
        ops.stop()
        print("  patch %s in, %d nav points lifted (max %.0f UU), %d lights" % (
            name, len(moves), max([0.0] + [lift(m[1], m[2]) for m in moves]), sum(len(actors_of(p)) for p in lfiles)))
        ed.ok("LIGHT APPLY", allow=("Couldn't bring window", "Can't find"))
        import time
        t0 = time.time()
        ed.paths()
        print("  LIGHT APPLY + PATHS DEFINE (%.0f s for paths)" % (time.time() - t0))
        ed.save(OUT)
    ed_session(job)


def stage_arenas():
    """re-place the greybox arenas in OUT from the layout's current L["arenas"] (e.g. after anchors.arenas changed:
    3b315e5 slid E1 / E3 inland): delete every actor tagged Arena_*, import the new remake_arenas.t3d, light it,
    PATHS DEFINE, save (backup <OUT>_prearenas.un2)"""
    from uedlib import Ops  # noqa
    p = os.path.join(RUN, "remake_arenas.t3d")
    write_t3d(p, arena_actors())
    files = chunks(p)
    shutil.copyfile(os.path.join(MAPS, OUT + ".un2"), os.path.join(MAPS, OUT + "_prearenas.un2"))

    def job(ed):
        ed.exec("!answer yes")
        ed.load(OUT)
        old = [a["Name"] for c in ("StaticMeshActor", "PathNode") for a in ed.actors(c)
               if a["props"].get("Tag", "").startswith("Arena_")]
        ops = Ops.attach_to(ed.pid)
        for k in range(0, len(old), 40):
            ops.select(*old[k:k + 40])
            ed.ok("ACTOR DELETE")
        ops.stop()
        ed.deselect()
        for f in files:
            ed.import_t3d(f, add=True)
        ed.light(selected=True)
        ed.deselect()
        ed.paths()
        ed.save(OUT)
        print("  %s: %d old arena actors out, %d in" % (OUT, len(old), sum(len(actors_of(f)) for f in files)))
    ed_session(job)


def stage_patchlayers():
    r"""the terrain patch gets the island's texture layers (Q92 follow-up: it had the first layer only, no alpha): each
    island alpha map (<run>\alphas\<layer>.tga, the 128 x 128 maps groundpaint.py wrote and terrain_apply imported)
    resampled over the patch's area to the patch's own grid, imported as MyLevel.PatchLayers.<layer>, and the patch
    TerrainInfo re-made from the island's (all its layers, AlphaMap -> the patch's, UV scale x island/patch cell so the
    textures keep their world size), then LIGHT APPLY, save (backup <OUT>_prelayers.un2)"""
    from PIL import Image
    import numpy as np
    from uedlib import Ops, t3d_set  # noqa
    prefix = os.path.join(RUN, o.get("patch", "patch2"))
    info = json.load(open(prefix + ".json"))
    n, cell = info["n"], info["TerrainScale"][0]
    ISL = (-14487.546875, 4835.837891)
    out_dir = os.path.join(RUN, "patch_alphas")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for f in sorted(os.listdir(os.path.join(RUN, "alphas"))):
        if not f.endswith(".tga"):
            continue
        im = Image.open(os.path.join(RUN, "alphas", f))
        A = np.asarray(im.convert("RGBA")).astype(float)
        H, W = A.shape[:2]
        # patch point (i, j) -> world -> island alpha pixel (same mapping as the heightmap: 512 UU a pixel, centred)
        ii, jj = np.meshgrid(np.arange(n), np.arange(n))
        X = info["Location"][0] + (ii - n / 2) * cell
        Y = info["Location"][1] + (jj - n / 2) * cell
        fi = np.clip((X - ISL[0]) / 512.0 + W / 2, 0, W - 1.001)
        fj = np.clip((Y - ISL[1]) / 512.0 + H / 2, 0, H - 1.001)
        i0, j0 = fi.astype(int), fj.astype(int)
        u, v = (fi - i0)[..., None], (fj - j0)[..., None]
        R = (A[j0, i0] * (1 - u) * (1 - v) + A[j0, i0 + 1] * u * (1 - v) + A[j0 + 1, i0] * (1 - u) * v
             + A[j0 + 1, i0 + 1] * u * v)
        p = os.path.join(out_dir, f)
        Image.fromarray(np.clip(R, 0, 255).astype(np.uint8), "RGBA").save(p)
        made.append((os.path.splitext(f)[0], p))
    print("  %d patch alpha maps -> %s" % (len(made), out_dir))
    shutil.copyfile(os.path.join(MAPS, OUT + ".un2"), os.path.join(MAPS, OUT + "_prelayers.un2"))
    k = 512.0 / cell

    def job(ed):
        ed.exec("!answer yes")
        ed.load(OUT)
        for name, p in made:
            ed.import_texture(p, name, "MyLevel", "PatchLayers", MIPS=0, ALPHA=1)
        T = ed.actors("TerrainInfo")
        isl = [a for a in T if "island" in a["props"].get("TerrainMap", "")][0]
        old = [a for a in T if a["Name"].startswith("TerrainPatch_")]
        if not old:
            sys.exit("no TerrainPatch_ in " + OUT)
        pname = old[0]["Name"]
        blk = re.sub(r"Name=\w+", "Name=" + pname, isl["text"], count=1)
        blk = t3d_set(blk, "TerrainMap", old[0]["props"]["TerrainMap"])
        blk = t3d_set(blk, "Location", "(X=%f,Y=%f,Z=%f)" % tuple(info["Location"]))
        blk = t3d_set(blk, "TerrainScale", "(X=%f,Y=%f,Z=%f)" % tuple(info["TerrainScale"]))
        lines = []
        for l in blk.splitlines():
            if re.match(r"\s*Layers\(\d+\)=", l):
                l = l.replace("IslandTerrainLayers", "PatchLayers")
                l = re.sub(r"(UScale|VScale)=([-\d.]+)", lambda q: "%s=%f" % (q.group(1), float(q.group(2)) * k), l)
                l = re.sub(r",?TerrainMatrix=\(.*?\)\)\)", ")", l)      # the engine recomputes it
            lines.append(l)
        tp = prefix + "_layers.t3d"
        open(tp, "w").write("Begin Map\n" + "\n".join(lines) + "\nEnd Map\n")
        print("  patch layers:", [l.strip()[:110] for l in lines if "Layers(" in l])
        ops = Ops.attach_to(ed.pid)
        ops.select(pname)
        ed.ok("ACTOR DELETE")
        ops.stop()
        ed.deselect()
        ed.import_t3d(tp, add=True)
        ed.deselect()
        ed.ok("LIGHT APPLY", allow=("Couldn't bring window", "Can't find"))
        ed.paths()
        ed.save(OUT)
    ed_session(job)


def stage_dock():
    """The dark first view (2026-10-09, user: "do both"): the PlayerStart's yaw turned away from the low sun
    (codirect.SUN_AZ, Unreal yaw degrees; yaw= in degrees, default 0: front light at 136 deg off the sun, still 45 deg
    toward the spine) and a soft sky fill over the dock (one unshadowed-looking Light 12 m up, wide and dim, cool;
    fill=0 leaves it out), then LIGHT APPLY. OUT is backed up first as <OUT>_predock.un2."""
    from uedlib import Ops  # noqa
    st = json.load(open(os.path.join(RUN, "remake_start.json")))
    yaw = float(o.get("yaw", 0))
    fp = os.path.join(RUN, "remake_dockfill.t3d")
    fill = o.get("fill", "1") == "1"
    if fill:
        write_t3d(fp, ["\n".join([
            "Begin Actor Class=Light Name=GenLight_dockfill",
            "    Location=(X=%.1f,Y=%.1f,Z=%.1f)" % (st["X"], st["Y"], st["Z"] + 600),
            "    LightBrightness=%s" % o.get("bright", "56"),
            "    LightHue=150",
            "    LightSaturation=210",
            "    LightRadius=%s" % o.get("radius", "64"),
            "End Actor"])])
    if not os.path.exists(os.path.join(MAPS, OUT + "_predock.un2")):     # reruns keep the first backup
        shutil.copyfile(os.path.join(MAPS, OUT + ".un2"), os.path.join(MAPS, OUT + "_predock.un2"))

    def job(ed):
        ed.exec("!answer yes")
        ed.load(OUT)
        ed.deselect()
        old = [a["Name"] for a in ed.actors("Light") if a["Name"].startswith("GenLight_dockfill")]
        ps = ed.actors("PlayerStart")
        ops = Ops.attach_to(ed.pid)
        if old:
            ops.select(*old)
            ed.ok("ACTOR DELETE")
        if fill:
            ed.import_t3d(fp, add=True)
            ed.deselect()
        ops.move(ps[0]["Name"], pitch=0, yaw=int(yaw * 65536 / 360) % 65536, roll=0)
        ops.stop()
        print("  start %s yaw %g deg (sun at %g), fill %s" % (ps[0]["Name"], yaw, 136, fill))
        # the outdoor zone had no ambient at all (AmbientBrightness 0): whatever the low sun misses rendered pure
        # black. SET reaches every ZoneInfo in memory (the class default too, harmless: the map saves the actor's)
        amb = o.get("ambient", "14")
        if amb != "0":
            for p, v in (("AmbientBrightness", amb), ("AmbientHue", "150"), ("AmbientSaturation", "200")):
                ed.exec("SET ZoneInfo %s %s" % (p, v))
            print("  zone ambient %s (hue 150, sat 200): %s" % (amb, [a["props"].get("AmbientBrightness") for a in ed.actors("ZoneInfo")]))
        ed.ok("LIGHT APPLY", allow=("Couldn't bring window", "Can't find"))
        ed.paths()          # a new actor marks the level changed: the game refuses to load it with stale paths
        ed.save(OUT)
    ed_session(job)


if STAGE == "dock":
    stage_dock()
if STAGE == "patchlayers":
    stage_patchlayers()
if STAGE == "arenas":
    stage_arenas()
if STAGE == "patchin":
    stage_patchin()
if STAGE == "bsp":
    stage_bsp()
if STAGE == "specs":
    stage_specs()
if STAGE in ("t3d", "all"):
    stage_t3d()
if STAGE in ("mesh", "all"):
    stage_mesh()
if STAGE in ("map", "all"):
    stage_map()
if STAGE in ("paths", "all"):
    stage_paths()
if STAGE == "all":
    stage_bsp()
