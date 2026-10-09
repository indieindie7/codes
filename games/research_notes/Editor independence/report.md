# Editor independence: do UnrealEd's jobs inside the running game

Research report, 2026-10-08 (Avalon queue Q58). Nothing was run, built or installed for this. Sources: the repo docs
(`tools/C/U2EdBridge/README.md`, `EDITOR_OPS.md`, `LIGHTING.md`, `src/editor_ops.c`;
`games/unreal2_mods/U2GM/README.md`), the fork (`d3d8to9-gi/source/u2shaders.hpp`), the game's own
exported UnrealScript (`Documents/Tools/u2_export/full_Engine/Classes`) and the export table of the
game's own `System/Engine.dll` / `Core.dll` (read by a small PE parser). No leaked engine source was used.

The user's note: "drill into engine improvements to make us less dependent of unreal editor or just
port it inside this game". The rule: the better and the less gameplay-disruptive, the better.

Labels: **verified** = in our docs/decompile or the export table; **guess** = test first.

## 0. Short answer

Don't port the editor. Port the **four engine calls we actually need** into the game process, where
the fork's `d3d8.dll` already runs native Engine.dll code (gmterrain: `SetHeightmap`/`CalcVertices`/
`UpdateVertexBuffers`, u2shaders.hpp ~2429-2475; U2Live: `UViewport::Exec`, ~2042-2081). Key facts:

1. **Baked BSP light is recomputed from stored shadow bits whenever a lightmap's cache is rebuilt** (LIGHTING.md 1.2-1.4).
   BSP texels = zone ambient + each light's colour x its visibility bitmap, made by
   `FLightMap::GetTextureData` and cached by revision. So *colour, brightness and ambient* changes
   to existing lights need no editor, only a cache refresh. Only *new or moved shadows* need a bake.
   That explains "live zone ambient changes do nothing visible": the cached lightmaps are never
   rebuilt (guess; the cheapest test: section 3, step 1).
2. **The light bakers and the path builder live in Engine.dll, not Editor.dll** (verified exports):
   `UStaticMesh::Illuminate`, `UTerrainPrimitive::Illuminate`, `UModel::Illuminate`,
   `UTerrainSector::StaticLight`, `FLightMap::GetTextureData`/`GetRevision`, and
   `FPathBuilder::definePaths` / `defineChangedPaths` / `undefinePaths` / `buildPaths`. Also
   `UEngine::Flush`, `GCache`, `AActor::ClearRenderData` (also a script native, Actor.uc:1111),
   `ULevel::FarMoveActor`, `AZoneInfo::PostEditChange`. Only the BSP/CSG builder and the light-list
   builder (`FEditorVisibility`, "TestLights/FormLights") are editor-only.
3. `ZoneInfo.AmbientVector` is a plain writable script var (ZoneInfo.uc:36), next to
   `AmbientBrightness/Hue/Saturation` (:37). `Actor.bLightChanged` is a transient script var (Actor.uc:219).

## 1. Inventory: what we use UnrealEd for today

| # | Job | Where (repo) | How often it blocks live work |
|---|---|---|---|
| E1 | **Static light bake**: BSP lightmaps, static-mesh vertex light, terrain vertex light (`LIGHT APPLY`, ~20 s on TutA, 19 s of it CPU rays) | LIGHTING.md 1, 1.6; gm_commit `!light`/`LIGHT APPLY CHANGED=1` | Every light edit, carve, commit. Live stand-in: dynamic `GMLight` (no shadows, 8 lights per actor). **Highest** |
| E2 | **Light leaf lists** (`MAP REBUILD` -> TestLights/FormLights): a new or moved light reaches nothing until a rebuild, and after it a full relight | LIGHTING.md 1.1, 7.2 | Every new baked light |
| E3 | **Zone ambient per zone** (`!setprop`; `SET ZoneInfo` is class-wide) | EDITOR_OPS 3b, LIGHTING 7.3 | Mood/weather/darkness tuning; live changes don't show on baked surfaces |
| E4 | **BSP geometry / CSG / zones and portals** (`MAP REBUILD`, `BRUSH LOAD`, U2Model add/cut) | uedlib `rebuild`, `load_brush`; U2Model | Carves, new rooms |
| E5 | **Making edits permanent** (`MAP SAVE` as `<Map>_LiveN`, then `gm travel`) | U2GM README "Commit" | Every commit: editor start (~7 s) + bake + reload; the bridge is the fragile part |
| E6 | **AI paths** (`PATHS DEFINE`; `PATHS BUILD` > 5 min on T3D-imported copies of stock maps) | uedlib `paths()`, gm_commit `--paths` | When props should change routes |
| E7 | **Asset import**: textures, static meshes, terrain heightmap bake | uedlib, gm_commit terrain route, BUILDING_PIPELINE.md | Per new asset; terrain only at commit |
| E8 | **Inspection data for our tools**: `MAP EXPORT` T3D, `!meshverts`, `!lightsat`/`!lights`, viewport shots | EDITOR_OPS 3, 3b; LIGHTING 7.5 | Each bake/diagnosis; `MAP EXPORT` writes nothing on some maps (TutA, 2026-10-08) |
| E9 | (not the editor, same pain) **Script package install needs a game restart** | U2GM README Install | Every UnrealScript change |

