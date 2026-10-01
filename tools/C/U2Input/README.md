# U2Input: click Unreal II's menus and buttons from a script

A `dinput8.dll` proxy for Unreal II's `System` folder. It passes everything to Windows'
real DirectInput and adds a named pipe, `\\.\pipe\U2Input-<pid>`, through which a program
can point, click and press keys in the game, while the game runs in the background and
without touching the real mouse or keyboard.

```python
from u2input import U2Input
inp = U2Input()             # finds the running Unreal2.exe
inp.focus()                 # let the game take input while it isn't the foreground window
inp.vkey(0x75)              # F6: opens the U2Wardrobe menu
inp.click_at(305, 192)      # point at client pixel (305, 192) and click: the "Skaarj" button
```

Build: `build.bat` (Visual Studio x86 compiler) -> `bin\dinput8.dll`; copy it to `<game>\System`.
Remove that file to uninstall. Log: `System\U2Input.log`. `probe.py` captures the game
window (PrintWindow, works when covered) for checking what a click did.

## How Unreal II reads input (what had to be faked)

| input | where the game gets it | what U2Input does |
|---|---|---|
| mouse buttons and movement | DirectInput 8, buffered (`GetDeviceData`), mouse only | adds queued events to what the game reads |
| menu pointer position | `GetCursorPos` in WinDrv.dll, re-read on `WM_MOUSEMOVE` | `cursor X Y` answers WinDrv's `GetCursorPos` with a virtual position and posts a `WM_MOUSEMOVE` |
| focus | WinDrv checks `GetFocus` / `GetForegroundWindow`; DirectInput only delivers to the foreground window | `focus on` answers both with the game window and fakes `Acquire`; the real devices are never acquired (that would take your real mouse) and WinDrv's `SetCursorPos` / `ClipCursor` are swallowed |
| keyboard | window messages (not DirectInput) | `vkey VK` posts `WM_KEYDOWN` / `WM_KEYUP` |

Pipe commands: `ping`, `focus on|off`, `cursor X Y`, `move DX DY`, `click N`, `down N`,
`up N`, `vkey VK`, `vdown VK`, `vup VK` (plus `key`/`tap` for DirectInput keyboards, unused by
Unreal II). Coordinates are client pixels of the game window.

## Verified (2026-09-30), in a background pilot run

- Stock pause menu: pointer moves and hovers (OPTIONS / CREDITS highlight), a click opens Options.
- U2Wardrobe: F6 opens it, clicking "Skaarj" dresses Dalton, the third-person button works, F6 closes it.
- Injected mouse movement turns the player in gameplay.
- The real cursor never moved or was confined while `focus on` was used.

In-game menus only take the mouse while the game is paused (as the pause menu does); a
HUD-style overlay that doesn't pause keeps the mouse on aiming.
