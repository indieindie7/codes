# Avalon redesign, 2026-10-09: the LEVEL DESIGNER

Role: how the town and its interiors PLAY (codirect.py LD1-LD7). Written during the user's playtest, so no GPU, game,
editor or pilot runs were used. The only things run were CPU reads of the TutA_Cine8 run folder and a re-run of
`codirect.py` on its graded heightmap. The references are web pages, nothing was downloaded, and none of them ship.

Units: 50 UU = 1 m (project convention). U2 numbers used throughout:
- the player walks at 263 UU/s (5.3 m/s);
- NPC hit odds fall off past 1024 UU (20 m), and fights in the open past 2048 UU (41 m) are won by volume of fire;
- the sight cap is 6000 UU (FairFights);
- floors are walkable up to ~45 deg, and the critical route is held to <= 30 deg;
- player MaxStepHeight is 37 UU (U2PlayerSP.uc).

Skaarj sizes (exported U2Pawns): U2SkaarjLight CollisionHeight is 65, so it stands ~130 UU tall. U2SkaarjHeavy has radius 34 and
height 70. Doors and ducts that Skaarj use must therefore be **>= 192 UU high and >= 128 UU wide**.

---

## 0. What the current map says (measured on the CPU, TutA_Cine8)

| check | on `isl_e.bmp` (before grading) | on `isl_ec.bmp` (after cut/fill, what ships) |
|---|---|---|
| LEVEL score | 0.93 | **0.69** |
| LD2 pacing | 7 beats in 47 s, longest quiet 29 s | same |
| LD4 street ends on a view | 6 of 8 | **3 of 8** |
| LD5 junction arenas (mean) | 0.75 (81 % of rays blocked at the best one) | **0.44** (50 %) |
| LD7 quiet stretch into a fightable junction | yes | **no** |

**The main finding is that grading kills the play.** The pads and road cuts flatten exactly the knolls and banks that
broke the sightlines and gave the high spots. The Cine8 review scored the level *before* cut/fill. From now on:
1. score LEVEL on the graded heightmap;
2. place cover as clutter after grading, never rely on raw terrain for it.

Other facts from the layout:
- **The town is short.** The spine from the dock to the tower is 12 265 UU, which is **47 s** of walking. The whole spine to
  the mine is 28 261 UU (107 s). A 47 s town has no room for a build-up, so the critical route below
  deliberately leaves the spine. It goes through the works, the drainage and the tower's inside, and comes out at
  ~37 000 UU of walking (~140 s). With the fights, the slice runs 9-12 minutes.
- **The works are 4000-6000 UU south of the spine.** hall_a/b, plant_office, tank_farm and the dorms sit there and are
  reached only by one branch: a 5990 UU dead-end road. They are the best combat ground on the island and the
  route never visits them.
- **A duplicate branch.** layout_spine still emits the 7000 UU branch (3293,-7084)->(-1657,-12033) twice (noted
  in Q39, still there).
- **No AI navigation off the tower.** TutA's ~50 path points are all on the tower decks, and the town has none.

---

## 1. The critical path (Cine8 coordinates; the roles carry to any seed)

The parti's four beats stay the spine of the experience:
1. the dock: dread;
2. mid-spine: exposure;
3. the company gate: smallness;
4. the catwalk: melancholy.

Between them the route is pulled through the places where Avalon's story actually happens.

```
 SEA                                                          N (+Y) up, E (+X) right
  P0 dock jetty (6026,-5339)
   |  E1 DOCK YARD
  P1 dock gate --path--> spine s=0 (4712,-7196)
   |  Tin Row / old core (tin_bar, water_tower, mess = I4 refuge)
  P2 spine s=832 (3880,-7196) --branch south 5990 UU--> P3 works road end
   |                                            I2 PROCESSING HALL (hall_a 3455,-11176)
   |                                            P4 dorm square E2 (checkpoint 2256,-8976 / dorm_c)
   |                                            P5 drainage mouth (~1300,-8100, under the plant fence)
   |                                            I3 DRAINAGE  ->  sluice gallery = THE REVEAL
   |                                            P6 cooling-tower basin E3 (2175,-4637)
  P7 spine s=3801 (1704,-5212) <---------------------'
   |  spine climb: pump_house, clinic, bend at s=7696 (-1240,-2780) "tower glimpsed over roofs"
  P8 company gate E4 (company_store 94,-808 .. s=10509)
  P9 tower base s=12265 (-546,716)  -> I1 TOWER: lobby hold -> freight lift -> command deck -> catwalk
```

