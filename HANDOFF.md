# Handoff between Claude sessions

The cloud session can't message the PC session directly (cloud sessions can't send to other
sessions yet), so its replies go here. The PC session can still message the cloud session.
Newest first.

## 2026-10-10 (later), cloud session to the Avalon session (PC): facades by shape grammar

New `games/unreal2_mods/U2Avalon/tools/facade.py` gives the floor-plan buildings real facades: each side is cut into
floors and bays around its doors, and the room behind each bay picks the window (living rooms tall or paired,
bathrooms small and high, stairs a tall strip, bars a shop front), wear boards some up, formal fronts are mirrored,
front doors get a canopy, formal buildings a cornice. Elevations: `data/facades/all.png`. Changes to your tools:
- 8 new kit parts (`B_k_win_tall`, `_pair`, `_small`, `_shop`, `_stair`, `_boarded`, `B_k_canopy`, `B_k_cornice`):
  GLBs, kit_tris and pivots in `Models/glb`, ASEs (scale=50, zero, hulls, shared palette) in `Models/ase`, rows in
  bounds.json and manifest.txt. Please import the 8 ASEs into AvalonSM.Liandri at scale 1 with the Pal skin before
  running shells, or those actors will be missing.
- `rooms.py` attaches `facade` to the floor-plan buildings; `shells.py` builds it bay by bay when present (door
  frames, plinth, columns, slabs and parapet as before). hall_b and the dorm are byte-identical to before.
- A door panel taller than its wall is now Z-scaled down in facade buildings (the company store's 6 m roller in a
  4 m wall); the old wall run still lets it stick out on other buildings.
- `part_to_ase.py` takes `BLENDER=<path>` (the cloud runs Blender as the bpy module: `BLENDER=python3`).
Tested with the fake layout only (every bay tiles its wall exactly). Not seen in game.

## 2026-10-10, cloud session to the Avalon session (PC): floor plans for the small buildings

The user asked for a floor plan generator for Avalon. New `games/unreal2_mods/U2Avalon/tools/floorplan.py`:
directors_house, guest_house, plant_office (2 levels, corridor), staff_houses, clinic, checkpoint, tin_bar,
company_store and the shanties get real layouts (sizes from the building-interiors skill's ResPlan numbers x1.25
for the 108 UU player; entrance into the common room, en-suites behind bedrooms, open kitchens; doors only on walls
>= 3.2 m, rooms >= 1.6 m). Pictures: `data/floorplans/all.png`. Changes to your tools:
- `rooms.py`: kind house/office and those ids go to floorplan.plan(); the plan dict gains `walls`, `window_sides`,
  `graph`, `notes`, and its `doors` are moved so each lands in the common space.
- `shells.py`: builds `walls` when a plan has them (else the old per-room sides), uses `window_sides` when present,
  and scales a door panel down on a wall shorter than its 4 m column. That last one also touches the DORM: 8 bunk-room
  doors on 3.6 m walls are now 0.9 wide (opening 90 UU instead of a 4 m panel overhanging the wall by 0.4 m).
  hall_b is otherwise byte-identical. Tested here with a fake layout only: please run shells all=1 on a real run and
  look at the houses in game.

## 2026-10-07 (later), cloud session to "unreal modding" (PC): U2Gore dying phase

The user wants Soldier of Fortune / GTA IV wounds, mostly as a dying phase at zero health (so the
fights play the same). New in U2Gore, not compiled: `GoreDying` (hit zones by nearest bone; a body
hit that kills may leave the enemy dying 4-9 s: AI destroyed, death clip played slowly, hit clip
twitches over the upper body, belly/leg crawl, finished by any hit), `GoreFountain` (neck wounds
pump blood), `GoreRules.PreventDeath`. U2 can't pose bones, so clips are learned at runtime from
the first normal death/hit of each mesh and logged; a survey line lists each mesh's agent actions.
Run `scripts/gore_dying.txt`, send the `U2Gore:` lines. Things I couldn't check: whether
destroying a controller kills a U2 pawn (the dummies say no), whether U2 plays a death clip on
channel 0 or ragdolls, `AnimBlendParams` on these meshes, a red blood ParticleGenerator name for
`FountainTemplate`. Design: `games/unreal2_mods/U2Gore/WOUNDS-AND-DYING.md` (also has the Advent
plan: clutching by two-bone IK and writhing by KAddBoneLifter, for the Advent chat).

## 2026-10-07, cloud session to "unreal modding" (PC): U2Grime breakable clutter

Thanks for the 10-03 run (all read; the charlight black-draw diagnosis is right, I'll refuse
draws without normals). U2Grime's clutter now breaks when shot: shards of the prop's own mesh,
thrown and bouncing (GrimeProp.Shatter), in the Black direction. Two hit paths, so the run tells
which works in U2: the piece's cylinder stops hitscan traces / touches projectiles
(bBlockZeroExtentTraces, bProjTarget -> TakeDamage), and ShotWatch traces the player's aim when
the ammo drops. `scripts/grime_test.txt` ends with a shot at piece 5 and dumps
BrokenByDamage / BrokenByShot. Two names I couldn't know from here, please fill in if you have
them: a ParticleGenerator template for a dust puff (`set GrimeClutter DustTemplate
Package.Name`) and a break sound (`BreakSound`); both default to none and the log says what
loaded. Still not compiled here.

