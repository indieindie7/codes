# How others build towns: artists, level designers, city games, real settlements

Collected 2026-10-06 after the user's note that our generated towns "still look like a cluster of random
buildings": before tuning more rules, look at how people who are good at this actually do it. Four
research passes (subagents, web sources at the end of each section); each rule ends with how our pipeline
(binder -> interest-map layout -> provides/needs systems -> pads/roads -> actors) would apply it. The
synthesis, "what changes for us", is at the end.

## 1. Real remote industrial settlements

Cases: Hashima, Pyramiden, Longyearbyen, Kiruna, Norilsk, Fordlandia, Sullom Voe, Sakhalin-II,
Alaskan canneries (Funter Bay, Kake), Antarctic stations, Australian FIFO camps, US company towns.

- **The shore is the machine, not the town.** The wharf is the origin: office, radio room, store and bath
  within 50 m of it; the biggest shed stands over the water on piles; fuel tanks just upslope behind the
  power house; terminals put the tank farm on a cut bench 100-300 m inland with long straight jetties to
  deep water. -> Dock first; office/store within 50 m; main hall on the waterline; tank farm on its own
  bench behind the power house; the long jetty is the silhouette.
- **Resource comes down, people live beside, product goes out by one line.** Mines above the town, ore
  down a straight cableway or incline whose towers march over roofs and terrain (Longyearbyen: 74
  towers and a hub on pillars). -> Wellheads uphill, one straight conveyor to the silos/dock with towers
  every 40-80 m, a hub where lines meet. The line is the dominant structure, not a detail.
- **One spine, then class terraces.** One main street carries the civic buildings with a monument at its
  head; housing sorts by rank and view: managers on the knoll overlooking the works out of the dust,
  bunkhouses between spine and plant, the oldest best-sited block is the fenced company core. -> Spine
  road dock -> mine; dorms between spine and plant; director's house on the highest terrace with a
  sightline to the works; a fenced core cluster as the oldest ring.
