# Running old games in the background (how each chat does it)

Goal shared by all chats: a script drives and captures the game while the user
keeps using the PC. That means no stolen focus, no cursor clipping, and no
global SendInput/keybd_event. Every method below follows the same rules:

- **Fake focus inside the process.** Never acquire the real input device.
- **Input goes to the game's own window or code.** Use window-targeted
  PostMessage, injection inside the game, or a fake DirectInput device.
- **Park the window off-screen or on another monitor.** Capture frames with
  PrintWindow or the game's own screenshot command.
- **Leave the user's settings alone.** Use throwaway config copies, or restore
  the originals afterwards.
- **Run one instance at a time.** Kill the game before replacing a DLL it has loaded.

---

## 1. Unreal II: U2Input proxy and U2Pilot (unreal2 chat)

### U2Input (`tools/C/U2Input/`)

**What it is.** U2Input is a `dinput8.dll` proxy placed in `<game>\System\`.
- Log: `U2Input.log`
- Control pipe: `\.\pipe\U2Input-<pid>`

**`focus on` (fake focus).** It IAT-patches these WinDrv imports:
- `GetFocus`
- `GetForegroundWindow`
- `GetCursorPos`
- `SetCursorPos`
- `ClipCursor`

It also fakes `Acquire`.
- The real device is never acquired. An earlier version acquired it, and the
  game confined the user's cursor 27 times.

**How Unreal II reads input:**
- **Mouse:** DirectInput8 buffered `GetDeviceData`. The proxy feeds fake deltas into it.
- **Keyboard:** window messages. The proxy posts `WM_KEYDOWN`, `WM_KEYUP` and `WM_CHAR`.
- **Menu pointer:** `GetCursorPos` is re-read on `WM_MOUSEMOVE`.
  - `cursor X Y` posts `WM_MOUSEMOVE`.
  - Clicks are fake DirectInput buttons.

**Clients:**
- `u2input.py`: the low-level pipe client.
- `u2ctl.py`: the high-level driver. It supports `exec "cmd"` through the
  console, `press`, `hold W 1.5`, `look`, `fire`, `click X Y` and `run file`.

**Window and capture:**
- `U2PILOT_PARK=X,Y` parks the window, for example `-1800,60` on the left monitor.
- `probe.py` captures with PrintWindow. This works even behind a browser.

### U2Pilot `--background` (`tools/python/U2Pilot/`)

Run it with `python u2pilot.py scripts/<x>.txt --background`.

**Driver.** The steps run inside the game through the `PilotDriver` mutator.
- The runner writes the steps to `System\U2Pilot.ini`.
- Input goes through a `PlayerInput` subclass, so the real keyboard and mouse are never touched.

**Launch:**
- The game starts without focus and is then kept off-screen.
- If the game grabs focus after a cutscene, the runner gives it straight back.
- If the game clips the cursor, the runner releases it.

**Settings stay untouched.** The game runs with throwaway configs:
- `-ini=PilotRun.ini -userini=PilotRunUser.ini`
- mouse capture off
- `-nosound`
- a 960x540 window

**Frames and logs:**
- Frames come from the game's own `shot` command, so recording works while the window is hidden.
- `-forcelogflush` and the `?PilotRun=<id>` tag let the runner follow the live log step by step.
- Results go to `runs\<time>_<script>\`.

**Borderless.** Use dgVoodoo with `FullScreenMode=true` and
`FullscreenAttributes=fake`. The Borderless Gaming `dxgi.dll` squashed the
window, so it was moved aside.

**Caveats:**
- The game stalls while loading if it is unfocused.
- Killing the game leaves `Running.ini` behind, so the next start runs crash recovery.

## 2. Advent Rising (advent rising modding chat)

**Launch.** Start the exe directly with the Steam environment set:

```powershell
$env:SteamAppId='3800'; $env:SteamGameId='3800'
$env:PATH = "<Steam folder>;$env:PATH"
Start-Process "$g\System\advent.exe" -WorkingDirectory "$g\System"
```

- Check that no other instance is running first. Two instances corrupt the ini.
- Read `System\Advent.log` afterwards.

**Background runs.** Advent has no DirectInput proxy and no fake focus.
- `AdventMod/test_run.ps1` parks the game window off the left edge of the screen (`SetWindowPos`), hands focus straight back to the previous window (`AttachThreadInput` + `SetForegroundWindow`), and grabs screenshots with `PrintWindow`.
- The game is driven from inside by script: ModPilot steps (`GOTO`, `SPAWNPACK`, `FLOORMAP` and others) run by the mod, not by injected input.
- `AdventNative.dll` only does a borderless resize/restore of the game window.

## 3. Hydrophobia: Prophecy, the HydroWater mod (this chat)

HydroWater is a `dinput8.dll` proxy. The background switches live in `HydroWater.ini` in the game folder.

| Key | Effect |
|---|---|
| `borderless = 1` | Borderless window at desktop size. The swap chain is kept, not exclusive fullscreen. |
| `background = 1` | Fake focus. The user32 calls `GetForegroundWindow`, `GetFocus`, `GetActiveWindow` and friends are hot-patched in-process, with E9 detours chained if another hook got there first. DirectInput devices are switched to background/non-exclusive cooperative level. The game keeps running and rendering unfocused. |
| `control = 1` | The game polls the control file `HydroWater.cmd` in its folder. |

**Control file commands.** Write one line per command, CRLF-terminated.

| Command | Effect |
|---|---|
| `shot <path.bmp>` | Saves a frame from the game's own back buffer. |
| `chapter <n>` | Loads a level. Use it from a fresh menu, or from inside a level. |
| `continue` | Continues the game. |
| `state` | Logs the game state: 0x29 menu, 2 playing, 0x1a popup. |
| `key <vk>` | Posts a key to the game window. |
| `click [r] [x y]` | Posts `WM_MOUSEMOVE` and then button down/up messages. The game reads mouse buttons from window messages and only the deltas from raw input. |

**Write the path as an argument.** In bash, never put the path inside the printf format string, or its backslashes become escapes:

```bash
printf 'shot %s\r\n' "$(cygpath -w "$S/x.bmp")" > "$G/HydroWater.cmd"
```

**Launch steps:**
1. Run `steam://rungameid/92000`. The exe is SteamStub-wrapped, so it is never patched on disk.
2. The settings launcher dialog always appears. The script presses Start with `BM_CLICK` (control id 1) on the dialog's handle. No real click is needed.
3. Park the window at off-screen coordinates, then capture it with PrintWindow or `shot`.

