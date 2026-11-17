# ScoutDrone (The Solus Project) — experimental, shelved

A UE4SS Lua mod that spawns a small companion drone. The drone points out useful items (food, water, torches, tools) that the player walked past without looking at.

**Status: shelved on 2026-11-17. Not fun to play with in this state.** Published as a reference for UE4SS Lua work on this game, not as a finished mod.

## What it does

- Fair play: the drone only knows items it has seen itself (range 2500 uu + line of sight from the drone). "Not looked at" is the game's own per-item flag `HasEverBeenViewedOrUsed`.
- No screen overlay. The drone flies to the item, hovers above it and pulses its light.
- Body is built from engine basic shapes (ball with a twin-eye lamp on top).

## Known problems (why it was shelved)

- The point light sits next to the white eye discs and blows out into a glare that blinds the player.
- The drone picks a new scout spot on every curve the player walks, so it darts around.
- It floats. The wanted design was a ball that rolls on the ground.
- The hints did not feel helpful in play.
- Long sessions are untested.

## Install

1. Install UE4SS into `Solus\Binaries\Win64\` (game is UE 4.19.2).
2. Copy this folder to `Solus\Binaries\Win64\ue4ss\Mods\ScoutDrone\`.
3. Add `ScoutDrone : 1` to `ue4ss\Mods\mods.txt`.
4. Optional log: edit `ROOT` at the top of `Scripts/main.lua` to an existing folder. Without it the mod runs with no log.

## Notes for modders (things that cost time)

- Run all Lua from a hook on `SolusPlayer_C:ReceiveTick`. Lua in `LoopAsync` corrupted the VM.
- Do not keep asset pointers across frames. A cached sound cue was freed by engine GC after about a minute and the next `PlaySoundAtLocation` crashed the game. Resolve assets with `StaticFindObject` at each use.
- Calls that work: `SpawnActor` (StaticMeshActor, PointLight, set `.Mobility = 2`), `K2_SetActorLocation(v, false, {}, true)`, `K2_SetActorRotation`, `SetActorScale3D`, `LineTraceSingle`, `CreateDynamicMaterialInstance` on `BasicShapeMaterial` (vector parameter `Color`).
- Never compute a world object's position from the player's view direction each frame. It swings when the player turns.

Non-commercial fan mod. No game files included.
