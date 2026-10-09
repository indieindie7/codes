# Avalon redesign: the ARTIST (2026-10-09)

Role (codirect.py): the look. Silhouettes, shape language, materials, palette, wear and history, the
figure-ground grain, the believability metrics (IMP/HIER), and the detail budget by rank.

Playtest swap in force: no images generated, no GPU/game/editor/pilot runs. Everything below comes from
the code, the binder, the marks (Shot00048, Shot00065, Shot00075 looked at), the round-2 paint-over
`round2/k_sun_window.png` (the user's chosen Aztec crane-temple), `islands/concepts_board.jpg`, and web
references (the mood board in section 8; nothing downloaded; the references inform the design and the art never ships).

Read with: `binder/parti.json` ("The company holds the high ground; the town lives in its shadow and its
smoke"), `tools/palette.py`, `tools/build_parts.py`, the user's taste notes (Aztec-dystopian, Y2K,
peak frame, Sam Hyde whole-shape-first, Unreal character art, couture ornament-on-dark).

---

## 0. What the current build says (the critique first)

From the marks:
- **Shot00048** (3D primitives, 10-08 00:01): the shapes are right but every mesh reads as one flat
  grey-green clay. There is no value separation between body, trim and accent. The crane is a "fishing
  pole": a single thin line with no lattice and no counterweight. The bases float.
- **Shot00075** (storm, "oh nice"): the storm mood works and the tall stack with a yellow band reads well.
  But (a) **every shack has the same orange rim**, so the shanty reads as a box of identical toys
  instead of scavenged housing; (b) the **cone towers with a red dome and two windows over a door read as
  faces** (pareidolia: ghost heads), which is funny at a glance and wrong for dread; (c) the hill has no
  terraces under the buildings, so the buildings sit on the slope like pieces on a board.
- **Shot00065** (the deck under the overhang): pure black. In silhouette terms this is the peak frame's
  "dark frame", and it should stay dark. But the frame needs **one value edge**: a lit rail, a lamp, or a
  wet floor catching the sky. Otherwise it reads as missing geometry, not as shadow.
- **k_sun_window (round 2)**: the target. A stepped, battered-wall temple mass on high ground with
  **rust-red domes repeated at three sizes**, crane jibs and ore cables grafted on top, a low sun, and
  the town flattened and quiet below. Everything in this proposal pulls toward that frame.

The whole-shape verdict (squint test): the island today has **no dominant mass and no grain contrast**.
The company, the works and the shanty are made of similar-sized boxes in similar values. The fix comes
before any detail work: one big stepped mass, a coarse grain for the company, a fine grain for the shanty,
and one value plan.

---

## 1. Shape language guide

### 1.1 The three families (one kit, three characters)

| family | owner | silhouette rule | angle words | motif |
|---|---|---|---|---|
| **Company temple** (Liandri core, high ground) | liandri | **battered walls** (8-12 deg batter, talud), **stepped terraces** (3-5 tiers, each tier 0.7-0.8x the one below), heavy **overhanging slabs** (tablero) at each step, **one ceremonial stair cut into the mass** on the axis, **machinery grafted on top** (crane jibs, cable heads, domes) | wide base, heavy, horizontal bands, symmetric on the axis, broken only by the machines | **the sphere/dome** in rust-red at 3 sizes (tower domes 12 m, spherical tanks 6-9 m, lamp globes 0.6 m) |
| **Works** (plant, shore plateau) | liandri | **function first, Becher typology**: sawtooth halls with heavy slabs, stacks with bands, hyperboloid cooling towers, silos on legs, pipe racks. Every shape is explained by a process. **One straight ore line (the datum)** runs through it all | long, low, repeated, rhythmic (bents, pylons, teeth) | **the band**: dirt band at the foot, grey coping, orange or yellow ring on stacks |
| **Shanty** (decline, downwind) | nobody | **company prefab turned into housing by additions**: the same 4 m panel, but tilted 3-8 deg, stacked off-grid, with pitched and lean-to roofs, stilts on slopes over 14 deg, and overhangs over the path | small, jagged, fine-grained, leaning downhill, never symmetric | **the patch**: one scavenged panel of a different colour per hut (a company rust-red or orange door used as a wall) |
| **Authority** (the tower, the pad, the checkpoint) | authority | **vertical and thin**: a shaft, an antenna, a disc pad. Older than everything, rectilinear, **no batter**: the Authority builds straight up because it has no land | tall, narrow, cold, lonely | **the antenna**: guyed masts, red aviation lamps, a single cyan window strip |

The parti's two towers must not be the same shape. The Authority tower is a **vertical stalk**; the
Liandri crane-temple is a **broad stepped mass**. When both are in a frame, the eye reads "old thin
government / wide new company" without words. (See the note for the writer in section 9 on which one is the
"hero" in parti.json.)

### 1.2 Rules that make it read as Aztec-dystopian, not as a pyramid theme park

1. **Battered base, vertical top.** The temple mass is battered up to the last terrace, and the machine
   house on top is vertical and boxy (the Colegio Militar move: archaeological mass, modern box on it).
2. **Steps are habitable.** Every terrace is a real deck with a parapet, lamps, doors and cranes. No
   decorative steps. The terraces are the town's "upper streets".
3. **One stair, on the axis, cut in.** The stair is cut *into* the battered face (the company_gate beat:
   "smallness - battered wall, stair cut-in"). It is 4-8 m wide, has landings every 3.4 m of rise, and
   lamps on both cheek walls. The Ur ziggurat's three converging flights are the variant for the main
   gate.
4. **Framed panels (tablero) carry the ornament.** The flat panel over each talud holds the dense
   detail: vents, rivets, pipe runs, a stencilled LIANDRI number. The talud stays plain and dark (the
   couture rule: dense ornament on a simple dark ground).
5. **Machines break the skyline, not the walls.** Cranes, cable heads, domes, antennas and stacks only
   on top. The walls stay quiet.
