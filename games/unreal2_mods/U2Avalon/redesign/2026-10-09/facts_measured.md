# Open facts from plan.md s.8, measured (2026-10-08 23:5x, unreal modding part2)

Measured live in TutA on the player pawn `U2PlayerTutorial0` with `gm pick` + `gm set PROP` (prints the value):

| fact | value | notes |
|---|---|---|
| CollisionRadius | **28** UU | the engineer assumed ~25; Engine's Pawn default is 34 (U2 overrides it) |
| CollisionHeight (half) | **54** UU | so the player is 108 UU tall for collision; headroom rule >= 120 UU holds |
| MaxStepHeight | **37** UU | U2PlayerSP.uc default 37; Engine Pawn default 35 ("never change for NPCs") -> AI steps 35, design risers <= 35 |
| JumpZ | 470 | |
| GroundSpeed | 263 UU/s | as U2FairFights measured (5.3 m/s) |
| WalkableFloorZ | not a property in this engine build | the floor-angle limit is native; test a 45 deg ramp in game |
| Ladders | **supported**: PHYS_Ladder is used by U2Pawn (footsteps) and U2PlayerController (ladder sounds) | LadderVolume itself is native (Engine.u didn't export); place one and test |
| Lifts | LiftCenter/LiftExit not found in the exported U2 / U2AI / U2Pawns script | Engine.u batchexport failed (exit 1); check in UnrealEd's actor browser |
| Cutscene pawns | CutscenePlayer 17 / 61, CutscenePlayerAtlantis h 70, Aida 17 / 61 | from exported U2Pawns |
| Wardrobe scale | the player pawn's DrawScale is 1.225 with the Peacekeeper outfit | collision is not scaled with it |

Exports: Documents\Tools\u2_export\all\{U2, U2AI, U2Pawns} (ucc batchexport, the game's own packages).