### Timings at 263 UU/s

Walking only. Fights and exploration are listed separately.

| leg | from -> to | UU | walk s | cum. walk | beat at the end (LD2: <= 60 s apart) |
|---|---|---|---|---|---|
| 0 | jetty -> dock yard | 800 | 3 | 0:03 | **E1 Dock Yard** fight (mercs) |
| 1 | dock yard -> dock gate -> spine s=0 | 2 500 | 10 | 0:13 | the gate: tower HIDDEN behind the quay silos (dread) |
| 2 | spine 0 -> 832, Tin Row | 832 | 3 | 0:16 | the mess door, lit (I4 refuge, optional) |
| 3 | branch south to the works | 5 990 | 23 | 0:39 | the hall's roller door + conveyor (weenie: the hall chimney) |
| 4 | I2 Processing Hall traversal | 4 200 | 16 | 0:55 | **I2** fight on the line |
| 5 | hall exit -> dorm square | 2 500 | 10 | 1:05 | **E2 Dorm Square** (barricade, traces) |
| 6 | dorm square -> drainage mouth | 1 400 | 5 | 1:10 | the culvert grate, the PA cuts out |
| 7 | I3 Drainage, quiet stretch | 3 600 | 14 (creep: 35-50) | 1:24 | **LD7 quiet**: traces only, no enemies |
| 8 | sluice gallery (the reveal) | 1 536 | 6 | 1:30 | **REVEAL**: lights out, a Skaarj |
| 9 | sluice -> cooling basin | 900 | 3 | 1:33 | **E3 Cooling Basin** (the remix brawl) |
| 10 | basin -> spine s=3801 | 800 | 3 | 1:36 | back on the spine; the cooling towers loom (the hero) |
| 11 | spine 3801 -> 7696 (bend) | 3 895 | 15 | 1:51 | the tower glimpsed over roofs (exposure) |
| 12 | spine 7696 -> 10509 | 2 813 | 11 | 2:02 | **E4 Company Gate** (battered wall, stair cut-in) |
| 13 | gate terraces -> tower base | 1 756 + 600 climb | 9 | 2:11 | **I1 lobby hold** (lift wait) |
| 14 | lift ride + command deck -> catwalk | ~2 000 | 8 + lift 20 | 2:39 | **release**: the catwalk, dusk rain |

Totals:
- walking ~37 000 UU = **~2:20 on foot**, longest walk without a beat 23 s (leg 3), so LD2 passes everywhere;
- fights, by design: E1 60-90 s, I2 90-120 s, E2 30-45 s, reveal 20-30 s, E3 60-90 s, E4 90-120 s, I1 hold 60-75 s;
- exploration and creep about 2-3 min;
- **slice length 9-12 min.**

Pacing shape (L4D build-up / peak / relax):

```
intensity
  peak |            I2                      E3        E4    I1
       |   E1      /\                /R\   /  \      /\    /\
       |  /\      /  \    E2        /   \_/    \    /  \  /  \
       | /  \____/    \__/  \______/            \__/    \/    \___ catwalk
       |dock  Tin Row  hall  dorms  DRAIN(quiet) basin spine gate tower
```
After each peak there are >= 30 s without forced combat:
- E1 -> Tin Row and the mess;
- I2 -> the dorm square (traces);
- E3 -> the spine climb;
- E4 -> the tower lobby. This is the one deliberate exception: the lift hold follows E4 after a 20-30 s gap, and the lift ride
  and catwalk are the long relax.

---

## 2. Encounter spaces (6)

Common rules, the same as Sanctuary's arenas.py so the two projects score alike:
- cover: **>= 3 pieces 256-1024 UU out**, half height 50-64 UU and full height >= 110 UU;
- **>= 2 entries** (nav quadrants);
- **30-80 % of 16 rays blocked within 2048 UU**;
- a **high spot +150 UU or more within 800 UU**;
- enemies **256-1024 UU off the route**;
- spawns arrive through a door, pod or vehicle (never popping in) and never inside the player's 90 deg rear cone;
- health within 30 s of walking after the fight.

FairFights attack tokens stay on (RangedTokens=2) so a squad of 4-6 does not hitscan in unison.

