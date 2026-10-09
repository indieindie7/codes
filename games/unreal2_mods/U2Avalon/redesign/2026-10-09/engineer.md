# Avalon redesign: the ENGINEER's proposal (2026-10-09)

Role: civil and process engineering (codirect.py ENGINEER, E-checks). Written during the playtest swap: no GPU, game, editor
or pilot job ran. The only computation was CPU-only Python over the existing run folders (`TutA_Cine8`, `TutA_Town7`). It
used `codirect.review()` and a probe that sampled the cut heightmaps. All numbers below come from that probe unless marked
otherwise.

Scale: 1 m ≈ 50 UU; the player walks at 263 UU/s (5.3 m/s); a heightmap cell is 512 UU (10.24 m). The game-metric
numbers (doors, risers) come from `research_notes/Level design practices/report.md`. That report warns that U2's pawn
CollisionRadius/CollisionHeight haven't been read from the game. **Check them first**: the interior numbers assume a
UT-like pawn of about radius 25 UU and half-height 44 UU (88 UU, about 1.76 m), MaxStepHeight about 35 UU, and a
walkable floor of about 45°.

---

## 1. The plant's process flow (mine → conveyor → processing → storage → dock)

The binder already has most of the pieces, but no single chain runs through them. As the binder stands:
- ore can come from a wellhead, a silo or a rig;
- `hall_*` take ore from whichever provider is nearest;
- `tank_farm` "needs fuel";
- the cooling towers cool a hall.

A real island concentrator is one line that falls downhill. This is the line I propose. Each step is one building, and
one visible carrier joins it to the next:

```
 MINE (high, inland)                                        z highest
  [mine_portal + headframe] -> [crusher_house] -> ROM pad
        |  overland belt gallery, straight, <= 12 deg, bents every 20 m   <- THE ORE LINE (parti datum)
        v
  [transfer_tower] (at each bend, 10+ m over the incoming belt)
        v
  [silos]  coarse/fine ore bins at the TOP of the plant terrace        z(silo) < z(mine)
        |  short feeder belt (enters the hall at roof height)
        v
  [hall_a]  CRUSHING + GRINDING (core era, the old mill)              terrace 1
        |  slurry launders/pipes, falling
        v
  [hall_b]  FLOTATION + FILTERS (boom era, the big lit hall)          terrace 2 = 4.8 m lower
        |-> [thickener] (outside, low end)  -> tailings line -> [tailings_outfall] (sea, downwind, down-current)
        v
  [tank_farm]  CONCENTRATE SLURRY tanks (agitated; the pipeline's origin at their feet)
        |  slurry pipeline on sleepers, pump_station = its booster/terminal pump at the shore end
        v
  [conc_shed + filter] at the dock -> [shiploader] on the quay  -> ship
                                   -> trucks -> [cargo_pad] (the off-world share)
```

Utilities that serve the line:

```
 [intake] (screens at the shore) -> [pump_house] (wet well + 2 duty/1 standby pumps + desal stacks)
     -> rising main UP the hill -> [water_tower] (the HIGH service reservoir, 20-30 m head)
     -> town + halls;  [water_tanks] stay LOW by the pump house as raw/desalinated storage
 berth -> fuel line on sleepers -> [fuel_depot] (bunded, >= 100 m from homes) -> [generator_house]
 [cooling_towers] cool the GENERATOR's condenser (and hall_b's process water) -> stand beside the generator
 [generator_house] -> [substation] (new) -> pylons -> plant, town, the one line to the tower
 [sewage_works] (new, small) at the lowest land cell, downwind of company housing, outfall >= 150 m from the intake
 offshore: [new_rig], [wellhead_a/b] = sea-floor borehole ore; slurry by sea-floor pipe to the dock's conc_shed
           (or drop them from the ore chain and keep them as the "where the money is now" story set)
```

The real precedents:
- Kennecott: a 14-storey mill climbs the hill under the tramway terminal.
- Hedley: a gravity tramway runs down to a mill built so the ore moves through by gravity.
- Antamina-style concentrate slurry lines to a port filter plant (a general fact, not fetched this session).
- The 911metallurgist flowsheets: crush → screen → fine ore bin → ball mill/cyclone → rougher/cleaner cells →
  thickener → filters set directly above the concentrate bins → shed.

