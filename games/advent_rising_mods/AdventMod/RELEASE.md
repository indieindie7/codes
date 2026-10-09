# AdventMod: release-readiness audit (2026-10-09)

The user's line: "if we can test everything and it's all done the mod will be finished." This file is
the finish line: what ships on and off, what the zips must and must not carry, what the docs lacked
(now added to README.txt / NEXUS.md), what the user has to have seen working, and the licences.
Audit of master at 30fd633 plus the working tree. No build, no zip, no game run was made for it.

**Top blockers, in order** (details in the sections below):

1. **The repo's `System\AdventMod.u` is the `-JiggleSkin` build: it carries the Seeker skin texture**
   (`SeekerSkinJ` / `seeker_infantry_filled` are inside the working-tree file and the game's copy).
   It is uncommitted (`M` in git status). It must never be committed and never packaged. The committed
   `AdventMod.u` (HEAD) is older than the jiggle mesh, ModNeeds and foot IK. The release needs a fresh
   **plain** `build.ps1` (no switch), then `System\AdventMod.u` committed from that, and the
   `-GraphicsOnly` build redone the same way (`System\AdventMod-graphics.u` in git is from 2026-10-06).
2. **The repo's `System\d3d8.dll` is stale** (2026-10-08 15:12, 948 KB): it has no `atmos=`, `sheen=`,
   `terraindetail=` code, yet the shipped `U2Shaders.ini` turns all three on. The game runs a newer
   build (16:01, fork ~0ee70ee) and the fork's `bin\Release\d3d8.dll` is newer still (2026-10-09,
   c04da3a: `surface=` detail DDS, `zwrite=`). Copy the fork build the user is playing on into
   `System\` (and check `gideon_uniform_pbr.dds`, item 4) before `package.py`.
3. **Defaults that the user has never seen and that change play**: `bDeathAnims` ships **off** while
   README.txt (2.1) promises death animations and the user's own ini has it **on**; `bSlideMeter`
   and `bLogBones` ship **on** (measurement/logging); `bArmor` + `bPlateActors` (steel plates on the
   Seekers) ship on but were rebuilt after the user's last verdict ("pink sheen", parked). See table.
4. **Game-derived data in the package**: `U2Shaders\gideon_uniform_pbr.dds` (normal/roughness map
   computed from Gideon's own skin texture: a transform of game pixels) is in the zip and
   `pbr=2e106041 gideon_uniform_pbr.dds` is in the shipped ini. Either drop both from the release
   or decide that a derived map is fine (the gib meshes cut from the game's models and the jiggle mesh
   are the precedent for *geometry*; no release so far has shipped anything made from texture pixels).
5. **Armour hit data is not shipped**: `native\armour.c` reads `<game>\AdventMod\Armour\<mesh>.amesh`
   (made by `build.ps1` from the user's psk exports); `package.py` and the installer copy nothing
   there, so players get the bone-table fallback (works, logged once per mesh, less precise). Decide:
   ship `AdventMod\Armour\*.amesh` (ref skeleton + weighted vertices + faces/UVs + a flag per face, no
   pixels) with a README copy step, or state the fallback.

Also before "finished": the licence folder lacks three pieces the d3d8.dll contains (Dear ImGui,
stb_image_write, UnityPCSS), the stray `U2Shaders\UsersjohnAppDataLocalTempg3.asm` and
`terrain_detail_preview.png` would go into the zip's `System\U2Shaders`, and the installer's "Done!"
line still points at menus that no longer exist (Video > More Display Options).

## Status after the fix pass (2026-10-09, source only, no build)

| blocker | state |
|---|---|
| 1. -JiggleSkin `AdventMod.u` | **pending the build session**. `package.py` now refuses any `AdventMod.u` / `AdventMod-graphics.u` that contains `SeekerSkinJ` |
| 2. stale `d3d8.dll` | **pending the build session**. `package.py` now refuses a `System\d3d8.dll` without the string `atmos` |
| 3. defaults | **fixed in source**: `ModReact.bDeathAnims=True`, `ModMoves.bSlideMeter=False`, `ModPlayerBlood.bLogBones=False` (table rows below updated). Every other log/measure default was already off. Needs the plain build to take effect |
| 4. `gideon_uniform_pbr.dds` | **fixed in package.py**: the .dds is not in the allow-list and the `pbr=2e106041 ...` line is cut from the shipped `U2Shaders.ini` (`package.py` refuses if the name is still in it). The local `U2Shaders\gideon_uniform_pbr.dds` and the rule in the repo's `System\U2Shaders.ini` stay for the user's own play. **The PBR skin rule is left out of the release**: a player can regenerate it with `tools\make_pbr_maps.py <Gideon's uniform texture, exported from the game's Textures as dds/png> gideon_uniform_pbr.dds uniform` (needs numpy + Pillow) into `System\U2Shaders\` and add `pbr=2e106041 gideon_uniform_pbr.dds 1.8 1.6` to `U2Shaders.ini` (`tools\tex_hash.py` gives the hash); not documented in the README |
| 5. armour data | **fixed in package.py / installer / README**: `AdventMod\Armour\*.amesh` ship from the game folder build.ps1 wrote them to (`--game <folder>` to point elsewhere; refuses when none are there); never `*_faces.png` / `*_mask.png` (an image-extension guard refuses any png/tga/jpg in the list bar the LUT bmps). The installer copies them to `<game>\AdventMod\Armour` and removes them on uninstall; README manual step 2 names the folder; KNOWN LIMITS reworded |
| licences | **fixed**: `Licenses\DearImGui-LICENSE.txt` (copied from the fork), `stb_image_write-LICENSE.txt` (the header's dual-licence block), `UnityPCSS-LICENSE.txt` (MIT, Copyright (c) 2017 Lucas Norr). AMD CAS and Khronos: no licence file exists locally (only the shader header's notice), so CREDITS.txt names the licence and where its text lives instead of a reproduced copy. CREDITS.txt: branch gi-cascades, the fork's licence (BSD-2 for the layer, GPL-3 for the U2Shaders additions), atmos.hlsl under Quilez, the technique credits, Kimodo clips, "no game textures" + the derived meshes |
| stray shader files | **fixed**: `package.py` takes `U2Shaders\` by an explicit allow-list (the tracked files bar the pbr dds; .py + terrain_src.hlsl go to Source) and prints what it skipped |
| installer "Done!" line | **fixed**: names the Options hub (Gameplay, Camera, Audio, Screen, Graphics, Quality, Accessibility, Controls) |
| version | **fixed**: `VER = "3.0"`, README title "AdventMod 3.0 - ...", CHANGES header "3.0 (2026-10)". The "Gore (new in 2.1)" heading is true as written and stays; `package.py --graphics` now cuts on `"  Gore ("` instead of the version. `package.py --check` (new) runs every refusal and anchor lookup without writing a zip: it passes on a scratch copy with stand-in binaries, and on the real tree it refuses as it should (blockers 1 and 2) |

**What remains for the build session** (in order): close the game; plain `build.ps1` (no switch); confirm
`System\AdventMod.u` has no `SeekerSkinJ`; `build.ps1 -GraphicsOnly` for `System\AdventMod-graphics.u`,
then plain again so the installed build is the full one; copy the fork's current `d3d8.dll`
(`Documents\github\d3d8to9-gi\bin\Release`, c04da3a; contains `atmos`) into `System\`; commit
`System\AdventMod.u`, `AdventMod-graphics.u`, `AdventNative.dll`, `d3d8.dll` by path; `package.py --check`,
then `package.py` and `package.py --graphics` when the user asks for the zips. The play-test (section 4)
still decides the "needs verdict" rows; nothing in this pass touched a feature switch.

---

## 1. Shipping defaults

Every config switch, with the compiled default (`defaultproperties`, or False/0/"" when absent), where
the user's own ini differs, and a verdict. "Needs verdict" = defaults on (or off) but the user has not
played it; the play-test in section 4 decides. The user's live `System\AdventMod.ini` was read for the
"user ini" column (it holds only what the game wrote; everything else is at the compiled default).

### Debug, log and test-only switches (must ship off / empty)

| class | key | default | user ini | verdict |
|---|---|---|---|---|
| ModSettings | bFpsGraph | False | False | ship off (standing rule; the user has had it on before: it is their ini, not the build) |
| ModSettings | bGoreLog | False | **True** | ship off. The user's ini has it on: every hit and mark goes to AdventNative.log (costly in a long fight). Not a build issue, but worth telling the user |
| ModSettings | bD3DTrace | False | False | ship off (a test ini with it on GPFs at the first tick, ARMOUR.md) |
| ModSettings | bDebugFOV, bShadowProbe, bTargetLog, bDebugCombat, bJumpLog, bMouseLog | False | False | ship off |
| ModSettings | DebugStuckTurn | 0 | 0 | ship 0 |
| ModSettings | DebugDecalTexture, DebugCommands, DebugOpenMenu, DebugActions, DebugLevelMenu, DebugLevelCommands, DebugMenuDelay | "" / 0 | "" | ship empty (ModGUIController / ModMutator run them when set) |
| ModShadowController | bDebugStockDir, bDebugOwnShadow | False | | ship off |
| ModTitle | bLogSequence | False | | ship off |
| ModGibAtlas | bCardLog / CardDebug | False / 0 | | ship off |
| ModArmor | bArmorLog | False | | ship off |
| ModArmor | GridTest | "" | | ship empty (spawns the ModArmourGrid harness) |
| ModReact | TestClip | "" | | ship empty |
| ModMelee | bTestBlade | False | **True** | ship off (the player starts with a blade; the user's ini has it on for testing) |
| ModMinds | bMindLog, bHoundLog, bWallKickLog | False | | ship off |
| ModNeeds | bNeedsLog | False | | ship off |
| ModNeeds | ForceHunger / ForceFatigue / ForceCuriosity | -1 | | ship -1 (test hooks) |
| ModAction / ModBody / ModFeet / ModJiggle | bActionLog, bBodyLog, bFeetLog, bJiggleLog | False | | ship off |
| ModFeet | bFeetMeter | False | | ship off (the foot-to-floor meter logs every 8 s) |
| ModMoves | bSlideMeter | False (was True; fixed 2026-10-09) | | ship off: it is a measuring tool (per-footfall bone reads for every walking character on screen, a log line every 8 s). It was left on for the stride-match work; nothing a player sees depends on it |
| ModPlayerBlood | bLogBones | False (was True; fixed 2026-10-09) | | ship off: a once-per-level log of the hand bones and weapon place. Harmless but a debug default |
| ModPilot | Steps | empty | | ship empty (a non-empty list makes the mod drive the player) |
| ModLive | bResume etc. | False | | written by "live save" only; nothing to ship |

Pilot commands (`ModPilot`: 70 steps, SPAWN, HURT, GIBAHEAD, SPAWNPACK, WALLKICK, NEEDS, GOTO...) and
`mutate needs ...` / `mutate live ...` only work when a pilot script or the console is used; they
ship in the source (GPL) and are inert. `ModTestCommandlet` is a compiler-side check, inert in game.

### Graphics (seen by the user, shipped in 2.0/2.1)

| class | key | default | verdict |
|---|---|---|---|
| ModSettings | bShadowFix, bSoftShadows, bNoGamePostFx | True | ship on (2.0) |
| ModSettings | bTrilinear, bWidescreen | True | ship on |
| ModSettings | bBorderless (via bScreenModeSet) | borderless once | ship as is (2.1) |
| ModSettings | FOV 75, MaxFps -1, PostPreset 1 (Natural), Sharpen 0.4, bSMAA True | | ship as is |
| ModSettings | GiLevel | 0 (off) | ship off (user plays with 1; menu row exists) |
| ModSettings | bAmbientOcclusion | False | ship off (user plays with it on; menu row "Ambient Light") |
| ModSettings | Colorblind 0 / ColorblindStrength 1 | | ship as is (the user's ini has Colorblind=3: their choice, the menu writes it) |
| ModShadowManager | bPcssIndoorsOnly True, NpcShadows 20, bCrowdShadows True, bCrowdActorShadows True | | ship as is |
| ModShadowController | bPlayerOnly False, bSunOnlyOutdoors True, bRespectBaked True | | ship as is |
| ModPanel | bPanel True | | ship as is |
| U2Shaders.ini | pcss, post, smaa, gi (off unless the page sets it), ssao (same), sss=1, gloss, streaks, strings, hands, lens, atmos, soft, terraindetail, sheen, aniso=16, lagfix (in the dll) | all on | ship on. **Needs verdict**: atmos (fog strength per level), sheen, terrain detail, sss/char_skin: the graphics pass of 2026-10-08 was checked in hidden runs only (GRAPHICS-PASS.md "Have a person playtest"); light shafts were never seen at all |

### Gameplay, gore and combat (2.1 and after)

| class | key | default | verdict |
|---|---|---|---|
| ModSettings | bPadDriftFix True, bRawMouse True, bCombatPickupFilter True, ExploreSpeed 1.25, Damage* 1.0 | | ship as is (bRawMouse and ExploreSpeed were new after 2.0; the user has played them) |
| ModGore | bBlood, bImpacts, bCasings, bCorpseShots, bRemains, bGibs, bBloodCoats, bDirt, bWounds, bBleedTrail, bScreenBlood, bBlastShake, bWallRuns, bLivePools, bWallHoles, bBreaches | True | ship on (2.1 and the 2026-10-06/07 gore work the user saw in play) |
| ModGore | bFootprints, bDrips, bBodyStreaks, bGooStrings | True | **needs verdict**: built 2026-10-08, checked in hidden runs only (GORE-DESIGN.md "Playtest by a person, then tune": streak brightness, goo frequency, drying, wall-run amount) |
| ModGore | bKarmaFreezeFix | False | ship off (tested 2026-10-08: frozen bodies stood up; the script hold does the job) |
| ModGore | bHoundRagdolls | False | ship off (hound ragdolls crash the game; hounds use the hand-keyed clips) |
| ModGore | budgets: MaxDecals 80, MaxHoles 160, MaxGibs 60, MaxDrops 24, MaxFootprints 40, MaxWounds 48, MaxClutter 150, MaxCoats 10, MaxDirt 60, MaxRubble 30 | | ship as is |
| ModReact | bFlinch, bSpringFlinch, bStagger, bKnockdown, bDeathRagdoll, bClipFloor | True | ship on |
| ModReact | bDeathAnims | True (was False; fixed 2026-10-09) | ship on: what the README promises and what the user plays with (their ini had it on). Play-test item 9 still has to confirm it |
| ModReact | bDeathAnimRagdoll | False | ship off (a ragdoll begun from a clip crashed twice) |
| ModReact | bPoweredRagdoll | False | ship off (calibration never finished) |
| ModSever | bSever True, bStumps True | | ship on |
| ModMelee | bBlades True, bBladeLight True, bSwingAnims True | | ship on (blade pickups: 2.1 shipped them undocumented; swings v2 "not yet judged by the user") → **needs verdict on the swings** |
| **ModArmor** | **bArmor True, bPlateActors True** (steel plates of our own on the Seekers), bPreserveTtk True, bPlates False, bExpose False | | **needs verdict**: the plate actors are the 2026-10-07 rebuild after the user parked the first version ("pink sheen"). ARMOUR.md says they work; no user verdict on the look is recorded. If they jar: `bArmor=False` keeps everything else |
| **ModArmor** | **bArmourHits True, bArmourSparks True, ArmourFactor 1.0** | | **needs verdict** (new 2026-10-09): sparks instead of blood on an armour hit, no damage change at 1.0. Players get the bone-table fallback unless the .amesh files ship (blocker 5) |
| ModGibAtlas | bGibCards True | | ship on (seen 2026-10-07) |
| ModPlayerBlood | bHands, bLens, bReplaceScreenBlood | True | **needs verdict** (2026-10-08, hidden runs only; lens strength is on the tuning list) |
| **ModMinds** | **bMinds True** (feelings, cover, suppression, tokens, path profiles, flanking) | | **needs verdict**: built 2026-10-08, A/B runs only. `bMinds=False` = stock AI |
| **ModMinds** | **bHoundPack True** | | **needs verdict**: 6+6 A/B runs (more bites from the sides, later first bite); "direction right, not proven for pinning" |
| **ModMinds** | **bHoundWallKick True, bLeapLinks True** | | **needs verdict**: the move works (15 of 18 kicks) but is rare (one per hound per 30 s) and links were never taken on the test map. Harmless if unseen; ship on unless a kick looks wrong |
| ModMinds | bPathProfiles True | | ship on (part of bMinds) |
| **ModNeeds** | **bNeeds True** | | **needs verdict**: 17 clean hidden runs; hounds feed on fallen mates, marines investigate noises, starved packs commit early. Off = ModMinds alone |
| **ModMoves** | **bLean True, bStrideMatch True** | | **needs verdict** (2026-10-08; lean verified by numbers, never judged by eye) |
| **ModAction** | **bVault, bSlam, bBarge True** | | **needs verdict** (2026-10-08: Gideon vaults cover, slams into walls on a dodge, barges props) |
| **ModBody** | **bSeekerArms, bHoundBody, bGroundPitch True** | | **needs verdict** (2026-10-08: Seeker arms show anger/fear, hounds snarl/cower and pitch to slopes) |
| **ModFeet** | **bFootIK False** | | **off until the user plays it** (FEET.md). Measured good (ankle 7-8 over its floor, no faults in 11 runs); open: no foot tilt to slopes, humans only, the whole body dips on stairs at a run. Recommendation: play one level with `bFootIK=True`; ship **on** if nothing jars, else leave off and say so |
| ModFeet | bPlayerFeet, bAIFeet, bPelvis True; MaxDrop 12, MaxLift 35, Gain 10, PelvisDrop 30 | | ship as is |
| **ModJiggle** | **bJiggle True** | | **needs verdict**: 4 clean hidden runs, "how it reads in motion to the user" not measured; the knobs are Gain and the per-bone clamps (ModJiggleBones) |
| ModJiggle | bJiggleSkin | False | **ship off, and the release build must be the plain build** (no `-JiggleSkin`): the filled skin is a game texture, local only (blocker 1) |
| ModJiggle | bRelink True | | ship on (the mesh swap the jiggle needs) |

**Recommended release set:** every table above as shipped; the three `defaultproperties` edits
(`ModMoves.bSlideMeter=False`, `ModPlayerBlood.bLogBones=False`, `ModReact.bDeathAnims=True`) are done in
the source (2026-10-09) and need the plain build. Everything marked "needs verdict" ships **on** if the play-test (section 4)
passes and gets its config key named in the README so a player can turn it off; `bFootIK` goes on only
with a yes from the user. Nothing else changes.

## 2. Package audit (`package.py`, VER = "2.1")

What the full zip gets (`AdventMod-<ver>.zip`; the `-nexus.zip` is the same without the two .bat files
and with the README's installer paragraphs replaced):

| zip path | source | status |
|---|---|---|
| System\AdventMod.u | System\AdventMod.u | **must be a fresh plain build** (blocker 1). Today's working-tree file is the -JiggleSkin build (16.8 MB, contains `SeekerSkinJ`); HEAD's is 14.8 MB and predates jiggle/needs/feet |
| System\AdventMod.int, AdventNative.dll | System\ | AdventNative.dll in the working tree is current (modified, uncommitted); commit it with the .u |
| System\d3d8.dll | System\d3d8.dll | **stale** (blocker 2): copy the fork build (gi-cascades, the one in the game folder or `bin\Release`) |
| System\U2Shaders.ini | written from System\U2Shaders.ini | current; see item 4 on the `pbr=` line |
| System\U2Shaders\* | the `SHADERS` allow-list in package.py | fixed 2026-10-09: the stray `.asm` / `_preview.png` and `gideon_uniform_pbr.dds` are skipped (the first two were taken by the old whole-folder copy) |
| Source\U2Shaders\*.py, terrain_src.hlsl | | fine (generators) |
| KarmaData\Advent.ka | | fine (full edition only) |
| Install / Uninstall AdventMod.bat | | full zip only; **not in the Nexus zip** (correct). "Done!" names the hub now; copies/removes `AdventMod\Armour` (2026-10-09) |
| AdventMod\Armour\*.amesh | `<game>\AdventMod\Armour` (build.ps1's output; `--game`) | added 2026-10-09; the `*_faces.png` / `*_mask.png` beside them never (allow-list + image guard) |
| Licenses\* | | seven files now (section 5); the three missing texts added 2026-10-09 |
| Source\native\*.c | | fine (nothing third-party inside: only the CRT and windows.h) |
| Source\Classes\*.uc | | fine; includes the test classes (ModPilot, ModTestCommandlet, ModArmourGrid), which is right for GPL source |
| README.txt | README.txt (rewritten for the Nexus zip) | updated by this audit |

**What the new features need that is NOT in the zip:**

- `AdventMod\Armour\*.amesh` (armour hits, blocker 5). Generated at build into the game folder from
  `Documents\AdventRising_meshes\*.psk` + the game's `Textures` by `tools\make_armour_data.py`. Content:
  ref skeleton, vertices with weights, faces with UVs and one armour bit per face. No texture pixels
  (the bit was *sampled* from the game's chrome mask offline). Next to them the build also writes
  `*_faces.png` (the game's diffuse with armour faces tinted: **game pixels**, "scratchpad only" per the
  tool's docstring) and `*_mask.png`; if the .amesh files are ever shipped, take only `*.amesh`.
  Without them the mod works: `armour: no data for mesh X: the bone table decides` once per mesh.
- `AdventMod\Meshes\seekerinfantry_jiggle.psk` is **not needed at run time**: `#exec MESH MODELIMPORT`
  compiles it into AdventMod.u (`SeekerInfantryJ`). It is the game's own Seeker mesh re-rigged (same
  points, UVs, weights, plus 10 bones): geometry derived from a game asset, as the gib parts already
  are. Not in git (lives in Documents\AdventRising_meshes\jiggle). Fine under the existing precedent.
