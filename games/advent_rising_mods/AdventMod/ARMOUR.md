# Destructible armour (parked 2026-10-06, rebuilt 2026-10-07)

Wolfenstein-style plates on the Seeker soldiers. Built in three phases and verified in
game; switched off in the shipped mod (`bArmor=False` in `ModArmor`) after the user's
play-test: the exposed-flesh look read as a pink sheen rather than a broken plate. The
code stays (`ModArmor.uc`, `ModArmorTextures.uc`, `tools/make_armor_masks.py`, the
`Textures/armor_seekerinfantry_m*.tga` masks) for the rebuild described at the end.
`bArmor=True` in `[AdventMod.ModArmor]` of `AdventMod.ini` turns it back on as it was.

## What works (keep)

- **Damage model.** Six plates (head, torso, each arm, each leg) with points of their own.
  A hit on a held plate loses `Absorb` (0.7) of its damage to the plate; a broken region
  takes `ExposedBonus` (1.5x, head 2x). Explosions share `BlastShare` (0.4) over every
  plate and hurt the body in full. `ModGoreRules` feeds every hit through `Strike()`
  before the flinch and the blood, so they react to what got through.
- **Time to kill preserved** (`bPreserveTtk`). Plate points `P = a·H·(B−1)/(B−1+a)`
  make the damage to kill through a region from full health equal to the plain health
  `H` (absorb `a`, bonus `B`); region shares under 1 (limbs 0.6) give a lighter plate and
  a slightly faster kill, never a slower one. Verified by the formula and in play (the
  user's session log: 137 armour events, no complaints about sponginess).
- **Plates flying off (phase 2).** `Plate()` throws the region's own piece of the
  character mesh (the gib parts of `ModGibParts`) through `Gore.ThrowPart`, scaled
  `PlateScale` 0.9, in the body's skin, no blood, with `Chunks` small fragments; it
  stays `PlateStay` seconds. The body jerks and staggers. This looked right.
- **Region by bone.** `Region()` picks the plate of the bone nearest the hit;
  `LastBone` is kept for the plate throw.

## What didn't (the reason it is parked)

Phase 3, the flesh under a broken plate, was a texture trick: one `Combiner` stage over
the skin with a texture per set of broken plates (`Armor_seekerinfantry_m01..m15`), the
meat in its colour and the region in its alpha, serving as `Material2` and `Mask`
(`CO_AlphaBlend_With_Mask`, `AO_Use_Alpha_From_Material1`). Renderer lessons, all
verified in game:

- A combiner inside a combiner draws the whole skeletal mesh as a flat colour.
- A separate mask texture (white, or region colours) also draws a flat colour.
- The texture as its own mask works. Left and right limbs share texels on the Seeker, so
  a broken arm shows flesh on both arms.
- Ragged "torn" patches with darker meat (second attempt) still read as a pink/purple
  sheen on the armour in motion, not as a hole with flesh in it. The Seeker's armour is
  painted into its one skin, so nothing can look "under" it.

## The rebuild (when picked up again)

Make the plates real objects on top of the body instead of a repaint of the body:

1. **Plate actors on bones.** For each single-bone region (helmet, chest, shoulders,
   thighs) attach the region's gib part as its own actor (`AttachToBone`), scaled up a
   few percent so it sits over the body, with our own metal material (not the game's
   skin). Forearms and shins bend across two bones and would animate wrong as rigid
   pieces: leave them bare, or split the parts per bone in GibSplit first.
2. **Breaking = detaching.** On a break the attached plate becomes the thrown piece
   (`Plate()` already does the throw), and the untouched normal Seeker is what shows
   underneath. No combiner, no masks, no flesh texture.
3. **Look.** Scratches and a cracked look on the plate material at low plate points
   (swap the material at 50 % and 20 %), sparks on plate hits, the break sound (parked
   earlier: the Gameplay page is full, so the toggle is ini-only).
4. **Drop** `ModArmorTextures`, the `m*` masks and `bExpose` once the plate actors are
   in; `make_armor_masks.py` stays useful for per-bone region cuts.

Estimated half a day. Gotchas to remember: no bool arrays in structs (byte); `Break` is a
reserved word (hence `Shatter`); locals are case-insensitive against parameters; a config
dynamic array is emptied by an ini section that lacks the key (`Armored` is therefore not
config); the pilot's `hurt N` arrives doubled; hits at or over `GibOverkill` gib the body.

## Rebuilt (2026-10-07): plates as their own actors

Done as planned above, and back on by default (`bArmor=True`, `bPlateActors=True`; the flesh
repaint `bExpose` and the gib-piece throw `bPlates` are off).

- **Meshes and textures are ours** (`tools/make_plates.py`): a chest plate (wrapped breastplate
  with a ridge and arm-hole cut), a helmet dome with a visor slot, shoulder pauldrons and thigh
  guards; light brushed steel with rim bevel, panel lines, rivets and scratches, and a dented,
  scorched variant. Both windings on every triangle.
- **ModArmorPlate** (one per region) is attached with `AttachToBone` to head, spine2,
  leftArm/rightArm and leftUpLeg/rightUpLeg. Placement is worked out once, when the character is
  first seen (ModArmor's Tick scans every 0.5 s): out of the body's front (shoulders: out to the
  side and a little up) by `WearOut` and up by `WearUp`, times the collision height, its +X facing
  out and +Z up; the world placement is turned into the bone's frame (`SetRelativeLocation`,
  `SetRelativeRotation` from `OrthoRotation` of the axes expressed in the bone's coords).
  `WearOut`, `WearUp`, `WearScale` are config (static arrays: `WearOut[1]=0.3` in
  `[AdventMod.ModArmor]`).
- **Damage look**: at half its points a plate swaps to the dented texture.
- **Break**: the worn plate is detached and a loose copy (ModRubble's fake physics, the plate's
  mesh, the dented texture) is thrown away from the shot; the body underneath is the untouched
  Seeker, so no pink.
- **Calibration lesson**: the Seekers are hunched and deep; offsets that look small (0.12 x height
  for the chest) leave the plate inside the body. Working values: chest 0.30, shoulders 0.20,
  thighs 0.25 out; sizes chest 0.50, shoulders 0.32, thighs 0.34, helmet 0.30 (x collision height).
- Verified in the harness: all six plates spawn on placed and spawned Seekers, the helmet and chest
  plate read clearly, breaks detach and throw, bare regions take the bonus. Not yet seen in motion
  by the user; the shoulders and thighs may still want tuning.

---

# Where the plates are (2026-10-09): armour or flesh, per hit, from the skin itself

The user's idea: use the enemies' texture layout ("sprite bounding") to know, for any hit,
whether it struck armour or flesh, so damage, gore (sparks against blood) and the AI
(presenting the plated side) can react per spot. Built offline on 2026-10-09; compiles (0
errors); the offline check passes; **run in the game the same day**: the test list and the
results are at the end.

## Inventory: what the enemies are made of

Every enemy mesh in Advent is **one material section** (one `HWSkinShader*` material, one
skin sheet), so there are no "armour sections" to read off the mesh; the only mesh with an armour
section of its own is the Aurelian `infantry` (`InfantryArmor_HSH`), an ally. The split therefore
comes from the texture, and the game itself says which parts are hard: the `HWSkinShader`
materials carry a **chrome mask** (`SpecularMaskMaterial`, the Red channel of the `*_rgb` /
`*_rg` texture; the skin shader is `out = lerp(v0*(t0 + t1*dot(t2,c1))..., ...)` with t1 the
chrome environment map and t2 the mask) that the renderer uses to put the metal reflection on
plates, guards and gear and not on skin or leather. A triangle whose UV triangle is mostly
chrome-masked (7-sample grid over the triangle, texel level 0.35, face level 0.5) is **armour**;
the rest is flesh (skin and the leather harness alike).

| mesh | pawn classes | material sections | faces | armour faces | armour surface | mask (Red) |
|---|---|---|---|---|---|---|
| seekerinfantry | SeekerInfantry | 1: infantry_hsh | 3135 | 112 | 8% | seekerelite_rgb (borrowed) |
| SeekerElite | SeekerElite | 1: eliteu_hsh | 3156 | 78 | 3% | seekerelite_rgb |
| SeekerCommander | SeekerCommander, SeekerRanhor | 1: comanderu_hsh | 3234 | 64 | 3% | seeker_commander_rgb |
| seekerpilot | SeekerPilot (+ _Brute) | 1: skrspace_hsh | 3673 | 259 | 4% | seekerspace_rg |
| SeekerScanner | SeekerScanner, SeekerClayPigeon | 1: seekerscanner_hsh | 2949 | 393 | 9% | seeker_scanner_rgb |
| seekerhound | SeekerDog | 1: seekerhound_hsh | 2212 | 0 | 0% | seekerhound_rg |
| seekershocktrooper | ShockTrooper | 1: shocktrooper_hsh | 2931 | 14 | 0% | shocktrooper_rg |
| kchell | SeekerKchell | 1: Ambassador_HSH | 3308 | 0 | 0% | ambassador_rgb |
| specops | SpecOpsSoldier | 1: specops_hsh | 3319 | 161 | 2% | specops_rg |

- The Seeker infantry's material (`seekerinfantry_hsh`) has **no mask** (its `Specular` slot
  is a flat white texture); its sheet shares the elite's UV islands (2856 of 3135 faces have the
  same UV triangle within a texel), so the elite's mask serves it.
