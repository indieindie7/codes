# City generators, and what the binder town should borrow

Written 2026-10-06 after the random-island batch showed the town standing on identical coordinates on
every island. The binder sheets carry fixed `at:` positions; the island changes under them. The user's
intent: the binder fixes only a few landmarks, everything else is placed procedurally around them and
"fluctuates like a Voronoi map".

## How the generators work

**Parish and Müller, CityEngine (SIGGRAPH 2001).** Roads first, as an L-system with *global goals*
(follow population density, radial or grid patterns) and *local constraints* (snap to nearby roads,
avoid water, limit slope); blocks are the cycles of the road graph, lots come from recursive block
subdivision, buildings from a second grammar. Built for cities: dense, regular, flat. The two-stage
idea (goal proposes, constraint corrects) is the part that survives everywhere.
<https://history.siggraph.org/learning/procedural-modeling-of-cities-by-parish-and-muller/>

**Kelly and McCabe, Citygen (2006 survey, 2007 system).** The same pipeline made interactive: road
networks "automatically mapped to terrain models" that adapt to the geometry, blocks extracted from
the graph, convex and concave blocks subdivided into lots. Confirms the city pipeline is terrain-aware
only at the road step. <https://www.researchgate.net/publication/228671232_A_Survey_of_Procedural_Techniques_for_City_Generation>

**Chen et al., tensor fields (2008).** Streets follow a designer-painted direction field (grid, radial,
along a coastline or a height contour). Good for cities that bend round geography; too heavy for a
plant of thirty buildings.

**Watabou, Medieval Fantasy City Generator.** Every map has an underlying mesh; districts are its
cells, roads run along its edges. Started as "city-shaped Voronoi diagrams"; wards get a type
(craftsmen, slum, market) that sets density and building style, and the user can warp mesh nodes.
This is the Voronoi fluctuation the user asked for: cells as districts, buildings sit inside their
cell, nudging a node moves the whole neighbourhood. <https://watabou.itch.io/medieval-fantasy-city-generator/devlog>
(the Haxe source, TownGeneratorOS, is in Documents\Tools\citygen.)

**Emilien, Bernhardt, Peytavie, Cani, Galin, "Procedural Generation of Villages on Arbitrary
Terrains" (Visual Computer 2012).** The one that fits our problem: sparse settlements on hills and
coasts, not cities. Three steps.

1. *Village skeleton.* A growth scenario (a list of events: "seed 6 houses", "change village type to
   fortified") seeds buildings one at a time. A candidate position is drawn at random; its interest
   `I = max(0, Σ wᵢ fᵢ)` is computed from functions `fᵢ ∈ [-1, 1]` (any `fᵢ = -1` forbids the spot);
   an aggregation test keeps the spot with probability rising with I, otherwise redraw. The functions:
   - *sociability*: attraction-repulsion on the distance to neighbours (λmin too close, λ0 preferred,
     λmax too far), parameters per pair of building types;
   - *worship*: the same attraction, only toward the church (our tower / plant office);
   - *accessibility*: an asymmetric bell on the distance to the nearest road;
   - *slope*: a bell on the slope with a forbidden range;
   - *water*: a decreasing function of the distance to water, with min and max;
   - *fortification*: 1 inside the walls, decreasing outside;
   - *geographical domination*: `Σ (h(x) − h(p)) / (1 + |x − p|²)` over the neighbourhood, for churches
     and anything that wants to overlook.
   Each new building is immediately connected to the network by a least-cost road (slope, curvature,
   water and building-crossing costs), with existing road cells costing `w_ex ≪ 1` so roads are reused
   rather than duplicated; then a cycle step looks for a nearby road node in a cone and adds a shortcut.
   Roads attract the next settlers (accessibility) and settlers extend the roads: the loop is the point.
2. *Parcels*: not plain Voronoi (too isotropic, not aligned with roads) but an anisotropic conquest:
   each seed first claims a stretch of its road, then spreads from it perpendicular to the road, with
   slope making spread across the gradient expensive; corners go to whoever arrived first.
3. *Open shape grammar*: windows and doors move or change shape when a rule would put them in the
   ground on a slope.
   Validation against real villages: mean parcel neighbours 2.87 vs 2.81 real, contour edges 4.29 vs
   4.07. <https://perso.liris.cnrs.fr/egalin/Articles/2012-villages.pdf>

**GDMC, the Minecraft settlement competition (2018 to now).** Generators get an unknown terrain and
are judged on adaptability, functionality, narrative and aesthetics. The 2022 winner (Decentralised
Iterative Planning) runs about forty agents over feature maps (height, slope, water, roads, plots,
inside/outside walls) for 60 time steps: the first road is seeded at the flattest spot, road agents
shorten A* travel between random points and bridge water, plot agents pick the fittest of a random
subset of locations under their slope and road-distance limits, and a second pass gives plots a role
(residential, commercial, industrial) from a toy economy, so shops cluster near homes and away from
industry. Jury scores about 6.6 to 7.1 of 10. Recurring judge complaints across years: flattening
the land instead of adapting to it, foundations unsolved on cliffs, bridges over puddles, dark
streets. <https://ar5iv.labs.arxiv.org/html/2309.10871>, <https://arxiv.org/abs/2108.02955>

**Dwarf Fortress / 4X site scoring**, the older game habit: a settlement site is the argmax of a
weighted sum of rasters (flatness, fresh water, coast, resources, defensibility). Same as the interest
map with one sample.

## What applies to the binder town

The binder already is a *growth scenario* (layers core, boom, decline) with a *building encyclopedia*
(kind, size, users, wear) and *sociability facts* (who works where, what fears what). What it lacks is
the interest machinery and the roads-as-you-go loop. The plan, implemented as `tools/layout.py`:

- **Anchors.** Sheets with `anchor: yes` keep their `at:` (the command tower is BSP; the Authority pad
  belongs to it). Everything else floats.
- **Interest per kind**, from the sheets: halls want flat ground near the plant office and each other;
  the office wants the coast and a view of the tower at a distance; the dock, jetty, intake and pump
  station want the waterline with deep water in front; rigs want open water 150 to 700 m out; the
  director's house wants domination and distance from the halls; wellheads want to spread inland; the
  dorm wants the halls but not the cooling towers. Weights are small integers; nothing is tuned yet.
- **Seeding order** = the binder layers, plant office first inside its layer, so the core clusters
  before the boom spreads.
- **Roads as you go**: each placed building gets a least-cost path (slope², water, footprints) to the
  network, reuse weight 0.2, so a trunk road forms from the tower and side tracks hang off it. The
  checkpoint is then put on that trunk.
- **Voronoi fluctuation**: after seeding, each floating building drifts toward the centroid of its
  Voronoi cell a few times, as long as its interest does not drop. Buildings keep their relations
  but never the same coordinates twice.
- **Doors** face the nearest road (the checker's rule), docks face the sea.

What stays for later: anisotropic parcels (fences, yards), the cycle step for shortcuts, open shape
grammar for the prefab walls on slopes (we terrace instead), painting the roads into the terrain
layers. The judge list from GDMC is a good checklist for our own sheets: no flattening beyond the
pads, no road up a cliff, lights along the trunk road.
