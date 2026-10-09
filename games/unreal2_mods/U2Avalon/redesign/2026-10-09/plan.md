# Avalon redesign, 2026-10-09: the combined plan

This merges the five role files in this folder: [writer.md](writer.md), [director.md](director.md),
[engineer.md](engineer.md), [level_designer.md](level_designer.md) and [artist.md](artist.md). It was written during
the playtest swap (PIPELINE.md "Playtest swap"): nothing was generated, rendered, launched or downloaded. The web
references are merged in [references.md](references.md). For details, read the role file section named in each item.

Units: 1 m = 50 UU. The player walks 263 UU/s (5.3 m/s).

---

## 1. Decisions for the user

Each one needs a yes/no or a pick before the work it blocks can start. **Rec.** = the team's recommendation.

**D1. The hero: the Liandri stepped temple on the summit.**
- (a) Keep `hero: tower`, the Authority tower (as in parti.json now).
- (b) `hero: liandri_tower`, a new sheet: the round-2 CraneTower on a 30 m battered plinth on the Q74 summit. The
  Authority tower stays the player's home, rewritten as "the oldest building on the island, and the poorest".
- (c) As (b), but the command-room window keeps the cooling towers as its hero (F1), and the temple is the hero of
  the walk, the company gate and the decks.
- **Rec.: (b), falling back to (c).** The writer and the artist both want (b) (writer s.1, artist s.1.1 and s.9). The
  director and the engineer keep the cooling towers as the window hero. A CPU check with compose.py settles it: is the
  summit inside the window cone (yaw 300 +-34) and does the temple's top cross the skyline? If not, use (c).
  compose.py and the A-401 walk then need a hero id per frame.

**D2. Hawkins as the lone figure on the catwalk (the peak frame, beat 4).**
- (a) Hawkins at the rail at 1930 (writer s.5.5: a new catwalk stop in his routine, plus a cigarette tin prop).
- (b) A nameless garrison marine on a smoking break (director F5).
- **Rec.: (a), with (b) as the fallback** if the engine cannot pose her there. The frame works with any lone figure.
  Hawkins is **male** (user 2026-10-08: remade characters keep the stock gender for voice reuse); "Ruth" is dropped,
  new lines are spliced from the stock Commander voice. writer.md / tutorial_fold.md pronouns fixed.

**D3. The shanty's population: about 470 against the company's official 380.**
- (a) Keep 380 and thin the shanty to match it.
- (b) Raise Tin Row: families 24 -> 60, traders 26 -> 40, plus a new `ship_row` group of 40. About 470 people, about
  140 of them "officially not here". The PA keeps saying 380 (new line pa13).
- **Rec.: (b)** (writer s.4.1). It matches the shanty you asked for in Q74. Side effects: the artist checks that the
  shanty's figure-ground stays compact, and the fuel depot must stay 100 m off the larger Tin Row (E16). The mess
  stays sized for the 380 (engineer s.2.5), because Tin Row does not eat in the company mess.

**D4. Can the player enter Liandri House (the temple)?**
- (a) Shown, not given: the player sees the empty, top-lit scrip exchange hall through a glass door at the gate.
- (b) Enterable as a new interior.
- **Rec.: (a)** (writer s.3.11; the level designer has no fight planned there). It costs one glass door and one room
  seen from outside. It is the counterpart of the command room: the company's room is bright and empty.

**D5. The palette: 8 or 12 stripes.**
- (a) 12 stripes: add `slate` (the Authority), `cyan` (cold light, emissive), `hazard` (yellow) and `soot` (stains
  only).
- (b) Keep 8 and swap `steel` for `slate`.
- **Rec.: (a)** (artist s.2.2). Cost: Pal.tga, palette.json, glb_to_ase.py and part_to_ase.py change. Do NOT re-run
  glb_to_ase over the existing B_*.glb (the stripe order changes). (b) is the cheap fallback: the Authority gets its
  colour and the other three jobs wait.