- **Terrain is terraced; wind and permafrost shape the forms.** Bent streets against wind, closed blocks
  as wind walls, snow fences along roads, everything on piles, heat and water pipes above ground in
  bundles beside the roads bridging over them (Longyearbyen's signature), long buildings aligned to the
  storm wind, fuel and generators 100 m+ downwind of housing. -> Terraces with retaining walls along
  contours; a pipe rack along every road with hoops at crossings; rows aligned to a wind vector; snow
  fences at the windward edge; fuel cluster downwind.
- **Density extremes.** Hashima: 5,259 people on 6.3 ha in 7-10 storey slabs linked by courtyards and
  bridges inside a seawall; FIFO camps: identical modules joined by covered walkways round a mess. ->
  Two housing archetypes: stacked slabs with stair towers and bridges, or a module grid with walkways.
- **Clutter inventory (observed).** Boardwalks, a water tank upslope of the bunkhouses, a dammed creek
  with a pipe, privies over the tide line, Quonset huts, a steel water tower with the work whistle,
  greenhouses off the power house, cemetery at the valley head, pipe bundles, cableway towers, snow
  shields, piles under every slab, an airstrip on the one flat, separate coal and cargo quays, dead
  vehicles and rust.
- **How half-abandonment reads.** Wooden and light buildings rot first; concrete and steel towers remain;
  patched collapses, vegetation amid ruins, leaking pipes with stains, squatters in the managers'
  houses; a cleared site leaves roads, slabs, retaining walls and the tank bund. -> Decay pass by
  material.

Sources: Wikipedia (Hashima Island, Pyramiden, Longyearbyen, Kiruna, Fordlândia, Sullom Voe Terminal,
Company town, Goldsworthy WA, Kake Cannery); nippon.com; Norwegian Polar Institute cruise handbook; RCI
Eye on the Arctic (Pyramiden; Norilsk); hurtigrutensvalbard.com; arkitekturguide.uit.no; kiruna.se;
gw2ru.com (Norilsk); messynessychic.com (Fordlandia); scottish-places.info; sakhalinenergy.ru;
offshore-technology.com; nps.gov (Funter Bay); antarctica.gov.au; Cambridge Polar Record (McMurdo);
spacearchitect.org (Halley VI); sciencepoles.org; mining-technology.com (FIFO); CBC (Conrad).

## 2. How concept artists compose settlements

- **Three-tier focus, each with a job**: primary landmark, a secondary counter-mass offset from it,
  a tertiary foreground accent that points back; everything else is filler simplified below both
  (Goeltner's "The Village"). -> One landmark (tallest, most ornate), one counter-mass, one accent; a
  detail budget per building that falls with rank.
- **Spend detail where the eye goes; starve the rest** (Laney's village: the church got the time, the
  houses stayed modest so the contrast guides the eye). -> Filler buildings get fewer windows, no accents.
- **Primary, secondary, tertiary shapes** (Blevins): big shapes survive the squint test, tertiary are
  tiny interest. -> Skyline and masses first, then roofs and annexes, then chimneys, poles, laundry;
  never more tertiary than the silhouette can carry.
- **Push the silhouette; avoid 90-degree sameness.** -> Jitter ridge heights and eave lines; one or two
  tall thin verticals (mast, chimney, crane) break the roof band.
- **Repetition with variation, one design language** (80.lv town: one modular kit, but "the same crack in
  every corner" gives it away). -> One grammar per settlement (roof type, wall material, window
  proportion); vary scale, mirroring, annexes and wear, not the grammar. **70/30**: 70 % unifying
  material and colour, 30 % accents.
- **Start from culture, period and one functional problem** (Feng Zhu: references drive 90 % of the base
  design). -> A reason to exist per settlement; building types derive from it.
- **Form from gradual bricolage, not a plan** (favela analysis: houses under constant renovation, growing
  first sideways then up, streets determined by use). -> Grow a house iteratively: core box, lean-to,
  upper storey, each addition a different material and age.
- **Paths worn by use** (desire lines; medieval layouts "determined by use"; small paths link homes,
  barns, wells). -> Shortest door-to-door routes wear the ground; corners cut.
- **Traces of occupation, not people** (McQue: water cans on roofs, signboards, window flaps, pots,
  tangled cables, machinery worn by decades; "who maintains these, who cooks the food?"). -> A prop
  pass keyed to each building's job.
- **Decide where the dirt goes** (Ghibli: where the soot stained the ceiling, where the rain leaks;
  every beam slightly curved, every roofline with a belly). -> Weathering is directional: streaks under
  sills, a dark band at ground contact, moss on the wet side, sag on old roofs.
- **Site strategies on slopes**: plinth under 10 %, terrace with retaining wall 10-25 %, stilts beyond
  or on wet ground; always a visible wall or plinth band. **Roads follow contours**; stairs and
  switchbacks where they must climb. **Nature grips the building** (Oga: it should be "strangled by
  vines", moss fading into the grass). -> A blend zone at every footprint edge.
- **Massing first, then multiply** (Gurney: map -> plan -> maquette -> paint). -> Plan view (streets,
  plots), extrude masses, then detail: our stage order already.
- **Reading as one place**: density by region (southern villages touch, courtyard farms round a yard);
  shared walls, courtyards and fences make a continuous street line; clutter lives at the seams
  between buildings, not on open ground; one light, one weathering direction, one palette.

Sources: steemit.com (conceptmonk, The Village breakdown); 80.lv (2D concept to 3D village; stylized
medieval town); polycount.com (village WIP); neilblevins.com (primary/secondary/tertiary shapes);
montcarta.com (70/30); fzdschool.com (Design Cinema 96) and Design Cinema 108 (Narshe); buala.org (the
aesthetics of the favela); ludusludorum.com and medievus.com (medieval village layout); 99percentinvisible
(desire paths); parkablogs.com and thisnorthernboy.blog (Ian McQue); elearning.asc.edu.ag (Ghibli
architecture); animationobsessive.substack.com (Kazuo Oga); 3dastudio.com (imperfection);
firstinarchitecture.co.uk (sloped sites); gurneyjourney.blogspot.com (worldbuilding maps; maquettes;
Waterfall City); therookies.co (world building in concept art).

## 3. How level designers build areas

- **Greybox, playtest, then art** (Level Design Book; CDPR's Witcher 3 villages built as grey boxes from
  story needs, then meshes, then "compositions for every street and corner", then foliage and decals;
  Guerrilla's bright critical-path blockouts). -> Validate the grey volume and path graph (walkability,
  widths, sightlines) before any mesh; the art stage cannot change the graph. **Bethesda kit phases**:
  concept, proof, graybox, build-out, polish, one kit artist with one designer.
- **Rockstar RDR2**: the world first, distances between towns tuned, every box became a house once the
  team decided who lives there and their routine, down to grass matted along the daily route. -> Our
  binder routines should produce worn paths, prop clusters and door orientation.
- **Wayfinding vocabulary** (Lynch: paths, edges, districts, nodes, landmarks; HL2's station exit framing
  the Citadel). -> At least one landmark visible from every node, framed by the exit of the space before.
- **Breath of the Wild's triangle rule**: large triangles are landmarks, medium ones block sight to make
  reveals, small ones pace; "gravity" ranks structures by visibility. -> A medium occluder between the
  approach road and the town so it is revealed, not just seen.
- **Dark Souls loop-backs**: long outer route, one-way shortcuts folding back to the hub; distant areas
  visible long before reachable. -> The town as a loop graph with gated shortcuts.
- **Fronts and backs** (Arkane's Dunwall: streets with a hierarchy of fronts and back alleys). -> A
  primary street plus a parallel back network of yards and alleys between building rows.
- **Big-medium-small, clusters not scatter**; every prop needs a reason ("if there is a rock in the
  sand, where did it come from?"); **props cover kit seams**. -> Props as cluster templates anchored to
  a parent (cart + barrels + straw), placed at building-to-building and building-to-ground seams.
- **Environmental storytelling** (Worch and Smith, "What Happened Here?"): props form a cause-and-effect
  chain the player reconstructs; it must be possible to miss some. -> Sentence templates (actor, event,
  consequence) expanding into 3-5 props with spatial constraints, in only some buildings.
- **Skyrim kit rules**: footprints as multiples (512 rooms, 256 halls), pieces inside the footprint,
  separate architecture kit from clutter kit, no pre-cluttered rooms (repeated clutter is spotted before
  repeated walls), standard pieces beat hero pieces. -> Power-of-two footprints; dressing kit separate;
  the same clutter group never twice in one view.
- **Terrain**: embed into the ground rather than sit on it; roads as splines that deform the heightmap
  and drop a decal; vegetation from density maps zeroed inside lots and along paths (Guerrilla).
- **Metrics**: 60-120 s travel between points of interest; Ubisoft moved away from "a POI every 50 m";
  Rust places monuments by simulating placements and keeping the best fit.

Sources: book.leveldesignbook.com (blockout, wayfinding, env-art); gamedeveloper.com (Skyrim modular
level design; BotW lessons; Horizon FW blockouts); blog.joelburgess.com; gist.github.com/idbrii (BotW
CEDEC notes); slidetodoc.com and niemanstoryboard.org and gdcvault.com (What Happened Here?);
thegamer.com (Dark Souls); historyhit.com and fastcompany.com (RDR2); pcgamer.com (Dunwall); 80.lv
(Witcher 3 world building; Horizon procedural placement); therookies.co; exp-points.com;
worldofleveldesign.com; gamesradar.com (AC Shadows POI spacing); rust.facepunch.com (devblog 161);
kaarwan.com (sloped sites); Wikipedia (desire path).

## 4. How city games grow towns, and how players lay them out

- **Cities: Skylines**: zone cells hang off roads (within 4 tiles), every building faces its road,
  buildings level up by services and land value. -> Roads are the only placement substrate: parcels are
  road-adjacent strips; a building's "level" is the count of its satisfied needs.
- **SimCity GlassBox**: maps (pollution, land value, desirability, resources), rules that convert
  resources, agents carrying them along roads, zones that grow when map thresholds are met. -> Our
  interest maps are GlassBox maps; add pollution and desirability layers written by providers.
- **Townscaper / Bad North**: hex grid split to quads and relaxed into an aperiodic grid; WFC picks
  tiles under adjacency; Bad North restarts if beach-to-structure paths fail. -> A relaxed irregular grid
  near the old core; walkability from every door to the main road validated, re-roll on failure.
- **Foundation**: no drawn roads; villagers place houses where desirability is high within 150 m of
  work; roads emerge from worn footpaths. -> Houses sampled within a work-distance cap; secondary paths
  from accumulated traffic.
- **Frostpunk**: radial rings round one heat source. **Against the Storm**: non-overlapping hearth discs;
  storage at the hub edge, production on the rim. -> Radial placement for single-anchor towns; Poisson
  hubs.
- **Manor Lords**: burgage plots between road and setback, levelled by market supply, deep plots get a
  backyard producer; the default form is the one-street Strassendorf. -> Plots as polygons between the
  road and a setback; depth decides a backyard extension.
- **Workers & Resources**: design the chain backwards from the product; walking 300-480 m else transit;
  conveyors unlimited, pipes limited; factory-to-factory links beat trucking. -> Per-link distance limits
  in our provides/needs graph (we have them); solve back from consumer to raw source.
- **Players' rules for realism**: road hierarchy arterial / collector / local, never skip a tier, no
  houses fronting the arterial; don't grid everything, old cores follow contours; industry downwind and
  downstream behind a buffer, on its own loop near port or rail; service radii define hubs, every house
  inside the market disc, production outside it; minimise walking (stockpiles next to workshops, a
  central hall); one funnelled entrance plus a back exit; growth in rings and infill with slack left for
  later; transport is the spine, everything hangs off it.

Sources: Steam Community guides (Cities: Skylines traffic and realism; Banished layouts; Anno 1800;
Manor Lords; Frostpunk; Against the Storm; Workers & Resources); cs2.paradoxwikis.com (zoning);
chillplacegaming.com (road hierarchies; Anno layouts); cs2-master-guide.tiiny.site; dedoimedo.com (CS
traffic; W&R industry); gamesradar.com (CS2 pollution); gamedeveloper.com and pcgamer.com (GlassBox);
gamedeveloper.com (how Townscaper works); github.com/mxgmn/WaveFunctionCollapse; Konsoll 2018 (Bad
North); anno1800.fandom.com; wiki.hoodedhorse.com (Manor Lords burgage plots; Against the Storm
hearths); game8.co; rimworldwiki.com; gamepur.com (killbox); dwarffortresswiki.org (design strategies);
thegamer.com (Frostpunk layout); wiki.polymorph.games and pcgamer.com (Foundation).

## What changes for us

The four passes agree on more than they differ. Ranked by how far each moves our towns from
"a cluster of random buildings":

1. **Roads are the substrate, not a consequence.** Every source: buildings hang off a street, face it,
   and share a continuous front line; clutter sits in the seams between them. Today our layout samples
   positions and grows roads afterwards. Flip it: the spine first (dock -> plant -> tower -> mine),
   then plots as strips along it, then buildings in the plots facing the road, shared fences filling the
   gaps. The Strassendorf is the default form of a one-reason settlement.
2. **One line dominates.** Real plants are read by their conveyor or cableway; concept artists want one
   or two tall verticals and one landmark with a counter-mass. Our conveyor from the wellheads to the
   silos should be the biggest structure in the view, straight, with towers, and the systems layer
   already knows where it runs.
3. **Big-medium-small, clusters not scatter.** Props as anchored templates (a bay = pallets + crates +
   a lamp; a tank = bund wall + valve stand + barrels), never uniform scatter; the same group never
   twice in one view; a detail budget that falls with the building's rank.
4. **Terrain answers the town.** Pads become terraces with a visible retaining-wall band; roads cut
   benches and drop a decal; vegetation density is zero inside plots and along paths and grips the
   footprint edge with a blend zone. We now have pads, graded roads and ground paint; the wall band and
   the blend zone are missing.
5. **History is visible.** Growth rings as epochs (core cluster, boom ring along the spine, decline
   fringe); directional weathering and a decay pass by material; routines worn into the ground as
   desire lines, which our citizens' routines can produce directly.
6. **Validate like a level designer.** Greybox first: walkability from every door to the spine,
   a landmark visible from every node, a medium occluder before the reveal, and travel time between
   points of interest, all checked before any mesh is placed, with re-roll on failure.
