r"""Concept to believable town, one command (see ../PIPELINE.md):

    py tools/town.py <seed> [style=plateau|ridges] [name=TutA_Town] [pilot=1] [shift=-5300] [rerolls=3] [sun=low|stock]

island (terrain tool sketch, formed + eroded) -> layout (interest maps, roads, Voronoi drift) -> systems
(provides/needs, connections; an unmet core need re-rolls the layout with the next seed) -> pads -> TutA
terrain -> buildings as StaticMeshActors + lighting -> editor pictures -> pilot run -> report.md.
Everything lands in Documents\U2_research\towns\<name><seed>\ (root=<dir> puts it elsewhere).
The co-directors' FINAL review runs on the graded heightmap (isl_ec.bmp) after the walks; the pre-grading review is
kept for comparison (codirection_final.txt, report.md). stop=score ends there: the CPU-only part, no editor or game
(with reuse=1 it re-scores an existing run folder's islands and layouts).
"""
import json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(HERE, "tools")
sys.path.insert(0, TOOLS)
import island_batch as ib  # noqa  (helpers: run, pilot_script, populate, enable_map, island_png, TEMPLATE, PILOT, GAME)
import systems  # noqa
import compose  # noqa
import codirect  # noqa  (the five co-directors; the final review runs on the graded ground for every style)
import anchors  # noqa  (the story buildings' placement rules: the hero's summit, guest house, water tower, the drain)
import takes  # noqa  (the informal taps: binder takes:)
import rooms  # noqa  (interior plans for the shell build -> <run>/rooms.json)
import pathlinks  # noqa  (pathnodes.py on the run folder + the drain / truck-road node chains -> <run>/isl_paths.t3d)
import binder  # noqa

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
seed = int(args[0]) if args else 1
STYLE = o.get("style", "plateau")
NAME = o.get("name", "TutA_Town")
PILOT = o.get("pilot", "1") != "0"
SHIFT = o.get("shift", "-5300")
COMPOSE = o.get("compose", "1") != "0"   # score layouts through the command room window and keep the best
REROLLS = int(o.get("rerolls", 6 if COMPOSE else 3))
SUN = o.get("sun", "low")              # low = re-aim the baked sun at the sky's painted one (lowsun.py); stock = leave it
METHOD = o.get("method", "spine")      # spine = street first, plots along it (layout_spine.py); interest = layout.py
name = "%s%d" % (NAME, seed)
RUN = os.path.join(o.get("root", r"C:\Users\john\Documents\U2_research\towns"), name)   # root=<dir>: a test copy elsewhere
os.makedirs(RUN, exist_ok=True)
base = os.path.join(RUN, "isl")
t0 = time.time()
log = []


def step(title, fn):
    t = time.time()
    print("\n## %s" % title, flush=True)
    r = fn()
    log.append((title, time.time() - t))
    return r


# 1-3. the island and the town, chosen together. style=cinema (2026-10-08): ONE generator - the island is designed
# from the command room's window and the parti (island_form.py style=cinema), several islands x several layouts are
# made, and the five co-directors (codirect.py: WRITER = the parti + the town model, DIRECTOR = the cinematography
# rules, ARTIST = the drawings + metrics) review every candidate; the one they agree on best is built. Other styles:
# one island, the layouts keyed by systems + the window frame as before.
NAV = os.path.join(os.path.dirname(TOOLS), "data", "navpoints_TutA.json")
CODIRECT = STYLE == "cinema"
REUSE = o.get("reuse", "0") == "1"           # reuse=1: keep islands/layouts already made in this run folder (a resumed build)


def made(path):
    return REUSE and os.path.exists(path)
ISLANDS = int(o.get("islands", 4 if CODIRECT else 1))
if CODIRECT:
    REROLLS = int(o.get("rerolls", 2))