**What it means for the binder:**
- **New sheets:** `mine_portal` (+ headframe), `crusher_house`, `transfer_tower`, `thickener`, `conc_shed`,
  `shiploader`, `substation`, `sewage_works`, `tailings_outfall`, `plant_fence` with `dock_gate`/`company_gate`. The
  gate and fence names already appear in `parti.json` as edges/gateways, but they have no sheets.
- **Changed roles:**
  - `hall_a` becomes crushing + grinding;
  - `hall_b` becomes flotation + filters;
  - `tank_farm` becomes concentrate slurry, so it is not fuel: drop its `needs fuel` and `provides fuel`;
  - `pump_station` becomes the slurry booster/terminal pump;
  - `cooling_towers` cool the generator.
- **systems.py:** a new resource `conc` (pipe, reach 600) runs hall_b → tank_farm → conc_shed. Ore gets a stage order
  (see E22).

## 2. Interiors (dimensions for `build_parts.py`)

### 2.0 What the kit has now, and what it lacks

`build_parts.building()` fills every walled building with a solid charcoal box:
`box(0, 0, H/2, W-0.5, D-0.5, H, "charcoal")`. Two consequences:
- No interior can be walked today.
- Doors are only painted panels on that solid box.

`stair()` is a solid 1.8 × 3.6 × H block, not steps. The interiors need a **hollow mode** plus about 12 new parts. The
proposed kit is below. All of its parts are boxes and cylinders, like the existing parts, in metres, with front = −Y:

| part | real basis | game size (m) | UU | notes |
|---|---|---|---|---|
| `shell(hollow=1)` | portal frame shed | walls 0.3 thick, columns 0.4 sq at **6 m bays** | 300 UU bays | no inner box; floor slab 0.3; roof on the columns; the window strips stay |
| `door_personnel` | 0.9 × 2.1 real | **1.6 × 2.8** (was 1.3 × 2.6) | 80 × 140 | inside the 64–96 × 128–160 UU game band, not at its edge |
| `door_roller` | 4–5 m truck doors | **5 × 5** for halls (4 × 4 stays for sheds and pumps) | 250 × 250 | the crane_cab truck fits; a real opening, not a painted panel |
| `stair_flight` | OSHA riser ≤ 24 cm, tread ≥ 24 cm | riser **0.283**, tread **0.56**, width **1.6** (main 2.0), 12 risers = one 3.4 m storey | 14.2 / 28 / 80 (100) UU | about 27°, reads as stairs; landing 1.6 × width every 12 risers; flight run 6.2 m (308 UU) |
| `landing` | | width × 1.6 | | at every storey and every 12 risers |
| `slab_grating` | bar grating | 0.1 thick | 5 UU | catwalk and mezzanine floors; the "grated catwalk" of the peak frame |
| `catwalk` | 0.8–1.0 real | **1.6 clear** (main 2.0) | 80 (100) UU | 2 × pawn radius + margin; a run along a path at height z |
| `rail` | OSHA top 42 in (1.07 m), mid-rail at half | top **1.1**, mid **0.55**, posts every 1.5 m, orange | 55 / 27 UU | on **every** edge with a drop > 1 m (this answers Q9) |
| `ladder` | caged ladder | 0.6 wide, cage over 3 m | | **decoration only** until U2's LadderVolume is confirmed; player routes use stairs |
| `hoist_beam` | monorail / overhead crane | I-beam 0.4 deep, along the bay line at H − 1.5 | | one over every machine row; the crane rail in the halls |
| `pipe_run` | | ⌀0.3–0.6 on brackets at 3.0 m | 150 UU | headroom over a walk route ≥ 2.4 m (120 UU) |
| `conveyor_gallery` | 1.2 m belt | gallery **2.4 w × 3.0 h**, walkway 0.8 one side, bents every **20 m** | 120 × 150 UU | a walkable tube; incline ≤ 12° |
| `transfer_tower` | | 6 × 6 plan, 3–4 storeys of 3.4 m, a head chute | 300 sq | stair inside, open top deck with rail |

Machinery primitives:

