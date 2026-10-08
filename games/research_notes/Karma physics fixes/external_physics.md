# External physics for Advent Rising characters (replace Karma)

Goal: run ragdolls, powered ragdolls and hit reactions in a modern library inside AdventNative.dll
(32-bit, UE2 build 2226), and use Karma only for what still works (or not at all for pawns).

## 1. Library choice (32-bit x86 MSVC)

| Library | Licence | 32-bit x86 today | Character features |
|---|---|---|---|
| **Jolt** (5.x) | MIT | Yes: "Windows x86/x64/ARM64", SSE2 minimum; MSVC x86 SSE2 is in its determinism test list | `Ragdoll` + `RagdollSettings`, SwingTwist/Hinge constraints with position/velocity motors, `DriveToPoseUsingMotors`, `DriveToPoseUsingKinematics`, `SkeletonMapper` (high-detail anim skeleton to low-detail ragdoll), group filters for self-collision, `HeightFieldShape`, `MeshShape` |
| Bullet 3 (2.8x API) | zlib | Builds 32-bit (premake/cmake), but in maintenance mode: issue tracker closed, no recent releases | btMultiBody + PD motors (pybullet humanoid demos), classic btRagdoll demo with cone-twist; tuning is harder, and impulse joints drift |
| PhysX 4.1 | BSD-3 | Yes: 4.1.2 ships x86 Windows builds (vcpkg/NuGet) | Reduced-coordinate articulations with joint drives: stable but heavy to integrate |
| PhysX 5.x | BSD-3 | Docs only show win.x86_64 build presets. Treat 32-bit as unsupported (not verified in release notes) | n/a |
| ODE | BSD or LGPL | Yes | Same family as Karma (LCP, impulse joints). It would repeat Karma's problems |

**Pick Jolt.** It is C++17 (VS2022 / Clang 16+), so wrap it behind a small `extern "C"` API in a
separate C++ translation unit. Keep AdventNative in C. Existing C wrappers are JoltC
(SecondHalfGames), joltc (JoltPhysicsSharp) and zphysics (Zig), but a custom 20-function shim is
simpler. Zig's `zig c++ -target x86-windows` can build it. Keep the shim's exports free of SEH and
exceptions, and give Jolt its own allocator (`JPH::Allocate` hooks).

## 2. Architecture

**Units and frames.** UE2 is left-handed and Z-up, with ~1.9-2.0 cm per unreal unit (uu).
Simulate in metres (scale ~0.02) and flip one axis at the boundary. Convert rotations in a single
helper: FRotator (65536 units per turn) and FCoords go to `JPH::Quat`. Convert near the player and
keep values small. Floats are fine within 5 km.

**World mirror, in order of effort:**
1. *Local proxies (prototype):* do engine line traces (native `XLevel->SingleLineCheck`) around the
   corpse each 0.25 s. Build a ground plane plus a few boxes, or a small `HeightFieldShape` patch
   (e.g. 16x16 samples of downward traces). This is cheap and works on any map.
2. *BSP export at map load:* walk `Level->Model` (Points, Vectors, Surfs, Nodes and their verts).
   Triangulate the polys of collision-enabled nodes into one static `MeshShape`. Cache it to disk
   per map.
3. *Terrain:* read the `ATerrainInfo` heightmap and scale into one static `HeightFieldShape`.
4. *Static meshes:* build one `MeshShape` per `UStaticMesh` collision model (cached by mesh), then
   instance it for each actor with its location, rotation and DrawScale3D (a `ScaledShape` or a
   baked transform).
5. Movers and dynamic Karma props become kinematic bodies, updated each tick from the actor's
   transform.

**Per-tick sync (game thread, one `JPH::PhysicsSystem`, `JobSystemSingleThreaded` or 2 workers):**
1. For each active character, read the animated pose (native bone matrices after the pose build,
   or `GetBoneCoords`) and build a `SkeletonPose` for it.
2. Accumulate frame dt. Step at a fixed 60 Hz with `collisionSteps = 2..4` (120-240 Hz effective),
   with at most 4 steps per frame. Jolt's docs say it is stable at 60 Hz with 1 collision step.
3. Before each step, call `DriveToPoseUsingMotors(prevPose, pose, dt)` (powered) or nothing
   (corpse).
4. After stepping, run `Ragdoll::GetPose`, then `SkeletonMapper` back to the full skeleton. Write
   the result as parent-relative bone rotations (`SetBoneRotation`, or better the native
   post-pose-build hook) and move the actor or mesh origin to the pelvis.
5. Sleep: Jolt deactivates resting bodies on its own. Freeze a corpse only after the bodies are
   asleep, and never remove it while it is below a floor. This avoids Karma's fall-through bug,
   because world collision stays in the sim.

**Cost.** A ragdoll is about 11-15 bodies and 10-14 constraints. Ten ragdolls is about 150
bodies. Jolt's sample shows 160 full ragdolls piled on a Horizon Zero Dawn level in real time.
Estimate: 0.3-1.5 ms per frame single-threaded at 60 Hz x 4 collision steps on a modern CPU (to be
measured).

## 3. Prior art

