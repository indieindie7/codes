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
python u2ed.py exec PATHS BUILD
python u2ed.py exec MAP SAVE FILE="..\Maps\MyMap_edit.un2"
python u2ed.py stop
```

Always save under a new name: the original map stays as it was.

## Not known yet (needs a test on the PC)

- Whether Unreal II's `MAP EXPORT` / `MAP IMPORT` round-trip a whole map. **First test:**
  export a map, import that T3D unchanged, rebuild, and play it. Things a T3D does not carry:
  resources stored inside the map's own package (`myLevel`: static meshes, textures made in the
  editor); terrain height maps (separate textures). Lighting and AI paths are rebuilt anyway.
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
