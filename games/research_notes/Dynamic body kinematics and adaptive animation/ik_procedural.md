# Real-time IK and procedural body kinematics for game characters (target: Advent Rising / UE2 UnrealScript)

## Which IK solvers exist, what do they cost, and which suit a slow scripting language with few iterations?

### Takeaway
For UnrealScript the best fit is closed-form solving: an analytic two-bone (law-of-cosines) solver for legs and arms, plus single-joint aim rotations spread across spine, neck and head. Each costs a fixed handful of acos, cross and normalize calls per limb with no iteration. FABRIK is the cheapest iterative solver per iteration and converges about 10x faster than CCD, so it is the fallback for longer chains such as tails and tentacles. Jacobian methods (transpose, pseudo-inverse, DLS) take about 1,000x more iterations and are not viable in script. Full-body solvers (Final IK FBBIK, Unreal PBIK, Unity Animation Rigging) are native, iterative and multi-effector, so they would only be possible through the DLL hook.

### Cited Findings
**FABRIK (Aristidou & Lasenby 2011)**
- Published in Graphical Models 73(5):243–260, 2011 (DOI 10.1016/j.gmod.2011.05.003). It avoids rotational angles and matrices and works in position space: each joint is placed by "finding a point on a line", in a backward pass from the end effector followed by a forward pass from the root. — [FABRIK paper PDF](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf); [author page](https://www.andreasaristidou.com/FABRIK)
- Table 1 averages 20 runs on a 10-joint unconstrained chain, in unoptimised MATLAB on a 2.2 GHz Pentium Dual-Core. Reachable target: FABRIK 15.5 iterations, 13.3 ms, 0.86 ms/iteration. CCD 26.3 iterations, 123.6 ms, 4.69 ms/iteration. Jacobian Transpose 1,311 iterations, 12.99 s. Jacobian DLS 999 iterations, 10.48 s. SVD-DLS 809 iterations, 9.30 s. FTL 21.1 iterations, 20.5 ms. Triangulation 1 iteration, 57.5 ms. — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- Unreachable target: FABRIK 67.6 iterations, 62 ms. CCD 390 iterations, 3.93 s. Jacobian Transpose 6,549 iterations, 33.9 s. In the unconstrained unreachable case FABRIK can finish in 1 iteration (0.2 ms), because it simply points the chain straight at the target. — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- The authors say FABRIK is "approximately 10 times faster than the CCD method and a thousand times faster than the Jacobian-based methods" for large end-effector movements. Their Fig. 11 setup was a 900 mm chain with the target 600 mm away and a tolerance of 1e-3 mm. — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- On CCD's quality: it "can roll and unroll itself" before reaching the target and overemphasises the joints near the end effector. It behaves better when the target is close to the end effector or the frame rate is high, which is the typical per-frame tracking case. — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- On Jacobian methods: they handle multiple end effectors naturally. Constraints are not straightforward to add, and pseudo-inverse variants suffer from singularities (Transpose and DLS do not). They converge slowly because each step is a small linear approximation, and they can oscillate when tracking moving targets. The DLS damping used in the paper was k = 1.1, following Buss & Kim. — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- On Triangulation: the poses look unnatural (joints near the end stay straight), it cannot handle multiple end effectors, and it fails to reach the target when constrained. — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- FABRIK joint limits use rotational limits defined by conic sections (circle, ellipse or parabola per quadrant) plus orientational (twist) limits. A target outside the cone is re-projected to the nearest point on the conic section. — [FABRIK paper, §4, Algorithm 3](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- FABRIK multi-end-effector tests include a Y-shaped body (10 joints, 2 effectors), a hand (26 joints, 5 effectors) and a humanoid (13 joints, 5 effectors). — [FABRIK paper](https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf)
- Final IK's practical notes on FABRIK: it usually needs fewer iterations than CCD, but each iteration is slower, especially with rotation limits. "Each limit reduces the solver's stability and continuity." Its parameters are target, weight, tolerance, maxIterations and useRotationLimits. — [Final IK FABRIK docs (RootMotion)](http://www.root-motion.com/finalikdox/html/page6.html)
  - Conflict: the paper measured FABRIK as having the cheapest iteration (0.86 ms vs 4.69 ms for CCD in MATLAB), while Final IK says a FABRIK iteration is slower than a CCD one. The difference is probably down to implementation and constraints. Measure in your own code.

**Jacobian family (Buss)**
- Buss's survey "Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares Methods" (unpublished, Oct 2009) covers the Jacobian transpose, pseudo-inverse, SVD analysis and DLS methods. It also proposes forming the Jacobian from target positions. A companion paper, "Selectively Damped Least Squares" (Buss & Kim, J. Graphics Tools 10(3), 2005), extends DLS. — [Buss IK methods page](https://mathweb.ucsd.edu/~sbuss/ResearchWeb/ikmethods/index.html); [survey PDF](https://mathweb.ucsd.edu/%7esbuss/ResearchWeb/ikmethods/iksurvey.pdf)
  - Caution: a Crossref record cites this survey as an IEEE J. Robotics & Automation article, which conflicts with the author's own statement that it is unpublished. — [Crossref](https://api.crossref.org/works/10.1145%2F3061639.3062223)

**Analytic two-bone IK**
- Daniel Holden's method has no iteration. First, clamp the reach to [eps, l1+l2−eps]. Second, compute the desired hip and knee interior angles with the law of cosines: `acos((lcb²−lab²−lat²)/(−2·lab·lat))` and `acos((lat²−lab²−lcb²)/(−2·lab·lcb))`. Third, rotate both joints by the angle difference about the bend axis `normalize(cross(c−a, b−a))`. Fourth, swing the hip about `cross(c−a, t−a)` to put the heel on the target. Clamp every dot product to [−1, 1] before calling acos. — [Orange Duck: Simple Two Joint IK](https://theorangeduck.com/page/simple-two-joint)
- On swivel and pole: by default the bend plane is inherited from the current animated pose, which keeps the animator's knee direction. For a nearly straight leg, a more stable bend axis is `cross(c−a, d)`, where d is a reference direction such as the knee's forward axis. — [Orange Duck: Simple Two Joint IK](https://theorangeduck.com/page/simple-two-joint)
- ozz-animation's IKTwoBoneJob takes these inputs:
  - model-space matrices, and outputs correction quaternions for the local transforms
  - a mid-joint axis (a positive rotation about it opens the joint)
  - a pole vector
  - a twist angle about the start-to-end axis
  - a soften ratio that stops the chain from snapping straight
  - a "reached" output flag
  — [ozz-animation IK docs](https://guillaumeblanc.github.io/ozz-animation/documentation/ik/)
- Godot 4.6 TwoBoneIK3D is described as a rotation-based "intersection of two circles" solver. It needs a pole target and is deterministic: it builds a plane from the joints and the pole and controls twist through the pole direction. It treats any intermediate bones as straight virtual bones. — [Godot TwoBoneIK3D class docs (4.x)](https://godot-pl.readthedocs.io/pl/4.x/classes/class_twoboneik3d.html); [Godot blog: IK returns in 4.6](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)

**Full-body IK in commercial engines**
- Unreal's PBIK ("Full Body IK" plugin, Experimental FullBodyIK folder) is built "on a position-based solver at its core" and solves multiple chains under one root with multiple effectors. Each effector has these settings:
  - chain depth
  - pull-chain alpha, which partitions the skeleton into chains from each effector to the nearest fork. The docs say it can significantly improve convergence on dense chains but may misbehave on highly constrained chains such as robot arms.
  - position, rotation and strength alphas
  - pin rotation
  It also has pin and joint constraints. — [Epic PBIK API](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/PBIK); [FEffectorSettings](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/PBIK/FEffectorSettings)
- Unreal's IK Rig FBIK has an Iterations setting. High counts "can help solve complex joint configurations with competing constraints, but will increase runtime cost". — [FIKRigFBIKSettings](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/IKRig/FIKRigFBIKSettings)
- Unity's Animation Rigging package provides predefined constraints built on the C# Animation Jobs API, including Two Bone IK, Chain IK, Multi-Aim and Damped Transform. Damped Transform smooths position and rotation from a source to a constrained object, which gives cheap secondary motion. — [Unity Animation Rigging constraint components](https://docs.unity3d.com/Packages/com.unity.animation.rigging@1.0/manual/ConstraintComponents.html); [Unity Learn: Damped Transform](https://learn.unity.com/tutorial/using-animation-rigging-damped-transform)
- Unity's built-in TFBIK has a max-iterations cap that trades accuracy for cost. — [Unity TFBIK docs](https://docs.unity.cn/cn/tuanjiemanual/ScriptReference/Animations.TFBIK.html)
- Godot 4.6 adds IKModifier3D and its subclasses: TwoBoneIK3D, ChainIK3D, SplineIK3D, IterateIK3D, FABRIK3D, CCDIK3D and JacobianIK3D. Godot 4.4 added LookAtModifier3D, and 4.5 added SpringBoneSimulator3D, BoneConstraint3D and AimModifier3D. — [Godot blog: IK returns in 4.6](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/); [GameFromScratch](https://gamefromscratch.com/inverse-kinematics-ik-return-to-godot/)

**UE2 / Advent Rising API available to script (local engine source)**
- Advent's `Engine/Classes/Actor.uc` (lines 1054–1083) declares:
  - `GetBoneCoords(name)`
  - `GetBoneRotation(name, optional int Space)`
  - `SetBoneRotation(name, optional rotator BoneTurn, optional int Space, optional float Alpha, optional int preCalculatedBone)`
  - `SetBoneDirection(name, rotator BoneTurn, optional vector BoneTrans, optional float Alpha, optional int Space, optional int preCalculatedBone)`
  - `SetBoneLocation(...)`
  - `SetBoneRotationOnly(...)`
  - `SetBoneScale(...)`
  - `AnimBlendParams(...)`
  - `GetRootLocation` / `GetRootRotation` / `LockRootMotion`
  - `GetBoneRotationAtFrame` / `GetBoneOffsetAtFrame`
  The extra `preCalculatedBone` argument is Advent-specific; stock U2 lacks it (compare `Documents\Tools\u2_export\full_Engine\Classes\Actor.uc:1315-1317`). — local file `C:\Users\john\Documents\AdventRising_src\Engine\Classes\Actor.uc`
- Advent already drives arm chains from script. `PlayerController.uc` (around lines 1800–1825) first clears with `SetBoneRotation(bone, noRot, 0.0, 0)`, then sets `SetBoneDirection('rightArm', rotShoulder,,1.0, 2, 0)`, `('rightForeArm', rotElbow,,1.0, 3, 0)` and `('rightHand', rotWrist,,1.0, 4, 0)`. Each bone gets a different Space/slot integer (2–7). `EonCameraSystem.uc:351` aims `Spine2` with `SetBoneDirection('Spine2', rot, , 0, 50)`, and `Turret.uc:180` uses SetBoneRotation for turret pitch and yaw. — local files `C:\Users\john\Documents\AdventRising_src\Engine\Classes\PlayerController.uc`, `...\EonEngine\Classes\EonCameraSystem.uc`, `...\EonVehicles\Classes\Turret.uc`

### Inferences
- Script cost model: one analytic two-bone solve is about 5 acos, 3–4 cross products and a few normalizes. That is roughly 30–60 UnrealScript operations per limb with no loop, so four limbs plus a 4-bone aim chain per pawn per tick should be affordable for a handful of visible pawns. FABRIK at 5–10 iterations over 4–6 joints is maybe 10x that, which is fine for one hero tail or tentacle but not for crowds.
- Prefer solvers whose output is a per-bone rotation delta, because the API sets rotations, not positions. Analytic two-bone and aim/look-at fit this directly. FABRIK produces joint positions, which must be converted back to rotations, adding one more aim-style step per bone.
- `GetBoneCoords` most likely returns the pose from the last skeletal update, which may already include last frame's controllers. That means a one-frame lag and possible feedback. The standard mitigation is to solve against cached animated (pre-IK) bone data, or to compute the full delta each frame with the controllers cleared first. This is unverified; test it in the engine.
- Use CCD only where the "curl from the tip" look is acceptable (tails, cables). Avoid it for human limbs, given the roll/unroll artefacts the FABRIK paper describes.

### Gaps
- No public, quantitative per-frame cost figures were found for Final IK FBBIK, Unreal PBIK or Unity Animation Rigging. Only the qualitative "more iterations, more cost" statements are available.
- Final IK's FBBIK design (its spring/pull/reach/push model and default iterations) could not be retrieved. The fetched RootMotion page covered only FABRIK.
- The exact semantics of UE2's `Space` argument (component vs. local, and Advent's slot numbers 2–7 and 50) and whether `GetBoneCoords` includes bone controllers could not be confirmed. The UDN SkelAnim2 page redirected away.

## Procedural layers: foot placement, hand IK, look-at/aim, reach, recoil/hit additives, secondary motion, inertialization

### Takeaway
All of these layers can be built from two primitives: analytic two-bone IK and aim rotation spread over several bones. A critically-damped spring underneath them gives secondary motion, recoil recovery and transition smoothing. Inertialization (Bollo, Gears of War 4) is especially well suited to script: at a transition it stores one offset per bone and decays it with an exponential spring. Only the destination animation is evaluated, so there is no double-pose blend cost.

### Cited Findings
- Bollo's GDC 2018 talk "Inertialization: High-Performance Animation Transitions in Gears of War" describes the motivation: conventional blended transitions evaluate both source and destination, which roughly doubles animation cost during the transition. The Coalition removed blended transitions and treated transitions as a post-process. The talk covers the math for vectors and quaternions and how to add the technique to an existing engine. Bollo also gave a related SIGGRAPH 2017 talk, "High Performance Animation in Gears of War 4". — [GDC Vault: Inertialization](https://www.gdcvault.com/play/1025331/Inertialization); [SIGGRAPH history: David Bollo](https://history.siggraph.org/person/auto-draft-642)
- Holden's spring-based inertialization has two steps.
  - At the transition, store the offsets: `off_x = (src_x + off_x) − dst_x` and `off_v = (src_v + off_v) − dst_v`.
  - Each frame, decay the offset with a critically damped spring: `y = 2·ln2/halflife`, `j1 = v + y·x`, `x' = e^(−y·dt)·(x + j1·dt)`, `v' = e^(−y·dt)·(v − y·j1·dt)`. Then output `out = in + off`.
  The blend has no fixed duration and needs no stored transition time. It is "very fast" when all bones share one half-life. — [Orange Duck: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- The same article recommends springs for filtering noisy signals, for velocity controllers and for prediction. For extrapolation: `x' = x + (v/y)(1 − e^(−y·dt))`. — [Orange Duck: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- Dead blending is an alternative. It extrapolates the source pose forward with its velocity (decaying that velocity over a half-life) and cross-fades the extrapolated pose into the destination with smoothstep. At the transition it needs only the current pose and velocity, but it damps detail and can cause foot sliding or "mushiness". A learned extrapolator costs about 30 µs per frame. — [Orange Duck: Dead Blending](https://theorangeduck.com/page/dead-blending)
- Aim and look-at chains: ozz's IKAimJob orients one joint's forward vector toward a target, with an up vector and an offset (for example eye position relative to neck). Its look-at sample "iteratively distributes aiming across a chain of joints" (spine to head). The sample also includes foot IK. — [ozz-animation IK docs](https://guillaumeblanc.github.io/ozz-animation/documentation/ik/)
- Secondary motion: Godot 4.5 SpringBoneSimulator3D [Godot blog](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/); Unity Damped Transform [Unity Learn](https://learn.unity.com/tutorial/using-animation-rigging-damped-transform).
- Ubisoft's IK Rig (Alexander Bereznyak, GDC 2016) applies retargeting-like principles at runtime. It reacts in real time to obstacles, prop weight and character states such as tired or wounded, and can turn one base motion into others (for example a male walk into a female crouch). — [GDC Vault: IK Rig Procedural Pose](https://gdcvault.com/play/1022984/IK-Rig-Procedural-Pose); [80.lv: How Ubisoft revolutionises animation](https://80.lv/articles/how-ubisoft-revolutionises-animation-in-games)

### Inferences
These are standard industry practice reconstructed from the primitives above. No single citation covers them; verify in implementation.
- **Foot placement:**
  1. Trace down from each animated foot position to the ground.
  2. Compute each foot's height error.
  3. Lower the pelvis by the larger (most negative) error, so the leg that must reach further down can.
  4. Two-bone solve each leg to its traced point.
  5. Rotate each foot by the rotation from up to the ground normal, clamped to about 30–45°.
  Spring-smooth the pelvis offset and the foot targets (Holden's spring above) to avoid popping. In UE2, set the pelvis offset with `SetBoneLocation` on the root or pelvis bone, or just lower the mesh with PrePivot.
- **Off-hand grip:** Read the weapon's grip socket position (an attachment bone, via GetBoneCoords on the weapon actor or computed from the hand bone plus a fixed offset). Two-bone the off-hand arm to it each tick after aim is applied. The pole is the animated elbow direction.
- **Aim and look-at:** Compute the yaw/pitch delta between the current facing and the target. Spread it across Spine1/Spine2/Neck/Head with weights such as 0.2/0.3/0.2/0.3, clamped per bone. Advent already uses `SetBoneDirection('Spine2', ...)`, so extending it to a weighted chain is a small step.
- **Recoil and hit reactions:** Add a spring impulse (velocity kick) to a per-bone offset rotation on spine, clavicle or head, and let the spring decay it. It costs one spring per affected bone and is applied with `SetBoneRotation` at Alpha 1 as an added delta.
- **Inertialization in UE2:** A script-side approximation is feasible for the bones you control procedurally, by spring-decaying the IK or aim deltas. True pose inertialization of the full skeleton needs the pre-transition pose for every bone (GetBoneCoords per bone at transition) plus per-bone overrides every frame afterwards. That is likely too expensive in script for more than a few characters and is a candidate for the DLL hook.

### Gaps
- The Bollo GDC talk's slides and recording are login-walled. Bollo's own quintic-polynomial formulation (as opposed to Holden's spring version) could not be verified from the source.
- No primary source was found for a specific shipped foot-IK pelvis-adjustment algorithm; the steps above are standard practice.

## Shipped examples: what IK and procedural layers did major games use?

### Takeaway
Public detail is thin and mostly locked in GDC Vault. The confirmed points:
- Gears of War 4: inertialization.
- Overgrowth: procedural animation from very few keyframes, plus physics.
- Uncharted 4: full-body IK and physics layered on climbing.
- The Last of Us Part II: motion matching for locomotion, traversal, melee and cover, plus full-body IK on horses.
- Horizon Zero Dawn: a GDC talk on machine animation tech, IK details unconfirmed.
- Assassin's Creed (Ubisoft): IK Rig runtime pose adaptation.
- Red Dead Redemption 2: NaturalMotion Euphoria physics-driven reactions.
- Ghost of Tsushima: nothing public found.

### Cited Findings
- **Gears of War 4:** inertialization replaced blended transitions to halve transition cost. — [GDC Vault](https://www.gdcvault.com/play/1025331/Inertialization)
- **Overgrowth:** David Rosen's GDC 2014 Animation Bootcamp talk "An Indie Approach to Procedural Animation" shows simple procedural techniques producing interactive, fluid animation from very few keyframes, with examples from Overgrowth, Receiver and Black Shades. — [Game Developer: video of the talk](https://gamedeveloper.com/design/video-an-indie-approach-to-procedural-animation)
  - A community summary claims about 13 keyframes in total for the whole character. This is secondhand. — [Unity forum thread](https://discussions.unity.com/t/an-indie-approach-to-procedural-animation-gdc-video-talk/538228)
- **Uncharted 4:** a Game Informer feature quotes Jeremy Yates describing the climbing system as using "full-body inverse kinematics and full-body physics systems". Nathan's hands behave differently on smaller handholds. — [Game Informer](https://www.gameinformer.com/b/features/archive/2015/01/23/how-uncharted-4-is-taking-game-technology-to-the-next-level.aspx)
- **Uncharted 4:** Michal Mach's GDC 2017 talk covered layering physics simulation over gameplay animation. — [GDC: Naughty Dog deconstructs Uncharted 4's physics animation](https://www.gdconf.com/news/see-naughty-dog-deconstruct-uncharted-4s-physics-animation-gdc-2017)
- **The Last of Us Part II:** GDC 2021 "Motion Matching in The Last of Us Part II" by Michal Mach and Maksym Zhuravlov. — [Naughty Dog at GDC 2021](https://www.naughtydog.com/blog/naughty_dog_at_gdc_2021)
- **The Last of Us Part II:** Mach's reel says motion matching was used for locomotion, traversal, melee and cover, and gives reliable foot matching when blending into traversal. He also set up the horse's full-body IK parameters and the ragdoll for riders. — [Michal Mach TLOU2 reel (Vimeo)](https://vimeo.com/433024043)
- **Horizon Zero Dawn:** Richard Oud's GDC 2018 talk "Animation Bootcamp: Bringing Life to the Machines of Horizon Zero Dawn" covers reference, motion style, workflow, animation tech and AI. The abstract does not mention IK. — [GDC Vault](https://gdcvault.com/play/1025040/Animation-Bootcamp-Bringing-Life-to); [80.lv](https://80.lv/articles/horizon-zero-dawn-beasts-animation-production)
- **Assassin's Creed (Ubisoft):** IK Rig was built at Ubisoft Toronto as a systemic, cross-project animation system. — [80.lv interview](https://80.lv/articles/how-ubisoft-revolutionises-animation-in-games); [GDC Vault](https://gdcvault.com/play/1022984/IK-Rig-Procedural-Pose)
- **Red Dead Redemption 2:** Rockstar uses NaturalMotion Euphoria (licensed in 2007 and used in GTA IV, RDR, Max Payne 3, GTA V and RDR2), which mixes physics, AI and authored animation. Rockstar's Phil Hooker said it was "really evolved" for RDR2 for human and animal reactions: being dragged in the stirrups, being trapped under a dead horse, reaching for a lasso. — [Wccftech interview](https://wccftech.com/rockstar-euphoria-evolved-rdr2/amp/); [Wikipedia: NaturalMotion](https://en.wikipedia.org/wiki/NaturalMotion)
- **Ghost of Tsushima:** the Sucker Punch GDC 2021 talks found cover procedural grass, the guiding wind and open-world systems. None covers IK or character procedural animation. — [GDC Vault: Procedural Grass](https://gdcvault.com/play/1027214/Advanced-Graphics-Summit-Procedural-Grass); [GDC news: guiding wind](https://gdconf.com/news/see-how-ghost-tsushima’s-guiding-wind-came-life-gdc-2021)

### Inferences
- The shipped AAA pattern is a base pose (clips or motion matching), then post-process IK (feet, hands, aim), then physics or spring layers, with inertialization or blending for transitions. Overgrowth shows that a small team can get most of the responsiveness from procedural layers over few poses. That is the most relevant model for a script-level mod.
- Euphoria-style active ragdoll is out of reach for UE2 script. It would need Karma motors, which the separate Advent physics plan covers.

### Gaps
- No public talk was found on The Last of Us Part II's foot IK or look-at, Ghost of Tsushima's character IK, Horizon's machine leg IK, or Assassin's Creed's shipped foot and hand IK. The relevant GDC slides are behind GDC Vault login.

## Open-source implementations and licences

### Takeaway
The best permissive references to port from are:
- ozz-animation (MIT, C++): two-bone, aim, look-at and foot IK samples.
- TheComet/ik (MIT, C89): FABRIK plus 2-bone and 1-bone solvers.
- Caliko (MIT, Java): FABRIK with constraints.
- Godot 4.6 (MIT, C++): TwoBoneIK3D, FABRIK3D, CCDIK3D, JacobianIK3D, spring bones and look-at.
- Holden's articles: formulas only, and no licence was stated on the pages.

Final IK is a paid Unity Asset Store product, so use it for reference only.

### Cited Findings
- **ozz-animation:** MIT licence, copyright Guillaume Blanc. Two-bone IK, aim IK, and look-at and foot IK samples. — [ozz-animation IK docs](https://guillaumeblanc.github.io/ozz-animation/documentation/ik/)
- **TheComet/ik:** C89 with no dependencies, MIT licence. FABRIK plus specialised 2-bone and 1-bone solvers, with target rotations. Joint constraints are "in progress", and it has a benchmarks build flag. — [GitHub: TheComet/ik](https://github.com/TheComet/ik)
- **Caliko:** Java FABRIK with 2D and 3D chains, MIT licence, and a core module with no dependencies. Published in the Journal of Open Research Software in 2016. — [GitHub: FedUni/caliko](https://github.com/FedUni/caliko); [DOAJ record](https://doaj.org/article/7b9626bc30a0408daea4888ad3cfd2ff)
- **Rust crate `fabrik`:** MIT licence, basic 2D and 3D chains only, with joint restrictions still on the roadmap. — [docs.rs fabrik](https://docs.rs/crate/fabrik/0.1.0)
- **Godot 4.6 IK nodes:** the engine is MIT-licensed (general knowledge; the licence page was not fetched). — [Godot blog](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/)
- **Orange Duck spring and inertialization code:** linked from the articles to the author's GitHub repos (Motion-Matching, Spring-It-On). The articles do not state a licence. — [Dead Blending](https://theorangeduck.com/page/dead-blending)

### Inferences
- For UnrealScript, port formulas rather than code. Holden's two-joint IK plus the ozz aim/look-at approach cover feet, hands and spine. A port of TheComet/ik's FABRIK loop (C89, simple vector math) maps cleanly to UnrealScript vectors if a tail or tentacle chain is needed.
- If the DLL hook route is taken, ozz-animation (MIT, C++) or TheComet/ik (MIT, C) can be linked natively. Both fit the user's preference for licences compatible with non-commercial GPL mods.

### Gaps
- The licence files for the Godot repo and Holden's GitHub repos were not fetched or verified here.
- No MIT-licensed, general-purpose C++ FABRIK library with full joint constraints was confirmed. TheComet/ik's constraints are unfinished.
