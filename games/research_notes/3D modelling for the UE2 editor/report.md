# 3D modelling concepts for the Unreal II editor and its pipeline

Research pass, 2026-10-08, by a research agent from web sources and the local exec vocabulary dump (`Documents\U2_research\ghidra\editor_exec_tokens.txt`).

The question: which modelling ideas from the last 20 years can be hooked into UnrealEd 3 (the Unreal II build) or into the pipeline around it?

Where each idea would live:
- **A**: inside UnrealEd, through exec commands over U2EdBridge.
- **B**: inside UnrealEd, by calling its internal C++ from the injected DLL.
- **C**: offline in Python or Blender, imported as T3D, ASE or a static mesh.
- **D**: in game, at runtime.

## Summary

1. **The cheapest big win is a kit, not a modeller.** A small modular kit with fixed metrics, one trim sheet and baked vertex colour, generated offline (C) and placed by the level generator as StaticMeshActors in T3D. This is the Bethesda kit approach (Burgess/Purkeypile) plus Insomniac's "Ultimate Trim", at a 2003 budget.
2. **UnrealEd already has most blockout operations as commands (A).** The vocabulary includes:
   - `BRUSHCLIP`, `BRUSH FROM INTERSECTION` and `BRUSH FROM DEINTERSECTION`;
   - `MERGEPOLYS` / `SEPARATEPOLYS`, `FLIPFACES`, `SMOOTH` / `UNSMOOTH`;
   - `BRUSH ADD` / `SUBTRACT` / `ADDVOLUME` / `ADDANTIPORTAL`;
   - `STATICMESH TO BRUSH`, `CreateStaticMeshFromBrush` and `SAVEBRUSHASCOLLISION`;
   - the ASE importer, including the `MCDCX` collision-hull prefix.

   The Hammer/TrenchBroom core (clip, carve, merge, convert) therefore needs recipes in `uedlib.py`, not DLL work.
3. **Do real polygon modelling offline (C).** Blender BMesh, Geometry Nodes, building_tools, Manifold booleans, xatlas, QEM decimation and CoACD hulls cover UE5 Modeling Mode at the fidelity this engine shows. Keep B for what only the editor can do: reading the CSG result, light and bake write-back, and selection.
4. **UE2 brush rules are looser than Quake's, but not free.** UnrealEd's CSG filters each brush polygon through the world BSP, so a closed concave brush is legal; the stock stair builders emit concave solids. This is an inference, not documented. Each polygon must still be planar and convex with at most 16 vertices (`FPOLY_MAX_VERTICES`, from memory; verify). A generator that emits convex, on-grid, axis-aligned brushes gets far fewer BSP holes. Large or complex shapes should be static meshes.
5. **AI image-to-3D (Hunyuan3D, TRELLIS) is for props and imposters, not architecture.** Its output needs decimation to 1–5k tris, re-UV and a bake. For kit pieces, code-driven modelling (Blender Python, LLM-written parametric scripts) gives clean, snappable geometry.

**Top 8, in order:**
1. kit + grid metrics;
2. trim sheet + automatic trim UVs;
3. brush recipes over A (clip, intersect, merge, convert);
4. a convex-brush emitter with validation in the T3D generator;
5. vertex-colour AO/light bake for static meshes;
6. decimate + LOD + collision-hull chain;
7. WFC/grammar placement of kit pieces;
8. LLM-written parametric props.

## Concept table

Effort: S = a day or two, M = about a week, L = several weeks. Value is for level remixes.

