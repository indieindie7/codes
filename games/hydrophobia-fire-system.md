# Hydrophobia: Prophecy, the fire system (decompiled 2026-10-25)

Index
1. What it is (l12-18)
2. Data: the fire list and the burning pieces (l19-25)
3. Update order, per frame (l26-32)
4. Extinguish by water (l33-40)
5. Floating fire on the water (l41-47)
6. Burn level, heat haze, fire light (l48-52)
7. Where the code is (l53-70)

## 1. What it is
Three cooperating parts in `HydroPC.exe` (HydroEngine, D3D9, Havok 2010):
- a **fire manager** that owns a flat list of fire points and gives each one a particle system named `FireSystem` or `FloatingFireSystem`, plus a light/heat call;
- **burning pieces** on world objects (debris, crates, Malthus bodies) that carry a burning flag and are checked against the water surface every frame;
- **level particle entities** named `Floating_Fire` and `PD_System_01_Fire`, special-cased by name in the entity update so they ride the water surface.
Fire is not simulated as a field. It is points + particles + a water-height test. All the look comes from the particle definitions (in `hydro.dat`, see the `hydrophobia-mod` skill) and from the `MHHeatHaze`/`MicroHeat` post effects.

## 2. Data: the fire list and the burning pieces
Fire manager (object `in_EAX` in FUN_00c37980, the effects manager):
- fire list: pointer `[0x274b]`, count `[0x274c]`, stride `[0x274e]` (packed 20-bit); record: `+0` id, `+4,+8,+c` position, `+0x10` extra, `+0x14` size (radius), `+0x18` particle-system handle, `+0x1c` flags: bit0 = floating (uses `FloatingFireSystem`), bit1 = disabled.
- two input queues filled by gameplay: `[0x274f..0x2752]` enable/disable by id (sets/clears bit1, calls FUN_0097fc80 on the handle), `[0x2753..0x2756]` position/size updates by id (size only taken when it changed by more than `DAT_00e79ef4`).
- critical sections at `[0x27c3]` and `[0x27c9]` guard both queues (the water job threads post into them).
Burning pieces (FUN_00d191f0): a group record `param_1` with an array at `+4`, stride 0x140; each piece: `+0` burning flag, `+4` "has fire" flag, `[0x41..0x44]` cached position, `[0x45..0x46]` link to the world-object table `DAT_020e7580` (stride 0x8f8, up to 0x400 objects; `+0x2c/+0x30/+0x34` object position, state bits at `DAT_020e7afc`), `[0x49]` top height, `[0x4a..0x4d]` velocity.

## 3. Update order, per frame
FUN_00c3e070 (effects-manager tick, called from the main update FUN_00d0e9d0 in its `FireUpdate`/`Floating_Fire` profiler sections) runs:
1. FUN_00c37980, the fire manager: apply the two queues, then for every fire record not disabled: zero a 0x3c-byte particle transform, ask the world `vtable+0x34(pos, &a, &b)` (the same "sample the water at this point" query the sound manager uses in FUN_00c2c380); if `b != 0` (point under water) the fire is skipped and, if it had a particle system, FUN_009812c0 kills it and the handle goes to 0. Otherwise create the particle system on first sight with FUN_00a2e280(name, 1, &transform, 1.0f, ...) where name = `FloatingFireSystem` when flag bit0 else `FireSystem`, re-set its transform (FUN_00981430) when position or size moved more than `size * 0.5`, and call `vtable+0x30(pos, ..., size, size * DAT_00e77224)` = the fire light / heat source for that fire.
2. FUN_00c2a7e0, FUN_00c3d790, FUN_00c37090, FUN_00c36f80 (other effect lists: splashes, sheets, fear sounds).
3. FUN_00c2fe20, FUN_00c270b0, FUN_00c31060, FUN_00c2fcf0 (water sounds and sheets).
Burning pieces are updated from the object manager instead: FUN_00cb92e0 calls FUN_00d191f0 per group.

