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
