# F.E.A.R. enemy AI and Goal-Oriented Action Planning (GOAP)

Primary sources read in full for these notes (all four Orkin papers + F.E.A.R. SDK source files):
- Orkin, "Three States and a Plan: The A.I. of F.E.A.R." (GDC 2006 paper) — mirror PDF: https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf (original: http://alumni.media.mit.edu/~jorkin/gdc2006_orkin_jeff_fear.pdf, now 404; archived: http://web.archive.org/web/2023/https://alumni.media.mit.edu/~jorkin/gdc2006_orkin_jeff_fear.pdf)
- Orkin, "Applying Goal-Oriented Action Planning to Games" (draft for AI Game Programming Wisdom 2, 2003, pp. 217-228) — http://web.archive.org/web/20230912173044/https://alumni.media.mit.edu/~jorkin/GOAP_draft_AIWisdom2_2003.pdf
- Orkin, "Symbolic Representation of Game World State: Toward Real-Time Planning in Games" (AAAI Challenges in Game AI Workshop 2004, pp. 26-30) — http://web.archive.org/web/20230912173050/https://alumni.media.mit.edu/~jorkin/WS404OrkinJ.pdf
- Orkin, "Agent Architecture Considerations for Real-Time Planning in Games" (AIIDE 2005) — http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf
- Orkin's GOAP index page (resources, implementations, games list) — http://web.archive.org/web/20230713022726/https://alumni.media.mit.edu/~jorkin/goap.html (the live alumni.media.mit.edu page now returns 404)
- F.E.A.R. SDK v1.08 AI source, unofficial GitHub mirror — https://github.com/xfw5/Fear-SDK-1.08 (files under Game/ObjectDLL/)

## 1. Orkin's architecture: three-state FSM, world state, goals vs actions, A*, costs, replanning, performance

### Takeaway
F.E.A.R. soldiers run a tiny FSM (Goto, Animate, UseSmartObject). All the "when to switch state and with what parameters" logic moved into a STRIPS-like planner. The planner does a regressive A* search over actions. Each action has symbolic preconditions/effects stored in a fixed array of about 20 agent-centric keys, plus procedural "context" preconditions/effects. Expensive checks (rays, paths, cover search) are pushed into time-sliced sensors that cache results in working memory. Replanning happens only when the plan is invalidated or the top goal changes, and plans are usually 1-2 actions long.

### Cited Findings
**Three states**
- The FSM has only three states: Goto, Animate and UseSmartObject. UseSmartObject is "a specialized data-driven version of the Animate state", so effectively two states. Orkin's line: "all A.I. ever do is move around and play animations!" — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- Actions connect planner to FSM: "ActivateAction() function sets the A.I. into some state, and sets some parameters. For example, the Flee action sets the A.I. into the Goto state, and sets some specific destination." Action class = symbolic `WORLD_STATE m_Preconditions; m_Effects;` + `CheckProceduralPreconditions()` + `ActivateAction()` — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- In AIGPW2: "A GOAP system does not replace the need for a finite-state machine… but greatly simplifies the required FSM… each action represents a state transition"; Dodge and ReloadWeapon both set state Animate with different animations; patrol = plan of Goto between points — [Orkin AIGPW2 draft](http://web.archive.org/web/20230912173044/https://alumni.media.mit.edu/~jorkin/GOAP_draft_AIWisdom2_2003.pdf)

**Goals, Goal Sets, Action Sets (data-driven per character type)**
- Designers assign a Goal Set per AI in WorldEdit (sets authored in GDBEdit). Goals "compete for activation, and the A.I. uses the planner to try to satisfy the highest priority goal." The same goal set (Patrol + KillEnemy) gives different behaviour for soldier, assassin and rat because their Action Sets differ. The rat cannot build any KillEnemy plan, so it falls back to Patrol — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- Example goal priorities shown: Work 8.0, Stunned 80.0, Death 100.0 — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- A goal "knows how to calculate its current relevance, and knows when it has been satisfied". NOLF2 characters had about 25 goals, each with an embedded hard-coded plan. GOAP goals contain no plan, only satisfaction conditions — [Orkin AIGPW2](http://web.archive.org/web/20230912173044/https://alumni.media.mit.edu/~jorkin/GOAP_draft_AIWisdom2_2003.pdf)
- Engineers implement goals/actions with their preconditions and effects. Designers only pick which goals and actions each NPC type gets, via data files. This removes flag proliferation such as "CanSwim, CanFly, KicksDoors, or DestroysDoors" — [Orkin AAAI04](http://web.archive.org/web/20230912173050/https://alumni.media.mit.edu/~jorkin/WS404OrkinJ.pdf)
- Late-added enemy type: flying drones built by combining the ghost's aerial-movement actions with the soldier's weapon/tactical actions — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)

**The "seven layer dip" (how the soldier behaviour was layered)**
In order — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf):
1. KillEnemy goal, satisfied by Attack.
2. Dodge goal, satisfied by DodgeShuffle or DodgeRoll (when a gun is aimed at him).
3. AttackMelee action (an extra way to satisfy KillEnemy when close).
4. Cover goal, reached with GotoNode. Then AttackFromCover satisfies KillEnemy at a Cover node. DodgeCovered is added too.
5. BlindFireFromCover: "If the A.I. gets shot while in cover, he blind fires for a while."
6. Ambush goal: "When an A.I.'s cover is compromised, he will try to hide at a node designated by designers as an Ambush node."
7. Dialogue. Orkin's point: "We never have to manually specify the transitions between these behaviors."
- F.E.A.R. AI "always try to stay covered, never leave cover unless threatened and other cover is available, and fire from cover to the best of their ability". NOLF2 AI, by contrast, popped "in and out randomly like a shooting gallery" — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)

