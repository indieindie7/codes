---
name: drawing-to-building
description: The user's own drawings of a building/object (front, side, top, angled views on paper) -> coloured views -> Hunyuan3D parts -> sizes from a depth pass on the angled sketch -> assembled model -> the drawings projected back on as the texture. Use when the user sends a new set of building/object views to turn into 3D (housePlan1 was the first, 2026-10-11). Also a top-down level map drawing -> 3D blockout + level-design analysis (page3).
---

<!-- skilltree -->
> Skill tree: this file is the overview. Each `->` line points to the full section in `tree/`; Read only the branch the task needs.
# Drawing -> building (built 2026-10-11, housePlan1)

User (10-11): "what i will be doing is drawing top, side, angled and front views of the building/object" and "some top views of objects are just for showing like wall plans" -> a top view is only painted when it shows the real roof/top; wall-plan tops are layout only (`"use": "plan"`).

All tools in `<Hunyuan3D-2 folder>` (venv python; Blender 5.2 `blender -b --factory-startup -P <script> -- ...`). Example data: `Documents\U2Golem\scenefit\house\` (crop_*, colour\, out2\, depth\, tex\).

## Steps
-> `tree/01-steps.md` (~560t): 1. Page -> crops. PDF: pdf2png.ps1 -pdf <f> -outDir <d>. Crop each part's views (front/side/top/angled) by hand into crop_<part>_<view>.png;...

## No-Hunyuan route: depth_carve.py (2026-10-11, CPU, seconds)
-> `tree/02-no-hunyuan-route.md` (~260t): User asked to build from the views themselves instead of a Hunyuan base. Step 3 can be replaced by

## Porches + shed (2026-10-12, CPU, seconds)
User: "yes rebuild the house with the porches and shed". `porch_shed.py -- <in.glb> <out.glb> depth\measure.json [depth_x=2.0]` (Blender) deletes objects named *awning*, builds porches (sloped roof 2.23 m at the wall falling 0.35 m, posts to the ground; depth = awning_depth x depth_x = 0.98 m on housePlan1) on the gable (-Y) and long (+X) walls, and adds object "shed" (1x1 m, 2.0/1.75 m mono-pitch) on the -X side. housePlan1: `carve\house_porch_shed.glb`, `carve\porch_shed_turn.png` (from carve\house_carved_drawn.glb).

## project_drawings.py
views.json entries: img, objects ("all" or names), yaw (0 front -Y, 90 right +X, 180 back, 270 left), pitch (90 = top), weight, mirror (also paint the opposite face, flipped), use ("paint"|"plan"). Each view is orthographic; the objects' projected bbox is stretched onto the drawing's ink bbox; z-buffer hides covered texels; best view per texel wins (averaging doubled the lines). Ink = pixels darker than ink=140, the rest becomes paper colour, so ruled lines drop out. Smart UV island_margin must be tiny (0.0005): Hunyuan's 20k faces with 0.01 left 2% of the texture used. keep=W reuses UVs + texture already on the mesh.

## Results / gotchas
-> `tree/03-results-gotchas.md` (~1160t): housePlan1: depth\measured_turn.png (user: "much better"), tex\drawn_turn2.png (row 1 elevations only, row 2 + angled sketch with windows).

## Level map -> blockout + analysis (page3, 2026-10-12)
Now its own skill `drawing-to-level` (scripts there). First write-up: `tree/04-level-map.md`: top-down map drawing -> layout.json -> build_level.py (Blender) -> analyze_level.py (pysovist sightlines, landmark visibility, squeeze/release, overlay on the drawing).

## Direction (user, 2026-10-12)
- Background scenery = the drawings themselves as impostor cards (billboards; several drawn angles swapped by view angle when needed), not meshes. Splats are OK for backgrounds too (TRELLIS offered, not installed).
- Meshes only for things that animate: those get redrawn by hand many times, and the growing set of views (turnarounds) is the input that makes mesh generation better. Keep every redraw of an asset together so the views pile up.
