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

## The journal
Every edit is one line in `System\U2GM.ini` (`[U2GM.GMMaster] Ops[...]`). Only the game writes it; edit it only while the game is closed, because the game rewrites its ini from memory.
- Each line is tagged with its map family: `@tuta place StaticMeshActor112 X Y Z YAW SCALE`, `@tuta hide NAME`, `@tuta mesh Pkg.Group.Mesh X Y Z YAW SCALE`.
- This is AvalonEditor's format, so `U2Avalon/tools/live_bake.py` can bake a session into the map.
- The world is always the map plus its journal. Undo and redo change the journal and replay it.
- A map's static meshes can't move at run time, so the first edit swaps one for a movable copy (`GMMesh`, `AmbientGlow=70`) and hides the original.

## Next (week 1, days 3–7)
- **Day 3:** a native terrain brush in the d3d8 fork (`ATerrainInfo::SetHeightmap`/`Update`).
- **Days 4–5:** an ImGui panel and gizmo drawn by the fork.
- **Days 6–7:** `gm commit`, which replays the journal into `<Map>_Live1` through UnrealEd and relights.
