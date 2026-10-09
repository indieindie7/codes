# Advent Rising: creature minds (AI design)

AdventMod's layer over the game's enemy AI. It gives each creature a psychology: traits that make it who it is, and feelings that change with what happens. Those feelings drive four behaviours: suppression, real cover use, squad morale with flanking, and hunting as a pack. Code: `AdventMod/Classes/ModMind.uc`, `ModMinds.uc`, `ModMindRules.uc`.

Status (2026-10-08): built and compiled, first in-game tests below.

## 1. What the game already does (recon)

- Every enemy is a `Bot` (WarfareGame, script, 12k lines) in a `SquadAI`.
- `Bot.ExecuteAttack` picks what to do by rolling odds from the pawn's `AdventPawnAbilities`: cover, attack (TacticalMove), crouch, charge, stalk, leap, dodge, flee.
- Every state change goes through `SquadAI.AssignState`, which respects `bLockState`.
- Weak points:
  - TacticalMove wanders to random spots instead of using paths.
  - Placed cover markers exist in 21 of 44 maps (about 320 in all).
  - There's no flanking, and the leader's "orders" are only animations.
  - The game's warning to the target when the player fires mostly does nothing.
  - Skill is always 5; difficulty only changes spawn counts and damage.
- Hooks we can use:
  - the Bot's public `Do*` functions;
  - its fire switch (`bDisableTimedFire`);
  - `Pawn.ShouldCrouch`;
  - `FindPathTo`;
  - the level's path nodes;
  - GameRules `NetDamage` and `ScoreKill`.
- The Mutator replacement hooks never run in this build, so nothing replaces the game's controllers.

## 2. The mind

**Traits** come from the species, plus or minus `TraitSpread` (0.15) for each creature:

| species | courage | aggression | discipline | social | cunning | character |
|---|---|---|---|---|---|---|
| human (marines, spec ops, bounty hunters, Aurelians) | .45 | .45 | .5 | .75 | .6 | Afraid of losses, takes cover, flanks. |
| Seeker | .7 | .65 | .75 | .35 | .45 | A cult's foot soldiers: obedient and brave, shaken more by fire than by their own dead. |
| Seeker veteran (elite, commander, brute) | .85 | .7 | .85 | .3 | .7 | Steady, and the clever flanker. |
| hound | .6 | .9 | .15 | .9 | .65 | Pack predator: no cover, circles its prey, rages when the pack is hurt. |
| construct (shock trooper) | 1 | .6 | 1 | 0 | .3 | Feels nothing. |

**Feelings** run from 0 to 1. They rise with events and ebb with time.

| event | what it does |
|---|---|
| a shot passes within 220 units | Pressure up, more with poor discipline; a little fear. |
| hit | Pressure up a lot; fear (less with courage) and anger (with aggression) up by the share of health lost. |
| a death it could see | Fear and anger, scaled by sociability, much more for its own kind and more again if the body came apart. |
| enemy within 250 units | Fear for the timid, anger for the aggressive. |
| low health, or squad below half | Fear creeps up by itself. |
| time | Pressure fades in seconds, but barely while still under fire; fear and anger fade in tens of seconds; stress fades slowly and keeps a floor under fear. |

## 3. How the feelings act

**Continuously**, each creature gets its own copy of its `AdventPawnAbilities`, so the game's own dice change:

| feeling | effect on the game's odds |
|---|---|
| pressure | more cover, dodging and crouching |
| fear | more cover and fleeing, less attacking and charging, slower reactions |
| anger | more charging and enraging, quicker reactions |

**Tasks** are picked a few times a second, never while the creature is mid-animation, scripted, leaping or dying. The first match wins:

| task | when | what it does |
|---|---|---|
| **panic** | fear > 0.92 with courage < 0.45 | Humans `DoPanic`, others `DoFlee`. |
| **pinned** (suppression) | pressure > 0.7 | Fire off, head down. Goes to cover if any is within 900 units, otherwise holds still. Pops up to shoot as pressure falls, and is freed below 0.35. |
| **fall back** | fear > 0.7 | Cover further from the enemy, or a run back to the squad's formation centre along paths. |
| **charge** | anger > 0.75 with aggression | Seekers try `DoEnrage`, others `DoCharge`. |
| **early cover** | under some fire or below half health; odds from cunning and fear | Takes cover before it has to. |

**Cover finder** (part B), over the level's path nodes plus their own cover points. A spot qualifies if it is:
- hidden from the enemy's eyes at crouch height;
- clear to shoot from one step to the side, standing;
- reachable in a straight run;
- not much nearer the enemy;
- not claimed by a squad mate.

Closest wins, and the afraid prefer spots further back.

**Squad** (part C):
- At most one flanker every 6 s. It's the member with the most cunning × calm, not busy, with at least 2 members engaged. It goes about 75° round the enemy from the squad, to the path node nearest that point that can see the enemy, leg by leg via `FindPathTo`.
- Losses: when a squad has lost half its number, Seekers and hounds get angrier while humans' fear creeps up, which ends in falling back.
- Hounds: two or more in a squad each take a spot 550 units round the prey (an angle of their own, drifting), then charge together.

## 4. Settings: `AdventMod.ini`, section `[AdventMod.ModMinds]`

- Switches: `bMinds` (off = stock AI), `bMindLog` (every feeling and decision in AdventNative.log).
- Tuning: `TraitSpread`, `PinPressure`, `FreePressure`, `FleeFear`, `PanicFear`, `ChargeAnger`, `CoverReach`, `NearMissReach`, `FlankEvery`, `HoundCircle` (packs off); the hound pack's own are in section 9. Wall-kicks and leap links: section 10.
- Pilot command: `MINDLIST` (every mind's feelings, task, shots past and hits; a hound's pack role).
- Needs and advertisements (hunger, fatigue, curiosity, safety, aggression; corpses, cover, noises, mates): section 11, `[AdventMod.ModNeeds]`.

## 5. Tests

See the end of this file once the in-game runs are in.

## 6. Known limits and ideas

