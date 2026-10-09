# U2Avalon handoff index (2026-10-09, last code commit a1c71a9, status commit 14c3f5f)

Repo paths below are relative to `games/unreal2_mods/U2Avalon/`.
- `<game>` = `C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening`.
- `<run>` = `C:\Users\john\Documents\U2_research\towns\TutA_Remake907`.

## Read first, in order
1. `redesign/2026-10-09/plan.md`: the approved redesign. Then `facts_measured.md` (player and step sizes) and `marks_checklist.md` (the user's old marks, kept as requirements).
2. `PIPELINE.md`: the town.py stages, plus "Done, partial, next" and "Where things are".
3. `tools/remake_build.py` docstring: the editor build stages on top of town.py.
4. `marks/QUEUE.md` (gitignored, local only): every user mark Q1-Q95 and its status. The open ones are Q89, Q91-Q95.
5. `redesign/2026-10-09/writer_drama_manager.md`: the story sim.
6. `redesign/2026-10-09/level_designer.md` s.139-231 (arenas) and `STORY_ASSETS.md` (story parts, plus the hand-made steps).
7. Memory, outside the repo: `C:\Users\john\.claude\projects\C--\memory\u2avalon-project.md` ("State 2026-10-09 evening" block) and `avalon-storysim.md`.

## Works end to end today
- **New Game opens `TutA_Remake`:** via `<game>\UIScripts\ModMenus.ui` + `U2Menus.ui`, events 5/6/7 = `UIOPENMAP TutA_Remake?Game=U2.MissionGameInfo` (backups `*.before-avalon-newgame`). The suit, HUD and weapon work. TutA's 131 s intro cinematic plays first.
- **Town and terrain:**
  - Command: `py tools/town.py 907 style=plateau name=TutA_Remake`.
  - Output: `<game>\Maps\TutA_Remake907.un2` plus `<run>`. `<run>\report.md` is the run report.
- **Editor build:**
  - Command: `py tools/remake_build.py <run> TutA_Remake907 stage=<s>`, which writes `<game>\Maps\TutA_Remake.un2`.
  - Stage order used: `t3d`, `mesh` (pkg AvalonSM4), `map`, `paths`, `specs`, `bsp`, `arenas`, `dock`.
  - `patchin` / `patchlayers` exist, but their result was removed again (see Q92).
- **Interior lights:** `tools/interior_lights.py` writes `<run>\remake_lights.t3d` (54 lights), imported by `stage=patchin`.
- **Fights:**
  - `py tools/avalon_fights.py <run>` writes `<game>\System\U2AvalonFights.ini`.
  - They run in the class `games/unreal2_mods/U2Sanctuary/Source/U2Sanctuary/Classes/AvalonDirector.uc`, spawned by `SanctuaryMutator.uc` on TutA_Remake. It is compiled into `<game>\System\U2Sanctuary.u` (backup `.before-avalonfights`).
  - Fights E1-E4 plus I2 (in hall_b). Mercs spawning at E1 is verified.
- **Dock start (`stage=dock`, 2026-10-09):**
  - start yaw 0 (away from the sun at az 136);
  - `ZoneInfo` ambient 14 (it was 0, so shadows rendered pure black);
  - fill light `GenLight_dockfill`;
  - paths rebuilt. Verified in game.
- **In-game checks with no user:**
  - Launch `<game>\System\Unreal2.exe` and wait about 40 s for the menu.
  - Run `py -3.13 tools/C/U2Input/u2ctl.py exec "UIOPENMAP TutA_Remake?Game=U2.MissionGameInfo"` (the path is from the repo root).
  - Wait about 60 s, then press SPACE about 40 times to skip the cinematic.
  - Capture with `py -3.13 tools/C/U2Input/probe.py out.png wait:S`.
- **Pilot (U2Pilot):** `tools/python/U2Pilot` (memory `u2pilot-runs-preauthorized.md`). town.py `pilot=1` runs it.

## Known gotchas
- **Game must be closed** for UnrealEd / UCC builds. Packages the game has loaded are locked, so bump `pkg=` to re-import meshes.
- **PYTHONUTF8=1 breaks u2ed's tasklist decode:** run without it.
- **Stale paths:** any new actor marks the map's paths stale, and the game then refuses to load it ("Paths should be rebuilt"). Every stage runs `ed.paths()` before saving.
- **Run order:** PATHS DEFINE always after LIGHT APPLY. Import in chunks of at most 150 actors (one 850-actor import crashed UnrealEd).
- **Snapping:** `ACTOR ALIGN SNAPTOFLOOR` snaps the origin, so it buries top-pivot slabs. Don't use it.
- **Material-less kit:** the `B_k_slab` kit mesh has no material, so the greybox cover renders black.
- **Pressing ESC during the intro cinematic** opens the in-game menu. A UIOPENMAP sent then crashed the game (GPF in MainMenuItemHolder). Use SPACE instead.
- **Opening maps from outside:** the command line `Unreal2.exe <map>` and console `open` didn't switch maps. Use UIOPENMAP.
- **UCC rewrites Golem `Glm*.ugx`** on every run. That's routine.
- **Subclass config:** a subclass with its own config inherits the parent's loaded config arrays. AvalonDirector.Start() clears them.

## Half-done (file, then next step)
- **Q93, floating dark boxes from the dock start:**
  - Not placed actors, brushes, mutators or the d3d8 fork.
  - New sighting: a row of about 6 boxes over the sea toward +X, sun-lit, then a dark tracked object overhead. Shot: `marks/q93_rowofboxes_dock11.png`.
  - Next: a user `avalon mark` under one, or compare against `TutA_Remake907` at the same spot.
- **Q92, the terrain patch renders pitch black in game:**
  - Files: `tools/terrain_patch.py`, `remake_build.py` `stage_patchin` / `stage_patchlayers`.
  - Kept in `<game>\Maps\TutA_RemakeQ92.un2` and `TutA_Remake_withpatch.un2`.
  - Next: find why it's black. Untested guess: the ambient was 0 then, so retest it with the new zone ambient.
- **Greybox cover black:** next, give the `slab_box()` actors in `remake_build.py` a `Skins(0)` (needs the slab's UVs checked).
- **Sluice fight:** needs the drain entrance (Q91, `STORY_ASSETS.md` s.3: the drain grate terrain hole is by hand).
- **Tower lobby fight:** needs TutA's lift; `tower=1` in `remake_build.py` overlaps TutA's tower BSP.
- **`storysim.py resume=`:** new and untested end to end, until the run below finishes.
- **Not started:**
  - fold the tutorial in (`redesign/2026-10-09/tutorial_fold.md`, the Advent chat's part);
  - Q89 Atlantis travel hang (Wardrobe suspected);
  - swap into `TutA.un2` (plan s.7; ask the user before overwriting).

## The two background storysim runs (started 2026-10-09 ~19:20)
- **What:** `<scratchpad>\sims.sh`, i.e. `start_servers.sh small`, then the two runs, then `stop_servers.sh`.
  - Citizens on local Gemma :8081.
  - The 6 main characters plus the drama manager on Claude CLI (`claude -p`).
- **Run 1:**
  - `py tools/storysim.py days=3 resume=<O>\day1_test out=<O>\day1_test_cont`: days 2-3 continued from the day-1 test.
  - `<O>` = `C:\Users\john\Documents\U2_research\storysim`.
- **Run 2:** `py tools/storysim.py days=3 out=<O>\fresh3`, three fresh days.
- **Output per run:** `log.jsonl`, `day_N.md`, `day_N_review.json`, `memories.json`, `story.md`.
- **Stop:**
  - Kill the `py tools/storysim.py` processes (TaskStop doesn't kill the children; use `Get-CimInstance Win32_Process` + `Stop-Process`).
  - Then `sh C:\Users\john\Documents\Tools\llm\stop_servers.sh`.
  - Tell the Advent chat that the GPU is free (I claimed it).
- **Resume a cut run:** `py tools/storysim.py days=3 resume=<that run dir> out=<new dir>` (it resumes after the last finished day).

## Outside git (does a fresh session need it?)
- **Needed:**
  - `<game>\Maps\TutA_Remake*.un2`: the remake map plus its backups `_predock`, `_prepatch`, `_presnap`, `_prearenas`, `_prelayers`, `_preholes`, `_withpatch`, `Q92`, `907`.
  - `<game>\System` files: `U2AvalonFights.ini`, `U2Sanctuary.u`, `U2AvalonCards.ini`, User.ini mutators, and the `.before-*` backups.
  - `<run>`: the layout, rooms, T3Ds and patch BMPs for the current map. Every remake stage reads it.
  - `<game>\StaticMeshes\AvalonSM4.usx` and the earlier `AvalonSM*.usx`.
  - `C:\Users\john\Documents\github\codes\tools\C\U2EdBridge`: uedlib, u2ed. This is in git, under the repo's `tools/`.
- **Needed for the story sim only:**
  - `C:\Users\john\Documents\Tools\llm`: llama.cpp, models, start/stop scripts, `localread.py`.
  - `C:\Users\john\Documents\U2_research\storysim\*`: the runs.
- **Reference only:**
  - `Documents\U2Golem\` (Hunyuan models: liandri, islands);
  - `Documents\design-refs\avalon_concepts\` and `avalon_real_places\`;
  - `Documents\U2_research\terrain\` and the other `towns\` runs.
- **Original TutA:** `<game>\Maps\TutA.un2.original` / `TutA_Stock.un2`. The campaign `TutA.un2` is still an older generated town (Town5_Side), not the remake.

## Design decisions carried in my head (not written elsewhere)
- **The remake stays a separate map** (`TutA_Remake`) reached by New Game. Overwriting `TutA.un2` waits for the user's OK after a full playthrough.
- **Fight triggers sit at each arena's way in (P, radius 500),** not its middle: since the arena slide, E1's middle is 19 m from the start.
- **Greybox cover stays boxes** until the user plays the fights. Real props come only after the layout of cover is approved.
- **Start view:** the user approved "both" (turn the start and raise the ambient). The director's back-light preference (`codirect.light_off`) is overruled at the start only.
- **Ambient 14 is a floor, not a look:** dusk darkness should come from the low sun and fog, never from black shadows.
- **Story sim:** big = Claude since Pantheon was deleted (disk space). The user chose to run both "continue" and "fresh" so the two can be compared. Pick the better continuity for the writer.
- **Token rules (`C:\Users\john\.claude\CLAUDE.md`):** subagents on Sonnet only, cheap reads.
