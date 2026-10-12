<!-- branch of skill drawing-to-building (root: ~/.claude/skills/drawing-to-building/SKILL.md); paths are relative to the skill folder -->
## No-Hunyuan route: depth_carve.py (2026-10-11, CPU, seconds)
User asked to build from the views themselves instead of a Hunyuan base. Step 3 can be replaced by
`depth_carve.py part carve\<part>.glb carveiews_<part>.json n=96 name=<part>` (views: img, mask = colour\<part>_<view>.png, yaw): every view's silhouette carves a block (visual hull). Then steps 5-8 unchanged on carve\*.glb.
- Result housePlan1 (`house\carve\carve_turn2.png`, textured `carve\drawn_turn_carve.png`): cleaner, straighter walls and roof than Hunyuan; awnings come out as posts + roof.
- Depth on front/side elevations adds nothing (flat drawings). `depth_carve.py scene <in.glb> <out.glb> <views.json>` carves an assembled model with the angled sketch's Depth Anything map: v1 (tol 0.06) gouged grooves along pen lines; v2 (blur 9, tol 0.1, minblob 15) still dented the roof by the chimney. Don't use it; the angled sketch's depth is for measuring (step 4) only.
