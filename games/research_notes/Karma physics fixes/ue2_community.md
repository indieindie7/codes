# How UE2 games/mods made Karma ragdolls behave (for AdventMod, build 2226)

2026-10-08. **Sources:**
- [1] UT2004's own `KarmaData\*.ka` (local Steam install).
- [2] UT2004 script: `xPawn`, `KarmaParams*`, `LevelInfo` (Documents\UT2004_extract).
- [3] Advent's `AdventPawn` (AdventRising_src).
- [4] UT2003/UT2004 native Karma glue (`KSkeletal`, `KScript`, `KPhysic`, `KTriListGen.cpp`) from github.com/Wallz/UnrealEngineSRC. **This is leaked Epic code with no licence: read it for behaviour only, never copy it.** Copies are in the scratchpad (uesrc).
- [5] Killing Floor / Red Orchestra script, github.com/InsultingPros/KillingFloor (no licence, reference only).
- [6] Unreal Wiki: [Karma](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma.html), [Ragdoll Injury System](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Ragdoll_Injury_System.html), and the BeyondUnrealWiki GitHub mirror.

The UDN pages (RagdollsInUT2003, KarmaAuthoringTool) now redirect, and archive.org is blocked, so nothing is quoted from them. SWAT 4 and Tribes: Vengeance use Havok, so they don't apply. No Advent ragdoll community exists. Unit: 1 Karma unit = 50 UU.

## 1. .ka authoring (Epic's Human.ka compared with make_ka.py)
- **15 bodies, no head/hand/foot parts.** The head sphere is geometry on the *neck* part. Drop our foot and toe parts (hound, Seeker).
- **Filler bodies have no collision.** spine, spine2 and the clavicles are `dynamics_only`: mass, no contacts.
- **Joint limits:**
  - knee hinge −0.29..1.29 rad, elbow −0.17..1.57;
  - **neck and clavicles are hinges ±0.28**;
  - skeletal cones are elliptical: thigh 0.79×0.40, upper arm 0.52×0.79, spine 0.31→0.15;
  - **twist 1.57 everywhere**; stiffness 1000, damping 1.
  
  Ours use round cones of 1.0–1.3 (floppy) and twists of 0.2–0.8, so animated start poses can begin outside the limit (see §4).
- **Total mass about 0.19; ours is 1.0.** Impulses and `KShotStrength` are mass-relative, so ours push about 5× weaker.
- **`.ka` LIN_DAMP/ANG_DAMP are ignored.** Damping is overwritten every step from `KLinearDamping`/`KAngularDamping` [4].
- **NO_COLLISION:** UT lists 19–25 pairs, including non-adjacent ones (l thigh–r thigh, upperarm–spine1, neck–spine1). Our "siblings crash" conclusion is suspect: re-test.
- **Bone names and missing bones:** the engine lowercases mesh bone names before lookup, so part ids must be lowercase. A part with no matching bone only logs "Not All Physics Parts Have Graphics Bones!". **The unplaced body stays jointed to the placed ones**, which trips the joint-error kill in §4: a likely cause of the hound crash. If no part matches at all, an assert fires.
- The `PART parent=` attribute doesn't build the joints (Alien.ka has a mismatch). Joint axes are given per part frame.
- **Non-humans:** there is no quadruped in UT. Skaarj.ka = biped + 3-part tail chain. For the hound, use the human template: pelvis, spine, neck carrying the head sphere, and four legs as cone + hinge.

## 2. Settings
| | UT2004 | KF / RO | ours |
|---|---|---|---|
| KFriction / KRestitution | 0.6 / 0.3 | **1.3 / 0.2** | 0.6 / 0.1 |
| KImpactThreshold | 500 | 85 | 500 |
| RagDeathVel / UpKick / ShootStrength | 200 / 150 / 8000 | 100 / 0 / 200 | 250 / 60 / 8000 |