| # | Concept | Best-known implementation | Where | Effort | Value |
|---|---|---|---|---|---|
| 1 | Blockout / greybox | Level Design Book | A (BSP from T3D) | S | High (already the base) |
| 2 | Grid metrics, snapping | Doom/Quake metrics, LDB | C + A (BRUSHSNAP) | S | High |
| 3 | Modular kit (loopback/stack/gap tests) | Skyrim/Fallout kits, GDC 2013 | C + T3D placement | M | **Very high** |
| 4 | Brush clip | Hammer clip, UnrealEd BRUSHCLIP | A | S | Medium |
| 5 | Carve / CSG subtract | Hammer carve, TrenchBroom | C or A | S–M | Medium |
| 6 | Intersect / deintersect | UnrealEd BRUSH FROM (DE)INTERSECTION | A | S | Medium |
| 7 | Vertex/edge/face edit | Hammer vertex tool, TrenchBroom, VERTEXEDIT | C → T3D; A for fixes | M | Low–medium |
| 8 | 2D shape → solid (extrude, revolve) | UnrealEd 2D Shape Editor, ProBuilder Poly Shape | C | S | Medium |
| 9 | Extrude/inset/bevel/loop cut/bridge | Blender BMesh, UE5 PolyEdit, ProBuilder | C | S to use, L to rebuild in B | Medium |
| 10 | Half-edge / BMesh topology | OpenMesh, BMesh, FDynamicMesh3 | C | – | Enabler |
| 11 | Robust mesh boolean | Manifold (manifold3d), Blender Exact | C | S | Medium |
| 12 | Brush ↔ static mesh | CreateStaticMeshFromBrush, STATICMESH TO BRUSH | A | S | High |
| 13 | Merge coplanar / weld / triangulate | MERGEPOLYS, bspMergeCoplanars, Blender | A + C | S | Medium |
| 14 | Smoothing groups / split normals | ASE *MESH_SMOOTHING | C (ASE writer) | S | Medium |
| 15 | Shape grammar (CGA) | Müller et al. 2006, CityEngine | C | M | High (towns) |
| 16 | Procedural building add-on | building_tools (installed) | C | S | Medium–high |
| 17 | Node-graph modelling | Houdini, Geometry Nodes | C | M | Medium |
| 18 | Wave function collapse (3D tiles) | mxgmn WFC, Townscaper, Bad North | C → T3D | M | High |
| 19 | Trim sheets | Insomniac "Ultimate Trim", GDC 2015 | C | M | **Very high** |
| 20 | Auto UV / lightmap atlas | xatlas, Blender Smart UV | C | S | Medium |
| 21 | QEM decimation, LOD | Garland & Heckbert 1997, meshoptimizer | C | S | High (AI props) |
| 22 | Vertex-colour AO/light bake | Blender bake to Color Attribute; our !bakeload | C or B | S–M | High |
| 23 | Normal/AO bake high → low | Cycles bake (retopo_bake.py exists) | C | S | Medium |
| 24 | Convex decomposition collision | CoACD, V-HACD; UE2 MCDCX_ / SAVEBRUSHASCOLLISION | C → ASE | S | High |
| 25 | Image-to-3D | Hunyuan3D-2 (installed), TRELLIS | C | S | Medium |
| 26 | Learned low-poly meshing | MeshAnything V1/V2 | C | – | Low (rejected locally) |
| 27 | LLM-written modelling code | Text-to-CadQuery, CAD-Coder (2025) | C | S–M | High |
| 28 | Cube-grid modelling | UE5 CubeGrid | C (voxels → boxes → brushes) | M | Medium |
| 29 | Terrain erosion, splat maps | World Machine/Gaea; UE2 TERRAINEDIT | C + A | S | Medium |
| 30 | Runtime mesh edits | UE5 Geometry Script runtime | D | L | Low–medium |

## Deeper notes on the top 8

### 1. Modular kit with grid metrics (C + T3D placement)

The Bethesda practice: a fixed snap grid, pieces that connect on every side, and variants on the same footprint. The Level Design Book adds three kit stress tests (loopback, stack, gap) and warns that a first kit is hard to use.

For us:
- One power-of-two module: 256 or 512 wide, 256 or 384 storey height. Doors, corridors and stair rises divide into it.
- About 20 pieces per theme: wall, wall+door, wall+window, corner in/out, floor, ceiling, stair, ramp, pillar, trim cap, broken variants.
- Pieces exported as ASE with collision, or authored as brushes and frozen with CreateStaticMeshFromBrush.
- The generator places StaticMeshActors in T3D. That means no CSG and no BSP holes; the BSP keeps only the hull and the zone portals. Big static-mesh interiors need antiportals or zones (`Brush AddAntiPortal`).