- **MetaHookSv BulletPhysics** (GoldSrc / Sven Co-op, 32-bit native plugin). It is the closest
  match: Bullet ragdolls bolted onto a 1998 engine through hooks.
  - It reads per-model `_physics.txt` files: capsule or sphere bodies per bone, then point,
    conetwist or hinge constraints.
  - It switches to ragdoll at a configured frame of the `DIE_` sequence, so the animated death
    pose comes first.
  - It simulates at a fixed `bv_simrate` (default 64, clamped to 32-128) and has a
    `bv_force_updatebones` option.
  - It has an in-game debug draw and config editor. Lessons: data-driven per-model configs, plus
    a debug draw/editor, are what made it workable.
- **GTA San Andreas, madleg's "Ragdoll Bullet Physics"**. It is ASI-based, and users tune
  damping, mass and hit reactions in `RagDoll_Physics.ini`. Several community "natural bodyweight"
  config packs exist, so expect tuning to be a long tail.
- **Jolt in production:** Horizon Forbidden West (Guerrilla), and Godot 4.4+ ships Jolt as its 3D
  backend. The ragdoll API is battle-tested.
- **Active-ragdoll pattern (Unity/Unreal "physical animation"):** keep the pelvis or root
  animated, drive the limbs with joint drives, and lower drive strength on hit, then ramp it back.
  This is the Euphoria-lite approach that needs no balance controller.

## 4. Powered ragdoll in Jolt

- `DriveToPoseUsingMotors(pose)` targets local joint orientations with position motors.
  - The two-pose overload also feeds the target velocity, which gives less lag.
  - The spring comes from `MotorSettings.mSpringSettings` (FrequencyAndDamping; default 2 Hz,
    damping 1.0).
  - The torque limit `mMaxTorqueLimit` defaults to unlimited. Set a finite limit so hits can win.
  - A start point: 2-4 Hz and damping 1 on the spine and limbs, 6-10 Hz on the neck and hands,
    torque limits scaled by the child body's mass.
- `DriveToPoseUsingKinematics(pose, dt)` sets body velocities so the ragdoll reaches the pose in
  dt. It is a hard key that still pushes dynamic objects. Use it for the pelvis and root while the
  pawn is alive.
- **Hit reaction:**
  1. Pelvis kinematic, limbs motor-driven.
  2. On hit, call `AddImpulse` at the hit point on the struck body.
  3. Scale the motor frequency or torque limit of that chain by 0.1-0.3, then ramp it back over
     0.3-0.6 s.
  4. Blend the physics pose back to the animation.
  5. On death, turn off motors (or keep a weak 1 Hz drive toward a death pose for stiffness, as
     in the "160 Ragdolls Driven to Pose" sample) and release the pelvis.
- **Stability:** 60 Hz with 2-4 collision steps is comfortable for 1:10 mass ratios. Avoid tiny
  hand or foot bodies (merge them), and call `ResetWarmStart` after `SetPose` teleports.

## 5. Staged plan and effort (evenings of focused work)

0. **Build spike (1-2):** Jolt x86 static lib plus a C shim inside AdventNative. Run a
   standalone smoke test of dropping a box on a plane.
1. **Corpse on a flat plane (3-5):** hand-written ragdoll settings for the main human skeleton
   (about 12 capsules). On death, `SetPose` from the current bone coords, simulate on an infinite
   plane at the pawn's floor Z, and write bones back. Proves the conversions and sync.
2. **World collision (4-8):** trace-built local proxies first, then BSP, terrain and static-mesh
   mirror with a disk cache. Debug-draw the Jolt shapes in-game.
3. **Powered hit reactions (5-10):** keyed pelvis plus motor-driven limbs, impulse and strength
   ramp, blend back. Tune per skeleton in a data file, as MetaHookSv does.
4. **Polish (open-ended):** pooling of 10 active ragdolls with the oldest put to sleep or frozen,
   per-skeleton configs for aliens, gore hookup (dismember means removing a constraint).

Total is about 3-5 weeks part-time to a robust corpse-and-hit-reaction system. Stages 1-2 alone
remove the fall-through and crash class of Karma bugs.

## Sources
- Jolt README and docs: https://github.com/jrouwe/JoltPhysics, https://jrouwe.github.io/JoltPhysics/
- Jolt Ragdoll API: https://jrouwe.github.io/JoltPhysics/class_ragdoll.html
- Jolt MotorSettings.h and PoweredRigTest.cpp (repository sources)
- Jolt samples list (Rig section): https://github.com/jrouwe/JoltPhysics/blob/master/Docs/Samples.md
- Bullet: https://github.com/bulletphysics/bullet3
- PhysX 4.1 x86 packages: https://www.nuget.org/packages/nvidia.physx; PhysX 5 build docs: https://nvidia-omniverse.github.io/PhysX/physx/5.4.1/docs/BuildingWithPhysX.html
- MetaHookSv BulletPhysics: https://github.com/MetaHookSv/BulletPhysics (docs/en/features.md)
- GTA SA Bullet ragdoll configs: https://libertycity.net/user/Hocus/files/gta-san-andreas/mods/parameter-editing/
- JoltC wrapper: https://github.com/SecondHalfGames/JoltC
