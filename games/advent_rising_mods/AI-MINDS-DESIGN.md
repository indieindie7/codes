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
- Tuning: `TraitSpread`, `PinPressure`, `FreePressure`, `FleeFear`, `PanicFear`, `ChargeAnger`, `CoverReach`, `NearMissReach`, `FlankEvery`, `HoundCircle` (packs off); the hound pack's own are in section 9.
- Pilot command: `MINDLIST` (every mind's feelings, task, shots past and hits; a hound's pack role).

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

