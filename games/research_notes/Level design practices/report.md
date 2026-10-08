# Level design practices for the Avalon remake

Research notes, 2026-10-07 (research agent; saved by Claude). Purpose: give the Avalon rebuild tool (spine-street town generator, static-mesh buildings, terrain carves, live edits) a set of rules it can check, with the reasons behind them. Numbers marked **(proposed)** are defaults to tune, not published figures.

Scale throughout: **about 50 UU = 1 m** (UT2003/2004 convention: pawn half-height 88 UU). **Check U2's pawn CollisionHeight/CollisionRadius before trusting the metric tables.**

## 0. Avalon in one paragraph (the target)

"An awful patrol in a backwater place" gives three experience goals:
1. **Legibility.** From the command tower you can name every district and point to it. From the ground you always know where the tower is.
2. **Neglect.** Built cheaply for extraction, not cared for, with a history the player can read without being told.
3. **Unease.** A storm, distances you cannot cross, creatures glimpsed before they are fought.

## 1. Core principles

- **Holistic level design** (Steve Lee, Arkane, GDC 2017): every space answers what the player *does* here, what they *see*, and what it *tells* them.
- **30 seconds of fun** (Bungie, Halo): the unit is a short beat (see, approach, engage, resolve); variety comes from recombining beats in new contexts.
- **Modular kits** (Burgess & Purkeypile, Skyrim, GDC 2013):
  - the footprint is the snapping grid, and sub-kits use multiples of it;
  - one game-wide door standard;
  - walkable space at least 2 character widths;
  - pivots at the ground centre;
  - **art fatigue**: repeated hero *details* are spotted long before repeated walls;
  - postpone hero pieces;
  - stress-test the kits.
- **Architecture** (Totten): prospect/refuge, figure-ground, the Disney weenie, compression and release. Denying refuge gives anxiety.
- **Rogers**: plan a beat chart before geometry; every area has a gameplay purpose; lead the player with light, geometry and enemies.
- **Schell**: the lens of unification (one theme) and an interest curve along each main route.
- **The Level Design Book**: research → metrics → blockout → playtest → art. Players don't look up, look where they move, and look at contrast.

Checklist:
- [ ] Every district has a **verb**, a **picture** and a **fact** (the Lee test).
- [ ] Routes break into beats of ~20–60 s of walking (~10 000–25 000 UU at ~440 UU/s; check U2). No stretch longer than ~60 s without a new view, encounter or story object.
- [ ] Buildings snap to a base footprint grid; sub-kits are multiples of it; one shared door size.
- [ ] Each hero-detail mesh appears at most once per district (proposed).
- [ ] Minimum walkable width ≥ 120 UU, checked with bot pathing.

## 2. Composition and wayfinding

Lynch's five elements (*The Image of the City*), as data types:

| Element | Avalon | Rule |
|---|---|---|
| Paths | spine street, jetty road, mountain switchbacks | continuous, directional, go somewhere visible |
| Edges | coastline, terrace walls, mesa cliff, compound fence | clear boundaries that double as map limits |
| Districts | mining town, shanty, rigs, command compound, mesa | uniform texture inside, different from the neighbours |
| Nodes | plaza, jetty, lift base, gate | junctions that hold encounters and set pieces |
| Landmarks | tower (global), a crane or stack per district (local), the mesa (far) | far-visible, unique silhouette |