**D6. Where the beats are walked: TutA's tower only, or a generated map that starts at the dock.**
- In TutA the player can only walk the tower's decks, so the dock-to-tower walk is never played (director s.0.3).
- (a) TutA only: put the four beats on the tower's own route: corridor (dread), overhang deck (exposure), stair past
  the base (smallness), catwalk (melancholy) (director's beat map).
- (b) Generated maps (TutA_Cine8 and later) put the PlayerStart at the dock, and the full critical route of section 5
  is played there.
- **Rec.: both.** (a) costs only lights and props in the existing BSP. (b) is the real redesign (level designer s.1).
  TutA's opening (command room, then the lift) stays as the bookend: the player sees the town from the window first
  and walks it afterwards.

**D7. What waits at the end of the drain.**
- (a) The writer's version: the outlaws' road; Rook's lamp is on, goes off; Rook's people fight at the junction.
- (b) The level designer's version: an Unreal-1 reveal, one agile Skaarj in the sluice gallery.
- (c) Both: the lamp that should not be on is Rook's, at his crates; his man lies dead beside it; then the lamps die
  and the Skaarj appears. Rook's people are fought earlier, at the dock (E1).
- **Rec.: (c).** It keeps the writer's story props and the level designer's reveal recipe.

**D8. Company security at the dorm square (E2): enemies or not?** The level designer's layout has them as enemy
mercs behind a barricade facing the drain. **Rec.:** keep them hostile (contractors who shoot anyone in the
quarantine), and have the writer give the barricade its reason: they were holding off whatever came out of the drain.

**D9. The engineer's process chain** (engineer s.1): about 10 new sheets (`mine_portal`, `crusher_house`,
`transfer_tower`, `thickener`, `conc_shed`, `shiploader`, `substation`, `sewage_works`, `tailings_outfall`,
`plant_fence` with `dock_gate`/`company_gate`) and new roles (hall_a crushing and grinding, hall_b flotation and
filters, tank_farm concentrate slurry, pump_station the slurry pump, cooling towers serving the generator).
**Rec.: yes.** The model fixes (tank_farm not fuel, rigs supplied by boat) go ahead now as bug fixes; the new sheets
wait for your yes.

**D10. A plant control room.** (A) a new room on hall_b's uphill gable, consoles facing the plant; (B) Liandri props in
TutA's command room. **Rec.: (A).** (B) would turn the Authority's room into the company's, which breaks the writer's
"busy out there, nothing in here" (writer s.3.1, engineer s.2.3).

**D11. Binder folds** (writer s.4.3): the second director's villa becomes `guest_house` (the inspector who never
comes); the Q12 "Liandri business venue" folds into the temple's terrace; new citizens: the medic Ilunga, the
teacher Marau, the scrip clerks. **Rec.: yes.**

---

## 2. Where the roles agree (goes ahead without a decision)

1. **The parti sentence and the four beats stay** as approved (all five).
2. **Protect the peak frame and the command room.** The catwalk is a dark frame, a grated catwalk with lit ground
   under it, one figure at 40-100 m, dusk rain. No combat on the catwalk or in the command room (all five).
3. **One unique landmark.** Cut the far copies of the crane tower (Q11) and the "fishing-pole" cranes. At most one far
   echo, plain (no stepped base, no red domes), under 1/3 of the hero's on-screen height (writer, director, artist).
4. **A drain under the town is the LD7 quiet stretch and ends in a staged reveal** in the Unreal-1 first-Skaarj style
   (all five name it, in different forms; section 3.2 merges them).
5. **"Too dark" is a legibility problem, not a brightness one.** The frame may be black; the path may not
   (director's value ladder; writer, artist and level designer agree).
6. **Grading flattens the play.** Score on the graded heightmap and place cover as clutter after grading (level
   designer s.0, engineer E1).
7. **Interiors become real.** Hollow shells instead of solid boxes, and doors as real openings (engineer s.2.0, level
   designer s.3, artist s.4, writer s.3, director s.2).
8. **The company gate is a battered wall with one stair cut into it**, plus a side switchback for trucks (all five).
9. **The mess is the one warm social room and a rest stop, not an arena** (all five).
10. **The shanty is the company kit turned into homes by additions**: no orange rims, one patch panel per hut, cables,
    laundry, panels hung upside down (writer s.3.8, artist s.3.3).
11. **Rails on every walkable edge with a drop over 1 m** (Q9), 1.1 m top rail and 0.55 m mid-rail (engineer, artist).
12. **One red aviation lamp on the tallest structure is the frame's single loud accent**; frame darks are authored at
    about 10 % value, never 0, because UE2 vertex light crushes them (director, artist).
13. **The command room's light**: the window is the key; screens and lamps stay below it in value (director I1, writer
    s.3.1, artist s.4.1).
14. **The dead hall (hall_c) stays dead**: eleven lockers, missing roof teeth, rain falling in (writer, engineer,
    artist).

---

## 3. Where the roles conflict, and the proposed resolution

### 3.1 The route's length against the engineer's process chain
- **Level designer:** the spine is only 47 s long, so the route detours through the works: hall_a as a 4200 UU
  assembly-line fight (I2), then the dorm square, the drain and the cooling basin. That gives about 140 s of walking and a
  9-12 minute slice. The generator_house and the fuel drums sit at the company gate (E4).