layout = base + "_layout.json"
best = None
reviews = []
for ki in range(ISLANDS):
    iseed = seed if ISLANDS == 1 else seed * 10 + ki
    ib_ = base if ISLANDS == 1 else base + "_i%d" % ki
    if not made(ib_ + "_e.bmp"):
     step("island %d (seed %d, %s)" % (ki, iseed, STYLE), lambda: ib.run(["py", os.path.join(TOOLS, "island_form.py"), iseed, ib.TEMPLATE,
                                                                     ib_ + "_e.bmp", "png=" + ib_ + "_sketch.png", "style=" + STYLE]))
    # the stock island's relief: hills as tall as TutA's own, the plain kept at the tower's foot
     step("relief", lambda: ib.run(["py", os.path.join(TOOLS, "relief_match.py"), ib_ + "_e.bmp", ib.TEMPLATE]))
     # the camera: what the player can see from the playable area (the tower's NavigationPoints)
     step("viewshed", lambda: ib.run(["py", os.path.join(TOOLS, "viewshed.py"), ib_ + "_e.bmp", NAV, "-", ib_]))
    for k in range(REROLLS):
        lseed = iseed + 100 * k
        cand = ib_ + "_layout_%d.json" % lseed
        tool = "layout_spine.py" if METHOD == "spine" else "layout.py"
        if not made(cand):
            step("layout %s (seed %d)" % (METHOD, lseed), lambda: ib.run(["py", os.path.join(TOOLS, tool), ib_ + "_e.bmp", cand,
                                                                          "seed=%d" % lseed, "shift=" + SHIFT, "png=" + cand[:-5] + ".png", "vis=" + ib_ + "_vis.npz"]))
        # a layout made before binder 1940260 (reuse=1) lacks the rule-placed story buildings: place them now
        _Lc = json.load(open(cand))
        if anchors.PARTI_HERO not in _Lc["buildings"] or "drain" not in _Lc:
            print("  anchors (late, an older layout):", ", ".join(anchors.apply(_Lc, anchors.load_heights(ib_ + "_e.bmp"))), flush=True)
            json.dump(_Lc, open(cand, "w"), indent=0)
        elif "occluders" not in _Lc:              # a round-2 layout: beat 1's occluder (round 3) only
            _occ = anchors.dock_occluder(anchors.load_heights(ib_ + "_e.bmp"), _Lc, binder.load()[1])
            _Lc["occluders"] = _occ["placed"]
            _Lc.setdefault("anchors", {})["occluder"] = {k: v for k, v in _occ.items() if k != "placed"} | {"n": len(_occ["placed"])}
            print("  occluder (late, a round-2 layout):", _occ["note"], flush=True)
            json.dump(_Lc, open(cand, "w"), indent=0)
        Lc, core_unmet = systems.run(cand, report=True)
        frame = compose.score(ib_ + "_e.bmp", cand) if COMPOSE else {"total": 0.0}
        if CODIRECT:
            Rv = codirect.review(ib_ + "_e.bmp", cand)
            reviews.append(codirect.report(Rv, "island %d layout %d" % (ki, lseed)))
            print(reviews[-1], flush=True)
            key = (1 if Rv["vetoes"] else 0, -Rv["total"])
        else:
            print("  seed %d: systems %.2f, %d core unmet, window frame %.2f (%s buildings, hero %s)" % (
                lseed, Lc["systems"]["score"], len(core_unmet), frame["total"], frame.get("in_frame", "-"), frame.get("hero")), flush=True)
            key = (len(core_unmet), -(0.5 * Lc["systems"]["score"] + 0.5 * frame["total"]))
        if best is None or key < best[0]:
            best = (key, cand, frame, ib_)
        if not core_unmet and not COMPOSE and not CODIRECT:
            break
if CODIRECT:
    open(os.path.join(RUN, "codirection.txt"), "w", encoding="utf-8").write("\n\n".join(reviews) + "\n\nCHOSEN: %s\n" % os.path.basename(best[1]))
if best[3] != base:                                  # the chosen island becomes THE island of this run
    import glob as _glob
    for fsrc in _glob.glob(best[3] + "_*"):
        suf = fsrc[len(best[3]):]
        if not suf.startswith("_layout"):
            shutil.copy(fsrc, base + suf)
score = subprocess.run(["py", ib.TERRAIN, "score", base + "_e.bmp", "--cell", "512", "--zstep", "0.5", "--unit", "0.02"],
                       capture_output=True, text=True).stdout
