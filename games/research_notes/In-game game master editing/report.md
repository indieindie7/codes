# In-game "game master" editing for Unreal II (and Advent Rising)

Research report, 2026-10-07. No game, editor or install was run.
- **Verified** means read from `Documents\Tools\u2_export\full_Engine` or from the export table of U2's Engine.dll (Ghidra copy).
- **Guess** means test it first.
- The prior-art descriptions are from general knowledge and were not re-checked online.

## 0. Recommendation

**One op journal is the source of truth.** Each GM action is applied live in the game and committed later in the editor. This follows Dreams' edit list and Cube 2's small edit messages.

- **Op examples:** `spawn`, `move`, `turn`, `scale`, `hide`, `light`, `terrain raise x y r h`, `mesh place pkg.name`, `possess`, `event`.
- **Starting point:** AvalonEditor's `Ops[]` journal.
- **Storage rule (from the level team, 2026-10-07):** the running game rewrites its whole config ini from memory on every SaveConfig, so external edits to an ini the game holds are lost. Keep the journal in its own file (append-only, written by the game or by tools while the game only reads it), never patched into a game-owned ini.

| layer | does |
|---|---|
| (c) UnrealScript GM mode | camera, pick, transform, palette, possess, freeze, events, GM lights, journal, undo |
| native core in the fork | terrain via `ATerrainInfo::SetHeightmap`/`Update`; later `UStaticMesh::Build`; fast command path |
| (b) fork overlay | ImGui panel, ImGuizmo, brush circle, ghost previews; input gated through U2Input |
| (a) UnrealEd beside the game | commit: `!move`/`!light`, terrain import, `MAP REBUILD` only for brushes, U2Bake, `<Map>_LiveN`, ClientTravel |
| (d) companion app | optional second-monitor panel; Blender for real modelling |

## 1. Prior art: the lessons

- **Vampire: Redemption storyteller mode:** mood tools (light, sound, music) and possession are core GM verbs.
- **NWN DM Client:** the GM works inside fixed geometry and prepares things in "limbo" before revealing them.
- **Arma 3 Zeus:** the closest analogue. Free camera, place units and modules, draw waypoints, remote-control a unit, a spending budget.
- **Halo Forge:** one button switches between playing and editing in a running match. Grab-and-carry placement, plus a precision mode.
- **Garry's Mod:** direct manipulation with the physgun and toolgun; per-action undo always works.
- **Cube 2:** octree push/pull editing in game; co-op edits are sent as tiny ops.
- **CryEngine Sandbox / Unreal PIE:** the editor and the game run in one process, so there is zero latency. Their "eject" plus "keep simulation changes" is our commit.
- **UE5 Modeling Mode / Geometry Scripting / Multi-User / UEFN live edit:** a runtime mesh object is kept apart from cooked meshes, and transactions are the unit of sync.
- **Roblox Team Create:** one uniform object model means one property panel works everywhere.
- **Dreams:** signed-distance edit lists are the asset itself: small, undoable, and re-evaluable.
- **Teardown:** voxels make editing trivial but need their own renderer.
- **Minecraft / Valheim:** snapping and a ghost preview; a "level the ground here" brush.
- **Tabletop Simulator:** rewind serves as undo, and locking objects prevents accidents.
- **Foundry VTT:** layers, prepare hidden then reveal, a macro hotbar.

**Common recipe:**
1. One key toggles between play and GM mode.
2. Free camera plus possession.
3. A palette with ghost preview and snapping.
4. A gizmo plus numeric entry.
5. An undo log that always works.
6. Prepare hidden, then reveal.
7. Mood and behaviour tools count as much as geometry.
8. Edits are small ops replayed everywhere.
9. A budget.

## 2. What U2 can change at runtime

- **Actors:** script can spawn, move, scale, change the draw type and collision, and use `SetPropertyText`. Map statics are swapped for movable copies.
- **Static mesh assets:**
  - Script can use existing meshes, or load a new package per change via `DynamicLoadObject`.
  - Natively, `UStaticMesh::Build` is exported. Guess: building a transient mesh works.
- **Terrain:**
  - There are no script natives in U2 or Advent (`PokeTerrain` came later, in UT2004).
  - Exported: `SetHeightmap`, `Update`, `GetHeightmap`, `SetLayerAlpha`, `UpdateVertexBuffers`, `WorldToHeightmap`, `LineCheck`/`PointCheck`.
  - Guess: collision follows the edited heightmap.
  - Lighting goes stale; fix it with U2Bake terrain colours.
- **BSP:** editor only.
- **Lights:**
  - Only dynamic lights can change at runtime, at most 8 per actor.
  - Static lights need an editor relight.
- **AI paths:**
  - Editor only (`PATHS BUILD`).
  - Live encounters use GM waypoints, direct moves and `AIScript`.
- **Water:** `FluidSurfaceInfo` is a live height grid that the engine renders and collides with. Guess: usable as a sculptable patch.
- **GM verbs in `CheatManager`:** `Ghost`, `Fly`, `Avatar`, `PlayersOnly`, `SloMo`, `CauseEvent`, `Summon`, `FreeCamera`, `CheatView`. The HUD has `Draw3DLine`.
- **Three routes to live meshes:**
  1. A new package per change. Works now; takes seconds.
  2. `UStaticMesh::Build` in process.
  3. The fork draws the geometry itself, with invisible box or cylinder collision proxies.

## 3. Techniques

- **Terrain brushes:**
  - Raise, lower, flatten, smooth, noise, level-here, and a ramp between marks.
  - Ported from `terrain_cutfill.py` and `island_form.py`, followed by `Update` on the touched region.
  - Live layer painting through `SetLayerAlpha`.
