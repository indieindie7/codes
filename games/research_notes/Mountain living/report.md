# Mountain living: how people build on steep slopes (for the Avalon shanty generator)

Date 2026-10-08 (Avalon queue Q68: "research how people engineer living in mountains and ask creative team to remake this").
Web research only. Scale: 1 m = 50 UU. Related notes: "Civil engineering for the generator", "Organic settlement generation".

## 1. What real hill towns teach
- **Rio, Rocinha (favela).** No plan; houses grow upward. Owners keep adding floors on flat slab roofs ("laje"), so heights
  vary along one lane. Access is narrow alleys (becos) and stairs; only a few main streets carry vehicles. Character changes
  sharply within short distances. Roof water tanks and tangled cables everywhere.
- **Medellin (Comuna 13, Santo Domingo).** Metrocable (8-person cabins) and outdoor escalators added later as the spine.
  Every station and pylon base got a plaza, viewpoint, library or shops: the station is the neighbourhood centre.
- **Valparaiso.** About 30 funiculars ("ascensores", 1883-1932) climb from the flat port to a shelf ~80 m up; stairs
  everywhere else. Formal city on the flat, precarious housing on the hills. Top stations open onto a promenade with shops.
- **La Paz / El Alto (Mi Teleferico).** Lines pass right over houses at ravine edges. Yellow line: ~31 pylons over 3.6 km
  (one per ~115-120 m), up to 65 m tall. Landslides where water seeps into ravines (Nino Kollo collapse).
- **Santorini, Oia.** Cave houses ("yposkafa") dug into the cliff: two vaulted rooms one behind the other, a door and two
  small windows on the face. One house's roof is the terrace of the next one up. Every house had a cistern. Poor in the
  cliff, rich captains on the rim.
- **Amalfi / Positano.** Rows along the cliff with one hairpin road; everything else is stairs. Shops line the road; the
  church and piazza sit at the main junction.
- **Hong Kong ladder streets.** Stone-step streets straight up the slope (~350 m) that double as markets: stalls, repair
  shops and temples at landings and cross streets.
- **Jabal Haraz, Yemen.** Villages on ridge tops and spurs; outer houses form the town wall with 1-2 gates; terrace walls
  below several metres high.
- **Yuanyang Hani terraces.** Zones top to bottom: forest, village just below, terraces, river; water flows from the forest
  through the village into the terraces.

Sources: arxiv.org/pdf/2105.03235; dusp.mit.edu/projects/favelas-4d; leekuanyewworldcityprize.gov.sg (Medellin);
holcimfoundation.org (securing public space); en.wikipedia.org/wiki/Valpara%C3%ADso_funiculars;
revista180.udp.cl (621/977); en.wikipedia.org/wiki/Mi_Telef%C3%A9rico; remontees-mecaniques.net (linea amarilla);
eju.tv/?p=1613321; holeinthedonut.com (Oia cave architecture); en.wikipedia.org/wiki/Ladder_streets;
en.wikipedia.org/wiki/Jabal_Haraz; whc.unesco.org/en/list/1111

## 2. Engineering

### 2.1 How a house meets the ground, by slope
- 0-10 %: slab on the ground (plazas, depots, road heads).
- 10-20 %: step the house with the slope; low retaining walls 1-2 m.
- 20-35 %: cut a level bench and fill the low side, or a stepped foundation; back wall half-buried, downhill side on a
  1-3 m plinth.
- 35-70 %: piers/stilts on the downhill side; stacked houses.
- > 70 %: only cut-in rooms, anchored stilts, or nothing.
Cut-and-fill is cheap but slides if its wall fails; stilts avoid digging.
Sources: studiomatrx.org (sloping site design); blockrenovation.com (building on a slope)

### 2.2 Movement limits
- Roads: 8-12 % normal, 15 % max (impassable in rain/ice above). Switchbacks on steeper ground; hairpins flattened to <= 10 %.
- Ramps / handcart paths: 8.3 % (1:12) comfortable, ~12 % tolerable.
- Stairs: 30-37 deg typical, 17-21 cm steps; informal stairs 40-45 deg. A landing every 10-16 steps. Where the ground is
  steeper than the stair, it zig-zags.
- Consequence: on a steep cone nothing straight up the slope can be a road: stair, escalator, funicular or cable car.
Sources: frst557.sites.olt.ubc.ca (switchback notes); eng-tips.com (thread 172760); inspectapedia.com (stair angles)

