# Horizon Zero Dawn / Forbidden West machine AI (Guerrilla Games)

Source quality key: **[P]** = primary (Guerrilla talk page, slides or speaker notes, developer interview); **[S]** = secondary analysis (mostly Tommy Thompson / AI and Games, which paraphrases the Guerrilla talks). Many of the HZD details reach us only through [S]. The original HZD slides (Beij 2017) are on Guerrilla's site, but 32 of the 35 pages are images with no extractable text. Only the HTN-intro speaker notes (pp. 12-14) could be read.

No code from any of these talks is published. The only "code" anywhere is HTN domain snippets on Verweij's slides. Guerrilla's publication pages give no licence for the slides or the snippets, so treat them as all-rights-reserved reference material: learn the ideas, don't copy code.

---

## 1. Architecture: HTN planner, utility, groups/herds, the Collective, roles, alert states

### Takeaway
Every machine is an HTN-planning agent, and every herd is also an agent: a bodiless "group agent" with its own blackboard that plans role assignments for its members. Above the herds sits a world-level "Collective" that spawns machines and moves them between groups. Attack choice inside the HTN is scored by a utility function. When alerted, a herd re-partitions into "flee" and "combat" subgroups. The planner is the Killzone-era HTN, which since HZD has had a Prolog-like precondition solver and a C++ code generator.

