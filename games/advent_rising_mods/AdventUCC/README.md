# AdventUCC

The missing `ucc` for **Advent Rising** (2005, Unreal Engine 2 build 2226).
GlyphX shipped the UnrealScript compiler inside `System\Editor.dll` but not the
`ucc.exe` that runs it, and no SDK was ever released. AdventUCC runs those
commandlets, so the game's scripts can be exported to source and new script
packages can be compiled.

    AdventUCC batchexport EonGame.u class uc C:\src\EonGame\Classes
    AdventUCC make

Tested on the Steam version: all 17 script packages export (1,938 classes), a
new package compiles and loads back, and compile errors are reported with file
and line.

## How it works

The game's own launcher (`advent.exe`) holds the platform code a `ucc.exe`
needs (memory, files, config, log), so AdventUCC reuses it instead of
re-creating it:

1. `AdventUCC.exe` starts `advent.exe` suspended and loads `AdventUCCHook.dll`
   into it.
2. The hook redirects Core.dll's `UObject::StaticLoadClass` export. The
   launcher's first class load after `appInit` is the game engine class; at
   that point the engine is initialised but no window, renderer or level exists.
3. Instead of loading the game engine, the hook sets the UCC globals, creates
   the commandlet (`Editor.<Name>Commandlet`) and calls its `Main`, then ends
   the process. The game itself never starts.

Extras the hook adds:
- commandlet output (the engine's `GWarn`) is captured and printed
- compile errors get their `file(line)` (the game's feedback device drops it)
- a guard for an engine bug: the class exporter crashes on empty exported
  object references in a class's defaults
- a failed compile returns exit code 1

Nothing in the game folder is modified. AdventUCC uses its own config
(`work\AdventUCC.ini`, a copy of the game's `default.ini` made on first run)
and removes the engine's `Running.ini` marker afterwards.

## Compiling a package

1. Put the source in `<game>\MyPackage\Classes\*.uc`.
2. In `work\AdventUCC.ini`, section `[Editor.EditorEngine]`: remove
   `EditPackages=UnrealEd` (the game ships no `UnrealEd.u`) and add
   `EditPackages=MyPackage` after the last entry.
3. `AdventUCC make` - writes `<game>\System\MyPackage.u`. Existing packages
   are never rebuilt (delete a `.u` to recompile it).

## Settings (environment variables)

- `ADVENT_SYSTEM` - the game's `System` folder (default: the Steam library on H:)
- `ADVENTUCC_TIMEOUT` - seconds before the game process is stopped (default 300;
  a timeout usually means the game opened an error dialog)

The Steam copy's `advent.exe` refuses to start without Steam ("Failed to find
Steam"): Steam must be running. AdventUCC sets `SteamAppId` and adds Steam's
folder to the path, which is what Steam does when it launches the game.

## Building

`build.bat` - needs Visual Studio with the C++ desktop workload (32-bit target).