- **Engineer:** the plant must fall downhill in process order (mine > silos > hall_a >= hall_b > conc_shed at the
  dock). hall_a is 36 x 16 x 10 m (1800 UU long), hall_b is 48 x 20 x 14 m. The cooling towers stand beside the
  generator; the generator and the fuel depot stand by the berth, at least 100 m from homes.
- **Resolution:**
  - make E22 (the process chain) a veto and the route's 120-160 s of walking an LD target, both scored on the same
    layout;
  - I2 becomes **the production line, walked downhill**: hall_a -> the belt gallery -> hall_b, about 5000 UU. This
    keeps the level designer's Titanfall "follow the line" idea and its three floors (0 / +256 / +512 UU fit
    hall_b's 0 / +4.8 m / +9.6 m levels). The gallery must be widened to a walked size (section 4);
  - the drain is the plant terraces' storm drain, so it runs downhill from the works to the cooling basin. That fits
    gravity and the chain;
  - E3, the cooling basin, sits with the cooling towers beside the generator. Remove the generator_house and the fuel
    drums from E4; the engineer's new `substation` stands at the gate instead.

### 3.2 The drain (four versions)
| role | what it is | size | ends in |
|---|---|---|---|
| writer | the outfall culvert, works -> under the spine -> sea; the outlaws' road (Rook, Haldane's weep, Arashiro's jars) | ~6 m vault; 130-320 m long | a junction into the dead hall; Rook's lamp |
| level designer | a storm culvert under the plant fence -> sluice gallery -> cooling basin | 384 x 320 UU culvert, 3600 UU long; gallery 1536 x 768 x 448 UU | the Skaarj reveal, then E3 |
| artist | a culvert network under the terraces -> a small G-Cans pillared hall -> sea outfall | B_culvert 4 x 3 m; pillars 2 x 4 m on a 12 m grid, 10-14 m high | the reveal among the pillars |
| director | one culvert where a gully crosses the spine | 4-5 m across, 40-60 m long | a bright mouth with a silhouette in it |
| engineer | no culvert spec in engineer.md; `drainage.py` does not exist yet | - | - |

**Resolution:** one drain, three parts.
1. **The culvert** (the quiet stretch): the level designer's section, 384 x 320 UU (7.7 x 6.4 m) with a 128 UU dry
   ledge and about 3600 UU of length (35-50 s of creeping). It carries the writer's props: Haldane's bucket at the weep,
   Arashiro's jars, Rook's crates, wet footprints, the r10 radio line. The water is a decal plus sound, never a
   WaterVolume.
2. **The sluice gallery** (the reveal): the level designer's 1536 x 768 x 448 UU room, dressed as the artist's
   pillared hall. The 2 x 4 m pillars stand in the side alcoves, which gives the half cover the Skaarj fight needs.
   The director's frame: the silhouette against the red beacon in the gate mouth.
3. **The outfall spur** (off the critical route): the writer's smugglers' road to the sea and the boat landing,
   behind a locked grate; it is Rook's way in.

The engineer owns the routing (`drainage.py`, new) and the grades. The artist's 4 x 3 m `B_culvert` is too low for a
Skaarj (192 UU needed), so use it only on unwalked runs. Writer's `drain` sheet: set `lit` to match the lamps the
reveal turns off, and give it a culvert size instead of `6 6 6`.

### 3.3 Light and darkness
| question | positions | resolution |
|---|---|---|
| The peak catwalk's lamps | artist: a sodium lamp on every second bent, an aviation lamp at the far end. Director F5: nothing brighter than the horizon band; add nothing | On the TutA peak catwalk, no new lamps in frame. The artist's catwalk rule applies to every other catwalk (hall_b, the terraces) |
| The deck under the overhang (Shot00065, Q47) | director: one lamp pool on the floor 6-8 m out, slab unlit. Artist: the rail must catch the sky as the brightest thin line. Writer: the overhang is dark, the horizon bright | Do all three: they don't clash. Fix the Q57 bright gap texture first |
| The mess | writer and director: the warmest room, warm pools on the tables. Artist: cold fluorescent tubes over the tables plus the bar's warm bulb | Warm pools over the tables dominate (so F9's window reads warm from the street); one cold, flickering tube over the servery keeps the artist's company-vs-people split |
| Command-room screens | artist: cyan screens as fill. Director: dim the screens facing the window, a screen brighter than the town steals the key (Shot00092) | Screens on, cyan, below 50 on the value ladder; the ones facing the glass dimmed. Desk lamp off; one dead tube |
| The drain | writer: `lit: no`. Artist: caged bulbs, one in three dead, shafts from street grates. Level designer and director: lamps that die on a script | The drain has lamps (the path must read), and the gallery's six lamps die from the far end. The binder sheet says `lit: yes` |
| "Too dark" generally | the director's value ladder; the artist's "every light has a fixture you can see" | Both rules, and the fork's GI world cache as the honest fill. Pawn AmbientGlow 30 until Q71 lands |

