# From concept to a believable town: the Avalon pipeline

One command, `py tools/town.py <seed> [style=plateau|ridges] [name=TutA_Town] [pilot=1]`, runs every system
we built this week in order and leaves a run folder with the evidence. The design rule throughout is
*systemic*: nothing is placed because it looks right; it is placed because something else in the town needs
it there, and the thing that carries that need (road, pipe, cable, conveyor) is visible.

## The stages

| # | stage | tool | what decides |
|---|---|---|---|
| 0 | **premise** | `binder/` (citizens + building sheets) | who runs the place, who lives there, what each building is for, when it was built (core / boom / decline), who uses it. The binder is the growth scenario of Emilien and Galin and the encyclopedia of Watabou's wards. |
| 1 | **concept** | FLUX Kontext paint-overs + Sana (`design-refs/avalon_concepts/islands/run_concepts.sh`) | the look: Liandri sloped concrete, rust panels, sunset, gas giant. Paint-overs run over our own in-game frames so they critique the real layout. Cut-outs (`make_cuts.py`) feed stage 5. |
| 2 | **island** | `tools/island_form.py` (the terrain tool's sketch -> uplift -> stream power -> erosion) | ridges, an inlet, bays; or `style=plateau`: volcano cone, cliff plateau at the tower's level, the coast road. Sea level set for ~40 % land on the tower's landmass. Scored by `terrain_score`. |
| 3 | **layout** | `tools/layout.py` | anchors (tower, Authority pad) stay; everything else is seeded by interest maps (slope, waterline, sociability, avoidance, road access, domination, buildable room, the window sector), in binder layer order, with least-cost roads grown as each building arrives, then Voronoi drift. Doors face roads, quays face the sea. |
| 4 | **systems** | `tools/systems.py` | each building's provides/needs (ore, power, water, fuel, cooling, workers, goods, comms, supply); nearest provider within reach; connections routed (pipes, cables, conveyors L-shaped along roads; goods and workers by road). Unmet core needs fail the run so the batch re-rolls. |
| 5 | **assets** | `tools/build_parts.py` (prefab kit), `tune_buildings.py` (kiln silhouettes), Hunyuan from concept cuts (`run_models.sh`) -> `bake_cards.py` (8-way imposters), `palette.py` (measured Hunyuan colours) | what each building looks like: parts chosen from the sheet (kind, size, doors, bays, roof, wear, lit) and, next, from its neighbours (door toward the arriving road, bay toward the yard, pipes on the facing side: Tiny Glade's rule-on-the-shape idea). |
| 6 | **ground** | `tools/terrain_cutfill.py`, `tools/walks.py`, `tools/groundpaint.py`, `tools/clutter.py` | cut-and-fill pads under every footprint (groups share a terrace), blended back; roads graded; the citizens' routines walked door to door on the graded ground (active-walker model: trips merge into worn trunks) and painted as foot paths; walks also report door wants and travel times. |
| 7 | **build** | `tools/terrain_apply.py`, `tools/export_mutator.py t3d=`, `uedlib` | the heightmap into TutA's TerrainInfo (copy, delete, re-import), the buildings as StaticMeshActors at ground height, LIGHT APPLY, save. Cards stay in the mutator ini. |
| 8 | **verify** | `tools/binder.py` check, `U2Pilot` run, editor pictures, `terrain_score`, the systems report | routines reach real places, doors face arrival, abandoned = worn and dark; the window frames the plant; every need met; the pictures a reviewer can judge. |

**Playtest swap (the user, 2026-10-09):** while the user is playing (the GPU is theirs), stage 1 and the
Hunyuan part of stage 5 don't generate images. The creative team finds fitting images and art on the
internet instead. For each one it records:
- the page URL, the artist or source, and the licence;
- what in it fits (silhouette, material, light, mood);
- which building sheet or interior it is for.

It collects them in a reference board (`redesign/<date>/references.md`). Nothing is downloaded without
the user's OK. References inform the sheets, palette and parts, and the art itself never ships in a mod.
Generation (Kontext paint-overs, Sana, Hunyuan) resumes when the GPU is free. Also offline during a
playtest: no pilot runs and no editor or game launches. The binder, layout, scoring and drawings still run
on the CPU.

Feedback loops: stage 1 over stage 8's frames (concepts of the real layout), stage 4 failing back into
stage 3 (re-roll), stage 8's checker back into stage 0 (a citizen with nowhere to go is a missing sheet).

## What "systemic" means here

- **Every building has a reason.** The sheets say who uses it; `systems.py` says what it consumes and
  produces. A hall without ore, power, water and workers within reach is a failed town, not a prop.
- **The reasons are visible.** Connections are routed, measured and (next) rendered: conveyors from the
  wellheads to the silos to the halls, pipes from the intake to the cooling towers, cables from the
  generator house, the goods road to the dock. A player should be able to read the plant's process by
  following the lines.
- **Time is visible.** The three binder layers are three growth rings: the core clusters first on the
  best ground, the boom spreads along the roads the core built, the decline is what is worn and dark.
- **The ground answers the town.** Pads are cut into the slope the way real plinths are, roads climb
  at a real grade, quays reach into deep water, rigs stand offshore, the plateau meets the tower.
- **Nothing is unique twice.** Positions come from interest sampling and Voronoi drift, buildings from
  parts with wear and palette variation, islands from random sketches: the same binder gives a
  different believable town per seed.

## Done, partial, next

Done: stages 0, 2, 3, 6, 7, 8 (pictures, checker, scores), the concept loop, the systems analysis.
Partial: stage 5 reads only the sheet (neighbour-aware rules not written); stage 4's connections are
computed but not yet placed as meshes in the TutA map (the generated map has `pipe_network` already);
stage 3 still relaxes its clustering on narrow coasts.
Next, in order: (1) place connections as pipe/cable/conveyor meshes and lamp posts along roads in the TutA
map; (2) neighbour rules in `build_parts.py` (door toward the arriving road is first); (3) paint roads
and the erosion masks into the terrain layer alphas; (4) a 2D WFC over footprints for panel variation
(Townscaper); (5) retaining-wall parts on terrace risers.

Floor plans (2026-10-10): `tools/floorplan.py` plans the houses, offices and small buildings (rooms.py routes
kind house/office and those ids to it). Room sizes come from 8,061 real plans (the building-interiors skill)
scaled x1.25 to the measured player, connections from the same plans (entrance into the common room, en-suites
behind their bedroom, 3 in 4 kitchens open), and the kit's limits (doors on walls >= 3.2 m, rooms >= 1.6 m).
It writes rooms.py's schema plus `walls` (exact partitions with doors), `window_sides`, `graph`, `notes`;
shells.py builds `walls` when present. Pictures: `data/floorplans/*.png`.

## Where things are

Run folders: `Documents\U2_research\towns\<name><seed>\` (sketch, layout map, systems report, terrain
score, editor pictures, pilot sheet, `report.md`). Maps: `<game>\Maps\<name><seed>.un2`. Models from
concepts: `Documents\U2Golem\islands\`. Concepts and cuts: `Documents\design-refs\avalon_concepts\islands\`.
Research: `games/reports/City generators for the binder town.md`, the terrain reports beside it.