Already editor-free: actor move/turn/scale/hide/spawn (U2GM), terrain sculpt (fork gmterrain), texture look
(texedit/`replace=`/`texadjust=`), dynamic lights, gore, weather/props (U2AvalonCards), new meshes via a new
package per change (`DynamicLoadObject` + `SetPropertyText("StaticMesh", ...)`, EDITOR_OPS 4).

## 2. Options per job, inside the running game

Effort in working days for one session; risk = chance it fails or destabilises the game.

### E3 + part of E1: ambient and existing lights' colour/brightness (no new shadows)
- **(a) Script + flush.** `gm ambient B H S` sets the zone bytes (and `AmbientVector`), then
  `ConsoleCommand("FLUSH")` for BSP and `ClearRenderData()` on the zone's actors (ambient is added at draw time,
  LIGHTING 1.3/7.1). **0.5 day.** Risk low; FLUSH re-uploads every texture (a hitch, fine for a GM action).
- **(b) Native, no hitch.** From the fork: bump the revision of the changed zone's `FLightMap`s only;
  terrain: `UTerrainSector::StaticLight(1)` per sector (gmterrain's `UpdateVertexBuffers(..., relight=1)`
  already does this). **1-2 days.** Risk low-medium (offsets).
- **(c) Existing static Light's brightness/hue** (flicker, brownout, power cut on baked lights): change the
  property, set `bLightChanged`, flush/bump. Meshes re-fill colours only when the light's `Applied` flag
  disagrees (LIGHTING 7.1), so they need the StaticLight hook of E1(c). **+1 day.** Shadows stay as baked.

### E1: new or moved light with shadows
- **(a) Keep dynamic GMLight (today).** Lose: shadows, 8-light cap, bake look.
- **(b) Fork screen-space lights** in the GI pass (`gi=1`, u2shaders.hpp ~6938-7700, `GBufPS`/`LightPS`) with
  a short screen-space shadow march. **3-5 days.** Risk medium (off-screen occluders cast nothing). Visual only.
