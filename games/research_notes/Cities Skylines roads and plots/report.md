# Cities: Skylines roads and plots, and how to copy them for the Avalon generator

Research 2026-10-08 (Avalon queue Q73: "research how cities skylines does roads and plots"). Sources: the Paradox
wikis, Colossal Order feature pages, and the public source of CS1 mods (Zoning Adjuster, Network Extensions 2,
Network Anarchy, Intersection Marking Tool). Zoning Adjuster says it re-implements CO's zone-block code, so its
constants are the game's. No-leaked-source rule: repos holding decompiled CS2 game code were used for type/field
*names* only (one API listing), never their code.

## 1. Roads (CS1, then CS2)

**Data model.** A graph. A node has a position and flags; a segment joins two nodes with `m_startDirection` /
`m_endDirection`; its centreline is a **cubic Bezier** (P0/P3 = nodes, P1/P2 along the end directions,
`NetSegment.CalculateMiddlePoints`; straight = collinear controls). Long drags split into segments of <= 96 m by
default (Network Anarchy: 4..256). Per network type (`NetInfo`): half width 8..16 m (under 8 misbehaves), segment
(mesh tiling) length usually 64, max turn angle (above it a node mesh replaces a smooth bend), min corner offset
(> 40 breaks), **max slope 0.25** on every elevation variant (CSUR NetInfo templates), lanes (offset, width, vertical
offset, direction, type; lane props with repeat distance and probability). https://skylines.paradoxwikis.com/Road_Editor

**Segment mesh deformation.** Authors model a straight ~64 m stub along Z, sliced into a grid. At render time two 4x4
matrices per segment (`_LeftMatrix`, `_RightMatrix`) hold the control points of the left and right edge Beziers; the
vertex shader maps z -> t, x -> lerp between the edge curves, adds y. One mesh bends to any curve, no CPU work; UVs
scroll along V. (NodeMarkup NetworkRender.cs; Road_Editor wiki.)

**Nodes and intersections.** Each segment end gets left/right corners (`NetSegment.CalculateCorner`) pushed back from
the node by the corner offset, and further where neighbouring edges would cross. The segment mesh is drawn between its
end corners; a node mesh (another stretched stub) fills the polygon between all attached corner pairs. Flags pick the
variant (junction, end, type transition); "Flat Junctions" forces a level node.

**Elevation.** Five NetInfo variants per road: Basic, Elevated, Bridge (pillars), Slope (ramp), Tunnel. Elevation steps
1..12 m (default 3). Pillars at nodes; Bridge when the gap is too big for Elevated.

**Terrain conform (CS1).** Flags Flatten Terrain (slope blend skirt), Lower Terrain, Clip Terrain, Follow Terrain.
No retaining walls in CS1.

**CS2.** Curve modes (Straight, Simple, Complex, Continuous, Grid, Replace, Parallel), elevation steps 1.25/2.5/5/10 m,
negative elevation = cut road with **automatic retaining walls** (tunnel when deeper), slope readout, roundabouts,
snapping toggles (geometry, 8 m cell length, 90 deg, building sides, guidelines, zone grid).
https://www.paradoxinteractive.com/games/cities-skylines-ii/features/road-tools, https://cs2.paradoxwikis.com/Roads,
https://colossalorder.fi/?p=1547

## 2. Zoning and plots

**CS1 (exact, ZoningAdjuster CreateZoneBlocks.cs / CalcBlock1Patch.cs).**
- Cell 8x8 m; zoning reaches 4 cells (32 m) from the road edge. https://skylines.paradoxwikis.com/Zoning
- Each segment makes up to 4 blocks (start/end x left/right); a block = `rows` along the road (max 8 = 64 m) x 4 deep,
  stored as 8x8 bit masks (`m_valid`, `m_shared`, `m_occupied1/2`, 4-bit zone types).
- Straight: `rows = floor(len/8 + 0.1)`; over 8 -> start half `(rows+1)>>1`, end half `rows>>1`; centre = node + dir *
  offset + normal * (halfWidth + 32); halfWidth rounded (< 4 -> 4, 4..8 -> 8, else rounded); shift 4 m if halfWidth is
  not a multiple of 8.
- Curved: never bent; each side cut into two straight blocks (inner: chords at t ~0.04-0.5 and 0.5-0.96; outer: two
  tangents meeting at the midpoint), `floor(chord/8)` rows each -> the familiar wedge gaps.
- Cell invalid if terrain differs from the road side by > 8 m, outside the owned area, or any other segment's footprint
  overlaps it; then every cell **behind** an invalid one is invalidated (each survivor has a straight run to the road).
- Overlapping blocks: per cell one block wins (older build index / closer road), the loser's cells masked shared.
- Buildings: lots 1..4 wide x 1..4 deep, front on the road; the spawner needs a run of same-zone valid empty cells
  starting at column 0; no setback beyond the model (Zoning Adjuster adds 0..8 m); no corner models in CS1.

**CS2.** Same 8 m cells, up to 6 deep. Lot sizes (wiki v1.0): low density 2x2..4x6, row housing 1x2..1x6, medium/high/
mixed/office/industry 2x2..6x6. Vacant lots carry `CornerLeft`/`CornerRight`; cells know `Roadside`, `RoadLeft/Right/
Back`. Wide low-density areas split into several lots (6x6 -> two 3x6). Signature buildings are hand-placed landmarks
inside the zoned fabric. https://cs2.paradoxwikis.com/Zoning,
https://www.paradoxinteractive.com/games/cities-skylines-ii/features/zones-signature-buildings

