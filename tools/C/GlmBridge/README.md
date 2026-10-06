# GlmBridge

Remote control for **Unreal II's Golem Studio** (`GlmEd.exe`), the character/mesh editor.
Where [U2EdBridge](../U2EdBridge) drives UnrealEd through its `Exec` interface, this
drives Golem through its own command layer, found by reading `GlmLib.dll` with Ghidra
(notes: `Documents\U2_research\ghidra`, not in git).

```
python glm.py start
python glm.py exec "!windows"
python glm.py exec "!commands"
python glm.py exec "EditFileSave"
python glm.py stop
```

## How Golem takes commands

- Every editor window carries a `GLM::WWindow` object (`WWindow::StaticWindowGetObject` =
  `GetWindowLong(GWL_USERDATA)`), and a `WWindow` is a `GLM::RObject`.
- `RObject::ExecuteCommand(CDatString &result, const char *line)` splits the line into words
  (double quotes group words; a backtick is a quote), finds the first word in the object's class
  and its parents (`RClass::GetCommandNamed`), checks the parameter count and calls it. The
  menus run their items through the same table, so anything a menu does has a command name.
- `LOG_AddTarget` registers a log sink; the bridge uses one to return everything Golem logs
  while a command runs.

## Protocol

One line per command on `\\.\pipe\GlmBridge-<pid>`; the answer is the captured log, the
command's own result text, then `<<<GLM rc=N>>>` (1 = the command ran, 0 = not handled).

| Line | Does |
|---|---|
| `<command words>` | run on the main window's object |
| `/Folder/File.gem/Object <command>` | run on that workspace-tree item (`item:/...` is the same; Git Bash rewrites a leading `/`, so use `item:` there or `export MSYS2_ARG_CONV_EXCL='*'`) |
| `/Folder/File.gem !commands` | the command table of that item's class chain |
| `!tree [depth]` | the workspace tree with each item's class |
| `!classes` | every GLM class that has commands, with its table (from GlmLib's exported sClass statics) |
| `win:<command>` | a WINDOW command on the main window (what the main menu runs: UseLastWorkspace, VssEnable, TickBackground, TexturesUseWorkspace ...) |
| `@<hwnd hex> <command words>` | run on that window's object (hwnds from `!windows`) |
| `!windows` | every window of the process: hwnd, Win32 class, title, GLM class of its object |
| `!commands [hwnd]` | the command table of that object's class chain, with parameter counts |
| `!answer yes` / `!answer no` | how Yes/No message boxes are answered (default No); boxes are logged as `[dialog -> ...]` |
| `!log` | the last 64 log lines Golem wrote |
| `!ping`, `!quit` | |

`glm.py` renames `System\dxgi.dll` (the BGProxy, not part of the game) aside while Golem runs,
as `golem.py` does, and uses U2EdBridge's `u2edinject.exe` to launch GlmEd suspended with the
DLL already inside.

## Build

```
zig cc -target x86-windows-gnu -O2 -shared -o bin/GlmBridge.dll src/glmbridge.c -luser32 -lkernel32
```

## State

2026-10-05: works. `!tree` lists the loaded workspace (U2Import.gws: Weapons, Creatures, Malcolm.gem with
MalcolmModel/Triangles/Vertices/BonePoints/Hierarchy/Materials/Scripts/Lod...), `/Malcolm/Malcolm.gem
TotalFrameCount` runs and its result box comes back as `[dialog -> OK] Total Frame Count: 1 frames`.
Golem's panes (Workspace, Entity) are separate `#32770` dialogs and the render view is a
`GLM_WIN_WEdRenderWindow`; before a workspace loads `!windows` shows only `WEdMainWindow`. The
commands live on the tree objects (12 classes, 104 commands: `!classes`), all with 0 parameters, i.e.
they are the menu actions and some open their own dialogs (file pickers are not MessageBoxes, so a
command that opens one blocks until it is closed from outside; `ExportAttributes` does that).

Golem starts with no workspace unless `UseLastWorkspace` (DWORD 1) is set under
`HKCU\Software\Legend Entertainment\Golem\Golem Studio` next to `LastWorkspace`; glm.py does not
set it, set it once by hand (done on this PC). `!quit` answers the exit confirmation Yes so settings save.