Legend for the diagrams: `[ ]` a building or solid, `##` full cover, `==` half cover, `^` high spot, `>` entry,
`S` spawn, `P` the player's arrival, `~` water, `:` sightline breaker.

### E1 Dock Yard (exterior): the first fight teaches the hitscan

Size: 3 200 x 2 400 UU, the quay apron between the jetty and the dock gate.
Lineup: Rook's smugglers unloading, 3 x U2MercJapLight + 1 x U2MercJapMedium.

```
          ~~~~~~~~~~~ SEA ~~~~~~~~~~~
   P>=== jetty ===[crane legs]^ crane cab (+400 UU, ladder)
        ==crates==     ##container##       == pallets ==
   [quay shed]    :forklift:      ##container##     [silo]  <- tower hidden behind (dread)
        ==        S(boat)   ==barrels==      ##       ==
   >side lane (shore path)          >dock gate (to spine)   >back lane behind the shed
```
- **Story before the fight.** The mercs start unaware, visible from the jetty at 1400-1800 UU. This is the Level Design
  Book's "player ambushes enemies" foothold. The player sees the whole yard before the first shot.
- **Cover.** 7 pieces: 2 containers (full), crates, pallets and barrels (half), spaced 200-400 UU. The crane legs are a
  ring-around-the-rosie pillar.
- **High spot.** The crane cab is +400 UU, reached by a ladder. It is exposed, which is the price of seeing the yard.
- **Entries.** 3: the jetty, the shore path and the back lane. The gate is the exit.
- **Spawns.**
  - 3 mercs start placed.
  - The Medium arrives 10 s into the fight from the boat (S). The boat itself is the visible cause of the reinforcement.
- **Teach.** Hitscan at range hurts, and cover inside 1024 UU makes it fair. So the opening sightline is long and
  the cover pulls the fight in to 600-1000 UU.
- **Sightlines.** The yard itself is open. The containers and crane break 50-60 % of the rays.

### E2 Dorm Square (exterior): traces and a short fallback

Size: 2 400 x 2 000 UU, between the checkpoint, dorm, dorm_c (abandoned) and the memorial.
Lineup: company security behind a barricade facing *away* from the player (they were holding off something
else), 2 x U2MercJapLight + 1 x U2MercJapHeavy.

```
   [dorm_c, dark, door torn]      [memorial]^ (plinth +160)
     : claw marks, husks :            ==
  P> hall exit lane    ==sandbags==   ##barricade## S(checkpoint door)
     [dorm]  ==laundry carts==        [checkpoint]^ roof +300 (stair)
     >back lane                  >road north (to the drainage path)
```
- **Halo canonical fallback, small scale.** Barricade -> checkpoint door -> roof. The Heavy holds the roof.
- **Foreshadowing beats the fight.**
  - dorm_c's door is torn outward, and dead Izarian hive husks lie in its hall;
  - the barricade faces the drainage;
  - the radio line is clipped mid-sentence (writer).
- **Cover.** 5 pieces at 250-700 UU. Sightlines are broken 55-70 % by the dorm rows.

### E3 Cooling-Tower Basin (exterior): the remix brawl

Size: 3 600 x 3 000 UU, the dry cooling pond round the cooling-tower legs. It is 300 UU below the yard, so the
basin rim is the high ground. Lineup: 2 x U2SkaarjLight (agile) fighting 3 x U2MercJapLight, with the player as
the third party. That is enemy palette 4, a brawl kept readable because the two factions fight each other (Level Design Book).

```
   rim (+300) ^------^ pipe rack walkway ^-------^ rim
   >sluice mouth (P, from I3)                   >ramp to spine (exit)
      ~ puddles ~   ( TOWER LEG )   ==pump skid==
     ==valve==      ( TOWER LEG )        ##control hut##  S(mercs: hut door)
   S(Skaarj: second culvert)   ( TOWER LEG )   ==
   >maintenance stair                     >drain grate (Skaarj only, 192 high)
```
- **The tower legs are pillars.** They make a combat bowl that suits the Skaarj's dodge and leap, which is the move
  the reveal just taught.
- **Spawns.**
  - The Skaarj come out of the second culvert and the grate.
  - The mercs come from the control-hut door.
  - Both are visible from the sluice mouth.
- **Halo spice.** A merc on the rim walkway is the "sniper".

### E4 Company Gate and Stair Cut-in (exterior): smallness, then the big remix