6. **No faces.** Never two windows over a door on a narrow cone or tower. Offset the openings, or use a
   horizontal window strip.

### 1.3 Y2K-era layer (Unreal II, 2003)

- **Chrome and bevel, rarely**: one polished metal element per landmark (the crane cab, the dome ring,
  the dropship) to catch the low sun. The Y2K signature is the glint, not the surface.
- **Bold team colour + a loud wordmark**: the company's identity is a big stencilled **LIANDRI** wordmark
  and a number on the temple's top box, readable from the window (the BattleBots/UT "one loud graphic"
  rule). Orange = Liandri. Slate blue + cyan = Authority/TCA.
- **Visible mechanism**: counterweights, sheaves, cable drums, pistons, pocketed (holed) lattice plates
  on the cranes. Function shown openly is the era's ornament.
- **Cables and hum (Lain)**: power lines between pylons, sagging cables across the shanty lanes, and the
  hum on the soundscape. Cables are the shanty's ornament.
- **Threat display (plumes)**: the plant "grows its silhouette" when the line runs: steam plumes on the
  cooling towers, a flare on the rig, and the crane jibs swinging. It looks dead when the line stops.

### 1.4 Silhouette tests (the artist's checks, all CPU-only from the layout + sheets)

- **Skyline signature per district** (threshold the dusk frame at 50 % grey): core = stepped mass + jib +
  domes; works = sawtooth + stacks + hyperboloids; shanty = fine jagged saw of pitched roofs + poles;
  Authority = one shaft + antenna. If two districts give the same skyline profile, one of them is wrong.
- **Grain** (figure-ground, drawings.py): company footprints 25-60 m, works 15-40 m, shanty 5-8 m.
  A district's median footprint must differ from its neighbour's by **at least 2x**. This is a cheap
  artist score to add next to IMP/HIER.
- **One-good-frame**: from the command-room window (compose.py), the frame must pass the 3-value squint:
  dark frame (window + deck) / mid (town) / light (sky + sea), with the hero's top crossing the skyline.

---

## 2. Material and palette guide

### 2.1 The measured 8 colours stay as the base

`palette.py` is right about the proportions (bodies 55 % charcoal/steel, trim 25 % grey, accent 10 %
rust-red, dirt bands brown, orange small). The problem in the game isn't the hues. It's that **the parts
use the palette per part, not per value role**, so in vertex light everything compresses to mid grey.

