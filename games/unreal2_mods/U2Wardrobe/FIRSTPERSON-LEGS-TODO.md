# First-person body: legs and feet (parked 2026-10-02)

State: head-locked camera, the body slides back when looking down (DownPush), step snaps eased
(StairEase/StairMax). Commit cfebd2b. What's left is the legs.

## Problems seen (the user's video, 2026-10-02)
- The stock walk/run cycles look wrong from the head: big knee lifts, and the feet slide when
  the speed doesn't match the cycle.
- Stairs: Sanctuary's and Avalon's (TutA) stairs are smooth collision ramps (height changes
  about 1 unit per tick, measured with bStairLog). The body slides up a ramp while the walk
  cycle plays as if on flat ground, so the feet sink into the steps going up and float going down.

## What the engine gives us (exported Engine.u, UCC batchexport)
- Legend/Golem meshes: `MeshGetNodeNamed`, `MeshNodeGet/SetTranslation`,
  `MeshNodeGet/SetRotation`, `MeshNodeGet/SetScale`, with `EMeshNodeRelType` World / Mesh /
  ParentNode / RefPose. Scale had no effect on these meshes; **rotation and translation are
  untested**: that's the first test.
- `PlayAnim` / `LoopAnim` (Rate, TweenTime, Channel), `AnimBlendParams(Stage, Alpha, In, Out,
  BoneName)`, `GetAnimFrames`, `GetAnim`/`GetAnimCount` (list a mesh's animations),
  `AnimRate` (negative = scaled by velocity).
- `SetBoneRotation` / `SetBoneDirection` / `SetBoneLocation` exist too (skeletal meshes;
  maybe not Legend's).

## Plan, in order
1. **Bone test:** bend one knee 30 degrees with MeshNodeSetRotation every tick (ParentNode and
   RefPose spaces), then take a screenshot. If it shows, foot IK is possible; if not, only
   mesh-offset tricks are left.
2. **Speed-matched legs:** choose walk/run/idle from horizontal speed, set the rate from
   speed / the cycle's stride, idle when nearly still (no slow-motion walk).
3. **Feet on steps** (only if step 1 works): trace down under each foot bone; lower the pelvis
   by the lower foot's offset (capped at about 20); two-bone IK on the higher leg (law of
   cosines); ankle along the floor normal. Skip it while running.
4. Turning while standing: VRIK-style procedural steps, later.
5. The user joked "inb4 we build a dynamic animation system": a full procedural locomotion
   layer (Rosen/Overgrowth style, springs and a few key poses) is the far end of this.

## Sources (research agent, 2026-10-02)
- Froyok, True First Person Camera in UE4: https://www.froyok.fr/blog/2018-06-true-first-person-camera-in-unreal-engine-4/
- Mirror's Edge first-person movement: https://www.gameanim.com/2010/11/05/creating-first-person-movement-for-mirrors-edge/
- David Rosen, GDC 2014 procedural animation: https://www.youtube.com/watch?v=LNidsMesxSE
- Johansen, Locomotion System: https://runevision.com/thesis/ , https://github.com/runevision/LocomotionSystem
- Little Polygon, procedural locomotion: https://blog.littlepolygon.com/posts/loco1/
- Final IK VRIK: http://www.root-motion.com/finalikdox/html/page16.html
- VRChat full-body tracking: https://docs.vrchat.com/docs/full-body-tracking
- UE4 IK setups: https://docs.unrealengine.com/4.26/en-US/AnimatingObjects/SkeletalMeshAnimation/IKSetups
- Smoothing MaxStepHeight (mesh offset interp): https://forums.unrealengine.com/t/smoothing-out-maxstepheight-behaviour/459841
- Gmod Enhanced Camera: https://github.com/elizagamedev/gmod-enhanced-camera ; gs_legs: https://github.com/Kefta/gs_legs
- tr7zw FirstPersonModel: https://github.com/tr7zw/FirstPersonModel
- Skyrim Improved Camera SE: https://www.nexusmods.com/skyrimspecialedition/mods/93962

Test scripts: U2Pilot scripts/fp_down.txt, fp_stairs.txt, fp_stairs_dir.txt, fp_tuta_walk.txt.
