# Organic settlement generation for the U2Avalon town

Research pass 2026-10-07. Problem: the generated frontier mining town (U2Avalon: binder -> interest-map /
spine layout -> systems -> pads -> StaticMeshActors) reads **sparse and samey**. The other team is making
shanty blocks ~3x denser. Target look: informal hillside settlement / favela, stepped and battered
(Aztec-like) terraces, frontier mining outpost, **only the original level's kit** (no new art style).

What already exists (so this note does not repeat it): Emilien & Galin 2012 interest maps (`layout.py`),
dock -> tower -> mine spine with frontage plots and fences (`layout_spine.py`), least-cost roads,
active-walker foot paths (`walks.py`, Helbing), cut/fill pads with shared terraces and retaining walls on
rims (`terrain_cutfill.py`, `clutter.py` step 6), clutter (lamps, crates, barrels, fences, rocks, trees),
viewshed (`viewshed.py`). See also `games/reports/How others build towns.md` and
`City generators for the binder town.md`.

Licence key: **[code: MIT/BSD/GPL/CC BY-SA - reusable]**, **[paper: algorithm only, reimplement]**,
**[no reuse: proprietary/commercial - ideas only]**.

---

## 0. Diagnosis: why the town reads sparse and samey

1. **One building per plot, plots spaced by a 10 m yard (`GAP_M`) and 4 m setback.** Informal settlements
   have *zero* setback and shared walls; the gap is the alley (1-3 m), not a yard. Density comes from
   party walls, not from more plots.
2. **One storey everywhere.** Favelas read as favelas because of stacking: 2-4 storeys of differing
   footprints, setbacks, cantilevers, roof terraces.
3. **Buildings are whole objects.** Every building is "a kit building" with a full silhouette. Organic
   towns are made of *additions*: lean-tos, extra rooms, stairs, balconies, water tanks, bridges. The
   repetition hides because no two aggregates have the same additions.
4. **Flat ground between buildings.** On a hill the town *is* the terraces: steps of 2.5-3.5 m with
   battered walls, stair alleys climbing perpendicular to contours.
5. **The glue is missing at the human scale.** Wires spanning alleys, pipes along walls, laundry, signs
   at junctions, junk on roofs. These carry 50 % of the "informal" read in every shipped example.

The fix is therefore less about a new layout algorithm and more about **(a) a fine-grid accretion/infill
pass inside the existing spine blocks, (b) vertical stacking + additions, (c) terrace quantisation,
(d) an edge-driven dressing pass.** Section 6 is the concrete algorithm.

---

## 1. Informal settlement / organic growth models