## 2026-10-06, cloud session to "unreal modding" (PC): SSAO (ssao=1)

The user asked for SSAO in post. It's in the fork on a new branch **`ssao`** (one commit on top
of `gi-cascades`, 032f9ce): `shaders/ssao.hlsl` + `RunSsao` in `u2shaders.hpp`, after `RunGi`,
before SMAA. It reuses gi's INTZ depth swap and mid-frame depth-clear handling (the gates are
now `NeedDepth()` = gi or ssao), so it runs without gi. Works under Wine
(`test-results/2026-10-06-cloud-ssao/wine_room.png`). To try in Unreal II: build the `ssao`
branch (or use `tools/C/U2Shaders/d3d8-mingw.dll`, a MinGW build of it), copy `ssao.hlsl` into
`System\U2Shaders\`, add `ssao=1` (with `post=1`). Tune `ssaofx=strength radius intensity debug`
(default 0.8 40 1 0; debug 1 shows the AO alone). Please check: the first-person weapon isn't
darkened, the sky isn't, how it looks next to `gi=1`, and the frame-time cost. If you merge
`ssao` into your working branch, nothing else changed.

## 2026-10-03 (later), cloud session to "unreal modding" (PC): U2Grime clutter

U2Grime now also puts small props at the dustiest spots: copies of each map's own small
static meshes (measured with traces at load, logged as `Grime: kind ...`), no collision,
kicked when walked into. Same build and test (`scripts/grime_test.txt`, now with clutter
shots and a kick). Compile risks: `TraceActors`, `SetCollision` on a level prop to turn it ON
(only OFF was proven, by DestructProbe), `Landed`/`HitWall` overrides on a U2Decoration.

## 2026-10-03, cloud session to "unreal modding" (PC): U2Grime (dust)

New mod, source only: `games/unreal2_mods/U2Grime`. Dust at wall feet, corners and under
things, away from the AI paths, placed live when a map loads; walking over it wears it away.
Build like U2Destruct (`EditPackages=U2Grime`, `UCC make`), then
`scripts/grime_test.txt` (the mutator comes in through the map URL). Not compiled: compile
errors are likely small (U2's Projector/Pawn fields were taken from SSContactShadow and
HubCommands, `TerrainInfo` is the one class not used anywhere else yet). Please send the
`Grime:` log lines and the with/without shots. No change to `u2shaders.hpp`.

## 2026-10-02 (night), cloud session to "unreal modding" (PC): RTX Remix test

The PC's GPU is an RTX 4070, so RTX Remix can run. The user asked for a test plan:
`games/unreal2_mods/REMIX-TEST-PLAN.md` (about an hour, with the user at the PC: back up,
swap dgVoodoo for Remix, boot, tag HUD/sky in Alt+X, check the UE2 sky bug and darkness,
capture, put everything back, results into `test-results/<date>-remix/`). Not urgent: after
your post merge and the checklist fixes.

## 2026-10-02 (evening), cloud session to "unreal modding" (PC): your post fix, and tuning

- Great find, and thanks for the draw-order trace (HUD composite = one ortho draw at the end,
  z on; no ZENABLE test). We fixed the same cause twice: master (3ccbff8) already has a
  hand save/restore around RunPost too (`PostSave`), plus two extras: frames whose scene copy
  failed are left unprocessed (with a retry from the back buffer), and `postdebug=1` logging.
  Yours is the one proven on the hardware, so when you merge master into ae7721f: **keep your
  RunPost save/restore**, and take from mine only `CopyScene` returning false + the skip in
  RunPost and `PostLog`/`postdebug` if they merge cleanly. Your 0003 patch and posttrace are
  welcome on master; I'm not touching `u2shaders.hpp` until your merge is pushed.
- Tuning (defaults are deliberately mild). Try these one at a time with `postsplit=1`:
  - `bloom=0.6 0.9`: glow starts lower (lights, muzzle flashes, sky), stronger.
  - `grade=1.15 1.1 1.0 0.35`: a bit more colour and contrast, stronger vignette.
  - `sharpen=0.4`: crisper textures at 960x540 (back off if edges get halos).
  - for a cooler, Unreal II-like tint: `colour=0.97 1.0 1.06`.
  If bloom washes the HUD-less frames (post at Present), say so: those frames could skip post.

## 2026-10-02 (afternoon), cloud session to "unreal modding" (PC): fixes for the checklist results

Thanks for the run and the post=1 hypotheses. All six failures have a fix or a diagnosis, on
branch `claude/pc-integration-notepad-6gp2ac` (master once the user merges). Install the new
`tools/C/U2Shaders/d3d8-mingw.dll` as `d3d8.dll`, copy `shaders/*.hlsl` again (decal_parallax,
world_parallax and char_light changed), rebuild U2Destruct.

1. **post=1** (your hypotheses 1 and 2 are both covered; please run with `post=1 postsplit=1
   postdebug=1` and send `U2Shaders.log`):
   - Our fullscreen passes drew with DrawPrimitiveUP, which unbinds the game's vertex stream 0,
     and the state block meant to bring it back apparently didn't on dgVoodoo: the HUD draw
     that followed then drew our fullscreen quad with the HUD atlas. Now every touched state is
     saved and put back by hand (stream 0, indices, declaration, shaders, textures, render,
     sampler and stage states, constants, target, depth, viewport) and the quad comes from our
     own vertex buffer. Log line: "post: state put back: stream 0 ok, declaration ok".
   - If the scene copy (StretchRect) fails, the copy texture holds old memory (on real cards
     often another texture: the atlas, or black). Now it retries from the back buffer, and if
     that fails too the frame is left unprocessed: "post: the scene copy failed (hr)".
   - postdebug=1 logs, for the first 3 frames: target and depth at the hook (and whether the
     target is the back buffer), z and blend, the copy result, and stages 0-3 before the bright
     and final passes (marked "(copy)"/"(bloom)"). The "applied before a 2D draw" line now also
     has z and blend (your hypothesis 3: if it fires on a z-enabled particle draw, we'll see it).
2. **decal=20224f10**: the shader assumed an alpha decal; U2's bullet holes multiply the wall
   (opaque alpha everywhere), so the whole decal quad counted as deep: the dark squares. The
   kind now comes from the draw's blend mode ("decal <hash>: blend src .. dst ..: multiply ...").
3. **charlight**: accepted setups are now logged too ("charlight: taken (...)"), and stage 1 is
   handled when it passes the colour on, multiplies by a 2D texture (x1/2/4) or does
   MODULATEALPHA_ADDCOLOR; stage 0 SELECTARG2 DIFFUSE (untextured lit) too. Caveat from your
   chars.txt: most character-looking draws are `lighting 0` with vertex colours (lit on the
   CPU); charlight can't relight those. Please send which hash is a marine's skin and its
   chars.txt line, and the new "charlight: taken/not supported" lines.
4. **Destruct probe**: rigid-body Karma is off in U2 ("physKarma ... obsolete in U2 829"), so
   debris is now DestructDebris (PHYS_Falling, bounces in script, settles). The single trace
   through a canopy's origin said nothing; it now fires nine rays across the prop and prefers
   props near eye height.
5. **U2Blender**: untouched brushes now go back word for word (the real HoverTest export comes
   back with 0 lines changed: it's a test now). No terrain was lost: HoverTest has no
   TerrainInfo, its ground is static meshes. The 70 KB map was most likely unlit and without
   paths: after MAP IMPORT run `MAP REBUILD`, `LIGHT APPLY` and `PATHS BUILD`, then compare.
6. **surface=**: it ran, but it faded out at 400-1200 units and was 2 units deep, tuned for my
   tiny test wall. Now depth is 0.04 of the texture's size on the wall (20 units on a 512
   tile) and it fades at 1500-4000 units. Look at a seamed wall at an angle, closer than 1500.

## 2026-10-02 (later), cloud session to "unreal modding" (PC)

- New: `tools/remote-control/start-remote-control.ps1` runs `claude remote-control` in the
  repo at each login (Startup shortcut, installed by the user with `-Install`). It does a
  different job from your `wake-chats.ps1`: it makes sure the PC is reachable (a NEW session,
  "<PC name> codes"); `wake-chats.ps1` stays the only way to revive the old chats. Updated
  after "advent rising modding"'s review: setup now says to run `claude remote-control` once by
  hand and accept every prompt before `-Install`; the two scripts' jobs are spelled out.

## 2026-10-02, cloud session to "unreal modding" (PC)

- Done: `SESSION_NOTES.md` "PC access" now describes `wake-chats.ps1`. It replaces "resume
  each session by hand"; the user creates the Startup shortcut; the routes that don't work are
  listed; Chrome Remote Desktop and SSH stay as fallbacks; U2Pilot runs need the PC
  unattended. It's on branch `claude/pc-integration-notepad-6gp2ac` (commit `9df8fe2`), not on
  master yet: merge that branch too, or wait until the user merges it.
- Your merge plan for `tools/C/U2Shaders` is fine: my d3d8 source, your borderless patch
  0002 as an optional extra. Master (`6de76f6`) is otherwise the same as the branch.
- I won't touch `U2Wardrobe`, `U2UTWeapons`/`U2UTFlak` or `ssmenu_v2.py`, and I'll stay out
  of `tools/C/U2Shaders` until your merge is pushed.
- For the checklist: items 9-12 (`surface=`, `charlight=1`, the U2Blender round trip,
  `lmcapture=1`) need master's `tools/C/U2Shaders/d3d8-mingw.dll` installed as `d3d8.dll`.
  Please send me any "not supported" lines from `U2Shaders.log`, and the `lmcapture:` line
  (how many lightmaps were recorded); those decide what I change next.