### 2. Trim sheet + automatic trim UVs (C)

Paint one texture as horizontal strips (panels, bevels, caps), then UV every mesh onto them. Bevels get hard edges, and no UV island straddles two normal directions.
- One 1024² trim plus one 512² tiling texture can skin a whole kit.
- The fork's `pbr=HASH` rule can add normal and PBR maps.
- Implementation: a Blender bmesh script (about 200 lines) classifies faces by orientation and edge length, assigns each to the trim strip of matching height, and scales U to world length.

### 3. Brush recipes over the command layer (A)

| Hammer | Unreal |
|---|---|
| clip | BRUSHCLIP (needs 2 clip markers and a focused viewport) |
| carve | native subtract at CSG time |
| vertex edit | VERTEXEDIT, but better: compute vertices offline and re-import |

Recipes for `uedlib.py`:
- `clip(brush, plane)`;
- `freeze(selection) -> staticmesh`;
- `collision_from_builder()`;
- `merge_coplanar()` after every generated room.

Known gotchas:
- only the first BRUSH LOAD per session takes effect;
- BRUSH SCALE acts on selected brushes only;
- a Brush brought in with MAP IMPORTADD isn't carved by MAP REBUILD.

### 4. Convex-brush emitter with validation (C → T3D)

UnrealEd's CSG (`bspBrushCSG`) accepts closed concave solids. Still required:
- planar, convex polygons with at most 16 vertices;
- outward winding;
- a closed solid, or the Sheet flag;
- vertices on the grid.

UDN's advice against holes: grid snap on, modular units, simple BSP, no rotated brushes.

Emitter rules:
1. Decompose shapes into convex cells (boxes and prisms, plane-clip slopes, CoACD for odd shapes).
2. Snap vertices to integer UU.
3. Validate before writing:
   - planarity within 0.1 UU;
   - convex polygons of 16 vertices or fewer;
   - a closed manifold;
   - no zero-area faces;
   - no vertices closer than 1 UU.
4. Prefer whole-room subtracts plus a few adds. Bake any rotation into the vertices.
5. After import, read back with EDIT COPY and diff the polygon count.

### 5. Vertex-colour AO/light bake (C, with B write-back)

UE2 static meshes carry per-vertex colour.
- **Asset-level:** Blender "Bake to Color Attribute" AO, exported in the ASE. Subdivide big flat faces first so the AO has vertices to land on.
- **Scene-level:** the existing `!bakeload` hook writes bounce light into instance colours.

The two stack.

### 6. Decimate + LOD + collision (C)

- **Decimate:** QEM (Garland & Heckbert 1997). meshoptimizer's `meshopt_simplifyWithAttributes` can lock border vertices so kit pieces still meet.
- **LOD:** UE2 static meshes have no LOD chain, so use cull distances or imposter cards.
- **Collision:** per-triangle by default; a collision model comes from `SAVEBRUSHASCOLLISION` or `MCDCX_*` hull objects in the ASE. The UseSimpleBox / Line / Karma flags choose which one a query uses.
- **Pipeline:** CoACD per prop, up to about 8 hulls, written as `MCDCX_n` in the ASE. Keep weapon traces per-poly.

### 7. WFC and shape grammar for kit placement (C → T3D)

- **WFC** with constraint propagation. Corner-based (dual-grid, Townscaper-style) tiles turn a 2-state occupancy grid into about 16 module cases. The story-beat spine fixes the anchor rooms, and WFC fills the space between them.
- **CGA-style splits** for Avalon's buildings: mass, then floors, then bays, then kit facade pieces. building_tools or a 300-line grammar can do this.

### 8. LLM-written parametric props (C)

Modelling as code generation (Text-to-CadQuery, CAD-Coder 2025). Locally, scripted buildings scored 0.70–0.81 silhouette IoU against 0.68–0.92 for Hunyuan. They lose on thin, complex shapes but give clean, low, snappable geometry.