| source | what it does | use for us | licence |
|---|---|---|---|
| Emilien, Bernhardt, Peytavie, Cani, Galin 2012, *Procedural generation of villages on arbitrary terrains*, The Visual Computer. https://perso.liris.cnrs.fr/egalin/Articles/2012-villages.pdf | interest maps per building type, roads grown as buildings arrive, parcels by anisotropic Voronoi, terrain-adapted | **done** in `layout.py`. Unused bits: their *parcel* step (anisotropic Voronoi with road-facing aspect) and *walls/fences* from parcel boundaries | paper |
| Vanegas, Kelly, Weber, Halatsch, Aliaga, Müller 2012, *Procedural Generation of Parcels in Urban Modeling*, CGF 31(2). https://www.cs.purdue.edu/cgvlab/papers/aliaga/eg2012.pdf | two subdividers of a block: **OBB recursive split** (split the oriented bounding box perpendicular to its long axis until area < target, keep road access) and **straight skeleton strips** (frontage strips along the block boundary) | OBB split is ~40 lines and gives **narrow deep lots with party walls** = the favela row. Use it to turn each spine plot into 2-5 lots | paper |
| Weber, Müller, Wonka, Gross 2009, *Interactive Geometric Simulation of 4D Cities*, Eurographics. https://doi.org/10.1111/j.1467-8659.2009.01378.x | city grows over time steps: streets extend, land-use value drives lot development and *redevelopment* (densify) | matches our binder layers (core/boom/decline). Idea to borrow: each time step **densifies** existing lots (add storey/addition) rather than only adding new ones | paper |
| Lechner, Watson, Wilensky et al. 2003, *Procedural City Modeling* (agent-based, NetLogo). https://ccl.northwestern.edu/papers/ProceduralCityMod.pdf | developer agents (residential/commercial) and road agents ("extenders", "connectors") on a terrain patch grid; agents place where value is high and road access exists | the *connector* road agent (adds a link when travel along network >> straight-line distance) is a cheap way to make alley shortcuts | paper (NetLogo models are usually GPL - check) |
| Barros 2002-2004, *Peripherisation* CA/agent models of Latin-American informal growth, CASA WP 55. https://discovery.ucl.ac.uk/id/eprint/243/1/Paper55.pdf | low-income agents settle at the periphery, are displaced as areas consolidate; growth = **infill + edge expansion** | rule: poor housing appears where land is *worst* (steep, near hazards, near the works' noise) - invert some interest weights for the shanty ring | paper |
| Patel, Crooks, Koizumi 2012, *Slumulation*, JASSS 15(4)2. https://www.jasss.org/15/4/2.html | households, developers, politicians; slums emerge on unserviced land near jobs | rule: shanties cluster within walking distance of jobs (the plant), not of the civic spine | paper |
| *Simulating informal settlement growth in Dar es Salaam: an agent-based housing model* (CoMSES). https://catalog.comses.net/publications/247 | vector micro-model: **three rules - infilling, extension, enlargement - reproduce real informal housing patterns** | this is the core of our accretion pass (section 6) | paper; check CoMSES model licence |
| SBGames 2020, procedural favela generation (A* roads on heightmap, quadtree lots, alleys). https://www.sbgames.org/proceedings2020/ComputacaoFull/209687.pdf (large PDF) | A* with slope cost -> **zigzag roads, dead ends, big blocks**; quadtree subdivides blocks into lots; leftover thin cells become alleys | the zigzag + dead-end character is what our least-cost roads lack; quadtree lots on a slope-aligned frame is an alternative to OBB | paper |
| Helbing, Keltsch, Molnár 1997, *Modelling the evolution of human trail systems*, Nature 388. | active walker: walkers prefer worn ground, trails merge | **done** (`walks.py`). Extension: run walkers *after* shacks exist, and let footpaths with traffic > T become reserved alleys (roads emerging from paths) | paper |
| Hillier & Hanson 1984, *The Social Logic of Space*; **depthmapX** (space syntax: axial/isovist/integration). https://github.com/SpaceGroupUCL/depthmapX | integration = how central a street is in the network; isovist = visible area from a point | compute integration on our alley graph: high-integration alleys get shops/signs/lamps, low ones get dead ends/laundry. Isovist = FPS sightline metric (section 4) | **GPL-3 code** |

**Stair/alley networks on steep slopes.** Real hillside favelas (Rocinha, Santa Marta) have a few
switchback vehicle roads and a dense net of **stair alleys running straight down the fall line**, 1-2 m
wide, with landings at every terrace. Model: two edge types in the path graph - *road* edges (grade
<= 12 %, any direction) and *stair* edges (only within +-25 deg of the fall line, grade up to 70 %, fixed
cost per riser). A* over that graph produces the characteristic road switchbacks crossed by straight
stairs. See also Santa Marta computational study: https://img-journal.unibo.it/article/view/12810.