| part | dimensions (m) |
|---|---|
| `mill` | cylinder r 2.0, length 6.0, axis along the hall, on two 1.5 m plinths, drive box 2 × 2 × 2 at one end |
| `crusher` | 3 × 2.5 × 3 box under a 4 × 4 hopper |
| `cells` | flotation: a row of 2.5 × 2.5 × 2.0 boxes with a 0.6 launder along the front |
| `cyclone_cluster` | 4 cones r 0.4 h 2.0 on a ring frame |
| `thickener` | cylinder r 8, wall 3 high, raised 1 m, a bridge to a central drive |
| `filter` | 6 × 3 × 3 on legs over a bin |
| `pump` | 1.2 × 0.8 × 1.0 on a 0.3 plinth |
| `mcc_panel` | 3 × 0.6 × 2.2 |
| `console` | 2.4 × 0.9 × 0.8 |
| `bunk` | triple, 2.0 × 0.9 × 2.4 |
| `table` | 4.8 × 0.9 × 0.75 |

Rules for every interior:
- Clear headroom ≥ 2.4 m (120 UU) anywhere the player walks.
- Aisles ≥ 1.5 m (75 UU) round every machine (maintenance access).
- 2 exits in any room over 20 m long or holding over 50 people.
- No point more than 45 m (2250 UU, 8.5 s of walking) from an exit.

### 2.1 Processing hall (`hall_b`, flotation + filters). Proposed 48 × 20 × 14 m (2400 × 1000 × 700 UU), stepped

- **Grid:** 8 bays of 6 m along the hall, 1 span of 20 m. Gable ends: the high (uphill) end faces the silos, the low end
  faces the thickener.
- **Two floor levels on two pads, 4.8 m apart (Kennecott/Hedley: the hall steps down the hill):**
  - **Upper floor** (bays 1–3, +4.8 m over the lower floor):
    - the feed belt from the silos/transfer tower enters through the gable at roof height (+12 m, 600 UU) and drops via a
      chute to the cyclones;
    - the regrind mill sits here;
    - roller door 5 × 5 on the uphill side for mill relines.
  - **Lower floor** (bays 4–8):
    - 3 rows of flotation `cells` along the hall, stepping down: rougher row → scavenger → cleaner, about 1 m between rows;
    - aisles 1.5 m between the rows;
    - 2 `filter` units over the concentrate bin at bay 8;
    - the low gable roller door (5 × 5) for the concentrate loader;
    - personnel doors in bays 4 and 8 on the long sides (2 exits).
- **Mezzanine (operating platform):**
  - +4.8 m over the lower floor (240 UU), level with the upper floor;
  - 3.0 m deep along the long wall that faces the yard, bays 3–8;
  - a grating slab with rail; it looks down on the cell tops (players see the froth).
- **High catwalk:**
  - +9.6 m (480 UU), 1.6 m wide, along the opposite long wall at the crane-rail line;
  - it ends at an exterior door onto a platform on the gable: **the dusk frame** (see 6);
  - the overhead crane rail sits at +11 m, with one `hoist_beam` across.
- **Stairs:**
  - one main 2.0 m stair, upper floor ↔ lower floor, in bay 3 (12 + 12 risers, about 4.8 m);
  - a 1.6 m stair from the mezzanine to the high catwalk in bay 8;
  - caged ladders at the gable ends as decoration.
- **Services:**
  - the pipe rack runs inside along the mezzanine wall at +3.0 m;
  - the slurry line leaves through the low gable to the thickener;
  - the window strips at +7 m light the catwalk from the side (back-light for the director).
- **Size check:**
  - walk end to end: 48 m = 9 s;
  - longest open sightline down the aisle: 48 m, more than the LD's 41 m, so the cell rows and the mill break it (see 6).

`hall_a` (crushing + grinding, core era): keep 30 × 14 × 8 but make it **36 × 16 × 10** so that 2 mills fit.
- One floor.
- `crusher` + hopper at the high end under the feed belt.
- 2 `mill`s along the hall with a `hoist_beam` over them.
- `cyclone_cluster` on a 4 m platform; 1.6 m stair to it.
- The slurry line leaves the low end for hall_b.
- Its patched panels and its oldest sawtooth roof stay.

### 2.2 Pump house (`pump_house`). Proposed 12 × 8 × 6 m (600 × 400 × 300 UU); now 8 × 6 × 5, too small to enter

- **Shore end:** the intake channel comes in under the floor. A 4 × 3 m grated opening over the **wet well** (dark water
  2 m down) is the travelling-band screen bay.
- **Pumps:** 3 `pump`s on plinths in a row across the hall, 2 duty and 1 standby, with 1.5 m aisles.
- **Header:** ⌀0.5 at +1.5 m along the back wall, then the **rising main** out of the uphill wall to the water tower. It
  is visible outside, climbing the slope on saddles every 6 m.