- Only creatures in a squad are adopted. A pawn the pilot spawns has none, and the Bot's `Do*` functions need one.
- Moves are straight `MoveTo` legs. Cover must be in a straight line, and flanks and fall-backs re-path each leg.
- Not yet: suppression on the player's allies from enemy fire (it works for any instigator that is the creature's enemy, but it's untested); voice barks for the feelings (the game has `pawnSoundEvent` lines such as EnragedGrunt); a director that paces encounters by the player's stress; fixing the three stock bugs (Crouch.BeginState calls Super.EndState, LocateNearbyCoverPoint has no None check, Frustration over-increments).

## 7. Path costs (tested 2026-10-08)

The pilot's `ROUTETEST [distance]` runs the engine's own search (`FindPathToward`). It needs an AI controller: the player's returns no routes. It searches once normally, then once with each field raised on the route's middle nodes, and restores everything afterwards.

Results on level03sectionc and level14sectiond: all five are read by the native search. The route goes round the raised nodes:
- `NavigationPoint.ExtraCost`
- `TransientCost`
- `FearCost`
- `bBlocked`
- `ReachSpec.Distance`

Where no other way exists, the costs leave the route as it is, and `bBlocked` gives "no route".

So strategy changes can be cost profiles. Raise the costs before a creature's `FindPathTo`/`FindPathToward` and put them back after:
- exposure to the player's sight;
- the squad's main route, for flankers;
- danger, where creatures died.

`ModMinds.NextLeg` is the single place this plugs in.

## 8. Cost profiles and orders (built 2026-10-08)

**Exposure:** `ModMinds.Sweep` keeps a live set of the path nodes the player can see. It runs 120 sight traces per tick, round the level's nodes within 4000 units of the player.

**Profiles:** each creature's next leg (`NextLeg`) is planned with a cost profile for what it is doing. The costs are raised on `ExtraCost` for that one `FindPathTo` and restored right after.

| profile | used by | what it costs |
|---|---|---|
| push | everything else | nothing: the shortest route |
| hidden | pinned, in cover | +2000 on nodes the player sees |
| flank | flankers | hidden, +4000 more in the player's front 120°, +800 on squad mates' routes |
| fallback | falling back, panicking | hidden, +1500 on nodes nearer the player than the creature |

**Orders:** `MINDORDER push|hidden|flank|fallback|none` (pilot; later the director) sets a strategy for the creatures fighting the player.
- **push:** shortest routes, no early cover.
- **hidden:** hidden routes, early cover likely.
- **flank:** flankers three times as often, several at once.
- **fallback:** everyone falls back once, toward and behind the squad's centre.

**Test** (level14sectiond, 300 nodes, the same order sequence, two runs each): route nodes in the player's sight, over all planned legs.

| | run 1 | run 2 | overall |
|---|---|---|---|
| profiles on | 252/467 | 138/234 | about 56% |
| profiles off | 124/160 | 531/535 | about 88% |

It is an open arena, so some exposure can't be avoided. Settings: `bPathProfiles`, `SweepBudget`, `ExposeReach`, `ExposeCost`, `FrontCost`, `RouteCost`, `CloserCost`.

## 9. Hound packs (built and tested 2026-10-09)

The user's ask: hounds that stop dashing at the player and instead skip about, work round the sides, and pin the player down. The game's hound is the engine's (its gait, its leaps and bites through `AdventPawnAbilities`); the mind only says where it goes and when it may commit. Before this, two or more hounds each took a spot 550 units round the prey and then all charged (section 3). Code: `ModMinds.HoundPack` and the functions above it (`SkipLeg`, `HoundFlankSpot`, `HoundCommit`, `SidesTick`, `HoundStats`).

**Roles** are facts each hound reads (Horizon's group agent, Halo's hold-then-charge). Dealt per squad every 1.5 s, at once when one is hurt or roleless:

| role | who | what it does |
|---|---|---|
| **holder** | the one nearest the prey's front (the current holder keeps it while it stays in front and unhurt) | Keeps the front at `HoundHold` (380), feinting in on even legs and out on odd (+-70). Never commits first. |
| **flanker** | the rest, sides by turns (+1, -1, +1 ...), so with three or more there is one on each side | Goes round to +-`HoundFlankAngle` (120 degrees) from where the prey looks. Far out: a path leg with the flank cost profile (section 8) to a spot scored over the path nodes: near the wanted point, about `HoundHold` from the prey, far round from its view (+300 outside the front cone), not next to another hound (`MateSpacing`), with a straight run to the prey. Inside 600: zig-zag legs. In place (more than `HoundFlankAngle` - 35 round, under 700 away): keeps its angle as the prey turns and moves. |
| **closer** | the one committing the leap | A flanker outside the prey's front cone (`HoundCommitFront` 120, narrower the angrier the pack); or the holder when the prey is **pinned**; or, after `HoundHoldMax` (6 s, shorter the angrier) with no flanker in place, the nearest. It takes the pack's melee token (the others lose theirs: only the closer may leap or bite) and charges (`DoCharge`, 4 s). One closer at a time; two when the prey is pinned and the pack is three or more. |
| **skirmisher** | a lone hound | Holds and skips like the holder, commits when the prey is pinned or the hold runs out. |

**Skipping** (`SkipLeg`): inside 600 units every move is a leg of `HoundSkipLeg` (200, x0.75..1.25) at `HoundSkipAngle` (45 +-10 degrees) off the line to the goal, left and right by turns, to a point traced clear of walls, with a floor under it no more than 70 below the hound's, and not within 230 of the prey. `HoundSkipDodge` (0.3) of the legs are the engine's own dodge (`Bot.DoDodgeDir`: the hound has `Dodge_L/R/F/B` clips, root motion). A leg ends on arrival or when the move ends, then a dwell of 0.1-0.3 s. Both sides blocked: a straight leg to the goal, never a stall.

**Pinning:** a trace `HoundPinWall` (300) behind the prey, behind its movement when it moves, away from the holder when it stands: a hit pins it (logged `hounds: pin: a wall N behind the prey`), and the holder commits. Flank sides alternate so a pack of three keeps a hound on each side of the prey.

**Feelings** keep charge: fear past `FleeFear` sends that hound to the pack's rear (its centre, 500 further from the prey) and out of the roles; anger narrows the commit cone (-30 % at full anger) and shortens the hold (-60 %), and the existing enrage still charges an angry hound that holds the token. `ModBody` shows the roles: a flanker slinks with its head 8 degrees lower, a holder 4, a committing closer drives its neck forward and the jaw opens.