All three use damping 0.15/0.05, KVelDropBelowThreshold 50, KBuoyancy 1 and KStartEnabled. KF clamps spin (RagMaxSpinAmount 100). UT corpses de-res after 13 s; KF/RO keep them 30 s.
- `bHighDetailOnly`, `bClientOnly`, `bKDoubleTickRate`, `bKStayUpright`, `bDoSafetime` and `bDestroyOnWorldPenetrate` are **PHYS_Karma only**. But `bKDoubleTickRate` moves a ragdoll's world-triangle query into the double-rate pass. UT never sets it: we should set it False.
- **`bDestroyOnSimError` defaults to True.** A solver NaN destroys the pawn. Set it False.
- **Level settings:**
  - `RagdollTimeScale` (UT's slow-mo-death mutator uses 0.3);
  - `MaxRagdolls` 4 (when full, KMakeRagdollAvailable freezes the oldest non-important body);
  - **`bKStaticFriction`, "better ragdoll/ground friction, more CPU", exists in Advent: try it.**
- `KSetSimParams` is global until exit. Epsilon below about 0.000025 stops the simulation. MaxTimestep (default 0.04) has a per-tick step cap, so going too low slows Karma down; our 0.016 is fine.

## 3. Falling through floors
- **Static meshes collide per triangle only if `UseSimpleKarmaCollision=False`.** With the default True, only authored Karma hulls count, so **a hull-less mesh is invisible to ragdolls** [4]. This likely explains the stairs sinking and "floors that don't stop bodies". The flag is read every frame, so flipping it at runtime on those meshes is worth testing (unverified).
- `KSetBlockKarma(true)` before `SetPhysics` is required. Thin grates and terrain can still be tunnelled through.
- **What `KFreezeRagdoll` does:** it tears Karma down, sets PHYS_Falling and zero velocity, and **leaves bCollideWorld=0**, so the body drops out of the world. UT hides this with de-res. Our PHYS_None hold is correct.

## 4. Engine bugs and crash mechanisms
- **Ragdoll start:** it is deferred one tick, puts every body at the current bone pose, and ignores the mesh offset from then on. If PrePivot was lifted (ModReact.OnFloor), the body jumps. Two paths destroy the pawn:
  - an out-of-limit pose leads to a SimError, then destroy (if bDestroyOnSimError);
  - **any joint gap above 50 UU logs "(Karma:) Excessive Joint Error. Destroying RagDoll." and calls `DestroyActor(pawn)` unconditionally.**

  Advent recycles pawns, so these are prime suspects for the clip→ragdoll and hound GPFs. **Check advent.log for "(Karma:)" lines.** Advent's own ragdoll code starts the ragdoll at the death clip's AnimEnd. UT and KF call `StopAnimating(true)` before `SetPhysics`.
- **`KIsAwake` is always false for ragdolls** (the source says "JTODO").
- **`KWake` wakes only mesh bone 0's body.** Our root bone isn't a part, so it does nothing. To wake a ragdoll, give a tiny `KAddImpulse(v, p, 'hips')`, which enables that body.
- **`KAddImpulse` on a ragdoll:**
  - with a bone name, it pushes that body's centre of mass (no torque);
  - **an unknown bone name indexes −1** (out of bounds);
  - with no bone, it does nothing unless a trace hit the body first.
- `KSetSkelVel` sets whole-body linear and angular velocity (UT's rocket throw: dir·200 + 250 up, ang 18000).
- `KScaleJointLimits` *multiplies* the cone and hinge stops (repeated calls compound; twist is untouched).
- **Built-in convulsions** (`bKDoConvulsions`): limits ×0.5 for 0.1 s, then restored at infinite stiffness. A free twitch for dying bodies.

## 5. Powered, animated and get-up attempts
- **Bone lifters are not motors.** Each is a soft upward contact at one body (LiftVel UU/s, softness curve, lateral friction). Epic: you "MUST turn collision off" first. UT uses them only for the de-res float-away (Spine/Spine2, 0→32 UU/s).
- **The only documented get-up** (Injury System, [6]):
  1. KFreezeRagdoll;
  2. restore bCollideWorld and SetCollision;
  3. relink the mesh (dummy, then the original) to clear the ragdoll state;
  4. blend the saved bone directions out with SetBoneDirection, alpha 1→0.
  
  Lifters were rejected for this. Very short ragdolls become a "ball of limbs".
- **KF BodyAttacher** pins a ragdoll to the world with a `KBSJoint` (KPos in UU/50). Advent's KConstraint has `KConstraintBone1/2`, so per-bone constraints are an untested alternative to impulse-driven powered ragdolls.
- Nobody shipped motor-driven Karma ragdolls. Hinge motors and StayUpright work only on PHYS_Karma rigid bodies.

## Next steps
1. **make_ka.py:**
   - twist 1.57;
   - elliptical cones;
   - neck and clavicle hinges;
   - no head, hand or foot bodies;
   - collision-less fillers;
   - mass about 0.2;
   - more NO_COLLISION pairs.
2. **CorpseParams:**
   - bDestroyOnSimError=False;
   - friction 1.3, restitution 0.2;
   - bKDoubleTickRate=False;
   - Level.bKStaticFriction=True.
3. **Before going limp:**
   - PrePivot=0;
   - widen limits briefly (`KScaleJointLimits(2,1000)`, then `(0.5,1000)`);
   - log "(Karma:)" lines.
4. **Wake and twitch:** wake with a named-bone impulse; twitch with convulsions.
5. **Stairs:** test UseSimpleKarmaCollision=False on the stair meshes.
