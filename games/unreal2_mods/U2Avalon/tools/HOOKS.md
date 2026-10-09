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