### 3.4 Smaller conflicts
- **The window's sun score.** The director shows it is inverted (section 4, B1). The engineer's note to "put the
  hall_b gable frame where the sun is 90-180 deg off the view" repeats the old rule. Use the director's bands
  (0-60 back light, 60-120 side, 120-180 front).
- **Beat 4's location.** The engineer offers hall_b's gable platform as the "catwalk" beat. **Keep beat 4 on the tower
  catwalk**; the hall_b gable is a second dusk frame without a figure.
- **Door and corridor sizes.** The engineer's doors are 1.6 x 2.8 m (80 x 140 UU) and the dorm corridor is 2.4 m (120 UU).
  The level designer wants doors of 128-192 x 192-256 UU, corridors >= 256 UU and Skaarj routes >= 128 x 192 UU.
  **Two classes:** the engineer's sizes inside non-combat rooms (dorms, mess, offices); the level designer's sizes on
  every combat or AI route (section 4).
- **Catwalk width.** Engineer 1.6 m, artist 1.2 m; level designer: AI nodes only where it is >= 128 UU (2.56 m). Use
  1.6 m for player-only catwalks, 2.6 m wherever AI walks.
- **Stair risers.** Engineer 0.283 m risers and 0.56 m treads (14.2 / 28 UU); artist 0.19 / 0.28 m (9.5 / 14 UU);
  level designer risers <= 24 UU. The artist's 14 UU tread fails E27's tread >= 25 UU. Use the engineer's flight
  everywhere, the artist's cheek walls and nosings on the cut-in stair.
- **Rail colour.** Engineer: safety orange on rails, stringers and hoist beams. Artist: orange only for company doors
  and the usable path; hazard yellow for edges, hooks and moving machines. **Use the artist's grammar**, because the
  level designer relies on it as a gameplay channel. Rails are charcoal with hazard-yellow toe boards.
- **Where the checkpoint is.** In Cine8 it is on the dorm square (E2); the writer puts it on the route after the
  company gate, where the company cable crosses the Authority road. Keep the layout's position for E2 and have the
  engineer route the tower's single power cable past it.
- **The company gate and two towers.** With D1 (b), the gate is the foot of the temple's plinth (writer); the level
  designer's E4 leads to the Authority tower's base. The layout must put the gate terraces between the spine and both
  towers. The engineer and the level designer place it on the next layout run.
- **The lift lobby.** The writer wants the climb quiet ("going up, alone"); the level designer has a hold fight in the
  lobby. Both: the fight is in the lobby while the lift comes, and the ride is alone.

---

## 4. Bugs found in our tools

