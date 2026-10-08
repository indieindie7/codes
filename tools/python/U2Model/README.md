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
4. Those polygons go back in through `StaticMeshFactory` as a PolyList, giving one static mesh (`U2ModelSM.Shapes.<Name>`) with its own collision.
5. The test map `U2ModelTest` holds both versions side by side.

**Verified in game** (pilot `u2model_test.txt`): the player rests on the roof and on the hollow interior floor of both the brush version and the frozen mesh, matching within 3 units.

**Pictures:** `shots_editor.py` uses the editor's viewports. The perspective camera doesn't follow `view()` on these maps, and the ortho views (`shots/u2model_editor_front.png`) show the build.

**Faces:** non-convex faces are triangulated. The editor accepts polygons up to 32 vertices, and concave brushes are fine.

**Next:**
- `!readmesh` in the bridge DLL: read a built mesh's triangles straight from memory instead of the export round-trip.
- Trim-sheet UVs and an AO bake into vertex colours for the frozen meshes.
- A kit of pieces on a grid for the level generators.