The practical form:
1. A bmesh library of parametric primitives: chamfered box, pipe run, I-beam, railing, ladder, tank, hatch, panel inset, bolt ring.
2. The LLM writes calls to it from a reference image and a size anchor.
3. `tools/fidelity.py` scoring drives a parameter search.
4. Every result goes through trim UV, AO bake and collision.

## Other notes

- **Modern editors:**
  - Hammer: block, clip, vertex tool, carve.
  - Hammer++: the same, with quality-of-life features.
  - TrenchBroom: validity-preserving vertex edits, CSG merge/subtract/intersect.
  - Source 2 Hammer and UE5 Modeling Mode both moved to polygon meshes: PolyGroup Edit, booleans, CubeGrid, UV, bake, collision. Geometry Script exposes these ops to scripts.
  - ProBuilder: extrude, bevel, poly shape; booleans still experimental.
- **What blockout designers use most:**
  1. block placement on a grid;
  2. clip;
  3. extrude / push-pull;
  4. vertex snap;
  5. duplicate / array;
  6. simple subtract;
  7. convert to mesh.

  Bevel, loop cut and bridge are art-pass tools.
- **Data structures:** half-edge assumes manifold surfaces; BMesh allows non-manifold geometry. UE2's FPoly lists have no adjacency, so edit offline and re-import. ASE stores smoothing groups per face and vertex colours.
- **AI 3D budget:** Hunyuan and TRELLIS give dense meshes with baked-in lighting. The working route is decimate + re-UV (xatlas or Smart UV) + bake from the high-poly.
- **Terrain additions:** hydraulic/thermal erosion before quantising to G16; splat maps from slope, height and flow; deco layers on the same masks.

## Claims checked (2026-10-08)

Checked two ways: statically in the decompiled Editor.dll (local `U2_research\ghidra\MODELLING_HOOKS.md`), and in game with `tools/C/U2EdBridge/tests/claims.py`. That script builds a test map through the editor, then the pilot drops the player above each shape and reads where it comes to rest.

| Claim | Code says | Game says | Verdict |
|---|---|---|---|
| Closed concave brushes are legal | `bspBrushCSG` / `csgRebuild` have no convexity test or split | L block with split caps: lands on both arms, falls through the notch to the floor | **true** |
| Polygons must be convex | Not checked on import; convexity is only tested in the coplanar-merge helpers | L with single concave 6-vertex caps: arms and notch collide correctly | **concave caps work for collision.** Rendering and lighting of concave faces weren't checked, so keep faces convex |
| At most 16 vertices per polygon | The FPoly holds 32; vertices past 32 are silently dropped | 20-sided pillar: lands on its top cap | **refuted: the limit is 32** |
| `MCDCX_` hulls are the collision | Only `MCDCX*` names count; they become a triangle collision model (not convex hulls). Line/box checks use it only when the simple-collision flags are set | Box 64 high with a 512-high `MCDCX_` hull: the player stands at 512, even with no flags set | **true for player movement** (default flags). Weapon traces were not tested |
| Brushes imported with `MAP IMPORTADD` get built | – | Not built ("Nodes: 0 -> 0") | **refuted.** Brushes go through the builder brush: `BRUSH IMPORT FILE=` (a T3D PolyList), `MOVETO`, `ADD`/`SUBTRACT` |

Other gotchas from the test:
- Editor paths must have no spaces; use the 8.3 short path.
- `SET <Class> prop` also changes the class default, so objects created afterwards inherit it.
- The ASE writer negates X, which flips the triangle winding: faces must be reversed, or the collision faces point inward and the player falls through.

## Open checks

- Confirm `FPOLY_MAX_VERTICES` and the planarity tolerance in Editor.dll (Ghidra).
- Test whether `MCDCX_` hulls work as collision in this pre-UT2003 build.
- Find the BRUSHCLIP marker workflow from Editor.log `Cmd:` lines.

## Confidence

