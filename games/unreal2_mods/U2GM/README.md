# U2GM: game master mode for Unreal II

Change the level while it is played. This is week 1, days 1–5 of the plan in `games/research_notes/In-game game master editing/report.md`. The script is here; the terrain brush and the panel are in the d3d8 fork (`d3d8to9-gi`).

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

## Panel (days 4–5)
An on-screen GM panel and a move/rotate gizmo, drawn by the d3d8 fork with Dear ImGui (v1.92.9b, MIT, vendored in `d3d8to9-gi/source/imgui/`). Built and compiled on 2026-10-08, **never run in the game**.

**Parts** (`staging/` holds the three builds):
- `d3d8.dll`: the fork (`source/u2shaders.hpp`, "gmpanel"). It draws the panel at Present, after the HUD, on the back buffer. ImGui's dx9 backend saves and restores every render state, and the fork restores the render target, depth buffer and viewport.
- `U2GM.u`: GMMaster now execs `System\U2GMPanel.txt` every `PanelPoll` seconds (2 s, or 0.25 s while the panel is open). After every command it writes a `PanelState=` line to `U2GM.ini`, and the panel reads it.
- `dinput8.dll`: U2Input with a new export, `U2InputHoldMouse(on)`.

**Enable:** put the three files in `System` while the game is closed. Add `gmpanel=1` to `System\U2Shaders.ini` (off by default). `gmpanel=2` draws ImGui's own cursor, in case the OS cursor stays hidden. `gmpanelscale=1.5` makes the panel bigger. The panel never runs in UnrealEd. Its window position is kept in `System\U2GMPanel.imgui.ini`.

**Controls:**
- **F7** shows or hides the panel.
- While it's shown:
  - The OS cursor appears in the middle of the screen.
  - Keys and clicks go only to the panel. Key releases still reach the game, so nothing stays held.
  - Mouse look and firing are held off.
- **Panel sections:**
  - **Top row:** GM mode, Freeze, Possess/Release, Undo, Redo.
  - **Picked:** name, class, mesh, location, yaw and scale. Buttons: Pick (crosshair) and Hide.
  - **Click in world** chooses what a click on the scene does: pick, spawn the selected palette entry, move the picked actor here, or raise, lower, flatten or smooth terrain. The click is aimed along the mouse's line, not the crosshair.
  - **Move:** a step field and ±X/±Y/±Z. Turn ±15, Scale ±10%. Toggles for the gizmo, live preview and snap.
  - **Spawn:** the palette list from `U2GM.ini`. Click an entry to select it, then use Spawn at crosshair.
  - **Terrain:** radius and height fields, and Raise, Lower, Flatten and Smooth at the crosshair.
  - **Journal:** this map's journal lines.
  - **View check:** the camera position from the D3D matrices beside the game's eye position. They should roughly agree.
- **Gizmo** (on the picked actor):
  - Drag the red, green or blue arrow to move along X, Y or Z, in GridSize steps.
  - Drag the yellow ring to turn, in YawStep steps. The dot on the ring is the way the actor faces.
  - While you drag, `gm preview` moves the actor at most every 150 ms, without a journal line.
  - Release sends `gm moveto X Y Z` or `gm turn DEG`, one journal line and one undo step. Escape cancels.