### 2.3 Access
Two networks: contour lanes run level around the slope (houses face them, they carry traffic); stairs run straight down
the slope (foot only, shortcuts between lanes) and cut the rows into blocks. Commerce gathers where the two cross, on
landings, at stations and along the one road.

### 2.4 Water
Runoff causes the landslides. Gullies carry storm water: open, lined, small bridges, rubbish. Never built in. Roofs with
gutters and downpipes; open channels beside stairs. Roof tanks and cisterns; water piped down from the top.

### 2.5 Utilities
Pipes and cables along stairs and roads on poles, tangled at every crossing ("gatos" = illegal taps in Rio). Cable towers
on high points.

### 2.6 Social geography
Both patterns exist: rich on the rim (Oia) or poor higher up where access is worst (Valparaiso, Rio). A corporate colony
can use both: company buildings on the summit, the poorest shacks farthest in walking time from stations and the road.
Density follows access, not height.

## 3. Generator rules (metres; x50 for UU)
1. **Slope classes:** < 20 % normal; 20-35 % cut bench; 35-70 % stilts or stacked; > 70 % none (at most one cliff niche per 30 m).
2. **Orientation:** long axis parallel to the contour (+-15 deg); door/windows face downhill or onto the lane.
3. **Footprint:** 3-4 m deep x 4-8 m wide (deeper only on gentle ground); 1-3 floors, more near stations and in lower rows.
4. **Rows:** wavy contour rows one storey apart in height (3-4 m); horizontal spacing = 3.5 m / tan(slope) (~7 m at 27 deg).
5. **Row runs:** 4-10 houses (20-50 m), 0.8-1.5 m gaps or shared walls, then a stair.
6. **Stairs:** straight down the slope every 30-60 m (30 in the core, 60 at the edge); 1.2-2 m wide, 30-40 deg, zig-zag above
   40 deg; a landing every 2-3 m of height and at each row; each carries a drain and pipes.
7. **Retaining walls:** under every row, 1.5-4 m, drain holes and rust streaks; above 35 % use stilts instead.
8. **Stacking:** above 35 % the lower row's roof is the upper row's lane (0.5-1 m setback).
9. **Road:** one winding/spiral road, <= 12 % (15 % max), hairpins of 8-15 m radius on spurs. The straight spine is a stair
   or funicular, never a road.
10. **Gullies:** 2-4 drainage gullies down the slope, 4-8 m clear strip, lined channel, footbridges, rubbish; nothing built.
11. **Spurs and summit:** company buildings, watch post, generator, cable tower, water tank.
12. **Junctions:** every stair-lane crossing gets one of: stall, bar, shrine, tap, cable pole, rubbish pile; main crossings
    a 6-12 m plaza.
13. **Cable car:** 2-3 stations, each a plaza/market with the densest housing within 50-100 m; towers every 100-120 m on high
    points, 10-30 m tall, 5-8 m clear under the line.
14. **Density by walking distance** to a station or road head: < 50 m full rows of 2-3 storeys; 50-150 m rows with gaps,
    1-2 storeys; beyond, scattered shacks, poorer materials, more stilts.
15. **Vertical zones:** company/refinery and water tower on the summit, the densest band just below, thinner and more ragged
    lower down, cliffs empty.
16. **Water:** main pipe from the summit tank down each spine stair, branching along the lanes; roof tanks on 1 shack in 3;
    gutters on every roof.
17. **Chimneys and windows:** chimneys at the uphill end of roofs, smoke bending downwind; lit windows toward the main view,
    so a view from the road reads as stacked layers.
18. **Irregularity:** +-15 deg rotation, +-20 % size, 1 house in 5 out of line, materials/colours/heights change every 20-30 m.

## 4. Changes to the current Avalon shanty (after the Q51 pass)
Replace the 3 perfect rings (34/58/84 m) and clusters of 3 with many short wavy contour rows one storey apart. Add stairs
straight down the slope every 30-60 m. Turn the straight spine road into a stair carrying pipes and a drain, and the ring
roads into one winding road with hairpins on spurs. Carve 2-4 empty gullies. Put plazas at cable stations and at
road-stair junctions. Make density peak at the stations instead of spreading evenly per ring.