- What counts as armour by the game's own mask is **small**: the pilot's helmet (head 43 %),
  forearm and gauntlet guards (infantry leftArm 47 %, leftForeArm 41 %; scanner leftForeArm
  71 %), knee guards, the spec-ops' vest bits. The Seeker body is skin and a leather harness,
  neither chrome-masked. The hound and the Kchell have none. The shock trooper's whole suit
  is a dark, low-chrome material: 14 faces. If the leather harness should count as a third
  class (thud, no blood), it would need a colour split of the diffuse per species; the
  per-triangle flag byte has room for it.
- Per-bone armour shares (area-weighted, by dominant bone) are in `ModArmourMap.uc` (numbers
  only); the full tables and the mask/face sheets are in the scratchpad
  (`scratchpad\armour\data\*_faces.png`, `*_mask.png`, `armour_faces_3d.png`).
- Masks: the derived 1-bit masks (armour faces rasterised in UV space, no texture pixels) and the
  per-triangle data are **generated at build time** into `<game>\AdventMod\Armour\<mesh>.amesh`
  by `tools/make_armour_data.py` (from `Documents\AdventRising_meshes\*.psk` and the game's
  `.utx`), like the gib parts; nothing from the game's textures or meshes is in the repo. The
  1-bit masks could be committed (no pixels), but they are regenerated anyway.