- `AdventMod\Anims\*.psa` (deaths, blade swings, hound clips): compiled in; our own clips. Fine.
- `AdventMod\Gibs\*.ase`: compiled in (2.1 precedent).
- `AdventMod\Textures\*.tga`: compiled in; all generated by `tools\make_*.py` (checked: every `#exec
  TEXTURE IMPORT` file is a generated one; `armor_seekerinfantry_m01..15` are flat meat colour x UV
  region masks, no pixels). The git-ignored `armor_seekerinfantry_c*.tga` are not imported.

**Must NOT be included** (none of these are in `package.py`'s list, so they are safe unless the list
changes): `Textures\`, `hound_game3.png` (a game screenshot, git-ignored), `obj\*.obj`, `sheet.py`,
`test_run.ps1`, `build.ps1`, `*.md` design docs, the `*_faces.png` sheets, the user's game-folder
`AdventMod\Textures\seeker_infantry_filled.tga`, `System\AdventNative.exp/.lib` (git-ignored).

**.gitignore**: `AdventMod\.gitignore` has `obj/`, `System/*.exp`, `System/*.lib`; the root `.gitignore`
has the screenshot, the `c*.tga` masks, the `.asm` dump, `terrain_detail_preview.png` and `sheet.py`.
Missing: nothing that would leak pixels by `git add -A` **except** `System\AdventMod.u` itself when it is
a -JiggleSkin build (git cannot tell; the rule has to be a habit: plain build before any commit that
touches `System\`). `System\AdventMod-graphics.u` is tracked and stale (2026-10-06).

**d3d8.dll provenance**: the fork is `github.com/indieindie7/d3d8to9`, branch `gi-cascades` (worktree
`Documents\github\d3d8to9-gi`, HEAD c04da3a 2026-10-09). `package.py`'s docstring and README.txt say
gi-cascades; **`Licenses\CREDITS.txt` still says branch `advent-post`** (fix the line). The dll compiles
in Dear ImGui (the GM panel / sketch code, 9 "ImGui" strings in every build) and `stb_image_write.h`
(sketch PNG writer; its name string is not in the binary but the code is linked). Both need their
licence texts in `Licenses\` (section 5).

## 3. Docs audit

README.txt (2.1) described only shadows, post, terrain, GI, the 2.1 gore and the **old** options layout
(Options > Video > More Display Options), which the menu hub replaced before 2.1 shipped. Undocumented
until this audit: the Options hub (Gameplay/Camera/Audio/Screen/Graphics/Quality/Accessibility/Controls),
the Gameplay page, raw mouse look and exploring speed, the energy blade, wall holes and breaches, the
2026-10-08 blood work (wall runs, streaks, goo, drops, footprints, hands, lens, drying), the graphics
pass (fog, soft particles, terrain detail, sheen, skin/SSS, ambient occlusion), the AI (minds, hound
packs, wall-kicks, needs), bodies (lean, Seeker arms, hound snarl, vault/slam/barge, jiggle), foot IK,
armour plates and armour hits, death animations, and every new config section. NEXUS.md still carried
the 2.0 BBCode.

Done in this audit: README.txt rewritten in place (same voice, same anchors `package.py` cuts on: the
title line, "  Gore (new in 2.1)" ... "  Fixes", the KarmaData lines, "Easy way:"/"Manual way:", the
uninstall sentences; the gameplay sections sit inside the Gore...Fixes range so `--graphics` drops them,
the graphics-pass section sits before it so the graphics edition keeps it), with a KNOWN LIMITS section
and a CHANGES section; NEXUS.md's description rewritten for the next release. The version line in the
README is still "2.1" because `package.py --graphics` keys on it: bump `VER`, the README title, the two
"(new in 2.1)" anchors and NEXUS.md together. **Proposed version: 3.0** (new AI, bodies and combat
systems, not a 2.x polish). The installer's "Done!" sentence ("Options > Video > More Display Options >
Graphics") is wrong since the hub; the .bat is outside this audit's files: one line to change.

## 4. The play-test (what "done" needs), and the known limits to state

The user plays the installed build (the -JiggleSkin build, everything on except foot IK). To call it
finished they must have seen, in normal play, each of these working and not jarring:

1. **Hound packs** (any hound encounter: level03sectionb/c/d, level06sectionb): hounds hold off in front,
   go round the sides, one leaps at a time; not all three charging at once. Off switch `bHoundPack`.
2. **Wall-kicks**: at least one hound leap-to-wall-and-off seen; no hound stuck on a wall or in the air.
3. **Needs**: a hound stopping to feed on a dead mate in a lull; a marine walking toward a noise.
4. **Minds in general**: enemies taking cover, falling back, flanking; nobody frozen, oscillating or
   walking into walls; the aim-fairness beat (first shot comes after ~0.6 s) not making fights trivial.
5. **Seeker jiggle** (`bJiggle`): the belly/chest/throat/arms lag and settle on walking and hits, the arm
   guards do not deform, no stretched flesh; amplitude feels right (knobs Gain, ModJiggleBones MaxDeg).
   Also the plain skin (without `-JiggleSkin`) looks acceptable on the swapped mesh.
6. **Armour**: the steel plates on Seekers (helmet, chest, shoulders, thighs) read as armour, dent and
   fly off; sparks (no blood) on a hit to a guard, blood elsewhere; no "pink sheen". `bArmor`,
   `bArmourSparks`.
7. **Foot IK** (play one level with `[AdventMod.ModFeet] bFootIK=True`): feet on stairs and step edges,
   no knee pops, no foot through the floor, Gideon's crouch unaffected; the body dip when running on
   stairs is bearable.
8. **Gore of 2026-10-08** (any firefight): wall runs, streaks down bodies, goo strings on gibs, drops
   from ledges and ceilings, bloody footprints, blood on Gideon's hands and gun, lens drops; drying over
   a few minutes; no hitches (perf lines in U2Shaders.log: 0-1 frames over 50 ms per 30 s).
9. **Death animations**: with `bDeathAnims=True` bodies die with the clip for the hit zone, then lie
   still; no body standing up, no crash at a scripted death (the level03sectionb explosion room).
10. **Bodies**: Gideon leans into turns, vaults waist-high cover at a run, slams a wall on a dodge; Seeker
    arms rise in anger; hounds snarl and stand level on slopes.
11. **Graphics pass**: fog on the crash level reads as haze (not grey wash), soft smoke edges, ground
    grit up close, sheen on the station's metal, skin on faces; GI/AO rows on the Graphics page work.
12. **Stability**: a full chapter without a crash; save and load mid-fight; a level change mid-gore; a
    cutscene with blood about; quit and restart keep the settings.
13. **Menus**: every hub page opens from the title and the pause menu, the resolution prompt works,
    Reset on a page does not kill the mod's lines (the installer patches Defaults\ too).
14. **Soak** (optional, harness): a 10-15 minute automated fight: caps hold, no slowdown, memory steady.

Known limits to state honestly (now in README.txt "KNOWN LIMITS"): wall-kicks are rare mid-room;
jiggle amplitudes are hand-set; foot tilt to slopes is missing and foot IK is new and off; the filled
Seeker skin is a local experiment that never ships; hound ragdolls are off (they crash), hounds use
hand-keyed clips; light shafts were never verified; exclusive fullscreen, the GOG build and AMD/Intel
GPUs are unverified; the pack and needs systems were measured in A/B runs, not tuned by eye; the
armour hit test without the data files uses a per-bone table; cutscenes, vehicles and the first-person
camera were not tried with foot IK.

## 5. Licence check

| piece | where it is | licence | in Licenses\ ? |
|---|---|---|---|
| d3d8to9 (crosire / Patrick Mours) | d3d8.dll | BSD 2-clause | yes: d3d8to9-LICENSE.md |
| SMAA (Jimenez et al.) | SMAA.hlsl, AreaTexDX9.dds, SearchTex.dds, smaa_passes.hlsl | MIT | yes: SMAA-LICENSE.txt |
| AMD FidelityFX CAS | post_final.hlsl (ported) | MIT | credited in CREDITS.txt; no separate text (MIT asks for the notice: the header in post_final.hlsl carries it; add the MIT text to be clean) |
| Khronos PBR Neutral (shoulder) | post_final.hlsl | Apache-2.0 | credited; no text (Apache asks for the licence to accompany: add a copy) |
| Inigo Quilez: texture repetition, better fog | terrain_src/terrain3/4.hlsl, atmos.hlsl (fog integral) | CC BY-NC-SA 3.0 | credited; atmos.hlsl not listed in CREDITS (add) |
| Jimenez 2014 bloom (technique) | post_down/up.hlsl | technique, credited | n/a |
| Mikkelsen 2022 hex-tiling (technique) | terrain_src.hlsl | technique | not credited: add a line |
| McGuire/Mara/Luebke SAO (technique, own code) | ssao.hlsl | technique | add a line |
| Jimenez et al. Separable SSS (technique, own kernel) | sss.hlsl | technique | add a line |
| Radiance cascades (Sannikov) | gi.hlsl | technique | add a line |
| Valve lightwarp / Penner pre-integrated skin (technique) | char_skin.hlsl | technique | optional |
| UnityPCSS (Lucas Norr) | pcss_proj.hlsl ("method after ... as implemented in UnityPCSS, MIT") | MIT | yes (2026-10-09): UnityPCSS-LICENSE.txt + CREDITS line |
| Dear ImGui (Omar Cornut) | compiled into d3d8.dll (fork source/imgui) | MIT | yes (2026-10-09): DearImGui-LICENSE.txt, copied from the fork |
| stb_image_write (Sean Barrett) | compiled into d3d8.dll (fork source/stb_image_write.h) | public domain / MIT (dual) | yes (2026-10-09): stb_image_write-LICENSE.txt, the header's block |
| Jolt | not used | | n/a |
| MinHook / Zydis / SafetyHook | not used (AdventNative.dll is plain C with windows.h) | | n/a |
| Kimodo (NVIDIA) generated clips | Anims\*.json → ModDeaths.psa, blade takes | the clips are outputs; Kimodo code Apache-2.0, models "NVIDIA Open Model" | the mod ships motion data, not the model: a credit line ("death clips generated with NVIDIA Kimodo, hand-keyed blade and hound clips") would be honest; check the Open Model licence's output clause before the Nexus upload |
| Advent Rising assets | gib meshes, jiggle mesh, armour data: geometry derived from the game's models; no texture pixels shipped (see blocker 4 for the one derived map) | GlyphX/Majesco | CREDITS says "No game files are included": true for files; say "no game textures" and note the derived meshes |
| AdventMod itself | | GPL-3.0, non-commercial | yes: GPL-3.0.txt, CREDITS.txt (branch name fixed to gi-cascades 2026-10-09) |

## 6. What this audit changed

- `RELEASE.md` (this file).
- `README.txt`: new sections (options hub, gameplay, blade, blood of 2026-10-08, graphics pass, AI,
  bodies, foot IK, armour, death animations), GOOD TO KNOW keys for every new section, KNOWN LIMITS,
  CHANGES; `package.py` anchors kept (checked by index lookup, no zip built).
- `NEXUS.md`: the page draft for the next release (title, summary, BBCode description, file list).
- No class, native file, ini, .bat, package.py or build.ps1 edit. Nothing built, installed or run.
