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
- Tuning: `TraitSpread`, `PinPressure`, `FreePressure`, `FleeFear`, `PanicFear`, `ChargeAnger`, `CoverReach`, `NearMissReach`, `FlankEvery`, `HoundCircle`.
- Pilot command: `MINDLIST` (every mind's feelings, task, shots past and hits).

## 5. Tests

See the end of this file once the in-game runs are in.

## 6. Known limits and ideas

- Only creatures in a squad are adopted. A pawn the pilot spawns has none, and the Bot's `Do*` functions need one.
- Moves are straight `MoveTo` legs. Cover must be in a straight line, and flanks and fall-backs re-path each leg.
- Not yet: suppression on the player's allies from enemy fire (it works for any instigator that is the creature's enemy, but it's untested); voice barks for the feelings (the game has `pawnSoundEvent` lines such as EnragedGrunt); a director that paces encounters by the player's stress; fixing the three stock bugs (Crouch.BeginState calls Super.EndState, LocateNearbyCoverPoint has no None check, Frustration over-increments).