- Reading the `.utx`: `tools/utx_tex.py` (tagged properties with int32 name refs, UE2 info byte;
  a bool tag is `info size` with the value in bit 7; DXT1/3/5 mips through a DDS header; the
  `HWSkinShader*` material graph).

## The lookup: a ray against the skinned mesh (native), the bone table as the fallback

**Chosen: (a) native ray-vs-skinned-mesh**, `native/armour.c`, since every mesh is one section
and the engine only reports where a hit met the collision cylinder.

- Data: `.amesh` v1 = the reference skeleton (name, parent, local position, mesh-space
  rotation and origin), vertices with up to 4 weights, triangles with UVs, armour flag and
  section. The ref pose is composed from the psk with the root as-is and every child's
  quaternion conjugated (ActorX; the shock trooper, whose ref rotations aren't near identity,
  decides it: 7.0 against 15.9 units of bone-to-vertex-centroid error).
- Pose: the mesh instance's per-bone `FCoords` at `+0xB4/+0xB8` (mesh space, the ones
  `GetBoneCoords` reads), the actor's instance at `+0xF8` and mesh at `+0xD4`, `MeshToWorld`
  for the world transform (all as `footik.c` uses them). Whether the `FCoords` rows are the
  bone's basis vectors or the rotation's rows is learnt on the first posed query from the ref
  skeleton's local positions (a near-reference pose is a tie and is asked again). The engine's
  ref skeleton (`Mesh+0x1DC`, `FMeshBone` 0x40: name +0, parent +0x34) is checked name by name
  against the data before anything is trusted.
- Skinning `v = O_b + R_b * RefInv_b * (p - RefO_b)` over the weights, then Moller-Trumbore
  over every triangle, nearest hit. The ray is the shot's: from `HitLocation - Dir * RayBack`
  (150 units back, outside the body) along `Dir`.