**Input gating:**
- The fork calls U2Input's exported `U2InputHoldMouse(1/0)`, found in `System\dinput8.dll` with `GetProcAddress`.
- Why U2Input: Unreal II reads the mouse only through DirectInput, so eating window messages can't stop mouse look. Its exclusive DirectInput mouse also hides the cursor and suppresses mouse messages, so ImGui would get none.
- While held, U2Input:
  - unacquires the game's mouse;
  - returns no data (three button releases first, so a held fire button doesn't stick);
  - refuses `Acquire`;
  - swallows WinDrv's `SetCursorPos`/`ClipCursor`.
- When released, it acquires the mouse again on the game's next read.
- The fork's window hook does the keyboard. Without U2Input the panel says so, and mouse look isn't held.

**Command path:**
- Each button press becomes a line `gm q SESSION K CMD` in `System\U2GMPanel.txt`. The file is written whole, then renamed into place.
- Each line runs once: K must be above the last one run, or the session must be new. The fork's session changes every game start, and the fork deletes an old file at startup.
- The fork only writes commands made of letters, digits and `._-#:,+`.
- Lines leave the file once `PanelState`'s `seq=` shows that the game took them.
- New script commands, used by the panel:
  - `gm panel 1|0`: poll fast or slow.
  - `gm ray SX SY SZ EX EY EZ`: the next command aims along this line.
  - `gm preview X Y Z YAW`: move and turn the picked actor without a journal line.

**Guessed (check these first):**
- The gizmo's view: the last perspective draw on the back buffer with an identity world matrix. If the gizmo or clicks are off, compare the panel's view check.
- `PC.ConsoleCommand("exec U2GMPanel.txt")` running `gm` lines. This is the AvalonLive path, which works.
- U2Input's unacquire showing the OS cursor and giving the panel mouse messages.
- WinDrv re-reading the mouse after `Acquire` comes back.
- Yaw sign: the ring is measured from +X towards +Y, which is Unreal's yaw.

**Test list** (other session; the game running on a map with terrain; `U2Shaders.log`, `U2Input.log` and `Unreal2.log` at hand):
1. Install the three `staging` files, set `gmpanel=1` (keep `gmterrain=1`), start the map with `?Mutator=U2GM.GMMutator`. `U2Shaders.log` says `gm panel: on (F7), session N ...`.
2. Press F7.
   - The panel appears and the cursor shows in the middle.
   - Moving the mouse doesn't turn the view, and clicking doesn't fire.
   - `U2Shaders.log` says `U2InputHoldMouse found` and `gm panel: shown`. `U2Input.log` says `mouse held`.
   - The HUD and the scene look unchanged under the panel: no black, no missing post effect.
3. Tick **GM mode**. Within about 0.5 s the checkbox stays ticked, the console says GM mode on, and "game took line" rises.
4. **Pick (crosshair)** on a crate or wall mesh. The Picked lines fill in, and the gizmo sits on the actor. Compare the view check numbers.
5. Click another mesh in the world (mode: pick). It becomes picked.
6. Drag the red arrow.
   - The actor follows in about 0.25 s steps.
   - On release, the journal shows `place NAME ...` and the actor stays put.
   - Undo puts it back, and Redo moves it again.
7. Drag the yellow ring by about 45°. The label reads `turn +45`, and the release journals one turn. Drag again and press Escape: the actor goes back.
8. Use ±X, Turn +15 and Scale +10%. Each one changes Picked and adds a journal line.
9. Select palette 0, set Click in world to "spawn", and click the ground. A crate appears where you clicked.
10. Set the mode to "raise terrain", radius 512, height 256, and click a slope. A mound appears at the click, not at the crosshair.
11. Freeze, then Possess with the crosshair on a marine, then Release.
12. Press F7.
   - The panel goes and mouse look returns at once.
   - `U2Input.log` says `mouse given back`.
   - Walk, fire, and open the console (Tab): nothing is stuck.
13. Alt-Tab out and back with the panel open, then close it with F7. Change resolution or fullscreen with the panel closed, then open it again. Watch for crashes and log lines with `didn't start`.
14. Watch for:
   - "game took line" never rising (exec path)
   - a gizmo drawn away from the actor
   - clicks picking the wrong thing
   - the cursor staying hidden (try `gmpanel=2`)
   - hitches when the panel opens

## Next (week 1, days 3–7)
- **Day 3:** a native terrain brush in the d3d8 fork: built (above), not yet run in the game.
- **Days 4–5:** the ImGui panel and gizmo: built (above), not yet run in the game.
- **Days 6–7:** `gm commit`, which replays the journal into `<Map>_Live1` through UnrealEd and relights.
