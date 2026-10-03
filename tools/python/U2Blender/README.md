# U2Blender

Unreal II (Unreal Engine 2) maps in Blender and back, through UnrealEd's T3D text format.

```
UnrealEd ──MAP EXPORT──▶ map.t3d ──Import──▶ Blender ──edit──▶ Export ──▶ map_edit.t3d ──MAP IMPORT──▶ UnrealEd
```

- **Brushes** become meshes, one object per brush, in collections `UE Brushes Add`,
  `UE Brushes Subtract` and `UE Brushes Other` (builder brush, volumes). Each face keeps its
  texture (as a material named after it) and its texture alignment (face attributes `ue_origin`,
  `ue_texu`, `ue_texv`, `ue_pan`, `ue_flags`), which moves, turns and scales with the object.
  Set the viewport's Solid shading to *Object* colour to see add (blue) and subtract (orange)
  brushes as in UnrealEd.
- **Lights** become Blender point lights (colour from hue/saturation; the energy is a rough
  estimate from brightness and radius, see the light's `ue_note`).
- **Static meshes** become cube empties, or the mesh itself when the import's *Static mesh
  folder* has it as `<Name>.obj` (for example exported with umodel; that path is untested).
- **Every other actor** (player starts, triggers, AI paths, scripted sequences) becomes an
  empty with its original T3D text in the custom property `ue_t3d`.

Export writes every actor back from its own text, changing only what was edited: an actor that
was not touched comes out word for word; a moved or turned one gets new `Location`/`Rotation`
(and `DrawScale3D` if scaled). Brushes are written in world space around their object's origin
(no rotation, scale or pre-pivot left on them). New meshes put in `UE Brushes Add` or
`UE Brushes Subtract` become new brushes (texture alignment: planar, one texel per unit, along
the face's main axis); new lights become new `Light` actors. Actors are written in their
original order, new ones last: brush order is what CSG builds from.

Units: the importer's *Scale* (default 0.02 Blender units per Unreal unit, about 1 m per 50
units) is stored in the scene and used again on export. Unreal is left-handed, Blender is not:
Y is mirrored both ways (see `t3d.py`).

## Install

Blender 4.2 or newer: zip this folder (`U2Blender/`, with `__init__.py` at its top) and use
*Edit > Preferences > Get Extensions > Install from Disk*, or copy the folder into Blender's
`scripts/addons/`. The menus are *File > Import / Export > Unreal T3D map (.t3d)*.

## With U2EdBridge (no clicking in UnrealEd)

```
python u2ed.py start
python u2ed.py exec MAP LOAD FILE="..\Maps\MyMap.un2"
python u2ed.py exec MAP EXPORT FILE="C:\work\MyMap.t3d"
    (Blender: import, edit, export C:\work\MyMap_edit.t3d)
python u2ed.py exec MAP IMPORT FILE="C:\work\MyMap_edit.t3d"
python u2ed.py exec MAP REBUILD
python u2ed.py exec LIGHT APPLY
python u2ed.py exec PATHS DEFINE
python u2ed.py exec MAP SAVE FILE="..\Maps\MyMap_edit.un2"
python u2ed.py stop
```

Always save under a new name: the original map stays as it was.

`MAP REBUILD` only rebuilds geometry: lighting (`LIGHT APPLY`, UnrealEd 2's lighting build;
if Unreal II's editor names it differently, its Build menu does the same) and AI paths must be
built too, or the map comes out unlit and without paths.

## What the first PC test showed (Oct 1, HoverTest)

- 456 actors in and out, 0 warnings. The first exporter rewrote the 3 untouched brushes (float
  noise like `-10240.000153`, `Texture=Engine.DefaultTexture` added, `MainScale`/`PostScale`
  dropped). Fixed: untouched brushes now go back word for word, edited ones with rounded
  coordinates and no attributes they didn't have. `test/test_blender.py` checks the real map:
  exported unchanged, 0 lines differ.
- The rebuilt map was 70 KB instead of 705 KB, and loading it hung. No terrain was lost (the
  map has no TerrainInfo; its ground is 443 static meshes, all in the T3D). Most likely the
  difference is the baked lighting of those 443 meshes and the AI paths, which only
  `MAP REBUILD` was run for. **Done 2026-10-03:** with `LIGHT APPLY` and `PATHS DEFINE` the rebuilt map is 703,531 bytes (original 704,791) and plays; `PATHS BUILD` hangs (it also auto-adds path nodes, endlessly), see `test-results/2026-10-03-pc`.

## Not known yet (needs a test on the PC)

- Whether the full build above gives back a map that plays like the original. Things a T3D
  does not carry: resources stored inside the map's own package (`myLevel`: static meshes,
  textures made in the editor; HoverTest's come from packages, so it doesn't test this).
- Sheared brushes (MainScale/PostScale SheerRate): the sheer is ignored on import, with a warning.
- How umodel-exported static meshes are oriented (the importer assumes X forward, Z up).

## Baking lightmaps (global illumination) in Blender

`bake_lightmaps.py` bakes new lightmaps from what U2Shaders' `lmcapture=1` recorded in the game
(the real, built level: `System\U2Shaders\capture\`), lit by the map's own lights (`--t3d`,
through the importer above), with Cycles: direct and bounced light. Out come DDS files and the
`replace=` lines that make the game draw them instead of its own lightmaps.

```
blender -b -P bake_lightmaps.py -- --capture "C:\...\System\U2Shaders\capture" --t3d C:\work\MyMap.t3d --samples 128
    -> System\U2Shaders\baked\<hash>.dds + replace_lines.txt (paste into U2Shaders.ini)
```

Each bake is scaled so its average brightness equals the game's own lightmap (`--no-match` to
turn that off): the level keeps its exposure; where light falls and how it bounces is what
changes. Unreal's light brightness/radius to Blender watts is a rough guess, which the matching
mostly hides. Tested end to end on U2Shaders' test wall under Wine (capture, bake, swap); not
yet on a real Unreal II level.

## Test

`python test/test_blender.py [render.png]` with Blender's Python module (`pip install bpy`,
Python 3.11): imports `test/sample.t3d` (written by `test/make_sample.py`), checks it against the
file, exports it unchanged (same actors, same faces and texture alignment) and edited (moved,
turned, a new brush and light), and imports the edited file again.
`python test/test_bake.py`: bakes `test/capture_sample` (a capture from U2Shaders' Wine test)
with a test light and checks the DDS (size, mips, light falloff, matched brightness).