**World state representation**
- F.E.A.R. differs from STRIPS in four ways: a cost per action, no Add/Delete lists, procedural preconditions, and procedural effects — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- World state = "fixed-size array of four-byte values". Examples: TargetDead [bool], WeaponLoaded [bool], OnVehicleType [enum], AtNode [HANDLE or variable*]. A variable value points to a value in the parent goal's or action's precondition array; for example, the Cover goal specifies which node Goto must reach — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- Limitation: the agent can reason about only one weapon and one target at a time. "Targeting and weapon systems choose which weapon and enemy are currently in focus" outside the planner — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- The fixed array is indexed by symbol for instant lookup. Its limits: no way to say who a symbol refers to; preconditions are conjunctions only; each symbol appears in only one clause; and every search node copies the state. A prototype with arbitrary expressions was too slow ("dynamic memory allocations and slower precondition validation"). The fix was an "agent centric" representation where all symbols are relative to the agent. Symbols were kept general, e.g. ReactedToDamage became the enum ReactedToEvent — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Shipped symbol list, as published: AnimPlayed, AtNode, AtNodeType, AtTargetPos, DisturbanceExists, Idling, PositionIsValid, RidingVehicle, ReactedToWorldStateEvent, TargetIsAimingAtMe, TargetIsDead, TargetIsFlushedOut, TargetIsSuppressed, TraversedLink, UsingObject, WeaponArmed, WeaponLoaded — [Orkin AIIDE05 Appendix A](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- The SDK's `ENUM_AIWORLDSTATE_PROP_KEY` has 22 keys. On top of the list above it adds AnimLooped, CoverStatus, MountedObject, SurveyedArea and TargetIsLookingAtMe — [F.E.A.R. SDK mirror, AIWorldState.h](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIWorldState.h)
- Published action list (Appendix B), about 40 actions: Animate, Attack, AttackFromNode, AttackFromVehicle, AttackGrenade, AttackGrenadeFromCover, AttackLunge, AttackMelee, AttackReady, BlindFireFromCover, DismountVehicle, DodgeRoll, DodgeShuffle, DrawWeapon, EscapeDanger, FlushOutWithGrenade, Follow, GetOutOfTheWay, GotoNode, GotoNodeOfType, GotoTarget, GotoValidPosition, HolsterWeapon, Idle, InspectDisturbance, InstantDeath, LookAtDisturbance, MountVehicle, ReactToDanger, Recoil, Reload, SuppressionFire, SurveyArea, TraverseBlockedDoor, TraverseLink, UseSmartObjectNode — [Orkin AIIDE05 Appendix B](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- The SDK mirror has 72 AIGoal*.cpp and 123 AIAction*.cpp files. These counts include abstract bases and managers, and the shipped game plus expansions have more than the 2005 paper lists — [GitHub tree of xfw5/Fear-SDK-1.08](https://github.com/xfw5/Fear-SDK-1.08/tree/master/Game/ObjectDLL)

**Context preconditions/effects**
- "Context precondition is something that needs to be true, but that the planner will never try to satisfy". Example: the target must be within some distance and field of view. It can be any boolean code, but it is re-evaluated every time the planner tries the action, so keep it cheap. Cache results or read values computed periodically outside the planner — [Orkin AIGPW2](http://web.archive.org/web/20230912173044/https://alumni.media.mit.edu/~jorkin/GOAP_draft_AIWisdom2_2003.pdf)
- Example: run-away is used only if `CheckProceduralPreconditions()` finds a safe NavMesh path; otherwise the AI hunkers down in place — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- ReactToDanger, EscapeDanger, InspectDisturbance and LookAtDisturbance all have the effect DisturbanceExists=false. Context preconditions choose among them by checking working memory for dangerous disturbances such as grenades. A context effect function runs after an action completes — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)

**A* search, heuristic, costs**
- Search is regressive (backward from the goal). Forward search would need a brute-force search to discover, for example, "turn on generator before using laser". Nodes are world states, edges are actions, node cost is the sum of action costs, and the heuristic is the number of unsatisfied goal properties. The goal state grows as actions add their preconditions — [Orkin AIGPW2](http://web.archive.org/web/20230912173044/https://alumni.media.mit.edu/~jorkin/GOAP_draft_AIWisdom2_2003.pdf)
- Actions are hashed by effect symbol, so finding candidate neighbours is instant. One action can sit in several bins — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf); see also [Orkin AAAI04](http://web.archive.org/web/20230912173050/https://alumni.media.mit.edu/~jorkin/WS404OrkinJ.pdf)
- Costs make specific actions win over general ones. Default action cost is 1.0 and generic Attack costs 5.0. So the plan [GotoNode, AttackFromCover] (cost 2) beats [Attack] (cost 5), and "The NPC will fire from cover if possible" — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- The same A* code serves navigation (NavMesh polygons) and planning (world states). For crawling under an obstacle, the AI first finds a path, then plans how to get past the obstacle — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- SDK: `CAIPlanner::BuildPlan(CAI*, CAIGoalAbstract*)` runs a generic `m_AStar` with planner-specific Storage, Goal and Map classes, and `BuildEffectActionsTable()` builds the effect hash. The plan is read back by walking parent pointers — [SDK mirror, AIPlanner.cpp](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIPlanner.cpp)

**Replanning triggers**
- "We only formulate a new plan when the current plan has been invalidated, or the most relevant goal has changed… The time between planner searches can sometimes be measured in minutes!" — [Orkin AAAI04](http://web.archive.org/web/20230912173050/https://alumni.media.mit.edu/~jorkin/WS404OrkinJ.pdf)
- When sensors detect significant changes, the agent re-evaluates goal relevance. Only one goal is active at a time — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Worked replanning example. The AI plans GotoTarget then Attack. The player blocks the door, which invalidates GotoTarget. The TraverseLink goal wins and the plan is TraverseBlockedDoor (kick). Its context effect records "door still blocked" in working memory. KillEnemy is planned again; the pathfinder now avoids the door, so the AI dives through the window, which needs another TraverseLink plan — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- SDK: `CAIGoalMgr::UpdateGoalRelevances(bool bReplan)` picks the max-relevance goal and calls `pGoalMax->BuildPlan()`. On failure it calls `HandleBuildPlanFailure()` and falls through to the next goal — [SDK mirror, AIGoalMgr.cpp](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIGoalMgr.cpp)

**Agent architecture and performance budget**
- The architecture follows MIT C4: blackboard, working memory, subsystems (targeting, navigation, animation, weapons) and sensors. Actions "activate" by writing blackboard variables; for example, GotoTarget sets a destination and the nav system paths there on the next update — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- The planner must finish its whole search within one frame, so expensive checks are amortized in sensors. SensorNodeCombat polls 3 times a second for cover and firing nodes, sorts them by distance, and judges validity by node radii that must contain the target. Per frame, non-every-frame sensors update until one returns true ("did significant work"). Allowing only one sensor per update was too slow to react — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- WorkingMemoryFact: 10 fact types (Character, Object, Disturbance, Task, PathInfo, Desire…) and 16 attributes, each a value plus a 0..1 confidence. Garbage collection is ad hoc; Orkin suggests expiry times instead — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Combat involves 4 to 8 enemies at a time, a limit set by the renderer — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf). The 2004 paper says "up to ten NPCs at once" — [Orkin AAAI04](http://web.archive.org/web/20230912173050/https://alumni.media.mit.edu/~jorkin/WS404OrkinJ.pdf)
- Measured data from logged F.E.A.R. sessions: 55 distinct actions logged. GOAP plans are "rather short (1 or 2 actions)". Planning is so fast that millisecond timestamps of consecutive plans collide. Max planning speed is 8.5 plans/s per NPC. The longest gap between planner calls was 529.75 s. UseSmartObjectNode was 26% of all 9781 action occurrences. Half of all actions occur 22 times or fewer. Action costs showed "no clear influence" on action usage — [Jacopin, "Game AI Planning Analytics: The Case of Three First-Person Shooters", AIIDE 2014](https://cdn.aaai.org/ojs/12728/12728-52-16245-1-2-20201228.pdf)
- Orkin's suggested optimizations: optimize A*, cache previous searches, spread plan formulation over several updates, and prune with context preconditions — [Orkin AIGPW2](http://web.archive.org/web/20230912173044/https://alumni.media.mit.edu/~jorkin/GOAP_draft_AIWisdom2_2003.pdf)

### Inferences
- UE2/UnrealScript mapping. Orkin's Goto/Animate split maps onto the existing Bot states. MoveToDestination, TacticalMove, Charge and Flee play the role of Goto; Crouch, Dodge, Wait and firing states play the role of Animate. Each GOAP action's `Activate()` would `GotoState('X')` and set blackboard-like fields on the controller, for example Destination, MoveTarget or a cover NavigationPoint.
- A 32-bit int bitmask (≤32 boolean keys) plus a small byte/int array for enum keys (AtNodeType, CoverStatus) is enough to copy F.E.A.R.'s design. F.E.A.R. itself ran on about 17-22 keys. Plans of 1-2 actions mean an iterative A* with a small fixed open list (16-64 nodes) in UnrealScript should fit within its instruction budget. Cap iterations and fall back to the next goal on failure, as `HandleBuildPlanFailure` does.
- Do not plan per tick. Replan on (a) a goal-relevance change and (b) action failure or invalidation. Push traces and cover searches into timers or "sensors" that write cached facts, about 3 Hz for cover like SensorNodeCombat.

### Gaps
- The exact A* open-list size and iteration cap in AIPlanner.cpp were not extracted (file downloaded but not read line by line). Per-plan CPU time in ms was never published by Orkin. Jacopin says only that timestamps collided at ms resolution.
- The GDC06 slides (gdc2006_orkin_jeff_fear.zip) were not retrieved.

## 2. Squad behaviours: coordinator, simple behaviours, goals not scripts, flanking/suppression

### Takeaway
A global coordinator re-clusters AIs into squads by proximity. Each squad runs at most one simple "activity" (GetToCover, AdvanceCover, OrderlyAdvance, Search; the SDK adds ExchangeWeapons). An activity fills slots, then issues orders that are only facts or tasks; each AI's own goal system decides whether to obey. Flanking, pincers and retreats were never implemented. They emerge from "move to nearer valid cover" around walls, and dialogue makes them read as intentional.

### Cited Findings
- "a global coordinator… periodically re-clusters A.I. into squads based on proximity. At any point in time, each of these squads may execute zero or one squad behaviors." There are simple behaviours (suppression, positioning, following) and complex ones (flanking, coordinated strikes, retreats, reinforcements) — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- The four simple behaviours — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf):
  - Get-to-Cover: members not in valid cover get to valid cover while one lays suppression fire.
  - Advance-Cover: members move to valid cover closer to the threat while one suppresses.
  - Orderly-Advance: single file, each covers the one in front, and the last faces backwards.
  - Search: the squad splits into pairs that cover each other and systematically search rooms.
- Four-step lifecycle. (1) Find AIs that can fill required slots. (2) Activate and send orders. (3) Monitor progress each tick. (4) Finish with success, or failure through death or interruption. "A.I. have goals to respond to orders, and it is up to the A.I. to prioritize following those orders versus satisfying other goals" — fleeing a grenade beats an advance order — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf); same point in [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- The squad behaviour does no map analysis. Each AI's sensors already hold a list of valid cover nodes nearby. The behaviour just picks a node the AI knows about and makes sure no two AIs are sent to the same node — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- "we actually did not have any complex squad behaviors at all in F.E.A.R." An apparent flank is "a side effect of moving to the only available valid cover he is aware of". A pincer is just Advance-Cover to nearer cover that happens to lie on either side of the player. "Retreats emerge in a similar manner." — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- The squad system was inspired by Evans & Barnet, "Social Activities: Implementing Wittgenstein" (GDC 2002). It was "ad-hoc", not planner-based. Orkin suggests HTN for future squad planning because it handles parallel actions — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- SDK code details:
  - CAICoordinator clusters with `SQUAD_THRESH_WIDTH 800` and `SQUAD_THRESH_HEIGHT 250` (an AABB in game units). It regenerates squads every `m_fSquadRegenRate = 1.f` second and updates one squad per call, round-robin — [SDK AICoordinator.cpp](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AICoordinator.cpp)
  - Activity types: AdvanceCover, GetToCover, ExchangeWeapons, OrderlyAdvance, Search — [SDK AIEnumActivityTypes.h](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIEnumActivityTypes.h)
  - CAIActivityAbstract has these virtuals: `IsActivityRelevant`, `FindActivityParticipants`, `ActivateActivity`, `UpdateActivity`, `DeactivateActivity`. It holds a priority, update rate, timeout, expiration time and up to 20 participants. Status values: Advancing, Complete, Failed, Initialized, Searching, Suppressing, Updating — [SDK AIActivityAbstract.h](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIActivityAbstract.h)
  - GetToCover picks an `m_hSuppressAI` and orders it to suppress. It waits until the suppressor's target is visible from its weapon (`WaitingForSuppressionFire`), then issues cover orders through `kFact_Task` working-memory facts. It ignores AIs with scripted cover/ambush tasks and uses a `kKnowledge_NextSuppressTime` timeout — [SDK AIActivityGetToCover.cpp](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIActivityGetToCover.cpp)
- Suppression is a planner action too (SuppressionFire, with symbol TargetIsSuppressed). Flushing out with grenades is FlushOutWithGrenade, with symbol TargetIsFlushedOut — [Orkin AIIDE05 appendices](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)

### Inferences
- For Advent Rising, a "squad coordinator" Actor (or GameRules/Mutator) can cluster Pawns by distance about once per second. It runs at most one activity per squad and communicates only by setting an "order" field on each controller. That field is read by an `OrderedMove` / `FollowOrder` goal whose relevance sits below Flee/Dodge, which gives the F.E.A.R. "orders can be ignored" property for free.
- Flanking needs no dedicated code if cover choice favours valid cover nodes closer to the player and nodes are not shared. Level geometry produces the flank. The cheapest win is a reservation table for cover nodes.

### Gaps
- The SDK's AdvanceCover, OrderlyAdvance and Search code was only skimmed. The exact rules for "closer cover" were not extracted.

## 3. Illusion of intelligence: barks explaining behaviour

### Takeaway
Dialogue is chosen "after the fact" by the squad layer once it knows what AIs will do. It is a separate system with lines hooked into code by hand, not into the planner. It uses two-voice exchanges, announces intentions that aren't implemented ("reinforcements"), and explains failures ("I've got nowhere to go!").

### Cited Findings
- "Having A.I. speak to each other allows us to cue the player in to the fact that the coordination is intentional." The last survivor says a variant of "I need reinforcements", but there is no reinforcement mechanism; the player assumes the next enemies are the reinforcements — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- Prefer dialogue over announcement. Someone asks a shot ally for his status and the ally answers "hit" or "alright". Searchers ask each other "see anything?" — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- "We also use dialogue to explain a lack of action… The A.I. says 'I've got nowhere to go!'" — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- "all decisions about what to say are made after the fact, once the squad behavior has decided what the A.I. are going to do". The combat dialogue system "was completely separate from the action planning system. We manually hooked dialogue lines into the code in various places", with lots of trial and error; for example, you shouldn't ask a dismembered ally for his status — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- SDK: activities call `g_pAISoundMgr->RequestAISound(hAI, kAIS_OrderAdvance, kAISndCat_Event, hTarget, delay)` and `RequestAISoundSequence(...)` for two-speaker call and response. For example, AdvanceCover failure: the ally says OrderAdvance and the AI needing cover replies NegativeStrong after 0.5 s — [SDK AIActivityAdvanceCover.cpp](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIActivityAdvanceCover.cpp)
- SDK bark vocabulary (kAIS_* enum) includes: Advancing, Affirmative, BackupUrgent, CheckIn, Copy, DoYouSeeHim, FanOut, GetBehindHim, Grenade, GrenadeThreat, HoldPosition, ManDown/ManDownTwo/ManDownThree/ManDownAll, Negative, NoShot, NowhereToGo, OrderAdvance, OrderCover, OrderSearch, PinnedDown, Regroup, RequestAdvance, RequestAmmo, RequestCover, SearchClear, SearchFailed, ShutUp, SniperDetected, StatusCheck, StatusOK, SuppressionFire, Thanks, UnderFire, WhatThe, WhereIsHe, WhereShouldIGo. It also has location callouts (LocationDesk, LocationCrate, LocationVent… about 20) and CombatOp* lines for environmental hazards (Barrel, Tank, Valve, PowerBox, Supports) — [SDK AISoundTypeEnums.h](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AISoundTypeEnums.h)
- Future direction Orkin proposed: treat dialogue lines as planner actions with preconditions and expected effects ("Look out! Grenade!" makes the ally move away) — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)

### Inferences
- In UE2, a central "bark manager" with per-category cooldowns and a request/sequence API (speaker, line, responder, reply, delay) copies kAIS cheaply. Trigger it from (a) squad activity start and fail events and (b) individual events: death of a squadmate, cover invalidated with no cover found ("nowhere to go"), grenade sensed.

### Gaps
- AISoundMgr's priority and cooldown logic was not read.

## 4. Cover and navigation: AI nodes, dynamic cover, blind fire, destructibles

### Takeaway
Designers place nodes (Cover, Ambush, smart-object nodes such as flippable tables). Validity is dynamic: node radii must contain the target, and a polling sensor re-sorts nodes about 3 times a second. Node dependencies chain into plans. Blind fire is just an action available when shot while at a cover node.

### Cited Findings
- Designers' job is "to create interesting spaces for combat, packed with opportunities", such as furniture for cover, windows to dive through and multiple entries for flanking. They do not script individuals — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- SensorNodeCombat polls 3 times a second for cover and firing nodes. Validity is based on node radii that must contain the current target, and nodes are sorted by distance (normalized confidence) — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- When a threat is found along the path to a tactical destination, the AI crouches and re-evaluates. The PassTarget sensor checks one path per frame until it finds a safe route — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Node dependencies. A table must be flipped before use as cover, giving the plan `GotoNode(TableNode) UseObject(Table) GotoNode(NodeCover78) AttackFromCover()` — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Blind fire: BlindFireFromCover when shot while in cover. Ambush nodes are used when cover is compromised — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- Doors and windows are NavMeshLinks, handled by TraverseLink and TraverseBlockedDoor. Blocked-link knowledge is stored in working memory and consulted by the pathfinder — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Sensed grenades invalidate cover. EscapeDanger and ReactToDanger are distance-gated, and AIs outside the blast radius fall back to LookAtDisturbance, an emergent "watch the grenade land" behaviour — [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)

### Inferences
- UE2 equivalent: subclass NavigationPoint (or tag existing PathNodes) as CoverNode, with a valid-threat radius, a facing cone, a crouch/stand flag and an "ambush" flag. A per-bot timer about 3 times a second filters nodes by distance plus a FastTrace from node to enemy, and the result is cached. CoverStatus and AtNodeType become planner keys.

### Gaps
- No primary source found on how F.E.A.R. handled destructible cover specifically, beyond grenade/danger invalidation and dynamic node validity. The SDK's AINodeCover / node-status code was not inspected (the tree has AIEnumNodeStatus.h).

## 5. F.E.A.R. SDK / public tools and open-source GOAP libraries (licences)

### Takeaway
The F.E.A.R. SDK v1.08 ("Public Tools") ships the complete AI C++ source under Monolith copyright. It is a modding EULA, not an open licence, so use it as a reference only and do not copy code. For reusable code, ReGoap and Crashkonijn GOAP are Apache-2.0, sploreg/goap is MIT, and GPGOAP (C) is the smallest reference.

### Cited Findings
- Orkin lists "F.E.A.R. SDK v1.08 - includes complete A.I. source code" (link to fear.filefront.com, now defunct). He also lists GPGOAP (Bram Stolk) and ReGoap (Luciano Ferraro) as open-source implementations — [Orkin GOAP page (archived)](http://web.archive.org/web/20230713022726/https://alumni.media.mit.edu/~jorkin/goap.html)
- The SDK source headers read "(c) 2003 Monolith Productions, Inc. All Rights Reserved". The GitHub mirror (xfw5/Fear-SDK-1.08, last push 2015) has no licence file detected by GitHub — [SDK AIPlanner.cpp](https://github.com/xfw5/Fear-SDK-1.08/blob/master/Game/ObjectDLL/AIPlanner.cpp)
- VUG announced the SDK as "officially licensed tools to create their own modifications" — [GameSpot, "F.E.A.R. the SDK kit"](https://www.gamespot.com/articles/fear-the-sdk-kit/1100-6140384/). Softpedia lists "F.E.A.R Public Tools 1.08" — [Softpedia](https://games.softpedia.com/downloadTag/F.E.A.R%20Public%20Tools)
- Licences, as reported by the GitHub API on 2026-10-08:
  - luxkun/ReGoap (C#/Unity): Apache-2.0, about 1.1k stars — https://github.com/luxkun/ReGoap
  - crashkonijn/GOAP (C#/Unity, multithreaded): Apache-2.0, about 1.8k stars — https://github.com/crashkonijn/GOAP
  - sploreg/goap (Java, jMonkeyEngine-style): MIT — https://github.com/sploreg/goap
  - stolk/GPGOAP (C): no SPDX licence returned by the API; check the repo before reuse — https://github.com/stolk/GPGOAP
- GPGOAP design is a close fit for UnrealScript. World state is boolean atoms (a bitfield of values plus a "don't care" mask), and actions have pre/post conditions and a cost. It returns the lowest-cost plan. Its README soldier example uses scout, approach, aim, shoot, load, detonatebomb and flee — [GPGOAP README](https://github.com/stolk/GPGOAP)

### Inferences
- UnrealScript can't link C#/C libraries, so any library is a design reference anyway. Porting GPGOAP's ~300-line bitmask A* (values + care mask in two ints) into UnrealScript is the most direct path. Treat the F.E.A.R. SDK as read-only documentation, consistent with the user's rule of avoiding no-reuse licences.

### Gaps
- The F.E.A.R. Public Tools EULA text was not found online. The Steam release reportedly includes the SDK in its "extras" folder (unverified forum claim, [Steam discussion](https://steamcommunity.com/app/21090/discussions/0/1732087825006409925)). If the user owns F.E.A.R., the EULA in that folder is the authoritative text.
- GPGOAP's licence is unconfirmed.

## 6. Later uses, lessons/limitations, and GOAP vs HTN vs BT vs utility

### Takeaway
GOAP spread widely: Condemned, S.T.A.L.K.E.R., Fallout 3, Empire: Total War, F.E.A.R. 2, Just Cause 2, Transformers: WfC, Deus Ex: HR, Shadow of Mordor and Tomb Raider. Known costs: hard to debug, weak designer control and authored sequences, no ordering or hierarchy, backward search can't do partial plans, and many actions are rarely used. HTN (Transformers: Fall of Cybertron, Killzone) traded GOAP's search for authored hierarchy and was faster.

### Cited Findings
- Games using GOAP architectures (Orkin's list): F.E.A.R., Condemned: Criminal Origins, S.T.A.L.K.E.R.: SoC, Mushroom Men, Ghostbusters (Wii), Silent Hill: Homecoming, Fallout 3, Empire: Total War, F.E.A.R. 2, Demigod, Just Cause 2, Transformers: War for Cybertron, Trapped Dead, Deus Ex: Human Revolution — [Orkin GOAP page (archived)](http://web.archive.org/web/20230713022726/https://alumni.media.mit.edu/~jorkin/goap.html)
- GDC 2015 AI Summit, "Goal-Oriented Action Planning: Ten Years Old and No Fear!" (Chris Conway, Peter Higley, Eric Jacopin). Monolith "continued to grow their implementation of GOAP… such as the recent Shadow of Mordor". Crystal Dynamics covered "debugging and reporting of the (often novel or unexpected) GOAP behaviors in their Tomb Raider titles". The abstract notes GOAP had "mixed success" versus traditional methods — [GDC Vault 1022019](https://gdcvault.com/play/1022019/Goal-0riented-Action-Planning-Ten)
- Orkin's own limitations:
  - No scheduler, so ordering such as DrawWeapon before GotoTarget must be forced through more restrictive preconditions, which makes actions less reusable.
  - No compound actions, though "designers always want a specific sequence of actions" in some cases.
  - Planning was individual only.
  - [Orkin AIIDE05](http://web.archive.org/web/20230912173042/https://alumni.media.mit.edu/~jorkin/aiide05OrkinJ.pdf)
- Jacopin's data. Half of F.E.A.R.'s actions are "poorly used", and action costs had no visible effect on usage. Most planner time goes to patrol and animation rather than combat. "alternatives to AIP should be considered for repetitive actions (i.e. plans of length 1) and fixed plans". Rat02 kept planning long after the player left (a culling issue). GOAP plans run 1-2 actions and HTN plans 2-5 — [Jacopin AIIDE 2014](https://cdn.aaai.org/ojs/12728/12728-52-16245-1-2-20201228.pdf)
- HTN versus GOAP from a studio that shipped both. High Moon used GOAP in Transformers: War for Cybertron and HTN in Fall of Cybertron. HTN uses depth-first decomposition with no heuristic or cost sorting, and the hierarchy culls branches, so "the HTN planner in Transformers: Fall of Cybertron [was] considerably faster than our GOAP system". HTN plans forward and so supports partial plans, while GOAP/STRIPS backward search "has to complete the entire search in order to know what first step to take". The chapter warns that replanning on every world-state change caused bugs; don't replan on a completed task's own expected effects — [Humphreys, "Exploring HTN Planners through Example", Game AI Pro ch. 12](http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter12_Exploring_HTN_Planners_through_Example.pdf)
- Unlike behaviour trees, "HTN planners can reason about the effects of possible actions" — [Humphreys, Game AI Pro ch. 12](http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter12_Exploring_HTN_Planners_through_Example.pdf)
- Orkin on FSMs versus planning: "It's not that any particular behavior in F.E.A.R. could not be implemented with existing techniques. Instead, it is the complexity of the combination and interaction of all of the behaviors that becomes unmanageable." He suggests HTN for squads — [Orkin GDC06](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- Secondary overview: Tommy Thompson, "Building the AI of F.E.A.R. with Goal Oriented Action Planning" (AI and Games, AI 101). It points to the same primary sources plus Jacopin's paper — [summary page](https://www.chaindesk.ai/tools/youtube-summarizer/building-the-ai-of-f-e-a-r-with-goal-oriented-action-planning-ai-101-PaOLBOuyswI) (auto-generated summary; secondary)

### Inferences
- For a GOAP-lite inside Advent Rising, the evidence argues for:
  - a small action set (about 10-20 actions; F.E.A.R.'s real plans were 1-2 steps);
  - priority goals with relevance functions;
  - hand-authored "compound" actions where designers want fixed sequences;
  - squad behaviour kept outside the planner;
  - heavy investment in barks and in a debug overlay showing goal, plan and current state per bot. Crystal Dynamics' talk centred on debugging unexpected behaviour.
- Utility scoring fits naturally as the goal-relevance function (F.E.A.R. goals already compute a relevance number), so this is a hybrid: utility picks goals, GOAP sequences actions.

### Gaps
- No primary technical source was retrieved on GOAP internals in Shadow of Mordor, Tomb Raider (2013) or Deus Ex: HR. Only the GDC 2015 abstract and Orkin's list confirm their use. The GDC 2015 talk video and slides are GDC Vault-gated.
- No primary source was retrieved for a GOAP versus utility AI comparison (for example Dave Mark's GDC talks). The behaviour-tree comparison rests only on Humphreys' remark above.
