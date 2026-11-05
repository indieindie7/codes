# Atrio Companion mod - notes
Index (section: gist)
1. What it is: BepInEx 5 plugin, AI follower + L4D-style text callouts
2. Build + install: dotnet build, copy dll to BepInEx\plugins
3. Config: cfg keys, hotkeys, debug test keys
4. How it works: follow, pathing, senses, callouts, fair play
5. Game hooks used: classes/fields read from the game
6. Test: minimized auto-load test, save backup, log proof
7. Known limits / next ideas
8. Test result 2026-11-04: what fired, what was not seen

## 1. What it is
- `plugin/Plugin.cs` (one file, no Harmony patches). Atrio: The Dark Wild, Unity 2022.3.24 Mono, single-player.
- Companion = procedural cyan blob sprite (billboarded, bobbing) that walks 2-4 m from the player, idles when the player stops, teleports beside the player if > 25 m behind. No combat.
- Callouts: floating text above the companion + 3-line HUD log bottom-left (IMGUI). Each type has its own cooldown, plus priority so a low-priority line can't cut off a higher one.

## 2. Build + install
- `cd plugin; dotnet build -c Release` (net472, refs point at the Steam install's Managed dlls + BepInEx core).
- Copy `plugin/bin/Release/net472/AtrioCompanion.dll` to `<game>\BepInEx\plugins\`.
- Game: `C:\Program Files (x86)\Steam\steamapps\common\Atrio The Dark Wild` (BepInEx 5.4.23.6 already installed).

## 3. Config (`BepInEx\config\local.atrio.companion.cfg`)
- General: Enabled, ToggleKey (F7), TestCalloutsKey (F8, fires each callout type in turn, logged as debug).
- Follow: FollowDistanceMin 2, FollowDistanceMax 4, TeleportDistance 25, Speed 6.
- Senses: SightRadius 14, ResourceRadius 9, LowHealthFraction 0.3, MachineIdleSeconds 30.
- Callouts: HudLine, FloatingText, Volume (text size/opacity, 0 = silent), CooldownScale, DisplaySeconds 4, IdleChatterAfterSeconds 90.
- Cooldowns (s): enemy 10, danger 30, lowhealth 25, resource 45, night 90, idle 120, unpowered 60, norecipe 90, machineidle 75.
- Debug (test only, keep off for play): SpawnWithoutPlayer, AutoLoadSaveSlot (-1 off; else loads that slot from the title screen after 4 s), SpawnOffset (spawn N m away to prove following).

## 4. How it works
- Follow: hysteresis (start moving > max, stop < mid, back off < 0.8*min). Path = `NavMesh.CalculatePath` (game's baked navmesh, same one MobMovement/creatures use), re-pathed every 0.4 s, walking corner to corner; each step goes through a SphereCast fan (0, +-30, +-60, +-90, +-135 deg) so it slides around props. Speed scales up to 3x when far.
- Senses every 0.5 s; object lists refreshed every 1.5 s (creatures, harvestables) / 5 s (machines).
- Fair play (user rule 11-03): every callout needs the thing within the companion's own radius AND a clear `Physics.Linecast` from the companion's eye. Low health reads the player's own health (the companion sees the player). Night = DayNightCycle.IsDaytime flip (anyone sees dusk).
- Direction words (left/right/ahead/behind) are relative to the camera view from the player.
- Types: enemy (+ "danger" when >= 3 seen), lowhealth, resource, unpowered machine, machine without recipe, machine idle (has recipe, not cooking for MachineIdleSeconds), night falling, idle chatter after a long quiet. 3-5 line variants each.
- Every callout logs `[callout:<type>] "<text>" at companion=(x,y,z)`; position every 5 s as `[pos] companion=... target=... dist=... moving=...`.

## 5. Game hooks used (from ILSpy source in C:\re\atrio\src_*)
- Player: `Isto.Core.Beings.PlayerController` (FindObjectOfType), `PlayerHealth._currentHealth` (reflection) / `currentMaxHealth`.
- Enemies: `Isto.Core.Beings.Health` (HP > 0) on an object with a BehaviorDesigner `Behavior` tree.
- Resources: `HarvestableController` (playerHarvestable, item, IsGrowing).
- Machines: `Isto.Atrio.Factory._systemFactory` (reflection) -> `Isto.Core.Automation.AutomationFactory` (Recipe, Cooking, WaitingToDropItem); `Isto.Core.Power.PowerTethered` (Powered, PowerSource, Registered).
- Night: `Isto.Atrio.DayNightCycle.IsDaytime`.
- Auto-load: `Isto.Core.Game.GameState.IsInTitleScene()` / `LoadSaveGame(int slot)` (GameState.cs ~:306).

## 6. Test
- Atrio running = check its start time/command line first; an instance the user started is never killed.
- Back up `%USERPROFILE%\AppData\LocalLow\Isto\Atrio\SaveSlot*` first (the game autosaves); restore after.
- cfg: AutoLoadSaveSlot = 0, SpawnOffset = 10. Launch minimized:
  `Start-Process -WindowStyle Minimized -FilePath "<game>\Atrio.exe" -WorkingDirectory "<game>" -ArgumentList '-screen-fullscreen 0 -screen-width 1280 -screen-height 720'`
  (no steam_appid.txt needed while Steam runs.) Unity keeps updating while minimized.
- Proof: grep LogOutput.log for `player found`, `companion spawned`, `navmesh path ok`, `[pos]` dist dropping from ~10 to 2-4, `[callout:`.
- Reset cfg Debug keys to -1 / 0 after.

## 7. Known limits / next ideas
- Visual is a placeholder blob; next: tinted clone of a friendly creature's Spine skeleton.
- Enemy check = "creature with a behaviour tree", so passive critters can be called hostile; next: filter by attack behaviours (BeeAttack, BoxMonsterLungeAtPlayer...).
- Companion does not collide with the player's CharacterController and is not saved; it respawns on load.
- Direction words use the camera, not compass points.

## 8. Test result 2026-11-04 (run 3, slot 0, proof in test/run3-proof.log)
- Loaded, auto-loaded slot 0, player found, companion spawned 10 m off -> walked on navmesh to 2.8 m and idled; teleport fired when the load moved the player 47/158 m.
- Callouts fired: resource ("promoted employee" = old player body piles), idle chatter after 90 s quiet. Zero errors in LogOutput.log.
- Not seen in this save spot (player stands still, no creatures/machines in 14 m, daytime): enemy, danger, lowhealth, machine, night. Code paths compile; need a save near a base / at dusk.
- Gap: several same-named piles each get one callout (dedupe is per instance); dedupe by name next.
- Saves backed up and verified unchanged after the test; cfg Debug keys reset to -1 / 0.