- **Lifting:** a `hoist_beam` at +4.5 m along the pump row; roller door 4 × 4 in line with it, so a pump can be pulled
  out.
- **Desal stacks:** 2 rows of RO pressure-vessel racks (cylinders r 0.2, length 6, stacked 4 high) in the back third.
- **Doors and controls:** `mcc_panel` + a small window by the personnel door (1.6 × 2.8) on the dorm-road side, as the
  sheet already has it.

### 2.3 Control room

TutA's tower command room is the Authority's, and its BSP is fixed. Two options; I recommend option A.

**Option A: the plant control room on top of `hall_b`'s uphill gable (or the plant office's top floor)**
- Size: 14 × 8 × 3.6 m (700 × 400 × 180 UU), on a stair tower.
- Glazing on the side facing the plant:
  - sill at 0.6 m (30 UU);
  - glass up to 3.2 m;
  - mullions every 2 m;
  - outward-sloped glass at 15° (anti-glare, the classic control-room look).
- Raised floor 0.3 m (15 UU, one step) across the room.
- Consoles in a shallow arc, 3 m back from the glass:
  - 4 `console`s, each 2.4 m wide;
  - 3–4 screens per console (AusIMM sizing: 7 × 5 m is the minimum for one controller; this room fits 4 operators and
    visitors);
  - the screens run left-to-right in the **same order the plant appears through the glass**, so the generator sorts the
    buildings by bearing from the room (the refinery "no mirror-imaging" rule).