Size: 2 800 x 2 400 UU, three terraces climbing 160 + 200 + 240 UU toward the tower plateau. The battered company wall
(Aztec stepped, ENGINEER and ARTIST) has one stair cut into it.
Lineup:
- 1 Berserker Skaarj (U2Enemies, melee rush);
- 2 x U2SkaarjLight arriving by drop pod;
- the company's mercs are already dead (the bodies tell it).

```
 TOWER PLATEAU (tower base, I1 door)  ^ terrace 3 (+600 total)
 ##parapet##   [generator_house]   ==fuel drums==   >side ramp (switchback, engine)
 ---- battered wall ---- STAIR CUT-IN (192 wide, landing every 12 steps) ----
   terrace 2 (+360)  ==planters== [company_store]  S(drop pod 1 lands here)
 ---- terrace wall ----            ramp            ----
   terrace 1 (+160)  P> from spine     ==barrier==   S(drop pod 2, visible streak)
```
- **Canonical fallback in reverse.** The PLAYER climbs and the Skaarj hold the terraces.
  - The Berserker charges down the stair (a chokepoint the player can use against it).
  - The Lights leap between terraces, which makes the terrace edge the cover.
- **Entries.** 2 routes up: the stair cut-in (short, exposed) and the side switchback (long, covered). This is the go-over or
  go-around choice of Nintendo's triangles.
- **Visible reinforcement causes.** The drop pods are visible streaks, as in Sanctuary Open.

### I2 and I3 encounters and the I1 hold
These live inside the interiors and are described with their layouts in section 3.

---

## 3. Interior combat layouts (4)

Interior rules for U2:
- combat rooms 1 024-2 048 UU across, so the fights land in the fair 512-1 500 UU band;
- **no open indoor line longer than 2 048 UU** without a break;
- corridors 256 UU or more (AI two abreast), connectors 192 or more;
- ceilings: 256-384 in rooms, 800-1 200 in halls;
- doors 128-192 W x 192-256 H;
- every combat room has 2 or more ways in and one height change.

**Exterior to interior transitions:**
- a lit threshold (warm door lamp, the "go" colour);
- a 256-512 UU vestibule or airlock, a compression beat before the room;
- a NoRain box (Q50) covering the whole shell;
- a zone portal at the door so ambient, fog and sound switch;
- light levels: dark vestibule, then lit room (D1 compression/release).

### I1 The Tower (base lobby, freight lift, command deck, catwalk)

The real TutA command room stays as it is: about 3 700 x 1 900 x 650 UU (the NoRain box -1300..2400, 400..2300,
4150..4800), with the deck under the overhang at z ~3 900. The tower stands ~7 900 UU over its ground (z -3 767 to
~4 150), so the inside is a lift, never stairs.

```
 BASE LOBBY (new shell at ground, 1 800 x 1 400 x 600)       COMMAND DECK (existing)
   >E4 plateau door (airlock 384)                             [lift arrival]
   ==desk== ##pillar## ##pillar## ==crates==                  window band (yaw 300) -> the plant
   ^mezzanine (+256, 2 stairs, rail)  S(service door)         [Hawkins' table]
   [FREIGHT LIFT cage 512x512, call 20 s]  S(vent, 192)       > outdoor deck -> CATWALK (release)
```
- **The lobby hold** (Destiny "hold the zone", which the user likes). The lift call takes 20 s, and two waves of
  U2SkaarjLight come from the service door and the vent (3 + 2, tokens on).
  - Cover: 2 pillars (full), the desk and crates (half).
  - The mezzanine is the high spot, and it has two stairs so it can't be camped safely.
- **The lift ride** is the relax. The shaft has slit windows onto the town, which is the "survey" moment: every
  district named from above.
- **The command deck** is a refuge (prospect-refuge): no fight. The catwalk at dusk in rain is the parti's release frame
  (design-taste-avalon-peak-frame).

### I2 Processing Hall (hall_a): an assembly-line traversal

Shell 4 200 x 1 600 x 1 000 UU. A sawtooth roof, a conveyor down the long axis, a gantry crane and two catwalk levels.
The idea comes from Titanfall 2's "Into the Abyss": follow the production line, and the line ends in a space made of
its own product.
Lineup:
- 4 x U2MercJapLight;
- 1 x U2MercJapMedium on the gantry;
- 1 x U2MercJapHeavy at the end.

