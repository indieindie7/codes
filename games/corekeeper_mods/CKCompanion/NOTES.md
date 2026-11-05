# Core Keeper Companion mod - notes
Index (section: gist)
1. What it is: BepInEx 5 plugin, clumsy AI buddy (player clone) + callouts
2. Install: BepInEx 5.4.23.6 + three fixes needed for Core Keeper (Unity 6)
3. Build: dotnet build plugin + patcher
4. Config: cfg keys, hotkeys, debug test keys
5. How it works: spawn, look, pathing, senses, callouts
6. Game hooks used
7. Test: minimized auto-load test, save backup, proof
8. Test result 2026-11-05 and known gaps
9. AutoPlayer: instruction text -> goals -> task tree, inbox/status channel, input patches
10. L4D layer: Director (threats, pacing, occupancy, telemetry) + survivor reflexes; runs 19-20

## 1. What it is
- `plugin/Plugin.cs` (one file, no Harmony patches). Core Keeper 1.x, Unity 6000.0.59, Mono, ECS.
- Buddy = clone of the player's GameObject with a random look and name (Pip, Moss, Nib, Dobbs...). It acts like a low-agency friend: follows 1.5-3 tiles, trips now and then, talks in a funny, well-meaning voice. No combat.
- Callouts: floating line above the buddy + 3-line HUD (IMGUI). Fair play (user rule 11-03): only what the buddy itself can see (tile line of sight, radius).

