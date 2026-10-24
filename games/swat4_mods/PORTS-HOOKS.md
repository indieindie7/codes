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
