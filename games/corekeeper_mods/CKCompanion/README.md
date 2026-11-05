# CKCompanion 0.1.0 (BepInEx 5) - Core Keeper

An architecture test, not a gameplay mod. The question was: how far does a Left 4 Dead style AI layer (director + survivor reflexes) and an instruction-driven autoplayer go in a top-down ECS game, built from the outside with a BepInEx plugin and no source access. The game itself was mostly a test bed.

Three parts, one dll:

1. **Companion NPC** - a clone of your character with a random look and name that follows you (1.5-3 tiles), trips now and then, and calls things out (enemy, boss, chest, ore, low health, idle chatter). Fair play: it only calls out what it can see itself (tile line of sight, 9-tile radius). No combat, no save changes.
2. **Director** (`Director.cs`) - L4D-style pacing: threat board, intensity from damage taken and nearby enemies, phases relax -> buildup -> peak -> fade, a visited map for exploration frontiers, an occupancy map built from placed objects' physics footprints, danger cost fed into A*, telemetry csv every 5 s.
3. **AutoPlayer** (`AutoPlayer.cs`) - text instructions -> goals -> hierarchical task tree (Seq/Repeat compounds over GoTo/Equip/Dig/Attack/Wait primitives). Reflexes interrupt the running goal and resume it: down -> recover, low hp with an enemy near -> flee then eat, enemy close -> defend (chokepoint fallback when swarmed), drop near -> loot. Input is injected with Harmony prefixes on `PlayerInput`, only while a goal runs, so it works with the window minimized.

Pathing is a tile A* that mirrors the game's own walkability rule (`GetTopTile(pos).tileType.IsWalkableTile()`), allows the diagonal squeeze between two bigRoot tiles the player can really do, treats placed objects by their collider footprint (doors excluded), learns blockers it bumps into, and falls back to partial paths / a 40k-node search / an occupancy-ignoring search before failing.

## Install (Core Keeper needs three fixes on top of BepInEx)
1. Install BepInEx 5.4.23.6 x64 into the game folder.
2. Replace `BepInEx\core\0Harmony.dll`, `MonoMod.Utils.dll`, `MonoMod.RuntimeDetour.dll` and `Mono.Cecil*.dll` with the game's own copies from `CoreKeeper_Data\Managed` (the game ships HarmonyX 2.10.2 / MonoMod 22.3.23.4 / Cecil 0.11.4; BepInEx's older ones crash `Manager.EarlyInit` with MissingMethodException). These are the game's files, so they are not in the zip.
3. Unzip the release over the game folder: `BepInEx\patchers\CKResolveFix.dll` (without it the preloader cannot resolve netstandard 2.1 and every plugin is silently skipped, "0 plugins to load") and `BepInEx\plugins\CKCompanion.dll`.
4. Start the game and load a world. F7 toggles the companion, F8 cycles test callouts.

Verify: `BepInEx\LogOutput.log` shows `companion spawned` and `[callout:...]` lines. If the chainloader reports 0 plugins after changing dlls, delete `BepInEx\cache\chainloader_typeloader.dat`. DLLs are locked while the game runs.

Uninstall: delete the two dlls and `BepInEx\config\local.corekeeper.companion.cfg`.

## Driving the AutoPlayer
Append a line to `BepInEx\ckauto\inbox.txt`, or use the CLI (edit the game path at the top of `tools/ckauto.py` if yours differs):

```
py tools/ckauto.py "explore 15 then go home then fight all then hold 60"
py tools/ckauto.py --watch 60 "mine 3 walls"
py tools/ckauto.py stop
py tools/ckauto.py            # status only
```

Grammar (split on `,` `;` `then` `and`): `mine|dig|get [N] [copper|tin|wall]`, `explore [N]`, `fight|kill|attack|clear|hunt [N]` (no N = all), `go X Z`, `go home|core|base`, `hold N`, `wait N`, `heal|eat`, `flee`, `loot`, `stop`. Debug: `probe` (tile census + 15x15 grid in the log), `push DX DZ [S]` (raw move).

`BepInEx\ckauto\status.txt` shows the goal tree (`[>]` running, `[x]` done, `[!]` failed), the queue, an ASCII map around the player and recent events. `telemetry.csv` (t, x, z, hp, intensity, phase, enemies, deaths, stucks, repaths, kills, heals, flees, damage, visited) and `trace.csv` (position + input every 0.25 s) sit next to it. Log lines are tagged `[auto]`, `[callout:<type>]`, `[pos]`, `[teleport]`.

## Config (`BepInEx\config\local.corekeeper.companion.cfg`)
General (Enabled, ToggleKey F7, TestCalloutsKey F8, Name, LookSeed), Follow (distances, TeleportDistance 20, Speed, Clumsiness), Senses (SightRadius 9, LowHealthFraction 0.3), Callouts (HudLine, FloatingText, CooldownScale, DisplaySeconds, IdleChatterAfterSeconds). Debug (AutoLoadWorld, AutoLoadCharacter, SpawnOffset, WanderRadius) is for unattended tests only; leave it at -1 / 0 / 0 / 0.

## Build
`cd src/plugin; dotnet build -c Release` and `cd src/patcher; dotnet build -c Release` (net472, the csproj HintPaths point at a default Steam install).

## Test results (2026-11-05, 32 unattended runs with the window minimized)
- Companion: follow, teleport-back, clumsy trips, hello/chest/enemy/low-health callouts seen live; a 4 h AFK run with no exceptions (`test/run12-afk-excerpt.log`, `run13-teleport.log`, `run14-wander.log`).
- AutoPlayer + Director: the full mission `explore 15 then go home then fight all then hold 60 then explore 15 then go home` runs end to end; every goal and every reflex fired at least once. After the walkability, squeeze, occupancy and adjacent-stop fixes the last three runs completed every leg with 0 stucks and 0 exceptions.
- Known gaps: dense bigRoot mazes where the tile model and the physics disagree (roots regrow or get cut, unloaded tiles read as empty); kills are counted by target hp reaching 0, so trap and companion damage inflate the count; the flee reflex fired too late once in a slime nest (death at 27 % hp). Details in `NOTES.md` sections 8-10.

## Changelog
- 0.1.0 (2026-11-05): first release.