| # | where | bug | fix |
|---|---|---|---|
| B1 | codirect.py:344-346 | The sun score is backwards. `off = abs(SUN_AZ - LOOK)` = 164 deg is scored 1.0 as "back/side light", but az 136 is where the sun is, so from the window (yaw 300) it is behind the viewer: front light | Score back light at 0-60 deg, side light at 60-120 and front light at 120-180, and score per view: the window by "housing in shadow, hero lit", the decks and catwalk by back light. Don't move the sun (director s.0.1) |
| B2 | compose.py:28 | `PITCH = -28` with a 26 deg half height frames -54..-2 deg, so the horizon and sky are never in the frame | PITCH -9, horizon on the upper third; set the command-room PlayerStart's pitch to about -9 too |
| B3 | codirect.py:341 | The background layer is given away free ("the sea horizon is always there"), which hides B2 | Score the horizon's actual position in the frame |
| B4 | town.py:85 | The reviews read `_e.bmp`, the natural ground; the graded `_ec.bmp` is what ships. LEVEL falls 0.93 -> 0.69 after grading | Review on `_ec.bmp`; re-place cover as clutter after cut/fill; keep >= 64 UU relief in arena footprints |
| B5 | codirect.py:385 vs terrain_cutfill.py:167 | E1 caps spine/branch at 10 %, cut/fill grades to `MAX_GRADE 0.12` | One shared cap table (spine/branch 10 %, lane 15 %, haul 8 %) imported by both; add a short-pitch cap for 30-35 % residual pitches |
| B6 | systems.py:177-216 | No process order: each need takes the nearest provider, so halls take ore straight from a wellhead and skip the silos | A stage order for ore and the new `conc` resource; check E22 (the chain is complete and in order) |
| B7 | systems.py:201 | `ok = ok or d <= 900` silently overrides a conveyor's 220 m reach | Delete the line; long runs become ropeways (B_cable) or get transfer towers |
| B8 | codirect.py:436-437 | E16's fuel list includes tank_farm; its homes are kind house/dorm, so tin_bar and memorial count as homes and the shanty is missed | Fuel = fuel_depot and `kind: fuel` only; homes = house/dorm minus social and altar functions, plus shanty* and old_camp; add the bund (E16') |
| B9 | systems.py / binder | tank_farm "needs/provides fuel" (a modelling error); new_rig's supply goes by road (990-1026 m against a 500 m reach); cooling serves hall_a, not the generator | tank_farm = concentrate slurry; rig supply by `boat`, reach 3000 m (E25); cooling serves the generator |
| B10 | layout_spine.py:811-824 | Decline abandonment can pick a building with named residents (staff_houses in Town7, plant_staff homeless) | Skip any building that is a citizen's `lives:` |
| B11 | layout_spine.py:693-716 | **The duplicate branch**: `add_branch()` appends to `SPINE.taken` but never reads it, so a second failed placement picks the same roomiest spine point and emits the same straight 140 m (7000 UU) branch again; this is the (3293,-7084)->(-1657,-12033) pair | Skip spine positions inside `SPINE.taken[side]` in the search (or reuse an existing branch) |
| B12 | codirect E12 | Tests only `abs(incline) <= 15 deg` end to end, so ore running uphill into the halls passes "3 of 3 OK" | E12': direction and stage order, belts <= 12 deg, a transfer tower at every bend |
| B13 | codirect E1 | Reads the natural heightmap (same root as B4) | E1' on the graded ground |
| B14 | build_parts.py:247, :178, :114 | Every walled building is a solid charcoal box; `stair()` is a solid block; doors are painted panels 1.3 m (65 UU) wide | Hollow mode and the kit in section 5 |
| B15 | build_parts.py `CONVEYOR_M = 60` | The ropeway's tower spacing is used for belt galleries too | Per carrier: belt bents every 20 m, ropeway towers every 60 m |
| B16 | terrain_cutfill.py | One pad disc per building at its centre height; a 48 m stepped hall needs two | `pads: 2 step=4.8` on a sheet |
| B17 | layout (Cine8 / Town7) | Water head is backwards (reservoir on the shore, pump house above its tanks); Town7's quay deck is 15 m over the sea; ore runs uphill into the halls | Fixed by the new checks E14', E23, E12' and a re-roll, not by hand |
| B18 | role files | director.md F2 calls Hawkins "he"; the artist's B_stair tread (14 UU) fails E27; the artist's B_culvert (150 UU high) is under the Skaarj's 192; writer.md says "about 500" in s.0 and "about 470" in s.4.1 | Corrected in this plan; the role files stay as written |
| B19 | layout_spine.py:812 | `if PASSES >= 3 and PASSES >= 1` (harmless, redundant) | `if PASSES >= 3` |