## 3. Mods and docs
- Zoning Adjuster (MIT): https://github.com/algernon-A/ZoningAdjuster
- Network Extensions 2 (`IZoneBlocksCreator`, alley zoning): https://github.com/andreharv/NetworkExtensions
- Network Anarchy / Fine Road Tool: https://github.com/Quboid/NetworkAnarchy
- Move It (hand art direction over a procedural base): https://steamcommunity.com/sharedfiles/filedetails/?id=1619685021
- Node Controller / Adaptive Roads (`m_maxSlope = 0.25f`): https://github.com/kianzarrin/AdaptiveNetworks
- Intersection Marking Tool: https://github.com/MacSergey/NodeMarkup
- CO dev diaries: zoning https://forum.paradoxplaza.com/forum/developer-diary/cities-skylines-dev-diary-2-zoning.804803 ;
  road modding https://forum.paradoxplaza.com/forum/threads/cities-skylines-green-cities-dev-diary-8-road-modding.1050864 ;
  CS2 code modding https://www.paradoxinteractive.com/games/cities-skylines-ii/modding/dev-diary-3-code-modding

## 4. Recipe for the Avalon generator (Python -> ini of static meshes)

**4.0 Data model.** Copy CS: `Node(pos, kind)` + `Edge(a, b, ctrl1, ctrl2, type)` as a 3D cubic Bezier; derive every
mesh, plot and wall from the graph each run, never edit meshes directly. 1 m ~ 52.5 UU; the 8 m cell = 420 UU (or 512 UU
if the kit is power-of-two).

**4.1 Roads along splines (UE2 can't bend a mesh per instance).**
- (A) Short straight pieces + joints (default). Sample by arc length; one segment mesh per chord (yaw/pitch from the
  chord, DrawScale3D.X = chord / mesh length). Sagitta s = L^2/(8R), keep s <= 0.1 m -> L <= sqrt(0.8 R):
  R 15 m -> 3.5 m (13 deg/piece); 30 -> 4.9 (9.4 deg); 60 -> 6.9 (6.6 deg); 120 -> 9.8 (4.7 deg); >= 250 -> >= 14 (< 3.3 deg).
  Kit lengths 4/8/16 m, pick the longest that passes. Hide the outer-edge gap (~w*theta/2) with a joint/knuckle or pad
  piece wherever theta > 2 deg; sink the inner overlap 1-2 cm; change pitch only at joints, <= 3 deg each.
- (B) Track set: U2Model-baked arcs (R 16/32/64/128 m in 11.25/22.5/45 deg) and +-5/10 % ramps; fit roads as straights +
  arcs like model railway track; snap curves to kit radii. Best looking.
- (C) Bake per road: bend a gridded straight mesh along the real Bezier in Python with the CS shader maths, one static
  mesh per road. Perfect fit, more packages.
- Per road type ground / bridge (pillars every <= 24 m and at nodes when deck > 3 m up) / cut-tunnel, picked per piece from
  `deck_z - ground_z`.

**4.2 Plots (CS1 zone blocks, simplified).** Per edge and side: offset by halfWidth; straight -> `rows = floor(len/8 +
0.1)`, blocks of <= 8 rows; curved -> 2 chords per side (more over 60 deg), wedge gaps left for props/stairs/junk; depth 4
(town), 6 (factory yards), 2 (shanty). Invalid cells: road footprint + 1 m, |ground - road z| > 8 m (4 m on the shanty
cone, stilts instead), water, landmarks; invalidate everything behind; resolve overlaps per cell (older/wider road wins);
flag corner cells. Fill lots largest first (mix ~30 % 1x1, 30 % 2x2, 25 % 3x3, 15 % 4x4) from column 0, all cells valid
and free; building at the lot centre facing the road, setback 0 (shanty) / 2 m (houses) / 4-8 m (factories, yard in
front). Corner lots: corner models or face the higher-ranked road. Leftover cells: props. Landmarks first.

**4.3 Steep terrain.** Grades (rules of thumb, not CS - CS allows 25 %): main 8 %, streets 12 %, shanty lanes 18 % short
runs, beyond that stairs 30-35 deg with landings every 3 m of rise. Switchbacks: hairpin inner radius 8-12 m, flat (<= 4 %),
leg length = height gain / grade. On a cone: contour roads (spiral rings) joined by switchbacks and stair lines; plots cut
into the uphill side, stilts on the downhill side. Terrain: flatten under road + shoulder, blend a skirt (width = dh / 1.0
rock, / 0.5 soil); if the skirt > 6 m or cut/fill > 1.5 m use retaining walls (cut wall uphill, fill wall or stilts
downhill), wall pieces with the same L rule, height rounded up to a 2/4/8 m kit. Plots: < 1 m flatten, 1-4 m terrace,
4-8 m stilts (pillars every 4 m), > 8 m invalid.

**4.4 Intersections.** Merge nodes within 0.5*halfWidth; sort arms by angle; intersect neighbouring edge offset lines and
pull each arm back there plus a corner offset (8-16 m town, < 40); fill the node with a T/Y/X/end/transition junction mesh
or a flat pad scaled to the corner polygon + quarter-circle kerbs; keep junctions flat (node z = mean of the arms, each
arm reaches its grade within its first piece); reject arms meeting under 30 deg; on the cone keep junctions on <= 6 %.

**Defaults:** cell 8 m (420 UU); depth 4/6/2; block <= 8 cells; lots 1x1..4x4 (industry to 6x6); straight pieces 4/8/16 m;
sagitta 0.1 m; grades 8/12/18 %; walls when cut/fill > 1.5 m; stilts when the drop > 4 m; cell invalid over 8 m; corner
offset 8-16 m; elevation step 1.25-3 m.

## Caveats
CS1 zoning numbers are exact (Zoning Adjuster's MIT source). CS2 lot details are thinner (wiki + an API name listing).
The grade and wall/stilt thresholds are real-world rules of thumb, not CS. The Move It link was not opened.