## 4. Extinguish by water
In FUN_00d191f0 for each burning piece:
- FUN_00c19990(&cell, &sheet, &depth) samples the water grid at the piece (the HydWaterGridManager query; depth and the second height are 0 when there is no sheet there).
- surface height `s = DAT_00e77224 - (h + depth)` (the game's inverted y), compared with the object's water-line field `obj+0x34 (DAT_020e75b4)` minus the margin `DAT_00e7bd60`.
- when the sheet exists (`depth != 0 && h != 0`), the piece is burning (`+0 != 0`) and `s < waterline - margin`: if the piece has no fire of its own (`+4 == 0`) only the object's state bits get `|1` (wet) and `|2`; else, once per group (`param_1+0x4c` latch), spawn the steam/smoke effect FUN_00c25240 at the cached position and play FUN_00c2c380 = "Water extinguishing fire.wav" (through the `WaterSounds` bank, volume scaled by the master `vtable+4(1)`), then clear the burning flag and set `param_1+0x2c = DAT_00e77224` (a re-ignite timer).
- the fire manager side does the visual: next frame the fire record for that piece is under water (`vtable+0x34` says so) so its particle system is killed.
The script-facing check `{b}Extinguished{-b}` (string at 00e9da00) and `Set Burn Level` (00ea12d8) are reached through the script binding tables, not direct refs; they read this burning flag and the burn level below.

## 5. Floating fire on the water
`Floating_Fire` is a particle entity in the level (0x118-byte records, name at `+0x74`). Three places compare the name:
- FUN_00c4c210 (entity update, case 1): calls FUN_00c11c50(DAT_01cb6780, pos, &height, extra) = the generic "water height and velocity at a point" query on the water manager (also used by reflections, explosions and sounds); if the sampled height is above the entity's own y the entity is lifted to it (`vtable+0x30` of DAT_0194cd94), so the fire rides the sheet. State 5 with no owner triggers FUN_00c236c0 (burn out).
- FUN_00cb05f0: visibility/active test: `Floating_Fire` and `PD_System_01_Fire` use FUN_0041ed60 (the water-dependent test) instead of the plain `~flags & 1`.
- FUN_00cb1300 (enable/disable): for these two names it also releases the render proxy (FUN_00d1df40), posts the sound FUN_009919b0 on disable and calls FUN_00c24960(index, state); for any other entity it only flips bit0 at `+0x9c` and the object-table state.
So floating fire is a normal fire particle system whose emitter is clamped to the water surface every frame and killed when the sheet drops below it; nothing spreads on the water.

## 6. Burn level, heat haze, fire light
- Burn level is a per-character float 0..1 (`Set Burn Level`, tooltip "0.0 (no burn) to 1.0 (crispy)") that drives the `malths_burned` material/anim states (`On_Fire_*`, `AN_OnFire*`, `Task_OnFireAttack`): burned Malthus are an animation + material swap, not a sim.
- `hydro.firelightparams` is a console var (string 00e7e2f0) read by the light call at `vtable+0x30`: per fire, position, size and `size * DAT_00e77224` as range.
- `MHHeatHaze` / `MicroHeat` are post effects (strings 00e7e2c8, 00e847f4) in the same effects manager; `hydro.debugfiresystems` draws the fire list.

## 7. Where the code is
Ghidra project `Documents\Hydrophobia_research\HydroGhidra.gpr`, program `HydroPC.exe.unpacked.exe` (Steamless, read only). Decompiled dumps (not in git): `Documents\Hydrophobia_research\fire_refs\` (DataRefs on the fire strings, `refs.txt`, `functions.txt`), `fire_callers\`, `fire_callers2\`, `fire_code\`.

| Function | Role |
|---|---|
| FUN_00c37980 | fire manager update (fire list, queues, FireSystem / FloatingFireSystem particle create/kill, light call) |
| FUN_00c3e070 | effects-manager tick that calls it |
| FUN_00d191f0 | burning pieces: water sample, extinguish, steam + sound; caller FUN_00cb92e0 |
| FUN_00c2c380 | plays "Water extinguishing fire.wav" from the WaterSounds bank |
| FUN_00c19990 | water-grid sample at a point (depth + height) |
| FUN_00c11c50 | water manager "height/velocity at point" (object DAT_01cb6780) |
| FUN_00c4c210, FUN_00cb05f0, FUN_00cb1300 | Floating_Fire / PD_System_01_Fire entity special cases |
| FUN_00a2e280 | particle-system factory by name (30 call sites: splashes, explosions, fear sounds, fire) |
| FUN_00d0e9d0 | main update, profiler sections FireUpdate / Floating_Fire at 00d135bd, 00d13c6e |

Strings: 00e87fe8 FireSystem, 00e87fd4 FloatingFireSystem, 00e7fe30 Floating_Fire, 00e7fe48 FireUpdate, 00e87cc8 "Water extinguishing fire.wav", 00e9da00 Extinguished tooltip, 00ea12d8 Set Burn Level tooltip, 00e8099c hydro.debugfiresystems.

For a Bevy brawler: copy the shape, not the code. Fire = list of (pos, radius, floating?, particle handle); one water-height query per fire per frame decides alive/dead; extinguish = one steam burst + one sound + flag off, with a cooldown before re-ignite; floating fire = emitter y clamped to the surface height.
