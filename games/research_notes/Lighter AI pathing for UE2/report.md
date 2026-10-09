# Lighter, faster AI pathing for Unreal II (UE2, build 829)

Research 2026-10-09, asked by the user after TutA_Remake's PATHS DEFINE ran 45+ minutes ("research a fix for this
costly ai pathing system and make something lighter and more dynamic we can do faster recalculations"). No game files
changed. Sources:
- our own Ghidra exports of the game's binaries (`Documents\U2_research\ghidra\bridge-exports\{Engine,Editor}\<address>.json`);
- constants read from `Engine.dll` and `Core.dll`;
- the script source embedded in `System\Engine.u`;
- the exported U2/U2AI scripts (`Documents\Tools\u2_export`);
- the node file `U2_research\towns\TutA_Remake907\isl_paths.t3d`.

See also `research_notes\Agent locomotion and pathfinding\pathfinding.md`.

**Short answer.** PATHS DEFINE is slow for two reasons:
- every node pair within 1200 UU gets a step-by-step walk simulation;
- that simulation is repeated for up to **9 creature sizes**.

We give it about 29,000 candidate pairs. Fixes, in order:
1. Fewer nodes: a staggered ~1100 UU lattice with no static cover nodes (about 20x fewer pairs).
2. Trim `LevelInfo.PathSizes` from 9 to 2-3 sizes (up to about 4x more).
3. The stock `PATHS DEFINECHANGED` command for later edits.

The bigger plan: write the ReachSpecs ourselves from Python, and let script switch edges on and off at runtime
(`ReachSpec.DisabledCount` / `ExtraCost`) when the GM edits terrain.

---

## 1. Why PATHS DEFINE is slow

### What the editor does (from our decompile)
- **`UEditorEngine::Exec_Paths`** (Editor 10253d40) handles:
  - `PATHS DEFINE`: `FPathBuilder::undefinePaths`, then `definePaths`;
  - `PATHS DEFINE DIFF`: the same, and logs every changed ReachSpec;
  - **`PATHS DEFINECHANGED`**: `FPathBuilder::defineChangedPaths`, an incremental rebuild;
  - `PATHS UNDEFINE`, `REMOVE`, `BUILD`, `ENABLE/DISABLE [SELECTED]`.
  - It parses `VISIBLEONLY=`, but the value appears unused.
- **`FPathBuilder::definePaths`** (Engine 103d4d20):
  1. makes a Scout pawn (`getScout`) and turns on path collision;
  2. links every NavigationPoint into `Level.NavigationPointList`;
  3. runs `addReachSpecs` on every node;
  4. runs `PrunePaths` on every node.
- **`ANavigationPoint::addReachSpecs`** (103ccc00) pairs every NavigationPoint with every other one. `ProscribedPathTo` (103cbf90) skips a pair when:
  - the squared distance is over **1,440,000**, i.e. **1200 UU** (the double at 0x1051ed18; `LevelInfo.PathsMaxDistSquared` in script); or
  - `bOneWayPath` is set and the target is behind the node.

  Names in `ProscribedPaths[]` / `ForcedPaths[]` make specs with no test. Every other pair goes to `UReachSpec::defineFor`.
- **`defineFor` → `findBestReachable`** (103f3c00):
  1. shrinks the Scout to `PathSizes(0)` and runs `PlaceScout`, `APawn::actorReachable` and `walkReachable`;
  2. runs `TestReach` for each larger PathSizes entry until one fails, placing the Scout and walking again each time.
- **U2's `LevelInfo.PathSizes` has 9 entries** (radius/height): 20/20, 28/32, 28/54, 34/70, 40/70, 60/70, 60/96, 80/100, 100/100. On open terrain all nine usually pass, so one connected pair costs about 9 walk simulations.
- **`walkReachable`** (103ddd70) steps a fixed **16 UU in the editor** (12-32 in game, by pawn), capped at 100 steps.
  - Each step is a `walkMove`: several swept `MoveActor` calls plus a floor trace.
  - Our average pair is about 840 UU: about 52 steps, about 200+ sweeps per size.
- **`PrunePaths`** (103ce7a0) drops a spec when another route is at most **1.2x** as long (0x1052c078). It uses the recursive `FindAlternatePath`, so its cost grows with (specs per node)^2.

