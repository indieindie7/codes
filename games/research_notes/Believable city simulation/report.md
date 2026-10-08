# Stacking simulations on the spine town: a ranked report

Research pass, 2026-10-08 (Q35; the user: "do some research about improving our spine city model for more believable cities, maybe stacking on top some other simulations"). Written by a research agent.

Code read: `layout_spine.py`, `systems.py`, `binder.py`, `walks.py`, `clutter.py`, `viewshed.py`, `district.py`, `live_gen.py`, `town.py`, `terrain_cutfill.py`.

Reports read:
- `Organic settlement generation/notes.md`
- `Level design practices/report.md`
- `How others build towns.md`
- `City generators for the binder town.md`

This report doesn't repeat those. It adds the simulation layers. The accrete/stack/dress algorithm in notes.md §6 is the right *geometry* pass, and this report supplies the *drivers* that tell it where and how much.

## Summary: the ranked stack

Each pass runs after `layout_spine.py` and writes into the same layout JSON. Order = biggest believability gain per effort.

| # | Pass (new file) | What it adds | Effort |
|---|---|---|---|
| 1 | **Value fields + epochs** (`fields.py`) | Access, nuisance (pollution plume), view and slope rasters. A bid-rent rule decides who gets which land. Each building gets an `age`. | S |
| 2 | **Imperfect plots** (inside `layout_spine.py`) | Gap, setback and yaw become distributions driven by value and age. Some gaps go to zero (party walls). Plots get backs. | S |
| 3 | **Epoch growth / accretion** (`accrete.py`, the notes.md §6 design) | Grown in core → boom → decline steps. Each step infills, extends and adds storeys where value is high. Old = most additions. | M |
| 4 | **Road hierarchy + loops** (`roads2.py`) | Back lanes behind the plot rows, a connector rule that closes loops, Galin-style grade and curvature costs (switchbacks), road classes. | M |
| 5 | **Desire lines → lanes, with decay** (`walks.py` extension) | Rerun the walkers on the grown town. Busy trails become lanes. Worn shortcuts cut fence gaps. | S |
| 6 | **Space-syntax integration** (`syntax.py`) | Per-segment integration and choice. Shops, signs, lamps and gathering spots on the busy segments; dead ends, laundry and junk on the quiet ones. | S |
| 7 | **Utility trees** (rewrite of `systems.py`'s `l_route`) | Per resource, a Steiner-approximate tree along the roads. Shared trunks become pipe racks and pylon lines. The ore line stays straight. | S |
| 8 | **Wear and clutter from use** (`clutter.py` inputs) | Clutter density = traffic × function × age × (1 − value). Directional weathering from the wind vector picks the Skins variant. | S–M |

**Metrics to compute before and after** (section 11):
- **Imperfection score**: gap and setback CV, yaw spread and its correlation along a row, and the party-wall share.
- **Hierarchy score**: the Gini of segment betweenness, the dead-end share, loops, the orientation entropy, and the correlation between building age and distance from the dock.

## 0. What the current code does, and where it reads as fake

1. **Constant spacing.** `GAP_M = 10`, `SETBACK_M = 4` and `ROAD_HALF_M = 4` are the same for every plot. Real frontage has gap CV ≈ 0.5–1.0 and many zero gaps.
2. **Perfect facing.** `yaw = atan2(-ny, -nx)`: every front looks exactly at the road. Real rows wobble 2–10°, coherently along a stretch.
3. **No backs.** Plots are footprint-deep: no yard, no lane, no back side.
4. **Thin hierarchy.** One spine plus up to two `branches_to_room` roads. `add_branch` makes a straight 140 m stub. There are no loops, lanes or alleys, and every branch is a dead end.
5. **Time layers only sort.** `LAYERS` orders placement and `STRETCH` sets fractions along the spine. Age doesn't change where a building stands or how it looks.
6. **Road cost is isotropic.** `path()` = `step * (1 + 30 dz²)`, with no curvature or grade cap. Chaikin then smooths the zig-zags, so there are no switchbacks or contour-hugging roads.
7. **One line per need.** `systems.py` routes each consumer → provider pair as an L-shape. Parallel duplicate pipes appear and never share a trunk.
8. **Walks don't feed back.** `walks.py` is a good Helbing active walker, but its wear never decays, and its trunks never become roads.
9. **No nuisance field.** Only a dorm/house push away from cooling/tanks. There is no wind, plume or land value, so the shanty ring has no reason to be where it is.

## 1. Growth over time

### 1a. Lechner et al., "Procedural City Modeling" (2003) and "Procedural Modeling of Urban Land Use" (2006)

Developer agents (residential, commercial, industrial) build where land value is high and a road is near. Road agents grow the network: *extenders* push into new land, and *connectors* add a link when the travel distance along the network is much longer than the straight distance. Land value comes from access, terrain and neighbours.

Sources: https://ccl.northwestern.edu/papers/ProceduralCityMod.pdf · https://ccl.northwestern.edu/papers/2006/TR-2007-33.pdf

**Take:**
- the **connector rule** (pass 4);
- **developer agents that sample the value field** (pass 3).

We have 46 binder buildings, not thousands, so skip the full patch simulation.

**Effort:** S for the connector, M for the agents.

### 1b. Weber, Müller, Wonka, Gross, "Interactive Geometric Simulation of 4D Cities" (Eurographics 2009)

A city simulated over time on exact geometry. Per step: streets extend, value is recomputed from accessibility, and lots are developed or **redeveloped** (densified, taller). Time leaves traces: old cores are irregular and dense, edges are newer and sparser.

Source: https://doi.org/10.1111/j.1467-8659.2009.01387.x

**Take: epochs.** The binder layers become time steps. Per epoch:
1. extend the spine (core = the works stretch; boom reaches the tower and mine);
2. recompute value;
3. place that layer's buildings;
4. densify older plots.

Decline marks some plots abandoned. Output per building: `age`, `epoch_built`, `additions[]`.

**Effort:** M.

### 1c. Vanegas, Aliaga, Beneš, Waddell (SIGGRAPH Asia 2009) and UrbanSim

Households and jobs choose locations by price and access; prices respond; the loop iterates. Vanegas et al. close the loop with the generated geometry.

Source: https://www.cs.purdue.edu/homes/bbenes/papers/Vanegas09ToG.pdf

**Take:** a **fixed-point loop**: layout → walks → value → re-place the movable buildings, 2–3 times. `town.py` already rerolls on systems failure; this is a rerun on value.

**Effort:** S.

### 1d. Accretion: infill, extension, enlargement

Informal and company-town growth is mostly additions: infill shacks, lean-tos and annexes, added storeys. The Dar es Salaam agent model reproduces real patterns with just these three rules. Barros and Slumulation put poor housing on the worst land within walking distance of jobs. This is already designed in notes.md §1 and §6.

Sources: https://catalog.comses.net/publications/247 · https://discovery.ucl.ac.uk/id/eprint/243/1/Paper55.pdf · https://www.jasss.org/15/4/2.html

**Drivers:**
- P(infill) ∝ value × access × (1 − nuisance)⁰·⁵ for company plots;
- P(infill) ∝ (1 − value) × job proximity for shacks;
- additions ∝ `age`;
- storey cap ∝ value.

### 1e. "Older core, newer edges": rules per epoch

- **Core:** the spine runs dock → works only. Small gaps, 2–4 m setbacks, low yaw jitter (planned). The most additions accrue later.
- **Boom:** the spine is extended. Wider, uniform company-prefab plots, low jitter, few additions.
- **Decline:** no new company plots. Shacks infill the worst land and the gaps between boom plots. 10–20 % of core plots are abandoned, with squatter additions.

Age drives wear, skins and decay (pass 8).

## 2. Road networks

### 2a. Parish & Müller, CityEngine L-system (SIGGRAPH 2001)

*Global goals* propose the next segment; *local constraints* correct it (snap to a node, stop at water or steep slope).

Source: https://cgl.ethz.ch/Downloads/Publications/Papers/2001/p_Par01.pdf

**Take:** lane growth off the spine.
- Propose a lane every 40–80 m along a plot row.
- Snap it to a lane end within 25 m, which makes a loop.
- Stop at slope > 25° or water.
- Dead ends are allowed in low-value areas.

**Effort:** M (part of pass 4).

### 2b. Tensor-field streets: Chen, Esch, Wonka, Müller, Zhang (SIGGRAPH 2008)

Streets traced as hyperstreamlines of a painted two-direction field.

Source: https://www.sci.utah.edu/~chengu/street_sig08/street_project.htm

**Take, the cheap version:** major direction = the contour, minor = the fall line, both from the heightmap. In the shanty ring, lanes follow the contour, stair alleys run down the fall line, and plot and shack yaw snap to the local field. That gives coherent but varied orientation.

**Effort:** S for the field and yaw snap, M for streamline tracing.

### 2c. Galin et al., "Procedural Generation of Roads" (Eurographics 2010)

A weighted *anisotropic* shortest path with a large neighbourhood mask. The cost covers slope (hard grade limit), curvature, water and vegetation. It gives smooth curves without Chaikin, and real **switchbacks**.

Source: https://perso.liris.cnrs.fr/egalin/Articles/2010-roads.pdf

**Take:** replace `path()`.
- State = (cell, incoming direction); a 7×7 mask (~32 directions).
- Cost = length × (1 + k_g·g²); grade > 12 % forbidden for vehicles; plus k_c × turn²; plus a water penalty.
- **Existing road cells cost w_ex ≈ 0.2**, so roads merge into shared trunks (the Wildlands rule).
- Output a grade per vertex for `terrain_cutfill` benches.

**Effort:** M.

### 2d. Galin et al., "Authoring Hierarchical Road Networks" (Pacific Graphics 2011)

Road classes with their own metrics, generated in order of importance, with path merging into junctions.

Source: https://www.cs.purdue.edu/homes/bbenes/papers/Galin11CGF.pdf

**Take:** tag each road `class` and route the classes in this order:
- `spine` (8 m) and `branch` (6 m), with the vehicle grade cap;
- `lane` (3–4 m), with a 20 % cap;
- `path` (from walks);
- `stair` (fall line, up to 70 %).

`clutter.py` then sizes slabs, lamps and verges by class.

**Effort:** S once 2c exists.

### 2e. Emilien et al., villages on arbitrary terrains (2012) and WorldBrush (2015)

2012 is already implemented in `layout.py`. Two parts are unused: the **cycle step** (search a cone ahead of a road end for a node and add a shortcut) and **anisotropic parcels**. WorldBrush learns distributions (spacing, orientation, sizes) from examples.

Sources: https://perso.liris.cnrs.fr/egalin/Articles/2012-villages.pdf · https://www.cs.purdue.edu/homes/bbenes/papers/Emilien15ToG.pdf

**Take:**
- the cycle step (pass 4);
- WorldBrush's idea as **metric targets**: measure spacing and orientation distributions from a real reference (Longyearbyen, a favela tile, a company-town aerial) and tune pass 2 to match.

### 2f. Ghost Recon Wildlands

The Houdini road builder treated existing roads as "dirt cheap", so the roads joined into one network. It also had a settlement builder. This is the single most useful road trick for us.

Sources: https://80.lv/articles/procedural-technology-in-ghost-recon-wildlands/ · https://80.lv/articles/procedural-world-building-in-ghost-recon-wildlands/

## 3. Land use and value fields

### 3a. Accessibility

Multi-source Dijkstra over the road graph plus off-road cells (reuse the CSR graph in `walks.py`) gives `T_dock` and `T_works` in minutes. Then:

`access = exp(-T_dock/5 min) + exp(-T_works/3 min)`

**Effort:** S.

### 3b. Nuisance and pollution: a Gaussian plume

Add a prevailing `WIND` vector (the storm direction). For each emitter (cooling towers, generator, chimneys, tank farm, silos):

```
C(x) = Q * exp(-cross² / (2σ(d)²)) / σ(d),   d = distance downwind > 0,   σ(d) = 0.08·d + 20 m
```

plus `Q2 * exp(-r/80 m)`. Sum into `NUIS`. The same field later puts soot on walls (pass 8).

Source: https://en.wikipedia.org/wiki/Atmospheric_dispersion_modeling

**Effort:** S.

### 3c. Slope, view and domination

One field: `view = Σ_k (h(x_k) − h(p))⁻ / (1 + |x_k − p|²)` (Emilien's domination term), plus optional sea visibility from `viewshed.py`.

### 3d. Bid-rent: the shanty ring as the poor-land outcome

Per cell, `V = a·access + b·view − c·NUIS − d·slope_penalty`. Assign by bid order:
1. company core (office, store, clinic): bids for access + view;
2. dorms: access to the works, tolerate nuisance;
3. the director: view, avoids nuisance;
4. shanties get the residual: steep, downwind and on the works' edges, but within a 10 min walk of the works (Slumulation).

In code, `try_place`'s score uses `bid_k(V components)` instead of the ad hoc avoid terms. The shanty mode in `live_gen.py` gets the candidate mask `V < p30 & T_works < 10 min`.

Source: https://en.wikipedia.org/wiki/Bid_rent_theory

**Effort:** S.

## 4. Space syntax (Hillier)

*Integration* (closeness on the angular dual graph) predicts where movement and shops concentrate. *Choice* (betweenness) predicts through-routes. Low-integration segments are the quiet back alleys.

Sources:
- https://en.wikipedia.org/wiki/Space_syntax
- depthmapX (GPL-3): https://github.com/SpaceGroupUCL/depthmapX
- cityseer (AGPL-3): https://github.com/benchmark-urbanism/cityseer-api/
- momepy (BSD): https://github.com/pysal/momepy

**Pass `syntax.py`:**
1. Build the graph from roads + lanes + walk trunks.
2. Build the angular dual (weights = turn / 90°).
3. Compute integration (closeness at r ≈ 400 m) and choice with networkx.

**Uses:**
- Top 15 % integration → a node: sign, lamp, water tank, shop front, gathering spot.
- Top choice → lamps every 30 m and road wear.
- Bottom 20 % → dead ends, laundry, junk, darker.
- Check: integration should peak near the dock/works core. If it doesn't, add a connector.

**Effort:** S (~80 lines).

## 5. Footpaths and desire lines

The Helbing active walker: walkers are pulled toward visible trails; wear is deposited and **decays**; a few trunks emerge, merging into Y-junctions. `walks.py` lacks the decay and the visibility pull. Foundation builds all its paths this way, and its villagers cut through gardens: the lived-in signal we want.

Sources: https://arxiv.org/abs/cond-mat/9806097 · Nature 388:47 (DOI 10.1038/40353) · https://www.pcgamesn.com/foundation/medieval-city-builder-out-now

**Pass:**
1. Decay `wear ← wear·(1−0.3) + deposit`, and a 3×3-blurred wear for the discount, so trails attract walkers from ~5 m.
2. Run after accretion.
3. Promote traffic > T_lane to `class: "lane"` roads and > T_path to `class: "path"` (skeletonise, then Douglas-Peucker).
4. Where a trunk crosses a fence: cut a gap or a gate. Trodden yards become bare earth in `groundpaint.py`.
5. Feed the traffic to pass 8.

**Effort:** S.

## 6. Wear and clutter

Clutter collects where use is high and care is low:
- trash at corners, dead ends, plot backs and doors;
- crates at bays;
- laundry across narrow lanes between dwellings;
- cables along walls to their source;
- signs at the busiest junctions.

Weathering is directional: water washes down facades and leaves stains below sills (Dorsey, Pedersen and Hanrahan, SIGGRAPH 1996, https://graphics.stanford.edu/papers/flow), and γ-ton tracing generalises it (US7557807).

```
density(p) = base[kind] * (1 + traffic(p)/T) * (0.5 + age(b)) * (1.2 - value(p)) * (1 + 0.5*low_integration(p))
```

- **Crates:** ∝ the hall's goods flow from `systems`.
- **Laundry:** across lanes < 4 m between dwellings, more in low-value, old areas.
- **Signs and lamps:** at integration nodes.
- **Skins:** by grime = age × (wind exposure + NUIS): clean, streaked or soot.
- **Wall feet:** a dark band on the windward side.
- **Rust streaks:** under pipe racks, only in the viewshed (projectors are expensive in UE2).

**Effort:** S for density driving, M for edge-driven placement.

## 7. Utility networks

Real utilities are trees with shared trunks along roads.
- The MST (Kruskal) is the baseline.
- The Steiner tree (the Kou–Markowsky–Berman 2-approximation, `networkx.algorithms.approximation.steiner_tree`) adds junctions.
- Far Cry 5's Houdini toolset had a power-line tool.

Sources: https://en.wikipedia.org/wiki/Steiner_tree_problem · https://80.lv/articles/houdini-procedural-world-generation-of-far-cry-5/ · https://gdcvault.com/play/1025215/Procedural-World-Generation-of-Far

**Pass:**
1. Graph = road vertices (≥ lane) plus one link per building. The spine costs ×0.5 (a pipe-rack corridor).
2. Per resource: a Steiner tree over providers ∪ consumers, split by provider.
3. Edges carrying ≥ 2 resources become a pipe rack (district.py's `PipeRack`), with hoops over road crossings.
4. Power: pylons every `RELAY_M`, with sagging cables to the walls. Comms stay radio.
5. The ore line stays straight, with a hub tower where runs meet.

**Effort:** S.

## 8. Shipped games and tools

| Source | Take for us |
|---|---|
| Townscaper / Bad North (Stålberg) | An irregular grid sits between free placement and a rigid grid; pass 2 jitter does that job at plot scale. https://www.gamedeveloper.com/game-platforms/how-townscaper-works-a-story-four-games-in-the-making |
| Watabou MFCG | Ward type → density, jitter and skin palette; each district gets a parameter set. https://watabou.itch.io/medieval-fantasy-city-generator/devlog |
| Manor Lords | Plots face the first-drawn edge; deep plots get a backyard extension slot, which gives back sides. https://wiki.hoodedhorse.com/Manor_Lords/Buildings |
| Cities: Skylines | Buildings level up with value and services: storeys/additions ∝ value × satisfied needs. |
| Foundation / Banished | Paths emerge from traffic; shortcuts cut gardens (pass 5). |
| SimCity GlassBox | Maps (pollution, value) + agents + resource rules (pass 1). |
| Dwarf Fortress / RimWorld | Stamped bases read as generated because they lack age and accretion. |
| GDMC (Minecraft) | Agents over feature maps; judges' complaints (flattening, unsolved foundations, dark streets) as checks. https://arxiv.org/abs/2309.10871 |
| Marvel's Spider-Man (GDC 2019) | Hand-authored work is kept if it still meets spec after regeneration: our `avalon mark` edits need a re-validated override layer. https://gdcvault.com/play/1026496 |
| Ghost Recon Wildlands | Existing roads are "dirt cheap" for the road builder (pass 2c). |
| Far Cry 5 | Power-line tool (pass 7). |
| Cyberpunk 2077 | A prefab hierarchy: building + additions + clutter as one aggregate (also suits merging into one UE2 mesh). https://gdcvault.com/play/1027571 |
| StreetGAN (Hartmann et al., WSCG 2017) | Not worth building, but its evaluation by road-graph statistics is the right idea (section 11). https://otik.zcu.cz/bitstream/11025/29554/1/Hartmann.pdf |

**Not found:** any AC Unity technical talk on procedural Paris, and Martin Evans' road blog (not indexed).

## 9. What makes a generated town look fake: automatable checks

| Tell | Check on the JSON | Target (proposed) |
|---|---|---|
| Uniform spacing | gap CV per road side; party-wall share (gaps < 1 m) | CV ≥ 0.5; party walls 15–40 % in core/shanty, < 10 % at works |
| Uniform setback | setback CV | ≥ 0.3 |
| Perfect facing | std(yaw − road normal); lag-1 autocorrelation along a row | 3–8°; r > 0.4 |
| No hierarchy | Gini of segment betweenness | ≥ 0.5 |
| No backs | share of perimeter facing a yard or lane | ≥ 40 % |
| Dead ends | degree-1 share; loops E − V + C | 10–30 %; ≥ 2 loops in core |
| Grid-straight roads | Boeing orientation entropy (36 bins); circuity | ≈ 3.3–3.5 nats; 1.05–1.2 |
| No landmark | landmark visible from walkable cells | ≥ 70 % |
| No time | Spearman ρ(age, network distance from dock); additions vs age | ρ ≤ −0.4 |
| Clutter unrelated to use | r(prop density, traffic + integration) | ≥ 0.4 |
| Duplicate utilities | pipe length ÷ Steiner length; parallel runs < 5 m apart | ≤ 1.2; none |
| Repeated clutter group | template hash per viewshed tile | no repeats |

Orientation entropy reference: Boeing 2019, https://arxiv.org/abs/1808.00600 (irregular colonial Olinda ≈ 3.49 nats; grids ≈ ln 4 = 1.39). Morphometrics: momepy.

## 10. The stack in detail

1. **Value fields + epochs (S).**
   - Compute `access`, `NUIS` (plume with `WIND`), `view`, then `V`.
   - Wrap placement in `for epoch in core, boom, decline`: the spine is truncated to the works for core, then extended.
   - Write fields npz plus per-building `age` and `value`.
2. **Imperfect plots (S, `try_place`).**
   - `GAP_M ~ lognormal(med 6 m, σ 0.7)`, with P(0) = 0.3 in core and shanty.
   - `SETBACK_M ~ 1–6 m`, smaller where value is high.
   - `yaw = road normal + AR(1) noise (σ 4°, ρ 0.6)`, or snapped to the contour field in the shanty.
   - Depth = footprint + U(0, 15 m) → a back yard; fences close the back and side lines.
3. **Epoch growth / accretion (M, `accrete.py`).** Drivers from 1–2:
   - infill P from V, or from 1 − V × job proximity for shacks;
   - additions ∝ age;
   - storeys ∝ V;
   - decline abandons 10–20 % of low-V boom plots.
4. **Roads (M, `roads2.py`).**
   - Galin `path()`: grade cap, curvature, w_ex = 0.2.
   - Back lanes behind deep rows.
   - Connector: network/euclid > 2 and euclid < 80 m → a lane.
   - Contour lanes and fall-line stairs in the shanty.
   - Classes everywhere.
5. **Walks with decay (S).** Promote trunks, cut fence gaps, mark trodden yards.
6. **Space syntax (S).** Nodes → signs, lamps, gathering spots; quiet ends → dead-end dressing.
7. **Utility trees (S).** Steiner along roads, racks on shared edges, pylons, cables.
8. **Clutter from use (S–M).** Density from traffic × age × (1 − value) × low integration; skins by grime.

**Why this order:**
- 1–2 are cheap and change every frame: constant spacing and perfect facing are today's strongest tells.
- 3 needs 1–2 to know where.
- 4–5 give hierarchy.
- 6–8 make the clutter mean something.

**Not now:** a full tensor solver, WFC massing, GAN roads, a full UrbanSim market.

**Taste fit:**
- *One good frame:* the hierarchy and landmark checks put a trunk, a node and a ragged edge in the command-room window.
- *Dystopian corporate:* bid-rent gives the company the best land and puts the shacks downwind of the cooling towers, sooted by the plume.
- *Organic:* accretion, decaying desire lines, wobbling rows.

## 11. Metrics (`metrics.py`, numpy + networkx, from the layout JSON)

**A. Imperfection** (per road side, plots sorted by s):
```
gap_cv = std(gaps)/mean(gaps); party = share(gaps < 1 m); setback_cv; yaw_dev = std(wrap(yaw - normal)); yaw_ac = lag-1 autocorr
IMP = mean(clip(gap_cv/0.5), clip(party/0.25), clip(setback_cv/0.3), clip(yaw_dev/5), clip(yaw_ac/0.4))
```
Today's output scores ≈ 0 on most terms: a sharp before/after signal.

**B. Hierarchy and time** (graph of roads + lanes + paths):
```
gini_choice (length-weighted edge betweenness); dead_share; loops = E - V + C; entropy (Boeing, 36 bins); age_rho = Spearman(age, network distance from dock)
HIER = mean(clip(gini/0.5), band(dead,0.1,0.3), clip(loops/3), band(entropy,3.0,3.6), clip(-age_rho/0.4))
```

**C. Use-correlation (optional):** Pearson r between props per 20 m tile and traffic + integration; > 0.4 means the clutter tells where people go.

`town.py` can reroll on low IMP/HIER, as it rerolls on unmet core needs.

**Not verified:** Weber 2009's exact per-step rules (only the abstract was read); the GDC talk contents beyond their session descriptions. The section 9 targets are proposals to tune, except Boeing's entropy values.