open(os.path.join(RUN, "terrain_score.txt"), "w").write(score)
shutil.copy(best[1], layout)
shutil.copy(best[1][:-5] + ".png", base + "_layout.png")
L = json.load(open(layout))
FRAME = best[2]
if COMPOSE:
    compose.score(base + "_e.bmp", layout, png=base + "_frame.png")
print("  using", os.path.basename(best[1]), "score %.2f, %d core unmet, window frame %.2f" % (L["systems"]["score"], best[0][0], FRAME["total"]), flush=True)
open(os.path.join(RUN, "systems.txt"), "w").write(
    "needs %d unmet %d score %.2f\n" % (L["systems"]["needs"], len(L["systems"]["unmet"]), L["systems"]["score"])
    + "".join("  %s needs %s: %s\n" % tuple(u) for u in L["systems"]["unmet"]))
# the co-directors on the natural ground, before cut/fill: kept only for comparison with the final review below
# (the level designer, 2026-10-09: grading flattened Cine8's cover and high spots, LEVEL 0.93 -> 0.69)
PRE = codirect.review(base + "_e.bmp", layout)

# 4. pads, 5. terrain into TutA, 6. the buildings as actors + lighting + editor pictures
step("pads + roads", lambda: ib.run(["py", os.path.join(TOOLS, "terrain_cutfill.py"), base + "_e.bmp", base + "_ec.bmp", "shift=" + SHIFT, "layout=" + layout]))
ib.island_png(base + "_ec.bmp", base + "_map.png")
step("viewshed (final ground)", lambda: ib.run(["py", os.path.join(TOOLS, "viewshed.py"), base + "_ec.bmp", NAV, layout, base]))
# the citizens' routines walked on the graded ground: desire lines, door wants, travel-time checks
step("walks", lambda: ib.run(["py", os.path.join(TOOLS, "walks.py"), base + "_ec.bmp", layout, "png=" + base + "_walks.png"]))


