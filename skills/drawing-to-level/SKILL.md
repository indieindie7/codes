---
name: drawing-to-level
description: Turn the user's top-down level map drawing (houses, trees, path arrows, landmark, camera arrows) into a 3D Blender blockout rendered from the drawn cameras, then score it as a level - landmark visibility along the path, first reveal, squeeze/release (isovists via pysovist), clearance, winding, leading lines - with an overlay drawn on the user's own sketch. Also scores any generated layout (Avalon towns) given in the same layout.json format. Use for "make my level map 3D", "analyse this level", "is the landmark visible", sightline/isovist checks.
---

# Drawing -> 3D level + level analysis (built 2026-10-12, page3; the user: "that is perfect")

First run: `<work>/page3/` (scans `IMG_20261012_0001.jpg` map, `_0002.jpg` mansion front).
Scripts (copies of the page3 ones) are in `scripts/` here. Run them from the level's own folder.

## 1. Read the map into layout.json (by hand, ~15 min)
- Rotate the scan upright -> `map_up.png`; thumbnail to 1400 wide with a 50 px grid -> `map_grid.png`.
- Read every object off the grid into `layout.json` (grid px; `scale_m_per_px` 0.1 for page3; y down = north/uphill):
  ```
  buildings [[cx,cy,w,h,angle_deg_clockwise], ...]   round_C [cx,cy,r]   mansion_A [cx,cy,w,h,angle]
  trees [[x,y],...]   path [[x,y],...] (in walking order)   cameras [[x,y,dx,dy],...] (drawn C1 arrows)
  hill {top:[x,y], height_m, radius_px}   edge_labels {A2:[x,y],...}   map_box [x0,y0,x1,y1]
  ```
- Edge labels (A2, B3...) are links to neighbouring sheets; keep them.

## 2. Cards from the drawings
`scripts/cut_cards.py` (Hunyuan venv python `-I`): alpha card per drawn tree / side view / landmark front. Mask = gray < thr (110; 120 for the mansion),
MORPH_CLOSE grow 9 (15), keep parts > 0.2% of the area, flood-fill the inside so the pencil inside stays. Crops are in layout.json `cuts_preview_px`.

## 3. Blockout
`"/c/Program Files/Blender Foundation/"*/blender.exe -b --factory-startup -P build_level.py -- <folder>` (~6 s, CPU/EEVEE):
hill = `H*max(0,1-d/R)^2`, path strip, leaning boxes 5-8 m + pyramid roofs, C cylinder + dome, crossed tree cards,
landmark card 16 m tall, dusk sun. Renders `renders/cam1..n` (drawn cameras, 1.7 m eye), `top` (ortho), `overview`; saves `level_blockout.blend`.
Contact sheet: PIL, 3x2 at 640x360 -> `renders/sheet.jpg`.

## 4. Analysis
`py -3.13 -I analyze_level.py <folder>` (pysovist 0.1.2 MIT + shapely 2.2, installed for py 3.13) -> `analysis.json` + `analysis_overlay.png`.
Path sampled every 2 m. Per sample: landmark seen (2D, free line to any of 9 points on it), A seen in 3D (eye 1.7 m, worst-case 8 m roofs, the hill),
isovist area / r_max (exact 2D, `max_distance` 60 m), clearance to the nearest building, angle between path heading and the landmark.
Report: visible %, first seen, hidden stretches, % seen within 45 deg ahead (leading lines), release points (area local minimum then +50% within 10 m),
min clearance, winding ratio (length / straight line).
Overlay on the drawing: green = A seen, blue = A only over roofs, orange = only C, red = none; dot size = isovist area.

### Heuristics it encodes (from the research, 10-12)
1. Landmark ("weenie") visible from the start and from a good share of the path. 2. Tease then reveal: a glimpse, a hidden stretch, a full reveal.
3. Compression then release: a narrow spot right before a wide view. 4. Leading lines: path heading within 45 deg of the landmark.
5. Clearance >= player width + margin (~2 m here). 6. Winding ratio 1.3-2 for a small town. Not yet coded: POI spacing 30-60 m, dead ends need a reward,
chokepoints/loops via networkx betweenness.

## Page3 result (reference numbers)
Path 117.8 m, winding 1.8. A seen 39%, first at 22 m, hidden 24-60 and 74-88 m, then in view up the hill (good tease/reveal).
C seen 80%, from the start (guides the first half). One release at 84 m = also the tightest squeeze (0.12 m to the big house under the mansion): widen there.

## Gotchas
- Camera pitch must follow the slope: aim 25 m ahead at the ground there + 2.5 m. A flat 84 deg tilt shows only hillside.
- Drawn camera arrows at the sheet edge can point off the map (page3 cam3, cam4): empty hillside there is faithful.
- pysovist: `isovist(segments (n,2,2), origin, max_distance=...)`, metrics in `.metrics` (names in `pysovist.METRIC_NAMES`); without max_distance an open view is unbounded (inf area).
- The 2D check under-counts tall landmarks and the 3D check uses one target point; read both.
- Other tools looked at: momepy (street networks), depthmapX (heavy C++), MarkovJunior / DeBroglie (generation, need .NET, not installed), Rust `wfc` crate.

## Using it on generated layouts (Avalon)
Write the generated town into the same layout.json shape (buildings as rectangles, the landmark as `mansion_A`, the spine as `path`), run step 4,
and use visible %, first-seen distance, release count and min clearance as extra scores next to the generator's own.

Related: `drawing-to-building` (single buildings; its tree/04-level-map.md is the first write-up), `goobi-scan-cutout`, `sketch-concept-art`, `avalon-town-generator`.

## Reference: Drelvak's first-person Diablo Tristram (youtu.be/dhzCSubTDl8, 10-12)
Same idea from the other end: DevilutionX reads Diablo's tiles + collision grid and builds the 3D in code, so the original collision stays the truth.
Takeaways for this skill: (1) the layout/collision is the source, geometry follows it; (2) blocked cells with nothing drawn get boulders/trees so the block reads in 3D;
(3) check every view against the top/iso view (his rocks were re-tessellated until the horizon read sharp); (4) a live key toggle between top/iso and first person, facing kept in sync,
is the best review tool; (5) first person in crowded areas needs a side/behind enemy marker.