**Terracing.** Quantise pad heights to a step set (e.g. multiples of 3.0 m, the kit's storey height);
neighbouring lots on the same contour share one terrace (already done for groups); risers get a
**battered** (sloped 10-20 deg) retaining wall rather than vertical - that is the Aztec/dystopian read.
Wider terraces near the spine, narrower (one house deep) up the slope.

---

## 2. Dense kit-bash techniques that hide repetition

### Principles (common to every source)
1. **Kit pieces are small and combinable, hero pieces are few.** Repetition hides when the *combination*
   varies, not the pieces (Burgess/Purkeypile, *Skyrim's Modular Approach to Level Design*, GDC 2013:
   http://blog.joelburgess.com/2013/04/skyrims-modular-level-design-gdc-2013.html, slides+transcript
   also at https://www.gamedeveloper.com/design/skyrim-s-modular-approach-to-level-design). Their rules:
   strict grid snap, pieces that connect anywhere, *"the kit is not the level"*: clutter pass after
   layout, a few one-off hero props per space to give memory. [no reuse - talk]
2. **Break the silhouette at three scales**: mass (storey count, setbacks), roofline (tanks, antennas,
   rooftop sheds, parapets of varying height), edge (wires, overhangs, signs). A row of equal-height
   boxes with varying textures still reads samey; varying heights with identical textures does not.
3. **Additions are attached to a host by rule** (lean-to on the path side, balcony over the alley,
   external stair on the gable, bridge across an alley < 4 m when both sides have a floor at the same
   height). This is the Townscaper idea of "the rule lives on the shape" (Stålberg: corners, arches,
   stairs and gardens appear from neighbour configuration).
4. **Tint, wear and mirror inside one kit**: per-instance material/skin swaps from a small palette, 180
   deg yaw flips, small non-uniform scale on non-grid props (0.9-1.15), random wear decals.
5. **The glue pass is edge-driven, not area-driven**: walk wall edges and alley segments, place things
   *between* buildings (wires roof-corner to roof-corner, pipes down walls, laundry lines across narrow
   alleys, signs at junctions, crates at doors). Area scatter (current crates in yards) reads as random.

### Shipped games and tools
- **Townscaper / Bad North (Oskar Stålberg).** Irregular quad grid (relaxed triangles -> quads), **dual
  grid**: tiles live on grid *corners*, so a tile is chosen from the 8 surrounding occupied/empty bits,
  needing far fewer modules; WFC (Bad North) or marching-cubes-like lookup (Townscaper) picks modules.
  Talk: EPC 2018 Bad North WFC (summary https://80.lv/articles/using-wave-function-collapse-algorithm-for-dioramas),
  https://www.gamedeveloper.com/game-platforms/how-townscaper-works-a-story-four-games-in-the-making,
  "Beyond Townscapers" (Sweden Game Arena). [no reuse - commercial; ideas only]
- **Half-Life 2 City 17** (Viktor Antonov): one real reference city (Eastern Europe), Combine
  architecture *intruding* on it - the "alien structure cuts the old town" read. For us: the Liandri
  tower and ore line as the intruding structure, the shanty ring hugging it. **Dishonored's Dunwall**
  (same art director): stacked wooden additions and bridges on old stone blocks, verticality for routes.
  [ideas only]
- **Max Payne 3 / CoD MW2 "Favela"**: Rockstar photo-scanned São Paulo favelas (field trips; no technical
  breakdown found). Visual takeaways from the levels themselves: exposed brick+concrete frame, every
  roof has a blue water tank, rebar sticking out of the top (unfinished next storey), dense overhead
  wiring, stairs everywhere, laundry, painted ground-floor shopfronts only on main alleys. [ideas only]
- **Houdini**: no official SideFX "shanty town" tutorial found; closest: *Procedural Lake Houses* vol.1-3
  (silhouette -> modules -> set dressing, stacked stilt houses) https://www.sidefx.com/tutorials/procedural-lake-houses-volume-1/ ;
  Marina Bade's Houdini-for-Unity *Shanty Town* tool (80.lv:
  https://80.lv/articles/procedural-environment-for-unity-with-houdini/) - stacks prebaked modules by
  rule, the same hybrid we want. [no reuse - Houdini is commercial; techniques transfer]
- **Unreal 5 PCG**: graph of point sampling -> filters -> spawners; "PCG shape grammar" and attribute-set
  driven mesh selection. Concept to copy: everything is *points with attributes* filtered by
  density/slope/distance-to-spline, then spawned. That is exactly what `clutter.py` can become. [ideas]
- **Tiny Glade** (already cited in PIPELINE.md): rules on the shape, walls auto-decorate. [ideas]

### Within the one-kit constraint (Unreal II)
- Use **material skin overrides per actor** (`Skins[0]=...` on StaticMeshActor works in UE2) with 3-6
  pre-made variants of each building texture (rust tint, sun-bleached, soot, painted panel). Make the
  variants in a package as Combiner/Shader materials over the *same* base texture so the art style
  stays the kit's. (Verify which modifier classes Unreal II has - ColorModifier is UT2004-era; Combiner
  and Shader exist.)
- Reuse the kit's **panels, crates, pipes, fence segments, lamp posts** as additions: a fence segment on
  a roof = parapet; a crate stack against a wall = lean-to base; pipe meshes along walls; lamp post +
  cable = overhead wiring.
- The **imposter cards** (bake_cards.py) can carry distant density (far ring of shacks as cards) at
  near-zero cost.

---

## 3. WFC / constraint-based layout on terrain

- **mxgmn/WaveFunctionCollapse** (MIT): https://github.com/mxgmn/WaveFunctionCollapse - overlapping model
  (learns from an example bitmap) and simple tiled model (adjacency rules). [code: MIT]
- **DeBroglie** (Boris the Brave, MIT, C#): https://github.com/BorisTheBrave/DeBroglie - WFC with
  *global constraints*: path/connectivity constraint, border, fixed tiles, count. Its blog
  (boristhebrave.com) has the best practical WFC writing (e.g. "WFC tips and tricks", "Path
  constraint"). [code: MIT]
- **Merrell, *Model Synthesis*** (2007-2011): https://paulmerrell.org/model-synthesis/ - the 3D
  predecessor of WFC, modifies in blocks so it does not fail on large grids; paper describes
  backtracking-free block-wise resolution. [paper; check site for code]
- **Python**: plain numpy implementation of the tiled model is ~150 lines; no dependency needed.

**Does WFC fit a terrain town?** Partially.
- WFC is **local**: it guarantees neighbour compatibility, not global structure (a street that goes
  somewhere, a landmark, sightlines). Our spine/interest maps/systems already supply the global structure
  - that is the part WFC is bad at. Pure WFC towns read as "noise of houses".
- Terrain: works if the grid is **2.5D columns** whose ground level is *fixed* from the terraced
  heightmap (pre-collapsed cells), as in Bad North. Steep slopes become forced "retaining wall/stair"
  tiles.
- **Kit mismatch** is the real blocker: WFC needs modules with matching sockets on a grid. The U2 kit is
  whole buildings and props, not grid modules. So WFC fits *only* if we first cut/define a small socketed
  set from kit parts (wall panel, corner, stair, roof slab, empty) - which is what `build_parts.py`
  partly is.
- **Recommendation:** grammar/agents for layout (what exists + section 6); WFC later and only *inside a
  block* for vertical massing (which columns get 1-4 storeys, where stairs/bridges go) with constraints:
  every occupied cell reachable (DeBroglie path constraint), alleys pre-fixed as empty, ground fixed.
  PIPELINE.md already plans "2D WFC over footprints for panel variation" - that is the right scope.

---

## 4. Gameplay-aware layout for an FPS

**Kevin Lynch, *The Image of the City* (1960)** - five elements, mapped to our town:
- **Paths**: spine (vehicle), stair alleys (foot), rooftop routes. Each must have a *character*
  (width, surface, lighting) so the player knows which kind they are on.
- **Edges**: the sea, the terrace risers (battered walls), the plant fence. Edges stop sightlines and
  give orientation.
- **Districts**: dock/market, company core, shanty slope, works. Distinguished by one kit sub-set and
  one tint each (same kit, different dominant panel/colour), not by new art.
- **Nodes**: junctions of spine and stair alleys - plazas with a sign, lamp, water tank, shop.
- **Landmarks**: the tower and the ore line, visible from nearly everywhere (check with
  `viewshed.py`); plus local landmarks per district (a crane, a painted tank, a mast).

**FPS rules of thumb** (level-design practice, e.g. Unreal/UT community docs, Valve wiki on
sightlines, *The Level Design Book* https://book.leveldesignbook.com/ CC BY-SA? - check, Hillier isovists):
- **Sightline length**: in dense blocks keep max unbroken sightline along an alley at ~25-40 m; break
  longer ones with a bend, an addition, a hanging sign or a bridge. Long sightlines only on the spine
  and from terraces looking down (reward views at the landmark).
- **Cover density**: something to crouch behind every 5-8 m along player routes (crates, tanks, low
  walls, parked carts). Measure: for each path cell, distance to nearest cover-height object.
- **Verticality**: at least two vertical connections per block (stair alley + external stair/ladder or
  rooftop bridge), so fights can flank via roofs. Height advantage spots (terrace edges) need a counter
  route.
- **Choke points**: stairs between terraces are natural chokes; give each terrace >= 2 connections so
  no single choke is mandatory (unless the story wants one).
- **Loops > dead ends** on routes the player uses; dead ends are fine as dressing in low-integration
  alleys.
- **Metrics we can compute in Python**: isovist area per walkable cell (raycast on the occupancy grid),
  alley graph integration (space syntax), cover distance, connectivity per terrace, landmark visibility.
  Fail/flag thresholds feed back into the accretion pass (add a blocker / remove a shack).

---

## 5. Unreal Engine 2 constraints and tricks

(Unreal II = early UE2, 2003. Verify each property in the game's own `.uc`/editor before relying on it.)

- **Static meshes vs BSP.** Static meshes are the right primitive for repeated parts: shared vertex
  buffers, no BSP cuts, no holes. BSP is lightmapped and cheap for a few large simple shapes but every
  brush cuts the BSP tree and adds CPU visibility cost; a generated town should be ~all static meshes.
  Cost driver on 2003-era drivers is **actor count / draw calls** (roughly one per mesh section per
  actor), not triangles. Budget guide: aim for a few hundred *visible* meshes at once, not thousands.
  -> **Merge clutter offline**: the pipeline already writes ASE (`part_to_ase.py`, `glb_to_ase.py`) -
  bake each shack aggregate's small additions (wires, pipes, tanks) into **one merged mesh per
  aggregate** using the kit's own textures (same material = one section).
- **Lighting**: static meshes are **vertex-lit** (baked per vertex at LIGHT APPLY); terrain and BSP get
  lightmaps. Consequences: large flat low-poly meshes light badly (no shadow detail across a face);
  dense small meshes light fine. Per-vertex lighting can be *used* for variation: coloured local lights
  (a sodium lamp at nodes, a red warning light by the works) tint whole meshes for free after the bake.
  Unreal II has the U2Shaders fork with shadow maps - check how merged meshes interact with it.
- **Per-instance colour**: UE2 has no per-instance vertex colour on StaticMeshActor (that is UE3+). Use
  `Skins[]` overrides to variant materials (section 2), or bake colour variation into vertex colours of
  *merged* meshes at export time (ASE supports vertex colours; check that the U2 material multiplies
  them - UE2 static mesh materials can use vertex colour via `bUseVertexColor`-style flags on some
  material classes; test first).
- **Terrain DecoLayers**: `TerrainInfo.DecoLayers[]` - StaticMesh, DensityMap (greyscale texture),
  ScaleMultiplier, FadeoutRadius, MaxPerQuad, Seed, AlignToTerrain, ShowOnTerrain, LitDirectional.
  Cheap batched rendering, **no collision**, fade by distance. Perfect for rubble, litter, small rocks,
  weeds at wall feet and along path edges: generate the DensityMap from the layout (walls, path
  verges) as a BMP, same way the heightmap is exported. See `research_notes/Terrain look for generated maps/ue2_terrain.md`.
- **Occlusion**: UE2 terrain does **not** occlude. In an outdoor hill town everything behind a hill is
  drawn. Fix: **AntiPortals** (brush-based occluders) inside hill masses, inside big buildings and
  behind long terrace walls. A static mesh is culled only if *entirely* behind one antiportal; the
  occluded volume is the brush's bounding box. They are only considered if their zone is visible.
  Docs: https://docs.unrealengine.com/udk/Two/LevelOptimizationAntiportals.html ,
  https://unrealarchive.org/wikis/unreal-wiki/Legacy:Antiportal.html ,
  https://docs.unrealengine.com/udk/Two/LevelOptimizationStaticMesh.html .
  Generator rule: for each terrace riser > 4 m tall and > 20 m long, emit an antiportal box just inside
  the slope behind it; for each hill ridge between districts, a box inside the ridge.
- **Zones**: zoning open outdoor space hurts; only zone at real closures (tunnels to the mine, interiors).
- **CullDistance**: per-actor `CullDistance` (and CullDistanceVolume in later UE2 builds): small clutter
  30-60 m, medium props 80-120 m, buildings never. `clutter.py` already has `cull_of(mesh)` - extend it to
  every addition. Check Unreal II's Actor class actually has CullDistance (UT2003+ do).
- **Projectors** (grime, stains, painted signs, wear): `Projector` actors with `bProjectBSP/
  bProjectTerrain/bProjectStaticMesh/bProjectActor`; static projectors (`bStatic`, not dynamic) attach
  once at load. Each projector re-renders the receiving triangles, so use them sparingly (tens, not
  hundreds) and keep FOV/extent small. Better: grime on the ground via terrain layer alphas
  (`groundpaint.py`), grime on walls via Skins variants.
- **Collision**: give merged addition meshes simple collision or none (wires, laundry: none), keep
  player-relevant blocks (walls, stairs) with simple box collision so bots/pilot can path.
- **Bot paths**: dense alleys need PathNodes; generate them from the alley graph (one per junction +
  every ~10 m) so AI and `U2AutoPlay` can move.

---

## 6. Recommended algorithm for 1-2 days: "accrete, stack, dress"

Runs **after** `layout_spine.py` and `walks.py`, **before** `terrain_cutfill.py`/`export_mutator.py`.
New file e.g. `tools/accrete.py`, reads layout JSON + heightmap, writes extra buildings/additions into
the same JSON (so cut/fill, systems and export pick them up unchanged).

```
INPUT  layout.json (spine, plots, buildings, roads), walks trunks, heightmap H, kit table
GRID   fine occupancy grid G at 2.56 m (1/4 of a 10.24 m cell) over the shanty ring
       states: FREE, ROAD, ALLEY, STAIR, BUILT(level, id), RESERVED(door apron), WATER, STEEP

1. Reserve circulation
   rasterise spine/branches (ROAD, width 8 m) and walks trunks with traffic > T (ALLEY, width 2-3 m)
   stair alleys: for each terrace band, every 25-40 m along the contour, A* down the fall line
     using road edges (grade <= 12%) + stair edges (fall-line +-25 deg, grade <= 70%), mark STAIR (1.5-2 m)
   door aprons of existing buildings -> RESERVED (1.5 m)

2. Terrace levels
   Hq = round(H_smoothed / STEP) * STEP     (STEP = kit storey height, ~3 m)
   connected same-level patches = terraces; risers between them -> battered retaining-wall edges

3. Lots (Vanegas OBB split) inside each spine plot / free block
   split(poly): if area < A_target(rand 30-70 m2) or width < 4 m: emit lot
                else cut perpendicular to OBB long axis at 0.4..0.6, keep both halves touching
                     ROAD/ALLEY/STAIR (else re-cut or merge into neighbour)

4. Accretion (Dar es Salaam rules; iterate per binder layer core -> boom -> decline)
   repeat N_target times (N_target = 3x current housing):
     pick action by weights: INFILL 0.5, EXTEND 0.3, ENLARGE 0.2
     INFILL : choose a free lot; score = access(lot touches path) * slope_ok * neighbours_built^k
              * job_proximity(plant, Slumulation) * (1 - civic_core_mask)   # poor land, near work
              place kit shack footprint aligned to the lot's path edge, flush to neighbour walls (no gap)
     EXTEND : pick a BUILT edge facing FREE cells; add a lean-to/annex module (smaller, lower roof)
     ENLARGE: pick BUILT with age >= 1 layer; add storey k+1 with footprint = shrink/offset of storey k
              (setback 0-1.5 m toward the path, or cantilever 0-1 m over ALLEY if alley width > 2 m)
              max storeys by distance to spine (4 near spine, 2 at fringe)
     reject if: blocks ROAD/ALLEY/STAIR/RESERVED, door has no path within 2 m, or isovist check
                says it closes the last connection of a terrace

5. Additions (rules on the shape)
   for each aggregate:
     roof:     water tank (p .6), antenna/mast (p .2), rooftop shed (p .2 if storeys < max),
               rebar/unfinished parapet (fence segment) on top storey (p .3)
     path wall: balcony/overhang at storey >= 2 over ALLEY; external stair to an upper door
     between:  bridge (plank/walkway mesh) if two aggregates face across ALLEY < 4 m with floors
               at equal level (within 0.5 m)
     terrace rim: battered retaining wall along riser + stair where STAIR crosses it

6. Dress pass (edge-driven)
   for each alley segment of length L: wires roof-corner -> roof-corner across it every 4-8 m
   (catenary from a few straight pipe/cable meshes), laundry lines if width < 3 m and residential
   for each wall facing a path: downpipe at a corner, 0-2 wall pipes, sign if at a node
     (node = alley junction, ranked by space-syntax integration: top 20% get shop signs + lamp)
   at each door: 0-3 crates/barrels; at stair landings: one cover object (FPS cover every 5-8 m)
   DecoLayer density map: rubble/litter along wall feet and path verges -> BMP for TerrainInfo

7. Variation + cost
   per actor: Skins variant from district palette, yaw flip 0/180 for symmetric modules,
              scale jitter 0.9-1.15 on props only
   merge small additions per aggregate into one ASE mesh (same material set)
   CullDistance by size class; antiportal boxes behind risers > 4 m and inside ridges

8. Verify (extend existing checks)
   isovist max along alleys <= 40 m (else add sign/bridge/addition at midpoint)
   every terrace has >= 2 connections; landmark visible from >= 70% of walkable cells
   visible-actor estimate from 10 sample viewpoints <= budget
```

Day 1: steps 1-4 (grid, OBB lots, accretion with stacking) writing into layout JSON.
Day 2: steps 5-7 (additions + edge dressing + skins/cull), metrics in step 8.

## 7. The later bigger step

**Time-sliced growth + block-level WFC massing.**
1. Turn the binder layers into a real **growth simulation** (Weber 4D cities style): at each time step
   land value is recomputed from jobs (systems.py), access (alley integration) and views; lots
   *redevelop* (shack -> 2-storey -> 4-storey with tank), walkers re-run on the new town so new alleys
   emerge from footpaths (Helbing), decline layer *removes/abandons* storeys (roofless, dark).
2. Define a **socketed sub-kit** from existing parts (wall panel, corner, door, window, stair, slab,
   parapet, empty) on the 2.56 m x 3 m grid, then run **WFC (DeBroglie-style path constraint, or Merrell
   model synthesis for big blocks)** per block in 2.5D columns with ground pre-collapsed from the
   terraces and alleys pre-collapsed empty. Dual-grid (Stålberg) to minimise module count.
3. Export WFC output as merged per-block meshes (one actor per block per material) to keep the UE2
   draw-call budget.

---

## Sources (quick list)

- Emilien et al. 2012 villages: https://perso.liris.cnrs.fr/egalin/Articles/2012-villages.pdf
- Vanegas et al. 2012 parcels: https://www.cs.purdue.edu/cgvlab/papers/aliaga/eg2012.pdf
- Weber et al. 2009 4D cities: https://doi.org/10.1111/j.1467-8659.2009.01378.x
- Lechner et al. 2003 agent cities: https://ccl.northwestern.edu/papers/ProceduralCityMod.pdf
- Barros peripherisation, CASA WP55: https://discovery.ucl.ac.uk/id/eprint/243/1/Paper55.pdf
- Slumulation (JASSS): https://www.jasss.org/15/4/2.html
- Dar es Salaam informal growth ABM: https://catalog.comses.net/publications/247
- Procedural favelas (SBGames 2020): https://www.sbgames.org/proceedings2020/ComputacaoFull/209687.pdf
- Santa Marta computational strategy: https://img-journal.unibo.it/article/view/12810
- depthmapX (GPL-3): https://github.com/SpaceGroupUCL/depthmapX
- WFC (MIT): https://github.com/mxgmn/WaveFunctionCollapse ; DeBroglie (MIT): https://github.com/BorisTheBrave/DeBroglie
- Merrell model synthesis: https://paulmerrell.org/model-synthesis/
- Bad North WFC talk summary: https://80.lv/articles/using-wave-function-collapse-algorithm-for-dioramas
- How Townscaper works: https://www.gamedeveloper.com/game-platforms/how-townscaper-works-a-story-four-games-in-the-making
- Skyrim modular kits (Burgess/Purkeypile GDC 2013): http://blog.joelburgess.com/2013/04/skyrims-modular-level-design-gdc-2013.html
- SideFX Procedural Lake Houses: https://www.sidefx.com/tutorials/procedural-lake-houses-volume-1/
- Shanty Town Houdini->Unity tool: https://80.lv/articles/procedural-environment-for-unity-with-houdini/
- UE2 antiportals: https://docs.unrealengine.com/udk/Two/LevelOptimizationAntiportals.html ,
  https://unrealarchive.org/wikis/unreal-wiki/Legacy:Antiportal.html
- UE2 static mesh optimisation: https://docs.unrealengine.com/udk/Two/LevelOptimizationStaticMesh.html
- Max Payne 3 São Paulo research: https://gamingbolt.com/max-payne-3-this-is-how-rockstar-have-made-the-levels-more-realistic/amp
- Lynch, *The Image of the City* (1960); Hillier & Hanson, *The Social Logic of Space* (1984) - books.

Not verified in this pass (flagged): exact Unreal II availability of CullDistance, ColorModifier and
vertex-colour material flags; the Level Design Book's licence; CoMSES/NetLogo model licences. Check
before reuse.