**Weenie** (Disney; HL2's Citadel):
- Streets terminate on a view of the tower or a landmark.
- A weenie is a destination you can see but can't yet reach.

**Leading lines and framing**:
- Rails, pipes, cables, kerbs and terrace edges point at the goal.
- Frame the goal (an arch, a gap between buildings) wherever the path turns or crests.

**Light and colour**:
- Warm light on the route, cool or dark on dead ends.
- One saturated "go" colour, used sparingly.
- Use two or more guidance aids on the critical route: light and composition alone are only ~35–60% reliable, breadcrumbs and threats ~70–93% (Level Design Book).

**Breadcrumbs**: ammo, lights, blood drips, a fleeing creature, a radio voice. Especially useful in the shanty.

**Show, hide, reveal**:
- Show the goal far away, lose it through compression, then reveal it close up from a better angle.
- Unreal 1 creature reveals follow the same pattern: signs, withhold, a staged lit reveal, then a fight in a space that teaches the creature's move.
- The command tower is Avalon's "viewpoint" survey moment.

**Vistas**: at the end of every climb, with three depth layers (foreground frame, mid district, far landmark).

Checklist:
- [ ] Every ~2 500 UU of main path, at ~150 UU eye height, the tower or a local landmark is visible, both clear and in storm fog (proposed).
- [ ] Each street segment ends on a view (landmark, lit door or vista), never a blank wall.
- [ ] One local landmark per district, at least 2× the height of its neighbours, with a unique silhouette.
- [ ] The critical route has at least 2 guidance layers, and dead ends are darker than the route.
- [ ] Every climb ends in a 3-layer vista.
- [ ] From the tower, each district can be named by shape and colour alone.

## 3. Outdoor hubs and open spaces

### 3.1 Metrics (UE2-era, ~50 UU/m; verify for U2)

| Element | Number | Notes |
|---|---|---|
| Player | half-height 88, radius ~25 | check U2Pawn |
| Eye height | ~150 UU | the camera for vista tests |
| Step-up | ≤ 24 UU | stairs: 16 UU risers |
| Stair tread | 25–32 UU | 30–35° reads as stairs |
| Stair landing | every 12–16 steps | |
| Ceiling | ≥ 83 UU walkable, 128 UU recommended | industrial 200–300 UU |
| Corridor | ≥ 48 UU absolute, ≥ 128 UU for AI and comfort | combat corridors 256+ |
| Door | ~64–96 × 128–160 UU | narrower than corridors |
| Jump | ~64–72 UU | blocking ledges > 96 UU |
| Combat ranges | ≤ 256 / ≤ 1024 / ≤ 2048 UU (close / medium / long) | rescale to U2 weapons |

**Aztec steps**: climbable stairs use the riser numbers above. Monumental tiers are unclimbable (96–300 UU) with a stair cut into them. The tiers read as monumental because each one is taller than a person.

### 3.2 Sightlines and density

- Break long sightlines with ridges, buildings and spurs, then reopen them at chosen vistas.
- **Density gradient**: dense at the nodes, thinning outward, a few sparse outliers toward the horizon. Height rises toward the centre or the tower.
- **Three reads**:
  - primary forms at distance (tower, stacks, tiers);
  - secondary forms mid-range (balconies, pipes, cranes);
  - tertiary detail close up.
- **Skyline**: every district breaks the horizon (antennas, cranes, chimneys). A flat roof line is a dead skyline.

### 3.3 Hiding the map edge

From cheapest to strongest:
1. Water (an island).
2. A terrain rim (mesa or ridge).
3. Fog or haze beyond the farthest playable point, with atmospheric perspective. The storm pulls the fog in.
4. Skybox 3D layer: distant mountains, the mesa and far rigs at small scale in the SkyZone.
5. Diegetic soft blockers: fences, minefields, wrecks, "restricted" signs.

Checklist:
- [ ] Stair risers ≤ 16–20 UU; unclimbable terrace walls ≥ 96 UU; flag any 25–70 UU "almost climbable" ledges on paths.
- [ ] No straight, unbroken horizon within the fog end: from the tower, every 10° sector has a silhouette break.
- [ ] The heightmap or sea edge is never visible: rays toward the map edge hit water, the rim, skybox meshes or fog first.
- [ ] Density and height fall off from each node (proposed: the centre is ≥ 2× the density of the edge).
- [ ] Open areas wider than ~5 000 UU have at least 3 occluders.
- [ ] Primary silhouettes stay readable in storm fog. Run the tower screenshot test at clear, dusk and storm.

## 4. Environmental storytelling: the backwater patrol

Sources and what each teaches:
- **"What happened here?"** (Smith & Worch, GDC 2010): the player infers a story from cause and effect. Arrangement beats quantity.
- **Theme-park storytelling** (Carson, 2000): every object tells the place's story; cheat the scale toward what matters.
- **Narrative architecture** (Jenkins, 2004): evoke, enact, embed and emerge.
- **Half-Life 2**: in City 17, alien Combine structures intrude on the old city, two architectures in conflict. Ravenholm tells its story through the survivor's traps, signs and bodies.
- **BioShock**: an idealistic architecture shown failing.
- **Fallout**: vignettes and notes, used sparingly.
- **Shenmue**: traces of routine make a town believable.

Avalon:
- **Who built it.** The corporation or military: standardised, stamped, numbered prefab, plus the stepped "Aztec" concrete of authority.
- **Who lives here.** Miners and squatters: crates and corrugated metal built against the official walls and under the pipes. **Official (stepped, grey, ordered) against improvised (patchy, colourful, crooked) is the main story device.**
- **What happened.** One vignette per district: an overturned truck, a barricaded clinic, a burned watch post, a rig gone dark.
- **The patrol's misery.** A heater and a pin-up in the guard post, a "days since last incident" board, mud and puddles, rust streaks under every bolt, generators running for nobody, flickering lights, too many warning signs.
- **Procedural neglect cues.**
  - rust and dirt decals, scaled by height and by distance from the node;
  - 10–30% of windows broken or dark;
  - cable sag between buildings;
  - debris at wall bases;
  - dead or flickering lights;
  - mismatched patch panels.

Checklist:
- [ ] Each district has 1–3 cause-and-effect vignettes.
- [ ] Each district has one recurring personal prop family in its colour (laundry, shrines, tool racks, tags).
- [ ] Every town frame shows official and improvised architecture together.
- [ ] Neglect pass: ≥ 10% of windows dark or broken, ≥ 50% of facades with rust or dirt, ≥ 1 dead or flickering light per street (proposed).
- [ ] No two vignettes reuse the same prop arrangement.

## 5. Blockout → art, and authored quality in procedural generation

The loop:
1. Paper layout (Lynch elements plus a beat chart).
2. A metrics gym map.
3. A playable greybox; iterate on the layout only here.
4. Silent playtest observation (Valve). The user's in-game notes are this step.
5. Art pass on stable layouts only.
6. Polish.

Don't art a space whose layout still changes ("whole shape first").

Procedural generation with authored quality:
- **Spelunky** (Yu; Kazemi): carve a guaranteed solution path through a 4×4 room grid first, then fill from hand-authored templates chosen by their required exits, with controlled randomness.
- **Dormans**: generate the mission graph first, then the space that serves it (the same idea as the "story beat spine").
- **WFC / Townscaper / Bad North** (Stålberg; Gumin): small authored modules plus adjacency rules. The beauty is in the corners and junctions; an irregular grid avoids the stamped look.
- **No Man's Sky**: without authored constraints and curated palettes you get "procedural oatmeal".
- **Ubisoft Wildlands**: tools generate the bulk, designers override locally, and the overrides survive re-runs as separate layers.

Avalon:
- The spine street is the guaranteed path.
- Generate the beat graph before the buildings.
- Keep user edits in an override layer that regeneration respects.
- Invest in junction pieces: corners, stair cut-ins, shanty-meets-official-wall.

Checklist:
- [ ] A metrics gym passes the bot traversal test before new kits are used.
- [ ] Generation order: beats/critical path → nodes and landmarks → streets → buildings → dressing. Every regeneration re-runs the connectivity test first.
- [ ] Every node and landmark is reachable by the autoplay bot; no dead-end loops on the critical route.
- [ ] Hand overrides survive regeneration (diff before and after).
- [ ] Kits have corner, T-junction and end-cap pieces: no open edges, no z-fighting.
- [ ] Nothing gets dressed while its layout is still flagged "changing".

## 6. Encounters and pacing in a hub

- **The L4D AI Director** (Booth, 2009): build-up → peak → fade → relax (~30–45 s).
- **Pacing curves**: avoid a flat line; use waves with real valleys.
- **Arenas**:
  - cover at waist height (~50–64 UU) and full height, ~150–300 UU apart (proposed);
  - at least 2 routes in and through;
  - a reachable but exposed high spot;
  - readable enemy entrances.
- **Teach, then test**: a staged reveal (Unreal 1 Skaarj style), then a fight in a space suited to the new enemy, then mixing it with others.
- **Refuges** where you can see without being seen (guard huts, the tower).
- **The storm as the hub's interest curve**: clear weather is explore and relax; the storm is tension, with fog in and creatures out.

Checklist:
- [ ] Combat nodes have at least 2 entries, at least 3 cover pieces (half and full height) and one elevated position.
- [ ] Spawns are out of view but on a visible entrance, never inside the player's 90° rear cone.
- [ ] At least 30 s with no forced combat after each scripted fight (proposed).
- [ ] Each new enemy gets a sound → silhouette → corpse reveal before its first fight.
- [ ] Storm-phase sightlines ≤ 50% of clear-phase; spawn intensity rises with the storm.

## 7. Command tower review (live sessions)

Stand on the tower and turn 360° at clear, dusk and storm:
1. Can I name every district by shape and colour?
2. Does each district have a local landmark breaking the skyline?
3. Is there any straight horizon or visible map edge?
4. Can I see the main route as a line (lights, road, rails) from the tower to the rigs, shanty and mesa?
5. Is there one frame in each direction I'd screenshot?
6. Is there official against improvised architecture, and a neglect sign, in every district?

Then walk the spine street once: every turn shows the tower or a landmark, and every block holds a beat.

## Sources

- *The Level Design Book*, Robert Yang et al. https://book.leveldesignbook.com/ (Metrics: /process/blockout/metrics; Wayfinding: /process/blockout/wayfinding)
- "Legacy: General Scale And Dimensions" and "Unreal Unit", Unreal Wiki (archived). https://unrealarchive.org/wikis/unreal-wiki/Legacy:General_Scale_And_Dimensions.html
- Joel Burgess & Nate Purkeypile, "Skyrim's Modular Approach to Level Design", GDC 2013. https://gamedeveloper.com/design/skyrim-s-modular-approach-to-level-design
- Steve Lee, "Level Design Workshop: An Approach to Holistic Level Design", GDC 2017. https://gdcvault.com/play/1024301/ ; 80.lv summary https://80.lv/articles/gdc-2017-highlights-of-the-level-design-workshop
- Blake Rebouche, "Balancing Action and RPG in Horizon Zero Dawn Quests", GDC 2018. https://www.gdcvault.com/play/1025445/
- Kevin Lynch, *The Image of the City*, MIT Press, 1960.
- Christopher W. Totten, *An Architectural Approach to Level Design*, CRC Press.
- Scott Rogers, *Level Up!*, Wiley.
- Jesse Schell, *The Art of Game Design: A Book of Lenses*, CRC Press.
- Harvey Smith & Matthias Worch, "What Happened Here? Environmental Storytelling", GDC 2010.
- Don Carson, "Environmental Storytelling", Gamasutra, 2000.
- Henry Jenkins, "Game Design as Narrative Architecture", 2004.
- Valve, *Half-Life 2* developer commentary.
- Darius Kazemi, "Spelunky Generator Lessons". https://tinysubversions.com/spelunkyGen/ ; Derek Yu, *Spelunky* (Boss Fight Books, 2016).
- Joris Dormans, "Adventures in Level Design", PCG 2010; Dormans & Bakkes, IEEE TCIAIG 2011.
- Maxim Gumin, WaveFunctionCollapse. https://github.com/mxgmn/WaveFunctionCollapse ; Oskar Stålberg, Bad North / Townscaper talks.
- Sean Murray and Innes McKendrick, No Man's Sky talks, GDC 2017.
- Ubisoft Paris, "Ghost Recon Wildlands: Terrain Tools and Technology", GDC 2017.
- Michael Booth, "The AI Systems of Left 4 Dead", AIIDE 2009.
- "Examining Game Pace: How Single-Player Levels Tick", Gamasutra, 2009.
- Bungie / Jaime Griesemer, "30 seconds of fun".
- Alex Galuzin, World of Level Design. https://www.worldofleveldesign.com/

Verification: the metric tables, the Burgess kit rules, the Spelunky generator and the identity of Lee's talk were checked online on 2026-10-07. The rest is established secondary knowledge.