- **Signed-distance edit list:**
  - Add, subtract and smooth blend.
  - Meshed with surface nets, dual contouring or marching cubes, then cleaned with meshoptimizer.
  - Delivered through mesh route 2 or 3, and written as ASE for the commit.
- **CSG:** Manifold first; Godot CSG as a reference.
- **Cube 2's push/pull gesture**, copied onto our own grid.
- **The prefab kit (`build_parts.py`)** as the main GM "modelling", via pre-baked packages.
- **Lighting:**
  - Live: U2Bake probes into `AmbientGlow`, and GM fill lights with `bSpecialLit`.
  - At commit: `!light`, `LIGHT APPLY CHANGED=1` and U2Bake.
- **AI at commit:** PathNodes from `walks.py`, then `PATHS BUILD`.

## 4. Options compared

- **(a) Editor beside the game.**
  - 5-30 s per change, with a visible reload.
  - Changes everything, including BSP and paths, with full lighting and real persistence.
  - Mostly built already; the risk is editor crashes.
  - Use it for commit and preparation.
- **(b) Fork overlay.**
  - One frame of latency, but for drawing only.
  - No persistence until commit; collision only through proxies.
  - Best GM feel; 1-2 weeks of work. The risk is handing the cursor and input over.
- **(c) In-game UnrealScript.**
  - 0.1-2 s, or one frame with the fast path.
  - Real actors, collision and AI; dynamic lights only.
  - Days of work, since AvalonEditor exists.
- **(d) Companion app.**
  - Latency of the live channel.
  - Good for a second screen and for Claude.
  - A Blender sync would take weeks.

**Overlay details:**
- Draw ImGui after the HUD; the fork already detects `posthud`.
- ImGuizmo uses the fork's view and projection matrices.
- Picking: cast a ray through the inverse view-projection against scene depth, then confirm with a script `Trace`, or natively with `ULevel::SingleLineCheck` (guess).

**Fast channel:**
- The fork finds the GM object in `GObjObjects` and calls `FindFunctionChecked` + `ProcessEvent`.
- Guess: check that Core.dll exports both.
- That would cut latency from the 2 s file poll to about one frame. Keep the exec-file poll as the fallback.

## 5. Stages

1. **Week 1:**
   - Days 1-2: GM toggle with free camera, pick, palette spawn with snap, possess, freeze, undo/redo.
   - Day 3: one native terrain raise/lower/flatten brush; check that collision follows the new shape.
   - Days 4-5: ImGui panel, gizmo, ghost preview, input gating.
   - Days 6-7: a `commit` command that replays the journal into `<Map>_Live1`. Run the EDITOR_OPS.md test order on the ops DLL first.
   - Done means: raise a mound, drop three crates and a lamp, possess a marine, freeze, undo one crate, commit, and the reloaded map has all of it, lit.
2. **Stage 2 (1-2 weeks):** mood and behaviour tools.
   - Probe lighting into `AmbientGlow` live; fog and ambient sliders; sound cues.
   - Encounter ops, and a staged reveal on a hotbar key.
   - The `ProcessEvent` fast path.
3. **Stage 3 (2-3 weeks):** live geometry.
   - Reverse engineer `UStaticMesh::Build`, or fall back to `AvalonSM_liveN` packages.
   - The signed-distance sculpt kernel, Manifold for cutting, and live layer painting.
4. **End goal:**
   - A Forge/Zeus-style GM mode, committed into real maps between scenes, including AI paths and BSP.
   - Claude as co-GM proposes ops for approval.
   - Port to Advent after checking that its Engine.dll has the same exports.

## 6. Licences

- **Use:** d3d8to9 (BSD-2), Dear ImGui and ImGuizmo (MIT), Manifold (Apache-2.0), Godot CSG (MIT), Transvoxel tables (MIT), meshoptimizer (MIT), Recast (zlib), Cube 2 code (zlib, not its media), OpenVDB (Apache-2.0), libfive core (MPL-2), libigl core (MPL-2), Blender (GPL, as an external tool).
- **Usable with care:** Carve (GPL v2/v3; prefer Manifold), Cork (LGPL-3).
- **Avoid:** CGAL (GPL or commercial, and heavy).
- **No reuse:** U2, UT2004 and Advent sources (reference only); all the proprietary prior-art products; qUINT and iMMERSE.

## 7. First tests

1. The terrain exports in game: thread safety, whether collision follows, and whether `Update`'s last int means lighting.
2. Whether Core.dll exports `ProcessEvent` and `FindFunctionChecked`.
3. Which fields `UStaticMesh::Build` needs.
4. Handing the cursor between U2Input and ImGui.
5. The EDITOR_OPS.md test order.
6. Whether the vertex-colour write-back survives a reload.
7. The 32-bit memory budget for live packages and spawned actors.

## Sources

- [Alex Evans, SIGGRAPH 2015 (Dreams)](https://advances.realtimerendering.com/s2015/AlexEvans_SIGGRAPH-2015-sml.pdf)
- [Carve GPL licence (Blender list)](https://lists.blender.org/pipermail/bf-committers/2009-June/023558.html)
- [Transvoxel tables, MIT](https://docs.rs/transvoxel-data)
- Local files:
  - `U2Avalon/PIPELINE.md`
  - `U2EdBridge/EDITOR_OPS.md` and `LIGHTING.md`
  - `U2Bake/bake.py`
  - `d3d8to9-gi/source/u2shaders.hpp`
  - the `u2_export` classes (`TerrainInfo`, `Actor`, `HUD`, `PlayerController`, `CheatManager`)
  - the Engine.dll exports