def story_extras():
    """the informal taps (binder takes:) into the layout for clutter, the interior plans into <run>/rooms.json"""
    L_ = json.load(open(layout))
    _, sh = binder.load()
    ZG_ = anchors.load_heights(base + "_ec.bmp")
    L_["taps"] = takes.taps(L_, ZG_, sh)
    # beat 1's occluder, re-fitted on the GRADED ground (the quay pad can lift the dock stations by metres): what the
    # clutter builds and the final review counts
    _occ = anchors.dock_occluder(ZG_, L_, sh)
    L_["occluders"] = _occ["placed"]
    L_.setdefault("anchors", {})["occluder"] = {k: v for k, v in _occ.items() if k != "placed"} | {"n": len(_occ["placed"]), "ground": "graded"}
    # the greybox arenas E1-E4 (tools/arenas.py's plans) at the route stops, on the graded ground -> L["arenas"] for export
    L_["arenas"] = anchors.arenas(ZG_, L_, sh)
    json.dump(L_, open(layout, "w"), indent=0)
    takes.overlay(anchors.load_heights(base + "_ec.bmp"), L_, L_["taps"], base + "_taps.png")
    P = rooms.build(sh, binder.load_rooms(), L_)
    json.dump(P, open(os.path.join(RUN, "rooms.json"), "w"), indent=1)
    rooms.overlay(P, base + "_rooms.png")
    C = takes.conc_report(L_)
    A = L_.get("anchors", {})
    lines = ["taps: %d (%d ok), %d props: %s" % (len(L_["taps"]), sum(t["ok"] for t in L_["taps"]), len(takes.clutter_items(L_["taps"])),
                                                 ", ".join("%s %s %.0f m" % (t["taker"], t["resource"], t.get("metres", 0)) for t in L_["taps"])),
             "conc slurry line: %s, route %d m" % (" -> ".join(C["chain"]) or "none", C["route_m"]),
             "interiors: %d plans, %d rooms, %d check notes (rooms.json)" % (len(P), sum(len(p["rooms"]) for p in P.values()), sum(len(p["checks"]) for p in P.values()))]
    if "summit" in A:
        S_ = A["summit"]
        lines.append("hero %s on the summit: ground %.0f m, plinth %.0f m, truck road %d m (steepest %.0f %%, cap %.0f %%), %s" % (
            anchors.PARTI_HERO, S_["ground_mean_m"], S_["plinth_used_m"], S_["road_m"], 100 * S_["road_grade"], 100 * S_.get("road_cap", 0.12),
            ("in the window frame at u=%.2f%s" % (S_["frame_u"], ", searched wider" if S_.get("widened") else "")) if S_["in_window"]
            else ("on the frame's edge only (u=%.2f): the cooling towers keep the window" % S_["edge_u"]) if S_.get("edge_u") is not None
            else "NOT in the window (%.0f deg off; no buildable spot in the frame)" % S_["window_deg_off"]))
    if "guest_house" in A:
        lines.append("guest house beside %s (%s): %d m from the fuel (E16 %s)" % (
            A["guest_house"]["host"], A["guest_house"]["side"], A["guest_house"]["fuel_m"], "ok" if A["guest_house"]["e16_ok"] else "SHORT"))
    if "occluder" in A:
        lines.append("occluder: %s" % A["occluder"]["note"])
    for aid, ar in L_.get("arenas", {}).items():
        lines.append("arena %s %s: %s" % (aid, ar["name"], ("P on the %s at (%.0f, %.0f), origin (%.0f, %.0f) yaw %.0f, floor z %.0f, ground range %.0f m%s" % (
            ar["anchor"], ar["stop"][0], ar["stop"][1], ar["origin"][0], ar["origin"][1], ar["yaw"], ar["z"], ar["ground_range_m"],
            (", %.0f %% over the sea" % (100 * ar["over_sea_share"])) if ar["over_sea_share"] else "")) if ar["placed"] else ar["why"]))
    if "water_tower" in A:
        lines.append("water tower (E14'): head %.0f m (%s; %s)" % (A["water_tower"]["head_m"], "ok" if A["water_tower"]["e14_ok"] else "short",
                                                               A["water_tower"].get("pick", "highest ground")))
    if L_.get("drain"):
        D = L_["drain"]
        lines.append("drain: %.0f m (%d UU, %.0f s), %.0f %% under the spine, %.1f-%.1f m deep, cover <= %.1f m, outfall invert %+.1f m over the sea, "
                     "%d drop shafts, %d m at grade (covered cut)" % (
            D["length_m"], D["length_uu"], D["walk_s"], 100 * D["under_spine"], D["min_depth_m"], D["max_depth_m"], D.get("max_cover_m", 0),
            D["outfall_invert_vs_sea_m"], len(D.get("drop_shafts", [])), D.get("shallow_m", 0)))
    try:                                 # PathNodes on the graded ground (pathnodes.py; before the clutter: an empty clutter T3D)
        lines.append(pathlinks.summary(pathlinks.run(RUN)))
    except Exception as e:
        lines.append("pathnodes failed: %s" % e)
    open(os.path.join(RUN, "story.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join("  " + x for x in lines), flush=True)


step("taps, interiors (story keys)", story_extras)
# the architect's thinking drawings (Q36): figure-ground, Nolli plan, sections A/B/C at true scale
step("drawings", lambda: ib.run(["py", os.path.join(TOOLS, "drawings.py"), base + "_ec.bmp", layout, base]))
# the architectural set (parti, site analysis, framework, figure-ground, sections, codes, serial vision): <run>\plans
step("plans", lambda: ib.run(["py", os.path.join(TOOLS, "plans.py"), RUN]))
try:                                     # believability (Q35, tools/metrics.py), after the walks' paths join the network
    import metrics
    MET = metrics.score(layout)
    print("  believability: IMP %.2f HIER %.2f" % (MET["IMP"], MET["HIER"]), flush=True)
    open(os.path.join(RUN, "believability.txt"), "w").write(
        "IMP %.2f HIER %.2f\n%s\n" % (MET["IMP"], MET["HIER"], ", ".join("%s %s" % (k, v) for k, v in MET.items() if k not in ("IMP", "HIER"))))
except Exception as e:
    print("  metrics failed:", e)
# the final co-direction review on the GRADED ground (isl_ec.bmp, what ships), after the walks' paths joined the
# network; the pre-grading review is kept beside it for comparison (the level designer, redesign 2026-10-09)
FINAL = codirect.review(base + "_ec.bmp", layout)
FRAME_G = compose.score(base + "_ec.bmp", layout, png=base + "_frame.png") if COMPOSE else {}
open(os.path.join(RUN, "codirection_final.txt"), "w", encoding="utf-8").write(
    codirect.report(FINAL, "FINAL, graded ground (isl_ec.bmp)") + "\n\n" + codirect.report(PRE, "before grading (isl_e.bmp), for comparison") + "\n")
print(codirect.report(FINAL, "FINAL, graded ground"), flush=True)
print("  before grading: total %.3f, LEVEL %.2f -> graded: total %.3f, LEVEL %.2f" % (PRE["total"], PRE["level"]["score"], FINAL["total"], FINAL["level"]["score"]), flush=True)
if o.get("stop") == "score":            # stop=score: the CPU-only part (layouts, grading, walks, drawings, scores); no editor, no game
    sys.exit(0)
L = json.load(open(layout))
# the ground paint: rock base, sand on roads / yards / beach, plant life on gentle ground (TutA's three layers)
ALPHA_TPL = os.path.join(r"C:\Users\john\Documents\U2_research\terrain", "alphas")
step("ground paint", lambda: ib.run(["py", os.path.join(TOOLS, "groundpaint.py"), base + "_ec.bmp", layout, ALPHA_TPL, os.path.join(RUN, "alphas")]))
step("terrain", lambda: ib.run(["py", os.path.join(TOOLS, "terrain_apply.py"), base + "_ec.bmp", name, "alphas=" + os.path.join(RUN, "alphas"), "stock=" + ib.TEMPLATE], retries=2))
t3d = base + "_actors.t3d"
step("export", lambda: ib.run(["py", os.path.join(TOOLS, "export_mutator.py"), "shift=" + SHIFT, "family=" + name, "layout=" + layout, "t3d=" + t3d,
                               "heightmap=" + base + "_ec.bmp", "props=0"]))
# clutter and vegetation: lamps along the trunk roads, crates and barrels in the yards, fences, rocks, trees
clut = base + "_clutter.t3d"
step("clutter", lambda: ib.run(["py", os.path.join(TOOLS, "clutter.py"), base + "_ec.bmp", layout, clut, "seed=%d" % seed, "before=" + base + "_e.bmp", "vis=" + base + "_vis.npz"]))
try:                                           # the PathNodes again, now with the clutter's cover props (isl_paths.t3d: import AFTER the lighting build)
    print("  " + pathlinks.summary(pathlinks.run(RUN)), flush=True)
except Exception as e:
    print("  pathnodes (with clutter) failed:", e)
with open(t3d, "a") as f:                      # one import: the clutter actors are appended to the buildings' T3D
    body = open(clut).read()
    f.write("\n" + body[body.index("\n") + 1:body.rindex("End Map")])
step("populate", lambda: ib.populate(name, t3d, layout, base))
ib.enable_map(name)
if SUN == "low":
    step("low sun", lambda: ib.run(["py", os.path.join(TOOLS, "lowsun.py"), name, "out=" + name, "el=%g" % codirect.SUN_EL, "az=%g" % codirect.SUN_AZ,
                                    "hue=24", "sat=100", "bright=150"], retries=1))       # the sun the director scored
# motion in the view: plumes from the sheets' motion: keys, trucks on the spine, the reveal pass (U2AvalonCards.ini)
step("motion", lambda: ib.run(["py", os.path.join(TOOLS, "motion.py"), layout, "family=" + name]))

# 7. the game
sheet = None
if PILOT:
    script = os.path.join(ib.PILOT, "scripts", "town_%s.txt" % name.lower())
    open(script, "w").write(ib.pilot_script(name, layout))
    step("pilot", lambda: ib.run(["py", os.path.join(ib.PILOT, "u2pilot.py"), script, "--background"], cwd=ib.PILOT))
    runs = sorted(d for d in os.listdir(os.path.join(ib.PILOT, "runs")) if d.endswith("town_%s" % name.lower()))
    if runs and os.path.exists(os.path.join(ib.PILOT, "runs", runs[-1], "sheet.png")):
        sheet = os.path.join(RUN, "pilot_sheet.png")
        shutil.copy(os.path.join(ib.PILOT, "runs", runs[-1], "sheet.png"), sheet)
    # the second run: ground-level close-ups, camera distance scaled to each building
    cscript = os.path.join(ib.PILOT, "scripts", "closeups_%s.txt" % name.lower())
    open(cscript, "w").write(ib.closeup_script(name, layout))
    step("close-ups", lambda: ib.run(["py", os.path.join(ib.PILOT, "u2pilot.py"), cscript, "--background"], cwd=ib.PILOT))
    cruns = sorted(d for d in os.listdir(os.path.join(ib.PILOT, "runs")) if d.endswith("closeups_%s" % name.lower()))
    if cruns and os.path.exists(os.path.join(ib.PILOT, "runs", cruns[-1], "sheet.png")):
        shutil.copy(os.path.join(ib.PILOT, "runs", cruns[-1], "sheet.png"), os.path.join(RUN, "closeups_sheet.png"))

# 8. the report
S = L["systems"]
rep = ["# %s (seed %d, style %s)" % (name, seed, STYLE), "",
       "Map: `%s\\Maps\\%s.un2` (mutator cards enabled). Run folder: `%s`." % (ib.GAME, name, RUN), "",
       "## Systems", "needs %d, unmet %d, score %.2f; pipes %d m, cables %d m, conveyors %d m" % (
           S["needs"], len(S["unmet"]), S["score"], S["pipes_m"], S["cables_m"], S["conveyors_m"]),
       *("- %s needs %s: %s" % tuple(u) for u in S["unmet"]), "",
       "## The window frame", "score %.2f: %s buildings in frame, hero %s at u=%s (thirds %s), town span %s, depth %s, leading line %s (isl_frame.png)" % (
           FRAME.get("total", 0), FRAME.get("in_frame"), FRAME.get("hero"), FRAME.get("hero_u"), FRAME.get("thirds"), FRAME.get("span"), FRAME.get("depth"), FRAME.get("lead")),
       "on the graded ground: score %.2f, %s buildings, hero %s" % (FRAME_G.get("total", 0), FRAME_G.get("in_frame"), FRAME_G.get("hero")) if FRAME_G else "", "",
       "## Co-direction (final = graded ground, isl_ec.bmp; codirection_final.txt)", "```", codirect.report(FINAL, "FINAL (graded)"), "```",
       "before grading (isl_e.bmp), for comparison: total %.3f, %s" % (PRE["total"], ", ".join("%s %.2f" % (k, PRE[k]["score"]) for k in ("writer", "director", "engineer", "level", "artist"))), "",
       "## Story keys (story.txt: summit, water tower, drain, taps, conc, interiors)",
       open(os.path.join(RUN, "story.txt"), encoding="utf-8").read().strip() if os.path.exists(os.path.join(RUN, "story.txt")) else "-", "",
       "## Walks", "%d trips a day, %.1f km on foot; checks:" % (
           sum(1 for w in L.get("walks", []) if w.get("path")), sum((w.get("m") or 0) * w.get("n", 1) for w in L.get("walks", [])) / 1000),
       *("- " + c for c in L.get("walk_checks", [])), "- (none)" if not L.get("walk_checks") else "", "",
       "## Believability", open(os.path.join(RUN, "believability.txt")).read().strip() if os.path.exists(os.path.join(RUN, "believability.txt")) else "-", "",
       "## Terrain", "```", score.strip(), "```", "",
       "## Pictures", "- sketch: isl_sketch.png", "- layout: isl_layout.png", "- pads: isl_map.png", "- walks: isl_walks.png", "- viewshed (what the player sees): isl_vis.png",
       "- figure-ground: isl_figureground.png, Nolli plan: isl_nolli.png, sections A/B/C: isl_sections.png",
       "- the architectural set: plans/A-001 parti ... A-401 serial vision",
       "- editor: isl_ed_plant.png, isl_ed_side.png, isl_ed_island.png"] + (["- game: pilot_sheet.png, closeups_sheet.png"] if sheet else []) + [
       "", "## Timing", *("- %s: %.0f s" % (t, d) for t, d in log), "- total: %.0f s" % (time.time() - t0)]
open(os.path.join(RUN, "report.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
print("\nreport ->", os.path.join(RUN, "report.md"), flush=True)
