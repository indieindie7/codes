# Civil engineering rules for the Avalon island and town generator

Research pass, 2026-10-08 (the user: "also do some research into civil engineering to add to the model too"). Written by a research agent. Code read: `terrain_cutfill.py`, `layout_spine.py`, `systems.py`.

## Summary: top 10 by how engineered it looks, per effort

| # | Rule | Tool | Effort |
|---|---|---|---|
| 1 | **Batters, benches, retaining walls from height differences**: fill 1V:2H, cut 1V:1.5H in soil (1V:0.5H rock), a bench every 6–10 m of height, a wall wherever the batter would cross a plot or road | terrain_cutfill + clutter | M |
| 2 | **Fuel tank bunds**: hold max(110 % of the largest tank, 25 % of the total); the height follows from that | systems / props | S |
| 3 | **Culverts with headwalls where roads cross flow lines**, relief culverts by grade, lined chutes; never water over a fill slope | new drainage pass | S–M |
| 4 | **Haul-road cross-section**: 2 lanes ≈ 3.5× truck width, a safety berm on the drop side (≥ the tyre's rolling radius), a ditch on the cut side, cross-fall toward the high wall | terrain_cutfill roads + props | M |
| 5 | **Conveyor in straight runs** with a transfer tower at every bend, incline ≤ 15° (12° safe), a raised gallery where the ground is steeper, a stockpile + shiploader at the port | systems | S |
| 6 | **The berth at the 8–12 m depth contour**; on a shallow shore, a jetty out to it with mooring dolphins | layout_spine dock | S |
| 7 | **The water tank on the high point**, 20–30 m of head over the highest served building, on a stand if needed; the pump house at the intake | systems / layout_spine | S |
| 8 | **Grade caps per road class and real switchbacks**: haul 8 % target, 10 % sustained cap; streets ≤ 10 %; hairpins on flat landings, R ≥ 15 m | layout_spine path() + terrain_cutfill | M |
| 9 | **Tailings dam in a low valley downstream of the town; the waste dump by the mine** (flat-topped, benched, off the drainage lines) | layout_spine + island_form | M |
| 10 | **Cut/fill balance with visible spoil**: net cut → a spoil heap or dock reclamation; net fill → a borrow pit / quarry scar; heavy buildings on cut | terrain_cutfill | S |

**Next tier:**
- a breakwater on the windward side of the dock cove when the fetch is large;
- a sewage works at the low point, with the outfall downwind and down-current of the intake;
- catch drains above high cuts;
- a minimum curve radius per road class;
- turnarounds on dead ends;
- cliff set-backs.

**Scale warning.** One cell is 10.24 m. A 6 m batter at 1V:1.5H is 9 m wide, so all batters, benches, berms, ditches and walls are sub-cell. The heightmap only carries pad and road levels. The rest must be placed as meshes or decals along the computed rims.

## 0. What exists now

- **terrain_cutfill:**
  - **Pads:** a disc per building at the mean height. Discs merge when they overlap (MAX_TERRACE 64 m) and blend out over 8 m. The smoothstep peaks at ~1.5× the mean slope, so a 5 m step becomes about 1V:1.1H, steeper than soil stands.
  - **Roads:** a 7-sample moving average, clamped at 12 %.
  - **Dock cutting:** 9 m raised banks over 6 m laterally, about 1V:0.68H. Not stable as fill.
- **layout_spine.path():** 8-neighbour Dijkstra with a soft slope cost only. No grade cap, turn cost or road classes. The dock's "deep water" test is only 2 m. `plot_ok` allows 20° (36 %) everywhere.
- **systems:** utility trees along the roads, but no elevation logic: no tank head, no sewer fall, no conveyor incline check.

## 1. Earthworks and grading

**Findings.**
- **Balance and bulking:** engineers balance cut and fill (the mass-haul diagram). Volumes change with state: 1.0 m³ in the bank → 1.25 m³ loose → 0.90 m³ compacted. Rock swells. [FHWA earthwork](https://highways.fhwa.dot.gov/federal-lands/pddm/dpg/earthwork-design)
- **Batters:**
  - TDOT uses 2:1 (H:V) for fills and for cuts over 12 ft. [TDOT RD01-S-11](https://www.tdot.tn.gov/PublicDocuments/\DesignDivision\drawings\engr_library\design\StdDrwgEng\AEM\Current\RD01S11.pdf)
  - Cuts are "rarely steeper than 2:1 except in very competent rock".
  - Rock back slopes are much steeper. [TxDOT side slopes](https://www.txdot.gov/manuals/des/rdw/chapter-9--mobility-corridor-facilities--5r-/9-3-roadside-design-criteria/9-3-2-side-slopes.html)
- **Benches:**
  - A 5 ft bench per 10 ft of height on slopes over 20 ft. [Jackson Co. NC](https://www.jacksonnc.org/PDF/agenda/jan-07/item-2a.pdf)
  - Hong Kong berms about every 10 m of height (not verified).
  - Fill keyed into slopes in 0.6–2.4 m steps. [FHWA C204-50](https://highways.dot.gov/federal-lands/std-drawings/C204-50.pdf) · [NZ forest roads](https://docs.nzfoa.org.nz/live/nz-forest-road-engineering-manual-operators-guide/earthworks/cut-and-bench-fill-construction/)
- **Walls replace batters where there is no room:**
  - gravity walls about 1.5 m [FDOT](https://www.fdot.gov/docs/default-source/content-docs/roadway/ds/17/ids/IDS-06011.pdf);
  - crib 4–6 m [NPTEL](https://archive.nptel.ac.in/content/storage2/courses/105101083/Slides/Module%206/Lecture%2028/11.html);
  - gabions ≤ 3.7 m standard [KYTC](https://transportation.ky.gov/Highway-Design/Standard%20Drawings%20DGNS%202020/rgx050.pdf);
  - sheet piles at the waterfront.
- **Drains:** catch drains above cut crests, interceptors on benches, side drains at the toe. [MoRTH](https://morth.gov.in/sites/default/files/comprehensive_compendium_circular/304.3%20-%2026.7.76.pdf)

**Rules for terrain_cutfill.**
1. **Batter run from dh** (pad level − natural ground at the rim): fill 2.0·dh; cut 1.5·dh in soil, 0.5·dh in rock (natural slope > 30°).
2. **Benches:** a 2–3 m bench every 6 m of batter height.
3. **Walls:** if the batter would enter a plot, a road or the sea, build a wall instead.
   - h ≤ 1.5 m: masonry; ≤ 4 m: gabion; ≤ 6 m: crib; > 6 m: two tiers with a 2 m bench.
   - Emit `walls[]` for clutter to place.
4. **Blend:** `max(BLEND, k·|dh|·50)`, with k = 1.5 for cut and 2 for fill. Where there is a wall, a hard step plus the wall mesh.
5. **Pad level by balance:** bisect so cut·0.9 ≈ fill. Bias heavy buildings down to ≥ 60 % of the footprint in cut.
6. **Mass-haul report:** net cut becomes a spoil heap or dock reclamation; net fill comes from a borrow pit or quarry scar.
7. **The dock cutting:** a real engineer lowers the road into the hill, with the spoil going to the dock apron. Where it can't be cut, present the banks as a rock cutting (1V:0.5H with a bench) or wall them, and add catch drains on the crests.

## 2. Road geometry (Kaufman & Ault, *Design of Surface Mine Haulage Roads*, USBM IC 8758, read directly: https://stacks.cdc.gov/view/cdc/8915/cdc_8915_DS1.pdf)

**Grades:**
- Most states cap at 15 %. The optimum sustained grade is 7–9 %, and 10 % is the maximum safe sustained grade.
- Town streets: 7 % on level ground, 10 % on rolling terrain at 20 mph (AASHTO via [GT County](https://www.gtcounty.org/DocumentCenter/View/276/Appendix-A2-PDF)).

**Width:**
- 1 lane = 2× the vehicle width, 2 lanes = 3.5×; +1.2 m to pass a stalled truck.
- Virginia: ≥ 1.5×, or 3× where vehicles pass. [Va. Code](https://vacode.org/2025/45.2/II/C/9/7/45.2-923/)

**Safety berm:** ≥ the tyre's rolling radius (MSHA: mid-axle height). [MSHA](https://arlweb.msha.gov/training/surfhaul/slide37.htm)

**Cross-fall:** 2–4 %. Slope toward the high wall, one ditch.

**Alignment:**
- No sharp curves at crests or at the foot of long downgrades.
- Flat intersections, away from crests.

**Radius:** R = V²/(127(e+f)). At 30 km/h that is ≈ 32 m; a 15–20 km/h hairpin can be ≈ 15 m. [U. Idaho](https://www.webpages.uidaho.edu/niatt_labmanual/chapters/geometricdesign/professionalpractice/MinimumRadius.htm)

**Switchbacks:** built at the minimum turning radius, with the grade easing through the turn. Timber trucks need 13–15 m. [Czerniak & Trzciński](https://yadda.icm.edu.pl/baztech/element/bwmeta1.element.baztech-3d7044fd-d111-42f0-aad8-6af99410130b/c/czerniak_trzcinski_horizontal_2.1_2018.pdf)

| Class | Speed | Width | Grade target / sustained / short pitch | R_min |
|---|---|---|---|---|
| haul (dock → mill → mine) | 30 km/h | ≈ 10 m | 8 / 10 / 12 % | 35 m (15 m hairpins) |
| street | 30 km/h | 7 m | 8 / 10 / 12 % | 30 m |
| lane | 15–20 km/h | 4–5 m | 12 / 15 % | 12 m |
| footpath | — | — | > 15–20 % → steps | — |

**path() changes:**
- a hard grade cap per class;
- a turn cost;
- a switchback ladder for over-cap climbs (legs along the contour at the cap grade, landings ≥ 30 m at ≤ 4 %, legs ≥ 2 cells apart);
- an R_min check after Chaikin smoothing.

**Road cross-section:**
- 3 % cross-fall toward the cut;
- a V ditch on the cut side (~0.8 m);
- a berm on the fill side of haul roads where the drop is over ~3 m.

## 3. Drainage (IC 8758)

**Ditches:**
- in undisturbed ground, not through fill;
- interceptors at the toe of fills;
- lining by grade (none at 0–3 %, grass 3–5 %, rock or paved above).

**Culverts go:**
- at every ditch low point and every watercourse crossing;
- at intersections;
- before switchbacks on the upgrade;
- at every change from cut to fill.

**Relief culvert spacing:** ≤ 305 m at 0–3 %, 244 m at 3–6 %, 152 m at 6–9 %, 91 m at ≥ 10 %.

**Outlets:** never discharge over a fill outslope; headwalls at the inlets.

**New `drainage.py`** (after cut/fill):
1. D8 flow accumulation A on the edited map.
2. A culvert where a road crosses A ≥ 50 cells; a box culvert or bridge at A ≥ 500.
3. **Pits created by the cut/fill = dammed flow** → a culvert at the embankment's lowest crossing (the strongest automatic check).
4. Relief culverts by grade, with lined chutes.
5. Catch drains above cuts over 3 m with more than 20 cells upslope.
6. No pads on A ≥ 200 unless the channel is diverted; pads ≥ 1 m over the bed.
7. Every flow line ends at a visible shore outfall.

## 4. Ports and coastal works

- **Berth depth** = draught + low water + keel clearance. [Alaska DOT](https://Dot.alaska.gov/stwdmno/ports/assets/pdf/coastalengman/ch02.pdf) A coaster needs 7–8 m, a Handysize ≈ 11–12 m.
- **Breakwaters:** the entrance away from the dominant waves, ≥ ship length wide. [Transnav](https://transnav.eu/html,740.html) Armour on the seaward side at 1:1.5–1:2 (Hudson; [HR Wallingford SR150](https://eprints.hrwallingford.com/202/1/SR150.pdf)).
- **Slipways:** 1:8, toe ≥ 0.6 m below the lowest tide. [WA DoT](https://www.transport.wa.gov.au/mediaFiles/marine/MAC_P_RBFS_R22_GuidelinesDesignBoatLaunchingFac.pdf)

**Rules:**
1. Pick the dock by the distance to the D_berth contour, not the current 2 m test. If that contour is more than ~40 m out, build a **trestle jetty** with a berth head and dolphins, and run the ore conveyor along it to a shiploader.
2. A breakwater on the windward headland when the storm fetch is over ~1 km. Entrance facing the lee; 1V:1.5H seaward; crest 4–5 m with a crown wall.
3. The dock apron on reclaimed fill (the cutting's spoil), with a revetment at 1V:2H or a quay wall; piled buildings; heavy stockpiles on original ground.
4. A 1:8 slipway in the breakwater's lee.

## 5. Mining

- **Gravity mills** stand on hillsides: mine (high) → mill (the slope below) → port (low). [Hedley](https://livingsignificantly.ca/?p=1056)
- **Waste dumps:** off drainage lines, blending into hillsides. [WA DMP](https://dmp.wa.gov.au/Environment/ENV-MEB-223.pdf)
- **Tailings:** sited by downstream risk (GISTM). [Penman & Sanders](https://papers.acg.uwa.edu.au/p/2515_69_Penman/)
- **Conveyors:** ≤ 15° (12° safe; pellets roll back above 12°). Horizontal curves need radii of hundreds of metres, so plant belts run straight with transfer towers. [bulk-online](https://www.bulk-online.com/en/node/66799)

**Rules:**
1. z(mine) > z(mill) > z(stockpile). The mill on a 10–25° slope below the mine, on 3–4 stepped pads 6–8 m apart.
2. Conveyor runs straight, with a tower at each bend (≥ 10 m taller than the incoming belt) and incline ≤ 15° (target 12°). A raised gallery where the ground is steeper. Trestles every 60 m. It ends at a stockpile → jetty conveyor → shiploader.
3. A headframe over the shaft, the hoist house 30–60 m off in line with it, and 1–2 ventilation shafts on ridges.
4. A waste dump by the mine, off flow lines: flat top, 10 m lifts, 35–37° faces with 5–10 m berms, and an uphill diversion drain.
5. Tailings in a low valley downstream of the mill and away from town: a dam (≈ 1V:2.5H, verify) across a narrow throat with a spillway, draining to the sea, not through town.

## 6. Utilities

- **Water head:** 10–20 m internal (UK) to 24–30 m (South Africa, Bathurst NSW), so the tank base should be 20–30 m over the highest served building. [Bathurst](https://www.bathurst.nsw.gov.au/files/assets/public/v/1/council/plans-policies/brc-policy-manual/water-supply-minimum-pressure-standards-reviewed-oct-2023.pdf)
- **Sewers** by gravity at ≥ ~0.4 % ([9VAC25-790-320](https://law.lis.virginia.gov/admincode/title9/agency25/chapter790/section320/)), so treatment sits at the low point. Outfalls go far out, downwind and down-current of the intakes. [MWRA](https://www.mwra.com/media/file/deer-island-outfall-fqa1)
- **Power:** spans of 40–137 m; sag = wL²/(8H). [CPUC](https://ia.cpuc.ca.gov/Environment/info/dudek/LassenSub/documents/PEA_3.4.3.a-1-3.pdf)
- **Fuel bunds:** max(110 % largest, 25 % total). [Hydepark](https://hydepark-environmental.com/news/110-percent-bund-capacity-explained/)

**Rules:**
1. The tank on the highest cell within 300 m. Base ≥ highest served building + 8 m + 20 m, else a stand. A visible rising main from the pump house at the intake.
2. A sewage works at the lowest land cell, downwind of company housing, ≥ 150 m from the intake. ≥ 0.4 % fall. An outfall pipe past the breakwater, down-current. (The shanty downwind gets the smell: the parti.)
3. The generator near the fuel and seawater, its plume away from company housing. Street poles every 40–80 m; sag ≈ L²/(8H); substations.
4. Bund wall height = V / (bund floor − tank footprints), usually 1–1.5 m. Tanks ≥ 100 m from housing. A fuel line on sleepers from the berth.

## 7. Foundations and slopes

**Hillside codes** start at 10–15 %, tier at 30 %, and cap at 25 % ([Pleasanton](https://weblink.cityofpleasantonca.gov/WebLink/0/doc/69700/Page6.aspx)). No landslide areas.

**Rules:**
1. **Use by natural slope:**
   - ≤ 8.5° anything;
   - 8.5–14° terraced (housing, light industry);
   - 14–17° only masts, wellheads, stairs and the shanty (on stilts: nobody engineered it);
   - > 17° nothing.
2. **Set-backs** from cliffs/batters over 5 m: H/3 (≤ 12 m) from the crest and H/2 (≤ 5 m) from the toe (IBC §1808.7, not verified).
3. **Heavy buildings on cut** (≥ 60 % of the footprint).
4. **Shoreline buildings** on piles or the quay wall.

## 8. Settlement planning

- **Separation distances** (EPA Victoria Publication 1949, 2024) run to hundreds of metres. That doesn't fit a 1.3 km island, so use a **ranked order**: company housing farthest from and upwind of every heavy source (`dot(house − source, WIND) < 0`). The shanty may be downwind: the parti.
- **Emergency access** (IFC 503): fire roads 6.1 m wide; dead ends over 46 m need a turnaround (≥ 18 m diameter or a hammerhead); company housing has 2 disjoint routes to the dock or pad; first aid within ~400 m by road.
- The plume must not cross the command-room window unless that's wanted for the shot.

## 9. Automated engineering checks (`engcheck.py`)

- **E1** Road grade per class: no 50 m window over the sustained cap, no 100 m window over the short-pitch cap.
- **E2** Curve radius ≥ R_min, except marked hairpins.
- **E3** No sharp curves or intersections within 30 m of a crest.
- **E4** Every rim step has a batter or a wall; no soil slope steeper than 1V:1.5H without a wall.
- **E5** Walls ≤ 6 m per tier, with benches between tiers.
- **E6** |net cut − fill| ≤ 15 % of the volume moved, or a spoil heap / borrow pit absorbs it.
- **E7** No new pit without a culvert.
- **E8** Culverts at crossings with A ≥ A_c; relief-culvert spacing by grade.
- **E9** No pad on a flood path.
- **E10** Berth depth, or a jetty to it.
- **E11** Harbour shelter when the fetch is over 1 km.
- **E12** Conveyor: straight runs, towers at bends, ≤ 15°, z(mine) > z(mill) > z(stockpile).
- **E13** The tailings' downstream path stays ≥ 100 m from housing.
- **E14** Water head ≥ 20 m.
- **E15** Sewage at the low point with ≥ 0.4 % fall, the outfall downwind of the intake.
- **E16** Fuel bund volume; tanks ≥ 100 m from housing and not upwind of it.
- **E17** Slope use classes; crest set-backs.
- **E18** Heavy buildings on cut.
- **E19** Haul-road berms where the drop is over 3 m.
- **E20** Turnarounds on dead ends; 2 routes for company housing.
- **E21** Buffer order (company housing upwind and farthest).

## 10. Implementation order

1. terrain_cutfill: batters, walls[], balanced pads, heavy on cut, mass-haul, spoil/borrow, dock cutting fix.
2. drainage.py.
3. systems: bunds, tank head, conveyor runs and towers, poles and sag.
4. layout_spine: road classes + switchbacks, R_min, the berth contour + jetty, tailings, dump, mill, sewage sites.
5. port.py.
6. engcheck.py (E1–E21).

## Gaps

**Not verified in this session:**
- the Hong Kong berm interval;
- the CIRIA armour slopes;
- dump faces and lifts;
- the tailings dam slope;
- the IBC set-backs;
- CEMA's incline table.

**Also open:**
- The EPA Victoria tables weren't read, and the AASHTO Green Book is paywalled (its values come from summaries).
- A_c, A_flood and the game-scale distances are design choices to tune.
- IC 8758 dates from 1977, but it is still the source cited for haul roads.
