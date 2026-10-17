# SWAT 4 AI communication: research and SwatMinds design

SDK root: `C:\re\swat4\sdk\SDK\Source\Game` (paths below are relative to it). Read-only research, nothing copied.

## Part A: how other games do it

| Source | Takeaway for us | URL |
|---|---|---|
| F.E.A.R., Orkin, "Three States and a Plan" (GDC 2006) | Dialogue is chosen after the squad layer has decided, and is hand-hooked into code. Orkin calls the apparent mutual understanding "smoke and mirrors". Lines are written as exchanges (ally asks status, hit man answers) rather than lone shouts. Dialogue is also used to explain inaction ("nowhere to go"). | https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf |
| Halo, Butcher and Griesemer, "The Illusion of Intelligence" (GDC 2005) | Combat dialogue is driven by decisions and stimuli (hurt, death, saw enemy, grenade, seek cover). Selection uses priority, context, uniqueness and relevance. It picks a random dialogue type and nearby characters can reply. Slide: 57 events, 166 dialogue types, 12 speakers, 5147 lines. It is flavour only, with no state change. | https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf |
| Left 4 Dead / Source, Ruskin, "AI-driven Dynamic Dialog through Fuzzy Pattern Matching" (GDC 2012) | Many world facts are matched against thousands of lines. The most specific matching rule wins and less specific rules are fallbacks. Writers add cases without programmers. I could only read abstracts and secondary write-ups. Repeat control and speaker choice are from my memory of the talk, not verified. | https://www.gdcvault.com/play/1015528/AI-driven-Dynamic-Dialog-through ; https://emshort.blog/2012/03/16/gdc-2012-talk-on-dynamic-dialogue/ |
| The Last of Us, McIntosh, "Human Enemy AI" (GDC 2014) | Talk exists, but it is members-only and I could not read it. Treat enemy-communication claims about it as unverified. | https://gdcvault.com/play/1020338/The-Last-of-Us-Human |
| Ready or Not (VOID) | Suspect behaviours are fake surrender, faking death, human shields and hiding. I found no primary source on their callout implementation. | https://voidinteractive.net/?p=2442 |
| Game AI Pro (gameaipro.com) | Searches found no dedicated bark or speech chapter. Generic bark managers use priority, cooldown, once-only flags and queueing (https://www.strayspark.studio/docs/godot-dialog-system/barks). A token manager limits squad members performing the same action (the Unreal token plugin idea). | https://www.gameaipro.com |

**Patterns to reuse.**
- Speech is the output of a decision. Fire it after the state change, never as the cause.
- Gate it with priority, per-speaker cooldown, a squad-wide "one speaker at a time" token, and a higher-priority interrupt (SWAT 4 already has `bClearEventQueue` for this).
- Make it matter. F.E.A.R. and Halo mostly fake coordination. A heard call should also write to the listeners' state (shared knowledge), so the bark is true and not decoration.
- Prefer exchanges (call, then reply) over lone shouts.

## Part B: SWAT 4 SDK findings

**Firing speech.** Speech is an effect event on the pawn.
- `SwatAICommon/Classes/Actions/CharacterSpeechManagerAction.uc:19`, `TriggerSpeech(name SpeechEffectEvent, optional bool bClearEventQueue)`, is public and takes any event name. It queues the event, and `bClearEventQueue` interrupts the current line (`:42-55`).
- The queue runs in the `Running` state (`:160-175`) via `ISwatAI(m_Pawn).LatentAITriggerEffectEvent(...)` (`SwatAI.uc:2791`).
- `LatentAITriggerEffectEvent` first calls `TriggerEffectEvent(EffectEvent,,,,,,true)` as a query (`SwatAI.uc:2808`). If no sound is registered for the event it does nothing, so a wrong or unmapped name fails silently.
- It then calls `AITriggerEffectEvent` (`SwatAI.uc:2848`), which RPCs to clients in multiplayer, and waits up to `MaxAIWaitForEffectEventToFinish`.
- A mod gets the manager from a pawn:
  - Any AI: `ISwatAI(p).GetSpeechManagerAction()` (`ISwatAI.uc:146`, impl `SwatAI.uc:2275`).
  - Suspects: `ISwatEnemy(p).GetEnemySpeechManagerAction()` (`ISwatEnemy.uc:47`, impl `SwatEnemy.uc:597`).
  - Officers: `ISwatOfficer(p).GetOfficerSpeechManagerAction()` (`ISwatOfficer.uc:17`, impl `SwatOfficer.uc:698`).
- Caveat: `SwatAI.uc:2277-2279` asserts the speech goal exists. Guard against a dead or not-yet-initialised pawn. `ReadyToTriggerEffectEvents()` (`SwatEnemy.uc:1055`) also gates speech until the pawn has equipped.

**Suspect events** (`EnemySpeechManagerAction.uc`):

| Event | Wrapper | Line |
|---|---|---|
| `AnnouncedSpottedOfficer` / `...Scared` / `...Surprised` | `TriggerOfficerEncounteredSpeech` | 12 |
| `DoorBlocked` | | 28 |
| `AnnouncedFlee` | `TriggerFleeSpeech` | 33 |
| `CalledForHelp` | `TriggerCallForHelpSpeech` | 38 |
| `AnnouncedInvestigate` | | 43 |
| `AnnouncedBarricade` | | 48 |
| `AnnouncedNonCompliant` | | 53 |
| `ReactedDownOfficer` | | 58 |

Base class (`CharacterSpeechManagerAction.uc:62-140`):
- `AnnouncedCompliant`, `AnnouncedRestrained`
- `ReactedDown`, `Died`
- `ReactedInjuryNormal` / `ReactedInjuryIntense`
- `ReactedGas`, `ReactedBang`, `ReactedPepper`, `ReactedTaser`, `ReactedBreach`, `ReactedSting`, `ReactedBeanBag`
- `Screamed`, `ReactedHitByDoor`

**Officer events** (`OfficerSpeechManagerAction.uc`):
- Threat reports: `ReportedSuspectSpotted` (:41), `ReportedSuspectDown` and `ReportedSuspectNeutralized` (:46), `ReportedMaleSuspectFleeing` and `ReportedFemSuspectFleeing` (:58), `ReportedMale/FemSuspectWillNotComply` (:70), `ReportedHostageSpotted*` (:83), `ReportedHostageIncapacitated` (:97)
- Casualties: `ReportedOfficerDown` (:15), `ReportedLeadDown` (:20)
- Reactions to the player: `ReactedFirstShot`, `ReactedSecondShot`, `ReactedThirdShot` (:25-37)
- Sweep and clear: `StartedClearing` (:182), `ReportedThresholdClear` (:187), `ReportedContinuingClear2Plus` and `ReportedContinuingClear2Minus` (:192-199), `AnnouncedClear` (:116)
- Covering and orders: `AnnouncedStillCovering` (:322), `RepliedMoveTo`, `RepliedFallIn`, `CompletedMoveTo`, `CompletedFallIn` (:302-319)
- Secured: `ReportedSuspectSecured` (:292), `ReportedSuspectRestrained` (:362)
- Mirror and optiwand counts: `ReportedOneSuspectSeen`, `ReportedManySuspectsSeen` and others (:374-420)
- Also present: `AnnouncedComply` and `AnnouncedComplyWithGun` (:121-128).
- Hive-driven lines: `Hive.uc:303` fires suspect-down via the element squad, and `Hive.uc:670` fires `TriggerSuspectSpottedSpeech` when an officer first sees a suspect.
- Squad-level speech goes through `ElementSpeechManagerAction.uc:60`, which picks the closest officer, so one voice speaks.

**Can a mod call these?** Yes. The wrappers and `TriggerSpeech` are public. The mutator package must compile after `SwatAICommon` and `SwatGame` in EditPackages. I verified this by reading signatures only, not by compiling a test.

**Knowledge sharing in stock code.**
- There is no suspect hive. `Hive.uc:3` is "organize functionality between the officers": blackboard, officer assignments, `NotifyEnemyBecameThreat/Fleeing` (:154-165), `NotifyAIDied` (:284).
- Suspect-to-suspect sharing is by direct scan:
  - `RegroupAction.uc:366` `CallForHelp()` plays `CalledForHelp`, then loops `Level.pawnList`. For every conscious SwatEnemy in the same room with state below `EnemyState_Aware`, it calls `GetEnemyCommanderAction().CreateBarricadeGoal(CurrentEnemy.Location, false, false)`. This is the template to copy: speech plus state change.
  - `SwatEnemy.uc:517` `NotifyNearbyEnemiesOfDeath` hands nearby suspects with line of sight `NotifyNearbyEnemyKilled` (`EnemyCommanderAction.uc:478`). That lowers their morale via `ChangeMorale`. Stock never speaks here, which is our gap.
- Levers: `ISwatEnemy.BecomeAware()` (`ISwatEnemy.uc:36`), `SetCurrentState(EnemyState_Aware)` (`EnemyCommanderAction.uc:870`), `CreateBarricadeGoal` (`:1230`). `SwatAIAwareness/AwarenessProxy.uc` has a native `ForceViewerSawPawn(viewer, seen)` (:44). It is the nearest thing to injecting shared sight, and I did not test it.

## Part C: design for SwatMinds (comms layer)

Reuse only existing recorded lines. Splicing means chaining two stock events in `TriggerSpeech` (call, then reply). No TTS, no voice conversion.

**1. Emotion-to-event map** (fire from the existing emotion update, after the state change):

| Trigger | Event | Who |
|---|---|---|
| First sight of officers, or fear rising past the "spooked" threshold | `AnnouncedSpottedOfficer(Scared)` | the seer |
| Shot (hit) | `ReactedInjuryNormal` or `ReactedInjuryIntense` (by damage) | victim |
| Down | `ReactedDown` | victim |
| Fear high and nerve low (fleeing) | `AnnouncedFlee` | self |
| Taking fire in cover, with allies nearby | `CalledForHelp` | self |
| Ally downed or killed within hearing | `ReactedDownOfficer` for an officer kill (stock `AttackOfficerAction.uc:150`) | the nearest witness |
| Anger spike (a friend hit by an officer) | `AnnouncedNonCompliant` | nearest angry ally |
| Stress high, no contact (investigating) | `AnnouncedInvestigate` | self |
| Nerve breaks | `AnnouncedCompliant` | self |

Add a one-line reply from the nearest unhurt ally, delayed 0.8 to 1.5 s, using `AnnouncedInvestigate` or `CalledForHelp`. This is the F.E.A.R. status-exchange pattern.

**2. Gating.**
- Per-pawn cooldown of 4 s, or 10 s for the same event.
- Squad-wide speech token inside `SpreadFear`'s 3000-unit range: one speaker at a time, and the token is held until the line ends.
- Priority: Died, Down, Injury, CalledForHelp, Flee, Spotted, Investigate. Use `bClearEventQueue` only for priority 3 and above.
- Never speak while stock code is mid-line. Skip when `CharacterSpeechManagerAction` is not idle.

**3. Heard callout changes allies' state.** Reuse the `CallForHelp` loop, over the 3000 range with line of sight not required:
- `CalledForHelp`: +stress on listeners; those in `EnemyState_Unaware` or lower get `CreateBarricadeGoal(callerEnemyLocation)` (regroup or cover).
- Spotted-officer callout: listeners below `Aware` go to `BecomeAware()` once. This is the "they're here" effect.
- `AnnouncedFlee`, `ReactedDown`, `Died` heard: +fear on listeners, scaled by `SpreadFear`. Nerve-low listeners may answer with `Flee` or `Compliant`.
- Anger callouts raise anger in allies who are not already scared.
- A callout never raises fear above a cap. Without the cap, panic cascades.

**4. Officer side.**
- Reports to the player: on a first sighting by an officer, let `Hive.uc:670` do its job. Add a mutator trigger for the cases stock misses (an officer shot, a suspect fleeing, a suspect near the player) using `ReportedOfficerDown`, `ReportedMaleSuspectFleeing` and `ReportedSuspectNeutralized`, through `ElementSpeechManagerAction` so only the closest officer speaks.
- Covering: when the player takes a hit or a suspect gets line of sight to the player, the nearest officer says `AnnouncedStillCovering` or `ReactedFirstShot` and takes the engage position. Use `Hive.RequestNewEngagingPointForOfficer` (`Hive.uc:460`) or an existing engage action, and do not write new movement code.
- Cooldown 6 s per officer, and only one officer line at a time (the element token already exists).

**5. Verification.** Compile a test mutator, then call `ISwatAI(p).GetSpeechManagerAction().TriggerSpeech('AnnouncedFlee')` in-game on a suspect and confirm the sound plays and multiplayer clients hear it.
