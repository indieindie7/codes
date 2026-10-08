# U2GM: game master mode for Unreal II

Change the level while it is played. This is week 1, days 1–2 of the plan in `games/research_notes/In-game game master editing/report.md`. It is script only.

## Install
Copy `Classes` to `<game>\U2GM\Classes`. Add `EditPackages=U2GM` to the `Unreal2.ini` you compile with, and run `ucc make`. Copy `U2GM.u` into `<game>\System` while the game is closed. Load it with `?Mutator=U2GM.GMMutator`, or add it to `User.ini`'s `Mutator=` line.

## Console
| command | does |
|---|---|
| `gm` / `gm on` / `gm off` | GM mode: free camera through walls, no damage |
| `gm pick [NAME]` | pick what's under the crosshair, or an actor by name |
| `gm info` | what is picked, journal size |
| `gm move DX DY DZ` | nudge the picked actor |
| `gm moveto X Y Z` / `gm moveto here` | put it at a point / under the crosshair, snapped |
| `gm turn DEG`, `gm scale S` | turn it round the vertical, size it |
| `gm hide` | hide it (a placed mesh is removed) |
| `gm spawn N` / `gm spawn Pkg.Group.Mesh` | place palette entry N or a mesh under the crosshair, snapped to the grid and the ground, facing you |
| `gm palette`, `gm palette add PATH`, `gm palette clear` | the spawn palette |
| `gm snap SIZE`, `gm yawstep DEG` | grid (0 = off) and yaw snap |
| `gm possess` / `gm release` | take over the character under the crosshair / go back |
| `gm freeze` | stop everything but the players (again: go on) |
| `gm undo` / `gm redo` | step back or forward through the journal; the world follows at once |
| `gm journal` | this map's journal lines |
| `gm raise R H` / `gm lower R H` | terrain under the crosshair up/down by H world units within radius R (cosine falloff) |
| `gm flatten R` | terrain within R pulled to the height under the crosshair |
| `gm smooth R` | terrain within R smoothed |

## The journal
Every edit is one line in `System\U2GM.ini` (`[U2GM.GMMaster] Ops[...]`). Only the game writes it; edit it only while the game is closed, because the game rewrites its ini from memory.
- Each line is tagged with its map family: `@tuta place StaticMeshActor112 X Y Z YAW SCALE`, `@tuta hide NAME`, `@tuta mesh Pkg.Group.Mesh X Y Z YAW SCALE`.
- This is AvalonEditor's format, so `U2Avalon/tools/live_bake.py` can bake a session into the map.
- The world is always the map plus its journal. Undo and redo change the journal and replay it.
- A map's static meshes can't move at run time, so the first edit swaps one for a movable copy (`GMMesh`, `AmbientGlow=70`) and hides the original.
- Terrain lines: `@tuta terrain raise|lower|flatten|smooth X Y R H` (world units: centre, radius, height; for flatten H is the target Z, for smooth the strength 0..1). Script can't reach the heightmap, so the d3d8 fork applies these (below). A terrain line goes in the slot after the last used one, so terrain lines stay in time order (they don't commute).

## Terrain brush (d3d8 fork, week 1 day 3)
The fork (`d3d8to9-gi`, `source/u2shaders.hpp`, "gmterrain") watches `System\U2GM.ini`. When it changes, or a map loads, the fork reads this map family's terrain lines and finds the level's `TerrainInfo` objects through Core's `GObjObjects`. The first time it touches a terrain, it keeps a copy of the original heightmap. Then it rebuilds the result as the original plus every line in order, so `gm undo`/`gm redo` just work. It writes only the heights that differ from what the engine holds (`ATerrainInfo::SetHeightmap`) and rebuilds only that rectangle, the same way UnrealEd's brushes do. `CalcVertices` remakes positions and normals, which collision reads. `UpdateVertexBuffers(..., relight)` remakes the sector vertex buffers and bounds, and redoes static lighting from the baked light visibility. The engine calls run from the game window's message loop, not mid-frame. Each application is logged to `System\U2Shaders.log` as `gm terrain: ...`.

From the Engine.dll decompile:
- `Update(float, X1, Y1, X2, Y2, bRelight)` is `CalcVertices(float, X1, Y1, X2, Y2)` plus `UpdateVertexBuffers(X1, Y1, X2, Y2, bRelight)`. In `CalcVertices` the ends are exclusive, and 0 for X2/Y2 means the full width/height. The float is never used.
- In the game (not in the editor), `Update` then unloads the heightmap's lazy array. That's why the fork calls the two halves itself: the heightmap stays in memory.
- Collision (`LineCheck` → `LineCheckWithQuad`) reads the `Vertices` array that `CalcVertices` refreshes. Nothing else needs updating.
- UnrealEd's brushes (`UTerrainBrush*::Execute`) call `GetHeightmap`/`SetHeightmap` on each selected vertex, then `UpdateFromSelectedVertices`, which is `Update(0, bounds, 1)`.

**Enable:** put the fork's `d3d8.dll` in `System`, and add `gmterrain=1` to `System\U2Shaders.ini`. It's off by default and never runs in UnrealEd. Turning it off doesn't restore the terrain until the map reloads. Only G16 heightmaps are handled (U2's terrains use them). A P8 heightmap is skipped with a log line.

**Test list** (the game running with U2GM loaded and the fork's d3d8.dll; keep `System\U2Shaders.log` open):
1. On a map with terrain (the Avalon or hills maps), type `gm on`, fly up, and aim the crosshair at the ground.
2. Type `gm raise 512 256`. The console says `terrain raise X Y 512 256 (line K ...)`. Within a few frames the log says `gm terrain: TerrainInfo0 ... original kept`, then `... 1 line(s) applied, N height(s) changed, rebuilt ...`. A smooth mound about 256 units high and 1024 across appears. Check that it's lit (not black or flat-shaded) and doesn't pop in and out at the edges of the view.
3. Type `gm off` and walk onto the mound. You should walk up its slope, not through it (collision). Shots should hit its surface.
4. Type `gm on`, then `gm undo`. The mound is gone and the log shows the heights put back. `gm redo` brings the mound back. Then type `gm undo` again.
5. Aim at a slope and type `gm flatten 400`. You get a round flat patch at the crosshair's height. `gm smooth 600` over its edge softens it, and `gm lower 300 128` digs a dip.
6. `gm journal` lists the terrain lines. Reload the map (`open <map>` or restart). The log says `gm terrain: N terrain line(s) for <map> (map loaded)` and the edits are back without typing anything.
7. Watch for:
   - a hitch when a large radius is applied (the ms in the log line)
   - seams between terrain sectors at the edge of the change
   - `flatten` at the wrong height (it should match where the crosshair was)
   - log lines with `skipped:` or `faulted`

## Next (week 1, days 3–7)
- **Day 3:** a native terrain brush in the d3d8 fork: built (above), not yet run in the game.
- **Days 4–5:** an ImGui panel and gizmo drawn by the fork.
- **Days 6–7:** `gm commit`, which replays the journal into `<Map>_Live1` through UnrealEd and relights.