```
 >roller door (P, 384 W)                                        >loading bay (exit, 512 W)
 | VESTIBULE | ==ore hopper== |  bay 2: ##press## catwalk L1(+256) | bay 3: crushers | END: ore silo yard
 |  (dark)   | conveyor ===================================================> |  S(Heavy, bay door)
 |           | ^ gantry crane cab (+640, moves along: a moving high spot)     |
 >side door  | catwalk L2 (+512) ------ ladder ------ stair ------ ladder --- >  >office stair (flank)
```
- **The Doom 2016 lesson** (Lazarus Labs). Dead-end side aisles were joined into loops. Here each bay has an aisle
  on both sides of the conveyor plus catwalk crossovers every 1 000 UU, so the player can always circle.
- **A jungle gym, not a canyon** (Saltsman). There are three separate floors (0 / +256 / +512) with clear edges.
- **Cover** is the machines: presses and crushers full, hoppers and skids half, spaced 300-500 UU.
- **Sightlines.** The 4 200 UU long axis is broken by the presses at 1 200 and 2 600, so no line is over 2 048.
- **Spawns** come through the bay doors and the office stair, which is the flank (F.E.A.R. lesson: a second entry makes
  ordinary cover-seeking look like flanking).

### I3 Drainage (culvert under the plant fence): the quiet stretch, then the reveal

The ENGINEER's planned `drainage.py` culverts make this real: the plant's storm drain runs under the fence to the
cooling basin. The walk is 3 600 UU, then the sluice gallery.
- Section: a 384 W x 320 H box culvert with a 128 UU dry ledge. The water is <= 32 UU deep, decal plus sound,
  **not a WaterVolume** (Sanctuary lesson: there are no AI paths in water).

```
 P>grate (from E2 road)   culvert 384 W  ~~ ~~ dry ledge ~~ ~~   junction room 768x768 (shaft light from a grate)
   bend (no line > 1 500)     [body: security merc]       [claw marks, torn pipe]      [hive husk, dripping]
 ---> SLUICE GALLERY 1 536 L x 768 W x 448 H:  [gate drops behind P]  lamps 1..6 down the right wall
      alcove(=)  alcove(=)  alcove(=)  [far SLUICE GATE: red beacon, opens]  -> S(Skaarj)  -> mouth to E3 basin
```
- The full recipe is in section 4.
- The gallery is **768 UU wide on purpose**. The Skaarj Light's dodge and leap need room. A 384 culvert would make the
  first fight a melee scrum and teach nothing.

### I4 Mess Hall (mess, by the dock): refuge and recovery

Shell 1 600 x 1 000 x 384 UU, long tables, a serving counter and a window onto the dock yard.
- **The room's job is not combat.** It is the recovery point after E1: health on the counter, the PA, a TV with the
  company channel, and a pin-up and "days since last incident" board (the misery cues in Level design practices s.4).
- **A combat-ready layout for later replays or the GM.**
  - 2 doors (street, kitchen yard).
  - Tables are half cover in rows 192 UU apart.
  - The counter is full cover.
  - The kitchen loop makes a ring-around-the-rosie.
  - No high spot (a deliberate weakness: the mess is where you rest, not where you hold).

---

## 4. The Unreal-1 reveal (Rrajigar Mine, rebuilt in the drainage)

Unreal's first Skaarj (Rrajigar Mine, Cliff Bleszinski) goes like this:
1. a corridor of corpses;
2. barriers close;
3. lights die one by one from the far end;
4. walls open with red light and an alarm;
5. a Skaarj charges;
6. afterwards the barriers lift and the alcoves hold supplies.

Mapped onto Avalon:

