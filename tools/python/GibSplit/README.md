# GibSplit: skinned characters into gib pieces

Cuts a skinned mesh (ActorX `.psk`) into one static mesh per body part, closes every cut with a
flat "meat" cap, and writes a manifest. Made for AdventMod's gore (Advent Rising characters
exported by `games/advent_rising_mods/tools/ukx_mesh.py`), works on any `.psk` with a biped-ish
skeleton.

```
py -3.13 gibsplit.py <mesh.psk> <out dir> [--space zup|mesh] [--meat NAME]
py -3.13 preview.py <out dir> <picture.png>      # exploded view, caps in red
```

- **Parts:** each point goes to its strongest bone, then up the skeleton to the first bone
  named like a part root: `head`, `*ForeArm` (lower arm), `*Arm` (upper arm), `*UpLeg`/`*Thigh`,
  `*Leg`/`*Calf`, the Seeker's `*FrontShoulder/Arm` and `*FrontElbow/Wrist`, and
  spine2/3, neck, shoulders (chest). Everything else is the pelvis chunk. Edit `RULES` for
  other rigs.
- **Caps:** the edges where two parts meet (welded across UV seams) are chained into loops and
  fanned to their centre on an extra material slot (`meat`, the last *SUBMATERIAL), with a
  planar UV.
- **Output:** `<mesh>_<part>.ase` with a Multi/Sub-Object material: the character's own slots
  (UVs unchanged, so the skin texture fits) plus `meat`. Each part is centred on its own pivot;
  `--space zup` (default) turns Y-down meshes Z up. `<mesh>_gibs.json` lists part, file,
  spawn bone, pivot (in the original mesh space), size, faces, caps and a mass guess.
- **Mass guess:** closed volume x a density calibrated so Advent's marine totals ~90 kg.
  Meaningless for non-characters (ships, props) or meshes at another scale.
