# U2GM: game master mode for Unreal II

Change the level while it is played. This is week 1, days 1–7 of the plan in `games/research_notes/In-game game master editing/report.md`. The script is here; the terrain brush and the panel are in the d3d8 fork (`d3d8to9-gi`).

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
- This is AvalonEditor's format; `tools/gm_commit.py` bakes it into a map (`--ini U2AvalonCards.ini --section U2AvalonCards.AvalonEditor` for AvalonEditor's journal; the `live_bake.py` named here before was never written).
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

## Commit (days 6–7)
`gm commit` bakes the session's journal into a real map with UnrealEd, saves it as the next `<Map>_LiveN`, and sends the running game there. Built and tested offline on 2026-10-08. **It has never been run against the editor or the game.**

**Parts:**
- `tools/gm_commit.py`:
  - reads `U2GM.ini` (UTF-16 or 8-bit, quoted or bare values; read only);
  - takes the map family's `Ops[]` lines in slot order;
  - drives UnrealEd through uedlib.
- `GMMaster`: new commands `gm commit [cancel]`, `gm travel MAP`, plus `baked`/`committed`/`commitfail`, which the watcher sends.
- The fork's panel: a **Commit** section.

**Flow:**
1. `gm commit` (or the panel's Commit button):
   - `SaveConfig`;
   - writes `CommitRequest="family stamp map lines"` and `CommitStatus="stamp pending"` to `U2GM.ini`;
   - refuses edits (move/turn/scale/hide/spawn/terrain/undo/redo/preview) until the commit is answered. `gm commit cancel` releases them.
2. `py tools/gm_commit.py --watch` polls `U2GM.ini` every second. For a pending request it bakes `<map>` (the exact map the game is on) into the next free `<Parent>_LiveN`, with UnrealEd beside the game (`U2ED_WITH_GAME=1`, as `carve.py` does). It writes progress into `System\U2GMCommit.status`, and the panel shows that line.
3. The watcher answers through `System\U2GMPanel.txt` in q-line format, in its own session (2^30 and up): `gm baked STAMP K TEXT` for every baked slot, then `gm committed STAMP MAP N`, then `gm travel MAP`. On failure it sends `gm commitfail STAMP WHY`.
4. `gm travel` uses `ClientTravel` with the same URL options. After the load the player is put back where they stood, in GM mode if it was on.

Without the watcher: `py tools/gm_commit.py` runs one commit for the pending request, or for `--family tuta [--map TutA_Live2]`.

**Double apply (the scheme):** the baked map already contains the lines, so they must leave the journal before the new map loads.
- GMMaster empties slot K on `gm baked STAMP K TEXT`, but only if that slot still says TEXT and STAMP is the current commit.
- Edits are refused while a commit is pending, so the journal can't change under the bake. The text check is a second guard.
- The baked lines arrive in the same exec batch as, and before, `gm travel`. When `Replay()` and the fork's terrain watcher see the new map, the lines are gone.
- Lines the bake couldn't apply (actor not found, unknown line) are not reported, so they stay and keep replaying.
- Undo/redo history is cleared at `committed`: the commit is a checkpoint.
- The watcher's lines have their own sequence (`WatchSession`/`WatchSeq`, shown as `wseq=` in `PanelState`). The fork's lines and the watcher's can't hide or replay each other's.
- The rebuilt fork keeps the other session's lines when it rewrites the file. The watcher re-merges its lines if they disappear, and removes them once `wseq` shows the game ran them.
- Known blip: when the baked lines leave the journal, the fork briefly puts the old map's terrain back, about one second before the travel.
- The edits now live in `<Map>_LiveN`. Opening the original map again shows it without them.

**How each line is baked (on a copy):**
- **terrain:** **Route: heightmap export/import (carve.py's tested route), not a new ops-DLL SetHeightmap command.** It needs no new native code, and the brush math is the same either way.
  - Every TerrainInfo's `TerrainMap` is exported (`OBJ EXPORT`, a G16 BMP).
  - The brush lines are run over it in numpy, as a port of the fork's `GmRun` (float32, original plus every line in slot order, cosine falloff, clamp, +0.5 rounding).
  - It is imported back (`TEXTURE IMPORT ... MIPS=0`), then the TerrainInfos are re-pasted (`replace_actors`).
  - The cost: every TerrainInfo is re-pasted, and the sea's too, so they may get new names. Static meshes are not re-seated, which matches what the game showed.
- **place:**
  - `!select` + `EDIT COPY` reads the actor, then `!move NAME X Y Z - YAW -` keeps pitch and roll.
  - If the DrawScale changed, or with `--no-ops`, it goes the T3D way instead: copy, `ACTOR DELETE`, the edited block re-imported. `--no-ops` selects with stock `SELECTNAME`.
- **hide:** select + `ACTOR DELETE` (removed, not hidden).
- **mesh:** `OBJ LOAD` of `StaticMeshes\<Pkg>.usx`, then one `MAP IMPORTADD` of `StaticMeshActor` blocks (`Name=GMMesh<stamp>_<slot>`, `Group="U2GM"`).
- **Light:** `!light selected` on the imported blocks, `!light` on the moved actors, then `LIGHT APPLY CHANGED=1`. `--full-light` does a full relight instead.
- **Options:**
  - `--bake`: `!meshverts` → `U2Bake/bake.py --mode add` → `!bakeload` (all untested).
  - `--paths`: `PATHS BUILD` (slow on big maps).
- **Save:** `MAP SAVE` as `<Map>_LiveN`. The work folder is `%TEMP%\gm_commit\<Map>_LiveN`, holding the BMPs, `<map>_<terrain>.png` + `_diff.png`, `gm_import.t3d` and `commit.json`.
- Draw lines are never baked.

**Offline tests (pass):**
- `py -m unittest test_gm_commit -v` in `tools/`:
  - journal parsing: UTF-16 with and without BOM, quotes, case, other families and sections, slot order;
  - op parsing, yaw rounding, maps and LiveN numbering;
  - the terrain math against a cell-by-cell float32 port of the fork's loop: identical on a 128×128 map with 5 brushes;
  - BMP round trip;
  - the planned editor commands with and without ops;
  - the panel-file merge.
- Dry run: `py tools/gm_commit.py --dry-run --ini <sample U2GM.ini> --heightmap <G16 BMP> --out <dir>` prints every editor command, the T3D, the game lines, and writes the terrain PNGs. Without `--heightmap` it uses a flat 128×128 map at carve.py's TutA terrain constants.

**Guessed (check these first):**
- Heightmap ↔ world is `Location + ((x−W/2)·SX, (y−H/2)·SY, (raw−32768)·SZ/256)`, the relation carve.py measured on TutA. The fork asks the engine instead (`HeightmapToWorld`). If a baked mound sits off the game's by a cell or two, this is why.
- `SELECTNAME` + `EDIT COPY` copies just that actor (`--no-ops`).
- A re-imported actor keeps its name. Not needed for correctness.
- `LIGHT APPLY CHANGED=1` lights re-pasted TerrainInfos and imported meshes. Fallback: `--full-light`.
- The baked-line text survives the exec file unchanged (the comparison ignores case).
- `Level.GetLocalURL()` carries the mutator option. U2AvalonCards' reload uses it.
- `!setprop` is not used. `--bake` is wholly untested.

**Test list** (other session; game running with the new `U2GM.u` and fork `d3d8.dll` from `staging/`, `gmpanel=1 gmterrain=1`; keep `Unreal2.log`, `U2Shaders.log` and the watcher's console open):
1. On a copy-safe map with terrain (TutA), start `py tools/gm_commit.py --watch`. The panel's Commit section says `watcher: watcher up, waiting for gm commit`.
2. Make one edit of each kind:
   - move a static mesh with the gizmo;
   - `gm hide` another;
   - `gm spawn 0`;
   - `gm raise 1024 256`, then `gm smooth 800`.

   `gm journal` lists 5 lines.
3. Click **Commit** (or type `gm commit`).
   - The console says `commit N: 5 journal lines ...`. The panel shows `commit N pending` and the watcher's progress.
   - Try `gm move 0 0 32`: it is refused with the "baking" message.
4. The watcher prints the editor run, then `sent ... the game took them`. Within about 2 s:
   - the console shows 5 `baked line` log lines (in `Unreal2.log`), then `commit N: 5 lines baked into TutA_LiveM`;
   - the game travels to `TutA_LiveM`;
   - you're back where you stood, GM mode as before.
5. On `TutA_LiveM`:
   - the edits are there once only: the mound isn't doubled, there's one crate, not two;
   - `gm journal` shows 0 lines;
   - `U2Shaders.log` says `gm terrain: 0 terrain line(s)` or nothing for the new map.

   Compare the mound's place with a screenshot from before the commit: it should not be shifted.
6. Lighting: the moved mesh, the crate and the mound look lit, not black. If not, rerun with `--full-light` and note it.
7. `gm commit` with an empty journal says "nothing to commit". `gm commit` then `gm commit cancel` releases edits. A commit with the watcher stopped shows "no watcher answered".
8. Failure path: stop UnrealEd mid-commit (or rename the source map). The game hears `commit N failed: ...`, and the journal is unchanged.
9. `--no-ops` once: same result, and the moved actor may get a new name.
10. Watch for:
    - lines left in `U2GMPanel.txt` after the ack;
    - the panel's own buttons still working during and after a commit (both sessions);
    - `Invalid name` noise (harmless);
    - the editor taking focus while you play.

## Draw (Q27, for the level team)
Notes drawn in the world: an edge for a railing, an area marked "shanty here", a route for a road. Not world edits. Built 2026-10-08, untested in the game.
- **Commands:**
  - `gm draw add [X Y Z]` adds a point: the given one, or the hit under the crosshair (or under the panel's mouse ray) on ground or walls.
  - `gm draw undo` removes the last point. `gm draw clear` removes all of them.
  - `gm draw list` and `gm draw forget N` show and drop this map family's draws.
- **`gm draw done open|closed [NOTE]`** keeps one line in `U2GM.ini` `Draws[]` (64 slots), not in `Ops[]`, so replay and commit never treat it as an edit: `@family draw D<n> open|closed x1 y1 z1 x2 y2 z2 ... note TEXT`.
  - It logs `GM: draw D<n> ... (map M, slot K)` to `Unreal2.log` and runs `shot`, as AvalonEditor's mark does.
  - Open needs 2 or more points, closed 3 or more. A draw holds at most **40 points**, and the note is trimmed so the ini line stays under 1000 characters (Unreal's config strings).
- **Panel:**
  - Click in world = **draw (add a point)**: each click adds a point where the mouse ray hits.
  - The points and the polyline between them are drawn live in magenta, with the closing edge faint. The script keeps `DrawState="x,y,z ..."` in `U2GM.ini` for this.
  - Buttons: Point at crosshair, Undo point, Clear, a note field, Done (open) and Done (closed).
  - The note may use letters, digits, spaces and `._-#:,+!?()/%&`. Other characters, quotes and semicolons among them, become spaces.

**Test list (draw):**
1. Panel open, click mode **draw**. Click 4 spots on the ground and one on a wall. Five numbered magenta points appear, joined by lines that stay put as you turn the view.
2. **Undo point** removes the wall point.
3. Type the note `shanty here (3 huts)` and press **Done (closed)**.
   - The console says `draw D1 kept (closed), screenshot taken`.
   - A new `ShotNNNNN` appears.
   - `Unreal2.log` has `GM: draw D1 closed x y z ... note shanty here (3 huts)`.
   - `U2GM.ini` has a `Draws[0]="@tuta draw D1 ..."` line.
4. Type `gm draw add` 41 times: the 41st is refused. Then `gm draw clear`.
5. `gm commit` with a draw present: the draw is not in the watcher's line count and stays in `Draws[]`.

## Sketch (screenshot markup)
"Image editing tools when I'm on the console": freeze the frame, mark it up, save it as a PNG, and optionally send it as an `avalon mark`. Drawn by the d3d8 fork with the same Dear ImGui as the panel (`source/u2shaders.hpp`, "sketch"). Built and compiled on 2026-10-08, **never run in the game**.

**Parts:**
- `staging/d3d8.dll`: the fork with `sketch=1`. The PNG writer is stb_image_write v1.16 (public domain/MIT, vendored as `d3d8to9-gi/source/stb_image_write.h`).
- `staging/U2GM.u`: GMMaster gains `gm con big|quick 1|0` (sets `con=` in `PanelState`), `gm sketch mark NAME [NOTE]`, and `view=YAW,PITCH` in `PanelState`.
- `tools/sketch_console_ui.py`: adds four `TriggerEvent` lines to `<game>\UIScripts\Console.ui`, so the console itself says when it opens and closes. Backup `Console.ui.before-sketch`, `--undo`, `--dry-run`, idempotent.

**How the console is detected (and why this way):** U2's console isn't a script object. It's a UI component (`Console.ui`, a MultiStateComponent with states `NULL`/`ConsoleC`, and `QuickConsole` for Tab), so GMMaster has nothing to poll. Its `TriggerEvent=<state>,<delay>,ConsoleCommand,<cmd>` lines (the form `ModMenus.ui` uses for `UIOPENMAP`) run a console command on every state change. The patch makes the UI run `gm con big 1` / `gm con big 0` (`~`) and `gm con quick 1` / `gm con quick 0` (Tab). GMMaster writes `con=N` into `PanelState` at once (only on change), and the fork reads `U2GM.ini` every 10 frames.
- This is the UI's own state, whatever key opened it, however it was closed (Escape, Enter, `~`), with any binding.
- Detecting the console's 2D draws instead would need guessed texture hashes and size rules that change with SOverhaul and the resolution. Watching keys would miss every close path that isn't a key.
- The ~0.2 s delay doesn't matter for the picture (next point).

**The frozen frame:** when the console opens, the fork copies the next frame at its **first 2D draw**. That's the world with post applied, before the HUD and the console are drawn on top, so the console is never in it however late the flag comes. A frame with no 2D draw is copied at Present.
- `sketchhud=1` copies the whole presented frame instead: HUD and the open console included.
- The copy is a GPU `StretchRect`, read back once. Nothing is copied on frames where no copy is wanted.

**Use:**
- While the console is open, a yellow-edged strip **"Sketch this frame (F8)"** shows at the right, 30% down. Click it, or press **F8** at any time.
  - In the console: sketch mode opens on the frame frozen when the console opened.
  - Outside the console: a fresh frame is frozen first (one frame later).
- Sketch mode shows the frozen frame full screen (letterboxed if the window size changed), plus a tool bar. The mouse is held as for the GM panel (`U2InputHoldMouse`). Escape (outside a text field) or F8 closes it. The strokes stay with that frame until a new one is frozen. Opening the console again freezes a new frame, and its sketch starts empty.
- **Tools** (keys 1–7):
  - **Pen**
  - **Highlight**: 4× wide, 40% opaque
  - **Arrow**, **Rect**, **Ellipse**: drag
  - **Text**: type the label in the field, then click where it goes. It gets a dark outline.
  - **Crop**: drag. The last crop wins, the outside is dimmed, and Save writes only that part.
- **Colours:** 8 swatches: red, orange, yellow, green, cyan, blue, magenta, white.
- **Size:** 1–24 frame pixels. Text size is 16 + 2.5 × size.
- **Editing:** **Erase last** (Ctrl+Z) undoes the last stroke, crop or clear. **Redo** (Ctrl+Y). **Clear** (undoable). A right click drops the stroke being drawn.
- **Saving:**
  - **Save PNG** (Ctrl+S) and **Save as mark**. Both use the **note** field.
  - Strokes are kept as vectors in frame pixels. Save draws the frame and the strokes with ImGui's renderer into a target of the frame's size (what you saw, at 1:1), reads it back, cuts the crop, and writes the files on a thread.
- **Settings** (`System\U2Shaders.ini`, read at start):
  - `sketch=1`: on. It's off by default and never runs in UnrealEd.
  - `sketchkey=F8`: the key, F1–F24 or a virtual-key code like `0x77`.
  - `sketchhud=1`: freeze the presented frame instead.

  F8 is U2's **QuickLoad**. While `sketch=1` the key never reaches the game, so QuickLoad is off. Pick another key with `sketchkey=` if you want it back. Don't use F7 when `gmpanel` is on: the panel takes F7 first.

**Files** (all in `<game>\System\Sketch\`, created on the first save):
- `sketch-YYYYMMDD-HHMMSS.png`: RGB, the frame size or the crop. A second save in the same second adds `-2`, `-3`.
- `sketch-YYYYMMDD-HHMMSS.txt` contains:
  - `sketch`, `time`, `map`;
  - `eye X Y Z` (`PanelState` `cam=`, up to 1 s old);
  - `view yaw Y pitch P`;
  - `frame WxH, <world before HUD/console | presented frame>`;
  - `crop`;
  - `strokes N (Pen 3, Arrow 1, ...)`;
  - `labels "..." | "..."`;
  - `note <as typed>`;
  - `mark <what was sent, or why not>`.

  Without U2GM loaded, eye and view say `unknown`.

**Save as mark (for the level team):**
1. The fork sends `gm sketch mark <name> <note>` through `U2GMPanel.txt`. This needs U2GM loaded, so that `PanelState` is there. The note is cut to ASCII: accented letters become plain ones (`não` → `nao`), and characters outside letters, digits and `._-#:,+!?()/%&` become spaces.
2. GMMaster logs `GM: SKETCH <name> map M eye X Y Z yaw Y pitch P note ...` to `Unreal2.log`.
3. If AvalonCards is on the map, GMMaster runs `avalon mark <note> sketch:<name>`. That's a normal mark: AvalonEditor logs `Cards: edit MARK n at ... note <note> sketch:<name>` and takes its own `Shot*.bmp`, so the marks collector's shot pairing stays right.
4. `py U2Avalon/tools/live.py --marks` now also copies `System\Sketch\<name>.png` and `.txt` into `U2Avalon/marks/` beside the mark's `ShotNNNNN.png`, and prints both paths.

Without AvalonCards, the game says "saved and logged (AvalonCards isn't loaded here: no avalon mark)".

**Guessed (check these first):**
- **The console trigger.** `TriggerEvent=1,0,ConsoleCommand,...` fires on entering state 1 and `0,0` on entering state 0. This is read from `ModMenus.ui` and Console.ui's commented `EnableDrawWorld` lines.
- **Reaching `gm`.** The UI's `ConsoleCommand` reaches the player's ExecManagers. `UIOPENMAP` from the same path is an exec function on the player controller.
- **Startup noise.** The NULL state's trigger may fire once at startup, before U2GM's command exists, and log "Unrecognized command".
- **Clicking the strip.** The strip is clicked with the game's UI mouse while the console is open. The fork hit-tests the window's `WM_LBUTTONDOWN`, and U2's UI pointer is the OS cursor (U2Input notes). If clicks don't arrive, F8 still works.
- **The grab point.** The first 2D draw after the world is the same test the post uses. In third person, a z-tested orthographic draw mid-frame could freeze a half-drawn world; `posthud=z0` is honoured.
- **ImGui to a target.** Rendering ImGui draw data into an offscreen target is new in this fork (own `ImDrawList` + `ImDrawData`, `Textures=nullptr`).

**Install** (other session, game closed):
1. Back up `System\d3d8.dll`, `System\U2GM.u` and `UIScripts\Console.ui`.
2. Copy `staging/d3d8.dll` and `staging/U2GM.u` into `System`.
3. Run `py tools/sketch_console_ui.py`.
4. Add `sketch=1` to `System\U2Shaders.ini`. Keep `gmpanel=1` / `gmterrain=1` as they are; sketch works with `gmpanel=0` too.

**Test list (sketch):**
1. Start a map with U2GM (and AvalonCards for step 9).
   - `U2Shaders.log` says `sketch: on (key 0x77 = F8, frozen frame = the world before the HUD and console), files in ...System\Sketch`.
   - `U2GM.ini`'s `PanelState` ends with `con=0` and has `view=`.
2. Press `~`. Within about 0.5 s:
   - `PanelState` says `con=1`;
   - the strip "Sketch this frame (F8)" shows at the right;
   - the log has no `sketch: couldn't` lines.

   Close with Escape: `con=0` and the strip goes. Repeat with Tab (`con=2`), then close it with Enter and again with Escape.
3. Open `~` and click the strip.
   - The frozen frame fills the screen with no console and no HUD on it, and post (bloom/grade) is visible.
   - The tool bar is at the top and the cursor is free.
   - The mouse doesn't turn the view, and keys don't type into the console.
   - The log says `sketch: open (WxH, 0 stroke(s))`.
4. Each tool once, in a different colour each time:
   - a pen scribble;
   - a highlight swipe (see-through);
   - an arrow (the head at the release end);
   - a rect;
   - an ellipse;
   - type `door here` and click with Text (the outlined label appears);
   - Size 20, then a pen stroke (thick, round ends).
5. **Erase last** three times, **Redo** twice, then **Clear** and **Erase last** (everything comes back). Then Ctrl+Z and Ctrl+Y.
6. **Crop** a box: the outside dims. Type the note `test sketch näo`, press **Save PNG**.
   - The status says `saved System\Sketch\sketch-....png (+ .txt)`.
   - The PNG is only the cropped part, with the strokes exactly where they were drawn, at full resolution.
   - The `.txt` has `map`, `eye`, `view`, `crop`, `strokes`, `labels "door here"`, `note`, and `mark not asked`.
7. Press Escape. Sketch closes, the console is still open, and the mouse is back.
   - Press F8: the same frame comes back with its strokes.
   - Close it, close the console, then press F8 in play: a fresh frame (no HUD) opens with no strokes.
8. **Save as mark** without AvalonCards (any map with U2GM): the console says `[GM] sketch sketch-... saved and logged (...)`, and `Unreal2.log` has `GM: SKETCH sketch-... map ... eye ... note ...`.
9. On Avalon (AvalonCards loaded): **Save as mark** with the note `rail here`.
   - `[Claude] mark N taken` appears, plus a new `Shot*.bmp`.
   - `Unreal2.log` has `Cards: edit MARK N ... note rail here sketch:sketch-...`.
   - `py U2Avalon/tools/live.py --marks 1` prints the mark, `shot:`, `sketch.png:` and `sketch.txt:`, and copies the PNG into `U2Avalon/marks/`.
10. With the GM panel open (F7), press F8. The sketch covers the panel. Escape returns to the panel, still usable. F7 while sketching leaves the sketch open.
11. Alt-Tab out and back while sketching. Change resolution or fullscreen with sketch closed, then open the console and sketch again: no crash, and the frame has the new size.
12. `sketchhud=1` (restart): the frozen frame includes the HUD (and the console when frozen from the console).
13. Watch for:
    - a hitch on Save, over about 100 ms (the PNG is written on a thread; the readback isn't);
    - a black or garbage frozen frame (format; the log says `couldn't read`);
    - strokes offset from where they were drawn in the PNG;
    - text missing in the PNG (font upload ordering);
    - QuickLoad still firing on F8;
    - "Unrecognized command: gm con ..." spam with U2GM loaded.

## Next
- Week 1 is built: the terrain brush, the panel and commit are all untested in the game. Run the test lists above in order.
