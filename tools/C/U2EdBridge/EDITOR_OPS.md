# Per-actor editor operations for Unreal II's UnrealEd

Select by name, move/rotate one actor, relight only some static meshes, and ask why a spot is dark,
from a script, without the copy-all / delete / re-import / relight-everything round trip.
Found by reading the Ghidra decompile of `Editor.dll`, `Engine.dll` and `Core.dll` (build of
Mar 14 2003, project `Documents\U2_research\ghidra\U2Ed.gpr`), 2026-10-07. Nothing here was run in
UnrealEd yet: another session was using the editor. The lighting study is in [LIGHTING.md](LIGHTING.md).

Status key: **verified** = read in the decompile/assembly; **built** = compiles, never run;
**guess** = inferred, test it first.

## 1. Select by name

**There is a stock command for one name (verified):** `SELECTNAME NAME=<ActorName>`, top level in
`UEditorEngine::Exec` (string `u_SELECTNAME` at 0x102b4828, code at 0x10263d43). For every actor in
`Level->Actors` it calls `SelectActor(Level, Actor, Actor->GetFName()==Name, bNotify=0)`. So it:
- selects exactly that actor and **deselects every other one** (no adding to a selection);
- does not call `NoteSelectionChange` (no undo step, the property window and pivot don't update);
- runs only after `ULevel::Exec` and `UEngine::Exec` turned the line down (they don't handle it).

`Exec_Actor` has no `NAME=` (NONE, ALL, INSIDE, INVERT, OFCLASS, OFSUBCLASS, GROW, DELETED,
MATCHINGSTATICMESH, MATCHINGZONE, BRUSH, SELECTED, UNSELECTED), `Exec_Select` only has `NONE`, and
`Exec_Poly` selects surfaces. So `SELECTNAME` + `ACTOR ...` works today for one actor with the normal
bridge, e.g. `SELECTNAME NAME=StaticMeshActor12` then `EDIT COPY`.

**Bridge command (built):** `!select [+] PAT ...`, `!deselect PAT ...|all`, wildcards `*` `?`,
`selected` = the current selection. It calls the editor's own functions through `GEditor`'s vtable
(slots read from `??_7UEditorEngine@@6BUObject@@@`): `Trans->Begin` (0x78), `SelectNone` (0x134),
`SelectActor(level, actor, 1, 0)` (0x130) per match, `Trans->End` (0x7c), `NoteSelectionChange`
(0xe8), `RedrawLevel` (0xdc). `SelectActor` itself calls `Modify()` and flips `bSelected`
(actor+0x364, mask 0x200), the same as clicking. The builder brush is never matched.
`!list [PAT] [class=CLS]` prints `Name Class (Location) (Rotation) [selected]`, one per line.

## 2. Move / rotate

**No stock per-actor move (verified).** `BRUSH MOVETO` / `MOVEREL` move the builder brush
(`Exec_Brush`, "Brush MoveTo"). The viewport drag path is `FEdModeTools::MoveActors` ->
`MoveSingleActor` (Location += delta at +0x124, Rotation at +0x130, sets `bLightChanged`,
`ClearRenderData`); it is not reachable from a command. `SET` is class-wide.

**Bridge command (built):** `!move PAT x y z [pitch yaw roll]` (PAT must match one actor; `-` keeps a
value) and `!moveby PAT dx dy dz [dp dy dr]` (every match). Per actor, inside one undo transaction:
1. `Modify()` (vtable 0x24) so Ctrl+Z works;
2. write `Rotation` (offset from the property system, checked = 0x130);
3. `ULevel::FarMoveActor(actor, dest, bTest=0, bNoCheck=1, bAttachedMove=0)` (export; it re-hashes
   collision, moves attached actors, re-zones via `SetZone`, `ClearRenderData`; with bNoCheck there is
   no encroachment test, the same as the editor's own placement);
4. `PostEditMove()` (vtable 0x8c, empty for AActor, real for Mover/NavigationPoint/Projector/
   FluidSurfaceInfo) and `PostEditChange()` (0x54: in the editor sets `bLightChanged`, `ClearRenderData`);
5. `RedrawLevel` + `UpdatePropertiesWindows`.
Static lighting is stale after a move until `!light` or `LIGHT APPLY` (the move sets `bLightChanged`,
so `LIGHT APPLY CHANGED=1` picks it up). Brushes still need `MAP REBUILD`.

## 3. Light only these actors

**`LIGHT APPLY SELECTED=1` does nothing different from `LIGHT APPLY` (verified).** `Exec_Light`
parses `SELECTED=` and `CHANGED=` and calls `shadowIlluminateBsp(Level, Selected, Changed)`, but that
function never reads its `Selected` argument (no access to `[EBP+0xC]` in its assembly). U2Avalon's
`lowsun.py`, `island_batch.py` and `carve.py` use it believing BSP is left alone; it is not: every
`SELECTED=1` run re-lit the BSP and every static mesh. uedlib's `light()` docstring is corrected.

`CHANGED=1` is real: BSP lightmaps keep their layout and per-light bitmaps, and only lights with
`bLightChanged` are re-rendered; static meshes relight only if they or one of their lights changed.
Caveats: after `MAP REBUILD` the BSP has no lightmaps, so the first light must be a full one;
`SET Light ...` and the bridge's `hide_icons()` call `PostEditChange` on every light, which flags all
of them changed.

**Bridge command (built):** `!light PAT ...|selected` relights the vertex lighting of those
StaticMeshActors only, the way `shadowIlluminateBsp` does it per actor: `ClearRenderData`,
`GetActorRenderData` (refreshes the BSP leaves the actor touches), `GetPrimitive()->Illuminate(actor,
0)` (vtable 0x84, checked to be one of the four exported `Illuminate`s), `ClearRenderData`. BSP
lightmaps, terrain and other actors are untouched. It refuses movers, brushes, non-`bStatic` actors
(the engine bakes nothing for them) and hidden ones (`UStaticMesh::Illuminate` skips actors with
`bHiddenEd`/`bHiddenEdGroup`, so hidden actors keep stale or no lighting under LIGHT APPLY as well).

`!lights NAME` and `!lightsat x y z` print what the static lighting can use there: the BSP leaf/zone,
the zone's `AmbientBrightness/Hue/Saturation`, and the lights in the leaf light lists with their
type, brightness, radius and `bSpecialLit` (a mismatch with the actor means that light skips it).

## 3b. Baked lighting write-back (built 2026-10-07, never run)

`!meshverts [PAT] FILE` (engine geometry/colours/lights dump for U2Bake), `!bakeload FILE` (per-vertex
colours into the static-mesh instances, through a hook on the engine's StaticLight), `!bakeclear PAT|all`,
`!bakeinfo [derive on|off]`, `!setprop NAME PROP VALUE` (one property of one actor, e.g. one ZoneInfo's
AmbientBrightness - `SET` is class-wide). Evidence, formats and the test plan: LIGHTING.md section 7.
If PAT is left out of `!meshverts`, the path must not contain spaces.

## 4. New content in the running game

- **Unique package per change works (recommended).** `DynamicLoadObject("AvalonSM_3.Group.Mesh",
  class'StaticMesh')` loads a package the game hasn't opened; nothing in the engine prevents it. U2
  has no `SetStaticMesh` native, but `Actor.SetPropertyText("StaticMesh", "AvalonSM_3.Group.Mesh")`
  (exported, ignores `const`) works on a spawned non-static actor, and the live-edit mutator already
  spawns `CardMesh`es. Old packages stay loaded until map change; name them `AvalonSM_live<N>` and fold
  them back into `AvalonSM` on the next full build.
- **Reloading the same package in place does not work.** `UObject::ResetLoaders(Pkg, 0, 0)`
  (exported, decompiled) detaches the package's linker and closes its file, which would free
  `AvalonSM.usx` for overwriting, but every object already loaded stays in memory under the same name,
  so a later load returns the old meshes; replacing them needs garbage collection of objects the level
  still references. Not worth it.

## Using it

The ops build is a separate DLL with its own pipe (`\\.\pipe\U2EdBridgeOps-<pid>`), window message
(WM_APP+0x56) and log (`bin\U2EdBridge_ops.log`), so it is injected beside the working bridge into a
running editor and never replaces it:

```python
from uedlib import Ed, Ops, session
def job(ed):
    ed.load("TutA_Live2")
    ops = Ops.attach_to(ed.pid)                     # injects bin\U2EdBridge_ops.dll
    print(ops.exec("!opsinfo"))                     # offsets/flags it resolved; refuses if they look wrong
    print(ops.list("A1*_B_*"))
    ops.select("A17_B_dorm")
    ops.move("A17_B_dorm", 1200, -300, None, yaw=16384)
    ops.light("A17_B_dorm")                         # only this mesh's vertex lighting
    print(ops.lights_at(-349, 1388, 600))           # inside TutA's tower: zone, ambient, lights
session(job)
```

Build (does not touch `bin\U2EdBridge.dll`):

```
zig cc -target x86-windows-gnu -O2 -shared -DU2ED_OPS -o bin/U2EdBridge_ops.dll src/u2edbridge.c -luser32 -lkernel32
```

`src/editor_ops.c` holds all of it; `u2edbridge.c` only `#include`s it under `U2ED_OPS` and switches
the pipe/message/log names. Without `-DU2ED_OPS` the source builds the same bridge as before.

### Safety checks in the code

On the first `!` ops command it checks, and disables itself (logged) if any fails: every export it
needs is present; `GEditor`'s vtable is exactly UEditorEngine's (the slot numbers were read from it);
`Location`/`Rotation`/`XLevel`/`bSelected` found through the property system sit at the offsets the
decompiled code uses (0x124 / 0x130 / 0xd4 / 0x364 mask 0x200). Property lookup walks
`UStruct::Children` (+0x3c) / `UField::Next` (+0x2c) / `SuperField` (+0x28) and reads
`UProperty::Offset` (+0x48) and `UBoolProperty::BitMask` (+0x6c), all taken from Core's own
`GlobalSetProperty`, `StaticExec`, field-finder and `UBoolProperty::ExportTextItem`.
Values are printed with the engine's own `UProperty::ExportText` (vtable 0xa8).

### What to test first (in this order)

1. `!opsinfo` on an open map: offsets as listed above, actor count sane.
2. `!list` and `!select` on two names, then `ACTOR ...`/`EDIT COPY` to confirm the editor sees the selection; Ctrl+Z.
3. `!move` one StaticMeshActor, `MAP EXPORT` to check the T3D Location/Rotation, Ctrl+Z.
4. `!light` one actor next to a lamp; compare with a full `LIGHT APPLY` on a copy of the map.
5. `!lightsat` inside TutA's tower (see LIGHTING.md, "the dark tower").

Guessed, not verified: that `FarMoveActor`'s attached-actor move and `SetBase(NULL)` are harmless for
StaticMeshActors (they have no base), and that injecting a second bridge beside the first causes no
trouble (separate pipe and message; both subclass the main window and chain to the previous proc).


## !readmesh PKG.NAME FILE (2026-10-08)

Reads a static mesh's source triangles (`UStaticMesh::RawTriangles`) straight from memory and writes them to a binary "U2RM" file. Python decodes it with `tools/python/U2Model/readmesh.py`.

- **Finding the mesh:** `StaticFindObject` in memory first (a mesh made this session has no file yet), then the bare object name, then `StaticLoadObject`.
- **Lazy loading:** a mesh from a package keeps its triangles on disk. The lazy array's own `Load()` (FLazyLoader at +0x12c, vtbl[0]) brings them in. The TArray is at +0x138, `FStaticMeshTriangle` is 0x104 bytes, and Materials are at +0xf8.
- **Layout check:** every triangle must have NumUVs 1..8 and a material index within range, or the command refuses.
- **Verified:** on a fresh mesh and on one loaded from `U2KitSM`. `wall_door`: 28 triangles, both materials, the right bounding box.