Value roles (on every company building):
- **Body (55 %)**: charcoal/steel. Dark.
- **Trim (25 %)**: grey coping, slabs, platforms. Mid. It must be **at least 2 value steps** above the
  body (it is today, #4f4b4a vs #8f8c89. Keep that gap and don't lift the body further).
- **Accent (10 %)**: rust-red block, off-centre, one per facade. Never centred, never two.
- **Signal (< 3 %)**: orange doors and stripes. Company property only.
- **Light (< 2 %)**: glow.

### 2.2 Proposed changes (my recommendation: extend to 12 stripes)

The palette is missing three jobs: **the Authority's colour**, a **cold light**, and a **hazard
yellow**. It also lacks a **soot** darker than the lifted charcoal, for stains (charcoal had to be lifted
for vertex light, so stains now have nothing darker to use).

Add four stripes (Pal.tga becomes 12 column stripes; engineer's call, see section 9):

| name | linear rgb | sRGB | use |
|---|---|---|---|
| `slate` | (0.105, 0.135, 0.165) | #5b6670 | the Authority/TCA body: tower trim, checkpoint, pad markings; under the warm sun it reads as old steel, in shade as blue |
| `cyan` (emissive) | (0.25, 0.85, 1.0) | #8cefff | **cold light**: CRT screens, the Authority's single lit window strip, the command-room consoles, the Atlantis dropship |
| `hazard` | (0.55, 0.38, 0.03) | #c4a530 | yellow-black hazard stripes: crane hooks, grate edges, stair nosings, the bridge cranes inside the halls (the arena-hazard taste) |
| `soot` | (0.030, 0.027, 0.026) | #302e2d | stains only (stack tops, under vents, burnt-out shacks); never a body colour |

**If the 8 stripes must stay** (fallback): replace `steel` with `slate` (#5b6670). The company's
secondary walls go a hair cooler, which still reads as steel under the 136-degree warm sun. The
Authority gets its colour, and the other three jobs wait.

Rules for the user's "blue buildings with an orange stripe on top" (Round2 DormPod): this becomes the
**company dorm pod livery** only. Body `slate`, roof band `orange`. That gives the boom-era housing its
team colour. The shanty may reuse a blue panel, never a whole blue hut.

### 2.3 Emissive and accent rules

- **Warm glow (`glow`, sodium-orange) = the company.** Lit strips, door lamps, road lamps, terrace
  lamps. The plant at dusk is a warm grid. Spacing: road lamps 40 m (clutter.py has this), terrace lamps
  every 8-10 m along parapets, a door lamp over every lit door.
- **Cold light (`cyan`) = the Authority and screens.** At most one lit cyan strip per Authority building,
  plus the screens inside. The tower is "the tallest and poorest": mostly dark.
- **Red aviation lamps** (`rustred` geometry + a red dynamic light, or `glow` tinted): on every structure
  over 30 m (the Authority tower, the temple top, the mast, the crane jib tip, the stacks), blinking at
  about 1 Hz and out of phase. At dusk the skyline is drawn by these points (the concepts board shows it on the
  lattice mast).
- **Shanty light**: warm, irregular, low. String lights (small `glow` beads on a cable), one bulb per
  doorway, a drum fire. **Never a lit strip.** Lit strips are company tech.
- **Orange (signal)**: company doors, frames, a road dash, the pad markings. **The shanty never gets
  orange rims** (Shot00075). At most one scavenged orange door per 5 huts.
- **Hazard yellow**: only where the player or an NPC can get hurt or must look (edges, hooks, moving
  machines). This makes yellow a gameplay channel; see the note to the level designer.

### 2.4 Wear and history (what wear means, by direction and by age)

- **Directional weathering**: the storm wind is WIND = (0.83, -0.55). On **windward faces**, the
  `brown` share goes up by 0.15 and the rust streaks go under every opening. On **leeward faces** there
  is soot at the vents. **Sea-facing faces** get salt bleaching (one panel in 6 is `grey` instead of the
  body colour).
- **Drip streaks**: a `brown` vertical strip of 0.3 x 1.5 m under every window sill, vent and roof
  edge. B_wall already does this (drain streaks). Generalise it.
- **Traffic wear**: the dirt band is 1.2 m high at doors and 0.6 m on blank walls (people and carts
  rub the walls near doors).
- **Age rings** (binder layers):
  - **core** = *patched*: 1 in 4 panels is a different shade, plus bolted repair plates;
  - **boom** = *uniform*: one shade, clean edges, the newest lamps;
  - **decline** = *missing*: holes (charcoal), dead lamps, soot, a lean.
  `wall_panels()` does holes and rust from `wear`. It needs a `layer`-driven "patch" mode as well
  (section 6).
- **Abandoned = dark AND green**: moss/plant tufts at the foot (Völklingen), one roof panel down, doors
  open (a dark rectangle, not orange).

---

## 3. Per-district art direction

Detail budget by rank (share of unique parts/triangles in the view, for all districts):
**rank 1 hero 35 %**, **rank 2 district landmarks 25 %**, **rank 3 support 25 %**, **rank 4 infill 15 %**.
Rank 1 gets unique silhouettes and three scales of detail. Rank 2 gets one signature part. Rank 3 gets the kit plus one accent.
Rank 4 gets the kit plus additions only, and never a unique part.

### 3.1 Company core (high ground: the temple, plant office, store, mess, dorms, director)

- **Landmark**: the **Liandri crane-temple** (round-2 CraneTower) on a **30 m battered plinth** that
  replaces the floating base (Q33 lesson). It has 3 terraces, a machine-house top with the LIANDRI wordmark,
  two lattice jibs (not poles) with counterweights, rust-red domes at three sizes, ore cables leaving
  toward the works.
- **Ground**: everything here sits on **terraces with battered retaining walls** (B_wall plus a battered
  variant). Terrace risers are 3.4 m, the "datum" stair climbs them.
- **Materials**: charcoal battered concrete, grey coping, rust-red framed panels, orange doors, warm
  glow. The plant office stays "the only clean concrete": `pale` body, wear 0.05, a cyan-free window strip
  toward the sea.
- **Light**: the brightest district at dusk. A warm grid of terrace lamps.
- **Value**: dark masses with lit edges.
- **Signature**: the stair cut into the plinth at the company gate.

### 3.2 Works (shore plateau: halls, silos, cooling towers, tank farm, generator, pumps, rigs)

- **Landmark**: the **cooling towers** (parti "second"). They must be **pale** (the only light grey
  bodies on the island), so in the window frame they're the brightest mass and carry the steam.
- **Datum**: the **ore line**, straight, conveyor towers every 60 m (B_ctower and B_cable exist). Everything
  else is irregular against it.
- **Rhythm**: pipe-rack bents every 6 m, pylons, sawtooth teeth. The Becher typology: each type
  repeats with variation, never as one copy.
- **Materials**: rust-red silos and tanks, charcoal halls, pale sawtooth glazing (lit faces glow when the
  line runs), hazard yellow on cranes, gantries and hooks.
- **Wear**: windward rust. The dead hall C has missing teeth, moss and open roller doors.
- **Motion**: steam (cooling), smoke (generator stack), a flare (rig), cable buckets moving.

### 3.3 Shanty (Tin Row, Ship Row, the summit ring: downwind, in the smoke)

- **Character**: "one kit, two characters". Built from the *same* 4 m company panels, reused. The
  grain is fine (5-8 m). Huts step down the slope on stilts above 14 deg (engineer E17). Roofs overhang
  the lanes. Lean-tos everywhere.
- **Colour**: charcoal/brown/steel mix, **one patch panel per hut** (rust-red, slate, or a stencilled
  company panel hung upside down). No uniform orange rims.
- **Ornament**: **laundry lines, cables, antennas, drums, plant pots**. This is where the couture rule
  lives: a dense, small, repeated motif (laundry flags in 3-4 faded colours) over a dark simple ground.
- **Light**: warm, irregular, low, many small sources. The Tin Bar is the brightest point (a string of bulbs).
- **Wear**: high (0.75-0.9), soot under stove pipes, sagging roofs. **Lived-in, not dead**: open doors
  show a lit interior colour (a curtain).
- **Landmark (LD6)**: a **water-drum tower** (stacked drums on a scaffold, 2x the median hut height), or
  the wreck patio for Ship Row.

### 3.4 Authority (the tower, the pad, the checkpoint)

- **Character**: neglected government. Straight concrete gone grey, **slate** trim, one cyan window
  strip, a red aviation lamp, a guyed antenna, peeling stencils ("TCA" and a sector number).
- **Wear**: 0.45-0.5, but *the dull kind*: dirt and dead lamps, few holes. Neglect, not decay.
- **Light**: dark. One cyan strip, the pad's 4 corner lamps (2 dead), the aviation lamp.
- **The pad**: the old Atlantis dropship sits there, and a fuel hose lies across the pad. The company's
  docking-fee sign is stencilled in orange on the pad edge (company graphics on government ground).
- **Checkpoint**: a hut, a barrier arm in hazard stripes, a lamp, a log on a clipboard.

---

## 4. Interior art direction sheets

Common rule: **every light has a fixture you can see** (a tube, a bulb, a screen, a window). That gives
the rebake a reason (Q5/Q47/Q49) and makes the darkness read as shadow, not missing light. One warm and one
cold source per room at most, plus daylight.

### 4.1 Command room (the Authority tower: TutA's room and window)

- **Role in the story**: the player's home. It looks out on the company's town (compose.py window frame).
- **Materials**: slate-blue painted steel panels, charcoal floor with a scuffed path to the consoles,
  pale ceiling tiles (2 missing), a chrome window frame with a soft glint (Y2K).
- **Props**: 1970s-style console banks (the Trafford Park/Gravelines panels: rows of meters, toggle
  switches, a mimic diagram of the island's power line), 3 CRT monitors (cyan), Oduya's **traffic board**
  (a magnet board with ship and dropship tags), a radio set with a handset on a coiled cord, a coffee
  maker, mugs, a pinned paper map of the island with company-drawn changes in orange marker, logbooks,
  a dead plant.
- **Light**: the window (warm, low sun) as the key; the cyan screens as fill; 12 recessed floor corner
  lamps (Q31, already in) as the warm edge. **No overhead light on**: one tube hangs dead.
- **Wear**: taped cables across the floor, a cracked screen, a bucket under a leak (the rain-indoors
  bug becomes a story prop once NoRain[] fixes the real rain).
- **Frame**: the window mullions must not cross the hero. The deck outside must not hide the plant below
  4 degrees (the lesson in u2avalon-project).

### 4.2 Catwalks and decks (the peak frame: "dark frame -> grated catwalk -> lone silhouette at dusk, rain")

- **Materials**: open steel grating (charcoal) with a visible gap pattern (light comes up through it);
  rails 1.1 m tall, mid-rail, toe board in **hazard yellow** on the edge; posts every 2 m; bents every
  6 m.
- **Light**: a sodium lamp on every second bent (warm pool on the wet grating). An aviation lamp at the
  far end. Rails **lit from behind by the sky**: the rail is the leading line, so it must stay the
  brightest thin line in the frame (fix for Shot00065).
- **Props**: a fire hose cabinet, a cable tray under the deck, a chained gate, a fallen sign.
- **Wear**: rust bleeding from every bolt, puddles, birds (motion).
- **Figure**: one lone NPC at 40-100 m at the rail (parti beat 4).

### 4.3 Processing halls (A, B; C dead)

- **Materials**: concrete floor with painted walkways (yellow lines, orange "keep clear" hatch), steel
  columns with rust collars at the base, the **sawtooth clerestory** (north-light glazing) letting in
  shafts of dusty light.
- **Props**: a **bridge crane** across the whole hall (hazard-yellow girder, a hook block with a
  chain), a conveyor at 1.2 m height on stands, ore piles (brown/rust), chutes, a control cab on stilts,
  lockers, hard hats on pegs, a shift board.
- **Light**: daylight shafts from the teeth (the lit teeth outside are the same faces from inside),
  high-bay warm lamps every 8 m, a red warning beacon at the crane.
- **Wear**: hall A patched (mixed panels inside too), hall B clean, hall C: teeth missing, rain falling in
  through the holes (here it's correct), puddles with sky reflections, moss on the floor.
- **Arena role**: columns and ore piles are cover; the crane cab and catwalks are the high spot (LD5).

### 4.4 The mess (the one social room)

- **Materials**: tiled lower walls (pale, cracked), painted upper walls, a linoleum floor worn into
  paths between the hatch and the tables.
- **Props**: long tables in rows with benches (mismatched chairs at the ends), steel trays, a serving
  hatch with a roller shutter, a **menu board priced in scrip**, a ceiling-bracket CRT TV, Haldane's
  "unofficial" bar at the back (bottles on a plank shelf, a curtain, a warm bulb), notices about the
  Thursday power cut, a PA loudspeaker horn.
- **Light**: fluorescent tubes (cold-white, one flickering) over the tables; the bar's warm bulb. Two
  colour temperatures in one room = company vs. people.
- **Wear**: chipped tables, a tray stack, a mop bucket, condensation streaks on the windows.
- References: the 1954 Caerau Colliery canteen and Harold White's Lynemouth canteen (section 8).

### 4.5 Dormitories (dorm, dorm B, dorm C abandoned)

- **Materials**: steel-plate walls painted slate (boom) or pale green-grey (core era), a concrete floor,
  a window strip on both long sides.
- **Props**: **triple bunks** (the offshore platform layout: up to 12 men a cabin in the early years),
  lockers, personal curtains on the bunks (the only colour: printed fabrics, pin-ups, a flag), boots,
  heaters, laundry lines across the room, a kettle.
- **Light**: corridor fluorescent (cold); bunk reading lamps (warm, a few on); daylight through the strip.
- **Dorm C abandoned**: mattresses rolled, lockers open, a calendar stopped on a date, dust, glass on the
  floor (Hashima's left-behind rooms, Andrew Meredith's interiors).
- **Ornament**: the curtains are the dense motif on a dark simple ground.

### 4.6 Shanty interiors (Tin Bar, huts)

- **Materials**: company panels reused inside out (stencils show backwards), carpets on the floor,
  corrugated sheet ceilings, plastic sheeting.
- **Props**: a stove with a pipe through the roof, drums, a card table, home-still copper, crates as
  chairs, a radio, a curtain for a door, string lights, family photos.
- **Light**: string lights and a bulb, warm; a stove glow.
- **Tin Bar**: two huts knocked into one. The seam shows (two roof pitches, a beam where the wall was).
  The only room where a hand and a marine sit at one table: one company chair and one Authority chair.

### 4.7 Drainage (storm drains under the terraces: the LD7 quiet stretch)

- **Space**: a culvert network under the terraces that ends in a **pillared hall** (a small G-Cans: square
  concrete pillars 2 x 4 m on a 12 m grid, 10-14 m high) and a **sea outfall** with daylight at the end.
- **Materials**: wet concrete with a dark tide line at 1 m, algae (`brown` plus a green tint if added),
  formwork marks, steel ladders, hazard-striped sluice gates.
- **Light**: shafts down from grates in the terrace streets above (cold daylight or warm lamp light
  depending on the street), a few caged bulbs (one in three dead), the outfall's bright end (compression
  -> release, the peak-frame rule underground).
- **Sound**: dripping and the hum of the pumps (Lain hum).
- **Props**: a pump room with valves (hazard yellow hand wheels), debris washed down from the shanty
  (drums, a sandal, plastic), graffiti tally marks.
- **Gameplay**: the quiet stretch (25-60 s) that ends in the pillared hall. Pillars are cover, and the
  staged reveal happens there (Unreal 1 first-Skaarj recipe).

---

## 5. New parts the build_parts kit needs

All metres. Origin at the bottom centre, front = -Y (as the kit does now). Palette names from section 2.

| part | dimensions | notes |
|---|---|---|
| `B_talud` battered wall panel | 4.0 w x 3.4 h, 1.2 m thick at foot, 0.6 at top (batter ~10 deg) | charcoal, grey coping 0.3, dirt band; the temple and terrace faces; tiles along a terrace edge |
| `B_tablero` framed panel | 4.0 w x 1.7 h x 0.5 deep overhang, with a 0.15 frame | sits on a talud; the ornament carrier (vents, rivets, a stencil number); rust-red infill on 1 in 4 |
| `B_terrace` step block | 10.24 x 4.0 x 3.4 (one heightmap cell long) | the terrace riser (B_wall's taller, battered sibling) with a parapet 1.1 m and a lamp socket every 8 m |
| `B_stair` cut-in stair | 4.0 or 8.0 w; flight rise 3.4, 18 risers of 0.19, treads 0.28 (run 5.0); landing 2.0 deep; cheek walls 0.6 thick | hazard-yellow nosings; lamps on both cheek walls; variant `B_stair3` = the Ur triple flight for the company gate |
| `B_dome` | 12 m dia hemisphere on a 1 m ring; plus `B_sphere` 6 / 9 m dia spherical tank on 6 legs + a skirt | rust-red with a grey ring; the motif at three sizes. 16-24 sides, low-poly |
| `B_jib` lattice crane | mast 3x3 m section x 24 m; jib 2 m triangular lattice x 30 m; counter-jib 10 m + 4x2x2 counterweight; cab 3x2x2.5 | charcoal lattice, hazard-yellow jib tip, orange cab, red aviation lamp at the tip; **replaces the fishing poles**; hook block with a 0.8 m hook, cable 0.1 |
| `B_bridgecrane` (interior) | span = hall W - 1; girder 1.2 x 1.0; end trucks 2 m; hook drop 4 m | hazard yellow; for halls |
| `B_catwalk` | 1.2 w x 4.0 long grating 0.08 thick; rails 1.1 h, mid-rail 0.55, toe board 0.15 | grating as alternating bars (charcoal) + gap; hazard toe board |
| `B_stairtower` | 3.0 x 5.0 footprint, 3.4 m per flight, cage of 0.15 posts | for halls and the temple terraces |
| `B_rackbent` | 6.0 w x 5.0 h, 2 tiers (2.8 / 4.6), columns 0.3 | pipe-rack bent every 6 m (rhythm); pipes as separate 0.3/0.5/0.8 cylinders |
| `B_stack` | 2.5 dia x 30 m, a ladder, 2 bands (orange + grey) at 0.85 h, soot top 2 m | red aviation lamp |
| `B_lamp_sodium` | 8 m pole 0.15, arm 1.5, head 0.6 x 0.3 | glow head; for roads and terraces (replaces Mission_03M LampPost01 where it clashes) |
| `B_aviation` | 0.4 dia globe on a 0.6 bracket | red emissive + a blinking light actor |
| `B_container` | 6.06 x 2.44 x 2.59 (ISO 20 ft) | ribbed sides (4 ribs per m faked as 8 boxes), door end with bars; colours rust-red/slate/charcoal; the dorm annex + shanty bases |
| `B_shack` panel kit | panel 1.0-1.2 w x 2.4 h, corrugated look (5 thin boxes); roof sheet 1.2 x 3.0 | random tilt ±4 deg; for assembling huts from scavenged panels |
| `B_leanto` | 3.0 w x 2.5 d x 2.6/2.0 h (mono-pitch) | replaces the scaled B_shed_a lean-tos |
| `B_stilts` | platform 5 x 7, posts 0.2 dia at 2.5 m spacing, length to the ground (pivot top) | shanty on slopes over 14 deg; cross-braced |
| `B_laundry` | a 6 m line, 4-8 cloth quads 0.6 x 0.8 | 3-4 faded colours (needs the palette extension or vertex colour); motion later |
| `B_drumtower` | scaffold 3 x 3 x 9 m, 6 drums 0.6 dia x 0.9 | shanty landmark (LD6) |
| `B_grate_hazard` | 2 x 2 x 0.1 | floor vent with yellow/black stripes; the arena-hazard grammar |
| `B_pillar` (drainage) | 2 x 4 x 12 m with a 0.3 chamfer, tide line band | the pillared hall |
| `B_culvert` | box 4 w x 3 h x 10 long, 0.4 walls | drainage runs |
| `B_console` (interior) | 2.0 w x 0.8 d x 1.1 h, a sloped desk + an upright meter panel 1.8 h | slate, cyan screens, meter dots |
| `B_bunk3` | 2.0 x 0.9 x 2.4 (3 tiers) | with a curtain quad |
| `B_messtable` | 4.0 x 0.8 x 0.75 + 2 benches 4.0 x 0.3 x 0.45 | |
| `B_signboard` | 6 x 2 m panel with a stencilled LIANDRI wordmark (texture or boxes) | the loud graphic; on the temple top and the dock gate |

Changes to existing builders:
- `wall_panels()`: add a **layer-driven patch mode** (core: 25 % of panels swap to a neighbour shade +
  bolted plates) and **directional wear** (windward faces get +0.15 wear; needs the building yaw and WIND).
- `building()`: **plinth always**. A 0.6-1.5 m battered plinth under every walled building, down to the
  lowest ground under the footprint (fixes "bases floating", Q26/Q28).
- `door()`: orange frames **only if the owner is liandri**. Authority doors get slate frames, nobody
  doors get no frame (a dark hole + a curtain quad).
- The cone/tower builders: **no window pair over a door** (the face problem).

---

## 6. Keep, cut, add

**Keep**
- The 8 measured colours as the base, and the body/trim/accent proportions.
- The Hunyuan pattern: dirt band at the foot, grey coping on top, off-centre rust-red accent.
- The sawtooth hall with its heavy 1.5 m overhang slab; B_ctower + B_cable (the ore line as the datum).
- The dorm's container annex ("the annex nobody planned"): the seed of "one kit, two characters".
- The round-2 CraneTower concept as the company landmark, on its 30 m plinth.
- The storm, the parallax clouds (mark Q52), the yellow-banded stack, the rig flares.
- IMP/HIER targets (IMP 0.74-0.88 and HIER 0.88-0.94 on Town6/Town7 are good; hold them).

**Cut**
- Orange rims on shanty huts (Shot00075).
- Window-door "faces" on the cone towers.
- Imposter cards within ~1.5 km. Cards only for far islets.
- "Fishing pole" cranes, and mirrored duplicate cranes (Q51 did part of this).
- The untinted grey-green clay look: every 3D prop must take the palette roles, never one colour.
- Generic Mission_03M scaled wall slabs (already disabled).

**Add**
- Battered plinths and terraces under the company; the cut-in stair at the company gate.
- The sphere/dome motif at three sizes; lattice jibs with counterweights.
- Red aviation lamps on everything over 30 m; sodium terrace lamps.
- The palette's slate, cyan, hazard and soot (or slate alone as the fallback).
- Laundry, cables and patches in the shanty; a drum-tower landmark.
- A LIANDRI wordmark on the temple top and the dock gate.
- Directional weathering and age-ring wear.
- The grain score (company vs shanty median footprint >= 2x) next to IMP/HIER in metrics.py.

---

## 7. Believability and figure-ground (the artist's metrics)

- **IMP**: keep the targets (yaw spread 3-8 deg, setback CV, party walls). Add a rule: **the company
  district runs IMP low on purpose** (aligned on the axis, symmetric, a "pattern language inverted in
  the company zone", parti `ordering`), and the shanty runs it high. Score IMP per district: company
  0.3-0.5, works 0.5-0.7, shanty 0.8+.
- **HIER**: fine as is. The old core near the dock is honoured by the age-vs-distance term.
- **Grain** (new): median footprint by district, a ratio >= 2x between neighbours; figure-ground
  black share in the shanty 45-60 %, company 25-40 % with large open terraces (the Nolli plan shows the
  terraces as public white).
- **Detail by rank** (new, cheap): count the parts per building in the export and check the 35/25/25/15
  split within the window frame.

---

## 8. Mood board (25 web references, grouped by use)

Each entry lists the page, the source and the licence (as stated on the page or in the search
result; "not stated" = assume all rights reserved), what fits, and where it's used. **Reference only:
nothing is downloaded, nothing is traced or copied into textures, none of it ships.**

### A. The company temple (shape language, landmark)

1. **Heroico Colegio Militar, Mexico City (1976)**: Agustín Hernández Navarro with Manuel González Rul.
   Pages: https://en.wikipedia.org/wiki/Agust%C3%ADn_Hern%C3%A1ndez_Navarro ;
   https://archive.pinupmagazine.org/articles/interview-agustin-hernandez-sci-architecture-mexico-suleman-anaya .
   Licence: Wikipedia text CC BY-SA; photos per file; PIN-UP not stated.
   Fits: **the exact brief**: a concrete brutalist campus planned as a pre-Columbian ceremonial centre
   (Teotihuacan, Monte Albán); battered masses with modern boxes on top. It's said to have inspired
   Blade Runner, and Total Recall was filmed there. Silhouette, material (board-marked concrete), mood.
   For: the Liandri crane-temple, the company core plan, the company gate.
2. **Tikal Structure 5C-49, talud-tablero**: Uncovered History.
   https://uncoveredhistory.com/guatemala/tikal/tikal-talud-tablero-temple-5c-49/ . Licence: not stated.
   Fits: the **talud (sloped) + tablero (framed overhang) profile**, the module for `B_talud`/`B_tablero`.
   For: terrace faces, temple tiers.
3. **Pyramid of the Sun, Teotihuacan**: World History Encyclopedia image page.
   https://www.worldhistory.org/image/3631/pyramid-of-the-sun-teotihuacan/ . Licence: check the page
   (WHE images are often CC BY-NC-SA).
   Fits: terrace proportions (222 m base, ~70 m high, levels joined by stairs), the scale of a mass you
   climb. For: the plinth and terrace stepping ratios.
4. **Ziggurat of Ur**: Wikipedia (lead photo of the reconstructed façade and staircase).
   https://en.wikipedia.org/wiki/Ziggurat_of_Ur . Licence: CC BY-SA text; the photo per its Commons file.
   Fits: **three monumental stairs converging on a gate**; battered brick mass; bullet-marked walls
   (history on the surface). For: `B_stair3` at the company gate (beat "smallness").
5. **Sci-fi Planetary Mining Installation**: r_bago on ArtStation.
   https://r_bago.artstation.com/projects/Nq1Jog . Licence: not stated.
   Fits: machinery (a mining laser on twin cranes) **grafted onto a brutalist megastructure**, built on
   oil-rig/fracking structure, with Aliens-scale industry. For: the crane-temple's top, the jibs.

### B. The works (typology, process made visible, rust)

6. **Bernd and Hilla Becher, industrial typologies**: Smarthistory essay.
   https://smarthistory.org/?p=66679 (gallery: https://fraenkelgallery.com/artists/bernd-and-hilla-becher ).
   Licence: Smarthistory text CC BY-NC-SA; the photos are © the estate.
   Fits: water towers, cooling towers, winding towers, gas tanks as "anonymous sculpture": **one type,
   many variants, form dictated by process** ("a body without a skin"). For: the kit's variation rules,
   silos, water tower, cooling towers, the Becher grid as a silhouette check sheet.
7. **Zollverein Shaft XII**: Baukunst NRW.
   https://www.baukunst-nrw.de/en/projects/Objekt-Highlight--183.htm . Licence: not stated.
   Fits: cubic functional volumes, exposed steel frame with brick infill, **one dominant winding tower**
   as the works' landmark, everything concentrated on one line. For: hall B, the generator house, the
   works' ordering around the datum.
8. **Völklingen Ironworks**: ERIH.
   https://www.erih.net/i-want-to-go-there/site/world-heritage-site-voelklingen-iron-works . Licence: not
   stated. Fits: **rusted steel, charging platform catwalks 30 m up, plants reclaiming the plant**. For:
   catwalks, hall C (dead), abandoned wear (moss).
9. **Kennecott mill and company town, Alaska**: SAH Archipedia + Valdez Museum.
   https://sah-archipedia.org/node/7575 ; https://www.valdezmuseum.org/kennecott/ . Licence: not stated
   (NPS photos are often public domain; check per image).
   Fits: a **14-storey mill stepping down a mountainside**; the town painted red (the cheapest paint) with
   white trim, **the hospital the only white building**, a rail bed as the spine. For: the stepped
   company core on the slope, the clinic/plant office as the one pale building, the spine.
10. **Edward Burtynsky, *Oil***: Metivier Gallery exhibition.
    https://metiviergallery.com/exhibitions/110/ . Licence: © the artist.
    Fits: refinery architecture at landscape scale, tank farms, the colour of oil country. For: the tank
    farm, fuel depot, the works seen from the window.
11. **Edward Burtynsky, *Shipbreaking #1, Chittagong***: Remai Modern collection.
    https://collections.remaimodern.org/objects/4554/shipbreaking-1-chittagong-bangladesh . Licence: ©.
    Fits: **hulls cut open, rust in golden low light, tiny figures against huge steel**. For: the wreck,
    the dead rig, the dusk palette for rust.

### C. Company housing and the shanty

12. **Hashima (Gunkanjima), Nikkyū company housing**: PAKUTASO free stock photo.
    https://www.pakutaso.com/en/20190326079post-20005.html . Licence: PAKUTASO's free-use terms (read them
    before any use beyond reference).
    Fits: **a company mining town on a rock in the sea**: concrete dorm blocks stacked against each other,
    a sea wall, no space. The closest real place to Avalon. For: dorms, the core's density, the sea wall.
13. **Hashima interiors, Andrew Meredith**: Designcurial.
    https://old.designcurial.com/news/hashima---the-abandoned-japanese-island-4199747/ . Licence: ©.
    Fits: the Nikkyu company flats and the hospital's operating theatre: **left-behind rooms**. For: dorm C
    (abandoned), the clinic.
14. **Kowloon Walled City, Greg Girard (with Ian Lambot)**: M+ magazine.
    https://mplus.org.hk/en/magazine/exploring-kowloon-walled-city-photographic-journey . Licence: ©.
    Fits: additions on additions, cables, roof clutter, light from small sources. A known reference for
    game and film dystopias. For: the shanty's density and its cables, the summit ring.
15. **Portraits from Above: Hong Kong's informal rooftop communities**: Rufina Wu & Stefan Canham.
    https://halfletterpress.com/portraits-from-above-hong-kongs-informal-rooftop-communities/ . Licence: ©.
    Fits: **self-built huts on top of formal concrete**, documented with measured drawings: exactly "the
    company prefab turned into shanty by additions". For: shacks on the company terraces' roofs, the
    `B_shack` kit, drawings.py-style plans of a shanty block.
16. **Makoko, Lagos: living on stilts**: Ripples Nigeria (75 photos).
    https://ripplesnigeria.com/living-on-stilts-75-unforgettable-images-of-makoko-will-it-survive-sanwo-olus-smart-city-plan .
    Licence: not stated. Fits: **corrugated iron, planks and bamboo on stilts over water**. For: Ship Row,
    the old boat landing, `B_stilts`.
17. **Shanty Megastructures, Olalekan Jeyifous**: Dezeen.
    https://www.dezeen.com/2016/08/09/shanty-megastructures-lekan-jeyif-conceptual-images-lagos-nigeria/ .
    Licence: ©. Fits: **a shanty climbing a vertical megastructure** in a patchwork of corrugated metal and
    plastic. For: the shanty ring around the summit (mark 5) and shacks perched on the temple's lower
    terraces (company tissue, resident infill).

### D. Interiors

18. **Power station control room, Trafford Park**: Science Museum Group.
    https://collection.sciencemuseumgroup.org.uk/documents/aa110015087 (see also aa110015091).
    Licence: **CC BY-NC-SA 4.0**. Fits: meters, switches, a gallery wall of panels. For: the command room
    consoles (`B_console`).
19. **Gravelines nuclear plant control room**: energytransition.org, photo Serge Ottaviani.
    https://energytransition.org/gravelines . Licence: **CC BY-SA 3.0**. Fits: 1970s-onward console
    layout and colours, the mimic diagram. For: the command room, the plant office's control room.
20. **Colliery canteens**: Museum Wales, Caerau Colliery canteen and staff, March 1954 (item 2009.3/5819).
    https://museum.wales/collections/online/object/958afac8-f73f-345b-a787-f78cfa0503a0 ; and the National
    Coal Mining Museum, Harold White's Lynemouth canteen (NCB, 1950s): https://www.ncm.org.uk/?p=4405 .
    Licence: check each record. Fits: **a company canteen**: rows of tables, a serving hatch, tiled walls,
    the workers. For: the mess.
21. **G-Cans, Metropolitan Area Outer Underground Discharge Channel**: Interesting Engineering
    (photos Joe Nishizawa). https://interestingengineering.com/tokyos-futuristic-underground-flood-system .
    Licence: ©. Fits: **59 giant concrete pillars in a dim tank, light from above**: the "underground
    temple". For: the drainage pillared hall, `B_pillar`.
22. **The Nostromo, Ron Cobb**: Domus.
    https://www.domusweb.it/en/news/2025/09/19/alien-design-nostromo.amp.html . Licence: ©.
    Fits: a ship conceived as **an orbital refinery: pipes, valves, grilles and cables exposed**, plus a
    semiotic sign system. For: the interiors' signage language (a Liandri icon set for doors, hazards and
    rooms), the halls, the pump houses.

### E. Era and mood

23. **Simon Stålenhag, machines in the landscape**: CNN Style.
    https://amp.cnn.com/cnn/style/article/simon-stalenhag-sci-fi-art . Licence: © the artist.
    Fits: **huge machines as forgotten neighbours, small lone figures**, observed light and ground. For:
    the dead rig, the conveyor towers on the hills, the lone figure at the catwalk (beat 4).
24. **Serial Experiments Lain and power lines**: Atlas Obscura.
    https://www.atlasobscura.com/articles/why-power-lines-anime-electrical-infrastructure.amp . Licence: ©.
    Fits: **cables and poles as atmosphere, the hum**. Y2K, the user's own touchstone. For: power lines
    across the shanty, pylons along the spine, the hum in the soundscape.
25. **Unreal Tournament 2004 (the Liandri Archives)**: BeyondUnreal/Unreal Archive wiki.
    https://unrealarchive.org/wikis/the-liandri-archives/Unreal_Tournament_2004.html . Licence: wiki text
    per the site; game art © Epic.
    Fits: the era baseline for the **company's in-universe identity** (Liandri) and the 2003-04 Unreal
    look: bold team colours, chrome, lit strips. For: the wordmark, the signage, checking the palette
    against the engine era.

(`references.md` in this folder is the place PIPELINE.md names for the shared board. The other roles'
entries and these can be merged there.)

---

## 9. Notes for the other roles

**Writer**
- The binder's `tower` is "The Authority tower: the tallest building and the poorest", while the parti
  sentence says "the company holds the high ground" and the user's chosen landmark is the Liandri crane-temple.
  Proposal: **two towers in dialogue**. The Authority tower is the tallest (a thin vertical shaft); the
  company temple is the **heaviest and highest-standing** (a broad stepped mass on the plateau). Please
  write a sheet for the temple (`liandri_temple`: owner liandri, layer boom, kind temple, ~90 x 70 m
  footprint, 3 terraces + a machine house, users plant_staff/okafor/security) and decide which one
  parti.json's `hero` names. My vote: hero = the temple in the window frame and at the company gate;
  the Authority tower = the player's home and the dark frame.
- Give me in-world text for the graphics: the stencil numbers, the menu board in scrip, the docking-fee
  sign on the Authority pad, door icons. Writing on walls is the cheapest storytelling we have.

**Director**
- **Value plan**: dark frame (window, deck) / mid town / light sky. The cooling towers are the only pale
  bodies, so they're the brightest mass in the town; keep the hero's top above the skyline.
- **Red aviation lamps** draw the skyline at dusk; **warm sodium** = company, **cyan** = Authority. Use
  the two temperatures to split the frame (cold inside the command room, warm town outside).
- The rail on the dark deck (Shot00065) must catch the sky as a thin bright line: it is the leading line.
- The rust-red sphere at three sizes is a free eye-path: small lamp globe (foreground) -> tank (mid) ->
  temple dome (far).

**Engineer**
- Palette: going from 8 to 12 stripes touches `glb_to_ase.py` (Pal.tga stripe count + `palette.json`) and
  `part_to_ase.py`. Don't re-run glb_to_ase over existing B_*.glb (stripe order). The fallback is to swap
  `steel` for `slate` (8 stays 8).
- Batter and terraces: a 10-degree batter on 3.4 m risers is ~0.6 m set-back per riser. Retaining walls
  in real practice batter about 1:10, so the look is also sound engineering. The cut-in stair: 18 risers of
  0.19 m per 3.4 m flight with landings.
- `building()` plinth: down to the lowest ground under the footprint, capped (Q28's 15 % rule).
- Directional wear needs the building yaw and WIND = (0.83, -0.55) passed to build_parts (from the layout).

**Level designer**
- A **colour grammar** you can rely on: **orange = company door/usable path**, **hazard yellow = edge,
  hook, moving machine, danger**, **cyan = Authority/screen/info**, **warm bulbs in the shanty = people**.
  Nothing else uses these colours.
- Battered walls give **sloped cover** that the player can see over at the top of a terrace (the high
  spot, +3.4 m per terrace). Tablero overhangs make good shadowed overwatch.
- Catwalks: 1.2 m wide grating, 1.1 m rails. They're visual leading lines and also routes; keep them
  above the 45-degree walkable limit on stairs (stair towers at 3.4 m per flight).
- The drainage pillared hall is built for the LD7 quiet stretch: 12 m pillar grid, light shafts, one
  bright exit. Pillars sit 10-40 m apart along the route, matching the LD5 cover band.
- Hazard grates with yellow/black stripes are a telegraphed floor-hazard vocabulary (steam vents on the
  works floor), if you want arena hazards.
