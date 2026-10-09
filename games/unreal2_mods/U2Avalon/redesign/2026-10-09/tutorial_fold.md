# Avalon redesign, 2026-10-09: folding the tutorial into the route

> **User decisions, 2026-10-09:**
> - **Hawkins** is the stock male Commander Hawkins. Every new line of his is spliced from his own recorded lines, by phonetic or word mix (VoiceSplice).
> - **Never AI-generated voice**, for any character: no Piper and no kNN-VC. Lines below marked Piper must be spliced from stock recordings or cut.
> - **Hints are off for now** (`AvalonTutor Hints=0`). The safety nets stay.
> - **No grenade launcher** on this route. The player uses it in other maps.


The user's direction: *"this also sounds like a nice place to fold the tutorial into for it be to natural and let
player discover how it works"*.

This is a design only. Nothing was built, run, generated or downloaded. The game was not started, and no GPU,
editor or pilot runs were made. The stock tutorial was read from the user's own install (Dialog\, Scripts\,
System\*.int, UIScripts\, and class-name counts in the .un2 files) and from the local script export in
Documents\Tools\u2_export. The web sources in section 9 are reference only.

Inputs:
- level_designer.md: the critical route, encounters E1-E4 and I1-I4, and the sluice reveal (its section 4).
- director.md: frames F1-F14. **F1 (the window) and F5 (the catwalk) stay combat-free.**
- writer.md: the parti, Hawkins as the catwalk figure, and the citizens.
- artist.md: the colour grammar.
- engineer.md: rails, ladders and stairs.

---

## 0. The short version

1. **The stock tutorial is two maps.**
   - **TutA** is the command room: the cutscene, the salutes, Hawkins' "training run or ship?" choice, the
     objectives and the lift.
   - **TutB** is the basement course with Raff: the suit scan, the HUD, use, dialogue numbers, the obstacle
     course, the shooting range, a 5-point deathmatch, and the health and energy stations.
   - It teaches about 25 things, nearly all of them as "Raff says, then a key prompt, then a trigger waits for
     you to do it".
2. **On the new route each mechanic gets three moments.** Each place has a reason to exist in the town.
   - **Discover:** the world sets up the need.
   - **Safe first use:** nothing can hurt you.
   - **Test under pressure:** a later fight needs it.

   The cue is diegetic every time: a light in the artist's colour grammar, a sound, an object, a stencil, the
   PA, or a short Hawkins radio line.
3. **Key prompts survive only as an opt-in fallback.** They appear after you've been stuck for N seconds: the
   stock AlarmTrigger text such as "Crouch Key = " plus your real binding, one line, 4 s. They never show
   before the world has had its turn.
4. **The stock course is not deleted. It becomes the optional drill.** At the end, Hawkins' own stock line ("We've
   got a new refresher course set up in the basement. Either give it a run or get back to your ship.") and her
   stock two-choice menu still send the player to TutB or to the ship. Players who want drills get Raff,
   untouched.
5. **There are two blockers in the stock wiring that the generated TutA maps inherit** (section 2):
   - TutA runs **U2TutorialGameInfo**: no HUD (`bDisplayHud=false`) and no default weapon;
   - TutA's cine script **takes the power suit away** (`removeitemfromplayer U2.PowerSuitPhoenix`).

   A route with six fights needs both changed.

---

## 1. The stock tutorial inventory

### 1.1 Table: mechanic -> how TutA/TutB teaches it -> source

Mechanism names are U2 classes, or events wired between them. "dlg" means a DialogEngine conversation (.dlg
INI) started by an AI script's `dialoginitiate`.

