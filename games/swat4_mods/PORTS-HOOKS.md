# DK1 + FS2: how to hook in (2026-10-24)

Builds on FRIDAY-PLAN.md "Recon results". Measured on the user's running games.

## Door Kickers 1 (`F:\SteamLibrary\steamapps\common\DoorKickers`)
- `DoorKickers.exe` 32-bit (machine 0x14c), image base fixed? DllCharacteristics 0x8140 (has DYNAMIC_BASE, so ASLR: resolve by RVA).
- **Ships `DoorKickers.pdb` (21.6 MB)**: full symbols. ~3674 class::method names, e.g.
  `Game::Server_ProcessCommand(s)`, `Game::Server_ProcessActionWPCommand`, `Game::GeneratePath`,
  `Game::GetPathfinder`, `Human::SetAIPath`, `Human::SetAIState`, `Human::GetAIState`,
  `Human::UpdateAIStateParams`, `Game::DoAILocalEvent`, `GameRenderer::RenderAIDebug`,
  `Game::Net_Send/RecvNetworkCommands`, `Replay::*`, `Game::StartReplayPlayback`, `FieldOfView::*`.
  -> function hooks (MinHook) by PDB RVA; no guessing. Coop command path (`Server_ProcessCommands`) is the
  clean place to inject squad orders as if from a coop client.
- Also `DoorKickers_fullpause.exe` (second build).
- Imports: OPENGL32, OpenAL32, steam_api, ffmpeg dlls, ConfigTool.dll, **dbghelp.dll (only MiniDumpWriteDump)**
  -> easiest DLL proxy = local `dbghelp.dll` with 1 export (dbghelp is not a KnownDLL). opengl32 proxy also possible.
