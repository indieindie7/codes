# SolusBorderlessFps (The Solus Project, Steam 313630, UE4 x64 D3D11)

Two small fixes for a game its developer stopped updating:

1. **No exclusive fullscreen.** The game's "Fullscreen" mode takes over the display, so Alt+Tab is slow and the screen flickers. `solus_patch.py` changes 6 places in the exe (same size, 21 bytes in total) so the renderer never asks DXGI for exclusive fullscreen; the game runs as a borderless window even when the settings say fullscreen. Alt+Enter keeps working.
2. **FPS graph.** `winmm.dll` (a proxy for the system winmm) draws an fps number, the average frame time in ms and 240 scrolling frame-time bars in the top right corner (green up to 16.7 ms, yellow up to 33.4 ms, red above). F10 toggles it.

The two parts are independent; use either one alone.

## Install

Game folder: `...\steamapps\common\TheSolusProject\Solus\Binaries\Win64`

**FPS graph:** copy `winmm.dll` from the release zip into that folder. Remove = delete it.
Optional `solus_fps.ini` next to it:

```ini
[fps]
graph=1   ; 0 = start hidden
log=1     ; solus_fps.log, one line per second: fps, average ms, worst ms
key=121   ; toggle key, Windows virtual-key code (121 = F10)
```

**Borderless patch:** the Steam exe is wrapped (SteamStub), so the patch needs your own unwrapped copy:

1. Back up `Solus-Win64-Shipping.exe`.
2. Unwrap your exe with [Steamless](https://github.com/atom0s/Steamless) and put the result in place of the original.
3. `py solus_patch.py apply "<path>\Solus-Win64-Shipping.exe"` (checks every byte first and writes nothing on a mismatch).
4. In the game options pick borderless/windowed fullscreen at your desktop resolution.

Undo: `py solus_patch.py undo "<path>"`, or restore your backup. Steam "verify files" also restores the original exe.

No game files are in this repo or in the zip.

## How it works

- Patch list with offsets and the reason for each: `solus_patch.md`. It targets `FD3D11Viewport` (constructor, `Resize`, swap chain reset): the stored fullscreen flag is forced to 0 and `SetFullscreenState` always gets FALSE. Offsets are for the unwrapped exe of the final Steam build (unwrapped size 48197632 bytes).
- `solus_fps.cpp` hooks `IDXGISwapChain::Present` through the vtable and draws with `ID3D11DeviceContext1::ClearView` (solid rectangles), so it touches no pipeline state.
- Steam overlay: the overlay hooks the start of `Present` and calls back through the vtable, which loops into any vtable hook. The proxy keeps its own entry to the real function (first 14 bytes from `dxgi.dll` on disk plus a jump). If a Windows update changes those bytes, the proxy logs it and stays off instead of crashing.

## Build

`build_solus_fps.bat` (MSVC x64) writes `out64\winmm.dll`.

## Tested

Windows 11, Steam build, Steam overlay on: 40 s run at a steady 60 fps with the graph, borderless at 1920x1080, Alt+Enter confirmed by the player. Not tested: other resolutions lower than the desktop (the window may come up small), GOG build.
