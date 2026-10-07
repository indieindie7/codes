r"""Concept to believable town, one command (see ../PIPELINE.md):

    py tools/town.py <seed> [style=plateau|ridges] [name=TutA_Town] [pilot=1] [shift=-5300] [rerolls=3]

island (terrain tool sketch, formed + eroded) -> layout (interest maps, roads, Voronoi drift) -> systems
(provides/needs, connections; an unmet core need re-rolls the layout with the next seed) -> pads -> TutA
terrain -> buildings as StaticMeshActors + lighting -> editor pictures -> pilot run -> report.md.
Everything lands in Documents\U2_research\towns\<name><seed>\.
"""
import json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(HERE, "tools")
sys.path.insert(0, TOOLS)
import island_batch as ib  # noqa  (helpers: run, pilot_script, populate, enable_map, island_png, TEMPLATE, PILOT, GAME)
import systems  # noqa

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
seed = int(args[0]) if args else 1
STYLE = o.get("style", "plateau")
NAME = o.get("name", "TutA_Town")
PILOT = o.get("pilot", "1") != "0"
SHIFT = o.get("shift", "-5300")
REROLLS = int(o.get("rerolls", 3))
METHOD = o.get("method", "spine")      # spine = street first, plots along it (layout_spine.py); interest = layout.py
name = "%s%d" % (NAME, seed)
RUN = os.path.join(r"C:\Users\john\Documents\U2_research\towns", name)
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


# 1. the island
step("island", lambda: ib.run(["py", os.path.join(TOOLS, "island_form.py"), seed, ib.TEMPLATE, base + "_e.bmp",
                               "png=" + base + "_sketch.png", "style=" + STYLE]))
score = subprocess.run(["py", os.path.join(os.path.dirname(os.path.dirname(HERE)), "..", "tools", "python", "terrain", "terrain_tool.py")
                        if False else ib.TERRAIN, "score", base + "_e.bmp", "--cell", "512", "--zstep", "0.5", "--unit", "0.02"],
                       capture_output=True, text=True).stdout
open(os.path.join(RUN, "terrain_score.txt"), "w").write(score)

# 2 + 3. layout and systems, re-rolled until the core needs are met
layout = base + "_layout.json"
best = None
for k in range(REROLLS):
    lseed = seed + 100 * k
    cand = base + "_layout_%d.json" % lseed
    tool = "layout_spine.py" if METHOD == "spine" else "layout.py"
    step("layout %s (seed %d)" % (METHOD, lseed), lambda: ib.run(["py", os.path.join(TOOLS, tool), base + "_e.bmp", cand,
                                                                  "seed=%d" % lseed, "shift=" + SHIFT, "png=" + cand[:-5] + ".png"]))
    Lc, core_unmet = systems.run(cand, report=True)
    key = (len(core_unmet), -Lc["systems"]["score"])
    if best is None or key < best[0]:
        best = (key, cand)
    if not core_unmet:
        break
    print("  re-rolling: %d core needs unmet" % len(core_unmet), flush=True)
shutil.copy(best[1], layout)
shutil.copy(best[1][:-5] + ".png", base + "_layout.png")
L = json.load(open(layout))
print("  using", os.path.basename(best[1]), "score %.2f, %d core unmet" % (L["systems"]["score"], best[0][0]), flush=True)
open(os.path.join(RUN, "systems.txt"), "w").write(
    "needs %d unmet %d score %.2f\n" % (L["systems"]["needs"], len(L["systems"]["unmet"]), L["systems"]["score"])
    + "".join("  %s needs %s: %s\n" % tuple(u) for u in L["systems"]["unmet"]))

# 4. pads, 5. terrain into TutA, 6. the buildings as actors + lighting + editor pictures
step("pads + roads", lambda: ib.run(["py", os.path.join(TOOLS, "terrain_cutfill.py"), base + "_e.bmp", base + "_ec.bmp", "shift=" + SHIFT, "layout=" + layout]))
ib.island_png(base + "_ec.bmp", base + "_map.png")
# the ground paint: rock base, sand on roads / yards / beach, plant life on gentle ground (TutA's three layers)
ALPHA_TPL = os.path.join(r"C:\Users\john\Documents\U2_research\terrain", "alphas")
step("ground paint", lambda: ib.run(["py", os.path.join(TOOLS, "groundpaint.py"), base + "_ec.bmp", layout, ALPHA_TPL, os.path.join(RUN, "alphas")]))
step("terrain", lambda: ib.run(["py", os.path.join(TOOLS, "terrain_apply.py"), base + "_ec.bmp", name, "alphas=" + os.path.join(RUN, "alphas")]))
t3d = base + "_actors.t3d"
step("export", lambda: ib.run(["py", os.path.join(TOOLS, "export_mutator.py"), "shift=" + SHIFT, "layout=" + layout, "t3d=" + t3d,
                               "heightmap=" + base + "_ec.bmp", "props=0"]))
# clutter and vegetation: lamps along the trunk roads, crates and barrels in the yards, fences, rocks, trees
clut = base + "_clutter.t3d"
step("clutter", lambda: ib.run(["py", os.path.join(TOOLS, "clutter.py"), base + "_ec.bmp", layout, clut, "seed=%d" % seed, "before=" + base + "_e.bmp"]))
with open(t3d, "a") as f:                      # one import: the clutter actors are appended to the buildings' T3D
    body = open(clut).read()
    f.write("\n" + body[body.index("\n") + 1:body.rindex("End Map")])
step("populate", lambda: ib.populate(name, t3d, layout, base))
ib.enable_map(name)

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
       "## Terrain", "```", score.strip(), "```", "",
       "## Pictures", "- sketch: isl_sketch.png", "- layout: isl_layout.png", "- pads: isl_map.png",
       "- editor: isl_ed_plant.png, isl_ed_side.png, isl_ed_island.png"] + (["- game: pilot_sheet.png, closeups_sheet.png"] if sheet else []) + [
       "", "## Timing", *("- %s: %.0f s" % (t, d) for t, d in log), "- total: %.0f s" % (time.time() - t0)]
open(os.path.join(RUN, "report.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
print("\nreport ->", os.path.join(RUN, "report.md"), flush=True)
