# Plasma burns and through-and-through bullets (plan, 2026-10-16)

The user (10-16): "plasma does plasma damage to the body ... bullets should do the whole body penetration and traversal
while the blood and gibs be like simulated as if coming from the target and then hitting the objects around".

## How it works today (Classes/ModGore.uc)
- Every hit: ModGoreRules.NetDamage -> Melee.Strike -> Armor.Classify/Strike -> React.Hit -> ModGore.Hit (~796).
- Bleeds(): DamageType.bCausesBlood and BloodKind() from the surface type (1 red, 2 purple Seekers, 0 holograms,
  ShockTroopers, machines).
- Size = DecalScale (1.6) * clamp(0.35 + Damage/120, 0.35, 1).
- Exit spray = ONE instant Trace along the shot (tilted -0.25 z), from CollisionRadius out to SprayReach (260); a wall
  hit gets WallRun + WallDrip. Not a flying liquid.
- Then floor drips, bleed trail, blood coat (Spatter), wound lump if Damage >= 8 (AddWound, nearest of 12 bones), streak.
- Kill: WantsGib (~871) when overkill >= GibOverkill (60) or the type name says EXPLOSION/GRENADE/LAUNCHER/ALTFIRE/
  MISSLE (never PUSH/PULL/...). Only GibSet humans ('marine') and Seeker infantry. Gibs fly (ModGib), land with
  GibHit (splat by speed/1600, 0.2-0.5), sink to a stain (GibGone). Six instant spray traces round the body.
- Plasma burns exist only on WALLS: ShotGone (~1678) -> Burn (~1913), BurnChance 0.35, Burns[4] white-hot -> orange
  -> ember -> soot over 2.5-3.5 s. Bodies never burn.

## Weapons (stock source Documents\AdventRising_src, local only)
Damage types carry no physical flags, so the split is by name (config lists):
- Plasma / energy bolts: SeekerPulseFire (+AltFire), SeekerAssaultFire (+AltFire) (laser trails, dynamic light),
  AurelianLaser, EnergyBlast*, HumanBlasterAltFire. SeekerMicrowaveFire is in the explosion family.
- Bullets (tracers or instant): HumanPistolFire, SeekerPistolFire (no _Proj: instant), HumanXJ9Fire, SeekerXJ9Fire
  (tracer 12000-15000 uu/s), SeekerPhotonFire (sniper tracer, 10000).

## Plan (script only; no native or shader change in round 1)
1. **Config** in ModGore: `PlasmaTypes=`, `BulletTypes=` (substring of the type name), `bPlasmaBurns`, `bPenetration`,
   `bExitDrops`. All default on in the dev ini, logged with bGoreLog.
2. **Plasma on a body:** blood x PlasmaBleed (0.3): no exit spray, fewer drips, no bleed trail (seared shut).
   A sear on the body: a small additive glow riding the nearest bone (AddWound's bone search), cooling
   white-hot -> orange -> ember -> off with the Burns frames over ~3 s; a smoke puff (ModImpactPuff) at the hit.
   Later: a soot coat (ModBloodCoat Kind 3, own generated soot texture) that darkens with more plasma hits.
3. **Plasma kill:** no gib unless overkill >= 2 x GibOverkill; heavy soot coat instead (the char look).
4. **Bullets go through:** exit point = the far side of the body along the shot. An exit wound there
   (AddWound, bigger), and the shot goes on: Trace from the exit up to PenetrateReach (1500); a pawn there takes
   Damage x PenetrateKeep (0.5) through TakeDamage (guard flag so it chains once); a wall there gets the
   ShotGone impact (hole, chips, puff).
5. **Exit spray as flying drops:** 3-8 drops (by damage) thrown from the exit in a 20-degree cone along the shot,
   600-1000 uu/s, from the existing ModBloodDrop pool (MaxDrops 24). A new `bSpray` on the drop: landing on a wall
   makes a spray mark + WallRun (DropLanded skips walls today); on the floor a splat. When the pool is empty or the
   player is past DripReach, fall back to today's instant trace.
6. **Gibs** already fly from the body and mark what they land on; give their spawn velocity the shot direction
   (Dir) more weight for bullets, so pieces go away from the shooter.

## Test (test_run.ps1, background)
Pilot steps: spawn Seeker, shoot with pulse rifle (sear glows, no spray), XJ9 through two Seekers in a line
(second one hurt, exit wound, drops hit the wall behind), list counts (`droplist`). Check the gore log lines and
the FPS line (no hitch from the extra traces).

## Built and tested (2026-10-16, round 1)
- ModGore: ShotKind, Sear, ExitSpot, ExitDrops/SprayDrip, PassThrough, WantsGib plasma rule (2 x GibOverkill);
  ModBloodDrop.bSpray (DropLanded: spray mark + WallRun on walls); new ModSear.
- Gotcha: a `config array<string>` loads EMPTY when the ini has no key (this UE2 build), so the type
  lists are fixed `string[8]` arrays.
- Pass-through damage skips the player's friends (a test XJ9 went on into a SpecOps ally).
- Off-screen test (level03sectionb, two SeekerInfantry in line, pilot HURT): pulse -> "plasma sear ... bone 2",
  no spray, 312 overkill plasma did not gib; XJ9 -> exit wound + "exit drops 3-8", "pass-through ... hits
  SeekerInfantry1" (0.5 damage) which bleeds out its own back; 46 drops thrown, 46 landed; 15 gib parts on a
  400 XJ9 kill; fps 60 cap, worst 20-23 ms (same as before).
- Not yet checked by eye: the sear glow's size/brightness on the body, spray marks on a wall behind a target.
