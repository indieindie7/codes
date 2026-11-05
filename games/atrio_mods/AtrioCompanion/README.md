# Atrio Companion 0.1.0 (BepInEx 5)

An AI buddy for **Atrio: The Dark Wild** that walks beside you and calls things out, Left 4 Dead style ("Contact, left!", "That furnace has no power.", "Night's falling.").

## Features
- Follows at 2-4 m on the game's own navmesh, steers around props, idles when you stop, teleports back if it gets 25 m behind.
- Callouts as floating text above it plus a 3-line HUD log. Types: enemy spotted (with direction), many enemies, you are low on health, loot/resource nearby, machine unpowered / no recipe / idle, night falling, idle chatter. Several lines per type, own cooldown per type, no repeats of the same pile.
- Fair play: it only calls out what is inside its own sight radius with clear line of sight. No map reading.
- No combat, no save changes, no Harmony patches.

## Install
1. Install BepInEx 5 x64 (5.4.23+) into the game folder.
2. Copy `AtrioCompanion.dll` to `Atrio The Dark Wild\BepInEx\plugins\`.
3. Start the game and load a save. F7 toggles the companion, F8 cycles test callouts.

Verify: `BepInEx\LogOutput.log` shows `companion spawned` and `[callout:...]` lines.

Uninstall: delete the dll (and `BepInEx\config\local.atrio.companion.cfg`).

## Config (`BepInEx\config\local.atrio.companion.cfg`)
Follow distances, teleport distance, speed, sight radius, low-health threshold, per-type cooldowns, HUD/floating text, text size, hotkeys. The Debug section is for testing only.

## Build
`cd src; dotnet build -c Release` (net472; the csproj points at a default Steam install path, edit the HintPaths if yours differs).

## Known limits
- Placeholder look (cyan blob sprite).
- Any creature with an AI tree counts as hostile, so passive critters can trigger "enemy".
- Tested 2026-11-04 on game build with Unity 2022.3.24: follow, teleport, resource and idle callouts confirmed in a real save (`run3-proof.log`); enemy/low-health/machine/night lines not yet seen live.

## Changelog
- 0.1.0 (2026-11-04): first release.
