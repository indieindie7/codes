# Karma internals in Advent Rising's Engine.dll (decompiled 2026-10-08)

Source: Ghidra 12.1.4 headless decompile of `System\Engine.dll` (copy, image base 0x10000000),
strings and the exported UnrealScript only. No game launch, no other engine source.
Work files: `%TEMP%\claude\...\scratchpad\decomp_karma\` (strings.txt with referencing
functions, helper scripts) and the full decompile at `...\scratchpad\decomp_anim\out\Engine.c`.

Karma (MathEngine MdtWorld/Kea/Mcd/Mst) is statically linked, unnamed (`FUN_105b....`-`FUN_1063....`).
The engine's own Karma glue is named only where exported. Exported C++ names sit on 5-byte
incremental-link thunks (`jmp rel32`); the real bodies are listed below. Patching the thunk's
`jmp` target redirects every caller that goes through it (the engine's own calls do).

| Function | thunk (export) | real body |
|---|---|---|
| `AActor::KFreezeRagdoll` | 0x10303e04 | **0x1040b4c0** |
| `AActor::preKarmaStep` (virtual, vtable +0x15c) | 0x1030d585 | 0x1040bcd0 |
| `AActor::preKarmaStep_skeletal(float)` | 0x10304ead | **0x10411820** |
| `AActor::postKarmaStep` (virtual) | 0x103056be | 0x1040c020 |
| `AActor::postKarmaStep_skeletal` | 0x103052d6 | **0x10411a70** |
| `AActor::physKarmaRagDoll(float)` (per frame) | 0x1030d355 | 0x10413d60 |
| `AActor::KIsAwake` | 0x1030aa10 | 0x1040ad40 |
| `AActor::KWake` | 0x103112c5 | 0x1040b630 |
| `AActor::KAddImpulse` | 0x1030651e | 0x1040b6d0 |
| `execKMakeRagdollAvailable` | 0x10301348 | 0x1040fb80 |
| KTickLevelKarma (unnamed) | - | 0x103f91c0 |
| KInitGameKarma / KInitLevelKarma | - | 0x103f8bc0 / 0x103faf50 |
| world step with partitions ("KWorldStep") | - | 0x10404cc0 |
| KBuildPartitions | - | 0x10402bb0 |
| sim-error (NaN/Inf) check | - | 0x10403f00 |
| KInitSkeletonKarma | - | 0x10412b20 |
| asset instancing (.ka -> Mdt/Mcd) | - | 0x10412560 |
| KTermSkeletonKarma | - | 0x10413d80 (thunk 0x1030fc4f) |
| KScaleJointLimits impl | - | 0x10411390 |
| KSetSkelVel impl | - | 0x10411170 |
| .ka loader (`..\KarmaData\*.ka`) | - | 0x10419760 |
| .ka joint parser (type strings) | - | 0x106325f0 |

Global: `KGData` (`_KarmaGlobals*`, export 0x107c91ac, 0x1526c bytes). Level's MdtWorld* =
`ULevel+0x12e4`; level ragdoll list `ULevel+0x12f4/+0x12f8` (TArray<AActor*>).

## Offsets used below

AActor: 0x3c bitfield (bit2 bCollideActors, **bit3 bCollideWorld**, bit6 set at ragdoll init),
0x55 Physics (2 Falling, 0xe Karma, 0xf KarmaRagDoll), 0xb8 Level, 0xbc XLevel, 0xd4 Mesh,
0xf8 MeshInstance, 0x12c PhysicsVolume, 0x130 Location, 0x148 Velocity, 0x238 KParams.
LevelInfo: 0x328 KarmaTimeScale, 0x32c RagdollTimeScale, 0x330 MaxRagdolls, 0x334 KarmaGravScale.
KarmaParams: 0x88 KTriList, 0x90 KMass, 0x94 KLinearDamping, 0x98 KAngularDamping,
0xa0 KStartEnabled, 0xa4 KStartLinVel, 0xb0 KStartAngVel, 0xc0 KActorGravScale,
0xc4 KVelDropBelowThreshold, 0xc8 KMaxSpeed, 0xcc KMaxAngularSpeed, 0xd0 bits
(bit2 bKDoubleTickRate, bit3 bKStayUpright, bit7 bDoSafetime), 0xd4/0xd8 StayUpright stiffness/damping.
KarmaParamsSkel: 0xe8 KSkeleton, 0xf4 bits (bit0 bKDoConvulsions, bit1 bRubbery),
0xf8/0xfc KConvulseSpacing, 0x100-0x114 KShotStart/End, 0x118 KShotStrength, 0x11c bit0 bKImportantRagdoll.
USkeletalMeshInstance (ragdoll part): 0x418 McdModel* per graphics bone (num 0x41c),
0x424 MdtConstraint* per bone (num 0x428), 0x40c per-bone flags, 0x430 ragdoll initialised,
0x438 bounds FBox, **0x450 frozen**, 0x454 bone lifters (stride 0x28, num 0x458),
0x460/0x464 first/last bone index with a body, 0x47c ragdoll time, 0x480/0x484/0x488 convulsion timers.
McdModel -> MdtBody: `*(model+0x24)` (FUN_105d7b80).
MdtBody: 0x10 force accum, **0x20 torque accum**, 0x90 linear vel, 0xa0 angular vel,
0x170/0x180 impulse accums (+0x1a0 flag), 0x1ec bit0 enabled.
MdtBody API: AddForce 0x105c0a70, AddForceAtPos 0x105c0aa0, AddImpulse 0x105c0b70,
AddImpulseAtPos 0x105c0bc0, SetLinVel 0x105c0100, SetAngVel 0x105c0130, GetLinVel 0x105bf9a0,
GetAngVel 0x105bf9e0, GetTransform 0x105bf7e0, SetTransform 0x105bfe80, GetPos 0x105bfd90,
GetMass 0x105bf890, SetLinDamp 0x105c0160, SetAngDamp 0x105c0180, Enable 0x105c07e0,
Disable 0x105c0770, IsEnabled 0x105c0860. Unit scale U->ME = 0.02 (1 Karma unit = 50 UU).

## 1. World setup and stepping

KInitGameKarma (0x103f8bc0) defaults, i.e. the `KSimParams` block at `KGData+0x15250`:

| field | KGData | default |
|---|---|---|
| GammaPerSec | +0x15250 | 6.0 |
| Epsilon | +0x15254 | 0.001 |
| PenetrationOffset | +0x15258 | 0.015 |
| PenetrationScale | +0x1525c | 1.0 |
| ContactSoftness | +0x15260 | 0.008 |
| MaxPenetration | +0x15264 | 0.13 |
| MaxTimestep | +0x15268 | 0.04 |

**`KSetSimParams` is global**: execKSetSimParams just copies the 7 floats into KGData. Calling it
per ragdoll (ModGore does) changes the solver for every Karma object in the game.

KInitLevelKarma (0x103faf50): MdtWorld created, `SetMaxMatrixSize(64)` (world+0x1a8, default
unbounded), world+0x22c = 1 (NaN/Inf sim check on), auto-disable on (world+0x190 = 1) with
thresholds 0.02 / 0.05 / 0.02 / 0.05 (world+0x194..0x1a0; linear/angular velocity and
acceleration, Karma units), epsilon from KGData. Default world contact: type 2 (2-D friction),
friction 10, primary slip 0.5, softness = ContactSoftness. world+0x1e8 = 10 is left at the
library default (probably the Kea iteration limit; not confirmed).

KTickLevelKarma (0x103f91c0), per frame:
```c
dt = DeltaTime * Level->KarmaTimeScale;            // 0.9 in Advent
if (KGData->bAutoEvolve && !paused) {
    step   = min(dt, KGData->MaxTimestep);          // 0.04 cap: below 25 fps physics runs slow
    nSub   = clamp(ceil(DeltaTime * 40.0), 1, 4);   // only for bKDoubleTickRate actors
    stepDT = dt / nSub;
} else { step = 0.03; nSub = 1; }
MdtWorldSetEpsilon(world, KGData->Epsilon);
MdtWorldSetGamma(world, clamp(step * GammaPerSec, 0, 0.5));
for each ragdoll in Level ragdoll list: update world tri-list around it (FUN_104115b0, rate 0)
KUpdateContacts(level, rate 0);  KWorldStep(world, step, level, 0);
MdtWorldSetGamma(world, clamp(stepDT * 6.0, 0, 0.5));   // hard-coded 6, ignores GammaPerSec
repeat nSub: tri-lists (rate 1), KUpdateContacts(rate 1), KWorldStep(world, stepDT, level, 1);
```
So a normal ragdoll gets **one solver step per frame** (no substeps) unless its KarmaParams has
`bKDoubleTickRate` (then 1-4 substeps at ~40 Hz). KWorldStep (0x10404cc0) re-implements the
MdtWorld step per partition: if any body in a partition belongs to a ragdoll, that partition's
dt is multiplied by `RagdollTimeScale`; for each actor in the partition it calls the virtual
`preKarmaStep(dt)` (FUN_10403130, once per actor via KStepTag), packs and solves the partition,
with KGData+0x1522c set it integrates forces itself and applies "safe time" (bDoSafetime bodies
whose time of impact < dt get their velocity x0.1), then runs the NaN/Inf check (0x10403f00:
any non-finite force/velocity zeroes the whole partition's velocities and forces; positions are
not repaired), then destroys bDestroyOnSimError actors and calls postKarmaStep.

Per-step forces for ragdolls (`preKarmaStep_skeletal`, 0x10411820): for every body,
`SetLinearDamping(KParams.KLinearDamping)`, `SetAngularDamping(KParams.KAngularDamping)`
(+ water-volume fluid friction), `AddForce(mass * PhysicsVolume.Gravity*0.02 * KActorGravScale *
Level.KarmaGravScale)`. **The .ka `LIN_DAMP`/`ANG_DAMP` are overwritten every step** by the
pawn's KarmaParamsSkel damping (default 0.2/0.2).

postKarmaStep_skeletal (0x10411a70), per step: writes body transforms to bones, moves the actor
to the root body (MoveActor; bCollideWorld is off), clamps each body's linear speed to
`KMaxSpeed` (default 2500 UU/s); **no angular-speed clamp for ragdoll bodies** (KMaxAngularSpeed
is used only for single-body PHYS_Karma).

## 2. Ragdoll creation, .ka assets, the script natives

`.ka` files are loaded once at KInitGameKarma from `..\KarmaData\*.ka` into the asset DB.
Joint types the parser knows (0x106325f0, MeFile type id in brackets): `carwheel`(1) `hinge`(2)
`ballandsocket`(3) `conelimit`(4) `universal`(5) `rpro`(6) `prismatic`(7) `skeletal`(8)
**`angular3`(9) `spring6`(10)**. Parameters parsed:
- skeletal: CONE_TYPE, CONE_HALF_ANGLE_X/Y, CONE_STIFFNESS, CONE_DAMPING, TWIST_TYPE,
  TWIST_HALF_ANGLE, TWIST_STIFFNESS, TWIST_DAMPING (radians; no motor).
- hinge/prismatic: HIGH_LIMIT, LOW_LIMIT, HIGH/LOW_STIFFNESS, LIMITED, **MOTORIZED, DES_VEL,
  MAX_FORCE** (a velocity motor; no limit damping key).
- conelimit: HALF_ANGLE, STIFFNESS. angular3: STIFFNESS, DAMPING, ROTATION_ENABLED.
- spring6: LINEAR_STIFF_X/Y/Z, LINEAR_DAMP_X/Y/Z, **ANGULAR_STIFF_X/Y/Z, ANGULAR_DAMP_X/Y/Z**.

KInitSkeletonKarma (0x10412b20), run when Physics becomes PHYS_KarmaRagDoll (or lazily from
physKarmaRagDoll): looks up the asset named by KarmaParamsSkel.KSkeleton, `SetCollision(false,
false)`, instances it, then for each graphics bone (name lowercased) finds the model and joint
with that name; each body is placed at the bone's current world pose (GetBoneCoords), damping
from KarmaParams, enabled or disabled by `KStartEnabled`. Models with no matching bone are
destroyed after hook-up. Then: `SetCollision(true, false)`, **bCollideWorld cleared**
(`flags & ~8 | 0x40`), actor appended to the level ragdoll list, `KSetSkelVel(KStartLinVel,
KStartAngVel)`, death shot impulse (KShotStrength*0.01 along KShotStart->End at the hit bone),
`bRubbery` -> KScaleJointLimits(5.0, 5e8), convulsion timer.

Mass/inertia come straight from the .ka DYNAMICS (MASS, INERTIA, MASS_OFFSET); the engine does
not recompute them. **Our make_ka.py writes TOTAL_MASS = 1.0 for the whole body** (0.02-0.16 per
part). KAddImpulse on a ragdoll bone = `MdtBodyAddImpulse(impulse * 0.02 * 0.01)` at the centre
of mass (the position argument is ignored for ragdolls, so no torque): 2e5 UU -> 40 Karma
momentum units on a ~0.1 mass part = ~20000 UU/s before the KMaxSpeed clamp. That is the launch
seen with the powered-ragdoll test; 1e7 makes non-finite values -> the sim-error path.

physKarmaRagDoll (per frame, 0x10413d60): returns if frozen (+0x450); for every body after the
first in bone order it reads both anchors of `joints[i]` with **no null check**
(MdtConstraintGetPosition 0x105c1910) and if they are more than 1 Karma unit (50 UU) apart it
**destroys the actor** (`XLevel->DestroyActor(this)`). Also KVelDropBelow, convulsions
(KScaleJointLimits(0.5, 1000) for 0.1 s, then (2.0, FLT_MAX): after a convulsion every limit is
hard, the .ka stiffness is gone), bone lifters (implemented as a contact with a prescribed
upward velocity per lifted bone).

KScaleJointLimits impl (0x10411390): for each joint, Mdt type 1 (hinge: scales both MdtLimit
stops at limit+0x30/+0x40 and sets their stiffness at +4) or type 9 (skeletal: scales the two
cone half-angles stored as cos(a/2) at +0x170/+0x174 and sets cone stiffness +0x180). The
twist limit is never scaled.

KFreezeRagdoll (0x1040b4c0):
```c
if (skel->bRagdollInit) {
    KTermSkeletonKarma(skel);                 // destroys bodies/joints, removes from ragdoll list
    if (Physics == PHYS_KarmaRagDoll) { setPhysics(PHYS_Falling); Velocity = 0; }
    skel->bFrozen(+0x450) = 1;                // physKarmaRagDoll now does nothing, pose held
}
```
KMakeRagdollAvailable (0x1040fb80): if `Level.MaxRagdolls` (4) <= ragdolls alive, KFreezeRagdoll
the first one that is not bKImportantRagdoll. (It reads KarmaParamsSkel+0x11c without a null
check.) **This is the engine's "at rest" freeze**: there is no native rest detection; bodies are
frozen when the ragdoll cap is hit (AdventPawn.PlayDying calls KMakeRagdollAvailable).

KIsAwake (0x1040ad40) = `IsEnabled(getKModel()->body)`; a ragdoll has no actor KModel, so it is
**always false for ragdolls**. KWake (0x1040b630) for ragdolls enables only `models[0]` (bone 0),
which normally has no body, so it is a no-op. Neither checks the 0x418 body array.

## 3. Joint motors / stiffness

- `skeletal` joints (what make_ka writes, Mdt type 9) have soft limits only: cone and twist
  stiffness+damping. No motor.
- `hinge` has a built-in velocity motor (MOTORIZED/DES_VEL/MAX_FORCE) on its MdtLimit, plus
  limit stiffness. A motor drives toward a velocity, not a pose, but a per-step
  `DES_VEL = k*(targetAngle - angle)` with MAX_FORCE as the strength is a clean PD controller
  solved inside Kea.
- `angular3` (STIFFNESS/DAMPING) and `spring6` (ANGULAR_STIFF/DAMP x3) are soft constraints
  holding the relative orientation the two parts had at creation. These are implicit
  (in-solver) springs: the stable way to do a powered ragdoll in Karma.
- Engine paths that touch skeletal joints at run time: only KScaleJointLimits and bRubbery /
  convulsions. KarmaParamsSkel has no motor fields; nothing in the engine sets motors on
  ragdoll joints.
- A DLL can change any of these directly: the joint pointers are in `skelinst+0x424[bone]`
  (Mdt type at constraint+0xb0), limit fields as above; there are no exported MdtXxxSet*
  functions, so use the addresses/offsets here (KScaleJointLimits' own setters:
  0x105c2510 set stop, 0x105c2520 set stiffness, 0x105bdc40/0x105bdc60 cone half-angles,
  0x105bdc80 cone stiffness).
- Caution: only joints whose id equals a graphics bone name end up in 0x424 and are destroyed
  by KTermSkeletonKarma. A second joint per bone (e.g. adding an angular3 next to the skeletal
  one) would never be destroyed and would leave a constraint on freed bodies
  (KBuildPartitions only warns "Constraint found with invalid or destroyed MdtBody", then uses
  it). Doing it from a DLL means creating and destroying the extra constraints yourself.

## 4. The freeze / fall-through bug

Cause: KInitSkeletonKarma clears bCollideWorld; KFreezeRagdoll switches to PHYS_Falling and
never restores it, so physFalling moves the cylinder with no world collision until
FellOutOfWorld destroys the pawn. Both the script call and the MaxRagdolls cap go through the
same function.

Minimal native fix (one byte): in KFreezeRagdoll at **VA 0x1040b559** the call
`setPhysics(2, NULL, (0,0,1))` is `6a 02` (push 2) followed by `ff 90 1c 01 00 00`
(call [eax+0x11c]). Patch **0x1040b55a: 02 -> 00** (PHYS_None). The frozen pose is held by the
+0x450 flag, the actor stays where the root body was, collision stays bCollideActors=1 /
bBlockActors=0. Alternative: hook the thunk at 0x10303e04, call the original, then set
PHYS_None. Restoring bCollideWorld with PHYS_Falling is worse: the cylinder (Location = root
body) lands on its bottom and the corpse pops by CollisionHeight. The script workaround in
ModReact (SetPhysics(PHYS_None) after KFreezeRagdoll) does the same thing, but it misses the
freezes the engine does on its own through KMakeRagdollAvailable.

## 5. Hook points for a DLL

1. **Per-step pose drive**: redirect the thunk 0x10304ead (`preKarmaStep_skeletal`) to our
   function: call the original (gravity/damping), then for each bone i in [skel+0x460,
   skel+0x464] with `body = *(models[i]+0x24)`: compute the torque from the target
   animation pose (world rotations from the mesh instance) and add it to the torque accumulator
   (`body+0x20..0x28`) or adjust hinge motor DES_VEL. It runs once per solver step with the
   partition dt, inside KWorldStep, before the solve. Use torques with an equal and opposite
   torque on the parent (internal torque, so the body doesn't spin as a whole), scale gains by
   the part inertia and clamp. Don't use KAddImpulse from script for this.
2. **Stability**: give ragdoll KarmaParamsSkel `bKDoubleTickRate=True` (1-4 substeps at ~40 Hz,
   gamma 6/s); or patch the tick to use more substeps (0x103f91c0: `ceil(dt*40)` constant at
   0x106c84bc = 40.0f, clamp 4). MaxTimestep 0.04 is global (KSetSimParams).
   world+0x1e8 (10, probably the Kea iteration limit) and world+0x1a8 (max matrix size 64) are
   plain fields of `*(ULevel+0x12e4)`.
3. **Velocity clamps**: the linear clamp is per body in postKarmaStep_skeletal (KMaxSpeed); add an
   angular clamp in the same hook (thunk 0x103052d6): `body+0xa0` angular velocity.
4. **KIsAwake/KWake**: replace the thunks 0x1030aa10 / 0x103112c5: for PHYS_KarmaRagDoll,
   awake = any body in 0x418 enabled (`body+0x1ec & 1`), wake = MdtBodyEnable (0x105c07e0) on all.
5. **Corpse loss**: physKarmaRagDoll destroys the pawn when a joint separates by more than 50 UU
   (after big impulses). Hook the thunk 0x1030d355 or patch the DestroyActor call to freeze
   instead, so squads don't lose members.

## Crash candidates (hound GPF, death clip -> ragdoll)

Not reproduced; ranked by what the code does:
- physKarmaRagDoll reads `joints[i]` for every body after the first with no null check: any
  part whose joint wasn't created or doesn't match its bone name -> GPF on the first frame.
- A joint whose part was destroyed during hook-up (part name not a bone of the mesh) stays in
  the world -> KBuildPartitions warns, then dereferences a dead body.
- Big joint errors on the first step (bodies placed from the current pose, which after a root
  motion clip or with a scaled mesh may not match the .ka joint frames: the .ka `scale` is
  fixed, DrawScale is not applied to the asset) -> separation > 50 UU -> DestroyActor during the
  physics tick, or non-finite values -> partition zeroed but positions left NaN.
- KMakeRagdollAvailable and KTermSkeletonKarma dereference KarmaParamsSkel without null checks:
  swapping or clearing KParams on a live ragdoll crashes.
The hound skeleton itself checks out: hips is bone 0 (the first body), all part names are unique
bones (40 bones, no case clashes). The next step is a native log in the preKarmaStep hook:
a null joint, a NaN body, and the joint separation per bone.

## Tested in game (2026-10-08)
- **The one-byte KFreezeRagdoll patch (push 2 -> push 0) is harmful.** With it, a frozen ragdoll loses its pose and stands back up in its animation (heads 121-130 units over the floor after the freeze, in prints and in corpselist). Without it, ModReact's script hold (PHYS_None once the body is PHYS_Falling with no world collision) keeps bodies lying (heads -6 to 8 over the floor). karmafix.c stays in AdventNative behind `[AdventMod.ModGore] bKarmaFreezeFix`, default False.
- **The Epic-style .ka** (mass 0.2, twist 1.57, from make_ka.py) works: soldiers fall and lie flat, with no crash in two kills per run.
