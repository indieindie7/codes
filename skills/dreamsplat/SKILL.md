---
name: dreamsplat
description: The user's KEPT pipeline (2026-10-12) for turning their paper drawings into Dreams-style painted splat models, plus the reference sheet (rows = objects, columns = view angles) they paint over to polish the splats. Use for any "dreamsplat", "splat my drawing", "ref sheet" or "polish the splat" request.
---

# Dreamsplat: drawing -> painted brush-stroke model -> ref sheet -> polish

User 2026-10-12: "i feel like right now we have a very good pipeline, we will keep this one", and "this is exaclty what i wanted so far". The sheet idea is the user's own: "an excel ref sheet with row the name of object. and column the angle it shows. so i can like pass another one to better polish the dreamsplat model."

Work dir example: `<your work folder>/` (all paths below are relative to it). The scripts are CPU only, and they are not true 3DGS: each stroke is a painted ellipse, lit by one light and drawn far to near.
- P = `$HUNYUAN_PY`
- K = `$KONTEXT_PY $KONTEXT_DIR/kontext_edit.py` (GPU).

## 1. Drawing -> mesh (GPU, see skill drawing-to-building for the details)
- Cut each view from the page.
- Pick a route:
  - Hand shapes -> flat colour -> Hunyuan multi-view gives a clean blockout.
  - Kontext repaint -> Hunyuan gives surface detail.
- Best of both, the SDF shell blend: `$P sdf/shell.py <base.glb> <detail.glb> <out_prefix> 0.04` keeps the base silhouette and adds the detail within 4 cm. t040 was picked by the user; CPU ~11 min.

## 2. Paint the views (GPU, ~3 min per object)
1. `py -3.13 sdf/pair.py join <front.png> <side.png> pair_in.png` puts the two views on one canvas.
2. `$K pair_in.png pair.png "<prompt>" --steps 24 --guidance 4 --long 1024` paints them. Run one Kontext at a time.
3. `py -3.13 sdf/pair.py split pair.png <m>_front.png <m>_right.png` cuts them apart again.

Painting both views on one canvas keeps the side matching the front. The prompts are in `sdf/paint_sides.sh`. Gotchas:
- Give each object its OWN palette; one shared "warm colours" prompt made every building yellow and red.
- Kontext can change a thin shape (the booth became a gothic house), so check the outline.
- A run that stalls for more than 2 min on one step should be killed.

## 3. Splat
`$P sdf/splat.py <mesh.glb> <front.png> <right.png> <out.png> [views=8] [size=360]` takes ~1 min and draws two rows:
- tight: 45k strokes, which keeps the windows;
- loose: 9k strokes, sketchier.

Stroke colour comes from the front image for ±Z normals and the side image for ±X normals. Where one view's outline misses the mesh (paper colour), it falls back to the other view. The user liked the front view most: "the front is real good too".

## 4. Reference sheet + polish loop (`sdf/dreamsplat.py`)
- `sdf/objects.json` lists the objects: `[{"name","mesh","front","right", "colors": optional .npy}]`.
- `$P sdf/dreamsplat.py sheet sdf/objects.json sdf/ref1 [size=360] [angles=0,45,...,315]` writes:
  - `ref1_sheet.png`: one row per object (name on the left), one column per angle (degrees on top), using the same strokes as splat.py's tight row;
  - `ref1_layout.json`: the cell size, angles and row order, which polish needs.
  - Time: 5 objects × 8 angles ≈ 5 min.
- The user paints over the sheet in any paint program and at any size (it is rescaled back).
- `$P sdf/dreamsplat.py polish sdf/objects.json <painted.png> sdf/ref1_layout.json sdf/ref2` recolours the strokes:
  - Each stroke takes its colour from the column that faces it most squarely AND sees it (4 px depth test), with that view's shading divided out.
  - Only pixels that differ from the sheet as sent count (`layout.json` "sheet" names it), so untouched views never override a repaint. The first version picked the best-facing view outright, and an unpainted 0° cell overwrote a 45° repaint (fixed 10-12).
  - It writes `ref2_<name>.npy` plus a new `ref2_sheet.png`. Put the .npy path in "colors" in objects.json to keep going round the loop.
- First sheet: `sdf/ref1_sheet.png` (kA, candy, tower, spire, booth). kA's colour still comes from the raw `geo/kA_input_*` views until its Kontext side paint runs.

## Related
- Skills: drawing-to-building (mesh routes, house), local-gpu-ai.
- Real 3DGS (.ply) is possible later: TRELLIS writes it, or a 3DGS trainer on the sheet's views. Nothing online turns a drawing into splats directly (searched 10-12).


## Imposter frames for the Goobi brawler (10-12)
`$P sdf/dreamsplat.py sheet sdf/objects.json sdf/imp 480 300,310,...,350,0,10,...,60` (CPU ~10 min) -> sdf/imp_sheet.png + imp_layout.json; then `$P sdf/slice_imp.py sdf/imp_layout.json C:/goobi/brawler/assets/art/imposter` cuts transparent `<name>_00..12.png` (one crop box per object).