New checks to add with the fixes: E1', E12', E14', E16', E22-E30 (engineer s.4); LD8 interior rooms and LD9 the
reveal recipe (level designer s.6); "hero unique" (no other building >= 2/3 of the hero's on-screen height) (director);
the artist's grain score (median footprint ratio >= 2x between neighbouring districts) and IMP per district (artist s.7).

---

## 5. The interior kit (new build_parts parts)

Origin at the bottom centre, front = -Y, as the kit does now. "Combat" = on a fight or AI route.

| part | size (m) | UU | from | notes |
|---|---|---|---|---|
| `shell(hollow=1)` | walls 0.3, columns 0.4 sq at 6 m bays, floor slab 0.3 | 15 / 20 / 300 / 15 | E | no inner box; roof on the columns; window strips stay |
| `door_personnel` | 1.6 x 2.8 | 80 x 140 | E | non-combat rooms only |
| `door_main` | 2.6 x 3.9 | 130 x 195 | LD | combat rooms and Skaarj routes (>= 128 x 192); main doors about 2x the side doors |
| `door_roller` | 5 x 5 (halls); 4 x 4 (sheds, pumps) | 250 / 200 | E | a real opening; the I2 entry may go to 384 UU wide |
| `stair_flight` | riser 0.283, tread 0.56, width 1.6 (main 2.0); 12 risers per 3.4 m storey; run 6.2 | 14.2 / 28 / 80 (100); run 308 | E | about 27 deg; no 25-70 UU "almost climbable" steps |
| `landing` | stair width x 1.6 | x 80 | E | every storey and every 12 risers |
| `B_stair` (exterior cut-in) | 4.0 or 8.0 wide, engineer risers, cheek walls 0.6, landings 2.0 deep | 200 / 400; 30; 100 | A + E | hazard-yellow nosings, lamps on both cheeks; `B_stair3` = the Ur triple flight for the company gate |
| `B_stairtower` | 3.0 x 5.0, 3.4 per flight, cage posts 0.15 | 150 x 250, 170 | A | halls and temple terraces |
| `catwalk` (grating) | grating 0.08-0.1; width 1.6 player-only, 2.6 where AI walks; rail 1.1, mid 0.55, posts 1.5, toe board 0.15 | 4-5; 80 / 130; 55 / 27 / 75 / 7.5 | E + A | dark lattice with light below; hazard toe board |
| `slab_grating` | 0.1 thick | 5 | E | mezzanines |
| `ladder` | 0.6 wide, cage over 3 m | 30 | E | decoration until LadderVolume is confirmed |
| `hoist_beam` | I-beam 0.4 deep at H - 1.5 | 20 | E | over every machine row |
| `B_bridgecrane` | span = hall W - 1, girder 1.2 x 1.0, end trucks 2, hook drop 4 | 60 x 50, 100, 200 | A | hazard yellow; a moving high spot in I2 |
| `pipe_run` + `B_rackbent` | pipes 0.3-0.6 at 3.0; bent 6.0 x 5.0, tiers 2.8 / 4.6, columns 0.3, every 6 m | 15-30 at 150; 300 x 250, 140 / 230 | E + A | headroom >= 2.4 m (120) over paths, >= 5 m (250) over roads |
| `conveyor_gallery` | 2.4 w x 3.0 h, walkway 0.8, bents every 20 m; **walked variant 3.9 x 3.9** | 120 x 150; **195 x 195** | E + LD | incline <= 12 deg; the walked variant is the I2 link hall_a -> hall_b |
| `transfer_tower` | 6 x 6, 3-4 storeys of 3.4 | 300 sq, 170 | E | stair inside, open top deck = a high spot |
| `mill` | cylinder r 2.0, L 6.0, on 1.5 plinths; drive 2 x 2 x 2 | r 100, L 300 | E | full cover |
| `crusher` | 3 x 2.5 x 3 under a 4 x 4 hopper | 150 x 125 x 150 | E | |
| `cells` | 2.5 x 2.5 x 2.0 boxes, 0.6 launder | 125 x 125 x 100 | E | waist/chest cover in rows |
| `cyclone_cluster` | 4 cones r 0.4, h 2.0, on a ring frame | 20 / 100 | E | |
| `thickener` | r 8, wall 3, raised 1, bridge to centre | 400 / 150 / 50 | E | a 16 m ring arena |
| `filter` | 6 x 3 x 3 on legs over a bin | 300 x 150 x 150 | E | |
| `pump` | 1.2 x 0.8 x 1.0 on a 0.3 plinth | 60 x 40 x 50 | E | pump house: 2 duty, 1 standby |
| `ro_rack` | cylinders r 0.2, L 6, stacked 4 high | 10 / 300 | E | desal stacks |
| `mcc_panel` | 3 x 0.6 x 2.2 | 150 x 30 x 110 | E | |
| `console` | 2.4 x 0.9 x 0.8 desk; optional upright meter panel 1.8 high | 120 x 45 x 40; 90 | E + A | top under the sill in front of glass; upright panels on back walls only; slate, cyan screens |
| `bunk3` | 2.0 x 0.9 x 2.4, curtain quad | 100 x 45 x 120 | E + A | |
| `messtable` | 4.8 x 0.9 x 0.75 + 2 benches 4.8 x 0.3 x 0.45 | 240 x 45 x 37 | E + A | 12 seats; half cover at 192 UU spacing |
| `B_culvert` | walked: 7.7 w x 6.4 h, 0.4 walls, 2.56 dry ledge; unwalked: 4 x 3 | 384 x 320, 128; 200 x 150 | LD + A | |
| `B_pillar` | 2 x 4, gallery height (9 m), chamfer 0.3, tide band at 1 m | 100 x 200 x 448 | A | sluice-gallery alcoves |
| `sluice_gallery` | 30.7 x 15.4 x 9.0 | 1536 x 768 x 448 | LD | grate mover behind, sluice gate mover ahead |
| `B_grate_hazard` | 2 x 2 x 0.1 | 100 x 100 x 5 | A | telegraphed floor hazard |
| `B_signboard` | 6 x 2 | 300 x 100 | A | the LIANDRI wordmark |

Exterior parts from the artist (s.5), same kit pass: `B_talud` 4.0 x 3.4 m, 1.2 -> 0.6 thick (200 x 170 UU);
`B_tablero` 4.0 x 1.7 x 0.5 (200 x 85 x 25); `B_terrace` 10.24 x 4.0 x 3.4 with a 1.1 parapet (512 x 200 x 170);
`B_dome` 12 m and `B_sphere` 6 / 9 m (600 / 300 / 450); `B_jib` mast 3 x 3 x 24, jib 30, counter-jib 10 (150 x 1200,
1500, 500); `B_stack` 2.5 x 30 (125 x 1500); `B_lamp_sodium` 8 m pole (400); `B_aviation` 0.4 globe (20);
`B_container` 6.06 x 2.44 x 2.59 (303 x 122 x 130); `B_shack` panels 1.0-1.2 x 2.4; `B_leanto` 3.0 x 2.5 x 2.6/2.0;
`B_stilts` 5 x 7 platform, posts at 2.5 m; `B_laundry` 6 m line; `B_drumtower` 3 x 3 x 9 (150 x 150 x 450).

Builder changes: the hollow mode; a plinth under every walled building down to the lowest ground (Q26/Q28); door
frames by owner (orange = liandri, slate = authority, none = nobody); no window pair over a door on cones and towers
(the "faces"); `wall_panels()` patch mode by layer plus windward wear from WIND (0.83, -0.55) (artist s.5).

Interior rules (engineer s.2, level designer s.3): headroom >= 2.4 m (120 UU); 1.5 m aisles round machines; 2 exits
for rooms over 20 m or 50 people; no point over 45 m from an exit; combat rooms 1024-2048 UU across with no open
line over 2048 UU, 2+ entries and one height change; a lit threshold, a 256-512 UU vestibule, a NoRain box and a
zone portal at each entrance.

---

## 6. The critical route and its beats

Order: the level designer's route (s.1) on Cine8, with the writer's interiors and the director's frames. Walk
timings are from level_designer.md s.1. The writer's beats 1-4 are marked **B1-B4**.

| # | place | in/out | emotion | encounter | frame | key prop | roles |
|---|---|---|---|---|---|---|---|
| 0 | command room (TutA opening, intro cine) | in | irony, ownership | none (refuge) | F2 -> F1 | the cored cable tagged LIANDRI SUPPLY; Oduya's board of company callsigns | W, D, A |
| 1 | jetty and dock yard | out | **B1 dread** | E1: Rook's smugglers, 3 MercJapLight + 1 Medium from the boat; teaches hitscan | F7 (tower hidden behind the quay silos) | the PA (pa08) before any person is seen | all |
| 2 | Tin Row lane, the mess (I4), Tin Bar (optional) | out/in | belonging that excludes you; intimacy, guilt | none; health in the mess | F9 (the warm window) | the company mural; the cap and the beret at one card table | W, D, LD, A |
| 3 | works road -> hall_a -> belt gallery -> hall_b (I2) | in | labour, scale | I2: the production line, 4 Light + Medium on the gantry + Heavy at the end | F12 (north-light shafts, the roller door framing the cooling towers) | the bridge crane; the conveyor | LD, E, D, A |
| 4 | dorm square (E2) | out | foreboding | E2: security behind a barricade facing the drain, 2 Light + 1 Heavy | F13 (the dorm gallery) | dorm_c's door torn outward, hive husks | LD, W, D |
| 5 | the culvert (I3), quiet stretch | in | unease, curiosity | none, 35-50 s of creeping (LD7) | F11 | Haldane's bucket, Arashiro's jars, Rook's crates and lamp, a dead man | W, LD, A, D |
| 6 | sluice gallery: the reveal | in | dread, then shock | one agile SkaarjLight, solo, 20-30 s; ammo and health in the alcoves after | F11 (silhouette against the red beacon) | the sluice gate's red beacon | LD, A, D |
| 7 | cooling basin (E3) | out | release into the brawl | E3: 2 SkaarjLight against 3 mercs, player third party | F1's hero from below | the cooling-tower legs as pillars | LD, E |
| 8 | spine climb, the bend at s=7696 | out | **B2 exposure** | none | F8 (the hero's top over the roofs) | the hero lit, the street in shadow | all |
| 9 | company gate (E4) | out | **B3 smallness** | E4: Berserker down the stair, 2 SkaarjLight by drop pod | F10 | the ceremonial stair beside the truck road; Liandri House's empty hall through glass (D4) | all |
| 10 | checkpoint | in | sympathy | none | - | Nkemelu's log; the barrier tied up with a company strap | W |
| 11 | tower lobby (I1) | in | pressure | the lift hold, 3 + 2 SkaarjLight, 20 s call | F3 (the corridor version in TutA) | the lift call panel | LD, W |
| 12 | lift ride, command deck, overhang deck | in/out | compression, survey | none | F4 | the slit windows naming the districts | LD, D |
| 13 | catwalk | out | **B4 melancholy** | none | F5, the peak frame | Hawkins at the rail (D2); the dead rig's one light | all |

Walking about 140 s, with fights and exploring a 9-12 minute slice. F6 (the storm window) and F14 (the rigs) are
later beats from the command room.

---

## 7. Build order

### Phase A: CPU only, possible during a playtest
No approval needed:
1. Tool fixes B1-B13, B15, B19 (codirect.py, compose.py, town.py, systems.py, layout_spine.py, terrain_cutfill.py's
   cap import).
2. New checks: E1', E12', E14', E16', E22-E30, LD8, LD9, hero-unique, grain, IMP per district.
3. Re-score Cine8 and Town7 on the graded heightmap; compose.py check of whether the summit is in the window cone
   (the data for D1).
4. Read U2's pawn collision, step height and ladder classes from the game's own exported scripts (no leaked code).
5. A PathNode generator from the graded heightmap (one every 400-600 UU, two per cover piece, high spots).
6. 2D greybox plans of the four shells (I1-I4) and six arenas (E1-E4, I2, I3) with drawings.py.

After your approval (D-numbers in brackets):
7. Binder edits: parti hero and sheets [D1], Hawkins routine [D2], census and new groups [D3], liandri_tower sheet
   [D1, D4], process-chain sheets [D9], guest_house, citizens and PA lines pa13-pa15, r11 [D11] (Piper voices on the CPU).
8. build_parts: the hollow mode and the section 5 kit (B14); palette 12 stripes [D5] in glb_to_ase.py and
   part_to_ase.py, without re-running glb_to_ase on the existing B_*.glb.
9. `drainage.py` (the routing in section 3.2), `pads: 2` stepped buildings (B16).

### Phase B: needs the editor or the GPU
1. A town.py run with the fixes, to re-roll the layout (B17).
2. terrain_apply, the new meshes, and the interior shells as BSP add-brushes in TutA's own textures (level designer s.6).
3. The lowsun bake: check that the tower's shadow wedge reaches the housing (F1).
4. PathNodes imported after LIGHT APPLY, then PATHS DEFINE (the Sanctuary gotcha).
5. TutA-only lighting for D6 (a): the start pitch, halved corridor lamps, the deck lamp pool, the Q57 gap texture.
6. Kontext paint-overs and Hunyuan when the GPU is free (the temple, the mess mural).

### Phase C: in-game tests
1. Measure the open facts in section 8 first, before any interior is final.
2. Greybox playtests of E1-E4, I2, I3 and the I1 hold; the reveal script (lamps 0.6 s apart, the gate, the 1 s idle).
3. The frame checks F1-F14 against the peak frame; the Hawkins pose [D2].
4. A pilot run of the whole route: walking time and LD2 pacing.

---

## 8. Open facts to verify in the game

- **Pawn collision**: the player's CollisionRadius and CollisionHeight. The engineer assumed about 25 / 44 UU; nobody
  has read them.
- **Step height**: the level designer read MaxStepHeight 37 UU from U2PlayerSP.uc; the engineer assumed about 35. Check
  that the AI uses the same value.
- **The walkable floor angle** (~45 deg assumed) and whether a reachspec over steeper ground fails silently.
- **Ladders**: does U2 support LadderVolume? Until it does, ladders are decoration and routes use stairs.
- **Lifts**: LiftCenter/LiftExit for the freight lift; waves must path to the lobby, not the shaft.
- **Skaarj clearances**: SkaarjLight CollisionHeight 65, SkaarjHeavy radius 34, height 70 (from exported U2Pawns). Check
  the agile Skaarj's leap needs 256 UU of ceiling.
- **Doors and movers**: Door navigation points on the roller doors, the drain grate and the sluice gate; the Skaarj path
  must not exist before the gate opens.
- **Water**: no AI paths in a WaterVolume, so the drain's water stays a decal.
- **Collision on props**: Hunyuan, kiln and card meshes may have none; cover needs collision (`gm collide`, Q69).
- **The shadow**: does the BSP tower cast onto the terrain in the lowsun bake at sun elevation 6-9 deg?
- **The figure**: can a pawn be posed with AI off and an idle at the catwalk end, 40-100 m from the camera, and is the
  catwalk that long?
- **Lighting**: AmbientGlow against AmbientVector (Q71); vignette 0.35 or 0.5 indoors; the console screens' texture
  hashes for a `tint=`; the hero's readability in storm fog (2000/60000).
- **Lamp toggles**: can level lights be switched 0.6 s apart from script for the reveal?
- **The quay**: Town7's quay deck is 15 m over the sea; check E23 on the next layout.