- **Inferred, not documented:** that closed concave brushes are legal.
- **From memory, unverified:** the 16-vertex limit.
- **Confirmed by local strings but not run:** the editor commands.
- **Not opened:** the TrenchBroom manual and V-HACD links (standard URLs).
- **Not quoted:** UDN pages that failed to load.

## Sources

- Valve wiki: Reshaping solids https://developer.valvesoftware.com/wiki/Reshaping_solids ; Vertex Tool https://developer.valvesoftware.com/wiki/Hammer_Vertex_Tool ; Concave https://developer.valvesoftware.com/wiki/Concave ; TWHL https://twhl.info/wiki/view/2912 ; Source 2 mesh editing https://developer.valvesoftware.com/wiki/Source_2/Docs/Level_Design/Basic_Construction/Mesh_Editing_1
- TrenchBroom https://github.com/TrenchBroom/TrenchBroom ; GtkRadiant CSG https://en.wikibooks.org/wiki/GtkRadiant/The_CSG_Tools
- UE5 Modeling Mode https://dev.epicgames.com/documentation/en-us/unreal-engine/modeling-mode-in-unreal-engine ; Geometry Script https://dev.epicgames.com/documentation/en-us/unreal-engine/geometry-scripting-users-guide-in-unreal-engine ; ProBuilder https://docs.unity3d.com/Packages/com.unity.probuilder@6.0/manual/menu.html
- UDN Two: BSP brushes https://docs.unrealengine.com/udk/Two/BspBrushesTutorial.html ; brush clipping https://docs.unrealengine.com/udk/Two/BrushClipping.html ; static mesh collision https://docs.unrealengine.com/udk/Two/StaticMeshCollisionReference.html ; collision tutorial https://docs.unrealengine.com/udk/Two/CollisionTutorial.html ; static meshes from Maya https://docs.unrealengine.com/udk/Two/StaticMeshesFromMaya.html ; BSP optimisation https://docs.unrealengine.com/udk/Two/LevelOptimizationBSP.html
- Unreal Wiki archive: UnrealEd console https://unrealarchive.org/wikis/unreal-wiki/Legacy:UnrealEd_Console.html ; Building with CSG https://unrealarchive.org/wikis/unreal-wiki/Legacy:Building_With_CSG.html ; Vertex editing https://unrealarchive.org/wikis/unreal-wiki/Legacy:Vertex_Editing.html
- Burgess & Purkeypile, Skyrim's modular approach https://www.gamedeveloper.com/design/skyrim-s-modular-approach-to-level-design ; Level Design Book https://book.leveldesignbook.com/process/blockout/metrics/modular
- Olsen, The Ultimate Trim (GDC 2015) https://gdcvault.com/play/1022323/The-Ultimate-Trim-Texturing-Techniques
- Müller et al. 2006 https://course.ccs.neu.edu/cs5150f13/readings/muller_buildings.pdf ; WFC https://github.com/mxgmn/WaveFunctionCollapse ; marian42 https://github.com/marian42/wavefunctioncollapse ; Townscaper https://www.gamedeveloper.com/game-platforms/how-townscaper-works-a-story-four-games-in-the-making ; building_tools https://github.com/ranjian0/building_tools
- Garland & Heckbert 1997 https://www.cs.princeton.edu/courses/archive/fall06/cos526/papers/garland97.pdf ; meshoptimizer https://github.com/zeux/meshoptimizer ; xatlas https://github.com/jpcy/xatlas ; CoACD https://github.com/SarahWeiii/CoACD ; V-HACD https://github.com/kmammou/v-hacd ; Manifold https://github.com/elalish/manifold ; half-edge https://cs184.eecs.berkeley.edu/sp19/article/15/the-half-edge-data-structure ; BMesh https://docs.blender.org/api/4.4/bmesh.html
- Hunyuan3D-2 https://github.com/Tencent-Hunyuan/Hunyuan3D-2 ; TRELLIS https://github.com/microsoft/TRELLIS ; MeshAnything https://arxiv.org/abs/2406.10163 ; Text-to-CadQuery https://arxiv.org/abs/2505.06507 ; CAD-Coder https://arxiv.org/abs/2505.19713
