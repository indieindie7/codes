r"""The Avalon remake's editor build (redesign 2026-10-09, plan s.7 Phase B), on top of a finished town.py run.

    py tools/remake_build.py <run folder> <map built by town.py> [out=TutA_Remake] [stage=t3d|mesh|map|paths|all]
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
         "out=" + os.path.join(RUN, "remake_story.t3d"), "pkg=" + LIB, "entry=" + o.get("entry", "stair"), "heightmap=" + hm])
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
            if start == "dock" and "dock" in L["buildings"]:
                d = L["buildings"]["dock"]
                sp = (L.get("spine") or (L.get("roads") or [[(d["x"], d["y"] + 1)]])[0])[0]    # spine: a list of points
                yaw = int(round(math.degrees(math.atan2(sp[1] - d["y"], sp[0] - d["x"])) * 65536 / 360)) % 65536
                ops.move(ps[0]["Name"], d["x"], d["y"], d.get("z", 0) + 120, pitch=0, yaw=yaw, roll=0)
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


if STAGE in ("t3d", "all"):
    stage_t3d()
if STAGE in ("mesh", "all"):
    stage_mesh()
if STAGE in ("map", "all"):
    stage_map()
if STAGE in ("paths", "all"):
    stage_paths()