### Cited Findings
**HTN planner (primary)**
- Guerrilla's HTN breaks an abstract task into concrete actions by recursive decomposition. A "method" lists alternative "branches", which are tried in order from top to bottom. Each branch has declarative preconditions (nested and/or/not) plus replacement tasks. A solver searches world-state facts to satisfy the preconditions, binding variables as it goes and backtracking on failure. If no branch works, the planner backtracks up the recursion. Concrete (primitive) tasks are marked with `!`. — [P] [Beij, "The AI of Horizon Zero Dawn" slides, speaker notes pp.12-14](https://www.guerrilla-games.com/media/News/Files/The-AI-of-Horizon-Zero-Dawn.pdf)
- The talk abstract covers Guerrilla's move from level-based tactical shooters to open-world action RPGs: "navigation for agents of different sizes in a dynamic world", combining HTN planning with utility-based decision making, and systems for coordinating groups of agents. Dated 17 Oct 2017 (Game AI North). — [P] [Guerrilla: The AI of Horizon Zero Dawn](https://www.guerrilla-games.com/read/the-ai-of-horizon-zero-dawn)
- Decima's HTN derives from JSHOP2. It uses Lisp-style syntax, e.g. `(call is_effective_against ?w ?e)`. Slide "Decima's HTN vs behavior trees" lists four advantages: reasoning about future state; separation of selection and execution; local variables and task parameters; a flexible world state with powerful queries. The world state is a set of facts queried Prolog-style, such as `(in_fridge ?item)`, which returns multiple bindings. — [P] [Verweij, "From Byrd Box to Debug Boxes" slides (2026), pp.9-12](https://d3d3g8mu99pzk9.cloudfront.net/TimVerweij/Tim%20Verweij%20-%20AI%20and%20Games%20Summer%20School%202026%20-%20From%20Byrd%20Box%20to%20Debug%20Boxes%20-%20HTN%20Introduction%20and%20Application%20in%20DECIMA.pdf); talk page: [Guerrilla read page](https://www.guerrilla-games.com/read/from-byrd-box-to-debug-boxes-htn-introduction-and-application-in-decima)
- An "HTN translator" turns the domain into generated C++. Backtracking is modelled with the Prolog "Byrd box" model (call/exit/redo/fail ports). Debugging inserts logging at choice points and logs variable bindings. Credits: Robert Morcus (HTN translator), Hylke Kleve (first HTN planner), Ricardo Desmedt (VS Code HTN language extension). — [P] [Verweij 2026 slides pp.4,13-16,33-34](https://d3d3g8mu99pzk9.cloudfront.net/TimVerweij/Tim%20Verweij%20-%20AI%20and%20Games%20Summer%20School%202026%20-%20From%20Byrd%20Box%20to%20Debug%20Boxes%20-%20HTN%20Introduction%20and%20Application%20in%20DECIMA.pdf); [Guerrilla: HTN Planning in Decima (AI and Games Conf. 2024)](https://www.guerrilla-games.com/read/htn-planning-in-decima)
- Real domain example from Verweij's slides:
  - The root `(behave)` method has `branch_combat` (if `(enemy ?enemy)` then `do_combat_behavior ?enemy`), followed by `branch_idle`.
  - `do_idle_behavior` picks between two branches. The first is `move_to_grab_resource`, taken if the agent is `(in_role swarm_coordinator resource_collectors ?group resource_collector)` and its `role_context` supplies a resource. The second is `follow_swarm_leader`, taken if `(in_group swarm_coordinator stingspawn_swarm ?swarm_group)` and the group has an `other_member ... leader ?leader`.
  - A leader-side condition checks that no follower is more than 3.0 m away.
  - The point: group membership and roles are just world-state facts that the individual's HTN queries. — [P] [Verweij 2026 slides pp.28-30,36](https://d3d3g8mu99pzk9.cloudfront.net/TimVerweij/Tim%20Verweij%20-%20AI%20and%20Games%20Summer%20School%202026%20-%20From%20Byrd%20Box%20to%20Debug%20Boxes%20-%20HTN%20Introduction%20and%20Application%20in%20DECIMA.pdf)
- HFW machines still "use Hierarchical Task Network (HTN) to decide what to do" (David Speck, Senior AI Programmer). — [P] [Speck, "Building the AI behaviors for flying and swimming machines for HFW", speaker notes slide 8](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx); [talk page](https://www.guerrilla-games.com/read/building-the-ai-behaviors-for-flying-and-swimming-machines-for-horizon-forbidden-west)

**Killzone lineage (primary)**
- Killzone 2 multiplayer bots used three layers. A strategy AI (one per faction) gives orders to squad AIs, which give orders to individual AIs; feedback flows back up. The individual AI uses an HTN planner. Presented by Champandard, Verweij and Straatman at the Paris Game AI Conference, June 2009. — [P] [Killzone 2 Multiplayer Bots (slides)](https://www.slideshare.net/guerrillagames/killzone-2-multiplayer-bots); [Guerrilla: A Hierarchically-Layered Multiplayer Bot System for an FPS (Verweij MSc thesis)](https://www.guerrilla-games.com/read/a-hierarchically-layered-multiplayer-bot-system-for-a-first-person-shooter)
- Verweij joined Guerrilla in 2006 after that thesis. He specialises in "group behaviors and HTN planner technology" and worked on Killzone, HZD and HFW. — [P] [Guerrilla: HTN Planning in Decima](https://www.guerrilla-games.com/read/htn-planning-in-decima)

**Groups, Collective, roles, alert states (secondary; derived from Beij 2017 / Berteling 2018)**
- Each machine is an agent, and each herd is a "group agent" with no physical body. A group agent has a blackboard holding shared data (safe spots, patrol routes) so members don't each recompute it. — [S] [Thompson, "Behind the AI of HZD" Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- The group agent does not update every tick, so there is no instant hive mind. You can kill one machine without the rest instantly knowing. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- Individuals request HTN plans for tasks such as choosing areas to visit, attacking or fleeing. Group agents plan goal and role assignments and can form or dissolve subgroups. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- "The Collective" is a supergroup over all groups and machines. It handles spawning, group membership and transfers, and keeps the ecosystem within performance budget. A lone machine (e.g. a herd survivor) can ask to join an open-world group. Its "passport" (level, machine type) is checked against the group's requirements. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- Herd composition mixes recon, acquisition and combat classes. Acquisition machines (Striders, Grazers) stay in the centre while combat and recon machines patrol the outside. Recon: Watchers and Longlegs scout and alert. Transport: Behemoths and Shell-Walkers. Combat: Sawtooths and Stalkers. Role jobs include patrolling, investigating disturbances, attacking and scavenging. Each role has a cap on how many machines may fill it (numbers not given), and roles can change during play. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- Alert states: herds start "relaxed". Once alerted, the group rebalances into a flee group and a combat group: acquisition machines flee together while combat and recon machines go after the attacker. Most non-herd machines just fight when provoked, and only a few classes run. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- Herd behaviour persists even if you lure one machine away (Hermen Hulst: "an entire ecology which feels natural"). Watchers' "buddies can swarm and overwhelm you", and Scrappers are "really good at flanking and swarming" (David Ford). — [P] [PlayStation Blog, "The Making of HZD's Machines" (2017)](https://blog.playstation.com/2017/02/24/the-making-of-horizon-zero-dawns-machines/)

**Utility (secondary)**
- Attack selection uses a utility score of how "interesting" an attack is. Inputs: the machine's state, whether the player is aware of it, distance to the player, and damage dealt and received. The score is used as a precondition inside the HTN. Thompson likens it to Halo 3. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)

### Inferences
- The design pattern to borrow is **"groups are agents too, and their output is facts"**. A squad or pack object, ticked slowly (e.g. 2-4 Hz), writes facts like `in_role(pack, flanker, me)` or `leader(pack, X)`. Each soldier or hound reads those facts when choosing behaviour. This works without a full HTN: in UnrealScript it is a `PackController` actor plus a role enum on each pawn's controller.
- The slow group tick doubles as a stealth feature, because alarm spreads with a delay and you can pick off stragglers. It is cheap to copy: alert propagation via a timer, not instantly.
- A herd splitting into flee and fight groups maps directly onto Advent: on alert, non-combat aliens (or wounded hounds) flee while soldiers engage.

### Gaps
- The exact alert-state ladder in HZD (relaxed, suspicious, searching, combat, ...) and its numbers were not found in primary text. The HZD slide images could not be machine-read (no PIL/OCR here). They are the best next source; render pp.15-35 and read the diagrams.
- Role caps, group tick rate, and exact utility weights are unknown.
- The [Tim Verweij AI and Games Conference 2024 PPTX](https://d3d3g8mu99pzk9.cloudfront.net/TimVerweij/Tim+Verweij+-+AI+and+Games+Conference+2024+-+HTN+planning+in+DECIMA.pptx) (the longer version) was not read.

---

## 2. Perception, suspicion, investigation, stealth readability

### Takeaway
Perception is a set of per-machine sensors (sight, hearing, radar/proximity, touch) tuned per species. Stimuli are "information packets" attached to objects, so a sensor reads *what* it perceived (a corpse, a missed arrow, the player hidden in grass). Stealth reads to the player through species-specific sensor strength, patrol routes that deliberately pass tall grass, and recon machines whose job is to raise the alarm.

### Cited Findings
- Sensor types: visual (e.g. the Watcher's eye), aural (distant explosions, nearby thrown rocks), radar and proximity (Longlegs), and touch (the player bumping into a machine). Sensitivity is tuned per machine, so Watchers and Grazers are easier to sneak up on than Stalkers. — [S] [Thompson, "Behind the AI of HZD" Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-)
- Every object that can trigger sensors (player, NPCs, rocks, arrows, machines, wildlife) carries an "information packet" describing what it is and its state. This lets a machine tell a dead body from a missed arrow, and handle the player being concealed in long grass or behind trees. Characters interpret the same data differently, and a stronger sensor reads more of the event data. — [S] [Thompson Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-)
- Patrol paths are generated automatically from local geometry. They avoid awkward terrain but deliberately pass near stealth grass so the player can set traps or override machines. Patrolling machines avoid stealth grass, but investigating machines walk through it. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-), [Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-)
- Flying machines' hover mode (strafing, hovering in place) is used "in combat, investigation and search" (HFW). — [P] [Speck deck, notes slide 15](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- HFW's Burrower took over the Watcher's job of alerting other machines to the player, but it tunnels underground. — [P] [Game Developer interview with Zopfi & Fleury (2022)](https://www.gamedeveloper.com/game-platforms/evolving-the-machine-creatures-of-horizon-forbidden-west)
- Scanning (the Focus) is how the player learns weak spots and "behavioural patterns", so perception is legible from the player's side too. — [P] [PlayStation Blog 2017](https://blog.playstation.com/2017/02/24/the-making-of-horizon-zero-dawns-machines/)

### Inferences
- The "information packet" idea is cheap in UE2: give stimulus actors (projectiles, corpses, noise makers) a small struct or class tag, and let each enemy class weight them differently. Hounds react strongly to corpses and scent-like proximity, while soldiers react strongly to sound.
- Placing patrol routes near cover is a level-design trick. It costs nothing and is a big part of why the stealth "reads".

### Gaps
- No primary source found on the **suspicion meter** (fill rates, the yellow-to-red indicator above machines), search pattern logic, or how long investigation lasts. Thompson Pt.2 does not describe a graded suspicion system. The in-game indicator is observable, but its implementation is undocumented in what I found.

---

## 3. Combat engagement: tokens, circling, roles, fleeing, enrage, component damage

### Takeaway
Primary evidence is thin here. Thompson reports that while one machine attacks, the others circle and wait their turn. Larger machines are spread across combat groups with smaller ones supporting. The HFW Speck talk gives the real base loop: **intercept → attack (when the target is inside the attack's trigger volume) → evade if too close → repeat**, with richer behaviour layered on top. Components are designed shoot-off parts; colour coding tells you which are loot and which are weapons or weak points.

### Cited Findings
- While one machine attacks, the others circle the player and wait, which leaves openings: hit the passive one or counter the attacker. Larger machines are distributed across combat groups with smaller machines supporting them. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-). Conflicting primary colour: David Ford warns that Watcher "buddies can swarm and overwhelm you" ([PlayStation Blog](https://blog.playstation.com/2017/02/24/the-making-of-horizon-zero-dawns-machines/)). So the turn-taking is a soft limit, not a hard one-at-a-time rule.
- Base HFW melee loop: "Intercept" (close distance), "Attack" (constantly checks whether an attack is usable; each attack has a trigger volume, and a target inside it means the attack is in range), "Evade" when too close, then repeat. "Actual combat behavior is more complex, but build additive on this loop." — [P] [Speck deck, notes slides 35-36](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- Ranged vs melee: "Most flying machines prefer ranged attacks and turn it into a shooting duel". The Waterwing instead is "melee focused", navigating to positions where it can use melee attacks, and its melee attack doubles as its landing. When the player is underwater (can't fight back, so must flee or hide), the machine should "only want to pretend to be dangerous not necessarily kill player". — [P] [Speck deck, notes slides 42-43](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- Attack telegraphing: each attack has a wind-up that signals it, then a follow-through where damage is dealt. — [S] [Thompson Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-)
- Components: the team planned "multi-layered animals" with parts you can shoot off. Watcher: plating wears down slowly, and the eye is an instant-kill point. Scrapper: many weak points but "not one single critical weak point". Shell-Walkers can be disabled piece by piece. — [P] [PlayStation Blog 2017](https://blog.playstation.com/2017/02/24/the-making-of-horizon-zero-dawns-machines/)
- HFW colour code: "Yellow stands for resources and orange designates parts like weapons or weak points". Some valuable parts are hidden on purpose. For example, the Widemaw's teeth show only after its mouth armour is blasted off or when you shoot into its mouth as it tries to eat you. — [P] [Game Developer, Zopfi & Fleury](https://www.gamedeveloper.com/game-platforms/evolving-the-machine-creatures-of-horizon-forbidden-west)
- Fleeing: in HZD, acquisition machines flee as a group on alert, and only a few non-herd classes run. — [S] [Thompson Pt.1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-)
- Cooperative roles in HFW: the Leaplasher can pin players down for other enemies, and Frostclaws fight alongside human enemies. — [P] [Game Developer, Zopfi & Fleury](https://www.gamedeveloper.com/game-platforms/evolving-the-machine-creatures-of-horizon-forbidden-west)

### Inferences
- For Advent hounds: "intercept / attack-if-in-trigger-volume / evade-if-too-close" plus "one attacks, the others circle" covers 80% of the HZD feel. A pack-level counter of active attackers (an attack token) is the cheap way to enforce the circling.
- Thompson's "utility precondition" (awareness, distance, damage taken) can be a single score function per attack in UnrealScript.
- Component damage in UE2: per-bone hit zones (Advent's gore system already resolves hit bones) that set flags such as `bLostWeapon` or `bLegCrippled`. The behaviour layer reads those flags as preconditions: a crippled hound can't leap, and a soldier who lost his gun switches to melee. This is the "components change behaviour" effect.

### Gaps
- No primary source on **attack tokens / max simultaneous attackers**, circling radius, **enrage** states, or **flee-when-damaged** thresholds for individual machines. Also undocumented: how severing a component rewires the HTN (e.g. removing an attack branch); this is probably just a world-state fact, but that is unconfirmed.
- Hit-reaction / stagger / knockdown logic was not found in any talk read.

---

## 4. Navigation and animation

### Takeaway
Ground: runtime-generated navmeshes only around the player, one per size class. Air: in HZD, hierarchical A* over height-map mip levels; in HFW, a Sparse Voxel Octree shared by air and water. Movement and attacks are animation-driven, with root-motion **warping** so animations land on a moving target.

### Cited Findings
- Navmeshes are generated at runtime only near the player, since AI is only active there. There are six: four land sizes (small, medium, large, extra-large), one for swimmers (e.g. Snapmaw), and one for positioning machines when the player mounts them. Moving obstacles and other machines change the mesh in real time. Small rocks and trees block most machines, but Behemoths, Rockbreakers and Thunderjaws break them, though only when angry or chasing. — [S] [Thompson Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-)
- The Berteling GDC 2018 talk covered going from "one human enemy in tight corridors" to "more than 25 very different characters" in an open world, and reworking navigation and animation for that. — [P] (abstract) [GDC news: Beyond Killzone](https://gdconf.com/news/get-inside-look-ai-driving-horizon-zero-dawn-gdc-2018)
- HZD air navigation (Glinthawk, Stormbird) works as follows:
  - A* runs over 4 mip levels of a height map, starting on the coarsest (level 3), then refining on levels 1 and 0 and smoothing.
  - Flying over obstacles costs more than going around them, so machines glide around mountains.
  - Machines cannot fly under bridges or overhangs.
  - The Stormbird's dive circles the player, then strikes; blocking the sun was kept as a feature. — [S] [Thompson Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-) summarising Josemans, Game AI North 2017
- HFW uses a "Mover" component, which drives animation, clamps to the navmesh and adds code-driven movement. A Ground Mover clamps to the navmesh and an Air Mover is code-driven (velocity/acceleration/displacement), with Hover (helicopter: strafe, hover in place) and Glide (airplane) modes. "Gliding is important to sell animalistic inspiration." — [P] [Speck deck, notes slides 10-16](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- Medium transitions follow a fixed recipe: validate the animation's destination, play the take-off/landing/dive animation, disable clamping, switch Mover on an animation event, and finish the animation in the new nav space. — [P] [Speck deck, slides 12-13, 30, 33](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- HFW 3D navigation uses a Sparse Voxel Octree:
  - Grid cells are 64 x 64 x 64 voxels at 1-2 m per voxel, with a tree per cell; uniform children are pruned, and neighbour links enable pathfinding.
  - It suits mostly empty air and supports overhangs and caves, which fixes HZD's limitation.
  - Underwater is treated as a cave with the water surface as the roof. The same SVO, pathfinding and Mover work underwater; only the animation changes and velocity drops to sell water resistance. Air and water spaces are kept separate.
  - Paths are string-pulled, then Bezier-smoothed. The control point comes from the start velocity, and the result is checked against the SVO; if it fails, the control distance is halved, then the path falls back to a straight line. Plain steering "gave unsatisfactory results (too sharp turns and overshoot)". — [P] [Speck deck, notes slides 17-30](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- **Attack warping (HFW):** the system adds or removes translation and rotation on chosen animation frames so an attack connects even if the target is slightly out of the authored range. It works like this:
  - Track the target during "update" frames, then compute the extra translation needed so the "target frame" (the contact frame) lines up.
  - Spread that translation over "displacement" frames, preferably ones without ground contact, so the adjustment is less obvious.
  - Clamp the warp, and make attack trigger volumes match the warp range.
  - Other uses: landing on a specific spot, jumping navmesh gaps, orientation warping, turning after melee, landing on perch points. — [P] [Speck deck, notes slides 37-41](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- HZD likewise warped root bones by distance and time so starts, transitions, stops and landings come out correct (Thompson compares this to DOOM 2016). — [S] [Thompson Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-)
- A Watcher prototype "immediately felt so real" from animation alone, before it had any AI (Mathijs). — [P] [PlayStation Blog 2017](https://blog.playstation.com/2017/02/24/the-making-of-horizon-zero-dawns-machines/)

### Inferences
- Attack warping is the single highest-value idea for UE2 hounds. During a leap, lerp extra velocity or location toward the target over the airborne frames, clamped, and size the trigger radius to match. Script can do this in `Tick` during the attack state without engine changes.
- UE2 has paths, not navmeshes, and no runtime generation. Size classes can be faked with per-class `CollisionRadius` and reachspec flags. A runtime navmesh is expensive and not worth it.

### Gaps
- Movement prediction (leading the player's position) is not described explicitly beyond tracking the target during warping.

---

## 5. Forbidden West additions

### Takeaway
HFW kept the HZD architecture and added systemic traversal: jumping, climbing, swimming and diving, with medium transitions. It moved 3D navigation to an SVO, added mixed human-plus-machine encounters (riders, handlers), and introduced new cooperative roles.

### Cited Findings
- Arjen Beij (lead AI programmer) said jumping and climbing became "a systemic part" of machine behaviour. The AI looks for shortcuts where it used to take long detours, and amphibious machines jump in and out of water, sometimes combined with an attack. — [S] [TechRadar reporting a PlayStation Blog post](https://www.techradar.com/news/in-horizon-forbidden-west-aloy-is-much-tougher-but-so-are-the-machines) (original PS Blog post not opened)
- Machines move through the environment by jumping, climbing and swimming. — [S] [Press Start on PS Blog dev post (Nov 2021)](https://press-start.com.au/news/playstation/2021/11/09/the-latest-horizon-forbidden-west-developer-blog-is-all-about-its-menacing-machines/)
- Human enemies ride Chargers and Tremortusks or fight alongside Frostclaws. Designers made sure mixed fights still allowed several tactics. The Leaplasher pins the player for others. Returning machines were reworked to avoid overlapping roles (Watcher became Burrower). — [P] [Game Developer: Zopfi & Fleury](https://www.gamedeveloper.com/game-platforms/evolving-the-machine-creatures-of-horizon-forbidden-west)
- Air, water and medium transitions, the SVO and attack warping: see section 4. — [P] [Speck deck](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)
- The Burning Shores DLC (Waterwing) is described as a "semi-aquatic flying robot" that is "extremely aggressive, works in groups ... focusing on relentless melee attacks". The design doc paragraph is the starting point of the behaviour build. The idle behaviour exists "to sell lore/worldbuilding": it hovers and gestures so the player can spot what it is doing. — [P] [Speck deck, slides 5-9, notes slide 33](https://d3d3g8mu99pzk9.cloudfront.net/DavidSpeck/David_Speck+-+AiAndGames+-+FlyingAndSwimmingAI.pptx)

### Inferences
- "The idle exists to show the creature's job" is a cheap and strong lesson. Give Advent hounds a readable idle job (sniffing corpses, guarding a handler) so stealth approaches have something to watch.
- Human handlers with hounds parallel HFW's humans with Frostclaws: a handler can be the "group agent" for its hounds.

### Gaps
- No primary talk on HFW human-enemy AI or on the climbing/jump-link system (how jump/climb opportunities are found or annotated) was found.

---

## 6. Talks / papers index and licences

### Takeaway
Primary HZD/HFW AI material = 1 HZD slide deck (mostly images), 3 Guerrilla talk pages with downloadable decks (Verweij x2, Speck), the Killzone 2 bot talk and thesis, and two developer interviews. The detailed HZD herd and perception content otherwise survives mainly through AI and Games. No code or licence has been released.

### Cited Findings
- Arjen Beij, "The AI of Horizon Zero Dawn", Game AI North, 17 Oct 2017: [page](https://www.guerrilla-games.com/read/the-ai-of-horizon-zero-dawn), [PDF](https://www.guerrilla-games.com/media/News/Files/The-AI-of-Horizon-Zero-Dawn.pdf) (35 pp, mostly image slides). A related 2018 talk by Beij is linked from [CIG 2018 Maastricht](https://project.dke.maastrichtuniversity.nl/cig2018/?p=454) (not viewed).
- Julian Berteling, "Beyond Killzone: Creating New AI Systems for HZD", GDC 2018 AI Summit (navigation and animation): [GDC news](https://gdconf.com/news/get-inside-look-ai-driving-horizon-zero-dawn-gdc-2018). Slides and video not found free; probably on GDC Vault.
- Wouter Josemans, "Putting the AI back into Air: Navigating the Air Space of HZD", Game AI North 2017. Known only via [Thompson Pt.2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-).
- Tim Verweij, "HTN Planning in Decima", AI and Games Conference 2024 (Goldsmiths): [page](https://www.guerrilla-games.com/read/htn-planning-in-decima), [PPTX](https://d3d3g8mu99pzk9.cloudfront.net/TimVerweij/Tim+Verweij+-+AI+and+Games+Conference+2024+-+HTN+planning+in+DECIMA.pptx).
- Tim Verweij, "From Byrd Box to Debug Boxes", AI and Games Summer School 2026 (Leiden): [page](https://www.guerrilla-games.com/read/from-byrd-box-to-debug-boxes-htn-introduction-and-application-in-decima).
- David Speck, "Building the AI behaviors for flying and swimming machines for HFW", talk dated 07/11/2024: [page](https://www.guerrilla-games.com/read/building-the-ai-behaviors-for-flying-and-swimming-machines-for-horizon-forbidden-west). The PPTX is about 737 MB; its speaker notes were read.
- Champandard / Verweij / Straatman, "Killzone 2 Multiplayer Bots", 2009: [slides](https://www.slideshare.net/guerrillagames/killzone-2-multiplayer-bots); [thesis page](https://www.guerrilla-games.com/read/a-hierarchically-layered-multiplayer-bot-system-for-a-first-person-shooter).
- [S] Tommy Thompson, "Behind the AI of Horizon Zero Dawn" [Part 1](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-1-) and [Part 2](https://www.gamedeveloper.com/design/behind-the-ai-of-horizon-zero-dawn-part-2-) (Feb 2019), built from the three talks above. Also [80.lv overview](https://80.lv/articles/an-in-depth-look-at-ai-in-horizon-zero-dawn) (not read).

### Inferences
- Licences: none stated anywhere. Treat all of it as reference only. The HTN snippets are illustrative pseudo-code, not a library.

### Gaps
- No "Killzone 3 AI" talk was checked in this pass.
- The GDC Vault Berteling video was not accessed, and nucl.ai archives were not searched.

---

## 7. Cheap vs expensive to emulate in UE2 (Advent Rising)

### Takeaway
The "alive" feel comes mostly from cheap things: group roles, a slow-ticking group brain, alert propagation with delay, flee and fight splits, per-species sensor tuning, readable idle jobs, and attack warping with wind-up telegraphs. The expensive parts are a full HTN planner with a Prolog solver, runtime navmeshes and SVO 3D navigation, and component-damage art pipelines.

### Cited Findings
- (All cost judgements below are inferences; the facts they rest on are cited in sections 1-5.)

### Inferences
**Cheap (UnrealScript, no engine work):**
1. Pack or squad "group agent" actor with a blackboard (last known player position, safe spots) and role slots (scout / attacker / circler / support) with caps. It ticks at a low rate and assigns roles as properties on each controller.
2. Alert ladder relaxed → alerted → combat, spread by the group agent after a delay. On alert, the group splits into fight and flee groups (e.g. wounded or non-combat aliens flee).
3. Attack token: max N simultaneous attackers per pack. The others circle at a radius (`MoveTo` around the player on a ring) and wait their turn.
4. Per-attack range and trigger check plus a simple utility score (distance, whether the player sees me, damage taken).
5. Intercept / attack / evade base loop for hounds.
6. Attack warping: during the airborne frames of a leap or lunge, nudge `Velocity` or location toward the predicted target, clamped.
7. Stimulus tags on projectiles, noises and corpses, with per-class sensor weights. Scouts get strong sight and hounds get strong proximity or "smell".
8. Patrol routes placed beside cover, and idle animations that show each enemy's job.
9. Component flags from hit bones (lost weapon, crippled leg) feeding behaviour choice.

**Medium:**
- A "Collective" that recycles survivors into other groups and caps active AI for performance.
- A size-class path network (separate path nodes or reachspec flags for large creatures).

**Expensive or not worth it:**
- A real HTN planner with backtracking preconditions. A state machine or utility selector with good group facts gets most of the value.
- Runtime navmesh rebuilds, SVO flight and swim navigation, medium transitions.
- Rich shoot-off component art, plus behaviour branches per lost part on many species.

### Gaps
- No measured performance or cost figures are available from Guerrilla for any of these systems.