## 2. Install (all three are needed)
1. BepInEx 5.4.23.6 x64 unzipped into the game folder.
2. Replace `BepInEx\core\0Harmony.dll, MonoMod.Utils.dll, MonoMod.RuntimeDetour.dll, Mono.Cecil*.dll` with the game's own copies from `CoreKeeper_Data\Managed` (game ships HarmonyX 2.10.2 / MonoMod 22.3.23.4 / Cecil 0.11.4; BepInEx's older ones crash `Manager.EarlyInit` Harmony.PatchAll with MissingMethodException). Originals kept in `C:\re\corekeeper\bepinex_core_orig`.
3. `patcher/` -> `BepInEx\patchers\CKResolveFix.dll`. With Cecil 0.11 the preloader cannot resolve `netstandard 2.1` (preloader_*.log Fatal) and the chainloader cannot resolve BepInEx.dll itself, so every plugin is silently skipped ("0 plugins to load", cached in `BepInEx\cache\chainloader_typeloader.dat`). The patcher adds Managed/core/plugins dirs to both resolvers.
4. `plugin/bin/Release/net472/CKCompanion.dll` -> `BepInEx\plugins\`.
- DLLs in BepInEx are locked while the game runs: copy with the game closed.

## 3. Build
- `cd plugin; dotnet build -c Release` and `cd patcher; dotnet build -c Release` (net472; refs point at the Steam install).

## 4. Config (`BepInEx\config\local.corekeeper.companion.cfg`)
- General: Enabled, ToggleKey F7, TestCalloutsKey F8, Name, LookSeed.
- Follow: FollowDistanceMin 1.5, FollowDistanceMax 3, TeleportDistance 20, Speed 5, Clumsiness 1.
- Senses: SightRadius 9, LowHealthFraction 0.3.
- Callouts: HudLine, FloatingText, CooldownScale, DisplaySeconds 4, IdleChatterAfterSeconds 90.
- Debug (test only): AutoLoadWorld -1 (else world id to load from the title), AutoLoadCharacter 0, SpawnOffset 0 (tiles away at spawn), WanderRadius 0 (>0 = buddy walks to random points this far around the player, to test trips/ore while the player is AFK).

## 5. How it works
- Spawn waits until the tile map is filled (`Manager.multiMap.GetTileLayerLookup().AllTiles.Count() > 0`; it is empty for a few seconds after scene Main), then clones the player under an inactive holder (no Awake), strips colliders/rigidbodies/cameras/audio. The clone PlayerController stays inert like the menu preview.
- Random look: same steps as CharacterCustomizationMenu Randomize, via `customizationTable`; no helm/armor.
- Movement: tile A* (8 neighbours, no corner cutting, 3000 nodes; open set ordered by (f, seq) since int2 is not IComparable), re-path 0.4 s, teleport > 20 tiles or 3 s stuck, random trips. `transform.position = wpos - RenderOrigo`.
- Senses every 0.5 s; entities refreshed every 1.5 s. Callouts: enemy, danger (3+), boss (max HP >= 1500), lowhealth, chest (not locked), ore (vein seen 300 s), idle, hello, teleport, stuck, clumsy.
- Log lines: `[callout:<type>]`, `[pos]` every 5 s (with tile count), `[teleport]`, `[clumsy]`, `scene:`, `spawn check:`.

## 6. Game hooks (decompile `C:\re\corekeeper\src_other`)
- `Manager.main.player`, `Manager.load.GetNameOfCurrentScene()`, `Manager.camera.RenderOrigo`, `Manager.multiMap` (PugTilemap.SinglePugMap) tile lookup keyed by world int2 (x, z).
- EntityMonoBehaviour: isEnemy, currentHealth, GetMaxHealth(), WorldPosition, objectData.objectID.
- Auto-load: `SaveSlotPlayOption.StartGameFromActivity(worldID, charID)`.
- Animator hashes (PlayerController.cs:3093-3098, 3187): movementX -1801483167, movementY -476529417, facingX 898384463, facingY 1116435161, walkSpeed -1985230220, blink 842569181.

## 7. Test
- Back up `%USERPROFILE%\AppData\LocalLow\Pugstorm\Core Keeper\Steam\31559587\` (saves + worlds) first; backup 11-04 in `C:\re\corekeeper\save_backup_1104`.
- cfg Debug: AutoLoadWorld 0, SpawnOffset 6; `steam_appid.txt` (1621690) in the game folder when launching outside Steam. Launch minimized:
  `Start-Process -WindowStyle Minimized -FilePath "<game>\CoreKeeper.exe" -WorkingDirectory "<game>" -ArgumentList '-screen-fullscreen 0 -screen-width 1280 -screen-height 720'`
- Delete `BepInEx\cache\chainloader_typeloader.dat` after changing plugin resolution, or a stale "0 types" entry sticks.
- Reset Debug keys to -1 / 0 / 0 and remove steam_appid.txt after.

## 8. Test result 2026-11-05 (run 12, proof in test/run12-proof.log)
- Plugin loaded, world 0 auto-loaded, buddy "Dobbs" spawned 5.7 tiles away, walked by A* to 2.2 and idled. hello + chest callouts fired. No exceptions.
- Not seen yet (player stood still at spawn): teleport, enemy/danger/boss, lowhealth, ore, clumsy trip, idle chatter. Visual not checked by eye yet (window minimized).
- Installed 11-05 (game closed): patcher without diag writer, plugin with invariant `dist=`.
- Done after test: cfg Debug keys reset, BepInEx.cfg LogLevels default, steam_appid.txt removed. Saves restored from save_backup_1104 (AFK char was killed by a mushroom and autosaved; those saves kept in `C:
e\corekeeper\save_after_1105`).
- AFK 4 h follow-up (test/run12-afk-excerpt.log, first 260 lines): enemy + lowhealth callouts fired; after the player died and respawned at the Core (~14 tiles), the buddy walked there and sat at 2.2 tiles for the rest of the run. Follow works; no exceptions. 138 callouts, 128 of them idle.
- Run 13 (SpawnOffset 24, test/run13-teleport.log): buddy "Bumble" spawned 24 tiles off, `[teleport] far 24.0` to 1.5 tiles beside the player, teleport + chest callouts fired. Teleport verified.
- Run 14 (WanderRadius 12, Clumsiness 3, 3 min, test/run14-wander.log): 23 wander legs, 2 clumsy trips with callouts, chest callouts. Clumsy verified.
- Still not seen: stuck, danger/boss, ore (no ore within sight of the core base). Visual by eye not checked.
- Idea: back off idle chatter when the player has not moved for minutes (now every ~120 s for hours).

## 9. AutoPlayer (2026-11-05, plugin/AutoPlayer.cs, tools/ckauto.py)
- Instruction text -> goals (Goals.Parse; split on , ; then and) -> task tree (Seq/Repeat compounds; GoTo/Equip/Dig/Attack/Wait primitives). Reflexes interrupt the current goal: HP < 30% -> go home; enemy within 3 tiles -> defend. Idle = control stays with you.
- Grammar: mine|dig|get [N] [copper|tin|wall], explore [N], fight|kill [N], go to X Z, go home|core|base, wait N, stop.
- Channel: append lines to `BepInEx\ckauto\inbox.txt` (or `py tools/ckauto.py "mine 3 walls then go home"`); `BepInEx\ckauto\status.txt` = goal tree ([>] running, [x] done, [!] failed), queue, ASCII map around the player, recent events. Log lines `[auto]`.
- Input: Harmony prefixes on PlayerInput (GetInputAxisValue(h,v) for movement + aim, IsButtonCurrentlyDown / WasButtonPressedDownThisFrame for INTERACT, PrefersKeyboardAndMouse -> false) only while a goal runs. Works with the window minimized.
- Pathing: shared Buddy.FindPath (now partial paths toward far goals), water not walkable, TempBlocked tiles (60 s) when stuck on something not in the tile map.
- Tests (runs 15-18, minimized): mine 3 walls OK (equips CopperMiningPick slot 7, digs); explore OK in open ground; mine copper -> "nothing found" (no copper within 20 tiles of base).
- Known gap: furniture/stations/fences near the base are entities, not tiles, so GoTo gets stuck there (timeouts at about (-16,-5)). Next: build an occupancy set from placed-object entities or sidestep when blocked. Also untested: fight vs a live enemy, low-HP retreat, go home from far.
- Idea: free-text -> grammar via local Sage (8093) in ckauto.py when the parser does not understand.

## 10. L4D layer (2026-11-05, plugin/Director.cs + AutoPlayer.cs)
- Director (Director.Tick every frame, entity scan 0.4 s): threat board scored (1 + maxHP/100) x3 for bosses / distance; nearest drops; intensity from damage taken and enemies within 6 tiles (decays 4/s); phases relax -> buildup (>25) -> peak (>60, at least 8 s) -> fade -> relax; visited map (5x5 per 0.4 s) for frontier scores; occupancy from PlaceablePrefab entities within 40 tiles (game footprint: round(WorldPosition) + prefabCornerOffset/prefabTileSize rotated by DirectionCD via `EntityUtility.GetPrefabSizeAndOffset`; 1x1 torches skipped); danger cost within 3 tiles of an enemy fed into A* (`Buddy.ExtraCost`); `BepInEx\ckauto\telemetry.csv` row every 5 s (t,x,z,hp,max,intensity,phase,enemies,near4,goal,deaths,stucks,repaths,kills,heals,flees,damage,visited).
- Reflexes (AutoPlayer.Run, checked every frame, interrupt the goal and resume it; the goal's timeout clock is paused via Task.Shift): down -> Recover (wait for respawn, clears avoid marks); hp < 35 % with an enemy < 5 tiles -> Flee 3 s (direction scored by free run length, away from threats) then eat if food is in the hotbar; hp < 50 % and clear -> eat (held slot saved and re-equipped, a heal counts only if hp rose); enemy < 3.5 tiles (or < 6 at peak, or 2 within 4) -> defend; drop within 7 tiles and clear -> loot. Survival reflexes (down, flee) preempt a running reflex.
- Combat: target = top threat within radius, re-target every 2 s, 2 s quiet = done; approach by LineFree else partial A*; swing (held INTERACT) under 2.3 tiles, step back under 0.9; swarmed (3 within 4 tiles) -> fall back to `Director.Chokepoint` (few open neighbours, away from threats, line of sight), stand there and swing until the swarm thins or 8 s. A kill counts only when the target's hp reached 0 or the entity is gone ("lost" otherwise); "hit X hp a->b" lines prove swings land.
- Blocked-tile learning: GoTo makes no progress 1.5 s -> sidestep; again -> `Director.LearnBlockers` adds the footprints of static non-enemy entities within 1.6 tiles of the waypoint to `Buddy.Learned` (session-persistent, folded into Free()) and avoids the waypoint tile 20 s; "no path" clears the avoid marks once and retries. Explore: 120 candidates 8-18 tiles out, best 12 by frontier score, partial-path fallback to the farthest reachable tile.
- Grammar added: heal|eat|food, flee|run|escape|retreat, loot|pick up, hold [N] (defend in place), fight|kill|attack|clear|defend|hunt [N] (no N = all). Input patch for SECOND_INTERACT (Use2 = eat).
- Run 19 (6 min, explore 15 + go home x3): 0 deaths, no exceptions; go home, explore in open ground, loot/defend/eat reflexes and director phases worked. Failed: 69 stucks near base furniture (occupancy ignored rotation; avoid marks boxed the player in -> "no path"), explore "nothing more found", 70 "kills" overcounted (an inactive target counted as a kill). All fixed above (audit workflow wf_22429b02-bc5, 63 agents).
- Run 20 (full mission "explore 15 then go home then fight all then hold 60 then explore 15 then go home", 385 s): deaths 0, exceptions 0, kills 10 (all hp 0), damage 23, visited 1154, hp 108/131 at the end; every goal and reflex ran (explore 11/15 + 7/15, go home x2, fight all, defend, loot x4, hold). Failed: 152 stucks / 297 repaths, one stuck every ~2.5 s.
- Root cause of the stucks (runs 21-24): `Walkable()` used `HasTile(ground)`, so A* routed through bigRoot tiles (23 of the 49 tiles around the spawn are bigRoot). The game rule (Pug.Base `TileTypeUtility`, decompiled with ilspycmd): a tile is walkable when `GetTopTile(pos).tileType.IsWalkableTile()` (ground, dugUpGround, wateredGround, floor, bridge, rug, rail, ...); wall/bigRoot/fence/water/pit/ore are not. `Walkable()` now mirrors it via `Manager.multiMap.GetTileLayerLookup().GetTopTile(t)`.
- Spawn pocket: the spawn tile (18,-9) has bigRoot on all four sides, so with the game rule "explore 8" failed instantly ("49 candidates, 12 tried, 12 unreachable": A* forbade corner cutting). Raw-move test (inbox `push DX DZ [SECS]`, run 24): east into bigRoot moved 0.84, north-east through the diagonal gap moved 9.07. So the player squeezes diagonally between bigRoot tiles but not through them: `FindPath` now allows a diagonal whose blocked orthogonal neighbours are bigRoot (`Squeezable`, +0.6 cost); walls keep the no-corner-cut rule. `LineFree` is unchanged, so squeeze waypoints stay explicit.
- Debug tooling: inbox `probe` logs `Director.Probe` (top tile type/tileset, walk/free/occupied/learned for the player, next and waypoint tiles, a 7x7 census and a 15x15 grid: # wall, R bigRoot, P pit, ~ water, F fence, o ore, . ground, e occupied, @ player, plus entities within 1.5 tiles); the GoTo stuck branch logs the same probe; `BepInEx\ckauto\trace.csv` records t,x,z,mx,my,goal,reflex every 0.25 s while active.
- Run 25 (explore 8 with the squeeze rule, ~115 s): 8/8 legs reached from the spawn pocket, stucks 2, repaths 28, exceptions 0, damage 6.
- Run 26 (full mission, 420 s): explore 15/15 twice, go home, fight all (0 kills: nothing near the core), 1 death in a slime nest (respawn reflex returned to the core and the explore resumed), stucks 12, repaths 167, kills 168 (hp 0 seen; mostly AggressiveSlimeBlob hp 40), heals 2, flees 3, damage 293, visited 2121, exceptions 0. Failed: `hold 60` ("0/999") because `Hold` took its position and clock at parse time, five minutes before it ran (now taken on its first step); the last `go home` ("no path from (15,7)") because the player stood in a pocket 17 tiles from the core whose only exit leads away from it, so the 6000-node partial A* found no tile closer than the start (greedy dead end). GoTo now retries once with 40000 nodes (FindPath caches Free() per search), then drops avoid marks and learned blockers before failing.
- Run 27 (`hold 60` alone): "hold at (15,7) for 60s" -> hold fix verified (the pose is captured when the task starts, not at parse time).
- Run 28 (`go home` from the pocket (15,7)): null at 6k, 40k and with `IgnoreOccupied` -> "no path even ignoring placed objects" + probe grid (walls x12-14 at y7, x9-15 at y8, x13-17 at y6) -> FAILED. The pocket is a greedy dead end: the partial-path fallback walks to the reachable node closest to the goal, and from there nothing is closer, so every search returns null.
- Run 29 (bisect "go 27 -6 then go 7 -10 then go 0 0 then go 15 7", `LogOutput.run29.log`): leg 1 FAILED stuck at (17.6,-9.5): the model's only way east out of the spawn pocket (18,-9) is the diagonal squeeze into (17,-10), a dugUpGround tile that holds a `RootPlant/NonObtainable` entity with a physics collider. Occupancy only counted `PlaceablePrefab` entities, so the tile was "free"; `LearnBlockers` learned it, the next search found no path, the no-path handler cleared the learned tiles, and the loop repeated until FAILED. Leg 3 (0,0) was found only "when ignoring placed objects" yet walked fine: collider-less placeables near home over-blocked. Fix: `Director.Occupancy` now marks the footprints of every static non-enemy entity that carries a `Unity.Physics.PhysicsCollider` (any objectType except critters/pets/players/creatures/drops, ground torches excluded) instead of all placeables; the GoTo fallback log now says whether the occupancy-ignoring 40k search returned a full or a partial path.
- Known gaps: (1) dense bigRoot mazes: the model and the physics disagree in places (in run 26 the player walked (7,-10) -> (27,-6) but no model path exists in the probe grid of run 29); roots can be cut or regrow between runs, and tiles outside the loaded area read as `none`, so a long detour can be invisible. (2) Kills are counted by target hp reaching 0 while the player is in combat (run 26: 168 kills with only 28 "hit" lines: slime-nest spawns die to the companion/trap damage too). (3) The death in run 26 happened in a slime nest at ~(72,16) with the flee reflex firing too late at 27 % hp.
- Runs 30-32 (`go 0 0 then go 15 7 then go home`, then `go 6 -10 then go 0 0 then go 6 -10 then go home` twice): with the collider-based occupancy every leg completed, stucks 0, exceptions 0, repaths 11-12; `go 15 7` now fails fast ("no path from (12.2,6.2)": the (15,7) pocket is only reachable through the root plant at (17,-10), so the model says disconnected) instead of looping. Two more fixes from these runs: door entities (`WoodDoor`, `ElectricalDoor`... in Pug.Objects.dll) are skipped by the occupancy since they open for the player; and a destination that lies under a placed object (the core at (0,0)) ends the goto next to it ("destination under a placed object, stopped next to it") instead of running the 40k and occupancy-ignoring searches that always came back partial.