**Settings** (`[AdventMod.ModMinds]`): `bHoundPack` (on; off = the old circle-then-charge), `bHoundLog`, `HoundHold` 380, `HoundFlankAngle` 120, `HoundSkipLeg` 200, `HoundSkipAngle` 45, `HoundCommitFront` 120, `HoundHoldMax` 6, `HoundSkipDodge` 0.3, `HoundPinWall` 300.

**Pilot:** `HOUNDTEST [seconds]` logs every hound's role, task, distance and bearing round the player's view twice a second, and `houndstats:` every 5 s and at the end: first bite after the first hound engaged, bites and their damage, the bites' mean bearing (flank bites should raise it), melee contacts, the time hounds stood on two or more sides of the player (front, back, left, right within 900) as a share of the time any hound was engaged, legs skipped, flank arrivals, commits, pins. `SPAWNPACK n [ahead] [spread]` spawns n hounds in a squad of their own that know the player at once (a pawn spawned alone has no squad; the level's own hounds come from spawners later in each map, none at a start), `NEARENEMY dist [class]` puts the player by a hound, `HEALTH n` keeps it alive through a long fight. `MINDLIST` shows roles.

**What the runs taught** (fixed before the A/B): `SquadAI.AssignState` refuses a second state change in the same frame and the game's own `WhatToDoNext` often runs first, so a `DoMoveToDestination` or `DoCharge` from the mind silently did nothing; every move now goes through `Go` (checks the bot is in `MoveToDestination` on our plan, compared flat since the engine moves the destination's height, and gives it again after 0.4 s if not; giving it every tick restarts the `MoveTo` before it can step). A closer's charge is given again the same way. Spawned hounds were left hanging by the game in `MeleeAttack`/`LeapAttack` for 10-30 s on the ground far from the enemy; `Busy` no longer counts that. A pack hound's `NextDecision` is set by `Decide` every tick, so the pack's legs are gated by their own `LegAt`. Commits are rate-limited (1.5 s per pack, 3 s per hound, only within 750 of the prey) because the game drops the hound's enemy for a tick now and then, which ended the charge task and dealt a new closer at once.

**Test** (scratchpad `hound_pack_test.ps1`, level03sectionb's start, `SPAWNPACK 3 700 250`, the player unarmed, since `GIVE` did not put the pistol in hand: the game's hounds then guard and nip for 10, `SeekerDogBot.TryMeleeAttack`, the same in both arms): six runs each, the same steps, six HOUNDTEST watches of 6-8 s between which the player backs off, sidesteps and dodges, about 48 s. Each run 108-109 s with a hidden UnrealEd path build on the CPU at the same time. Bites and damage are the game's own (a leap that lands); "two sides" is the share of the time any hound was engaged (within 900) with hounds on two or more of front/back/left/right.

| run | pack | first bite (s) | bites | damage | bite bearing | two sides | legs | arrivals | commits | pins |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | on | 10.4 | 13 | 130 | 116 | 45 % (21/46 s) | 35 | 4 | 20 | 8 |
| A2 | on | 0.0 | 1 | 10 | 20 | 41 % (5/12 s) | 4 | 0 | 2 | 3 |
| A3 | on | 6.5 | 5 | 50 | 107 | 51 % (20/38 s) | 34 | 4 | 11 | 4 |
| A4 | on | 2.7 | 4 | 40 | 49 | 12 % (2/14 s) | 0 | 0 | 0 | 9 |
| A5 | on | 16.6 | 4 | 205 | 99 | 0 % (0/22 s) | 4 | 0 | 6 | 10 |
| A6 | on | 43.0 | 3 | 30 | 103 | 15 % (7/48 s) | 34 | 1 | 18 | 10 |
| B1 | off | none | 0 | 0 | - | 16 % (5/32 s) | - | - | - | - |
| B2 | off | 5.0 | 2 | 20 | 159 | 54 % (18/34 s) | - | - | - | - |
| B3 | off | none | 0 | 0 | - | 47 % (22/46 s) | - | - | - | - |
| B4 | off | 2.7 | 3 | 30 | 57 | 20 % (7/35 s) | - | - | - | - |
| B5 | off | 0.7 | 5 | 620 | 68 | 69 % (34/48 s) | - | - | - | - |
| B6 | off | 0.0 | 2 | 12 | 64 | 28 % (14/48 s) | - | - | - | - |

| | pack on (6 runs) | pack off (6 runs) |
|---|---|---|
| bites, damage | 30, 465 | 12, 682 (620 of it in B5) |
| mean first bite | 13.2 s | 2.1 s (4 runs; none in 2) |
| mean bite bearing (bite-weighted) | 99 degrees | 80 degrees |
| hounds on two or more sides (time-weighted) | 31 % (55/180 s) | 41 % (100/243 s) |
| legs skipped, flank arrivals, commits | 111, 9, 57 | - |

Reading: the pack bites more often and more from the sides and back (99 vs 80 degrees, 30 vs 12 bites), and the hold works as designed (the first bite comes later: the holder waits for a flanker or a pin). Pinning fires (44 pins: the player starts with its back to a wall and backs into it). What did not improve is the two-sides share: the stock circle-then-charge throws three hounds round the player too, and in the pack runs hounds were lost to the arena (A4 and A5: two hounds fell to a kill volume, 1000 damage; A2, A5: the game dropped the player as enemy when it backed round the start corner, and a pack hound with no enemy sits out). The far flank leg also failed often at this start (a flanker stuck at 1900 with `route None`: `NextLeg` falls back to a straight `MoveTo` when `FindPathTo` has no route). The runs are noisy (six each, a cramped start area, other NPCs about): the direction is right for flanking and holding, not proven for pinning. Next: a run on an open arena with the level's own hound packs (level03sectiond, level06sectionb have spawners), an armed player (why `GIVE` leaves the hand empty), a flanker that re-plans when its path leg stalls, and a prey the pack keeps for a few seconds after the game drops it.

## 10. Wall-kicks and leap links (built and run 2026-10-09)

