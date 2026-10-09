# Flesh jiggle on the Seekers (2026-10-09: A + C built, run in game the same day; B below)

Secondary motion for the Seeker infantry's flesh: the belly, chest, hump, throat, the four upper
arms and the two thighs lag and overshoot the body's own motion and swing away from hits. The
armour never does: **the plates only move from the bone relation** (the user's rule). Built on the
per-triangle armour flags of ARMOUR.md and the bone-director hook of FEET.md.

## The rule and its assert

The stock mesh's triangles are flagged armour/flesh by the game's own chrome mask
(`<game>\AdventMod\Armour\seekerinfantry.amesh`: 3135 triangles, 112 armour, the guards on the
left arm). Every point of an armour triangle (130 points) keeps exactly its stock weights; only
flesh points get weight on the new bones, and `tools/jiggle_rig.py` refuses to write the mesh if
any armour point carries any jiggle weight (`AssertionError`; the report line "Armour assert: 0
armour points with jiggle weight"). The jiggle weight is taken from the parent bone's own share
(never from another bone) and the new bones sit at their parents' joints with no rotation, so the
rest pose and every clip are byte-for-byte what they were until a jiggle bone turns.

## A. Mesh, rig, reference (done, CPU)

Files outside the repo (game-derived): `Documents\AdventRising_meshes\jiggle\`.

1. **Clips.** `tools/ukx_anim.py` reads the game's MeshAnimation objects (build 2226's own
   layout, documented in the tool: 12-byte RefBones, one key bulk, per-sequence chunks with a
   per-bone format table, a size table, then the sequences; rotation keys are 3 x uint16 with w
   implied, times are uint16 frame numbers, static bones 3+3 floats; the quats are kept in ActorX
   form, children conjugated: posed that way the feet land on the floor at y 0, the head at -82;
   the plain form puts the feet at -130). Exported: `Walk_F` (41 f), `Run` (18), `Idle_Active`
   (103) from `Seekers.Base`, `A_Punch_R` (41, 28 fps) from `Targeting`, `R_Front` (23, 35 fps)
   and `R_Back` (28) from `REACTIONS`, as .psa + JSON.
2. **Rig.** `tools/jiggle_rig.py build`: ten leaf bones, pivot at the parent's joint, lever = the
   region's centre in the parent's frame; weight = 0.6 x smoothstep(1 - distance/radius), capped
   by the parent's share, at most 4 influences per point (none had to be skipped):

   | bone | parent | points | mean / max weight | lever (units) |
   |---|---|---|---|---|
   | J_Belly | spine1 | 19 | 0.19 / 0.52 | 21 |
   | J_Chest | spine2 | 24 | 0.25 / 0.49 | 19 |
   | J_Hump | spine2 | 27 | 0.27 / 0.55 | 13 |
   | J_Throat | Neck02 | 22 | 0.09 / 0.14 | 9 |
   | J_ArmR | rightArm | 34 | 0.24 / 0.52 | 26 |
   | J_ArmL | leftArm | 74 (55 armour points skipped) | 0.39 / 0.59 | 16 |
   | J_FrontArmR | RightFrontArm | 16 | 0.19 / 0.41 | 21 |
   | J_FrontArmL | LeftFrontArm | 10 | 0.06 / 0.14 | 18 |
   | J_ThighR | rightUpLeg | 34 | 0.19 / 0.40 | 28 |
   | J_ThighL | leftUpLeg | 31 | 0.21 / 0.37 | 29 |

   88 bones, 3056 weight records (was 2772). The "front arms" are the knuckle-walking pair (their
   hands are `*FrontFoot`); the back pair (`rightArm`/`leftArm`) holds the gun. The throat and the
   front arms' regions are thin; their weights are small.
3. **Stripped mesh.** `tools/jiggle_strip.py` (Blender headless): the 112 armour faces deleted, 60
   plate-only points dropped, the 141 boundary edges filled (101 faces, split once and relaxed), the
   fill's UVs from the flesh ring; `seekerinfantry_stripped.psk/.blend`, `stripped_render.png` (the
   left arm's guard gone, a flat ribbon where the gauntlet was: the arm under it was never
   modelled) and **`plate_mask.png`** (512x512, the plate UV islands dilated 6 texels: 39 338
   texels, 15 %) for phase B.
4. **Reference sim.** `tools/jiggle_sim.py` (Blender soft body, goal-driven: the mesh skinned by the
   clip is the goal, armour and non-region points pinned at goal 1, region points down to 0.5 at
   the centre, gravity, 20-frame pre-roll, looping clips run twice). Region points lag the clip by
   0.7 (idle) / 1.9 (walk) / 4.7 (run) / 4.8-5.2 (hit reactions) / 6.4 (punch) units on average;
   the weighted centroid of a region by 0.3-1 unit in walk/idle and 3-30 in the punch (the clip
   whips 2 m forward in 1.4 s).
   `tools/jiggle_fit.py`: per frame, the turn of each bone about its joint that moves the lever's
   tip by the region's centroid lag (clamped 35 deg); then one damped spring per bone,
   theta'' = gain (c x -a)/|c|^2 - k theta - d theta', fitted over all six clips (Nelder-Mead,
   12 starts). **Verdict: the springs are not identified.** For nearly every bone and clip the fit's
   error equals the signal (e.g. J_ArmR Run 10.1/9.6 deg, J_Belly R_Back 15.8/15.7; full table in
   `fit_report.md`), the optimiser drives gains to 0 and k from 2 to 2800: the soft body's lag is
   not a second-order response to the centre's acceleration at 30 fps (18-41 frames, the hit clips
   start mid-impulse, the punch's accelerations are spikes). What the reference does give: the
   **amplitude per bone** (95th percentile angle 11-26 deg; lever-tip RMS 2-7 units in run and
   hits, 0.2-1 in idle/walk) and the share between bones. The live springs are therefore set by
   hand at a flesh-like 3.5 Hz (k 484), damping ratio 0.3 (d 13.2), gain 0.25 x the bone's share of
   the reference motion (0.14 throat .. 0.35 right arm), max amplitude 1.3 x the reference's 95th
   percentile (14-30 deg); `tools/make_jiggle_uc.py` writes them (and the raw fit, for the record)
   into `Classes/ModJiggleBones.uc`. `<clip>_jiggle.psa` (88 bones, the clip plus the fitted jiggle
   tracks) are in the jiggle folder for a look in Blender.
5. **Import path (decides C): the game CAN take a psk with added bones at build time.**
   `Editor.dll` carries `MESH MODELIMPORT MESH= MODELFILE= ... LODSTYLE=` (and `MESH ORIGIN`,
   `DEFAULTANIM`); AdventUCC runs the Editor commandlets (the .psa import already works this way,
   ModDeathAnims). `Classes/ModJiggleMesh.uc` imports `Meshes\seekerinfantry_jiggle.psk` as
   `AdventMod.SeekerInfantryJ` with the stock origin (0 -89 0) and rotation (yaw -64, roll 64,
   read from seekers.ukx). The game's clips have no track for the J_ bones, so they stay at the
   reference pose (identity at the parent's joint) until the DLL turns them. **Verified offline
   (build.ps1, 0 errors, the game closed)**: `AdventMod.u` carries `SkeletalMesh SeekerInfantryJ`
   (463 KB) and, read back with tools/ukx_mesh.py against the stock data: 1645 points at the same
   positions (the importer reorders them), 88 bones with the same names, parents, positions and
   rotations, 3135 faces with the same winding, 2080 wedges with the stock UVs, 3056 weights (the
   importer renormalises: differences of 1e-4), scale 1, the stock bounding box and origin, and
   **0 armour points with jiggle weight in the game's own copy** (130 armour points, as in the
   rig). Two importer facts cost a round: MODELIMPORT negates Y and reverses every triangle (the
   first import came out mirrored), so jiggle_rig.py writes a pre-flipped
   `seekerinfantry_jiggle_import.psk` for the build; and without `MESHMAP SCALE` the mesh came
   out with scale 0 and a zero box (now set from the stock). The material slot stays None (the
   psk's material name doesn't resolve at compile time): ModJiggle puts the Seeker's own skin on
   `Skins[0]`. `tools/make_armour_data.py` builds `SeekerInfantryJ.amesh` too (the stock-space
   psk is copied beside the game meshes by build.ps1), so ARMOUR.md's per-triangle test keeps
   working on the re-linked pawns.
   The live route therefore adds bones through the mesh, not at run time: `Actor.Mesh` is const
   (the class default can't be assigned: "Can't assign Const variables"), so ModJiggle re-links
   every Seeker infantry within range once (`LinkMesh(JiggleMesh, bKeepAnim)`, the three animation
   sets and `ambient` linked again, the skin `seekercharacters_tx.Main.infantry_hsh` on `Skins[0]`)
   and only hooks pawns whose mesh is the jiggle mesh. LinkMesh on a live pawn is the untested
   step (the movement channels may need the pawn's animation re-initialised: test 2 watches for a
   Seeker that stops animating). Fallback if the import or the relink fails in game: none of the existing Seeker
   bones is flesh-only in the sense needed (spine1/spine2/neck/thighs carry the whole limb, so a
   spring on them would move the armour with the bone relation: allowed by the letter of the rule
   but a body lean, not jiggle); the fallback would be springs on spine1/Neck02/the thighs with
   small amplitudes, to be built only if needed.

## B. Texture: done once, judged bad (2026-10-09)

The Seeker skin (`seekercharacters_tx` -> `seeker_infantry`, 512x512, exported with tools/utx_tex.py
into `Documents\AdventRising_meshes\jiggle	ex\`, never git) went through FLUX Kontext
(`Documents\Toolslux-kontext\kontext_edit.py`, the sana venv in Downloads\sana-diffusers;
"replace the grey metal armour plates and the gauntlet pieces with the same purple-grey alien
skin ... keep everything else", 512x512, 28 steps, guidance 2.5, seed 7). It took 80 minutes:
the GPU was shared with another chat's two llama-servers (9-11 GB), and a duplicate process
from a mangled taskkill loaded a second copy for a while. The raw edit was then composited over
the stock skin inside `plate_mask.png` only (feathered 2 px; Kontext has no mask input):
`tex\seeker_infantry_skinned.png`, sheet `skin_sheet.png` (stock | raw | composite).

**Verdict: bad.** Kontext recoloured the whole sheet a flat lavender (mean change 97/255 outside
the mask too) and kept the plates as plates (panel lines, rivets, the gun pieces), so inside the
mask the result is flat purple patches with metal detail, nothing like the blue mottled skin
beside them. A UV atlas isn't a picture Kontext understands; what would work is a real
mask-inpainting model, or painting the islands by hand from the neighbouring skin texels (clone
from the mask's ring, which a 30-line numpy pass could do: a patch-match fill of the islands from
the flesh ring). Not retried (the GPU was handed back).

How it would go into the game, if a good one existed: the regenerated 512x512 PNG -> .tga in
`<game>\AdventMod\Textures` (outside the repo, like the gib parts), `#exec TEXTURE IMPORT
NAME=SeekerSkinJ FILE=Textures\seeker_infantry_skinned.tga` in ModJiggleMesh, and ModJiggle puts
that texture (or a Shader wrapping it) on the re-linked pawn's `Skins[0]` instead of the stock
material. Game pixels: never shipped, never committed; the stock skin is what the jiggle mesh
wears now.

## C. Live springs (built, CPU; game test waits)

- `native/jiggle.c`: `JiggleConfig <gain> <log> <max accel>`, `JiggleBone <name> <k> <d> <gain>
  <max deg> <lever xyz>`, `Jiggle <pawn> <class> <n> <bone index...>`, `JiggleOff`, `JiggleHit <pawn>
  <class> <dir xyz> <strength>`. Per hooked bone a director (Space 99) + world-spacer callback as
  footik.c; in the callback: the region centre's world position (parent joint + lever, through
  MeshToWorld) finite-differenced to an acceleration (clamped to MaxAccel, history reset on a dt
  over 0.1 s), into the parent's frame, the pendulum drive, a hit's angular impulse, semi-implicit
  Euler with up to 16 substeps, the amplitude clamp (no velocity outward past it), and the bone's
  axes returned as R_parent x exp(theta). Refuses any bone that isn't a `J_` leaf (NumChildren 0),
  so EonEngine's spine/Hips/aim bones can never be hooked. Compiles with 0 warnings.
- `Classes/ModJiggle.uc` (spawned by ModMoves): the mesh swap, the parameter lines, the 0.5-s
  sweep (hook within Range, release when dead/ragdoll/out of range), `Hit()` from ModReact.Flinch.
- Config `[AdventMod.ModJiggle]`:

  | key | default | |
  |---|---|---|
  | bJiggle | True | on/off (on since the runs below) |
  | Gain | 1.0 | on every bone's drive |
  | StiffScale / DampScale | 1.0 / 1.0 | on every bone's k / d |
  | HitStrength | 2.0 | rad/s of swing per hit at 20 damage (x0.3..2 by damage) |
  | MaxAccel | 30000 | units/s^2 the driver is clamped to (a teleport never reads as a shove) |
  | Range | 3500 | AI within this of the player |
  | bRelink | True | Seeker infantry in range get LinkMesh to the jiggle mesh, once each |
  | OverK[i] / OverD[i] / OverGain[i] / OverMaxDeg[i] | 0 | per bone (the table's order), 0 = keep |
  | bJiggleLog | False | the DLL's 5-s lines: callbacks, us each, amplitude mean/max per bone |

## Test list (after the GPU go)

1. `build.ps1`: 0 errors (done, see A.5; the last build of the day failed on another session's
   in-progress ModMinds/ModNeeds edit, `ModMutator.uc(104): Unrecognized member 'Needs'`, not on
   this work: the previous AdventMod.u, with the jiggle mesh, is back in the game folder).
2. Hidden pilot run, level03sectionb or level14sectiond, `bJiggle=True bJiggleLog=True`, a spawned
   `SeekerInfantry` (the log's "relinked to the jiggle mesh" then "hooked <pawn> (10 bones)"; it
   must keep walking and animating after the relink), walking,
   running, hit by the pistol; `ShotP` pairs bJiggle off/on; expected log: "bone coords convention:
   rows are the rotation's rows", amplitudes mean 2-8 deg / max under the clamp while moving, ~0 at
   rest, a spike on a hit, 1-3 us per callback, 0 faults, no `exception` lines.
3. The armour rule in motion: the left arm's guard must not deform (its points have no J_ weight;
   a close ShotP of the arm while the body jiggles).
4. A 2-minute fight with Seekers: no crash, the AdventNative.log tail clean.
5. The skin: the swapped mesh must show the Seeker's own skin (Skins[0]); if the pawn is white or
   checkered the material resolution of MODELIMPORT is the cause.

## Reproduce (CPU)

    py -I tools/ukx_anim.py "<game>\animations\seekers.ukx" Base Documents\AdventRising_meshes\seekerinfantry.psk Documents\AdventRising_meshes\jiggle\clips Walk_F Run Idle_Active
    py -I tools/ukx_anim.py ... Targeting ... A_Punch_R ;  ... REACTIONS ... R_Front R_Back
    py -I tools/jiggle_rig.py build <seekerinfantry.psk> "<game>\AdventMod\Armour\seekerinfantry.amesh" <jiggle dir>
    py -I tools/jiggle_rig.py skin <seekerinfantry.psk> <jiggle dir>\regions.json <jiggle dir>\clips <jiggle dir>
    blender -b --python tools/jiggle_strip.py -- <seekerinfantry.psk> <...amesh> "<game>\AdventMod\Armour\seekerinfantry_mask.png" <jiggle dir>
    blender -b --python tools/jiggle_sim.py -- <jiggle dir>
    py -I tools/jiggle_fit.py <jiggle dir>
    py -I tools/make_jiggle_uc.py <jiggle dir>\jiggle_fit.json

Gotchas met: Blender 5's actions have no `fcurves` (set the keyframe interpolation preference
instead); a stiff soft body blows up to NaN on the explicit integrator (goal spring 0.5, 4-60
substeps, error 0.02 is stable); the .amesh bone record is 96 bytes; a per-vertex least-squares
turn goes wild on the few loose points of a violent clip (the centroid is the mass that jiggles).

## Results (2026-10-09, hidden runs on level14sectiond, build of master c07dd2b + the two fixes below)

Harness: `scratchpad\jiggle
un_jiggle_test.ps1` (`-On`, `-Fight`), on `test_run.ps1`. Four runs:
bJiggle off (baseline), on, on again after the first fix, and a 3-minute fight with three spawned
Seeker infantry (`-Fight`: 12 fire/capture cycles). The game ran to the end of every run; 0
`exception`, 0 `crash:` lines, 0 callback faults.

| what | result |
|---|---|
| relink | every Seeker infantry in range (4 placed `SeekerInfantry_PulseRifle*`/`SeekerInfantry4`, the spawned ones) logged "relinked to the jiggle mesh" then "hooked ... 10 bones, 88 posed"; they keep walking, aiming, firing and dying after the relink (fight run: 7 relinks, 32 hits) |
| skin | the relinked Seekers draw with their own skin (Skins[0]): no white or checkered body in any frame |
| convention | "bone coords convention: rows are the rotation's rows (0.00 vs 30.76)" on the first callback |
| cost | 0.8-0.9 us per callback, ~1170 callbacks/s per pawn (the pose is built twice a tick) |
| amplitudes, first on-run | every bone pegged at its clamp (means 15-25 deg) on moving Seekers: the pose build runs twice per tick, the second with a dt near 0, and the finite difference blew up to MaxAccel. **Fix**: a dt under 4 ms is the same frame again: no new motion, nothing integrated |
| amplitudes after the fix | standing/idle 0.1-0.9 deg mean (max 1-5); walking/fighting 4-9 deg mean, peaks at the clamp (14-30) on the throat, chest and arms; a hit adds a visible kick (J_ArmL 1.8/18.6 on SeekerInfantry3 after pistol hits) |
| hits | `jiggle: hit on <pawn>, strength 0.6..4.0` for every pistol (0.6) and heavier hit; ModReact.Flinch reaches the DLL |
| the spawned `SeekerInfantry1` | 0.0 all along in every run: hooked, posed (3000 callbacks / 5 s) but it never moves nor gets hit (the pilot's HURT found the nearer placed Seekers): the springs idle at 0 as they should |
| off/on frames | `jiggle_off_on_pairs.jpg`, `fight_sheet.jpg` (scratchpad): the bodies are intact in every frame, no stretched or detached flesh, the left arm's guard sits on the arm as before (structurally guaranteed: its points carry no J_ weight, verified on the game's copy of the mesh) |

bJiggle is therefore on by default. Not measured yet: how it reads in motion to the user (stills can't
show the 5-10 deg of lag); the Gain and the per-bone clamps are the knobs.
