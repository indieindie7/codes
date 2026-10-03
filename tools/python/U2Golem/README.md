# U2Golem: UT2004 characters into Unreal II

One command turns an ActorX character (`.psk` + textures, as UT2004's are) into an Unreal II
Golem mesh that walks, aims and dies with the marines' own animations.

```
py -3.13 u2import.py Malcolm --psk MercMaleD.psk --tex MercMaleDBodyA.tga --tex MercMaleDHeadA.tga
```

Result: `<game>\Meshes\Malcolm\Malcolm.gem`, compiled into `Meshes\GlmMalcolmG.ugx` and
`Textures\GlmMalcolmT.utx`. In game the mesh is `GlmMalcolmG.Malcolm`; test it with
`hub dummy GlmMalcolmG.Malcolm` (U2TestHub). To re-import, delete `Meshes\<Name>` first.

Needs Python 3.13 with `pywinauto` and `Pillow`. It drives Golem Studio with the real mouse for
about two minutes, on the leftmost monitor: don't touch the PC while it runs.

## Files

| file | what it does |
|---|---|
| `u2import.py` | the command: prepare, drive Golem Studio, `ucc make` |
| `prep.py` | scale, bone renames, weapon mounts, material names, plain TGA textures |
| `psk.py` | read/write ActorX `.psk` / `.psa` |
| `golem.py` | Golem Studio automation (tree menus, dialogs, materials, blueprint attributes) |

## Why each change is needed

- **Skeleton names.** Unreal II's biped is the same 3ds Max Character Studio rig as UT2004's,
  named `Merc ...` instead of `Bip01 ...`. After the rename, the blueprint's `Scripts` attribute
  points at `ArmorAnimsScripts` (Characters\Biped\ArmorAnims.gem), exactly like the marine
  blueprints, and the game's own animations drive the model. `--own-anims --psa x.psa` keeps
  the imported animations instead (they then need their own agent to play).
- **Scale.** Marine blueprints use `OriginScale 0.7027` and `OriginTranslateY -4`; their skeleton
  data is 1/0.7027 bigger than what you see. The mesh is scaled so it is 108 units tall in game
  (marine height, CollisionHeight 54) under that same OriginScale, so the shared animations fit.
- **Origin.** UT2004 meshes stand on their origin; Unreal II's are centred on the pawn.
- **Weapon.** Unreal II hangs the weapon on `handpointR02`; UT2004's `Bone_weapon` plays that role.
- **Textures.** Golem's PSK import names each material's texture `<prefix>0`, `<prefix>1`...;
  they are pointed at the real texture names, which `ucc make` imports from the folder.

## Gotchas found while building it

- `System\dxgi.dll` ("BGProxy", not part of the game) breaks Golem Studio's popup menus and the
  pilot's screenshots; it is renamed for the run and put back.
- Golem Studio's Render and Entity windows steal the foreground: they are closed first.
- pywinauto's tab-control and list-view readers crash this 32-bit program from 64-bit Python;
  tabs and list rows are clicked by position instead. Tree views and list boxes read fine.
- Saving asks "Are you sure you want to save ...?"; Windows dialogs here are in Portuguese.
- UnrealEd cannot show Golem meshes; check them in the game or in Golem Studio.

## The other way: Unreal II characters out to Blender

`gem.py` reads Unreal II's own Golem mesh files (`.gem`, "LGEM" v1; layout decoded from
`Meshes\Characters\Player\PlayerGame.gem`, Dalton). Two front ends:

```
blender -b --python gem2blend.py -- <in.gem> <out.blend> [texture dir]
py -3.13 gem2psk.py <in.gem> <out.psk>
```

- `gem2blend.py` builds a Blender scene: armature from the bone hierarchy, the mesh with its
  bone weights as vertex groups, UVs, one material per Golem slot with the matching `.tga`
  from the same folder (alpha off: Golem's alpha is a gloss mask). Converted to Z up.
- `gem2psk.py` writes an ActorX `.psk` (Z up, child bone rotations conjugated as ActorX
  expects), which can go straight back through `u2import.py` after editing.

What the format holds: a header of (count, offset) tables, an object table (0x40-byte records:
name, class, ..., data size, data offset), typed attributes (`VertexCount`, `WeightCount`...)
and a string table. The mesh objects:

| object | contents |
|---|---|
| `GemBoneHierarchy` | 88 bytes per bone: name, parent, local position, quaternion xyzw, scale |
| `GemBonePoints` | bone-name map; per point a model-space rest position + (weight count, first weight); (bone, weight) pairs; normals |
| `GemVertices` | render vertices: (point, normal, uv) indices |
| `GemTexUVFrames` | u, v floats |
| `GemTriangles` | 82-byte header, then (a, b, c, material) over render vertices; LOD data follows |

Verified on Dalton: 72 bones, 2401 points, 4330 render vertices, 4562 triangles, 3 materials
(Limbs, TORSO, Visor), posed in Blender with the weights following.
