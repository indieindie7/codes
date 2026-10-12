# Level map drawing -> 3D blockout + level analysis (page3, 2026-10-12)

Folder: `<work>/page3/`. Scans `IMG_20261012_0001.jpg` (top-down map: B houses, T trees, P path arrows,
A mansion on a hill, C round building, C1 camera arrows, edge labels A2/A3/B1-B3 = links to other sheets) and `_0002.jpg` (mansion front + graveyard).

1. `map_up.png` (map rotated upright) -> `map_grid.png` (1400 wide + 50 px grid). Hand-read every object into `layout.json`
   in grid px (0.1 m/px, y down = north/uphill): buildings `[cx,cy,w,h,angle]`, `round_C`, `mansion_A`, trees, path, cameras `[x,y,dx,dy]`, hill.
2. `cut_cards.py` (Hunyuan venv python `-I`): alpha cards for trees, C side view, mansion (gray < thr, close, keep big parts, fill inside).
3. `build_level.py` (Blender `-b --factory-startup -P build_level.py -- <folder>`): hill terrain, path strip, leaning boxes with pyramid roofs,
   C cylinder+dome, crossed tree cards, mansion card 16 m on the hilltop, dusk light, renders cam1-4 + top + overview, `level_blockout.blend`.
   Contact sheet `renders/sheet.jpg` is made afterwards with PIL (3x2 at 640x360).
4. `analyze_level.py` (`py -3.13 -I analyze_level.py <folder>`, needs pysovist 0.1.2 + shapely 2.2): path sampled every 2 m;
   landmark sight (2D, 9 points on the target) for A and C, a 3D check for A over worst-case 8 m roofs + hill, pysovist isovist area/r_max (60 m),
   release points (local area minimum then +50% within 10 m), clearance to buildings, winding ratio, angle to the landmark.
   Writes `analysis.json` + `analysis_overlay.png` (dots on the drawing: green sees A, blue A only over roofs, orange only C, red none; size = isovist area).

Results page3: path 117.8 m, winding 1.8; A seen 39% (first at 22 m, hidden 24-60 m and 74-88 m), C 80% (seen at start);
one release at 84 m, which is also the tightest squeeze (path 0.12 m from the big B under the mansion, 14 samples under 2 m).

Gotchas
- Camera tilt must follow the slope: aim at a point 25 m ahead, 2.5 m over the ground there (fixed in build_level.py).
- C1 arrows at the sheet edge (cam3, cam4) look off the drawn map toward the next sheet, so they render empty hillside. That is faithful, not a bug.
- pysovist `isovist(segments (n,2,2), origin, max_distance=...)`; `.metrics` keys are in `pysovist.METRIC_NAMES`. Unbounded without max_distance.
- Tools not taken: momepy (street networks), depthmapX (heavy C++), MarkovJunior/DeBroglie (need .NET, not installed), Rust `wfc` crate (generation, later).