- Input: USER32 message loop only (GetMessageW/PeekMessageW); no GetCursorPos/GetAsyncKeyState/raw input.
- Data mods: `mods\<name>\` overrides `data\` by path; `filesystem_mount.xml` merges extra files from every active mod;
  `mod.xml` (name, gameVersion 1.0.9, Workshop tags). XML only, no scripting.
- **Background input: WORKS** with `tools/bginput.py` (PostMessage). Needs a fake activate first
  (WM_ACTIVATEAPP/NCACTIVATE/ACTIVATE/SETFOCUS posted, no real focus change), then 5 mouse moves, then down/up with
  ~0.1-0.2 s gaps. Tested: Replays opened + Back, user's foreground window unchanged.
- Capture: PrintWindow(flag 3) works in background; ~1 in 3 frames come back black -> bginput retries.

## Frozen Synapse 2 (`C:\Program Files (x86)\Steam\steamapps\common\Frozen Synapse 2`)
- 64-bit. `FrozenSynapse2.exe` stub; engine `FrozenSynapse2.dll` (Torque 3D) **exports 2585 symbols**
  (`cb<Class>_<method>` script callbacks etc.).
- Imports d3d9, **VERSION.dll (3 fns)**, dbghelp (14 fns) -> `version.dll` proxy is the easy DLL entry.
- Input APIs: GetCursorPos, GetCursorInfo, GetForegroundWindow, GetFocus, SetCursorPos, ClipCursor.
- **Background input: posted messages IGNORED** (tested click + hover, even with fake activate).
  Needs the hook DLL: IAT-patch FrozenSynapse2.dll so GetForegroundWindow/GetFocus return the game hwnd,
  GetCursorPos returns our fake pos, SetCursorPos/ClipCursor no-op (u2input pattern, skill u2input).
- Better than clicks: **TorqueScript console**. `main.cs` supports `-console` (`enableWinConsole(true)`);
  console input = full script access (call GUI/game functions, `getAITurn`, start skirmish). Feed it with
  WriteConsoleInput, or `exec()` a .cs we drop in. Untested: restart the game with `-console` (window shows, start minimized).
- Capture: PrintWindow works in background (d3d9).
- Other: `Testplays\*.enc`, `testMatches\`, `serverTurnFiles\`/`clientTurnFiles\`, `customModes\gclGameTypeForSoak.ro`.

## Next
1. FS2: try `-console` launch (minimized) and run script commands; else build version.dll hook (x64).
2. DK1: dump PDB symbol RVAs (llvm-pdbutil / py `pdbparse`) for the AI/command functions; dbghelp.dll proxy logging
   `Server_ProcessCommand` to learn the order format, then inject orders.
3. Both: observation = PrintWindow frames now; later read game state from hooked functions.

## FS2 script bridge: WORKS (2026-10-24)
- Root `main.cs` (plain .cs, backup `main.cs.orig`) gets one line: `exec("smbridge/bridge.cs")`.
  `tools/fs2_bridge.cs` = bridge source; `tools/fs2bridge.py --install` sets it up.
- `py -3.13 -I tools/fs2bridge.py '<TorqueScript>'` (or `-f file.cs`): game polls `smbridge/in.txt` every 200 ms,
  evals each line; `SMB_out(x)` appends to `smbridge/out.txt`. Round trip ~0.7 s.
- Window must NOT be minimized (engine nearly stalls). Restore with ShowWindow(SW_SHOWNOACTIVATE=4) +
  SetWindowPos(HWND_BOTTOM, NOACTIVATE): runs behind other windows, no focus change. PrintWindow capture works then.
- Menu buttons are script calls (walk dump: claude-cap/fs2walk-*.txt): QUICK SKIRMISH `testFS2Skirmish()` (tested: loads
  "Light Extermination" turn 1/8, root gui MainScreenGui), AI MATCHES `loadScoreAttackGui()`, CUSTOM GAME
  `startCustomModeGui()`, SKIRMISH GENERATOR `loadSkirmishGenerator()`, QUIT `quit()`.
- `getAITurn` and `startGetAITurnThreaded` exist (isFunction 1). Console log: `%APPDATA%\FrozenSynapse2\console.log`.
- `dumpConsoleFunctions()` is huge and blocks the game for a while; grep the log after it settles.
- Launched with `-log 1`; added `steam_appid.txt` (445020) so the exe starts directly.
- Script fns found via `dumpConsoleFunctions()` (blocks ~50 s at -log 1): `AISoak`, `soakTest`, `serverSoakTest*`, `doGetAITurn`,
  `getAITurn`, `startGetAITurnThreaded`, `guiPrime`, `controllerPrimeTurn`, `doCharonAllAtEnd`, `getUnitIdIsAlive/...`,
  `getUnitFromUnitSet`, `updateUnitCounters`. Arg lists unknown (.dso).
- `AISoak()` = online league soak: offline it fails (missing league objects, `quickStartNewMapGame` not found).
- **`doGetAITurn()` in a skirmish runs Charon "StandardAI" for ALL units of both teams** (log: units 1-3 team 1,
  4-7 team 2, "3 best plans, chose one with N edges", friendly-fire checks). `guiPrime()` afterwards: the game
  went to a loading/tips screen (not checked yet whether the turn played out or the match reset).
- Next: check what prime did (out.txt + console.log), find the per-unit plan readout and set-plan calls, then
  loop doGetAITurn+guiPrime as an AI-vs-AI soak for data; then swap our policy for Charon on team 1.

## FS2 AI-vs-AI soak (2026-10-24)
- `trace(1)` / `trace(0)` through the bridge prints the full script call chain to console.log: best tool for the .dso-only scripts.
- Prime button = `guiPrime()` -> `mtSubmitTurn()` -> MessageBoxOKCancel "Submit Turn" -> `doMTSubmitTurn()` -> `spSubmitTurn()`
  -> `spSubmitTurnStage2()` -> `getAITurn(spbase.enc, aiturn.enc, spSubmitTurnStage3, 1)` -> `spSubmitTurnStage3()` -> `loadMT(...)` (outcome).
  Skip the dialog: call `spSubmitTurn()` directly.
- **`$gThreadCharon=1` (default) loses the callback**: `scriptFinishAIStepping` does `call($aiTurnCallback)` with it empty
  -> ": Unknown command." and the loading screen hangs. **`$gThreadCharon=0`** = synchronous Charon, callback fires, turn advances.
- **`$gcmAIDoesBothSides=1`**: Charon plans team 1 (the "human" team) too ("Applying AI for player 1..3", winning plans).
- State reads: `getCurrentTurnNumber()`, `getUnitIdIsAlive(id)` (ids 1..7 in Light Extermination; missing ids log an error, return 0).
- `testFS2Skirmish()` starts a match fine; **`playRandomSPMatch()` from the menu crashes the game** (skirmish.cs "Cannot re-declare object [csMGSSettings]").
- Minimized FS2 stalls and can hang (Not Responding) during outcome playback; `ShowWindow` on a hung window blocks the caller,
  so restore with `ShowWindowAsync(h,4)` + `SetWindowPos(HWND_BOTTOM, NOACTIVATE|ASYNC)`.
- `tools/fs2soak.py [matches] [out.jsonl]`: launches FS2 behind if needed, per match `testFS2Skirmish()`, per turn the
  globals above + `spSubmitTurn()`, waits for the turn number, logs JSONL (alive before/after, plan edges per unit, secs).
- Built-in: `map/scripts/AISim/AISim.cs.dso` is the city-mode "SIM GAME" (`$map.doSimWeekAIMatches`), not a general soak.
- **Soak status (10-24 noon): the turn cycle works for ONE turn only.**
  - `testFS2Skirmish()`: turn 0->1 ok; the turn-1 submit runs Charon (team 2 only, `$gcmAIDoesBothSides` ignored there),
    then the game drops back to the main menu (`GSBrowser setupUI`). It's a dev test match, not a full one.
  - `playRandomSPMatch()` called from inside a running skirmish loads the "Random AI Match" (5 turns, both sides on Charon),
    turn 0->1 ok in ~8 s, then FS2 **crashes** in `loadMTStage3` "Generating floor splat details" (2 of 2 runs;
    once more right after `randspmatchpostload`). No dump written. From the menu it crashes at once (csMGSSettings).
  - Untested cause: the window parked behind/unfocused (d3d9 device) vs an engine bug in this offline path.
    Next: one run with FS2 visible in front (needs the user's screen free), else skip the 3D outcome
    (look for a headless outcome: `serverSoakTest*`, `collateTurnFiles`, `$gcmAISim`) or the version.dll hook.
- **Front-window run (10-24 afternoon): same crash.** FS2 launched visible in front, skirmish -> `playRandomSPMatch()` -> turn 0->1
  in 8 s, then crash at `loadMTStage3` "Generating floor splat details" (3 of 3 now). So it is NOT the window being behind/unfocused.
  Next: skip the 3D outcome load (headless path: `serverSoakTest*`, `collateTurnFiles`, `$gcmAISim`), or version.dll hook to
  catch the crash; or stay on `testFS2Skirmish()` turn 0->1 only (one Charon turn per match = still usable data).
- **10-24 later: `playQuickFS2Skirmish()` (the real QUICK SKIRMISH button, menu id 2139) = no crash.** Real generated level
  (948 nav nodes), 6 units, turn 0->1 in 15 s with Charon on both sides. `testFS2Skirmish` / `playRandomSPMatch` levels have
  0 nav nodes and "end" at once (0 kills) -> that is the crash path. `$gcmAISim=1` makes `shouldISkipOutcome()` return 1.
  - Open: the turn-1 submit does not advance. Trace: `spSubmitTurn()` runs, but no Charon ("Applying AI") and no
    spSubmitTurnStage2; it reloads the same turn (loadMTStage2..4, `do3DOutcome:: turn 0 1`), getTurnThatWeAreIn()=0.
    Next: check `$alreadySubmittedMT` / `alreadySubmittedTurn()`, `preSubmitCall`, `continueSPMatch()`; maybe the 3D
    outcome must finish (`endFancyOutcome()` / `onEnterPlanningAfterFirstOutcome()`) before planning turn 1.
  - Test scripts: %TEMP%/fs2t3.py (quitSP, playQuickFS2Skirmish, submit loop).
- **Soak WORKS (one turn per match):** `py -3.13 -I tools/fs2soak.py 3 out.jsonl` -> 3 matches, turn 0->1 in ~11 s each, no crash,
  plan edges per unit logged (e.g. {4: 67, 5: 75, 6: 11}). Only AI-team units (4+) show plans: `$gcmAIDoesBothSides` seems ignored
  in the quick skirmish (team 1 has no plan). Turn 1 submits still reload turn 2 of 5 (screen "Turn 2 of 5"); trace of the turn-1
  submit = same chain as turn 0 (spSubmitTurnStage2 -> getAITurn -> doGetAITurn -> Stage3 -> loadMT), psychoff/*.enc rewritten.
  Next: diff spBaseBeforeAI.enc vs spbase.enc/pturn.enc to see whether the new turn is written; give team 1 a plan.
- **10-24 evening, multi-turn probe (paused):** turn files in `%APPDATA%\FrozenSynapse2\psychoff\turnFiles\` are named by game
  time in ms (`baseFile0.enc`, then `baseFile4992.enc`); the 2nd submit rewrote 4992 again, so game time never moves past the
  end of turn 1 when the outcome playback is skipped. Next test (`%TEMP%/fs2t5.py`): `doGoToEndOfTurn();` (or
  `eventOnReachEndOfOutcomePlayback()`, `doGoToTime`, `moveSimToOutcomeTime`) between submits.
  Fresh-launch gotchas: `quitSP()` on MainScreenGui crashes (now guarded); a minimized start (SW_SHOWMINNOACTIVE) left the game
  hung after the match load (now SW_SHOWNOACTIVATE). An un-minimized run also hung at 0 % CPU after load, while the user's
  UE5 game was on the GPUs: retest when no game is running.
- **Multi-turn soak WORKS (10-24 night, run 10):** 2 matches, 7 turns (m0 0->2 team wiped, m1 0->5 turn limit), no crash,
  15-31 s per turn. Fixes: (1) ROOT CAUSE of the `FrozenSynapse2.dll+0x489080` crash (native D3D9 too, DXVK innocent): on a
  fresh launch the startup sequence (`nextSSStage 0..4` -> `SSReadyForMain 4` -> `[mtInGame] endGame` -> MainScreenGui) is
  still running; a match started before it ends is torn down (load timeout) and a submit in it crashes in Charon apply.
  `wait_setup()` waits for it. (2) `$gcmAIDoesBothSides=1` stalls the 2nd submit: dropped. (3) `doGoToEndOfTurn()` after each
  submit, retried until `getTurnThatWeAreIn()` catches up (too early = no-op, game sits on OUTCOME). (4) Launch via
  `steam.exe -applaunch 445020 -log 1` (playtime tracking; works while another game runs); `FS2_STEAM=0` = direct start + DXVK.
  Charon plans only units 5-8; team 1 (1-4) stands still: that is our AI's slot (via fs2bridge). Ends with quitSP() to menu.
- **Gym (10-24 night):** `fs2soak.py N out.jsonl --brain idle|rush|pairs --map NAME`. Our side = `tools/fs2brain.py`:
  `units()` reads ids 1..15 in one bridge call (`getTeamOfPlayerWithId` 1/2/0, `getUnitIdIsAlive`, `getPosOfPlayerWithId`
  "x y" / "-1 -1"); ids per team vary by map (seen 1-3 vs 4-6, and 1-4 vs 5-8), so the old fixed `[:3]`/`[3:7]` split is gone.
  Moves: `planAddWaypoint(0, unitId, x, y, 0)` (verified: unit moved toward the waypoint in one turn; 1st/5th args unknown,
  0 works). `planAddOrder` (4..15 args) not decoded yet. Each match ends with a `score` record (alive per team, kills, deaths,
  win 1/2/0). **Fixed map** = `tools/fs2_fixedmap.cs`, a package around `startSkirmish(%setup, %enc)`: no file ->
  `saveEncounter(%file, %enc)` (file FIRST; the other order writes nothing; test1.enc = 149927 bytes); file -> `%e = new
  ScriptEncounter(); %e.loadEncounter(%file); %enc = %e;` (the global `loadEncounter()` is void). Verified: random start
  gave unit 1 at 1485.3 1937.64, two test1 starts both 2795.99 2253.94. Exec the package ONCE per game run (a re-exec after
  deactivatePackage breaks Parent::, "Unknown command startSkirmish"); `use_map()` guards with `$smFixedLoaded`.
  `setRandomSeed()` before `playQuickFS2Skirmish()` does not fix the map. Chain: playQuickFS2Skirmish ->
  getCityMapGenEnc(MPS_SkirmishExtCityMap,0) -> levelGenFS2(psychoff/offlineCityMapGen/genFileN.enc (201), ...) -> startSkirmish.
- **Render on the 3060 while the user games (10-24):** DXVK 3.1.1 x64 `d3d9.dll` copied into the FS2 game dir
  (`Documents\Tools\dxvk\dxvk-3.1.1`); `fs2soak.launch()` sets `DXVK_FILTER_DEVICE_NAME="RTX 3060"` and
  `DXVK_LOG_PATH=%TEMP%`; `%TEMP%\FrozenSynapse2_d3d9.log` shows the 4070 Ti "Skipping: Device filter". Undo = delete the dll.
  Fresh launch: `playQuickFS2Skirmish` is undefined on MainScreenGui; `Canvas.setContent(GSBRowserGui)` defines it (exec of
  skirmishGenerator.cs by hand hung the game after load). `$pref::video::fullScreen` set 0 (backup prefs.cs.smbak).
  Open: on DXVK every first submit crashes at `FrozenSynapse2.dll+0x489080` right after
  "Applying AI for player 1" (Charon plans for 5-8 are made), with or without `$gcmAIDoesBothSides`. The native-D3D9 soak
  (d7f8923) logged player 8 first and did not crash, so DXVK is the prime suspect; check on native D3D9 once gpu 0 is free.

## DK1 gym: native recon (2026-10-24 night)
Tool `tools/dk1/dk1sym.py` (dbghelp on the shipped PDB, read only): `fn <mask>`, `sig <fn>`, `type <Name>` (fields/enums),
`dis <fn>` (capstone, targets named). Exe image base 0x400000 (ASLR: use RVA + GetModuleHandle(NULL)).
- RVAs: `Game::_instance` D 0x3caa08; `Entity::g_entityPool` Entity*[8192] 0x3c0c70; `Entity::s_playerTeam` 0x3c0c6c;
  Game::Update(uint, InputQueue*) 0x1579d0; UpdateGameRunning(float) 0x156c80; Server_ProcessCommand(sClientCommand*) 0x169340;
  Server_ProcessCommands() 0x1692f0; Server_ProcessHumanAddToPath 0x16a010; GetMapHumansList() -> List<Human*>* 0x159020;
  RestartMap 0x1541d0; OnMissionCompleted 0x15b970; OnHumanDieEvent(sEventParams*) 0x159230; LevelStart 0x153860;
  LevelEnd 0x153ae0; Server_PauseToggle(int) 0x160540; Human::SetAIPath(Waypoints*) 0xa6be0; GeneratePath(V2,V2,char*) 0x1620d0;
  Net_BufferClientCommands 0x704e0. All thiscall (ecx = Game*), `ret 4` per arg.
- `sClientCommand` (32 B): +0 type eClientCommand, +4 entity (uint id = index into g_entityPool), +8 v1 Vector2, +0x10 v2,
  +0x18 i1, +0x1c i2. eClientCommand: 1 PAUSE_UNPAUSE, 2 ACTIVATE_GOCODE, 6 HUMAN_CREATE_PATH, 7 DELETE_PATH, 9 CHANGE_SELECTION,
  10 ADD_TO_PATH, 11 DELETE_PATH_UP_TO_POINT, 12 STOP_MOVE_TOGGLE, 13 ACTIONWP_SET_ACTION, 16 ACTIONWP_SET_ORIENTATION, 24 COOP.
- `List<T>` 16 B: +0 m_size, +4 m_list (T*), +8 m_elements, +0xc user-mem flag. (AddToPath loops count at +8 of the list.)
- Entity: +0x18 m_type (2 = Human), +0x1c m_vOrigin V2, +0x24 rotation, +0x90 m_team, +0x94 m_id. Human (1000 B):
  +0xa8 m_humanType, +0xfc m_state (eHumanState), +0x11c m_bSelected, +0x15c m_waypoints List<Waypoints*>,
  +0x194 m_actionWaypoints List<ActionWaypoint*>, +0x2b4 m_pAIBrain, +0x334 m_AIState.
- ADD_TO_PATH: entity -> Human, finds the action waypoint with flag bit 2 at +0xc0 (selected), Human::AddToPath(v1). So a
  path must exist (CREATE_PATH first). Next: dis Server_ProcessCommand case 6, then build a 32-bit dbghelp.dll proxy (MSVC x86,
  one export MiniDumpWriteDump forwarded to System32) that IAT-hooks PeekMessageW (main thread, every frame) and runs file
  bridge commands `<game>\dk1bridge\in.txt` -> `out.txt` (humans dump, create path, go code, pause, restart).

## DK1 gym: WORKS (2026-10-24 late)
Files `tools/dk1/`: `dk1hook.c` + `dbghelp.def` + `build.bat` -> `bin/dbghelp.dll` (32-bit proxy, export MiniDumpWriteDump
forwarded to System32; DllMain IAT-patches PeekMessageW/GetMessageW; bridge polled at most every 50 ms on the main thread),
`dk1gym.py` (send/humans/launch/run), `dk1sym.py` (+ `xref <fn>`: every E8 call to it).
- Install: kill game, wait 6 s, `cmd /c <full path>\tools\dk1\build.bat` (relative path fails), copy `bin\dbghelp.dll` to the
  game dir, Steam `-applaunch 248610`, `dk1gym.py launch` (HWND_BOTTOM, no activate), ~30 s to menu.
- Bridge: `in.txt` = "seq N" + commands; answer `out.txt` = "seq N", lines, "END". Each line runs in `__try`.
  Commands: `humans` (id team type state x y segs), `state`, `load L I`, `setstate N`, `toggle N`, `pause/resume N`,
  `move id x y`, `goto`, `path`, `cmd type ent v1x v1y v2x v2y i1 i2`, `dbg id`, `poke id off byte`, `restart`.
- Game fields: +4 m_state (eState 5 MAIN_MENU, 6 GAME_LOADING, 7 LOADING_ALMOST_FINISHED waits a click (byte RVA 0x3bc314),
  8 LOADING_FINISHED, 9 DEPLOY, 10 RUNNING, 11 ENDING, 12 ENDED), +0xc m_time (ms), +0x14 m_gameSpeed, +0x18 pause mask,
  +0xc4 m_mapListIndex (eMapList 0 SINGLE 1 RANDOM 2 KILLHOUSE 3 CAMPAIGN 4 COOP), +0xc8 m_mapIndex, +0xcc m_pMap.
  UpdateGameLoading calls LoadMap(+0xc4, +0xc8). SetState 0x14bb90. Server_Pause 0x1605e0 / Resume 0x160650 (resume does
  nothing while lock bit 2 is set; use PauseToggle(0) -> mask 0x1000 = running). Tables: 0x3af854 resume {2,0x100000,0x200000},
  0x3af894 first-unpause {0x1800000,0x800000,0x1000000}, 0x3af8b8 pause {1,0x40000,0x80000}.
- Start flow: menu (5) -> `load 0 0` -> 7 -> `setstate 8` -> 10 (pause 3) -> `toggle 0` -> 0x1000, sim runs.
  `load` straight from ENDING (11) crashes ("Game crashed :(" box); `setstate 5` first, wait 3 s, then load: 5 reloads OK.
- Mission 0/0: humans 18-22 type 2 (suspects), 23-24 type 1 (troopers, start (794,321), (790,261)); +0x90 team reads 0 for all,
  use m_humanType +0xa8. Dead = m_state +0xfc is 0 or 1 (Human::IsDead 0x2d0f0).
- Moving a trooper (player-style): cmd 6 CREATE_PATH (case 0x1696e5: DeletePath, sets m_bSelected 0x11c=1, CreateActionWaypoint
  at v2) then cmd 10 ADD_TO_PATH (v1 = point). Straight ADD_TO_PATH is clipped at the first wall, so `move` feeds every point of
  GeneratePath (static stdcall `(int [h+0xa0], V2 from, V2 to)`, ret 0x14) and then clears 0x11c (= mouse-up).
  Gate in Human::UpdateWaypointsMove 0x9b550: stop if ((flags 0x2b8 >> 5) | byte 0x29c) & 1 or (flags & 9) == 1; uses the last
  m_waypoints segment (data h+0x160, count h+0x164) if seg+0x10 m_bCompleted == 0 and points != 0; while 0x11c == 1 it only walks
  while seg+0xc m_iCurrentIndex < points-1 (so a path still "being drawn" stops at its last point).
  Waypoints (48 B): +0xc m_iCurrentIndex, +0x10 m_bCompleted, +0x20 List<sPoint> (data +0x24, count +0x28); sPoint 12 B
  {timeToWait, origin V2 +4}. `goto` (GeneratePath + SetAIPath) and cmd 2/12 alone do not move troopers.
- Command jump table VA 0x569ee0, index type-1.
- Gym: `dk1gym.py run N out.jsonl --brain idle|rush|pairs --secs S --map L/I` (one JSON record per match: troopers/suspects
  alive, win, state, game_ms, orders). rush = each trooper to its nearest live suspect, pairs = whole team to the suspect nearest
  the team centre; re-path only when the target moved > 48 px. Results 10-24, map 0/0: rush 4/4 wins (11.7-12.7 s, 2/2 troopers
  alive, 0/5 suspects), pairs 1/1 win 11.7 s, idle 0 kills in 30 s. Mission 0 is too easy: next = harder maps.

## DK1 gym on harder maps + workshop maps (2026-10-24/25)
- **Deploy screen** (maps that stop in eState 9): bridge `deploygo` = DeployScreen::OnDeployGO (RVA 0x88c20, this = *(game+0x28)), as the GO button; reaches RUNNING with the troopers. The bare `deploy` (Game::Client_FinishDeploy 0x16afd0) also reached RUNNING but **dropped the troopers**. `dslots` dumps the DeployScreen slots (array +0xc, count +0x10, 0x14 bytes; slot+4 = trooper obj, its +0x70 == Entity::s_playerTeam (RVA 0x3c0c6c); slot+8 != 0 = placed at a spot). OnDeployGO shows a message box when no trooper is placed.
- dk1gym fixes: loading blocks the bridge 10+ s (state() polls with 60 s timeout); run_match waits up to 10 s for troopers; bridge seq is now ms (seconds-seqs collided between back-to-back runs and read stale answers).
- `results/sweep.sh [out] [map:brain ...]`: kills + relaunches the game after a failed run ("Game crashed :(" box).
- Results (`tools/dk1/results/sweep.jsonl` + `sweep_retry.jsonl`, 90 s cap, rush / pairs):

| map | troopers / suspects | rush | pairs |
|---|---|---|---|
| 0/0 | 2 / 5 | win | win |
| 0/10 | 2 / 11 | lose (4 left) | win |
| 0/20 | 4 / 16 | lose | lose |
| 0/30 | 2 / 9 | lose | lose |
| 0/40 | 4 / 21 | lose | win |
| 0/50 | 4 / 16 | lose (timeout) | win |
| 0/60 | 8 / 21 | crash once | lose |
| 0/70 | 6 / 22 | lose | lose |
| 0/80 | 6 / 16 | win (retry) | lose |
| 0/90..0/120 | - | crash | crash |

  Losses with troopers alive and eState 11 = mission failed by objective (hostage/VIP), not wiped out. 0/90+ crash every time, also from a fresh launch: probably past the end of eMapList 0. Pairs beats rush on 0/10, 0/40, 0/50: grouping matters, a real signal for the squad brain.
- **Workshop maps:** `tools/workshop.py list|get <appid> ...` (browse page ids + public GetPublishedFileDetails file_url, no login). DK1: 92 top-rated "Levels" items (724 MB) in `F:\DK1Workshop\<id>\`, 89 unpacked to `<game>\mods\ws<id>\` (zip = folder with mod.xml + levels_<name>/); 2743310779 bad zip, 3494161399 no mod.xml. Not yet checked: whether the game loads them without the in-game Mods menu, and their eMapList/index. FS2 has no Steam Workshop.
