# From a ref sheet to a building in Unreal II: the pipeline on paper

Draft, 2026-10-05. Goal: turn the Liandri ref sheets (`Documents\design-refs\avalon_concepts\liandri\
refsheets`, 10 buildings x 2 variants, each a 3-view sheet on grey) into low-res meshes that stand on
TutA's shore, so that in-game shots of the real place can be painted over again, and so that the place
can eventually be walked through. Every step below already has a working tool from the character
pipeline (`tools/python/U2Golem/CHARACTER_PIPELINE.md`) or from U2AvalonCards.

## The chain

```
ref sheet (3 views)            Sana, done
  -> one clean view            crop the front or 3/4 view, rembg           prep: PIL + hy3dgen rembg
  -> high-poly mesh            Hunyuan3D img2shape (octree 384, ~2.5 min)  tools/python/U2Golem/img2shape.py
  -> painted mesh              Hunyuan3D paint_mesh from the same view     paint_mesh.py (~3 min, 40k faces)
  -> low-poly + bake           Blender Decimate to a budget, bake colour   flatten_bake.py (lowpoly-tool-choice: "A")
  -> game mesh                 .ase/.psk export, UnrealEd import           u2import.py / U2EdBridge, or .usx via ucc
  -> placed                    Props[] line in the layout                  make_props.py
  -> checked                   pilot run + window shots                    scripts/cards_harbour.txt
```

GPU cost per building: ~6 min (shape + paint). 20 buildings = ~2 h of GPU, so it runs as one announced
batch when the user is not playing, overnight-style, the way the cards batch did.

## Step notes

1. **View choice.** Hunyuan wants a single object on a plain background. Take the 3/4 view (right-hand
   figure on most sheets) cropped tight; where a sheet shows a scene (cargo dropship #2: ship + pad +
   containers) crop only the object. Multi-view input (front + side) is supported by Hunyuan3D-2mv and
   would give truer backs, but the installed pipeline is single-view; the back of a building is rarely
   seen from the tower, so single view is fine for the first pass.

2. **Shape.** `img2shape.py <cut.png> <name>_high.glb full octree=384 faces=0`. Known behaviour: thin
   parts (pylon arms, crane cables, mast antennas) may fuse or vanish; the cooling tower, tanks, silos,
   halls and rigs are solid shapes and come out well (the oil rig card already did).

3. **Paint.** `paint_mesh.py <high.glb> <paint.glb> <cut.png> faces=40000`. Colour comes from the
   sheet, so the grey/orange language carries over for free. Lighting baked into the sheet is flat
   studio light, which is what we want (no sun direction to fight the level's).

4. **Low-poly.** Blender Decimate (Collapse) of the painted mesh to a budget, with the colour baked to
   one texture: 1,500-3,000 tris for the big silhouettes seen from the tower (towers, halls, tanks),
   3,000-6,000 for the rig and crane that are also seen from the shore. Keep the hero pieces (dropship)
   higher. This is choice "A" from the low-poly decision (Decimate of the fine Hunyuan mesh + bake), not
   MeshAnything.

5. **Into the game.** Two routes:
   - **Static mesh package (preferred for buildings):** export .ase from Blender, import in UnrealEd
     through the U2EdBridge (`STATICMESH IMPORT`... the editor's own command vocabulary is in
     `Documents\U2_research\ghidra\editor_exec_tokens.txt`), save `U2AvalonM.usx`. Then the mesh is a
     normal `Package.Group.Name` for Props[].
   - **Golem/.psk** (the character route) works too but is for skinned things; not needed here.
   Texture: one 1024 DXT1 per building, imported with the mesh.

6. **Placement.** One Props[] line per building; `make_props.py` reads the mesh bounds from the .usx
   with `mesh_bounds.py`, so the new package goes through the same bounds step. Scale to the brief's
   sizes (cooling tower ~2,500 units tall; halls ~900; tanks ~800; rig deck ~2,600 wide).

7. **Check.** `cards_harbour.txt` pilot run for the window, air and shore views; then the paint-over
   round on top of the real meshes (the mesh blockout gave Kontext more than cubes did).

## What this gives and what it doesn't

- Gives: real 3D buildings in the game's own look, consistent with the concept frames, placeable by a
  text file, at ~2k tris each, in an evening of GPU.
- Doesn't: interiors, doors that open, collision tuned for walking (Props are no-collision scenery;
  turn collision on per building when the player can reach it), night lights (needs emissive
  textures: a second pass).

## Order of work

1. Cut the 20 views (CPU, now). 2. Batch shape + paint (GPU, announced). 3. Decimate + bake (CPU).
4. Import to a .usx (editor session, announced). 5. Layout + shots. 6. Paint-over round 3.
