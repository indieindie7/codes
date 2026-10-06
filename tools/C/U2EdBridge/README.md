# U2EdBridge

Remote control for **Unreal II: The Awakening's UnrealEd**. Send editor
commands from a script and get back everything the editor logged while running
them. No window clicking, and no message boxes left waiting for someone to
press OK.

```
python u2ed.py start
python u2ed.py exec MAP IMPORT FILE="C:\maps\arena.t3d"
python u2ed.py exec MAP REBUILD
python u2ed.py exec MAP SAVE FILE="..\Maps\Arena.un2"
python u2ed.py stop
```

Or from Python:

```python
from u2ed import Editor

with Editor.start() as ed:              # closes the editor when done
    print(ed.exec(r'MAP IMPORT FILE="C:\maps\arena.t3d"'))
    ed.exec("MAP REBUILD")
    ed.exec(r'MAP SAVE FILE="..\Maps\Arena.un2"')
```

Any command you could type into UnrealEd's command box works. Some examples:

| Command | Does |
|---|---|
| `MAP LOAD FILE=...` / `MAP SAVE FILE=...` | open / save a map |
| `MAP IMPORT FILE=x.t3d` / `MAP EXPORT FILE=x.t3d` | text (T3D) map in / out |
| `MAP REBUILD` | rebuild geometry (BSP) |
| `PATHS BUILD` | build AI navigation |
| `ACTOR ADD CLASS=...` | place an actor at the origin |
| `GET class property` / `SET class property value` | read / change defaults |
| `OBJ LIST CLASS=...` | list loaded objects |

Commands starting with `!` go to the bridge itself: `!ping`, `!answer yes|no`
(how Yes/No message boxes get answered; the default, No, keeps a "save
changes?" prompt from overwriting anything) and `!quit`. `python u2ed.py shell`
opens an interactive prompt.

## How it works

Unreal II ships no engine source or headers. However, its DLLs export their C++
functions under their mangled names, so the bridge finds what it needs by name.

1. `u2ed.py start` does four things:
   - renames dgVoodoo's `d3d8.dll` out of the way (UnrealEd crashes with it);
   - launches `UnrealEd.exe`;
   - loads `U2EdBridge.dll` into it with `u2edinject.exe`;
   - waits for the bridge to answer.
2. Inside the editor, the DLL finds `GEditor` (`Editor.dll`) and its `Exec`
   function, then opens the named pipe `\\.\pipe\U2EdBridge-<editor pid>`.
3. Each line sent down the pipe runs on the editor's **main thread**. The DLL
   posts a message to the main window, which it has subclassed, so commands
   run exactly as if they were typed into the command box.
4. While a command runs, the DLL copies all output from the command, `GLog`
   and `GWarn`. It also intercepts `MessageBoxW/A` in every module, answers
   the box and puts its text in the reply as `[dialog -> No] Title: text`.
5. `u2ed.py stop` closes the editor without saving and puts dgVoodoo back.

The pipe refuses network clients, but any program on your own PC can use it
while the editor runs.

If UnrealEd hits one of its own crashes, the "Critical Error" box keeps the
process alive. The client spots that box and raises `EditorCrashed` with the
crash text, so the script doesn't hang.

## Files

| File | |
|---|---|
| `u2ed.py` | command-line tool and Python client |
| `bin/U2EdBridge.dll` | the bridge (32-bit) |
| `bin/u2edinject.exe` | loads the DLL into a running process (32-bit) |
| `src/` | C source of both |

Some antivirus tools distrust DLL injectors; `u2edinject.exe` only calls
`LoadLibraryW` inside the process whose id you give it. If yours objects,
build it yourself from `src/`.

## Building

Needs [Zig](https://ziglang.org/download/) (used as a C compiler; nothing to
install):

```
zig cc -target x86-windows-gnu -O2 -shared -o bin/U2EdBridge.dll src/u2edbridge.c -luser32 -lkernel32
zig cc -target x86-windows-gnu -O2 -municode -o bin/u2edinject.exe src/u2edinject.c
```

Both must be 32-bit, like the game.

## Tested

Tested on the Steam version (build of Mar 14 2003):

| Step | Result |
|---|---|
| `start` → ready | about 7 s |
| `MAP LOAD` DM-Labs, `MAP EXPORT` → T3D | works (2.3 MB T3D) |
| `MAP IMPORT` that T3D, `MAP REBUILD`, `MAP SAVE` | works (1.7 s / 0.9 s / 0.1 s) |
| log capture | full output returned, e.g. 5,158 lines from the import |
| unknown command | `rc=0` |
| `stop` | editor closed, dgVoodoo restored |

## Known UnrealEd problems (not the bridge)

Both of these also happen when the commands are typed into the editor by hand:

- **`MAP NEW` then `MAP IMPORT` crashes the editor** (General protection fault
  in `FDynamicActor::Update` while redrawing). Import into a freshly started
  editor instead.
- **`PATHS BUILD` on a T3D-imported copy of a stock map runs for more than
  5 minutes.** The import turns the map's path nodes into "Invalid name"
  warnings. Paths on your own maps are untested.

## Viewport pictures (2026-10-05)

`!screenshot` did not catch the editor's D3D8 device in this setup ("no D3D8 device captured yet"). What works
instead: `winshot.py <out.png>` (run with a Python that has Pillow) grabs the editor window with PrintWindow
(PW_RENDERFULLCONTENT reads the D3D viewports too; no mouse, no focus needed). Camera control by command:
`SET PlayerStart Location (X=..,Y=..,Z=..)`, `ACTOR SELECT OFCLASS CLASS=PlayerStart`, `CAMERA ALIGN`, then
`SET Camera Rotation (Pitch=..,Yaw=..,Roll=0)` (SET reaches the viewport cameras; any later selection change
redraws). `ued_tour.py` does a whole tour this way. Never `SET` on `Info`, `ZoneInfo` or a ZoneInfo subclass (LevelInfo, SkyZoneInfo, WarpZoneInfo): general
protection fault. Reason (from reading the engine with Ghidra, 2026-10-05): `SET` runs
`UObject::GlobalSetProperty`, which touches EVERY object of the class, including class defaults and
objects outside the current map, and calls each one's `PostEditChange`; `AZoneInfo::PostEditChange`
dereferences the object's level (`XLevel`) without a null check, and those objects have none. Light,
Keypoint, NavigationPoint, AmbientSound and Emitter only run AActor's harmless PostEditChange.
**Fixed in the bridge (2026-10-05):** U2EdBridge.dll patches `AZoneInfo::PostEditChange` in memory at
startup so it tests the object's level instead of GIsEditor (same length, same jump); verified: `SET Info
bHiddenEd True` now runs with the editor alive (log line "ZoneInfo patch: ... SET Info is safe").