The RAGE hopper's move for the hounds, from the research note `games/reports/RAGE mutant wall and ceiling navigation.md`: a leap to a wall, a plant, a leap off it at the prey. The game's Seekers own the whole chain in stock script (`TryLeapToWall -> Leap -> CheckWallJump -> WallJumpBegin -> WallJumpEnd -> RequestLeapOffWall`), and the hound inherits it (`SeekerDogNative extends Seeker`), but never uses it: its `WallJumpAbility` is 0, and the only wall-jump clips it "has" are the upright Seekers' `WallJump_L/R`, which fold a quadruped wrong. So the mind drives the move from script and keeps the engine's test out (`Seeker.wallJumps` is set to 4 for the flight, which `CheckWallJump` refuses; it resets on landing). Code: `ModMinds.FindKickWall`, `StartKick`, `KickTick`, `KickPlant`, `KickLeapOff`, `BuildLinks`, `LinkOnRoute`, `LinkKick`; `ModLeapLink.uc`.

**The kick.** A wall is looked for within `WallKickRange` (700), 45 then 70 degrees either side of the line toward the target, on a line pitched up 16 degrees as the stock `TryLeapToWall` aims (so the plant point is above the hound). It must be world geometry at least 150 away, its normal in the band the stock `WallJumpBegin` takes (`-0.17 <= n.z <= 0.5`) and facing the target (the leap off must go out from the wall, as `RequestLeapOffWall` demands). The plant point is the hit, out by the hound's radius. Both arcs, to the plant point and off it to the target, are solved in closed form by time (the ground distance at the hound's `DesiredLeapSpeed`, the rise from the time and the drop; gravity is 3000 in this game) and swept with 70 % of the hound's body in six segments (Doom 3's `TestTrajectory`); either blocked and the wall is passed over. Then:

