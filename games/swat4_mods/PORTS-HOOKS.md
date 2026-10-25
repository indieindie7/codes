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