- Behind the consoles:
  - the mimic board/video wall on the back wall, top edge at about 2.6 m;
  - an MCC/server closet 3 × 2;
  - a kitchenette;
  - 2 exits (stair + catwalk bridge to the hall's high catwalk).

**Option B: a Liandri dispatch room in the tower** (the brief's wording)
- Use TutA's command room, which faces yaw 300 and looks about 28° down.
- Add only props: 3 `console`s along the glass, facing the plant, and a mimic board.
- Lesson from u2avalon-project: nothing may stand in front of the glass (a deck/balcony hides everything below 4°), so
  keep the console tops under the sill.

### 2.4 Dorm (`dorm`, `dorm_b`, `dorm_c`). Keep 24 × 10 × 7 (2 storeys of 3.4 m)

- **Corridor:** double-loaded along the long axis, **2.4 m wide** (120 UU). The real figure is 1.5 m; the game needs
  2 × pawn radius plus turning room.
- **Rooms:** 4.0 × 3.6 m. Per floor:
  - 4 rooms on each side, 8 rooms in all;
  - a stair bay of 4 m at the left end (`stair_flight` 1.6 wide, 2 flights + landing);
  - a wash block 4 m at the right end (showers, the drying room "that never dries").
- **Beds:** 16 rooms × 3 = 48 beds per block, which matches `dorm` (96 beds, count 2). `dorm_b` (120 beds, count 3):
  40 beds per block, so leave 2 rooms per floor as lockers/day rooms.
- **Room fit-out:**
  - 1 triple `bunk` + lockers per room;
  - a window strip at +2.2 m, as build_parts already has;
  - door 1.6 × 2.8 off the corridor.
- **Exits:** front and back personnel doors at the corridor ends. That gives 2 exits; the sheets already have
  front + back.
- **Existing annex:** the container stack on the right end becomes the external escape stair (orange), which is honest
  and readable.

### 2.5 Mess (`mess`). Proposed 24 × 12 × 5 m (1200 × 600 × 250 UU); now 16 × 9, too small for its users

**Sizing:**
- 380 people, about 250 on scrip, 3 sittings: about 90 seats.
- At about 1.2 m² a seat plus the servery, dining needs about 110 m² and the kitchen about 50 m².

**Zoning** (PKL camp-kitchen zoning: production → warewash → cold/dry store → servery → dining):
- **Dining, 16 × 12:**
  - 8 long `table`s (4.8 m, 12 seats each) in 2 rows of 4;
  - aisles 2.4 m; tables at 2.0 m centres.
- **Servery:** along the kitchen wall, a counter of 10 × 0.9.
- **Kitchen, 8 × 12, behind:**
  - production line;
  - warewash by the back door;
  - cold room 3 × 3;
  - dry store.
- **Haldane's bar:** the back corner of the dining room, 6 × 3, with its own back personnel door.

**Doors and services:**
- The 4 personnel doors stay: front, back (kitchen deliveries), left, right.
- A 2.4 m covered veranda on the front for the night shift's smoke break; it doubles as the LD's cover line.

---

## 3. E-check failures and risks in the current layouts (CPU probe, 2026-10-09)

ENGINEER score: **Cine8 0.60, Town7 0.64**. Per-check:

| check | Cine8 | Town7 |
|---|---|---|
| E1 road grades | 0.41 | 0.62 |
| E17 slope use | 0.89 | 0.93 |
| E21 buffer order | 0.43 | 0.77 |
| E14 water head | 0.48 | 0.20 |
| E12 conveyor incline | 1.00 | 1.00 |
| E16 fuel set-back | 0.37 | 0.29 |

### Failures in the town

1. **The ore runs UPHILL into the halls (Cine8), and no gravity at all (Town7).**
   - Cine8: wellhead_a → silos falls 11.2 m (good), but silos → hall_a rises **+8.2 m** and silos → hall_b rises
     **+8.4 m**. The silos sit 5 m over the sea, the halls 13.5 m.
   - Town7: everything sits on one terrace at +15.5 m.
   - E12 says "3 of 3 OK" because it tests only `abs(incline) ≤ 15°`, from end to end.
2. **Halls bypass the silos.** In Town7 hall_a and hall_b take ore straight from wellhead_a (226 m and 154 m). Two
   causes:
   - systems.py picks the *nearest* ore provider, with no process order;
   - a conveyor counts as OK at any distance up to 900 m (`ok = ok or d <= 900`), which silently overrides its 220 m
     reach.
3. **E14 water head: the reservoir stands on the shore.** In Cine8 water_tanks sit at +4.5 m and water_tower at +5.1 m,
   the lowest ground in the works, while the houses they serve stand at 9–16 m. Head: 13 m (Cine8) and 6 m (Town7)
   against the 28 m wanted. The pump house stands 6.6 m *above* its tanks: the flow is backwards.
4. **E16 fuel.**
   - Town7: fuel_depot is 29 m from tin_bar; the generator is 30 m from old_camp.
   - Cine8: tank_farm is 37 m from shanty_c.
   - Two measurement problems:
     - E16 counts `tin_bar` and `memorial` as homes, because both have kind `house`, and it misses the shanty.
     - It treats `tank_farm` as fuel because systems.py has it providing fuel. Once it is concentrate slurry, only
       fuel_depot is a fire set-back case.
   - No bund is modelled.
5. **E1 measures the wrong ground.** It measures grades on the *natural* heightmap: 59 % / 38 % of road length over the
   cap. On the cut-and-filled ground (`isl_ec.bmp`) the figure is 11 % in both runs, with a max of 35 % (Cine8) and 30 %
   (Town7). Two more problems:
   - The caps disagree: codirect uses 10 % for spine/branch, terrain_cutfill grades to `MAX_GRADE 0.12`.
   - Residual pitches of 30–35 % remain on the graded ground: walkable, but no truck climbs them.
6. **E21:** company housing is upwind of the works in only 43 % of pairs (Cine8).
7. **E17:** Cine8 puts beacon, company_store, shanty_b, company_mast and directors_house on ground that is too steep.
   For masts, E17 already allows 17°, so these are real misses.
8. **Quay height (Town7).** The ground under the dock's centre is +15.5 m over the sea: the quay deck sits on the plateau
   terrace, 15 m above the water. A real quay deck is 2–4 m over high water. Cine8: +1.0 m, fine.
9. **Systems:**
   - `new_rig needs supply` fails in both runs (990 m and 1026 m against a 500 m road reach). A rig is supplied **by
     boat**, so this is the wrong carrier, not a layout fault.
   - `hall_a needs cooling` fails in Town7 (226 m).
   - `tank_farm needs fuel` fails in Cine8 (261 m). This one is a modelling error.
10. **Cooling towers next to the wrong consumer.** They cool hall_a in the model. In Town7 they actually stand 18 m from
    the generator, which is the real consumer and good by accident.

### Risks in the parts (build_parts)

- Interiors are solid, and doors are painted on, so no building can be entered.
- The personnel door is 1.3 m (65 UU) wide: tight against the 64 UU minimum once the frame and collision round it.
- `CONVEYOR_M = 60` uses the cableway's tower spacing for every ore run. A belt gallery needs bents every 20 m; keep 60 m
  only for overland aerial ropeways (B_cable).
- The pad sits at the height sampled at the building's centre, so a 48 m stepped hall needs 2 pads. terrain_cutfill
  makes one disc per building.

## 4. New checks to add (codirect ENGINEER / engcheck.py)

| id | check | pass | source |
|---|---|---|---|
| E1' | road grade on the **graded** ground (`isl_ec.bmp`): no 50 m window over the class cap, no 100 m over the short-pitch cap; codirect and cutfill share one cap table (spine/branch 10 %, lane 15 %, haul 8 % target) | ≥ 90 % | report §9 E1 |
| E12' | conveyor **direction + stage order**: z(mine) > z(silo) > z(hall_a) ≥ z(hall_b) > z(conc_shed); belts ≤ 12° (15° hard); a transfer tower at every bend; no hall fed by anything but a silo/bin | each pair | report §5 |
| E14' | water: the service reservoir on the highest cell within 300 m; base ≥ highest served floor + 20 m; the pump house **below** it, with the rising main routed | ≥ 20 m | §6 |
| E16' | fuel: only `fuel_depot` (and any `kind: fuel`); homes = kind dorm/house **minus** social/altar functions **plus** shanty*/old_camp; ≥ 100 m and not upwind; bund volume ≥ max(110 % largest, 25 % total) → bund wall height | 100 m, bund | §6 |
| E22 | **process chain complete**: each ore/conc stage has exactly its upstream and downstream within reach, in order; any stage missing = VETO (the plant doesn't work) | all stages | new |
| E23 | **quay deck** 1.5–4 m over the sea; berth on the 8–12 m depth contour or a trestle jetty out to it | both | §4 E10 |
| E24 | **intake vs outfall**: sewage/tailings outfall ≥ 150 m from the intake, downwind/down-current | ≥ 150 m | §6 |
| E25 | **rig supply by sea**: carrier `boat` from dock/boat_landing, reach 3000 m | met | new |
| E26 | **clearances over routes**: pipe racks/galleries over a road ≥ 5 m (250 UU); over a footpath ≥ 2.4 m (120 UU) | all | new |
| E27 | **interior egress** (per interior JSON): 2 exits when > 20 m long or > 50 users; travel to an exit ≤ 45 m; every floor reached by a stair (risers ≤ 16 UU, treads ≥ 25 UU) | all | LD report |
| E28 | **rails**: every walkable edge with a drop > 1 m (50 UU) has a rail 55 UU high (Q9's railing, automated) | all | OSHA 1910.29 |
| E29 | **maintenance access**: 1.5 m aisle round every machine; a hoist beam or a roller door in line with every mill/pump | all | new |
| E30 | **heavy on cut**: halls, silos, thickener, tanks with ≥ 60 % of the footprint on cut, not fill | ≥ 60 % | §7 E18 |

Also fix E16's home list and drop `tank_farm` from fuel at once. Both are small changes in codirect.py/systems.py, and
they move the score without moving a building.

## 5. Keep, cut, add

**Keep**
- The spine and the straight ore line as the parti datum.
- `silos`, but move them to the top of the plant terrace.
- `cooling_towers` stay the hero, beside the generator.
- `tank_farm` (re-roled as concentrate slurry).
- The intake + pump_house pair at the shore.
- generator_house ↔ fuel_depot close together (Cine8 30 m: good).
- `hall_c` as the dead hall.
- Rigs offshore.
- B_ctower/B_cable for the overland run only.
- Graded roads and pads.

**Cut / merge**
- Wellheads standing on land at the tower's level (Cine8 wellhead_a and wellhead_b sit at the tower's +16.4 m): ore
  comes from the mine portal on land and from the rigs at sea.
- `tank_farm`'s fuel role.
- `pump_station` as a "booster between the generator and the shore": a 200–400 m line needs no booster. Re-role it as
  the slurry pipeline's terminal pump at the dock.
- The 900 m conveyor override.

**Add**
- `mine_portal` + headframe + `crusher_house` at MINE.
- `transfer_tower`(s).
- `thickener`.
- `conc_shed` + `shiploader` on the quay.
- `tailings_outfall` (deep-sea, down-current) or a tailings pond in a valley away from town.
- `substation`.
- `sewage_works`.
- A fuel bund wall.
- `plant_fence` with `dock_gate` and `company_gate`.
- The control room (2.3).
- Interiors for hall_b, hall_a, pump_house, dorm, mess.
- The hollow-shell kit (2.0).
- In terrain_cutfill, **2-pad stepped buildings** (`pads: 2 step=4.8` on a sheet).

## 6. Notes for the other roles

- **DIRECTOR**
  - hall_b's **high catwalk at +9.6 m** ends at a gable platform facing the sea. A dark frame (the door), grated floor,
    rail, a lone figure 40–100 m off on the transfer tower deck, dusk rain. That is parti beat 4 ("catwalk") and the
    user's peak frame (Shot00050). Put it where the sun is 90–180° off the view.
  - The overland belt gallery is the leading line into the hero: the cooling towers stand at the generator, at its end.
  - The control room's sloped glass is a second window frame, onto the plant rather than the tower's view.
- **LEVEL DESIGNER**
  - High spots: the transfer tower top deck (+10–14 m) and the hall_b mezzanine (+4.8 m) over the cell floor.
  - Cover:
    - flotation cells, 2 m high: waist/chest cover in rows, which breaks the hall's 48 m aisle sightline;
    - mills, 4 m: full cover;
    - the thickener rim: a ring arena 16 m across, raised 1 m.
  - The belt gallery is a 2.4 m wide tube route, a flank between hall_a and hall_b.
  - Each hall has 2+ exits, so it plays as a junction arena with ≥ 2 entries.
  - Stair numbers: risers 14.2 UU, treads 28 UU, so nothing falls in the 25–70 UU "almost climbable" band.
- **WRITER**
  - Okafor/plant_staff work the control room; the consoles face the plant, never the tower: the company doesn't look up.
  - The tailings outfall smells where the shanty is downwind.
  - The rising main from Arashiro's pump house climbs past the company houses to the water tower: water flows uphill to
    the company.
  - The dead hall was the old mill; hall_a carries on its job.
- **ARTIST**
  - Safety orange for every rail, stair stringer and hoist beam, the one accent on charcoal/steel. It matches the
    user's "blue with an orange band" idea.
  - Grating reads as a dark lattice with light under it.
  - Machinery in steel/charcoal, launders and the thickener rim in rust, the concentrate bin black.
  - Interiors take the same palette stripes (Pal.tga); no new textures are needed for the first pass.

## 7. Web references (inform the design, never ship; nothing downloaded)

Some facts below came from search-result summaries rather than a full read of the page, and are marked *(summary)*.
Licences are given only where the page states one; otherwise "not stated", and the images are not to be reused.

| # | page | source | licence | what fits | for |
|---|---|---|---|---|---|
| 1 | https://home.nps.gov/wrst/learn/historyculture/kennecott-mines-national-historic-landmark.htm | US National Park Service, Kennecott Mines NHL | US Government work (NPS text usually public domain; check each photo's credit) | the 14-storey braced-timber concentration mill climbing the mountainside under the aerial tramway terminal; mill + leaching plant side by side; tramways 6 mi *(summary)* | hall_a/hall_b stepped on 2 pads; the transfer-tower-at-the-top idea |
| 2 | https://www.loc.gov/item/ak0476 | Library of Congress, HAER AK-1-D (Kennecott concentration mill, measured drawings) | HAER records are usually "no known restrictions" (check the record) | measured drawings of a real gravity mill: floor levels, chutes, tramway terminal; first built in 1908 as the Bonanza tramway's lower terminal *(summary)* | hall_b section (floor heights, mezzanine, chute at roof height) |
| 3 | https://livingsignificantly.ca/?p=1056 | "Early Hedley Townsite and Stamp Mill" (local history site) | not stated | a mill "constructed to allow the ore to travel through the plant by gravity"; a gravity tramway 10–66.8 % grade; mine high, mill on the slope, town low *(summary)* | the whole chain's z-order (E12'); mine_portal → crusher → mill |
| 4 | https://www.zollverein.de/app/uploads/2018/02/UNESCO-Welterbe-Zollverein-Imagebroschüre-englisch.pdf | Stiftung Zollverein (UNESCO site brochure) | not stated (©) | strict right-angle axes; conveyor bridges linking washery and coking plant; washery about 90 × 30 × 40 m; the coal path runs from the top down *(summary)* | conveyor_gallery + transfer_tower; the ore line as the orthogonal datum |
| 5 | https://www.spitsbergen-svalbard.com/photos-panoramas-videos-and-webcams/spitsbergen-panoramas/longyearbyen/coal-cableway-centre-taubanesentrale.html | spitsbergen-svalbard.com (Rolf Stange) | not stated | the 1956/57 cableway hub where mine lines met before the harbour; its towers run down the valley (already on the user's real-place board) *(summary)* | transfer_tower / B_ctower angle station; the overland run's look |
| 6 | https://cruisehandboka.npolar.no/en/isfjorden/pyramiden.html | Norwegian Polar Institute, cruise handbook | not stated | a company town with mine entrances in the mountain above, a processing plant and a coal pier below, living quarters, mess and sauna; peak population over 1000 *(summary)* | dorm, mess, conc_shed/quay relation; the vertical zoning mine → plant → pier |
| 7 | https://cabinetmagazine.org/issues/7/burke-gaffney.php | Cabinet magazine, Burke-Gaffney on Hashima | not stated (©) | company blocks: a 1916 six-storey courtyard block of 9.9 m² single rooms with shared baths and kitchens; housing on the west side, the mine on the east *(summary)* | dorm room module; housing on one side, works on the other (E21) |
| 8 | https://www.ezview.wa.gov/pr/Portals/_1357/images/default/20110428%20GPT%20Terminal%20Operations%20for%20MAPT%20Final(1).pdf | Washington State (Gateway Pacific Terminal operations) | state public record (not stated) | photos with captions: a transfer tower that lifts to the top and drops onto the next belt; enclosed galleries onto an access trestle; a shiploader with gallery and boom *(summary)* | shiploader + conc_shed on the quay; gallery on trestle out to the berth (E23) |
| 9 | https://www.ausimm.com/bulletin/bulletin-articles/mine-monitoring-and-control-designing-a-control-room/ | AusIMM Bulletin | not stated | a worked size: 3–4 screens per console, about 7 × 5 m minimum for one controller, a raised floor for cables *(summary)* | control room (2.3) |
| 10 | https://new.abb.com/control-rooms/references/central-control-rooms-for-mining-and-mining-and-bulk-material-handling | ABB, central control rooms for mining | not stated (©) | a central room collecting thousands of process variables from km away; consoles + video wall *(summary)*; together with refinery practice, consoles face the process, which flows left to right | control room console order (bearing-sorted) |
| 11 | https://www.hunterwater.com.au/documents/assets/src/uploads/documents/Belmont-Desalination/Environmental-assessments/Report-5-BDRDP-D-Project-Description.PDF | Hunter Water, Belmont desalination project description | not stated | onshore pump station: a concrete wet well 9–11 m ⌀ up to 20 m deep, with screening + pump housing; an 800 m² building; a 1000 m intake pipeline *(summary)* | pump_house + intake (wet well, screens, pump row) |
| 12 | https://www.911metallurgist.com/flotation-plant-design | 911 Metallurgist | not stated (©) | the flowsheet: closed-circuit crushing → fine ore bin → grind → rougher/cleaner cells → thickener → filters "directly above concentrate storage bins" *(summary)* | hall_a/hall_b machinery order; thickener; filter over the bin |
| 13 | https://www.pkl.co.uk/products/transworld-kitchens/kitchens-and-camps/tw-400-dining/ | PKL (remote-site camp kitchens, vendor) | not stated (©) | zoning: production, warewash, dry/cold store, servery → dining; the TW 600 seats 212 *(summary)* | mess (2.5) |
| 14 | https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.25 and https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.29 | US OSHA | US Government work (public domain) | stairs: riser ≤ 9.5 in, tread ≥ 9.5 in, width ≥ 22 in; guardrail top 42 ± 3 in, mid-rail halfway *(summary)* | stair_flight, rail, catwalk (scaled up for the game in 2.0) |

---

## Method and limits

- **Probe:** a scratchpad script (`eng_probe.py`, not in the repo). For each building it read the ground under the
  building's centre on `isl_ec.bmp`, and it computed the conveyor rise/fall end to end, road grades on both heightmaps,
  and the distances above.
- **Not run:** no layouts were regenerated; that needs town.py with GPU steps.
- **Unverified:**
  - U2 pawn collision size, MaxStepHeight, and LadderVolume support: read them before building interiors.
  - The Kennecott gravity-flow detail is common knowledge, but the NPS page didn't state it.
  - Antamina's concentrate pipeline is from memory, not fetched.
