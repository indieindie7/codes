# Directors and Others: L4D AI Director, Halo AI, Alien: Isolation, The Last of Us, Half-Life squads, S.T.A.L.K.E.R. A-Life

Scope: architectures and specific techniques that make enemies feel smart, scary, or well-paced, plus published numbers and rules. Aimed at an encounter director for Advent Rising (UE2, UnrealScript Bot/SquadAI) that already has per-creature fear/anger/pressure/stress.

## Left 4 Dead: Michael Booth, "The AI Systems of Left 4 Dead" (AIIDE 2009)

### Takeaway
The L4D Director is a crude per-survivor "intensity" scalar driving a four-state pacing machine (Build Up, Sustain Peak, Peak Fade, Relax). It changes pacing (frequency), not difficulty (amplitude). Separately, it spawns enemies near the players through "structured unpredictability": randomised intervals and places, filtered by flow distance and visibility. Everything in the slides is cheap to build. The only real infrastructure is a navmesh with per-area flow distance and visibility.

### Cited Findings
**Intensity metric (exact published rules; no numeric gains or decay rates are published):**
- Each survivor's intensity is a single value. It rises when the survivor is injured by Infected (proportional to damage taken), is incapacitated, or is pulled or pushed off a ledge by Infected. It also rises when a nearby Infected dies, inversely proportional to distance. — [Booth, AIIDE 2009 slides (Valve)](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Intensity decays toward zero over time, but does NOT decay while Infected are actively engaging that survivor. The director tracks the maximum intensity across all 4 survivors. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Algorithm as published: "If intensity is too high, remove major threats for awhile. Otherwise, create an interesting population of threats." — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)

**Pacing state machine (published numbers):**
- **Build Up:** full threat population until survivor intensity crosses the peak threshold. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Sustain Peak:** keep the full threat population for 3–5 s after intensity peaks, which guarantees a minimum build-up duration. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Peak Fade:** switch to the minimal population and wait until intensity decays out of the peak range. This lets the current fight play out without using up the Relax period: "Peak Fade won't allow the Relax period to start until a natural break in the action occurs." — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Relax:** minimal population for 30–45 s, or until the survivors have travelled far enough toward the next safe room. Then Build Up resumes. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Full population means wanderers, mobs, and specials. Minimal population means no wanderers until the team is "calm", no mobs, and no new specials (existing specials may still attack). — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Boss encounters are NOT modulated by pacing, because "overall pacing affected too much if they are missing" and bosses are meant to change up the pacing anyway. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- "Algorithm adjusts pacing, not difficulty: amplitude (difficulty) is not changed, frequency (pacing) is." Also: "Survivor Intensity estimation is crude, yet the resulting pacing works." — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- The inspiration was Counter-Strike's "spiky" pacing: constant combat is fatiguing, and long inactivity is boring. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)

**Spawning and population ("structured unpredictability"):**
- Tools used:
  - Navigation mesh.
  - **Flow distance:** travel distance from the start safe room to each nav area. It answers "is this spot ahead of or behind the group".
  - **Escape route:** shortest path from start to exit.
  - **Potentially visible areas:** areas any survivor could see.
  - **Active Area Set (AAS):** nav areas around the team. Population is created and destroyed as the AAS moves, so a small pool of reused entities stands in for hundreds of enemies.
  — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Population is "not purely random, nor deterministically uniform". It is a superposition of population functions with designer-set randomisation in space and time. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Wanderers:** a count N per area, set at map (re)start from escape-route length and desired density. N enemies are created when an area enters the AAS. They are deleted (and N incremented) when the area leaves the AAS or a mob needs members. N is zeroed when the area becomes visible to any survivor, or when the Director is in Relax. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Mobs:** 20–30 common Infected, spawned at random intervals of 90–180 s on Normal. Boomer vomit forces a mob spawn and resets the interval. Mob size grows from a minimum just after a spawn to a maximum over time, so frequent successive mobs stay balanced. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Special Infected:** each spawns on its own random interval, in an AAS area not visible to survivors and suited to its class. Boomers spawn ahead (they are slow). Smokers prefer areas above the team. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Spawn-location sets:**
  - Behind: AAS areas at or behind the team's flow distance. 75% of mobs come from behind, because wanderers, specials, and bosses are usually met ahead.
  - Ahead.
  - Near the boomer-vomit victim.
  - Anywhere: the fallback.
  — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Bosses:** placed every N units along the escape route, plus or minus a random amount, at map start. Tank, Witch, and Nothing are "shuffled and dealt", and the same boss never comes twice in a row. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- **Weapon caches and items:** designers place many candidate spots and the Director picks which exist. Designer placement keeps visual storytelling and correct props, and predictable possible locations help players. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Why procedural: players memorise static spawns, and even multiple sets of scripted triggers get learned ("if they don't see A, they prepare for B or C"). — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)

