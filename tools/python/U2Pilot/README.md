# U2Pilot – a test harness for Unreal II: The Awakening mods

U2Pilot launches Unreal II, plays a scripted sequence of inputs, records what
happened and collects the game log. It lets a mod be built, run and checked
without a person sitting at the keyboard. It was made while developing
[U2SoftShadows](../../../games/unreal2_mods/U2SoftShadows) and
[U2SkipCutscenes](../../../games/unreal2_mods/U2SkipCutscenes).

Each run goes to `runs/<time>_<script>/` and contains:
- `video.mp4` and `sheet.png`: a video and a 4×4 contact sheet
- `frames/`: individual screenshots
- `Unreal2.log`: the game log
- `pilot.log`: a step-by-step log of the run

## Two modes

### Background mode (recommended)
```
python u2pilot.py scripts/tuta_full.txt --background
```
The steps are played **inside the game** by the `PilotDriver` mutator
(`unrealscript/U2PilotDriver`). The runner writes the steps to
`System\U2Pilot.ini` and the driver reads them from there.

- **Input** is injected through a `PlayerInput` subclass: movement axes,
  fire, jump, and run/crouch toggles. Nothing touches the real keyboard or mouse.
- **The game is launched without focus**, then kept off-screen. If it grabs
  focus when it hands control back after a cutscene, the runner gives focus
  straight back. It also releases the cursor if the game clips it.
- **Your settings stay untouched:** each run uses throwaway copies of your
  configs (`-ini=PilotRun.ini -userini=PilotRunUser.ini`), with mouse capture
  off, `-nosound` (unless `--sound`), and a 960×540 window.
- **Frames** come from the game's own `shot` command, so recording works even
  when the window is hidden.
- **Log tracking:** every launch is tagged with `?PilotRun=<id>`, and
  `-forcelogflush` makes the log live, so the runner can follow each step as
  it happens.

Background steps:

| Step | Meaning |
|---|---|
| `map URL` | start map; its URL options are kept (e.g. `Atlantis?MissionCompleted=2`) and extra `?Mutator=` entries are merged with the installed ones |
| `ini Section Key=Value` | set a value in the throwaway pilot config (Unreal2.ini copy; a section that only exists in User.ini, like `U2SoftShadows.SSShadowController`, is written there instead, and the log says so) |
| `userini Section Key=Value` | set a value in the throwaway User.ini copy |
| `waitcontrol [timeout]` | wait until the player can move (no cutscene) |
| `wait SECONDS` | wait, counted in game seconds |
| `move FWD STRAFE SECS` | hold movement (-1..1) |
| `turn YAW PITCH SECS` | turn the view (degrees) |
| `fire SECS` / `altfire SECS` / `jump` | press buttons |
| `crouch 1\|0` / `run 1\|0` | set the stance toggles (`run 0` = hold the Walking key) |
| `walk 1\|0` | hold / release the Walking key (Shift) |
| `lean L\|R\|F\|U [SECS]` | hold a lean key (`status` logs the lean direction) |
| `give CLASS` | give a weapon with full ammo and switch to it |
| `status` | log the current weapon, pending weapon and ammo |
| `spawn CLASS [DIST]` | spawn any actor DIST (150) units in front of the player |
| `spawnproj CLASS` | spawn a projectile as if the player fired it |
| `console CMD` | run a console command |
| `shots INTERVAL` / `shot` | take a screenshot every INTERVAL seconds / take one now |
| `travel URL` / `servertravel URL [items]` | change level (`servertravel` goes through the game's own level change; `items` keeps the inventory) |
| `inv` | log the player's inventory |
| `dump CLASS PROP...` | log properties of every actor whose class name contains CLASS |
| `@MAP step` | run the step only on that map (the driver restarts its list on every map) |
| `mark TEXT`, `quit` | write a log marker / quit the game |

### Foreground mode
```
python u2pilot.py scripts/smoke_test.txt
```
This drives the **real** keyboard and mouse through `SendInput`, using scan
codes because the game reads DirectInput. It records the window with
ffmpeg (gdigrab, or ddagrab as a fallback). It also has:
- `waitlevel`: waits until the log shows the level is loaded
- `waitplay`: waits out cutscenes by detecting their flat letterbox bars

Press **F12** to abort. Prefer background mode, because foreground mode takes
over the PC. Its Alt tap, used to grab focus, has also been seen to freeze
Unreal's game loop.

## Probes
`unrealscript/U2Stealth` holds two development mutators for measuring the
game's real values:
- `StealthProbe`: logs enemy sight/hearing, player visibility and noise
  values, and movement speeds.
- `DialogProbe`: logs cutscene and conversation state once a second, plus
  where cutscene stand-in characters' scripts currently are.

## Environment options

- `U2PILOT_LOG=Name.log`: the game logs to this file instead of `Unreal2.log` (when that one is locked, e.g. by a stuck game process).
- `U2PILOT_PARK=X,Y`: park the game window there (e.g. on a side monitor) instead of off-screen.
- `U2PILOT_SYSTEM=<path>`: run from another System folder, e.g. a full test copy next to the real one (`..\SystemBuild`, whose Unreal2.ini lists `..\SystemBuild\*.u` first). Useful to try a d3d8.dll or package without touching the installed game.
- Runs work with the PC locked if dgVoodoo is windowed (`FullScreenMode = false` in that folder's dgVoodoo.conf); in fake fullscreen the game hangs at map load while the desktop is locked.

## Setup
- Python 3 with `imageio-ffmpeg` (`pip install imageio-ffmpeg`).
- Compile `U2PilotDriver` (and optionally `U2Stealth`) with the game's
  `UCC make`, after adding `EditPackages=` lines for them to `Unreal2.ini`.
- Set `GAME_SYSTEM` at the top of `u2pilot.py` if the game isn't in the
  default Steam folder.

## Lessons learned
- Unreal II's cutscenes (matinee), the gaps between dialogue lines, and
  dialogue line lengths all run on **real time**. Changing the game speed
  alone doesn't speed them up.
- `UIConsole.FindLooseComponent` can crash or deadlock the game near level
  loads. Don't call it.
- Loaded saves ignore the URL's `?Mutator=`: the level comes back exactly as
  it was saved, including which mods were running.
