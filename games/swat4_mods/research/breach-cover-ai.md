# Breach, cover and squad AI: research for SwatMinds (SWAT 4 / UE2)

Sources are web search summaries (2026-10-17). Doctrine pages are informal training guides; treat numbers as heuristics. Corner-fed/center-fed and limited-penetration specifics were NOT found by search, so those rows are marked (unverified).

## 1. CQB rules as AI rules

| Rule | Trigger | Action | Comm line |
|---|---|---|---|
| Stack order | Team arrives at a closed door | Officers queue along the wall on the hinge/latch side, #1 nearest door, each facing the side they will cover; rear man watches behind | "Stacked" |
| Fatal funnel | Door opens, room unseen | Nobody stands in the doorway; pass through fast, aim/fire at threats while moving (not stop-then-shoot) | "Moving" |
| Points of domination (POD) | Entry | #1 and #2 take the two room corners on opposite sides, #3/#4 take next free corner or the center | "Corner" / "Left/Right clear" |
| Interlocking sectors | Each officer has a POD | Each gets an overlapping arc; stay in own arc first, then cover neighbor's blind arc | "Mine" / "Yours" |
| Buttonhook vs crossover | Door opens inward, hinge side known | First man turns around the frame and takes the near hard corner; crossover = each takes the far side; slice-the-pie when entry can wait | "Entering" |
| Dynamic vs deliberate | Dynamic: known threat, hostages, time pressure. Deliberate: unknown, no pressure | Dynamic = fast entry with flashbang. Deliberate = slice, mirror, then commit | "Breaching" / "Slicing" |
| Corner-fed vs center-fed (unverified) | Door position relative to room walls | Center-fed: split left/right. Corner-fed: first man takes the long wall, second the short wall behind the door | "Left" / "Right" |
| Overwatch handoff | One officer moves, another has line of sight | Mover announces, overwatch confirms covered, then mover goes; roles swap next leg | "Moving" / "Covered" |
| Threat priority | Several visible hostiles | Armed and aiming at me/teammate > armed > compliant but unsearched > unarmed; hostages and civilians never targeted | "Contact, left" |
| Sector clear | Officer's arc is empty | Call it and turn attention to neighbor's sector or the door | "Clear" |
| Leaving a cleared room | Team must exit through the fatal funnel | Announce before exiting so nobody gets shot by a friendly | "Coming out" |
| Don't flag friendlies | Player/teammate in line of fire | Hold fire, shift to a different angle | "Blocked" |

Sources: https://www.globalsecurity.org/military/library/report/call/call_97-20_btldrill.htm , https://boisestate.edu/sps-militaryscience/wp-content/uploads/sites/123/2014/04/building-clearroom.pdf , https://www.speedrun.com/door_kickers/guides/ehckc , https://maxvelocitytactical.com/shattering-conventional-cqb-dogma/ (critique: terms like "fatal funnel" are overcomplicated; the real point is enemy lines of fire, corners, not silhouetting).

## 2. Game AI techniques

| Technique | Source | What to borrow |
|---|---|---|
| F.E.A.R. GOAP: 3-state FSM (Goto, Animate, UseSmartObject) plus A* over actions | https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf , https://gdcvault.com/play/1013459/Three-States-and-a-Plan | Keep the executor tiny; put variety in goals/actions. Re-plan when a door shuts or cover is lost |
| F.E.A.R. squad layer: NPCs grouped by proximity, own goals; dialogue makes cooperation visible | https://www.cs.uky.edu/~sgware/reading/papers/orkin2005agent.pdf , https://www.gamespot.com/articles/fear-designer-diary-2-a-study-of-smart-ai-part-ii/1100-6134022/ | Squad coordination can be cheap: shared claims on positions plus spoken lines. A voice line is player-readable state |
| Halo behavior trees: prioritized, self-describing behaviors | https://web.eecs.umich.edu/~sugih/courses/eecs494/fall06/lectures/lecture18-halo2.pdf | Behaviors report their own relevance; pick by priority with hysteresis |
| Halo 3 objectives: squads distributed over prioritized tasks; combat dialogue | https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf | Room-clearing as tasks (breach, POD A, POD B, rear guard) that officers claim |
| Last of Us buddy AI (Dyckhoff, GDC 2014) | https://gamedeveloper.com/design/video-ellie-s-buddy-ai-in-i-the-last-of-us-i- | Buddy must never give the player away or block; deliberately limited to keep player trust |
| Utility AI / IAUS (Dave Mark) | https://gameai.com/iaus.php , https://www.gdcvault.com/play/1018040/Architecture-Tricks-Managing-Behaviors | Score options with response curves (danger, distance, ammo, morale); fits UnrealScript float math |
| Left 4 Dead Director (Booth): team treated as one player, pacing | https://www.shacknews.com/article/57892/left-4-dead-at-gdc | Director for suspects: raise/lower aggression from player stress. Survivor-bot logic not confirmed by search |
| UE4 AI_FPS thesis: BT, tactical positions, flanking | https://github.com/mtrebi/AI_FPS | Reference for cover scoring and group flank |
| GOAP demo plugin | https://github.com/Narratech/GOAP_NPC_Demo | Small GOAP reference |

