# SWAT 4 modding notes

Started 2026-10-17 (chat "SWAT 4 AI study"). Inputs: `HANDOFF-FROM-ADVENT.md` (this folder), `C:\re\devastation\HANDOFF-SWAT4.md` (8 Devastation ideas).
Rule: no game assets or SDK source committed here; file:line refs into the SDK only.

## Install + engine (verified 10-17)
- Install: `F:\gogGames\SWAT 4` (GOG Gold, game id 1409964317). Base `Content\System\Swat4.exe`, expansion (TSS) `ContentExpansion\System\Swat4X.exe`, + `*DedicatedServer.exe` in both.
- Engine: Irrational Vengeance (UE2.x). Renderer `D3DDrv.dll` imports **d3d9.dll** -> shader work needs a d3d9 proxy (not our d3d8to9 fork).
- Physics: **Havok** (Engine.dll has HavokActor, Havok6DOFConstraint, HavokCharacterCollision...; `HavokData\` folders; `SwatExpHavokClasses.u`). No Karma.
- Tools shipped: `UCC.exe`, `SwatEd.exe` (editor), `ScriptCompiler.dll`, `ShaderPackager.exe`.
- Script packages (ContentExpansion\System): AICommon Core Editor Engine Gameplay GUI IGEffectsSystem IGSoundEffectsSubsystem IGVisualEffectsSubsystem IpDrv RWOSupport Scripting SoundEffectsConfig SwatAIAwareness SwatAICommon SwatEd SwatEquipment SwatGame SwatGui SwatObjectives SwatProcedures Tyrion UWindow Voting. Several have native DLLs (Tyrion.dll, SwatAICommon.dll, SwatGame.dll, SwatAIAwareness.dll, AICommon.dll).

## Official SDK (verified 10-17)
- `F:\gogGames\SWAT 4\SWAT4_SDK.zip` (also `ContentExpansion\SDK\`), unpacked to `C:\re\swat4\sdk\SDK\` (research copy, never publish).
- Full UnrealScript source: 1492 .uc. Per package: AICommon 7, Gameplay 23, RWOSupport 38, Scripting 59, SwatAIAwareness 3, SwatAICommon 312, SwatEquipment 74, SwatGame 320, SwatGui 72, SwatObjectives 18, SwatProcedures 20, Tyrion 68.
- Modding doc as text: `C:\re\swat4\modding_overview.txt` (from SDK/Documentation/SWAT4_Modding_Overview.pdf, 11 pages).
- Mod setup per doc: own `<MOD_DIR>` next to Content (Content\Maps etc. inside), copy System\*.ini, edit `Startup.ini` + `StartupUCC.ini` (doc L137, L277), compile from `<MOD_DIR>\System` with `..\..\Content\System\UCC.exe make -nobind` (L310); add `EditPackages=` [Editor.EditorEngine] + `ServerPackages=` [Engine.GameEngine] in Swat4.ini and UCC.ini (L343-346); prefer subclassing (L333); `EnableDevTools=true` in Swat4.ini (L366); windowed: remove `Suppress=WindowedMode` (L350).

## AI layout (SDK, 10-17)
- Tyrion = goal/action/resource AI framework (Engine 35 .uc: AI_Goal, AI_Action, AI_Controller, AI_*Resource for character/movement/head/weapon, AI_PeriodicSensor).
- SwatAICommon: Actions 94, Goals 80, Sensors 12 (Vision, Hearing, Threatened, Compliant, Comply, Arrested, Distance*, DoorOpening, DoorSide, Target), SensorAction 9, Navigation 13 (Stackup/Clear/Flee points, Formation), Squads 8 (Hive, HiveBlackboard, OfficerTeamInfo, Red/Blue/Element) + Squad Actions 34 / Goals 33, InitialReactions, Idling, Patrolling.
- SwatGame: SwatAI, SwatAICharacter, SwatAIController, SwatEnemy, SwatHostage, SwatOfficer, EnemyArchetype, HostageArchetype, Enemy/HostageSpawner, PawnDoorKnowledge, GameEvent_* (PawnDamaged, EnemyFiredWeapon, PawnArrested...).
- Detailed maps (Sonnet agents, 10-17): `C:\re\swat4\map-suspects.md`, `C:\re\swat4\map-officers.md` -> merged below (sections "Suspect + hostage AI", "Officer AI + Tyrion engine").

## Suspect + hostage AI (spot-checked 10-17: compliance roll CommanderAction.uc:446-448, AI.ini keys)

Paths: SDK = `C:\re\swat4\sdk\SDK\Source\Game`. INI = `F:\gogGames\SWAT 4\ContentExpansion\System\AI.ini` (Content\System\AI.ini is the same minus 2 expansion keys + WildGunner section). Cited as AI.ini:line (expansion file). SwatPawn.ini is in the same folders.
Only the base-game source is in the SDK. Expansion-only behaviour has INI keys but no .uc (see 2).

### 1. Class chain and starting goals
- `SwatEnemy` extends `SwatAICharacter` extends `SwatAI` extends `SwatRagdollPawn`. All `native` (SwatEnemy.uc:2-5, SwatAICharacter.uc:4-13, SwatAI.uc:6-13). `SwatHostage` extends `SwatAICharacter` (SwatHostage.uc:2-5).
- `SwatAIController extends Tyrion.AI_Controller`, native. Its only script is `OnHearSound`, which forwards to `SwatAI.hearing` (SwatAIController.uc:10-14).
- Tyrion setup (SwatAI.uc:405-437): `ConstructCharacterAI` adds TakeCover, MoveTo, Incapacitated and ReactToBeingShot abilities. It then `SetupCommanderGoal()` and posts `CommanderGoal` (SwatAI.uc:433-439). An idle goal is posted at SwatAI.uc:558-564.
- Each pawn type registers its own CommanderAction as an ability. That one action is the brain: it satisfies `CommanderGoal` (CommanderAction.uc:1435).
  - Enemy: `EnemyCommanderAction`, EnemySpeechManager, Barricade, Investigate, Restrained, TakeCover, `EnemyComplianceAction`, `EnemyCowerAction` (SwatEnemy.uc:286-293).
  - Enemy hook `ConstructCharacterAIHook` (SwatEnemy.uc:308-316) adds AttackOfficer, TakeCoverAndAttack, Flee, ThreatenHostage, ConverseWithHostages, Regroup. SwatGuard and SwatUndercover override the hook (SwatGuard.uc:7, SwatUndercover.uc:7).
  - Hostage: Compliance, `HostageCommanderAction`, HostageSpeechManager, Flee, HostageReactionToOfficers, Cower, Restrained (SwatHostage.uc:51-54).
- Engagement: `EnemyCommanderAction` posts `EngageOfficerGoal` (EnemyCommanderAction.uc:1163-1176). Tyrion picks the registered action with the highest `selectionHeuristic`. Candidates satisfying that goal: AttackOfficer, TakeCoverAndAttack, Flee, Regroup, ThreatenHostage, EnemyCower (satisfiesGoal lines: FleeAction.uc:392, RegroupAction.uc:422, TakeCoverAndAttackAction.uc:690, ThreatenHostageAction.uc:464, EnemyCowerAction.uc:142).

### 2. Morale and compliance
- **Morale** is a single float, `CurrentMorale`, capped at `MaxMorale=1.5` (AI.ini:14, CommanderAction.uc:57,64). Initial value is `Instance.Morale` = `RandRange(Min,Max)` from the archetype (CharacterArchetype.uc:177, SwatAICharacter.uc:413) and is applied via `InitializeMorale` (CommanderAction.uc:125-128). Only enemies call it (EnemyCommanderAction.uc:120-135). Hostages are initialised by `CommanderAction` too, since Morale is on CharacterArchetype.
- **`ChangeMorale(delta, reason, bDoNotStartListening)`** (CommanderAction.uc:1179-1210):
  - It is ignored once a ComplianceGoal or RestrainedGoal exists.
  - It adds the delta and clamps with `FMin` to `MaxMorale`. There is no lower clamp.
  - A negative delta sets `bListeningForCompliance=true` unless the flag is passed.
  - Being shot passes the flag, so shooting a leg cannot force compliance (CommanderAction.uc:884).
- **Compliance roll** `OnComplianceIssued` (CommanderAction.uc:427-488), shared and not meant to be overridden:
  - It fires only if the pawn is not arrested, not compliant and not incapacitated.
  - A "comply" shout reaches it through `ComplySensor` (CommanderAction.uc:385-391).
  - If `bListeningForCompliance`, it rolls `RandomChance = 1 - FRand()` and complies when `RandomChance >= CurrentMorale` (lines 445-449). So morale >= 1.0 never complies; morale <= 0 always does.
  - After any roll it sets `bListeningForCompliance=false`, so the pawn ignores orders until morale drops again (line 465).
  - Ignored orders are counted. `MaxComplianceOrdersToIgnore=3` (AI.ini:11) tells the Hive "AI ignoring officers" (lines 478-484).
  - On success, `PostComplianceGoal` (CommanderAction.uc:513-535) calls `SetIsCompliant`, posts `ComplianceGoal` and calls `NotifyBecameCompliant`.
- **Morale deltas** (AI.ini:23-143; enemy values listed Low/Med/High; all are subtracted from morale unless noted):

| Source | Enemy Low/Med/High | Hostage |
|---|---|---|
| Flashbang | 0.5 / 0.5 / 0.5 | 0.65 |
| Gas | 0.35 each | 0.55 |
| Pepper spray | 0.75 each | 0.75 |
| Sting | 0.4 each | 0.6 |
| Taser | 0.9 each | 0.9 |
| C2 stun | 0.45 each | 0.65 |
| Shot (no compliance listen) | 0.2 / 0.1 / 0.0 | 0.5 |
| Dropped weapon | 0.25 / 0.15 / 0.1 | - |
| Out of usable weapons | 1.0 / 0.8 / 0.75 | - |
| Nearby enemy killed (within `MinDistanceToAffectMoraleOfOtherEnemiesUponDeath=500`) | 0.4 / 0.2 / 0.1 | - |
| Killed officer (ADDS to morale) | +0.3 / +0.4 / +0.5 | - |
| Surprised by comply shout | 0.8 / 0.6 / 0.5 | - |

- Notes on the table:
  - Stun-type deltas are applied by `StunnedAction.AffectMorale` and refunded when the stun ends (StunnedAction.uc:75-90). The refund applies only if the pawn is conscious.
  - The other enemy deltas are applied at EnemyCommanderAction.uc:428 (weapon), 458 (officer killed), 484-488 (nearby killed), 516 (no weapon) and 874 (surprise). Shot is at CommanderAction.uc:884.
  - Hostage deltas are at HostageCommanderAction.uc:23-29 and 171.
  - Enemy gets `bThreat` and the Hive is notified when it fires or aims at someone (SwatEnemy.uc:881, 954-960; ThreatenedSensorAction.uc:43-50).
- **Surprise** (`PreComplianceCheck`, EnemyCommanderAction.uc:861-877): applies only if the state is below `EnemyState_Aware`. The pawn becomes Aware. If the issuer is within `MaxSurprisedComplianceDistance=400` and outside the view cone of `SurprisedComplianceAngle=90` (2D dot test, lines 830-858; AI.ini:64-66), it takes the surprise morale hit before the roll.
- **Refusal** (`PostComplianceCheck`): on refusal, an enemy plays uncompliant speech and `EncounterEnemy(issuer)` (EnemyCommanderAction.uc:879-887). A hostage sets idle category `NonCompliant` and uncrouches (HostageCommanderAction.uc:~215-228).
- **Restrain / arrest**:
  - `SwatAICharacter.OnArrestBegan` calls `NotifyBeginArrest`, which posts `RestrainedGoal` (SwatAICharacter.uc:855-866, CommanderAction.uc:596-612).
  - `OnArrestInterrupted` calls `RestrainInterrupted` (CommanderAction.uc:614-622).
  - `NotifyRestrained` removes the ComplianceGoal (lines 624-629).
  - `CanBeArrestedNow` = `bCanBeArrested && !IsArrested && !IsBeingArrested && conscious` (SwatAICharacter.uc:850).
  - Compliance has no reset in the SDK source: `SetIsCompliant` only sets true (SwatAI.uc:2533).
- **"Un-arrest" / leaving compliance**: the expansion's AI.ini adds `UnobservedComplianceMoraleModification=0.1` and `LeaveCompliantStateMoraleThreshold=1.0` (AI.ini:145-149). No .uc in the SDK reads them (grep is empty), so that logic is compiled in the expansion's SwatAICommon.u and is not available as source.
- **Scream and flinch**: `ShouldScream` is `FRand() < chance` (EnemyCommanderAction.uc:795). Enemy chance is 0.65 / 0.5 / 0.3 by skill (AI.ini:~75). Hostage chance is 0.7 (AI.ini:41). The delay is Rand(`MinScreamTime=0.1`, `MaxScreamTime=1.0`) (CommanderAction.uc:901-910). Gunshot reaction range `MinReactToGunshotDistance=300` (AI.ini:15).

### 3. Combat
- Target selection:
  - `EncounterEnemy(pawn)` (EnemyCommanderAction.uc:1038-1079) sets `CurrentEnemy` and forces state Aware.
  - `ShouldEncounterNewEnemy` switches target if the new pawn is closer than the current one and within `DeltaDistanceToSwitchEnemies=300`, or if the current target cannot be hit but the new one can (lines 993-1010; AI.ini:~78).
  - `FindBetterEnemy` takes the closest visible conscious pawn when `CanHit(current)` is false (lines 1367-1387).
  - The lost-sight timer is 3-8 s (`MinLostPawnDeltaTime`/`MaxLostPawnDeltaTime`, AI.ini:~70). When it fires the pawn clears its enemy, then `FinishedEngagingEnemies` posts a Barricade goal at the last known position (lines 1389-1415).
- Initial reaction (a one-off animation): chance 0.15 / 0.10 / 0.05 by skill, only if all officers are farther than 200 (`MinDistanceToOfficersToDoInitialReaction`). SwatGuard always reacts (EnemyCommanderAction.uc:1099-1140; AI.ini:~73-77).
- `EngageOfficerGoal` picks one action by random `selectionHeuristic` (`FClamp(FRand(), min, max)`, with different ranges for aggressive and passive pawns). Aggressive is `FRand() < AggressiveChance` per archetype, rolled once at spawn (CharacterArchetype.uc:187). Morale is NOT part of this choice.
  - AttackOfficer: usable weapon and a target are required. Passive 0.0-1.0, aggressive 0.5-1.0 (AttackOfficerAction.uc:~45-60; AI.ini:~484-488).
  - TakeCoverAndAttack: needs cover available, farther than 200 from officers (`MinDistanceToOfficersWhileTakingCover`), a cover result not within 200 of or behind any seen pawn (`CoverIsInBadPosition`, TakeCoverAndAttackAction.uc:66-104). Passive 0.0-1.0, aggressive 0.75-1.0. Timings: crouch 1-3 s, stand 1-3 s, lean 1-2 s, aim-around 0.5-1.0 s over 90-270 degrees (AI.ini:~395-424).
  - Flee: needs a `FleePoint` outside the current room that is not claimed and not in the enemy's room (`FindFleePointDestination`, FleeAction.uc:268-300). It needs a room door more than 200 from officers (`CanGetOutOfRoomSafely`, lines 101-128). Passive 0.25-1.0, aggressive 0.0-0.75. If an officer is within 200 it returns `FRand()*0.1` (AI.ini:285-288; FleeAction.uc:130-175). `CrouchAtFleePointChance=0.8`.
  - Regroup: same shape, with passive 0.25-1.0 and aggressive 0.0-1.0, and it needs another living enemy (RegroupAction.uc:119-160; AI.ini:379-382).
  - EnemyCower: if there is no usable weapon it returns 1.0 if the pawn has already fled unarmed, else `FRand()`; otherwise 0 (EnemyCowerAction.uc:46-72).
  - ThreatenHostage: conditions are an armed enemy, a visible player, a hostage in the room within 256 of the enemy, and officers at least 200 away (`CanThreatenHostage`, ThreatenHostageAction.uc:128-145; AI.ini:442-465). Chance is 1.0 aggressive, 0.75-1.0 passive. It aims at the hostage, then shoots after 2.0-4.0 s (lines 420-458).
- Firing (`AttackTargetAction`, AttackTargetAction.uc:150-345):
  - It aims, waits until `CanHit`, fires, then sleeps `GetTimeToWaitBetweenFiring`.
  - The give-up timer is `MaximumTimeToWaitToAttack=7.5` (AI.ini:174).
  - Gap between shots comes from SwatPawn.ini:333-351 (pistol 0.1-0.2 s, SMG full auto 0.5-0.7 s, shotgun 0.3-0.6 s).
  - Aim error: Low 7.0 / Med 6.0 / High 3.0 (SwatPawn.ini:379-381, `GetAdditionalBaseAimError`, native, SwatEnemy.uc:937).
  - Full-auto burst length: Low 1-2 s / Med 0.6-1.0 s / High 0.2-0.5 s (SwatPawn.ini:388-393).
  - Full-body hit chance: 0.666 / 0.5 / 0.25 (SwatPawn.ini:410-412).
- Barricade (AI.ini:204-233):
  - Used when the enemy is suspicious or loses its target. It also triggers after `MaxBlockedDoorCount=3` blocked-door attempts (EnemyCommanderAction.uc:1266-1310).
  - `ShootAtDoorsChance=1.0`, shoots at an opening door for 2.0-3.5 s.
  - Closes and locks the nearest door with chance 0.5, subsequent doors 0.25.
  - Delay before barricading is 0.5-1.0 s.

### 4. Perception
- `VisionSensor` (VisionSensor.uc:1-126) keeps the `Pawns` seen list, `LastPawnSeen`/`LastPawnLost` and `GetVisibleConsciousPawnClosestTo`. It is fed by the native `VisionNotifier` (AICommon/Classes/Sensing/VisionNotifier.uc), which is native, so there is no FOV or range number in script.
- `HearingSensor` (HearingSensor.uc:1-68) stores the last `SoundMaker`, `Origin`, `Category` and time. `WillListenToSound` is virtual and returns true. `kDeltaHeardTime=2.5` is declared but unused here. The engine calls `SwatAIController.OnHearSound`.
- Sound categories seen in SoundEffects.ini (same folder): Gunshots (AISoundRadius 1500), BulletHitSpangs, Explosions, DoorInteraction, Footsteps (radius 150/300/600/1000 depending on movement), OfficerYelling.
- `ThreatenedSensor` is set by `ThreatenedSensorAction.UpdateThreatFrom`: the other pawn must be a threat and aiming at us (`SwatWeaponAction.IsAThreatBasedOnAim`) (ThreatenedSensorAction.uc:36-60). The `ThreatenedBy` pawn is exposed on the sensor (ThreatenedSensor.uc:5-33).
- Enemy `OnHeardNoise` (EnemyCommanderAction.uc:636-720):
  - Compliant or arrested: it only flinches for a nearby gunshot.
  - Otherwise: a threat in line of sight triggers `EncounterEnemy`.
  - Footsteps: engage if there is a current enemy, else `BecomeSuspicious` (lines 757-777).
  - DoorInteraction: a line-of-sight check on the door, then engage if Aware, else suspicious ("yes this is cheating", line ~692).
  - Anything else with no enemy: `BecomeSuspicious` (state Unaware to Suspicious to Aware, `ISwatEnemy.uc:22-27`). Investigator enemies get an Investigate goal, others get Barricade (lines 723-752).
- Hostage `OnHeardNoise` (HostageCommanderAction.uc:245-290):
  - A deadly noise (`IsDeadlyNoise`: Gunshots, BulletHitSpangs, Explosions; CommanderAction.uc:~339) makes the pawn crouch once with chance 0.85 (aggressive) or 0.65 (passive) (lines 336-350).
  - Gunshot hits within 300 make it run to a point and scream. Compliant hostages flinch.
  - It uses `IsInDanger` (lines 390-415): threatened, or a non-compliant enemy is visible, or a SwatEnemy is in the room.
  - If in danger it cowers (CowerGoal) and speaks "in danger" every 3-8 s. When a SwatOfficer or SwatPlayer comes into view it becomes Rescuer, and HostageReactionToOfficers runs (lines 417-460).
  - ReactToThrownGrenadeChance is 1.0 for hostages and 0.333 / 0.5 / 0.75 for enemies by skill.

### 5. Archetypes and data
- Config class: `EnemyArchetype` (config `EnemyArchetypes`), `HostageArchetype` (config `HostageArchetypes`), both extend `CharacterArchetype`. These are INI files at `...\Content\System\EnemyArchetypes.ini` (81 sections) and `HostageArchetypes.ini` (97 sections), plus ContentExpansion copies.
- Fields:
  - CharacterArchetype.uc:23-35: `Morale` (Range), `AggressiveChance`, Mesh, materials, `Equipment1..4`, `CharacterType`, `VoiceTypeOverride`.
  - EnemyArchetype.uc: `Skill` (array of `{Skill=EnemySkill_Low|Medium|High, Chance}`), `PrimaryWeapon`/`BackupWeapon` (array of `{Weapon, Chance}`), `InvestigatorOverride`, `ActorClass`.
- Examples: `[FoodWall_Jimenez]` has Morale 0.4-0.6, Skill Low (100%), AggressiveChance 0.75. EnemyArchetypes.ini morale ranges seen run from 0.0 to 0.9 (e.g. 0.33-0.60 and 0.50-0.75 for several). Hostages are mostly 0.05-0.10 with some 0.0-0.33.
- Per-map data: spawners (EnemySpawner/HostageSpawner/EnemyRoster/HostageRoster in SwatGame/Classes/Spawning), FleePoint actors, patrol lists and archetype references are placed in the `.s4m` map files (Content\Maps\*.s4m). They are binary, so no grep was done. `CustomScenarioCreator.ini` lets the user override enemy weapons through `CustomScenario.MutateEnemyWeapons` (EnemyArchetype.uc, `Initialize`).
- The tuning INIs are SwatPawn.ini (AI sections) and AI.ini. Both are plain text and are loaded per `config(AI)`.

### 6. Hook points for a fear / anger / suppression / panic mod

| Target | Final/native? | Why |
|---|---|---|
| `EnemyCommanderAction` and `HostageCommanderAction` (subclass, swap in at SwatEnemy.uc:286 / SwatHostage.uc:52) | script class, config vars; not final | Central brain. Override `ChangeMorale`, `GetShotMoraleModification`, the `Get*MoraleModification` functions, `OnHeardNoise`, `EncounterEnemy`, `ShouldScream`. Add new emotion floats here. |
| `CommanderAction.ChangeMorale` / `OnComplianceIssued` (CommanderAction.uc:1179 / 427) | script, not final (comment says "no overriding" for OnComplianceIssued, but it is not declared final) | Single choke point for morale. Replace the roll with fear/anger weighting. |
| `ConstructCharacterAI` / `ConstructCharacterAIHook` (SwatEnemy.uc:280, 308) | protected script | Register new abilities (new Flee, Suppressed, Panic actions). SwatGuard already does this. |
| `selectionHeuristic` of AttackOfficer / TakeCoverAndAttack / Flee / Regroup / EnemyCower | script, overridable | Replace `FRand()` with a function of fear/anger/suppression. Easiest place to make panic and cover choice emotion-driven. |
| `TakeCoverAndAttackAction.CanTakeCoverAndAttack` / `FindBestCoverToAttackFrom` / `CoverIsInBadPosition` (lines 66-104) | script; `AICoverFinder` is native (AICoverFinder.uc, `FindCover`, `IsCoverAvailable`) | Better cover choice: filter or score `CoverResult` candidates. The finder itself is native, so only post-filter. |
| `AttackTargetAction` (`AimAndFireAtTarget`, `ShouldSucceed`), `SwatEnemy.GetAdditionalBaseAimError` | AimError is `native event`; others are script | Suppression: raise aim error or add flinch. Native, so override via a script wrapper or a pawn-level multiplier. |
| `SwatAIController.OnHearSound`, `HearingSensor.OnListenerHeardNoise`, `VisionSensor.OnViewerSawPawn` | script event/functions; native notifiers underneath | Inject fear stimuli (near-miss bullets, explosions) into emotion state. Bullet near-miss is not a stimulus in script; gunshots arrive as sound categories. |
| `StunnedAction.AffectMorale` and the Gassed/Flashbanged/PepperSprayed/Stung/Tased/StunnedByC2 `GetMoraleModificationAmount` (StunnedAction.uc:69-90) | script | Add stress on top of the stun-morale refund. |

- The sensor classes, `AIKnowledge`, `Hive` and most pawn state (`IsFlashbanged`, `IsGassed`, `CanHit`, `CanHitTargetAt`, `IsOtherActorAThreat`) are native in SwatAI/SwatAICharacter (SwatAI.uc:1969-1970, 2543; SwatAICharacter.uc:826-832). Do not try to override them; wrap them.
- Gaps: no suppression or near-miss detection exists, no morale floor or decay over time, no hostage panic-flee goal (FleeAction is registered on hostages but nothing posts EngageOfficerGoal for them), and no un-arrest in source.

## Officer AI + Tyrion engine

Paths relative to `C:\re\swat4\sdk\SDK\Source\Game\`. Lines marked "~" are approximate.

### 1. Tyrion engine loop (Tyrion\Classes\Engine)
- Goal = "what": `AI_Goal` native abstract (AI_Goal.uc:11-14); Priority 0-100, default 50 (:21, :479); `priorityFn()` (:114); flags bInactive/bPermanent/bTryOnlyOnce/bTerminateIfStolen (:20-37).
- Action = "how": `AI_Action` native (AI_Action.uc:8-10); `satisfiesGoal` (:18), `selectionHeuristic(goal)` 0..1 default 1.0 (:391); `resourceUsage` bits RU_HEAD=1/ARMS=2/LEGS=4 (AI_Resource.uc:47-49).
- Resources are hierarchical: squad > pawn > leaf head/arms/legs (AI_Resource.uc:1-42); only leaves are "used".
- `chooseAction(goal)` is NATIVE (AI_Resource.uc:253): filter by satisfiesGoal, rank by selectionHeuristic, need free resources. Exact algorithm is in Tyrion.dll (inferred).
- Preemption: `resourceCheck()` (AI_Resource.uc:266-300): a goal with higher priority than the leaf's current goal calls `interruptAction` on the user; parent gets `resourceStolenCB` (AI_Action.uc:471).
- `addGoal` sets `bMatchGoals=true` (AI_Resource.uc:401), the native `processGoals` then re-matches. Permanent goals re-match after success (AI_Goal.uc ~:340).
- Idioms (script): waitForGoal/AllGoals/AnyGoal, interruptGoalIf (AI_Action.uc:112-222), waitForResourcesAvailable (:278); succeed/fail (:32-100).
- Sensors: `AI_Sensor` native (AI_Sensor.uc:9); `setIntegerValue` notifies recipients inside bounds (:151-180); goal activation/deactivation via `AI_SensorWithBounds` sentinels (AI_Goal.uc:24-25).
- Native = match/choose/processGoals, sensor core; script = all data, callbacks, idioms.

### 2. Squads and Hive
- `OfficerTeamInfo` (native, extends AICommon.SquadInfo); Element (all), Red, Blue squads created in SwatAIRepository.uc:104-120; getters native (:124-126).
- Officers join Red/Blue + Element in `AddToSquads` (SwatGame\Classes\AI\Officers\OfficerRedOne.uc:19-26).
- `InitAbilities` registers ~30 Squad*Action abilities (SwatAICommon\Classes\Squads\OfficerTeamInfo.uc:32-67).
- Player order path: CommandInterface.uc `SendCommandToOfficers` (~:1255-1410) -> `PendingCommandTeam` (:811, :1005-1013) -> OfficerTeamInfo.MoveAndClear (:678) etc. -> `PostCommandGoal` (:498-520), replaces old goal.
- Element-wide commands copy the goal to other team: ElementSquadInfo.uc:94-150.
- `CanExecuteCommand()` (OfficerTeamInfo.uc:270-289) false if no members, Hive `HasTurnedOnPlayer`, or officers busy (:291).
- Hive: native, config(AI), `new(self) class'Hive'` hard-coded (SwatAIRepository.uc:93-101). Blackboard: enemies, hostages, assigned targets, engaging point map (HiveBlackboard.uc:14-23).
- Hive loop: `OfficerSawPawn` (Hive.uc:492-537) -> native `UpdateOfficerAssignments` (:820) -> `AssignOfficer` (:822-838) -> `ClearCommandGoalsForOfficer` (:674-708) + `OfficerCommanderAction.EngageTarget`. Assignment overrides player commands.
- `CanAssignOfficerToTarget` (:764-786): same room, clearing into room, LOS to non-threat, `CanHit` on threat, or an engaging point exists.
- Rogue player: `NotifyOfficerShotByPlayer` (:549-575) accumulates damage; at config `PlayerDamageThreshold` (:24; AI.ini:727 = 100.0) `PlayerCrossedDamageThreshold` (:593) makes the player an enemy.

### 3. Officer combat
- Abilities list: SwatOfficer.uc:167-231 (OfficerCommanderAction, AttackEnemy, EngageForCompliance, MoveAndClear, Cover, Guard, deploy taser/pepper/etc.).
- `OfficerCommanderAction` (native class, script body): `EngageTarget` (:352), `ShouldEngageTarget` (:333), `EngageAssignment` (~:447) picks AttackEnemy for threats/player, else EngageForCompliance; calls `Hive.FinishedAssignment`.
- Priorities: MoveAndClear 90 (MoveAndClearGoal.uc:41), AttackEnemy 85 (AttackEnemyGoal.uc:29), EngageForCompliance/OrderCompliance 85, RestrainAndReport 80, FallIn 80, StackUp 75, Cover/Guard 60, StackedUp 39, WatchNonHostile 35.
- `AttackEnemyAction`: heuristic = FRand() (AttackEnemyAction.uc:31); posts AttackTargetGoal + MoveOfficerToEngageGoal; 0.1-0.25 s update; `FindBetterEnemy` re-runs assignments.
- `AttackTargetAction` (:170-345): waits for native `m_Pawn.CanHit(Target)`; officers loop only while `IsTargetAThreat()` (:265); fire via `AimAndFireAtTarget`, delay `GetTimeToWaitBetweenFiring` (SwatAI.uc:2015, per-weapon config :197-208); default fire mode Burst > Auto > Single (SwatAI.uc:1993-2011); `bHavePerfectAim` -> SetPerfectAimNextShot. Aim error is native (not visible).
- Rules of engagement: officers shoot only `bThreat` enemies; `BecomeAThreat` when aiming a firearm at a pawn (SwatWeaponAction.uc:142) or discharging (SwatEnemy.uc:881-892, :956-961).
- Less-lethal, restrain: player-ordered only (SquadSecureAction.uc:388 posts RestrainAndReportGoal).

### 4. Movement, nav, cover, awareness
- Stack-up: `GetStackupWeightForOfficer` = path distance, deflated by closer officers, -512 if wrong side of door (SquadStackUpAction.uc:472-493, :346-368); greedy pairing `DetermineOfficerStackupPoints` (:412-460).
- Move and clear: leader/follower roles, `SetupOfficerRoles`, `CreateClearFormation` (SquadMoveAndClearAction.uc:947); consts :66-72; Running state :1567-1612.
- BangAndClear needs a flashbang thrower or fails ACT_INSUFFICIENT_RESOURCES_AVAILABLE (SquadBangAndClearAction.uc).
- Formation: leader + members, reorder timer (Navigation\Formation.uc).
- Nav points StackupPoint/ClearPoint/BaseDoorPoint extend native PathNode; doors via ISwatDoor; belief flags in Doors\PawnDoorKnowledge.uc.
- Cover is player-ordered only: CoverAction.uc (FastTrace from eye, kMaxDistanceFromCoverFromLocation=100). TakeCover + native AICoverFinder are enemy-only; no officer script posts TakeCoverGoal.
- Officers do not duck or seek cover on their own under fire.
- SwatAIAwareness: native `AwarenessProxy` graph of vision/hearing points; the Hive owns it for officers, updated every 0.333-0.666 s (Hive.uc:17-19, :36-37). Not used for officer cover.
- Engage-point search: native `FindEngagingPointForOfficerInRoom` (Hive.uc:486); `MoveOfficerToEngageAction` retests every 1-3 s.

### 5. Leader dependence
- Every `SquadCommandGoal` requires non-None CommandGiver + CommandOrigin (SquadCommandGoal.uc:13-29).
- `SquadFallInAction` builds Formation(CommandGiver) (SquadFallInAction.uc:166), timers on CommandGiver (:77-79), LOS speech (:96-121).
- Stack-up / clear use CommandOrigin (a vector), so they survive the giver dying.
- `NotifyPlayerDied` only triggers speech (Hive.uc:341). Without a player, command-driven behaviour never starts; officers only idle, aim around, and engage via Hive assignment.
- Headless/bot test needs a pawn as CommandGiver.

### 6. Mod hook points
- `Hive.CanAssignOfficerToTarget` (Hive.uc:764) and `AssignOfficer` (:822): script, but Hive is hard-coded `class'Hive'` (SwatAIRepository.uc:95); scoring (`UpdateOfficerAssignments`) native, fixed.
- `OfficerCommanderAction.ShouldEngageTarget`/`EngageAssignment`: script in a native class; replace via ConstructCharacterAI.
- `SwatOfficer.ConstructCharacterAI` (SwatOfficer.uc:167): add or swap abilities (best hook; add a TakeCover ability here).
- `AttackEnemyAction.selectionHeuristic` (:31) / `AttackTargetAction.IsTargetAThreat`, `SetFireMode`, `AimAndFireAtTarget`: script, overridable.
- `OfficerTeamInfo.InitAbilities` / `CanExecuteCommand` (:32, :270): script.
- `SquadStackUpAction.GetStackupWeightForOfficer` (:472): event, overridable.
- `SwatAI.GetTimeToWaitBetweenFiring` (:2015): script plus config.
- Native, NOT changeable: chooseAction, processGoals, UpdateOfficerAssignments, FindEngagingPointForOfficerInRoom, Pawn.CanHit, awareness impl, AICoverFinder, aim error.
- No `final` keywords found in Squads; config defaults live in game AI.ini / SwatPawn.ini, not the SDK.

## Port candidates (Devastation HANDOFF-SWAT4.md + Advent AI-MINDS-DESIGN.md -> SWAT 4 hooks), 10-17
SWAT 4 already has: one morale float, random action choice (selectionHeuristic = clamped FRand), native cover finder (enemies only), no suppression, no morale decay, officers never take cover on their own.
1. **Emotion-driven action choice (best first mod)**: subclass EnemyCommanderAction (swap at SwatEnemy.uc:286) + override selectionHeuristic of AttackOfficer/TakeCoverAndAttack/Flee/Regroup/EnemyCower so fear/anger/stress (Advent ModMind) replace FRand. Compliance roll stays morale-based; fear feeds morale via ChangeMorale. Off switch: config bool -> stock FRand.
   - Devastation hide-when-hit (PROVEN 10-17, HANDOFF-SWAT4.md last section): hit adds fear +0.1 (+0.2 if dmg>20); away from cover in ranged fight -> hide if FRand*CoverAbility < fear; hiding resets fear 0, run+crouch 1-2 s, pop out. Live: CoverAbility 0 hid on 1st hit (0.07 s); CoverAbility 1 hid at fear 0.7/0.9. Use as per-archetype 'nerve' for suspects (TakeCoverAndAttack/Flee weight).
2. **Suppression**: gunshots arrive only as sound category Gunshots (AISoundRadius 1500) + BulletHitSpangs; no near-miss stimulus. Use spangs near the pawn as near-miss -> stress up, aim error up (wrap native GetAdditionalBaseAimError via pawn multiplier), cover/flee weight up.
3. **Cover scoring (Devastation idea 1)**: AICoverFinder is native -> post-filter its CoverResult in TakeCoverAndAttackAction (CoverIsInBadPosition :66-104): add officer-lane penalty, stay-at-current bonus, facing check.
4. **Officer self-cover**: register a TakeCover ability in SwatOfficer.ConstructCharacterAI (:167) for officers under fire (they never duck now). Respect player orders (priorities MoveAndClear 90 / AttackEnemy 85 / Cover 60).
5. **Leader-anchor gotcha (Devastation idea 2)** is real here: SquadCommandGoal needs a CommandGiver pawn; headless tests must spawn one.
6. **Props as noise (Devastation idea 6)**: Havok props -> make impact noise a HearingSensor stimulus (suspects become Suspicious, like DoorInteraction).
7. Skip for now: ragdoll joint port (Havok, not Karma; check HavokData + SwatRagdollPawn first), gibs (wrong tone for SWAT 4).
Next: build the empty mod package (doc setup) + compile with UCC, then a probe actor that logs morale/emotion per suspect.

## SwatMinds mod (first mod), 10-17
- Mod dir `F:\gogGames\SWAT 4\SwatMinds` (BASE game). `System\` = runtime (copied base ini/int + shaders.spk, Startup/StartupUCC/Version edited per SDK doc, `EditPackages=SwatMinds` + `ServerPackages=SwatMinds` in Default.ini, Suppress=ScriptLog etc. commented, EnableDevTools=true, StartupFullscreen=False). `BuildSystem\` = compile dir holding copies of the SHIPPED base .u files.
- GOTCHA: UCC make with the SDK FilePath rebuilds all 22 base packages from SDK source; Engine logs 4 "Unknown property in defaults" (LastSpeedHackLog, MaxTimeMargin, TimeMarginSlack, MinTimeMargin) = SDK source older than shipped. Don't run on rebuilt base packages; compile against shipped .u copies in BuildSystem. `CompileSwatMinds.bat` builds there and copies only SwatMinds.u to System.
- GOTCHA: a subclass that reads the parent's `m_pawn` (SwatCharacterAction, protected) makes UCC crash on save ("Referencers of ObjectProperty SwatAICommon.SwatCharacterAction.m_pawn", then assert in DynamicFlashlightSpotLight serialize). Use `AI_CharacterResource(goal.resource).m_pawn` instead.
- Design: `SwatMindsMutator` (config SwatMinds.ini) ticks every 0.25 s over pawns IsA('SwatEnemy'); per suspect Fear/Anger/Stress/Nerve. On first sight it swaps exact-class AttackOfficer/TakeCoverAndAttack/Flee/Regroup in `Pawn.CharacterAI.abilities` (Tyrion_ResourceBase.uc:44, script array) for `Mind*Action` subclasses (loaded by name). Their selectionHeuristic keeps stock eligibility (stock 0 -> 0) and returns `Score()`: attack 0.15+0.55A+0.35(1-F)N, cover 0.2+0.5S+0.4FN, flee 0.7F(1-N)+0.2S, regroup 0.4F+0.2S, + FRand*0.2.
  - Hit: fear +0.1 (+0.2 if dmg>20) x(1.5-nerve), anger +0.25*nerve, ChangeMorale(-fearAdd*0.25). Officers/player in sight (1500 uu): stress +0.08 each per tick, else -0.04. Decay fear -0.02, anger -0.015 per tick. Fear floor = (1 - morale/startMorale)*0.5. Nerve = 0.3+FRand*0.5 (+0.2 aggressive).
  - Mind* subclasses need their own AI.ini sections (copied from the stock ones as [SwatMinds.Mind*Action]).
- Run: `Content\System\Swat4.exe SP-FoodWall?Mutator=SwatMinds.SwatMindsMutator` from `SwatMinds\System` (GameInfo.uc:719 parses ?Mutator=). Log `SwatMinds\System\Swat4.log`, tag `SwatMinds:` (probe / add / swapped / hit / score lines).
- Verified 10-17: compiles 0/0; on SP-FoodWall, 3 suspects each got 4 abilities swapped, probe logs every 1 s, fear 0 at rest, no SwatMinds script warnings. NOT yet verified: combat (score/hit lines) needs a played engagement. Menu-started missions don't add the mutator yet (ServerActors untested).
- Devastation update 10-17 (HANDOFF-SWAT4.md last section): bots see a standing teammate in their line of fire, but rapid-fire teammates refuse crouch requests and the 100 uu sidestep fails from cover, so the shooter just stops; cover swap bug: a bot asked to give up its point found no other and lost its own. Fixes for an officer port: let any officer crouch on request (whatever the weapon), try several strafe distances, and keep the old cover point when the swap search fails. Final handoff 10-17 (all tests done; run data in C:edevastationNOTES.md runs 1-18).

## PCGamingWiki notes (user pasted, 10-17)
- `-nointro` skips the intro videos and fixes some fullscreen flicker. LaunchSwatMinds.bat passes it now.
- FOV is 85 and Vert- on widescreen. The FirstPersonFOV setting is [SwatGame.SwatPawn] in SwatPawn.ini; per the wiki it changes only the viewmodel and can break MP joins. Widescreen stretches the HUD.
- Above 150 FPS the player gets stuck on map geometry (enlarged hitboxes). Cap the FPS for playtests if this shows up.
- The "insufficient onboard video memory" error with >4 GB VRAM is a false positive; it can be skipped.
- The executables are 32-bit, and the LAA flag may help on modern PCs.
- Prior art: **Enhanced SWAT 4** (unofficial patch: widescreen HUD/FOV, raw input, borderless, AA). **SWAT: Elite Force (SEF)** is a total overhaul that needs TSS: cut content, better AI, a merged campaign, and an official GOG release since 2025-09-02. SEF-FR and SEF-FR Tactical derive from it. Before tuning SwatMinds further, check what SEF changed in the suspect AI, so we don't duplicate it and stay compatible. SEF targets the expansion while SwatMinds targets the base game.

## Launch fixes (10-17, playtest 1)
- ServerActors=SwatMinds.SwatMindsMutator does NOT survive map travel in SP. It spawned in Entry only, and no "SwatMinds up" line appeared on SP-Training.
- The `Mutator=` option in User.ini [DefaultPlayer] reaches only the first Entry URL; later travel URLs drop it.
- WORKING ROUTE: SP missions load through SwatRepo.uc:133, `"start" @ MapName`, where MapName comes from SwatMissions.ini. The mod copy of `SwatMinds\System\SwatMissions.ini` now has all 15 `MapName=SP-X?Mutator=SwatMinds.SwatMindsMutator`. Not yet verified in a mission.
- Resolution: the game reset to 800x600 because 1920x1080 was not in SwatGUIState.ini ScreenResolutionChoices. Added 1280x720 and 1920x1080, and set the Swat4.ini viewports to 1920x1080. The log still says "SetRes 1920x1080 Fullscreen 0" (windowed); Alt+Enter toggles fullscreen, since Suppress=WindowedMode is commented out.
- Playtest 1 was SP-Training: no suspects, so no data.

## Existing mods (10-17 survey; ModDB and Nexus both return 403 to fetches, so this was gathered by search and is partial)
- SWAT: Elite Force (needs TSS): suspect personalities (Insane/Polite), flee-and-shoot, officers keep their orders while engaging. Source reportedly ships with v7.2 (CompileSource.bat); licence not confirmed. https://www.moddb.com/mods/swat-elite-force
- SEF First Responders / FR Tactical Edition: tougher suspects and ROE changes.
- Suspect Invasion: 150 suspects per map, using the archetype morale. https://www.moddb.com/mods/suspect-invasion
- No standalone morale or compliance mod was found, so SwatMinds' emotion layer is new for the base game. Mark it incompatible with SEF.

## Playtest 2 results (10-17, SP-FoodWall from the menu)
- VERIFIED: the SwatMissions.ini `MapName=SP-X?Mutator=SwatMinds.SwatMindsMutator` route works. Log: `start SP-FoodWall?Mutator=...`, then "Add mutator", "up", 3 suspects each with 4 abilities swapped (nerve 0.44, 0.68, 0.35; none aggressive).
- Line counts: 251 probe, 10 score, **0 hit**. Mission completed: 0/3 suspects arrested, 1/3 incapacitated.
- Stress works: SwatEnemy2 saw 5 officers and reached stress 1.00 within 2 s. SwatEnemy1 reached 0.24.
- Fear stayed at 0.00 the whole time, because hits are its only source.
- **Bug: the hit was missed.** Timer skips non-conscious pawns, so a hit that incapacitates in one go never gets compared with LastHealth. Fix: run the health-delta check before the conscious filter, and log incapacitated/killed as their own events.
- **Design: mind scores flatten stock intent.** Examples: cover stock 0.91 became 0.31; flee stock 0.80 became 0.13; attack stock 1.00 became 0.45. The stock score encodes situation (cover available, escape route), but the mind score ignores it except when stock is 0. Next: blend, e.g. `mind = lerp(stock, emotion, 0.5)`, or scale stock by an emotion multiplier.
- **Design: fear needs non-hit sources.** Candidates: a nearby ally hit or down, officer shouts/compliance orders, gunfire nearby, flashbang/gas/pepper. Stress could also feed into fear when nerve is low.
- Only 10 action choices in about 140 s. Choices are rare events, so emotions must already be high when a choice happens.

## Fix pass 1 (10-17, SwatMinds.u built 13:55)
- Hits are now checked BEFORE the conscious filter. A suspect's first incapacitated/dead tick logs `SwatMinds down` and sets bDown.
- New fear sources:
  - `SpreadFear`: allies within AllyFearRange=1200 with FastTrace line of sight get fear +amount×(1.5−nerve) and anger +amount×0.5×nerve. Amount is 0.25 for an ally down and 0.08 for an ally hit. Logged as `SwatMinds feel`.
  - An officer within CloseRange=400 and in sight adds 0.03×(1−nerve) per tick.
  - Stress > 0.6 with nerve < 0.5 adds 0.02 per tick.
  - Flashbang, gas, pepper, sting or taser (ISwatPawn.uc:26-30) adds 0.05×(1.5−nerve) per tick.
- Score is now `stock×(1−MindWeight) + emotion×MindWeight + (FRand−0.5)×NoiseWeight`, with MindWeight=0.5.
- Gotcha: CompileSwatMinds.bat cannot replace System\SwatMinds.u while Swat4.exe is running, so close the game first. Run it as `Start-Process cmd '/c "...bat"' -WindowStyle Hidden -Wait`.

## Nexus mods installed (10-17, user downloads)
- **Remove Reticles**: Content\Textures\HUD.utx replaced; the original is kept as HUD.utx.orig. Applies to all launches, including SwatMinds.
- **Edit AI Data (Nikolay97)** is made for SEF_FR. Its 33 listed values were applied by key to the vanilla Content\System and ContentExpansion\System AI.ini, SwatGame.ini and SwatPawn.ini; originals are in *.orig. The SwatMinds\System ini copies are NOT changed, so playtests stay clean.
  - Suspect fire delays are 0.4-0.6 s.
  - Aim error is 4 for all skills.
  - Initial reaction chance is 0.10.
  - Hard/Elite damage multiplier is 1.0.
  - Toolkit qualify time is 4 s.
- **NOT installed:** RFS Audio Overhaul (needs SEF v7.2) and SEF Real Time Mirror Reflections (needs SEF; it replaces Engine.dll and Engine.u). SWAT: Elite Force is not installed on this PC.

## Playtest 3 results (10-17, SP-FoodWall, after fix pass 1)
- 4 suspects, nerve 0.77 / 0.42 / 0.98 / 0.81; three aggressive.
- 2 down lines (one-shot fix works): SwatEnemy2 dmg=164, SwatEnemy1 dmg=86.
- 0 feel lines: no ally within AllyFearRange=1200 with FastTrace sight when the downs happened. Next: hearing radius (no sight needed) for shots/downs.
- 17 score lines; the 0.5 blend keeps the stock order now.
- First fear came from stress + low nerve (SwatEnemy1 fear 0.21).
- User recording `C:\Users\john\Videos\2026-10-17 13-59-09.mp4` (54 s): ended MISSION FAILED 1/100 (unauthorized deadly force -10; 1/4 incapacitated, 1/4 neutralized).
- RFS Audio Overhaul + SEF Real Time Mirror Reflections (Nexus) need SEF; not installed.

## Borderless helper (10-17, verified)
- Window title is `Swat4`. `SwatMinds\borderless.pyw` (pythonw, started by LaunchSwatMinds.bat) restyles it to WS_POPUP|WS_VISIBLE (0x94000000) at the monitor rect (tested 0,0-1920x1080), ClipCursor while the game is foreground, skips minimized, SWP_NOACTIVATE, exits with the game.

## Research (10-17, Sonnet agents)
- `research/breach-cover-ai.md`: CQB rules (fatal funnel, points of domination, interlocking sectors) as slot claims on a shared board; F.E.A.R. callouts on state change; TLoU buddy rule (never block the player's aim/door); utility scoring; light L4D Director; no revive in SWAT 4, so cover-downed-officer / drag / cuff-assist / reload-cover.
- `research/ray-audio.md`: 1) check DefOpenAL32.dll for EFX or drop in OpenAL Soft x86; 2) UnrealScript Trace probes ~10 Hz for RT60/occlusion with a material absorption table; 3) proxy DefOpenAL32.dll sets EFX reverb + per-source low-pass; 4) Steam Audio only if too coarse.

## Fix pass 2 (10-17, SwatMinds.u built 14:08): hearing
- SpreadFear: seen (<= AllyFearRange 1200 + FastTrace) = full amount, logged "saw"; else within HearRange=3000 = HearFactor 0.6 x (1 - 0.5 x dist/HearRange), logged "heard". Feel lines now carry dist=.

## Random Instant Action (10-17, SwatMinds.u built 14:13, 0 errors; in-game check pending)
- Instant Action (SwatMainMenu.uc:91-106) calls GuiConfig.LoadLastMissionPlayed() (SwatGUIConfig.uc:352), which replays the private config LastMissionPlayed*; GameStart() (SwatGUIControllerBase.uc:241) saves it just before LoadLevel.
- SwatMindsMutator.RandomizeInstantAction (bRandomInstantAction=true): on each map load, PC.Player.GUIController -> SwatGUIControllerBase.GuiConfig, picks a random other MissionName[k], SetPropertyText on the three private fields, SaveConfig. Log "instant action next:". First click after a fresh install still replays the stored mission once.

## Playtest 4 results (10-17, SP-FoodWall, hearing pass)
- 4 suspects (nerve 0.78/0.58/0.96/0.59, two aggressive); 5 hit, 4 down (all suspects), 22 score lines.
- 15 feel lines, all "heard" (dist 310-804), 0 "saw": FastTrace from pawn centre fails even at 310 units, so the sight check may be too strict (try eye height).
- Max fear: SwatEnemy1 0.87 (3 hits of 26 dmg), others 0.16-0.22. Heard-down adds ~0.10-0.17.
- Recording `C:\Users\john\Videos\2026-10-17 14-09-56.mp4` (170 s): Food Wall, squad command menu used, sniper picture-in-picture, player wounded, suspect by the van in the back alley.

## Instant Action fix 2 (10-17, built 14:17)
- First version never ran: PC.Player.GUIController is None during PostBeginPlay (no "instant action next" lines). Now uses SwatRepo(Level.GetRepo()).GuiConfig (engine-level, LevelInfo.uc:406) and logs "instant action: no Repo/GuiConfig" on failure. Picks from all 13 campaign MissionName entries (no unlock check). A command-line map URL is ignored (game goes to splash), so test from the menu.
- Research added: research/tactical-fps-ai.md, research/ai-communication.md, plan research/swatminds-plan.md.

## Visual testing queue (10-17 ~21:00, from the Windows support 2 chat)
- User: "i will prob do some more visual testing in swat 4 if i can get the game to be more chaotic and fun" -> chaos/fun (SwatMinds AI, instant action) comes first; visuals after.
- Idea for the visual pass, from MARKitekta's spherical-harmonics lecture (video-notes tree/88, youtu.be/cddCr95fnvI): an L2 SH irradiance probe grid (9 coeffs per channel, one dot product per pixel, 108 B per probe) as the ambient term above UE2's zone/actor ambient, diffuse only. Light leaks through walls and no AO are the known failure (needs a per-probe occlusion factor); sharp lights ring (window them, don't raise the order). Lumen keeps SH only as a fallback; radiance caching is the real thing (his next episode).

## CQB research (10-18)
research/superexplainer-cqb.md: 8 TheSuperExplainer shorts -> suspect room-hold scoring (deep off-axis, hard cover, not beside door, split angles, stairs set back, re-peek swap). Build after suspect comms v1.

## Eye-height sight + comms v1 (10-19, SwatMinds.u built 10:59, 0 errors; in-game check pending)
- SpreadFear "saw" now traces victim chest (+40) or eye to suspect eye (`BaseEyeHeight`, exists on Pawn); the old centre trace gave 0 "saw" lines in playtest 4.
- Comms v1 = Ruskin rules (research/l4d-ai-talk.md) over stock recorded lines via `EnemySpeechManagerAction` (`ISwatAI(P).GetSpeechManagerAction()`): rule 0 saw ally down + fear>=0.5 -> Scream; 1 saw ally down + anger>fear -> NonCompliant; 2 ally down other -> CalledForHelp; 3 ally hit + fear>=0.4 -> CalledForHelp; 4 fear crosses 0.7 -> Flee line (re-arms <0.4); 5 anger crosses 0.6 -> NonCompliant (re-arms <0.3); 6 officer down -> nearest suspect (seeing first, within HearRange) ReactedDownOfficer, anger +0.2.
- Memory: per-suspect SayCooldown=6, global SayGap=2, per-rule RuleCooldown=20. Config bComms=true. Log lines `SwatMinds say <pawn> rule=<n> line=<x>` and `SwatMinds officer down <pawn> reactor=<i>`.
- Check in next playtest: "saw" lines > 0, say lines audible and not spammy.

## Combat gym (10-19, user: "a gym for training our combat ai ... adapt to player or learn from player mistakes")
- Plan: research/combat-gym-plan.md (train fast in a Python CQB sim, deploy weights as SwatMinds.ini config, adapt live with a habit logger + bandit + SaveConfig, fairness director).
- v0: tools/cqbgym/gym_v0.py (`py -3.13 -I gym_v0.py --rooms 150 --seeds 4`), output weights_v0.json. Learned hold-spot pick 0.80 suspect win vs 0.20 random, 0.60 hand CQB tips (mixed attackers); off_axis top weight; depth sign flips with player habit (doorway-stopper -> shallow). Table + caveats in the plan file.

## Hot AI knobs (10-19, asked by the PC chat; verified in a minimized SP-FoodWall run)
- **Direct map launch works (no menu):** `Content\System\Swat4.exe "SP-FoodWall?Mutator=SwatMinds.SwatMindsMutator" -nointro`, cwd `SwatMinds\System`. Mutator loads, Timer runs. This unblocks pilot/gym runs without menu input.
- **Hot reload:** every LiveInterval=3 s the mutator runs `exec SwatMindsLive.txt` (file in SwatMinds\System, repo copy SwatMinds/SwatMindsLive.txt) through `Level.GetLocalPlayerController().ConsoleCommand`. Lines are `set <Package.Class> <prop> <value>`; `set` changes the class default AND live instances.
- Verified mid-level: HearRange 3000->1000->3000, MindWeight 0.5->0.9->0.5 (mutator), stock `SwatAICommon.EnemyCommanderAction` HighSkillScreamChance 0.3->0.9->0.3 and MaxMorale 1.5->2.0 on the live instance EnemyCommanderAction7, each within one interval. Log `SwatMinds live ...` only when values change.
- Gotchas: `Actor.ConsoleCommand("exec ...")` from the mutator does nothing (ret empty, no change); a direct `Actor.ConsoleCommand("set ...")` does work. Route exec through the PlayerController.
- Needs restart: code changes (UnrealScript recompile = close game, rebuild .u). Values cached at spawn (e.g. a pawn's current morale already derived from MaxMorale) only affect later reads; behaviour-level before/after in combat not yet measured (player idle in the test).

## Auto officers (10-19, user: "ok enable ai officers and lets work on top of them")
SP only. `AutoOfficers()` in SwatMindsMutator (config `bAutoOfficers=true`, `OfficerThink=2`, `MaxDoorDist=2500`, `OrderTimeout=90`, `bGhostPlayer=false`) gives the stock Element squad its orders, with the player pawn as CommandGiver:
1. Secure the nearest compliant, conscious, unarrested SwatEnemy/SwatHostage (`Squad.Secure`).
2. Else the nearest unused door within MaxDoorDist that has 4 stack-up points on our side (`SwatDoor.GetStackupPoints(LeadLoc).Length >= 4`): open/broken -> MoveAndClear, locked -> BreachBangAndClear, else BangAndClear.
3. Else FallIn.
API: `SwatAIRepository(Level.AIRepo).GetElementSquad()`; commands in SwatAICommon Squads/OfficerTeamInfo.uc (MoveAndClear 678, BangAndClear 700, BreachAndClear 799, BreachBangAndClear 846, Secure 1230, FallIn 612; IsExecutingCommandGoal 545, ClearCommandGoal 524).
Gotchas found:
- Ordering at t~2 s crashes: `Assertion failed: Commander->achievingAction` (UHive::execUpdateOfficerAssignments). Gate: wait until every officer has `ISwatAI.GetCommanderAction()`, first order at >= 20 s.
- A player standing still at spawn blocks the spawn exit: officers walk to 2 nodes beside the player and stall forever (move goals never fail, no log). `bGhostPlayer=True` (player collision off) fixes it for unattended runs; set it via SwatMindsLive.txt `set SwatMinds.SwatMindsMutator bGhostPlayer True`. A real player who moves is fine.
- Minimized window is NOT the cause of stalls (tested windowed-behind with `tools/swat4_bgrun.ps1`).
- FoodWall_Standard_Door6 has 0 stack-up points on one side -> SquadStackUpAction script asserts and the squad hangs; hence the stack-up filter.
- MoveAndClear of Repo_Standard_Door1 never reports complete (room cleared by ~t=45, a hostage complied); `OrderTimeout` clears the goal and moves on.
- Debug: `set SwatGame.SwatOfficer logTyrion True` in the live file prints officer goal traces.
Verified (SP-FoodWall, ghost player, minimized, 330 s): MoveAndClear -> timeout -> Secure SwatHostage1 -> Secure SwatHostage0 -> BreachBangAndClear Door14, 0 asserts. Logs: `SwatMinds officers <cmd> ...`, `officers busy t= ... doordist:` every 10 s.
Next: door scoring with CQB attacker rules (research/superexplainer-cqb.md), AI-vs-AI gym runs (suspect tactics vs auto squad, hot knobs between runs), then co-op.

## Door scoring + gym A/B (10-19, user: "ok lets proceed")
- Mutator: config `bScoreDoors` (default False), `IntelW=1.5`, `IntelRange=1200`, `IntelLife=60`. Intel = suspect `Say()` spots + officer `LineOfSightTo` on non-compliant suspects within 3000 (no omniscience); `AddIntel` merges within 200 uu. Door score = `-dist/1000 + IntelW*IntelBehind` (behind = fresh, within IntelRange, `(I-D) Dot (L-D) < 0`). Scored cmd: locked+intel BreachBangAndClear, locked BreachAndClear, intel BangAndClear, else MoveAndClear. `Tally()` every 30 s: `SwatMinds tally t= score= orders= susDown= susArrest= susFree= hostSecured= offDown= intel=`.
- Runner `tools/swat4_gymrun.py`: per run writes live file (+ghost player, +mode lines, +`--set "Prop value"` lines), launches SP-FoodWall minimized, kills after `--secs`, restores live file, copies log to `--out` (default `SwatMinds\gymruns`), writes summary.md/json. `--parse-only` re-summarizes.
- Round 1 (`SwatMinds\gymruns_r1`, 3+3 runs, 330 s, level t~140 at last tally):

| mode | t | orders | susDown | susArrest | susFree | hostSecured | offDown | asserts |
|---|---|---|---|---|---|---|---|---|
| nearest | 140.67 | 5.33 | 1.67 | 0.33 | 1.33 | 0.0 | 0.0 | 1 |
| scored | 140.67 | 6.0 | 1.67 | 0.67 | 1.67 | 1.33 | 0.33 | 0 |

  Inconclusive: too short, and every run's first order (MoveAndClear Repo_Standard_Door1, no intel yet) stalls into the 90 s OrderTimeout. The one assert is stock (`BerettaM9_ThirdPerson FellOutOfWorld`). Scored mode does pick intel doors (score 1.2-1.5, BangAndClear). Round 2 running: `--secs 600 --set "OrderTimeout 45"`, out `SwatMinds\gymruns_r2`.
- Doctrine research: `research/swat-room-clearing.md` (next officer rules: contact+cover on secure, deliberate by default, don't idle in the funnel, hall/stair overwatch).
- **Parallel null-render gym (10-19, user: "yeah lets make the gym runs be like 5 minutes without spinning up texture rendering and have like 2 or 3 in parallel"), verified 3 at once:**
  - SWAT 4 is single-instance via the UTF-16 mutex name `Swat4IsRunning` (5 hits in Content\System\Swat4.exe; 2nd copy shows "SWAT 4 Already Running"). `-mptest` bypasses it but forces the log to `MPTestClient.log` for every copy (clash), so not used.
  - Runner makes `Content\System\Swat4Gym<k>.exe` (k=1..3; local game-file copies, never commit) with `Swat4IsRunning`->`Swat4IsRunnin<k>` and `ScriptLog.log` (UTF-16 at 0x1a364)->`ScriptLo<k>.log` (otherwise "Failed to write: ScriptLog.log" dialog).
  - Per slot: `-ini=Gym<k>.ini` (Swat4.ini with `RenderDevice=Engine.NullRenderDevice`, 320x240; verified: no D3DDrv/d3d9 module loaded, checked with 32-bit PowerShell), `-userini=GymUser<k>.ini`, `LOG=gym<k>.log`, URL option `?SMLive=GymLive<k>.txt`.
  - Mutator: PostBeginPlay logs `SwatMinds url ...`; `?SMLive=` overrides LiveFile. Gotcha: `GetLocalURL()` starts with the map name, so ParseOption needs `Mid(URL, InStr(URL,"?"))`.
  - The shared SwatMindsLive.txt is now only read (base lines), never rewritten.
  - Run: `py -3.13 -I tools/swat4_gymrun.py --runs 6 --secs 300 --jobs 3 --set "OrderTimeout 45" --out "F:\gogGames\SWAT 4\SwatMinds\gymruns_r2"`.
- **Round 2 (`SwatMinds\gymruns_r2`, 6+6 runs, 300 s, 3 parallel, OrderTimeout 45):**

| mode | runs | t | orders | susDown | susArrest | susFree | hostSecured | offDown | asserts |
|---|---|---|---|---|---|---|---|---|---|
| nearest | 6/6 | 115.17 | 4.67 | 1.67 | 0.0 | 1.83 | 1.17 | 0.67 | 0 |
| scored | 5/6 | 120.6 | 5.6 | 1.6 | 1.0 | 1.2 | 1.4 | 0.0 | 0 |

  Scored looks better (0 officers down vs 0.67, arrests 1.0 vs 0) but n is small and level time only reaches ~120-150 s in a 300 s run (load ~25 s, and with 3 in parallel the game clock runs slower than wall time). scored_5 lost its tallies because the kill cut the log; fixed after the round: the runner appends `exit` to each slot's live file 10 s before the end, so the game quits cleanly and flushes ("Log file closed").

## Gym training (10-19, robot-learning methods; research/robot-gym-training.md)
- `tools/cqbgym/gym_v0.py --train [--gens 40 --rooms 25]`: numpy CMA-ES self-play. Suspect hold-spot weights (5) vs league {doctrine, sloppy, rusher, current trained officer}, then officer knobs (stop, speed, turn, react, near-first; clipped to human ranges) trained to beat current weights. Rooms re-randomized each generation (size, door pos AND width 70-120, pillars). 40 gens x 25 rooms = 34 s. Output `tools/gym_weights.json` (weights, officer knobs, held-out table, history).
- Result (80 held-out rooms, suspect win rate): vs doctrine 0.467 (hand CQB tips 0.451), sloppy 0.925 (0.686), rusher 0.971 (0.660), vs trained officer 0.329 (0.344). Weights: depth .326, off_axis 1.0, hard_cover -.254, beside_frame -.739, door_line -.338. Trained officer ends at limits (speed 420, turn 400, react .15, no stop, near first): the self-play adversary saturates its box, so suspect gain vs a strong officer is small; gym_v0 mixed v0 weights score about the same. Not yet validated in-engine.
- `tools/swat4_gymrun.py --search N`: each candidate = 3 parallel games (scored mode) with random (first 4) then Gaussian-mutated-best IntelW [0,4], IntelRange [300,1500], IntelLife [20,180], OrderTimeout [20,90] `--set` lines. Score = mean over games of susArrest + hostSecured - 2*offDown - susFree from the last tally. Writes `<out>/search.json` (resumable: rerun appends) and logs under `<out>/search_logs/cNNN/`. Other flags unchanged.
- Proof run (`F:\gogGames\SWAT 4\SwatMinds\gymruns_search`, candidate 0: IntelW .54, Range 1317, Life 107, Timeout 37.85, 300 s): run scores -2, -3, None; mean -2.5. Slot 3 never reached a tally (stuck loading, no tally line), levels only reached t=60 at wall 300 s (Strata research was using CPU concurrently). So candidate scores need n>=2 runs with tally and a longer --secs; a candidate with a missing run is averaged over the rest. Not a tuning result.

## Autogym (10-19, endless data loop)
> **User:** "write up an autorun system for these that we can execute and it keeps generating data"

- `tools/swat4_autogym.py`: loops until `F:\gogGames\SWAT 4\SwatMinds\autogym\STOP` exists (or `--hours`). Per cycle:
  1. sim: `cqbgym/gym_v0.py --train --seed 1000+cycle` -> `autogym/sim/weights_NNNN.json`, summary row in `autogym/sim.jsonl`;
  2. engine: `swat4_gymrun.py --search 1` (every 3rd cycle `--reeval 1` reruns the best) into `autogym/engine/<map>/` (search.json + one row per game in data.jsonl); skipped while a real `Swat4.exe` runs, so the user can play;
  3. `autogym/REPORT.md` rewritten (best knobs per map, top 5, last sim).
- Options: `--maps a,b` (rotated), `--secs 600` (wall s per 3-game batch), `--no-sim`, `--no-engine`. Cycle numbers continue across restarts.
- Start hidden: `Start-Process py -ArgumentList '-3.13 -I tools\swat4_autogym.py' -WindowStyle Hidden` (cwd wt9 games/swat4_mods). Stop: create the STOP file.
- swat4_gymrun.py changes: a slot without "SwatMinds url" in its log after STALL=150 s is killed and relaunched once (the stuck-loading slot in the c85e25c proof run); `--reeval M`; per-game rows in `<out>/data.jsonl`; best only counts candidates with >= 6 good games once any has them (one 3-game batch is too noisy).

## Demo ideas test (10-19, user: "great lets test them", after video note tree/142 bycloud Gen 1.5)
- Trajectories: mutator `bTraj` (default off) + `TrajInterval=1.0` logs `SwatMinds traj t= orders= O0:x,y,yaw,state ...` (O officer, E suspect, H hostage; state c free / a arrested / d down). swat4_gymrun.py turns it on in every gym slot and writes `<game log>.traj.jsonl` (one frame per line, order/intel lines kept as `{t, ev}`); data.jsonl rows carry `traj_file` + `traj` count. Goal: demo data for a later learned/TRM brain and for "record the user's playtest as demos".
- Few-shot adaptation in the sim: tools/cqbgym/demo_test.py. Random officer style per trial, suspect sees K demo rooms and picks from generalist + 24 perturbations, scored on 80 held-out rooms. 200 trials, weights_0005: mean gain k1 -0.020, k2 -0.015, k5 -0.008, k10 +0.002, k20 +0.003 (87 wins / 72 losses). Verdict: no gain; the generalist spot scorer is already near the per-style best in this toy sim, so per-player adaptation is not worth building at this data scale. Out: F:/gogGames/SWAT 4/SwatMinds/autogym/demo/demo_test_w5.json.

## Autogym session 1 result (10-19 17:33-20:13, stopped by user)
- 16 sim trainings: held-out suspect win flat (doctrine 0.40-0.53, sloppy 0.93-0.99, rusher 0.96-1.0, trained officer 0.23-0.52). Sim has plateaued; more seeds add nothing.
- Engine SP-FoodWall: 45 games, 43 scored, 10 candidates. Best by rule = #1 {IntelW 2.52, IntelRange 635.25, IntelLife 104.2, OrderTimeout 68.49} score -0.611 over 18 games. #3 and #5 show 0.0 but over 3 games only. Per-game score spread about -8..+3, so 3-game means are noise.
- Main limit: level time reaches only ~150 s (last tally t) per 600 s wall batch, so missions never finish; the score mostly measures the first room. Fix this before more search.

## Gym at full speed (10-19, user: "SWAT 4 gym: make levels run full speed")
- Cause 1: the live file was exec'd every LiveInterval=3 level s; each `exec` (9 `set` lines) stalled the game 6-9 s wall, so level time ran 0.2-0.35x wall (clock probe: normal frames ~280 fps at 1:1, a ~6 s hitch every 3 level s). Not CPU, not null render (D3D single slot same), not a dt clamp.
- Cause 2: WinDrv `UWindowsViewport::ShouldPauseWhenLostFocus` (WinDrv.dll 0x11103920) pauses a slot whose window loses focus ("Pausing game due to lost focus"); with 3 slots (+ focusguard) slots froze at t=0.
- Fix (mutator): `ExitAfter` (final tally + `exit` at that level time, flushes the log), `bAlwaysTick=true` + Tick clears `Level.Pauser` when bGhostPlayer (logs "SwatMinds unpause"), `SideLog()` writes tally/clock/exit lines to System/SMTally_<live base>.txt (closed per write), `Dilation` fixed override, `bAutoSpeed` (off by default), `bClockProbe`, tally line + `wall= frames= dil=`.
- Fix (gymrun): live file exec'd once (`LiveInterval 1000000`), `ExitAfter <secs>`, default `Dilation 4` (override with --set), waits for the processes to quit (kill after secs+60 s), copies the side file to <out>/<mode>_<i>.tally.txt. `--secs` = level seconds now. GYM_D3D=1 env keeps the D3D renderer.
- Verified: 3 slots x 200 level s, dil 1: 232 s wall total, all clean exits, ~270 fps/slot (autogym/speedtest9). 3 slots x 300 level s, Dilation 4: 154 s wall total (82 s in level, 3.7x), ~290 fps/slot, scored mean orders 13.3, offDown 0 (speedtest10). Before: t~60-150 per 600 s wall, missions never finished.
- Caveat: Dilation 4 = ~15 ms sim step; AI/physics results looked in range but compare against dil 1 before trusting a fine A/B.
- 2026-10-19 22:08 autogym restarted at full speed: cycle 1 (sim 24 s + engine candidate #10, 3 games x 600 level s) done 22:11:36, ~3 min/cycle. Old rows (slow era, unfinished missions) still in SP-FoodWall/data.jsonl; compare only new rows. Next: live playtest with the user (engine step pauses while Swat4.exe runs).
- 2026-10-19 22:18 playtest 5 setup: autogym STOPPED again (STOP file). Gym SwatMinds.ini saved as `SwatMinds\System\SwatMinds.ini.gym`; playtest values: bGhostPlayer=False, bAutoOfficers=True (False made officers idle; default True = they self-order), Dilation=1, ExitAfter=0, bClockProbe=False, LiveFile= (empty), bTraj=True, knobs = best #1 (IntelW 2.52, IntelRange 635.25, IntelLife 104.2, OrderTimeout 68.49). Gotcha: gym slots SaveConfig into SwatMinds.ini, so check it before every playtest. Game launched from menu (Content\System\Swat4.exe, cwd SwatMinds\System).
- Gotcha (10-19 playtest 5): launch playtests with `SwatMinds\LaunchSwatMinds.bat` (starts borderless.pyw too), not Swat4.exe directly, or the window is plain windowed. The user could not type in the console (ConsoleKey=192, PT-BR keyboard?); restart the mission rather than relying on console `set`.
- 10-19 borderless fixes: borderless.pyw is now DPI-aware (SetProcessDpiAwarenessContext -4); without it the monitor rect was DPI-virtualized and the window came out too small. Verified rect 0,0,1920,1080, style 0x94000000. LaunchSwatMinds.bat now `start`s the game and exits (no cmd window left open).
- GOG Galaxy: `F:\gogGames\SWAT 4\goggame-1409964317.info` playTasks has a new primary "SWAT 4 SwatMinds (borderless)" -> `SwatMinds//LaunchSwatMinds.bat`; the stock task was renamed "(vanilla)", non-primary. Original is in `goggame-1409964317.info.orig`. Galaxy may need a restart, and an update/verify can revert it.
- 10-19 playtest 5 fixes (compiled OK): (1) instant action always repeated the map because SwatGUIControllerBase.GameStart() -> GuiConfig.SaveLastMissionPlayed() runs after the mutator's PostBeginPlay pick; the pick now runs once in Timer at t>3 (bIADone). (2) first auto-officer order now at ready+3 s (was max(t+10, 20)); the user saw officers idle in the truck. Note: the game pauses on focus loss in human play (unpause only with bGhostPlayer).
- 10-19 GOG: editing goggame-1409964317.info alone did NOT change Galaxy's Play button (Galaxy launched vanilla). Galaxy reads `C:\ProgramData\GOG.com\Galaxy\storage\galaxy-2.0.db` table PlayTaskLaunchParameters: playTaskId=1 now = `F:\gogGames\SWAT 4\SwatMinds\LaunchSwatMinds.bat`, label "SWAT 4 SwatMinds (borderless)" (Galaxy closed while editing; backup galaxy-2.0.db.swatminds.bak; survived a Galaxy restart). Original value: `F:\gogGames\SWAT 4\Content\System\swat4.exe`, label "SWAT 4 Gold Edition".
- 10-19 after playtest 5: (a) instant action: the GUI re-saves LastMissionPlayedName=current map after our pick (SwatGUIState.ini kept SP-FoodWall), so Timer now calls ReapplyInstantAction() every tick once picked (IAPick/IAPickFriendly) and re-saves if overwritten. The user's "only unlocked maps" guess was wrong: all 13 MissionName entries exist and LoadLastMissionPlayed has no unlock check. (b) bEscort=True (playtest ini; gym ini .gym has bEscort=False): no door clearing. Squad FallIn on the player (no OrderTimeout while falling in; Secure still issued). Once the player is still for 1.5 s (moved <120 uu, turned <45 deg), UpdateSectors traces 5 lanes (left/right/back + back diagonals, front 90 deg skipped), sorts them by open length (cap 1500), and posts AimAtPointGoal pri 40 on the nearest officer per lane (attack 80 / engage 85 still win). Goals are cleared when the player moves. Log "SwatMinds escort sectors". Compiled OK, untested in game.
- 10-19 playtest 6 ("good, kinda"): escort is now a "train". UpdateSectors runs every Timer tick (0.25 s) while the squad is falling in. Officers are sorted by distance behind the player (along the player's facing). The tail covers the rear (180). The others cover the side they stand on (90/270), alternating if two stand on one side. Aim points are parallel lanes from each officer (trace, 1200 uu), updated live via G.Point plus AimAtPointAction(G.achievingAction).Point. If the action ended (the body can't turn that far while walking), the goal is re-posted after 2 s. Log "SwatMinds escort train". Compiled OK, untested in game. Next idea: shoulder-tap / bounding (the tail holds the rear until the train has moved on, then catches up; the train halts at doors until all sectors are set). Refs: van der Sterren "Squad Tactics" (AI Game Programming Wisdom, 2002), Killzone position picking, F.E.A.R. squad coordinator (Orkin 2006), Ready or Not, Door Kickers 2.
- 10-19 next design (user idea + CQB refs, video-notes tree/160): (1) a coverage "paint" scorer, top down: threat points = nav points within ~1500 uu with LOS to the squad; painted when an officer's or the player's aim (±30°) + LOS hits them; fades over a few s; score = painted share. Usable live and as an autogym metric. (2) Sector assignment goes greedy on the oldest unpainted "dead space" (train sectors as prior). (3) Shoulder tap = move gate (all sectors held). (4) Director probe: virtual threat at the least-painted out-of-sight point, measure time-to-face; later real suspects.
- 10-19 late, user after the train playtest: "game was nice, lets build that and the taps together with a better cover system into the train. also i have 2 games we will bring this ai into, doorkickers 1 and frozen synapse 2. but tomorrow". TODO 10-20: build into the train the paint scorer + dead-space sector assignment, shoulder-tap move gate, and better cover (officers hold positions at wall/door edges, using AICoverFinder results filtered by sector). Later: port the squad AI (train, paint scorer, director) to Door Kickers 1 and Frozen Synapse 2.
- 10-19 user: "we will add the director ai into the game too": the director is also a live gameplay feature (it throws threats from unpainted, out-of-sight areas during real play), not only an autogym probe. Port it to DK1/FS2 too.
- 2026-10-20 user: "lets implement those ideas for now. and let the ais try to beat the game in a loop for self improvement and generate data unsupervised. later when i get back home we will try giving all the ais the pathfinding and dynamic animation system we tried in advent" / "autonomous unsupervised self improvement". Built (compiled OK):
  - Paint scorer `UpdatePaint` (bPaint, PaintRange 1500, PaintFade 3, PaintCone 0.866 = ±30°): nav cache via AllActors(NavigationPoint) (SP-FoodWall: 440 navs); threat = nav within range with LOS from a squad eye; painted = horizontal aim cone (officers ISwatAI.GetAimOrientation, player GetViewRotation) + LOS. Logs "SwatMinds paint t= share= threats=" every 5 s; Tally line now ends `paint= tap= tapN= dirFace= dirN= dirMiss= dirNoShow=` (means).
  - Dead space `DeadSpace` (escort only): an officer's train lane point is replaced by the oldest unpainted threat nav within 90° of its sector that it can see; held DeadHold 1.5 s or until painted; one officer per point.
  - Halt cover + shoulder tap `UpdateCover` (bCoverHold, escort only): player still HaltTime 1.5 s (<120 uu) -> each officer scores navs within CoverSearch 400 (and <700 from the player) by `CoverScore` = sector view length/1200 + 0.4 wall at back + 0.3 edge (wall on one side only) - dist/1000, must beat its own spot by 0.2; MoveToLocationGoal pri 95 (> MoveInFormationGoal 90), re-posted if it ends away from the spot. "SwatMinds tap dt=" = halt -> all sector aims within ~25°. When the player moves, cover is dropped except the tail, which holds until the gap to the next officer > TapGap 300 (or 8 s), log "tail tap-out".
  - Director `UpdateDirector` (bDirector, live + gym): every DirectorInterval 60 s (±25 %), out-of-sight nav DirectorMin 700..DirectorRange 2500 from the squad with the oldest paint time; nearest free unseen suspect gets MoveToLocationGoal 95 there (else a virtual probe). Time-to-face = first squad LOS -> aim cone; DirectorTimeout 30 s -> dirMiss (seen, not faced) or dirNoShow.
  - Smoke gym 1 game x 200 s SP-FoodWall (autogym/smoke1020): no asserts, paint share 0.13-0.98 (mean 0.68 at t=91), director sent SwatEnemy1 twice, first = noShow (suspect did not walk into view in 30 s).
  - Gym: swat4_gymrun.py parses the new fields (EXTRA regex); cand_score now adds `+ 2*paint - 0.5*dirMiss` (old candidate scores not comparable). SwatMinds.ini = gym ini again; playtest ini saved as SwatMinds\System\SwatMinds.ini.play (restore it before a GOG playtest).
  - Autogym restarted 10-20 07:52 over the 13 SP maps present in Content/Maps (no TSS maps; SP-Subway etc. fail "Can't find file"): FoodWall,Hospital,Tenement,ABomb,ArmsDeal,AutoGarage,Casino,ConvenienceStore,DNA,FairfaxResidence,Hotel,JewelryHeist,RedLibrary; ConvenienceStore verified, hidden. Stop: STOP file in SwatMinds\autogym.
  - Later (user at home): give all AIs the Advent pathfinding + dynamic animation system (skill advent-mod).
- 2026-10-20 10:45 results (114 games since 07:51, 13 maps): no real improvement (mean score -7.1 first half -> -6.9 second half). Clears (all suspects down/arrested, 0 officers down): FairfaxResidence 5/9, FoodWall 5/9, ConvenienceStore 2/9, all others 0. Kills ~10x arrests; big maps lose 3-4 officers; Tenement leaves ~13 suspects free. Director: 98 sends, ~all noShow.
- 2026-10-20 11:00 user: "add the fix and then lets let it run please". Changes:
  - Director bug: target was a nav the squad could NOT see, so an arriving suspect stayed unseen (noShow every time). Now target = a threat nav (squad has LOS) with the oldest paint time; the timeout log adds `left=` (suspect distance to the point) and `act=` (move goal has an action).
  - Search: + OfficerThink (0.5-4) and MaxDoorDist (1000-4000); cand_score arrests x2; autogym REEVAL_EVERY 3 -> 2; every map's search.json archived to search_v1.json (fresh search, scores not comparable). Paint/cover/tap/dead-space knobs are escort-only, so the ghost gym cannot tune them (needs a player bot or escort playtests).
  - Autogym restarted 10:59 (13 maps).

## Idea notes (parked 10-20, implement + test later)
User, 2026-10-20: "my idea was that in shadertoy i remember that there was a noise pixel refresher that was used for fast raytraced update, i was thing of having that plus surfels for updating visual knowledge of the maps, the ais should sometimes have a base information of wall layouts but not of furnitures or clutter like how some buildings have only floor schematics. like they are discovering how to navigate and always have a feel for proecting agrainst feom where the enemies might come from or from where their vision is not covering."
- **Noise-refresh vision rays.** Shadertoy trick: each frame re-trace only a blue-noise/dithered subset of pixels and blend into the accumulated image (temporal amortization). For the AIs: each tick every pawn casts a small blue-noise subset of rays inside its view cone (fovea dense, periphery sparse) instead of a full scan; results accumulate over ticks. Cheap, and gives a natural "takes a moment to take a room in" delay.
- **Surfel knowledge map per side.** Rays that hit write surfels (position, normal, last-seen time, confidence, kind: wall / clutter / door / pawn). Confidence decays over time (like stock AwarenessProxy points, but built from what was actually seen). Officers share one map (the Hive); suspects share theirs per group.
- **Floor-plan prior.** Start with walls only (BSP / static level geometry = "floor schematic"); furniture, static meshes and clutter are unknown until a ray hits them. Pathing and cover use the known map; the AIs discover the real layout as they go. Variant knob: no prior / walls / full map.
- **Exposure field.** From the surfel map: open frontier (unknown or stale space next to known openings: doors, corridor mouths, gaps behind clutter) = where an enemy could come from. Officers keep aim/cover on the highest-exposure directions their own vision is not covering. This generalizes the paint scorer + dead-space aim (which today use nav points + full FastTrace, and know the whole map).
- **Human-like perception on top** (10-20 chat): periphery detects motion only ("something there"), the fovea cone identifies; attention budget of ~3-5 tracked targets; reaction time grows with angle off the view direction, clutter, darkness, surprise.
- **Test in the gym:** compare prior = none / walls / full on paint share, dirFace (time-to-face), offDown, clears. The director keeps its god view as the probe.
- 2026-10-20 13:20: the F: USB enclosure (UASPStor) reset and dropped off; NTFS logged 19 delayed-write failures (F:\$Mft, $BitMap, SwatMinds\System files). The autogym died with it; orphan Swat4Gym2.exe killed. Data from 10:59 to 13:20 is on F: and unread. After replugging: run `chkdsk F:` before restarting the gym; consider moving the autogym OUT dir to C: to cut USB writes.
- 2026-10-20 21:40 user: "reseated try again please". F: back; `chkdsk F:` found errors (bad $I30 index entries, $SDH/$SII, MFT bitmap); `chkdsk F: /f /x` fixed them ("O Windows fez correções"), orphan .wav files restored to their folder. SwatMinds.u/.ini/.ini.play and all 13 data.jsonl files parse fine.
- Results 10:59-13:19 (87 games, fresh search, new score): no improvement yet (mean -7.24 first half -> -7.35 second half). Clears: FairfaxResidence 8/9, FoodWall 3/6, ConvenienceStore 2/6, others 0. Arrests still rare (0-1.2/game vs 3-11 kills). Biggest losses: officers down 3-4 on big maps, Hotel/Tenement ~10 suspects free.
- Autogym OUT moved to C:/Users/john/Documents/SwatMindsGym/autogym (old copy left on F:). Restarted 21:44 (13 maps); the game and slot logs still run from F:.