**Actor architecture (also in the talk):**
- Each actor has Locomotion, Body (animation), Vision (LOS, FOV, recognised set), and Intention components. Intention holds concurrent Behaviors, each managing an Action stack (hierarchical FSM plus stack). — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Actions return transitions: `Continue`, `ChangeTo(next, "reason")`, `SuspendFor(next, "reason")`, `Done("reason")`. Reason strings are used for debug output. Events (OnInjured, OnSight, OnSound, OnOtherKilled…) go to the innermost action first, then to buried actions, then to the parent. Contextual queries (ShouldHurry, SelectMoreDangerousThreat) propagate the same way. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- Movement uses "reactive path following": steer toward a look-ahead point on the path, with local avoidance. This is cheap to repath and fluid. Common Infected climb algorithmically, using a hull-trace sequence and picking the nearest of dozens of mocap climb heights. — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- SurvivorBot "fairness cheats":
  - They cannot deal friendly fire.
  - They never use Molotovs.
  - They are teleported back near the team when far out of place and no human is looking.
  — [Booth 2009](https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf)
- L4D2 exposes the tempo cycle to modders as director script keys such as SustainPeakMinTime, RelaxMinInterval, and IntensityRelaxThreshold, cycling BUILD_UP → SUSTAIN_PEAK → RELAX. This comes from a search snippet; I could not load the page itself (bot wall). — [VDC L4D2 Director Scripts](https://developer.valvesoftware.com/wiki/Zh/Left_4_Dead_2/Scripting/Director_Scripts)

### Inferences
- Advent already has per-creature stress, but L4D's metric is per-player and measures what happened TO the player (damage, downs, nearby kills, scaled by distance). An Advent director should keep a player-side intensity built from damage taken, nearby kills (1/distance), and grabs or knockdowns. Decay should hold while any enemy is "engaging", meaning it has the player as its enemy and line of sight.
- The four tempo states map directly onto UnrealScript `state`s in a GameRules or Info actor ticking at 1–4 Hz. Good starting values from the talk: Sustain Peak 3–5 s, Relax 30–45 s, wave interval 90–180 s, and roughly 75% of waves arriving from behind.
- UE2 lacks flow distance. A cheap substitute is a Dijkstra over PathNodes from the level start, run once at map load and stored per NavigationPoint. "Not visible" can be a FastTrace check from each candidate node to the player's eyes.
- Keep scripted set pieces (bosses) outside the pacing control, as Valve did.

### Gaps
- No published intensity gain constants, decay rate, or "peak threshold" value. The slides give only the rules. Shipped cvar defaults are on the VDC cvar list, which was blocked (403 / bot check) during this research.

## Halo (Bungie): Butcher & Griesemer 2002, Isla 2005 (Halo 2), Isla 2008 (Halo 3 Objectives)

### Takeaway
Halo splits work into a 3-minute design scope (territories, tasks, encounter flow) and a 30-second code scope (individual decisions). Halo 2 uses a priority-list behaviour DAG with binary relevancy, impulses, transient stimulus behaviours (for example, flee when the leader dies), and inherited character parameters. Halo 3 replaced designer-built FSMs with a declarative tree of prioritised tasks with capacities. Squads "plinko" down into tasks through a greedy cost-function assignment. Fear and leader-death breaking are explicit, exaggerated, and communicated through dialogue.

### Cited Findings
**Halo 1: "The Illusion of Intelligence" (Butcher & Griesemer, GDC 2002):**
- Design owns the "3 minute scope": racial personalities and strategic purpose. Code owns the "30 second scope": intelligent decisions and instant reactions. — [Butcher & Griesemer slides](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Design goals:
  - Enemies should be "Impressed" (surprise, anger, awe), "Fooled" (limited knowledge, predictable reactions), and "Thwarted".
  - Being thwarted means reaching a breaking point: "Flee in Terror, Berserk, Retreat, Defensive State".
  - Discarded ideas: randomness, a "fuzzy" emotion system, and hidden states.
  — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Unpredictability comes from emergent cause-and-effect stimuli (discovery, weapon fire, damage, death) and "analog reactions" in position and timing, not from dice. — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Knowledge model:
  - Individual "real" perception (vision, hearing, touch, "ESP"), with no cheating.
  - Selective memory and persistent state, so enemies "can be fooled".
  - Intent is communicated through language, posture, gesture, and focus of attention.
  — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Budget: 20–25 actors, 2–4 vehicles, about 15% of Xbox CPU. — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Playtest data, "Tougher = Smarter":
  - Weak-enemy test: 8% rated the AI "very intelligent".
  - Tough-enemy test: 43% rated it "very intelligent", and 92% found difficulty "about right".
  — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Decision logic: "Enemies cause alert", there is an innate combat cycle, and behaviours are activated by stimuli (charge, flee, seek cover, grenade, enter vehicle, check dead body). Each race has its own black box: "Grunts flee easily, Elites seek cover if hurt, Jackals carry shields". — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- **Firing points:** "This is my goal. Where should I be standing?" Discrete points are weighted by LOS, distance to target, proximity of cover, friends and enemies, vehicles, and grenades, and the environment is sensed by multiple ray casts. — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- **Combat dialogue:** generated from decisions and stimuli, filtered by priority, context, uniqueness, and relevance. Nearby characters can reply. Counts: 57 events, 166 dialogue types, 12 speakers, 5147 lines. — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Level-design rules: territories with killing zones, attacking and defending states, retreat conditions, and defensive fortification. Avoid subtlety and "looking broken". — [Butcher & Griesemer](https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf)
- Grunt fleeing on Elite death had to be made unmissable. Players did not notice it at first, so by ship every grunt fled every time an Elite died, with exaggerated panic runs. This is a secondary source (a lecture summarising the talk). — [Sturtevant, DU lecture](https://www.cs.du.edu/~sturtevant/s13-ai/lecture2.pdf); the contemporaneous Bungie update says grunts "lose their nerve" once the Elite dies and shout warnings to allies — [Bungie Weekly Update via Halopedia](https://www.halopedia.org/Bungie_Weekly_Update/03-16-01)

**Halo 2: "Handling Complexity in the Halo 2 AI" (Damian Isla, GDC 2005):**
- The core is a behaviour DAG of about 50 behaviours. Combat parents have 10–20 children. Total use is about 115 behaviours across about 30 character types, running at 30 Hz or more. — [Isla 2005, Gamasutra](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- Relevancy is binary, not float desire, because Isla found float tuning unscalable beyond 2–3 options. Decision schemes are prioritized-list (most common), sequential, sequential-looping, probabilistic, and one-off. Higher priorities can interrupt. — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Impulses:** lightweight priority-list entries that point to a behaviour elsewhere in the tree, for example `player_in_vehicle_impulse` placed above `fight_behavior`. — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Stimulus behaviours:** event handlers insert a behaviour into the tree for a short window (1–2 s in Halo 2). For example, an "actor died" event adds `flee_because_leader_died`, which checks whether the dead actor was a leader and whether other leaders are nearby. Because it sits in the tree, higher-priority behaviours still win. — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Self-preservation:** a set of impulses under engage, triggered by damage or a "scary enemy". Grunts carry unusually many retreat impulses. The article describes no separate fear meter. — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Behaviour tagging:** a bitvector (vehicle status, alertness) prefilters behaviours before relevancy checks. Passengers have no flee, self-preservation, or search branches. — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Memory:**
  - Per-target "props" store the actor's belief (last seen position), which can diverge from the truth, so actors can be fooled or surprised.
  - Per-behaviour short-term memory comes from small depth-indexed pools: 100 actors × 64 B × 4 layers ≈ 25 KB, versus about 192 KB naive.
  — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Designer control:**
  - Firing positions are designer-placed.
  - Orders group firing positions per squad and transition on triggers such as "x or more squad members killed".
  - Styles allow or disallow behaviours: defensive (no charge or search), aggressive (no self-preservation), noncombatant.
  — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)
- **Character files inherit parameter blocks** from parents (white Elite inherits from red Elite). This avoids about 10,350 hand-set numbers. — [Isla 2005](https://www.gamedeveloper.com/programming/gdc-2005-proceeding-handling-complexity-in-the-i-halo-2-i-ai)

**Halo 3: "Building a Better Battle: The Halo 3 AI Objectives System" (Isla, GDC 2008):**
- Canonical encounter, a two-stage fallback: enemies hold a territory, are pushed to a fallback point, then to a last-stand point, then the player "breaks" them and finishes them off. Add "spice" (snipers, turrets, dropships). — [Isla, Halo 3 slides (WPI mirror)](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- The control stack runs Encounter (mission script) → Task (designer) → Squad → individual. Within the task, the AI behaves autonomously. — [Isla Halo 3](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- Halo 2's "imperative" designer FSMs (transitions like "<75% alive?") have n² transition complexity. Halo 3 is "declarative": enumerate "tasks that need doing" and let the system decide who performs them. — [Isla Halo 3](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- **Structure:** a tree of prioritised, self-describing tasks, each with priority, activation script fragments, and capacity. Squads are poured in at the top and filter down. Higher tasks activating pull squads up, and deactivating tasks push them down ("a plinko machine"). Example: generator task with forward (>75% alive), fallback (>50%), and laststand, each with max 10. — [Isla Halo 3](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- **Assignment:** respect capacities (bin packing, NP-hard) while minimising cost H(s,t) with a greedy loop that repeatedly picks the min-cost (squad, task) pair that fits. H covers travel distance, coordination, tree balance, and nearness to the player. The cost is O(n²m), with n and m small. Cache H and timeslice. Warning from the slides: "AI can look really stupid with wrong H". — [Isla Halo 3](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- **Refinements:**
  - Filters restrict who may occupy a task (character type, in or out of a vehicle, sniper). They are implemented as infinite H.
  - Tasks can latch on or off.
  - Tasks can be "exhausted" by death or living count.
  - Assignment can be one-time.
  — [Isla Halo 3](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- **Leadership case study:** core tasks use a "leader" filter and peripheral tasks a "NO leader" filter. When the leader dies, the task enters a "broken" state that allows no redistribution in or out, and NPCs play "broken" behaviours. "Leader death 'breaks' followers." — [Isla Halo 3](https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf)
- **Isla at Develop 2008:**
  - "30 seconds of fun" is AI-driven.
  - Territory lets the player read risk.
  - Grid-based cover choices are outside the player's line of sight.
  - "Each AI has an internal model of each target, and that model can be wrong."
  - "Good mistakes" give the player a window. Example: a Hunter's missed melee has a long recovery that allows flanking.
  — [Gamasutra report, 2008](https://gamedeveloper.com/game-platforms/in-depth-bungie-on-eight-years-of-i-halo-i-ai)

### Inferences
- Advent's per-creature fear can drive Halo-style "breaking points" (flee in terror, berserk, retreat, defensive). The Halo lesson is to make the trigger discrete and legible: leader death leads to every follower breaking, with a bark and an exaggerated run. A smooth fear value that players never notice is the failure mode Bungie hit first.
- The Halo 3 Objectives system maps naturally onto UE2 SquadAI. A small UnrealScript "task" actor would hold priority, capacity, an activation condition (alive fraction, flag, player position), and a set of PathNodes or volumes as the territory. A director picks squad → task with a greedy cost loop. With fewer than 10 squads this is trivially cheap.
- Stimulus behaviours with a 1–2 s window are a cheap fit for UnrealScript events (`NotifyKilled`, `TakeDamage`, `HearNoise`): set a timed flag that the decision function checks at high priority.

### Gaps
- The full text of the Halo 1 talk proceedings (beyond the slides) was not found. Exact fear thresholds for grunts were never published. No public Halo AI source code exists.

## Alien: Isolation (Creative Assembly): two-layer director + behaviour tree

### Takeaway
A macro "director" always knows where the player is. It manages a menace gauge and only gives the alien vague hints. The alien's large behaviour tree (100+ nodes) must find the player with its own senses. When menace peaks or stays high too long, the director sends the alien "backstage" into the vents. Behaviours unlock over the campaign, mostly in response to the player's repeated escape methods, which produces apparent learning. The primary developer talk is Andy Bray's nucl.ai 2016 talk; most details here come from Tommy Thompson's analyses, including config files exposed by modding tools.

### Cited Findings
- The goal was "psychopathic serendipity", where the alien always seems to be in the right place. It is unscripted, unkillable, and kills in one hit. — [Thompson 2017, Game Developer](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation) (cites Andy Bray, "It's in the Vents", nucl.ai 2016, and Q&A with Bray)
- **Menace inputs:**
  - The alien is within a short walking distance.
  - The player has line of sight to the alien.
  - The alien is close on the motion tracker and could reach the player quickly. If it is in another room, menace rises more slowly.
  
  At peak menace, the director sends the alien to neighbouring areas or into the vents. — [Thompson 2017](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation)
- **Director hints:** the director periodically sends the alien toward the player's general area, never the exact position. Task priority determines whether the alien finishes its current action, blends, or interrupts. — [Thompson 2017](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation)
- **Front stage and backstage:** "Front stage" is active sweeping or searching. "Backstage" is entered when menace stays at peak too long. In backstage the alien uses vents, preferring ones ahead of where the player is heading. — [Thompson 2017](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation)
- **Behaviour tree:** 100+ nodes with about 30 top-level selectors (36 root branches per the 2020 config dump). Behaviours start locked and unlock as the player meets conditions. Unlocks are NOT driven by player deaths, to avoid unfairness. Fallback triggers unlock them at set campaign points. — [Thompson 2017](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation); [Thompson 2020](https://www.gamedeveloper.com/design/revisiting-the-ai-of-alien-isolation)
- **Learning examples:**
  - Locker searching and crawling into smaller vents unlock only after the player has escaped that way several times.
  - Flamethrower use is recorded, and later encounters change tactics (hissing, vent ambush, flanking).
  — [Thompson 2020](https://www.gamedeveloper.com/design/revisiting-the-ai-of-alien-isolation)
- **Senses (from configs exposed by the OpenCAGE tools):**
  - **Vision:** four view cones (normal, focussed, peripheral, close). Signal strength accumulates while the player stays in a cone.
  - **Hearing:** sounds have strength levels against thresholds. Gunfire triggers much faster than footsteps. Loud sounds make the alien run and can pull it out of backstage.
  - **Touch:** bumps and damage.
  - Flashlights trigger faster.
  - All detections decay, so the alien forgets.
  - **Attack condition:** vision or touch reaches full confidence, or certain sensors fire while the player is in a crawlspace.
  — [Thompson 2020](https://www.gamedeveloper.com/design/revisiting-the-ai-of-alien-isolation)
- **Search pattern:** areas of interest are hand-placed or generated from noise. The alien visits a nearby perimeter in a deliberately sub-optimal order, prioritised by visibility, so it backtracks and looks doubtful. "Search" points are walked to, and "spot" points are looked at from afar. Designers can mark places it never checks. — [Thompson 2017](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation)
- **Stalking and front-stage tuning:**
  - Stalking disables the urge to withdraw.
  - The stalk radius shrinks each pass, in a donut around objectives so the alien doesn't stand on them.
  - Front-stage sweeps have designer duration ranges, confined near the vent it emerged from.
  - Menace parameters include cooldowns, time-to-peak, and the number of menaces allowed per front-stage sequence.
  — [Thompson 2020](https://www.gamedeveloper.com/design/revisiting-the-ai-of-alien-isolation)
- **Difficulty:** Novice cuts vision and movement-sound responsiveness by over a third. Higher difficulty shortens backstage time and extends menace durations. At least 12 alien configurations exist. — [Thompson 2020](https://www.gamedeveloper.com/design/revisiting-the-ai-of-alien-isolation)
- **No cheating:** per Bray, the alien teleported only twice in the 12–18 h campaign, both for cutscenes. A short ray trace behind the alien prevents players sneaking up directly behind it. The motion tracker senses within about 1.5 m. — [Thompson 2017](https://www.gamedeveloper.com/design/the-perfect-organism-the-ai-of-alien-isolation)

### Inferences
- Menace is effectively L4D intensity computed from proximity and visibility instead of damage. That is the right metric for stealth or horror creatures in Advent, where the threat should build before any hit lands.
- "Director knows, creature guesses" is cheap in UE2. The director writes an approximate target location (player position plus a random offset of a few metres, refreshed every N seconds) into the creature's controller as an investigate point. The creature's own `SeePawn`/`HearNoise` then has to confirm it.
- Backstage maps to "go to a hidden PathNode or volume and stop being visible or audible". Unlocks map to per-save counters (for example, "times escaped by hiding in X") that enable branches.

### Gaps
- I did not obtain Andy Bray's nucl.ai 2016 slides or video directly. Menace numbers (rates, thresholds, cooldowns) are not published. The 2020 details come from config files and are hedged by the author ("as near as I can tell").

## The Last of Us (Naughty Dog): human enemy perception, search, and coordination; Infected hearing

### Takeaway
Perception uses a distance-dependent vision cone (wider when close) with an accumulate-and-decay sighting timer of about 1–2 s, and a single raycast point that favours the player in stealth. The AI shares a last-known position but never cheats on knowledge. Search uses a diffusing occupancy grid cleared by NPC visibility. A global Combat Coordinator hands out roles (one OpportunisticShooter, one ideal Flanker), which keeps lethality high without everyone shooting. Infected use designer "logical sounds" with per-type hearing multipliers, occlusion rays, and a movement-noise radius that scales with player speed.

### Cited Findings
**Navigation and spatial maps:**
- Navigation uses coarse navmeshes plus a per-NPC 2D grid with rasterised blockers. The budget is 20–40 navmesh pathfinds per frame in about 4 ms SPU time, and 1 grid pathfind per frame. — [McIntosh, "Human Enemy AI in The Last of Us", Game AI Pro 2 ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Exposure map:** a 2D bitmap on the navmesh (1 = visible from the player, 0 = occluded). It is computed with integer 360° raycasts over an 8-bit height map embedded in each navmesh, taking about 2–3 ms SPU spread over frames. It is used as a pathfinding cost so NPCs take less exposed routes. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Vision and awareness:**
- A plain frustum failed: players adjacent to NPCs went unseen while far ones were seen. The fix was "the angle of view for an NPC is inversely proportional to distance". — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Sighting timer:** increments each frame the player is seen and decrements when unseen. The player counts as perceived at about 1–2 s for a typical NPC. The threshold is much lower in combat and much higher if the NPC has never perceived the player (stealth). — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Raycast target:** weighted rays to many joints with a 60% threshold were too hard for players to predict. Shipped: a single point at the chest in stealth (player-favouring) and the top of the head in combat. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **No knowledge cheating:** on perception, an NPC creates an entity with location and timestamp and broadcasts it to all NPCs. If nobody perceives the player, the location stays stale. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Combat cycle and pacing cheat:**
- The cycle: the player reveals themselves, NPCs surround and advance, and if the player is unseen for 10 s or more, one NPC approaches to check. If the player is gone, NPCs enter search. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- This took about 2 min in focus tests. The fix: if the player moves more than 5 m from where NPCs believe he is, he counts as having snuck away and an NPC is sent immediately. The cycle dropped to about 30 s. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Posts (cover and positions):**
- Each NPC gathers its 20 nearest cover posts. Up to 160 rays per frame are cast, 4 per cover, and posts with all rays blocked are rejected. "Open posts" are cast around the last known position (LKP) for search approach. Pathfinds to posts are limited to 20 per frame and refresh round-robin in about 0.5 s. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Post selectors:** 17 shipped, in a LISP script. They multiply normalised 0–1 criteria (for example, a distance curve 3 m → 0, 5 m → 1) and the highest product wins. A criterion rejects cover whose path runs toward the player, fixing the "rush forward to take cover" complaint. All selectors are evaluated continuously, so state switches have no delay. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Architecture:**
- **Skills:** a prioritised FSM queried every frame, highest priority wins. Examples: panic, advance, melee, gun combat, hide, investigate, scripted, flank. Each skill has its own sub-FSM and pushes low-level behaviours (MoveToLocation, StandAndShoot, TakeCover) onto a stack. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Stealth and search:**
- A distraction makes NPCs request an "Investigator" role. One NPC walks to an investigation post, plays an animation, then resumes its script. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Search map:** a grid where only the known cell is lit. Once the player is lost, cells "bleed into their neighbours over time", and any cell visible to an NPC (from the exposure map) is cleared each frame. NPCs search the remaining probability mass. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Lethality and roles:**
- Every hit on the player plays a full-body hit reaction that removes control. "It was the loss of control that most affected players." — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Combat Coordinator:** a global object with roles Flanker, Approacher, Investigator, StayUpAndAimer, and OpportunisticShooter, using `RequestRole()`/`AcknowledgeRole()`. Only one NPC needs to shoot at a time. The OpportunisticShooter, if able to see and shoot, instantly blends to shooting even mid-animation. The Flanker role goes to the single best-rated flank path. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)
- **Flanking cost:** exposure-map flanking was unstable frame to frame. The fix was a fixed cost shape centred on the "combat vector", the average NPC position weighted by recent shots. Paths swing wide to the side. — [McIntosh ch.34](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter34_Human_Enemy_AI_in_The_Last_of_Us.pdf)

**Infected (Mark Botta, Game AI Pro 2 ch.33):**
- Infected rely primarily on hearing via designer "logical sound events", not real audio. Each has a designer radius, multiplied per character type and per current behaviour (Infected hear less when unaware). Infected hear about 6× better than humans. Rays from each listener to the source apply partial occlusion. — [Botta, "Infected AI in The Last of Us", Game AI Pro 2 ch.33](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter33_Infected_AI_in_The_Last_of_Us.pdf)
- Player movement-sound radius scales with player speed, so the player can approach fast from afar but must slow down when close. A short-range logical "breathing" sound handles stationary players. Smoke occludes hearing as well as vision, for fun. — [Botta ch.33](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter33_Infected_AI_in_The_Last_of_Us.pdf)
- Infected react to the stimulus itself (a brick's landing spot), not the inferred thrower. On lower difficulty, Clickers turn and bark at nearby stimuli before attacking. The Infected search builds a graph of navmesh points that reveal hiding spots, is non-exhaustive, and gives up back to wander. — [Botta ch.33](http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter33_Infected_AI_in_The_Last_of_Us.pdf)

### Inferences
- The cheapest high-value ports to UnrealScript:
  - The sighting timer with three thresholds (unaware, alert, combat), replacing an instant `SeePlayer`.
  - FOV widening at close range.
  - A shared last-known-position plus timestamp on the squad.
  - The 5 m "snuck away" rule.
  - A role token system on the SquadAI: a max of N shooters and one flanker. This is essentially Half-Life's slots.
- The diffusing search grid can be done on UE2 PathNodes instead of a bitmap: spread a probability value to neighbours every 0.5 s, and zero nodes any NPC can FastTrace to.
- The Infected's speed-scaled noise radius maps to `MakeNoise(loudness)` in UE2, with loudness proportional to `VSize(Velocity)`.

### Gaps
- GDC 2014 video (["The Last of Us: Human Enemy AI", GDC Vault](https://gdcvault.com/play/1020338/The-Last-of-Us-Human)) not reviewed. The Ellie buddy AI chapter (Max Dyckhoff) PDF URL guessed for gameaipro.com returned HTML rather than a PDF, so it was not reviewed. Game AI Pro chapters are free to read, but the book is copyrighted (no code licence).

## Optional: Half-Life 1 squad grunts and S.T.A.L.K.E.R. A-Life

### Takeaway
Half-Life's "smart" grunts are a schedule/condition system plus squad slot tokens: 2 ENGAGE slots and 2 GRENADE slots per squad, with everyone else taking cover. A leader-first-sight suppress order, barks tied to decisions, and a deliberate "enemy eluded" delay give the player time to react. The source is public but under a non-commercial, Valve-games-only SDK licence. STALKER's A-Life is an LOD scheme: full "online" AI within about 150 m, and a cheap "offline" graph simulation with formula combat elsewhere. It is relevant only if Advent needs off-screen persistence.

### Cited Findings
**Half-Life 1 (ValveSoftware/halflife SDK, `dlls/squadmonster.h`, `dlls/hgrunt.cpp`):**
- Squad slots are bit flags:
  - Human grunts: `bits_SLOT_HGRUNT_ENGAGE1/2` (2 shooters) and `bits_SLOT_HGRUNT_GRENADE1/2`.
  - Alien grunts: HORNET1/2 and CHASE.
  - Houndeyes: ATTACK1–3.
  - Global: `SQUAD_SPLIT`.
  - `NUM_SLOTS 11`, `MAX_SQUAD_MEMBERS 5`.
  — [squadmonster.h](https://github.com/ValveSoftware/halflife/blob/master/dlls/squadmonster.h)
- Grunt combat `GetSchedule()` priority order:
  1. Dangerous sound (grenade): "HG_GREN" bark, then take cover from the sound.
  2. Dead enemy.
  3. New enemy: non-leaders take cover; the leader barks and then suppresses or establishes line of fire. On first player encounter the leader plays a hand-signal "SignalSuppress" schedule once (`m_fFirstEncounter`).
  4. No ammo: cover and reload.
  5. Light damage: 90% take cover, about 10% flinch.
  6. Melee kick.
  7. Grenade launcher if the GRENADE slot is free.
  8. Can shoot: take an ENGAGE slot and fire; else grenade if a slot is free; else hide.
  9. Enemy occluded: grenade ("HG_THROW") if a slot is free; else take ENGAGE and move to establish line of fire ("charge"); else stand off and taunt.
  — [hgrunt.cpp](https://github.com/ValveSoftware/halflife/blob/master/dlls/hgrunt.cpp)
- **"Enemy eluded" fairness:** if the squad lost the player and a member re-finds him while he is not facing it, the squad plays `SCHED_GRUNT_FOUND_ENEMY`. A code comment says this is to "waste a little time and give the player a chance to turn". — [hgrunt.cpp](https://github.com/ValveSoftware/halflife/blob/master/dlls/hgrunt.cpp)
- Other details from `hgrunt.cpp`:
  - Range attack requires an unoccluded target, distance ≤ 2048 units, a facing dot ≥ 0.5, and no friendly in the line of fire.
  - The grunt randomly toggles standing or crouching (1 in 10).
  - `HGRUNT_LIMP_HEALTH 20`.
  - Schedules list interrupting conditions (e.g. `bits_COND_LIGHT_DAMAGE | HEAR_SOUND | NEW_ENEMY`).
  — [hgrunt.cpp](https://github.com/ValveSoftware/halflife/blob/master/dlls/hgrunt.cpp)
- **Licence:** "You may … download and use the SDK to develop a modified Valve game running on the Half-Life 1 engine… distribute… but only for free". Commercial use requires contacting Valve. It is not an open-source licence, and copying code into a non-Valve game (such as Advent Rising) is outside its grant. Reimplementing the ideas is fine. — [halflife LICENSE](https://github.com/ValveSoftware/halflife/blob/master/LICENSE)

**S.T.A.L.K.E.R. A-Life (Dmitriy Iassenev interview, AIGameDev/Gamasutra, 12 Mar 2008):**
- **Online mode** is full AI. **Offline mode** is its "level of detail": no animations, sounds, or active inventory, and paths follow a global graph only, without smoothing. — [Iassenev interview](https://www.gamedeveloper.com/game-platforms/interview-inside-the-ai-of-i-s-t-a-l-k-e-r-i-)
- Characters within a radius of the player (usually about 150 m, designer-settable per level) are online, and other levels are fully offline. — [Iassenev interview](https://www.gamedeveloper.com/game-platforms/interview-inside-the-ai-of-i-s-t-a-l-k-e-r-i-)
- **Offline combat** is turn-based, with a formula plus randomness (flee, death, avoidance). Offline stalkers trade, and generated "news" reports offline events the player can hear about. — [Iassenev interview](https://www.gamedeveloper.com/game-platforms/interview-inside-the-ai-of-i-s-t-a-l-k-e-r-i-)
- **Smart terrains** assign goals and destinations, take control of arriving NPCs for a time, and create camps, bases, and migrations. Iassenev regrets having no per-character needs model and weak team AI. — [Iassenev interview](https://www.gamedeveloper.com/game-platforms/interview-inside-the-ai-of-i-s-t-a-l-k-e-r-i-)

### Inferences
- Half-Life's slot tokens are the oldest and cheapest form of TLOU's Combat Coordinator. In UE2 SquadAI they are a bitmask on the squad with `OccupySlot` and `VacateSlot`, and they cap simultaneous shooters and grenadiers. Combined with barks ("HG_THROW", "HG_COVER") at decision points, this is the main cheap source of perceived squad intelligence.
- Advent's existing fear, anger, and stress values could gate slot requests. A high-fear creature never requests ENGAGE, and a high-anger one requests ENGAGE or CHARGE first. That makes the emotion values visible through behaviour, as Halo's lesson requires.
- A-Life-style offline simulation is probably unnecessary for linear Advent levels. The relevant idea is LOD: run full feelings and perception only within a radius of the player or in the current AAS, as L4D does.

### Gaps
- No A-Life update rates or NPC counts were published in the interview. I did not review the X-Ray engine source (the leaked or released versions have unclear licensing).