### Our numbers (measured on `isl_paths.t3d`)
| Layout | Nodes | Ordered pairs within 1200 UU |
|---|---|---|
| Current file: ground + high + drain + truckroad + **251 cover** | 1,799 | **29,108** (16 per node) |
| Without the cover nodes | 1,548 | ~22,900 |
| Every 2nd cell, square 1024 grid | 387 | 1,146 |
| **Staggered lattice, 1024 / ~1145 neighbours** | 389 | **1,590** |

29k pairs x up to 9 sizes x about 52 steps is about 13M `walkMove` calls, roughly 60M collision queries, on one core.

### What maps of that era used
- Nodes must be under 1200 UU apart to connect; `MAXPATHDIST` is in UnPath.h ([UDN Two: NavigationAI](https://docs.unrealengine.com/udk/Two/NavigationAI.html); UT2003 uses 1000 UU coverage, [NavigationAIUT2003](https://docs.unrealengine.com/udk/Two/NavigationAIUT2003.html)). In U2 it is **hard-coded** in Engine.dll.
- Community advice: the fewest nodes that cover the map; 300-700 UU indoors ([Unreal Wiki: Basic Bot Pathing](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Basic_Bot_Pathing.html)).
- Auto-generation took 5-10 minutes on a typical level ([UT AI reference](https://unrealarchive.org/unreal-tournament/documents/reference/unrealed/unreal-tournament-ai/index.html)).
- Shipped maps had a few hundred NavigationPoints (a rule of thumb; no exact published count found).

### Knobs and quick wins (cheapest first)
1. **Node layout** (`pathnodes.py`):
   - a staggered lattice at about 1024-1100 UU on open ground (about 6 neighbours each, all under 1200);
   - extra nodes only at door mouths, building corners, ramps and both ends of narrow passages;
   - drop the 2-per-prop cover nodes. **U2's AI makes its own cover points at runtime**: native `FindCoverSpot(...)` spawns a `CoverSpot` (Controller.uc; used at U2NPCControllerBasic.uc:4210).
   - About 20x fewer pairs.
2. **`PathSizes` on the map's LevelInfo** (a `var(Paths)` array, editable per map; the source warns "DO NOT MODIFY THIS UNLESS YOU KNOW WHAT YOU ARE DOING").
   - Keep only the sizes of the pawns that walk Avalon, e.g. 28/54 and 34/70.
   - A spec stores the largest size that passed, so a bigger creature added later needs its size back in.
   - Up to 4x.
3. **`PATHS DEFINECHANGED`** for later edits, through U2EdBridge.
   - `defineChangedPaths` (103d5590) rebuilds only nodes with `bPathsChanged` (offset 0x3f4, bit 0x40). It tests pairs with one changed end and prunes specs into changed nodes.
   - Moving a node in the editor sets the flag (`OldEditorLocation`, "dirty paths fix").
   - Untested: whether re-imported nodes, or untouched nodes near a terrain edit, get flagged. A 0 UU nudge via uedlib `!move` should flag them.
4. **Collision cost per step:** simple (box) collision on buildings and clutter, terrain only over the play area.
5. **What won't help:**
   - raising the 1200 limit (needs an Engine.dll patch);
   - splitting the map (the cost is per pair, and pairs are already local).

1 + 2 together should take a full define from 25+ minutes to well under a minute (an estimate: about 1,600 pairs x 2-3 sizes against 29k x 9).

---

## 2. Can we write the ReachSpecs ourselves and skip PATHS DEFINE?

### What a ReachSpec is in U2 (Engine.u source)
- `class ReachSpec extends Object native`: a **UObject, not a struct**.
- Fields, all `var() editconst`: `Distance`, `Start`, `End`, `CollisionRadius`, `CollisionHeight`, `reachFlags`, `MaxLandingVelocity`, `bPruned`, `bProscribed`, `bForced`, `DisabledCount`, `ExtraCost`, `bSpecialPath`, `bSpecialCollision`, `SpecialTeamNumber`.
- NavigationPoint has `var() const editconst array<ReachSpec> PathList`, plus `nextNavigationPoint`, `PathInCount`, `PathOutCount`, `bPathsChanged`, `ExtraCost`, `bBlocked`, `ConnectFlags`.
- Decompiled offsets match the source:

  | Field | Offset |
  |---|---|
  | Distance | +0x28 |
  | Start | +0x2c |
  | End | +0x30 |
  | Radius / height | +0x34 / +0x38 |
  | reachFlags | +0x3c |
  | bool bits | +0x44 |

- Flag bits (`ShouldFilterPath`): 2 = fly, 4 = swim, 8 = jump, as in the public UE2 `EReachSpecFlags`; walk is 1.

**The Advent chat's lead ("PathNodes without PATHS DEFINE")** is sound for U2 too. One difference: `PathList` holds object references, not inline structs, so each spec must exist as a named object in the level package.

### Route A: T3D import (most promising; a 15-minute test decides it)
What the decompile confirms:
- **The importer works in two passes.** `ULevelFactory::FactoryCreateText` (Editor 10247a30) spawns every actor first, keeps each one's property text, then runs `ImportProperties` on them all. So `PathList(0)=ReachSpec'...'` and `End=PathNode'...'` can point at actors defined later in the file.
- **`ImportProperties` (Editor 10268b40) accepts `Begin Object Class=X Name=Y ... End Object` inside an actor block.** It creates the object with `StaticConstructObject` in the import package and imports its properties.
- **The one thing to test:** the block is imported only if the class has class-flag bit **0x10**. In the UE2 flag table that is probably `CLASS_Parsed`, which every script class has (inferred from the same code using 0x200 = Placeable).
- `const` / `editconst` restrict script and the property window, not T3D import.

**The test**, on a copy of a test map:
1. A T3D with two PathNodes. GenPath0 holds `Begin Object Class=ReachSpec Name=RS0` (Start=GenPath0, End=GenPath1, Distance, CollisionRadius=34, CollisionHeight=70, reachFlags=1) and `PathList(0)=ReachSpec'RS0'`, plus the `nextNavigationPoint` links.
2. Import, check with `show paths`, save and reload.
3. In game: a pilot `FindPathToActor`.
4. Also export a small map with real paths (Edit -> Export) to see exactly how U2 writes PathList and specs.

**What we must write ourselves** (PATHS DEFINE normally does it):
- the `Level.NavigationPointList` head and the `nextNavigationPoint` chain;
- `PathInCount` / `PathOutCount`;
- `bPathsChanged=False`.

The LevelInfo already exists: setting `NavigationPointList` may need an editor `set` or a T3D replace; also check whether the game rebuilds the list at load. **Never run PATHS DEFINE afterwards**: it would wipe our specs.

**Python side (`pathspecs.py`):**
- For each pair within 1200 UU, sample the segment every 16-32 UU on our heightmap.
- Keep the pair only if every rise is <= 35 (AI step), the slope is walkable, the 28 UU radius capsule clears every building box, and the ceiling is >= 108.
- Emit specs at the 2-3 kept sizes.
- Lean conservative (wrong specs mean stuck NPCs); keep an Advent-style pilot ROUTETEST.
- A rebuild takes seconds.

### Route B: write the .un2 package directly
Possible; readers exist (e.g. [UELib](https://github.com/EliotVU/Unreal-Library)). Writing means new name/import/export entries and the exact tagged-property format of this licensee version: days of work and a risk of silently corrupt maps. Only if Route A's flag check fails.

### Route C: native, inside the game process
- Our d3d8 wrapper / dinput8 proxy already run in the game, and Engine.dll exports the path builder:
  - `?definePaths@FPathBuilder@@QAEXPAVULevel@@@Z` (ordinal 4986);
  - `?defineChangedPaths@...` (4984);
  - `UReachSpec::defineFor`.
- A native helper could call `defineChangedPaths` in game after a GM terrain edit, or append `UReachSpec` objects to PathList (a TArray at NavigationPoint+0x3a0).
- Risks: it must run on the game thread, a mistake crashes the game, and `GIsEditor` is 0 outside the editor (a different walk step).
- The fallback if script-level dynamics aren't enough.

---

## 3. A runtime alternative: our own navigation in UnrealScript

### How U2's AI asks for paths
- **The natives are `final`** (Controller.uc:366-556) and can't be overridden:
  - path search: `FindPathToActor`, `FindPathToPoint`, `FindPathTowardNearest`, `FindRandomDest`;
  - checks: `PointReachable` / `ActorReachable` (max distance^2 1.44e6), `FindCoverSpot`;
  - movement: `MoveToActor` / `MoveToPoint`, with `RouteCache[16]`.
- **The script wrappers can be overridden**, mostly in `U2NPCControllerShared`: `GetPathToActor` (:2060), `GetPathTo` (:2075), `GetMoveTargetFollow` (:2142), `FindBestPathToward` (:2461), and Basic's `FindAlternativeClosePath` (:2434). The states then call `MoveToActor(MoveTarget, ...)` or `MoveToPoint(Destination, ...)`.
- **Native-only callers** stay on the engine graph: the ScriptControllerBase patrol (:4001), `PawnProxyPathing`, and `GetNearbyPathNodes` (walks `NavigationPointList`).
- **Class chain:** AIController -> U2NPCController -> Scriptable -> Shared -> Base -> Basic -> Advanced -> Bot. No mixins: one small subclass per controller class we use (e.g. Basic and Advanced), each forwarding to a shared `NavHelper`.
- **Assigning the subclass:** our map can set `ControllerClass=` on the Avalon pawns; on stock maps a mutator swaps `ControllerClass` before the pawn spawns its controller.
- **Driving stock movement:** the override returns the next waypoint as an Actor (a pooled, hidden, non-colliding `NavWaypoint`, an Info subclass, moved along our path). The existing `MoveToActor(MoveTarget)` walks there; `MoveToPoint` already does basic wall-adjust (`PickWallAdjust`).

### Cheapest dynamics: levers that need no new graph
- Script-writable in U2, and read by the native search:
  - `ReachSpec.DisabledCount` ("if > 0 reachspec can't be used currently");
  - `ReachSpec.ExtraCost`;
  - `NavigationPoint.ExtraCost`, `bBlocked`, `cost`.
- Script can't add or remove specs (PathList is const).
- **The plan:**
  1. Python writes an unpruned **superset** graph: every plausible pair, the ones failing today with `DisabledCount=1`.
  2. After a GM terrain edit, a script `NavRepair` re-checks only the specs whose segment crosses the edited tiles: downward `Trace` every 64 UU, rises <= 35, walkable slope, `FastTrace` at knee and head height.
  3. It sets DisabledCount to 0 or 1, and ExtraCost for steep-but-walkable slopes.
- Tens of specs per edit: microseconds to a few milliseconds, no editor round trip.
- **Prior art:** KF2 does the same with path costs in UE3 (cost 100,000 makes zeds ignore a node; closing bollards, [Tripwire KF2 custom Kismet](https://tripwireinteractive.atlassian.net/wiki/x/AQC0K)). The Advent chat tested the same levers in its ROUTETEST.
- **Check first:** that traces see the new terrain after the fork's live `CalcVertices` edit, not just the rendered mesh.

### Full own navigation (only if the above falls short)
- **Data:** Python writes a coarse grid (512 UU heightmap cells, ~1,500 walkable on Avalon) or a staggered graph of ~400 nodes, with per-edge cost and flags.
- **Loading:** script can't read arbitrary files: a `perobjectconfig` ini section (like AvalonSet and U2GM `Draws[]`) or a generated `.uc` with defaultproperties.
- **Search:** A* with a binary heap, spread over ticks.
  - Core.dll stops any script loop at **1,000,000 iterations** ("Runaway loop detected"); the counter is shared and resets each tick ([Runtime problems](https://unrealarchive.org/wikis/unreal-wiki/Runtime_problems.html)).
  - UnrealScript is often quoted as about 20x slower than C++; one informal benchmark gives 1/7 to 1/40 ([lua-users: Lua vs UnrealScript](https://lua-users.org/wiki/LuaVersusUnrealScript)).
  - Budget a few thousand edge relaxations per tick across all NPCs: a ~400-node path in 1-3 ticks. **Measure with the pilot harness first.**
- **Many NPCs, one goal:** a flow field (one Dijkstra from the player's cell every ~0.5 s; each NPC reads its cell's arrow) ([Emerson, Flow Field Tiles, Game AI Pro](https://www.taylorfrancis.com/books/9780429100277/chapters/10.1201/b16725-29)).
- **Big maps:** HPA* (clusters with precomputed crossing costs; refresh only touched clusters) ([Botea, Muller & Schaeffer 2004](https://webdocs.cs.ualberta.ca/~mmueller/ps/hpastar.pdf)).
- **Live edits:** the GM brush knows its rectangle: re-sample those cells with traces, recompute walk/slope flags, dirty only the affected edges or clusters.
- **Local steering:** `MoveTo` / `MoveToActor` toward the next waypoint plus a separation push ([Reynolds steering](https://www.red3d.com/cwr/steer/)).
- **Prior art:** UT2004, Killing Floor 1 and Red Orchestra all used the engine graph; no public UnrealScript navmesh mod found. Closest: Pogamut, which built UT2004 navmeshes outside the game with Recast and drove bots from Java ([post](https://pogamut.cuni.cz/main/tiki-print_blog_post.php?postId=52), [earlier](https://pogamut.cuni.cz/main/tiki-print_blog_post.php?postId=46), [Recast/Detour](https://github.com/recastnavigation/recastnavigation); planner: Floyd-Warshall, [slides](https://diana.ms.mff.cuni.cz/pogamut_files/lectures/2015-2016/Pogamut_3-2016-Lecture-05-Slides-Navigation.pdf)).
- **Cost:** 1-2 weeks to make robust (stuck detection, doors, Mantas, ladders, native-only callers), and it duplicates what the engine does well once the graph is sparse.

---

## 4. Recommendation

1. **Try first (about 2 h):**
   - `pathnodes.py layout=stagger spacing=1100 cover=0`: keep door, corner, ramp and high nodes; drop the 251 cover nodes;
   - PathSizes on TutA_Remake's LevelInfo set to the 2-3 sizes of Avalon's NPCs;
   - PATHS DEFINE again (expect under 1 minute instead of 25+), then a pilot route test.
2. **Next (about half a day):** `PATHS DEFINECHANGED` through U2EdBridge when GM terrain edits are committed (nudge the nodes in the edited rectangle first so they get `bPathsChanged`), in `gm_commit.py`.
3. **Bigger plan (2-4 days, dynamic, no editor):**
   - the 15-minute T3D ReachSpec test (Route A);
   - if it passes, `pathspecs.py` computes specs from our heightmap and building boxes, and PATHS DEFINE is never needed again;
   - Python writes an unpruned superset graph;
   - a script `NavRepair` in U2GM toggles `DisabledCount` / `ExtraCost` on the specs crossing each `gm terrainline` or brush edit.
4. **Only if that falls short (1-2 weeks):** our own UnrealScript grid / HPA* / flow-field navigator through controller subclasses (section 3), the sparse engine graph kept for native-only callers; Route C in reserve.

## Local evidence index
- **Editor:** `Exec_Paths` 10253d40, `ULevelFactory::FactoryCreateText` 10247a30, `ImportProperties` 10268b40.
- **Engine:** `definePaths` 103d4d20, `defineChangedPaths` 103d5590, `addReachSpecs` 103ccc00, `ProscribedPathTo` 103cbf90, `defineFor` 103f3e90, `findBestReachable` 103f3c00, `TestReach` 103f3af0, `PlaceScout` 103f3880, `actorReachable` 103de9d0, `walkReachable` 103ddd70, `PrunePaths` 103ce7a0, `FindAlternatePath` 103cc780.
- **Constants:**

  | Value | Location | Meaning |
  |---|---|---|
  | 1440000.0 | Engine.dll 0x1051ed18 | 1200 UU limit, squared |
  | 56.0 | Engine.dll 0x1052c1b8 | "too close" warning |
  | 1.2 | Engine.dll 0x1052c078 | prune factor |
  | 1000000 | Core.dll | runaway-loop limit |

- **Script:** ReachSpec / NavigationPoint / Scout source in `System\Engine.u`; `u2_export\full_Engine\Classes\LevelInfo.uc` lines 250 and 582-590 (PathSizes); `Controller.uc` 366-556; `U2NPCControllerShared.uc` 2060-2475.
