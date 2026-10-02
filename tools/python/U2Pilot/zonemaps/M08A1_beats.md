# Beat graph: M08A1

149 wired actors, 94 chains (29 reach a door, cutscene, counter, AI or exit; the rest are ambience).
Chains are listed by the starting point's distance from the player start (a rough path order).

## Story chains

- **SceneManager** from other PlayerStart in zone 10 (0 from start)
  - -> cutscene SceneManager in zone 10, fires MusicScriptEvent1
  - -> trigger MusicScriptEvent [MusicScriptEvent1] in zone 10
- **O02** from objective ObjectiveEvent [M08_Objective02_Activate] in zone 10 (23 from start)
- **O03** from objective ObjectiveEvent [M08_Objective03_Activate] in zone 10 (46 from start)
- **O01** from objective ObjectiveEvent [M08_Objective01_Complete] in zone 10 (68 from start)
- **seal_door1** from trigger Trigger in zone 13 (3368 from start)
  - -> door Mover [seal_door1] in zone 0, fires seal1
  - -> door Mover [seal1] in zone 13
- **seal_door1b** from trigger Trigger in zone 15 (3488 from start)
  - -> door Mover [seal_door1b] in zone 0, fires seal1
  - -> door Mover [seal1] in zone 13
  - -> door Mover [seal_door1b] in zone 0, fires seal1
- **countfirstroomizarians** from counter Counter [FallingWall3] in zone 9 (4569 from start)
  - -> counter Counter [countfirstroomizarians] in zone 9, fires meetPollock1
  - -> trigger U2Dispatcher [meetPollock1] in zone 9
- **countfirstroomizarians** from counter Counter [FallingWall4] in zone 9 (4633 from start)
  - -> counter Counter [countfirstroomizarians] in zone 9, fires meetPollock1
  - -> trigger U2Dispatcher [meetPollock1] in zone 9
- **OneBrokenDoor** from trigger Trigger in zone 15 (4933 from start)
  - -> door Mover [OneBrokenDoor] in zone 0, fires BrokenDoor
  - -> other ParticleSalamander [BrokenDoor] in zone 15
  - -> trigger AlarmTrigger [BrokenDoor] in zone 15
- **glassdoor2** from trigger Trigger in zone 7 (5212 from start)
  - -> door Mover [glassdoor2] in zone 7, fires Musicaleventforthedoor
  - -> door Mover [glassdoor2] in zone 7
- **Camerasafe** from pawn U2Izarian in zone 7 (6348 from start)
  - -> counter Counter [Camerasafe] in zone 7, fires secondspeachoftheimbicile
  - -> trigger Trigger [secondspeachoftheimbicile] in zone 2, fires glassdoor1
  - -> door Mover [glassdoor1] in zone 7
  - -> door Mover [glassdoor1] in zone 7
- **Camerasafe** from pawn U2Izarian in zone 7 (6378 from start)
  - -> counter Counter [Camerasafe] in zone 7, fires secondspeachoftheimbicile
  - -> trigger Trigger [secondspeachoftheimbicile] in zone 2, fires glassdoor1
  - -> door Mover [glassdoor1] in zone 7
  - -> door Mover [glassdoor1] in zone 7
- **Camerasafe** from pawn U2Izarian in zone 7 (6425 from start)
  - -> counter Counter [Camerasafe] in zone 7, fires secondspeachoftheimbicile
  - -> trigger Trigger [secondspeachoftheimbicile] in zone 2, fires glassdoor1
  - -> door Mover [glassdoor1] in zone 7
  - -> door Mover [glassdoor1] in zone 7
- **hoardfuck** from pawn U2Izarian in zone 2 (7523 from start)
  - -> counter Counter [hoardfuck] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **h1** from pawn U2Izarian in zone 2 (8078 from start)
  - -> counter Counter [h1] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **boopex** from pawn U2Izarian in zone 2 (9266 from start)
  - -> counter Counter [boopex] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **h3** from pawn U2Izarian in zone 2 (9281 from start)
  - -> counter Counter [h3] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **h2** from pawn U2Izarian in zone 2 (9313 from start)
  - -> counter Counter [h2] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **onemoredeadalieng** from pawn U2Izarian in zone 1 (10217 from start)
  - -> counter Counter [onemoredeadalieng] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **h4** from pawn U2Izarian in zone 1 (10239 from start)
  - -> counter Counter [h4] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **asinlala** from pawn U2Izarian in zone 1 (10539 from start)
  - -> counter Counter [asinlala] in zone 2, fires Countpollockishaha
  - -> counter Counter [Countpollockishaha] in zone 2, fires pollockishaha
- **NewIndustrialDoor1** from trigger Trigger in zone 3 (10909 from start)
  - -> door Mover [NewIndustrialDoor1] in zone 1
  - -> door Mover [NewIndustrialDoor1] in zone 4
- **ajapornfar** from counter Counter [TheTrouts] in zone 3 (15836 from start)
  - -> counter Counter [ajapornfar] in zone 3, fires pollockcommentsontrouts3
- **ajapornfar** from counter Counter [Spunkers1] in zone 3 (15993 from start)
  - -> counter Counter [ajapornfar] in zone 3, fires pollockcommentsontrouts3
- **TransyDoor1** from trigger Trigger in zone 3 (18807 from start)
  - -> door Mover [TransyDoor1] in zone 3, fires finalmusictrip
  - -> counter Counter [finalmusictrip] in zone 3, fires MusicScriptEvent2
  - -> trigger MusicScriptEvent [MusicScriptEvent2] in zone 10
- **goestom08a2** from exit Trigger in zone 4 (19012 from start)
  - -> trigger LevelChange [goestom08a2] in zone 4
- **goestom08a2** from exit Trigger in zone 4 (19057 from start)
  - -> trigger LevelChange [goestom08a2] in zone 4
- **goestom08a2** from exit Trigger in zone 4 (19111 from start)
  - -> trigger LevelChange [goestom08a2] in zone 4
- **goestom08a2** from exit Trigger in zone 4 (19126 from start)
  - -> trigger LevelChange [goestom08a2] in zone 4

## Ambience chains (sounds, effects, props)

barlybyby x8, DropShipDummy x2, WillSlideDye x2, GoBigK x2, killallslowasses, starstheMusic1, DisIntroAmb, CreakNumbertwo, SolidGold, Distubekill, DisIzarianAmbientnumber1, showtheshadow, DisHumanDeath1, DisSteamScare1, DisMoreCreatureNoises, ShadowLurkNew1, ShadowLurkNew2, scriptedWakeup, ENCOUNTER1, UnderwaterHijinks, MusicScriptEvent1, DisSewerLaugh1, GoRoaches, MusicScriptEvent5, Distransitionupstairs1, KillAllRoaches, tauntyou1, wakeupcameraguys, MusicScriptEvent2, CameraAct1, Jump1, puppetlos, QQQDisRushIntoSolarium, solamesolame, Jump2, AllWillAttackPlayer, jump03b, neversawdatcomen, QQQQpollockishaha, GrassGrowlingGoodness, YeOldGrassGrowlers, LadderCreak2, LadderCreak1, Pollockflashbang, DisCrateMonger1, Mfreaks1a1, BoxBorker, MonGuts1a1, DisTrashTrouts, pollockcommentsontrouts1, pollockcommentsontrouts2, ploockcommentsonspunkers1, ploockcommentsonspunkers2, elvishasleftthebuilding1a1, Bordercreak1
