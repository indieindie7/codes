# Beat graph: TutA

38 wired actors, 15 chains (11 reach a door, cutscene, counter, AI or exit; the rest are ambience).
Chains are listed by walking distance from the player start along the AI path network (the order a player meets them, ignoring locked doors).

## Story chains

- **TutorialACutscene** from other PlayerStart in zone 1 (0 walked)
  - -> cutscene SceneManager [TutorialACutscene] in zone 1, fires Driver01Path, StartMusic, DropshipPath, DropshipSound, LetterboxText, Player02TutAStartDispatcher, PlayerTutAStartDispatcher, StartMusic, PlayerTutASaluteDispatcher, TutADestroyDispatcher
  - -> trigger MusicTrigger [StartMusic] in zone 1
  - -> cutscene SceneManager [DropshipPath] in zone 1
  - -> trigger SpecialEvent [DropshipSound] in zone 1
  - -> trigger AlarmTrigger [LetterboxText] in zone 1
  - -> trigger AlarmTrigger [LetterboxText] in zone 1
  - -> trigger U2Dispatcher [Player02TutAStartDispatcher] in zone 1, fires Player02TutAStart
  - -> trigger U2Dispatcher [PlayerTutAStartDispatcher] in zone 1, fires PlayerTutAStart
  - -> trigger U2Dispatcher [PlayerTutASaluteDispatcher] in zone 1, fires PlayerTutASalute
  - -> trigger U2Dispatcher [TutADestroyDispatcher] in zone 1, fires TutADestroy
- **Objective2** from objective ObjectiveEvent [u2sObjectiveTutorial] in zone 1 (164 walked)
- **Objective1** from objective ObjectiveEvent [dlgTutAElevator] in zone 1 (186 walked)
- **Objective3** from objective ObjectiveEvent [u2sObjectiveDropship] in zone 1 (189 walked)
- **CommandRoomDoor** from trigger Trigger [CommandRoomDoorTrigger] in zone 1 (402 walked)
  - -> door Mover [CommandRoomDoor] in zone 1
  - -> door Mover [CommandRoomDoor] in zone 1
- **BigLiftDoorDisabled** from other PropertyFlipper [u2sFlipLifts] in zone 1 (647 walked)
  - -> door Mover [BigLiftDoorDisabled] in zone 1
- **BigLiftDoor** from other PropertyFlipper [u2sFlipLifts] in zone 1 (648 walked)
  - -> door Mover [BigLiftDoor] in zone 1
- **TutAObjective1_Complete** from objective Trigger in zone 1 (653 walked)
  - -> objective ObjectiveEvent [TutAObjective1_Complete] in zone 1, fires Objective1
- **BigLiftDisabled** from other PropertyFlipper [u2sFlipLifts] in zone 1 (670 walked)
  - -> door Mover [BigLiftDisabled] in zone 1
- **BigLift** from other PropertyFlipper [u2sFlipLifts] in zone 1 (671 walked)
  - -> door Mover [BigLift] in zone 1
- **BigLiftDispatcher** from trigger Trigger in zone 1 (713 walked)
  - -> trigger U2Dispatcher [BigLiftDispatcher] in zone 1, fires BigLiftBeep, BigLiftDoor, BigLiftShake, BigLift
  - -> trigger SpecialEvent [BigLiftBeep] in zone 1
  - -> door Mover [BigLiftDoor] in zone 1
  - -> trigger EarthquakeTrigger [BigLiftShake] in zone 1
  - -> door Mover [BigLift] in zone 1

## Ambience chains (sounds, effects, props)

PlayerEnteredRoom, AtlantisLevelChange, TutBLevelChange, DroptheMarinePlease
