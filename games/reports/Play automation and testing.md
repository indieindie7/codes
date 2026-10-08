# Play automation and testing: how studios, researchers and old-engine modders do it, and what U2AutoPlay should do next

*2026-10-07. Three parallel research passes: what studios ship, research agents, practical techniques for old engines. Written for Unreal II's setup:*
- *U2AutoPlay (an UnrealScript bot driving the player's input on the NavigationPoint network);*
- *the U2Pilot harness (background launch, console commands, screenshots, log reading);*
- *live editing (AvalonLive, AvalonEditor).*

## The short version

1. **Studios mostly run scripted bots with good oracles, not clever AI.** Examples: Riot's League bots (about 5,500 checks per build, about 50% of critical bugs caught), Rare's Sea of Thieves (hundreds of thousands of small in-engine tests on every check-in) and Ubisoft's Division "client bots" (mission playthroughs, street wandering for performance). EA puts its reinforcement-learning agents on top of scripted bots, not in place of them. Reliability beats cleverness: wait on conditions instead of fixed sleeps, and hold new tests in staging before trusting them.
2. **The value is in the oracles and the reports** more than in the agent:
   - crash and log-error checks;
   - stuck and fell-out-of-world detectors;
   - a softlock watchdog;
   - position heatmaps with stuck clusters;
   - frame-time logs along fixed routes;
   - golden screenshots.
3. **The cheapest exploration idea that finds real bugs is Go-Explore-style reset-and-explore.** Keep an archive of visited places. Teleport back to rare or frontier places, then move randomly *off* the path network. Microsoft's 3D version found wall-top exploits, falls off the map and getting inside geometry, with 16 agents on one machine. Our bot only walks the path network, so it can't find any of those yet.
4. **Deep RL, Cradle-style pixel agents and trained glitch detectors cost far too much for us.** EA's curiosity agents needed 320 agents for a day. An LLM is useful one level up, as a **supervisor**: when the bot stalls it reads the condensed log and a screenshot, then sends high-level commands (TITAN, 2025: 15 bugs, against 9 for older methods).

## What studios do

| Who | What the bot does | Built how | Lesson for us |
|---|---|---|---|
| EA SEED (Battlefield V/2042, Dead Space) | Coverage, exploits, map difficulty, vehicle navigation | Reinforcement learning added to existing scripted bots; imitation learning from designer demos (about 20 min to train versus about 5 h for RL) | Scripted first; agents add to it. Battlefield V: 601 features, about 300 work-years to test by hand. [EA](https://www.ea.com/seed/news/seed-ml-research-aaa-game-testing), [arXiv 2103.15819](https://arxiv.org/abs/2103.15819) |
| EA curiosity agents (CoG 2021) | Find unreachable or exploitable spots | Novelty reward: a place counts as new more than about 5 m from anywhere visited | Visit heatmaps and **where-episodes-end clusters** pinpoint stuck spots. [arXiv 2103.13798](https://arxiv.org/abs/2103.13798) |
| Ubisoft Reflections, The Division (GDC 2019) | Take over the player, play missions, report; follow-bots; wander for performance data | Scripted client bots | Exactly U2AutoPlay's shape. [80.lv](https://80.lv/articles/gdc-using-ai-controlled-players-to-test-the-division/) |
| Ubisoft La Forge (IJCAI 2021) | Reachability where navmeshes fail (jump pads, grapples) | Deep RL navigation | An agent learned bunny-hopping, a movement exploit. [arXiv 2011.04764](https://arxiv.org/abs/2011.04764) |
| Rare, Sea of Thieves (GDC 2019) | Unit, integration and actor gameplay tests on every check-in | In-engine test framework anyone can write tests in | Small scenario tests, never flaky. [GDC Vault](https://gdcvault.com/play/1026366/Automated-Testing-of-Gameplay-Features) |
| Riot, League (Build Verification System) | Scripted cases send commands and query state | RPC into client and server; polls, never sleeps; a week in staging before a test counts | [Riot](https://www.riotgames.com/en/news/automated-testing-league-legends) |
| King, Candy Crush | Predicts level difficulty | CNN imitating real players' moves | Over 95% fewer manual level tweaks. [CIG 2018](https://www.gwern.net/doc/reinforcement-learning/imitation-learning/2018-gudmundsson.pdf) |
| Supercell (mo.co) | Find overpowered items and exploits before launch | RL bots at scale | Bots converging on one item means rebalance it. [PocketGamer](https://www.pocketgamer.biz/how-moco-used-ai-to-test-the-player-experience) |
| Unreal Gauntlet / Automation | Smoke, content stress (load every map), screenshot comparison | Runs the game from outside and judges from logs | The same design as U2Pilot. [Epic](https://dev.epicgames.com/documentation/en-us/unreal-engine/gauntlet-automation-framework-overview-in-unreal-engine) |
| modl.ai | Overnight exploratory bots report crashes, soft-locks and positions, with video | Plugin on an instrumented build | Replaced 10-hour manual playthroughs with a review. [modl.ai](https://modl.ai/testing-content-heavy-games-with-ai-bots) |

## What the research adds

- **Go-Explore 3D for reachability** (Microsoft, AIIDE 2022, [arXiv 2209.00570](https://arxiv.org/abs/2209.00570)): an archive of 1 m cells, return to rare or unreached navmesh cells, explore from there. It found wall tops, falls off the map, being inside geometry and out of bounds, and beat curiosity RL at far lower cost. The original [Go-Explore](https://arxiv.org/abs/1901.10995) found a scoring bug while trying to win.
- **Procedural personas** (Holmgård et al., [arXiv 1802.06881](https://arxiv.org/abs/1802.06881)): the same bot with different weights (explorer, rusher, fighter, completionist) shows how a level answers different players: skipped content, difficulty spikes.
- **Wuji** (NetEase, ASE 2019): optimise progress *and* novelty together. From 1,349 real bugs, four oracles: crash, stuck, logic and balance.
- **Imitation and replay**: record a human's route, replay it with mutations ("demo plus fuzzing"). Human-like agents matched human testers on 45 seeded bugs ([arXiv 1906.00317](https://arxiv.org/abs/1906.00317)).
- **Visual glitch detection**: CNNs catch about 88% of rendered glitches when trained on generated data. Vision-language models are weak judges alone ([GlitchBench, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Taesiri_GlitchBench_Can_Large_Multimodal_Models_Detect_Video_Game_Glitches_CVPR_2024_paper.html)). Use them to filter, with a human deciding.
- **LLM testers**: [TITAN](https://arxiv.org/abs/2509.22170) works from a condensed state, templated actions, reflection on stalls, and an LLM judge. Voyager and Cradle need a code API, or they're slow and fragile on pixels.

## Old-engine practice

- **UT's own QA**:
  - UnrealEd's **Review Paths** checks that must-reach nodes are reachable and that every mover has a node ([Unreal Wiki](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Bot_Pathing.html)).
  - Polge's method was to watch bots and use **ShowPath/RememberSpot** to find broken links.
  - **SoakBots** freezes the game on an AI error ([Testing Botplay](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Testing_Botplay.html)).
  - UT2004 could run a self-quitting background benchmark: `?spectatoronly ... -benchmark -seconds=77 -exec=`.
- **Demos**:
  - Quake records network state, so its demos never drift, and `timedemo` turns that into a benchmark.
  - Doom records inputs only, so its demos desync on any change.
  - So replay *intents and waypoints* plus a starting save, never raw keys ([Gaffer on Games](https://gafferongames.com/post/floating_point_determinism/)). U2's `demorec` may or may not work: test it.
- **Source engine**: `bot_goto_mark` proves a nav area can be reached. Our equivalent: path from the start to every navpoint and pickup, and log the ones that fail.
- **Script errors in UE2 logs** worth catching: `Accessed None`, `Accessed array out of bounds`, `Failed to load`, `SpawnActor failed`, runaway loops, the GPF/Critical block ([Log Warnings](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Log_Warnings.html)).

## The plan for U2AutoPlay and U2Pilot, in order

| # | Add | Catches | Effort |
|---|---|---|---|
| 1 | **Log triage gate** (Python): buckets for Accessed None, out of bounds, failed to load, spawn failed, runaway loop, GPF, keyed by class.function; a baseline; fail on a new bucket | Script errors, crashes; every later step reports through it | ½ day |
| 2 | **Watchdogs in the bot**: STUCK, FELL (out of world or below kill Z), NOPROGRESS; the harness kills a softlocked run and keeps the last screenshot and position | Stuck spots, holes, softlocks; turns every pilot run into a test | 1 day |
| 3 | **Reachability and trigger audit** (`autoplay audit`): breadth-first search over the path network from PlayerStart, `FindPathToActor` to every navpoint, pickup and trigger, one-way and dead-end clusters, Event/Tag names nobody fires | Unreachable pickups or triggers, broken lifts and doors, remix and generated-map mistakes, with no play needed | 1½ days |
| 4 | **Every-map smoke run**: load each map in the background, wait, screenshot, quit, triage | Missing packages, load crashes, script errors | 1 day |
| 5 | **Go-Explore mode**: a 2-5 m cell archive with visit counts; teleport to rare or frontier cells; 10-30 s of off-path moves (jump, strafe into walls, step off ledges) | Collision holes, wall-top exploits, out-of-bounds routes | 1-2 days |
| 6 | **Heatmaps** (done 2026-10-07: U2Pilot heatmap.py): positions, deaths, STUCK/FELL/NOREACH, and coverage (cells, nodes, edges) over a top-down capture | One picture of where a level is broken; coverage numbers | 1 day |
| 7 | **Golden screenshots and a fixed-route frame-time log**: fixed cameras with HUD and particles off, a tolerant diff against approved baselines; a frame-time CSV per route | Shader and fork regressions (the black-character bug), performance regressions | 2 days |
| 8 | **Personas, demo-plus-fuzz, LLM supervisor**: persona weights; record your play as waypoints and replay with mutations; on stalls an LLM reads the log and a screenshot and sends `autoplay goto` / `avalon` commands | Design-level insight; human routes the path network doesn't know; getting past lifts and scripted steps | 2-3 days |

**Don't**: deep RL agents, a trained glitch CNN, Cradle-style pixel control, true MCTS (UE2 has no fast state snapshots), raw input replay.

**Assert on outcomes, not exact positions**: runs never repeat exactly (frame time, random numbers). Check things like "reached the beat within T, no new error buckets".
