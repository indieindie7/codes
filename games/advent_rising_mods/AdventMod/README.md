# AdventMod

A mod framework for **Advent Rising** (Steam), built with [AdventUCC](../AdventUCC).
It brings the settings of the separate launcher ("Play Advent Rising") into the
game's own options menus, reachable from the title menu and from the pause menu.

> **Fixed 2026-10-03: slow motion and choppy gameplay.** AdventNative made a throwaway
> Direct3D 8 device (to find the game's device methods) without `D3DCREATE_FPU_PRESERVE`.
> Direct3D then drops the game thread's x87 FPU to single precision, and Unreal's frame
> timing (CPU cycle counter, in doubles) breaks: every frame's time step comes out wrong.
> At first it looked like the menu controller killed the frames, because the controller is
> what loads AdventNative; it was this. Measured after the fix: a 10 s wait in game takes
> 10.0 s of real time (before: 22-44 s). Any native code here that creates a device must
> pass FPU_PRESERVE.

| Page | Added |
|---|---|
| Options > Video | **Fullscreen**, **Borderless Window**, **VSync**, and a row that opens Display Options |
| Display Options (new page) | **Widescreen**, **Trilinear Filtering**, **Field of View** (60-120), **Minimum Frame Rate** |
| Graphics (new page, from Display Options) | **Post Effects** preset (Off, Natural, Cinematic, Gritty, Clean), **Soft Shadows**, **Shadows for Others** (the 20 nearest characters on screen), **Anti-Aliasing (SMAA)**, **Frame Cap** (monitor, 30, 60, 120, 144, none), **Shadow Darkness**, **Sharpening**. The post-processing rows need the U2Shaders `d3d8.dll`: AdventNative writes `System\U2Shaders.ini`, which the layer re-reads while the game runs |
| Options > Graphics | **Resolution** lists the five largest common sizes that fit the screen (stock: 640x480 to 1600x1200, 4:3 only) |
| Options > Audio | **Dialogue Volume** (the game saves one and has a caption for it, but never showed the slider) |

Settings apply at once. Borderless, VSync, Trilinear, Widescreen and FOV are saved in
`System\AdventMod.ini` and re-applied at start (the render device never saves
its own); the rest are saved by the game.

**Field of View.** The game has no FOV setting: each camera (third person 75,
first person 85, vehicles 90-95) sets its own when it takes over. The slider is
the third-person value and every gameplay camera is scaled by FOV/75, so the
views keep their relation; scripted camera points keep their framing, and zooms
still return to the scaled value. Nothing is touched at 75. The launcher's own
FOV option is a key-binding hack (`W=MoveForward | OnRelease FOV 75`) that would
undo this on every key release, so the mod removes it from any key at start.

## How it works

No stock game file is replaced.

- **`AdventMod.u`** (UnrealScript, `Classes\`)
  - `ModGUIController` extends the game's menu controller. The game picks that
    class from its config (`GUIController=` in `[Engine.Engine]`), so ours takes
    over `OpenMenu` and swaps in modded pages by name.
  - `ModVideoOptions`, `ModPCOptions`, `ModAudioOptions` extend the stock pages;
    `ModDisplayOptions` is a new page. An options page has at most 7 rows
    (toggles first, then up to 3 sliders).
  - `ModPanel` adds a translucent panel behind a page (the game's labels are dark
    grey and unreadable over a dark scene); colour in `[AdventMod.ModPanel]`.
  - `ModSettings` holds the saved settings, the FOV code and the bridge to native code.
  - `ModMutator` runs in every level (the menu controller is never ticked), also
    while paused (`bAlwaysTick`), and keeps the FOV applied. The game adds the keys of `[DefaultPlayer]` to every
    level URL and its GameInfo loads `Mutator=` from it.
  - `ModTestCommandlet`: `AdventUCC AdventMod.ModTestCommandlet` returns 7 when
    the native bridge works.
- **`AdventNative.dll`** (C, `native\`) does what script can't: the window.
  The engine loads it by itself: a `DynamicLoadObject("AdventNative.X")` finds
  no `AdventNative.u` and falls back to the package's DLL. The DLL then
  redirects Core's `UObject::StaticLoadObject`, so
  `DynamicLoadObject("AdventNative.<Command>", class'Class', true)` becomes a
  call into the DLL; non-None means true. Commands: `BorderlessOn`,
  `BorderlessOff`, `IsBorderless`. It writes `System\AdventNative.log`.

## Install

Players: `Install AdventMod.bat` (see `README.txt`, the player's readme). It
finds the game, backs up what it changes, copies `System\AdventMod.u`,
`AdventMod.int` and `AdventNative.dll`, and adds the configuration lines to
`Mydefault.ini` and `MyDefUser.ini` (and to their copies in `System\Defaults`,
which the launcher's "Default" button restores from). `Uninstall AdventMod.bat`
removes exactly those lines and files. The launcher itself only rewrites its
own settings line by line, so the mod's lines survive it.

Developers: `build.ps1` compiles with AdventUCC, builds the DLL and installs
into the game; `package.py` makes the release zips (with and without the .bat
files) in Downloads.

## Tested

Steam version, Windows 10, 1920x1080, by running the game (`test_run.ps1`) and
pressing the rows from inside through the debug settings:

- Borderless on/off: window measured 1920x1080 without caption, and back.
- VSync, Trilinear, Widescreen: the render device's value changes each way.
- Minimum Frame Rate: the slider sets it and the game saves it.
- Resolution: the list cycles 1024x768, 1280x720, 1366x768, 1600x900, 1920x1080.
- Dialogue Volume: the slider shows and moves.
- Field of View: in a level at 100, the third-person camera goes 75 -> 100
  (log) and the view is visibly wider (screenshot); the launcher's binding is
  removed from W.
- All four pages checked by screenshot.

Not verified: **Fullscreen** (exclusive fullscreen was not run), whether VSync
and Widescreen visibly change the picture, and reaching the pages by hand.

Debug settings, under `[AdventMod.ModSettings]` in `AdventMod.ini`:
`DebugCommands` (console commands at the title menu), `DebugOpenMenu` (a menu
class opened right after the title menu) and `DebugActions` (`clickN`,
`slideN=V`, `native:X` or console commands on that menu). Results are written
to `System\AdventNative.log`.