- **(c) U2Bake in the game.** Port the scene dump (`!meshverts`), the `BakeStaticLight` hook and `!lightsat`
  from `editor_ops.c` into a game-side native module; `bake.py` runs in the background (2-4 s full, 0.6 s
  incremental), colours go into the static-mesh streams and terrain sector colours. **1-1.5 weeks.** Risk medium.
  Lose: BSP shadows (not in the baker's scene yet); calibration against UE2's falloff (7.4).
- **(d) Engine's own bakers in the game** (`UStaticMesh::Illuminate`, `UTerrainPrimitive::Illuminate`): blocked
  by E2 (they only see lights already in the leaf lists). **2 days** after E2(b). `UModel::Illuminate` (BSP)
  renders into a "LightingViewport" with readback through our wrapper: **risk high**, not recommended.
- **(e) BSP lightmap override**: hook `FLightMap::GetTextureData` and add our texels, baked from `lmcapture=1`
  geometry. **1.5-2 weeks.** Risk medium-high.

### E2: light leaf lists
- (a) Avoid them live (dynamic / screen-space lights).
- (b) Native: rebuild `Model->Lights` with the new light added to every leaf within its radius and zone
  (distance + zone test instead of portal filtering). **2-3 days.** Risk medium (wrong list = black actors).

### E4: BSP geometry
- No realistic in-game option (the CSG builder is not exported). Build with static meshes (U2Model freeze,
  `GMMesh`); keep brush work in UnrealEd.

### E5: making edits permanent
- (a) The journal is the save format (map + journal + fork overrides, all re-applied on load). **0 days**; stop
  treating `gm commit` as needed for play. Lose: a standalone `.un2` without our mods.
- (b) `gm commit` stays the rare "export/ship" step.

### E6: AI paths
- (a) Native `FPathBuilder::defineChangedPaths(Level)` from the fork at a GM pause, off by default, GM maps only.
  **2-3 days.** Risk medium-high (AI route caches, scripted sequences).
- (b) Today: GM waypoints / AIScript. Zero risk.

### E7: asset import
- Textures: the fork covers the look; real UE2 texture objects still need ucc/editor.
- Static meshes: `ucc` with `#exec STATICMESH IMPORT`, or a new package per change loaded live.
- Terrain heightmap: already live in the fork; only commit exports it.

### E8: inspection
- Port `!lightsat`/`!lights` into the fork (level found via `GObjObjects`, as terrain and GoreLink do) and show
  "why is this spot dark" (zone, ambient, lights in reach) in the GM panel. **1 day.** Risk low (read-only).

### E9: script package without restart
- **Versioned packages**: build `U2GM_b<N>.u`, copy to `System` (a new file, no lock), reload the map with
  `?Mutator=U2GM_b<N>.GMMutator`. Config sections are named after the package, so the journal must live in a
  stable tiny package (`U2GMStore.u`) or be read by the fork. **1 day.** Risk low. Delete stale `_b*` at start.
  (The same scheme would work for U2AvalonCards, whose config would need the same split.)

## 3. Ranked plan (least disruption, best value first)

1. **Live ambient + baked-light colour, by script (0.5 day, zero gameplay effect).** `gm ambient B H S` on the zone
   under the crosshair (journal `@family ambient ZONE B H S`), set bytes + `AmbientVector`, `ClearRenderData()` on
   the zone's actors (`ZoneActors`, ZoneInfo.uc:88), then `FLUSH`. Test on TutA which surface kinds change. Same for
   `gm lightcolor NAME B H S`. Answers E3 and "ambient does nothing".
2. **Versioned script packages (1 day).** No restart per script iteration; speeds up everything after it.
3. **Native refresh + in-game diagnostics in the fork (2-3 days).** Per-zone lightmap revision bump (no hitch),
   terrain `StaticLight(1)`, the static-mesh StaticLight hook, `!lightsat` in the GM panel.
4. **Screen-space GM lights in the fork (3-5 days).** Journal lights drawn per pixel with screen-space shadows;
   `gm commit` still bakes real ones when shipping. Visual only.
5. **U2Bake in the game for static meshes + terrain (1-1.5 weeks; after 3).** Later, optional: BSP texels via
   `GetTextureData`, and in-game `defineChangedPaths` behind a flag (the only gameplay-visible item, so last).

After 1-4 the editor is needed only to ship a map and for BSP; after 5, only for BSP, paths (unless E6a) and shipping.

## 4. What still needs the editor, honestly

- **BSP / CSG / zones and portals.**
- **Baked shadows of new lights on BSP, done the engine's way** (GPU readback pass + real leaf lists).
- **A standalone `.un2`** that runs without our mutators and fork (sharing). Keep `gm commit` for that, rarely.
- **Correct path networks on big changes** (in-game `defineChangedPaths` unproven).
- **New UE2 asset objects** (textures, materials, static mesh packages).

Cheaper editor while it's still needed (0.5 day each): load the bridge with a proxy DLL that only acts inside
`UnrealEd.exe` instead of `u2edinject.exe` (what Defender flagged); use the native dump (`!meshverts`, `!list`)
or `ed.actors()` instead of `MAP EXPORT`; never `LIGHT APPLY SELECTED=1` (it is a full relight).

## 5. First tests (in this order)

1. TutA: `gm ambient 0 0 0` then `FLUSH`, screenshot the tower before/after; then `gm ambient 60 150 80`. Note which
   surface kinds changed (BSP, static mesh, terrain, pawns).
2. Same with one placed Light's `LightBrightness` (via `SetPropertyText`) + `bLightChanged=True`.
3. Versioned package: build `U2GM_b1`, reload the map with it, check `U2GM.ini` still feeds the journal.
4. Fork: `GetProcAddress` the exports named in section 0 and log them at startup (read-only check).

Open questions: that FLUSH + `ClearRenderData` makes ambient changes show on baked surfaces is untested (step 1).
The docs disagree on `PATHS BUILD` on imported maps (>5 min vs crash).