| step | where | what | duration |
|---|---|---|---|
| 1 Foreshadow (long before) | E2 / dorm_c | torn door, Izarian hive husks, the barricade facing the drainage, the clipped radio line | from 1:05 |
| 1b Sound | drainage legs | scrapes behind the culvert wall, at distance only; the PA dies at the grate | 1:10-1:24 |
| 2 Isolate | I3 culvert | 35-50 s of creeping, **no enemies**, one security merc's body (the "what happened here") | LD7: 25-60 s |
| 3 Commit | sluice entry | a grate mover drops behind the player (one-way: the Level Design Book's committed foothold) | 0 s |
| 4 Stage | gallery | the 6 wall lamps die one at a time from the FAR end toward the player (TestLamp/level-light toggles, 0.6 s apart); the red beacon on the sluice gate turns on; the alarm plays | ~5 s |
| 5 Reveal | sluice gate | the gate opens, and a SILHOUETTE stands against the red light for a beat (the Skaarj has a 1.0 s scripted idle before its AI wakes) | 1 s |
| 6 Fight that teaches | gallery 1 536 x 768 | **one** agile U2SkaarjLight: dodges, leaps the 768 width, slashes. The alcoves (half cover) stop the leap line. No other enemy. | 20-30 s |
| 7 Reward | gallery | the beacon goes off, the sluice stays open, and the alcoves hold ammo and health (like Rrajigar's supply alcoves) | - |
| 8 Remix | E3 basin, 3 s later | 2 Skaarj + mercs: the same move in a bigger space, among others | 60-90 s |

Rules this obeys:
- the first meeting is with that kind alone, at most 2 of it (arenas.py "teach");
- the reveal uses the level itself, never a cutscene;
- the silhouette, the move and the sound are the memorable creature.

---

## 5. Where AI paths and nav need care

1. **The town has no PathNodes.** Generate them from the graded heightmap:
   - one every 400-600 UU on roads and paths;
   - denser in the arenas (one per cover piece, both sides);
   - plus nodes on the high spots.
   Import them **after LIGHT APPLY**, then PATHS DEFINE. This is the Sanctuary gotcha: PathNodes placed before LIGHT APPLY crash it.
2. **Terrain slope.** A reachspec over ground steeper than ~45 deg fails silently, so check every arena entry slope on the
   graded map. The E4 terraces need ramps or stairs with real risers (<= 24 UU so AI and the player both climb;
   MaxStepHeight 37). No 25-70 UU "almost climbable" ledges on the route.
3. **Static meshes without collision.** Hunyuan, kiln and card props may lack collision, and the AI paths through them.
   Every cover piece needs collision. Either use kit meshes that have it, or put `gm collide` cylinders (Q69) on them.
4. **Doors and movers.** I2's roller doors, the I3 grate and sluice gate, and the I1 airlock need Door navigation points.
   The sluice gate stays shut until the reveal script opens it, so the Skaarj path must not exist before then.
5. **Lifts.** The freight lift needs a LiftCenter and LiftExits at both stops. The I1 hold waves must path to the lobby,
   not into the shaft.
6. **Drainage water.** Never a WaterVolume (no AI paths in water). The ledge and floor are ordinary ground with a
   puddle decal and sound.
7. **Catwalks and gantries.** These are narrow nav. Place nodes on catwalks only where the width is >= 128 UU. The moving
   gantry cab is a player-only high spot (no node on it).
8. **Skaarj leaps.** Agile Skaarj (bJumpDodges) need clear space: no low ceilings under 256 in the gallery or the basin, and
   no node pairs across a gap the Skaarj can't jump.
9. **Drop pods and spawn doors.** Each spawn point must sit within 400 UU of its door or pod (arenas.py "arrival") and be
   linked to the main graph by at least 2 reachspecs.
10. **The town's edge.** Map limits are the sea, the plant fence and the terrace walls. Blocking volumes go on the fence
    gaps that walks.py cut where no route is intended.

---

## 6. Keep, cut, add

**Keep**
- The spine dock -> tower and the parti's 4 beats. The tower stays hidden at the dock gate (WRITER, Q37 serial vision).
- The command room and window frame as they are. It is the refuge and survey moment, not a fight space.
- The cooling towers as the hero and the E3 arena: the hero gets a fight round its legs.
- The worn paths (walks.py). They are the AI's natural routes and the player's breadcrumbs.
- The shanty on the mountain as a vista and an optional exploration loop. It is not on the critical route.

**Cut**
- The duplicate 7 000 UU branch in layout_spine.
- Open ground over 2 048 UU in any arena with hitscan mercs, unless it has 3 or more occluders.
- Any cover piece the cut/fill flattened. Re-place cover after grading.
- Card or prop dressing inside arena footprints that has no collision.

**Add**
- The 4 interior shells:
  - the tower base lobby and lift;
  - hall_a as a real interior;
  - the drainage culvert and sluice gallery;
  - the mess.

  Make them as BSP add-brush shells in TutA's own textures and Mission_* trims, the way Sanctuary Open built its
  shells, so they look like the level's own architecture (the remix rule).
- Two **new links**: works -> dorms -> drainage -> cooling basin -> spine. This turns the works dead end into a loop
  (loopback typology), and the critical route grows from 47 s to ~140 s of walking.
- **The company gate**: the battered wall plus the stair cut-in and the side switchback (with the ENGINEER).
- **codirect LD changes**:
  - LD5 and LD7 on the graded heightmap;
  - an LD8 "interior rooms" check (room spans 1 024-2 048, no line > 2 048, 2 or more doors, a height change);
  - an LD9 "reveal recipe" check (a quiet stretch, a committed entry, a solo first fight, a reward).

  These are proposals only; I changed no code.
- **Encounter placement from LD5/LD7.** Spawn points out of view on visible entrances, and cover as clutter (the Q39 NEXT item).

---

## 7. Web references (13)

Nothing was downloaded. The references inform the layout and never ship.

| # | Page | Author / source | Licence | What fits | For |
|---|---|---|---|---|---|
| 1 | https://unrealarchive.org/wikis/the-liandri-archives/Rrajigar_Mine.html | The Liandri Archives (Unreal Archive); map by Cliff Bleszinski | CC BY-SA 3.0 (stated) | The first Skaarj staging: a corpse corridor, barriers close, lights die from the far end, walls open with red light, a solo Skaarj, supply alcoves after. **Pacing and reveal.** | I3 sluice gallery, section 4 |
| 2 | https://unrealarchive.org/wikis/the-liandri-archives/NyLeve's_Falls.html | The Liandri Archives; map by Juan Pancho Eekels | CC BY-SA 3.0 (stated) | Calm outdoor stretches alternating with interior fights; a lift down to a fork; a dark interior leading out to a bright exterior. **Exterior-interior rhythm.** | the whole route; the I2 -> E2 -> I3 -> E3 alternation |
| 3 | https://book.leveldesignbook.com/process/layout/typology | The Level Design Book (Robert Yang et al.) | CC BY-NC-SA 4.0 (stated) | Typologies: combat bowl or ring-around-the-rosie, arena/POI with gating, hub-and-spoke, loopback, string of pearls. **Flow.** | E3 (bowl), I2 (loops), the works loop |
| 4 | https://book.leveldesignbook.com/process/combat/encounter | The Level Design Book | CC BY-NC-SA 4.0 | Footholds (player ambushes, enemies ambush, a vista with a one-way commit) and the enemy palette table (1 type = tutorial, 4 = a readable two-faction brawl). **Encounter structure.** | E1 foothold, the sluice commit, the E3 brawl |
| 5 | https://combineoverwiki.net/wiki/Developer_commentary/Half-Life_2 | Combine OverWiki, transcribing Valve's HL2 commentary | not stated on the fetched page (check before quoting) | Canals: rest stops between pressure ("players needed some downtime"), the helicopter's ring path keeping it visible so cover can be placed, the drainage ramp, the street framing the Strider's first appearance. **Pacing, the reveal frame, industrial drainage.** | I3 drainage, the post-fight relax, the E4 drop pod sightline |
| 6 | https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf | Jeff Orkin (Monolith), "Three States and a Plan: The A.I. of F.E.A.R.", GDC 2006 (course copy) | author's copyright | Designers build "spaces filled with furniture for cover, glass windows to dive through, and multiple entries for flanking". Apparent flanking is the AI moving to the only valid cover via a back route. Squad moves: Get-to-Cover, Advance-Cover, Orderly-Advance, Search. **Cover, flanks.** | I2 side doors and office stair, the I4 tables, E2 |
| 7 | https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf | Damian Isla (Bungie), "Building a Better Battle: The Halo 3 AI Objectives System" (WPI course copy) | Bungie's copyright | The canonical encounter: hold a territory, then a fallback, then a last stand, then the player breaks them, with snipers, turrets and dropships as spice. Tasks = territory + aggressiveness. **Encounter flow, verticality.** | E2 (barricade -> door -> roof), E4 (terraces), the E3 rim sniper |
| 8 | https://www.guerrilla-games.com/media/News/Files/gdce05_killzone_ai.pdf | Arjen Beij and Remco Straatman (Guerrilla), "Killzone's AI: Dynamic Procedural Tactics", GDC Europe 2005 | Guerrilla's copyright | Positions scored by lines of fire, partial cover from the main threat, proximity and preferred range over a waypoint graph fine enough to represent cover. **AI nav density.** | Section 5: PathNodes on both sides of each cover piece |
| 9 | https://blog.playstation.com/archive/2017/05/12/classic-levels-deconstructed-the-beautiful-brutality-of-dooms-lazarus-labs | PlayStation Blog staff, with Hugo Martin, Marty Stratton and Jerry Keehan (id) | publisher's copyright | The crate room has "the line of sight breaks, the ins and outs". A lab's dead-end hallways were fixed by linking them into a loop. **Sightlines, circulation.** | I2 aisle loops, E1 container yard |
| 10 | https://blog.adamatomic.com/post/613311014289768448/design-of-doom-eternal | Adam Saltsman | author's copyright | Tall arenas are "jungle gyms" (distinct floors) or "canyons" (open, chaotic). Pickups pull players into positions they wouldn't take. **Verticality.** | I2 three floors, the I1 mezzanine, the E3 rim |
| 11 | https://www.gamedeveloper.com/design/level-design-for-combat | Max Pears (Game Developer, 2019) | publisher's copyright | Main doors ~2x the width of side doors; cover at doorways so entering isn't a death; consistent cover spacing so the route through a fight reads; spaces matched to weapon range. **Cover, entries.** | all door sizes, the I1 airlock cover, E1 |
| 12 | https://primagames.com/news/blocking-drunk-titanfall-2s-story-mode-came | Prima Games, on Christopher Dionne's GDC 2018 "action blocks" talk (Respawn; session https://gdcvault.com/play/1025105/) | publisher's copyright | Action blocks: "not perfect, but playable" prototypes. Into the Abyss follows one assembly line through a factory to a fight inside the prefab village it builds. **Greybox method, an industrial set piece.** | I2 processing hall; the greybox order |
| 13 | https://www.blog.radiator.debacle.us/2017/09/how-to-graybox-blockout-3d-video-game.html | Robert Yang (Radiator blog) | not stated | Graybox steps: a floor plane, human-scale references everywhere, fast blocks, playtest early, annotate what each block means and which sizes are fixed. **Greybox.** | the shell blockouts for I1-I4 before any art |

Searched but not used as a source: annotated top-down maps of these exact levels. None was found that the pages
themselves host (Mapcore's Titanfall 2 "Effect and Cause" breakdown returned 403). The diagrams above are mine.

---

## 8. Notes for the other roles

**WRITER**
- Needs these lines:
  - the clipped radio at E2;
  - the PA dying at the drainage grate;
  - one line from Rook's crew at E1 (they think the Authority is a joke);
  - nothing during I3 and the reveal (silence is the build-up);
  - one Hawkins line when the lift arrives.
- The security merc's body in the culvert is the "what happened here". Give him a name from the binder (a hand from
  the plant) so the PA roster can mention him earlier.
- Tell me whether the company's mercs are friends (E2) or rivals. My layout works either way, but the barricade
  facing the drainage needs a reason.

**DIRECTOR**
- Five frames need framing:
  1. the dock gate (tower hidden);
  2. the spine bend s=7696 (tower over roofs);
  3. the sluice silhouette against red;
  4. the lift slit windows (survey);
  5. the catwalk.
- The sluice gate is a frame inside a frame: keep the beacon the only saturated colour in I3.
- The drop pod streaks at E4 must cross the sky in front of the tower, not behind it.

**ENGINEER**
- The drainage culvert is now on the critical path. drainage.py should place it from the plant to the cooling basin, with a
  384 x 320 section and a 768-wide sluice chamber.
- The E4 terraces need risers of 160/200/240 UU with a stair cut-in at <= 24 UU risers and a switchback at <= 12 %.
- Please keep cover-scale relief (knolls, banks >= 64 UU) through cut/fill in arena footprints. Grading is what
  dropped LEVEL from 0.93 to 0.69.

**ARTIST**
- Official versus improvised in every arena:
  - E1: company containers against smugglers' tarps;
  - E2: company barricade against laundry carts;
  - I2: stamped machines against patched panels.
- Darken the dead ends, warm the route lamps, and use one "go" colour (the orange door band) on every exit door of
  every arena.
- The interiors use TutA's own textures and trims (remix rule). Hunyuan or cards only outside the playable footprint.

**ALL**
- Re-score with `codirect.py` on the **graded** heightmap.
- Greybox the 4 shells and the 6 arenas before any art pass ("whole shape first").
- The pilot run waits until the GPU is free.