1. *to the wall:* `Pawn.DoJumpTo(plant)` (the engine's leap: its jump clip, the bot turned at the point) with the velocity replaced by the swept arc; the bot is given `Wait` for the flight. Each tick: at the plant point (within radius + 30), or past the apex and touching the wall (the stock `CheckWallJump` trace, `Velocity.Z < 30`), it plants; landed first, or the flight time plus 0.4 s gone, the kick is off ("landed short", "missed the wall").
2. *planted:* `PHYS_None`, velocity zero, snapped to the plant point when within 80, turned flat at the target, the hips pitched up 35 degrees (`SetBoneRotation`, which ModBody leaves alone while the hound is not walking) and its leap crouch clip (`jump_start`), for `WallKickPlant` (0.15 s).
3. *off the wall:* at the prey (re-aimed now: a little ahead of it, up to its chest, as the stock `LeapAttack` aims) by `DoLeapAttackTo`, so the engine's air attack bites on contact; or to a spot by `DoJumpTo`. `PHYS_Walking` is set first, as the stock `RequestLeapOffWall` does (`DoJump` wants it). Done on landing: a closer's charge is given again at once, a leg goes on from where it landed.

**Who kicks.** The closer, when it commits (`HoundCommit`), with `WallKickChance` (0.6) when a wall fits: the leap at the prey comes off the wall instead of a straight charge; the charge follows the landing. A flanker inside 600 of the prey, instead of a skip leg, with half that chance: a wall on its outer side (the search is centred away from the prey), the leap off to its flank spot. One kick per hound per `WallKickCool` (4 s); a failed search looks again after a second. `Busy` is true mid-kick, so the pack deals it nothing else.

**Leap links** (`ModLeapLink`, the report's Rule 1), built once per level from the path graph, three nodes a tick from the level's first tick, placed as hidden actors at their plant points: two nodes within 1.5 x `WallKickRange` of each other (not stacked floors: 160 up or down at most) whose walk route is at least 2.5 x the straight line, or none within that cutoff (a Dijkstra over the `ReachSpec`s per node, indexed through `visitedWeight`), a wall beside the straight line (traced from its midpoint to either side, a hound's height up, out to 0.6 x the range) whose normal fits the band and faces the far node, and both arcs clear for a hound's body (the hound's size and leap speed from `SeekerDog`'s defaults). The best `LeapLinksMax` (40) by saving (route / straight) are kept; a link is two-way when the reverse arcs pass too. Use: in `NextLeg`, after the engine's route is found, a hound's plan is checked for a link whose near end is among the route's first four nodes and whose far end comes two or more nodes later (or whose way via the wall is less than half the rest of the route); the leg then goes to the near end, and `Decide`'s leg handling kicks from there to the far end (the arc checked again at that moment), the leg going on from the landing. Hounds only.

**Settings** (`[AdventMod.ModMinds]`): `bHoundWallKick` (on), `WallKickRange` 700, `WallKickChance` 0.6, `WallKickPlant` 0.15, `WallKickCool` 4, `bWallKickLog` (every kick, plant, leap off and miss as `wallkick:` lines), `bWallKickBackOff` (off: see below), `bLeapLinks` (on; needs the kicks on), `LeapLinksMax` 40.

**Pilot:** `LEAPLINKS` lists the level's links (ends, straight and route lengths and their ratio, the wall, two-way, uses); `WALLKICK` makes the hound nearest the player kick off a wall at it now, switch and cooldown or not (the `wallkick:` lines say where it went wrong). `HOUNDTEST`'s `houndstats:` adds `wallkicks N planted N leaps N kickbites N` (bites within 1.5 s of a leap off) and `links N used N`; each hound's line shows `kicks tried/planted/leapt` and its kick phase.

**Test** (scratchpad `hound_wallkick_test.ps1`, the pack A/B's steps with `bHoundWallKick` on or off, `-Probe` for the mechanics alone with one hound and `WALLKICK` forced six times, `-Goto X Y Z` for an open spot with walls): wall-kicks attempted / planted / leapt off, bites after a kick, flank arrivals via links, and the A/B against kicks off: bites, bite bearing, time to first bite, 3 + 3 runs on level03sectionb's start and the open spot. The engine's own wall test on a hound would show as `checking wall jump` lines in advent.log (Seeker.CheckWallJump logs it); the harness greps for them.

**Results** (2026-10-09, the same steps as the pack A/B, 3 + 3 at level03sectionb's start and 2 + 2 at an open room with walls (`GOTO -6019 7145 -986`, PathNode79, where five links meet), ~105 s each; kicks counted from the `wallkick:` lines over the whole run, the rest from the last `houndstats:`):

| run | kicks | first bite (s) | bites | damage | bite bearing | two sides | kicks tried / planted / leapt off / failed | bites within 1.5 s of a leap off |
|---|---|---|---|---|---|---|---|---|
| A1 start | on | 4.8 | 12 | 310 | 99 | 29 % | 6 / 5 / 5 / 1 (landed short) | 3 |
| A2 start | on | 1.2 | 7 | 640 | 80 | 87 % | 0 (no wall fit) | 0 |
| A3 start | on | 2.0 | 5 | 42 | 134 | 69 % | 8 / 7 / 7 / 1 (the engine took the body mid-flight: PHYS_RootMotion) | 1 |
| B1 start | off | 2.7 | 3 | 220 | 141 | 0 % | - | - |
| B2 start | off | 10.0 | 4 | 230 | 84 | 20 % | - | - |
| B3 start | off | 1.6 | 14 | 900 | 115 | 76 % | - | - |
| A1 open | on | 27.7 | 4 | 40 | 134 | 47 % | 2 / 1 / 1 / 1 (missed the wall by 99) | 0 |
| A2 open | on | 1.0 | 9 | 90 | 117 | 32 % | 2 / 2 / 2 / 0 | 1 |
| B1 open | off | 9.6 | 12 | 120 | 147 | 58 % | - | - |
| B2 open | off | 1.3 | 7 | 242 | 101 | 84 % | - | - |

Reading. **The move works:** 18 kicks in the five A runs, 15 went the whole way (wall reached in 0.2-0.3 s, planted 65-90 from the plant point, leapt off 0.15 s later, landed 0.6-0.8 s after that, a median 130 from the target, 12-700), 3 failed cleanly (one landed short of a wall 616 away, one missed by 99, one lost its body to an engine clip mid-flight: all end with the hound on the ground and its task back). Five bites came within 1.5 s of a leap off. No crash, no hound left hanging, no `checking wall jump` from the engine's own test. One flank kick to a flank spot in each of three runs landed 54-171 from the spot. **It is too rare to move the A/B:** about one kick per hound per 30 s; bites (24 for 992 against 21 for 1350 at the start, 13 for 130 against 19 for 362 in the open room) and bearings are within the noise of six-hound-minute samples, and the first bite is not earlier. The wall search fails mostly on *nothing* (no wall within 700 at 45/70 degrees: the hounds fight in the middle of rooms) and *too near* (the hound is already against a wall, under 250: the spot the pack's skipping puts it in). **Links were never taken:** all 19 links on this map join nodes with *no* walk route between them (SpawnPoints and PathNodes across a gap or a wall), so no bot route lists both ends; the detour pairs Rule 1 is written for (route 2.5 x straight, both ends on the graph) do not occur here.

Next, in order: links whose far end is only *near* the route's goal (the second rule, loosened); a map with real detours (level03sectiond, level06sectionb have hound spawners and bigger rooms); the plant waiting out a hit reaction that lands mid-flight.

**Built offline 2026-10-09, not yet run** (the first three of the list above; a GPU session tests them with `hound_wallkick_test.ps1` and `WALLKICK`):

- *Eight directions.* When the 45/70-degree pairs find nothing, `FindKickWall` goes on round the hound every 45 degrees (0, 90, 135, 180, 225, 270: the pairs' +-45 are not traced twice), pitched up as the pairs' first four are. The `walls:` log line shows them after a `| 8-dir:` mark. Behind `bHoundWallKick` as before: the same move, found more often.
- *A wall it stands against* (`bWallKickBackOff`, **off** until seen). `FindKickWall` now counts what the walls answered (`KickTooNear`, `KickOtherWalls`, the nearest too-near hit and its normal). When at least one wall was "too near" and no wall was refused for any other reason, `TryKick` gives the hound a short skip leg (`T_Skip`, `bKickBackOff`, `Mind_KickBackOff`, 1.5 s) flat along that wall's normal to 300 + 40 from it (traced clear, a floor under it, not within 230 of the prey when the kick is an attack), logged `backs off a wall N away (commit): M to go`; when the leg ends (arrived within 90, stalled, or timed out) `KickBackOffDone` tries the same kick once more (`, backed off` in its log line; no second back-off). No wall then either: a closer charges as it would have (`commit without the kick`), a flanker takes its next leg. Meanwhile a backing-off closer still counts as the pack's committing closer (no second one is dealt) and keeps its role through the 1.5 s deal; a flanker's back-off stands as its skip leg (the `flank kick` task isn't set over it). Without the room to back off (a corner): `no wall (...), and no room to back off the one N away`.
- *No kick in a hit reaction.* `TryKick` asks `ModReact.IsFlinching` (found once by lookup; none with the gore off) and refuses while the hound is in a spring flinch (`no kick while flinching`, another look in 0.5 s): the engine's hit clip is what took a body mid-flight in A3.

To test: `bWallKickLog` on, `WALLKICK` with the nearest hound put against a wall (`NEARENEMY` by a wall, or `GOTO` the player to a corner so the holder's ring is against it): expect `walls: ... too near N` then, with `bWallKickBackOff=True`, `backs off a wall`, a leg of about 100-250, and a `kicks (pilot, backed off)` or the `no wall` line with the 8-dir answers; the A/B as in the table above with the back-off on, counting kicks tried / planted and the `backs off` lines; and a run with the player firing at a hound as it commits, looking for `no kick while flinching` and no `physics changed to` line.

**Known limits.** The plant is a pose, not a clip: the hound's own set has no wall clip, so it holds its leap crouch with the hips pitched; the kick's second leap re-aims at the prey from the wall, so a prey that moved far since the commit gets a leap that goes where it is, not where it was. Links are tested with a hound's size at level start, from a hidden actor's traces: a door that opens later or a mover in the way is caught by the arc check at kick time, which then walks. Nothing native: the engine's `FindPathTo` does not see the links (the report's route 4a.2, a special `ReachSpec`, is the later step), so a link is taken only when the route already passes its near end.


## 11. Needs and advertisements (built, wired and run 2026-10-09)

The user's reading of the Trespasser report (section 3a, "borrow first" item 1): its dinosaurs oscillated because a state machine summed live emotions every frame with no commitment; what it "should have done" is a Sims needs system: slow internal clocks that make a creature want something when nothing is happening, things in the world that advertise what they satisfy, and a chosen activity that is finished before another is weighed. ModMinds' feelings are reactions (what just happened); this layer adds drives. Code: `ModNeeds.uc` (an Info, one per level; its own per-pawn records, keyed by `Pawn`, and the ad list; it finds `ModMinds` by lookup and reads each creature's `ModMind` for species, feelings, task, role and enemy). It moves no pawn: its result is a request `ModMinds` reads.

**Needs** run 0..1 per creature, by species:

| species | needs |
|---|---|
| human | Fatigue, Curiosity, Safety |
| Seeker, veteran | Aggression, Fatigue, Curiosity |
| hound | Hunger, Fatigue, Curiosity, Safety |
| construct, other | none (not adopted) |

| need | rises | falls |
|---|---|---|
| Hunger | on its own, `HungerRise` 0.0033/s (full in five minutes); a new hound starts at 0.2-0.4 | feeding at a corpse (its offer, 0.6) |
| Fatigue | `FatigueRise` 0.012/s while running (over 55 % of `GroundSpeed`), charging, skipping or wall-kicking | `FatigueRest` 0.02/s while standing (under 20 %); resting at cover or a resting place |
| Curiosity | `CuriosityRise` 0.0167/s while nothing happens (no enemy, no hit or near miss for 5 s) | `CuriosityRest` 0.05/s while something does; looking at a noise (its offer) |
| Safety | toward max(Fear, 0.7 x Pressure) at 2/s when that is higher | `SafetyRest` 0.03/s, twice that while pinned or in cover; reaching cover, or a mate |
| Aggression | toward Anger when that is higher; `AggressionRise` 0.02/s while an enemy is known | 0.3/s while charging |

Testing: `ForceHunger`, `ForceFatigue`, `ForceCuriosity` hold a need at a value (-1 = free).

**Advertisements** are `{id, kind, location, actor, owner, offer per need, radius, expiry}` in a list of at most 32 (full: the one expiring soonest goes). Each is posted by something in the world:

| ad | offers | radius, life | posted by |
|---|---|---|---|
| **corpse** (a dead pawn) | Hunger 0.6 (hounds), Curiosity 0.25 | 1600, 90 s | `PostCorpse` (ModMindRules.ScoreKill, Phase B); until then a scan every second for pawns with no health |
| **cover** (one creature's spot, from `ModMinds.FindCover`, so it is claimed there too) | Safety 0.7, Fatigue 0.3 | 1500, one query's life | `FindOwn`: every `CoverEvery` 3 s when it has an enemy and Safety > 0.35 or Fatigue > 0.5 (not hounds) |
| **noise** (the player's last known position; a shot, where the shooter stands; later the gore, a door) | Curiosity 0.3 + 0.5 x loud, Aggression 0.4 x loud | 1000 + 1000 x loud, 8 s | `PostNoise`: the player every second while any creature has it as enemy (refreshed, one ad), one shot a second from `ModMinds.Shots` |
| **resting place** (where it stands, no enemy about) | Fatigue 0.6 | 400, 10 s | `FindOwn`: Fatigue > 0.4 |
| **pack mate** (virtual: never posted, the pack would fill the list) | Safety 0.6 | 2000 | scored at choice time: the nearest living squad mate further than 300 (hounds) |

**Choice**, every `DecideEvery` 0.5 s per creature: each ad in reach scores sum over its needs of need x offer x falloff (1 at the ad, 0.5 at its radius); ads owned by another creature, and the ad it was just satisfied by (15 s), score nothing. The ad it is on gets `CommitBonus` 0.25, and nothing replaces a want younger than `MinRun` 3 s unless its ad has gone. Below `WantMin` 0.12 it wants nothing. The winner becomes the want: `Feed` (a corpse), `Rest` (cover, a resting place), `Investigate` (a noise), `Regroup` (a mate), logged (`bNeedsLog`) as `needs: SeekerDog3 hunger .62 fatigue .30 curiosity .10 safety .05 -> feed at corpse of Marine2 740 away (score 0.41, 0.0 s)`. **Satisfaction**: ModMinds' `Satisfied(P)` when its want leg arrives (within 140 of the spot it was given: a corpse's ragdoll slides from where the ad was posted), or ModNeeds' own test, within `ArriveReach` 220 of the ad for `ArriveTime` 1.5 s while the creature has nothing else on (standing beside the body mid-fight is not a meal); the ad's offer comes off the needs; a corpse is eaten a bite at a time (a third of its offer per feeding, gone under 0.05), a noise looked at is done with, cover and resting places stay. ModMinds calls `GiveUp(P, why)` when the want's task ends unfinished (the ad is then avoided 6 s).

**What the others read:** `Want(P, out At, out Target)` (0 none, 1 feed, 2 rest, 3 investigate, 4 regroup), `WantAge(P)`, `NeedOf(P, need)`; for the pack `HuntDrive(P)` = 0.2 + 0.8 x Hunger for a hound (0.6, the stock pack, for anything without a record): a fed pack stalks longer and commits only from the side, a starved one commits early and from in front; `WantsTell(P)`: a holder or skirmisher with Hunger over 0.6, not charging: the stalk croon before the leap (the sound: below). `List()` prints every creature and every ad (`needslist:` lines) and returns a summary; `Command("list|on|off|log on|hunger V|fatigue V|curiosity V|noise|noise near")` for the console (`noise near`: a noise 400 from the nearest creature free to act on it, the investigation test). The list shows each creature's task, Bot state and whether ModMinds would act for it (`busy`).

**Settings** (`[AdventMod.ModNeeds]`): `bNeeds` (on since the runs below; off = ModMinds alone, the pack as in section 9), `bNeedsLog`, `DecideEvery` 0.5, `CommitBonus` 0.25, `MinRun` 3, `WantMin` 0.12, the rates above, `CorpseFeed` 0.6, `CorpseLife` 90, `NoiseLife` 8, `RestLife` 10, `CoverEvery` 3, `ArriveReach` 220, `ArriveTime` 1.5, `ForceHunger`/`ForceFatigue`/`ForceCuriosity` -1. In `[AdventMod.ModMinds]`: `bWantReplan` (on), `bHoundRest` (off), `HoundRestFatigue` 0.7 (both below).

**Wiring** (applied 2026-10-09):

1. *ModMutator*: `var ModNeeds Needs;` spawned in `Every` after Minds (`if (!bGraphicsOnly && Needs == None && PC != None && Level.Game != None && !Level.Game.IsInFrontEnd) Needs = Spawn(class'ModNeeds');`); in `Mutate`: `if (Caps(Left(MutateString, 6)) == "NEEDS " && Needs != None) class'ModSettings'.static.Note("needs: " $ Needs.Command(Mid(MutateString, 6)));`.
2. *ModMind*: `const T_Want = 10;` (`TaskName` "want"), `var float TellAt;`.
3. *ModMinds*: `var ModNeeds Needs;` (set by ModMutator, or found once by `foreach DynamicActors`). In `Decide`, **before** `if (Enemy == None || Busy(M)) return;` (an idle creature never gets past it) and only for a calm one: `M.Task == 0 && M.Role != R_Closer && !Busy(M) && Now >= M.NextDecision && M.Pressure < FreePressure && M.Fear < FleeFear && M.Anger < ChargeAnger && (Enemy == None || (M.Species == S_Hound && VSize(Enemy.Location - M.P.Location) > 650))` (a hound may feed or regroup in a lull: the prey beyond 650, which a hold at `HoundHold` 380 is not; the melee token is no bar, it says who may attack and a feeding hound attacks nobody, and with two hounds both hold one all the time): `W = Needs.Want(M.P, At, Target); if (W != 0) { M.TaskDest = At; SetTask(M, T_Want, 8, "wants " $ Needs.WantName(W)); if (W == 2 && VSize(At - M.P.Location) < 160) M.B.DoWait('Mind_Rest', 2); else M.B.DoMoveToDestination('Mind_Want', NextLeg(M, At)); return; }`. In the keep-going `switch`, `case T_Want:` as the FallBack/Flank legs (re-issue the leg through `Go`; within 140: `Needs.Satisfied(M.P)`, `M.Task = 0`, `DoWait('Mind_Arrived', 0.6)`); the task ends (`GiveUp`) on its 8 s limit, a hit in the last second, pressure past `FreePressure`, an enemy for anyone but a hound, or the prey under 400 for a hound. In `HoundPack`, a member on `T_Want` is dealt no role and no leg (as `Busy`) while the pack has no closer, so a feeding hound is left to it until the pack commits; and the drive: `Drive = 1; if (Needs != None) Drive = mean over the members of Needs.HuntDrive(O.P);` then `Front *= (1.3 - 0.5 * Drive); Hold *= (1.6 - Drive)` (drive 0.2: cone x1.2, hold x1.4; 0.6, which is also the value with the needs off or for a hound with no record: x1, x1, the stock pack; 1: x0.8, x0.6), logged with the pack's `held N of M s, drive D` line. A member on `T_Want` is left out of the pack's members (no role, no leg) until its want ends. The tell: where the holder's feint leg is given, `if (Needs != None && Needs.WantsTell(O.P) && Now - O.TellAt > 4) { O.TellAt = Now; HoundLog(O.P.Name $ " croons (hunger " $ ...)"); }`, and the sound (added offline 2026-10-09, `ModMinds.Croon`, `bCroon` on): the hound's own stock growl. `SeekerDog`'s set (exported script, `EonCharacters.SeekerDog` defaults) has `SS_Attack` = `character.sdog.Attack` (the bite bark), `SS_Charge` = `character.sdog.charge`, `SS_Growl` = `character.sdog.growl`, `SS_snarl` = `AIVoices.sdog.Member_KilledEnemy` (a squad line, and its `pawnSoundEvent` case plays nothing), grunts, taunts, pain and death; `growl` is the one idle vocal that is neither the bark nor the charge call, so the croon plays it: `P.PlaySound(growl, SLOT_Talk, CroonVolume 0.5, false, 1200, pitch 0.9-1.1)` at the existing 4 s rate. The sound is loaded once by name (`CroonSound`, default `character.sdog.growl`; a `croon:` log line says what was found), and when the name fails the hound's own `SS_Growl` stands in; neither and the tell stays a log line (`(silent)` on the `croons` line). Not heard yet (built without the game): the GPU session should listen for it on a starved pack (`ForceHunger=0.9`) and judge the volume; the clip's length is unknown offline (umodel can't open Advent's `.uax`: "Serialized FString is not null-terminated").
4. *ModMindRules.ScoreKill*: `if (Minds != None && Minds.Needs != None && Killed.Pawn != None) Minds.Needs.PostCorpse(Killed.Pawn, Killed.Pawn.Location);`.
5. *ModPilot*: `NEEDSLIST`, and `NEEDS <cmd>` passing the rest of the step to `N.Command` (both through `NeedsCommand`).

**Runs** (scratchpad `needs_test.ps1`, level03sectionb's start, hidden, 17 runs of 75-110 s; `bNeedsLog`, `bHoundLog` on; every run: no crash, no `Critical`, and **0** `accessed None` lines in advent.log). Three things were fixed between runs and are in the text above: the want was finished by ModMinds' own arrival (feed1: the hound reached the spot, the corpse had slid 66 units, the feed never fired); the melee-token gate came out of the lull (feed2: two hounds, both with a token, wanted the corpse for 90 s and never went); the self-detected arrival counts only when idle (feed3: hounds "fed" beside the body in the first seconds of the fight).

*Feed* (`SPAWNPACK 3 700 250`, `HURT 2000` kills the nearest hound 4 s in, the player backs off between watches; feed4 and feed5 on the final code): the corpse ad is posted by ScoreKill the moment the hound dies (`ad: corpse of SeekerDog3 ... (feed 0.60)`) and both survivors want it within a second (`hunger .31 ... -> feed at corpse of SeekerDog3 703 away (score .14)`). feed4: `SeekerDog1 -> want (wants to feed 310 away)` as the holder when the prey was far, `feed done ... hunger .31 -> .00` half a second later, and it was out of the pack's roles meanwhile (`pack of 1`); feed5: the other hound's want ran its 8 s standing in `MoveToDestination` 1340 from everything, the stuck-leg case of section 9 (no route from the corner), and was given up cleanly. feed1 (before the fix): the same want reached its spot but did not feed. Hunger climbs as designed (0.26 to 0.63 over 80 s of a run); a hound's fatigue hits 1.0 after a minute of skipping and charging, which nothing rests yet (hounds get no cover ad and a resting place needs no enemy).

*Starved against fed* (the section 9 pack steps with `ForceHunger` 0.9 and 0.1, two runs each; the drive 0.91 against 0.28):

| run | hunger | hold (s, as logged) | commits: flanker / pinned / held out | bites, damage | first bite | croons |
|---|---|---|---|---|---|---|
| starved1 | 0.9 | 1-2 (36 of 48 samples) | 7 / 11 / 1 | 8, 80 | 2.7 s | 17 |
| starved2 | 0.9 | 1-2 (45 of 48) | 13 / 18 / 5 | 7, 450 | 6.0 s | 19 |
| fed1 | 0.1 | 3-7 (3 s: 13, 4 s: 12, 5-7 s: 14) | 0 / 20 / 0 | 5, 240 | 3.4 s | 0 |
| fed2 | 0.1 | 3-7 (7 s: 29 of 48) | 0 / 2 / 6 | 2, 20 | 3.2 s | 0 |

The hold shortens with hunger as designed (1-2 s starved, 3-7 s fed) and the starved packs commit more often from the flank and bite more (15 bites against 7); the fed packs' commits are nearly all the pin (this start has the player's back to a wall), so the "held out" reason is the small signal. The croon fires only starved (a holder with hunger over 0.6), every 4 s while it holds: the place for the stalk sound. Fed hounds filled the lulls with wants (fed1: 19 want tasks, 14 given up as the prey came back inside 400): a fed pack that is not fighting goes and looks at the player's last known position, which is close to Trespasser's "sated ones may not attack".

*Marines* (the start's three Spec Ops, `ForceCuriosity=0.8`, a noise posted twice; marines6-8 on the final code): `SpecOpsSoldier0` wants to investigate every time and never goes, correctly: it is in the game's `Scripting` state (the start's scripted follower), which `Busy` refuses (the list line shows it: `state Scripting busy True`). With the noise at the player, the two idle marines (`CoverPoint`, `MoveAside`) were out of its 2000 reach; with `noise near` (400 from the nearest free creature) `SpecOpsSoldier21` walked to it and looked both times in both runs (`investigate done ... 138 away`, `looked 2`), and `SpecOpsSoldier1` wanted it each time and set off (`task want state MoveToDestination`) but arrived once in four: the Bot takes a leg with no enemy, but the second marine's leg stalls (the first stands on the spot; no re-plan yet). Idle marines also rest where they stand once the chase after the player has tired them (`wants to rest`, `DoWait` 2 s): with the old fatigue rate every 22 s, which is why it is 0.012 now.

**Built offline 2026-10-09, not yet run** (the first two known limits below; a GPU session tests them with `needs_test.ps1`):

- *Want legs that re-plan* (`bWantReplan`, on: it only changes what a stalled leg does, which was to stand 8 s). A `T_Want` leg keeps its best flat distance to its spot (`ProgressBest`, `ProgressAt`, reset by `SetTask`); 1.5 s with no gain of 25 or more and it re-plans **once**: `WantWaypoint` picks a path node within 1000 that the creature can run straight to (a trace at hip height), nearer the ad than it is by 100 or more, the nearest to the ad with the run to it weighed 0.3, and the leg goes there (`Mind_WantReplan`, logged `want leg stalled N from its spot: re-plans via a node ...`); from the node the usual `NextLeg` goes on. A second stall, or no such node, gives the want up (`Needs.GiveUp(P, "leg stalled")`, the ad avoided 6 s, `... gives up`). The flank legs keep their old behaviour (section 9's "next" item still).
- *A rest for hounds* (`bHoundRest`, **off** until seen; `HoundRestFatigue` 0.7). In `HoundPack`'s move loop, a member that is not the closer, with no closer committing, the prey beyond 450 and its Fatigue over the threshold, takes `T_Rest` (`Mind_ToRest`, 6 s): a leg to the pack's rear (the pack's centre, 400 further from the prey), and on arrival (within 140) a `DoWait('Mind_Rest')` of 1-2 s (`bResting`, the task's limit set then; logged `tired (fatigue N): rests at the rear` and `rests N s`). While it rests, `ModNeeds.Decay` takes fatigue down at 5 x `FatigueRest` (0.1/s: 0.1-0.2 per rest, against 0.012/s rising while it skips and charges), so a hound that rests every 8 s or so (`RestAt`) holds its fatigue near the threshold instead of pinning at 1.0. A resting hound is out of the pack's roles (as a feeding one is) and the rest ends at once on a hit or the prey inside 400.

To test: `ForceFatigue=0.9` with `bHoundRest=True` and `bHoundLog`, the pack steps: expect `tired ... rests at the rear` lines between commits, hounds standing 1-2 s behind the pack, `needs:` lines with fatigue falling (`ForceFatigue` off for that: `NEEDS fatigue -1` after a forced start), and the pack's hold unchanged in the `held N of M s` lines; and the marines' noise test (`noise near`): `SpecOpsSoldier1`'s stalled want should now show `re-plans via a node` and arrive, or `gives up` within 3.5 s instead of 8.

**Known limits.** A want leg is one `MoveToDestination` re-issued through `Go`: it stalls where the pack's flank legs stall (no route, a mate on the spot); with `bWantReplan` it re-plans once (above), and runs out at 8 s. Hounds rest fatigue in a fight only with `bHoundRest` (above). A dead player posts a corpse ad too (the scan takes any pawn with no health that is not a player's, and a dead pawn has no controller). The scan finds bodies the moment they die as ScoreKill does, so the two post the same ad once (the second is dropped within 100 units). The croon is a log line until a hound stalk sound is found in its set.
