# Story assets: the drain, the taps and the hollow-shell kit (2026-10-09)

What this is: the three missing pieces of the redesign generator (plan.md s. 5, engineer s. 2.0, level designer I3/I4,
artist s. 4.7 / s. 5), built offline as parts + T3D. Nothing here has been in the editor or the game yet; the
"unreal modding part2" chat imports it. All numbers are measured from the built meshes (Models/glb/kit_pivots.json).

## 1. The parts (Models/glb/B_*.glb -> Models/ase/B_*.ase, world units, hulls inside)

Built by `tools/kit_parts.py` through build_parts.py (`ids=kit` = all of them, or `ids=B_culvert,B_k_wall`):

    "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python tools/build_parts.py -- Models/glb ids=kit
    py tools/part_to_ase.py scale=50 zero=1 hulls=1 <names...>        # -> Models/ase/<name>.ase on the shared Pal.tga
    py tools/kit_sheet.py                                              # -> Models/renders/kit_sheet.png (CPU, matplotlib)

**Conversion path used (the importer's safe path):** part_to_ase.py now passes `scale=50`, `zero=<name>` and
`hulls=1` through to glb_to_ase.py and writes NO material block (the palette skin is set on the actor / in the ini
as for every other Liandri mesh). The UVs are remapped onto the shared 8-stripe Pal.tga as before (glb_to_ase was
never rerun over the old B_*.glb). So these ASEs are in WORLD UNITS on disk, unlike the older B_wall / B_cable /
B_ctower / B_road ASEs, which are in metres and got their x50 at import. Import these at scale 1.

**Pivot:** glb_to_ase recentres XY on the bounds centre; `zero=` keeps the model's z = 0 as the pivot Z (slabs
whose TOP is z = 0, the culvert's invert at z = 0). The emitters place every part by its AUTHORED origin, using
`Models/glb/kit_pivots.json` (dx, dy = the origin's offset from the bounds centre, metres, in the part's own frame).
Placing one by hand: actor location = origin - R(yaw) * (dx, dy) * 50.

**Collision:** every walkable or blocking part carries `MCDCX_<name>_<k>` GEOMOBJECTs in its ASE, one convex box
per wall pier / lintel / slab / rail line, so door and window openings stay open (the claims test showed an MCDCX_
hull is the player's collision by default when the ASE has one). Poles, cables, hoses, ladders and frames have no
hull (hulls 0 below): the engine builds collision from their polys, or turn bCollideActors off on them. The
in-game check list is in s. 6.

| part | size m (X along, Y, Z) | UU | hulls | origin from centre (m) |
|---|---|---|---|---|
| `B_culvert` | 10.24 x 8.68 x 7.90 | 512 x 434 x 395 | 6 | 0.00, -0.00 |
| `B_culvert_bendP` | 9.36 x 9.88 x 7.90 | 468 x 494 x 395 | 12 | -4.68, -0.60 |
| `B_culvert_bendN` | 9.36 x 9.88 x 7.90 | 468 x 494 x 395 | 12 | -4.68, 0.60 |
| `B_culvert_drop` | 5.62 x 8.68 x 11.00 | 281 x 434 x 550 | 10 | -2.81, -0.00 |
| `B_shaft_slab` | 2.56 x 8.68 x 0.50 | 128 x 434 x 25 | 1 | 0.00, -0.00 |
| `B_junction` | 16.36 x 16.36 x 12.56 | 818 x 818 x 628 | 10 | -7.68, -0.00 |
| `B_gallery` | 31.72 x 16.36 x 9.96 | 1586 x 818 x 498 | 11 | -15.36, -0.00 |
| `B_pillar` | 4.20 x 2.20 x 8.96 | 210 x 110 x 448 | 1 | 0.00, -0.00 |
| `B_outfall` | 4.86 x 13.28 x 8.65 | 243 x 664 x 432 | 18 | -1.15, -0.00 |
| `B_drain_stair` | 14.00 x 3.16 x 8.83 | 700 x 158 x 442 | 22 | 7.00, -0.00 |
| `B_drain_hatch` | 3.46 x 3.46 x 7.80 | 173 x 173 x 390 | 4 | 0.00, -0.00 |
| `B_pole_a` | 1.52 x 1.20 x 5.59 | 76 x 60 x 280 | 0 | -0.51, -0.00 |
| `B_pole_b` | 0.60 x 0.91 x 5.65 | 30 x 46 x 282 | 0 | 0.00, -0.01 |
| `B_pole_c` | 1.03 x 0.60 x 6.18 | 52 x 30 x 309 | 0 | -0.02, -0.00 |
| `B_sagcable` | 10.03 x 0.08 x 0.64 | 501 x 4 x 32 | 0 | -5.00, -0.00 |
| `B_drum` | 1.02 x 0.77 x 0.97 | 51 x 38 x 48 | 0 | -0.20, -0.07 |
| `B_hose` | 10.05 x 0.33 x 0.10 | 503 x 16 x 5 | 0 | -5.00, -0.01 |
| `B_k_wall` | 4.00 x 0.32 x 3.40 | 200 x 16 x 170 | 1 | 0.00, 0.01 |
| `B_k_wall_in` | 4.00 x 0.30 x 3.40 | 200 x 15 x 170 | 1 | 0.00, -0.00 |
| `B_k_wall_door` | 4.00 x 0.32 x 3.40 | 200 x 16 x 170 | 3 | 0.00, 0.01 |
| `B_k_wall_door_in` | 4.00 x 0.32 x 3.40 | 200 x 16 x 170 | 3 | 0.00, 0.01 |
| `B_k_wall_main` | 4.00 x 0.32 x 4.40 | 200 x 16 x 220 | 3 | 0.00, 0.01 |
| `B_k_wall_roller` | 6.00 x 0.32 x 6.00 | 300 x 16 x 300 | 3 | 0.00, 0.01 |
| `B_k_wall_win` | 4.00 x 0.38 x 3.40 | 200 x 19 x 170 | 4 | 0.00, -0.00 |
| `B_k_column` | 0.46 x 0.46 x 3.40 | 23 x 23 x 170 | 1 | 0.00, -0.00 |
| `B_k_slab` | 4.00 x 4.00 x 0.30 | 200 x 200 x 15 | 1 | 0.00, -0.00 |
| `B_k_grating` | 4.00 x 4.00 x 0.12 | 200 x 200 x 6 | 1 | 0.00, -0.00 |
| `B_k_rail` | 4.00 x 0.06 x 1.13 | 200 x 3 x 56 | 1 | 0.00, -0.00 |
| `B_k_catwalk` | 4.00 x 1.60 x 1.23 | 200 x 80 x 62 | 3 | 0.00, -0.00 |
| `B_k_step` | 0.56 x 1.60 x 0.69 | 28 x 80 x 34 | 1 | 0.00, -0.00 |
| `B_k_ladder` | 0.74 x 0.90 x 3.42 | 37 x 45 x 171 | 0 | -0.35, -0.00 |
| `B_k_frame_p` | 2.30 x 0.50 x 2.95 | 115 x 25 x 148 | 0 | 0.00, 0.05 |
| `B_k_frame_m` | 2.86 x 0.50 x 3.99 | 143 x 25 x 200 | 0 | 0.00, 0.05 |
| `B_k_frame_p_auth` | 2.30 x 0.50 x 2.95 | 115 x 25 x 148 | 0 | 0.00, 0.05 |
| `B_k_plinth` | 4.00 x 0.80 x 1.20 | 200 x 40 x 60 | 1 | 0.00, 0.40 |
| `B_headframe` | 12.55 x 8.40 x 24.77 | 628 x 420 x 1238 | 3 | -2.72, -0.00 |
| `B_transfer_tower` | 10.27 x 6.60 x 14.00 | 514 x 330 x 700 | 9 | -1.84, -0.00 |
| `B_thickener` | 17.20 x 16.00 x 5.23 | 860 x 800 x 262 | 11 | 0.00, -0.00 |
| `B_shiploader` | 51.50 x 6.00 x 20.51 | 2575 x 300 x 1026 | 3 | -25.75, -0.00 |

Frame: every part is authored in Unreal's local frame, X = along / forward at yaw 0, Y = right, Z = up, metres x 50.

### 1.1 The drain (level designer I3; anchors.UU_* sections)
- `B_culvert`: one cell (512) long, interior 384 wide x 320 high over the dry ledge; the channel (256 wide) is 25 UU
  below the 128-wide ledge on the +Y side; walls, floor and roof 25 UU; outer 434 x 395. z = 0 is the INVERT (the
  channel floor), the ledge at +25, the roof underside at +345, the roof top at +370, the slab bottom at -25. Pivot
  at the piece's middle: place at the segment midpoint, DrawScale3D X = length / 512, pitched to the fall.
- `B_culvert_bendP` / `_bendN`: 22.5-degree mitred elbows (two 4 m arms meeting on the mitre plane, no inner pleat);
  P turns toward +Y (Unreal yaw +22.5), N toward -Y. Origin = the entry face's bottom centre; exit = origin + 4 m
  along the entry heading + 4 m along the exit heading.
- `B_culvert_drop`: 128 UU of upper floor, then a 128 UU shaft with no floor (a ladder on the ledge wall from +25 to
  -175 UU, a hazard edge), the far wall only above the upper invert so the lower run (placed from +256 along, at its
  own invert) opens into the shaft; the walls reach -180 UU. `B_shaft_slab` (128 x 434 x 25, top at z = 0) goes at
  the lower invert under the shaft. Drops over 180 UU get two shafts.
- `B_junction`: the 768 x 768 x 448 room, floor at the invert, 384 x 345 openings centred on both end faces, a 2 x 2 m
  grate hole in the roof with a 3 m shaft (the street grate's light shaft: put the light there), a pipe run and a
  valve stand. Origin at the entry opening's bottom centre.
- `B_gallery`: the sluice gallery 1536 x 768 x 448, both ends open 384 x 345 (the grate mover at the entry and the
  sluice gate at the exit are the importer's; hazard stripes and the red beacon housing are on the exit), a 128-wide
  dry walk 25 UU up along the +Y wall, six lamp brackets with glow heads on the +Y wall (the reveal's lamps 1..6 at
  x = 3.0 + 4.94 k m, z = 5.0 m). `B_pillar` (2 x 4 x 8.96 m, chamfered, tide band): story_export places 8 in two rows
  at x = 3.84 + 7.68 k, y = +-6.58 m, making the three alcoves per side.
- `B_outfall`: 128 UU of culvert with a headwall, 45-degree wing walls and a parapet; a bar grate across the mouth
  with three bars torn out on the ledge side (a 2.3 m gap = the way through to the basin). Origin at the tube's middle.
- `B_drain_stair`: the dorm-square entrance. Origin at the bottom landing's centre = the culvert's first invert point;
  the stair climbs toward -X (away from the drain) 7.4 m in 17 risers of 21.8 UU (treads 30 UU, 2.56 m wide) in a
  0.3 m walled trench with a kerb at ground level and a rail. DrawScale3D Z = depth / 7.4 m (risers stay <= 35 UU up
  to Z 1.6 = 11.8 m; deeper grates get the hatch). Plan: x = -14.0 .. 0, y = +-1.58 m from the origin.
- `B_drain_hatch`: the alternative, a 2.56-square ladder shaft 7.4 m tall (Z-scaled) with a hatch collar; used when
  the grate is deeper than 11.8 m or with `entry=hatch`.

### 1.2 The taps (takes.py polylines)
- `B_pole_a` (a scaffold tube, 6-degree lean, crossarm, a prop stick), `B_pole_b` (a timber on a drum foot),
  `B_pole_c` (a dead lamp post with a broken head): the hook point at 5.5 m = takes.POLE_H_M; 4.9-6.2 m overall.
- `B_sagcable`: a 10 m span along +X between two points at z = 0, a parabola 0.6 m (30 UU) deep, section 0.08 x
  0.04 m; placed with DrawScale3D X = span / 500 UU, Z = sag / 30 UU, pitched to the chord.
- `B_hose`: 10 m of hose on the ground (X-scaled per piece). `B_drum`: an oil drum with a hose coil.

### 1.3 The hollow-shell kit (storey 3.4 m = 170 UU; walls and slabs 0.3 m = 15 UU)
- `B_k_wall`: a 4 x 0.3 x 3.4 panel, the outside = -Y (dirt band + grey trim on that face); `B_k_wall_in` the plain
  interior panel. shells.py Z-scales them to any band height and X-scales them to any length.
- `B_k_wall_door` / `_door_in`: a 100 x 140 UU personnel opening (importer: >= 96 wide, >= 120 high) in a 4 x 3.4
  panel; `B_k_wall_main`: 128 x 192 (Skaarj routes) in a 4 x 4.4 panel; `B_k_wall_roller`: 250 x 250 in a 6 x 6 panel.
  Hulls: the two piers and the lintel, so the opening is real for collision.
- `B_k_wall_win`: a 3.2 x 0.9 m window opening at 2.0..2.9 m (45 UU tall: no pawn fits), two mullions, a sill; 4
  hulls round the hole.
- `B_k_column` 0.4 sq x 3.4 (Z-scaled to the building height); `B_k_slab` 4 x 4 x 0.3 with its TOP at z = 0 (a floor
  at level z has its walk surface at the actor Z; the roof slab actor sits at H + 15 UU so its underside is at H;
  NoRain boxes and the roof trace meet the slab's top at H + 15); `B_k_grating` 4 x 4 x 0.1 (top at z = 0).
- `B_k_rail` 4 m: posts, a 1.1 m (55 UU) orange top rail, a 0.55 mid rail, a 0.15 hazard toe board, one thin hull;
  `B_k_catwalk` 4 x 1.6 grating with rails on both sides (walk surface at z = 0).
- `B_k_step`: one step 0.56 deep (28 UU tread) x 1.6 wide x 0.68 (34 UU) high with a hazard nosing; shells.py
  places one per riser with Z = riser / 34 UU (rooms.py keeps risers <= 35) and Y = width / 1.6.
- `B_k_ladder` 0.6 wide, 3.4 tall (Z-scaled), caged from 2.2 m; decoration until LadderVolume is confirmed.
- `B_k_frame_p` / `B_k_frame_m`: orange frames round the personnel / main openings (company buildings only);
  `B_k_frame_p_auth`: the same in steel for Authority buildings; nobody's buildings get no frame.
- `B_k_plinth`: 4 m of battered plinth 1.2 m high (0.8 thick at the foot, 0.4 at the top), TOP at z = 0 on the wall
  line, outside = -Y; Z-scaled (`plinth_m=`) to reach the lowest ground.

### 1.4 The process parts (binder 10829b6, D7-D10)
- `B_headframe`: the mine portal, an 8 x 8 arch (2 m piers, a 1.5 m lintel, the dark inside, hazard stripes, rails
  out along +X) under a 24 m A-frame headframe with the sheave wheel and a lamp stub.
- `B_transfer_tower`: 6 x 6 x 14, corner columns, steel panels, a railed top deck at 12 m (walkable hull), a head
  house, the chute down the +X face.
- `B_thickener`: a 16 m ring 4 m high, the slurry surface, a centre column, a railed rake bridge across the top
  (walkable), the rake arms below, launder pipes.
- `B_shiploader`: a 30 x 6 pier deck at 3 m on piles (walkable, railed), a conveyor, a 12 m gantry at the sea end and
  a 25 m boom out over the water with a spout; origin at the shore end, +X toward the sea.
These four are parts only: no emitter places them yet (the sheets' `mesh:` can name them once they have a
building each; `mesh: B_thickener` on a sheet goes through export_mutator as any mesh).

## 2. The emitters

### 2.1 story_export.py (the drain + the taps)
    py tools/story_export.py <run>\isl_layout.json [heightmap=<run>\isl_e.bmp] [entry=stair|hatch] [drain=0] [taps=0]
or from the pipeline: `py tools/export_mutator.py <ini> layout=... heightmap=... story=1 t3d=...` appends the same
actors to the buildings' T3D and prints the notes. Standalone it writes `<run>\isl_story.t3d` and
`<run>\isl_story_notes.json` (the terrain-hole rectangle, the counts, the warnings).

The drain walk: `L["drain"]["path"]` (x, y, z_ground, z_invert every half cell) is simplified (Douglas-Peucker 2.5 m)
with the special spans kept as vertices; straights become B_culvert pieces (yaw, pitch to the invert fall, X = length
/ 512 + 0.4 % overlap); corners over 12 degrees get chains of 22.5-degree elbows centred on the corner (the residual
up to 11 degrees is overlapped); a fall steeper than 30 degrees becomes a drop shaft + shaft slab; the junction (768
centred on segments[2].s_uu), the gallery (segments[3]) and the last 128 UU become B_junction / B_gallery + 8
B_pillar / B_outfall along the span's chord (X-scaled to the chord). The entrance is B_drain_stair (or the hatch) at
the grate.

Scratch counts, Town7: 5 straights, 10 elbows, 4 drop shafts (two overran their short straights: the next piece
overlaps, noted in the json), junction, gallery + 8 pillars, outfall, stair = 35 actors; taps 3 poles, 39 cables,
5 hose pieces, 12 drums = 59. Cine8: 4 straights, 2 elbows, 0 shafts, 18 drain actors; taps 58.

### 2.2 shells.py (the hollow interiors)
    py tools/shells.py <run>  [only=hall_b,dorm] [all=1] [plinth_m=1.2] [shell=rooms|sheet]
Reads `<run>\rooms.json` (run `py tools/rooms.py <run>` first: the plans must come from the current rooms.py - the
control room is only in the new ones) and `isl_layout.json`; writes `<run>\isl_shells.t3d`,
`<run>\isl_shells_tower.t3d` (the Authority tower's lobby, separate because it stands where TutA's own tower BSP is:
your call) and `<run>\hollow.json`. Then `export_mutator.py ... hollow=<run>\hollow.json` leaves those buildings'
solid meshes out (every instance of a `count:` building, e.g. both dorm blocks).

Default set: hall_b (the processing hall, 48 x 20 x 14 per the engineer's SHELLS - NOTE the solid building and its
pad are the sheet's 36 x 16 x 11, so the shell overhangs the graded pad by 6 m at each gable; `shell=sheet` uses the
sheet's size instead), pump_house (12 x 8 x 6; sheet 8 x 6 x 5), dorm (2 blocks), mess (24 x 12 x 5; sheet 16 x 9 x
5), the tower lobby (36 x 28 x 12). Town7: 889 actors + 201 tower.

Per building: ground slab, roof slab + parapet, corner columns, plinth; walls per side as 4 m panels by storey band
(door panels on the ground band at the plan's door positions: roller 6 x 6, personnel 4 x 3.4; window panels on the
full bands of the kind's window sides: dorm front/back, office/house front/left/right, halls = the highest full band
only, the clerestory); partitions for every room smaller than the shell (shared walls deduplicated, a door toward
`door_to` or the room's front), the mess counter as a low block, upper-level slabs per room (the stair bay left
open), gratings with rails on their open edges (mezzanine, catwalk), stairs as single steps (+ a 1.6 m landing slab
when the top is not on a room's slab), ladders at hall gables, door frames by owner, the control room on hall_b's
gable as a box on the roof with window panels on the +x (plant) side and a door toward the catwalk, reached by the
gable stair tower's 20-riser stair (rooms.py).

Scratch T3Ds (Town7 and Cine8) are in the scratchpad: `runs\TutA_Town7\isl_story.t3d`, `isl_shells.t3d`,
`isl_shells_tower.t3d`, `hollow.json`, `isl_story_notes.json`, `isl_actors_story.t3d` (export_mutator story=1
hollow=, 204 actors: buildings minus the five hollow ones, conveyors, pylons, drain, taps).

## 3. Import (the other chat)

1. Meshes: `NEW StaticMeshFactory PACKAGE="AvalonSM" GROUP="Liandri" NAME="<name>" FILE="...\Models\ase\<name>.ase"`
   for every name in s. 1 (manifest.txt has the rows: group Liandri). No scale, no material block: set the skin as
   for the other Liandri meshes (AvalonSM.Pal.Pal). The emitters write `AvalonSM.Liandri.<name>` (pkg= changes it).
   Check one import for the MCDCX hulls: the browser's collision view should show the box pieces, and
   `UseSimpleBoxCollision` must stay OFF on these meshes (a box would close the doorways); the claims test used the
   defaults.
2. Buildings: `export_mutator.py ... story=1 hollow=<run>\hollow.json t3d=...` (or the two standalone T3Ds) + the
   clutter T3D as before; MAP IMPORTADD in chunks of <= 150 actors (the 850-actor crash); LIGHT APPLY after.
3. **The drain's terrain hole.** The terrain above the culvert stays solid (cover >= 1 m everywhere but the grate,
   where the roof top is 0.5 m under the ground). The entrance trench / hatch shaft needs a visibility hole: the notes
   json gives the rectangle (Town7: four corners in `isl_story_notes.json`, 14 x 3.2 m at the grate, heading along
   the drain's first segment) - paint those cells invisible in UnrealEd's terrain tool (visibility / hole mode on
   the TerrainInfo's quads; a 512-UU quad grid, so the hole is one or two cells). Nothing in our tools fakes this.
   The stair's kerb and trench walls stand 0.6 m proud of the ground to hide the cut edge. Alternative without
   painting: start the drain at a terrace rim where the ground drops (anchors.drain start=).
4. The gallery's movers (the entry grate, the sluice gate), the six lamps (brackets on the +Y wall), the red beacon
   light, the junction's grate light and the Door navigation points are placed by hand / U2GM.
5. Taps: story_export's poles and drums replace clutter.py's `takes.clutter_items` (Pylon at 0.45 + barrels): when
   `story=1` is used, run clutter.py with that section off (HOOKS.md) or accept doubles.
6. Lighting: shells are hollow, so interiors need lights (the lit: sheets); none are placed by these tools.

## 4. Hooks (one line each; see HOOKS.md)
- export_mutator.py: `story=1` (drain + taps), `hollow=<json>` (skip solid meshes), `entry=stair|hatch`; `mesh: none`
  without a `card:` is now skipped (binder 10829b6).
- town.py (not edited; the other agent's file): after `story_extras()` add `shells.build(run)` -> isl_shells.t3d +
  hollow.json, and pass `story=1 hollow=<run>/hollow.json` to the export step; clutter.py section 2d: skip
  `takes.clutter_items` when story=1.

## 5. Unfinished / known limits
- hall_b's two-pad stepped shell (`pads: 2 step=4.8`): not built; the shell is one level on one pad. The engineer's
  upper floor (bays 1-3 at +4.8 m) would be an upper slab + a 2 m stair in shells.py once terrain_cutfill grades
  two pads.
- The control room's glass sloped out 15 degrees: the window panels stand vertical; the sloped glass needs a part.
- The control room sits on the roof slab (z = H + 0.3) at the plan's x = 17 (the uphill gable in rooms.py's frame);
  shells.py does not read `low_gable` to mirror it.
- Doors above the ground floor (plan doors with z > 0) are ignored; roller doors only on the ground band.
- Elbows: the residual turn (up to 11 degrees) is overlapped, so a small outer-corner gap can show where a chain
  under-turns; the straight after each chain re-aims at the next vertex. A 90-degree corner = 4 elbows.
- Two of Town7's drop shafts overrun their straights (noted in the json): the following piece overlaps the shaft.
- Palette: 8 stripes only; the artist's slate / cyan / hazard yellow (12 stripes, D5) are not in; hazard reads as
  orange, the Authority's frames as steel.
- The tower lobby overlaps TutA's own tower BSP; it is in a separate T3D.
- The taps' hoses lie on the simplified ground (pitched per 10 m piece); on rough ground they clip.
- The four process parts have no emitter / sheet yet.
- No in-game test of anything here (no editor or game work in this chat).

## 6. Test list (in the game, after import)
1. Walk the drain end to end from the dorm-square stair: no gap at any joint, no pleat that stops the player, ramps
   (<= 30 degrees) walkable, every drop shaft's ladder usable (or droppable) and the lower run reached.
2. Headroom: the culvert's 345 UU and the door openings' 140 / 192 / 250 clear the 108-tall pawn; the junction's and
   gallery's 448 clear the Skaarj's 256 leap.
3. The outfall gap (2.3 m) passes the player; the bars block elsewhere.
4. Each shell: every exterior door opening passable (MCDCX hulls = piers + lintel, nothing in the gap); windows
   block; stairs climb (34 UU risers, AI too); the mezzanine / catwalk rails stop a walk-off; the upper dorm floor and
   the stair bay hole; the mess counter; the control room via the gable stair.
5. Rain: NoRain boxes meet the roof slab (top at H + 15 UU); the roof trace line.
6. Taps: poles stand on the ground (CullDistance 12000), cables hang from the hook to the shack eaves at their sag,
   drums on the ground; no cable through a building.
7. Collision sanity on one imported mesh: stand on B_k_slab, walk into B_k_wall, through B_k_wall_door.