## 3. Proposed design for SwatMinds

Architecture: keep Tyrion/Hive as the executor. Add one utility-scoring layer choosing among a small action menu per officer and per suspect, plus a team claim board (in the Hive) holding points, sectors and who is moving. Few states, many dialogue lines.

### 3.1 Officers: cover the player
- Claim board: on stacking, assign slots (breacher, #1 POD, #2 POD, rear). A slot is claimed once.
- Cover-the-player: compute the player's blind arcs (behind, away from facing, unchecked doors). One officer owns the player's six, one the nearest unwatched door. Utility = unwatched arc size x door proximity.
- Never-block rule (Last of Us): reject cover points near the player's path to the door or aim ray; step aside when the player moves toward the officer; never stand in a doorway after entering.
- Overwatch handoff: an officer moves only if another holds "Covered" on the destination. Cap simultaneous movers at half the team.
- Hold fire when the player or a teammate is in the line (friendly capsule ray check); say "Blocked".
- Threat priority score = armed x aimed-at-friendly x proximity; civilians and compliant suspects excluded.

### 3.2 Callouts (dialogue sells the AI)
Lines only on state transitions, per-line cooldown 3-5 s, one speaker at a time (queue by priority): "Stacked", "Breaching", "Moving", "Covered", "Contact left", "Clear", "Coming out", "Reloading", "Man down", "Blocked". Suspects bark too ("He is reloading", "I am hit", "Where did he go") so the player hears the reasoning, as in F.E.A.R.

### 3.3 Help/revive equivalents (SWAT 4 has no revive)
- Downed officer: nearest free officer scores "cover downed" (stand where the casualty is screened from known threats until clear), then "drag" the casualty out of the funnel toward the entry. Needs a drag animation or a slide fallback.
- Cuff assist: while the player cuffs, one officer covers the suspect and one watches the door; if the player is busy, an officer cuffs compliant suspects.
- Reload cover: when the player reloads, nearest officer says "I have you" and holds the player's arc.
- Medic-lite: short bandage on a wounded neighbor out of contact (costs time, announced).

### 3.4 Agency
- Morale, fear and stress floats feed utility scores. Suspects: flee, surrender, ambush, grab hostage. Officers: confidence drops when a teammate falls, raising caution and "Man down" calls.
- Suspects reason about danger: avoid the funnel themselves (hold off-axis, shoot the first man through), call backup, reposition after hearing a breach.
- Light Director (L4D style): adjust suspect aggression and ambush chance from player stress (recent damage, ammo, time) within fairness limits.
- Personality tags (cautious, aggressive) shift utility weights so identical stacks differ run to run.

### 3.5 Build order
1. Claim board, PODs, never-block cover filter. 2. Callout queue. 3. Overwatch handoff. 4. Downed-officer cover/drag. 5. Utility stress/morale layer and Director.

## Gaps
Not verified by search: corner-fed/center-fed specifics, SWAT 4 officer AI internals, Ready or Not, Ghost Recon/Rainbow Six, Radiant AI, RimWorld/Dwarf Fortress, YouTube talks, L4D survivor bot logic.