Paths used in the table:
- `D\` = `<game>\Dialog\`
- `S\` = `<game>\Scripts\`
- `I\` = `<game>\System\`
- `E\` = `Documents\Tools\u2_export\`

| # | mechanic | how the stock tutorial teaches it | mechanism | source |
|---|---|---|---|---|
| A1 | Opening, place and title | A dropship flies in. Letterbox text reads "Terran Colonial Authority HQ" / "Odyssey IV". Dalton (a 3rd-person stand-in) walks in and salutes, and Hawkins walks to him | SceneManager `TutorialACutscene` fires DropshipPath, MusicTrigger, SpecialEvent DropshipSound, 2 AlarmTriggers (`bLetterboxText`), and U2Dispatchers PlayerTutAStart / Player02TutAStart / PlayerTutASalute / TutADestroy | zonemaps\TutA_beats.md; `I\TutA.int` AlarmTrigger13/14; `S\TutA\PlayerTutA.u2s`, `Player02TutA.u2s`, `CommanderCinTutA.u2s` |
| A2 | Story: denied reinstatement, Ne'Ban, "the quietest patrol" | A cutscene conversation, 12 voiced nodes (Marshal/Commander) | dlg `CommanderTutACutscene`, ExitEvent dlgCutsceneOver; voice `Tutorial_A.Tutorial_01.Tutorial_01_002 .. _011` | `D\TutA\CommanderTutA.dlg` |
| A3 | The suit is taken away (no armour, no HUD in TutA) | Silent: the cine script removes it | `removeitemfromplayer U2.PowerSuitPhoenix`; game type `U2TutorialGameInfo` (`bDisplayHud=false`, `bGiveDefaultWeapon=false`; the TutA .un2 holds the class name once) | `S\TutA\CommanderCinTutA.u2s`; `E\full_U2\Classes\U2TutorialGameInfo.uc` |
| A4 | Moving and looking | Implicit: free walk in the command room | none | - |
| A5 | People react to you | Marines snap to attention within 384 UU. One says "Glad you could drop by, Marshal" (a line borrowed from MM_Marsh) | `testactorinrange Player 384` -> `agentcall Event_A_Attention`; dlg `Marine01TutASalute` | `S\TutA\Marine01-03TutA.u2s`; `D\TutA\MarinesTutA.dlg` |
| A6 | Using people (ambient) | Kai technicians at consoles answer "use" with seven alien babble lines in turn | dlg `KaiTutASpeech` (U2KaiA.Misc.Speak1-7, Enable/DisableNode chain); `agentcall Event_ButtonPress02` | `D\TutA\KaiTutA.dlg`; `S\TutA\Kai01/02TutA.u2s` |
| A7 | Dialogue choices (numbered) | Hawkins initiates: "Do you want to take the training run or get back to your ship?" with 2 choices (Tutorial / Return to ship) | dlg `CommanderTutAWelcome` -> ExitEvents dlgTutATraining / dlgTutADropship + dlgTutAElevator | `D\TutA\CommanderTutA.dlg`; `S\TutA\CommanderTutA.u2s` |
| A8 | Locked door as a gate | The command-room door is locked during the talk and unlocked after the choice | `sendevent CommandRoomDoorTrigger` (toggle) -> Mover CommandRoomDoor | `S\TutA\CommanderTutA.u2s`; TutA_beats.md |
| A9 | Objectives screen (U2's "PDA") | A new objective with a chime and a screen line: "Run through the TCA training program (Press F4 to list current objectives)" / "Return to your dropship (Press F4 ...)" | ObjectiveEvent u2sObjectiveTutorial / u2sObjectiveDropship / dlgTutAElevator (`U2GameInfo.UpdateObjective`, sound U2AmbientA.UI.NewObjective); AlarmTrigger0/2 text; LevelObjectives Objective1-3 | `I\TutA.int`; `E\cur_U2\ObjectiveEvent.uc` |
| A10 | The use reticle on objects | The lift trigger shows "Elevator" in the use reticle | Trigger5 `Description=Elevator`; `UseReticleOnEvents` (UseReticleText/Corners/TopBars) | `I\TutA.int`; every U2 actor's defaultproperties |
| A11 | Lift | Use the lift: beep, door, shake, ride. The choice flips which lift works | U2Dispatcher BigLiftDispatcher -> SpecialEvent BigLiftBeep, Mover BigLiftDoor, EarthquakeTrigger BigLiftShake, Mover BigLift; PropertyFlipper u2sFlipLifts + `setproperty Mover1..5 Tag/bHidden` | `S\TutA\CommanderTutA.u2s`; TutA_beats.md |
| A12 | Level exit | The lift goes on to TutB (training) or the Atlantis (ship) | TutBLevelChange / AtlantisLevelChange | TutA_beats.md (ambience chains) |
| B1 | Suiting up | Raff's script gives the suit when the player arrives | `giveitemtoplayer U2.PowerSuitPhoenix` | `S\TutB\RaffTutB.u2s` |
| B2 | Meeting the trainer, a door opens | "How ya doin', Marshal? ... Let me reboot the system." Raff types at a console, then "All set. Go on in." | dlg `RaffTutBWelcome/1/2` (Event OpenTutorialDoor), `agentcall Event_A_ButtonPress`, typing-sound dispatcher | `D\TutB\RaffTutB.dlg`; `S\TutB\RaffTutB.u2s` |
| B3 | Suit and lore exposition | A hologram Raff scans the suit: "XA/F power armor ... Underwater capable. Rechargeable shields. Plasma HUD" | dlg `RaffTutBScan/1/2/3`; holo projector scaler events; SpecialEvent "Scanning Sequence" | `D\TutB\RaffTutB.dlg`; `S\TutB\RaffHUDTutB.u2s`, `RaffHUD2TutB.u2s` |
| B4 | Reading the HUD | The HUD switches on, then a voice-over: health and shield upper left, ammo upper right (clip above reserve), weapons down the right | `sendevent TurnOnHUD`, `FlashDispatcher`; dlg `RaffTutBScan4/5` | same |
| B5 | Use (people and switches) | "Come over and look at me to activate the use reticle, then hit your 'use' control." A key prompt follows | dlg `RaffTutBScan6` ExitEvent dlgUseKeyMessage -> AlarmTrigger5 "Use Key = " + `KeyBinding` | `D\TutB\RaffTutB.dlg`; `I\TutB.int` |
| B6 | Dialogue numbers | "Go ahead, pick a number." Three throwaway choices | dlg `RaffTutBDialogTest` a/b/c | `D\TutB\RaffTutB.dlg` |
| B7 | Buttons open doors | "Go use the button next to the exit." | Trigger `Description=Door` (Trigger1/4/7/12/29) -> door movers | `I\TutB.int` |
| B8 | Suit radio | "you'll hear me through your suit's radio ... even extends off-planet" | dlg `RaffTutBAgilityTraining/1` (Speaker RaffRadio, `SoundFile=...,Player` = played on the player) | `D\TutB\RaffTutB.dlg`; `S\TutB\RaffObstacleCourseTutB.u2s` |
| B9 | Jump | "Jump over these blocks." Then a key prompt | dlg `RaffTutBAgilityTraining2` -> dlgJumpKeyMessage -> AlarmTrigger10 "Jump Key = "; event PlayerJumpedBlocks | same + `I\TutB.int` |
| B10 | Mantle | "If you jump straight up, and don't stop, you'll drag yourself onto that ledge." | dlg `...3/4`, dlgMantleMoverDispatcher (a mover raises the ledge), AlarmTrigger8 "Jump and hold down the jump button to mantle."; MantleMoverDone | same |
| B11 | Crouch | "crouch down and crawl under these blocks. Don't worry. I won't let 'em drop any further." | dlg `...5`, CrouchMover (blocks lowered), AlarmTrigger6 "Crouch Key = "; CrouchMoverDone | same |
| B12 | Combine the moves | "Use all your skills to get to the other side of the room. Ready? Go!" | dlg `...6`, dlgSetupHardCourse; ObstacleCourseFinished | same |
| B13 | First weapon pickup | The dispersion pistol on a tray: "Go ahead. Grab it." | DPTrayDispatcher; `giveitemtoplayer u2weapons.weaponTutorialInvDispersion` + `playsound U2WeaponsA.Dispersion.DP_Pickup`; PlayerTookDP | `S\TutB\RaffShootingRangeTutB.u2s`; `D\TutB\RaffTutB.dlg` |
| B14 | Primary fire | "Take a couple practice shots." Kraal-shaped targets. Range lamps go red, then green on a hit | Range01Door; KraalRangeLOSTrigger/KraalRangeSeen; DPPrimaryFired(Acknowledge); StaticMeshActor bHidden swaps (red/green lamps); AlarmTrigger2 "Primary Fire = " | same + `I\TutB.int` |
| B15 | Alt-fire (charge) | "Give the alternative fire a try. It builds up a charge" | dlg `...WeaponsTraining4`; DPSecondaryFired; AlarmTrigger4 "Hold down the alt fire to charge. Release to shoot. Alt Fire = " | same |
| B16 | Weapon tray / switching | The weapon tray slides in with the DP, AR and GL slots lit | TutorialHUD.ui: Tutorial_ShowWeaponTray / HideWeaponTray / HiliteWeaponN | `<game>\UIScripts\TutorialHUD.ui` |
| B17 | Assault rifle, auto fire, ammo HUD | "Load it up with ammo and mow down this dangerous desperado." "watch the upper right of your HUD" | `giveitemtoplayer u2weapons.weaponTutorialInvAssaultRifle`; CARPrimaryFired | `S\TutB\RaffShootingRangeTutB.u2s`; dlg `...6/7` |
| B18 | Reload | "Always try to find a quiet moment to reload before combat." | `sendevent ReloadMessage` -> AlarmTrigger3 "Reload Key = " | same + `I\TutB.int` |
| B19 | AR alt-fire, ricochet | "a concentrated bolt of five shards ... will even bounce off walls. See if you can ricochet" | CARSecondaryFired(Acknowledge) | same |
| B20 | Grenade launcher: contact vs timed | "tapping your primary fire makes the grenades explode on contact ... Holding down the trigger engages the timing mechanism" | `giveitemtoplayer u2weapons.weaponInvGrenadeLauncher`; GLPrimaryFired; AlarmTrigger1 "Tap the button to fire a CONTACT grenade, hold down primary fire to launch a TIMED grenade." | same |
| B21 | Grenade types (alt-fire cycles) | "Use your alt-fire to switch between grenade types. The crosshair on your HUD will tell you which one is chambered." Incendiary ammo appears | GLSecondaryFired; `setproperty ammoGrenadeIncendiary0 bHidden false`; ShootingRangeGrenadeFlipper; AlarmTrigger9 | same |
| B22 | Optional mastery | "You have unlocked the secret shooting range!" | AlarmTrigger7 | `I\TutB.int` |
| B23 | Weapons are taken back | Tutorial guns and ammo are removed and the tray is hidden | `removeinventoryfromplayer ...`, TakeWeaponsTrayDispatcher | `S\TutB\RaffDMTutB.u2s` |
| B24 | Combat loop: deathmatch vs Raff, first to 5 | Health and shields reset on death; a scoreboard; Raff taunts; "load up on ammo before you go in"; a bail button | `U2TutorialGameInfo` (NumKillsToWin 5, PawnFactory RaffBotFactory, RaffTrainingBot, `PowerSuitPhoenix.RestoreHealthAndArmor`, UI events TutorialScoreboardOn/Off, WhiteFlash); `U2PlayerTutorial.PreventDeath`; dlg `RaffTutBDeathMatch*`, PlayerWon/Lost, Coward | `E\full_U2\Classes\U2TutorialGameInfo.uc`; `E\cur_U2Pawns\U2PlayerTutorial.uc`; `S\TutB\RaffDMTutB.u2s` |
| B25 | Picking up energy from a kill | "run over my 'holo-corpse', so your power armor absorbs any remaining energy and applies it to your shields" | dlg `RaffTutBDeathMatch_INSERT` (only voiced here; whether real NPC kills do the same is **unverified**) | `D\TutB\RaffTutB.dlg` |
| B26 | Health and energy stations | "Just step inside each station and they'll work automatically." | HealthStation / EnergyStation (PowerStation: 75 units, 25/s, `bLimited`/`RechargeRate`; 2 each in the TutB .un2); dlg `RaffTutBStations1` | `E\cur_U2\HealthStation.uc`, `EnergyStation.uc`, `PowerStation.uc` |
| B27 | End | "Good luck, Marshal. Go keep the frontier safe." | dlg `RaffTutBEndTutorial*` ExitEvent dlgEndLevel | `D\TutB\RaffTutB.dlg` |

Voice files: `<game>\Voice\Tutorial_A\Tutorial_01\` (16 files, Hawkins and Dalton) and `Tutorial_02\` (54 files, Raff
and Dalton). The KeyBinding mechanism (`AlarmTrigger.KeyBinding`, a string appended to AlarmMessage) is in
`E\cur_U2\AlarmTrigger.uc`.

### 1.2 What the stock tutorial does NOT teach

The request asked about these. The tutorial doesn't cover them; they come up in the missions.
- **Aida:** not in TutA or TutB at all.
- **Ne'Ban:** named once, in Hawkins' line `CommanderTutACutscene5` ("a Hex-Core alien named Ne'Ban"). He is
  never seen. Isaak does not appear either.
- **Deployables** (AutoTurret, RocketTurret, FieldGenerator, ProximitySensor, EnergyRelay; `DeployableInventory`):
  none in either map. They are first met in the missions.
- **Lean, walk-key and swimming:** not taught. Swimming is only claimed ("Underwater capable"). Neither map
  has a WaterVolume, and TutB has no LadderVolume.
- **Inventory beyond weapons:** only the weapon tray (B16). There is no item or deployable inventory lesson.

---

## 2. Things that constrain the fold (read before building)

1. **Game type.** TutA (and so every TutA_* map built from a TutA copy, including the swapped campaign TutA) runs
   `U2TutorialGameInfo`, with `bDisplayHud=false` and `bGiveDefaultWeapon=false`. Its `AdjustPawnClass` forces
   `U2Pawns.U2PlayerTutorial`.
   - The six fights need the HUD.
   - Either set the generated map's LevelInfo game type to the campaign's `U2GameInfo` subclass (an editor step in
     `town.py`/uedlib, verify the exact class), or have the mutator turn the HUD on.
   - The HUD switching on is itself a lesson (section 4, L1).
   - Note: `DisabledAltFireWeapons` on U2PlayerTutorial is an NPC-AI list (`U2PawnAdvanced`: "weapons which NPC
     can't alt fire"), so it does **not** block the player's alt-fire.
2. **The suit.** `CommanderCinTutA.u2s` removes `PowerSuitPhoenix` one second into the map. If the generated map
   keeps that stand-in script, the player fights with no shields.
   - The redesign must give the suit back, as `RaffTutB.u2s` does with `giveitemtoplayer U2.PowerSuitPhoenix`.
   - The cleaner fix is not to run the stock cine scripts on the walk map at all.
3. **RESOLVED 2026-10-08: Hawkins is male (stock voice reused; binder already updated). Old note:** The stock voice is a man; the binder's Hawkins was a woman. The stock Commander lines (`Tutorial_01_003..014`)
   are a male voice, and Dalton calls him "Sir". `binder/citizens/hawkins.md` is **Cmdr. Ruth Hawkins**, 51, and
   the writer makes her the catwalk figure.
   - Reusing the stock cutscene audio means a male Hawkins.
   - New lines "in her voice style" need a voice: Piper female, or VoiceSplice of a bank that does not exist yet.
   - This is open question Q1. Until it is answered, new Hawkins lines below are written for **his character** (Q1 answered: male)
     (dry, straight-faced, short, he warns by understatement) and marked for either voice.
4. **Route order versus the stock flow.** The level designer's route runs dock -> ... -> lift -> command deck ->
   catwalk. The stock flow (and the writer's intro cine) starts in the command room.
   - Recommendation, used below: the opening cine is the writer's 6 shots *without the conversation*. It ends on
     the jetty (F7), and Dalton arrives by the rig shuttle.
   - Hawkins' stock conversation plays when the player reaches him: on the command deck, then he walks out to the
     catwalk, or at the catwalk rail **after** F5 has been seen.
   - The other order is Q2.
5. **Protected frames.** F1 (command window) and F5 (catwalk) get **no combat, no prompts, no hints and no new
   mechanics**. The command deck and catwalk only *use* what the player already knows (use a person, pick a
   number).
6. **The four beats and the reveal stay as approved.** Teaching never changes what the space does at a beat:
   - dock = dread, compression, tower hidden;
   - spine_mid = exposure;
   - company gate = smallness;
   - catwalk = melancholy;
   - the sluice reveal stays the Rrajigar recipe, with its silence. No radio, no PA, no hints in I3.
7. **Engine facts that limit cues:**
   - Ladders are decoration until LadderVolume is confirmed (engineer).
   - The drainage water is a decal plus a sound, never a WaterVolume (level designer).
   - Ledges of 25-70 UU that are "almost climbable" are banned on the route (level designer). Every jump and mantle
     ledge must be clearly one or the other, with a hazard-yellow nosing.
8. **Scope** (memory: the user loves planning more than finishing, so keep scope tiny):
   - The grenade launcher, the deathmatch and the secret range stay in TutB as the optional drill. They are not
     folded into the slice.
   - The slice teaches 15 mechanics (L1-L15).

---

## 3. Teaching rules for this route (from the research, section 9)

Each lesson is checked against these rules:

1. **Need, then tool.** The world creates the need first (HL2 crate stack, Mario's Goomba), then the tool is
   within reach.
2. **Demonstrate, then hand over** (HL2 sawblade, barnacle and crow). Someone else does it first, in view.
3. **Safe first, pressure later** (Episode One, Mario 3D World's introduce-develop-twist-retire). The first use
   can't hurt you; a later fight needs it.
4. **One new thing at a time**; combine only after each has landed (Portal; Dan Cook's skill atoms).
5. **Layer cues until playtesters notice, no more** (HL2 canal gate: sparks, crows, barrels, smoke, light). In our
   grammar:
   - **orange = company door / usable path;**
   - **hazard yellow = edge, hook, moving machine, danger;**
   - **cyan = Authority / screen / info;**
   - **warm bulbs = people** (artist 2.3).

   Nothing else uses those colours, so the colour itself is the cue.
6. **Hint at the problem, not the answer** (Episode One's antlion holes). Hawkins names what's wrong, never the key.
7. **Teach when and why, not just how** (Bycer). Reload is taught by an empty clip in a quiet room, not by a voice.

---

## 4. The fold: each mechanic on the new route

Route and times are from level_designer.md section 1 (Cine8 coordinates, walk at 263 UU/s). Each lesson has an id
L1-L15 used in the implementation (section 7). "T+" is the cumulative walking time from the level designer's table.

### 4.1 Route overview

| stop (LD) | beat / frame | lessons discovered here | pressure tests here |
|---|---|---|---|
| Opening cine | writer's 6 shots, ends at F7 | (A1 title; A2 moved to the end) | - |
| P0 jetty (T+0:00) | **dread**, F7 | L1 HUD and suit, L2 use (object), L3 first weapon, L4 primary fire, L5 objectives | - |
| E1 dock yard (0:03) | dread | L6 pickups from the dead (the AR), L7 AR alt-fire *demonstrated* by an enemy | L4 primary, cover |
| P1 dock gate (0:13) | dread, tower hidden | L8 talk + numbered choices | - |
| Tin Row / I4 mess (0:16) | rest | L9 reload (quiet), L10 stations | - |
| leg 3 works road (0:39) | - | L11 jump (Tin Row ditch, first) | - |
| I2 processing hall (0:55) | fight | L12 crouch (the jammed roller door) | L9 reload, L12 crouch (conveyor), L7 alt-fire |
| E2 dorm square (1:05) | traces | L13 mantle (checkpoint loading dock) | L13 mantle (roof route) |
| I3 drainage (1:10-1:24) | **LD7 quiet, silence** | L11 jump, second time (the culvert gap; isolated, no enemies) | - |
| Sluice gallery (1:30) | **the reveal** | L14 weapon choice vs a new enemy | L7 AR alt-fire / L4 DP charge vs the agile Skaarj |
| E3 basin (1:33) | remix brawl | - | everything; L11 jump down the rim |
| spine climb, F8 (1:51) | **exposure** | (no lesson: let the view work) | - |
| E4 company gate (2:02) | **smallness** | - | L13 mantle or L11 jump on the go-over route |
| I1 lobby hold (2:11) | hold | L15 call the lift | L2/L15 use under fire, L10 stations between waves |
| lift ride (2:39) | relax, survey | - | - |
| command deck (F1) | refuge | (uses L8: Hawkins' stock conversation) | **none** |
| catwalk (F5) | **melancholy** | - | **none** |

Teaching beats add about 60-90 s of walking and fiddling. The slice grows from 9-12 to roughly 10-13.5 min. LD2
(a beat at least every 60 s) still holds, because lessons fill the longest walk (leg 3, 23 s).

### 4.2 Lesson by lesson

Format per lesson:
- **Discover** (where the need appears)
- **Safe first use**
- **Test under pressure**
- **Cue** (diegetic; the colour grammar in brackets)
- **Fallback** (opt-in hint, section 6)

Line ids in `[brackets]` refer to the voice table in section 5.

#### L1: The suit and the HUD (stock B1, B3, B4)
- **Discover.** At P0 the rig shuttle drops Dalton on the jetty and lifts off. The rotor wash and the PA's dock
  notice (pa08) are the only sound. The suit's systems come up **one panel at a time**, as the stock TurnOnHUD +
  FlashDispatcher did:
  - the shield and health bars first, with the stock "WeaponPanelInitiate" UI sound;
  - the ammo block empty, because there is no weapon yet;
  - the weapon tray only later (L3).
- **Safe first use.** Nothing to do. The player just sees each element arrive alone, in a quiet place: the reveal
  *is* the lesson, as in Raff's scan, without the speech.
- **Pressure.** E1, three seconds later: shields drop and recharge (the XA/F "rechargeable shields"). The bar the
  player just saw appear is the bar that moves.
- **Cue.** Hawkins on the suit radio, first contact [H01]: "Dalton. Your suit's on my board. Green across. Try to
  keep it that way."
  - It teaches that the suit has a radio (stock B8) and that "green" matters.
  - It names no screen corner.
- **Fallback.** None needed. This is not a skill.

#### L2: Use, on an object (stock A10, B5, B7)
- **Discover.** The jetty's Authority dock post: a slate hut the company crowded off its own pier. It has one
  **cyan** strip lamp and a locker under it, the only cyan thing on the jetty (cyan = Authority/info). The locker
  hums.
- **Safe first use.** Look at it: the stock use reticle comes up with the description "TCA Locker" (a Trigger with
  `Description=`, as the stock "Elevator"/"Door"). Use it and it opens with the stock pickup sound.
- **Pressure.** L15: the lift call panel in the I1 lobby, under fire. The sluice and lift panels reuse the same
  cyan.
- **Cue.** The lone cyan light, the hum, and the reticle itself.
- **Fallback.** After 25 s on the jetty without opening it, tier 1 [H02]: "There's a station locker on that pier.
  Ours, believe it or not." Tier 2 is the stock text "Use Key = " + binding.

#### L3: The first weapon, from a locker with a story (stock B13, B16)
- **Discover.** Inside the locker:
  - the dispersion pistol (the stock rookie gun, infinite ammo);
  - a paper tag in Nkemelu's hand: *"Pistol's charged. Rifle's been on the requisition list since spring. N."*
    This ties to pa05 ("The Authority supply drop ... has been postponed") and to Nkemelu, who used to hold this
    post before the company took the dock and moved her to the checkpoint.
- **The story.** The law gets the popgun, and the outlaws (E1) carry better rifles. The next weapon comes from
  them (L6).
- **Safe first use.** Taking it slides the stock weapon tray in: TutorialHUD.ui `Tutorial_ShowWeaponTray` +
  `Tutorial_HiliteWeapon1`, reused as is.
- **Pressure.** E1.
- **Cue.** The tag (text on a prop texture, artist's in-world text list) and the tray animation.
- **Fallback.** None needed (L2 covers it).

#### L4: Primary fire, then the DP's charged alt-fire (stock B14, B15)
- **Discover.** The jetty's landward end is a company gate, closed with a **company padlock box** (orange =
  company). There is no other way off the pier: the sea is on three sides.
- **Safe first use.**
  - Primary shots spark on the box and leave scorch decals, but it holds. Each hit plays a "clank" and the box's
    lamp flickers, so the player sees it is *nearly* working.
  - A charged alt-fire shot (the DP "builds up a charge and then releases a bigger blast") blows it open.
  - Primary first, alt second: Portal's "one tool at a time", taught by the failure of the first tool.
- **Pressure.**
  - E1 straight after: primary fire against unaware mercs at 1400-1800 UU, the level designer's "player ambushes"
    foothold, so the first shot is the player's choice.
  - The DP charge again in the sluice (L14).
- **Cue.**
  - Sparks and a clank on primary; the box glows hotter with each hit (a TriggeredTexture / skin swap after 3 hits)
    as feedback that damage accumulates.
  - Hawkins tier 1 [H03] names the problem, not the answer: "Company locks. Better built than our doors."
- **Fallback.** After 30 s and at least 3 primary hits with no alt-fire, tier 2: the stock AlarmTrigger4 text
  "Hold down the alt fire to charge. Release to shoot. Alt Fire = " + binding.
- **Safety net.** After 90 s, the box's own timer "fails" and it opens anyway (a company lock on a timer, with a
  stencil "AUTO-RELEASE 0600-2200"), so nobody is stuck on the pier. This only fires if hints are off.

#### L5: Objectives (stock A9)
- **Discover.** When the padlock gives, the stock objective chime plays (U2AmbientA.UI.NewObjective via an
  ObjectiveEvent): "Report to Commander Hawkins at the tower". This is the only objective text on the whole route,
  and it is the stock UI, not a new prompt.
- **Safe first use.** The objective line shows on screen as in stock.
- **Pressure.** None. Objectives update at E4 ("Get to the tower lift") and on the command deck. The stock
  "(Press F4 to list current objectives)" suffix only appears as a tier 2 hint.
- **Cue.** The chime and the tower's red aviation light. The tower stays *hidden* at the dock (dread beat), so the
  objective names a place the player cannot yet see. That serves "dread"; it does not fight it.

#### L6: Pickups from the dead: the assault rifle and ammo (stock B17, B24 "load up on ammo")
- **Discover.** At E1, Rook's smugglers drop their rifles on death. The stock `DiscardInventory` already does this
  in U2.
- **Safe first use.** After the yard is clear, walk over a dropped rifle. The weapon tray adds slot 2 with the
  stock HiliteWeapon2 flash; ammo pickups from the other bodies top it up.
- **Pressure.**
  - I2, where the AR's volume of fire is needed against six mercs.
  - E3, where ammo runs low in a long brawl, and the dead mercs in the basin are the resupply.
- **Cue.** Nkemelu's tag already set it up ("Rifle's been on the requisition list"). The rifles lie in the open on
  the lit quay apron, and a dropped weapon reads as a weapon.
- **Fallback.** After 40 s clear of E1 without picking up a rifle, tier 1 from a dockhand behind the shed [D01]:
  "Rook's lot won't be needing those." No tier 2: it is optional, and I2 has rifles too.

#### L7: AR alt-fire: the ricochet bolt (stock B19)
- **Demonstrate.** In E1 the Medium merc arrives by boat at 10 s (the level designer's visible reinforcement). His
  first shot is an **alt-fire bolt that ricochets** off a container wall beside the player. The player sees the
  mechanic used on them before they own it (HL2's sawblade logic).
  - This needs a scripted single alt-fire from that NPC: the AI does alt-fire the AR (it is not in the NPC
    `DisabledAltFireWeapons` list), but its timing is not ours, so the director forces one.
- **Safe first use.** Any time after L6. The quiet Tin Row lane and the works road (leg 3) have hard concrete walls
  and tin signs that ring when hit. An empty company sign on the works road is an obvious target, half-hidden
  behind a corner: a bolt bounced off the wall knocks it down.
  - This is optional. It is a toy, not a gate.
- **Pressure.** The sluice gallery's agile Skaarj (L14): the bolt's five shards spread on impact and bounce in the
  768-wide gallery, so a dodging Skaarj is hit by the spread off the alcove walls. I2's presses make the same
  corners.
- **Cue.** The demonstration; the ringing sign.
- **Fallback.** Tier 2 only, and only in the sluice: after the player has been hit twice by the Skaarj, the stock
  AR alt line text. (The sluice itself stays silent, so no voice there.)

#### L8: Talk, and pick a number (stock A6, A7, B6)
- **Discover.** P1, the dock gate (dread, tower hidden behind the quay silos). The gate into town is a company
  turnstile with a **clerk's hatch**, lit warm and orange-framed (company door). The clerk is the "escort required"
  voice of pa04 in person.
- **Safe first use.** Use the clerk (the stock use reticle on a person) and a dlg opens with three numbered
  choices, all of which open the turnstile, as Raff's "pick a number" did [C01-C05]:
  - 1. "Authority business." -> clerk: "Everything's Authority business today. Docking fee's on the pad." Opens.
  - 2. "I'm here to see Commander Hawkins." -> clerk: "Up the hill, round the company, try not to touch anything." Opens.
  - 3. "Who were those men on the quay?" -> clerk: "What men?" Opens.

  It sells the three-powers story in four lines.
- **Pressure.** None for dialogue. It is used again, without help, on the command deck, where Hawkins' stock menu
  (A7) is the payoff.
- **Cue.** The warm hatch light, the clerk tapping the glass (the stock `Event_A_ButtonPress`-style agentcall), the
  turnstile's red lamp.
- **Fallback.** Tier 1 after 20 s: the clerk raps on the glass and calls [C00] "You. Marshal. Over here."
  Tier 2: "Use Key = ".
- **Optional, same lesson:** in the mess (I4), Marau and Ilunga can be talked to (A6's "people answer when used").
  The Kai babble trick (A6) becomes a deckhand who answers in Ship Row slang.

#### L9: Reload (stock B18: "find a quiet moment to reload before combat")
- **Discover.**
  - After E1 the AR clip is partly spent.
  - The I4 mess (optional refuge) or the Tin Row lane are quiet.
  - The lesson is the *why*: "reload in a quiet moment". So it is taught where it is quiet, after a fight, by the
    HUD clip number the player met in L1.
- **Safe first use.** Reload in the mess or the lane.
- **Pressure.** I2: four Lights, a Medium on the gantry and a Heavy at the end. A long fight where the clip *will*
  run out. The presses at 1200 and 2600 UU are the places to reload behind.
- **Cue.**
  - The empty-clip click (the weapon's own sound) and the HUD clip counter.
  - A mess wall board "DAYS SINCE LAST INCIDENT: 0" with a hand-written line under it: "COUNT YOUR ROUNDS - V."
    (Vask, the sergeant). It is the misery board the level designer asked for, doing a job.
- **Fallback.** Tier 1, the first time the clip hits 0 *outside* combat [H04]: "Count your rounds before you open
  a door." Tier 2: the stock AlarmTrigger3 "Reload Key = ".

#### L10: Health and energy stations (stock B26)
- **Discover.** The mess counter (I4) has a HealthStation set into the serving line: the "health on the counter"
  the level designer put there. An EnergyStation is by the door.
- **Safe first use.** After E1, walking past the counter, "Just step inside" happens by itself: the stock station
  sounds (U2A.Stations.*Activate/Ambient) are the cue. A Liandri plaque reads "MEDICAL - EMPLOYEES ONLY", with
  "employees" scratched out (who uses the room).
- **Pressure.** The I1 lobby hold: one health and one energy station in the lobby, reachable between the two waves
  (3 + 2 Skaarj), and in the sluice reward alcoves (the Rrajigar supply alcoves).
- **Cue.** The stations' own glow and hum; warm bulbs = people.
- **Fallback.** None. It is optional at the mess, and the hold places them on the obvious route.

#### L11: Jump (stock B9; the user's example "jump across a gap in the drainage")
- **Discover, first.** Leg 3 of the works road passes Tin Row's lower edge, where an **open storm ditch** (2.5 m
  wide, 60 UU deep, dry) crosses the path. The duckboard bridge is broken: one half lies in the ditch.
  - Shanty kids' chalk marks on the far side show where people jump: a **demonstrate** cue that needs no actor.
  - A Tin Row local jumping it on his walk route (walks.py routine) is the stronger demonstration, if NPC jumping
    proves reliable (Q6).
- **Safe first use.** Jump the ditch. Failing costs nothing: the ditch is shallow, has a ramp out at both ends, and
  you walk back.
- **Second use, isolated** (I3 drainage, the quiet stretch).
  - The culvert has one **collapsed section of the dry ledge**: a 160-192 UU gap over a deeper channel (still a
    decal plus sound, no WaterVolume).
  - Wet footprints that are not yours (the writer's foreshadow) run up to the edge and **continue on the far side**:
    someone jumped it. The footprints are the lesson.
  - A miss drops the player into the channel. It is ankle-deep, with a walk-back of about 6 s along the channel to
    a ramp. The quiet stretch stays quiet; nothing can hurt the player there.
- **Pressure.** E3: the fastest way off the rim into the basin bowl is a jump down a broken section. E4's go-over
  route jumps a gap in the terrace parapet while the Lights leap between terraces.
- **Cue.** The broken duckboard and the chalk marks; the culvert footprints; hazard-yellow paint on both lips of
  each gap (hazard yellow = edge).
- **Fallback.**
  - Ditch: tier 2 after 25 s at the edge, "Jump Key = ".
  - Culvert: **no voice** (silence rule). Tier 2 text only, after 40 s.

#### L12: Crouch (stock B11; the user's example "crouch under a conveyor in the processing hall")
- **Discover.** I2's roller door is **jammed half up**, as the writer's hall_c door is, here on hall_a.
  - The gap is 96-110 UU high: too low to walk under, plenty to crouch under.
  - Warm light and conveyor noise spill out under it; the hall is visibly busy beyond.
  - A stencil on the door's hazard-yellow bottom edge reads "MIND YOUR HEAD" (artist's in-world text), and a
    PA line plays [pa16].
- **Safe first use.** Crouch under the door into the dark vestibule (the level designer's compression beat). The
  mercs inside are not yet aware: the fight starts when the player steps out of the vestibule. That is the
  "Don't worry. I won't let 'em drop any further" of stock B11, made into a place.
- **Pressure.** Inside I2:
  - the conveyor runs at 1.2 m on stands; crouching under it is the fast way across aisles, and the cover from the
    gantry Medium;
  - the side aisles' crossings under the press feeds are crouch-height;
  - the level designer's loops make crouch-under the shortcut that lets the player circle.
- **Cue.** The light spill, the stencil, the PA, hazard yellow on every low edge (the conveyor frame's underside
  gets a yellow band).
- **Fallback.** After 20 s at the door, tier 1, PA again (it repeats like a PA). Tier 2: "Crouch Key = ".
  - There is no side door at the start (the level designer's side door enters mid-hall), so the lesson gates entry.
  - The LD's "side door" stays the flank route, opened from inside.

#### L13: Mantle (stock B10: "jump straight up, and don't stop")
- **Discover.** E2, the dorm square, approached from the hall exit lane.
  - The direct way into the square is over the checkpoint's **loading dock**: a concrete platform at mantle height,
    with a hazard-yellow nosing. Its stair end is blocked by the company barricade.
  - Before the fight starts, a sandbag line and laundry carts make "over the dock" the obvious line.
  - The ledge height must be measured: U2's mantle reach is not in our notes (Q5). Target "clearly above
    MaxStepHeight 37 and clearly mantleable", probably 80-120 UU.
- **Safe first use.**
  - The guards face away from the player, toward the drainage (the level designer's setup), so the first mantle is
    done unseen.
  - A second, safer chance sits in the mess's kitchen yard (optional): a low wall to the bins.
- **Pressure.**
  - E2's "small fallback": the Heavy holds the checkpoint roof, and the player's flank onto the roof is a
    mantle from a stacked crate.
  - E4: the go-over route up the terraces includes one mantle onto a broken terrace section while the Berserker
    charges down the stair.
- **Cue.** Hazard-yellow nosing on every mantle ledge (and only on mantle ledges and gaps: one meaning per colour);
  a scuffed boot-mark decal on the face.
- **Fallback.** After 25 s pressed against the ledge, tier 2: the stock AlarmTrigger8 text "Jump and hold down the
  jump button to mantle." (it names the button but is one line; no voice).

#### L14: A new enemy and the right weapon (the reveal: no lesson voice, no change to the recipe)
- The sluice gallery stays the level designer's section 4, step by step:
  - corpses and traces;
  - the grate drops behind the player;
  - the lamps die from the far end;
  - the red beacon;
  - the silhouette;
  - one agile U2SkaarjLight;
  - the supply alcoves.
- **What it tests.** Everything the player now owns, against a creature that **dodges hitscan**. The fight teaches
  (the encounter memory's "fight that teaches"):
  - plain AR primary fire is weak against its dodge;
  - the **AR ricochet bolt** (L7) off the alcove walls and the **DP charge** (L4) on the landing after a leap both
    work.
  - This is the user's example: alt-fire against the agile Skaarj.
- **Cue.** Only the space: the alcoves are half cover that stops its leap line and makes ricochet angles. No radio.
- **Reward.** The alcoves hold AR ammo, a health pack and an energy pack.
  - Optional: the **grenade launcher**, if the user wants it in the slice (Q7). Its first pressure use would be the
    E3 brawl, where the basin is a bowl that timed grenades roll down into.

#### L15: Call the lift (stock A11; the user's example "use the lift call button in the tower lobby")
- **Discover.** I1 base lobby. The freight lift cage has a **cyan** call panel (Authority = info): the only lit
  cyan in the lobby, the same cyan as the jetty locker (L2).
- **Safe first use.** None, on purpose: this is L2's pressure test. The player already knows "cyan thing, use it".
- **Pressure.** Using it starts the 20 s call: the motor whine climbs, and the cage counter (stock `BigLiftBeep`
  SpecialEvent) ticks. The two Skaarj waves come through the service door and the vent. The hold is "use it, then
  survive until it arrives".
- **Cue.** The cyan panel, then Hawkins [H05] when it is pressed: "Lift's slow. It was slow before they cut our
  power." This is the level designer's "one Hawkins line when the lift arrives", moved to the press so it explains
  the wait. On arrival [H06]: "Come up, Dalton."
- **Fallback.** After 30 s in the lobby without pressing, tier 1 [H07]: "The lift won't come to you on its own,
  Marshal." Tier 2: "Use Key = ".

### 4.3 The stock mechanics that are deliberately left in TutB (the optional drill)

These stay as they are, reached from the end conversation (A7's "training run" choice -> TutB):
- B2-B7 (Raff's scan and HUD tour, already covered by L1/L2/L8 on the route);
- B12 (the timed hard course);
- B20-B22 (grenade launcher and the secret range);
- B24 (the deathmatch and its scoreboard);
- B25 (holo-corpse).

Nothing in TutB needs changing. It is the "teach by drill" alternative for players who want it, and it costs
nothing.

### 4.4 The ending: the stock conversation where it belongs

- **Command deck (F1, refuge).** Hawkins is not at the window: his binoculars are on the sill, and his coffee tin is
  gone from the desk. Oduya says [O01]: "He's on the catwalk. He'll want you out there."
  - The deck itself has no prompt, no fight and no new mechanic. The player just looks out of the window (the
    director's hero frame).
- **Catwalk (F5, melancholy).** The frame first, untouched: the dark slab, the grating, the rain, Hawkins as the lone
  figure at the rail 40-100 m out.
  - When the player is within talk range, use him (L8 again, no help).
  - The **stock** conversation plays: `CommanderTutACutscene1 .. 9` (reinstatement denied, Drexler, Ne'Ban, "the
    quietest patrol", "Stow it, Dalton"), then the **stock** choice `CommanderTutAWelcome` (Tutorial / Return to
    ship).
  - The two ExitEvents keep their stock jobs: training -> TutB, ship -> the Atlantis.
  - If Hawkins is female (Q1), these nodes need re-voicing (section 5).
- The dialogue never starts by itself, so the frame is the player's to hold for as long as they want.

---

## 5. Voice: what is reused, what is new

### 5.1 Reused as is (stock files; nothing in the game's own folders is edited)

| use | stock asset | where |
|---|---|---|
| Hawkins' conversation at the catwalk | dlg `CommanderTutACutscene1..9`, `CommanderTutAWelcome` (+a/b, 1/2); `Tutorial_A.Tutorial_01.Tutorial_01_003Split1 .. 014` | 4.4 (only if Hawkins keeps the stock male voice; see Q1) |
| Dalton's replies in that conversation | `Tutorial_01_002, 004, 006, 008, 010b, 998, 999` | 4.4 |
| A marine's salute at the tower lobby door | dlg `Marine01TutASalute` (MM_Marsh_A.Marsh_02.Marsh_02_002) + `Event_A_Attention` | I1 entry |
| Weapon tray animation | TutorialHUD.ui `Tutorial_ShowWeaponTray`, `Tutorial_HiliteWeapon1/2` | L3, L6 |
| Pickup, objective and station sounds | U2WeaponsA.Dispersion.DP_Pickup; U2AmbientA.UI.NewObjective; U2A.Stations.* | L3, L5, L10 |
| Fallback key texts | AlarmTrigger messages from TutB.int: "Use Key = ", "Jump Key = ", "Crouch Key = ", "Reload Key = ", "Hold down the alt fire to charge. Release to shoot. Alt Fire = ", "Jump and hold down the jump button to mantle.", TutA.int "(Press F4 to list current objectives)" | section 6, tier 2 |
| Lift beep and shake | SpecialEvent `BigLiftBeep`, EarthquakeTrigger `BigLiftShake` (as in BigLiftDispatcher) | L15, the lift ride |
| The whole TutB course and Raff's 54 lines | unchanged | 4.3 |

The stock AI-script verbs used for the new NPCs (clerk, Oduya, Hawkins at the rail, the lobby marine) are the
same ones TutA/TutB use:
- `dialogenable` / `dialoginitiate`;
- `testactorinrange Player N`;
- `agentcall Event_A_ButtonPress` / `Event_A_Attention`;
- `turntoactor`, `gotoactor`, `sendevent`, `ontrigger`;
- `giveitemtoplayer U2.PowerSuitPhoenix`.

### 5.2 New lines

Voices are from `binder/radio_lines.md` and `pa_lines.md` unless marked.
- **Piper** = `tools/pa_voice.py` (piper-tts-setup).
- **VS** = VoiceSplice `voicesplice.py say <bank> "..."`, in hybrid mode: it keeps words the character really said
  and converts the new ones with Piper + kNN-VC.

There is **no Commander or Raff bank yet**. Building one takes about 45 min of CPU (`voicesplice.py build u2
Commander`), plus `matchset`.

| id | speaker | line | voice route |
|---|---|---|---|
| H01 | Hawkins (suit radio) | "Dalton. Your suit's on my board. Green across. Try to keep it that way." | Q1: **VS Commander bank** (male, stock-consistent; "Dalton" and "board" exist in his lines) **or Piper female** (needs a new voice download, approval first) |
| H02 | Hawkins | "There's a station locker on that pier. Ours, believe it or not." | same |
| H03 | Hawkins | "Company locks. Better built than our doors." | same |
| H04 | Hawkins | "Count your rounds before you open a door." | same |
| H05 | Hawkins | "Lift's slow. It was slow before they cut our power." | same |
| H06 | Hawkins | "Come up, Dalton." | same (VS can splice it almost whole from "Dalton" + stock words) |
| H07 | Hawkins | "The lift won't come to you on its own, Marshal." | same |
| C00 | gate clerk | "You. Marshal. Over here." | Piper en_US-john-medium (the company radio voice: one company, one voice family) |
| C01 | clerk | "Everything's Authority business today. Docking fee's on the pad." | Piper john |
| C02 | clerk | "Up the hill, round the company, try not to touch anything." | Piper john |
| C03 | clerk | "What men?" | Piper john |
| C04-C05 | Dalton's 3 choices | text only, as ShortText/LongText (the user's rule: the protagonist stays silent in new content; stock Dalton lines stay voiced) | none |
| D01 | dockhand | "Rook's lot won't be needing those." | Piper en_GB-northern_english_male-medium (the dock voice in r08) |
| O01 | Oduya | "He's on the catwalk. He'll want you out there." | Piper (Oduya has no voice yet; pick one voice for her and keep it: Q8) |
| pa16 | Liandri PA | "Hall A roller door is jammed at half height. Personnel will mind their heads. Production continues." | Piper en_US-amy-medium (the PA voice) |
| pa17 | Liandri PA | "The Authority lift is on the reduced supply schedule. Thank you for your patience." | Piper amy (plays in the lobby before the hold: sets up the 20 s wait) |

**What the lines must not do:**
- None of them name a key, a mouse button or a screen corner.
- The stock AlarmTrigger texts are the only place keys are named, and only in tier 2.
- No line plays in I3 or the sluice: silence is the build-up (level designer, writer).
- None plays on the command deck or the catwalk except O01 and the stock conversation the player starts.

**Hawkins' voice style for H01-H07.** He is 51, 26 years in the Authority, says "the quietest patrol" "with a
straight face. He means it as a warning." So:
- short sentences;
- no exclamation marks;
- understatement;
- he names the problem, never the solution;
- he is never chatty: at most one line per lesson, and only H01, H05 and H06 play unconditionally. The rest are
  tier 1 hints.

---

## 6. The opt-in fallback: hints after being stuck

Principle: the world gets the first try (tier 0, always on). Words come only if the player opts in.

| tier | when | what | limits |
|---|---|---|---|
| 0 world | always | the cue gets louder: the cyan lamp pulses, the PA repeats, the clerk raps the glass, the padlock box glows hotter | no text, no voice beyond the diegetic sound |
| 1 voice | opt-in, stuck >= N1 | one in-world line (H02, H03, H04, H07, C00, D01, pa16 again) that names the problem | once per lesson; never in I3/the sluice, F1 or F5 |
| 2 key | opt-in, stuck >= N2 | the stock AlarmTrigger text + the player's real binding (`KeyBinding`), one line, 4 s, the stock message area | once per lesson, then again only after another N2 |

- **"Stuck"** = the lesson's goal is not met while the player is inside the lesson's radius, and the player has
  not made progress along the route. Progress is distance-to-goal shrinking by more than 256 UU in the window.
- **N per lesson.** Movement lessons (L11-L13): N1 = 20 s, N2 = 25-40 s. Use/talk (L2, L8, L15): N1 = 20-30 s,
  N2 = 30-45 s. Combat (L7 in the sluice): after the player has been hit 2 times.
- Timers stop while a dialogue or cutscene is running, and while enemies are aware of the player, except L7 and
  L15, whose stuck state *is* under fire.
- **Opt-in.** `[U2AvalonCards.AvalonTutor] Hints=0|1|2` (0 = world only; 1 = + voice; 2 = + keys). The console
  `avalon hints 0|1|2` sets it. The default is Q3; this doc recommends **1**: voice hints are in-fiction, and keys
  are opt-in.
- **No text walls:** each hint is one line of at most 12 words, shown for at most 4 s, from the stock message slot.
  There are no new UI panels.
- **Safety nets** so nobody can be hard-stuck with hints at 0:
  - the padlock's auto-release (L4, 90 s);
  - the dock-gate clerk opening the turnstile after 60 s (L8: "Go on, then.");
  - the roller door's chain slipping 20 UU higher after 60 s (L12; it becomes walk-under-able crouched or
    not, and the conveyor lesson inside still teaches crouch);
  - the culvert channel's ramp (L11 can't block: a miss just walks back);
  - the mantle ledge's stair end: the barricade has a gap you can squeeze through after 60 s (L13 becomes
    optional).
- **The drill alternative:** the end conversation's stock "training run" choice (TutB) for anyone who wants Raff's
  explicit course.

---

## 7. Implementation sketch in U2's terms

### 7.1 Where it lives

- **Mutator:** U2AvalonCards' `AvalonCards` (already in the user's Mutator line). It spawns a new
  **`AvalonTutor`** (Info, `config(U2AvalonCards)`) on maps listed in `TutorMaps=` (e.g. `tuta,tuta_town7`), as it
  spawns AvalonPA/AvalonRadio/AvalonStorm.
- **Director pattern:** `AvalonTutor` copies the `OpenDirector` / `SanctuaryDirector` shape:
  - config rows staged a moment after map start (Timer 0.5 s, then 1 s);
  - logging with `bLog`;
  - optional hand-over to the GM (`bProposeOnly`) for placing cues by hand.
- **Map-side actors** come from the generator (`make_avalon.py` / `export_mutator.py`, T3D import), because
  triggers, movers and stations belong in the map:
  - `Trigger` with `Description=` for every use target (locker "TCA Locker", clerk hatch, lift panel "Freight Lift");
  - `Mover`s: the padlocked jetty gate, the dock turnstile, the jammed roller door (two keyframes: jammed, slipped),
    the culvert grate (one-way, the reveal's "commit"), the sluice gate, the freight lift (+ `LiftCenter` /
    `LiftExit` at both stops, level designer section 5);
  - `ObjectiveEvent`s (L5, the E4 update, the deck);
  - `AlarmTrigger`s, tier 2 only: AlarmMessage copied from TutB.int, `KeyBinding` set, `bInitiallyOn=false`,
    `MessageTime=4`. AvalonTutor triggers them by Tag; nothing else does;
  - `HealthStation` / `EnergyStation` (mess, I1 lobby);
  - `SpecialEvent`s for sounds (BigLiftBeep reuse) and `U2Dispatcher`s for sequences;
  - `AvalonLamp`s (L2/L15 cyan, the reveal lamps 1-6);
  - weapon pickups: the dispersion pistol is a scripted `giveitemtoplayer` from the locker, as `RaffShootingRangeTutB`
    does; the ARs come from the mercs' own drops.
- **NPC scripts (.u2s)** for the clerk, Oduya, the lobby marine and Hawkins at the rail. Put them in a mod
  Scripts\ folder and assign them with `ObjectivesTrigger` (bIgnoreDistance) or the director's spawn. They use only
  the verbs in 5.1.
- **Dialogue:** a new `AvalonTutA.dlg` (clerk C00-C03, O01, Hawkins H-nodes if they are conversations) plus the stock
  `CommanderTutA.dlg`, loaded the way OpenDirector loads `DialogDirs` and starts topics with
  `DialogEngine.Initiate`. No stock .dlg is edited.
- **Game type and suit** (section 2): the generated map's LevelInfo gets the campaign's single-player game type in
  the uedlib build step, **or** AvalonTutor:
  - sets `Level.Game.bDisplayHud=true` at L1 time (the HUD-boot moment);
  - gives `U2.PowerSuitPhoenix`;
  - and the walk map does not carry `CommanderCinTutA.u2s` / `CommanderTutA.u2s` (their door-lock and suit-removal
    side effects).

  The stock TutA stays untouched for the command-room-only campaign path.

### 7.2 Config rows (sketch)

```
[U2AvalonCards.AvalonTutor]
Hints=1
bLog=False
; Lesson: Id, Map, At, Radius, Goal, After, Cue (actor tag to "pulse"), Hint1 (sound), Hint2 (AlarmTrigger tag), N1, N2, Net (safety-net event), NetTime
Lessons=(Id="L2use",Map="TUTA_TOWN7",At=(X=6026,Y=-5339,Z=..),Radius=1200,Goal="event:TutLockerOpened",After="",Cue="TutLockerLamp",Hint1="H02",Hint2="TutUseKey",N1=25,N2=40,Net="",NetTime=0)
Lessons=(Id="L4alt",...,Goal="event:TutPadlockBroken",After="L3gun",Cue="TutPadlockBox",Hint1="H03",Hint2="TutAltKey",N1=30,N2=45,Net="TutPadlockAutoRelease",NetTime=90)
Lessons=(Id="L12crouch",...,Goal="crouch-under:TutRollerDoor",After="",Cue="PA16",Hint1="PA16",Hint2="TutCrouchKey",N1=20,N2=30,Net="TutRollerSlip",NetTime=60)
...
QuietZones=(Name="I3",...),(Name="F1deck",...),(Name="F5catwalk",...)   ; no hint voice, no combat spawns
```

### 7.3 How a lesson's goal is detected (all from script, polled in Timer at 0.25 s)

| goal kind | detection | precedent |
|---|---|---|
| `event:X` | a trigger/mover/dlg ExitEvent fires X (AvalonTutor listens with its Tag) | every stock tutorial step (PlayerTookDP, DPPrimaryFired, ...) |
| primary / alt fire | `Weapon.bFiring` / alt state plus the ammo drop (`GetAmmoAmount()`), as FairFights' view kick | U2FairFights KickFor() |
| reload | the clip count rises while reserve falls (or the weapon's reload state) | - |
| crouch-under | `Pawn.bIsCrouched` while inside a small volume (an `AvalonTutorZone` actor: radius/height) under the door or conveyor | - |
| jump / mantle | Physics == PHYS_Falling then landing at Z >= ledge top inside the far-side zone (mantle = landing on the ledge zone) | - |
| use | the use Trigger's Event | stock A10/B7 |
| talk | dlg ExitEvent | stock A7 |
| picked up | inventory scan (`FindInventoryType`) | RaffDMTutB `removeinventoryfromplayer` list |

Every lesson logs `AvalonTutor: <Id> discovered|first-use|pressure-use|hint1|hint2|net t=<s>` so the pilot can
grade it.

### 7.4 What the U2Pilot harness should check (tools/python/U2Pilot; background mode)

Scripts to write, but **not to run now**:
- `tutor_lessons.txt`;
- `tutor_hints.txt`;
- `tutor_route_autoplay.txt`;
- `tutor_quiet.txt`.

| # | check | how | pass |
|---|---|---|---|
| P1 | each lesson's goal can be met by the documented input | for L2-L15: `console hub tp` to just before the lesson; perform it (`crouch 1` + `move 1 0 2`; `jump`; `altfire 1.2`; `console use`); grep the `AvalonTutor: Lx first-use` log | 15/15 |
| P2 | hints fire in order and only when opted in | the same spots, then `wait N2+5` with `ini U2AvalonCards.AvalonTutor Hints=0`, `=1` and `=2` | Hints=0: no hint1/hint2 lines, only `net` after NetTime; =1: hint1 only; =2: hint1 then hint2 |
| P3 | safety nets free a stuck player | Hints=0, idle at L4, L8, L12, L13 for NetTime+5 | a `net` line, and the mover is open (`dump Mover Location`) |
| P4 | protected frames stay clean | `dump U2Pawn` (hostile classes) within 3000 UU of the F1 and F5 cameras during the whole run; grep for no `hint` lines and no AlarmTrigger messages while in QuietZones | 0 hostiles, 0 hints in F1/F5/I3 |
| P5 | the beats and reveal fire in the approved order | `console hub beats` / beatgraph.py on the walk map; AvalonTutor's log order versus the level designer's table (E1 < gate < I2 < E2 < I3 < reveal < E3 < E4 < I1 < deck < catwalk) | order matches; the reveal steps 3-7 in sequence |
| P6 | the HUD and suit are on before E1 | `shot` at P0 + 5 s; `inv` lists PowerSuitPhoenix; `dump GameInfo bDisplayHud` | HUD visible, suit present |
| P7 | the mantle and jump geometry is honest | `jump` / `move` into each L11/L13 ledge and gap; measure success over 5 tries, and with `crouch 1` under L12's door; also a "too high" control ledge | 5/5 at the lesson ledges; the control fails (proves the ledge is in band) |
| P8 | the forced ricochet demo happens | E1: log the scripted alt-fire of the Medium merc (`AvalonTutor: L7 demo`) within 15 s of his arrival | logged, no player damage required |
| P9 | the whole route is walkable by AI | U2AutoPlay `autoplay on` from P0 (`god`), heatmap.py: STUCK/FELL events at lesson spots | no STUCK at L4/L8/L11-L15 that the safety net does not clear |
| P10 | lines never overlap | log start and end of every H/C/O/pa line (SevenRadio-style actor); check that no two overlap and none plays in I3 | 0 overlaps |
| P11 | regression | triage.py against a new baseline for the walk map | no new script error buckets |

Notes:
- **Pre-authorized pilot runs.** Memory says U2Pilot runs are pre-authorized: announce them, F12 aborts. They still
  wait for the GPU being free (the playtest swap).
- **The pilot can't judge "discovered without help".** That needs a human first-play. The playtest note to the
  user: play with `Hints=0` once, and mark (with `avalon mark`) every spot where you stopped for more than 10 s.
  Those marks are the real data. The HL2 lesson is to layer cues until testers notice.

---

## 8. Open questions for the user

1. **Hawkins' voice. ANSWERED (user 2026-10-08): (a), male.** Rule: remade characters keep the stock
   character's gender, so the stock voice can be reused (spliced, never AI). Hawkins is male; new lines are
   VoiceSplice from the Commander bank. Original question kept below.
   **Hawkins' voice.** The stock Commander is a man ("Sir", male voice), and the binder made her Ruth Hawkins.
   Options:
   - (a) keep the stock male voice and drop "Ruth": VoiceSplice from a Commander bank, about 45 min CPU, no
     download;
   - (b) keep her female: the stock conversation would need re-voicing, and new lines need a Piper female voice
     (a download that needs your OK; lessac is installed but is Aida's voice in The Seven);
   - (c) female Hawkins only in new content, and the stock conversation moved to a male officer (Vask?).
2. **Order.** Opening cine without the talk, then the walk dock -> tower, then the stock conversation at the catwalk
   (this doc)? Or the writer's order: the talk in the opening cine, then Dalton sent down to the dock to walk back
   up?
3. **Hint default.** `Hints=1` (voice hints on, key prompts opt-in) as recommended, or `0` (world cues only) for the
   purest discovery?
4. **The padlock and the turnstile.** Are two "gates" in the first 15 s too much friction at the dread beat, or do
   they add to it (nobody wants you here)?
5. **Mantle height.** OK to measure U2's real mantle reach with a pilot probe when the GPU is free? Every L13 ledge
   depends on it.
6. **NPC demonstrations.** Should a Tin Row local jump the ditch and a hand crouch under the roller door (stronger
   teaching, but U2 NPC jumping and crouching is untested)? Or rely on chalk marks, footprints and stencils?
7. **Grenade launcher.** Keep it in TutB only (this doc) or give it as the sluice-alcove reward, with its first use
   in E3?
8. **Oduya's voice**, and whether the deck needs her at all, or Hawkins' empty window is enough.
9. **TutB.** Leave it fully stock as the optional drill (this doc)? Or eventually re-skin Raff's course as the
   tower's basement in the new art?

---

## 9. References (web; read only, nothing downloaded, none of it ships)

Unless a licence is named, treat each one as copyright, reference only.

| # | source | URL | author / publisher | licence | used for |
|---|---|---|---|---|---|
| 1 | Half-Life 2 developer commentary (transcript) | https://combineoverwiki.net/wiki/Developer_commentary/Half-Life_2 | Valve devs (Finol, Brown, Riller, Speyrer, Sawyer), transcribed by Combine OverWiki | Valve ©; the wiki's own licence page was not reachable | gate behind the skill (crate stack), "pick up that can", layered hints until testers notice (canal gate), the bugbait training (L4 padlock, section 6 tier 0) |
| 2 | HL2: Episode One commentary | https://combineoverwiki.net/wiki/Developer_commentary/Half-Life_2:_Episode_One | Valve (Scott Dalton, Finol, Wood), 2006 | © Valve | example, confirm, change; new monsters seen safe first; hint the problem, not the answer (H-lines) |
| 3 | HL2: Episode Two commentary | https://combineoverwiki.net/wiki/Developer_commentary/Half-Life_2:_Episode_Two | Valve, 2007 | © Valve | sawblade demonstration; locked arena that opens on the kill (the sluice's commit) |
| 4 | Portal developer commentary | https://combineoverwiki.net/wiki/Developer_commentary/Portal (also https://theportalwiki.com/wiki/Portal_developer_commentary) | Valve (Kim Swift, Robin Walker et al.), 2007 | © Valve | one tool at a time; isolate hard combinations; re-teach; final hint-free test (the sluice) |
| 5 | "Best Of GDC: The Secrets Of Portal's Huge Success" | https://www.gamedeveloper.com/pc/best-of-gdc-the-secrets-of-i-portal-i-s-huge-success | Mathew Kumar, Game Developer, 2008 (Swift and Wolpaw, GDC 2008) | © publisher | watch players; simplify visuals (one meaning per colour) |
| 6 | Miyamoto on World 1-1 | https://www.youtube.com/watch?v=zRGRJRUWafY | Eurogamer, 2015 (Miyamoto, Tezuka) | © Eurogamer | the first enemy is the simplest; a placement that forces contact (the jetty: no way off but the gate) |
| 7 | Sequelitis: Mega Man Classic vs. Mega Man X | https://www.youtube.com/watch?v=8FpigqfcvlM | Arin Hanson (Egoraptor), 2011 | © author | teach by situation, not text; demonstration (the E1 ricochet) |
| 8 | Half-Life 2's Invisible Tutorial | https://www.youtube.com/watch?v=MMggqenxuZc | Mark Brown, Game Maker's Toolkit, 2015 | © author | demonstrate, then hand over the tool, in about 10 s; against repeated text prompts |
| 9 | Super Mario 3D World's 4 Step Level Design | https://www.youtube.com/watch?v=dBmIkEvEBtA | Mark Brown, GMTK, 2015 | © author | introduce, develop, twist, retire (each lesson's three moments) |
| 10 | The Chemistry of Game Design | https://www.gamedeveloper.com/design/the-chemistry-of-game-design (orig. https://lostgarden.com/2007/07/19/the-chemistry-of-game-design/) | Daniel Cook, 2007 | © author | skill atoms and chains; room to repeat |
| 11 | Methods of Creating Invisible Tutorials | https://www.gamedeveloper.com/design/methods-of-creating-invisible-tutorials | Alex Pine, Game Developer blog, 2019 | © publisher | affordances by colour/sound/shape; skill gates; demonstration at a safe distance |
| 12 | Teaching Game Mechanics: A Hierarchy of Learning | https://www.gamedeveloper.com/design/teaching-game-mechanics-a-hierarchy-of-learning | Josh Bycer, 2016 | © publisher | teach what, how, **when and why** (L9 reload in a quiet room) |
| 13 | Inside: Teaching through Level Design | https://www.gamedeveloper.com/design/inside-teaching-through-level-design | Joey Simas, 2016 | © publisher | contrast colour and motion mark the one usable object; tension and relief between lessons |
| 14 | Tutorial (video games) | https://en.wikipedia.org/wiki/Tutorial_(video_games) | Wikipedia | CC BY-SA 4.0 | explicit vs implicit tutorials; HL1's opening as a "tutorial in disguise" vs its separate Hazard Course |
| 15 | Embracing Push Forward Combat in DOOM | https://gdcvault.com/play/1024940/Embracing-Push-Forward-Combat-in | Kurt Loudy, Jake Campbell (id), GDC 2018 | © GDC/id | teach by need (pickups from kills: L6) |
| 16 | Titanfall 2's Gauntlet | https://aftermath.site/vholume-game-titanfall-2s-gauntlet-indie-parkour/ | Chris Person, Aftermath, 2026 | © publisher | the drill as optional mastery (TutB kept as the drill) |
| 17 | Level Design in a Day: The Last of Us | https://gdcvault.com/play/1020174/Level-Design-in-a-Day | Elisabetta Silli (Naughty Dog), GDC 2014 (abstract only) | © GDC | the first human fight as the simplest arena; a guide NPC who leaves once the basics are learned (Hawkins on the radio, then absent until the end) |

Gaps:
- No source comparing the HL1 Hazard Course with Blue Shift / Opposing Force's boot camp could be fetched. The
  Valve Developer Community "Hazard_Course" page returned 403, and MapCore's "Level Design in The Last of Us" also
  returned 403. The contrast is used here only in its well-known form: a separate course (HL1's Hazard Course =
  our TutB) versus teaching inside the story's first level (HL1's own opening = our route).
- A GMTK video titled "What Makes a Good Tutorial" could not be confirmed to exist.
- The YouTube videos were not watched. Their takeaways come from titles, transcripts and summaries.

The level designer's references (Rrajigar Mine on the Liandri Archives, CC BY-SA 3.0, and the Level Design Book, CC
BY-NC-SA 4.0) still govern the sluice reveal and the encounters.
