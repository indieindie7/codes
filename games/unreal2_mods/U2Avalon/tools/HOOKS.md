# Hooks: the binder's story keys in the town generator

Binder 1940260 added keys the generator did not read: room sheets, `building:room` stops, `takes:`, the `conc`
resource, rule-placed story buildings, and the parti's hero. This file records where each one is wired in. The
wiring was applied on top of 24a454b. That commit already did the hero swap in compose.py, codirect.py and
layout_spine.py, and the `conc` chain in systems.py, so those parts are not repeated here.

## The modules

| module | reads | writes | CLI on a run folder |
|---|---|---|---|
| `binder.py` | `binder/rooms/*.md`, `rooms:`/`takes:` keys, `tower:catwalk` stops | `load_rooms()`; the checks | `py tools/binder.py` |
| `anchors.py` | heightmap + spine / layout | hero summit + truck road, guest_house, water_tower (E14'), the drain | `py tools/anchors.py <run>` -> `anchors.json`, `isl_anchors.png` |
| `takes.py` | layout with systems connections | `L["taps"]`, clutter props, conc report | `py tools/takes.py <run>` -> `taps.json`, `isl_taps.png` |
| `rooms.py` | sheets + room sheets (+ layout) | interior plans | `py tools/rooms.py <run>` -> `rooms.json`, `isl_rooms.png` |
| `pathlinks.py` | `isl_ec.bmp`, layout, `isl_clutter.t3d` (or an empty one) | runs `pathnodes.py` + drain / truck-road node chains | `py tools/pathlinks.py <run>` -> `isl_paths.t3d`, `paths.txt` |

The standalone CLIs never rewrite the run's layout unless you pass `write=1`.

## Pipeline order (town.py)

1. island, relief, viewshed (unchanged)
2. per candidate: `layout_spine.py`
   - section 3, after the anchors: `anchors.summit()` puts the parti's hero on the summit and adds its truck road
     as a branch;
   - section 4: `RULED` = {guest_house, water_tower, drain} are left out of the plot order;
   - after the plots: `anchors.beside()` (guest_house) and `anchors.water_tower_site()`;
   - at the output: `anchors.drain()` -> `out["drain"]` + `buildings["drain"]` (underground, at its grate), and
     `out["anchors"]`.
3. town.py: if a reused layout lacks the hero or the drain (an older layout), `anchors.apply()` places them
   late; then `systems.run()` (conc already in its chain, 24a454b), compose, codirect.
4. cut/fill, viewshed, `walks.py` (the drain is a tunnel edge between its grate and outfall:
   `anchors.walk_edges()`; kind `culvert` isn't walled).
5. **`story_extras()`** (new step after walks): `takes.taps()` -> `L["taps"]`; `rooms.build()` -> `<run>/rooms.json`;
   `isl_taps.png`, `isl_rooms.png`, `story.txt` (summit, water head, drain, taps, conc chain, interiors);
   report.md gets a "Story keys" section.
6. drawings, plans, metrics, the final review (unchanged); `clutter.py` places the taps' poles and drums
   (`takes.clutter_items`).

## The diffs, in short

layout_spine.py, after the anchor loop in section 3:

```python
import anchors
RULED = {"guest_house", "water_tower", "drain"}
SUMMIT = None
if PARTI_HERO in buildings and PARTI_HERO != "tower" and PARTI_HERO not in placed and o.get("summit", "1") != "0":
    SUMMIT = anchors.summit(Z, SPINE.pts, buildings[PARTI_HERO], MAIN, avoid=[...tower, authority_pad, dock, mine...])
    if SUMMIT:
        place(PARTI_HERO, SUMMIT["x"], SUMMIT["y"], SUMMIT["yaw"])
        ROADS.append(Road([tuple(p) for p in SUMMIT["road"][::-1]], "branch_summit"))
```

```diff
-order = [bid for bid in buildings if "at" in buildings[bid] and bid not in placed]
+order = [bid for bid in buildings if "at" in buildings[bid] and bid not in placed and bid not in RULED]
```

After the plot loop: `anchors.beside(placed, buildings, "directors_house", "guest_house", Z)` and
`anchors.water_tower_site(Z, placed, buildings, main=MAIN)`, each followed by `place()`. Before `json.dump(out)`:
`anchors.drain(Z, out, buildings, MAIN)`. Flags: `summit=0` and `drain=0` turn them off.

walks.py:

```diff
-NOT_WALLED = (..., "mast")
+NOT_WALLED = (..., "mast", "culvert")
+TUNNELS = anchors.walk_edges(L.get("drain"), to_fine, nearest_free, NF)
-        G = graph(wear, [(S, k, pen) for _, k, pen in ea])
+        G = graph(wear, [(S, k, pen) for _, k, pen in ea] + TUNNELS)
```

clutter.py, section 2d: `for mesh, x, y, yaw, scale, lift in takes.clutter_items(L["taps"]): actor(...)`.

compose.py (the coordinator's pick, 2026-10-09): `PITCH = -15.0`, so `PITCH_RU = 62805` (-2731). codirect's
horizon check reads `compose.PITCH`, so it follows. The command room's PlayerStart in the map should face Pitch
62805.

## The hero

Already done in 24a454b: `parti.json "hero"` with a `"tower"` fallback.
- compose.py: hero = the parti's hero if it is in frame, else `second` (cooling_towers), else the tallest.
- codirect.py: `hero_id()`.
- layout_spine.py: `PARTI_HERO` in `hides_tower`.

The ids that still read `"tower"` mean the Authority tower on purpose: the window's eye, the walk's end, the 150 m
squatter guard.

## The rules, round 2 (the coordinator, 2026-10-09)

- **The hero in the window.** The summit candidates are scored in compose's frame: yaw 300 ± 34, pitch −15 ± 26,
  with the top not hidden by the terrain.
  - Any spot in the frame beats any spot outside it, so a lower summit inside the cone wins over a higher one
    outside.
  - Inside the frame, height wins, plus 25 m of "height" for a vertical third. A spot at the frame's side edge
    (u < 0.1 or u > 0.9) gets half the bonus.
  - If the town's strip has no spot in the frame, the search widens to 600 m from the town's spine. Only then does
    it fall back to the highest spot outside the frame, logged on stderr and marked `fallback`.
  - The hero's dock clearance is 100 m (it was 150 m, which emptied Cine8's frame).
- **The truck road** is grade-capped. A step over `MAX_GRADE` (12 %) is closed, the routing uses 16 headings
  (knight moves), and the road switchbacks. The cap is relaxed only when no capped road exists (×1.25, ×1.5, ×2,
  then soft), and `road_cap` records it.
- **E16 for rule-placed dwellings.** The guest house stays ≥ 100 m from every fuel store (`systems.spec_of`
  providers of fuel). It walks up to 60 m further out, or behind the host, to manage it. If it can't, it is
  flagged `e16_ok: false`.
- **The drain profile** is laid from the outfall upstream:
  - The invert is +0.5 m over the sea at the outfall (a free outfall). Going upstream it rises by the 0.5 % fall,
    and the cover over the roof never exceeds 12 m.
  - Where the invert then drops faster than the fall, the step is a drop shaft (`drop_shafts`).
  - Where the cover is under 1 m (outside the last 15 m, the headwall), the run is a covered cut at grade
    (`shallow_m`).
  - The route avoids ground more than 12 m over the grate, and the outfall prefers a bank high enough for the
    culvert.
- **Splices.** When a company line already passes the shanty block (a run under 4 m), the tap becomes a splice:
  sagging leads (power) or hoses with drums (water) from the line to the nearest 3 shacks, each at least 3 m long.
  The styles are `splice_cable` and `splice_hose`.

## Still open

- No sagging-cable mesh exists. The spans and drops are in `L["taps"]` as lines with `sag_m`, and the poles use
  the Pylon at 0.45 scale. A crooked-pole part and a cable part are build_parts work.
- export_mutator doesn't build the drain yet. `L["drain"]` has the polyline with ground and invert z, the section
  sizes and the segments (grate, culvert, junction room, sluice gallery, outfall). The shell build needs a
  `B_culvert` part (artist s. 5).
- `rooms.json` is input for the hollow-shell kit (engineer s. 2.0), which doesn't exist yet.

## Round 3 (done 2026-10-09; the plan below was followed, with these notes)

- 1 anchors.summit: edge-only spots get no bonus; `edge_u`, `over_works_m` (works_z) are reported. compose.EDGE_U:
  the parti hero is the window hero only when inner, else `second`; `parti_hero` in compose's dict says which.
- 2 water_tower_site: head per candidate (`head_map`), the LOWEST with >= HEAD_M (28) wins, else the most head;
  `pick`, `head_in_target` (28-50 m), `candidates_with_head` in the site dict.
- 3 anchors.dock_occluder -> L["occluders"]; layout_spine calls it at the output (natural ground), town.py's late path
  adds it to round-2 layouts, and story_extras RE-FITS it on isl_ec.bmp (the quay pad lifts the stations by metres).
  clutter.py 2e builds the stack; codirect._boxes counts it; beat 1 = 1 / WARN 0.5 (no fit) / 0 (shows past it).
  LD2: BEAT_HARD_S = 90 scores, gaps over 60 s are a note. LD7: the drain's grate -> gallery time counts, credit qs/25
  under 25 s (UU_QUIET 3600 = 14 s, so it is partial until the level designer lengthens the quiet stretch).
- 4 pathlinks.py wraps pathnodes.py (read-only) + GenStory PathNodes on the drain invert and the truck road;
  town.py runs it in story_extras (empty clutter T3D) and again after the clutter. Town7: 8 parts, the truck road
  joins 2 of them (-> 7), the drain's grate has no walkable cell within 20 m.
- 5 codirect.marks_review (M1-M4 + needs-in-game), `R["marks"]`, printed by report(); score_runs root= + marks.
  liandri_tower.md: `model: PyramidTower` (Q83).
- 6 anchors.arenas: arenas.json's E1-E4 by origin + yaw at the route stops (E1 the dock, E2 the drain's grate, E3 the
  drain's outfall facing the cooling towers, E4 the truck road's foot facing the hero) -> L["arenas"] (world UU);
  LD5 counts their P as a junction and their cover as boxes.
- 7 anchors.process_chain (binder 10829b6): the nine chain sheets placed in order after the plots (layout_spine,
  RULED); systems STAGES ore = portal | crusher | transfer | silos | halls | hall_b, + tailings thickener -> outfall,
  thickener as an optional conc stage; rooms.py reads room sheets' `size:` and plans control_room on hall_b's uphill
  gable stair tower (B["hall_b"]["low_gable"] from the thickener placement tells export which end to mirror).
  Open: one transfer tower cannot bring a 100 m drop over 300 m under 12 deg (Town7's island, seed 907: the
  crusher -> transfer leg is 18 deg); the silos' "uphill" side is sometimes lower than hall_a.

The plan as it was written:
1. **An edge-only hero counts as outside the frame** (u < 0.1 or > 0.9).
   - anchors.summit: drop the half bonus for edge spots, and break ties among inner spots by height over the works.
   - compose.py: the parti hero counts as the window hero only when it is inner. Otherwise the cooling towers stay
     the window hero (plan D1 fallback c).
2. **Water tower (E14'):** in water_tower_site, pick the LOWEST candidate whose head is >= 28 m (target 28-50 m)
   over the highest floor of everything it serves, the hero included. Compute the head per candidate. If no
   candidate reaches 28 m, take the one with the most head.
3. **Beat 1.** codirect.serial already tests the hero.
   - Add a cheap occluder: anchors.dock_occluder() puts a B_shed_a stack on the first station's sightline to the
     hero, when the free ground allows it.
   - Write it to L["occluders"] and place it in clutter.py. codirect's _boxes must count it.
   - If no occluder fits, beat 1 is a WARN (0.5 credit), not a fail.
   - LD2: a gap over 60 s becomes a note; the score only counts past 90 s.
   - LD7: give credit for the drain's quiet stretch (25-60 s before the sluice gallery).
4. **pathnodes.py** (f112e91) runs in town.py's story step.
   - When isl_clutter.t3d doesn't exist yet, run it in a temp folder with an empty clutter T3D, and run it again
     after the clutter step in a full build.
   - Add PathNodes along the drain (invert + 60 UU) and the hero's truck road, from anchors.py.
   - Report the parts before and after: Town7 had 7 parts (1887 + 78 + 40 + ...).
5. **A "marks" review in codirect** (redesign/2026-10-09/marks_checklist.md): its own section, scored with notes,
   no veto, kept out of the 5-role total so the scores stay comparable.
   - Floating props: building footprints on graded ground, and clutter Z against the ground.
   - Horizon rigs: rigs, islets and far_islands inside the map extent and visible from the eye.
   - Q74: rich high, poor low, no poor housing on the town's top 10 %.
   - No cranes on pyramids: the hero's `model:` must not be a Crane. liandri_tower.md said `model: CraneTower`;
     the user's mark Q83 (the summit tower is AvalonSM3.Liandri.PyramidTower) decides: the sheet now says
     `model: PyramidTower`, and the check reads it.
   - Interiors too dark and rain roofs: list them as "needs in-game check", plus binder hints (lit: no, roof: none).

## Story assets (2026-10-09, STORY_ASSETS.md): the hooks

Done in this pass (kit_parts.py, story_export.py, shells.py, export_mutator.py): the drain culverts, the taps'
poles/cables/drums and the hollow shells exist as parts + emitters. One-line hooks for the files the other agent
holds (not applied here):

- town.py, after `story_extras()`: `import shells; shells.build(run)` -> `<run>/isl_shells.t3d` + `hollow.json`;
  and give the export step `story=1 hollow=<run>/hollow.json` (export_mutator.py reads both).
- clutter.py section 2d: `if not STORY: for mesh, x, y, yaw, scale, lift in takes.clutter_items(L["taps"]): ...`
  (story_export emits the real poles and drums; the Pylon-at-0.45 stand-ins would double them).
- The "still open" list above: the sagging-cable mesh (B_sagcable), the drain build (story_export.drain_actors) and
  the hollow-shell kit (shells.py) are no longer open; rooms.py's plans drive shells.py unchanged.

## Round 4 (2026-10-09): marks M1 and M3 in the generator; the TutA_Remake907 build run

Before (Town7's own layout re-graded, marks on isl_ec.bmp): M1 0.67, M3 0.40. After, on the same layout: M1 0.92
(the three left are footprints the old layout stacked on each other: shed_b in the dorm's row, the silos under the
hero's plinth), M3 1.00. On the fresh TutA_Remake907 run (below): M1 1.00, M3 1.00.

- **M1, the cause.** terrain_cutfill gave every sheet with an `at:` a disc of 0.6 x size + 600 UU at the mean height
  of its instances, merged overlapping discs into terraces up to 64 m across whatever their heights (area-weighted),
  forced the footprints last-wins, and graded the roads AFTER the pads. `far_islands` (kind islet, 400 x 200 m,
  "3 along") was not excluded: a 42600 UU disc at -4191 that forced most of Town7's island to one level (the dock
  rose 26 m, the director's house fell 26 m: E23's 15.5 m quay, the M3 flip from 1.0 natural to 0.4 graded). The nine
  chain sheets absent from an old layout got pads at their placeholder `at:` spots.
- **M1, the fix (terrain_cutfill.py, rewritten).** Order: the arenas' floors (anchors.arenas on the natural ground,
  land cells, lowest priority) -> the roads (graded from the natural ground) -> the pads -> the dock cutting -> every
  footprint forced level once more. A pad is the sheet's w x d rectangle turned by the layout yaw, one per instance of a
  `count:` group (anchors.footprints, shared with codirect), plus half a cell; ONE level per building = the mean of the
  road-graded ground under its footprint (a plot sits at its street); blended back over 400 UU. Touching pads within
  4 m share a terrace (members' own levels never span more than 6 m: `max_step=`, `max_span=`); otherwise each keeps
  its level and the step is a wall (clutter's rim walls, unchanged). Skipped: rig/barge/wreck/islet/culvert, the stock
  tower, and with layout= every sheet the layout did not place. The hero gets the same flat plinth terrace. A pad never
  sits under 2 m over the sea (`quay_m=`; E23). The tool prints its own M1 self-check (footprints over 2 m of range).
- **M1, the check (codirect.marks_review).** It read a disc of half the LONGEST side, centred half a cell off the
  game's cell frame (`i + 0.5 - fi`; _g and the export use `i - fi`). For a 48 m hall the disc reached 24 m into the
  street, measuring the road's slope, and the half-cell offset made every small footprint read its neighbour cell. It
  now reads the same rectangles + half a cell the grader forces (anchors.footprint_cells). The old numbers in this file
  are the old check's.
- **M1, the layout.** try_place never tested a plot against buildings placed off the roads (the hero on the summit, the
  chain, a cross-road neighbour): Town7 put the silos under the hero's plinth. layout_spine.overlaps_placed (separating
  axis test on the group rectangles + 2 m) rejects such plots; "every free plot overlaps a placed footprint" on stderr
  when nothing is left (add_branch then runs as before).
- **M3 (Q74), layout_spine.** RICH = directors_house, staff_houses, guest_house (beside the director's, so it follows);
  poor = is_poor (shanty*, old_camp, decline houses). The boom layer is placed before the decline, so: a RICH plot must
  stand on ground >= the town's plot ground's 60th percentile (and >= the poor's mean + 1 m when poor are placed); a
  poor plot on ground < the rich's mean - 1 m and < the 90th percentile (never on the top 10 %). The best plot that keeps
  the rule wins whenever one exists (hard); otherwise the score pays `rank_k` (2.0) per 10 m short and stderr says
  "Q74: no plot keeps the rank order". bid_rent reads the same rank (0..1 among the plot ground) as a value field:
  rich +0.6 x (rank - 0.5), poor the opposite. The plume rule (SMOKE_K, the shanty downwind) and the plot/road logic are
  untouched.
- **Arenas over the sea (anchors.arenas, after the build run).** TutA_Remake907 had E1 and E3 51 % over the water and
  remake_build left 17 cover pieces out. Two causes. (a) The facing: arenas.json's E1 draws the sea strip + jetty at
  the TOP of the plan with P under them and the dock gate at the bottom, E3 the rim + sluice mouth at the top and the
  legs below, so both look DOWN the plan (-y); placed with the docstring's +y they went inland-side-out (E1's "sea"
  strip sat on the quay, its dock gate 12 m under the sea). `ARENA_FACING` = {E1: -1, E3: -1} picks the local axis P
  looks along; E2/E4 keep +y. (b) The slide: once origin + yaw stand, the origin slides along the facing axis (and
  sideways), 4 m steps up to 40 m, the smallest slide first, until >= 80 % of the plan's full piece extent is land on
  the Z given (the graded isl_ec.bmp in story_extras, the natural in terrain_cutfill's floor pass); the yaw stays, P
  moves with the origin (`p`); no offset reaching 80 % = the best one, `land_short`, logged via log=. Per arena:
  `land_share_before` (the facing fixed, no slide), `land_share`, `slide_m/along/side`. On TutA_Remake907's graded
  ground: E1 0.49 -> 0.81 (33 m), E3 0.49 -> 0.83 (4 m), E2/E4 1.00 unmoved; cover on land E1 4 -> 10 of 10, E3 2 -> 4
  of 4. On the natural ground E1 reaches 78 % at 40 m (the dock pad is not cut yet), so cutfill's E1 floor sits ~7 m
  off the graded placement; harmless (the dock cutting follows), noted.
- **town.py.** `island=<run folder>` copies that run's island files (isl_e.bmp, isl_sketch.*, isl_vis.*; islands=1
  styles) and skips the island stage; the layouts are made afresh for the seed given. `from=score` resumes a finished
  stop=score run with the editor stages only (see the resume command below).

### The build run (the other chat's input)

    py tools/town.py 907 name=TutA_Remake style=plateau pilot=0 stop=score island=C:\Users\john\Documents\U2_research\towns\TutA_Town7

-> `C:\Users\john\Documents\U2_research\towns\TutA_Remake907`: Town7's island, six layouts rolled (907, 1007 ... 1407),
the best by systems + window frame built (isl_layout_1007.json -> isl_layout.json, with arenas, drain, taps, chain,
occluders), isl_ec.bmp, walks, rooms.json (27 plans, the hollow kit's input), isl_paths.t3d, story.txt, drawings, plans,
codirection_final.txt (five roles + marks; report.md only comes with the editor stages, from=score). The final table (graded ground): total 0.775 - WRITER 0.86,
DIRECTOR 0.62, ENGINEER 0.75, LEVEL 0.92, ARTIST 0.77; MARKS 1.00 (M1 0 of 47 footprints over 2 m, M2 1.0, M3 the company
houses 26 m over the shanty's mean and no poor housing on the top 10 %, M4 PyramidTower). Still open on this island: the
water tower's head (20 m, want 28), the belts over 12 deg (the HOOKS round-3 note), E1 (35 % of the road length over its
grade cap: the roads now follow the real ground; the old grading had flattened the island). The arena floors are only
partly level after the roads re-grade through them (E4 19 m of range, E1/E3 half over the sea): remake_build's cover
sits at the stop's ground, so check the greybox fights in the editor. Re-running the same command with `reuse=1` keeps the islands and
layouts and redoes the grading and the scores (deterministic: systems, walks, rooms and pathlinks draw no random
numbers; takes seeds its drums by crc32).

### The resume command (the editor stages only, no re-scoring)

    py tools/town.py 907 name=TutA_Remake style=plateau pilot=0 from=score

`reuse=1` WITHOUT stop= would also work but is not what you want: it re-runs systems on every kept candidate, copies the
chosen candidate over isl_layout.json again, re-grades, re-walks and re-makes the story keys before reaching the editor
(the same bytes, a few minutes). `from=score` touches none of that: it reads isl_layout.json and isl_ec.bmp as they are,
re-reads the two reviews for report.md, then runs ground paint, terrain_apply, export, clutter (+ the PathNodes again),
populate (import + LIGHT APPLY), low sun and motion -> `Maps\TutA_Remake907.un2`, and the report. pilot=0 keeps the
game out of it. It refuses to start without isl_layout.json + isl_ec.bmp in the run folder.
