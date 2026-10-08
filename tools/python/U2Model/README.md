# U2Model: basic shapes for Unreal II's editor

Basic shapes you can move, turn, scale and combine with add (`+`) and cut (`-`). They go into UnrealEd as brushes, can be frozen into one static mesh, and have an instant offline preview for mock-ups. Built 2026-10-08 on top of the editor research in `games/research_notes/3D modelling for the UE2 editor`.

```python
from u2model import *
post = box(512, 512, 320).move(0, 0, 64) + box(640, 640, 64)       # block on a plinth
post -= box(448, 448, 280).move(0, 0, 84)                          # hollow it
post -= box(128, 80, 224).move(0, -236, 84)                        # a door
post += stairs(160, 4, rise=16, run=40).rotate(yaw=90).move(0, -480, 0)
post.preview("post.png")                                           # instant picture, no editor
```

**Shapes:**
- `box`, `wedge` (a ramp);
- `cylinder`, `cone` (`r_top` makes a frustum), `pyramid`;
- `sphere`, `dome`;
- `stairs`, `arch` (a wall with an arched opening), `tube` (a pipe section);
- `prism(outline, h)`: any 2D outline, concave ones included;
- `extrude_profile(profile, depth)`: a side profile pushed through a depth.

Each shape sits on its base at the origin, in Unreal units. Every shape can `.move`, `.rotate(yaw, pitch, roll)`, `.scale`, `.mirror`, and `.check()` that it is closed, outward-facing and planar.

**Combining:** a `Model` is the ordered list of add and cut steps. The editor applies them in that order, like stacking brushes by hand.

**Into the editor:** `py build_editor.py demo_post GuardPost`
1. Each step goes in through the builder brush: `BRUSH IMPORT` of a PolyList file, `MOVETO`, then `ADD` or `SUBTRACT`. Brush actors in a `MAP IMPORTADD` are not built by the editor, so this is the only route.
2. `MAP REBUILD` runs the editor's own CSG.
3. `MAP SAVEPOLYS` reads the result back. The polygons inside the model's bounds are its surfaces.
4. Those polygons go back in through `StaticMeshFactory` as a PolyList, giving one static mesh (`U2ModelSM.<Name>`) with its own collision.
5. The test map `U2ModelTest` holds both versions side by side.

**Verified in game** (pilot `u2model_test.txt`): the player rests on the roof and on the hollow interior floor of both the brush version and the frozen mesh, matching within 3 units.

**Pictures:** `shots_editor.py` uses the editor's viewports. The perspective camera doesn't follow `view()` on these maps, and the ortho views (`shots/u2model_editor_front.png`) show the build.

**Faces:** non-convex faces are triangulated. The editor accepts polygons up to 32 vertices, and concave brushes are fine.

**Textures:** `shape.textured("Mission_06T.Surface_Wall.MetlWall_U06A500", scale)` and `model.textured(...)`.
- The editor commands load the texture packages first.
- A cut's faces take the cut brush's texture, so texture the cuts too.
- The freeze keeps every polygon's texture and mapping (`read_polylist_full` / `polylist_full`).

**Kit** (`kit.py`, `build_kit.py`): 9 pieces on fixed metrics.
- Metrics: 512-unit cells, 384-unit storeys, 32-unit walls, 160×256 doors.
- Pieces: floor, ceiling, wall, wall_door, wall_window, pillar, stairs_up, ramp, railing.
- `building(["###", "#.#", "###"], doors={(1, 2, "s")}, windows=...)` gives placements: walls on the outside edges, posts at the outside corners, any number of storeys.
- `build_kit.py` freezes the pieces into `U2KitSM.<piece>` and places a courtyard from them as StaticMeshActors (`U2KitTest`).
- Verified in game: roof, courtyard, room floor and doorway all hold the player at the right heights.

**Reading a mesh from memory:** `!readmesh PKG.NAME FILE` in the ops bridge (`tools/C/U2EdBridge`), decoded by `readmesh.py`.
- It reads the mesh's source triangles (positions, UVs, vertex colours, material, smoothing) straight out of UnrealEd.
- It checks the memory layout first and refuses if it looks wrong.
- It lazy-loads meshes that come from a package.
- `readmesh.to_t3d` writes them back in the editor's own mesh text format.

**Package gotchas:**
- The editor ignores `GROUP=` in `NEW StaticMeshFactory`, so meshes are `PKG.Name`.
- Saving a package after `OBJ LOAD`ing it keeps only this session's new objects, and the file is held open. So each builder writes its WHOLE package to a side file and swaps it in after the editor closes.

**Next:**
- An AO bake into vertex colours for the frozen meshes.
- Trim-sheet UVs.
- The level generators placing kit buildings.