**Caveat (2026-10-10).** Since the Steam update of 2026-10-09,
`background=1` and `control=1` crash inside `gameoverlayrenderer.dll`
right after the device is created.
- Borderless alone works.
- Workaround (2026-10-10): launch with the game's own `-nopause` switch (`steam.exe -applaunch 92000 -nopause`). With `background=0` it keeps simulating while unfocused; window-targeted `PostMessage` mouse clicks were not picked up during the logo screen.
- The shipped default is `borderless=1, background=0, control=0` until the culprit is found.
- The suspects are the user32 hot-patches, the DirectInput vtable hooks, and the Present vtable patches.

---

## Quick comparison

| | Unreal II | Advent | Hydrophobia |
|---|---|---|---|
| Hook point | dinput8 proxy plus mutator | Steam env launch, DI proxy approach | dinput8 proxy |
| Fake focus | IAT patches in WinDrv | same idea | user32 hot-patches plus DI background level |
| Input | pipe: posted messages and fake DI mouse | same idea | control file: posted messages |
| Script channel | named pipe, U2Pilot.ini | none | `HydroWater.cmd` |
| Capture | PrintWindow, game `shot` | Advent.log | `shot` from the back buffer, PrintWindow |
| Window | parked, dgVoodoo borderless | normal | borderless, parked |