- Offline check (`scratchpad\armour\test\armour_test.c`, the DLL's code posed with its own ref
  skeleton): skinned vertices reproduce the reference exactly (0.0000 units); rays at face
  centroids answer the face's flag (spec-ops 21/21 armour, 448/454 flesh; Seekers 10/15 armour
  with the rest hitting a neighbouring face first); **a cast costs 240-280 us** (1.6-2 k
  vertices, 3.1-3.7 k triangles, /O1). Hits are a few per second: no budget concern. (Could be
  cut to ~50 us by skinning once per pawn per frame and a bounding test per bone; not needed.)
- Live mesh data: not used. The `USkeletalMesh` object's vertex/wedge/face arrays were not
  located in memory (no offsets with evidence); the exported psk is the same data.
- Script protocol (`AdventNative`, bool answers only): `ArmourHit <pawn> <class> ox oy oz dx dy dz`
  answers true on an armour triangle; `ArmourLast` whether the ray met the mesh at all;
  `ArmourLog 0|1`; `ArmourReady`. Each hit is noted in `AdventNative.log`:
  `armour hit: <pawn> <bone> armour=yes/no uv=u,v tri=N section=<material> at X Y Z mesh x y z dist=D (us)`.
- **(b) bone table** (`ModArmourMap`, `ModArmor.TableClass`): the hit's nearest of the mesh's
  16 main bones; its armour share at or over `TableLevel` (0.5) means armour. Used when the
  native has no data for the mesh or the ray misses the body. (The compiler refuses elements
  of a 144-entry static array through a context expression, so the table is read through an
  instance's own accessors.)
- (c) the d3d8 fork's per-pixel pick (texedit) is the renderer's view, not the shot's ray: noted
  only.

## Use

`ModArmor` (config `[AdventMod.ModArmor]`):

| key | default | meaning |
|---|---|---|
| `bArmourHits` | True | classify every hit on a non-player pawn (`Classify`, from `ModGoreRules.NetDamage` before the plates) |
| `ArmourFactor` | 1.0 | damage x this on an armour hit (1.0 = no gameplay change until the user decides) |
| `bArmourSparks` | True | `ModGore.Hit`: sparks (`EonEffects.fx_Default_Sparks`, as the blade's strikes) instead of blood on an armour hit; a kill still bleeds and dies as before |
| `RayBack` | 150 | the ray starts this far back along the shot |
| `TableLevel` | 0.5 | bone table: the share that counts as armour |
| `GridTest` | "" | the test harness only: `"cols rows damage delay"` (all four) spawns `ModArmourGrid` |

`ModArmor.ArmourSide(Pawn)` returns +1 (its right), -1 (its left) or 0 from the table's
left*/right* bone shares, for a later "present the plates" behaviour: a mind `M` asks
`Gore.Armor.ArmourSide(M.P)` (ModMinds was being edited by another session, so the one-line
call isn't in yet; the behaviour itself is not built).

The log lines: the native's `armour hit: ...` (above), the table's
`armour hit: <pawn> <bone> armour=yes/no share=S (bone table)`, and `gore: the hit on <pawn>
met armour: sparks, no blood`.

## Test list (run 2026-10-09: see Results below; the harness is tools/run_armour_test.ps1)

1. `scratchpad\armour\run_armour_test.ps1`: level14sectiond (Seeker infantry), the pilot spawns
   a `SeekerInfantry` 450 units ahead, then `ModArmourGrid` (ini `GridTest=5 8 5 45`) fires a
   5x8 grid of rays from the camera across the body, each a real pistol-sized hit (sparks on
   armour, blood on flesh), then `SHOTP`/`SHOT`. Expected: `armour: seekerinfantry loaded`,
   `bone coords convention N` logged once, most rays `armour=no`, the arm guards `armour=yes`,
   casts under 1 ms, no `exception` lines.
2. `scratchpad\armour\armour_sheet.py <log> seekerinfantry <shot.png> out.png`: the hit points
   (orange armour, blue flesh) over the ref-pose render (front and side, from the logged
   mesh-space point) and over the screenshot (world point projected with the logged
   `armourcam:` camera, UE2 projection; roll ignored).
3. The same on a SeekerPilot (helmet: head 43 %) and a SpecOpsSoldier; the hound should log
   `armour=no` everywhere and never spark.
4. A real fight with `bArmorLog=True`: the `armour hit:` lines per shot, the sparks on guards.
5. The fallback: delete `<game>\AdventMod\Armour\seekerinfantry.amesh` for one run: every hit
   must come from the bone table (`(bone table)` lines), no crash.

Gotchas met on the way: the compiler's "Context expression: Variable is too large (576 bytes,
255 max)" on `class'X'.default.Array[i]` for big static arrays (instance accessors instead);
static arrays inside a struct literal in `defaultproperties` were refused ("Bad termination")
for three of nine entries (flat arrays instead); heredocs through the shell lose tabs, so
`.uc` edits went through the editor; `python` on this PC has no numpy/Pillow, `py` does
(`build.ps1` calls `py -I` for the generator, which is numpy-free).

## Results (2026-10-09, hidden runs on the committed sources, worktree build of d30b5ba)

Harness `tools/run_armour_test.ps1` (also in the scratchpad), sheets by `tools/armour_sheet.py`,
offline check `tools/armour_test.c`. Eight game runs that reached the level, one of them a fight.

| run | target | result |
|---|---|---|
| grid, Seeker infantry (level03sectionb, spawned) | 5x8 rays, each a 5-point pistol hit | data loaded (78 bones, 3135 tris, 112 armour); **row convention 2 learnt on the first query** (0.47 against 25.9 units per bone: rows are the rotation's rows, as FEET.md found); 13 of 40 rays met the body; hits on feet, legs, hips, front arm, all `armour=no` (the guards are on the arms, which this grid didn't cross); no exceptions |
| grid, SpecOpsSoldier (the level's own, twice) | | 9 of 40 met the body, 0 armour (its chrome bits are small vest pieces) |
| grid, SeekerDog (spawned) | | 12 of 40 met the body, **0 armour, no spark line** (as required) |
| grid, SeekerScanner (spawned) | | 16 of 40 met the body, **3 hits on the left forearm guard `armour=yes`, each `gore: ... met armour: sparks, no blood`**; sheet `sheet_run13.png`: the dots sit on the scanner's body in the frame, the orange ones on the gun arm |
| fight, level14sectiond, the player's own pistol on a spawned infantry | 22 real hits in 15 s | hips, spine2, neck, Neck02, Head_Nose, leftUpLeg, LeftFrontElbow `armour=no`; **leftForeArm and leftArm `armour=yes` with sparks** (the gauntlet); 3 hits whose ray missed the body fell back to the bone table (`righthand`, `leftLeg`, `share=0.00`); a SeekerCommander of the level was classified too (its data loaded on the fly). The game crashed about 35 s after the last armour line, in the level's own firefight (wall holes, pools, hound packs): not attributable to the classification |
| fallback, infantry `.amesh` moved aside | | `armour: no data for mesh SeekerInfantry (..\AdventMod\Armour\SeekerInfantry.amesh): the bone table decides`, logged once; no crash. (The grid probe alone doesn't consult the table; the table's live use is the fight run's `(bone table)` lines) |

- **Cost in game: 0.7-1.3 ms per cast** (2.6 ms the first time a mesh is seen), against 0.24 ms
  offline: the difference is `FindActor`, a scan of the whole object table per call. A cache of
  the last actor by name would bring it back to ~0.3 ms; a few hits a second cost nothing either way.
- Seeker pilot: `EonCharacters.SeekerPilot` and `SeekerPilot_AssaultRifle` don't load through
  `DynamicLoadObject` from the pilot's SPAWN ("no class"), so the helmet (head 43 %) is untested;
  the scanner's forearm guard (71 %) stood in.
- **Harness lesson:** `bD3DTrace=True` in the test ini is a General Protection Fault at the
  level's first tick on every build tried (7 runs, including the commit before this work); the
  level must be opened as `open <map>?Menu=?Game=EonEngine.EonGameInfo`. Neither is in this work.
- The sheet's ref-pose panels place the live mesh-space point on the T-pose render, so a hit on a
  raised arm shows beside the T-pose arm; the frame overlay (UE2 projection from the logged
  camera) is the one to read for where a shot landed.
