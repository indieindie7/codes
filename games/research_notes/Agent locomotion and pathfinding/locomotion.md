# Procedural and physics-based character locomotion (for a UE2 / Advent Rising build 2226 target)

Context assumed: UnrealScript can call SetBoneRotation/SetBoneDirection; Karma ragdolls with self-authored .ka files; ActorX .psa clips; no source to native animation; a hooking DLL can inject native code. Research run 2026-10-08; about 20 tool calls. Many GDC talks are behind the GDC Vault login, so talk contents are often known only from listings and summaries (flagged below).

## 1. Cheap procedural layers over canned animation (foot IK, warping, lean, look-at, hip height, hit additives)

### Takeaway
The best value for the cost is a post-animation layer that runs after the clip is sampled. It has four parts: (a) a ground probe plus analytic two-bone leg IK plus pelvis lowering, (b) foot locking during contact, (c) stride/speed warping so foot spacing matches the capsule speed, and (d) a capsule-to-mesh "adjustment" damper. All four need only per-frame bone overrides, which UnrealScript SetBoneRotation already gives us. Daniel Holden's own advice is that foot locking is hard to make look good, and that a little sliding often looks better than a distorted pose.

### Cited Findings
- **Stride warping (UE5 AnimationWarping plugin):** changes the animated stride so foot spacing matches capsule speed, which removes per-speed playback tuning. Stride scale = locomotion speed / root-motion speed. Stride Scale 1 = default warp, 0.5 halves the stride, 2 doubles it. — [Epic: Pose Warping in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/pose-warping-in-unreal-engine)
- **Orientation warping (same plugin):** warps the leg IK bones separately to match the locomotion direction, and twists the spine so the upper body keeps facing the chosen way. The warp angle is the rotation between the root-motion direction and the locomotion direction. A delta-angle threshold (default 90 deg, 0 disables it) guards against extreme warps. Its stated purpose is fewer in-between/blendspace clips. The plugin also contains Slope Warping, which the Chinese docs mark as still in development and not for shipping. — [Epic: Pose Warping](https://dev.epicgames.com/documentation/unreal-engine/pose-warping-in-unreal-engine); [AnimationWarping plugin API](https://dev.epicgames.com/documentation/unreal-engine/API/PluginIndex/AnimationWarping)
- **UE5 foot placement lock types:** UE5 ships a foot-placement node with lock-type settings (EFootPlacementLockType). This confirms foot locking is a standard production layer. — [Epic API: EFootPlacementLockType](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/AnimationWarpingRuntime/EFootPlacementLockType)
- **Holden's foot-locking recipe:** contact starts → lock point = the foot's ground-projected position. While locked, feed an inertializer that fixed point with zero velocity. Unlock when contact ends, or when the lock drifts beyond an `unlock_radius` from the animated foot, then inertialize back to the animation. Compute the heel target from the locked toe and pin it with a two-joint IK. Extras: stop ground penetration and bend the toe on contact. Caveat: "foot locking is hard to make look good"; small sliding often beats a distorted pose. — [Holden, "Code vs Data Driven Displacement"](https://theorangeduck.com/page/code-vs-data-driven-displacement)
- **Capsule vs mesh synchronization:**
  - Snapping the character to the simulation gives direct control but causes sliding and spinning.
  - Snapping the simulation to the character gives less sliding but feels sluggish.
  - Recommended: let both move, then pull the character toward the simulation each frame with a damper, rate `1 - 2^(-dt/halflife)`.
  - Rotate more slowly than you translate.
  - Cap the correction at `0.5 * speed * dt` (linear) and `0.5 * angular_speed * dt` (angular). Because of the cap, a standing or plant-turning character barely slides.
  - Clamp the maximum distance/angle between the two.
  — [Holden, same article](https://theorangeduck.com/page/code-vs-data-driven-displacement)
- **Holden's IK and foot-locking article:** covers two-bone IK on the toe target, runtime foot locking via inertialization, automatic contact annotation of clips, and offline foot-slide removal. The full source is reportedly on GitHub. I could only reach aggregator copies, not the original page. — [zeli.app summary of "Inverse Kinematics and Foot Locking"](https://zeli.app/de/story/49595505)
- **Unity Animation Rigging:** ships Two Bone IK and Multi-Aim constraints, built on the C# Animation Jobs API. Multi-Aim is a procedural look-at; a blog example uses Two Bone IK for lower-body correction. — [Unity Animation Rigging 1.0 constraint list](https://docs.unity3d.com/Packages/com.unity.animation.rigging@1.0/manual/ConstraintComponents.html); [Unity blog: character and props interaction](https://blog.unity.com/es/games/advanced-animation-rigging-character-and-props-interaction)
- **Overgrowth (David Rosen, GDC 2014 Animation Bootcamp, about 30 min):** "simple procedural techniques" for fluid, interactive animation from very few keyframes, with examples from Overgrowth, Receiver and Black Shades. Rosen argues animation and code should work more closely together, so code takes over repetitive animator work. A Unity forum user claims the demo character used only 13 keyframes in total (unverified forum claim). — [Game Developer write-up](https://gamedeveloper.com/design/video-an-indie-approach-to-procedural-animation); [GDC Vault](http://www.gdcvault.com/play/1020583/Animation-Bootcamp-An-Indie-Approach); [Unity forum thread](https://discussions.unity.com/t/an-indie-approach-to-procedural-animation-gdc-video-talk/538228)
- **Motion matching uses the same idea:** Clavet's trick is that only a few bones need to match, mostly foot positions and velocities. This supports the idea that players read "proper walking" mainly from the feet. — [Game Developer: most inspiring animation tech talks of 2016](https://gamedeveloper.com/programming/most-inspiring-game-animation-tech-talks-of-2016)

### Inferences
- **All of these fit in UnrealScript.** Each technique is a per-frame bone override. Two-bone IK is analytic (law of cosines plus a pole/knee vector), so it costs a few trig calls per leg. UnrealScript SetBoneRotation (with alpha blend) on thigh, calf and foot, plus a pelvis offset, is enough.
  - The hard parts: reading the animated bone's world position before the override (GetBoneCoords, if Advent exposes it), and knowing the bone axis conventions in Advent's skeleton.
  - Ground probe: one Trace per foot.
  - Hip lowering: drop the pelvis by the lower foot's ground delta (clamped), smoothed with a damper.
- **Lean, look-at and hit additives are cheaper still.**
  - Lean/bank into turns: roll the spine/pelvis by k * (lateral acceleration or yaw rate * speed), damped.
  - Look-at: SetBoneDirection on head/neck, with angle limits and a damper.
  - Hit reaction: add a short decaying rotation impulse (spring-damper) to the spine/clavicle bones in the hit direction.
  These are the "procedural layer" items that Rosen-style work leans on. This is my synthesis, not from a single source.
- **Stride warping without native access:** change the clip's playback rate to speed / authored root speed, within limits. Beyond those limits, scale thigh pitch amplitude, or blend walk/run by speed. True stride warping (moving IK foot targets along the travel direction) needs the IK layer above.
- **Warping fits Advent best.** It keeps the authored clips, so the art style survives, and degrades gracefully when turned off.

### Gaps
- The Overgrowth talk's details (keyframe interpolation, how the walk cycle is driven by speed, ragdoll blending) are behind GDC Vault. I could not verify them, and summaries give no technical specifics.
- I could not reach the original orangeduck "Inverse Kinematics and Foot Locking" page or confirm its licence (orangeduck's Motion-Matching repo is MIT, see section 4).
- I found no GDC foot-IK talk beyond these (e.g. specific Naughty Dog or Guerrilla foot IK talks) in this pass.

## 2. Fully procedural gaits for multi-legged and creature agents (spiders, hounds)

### Takeaway
Procedural walkers converge on one recipe:
- Each foot stays planted until it drifts too far from a predicted rest target. The target is the rest offset plus velocity * lookahead, raycast onto the ground.
- The foot then steps along an arc.
- Legs are grouped so that opposite groups alternate.
- The body height and tilt follow the average foot plane through a spring.

Rain World and Spore show the extremes: point-chain soft bodies with cosmetic limbs, versus morphology-independent animation solved by IK. Learned quadruped gait (MANN) exists but needs dog mocap and a neural-network runtime.

### Cited Findings
- **Spider Walker (Blender add-on) step logic:**
  - Estimate body velocity from the body bone.
  - Predicted target = the leg's rest position relative to the body, shifted forward by speed along the travel direction.
  - When the planted foot drifts far enough from the target, raycast down from the target onto collision to find a landing point, and step.
  - Legs step in list order, so they don't move in unison; planting ahead of the body avoids dragging.
  Licence not confirmed; the author says parts of the code were AI-assisted. — [Digital Production: Spider Walker](https://digitalproduction.com/2026/08/28/spider-walker-automates-multi-leg-animation/); [80.lv](https://80.lv/articles/free-blender-tool-for-procedural-spider-walks)
- **Rain World (Joar Jakobsson):**
  - Creatures are points in space joined at set distances (distance constraints), with a paper-doll set of sprites drawn over them. This makes them soft and bendable, able to move through nearly any environment.
  - The slugcat is two spherical body chunks at a fixed distance; its limbs and tail are cosmetic and animated procedurally from the player's inputs.
  - Jakobsson moved from mixing classical and procedural animation toward fully procedural.
  - A GDC 2016 Animation Bootcamp session (Jakobsson and James Therrien) exists, but I found no slides.
  — [Game Developer: Rain World ecosystem](https://gamedeveloper.com/design/crafting-the-complex-chaotic-ecosystem-of-i-rain-world-i-); [Unity blog: procedural design in Rain World](https://unity.com/en/blog/exploring-procedural-design-rain-world); [gameanim.com listing](https://www.gameanim.com/category/learn/presentations/page/8/)
- **Spore (Hecker et al., SIGGRAPH 2008, ACM TOG 27(3) art. 27):**
  - Animators keyframe in a custom tool ("Spasm").
  - Motion is stored in a morphology-independent form (structure plus style), retargeted at runtime into pose goals for a "robust and efficient" IK solver.
  - This lets one set of animations drive creature skeletons the animators have never seen.
  — [Hecker's paper page](https://chrishecker.com/Real-time_Motion_Retargeting_to_Highly_Varied_User-Created_Morphologies); [PDF copy](https://www.cse.chalmers.se/edu/year/2011/course/TDA361/Advanced%20Computer%20Graphics/027-hecker%20copy.pdf); [talk: How To Animate a Character You've Never Seen Before](https://chrishecker.com/How_To_Animate_a_Character_You%27ve_Never_Seen_Before)
- **MANN (Zhang, Starke, Komura, Saito, SIGGRAPH 2018):**
  - A gating network blends expert weight sets of a motion-prediction network, trained end-to-end on unstructured dog mocap, with no hand-labelled gait phases.
  - Covers periodic gaits (walk, pace, trot, canter) and non-periodic actions.
  - Unity prototype plus TensorFlow.
  - About 2 ms/frame per a Starke forum post, not stated in the paper.
  — [80.lv](https://80.lv/articles/mode-adaptive-neural-networks-for-quadruped-motion-control); [GameDev.net thread](https://gamedev.net/forums/topic/696849-siggraph-2018-mode-adaptive-neural-networks-for-quadruped-motion-control); [SIGGRAPH history](https://history.siggraph.org/?p=100804)

### Inferences
- **A UE2 hound/spider walker is a pure UnrealScript job.** It needs:
  - per-leg state (planted pos, step start/end, step timer);
  - a lookahead target plus Trace;
  - an arc lerp for the swing (sine lift);
  - two-bone (or three-bone for digitigrade hind legs) IK through SetBoneRotation;
  - body height/pitch/roll from the planted-foot plane with a critically damped spring.
- **Gait timing for quadrupeds:** pair legs into alternating groups, or use fixed phase offsets.
  - Trot: diagonal pairs in phase, offset 0.5.
  - Walk: four-beat, offsets around 0, 0.25, 0.5, 0.75.
  - Gallop: front and rear pairs nearly in phase.
  These are standard biomechanics values from my background knowledge; I found no source in this pass.
- **Rain World-style Verlet chains** (distance constraints iterated a few times per tick) are cheap and engine-agnostic. They would suit tails, tentacles or worm-like enemies in UE2.

### Gaps
- I did not find a confirmed MIT/BSD-licensed spider/quadruped procedural walker repo in this pass. Search GitHub with a licence filter next.
- I found no primary source for quadruped footfall phase offsets.

## 3. Physics-based control: active/powered ragdolls, SIMBICON, Euphoria, partial ragdoll hit reactions, and Karma feasibility

### Takeaway
"Physical animation", a PD/spring per joint driving the ragdoll toward the animated pose, is the practical tier: an animated character that reacts physically, with partial-ragdoll hit reactions. Full balance controllers (SIMBICON, Euphoria) are much harder:
- SIMBICON's reference implementation ran ODE at a 5 ms step (a 2D variant at 0.1 ms).
- It used torque limits around 90-1000 Nm and world-frame torso/swing-hip control.
- Euphoria built a full biomechanical "dynamic balancer".

In Karma we should expect stability limits: the mass-ratio limit is ≤100 per Epic's KAT docs. Partial/powered ragdoll for reactions is feasible; a standing, walking SIMBICON biped is a research project.

### Cited Findings
- **SIMBICON (Yin, Loken, van de Panne, SIGGRAPH 2007, ACM TOG 26(3) art. 105), control structure:**
  - A finite state machine of target poses.
  - Every joint uses PD control, τ = kp(θd − θ) − kd·θ̇. The target poses "are typically not actually achieved".
  - The torso and swing hip have targets in the world frame. Stance-hip torque = −τ_torso − τ_swing, so the torso stays upright using only internal torques.
  — [SIMBICON paper PDF](https://www.cs.ubc.ca/~van/papers/2007-siggraph-simbicon.pdf)
- **SIMBICON balance feedback:**
  - θd = θd0 + cd·d + cv·v on the swing hip, where d and v are the horizontal COM distance and velocity relative to the stance ankle.
  - cd and cv are usually in [0,1]. The basic 3D walk uses cd = 0.5, cv = 0.2 in both planes.
  — [SIMBICON paper](https://www.cs.ubc.ca/~van/papers/2007-siggraph-simbicon.pdf)
- **SIMBICON simulation setup:**
  - 3D biped in ODE 0.6, 0.005 s time step, LCP contacts, friction 0.8.
  - The 2D model used a 0.0001 s step, penalty ground (kp = 100000 N/m, kd = 6000 Ns/m), friction 0.65, torque limits 1000 Nm (370 Nm for all but the fast run). The basic walk needs at least 90 Nm or it "becomes weak-kneed and falls".
  - Ran 5x faster than real time, unoptimized, on a 1.8 GHz Core Duo (as stated in the paper; I did not confirm which model this refers to).
  - Robust to a 350 N, 0.2 s diagonal push to the torso, plus unexpected steps, slopes and parameter changes.
  - Mocap-driven variants use feedback-error learning for low-gain tracking.
  — [SIMBICON paper](https://www.cs.ubc.ca/~van/papers/2007-siggraph-simbicon.pdf); [project page](https://www.cs.ubc.ca/~van/papers/Simbicon.htm)
- **GENBICON:** follow-up that improves balance with an inverted-pendulum foot-placement model. — [search summary of SIMBICON-related work](https://www.cs.ubc.ca/~van/papers/Simbicon.htm) (secondary; not read directly)
- **Euphoria / NaturalMotion:**
  - "Dynamic Motion Synthesis": real-time simulation of biomechanics and motor control, based on Oxford research.
  - First shipped in GTA IV (Rockstar, announced 2007).
  - Fan sources describe a core dynamic balancer, plus behaviours such as grabbing wounds, catching a fall and protecting the body (treat the behaviour list with caution).
  — [Wikipedia: NaturalMotion](https://en.wikipedia.org/wiki/NaturalMotion); [Oxford innovation note](https://innovation.ox.ac.uk/?p=8954); [gta4.net 2007](https://www.gta4.net/news/3822/rockstar-to-use-naturalmotions-euphoria-engine/)
- **UE physical animation:**
  - UE5's PhysicsControl plugin drives bodies toward animation with damped springs set by strength, damping ratio (1 = critical, no overshoot), extra damping, and a target-velocity multiplier (1 = track the animation's velocity).
  - The older Physical Animation component arrived in UE 4.14.
  — [Epic API: FPhysicsControlData](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/PhysicsControl/FPhysicsControlData?lang=en-US); [Borui Liao, physics-based character animation in UE](https://boruiliao.medium.com/what-is-physics-based-character-animation-in-games-using-unreal-engine-approach-as-an-example-571560376e4c)
- **Karma in UE2, structure:**
  - The ragdoll is a skeleton physics asset with per-bone masses and joint limits, attached via KarmaParamsSkel.KSkeleton.
  - KAddBoneLifter applies lifting forces independently of other forces; set bBlockKarma false first or results are erratic.
  - Ragdoll queue: creating one when full is unpredictable, and KMakeRagdollAvailable purges the oldest.
  - Destroying an actor inside KImpact reportedly crashes the engine.
  — [UDN: Karma Reference](https://docs.unrealengine.com/udk/Two/KarmaReference.html); [UDN: Ragdolls in UT2003](https://docs.unrealengine.com/udk/Two/RagdollsInUT2003.html); [Unreal Wiki: Karma Functions and Events](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Functions_And_Events.html)
- **Karma authoring constraints:** KAT units are 50x smaller than Unreal units (scale 0.02), and the largest-to-smallest mass ratio should stay ≤ 100. — [UDN: Karma Authoring Tool](https://udn.epicgames.com/Two/KarmaAuthoringTool.html)

### Inferences
- **Powered ragdoll in Advent needs native access.**
  - The script API exposes bone lifters, but not, as far as I found, per-joint motor targets.
  - Option A: the DLL hook calls MathEngine/Karma joint functions (e.g. limited angular motors, or applying torques τ = kp(θanim − θ) − kd·ω per body per tick).
  - Option B (script-only approximation): bone lifters plus impulses (KAddImpulse) on the pelvis/chest to keep a falling ragdoll "struggling".
- **Gains:** PD gains must be tuned against the substep rate. A 5 ms step was needed for SIMBICON in ODE, and UE2 ticks Karma at the frame rate with its own substeps. Use critically damped gains: kd ≈ 2·sqrt(kp·I_eff).
- **Partial-ragdoll hit reaction is the cheapest physical win,** and it can be done kinematically, without real physics: a spring-damper additive on the upper-body bones in the hit direction, plus optional lifters. Full SIMBICON-style walking for gameplay NPCs is not worth it in Karma.
- **What makes physical motion read as real:** visible weight transfer and recovery steps after a push (SIMBICON's foot-placement feedback), and limbs that collide with and react to the world. Euphoria's GTA IV reputation rests on stumbling and recovery, not on its normal walk.

### Gaps
- I found no source on MathEngine Karma's solver type, iteration counts or joint-motor API, or on whether UE2 exposes Karma joint motors to native code. Ghidra on Advent's Engine.dll/Karma exports is the way to answer this; see the existing "Advent physics plan" memory.
- I found no published measurements of Karma ragdoll stability under PD driving.
- Euphoria internals are proprietary; I found no technical paper.

## 4. Data-driven: motion matching, learned motion matching, PFNN/MANN, DeepMimic/AMP/ASE (runtime needs; could one run in a 2005 engine?)

### Takeaway
Motion matching is a nearest-neighbour search over a feature database: foot positions and velocities, hip velocity, future trajectory points. Its CPU cost is low (a 2005-era CPU can brute-force a few thousand frames), but it needs long mocap takes and a full pose-playback path we do not have natively (we only have .psa clips). Learned/neural variants shrink memory to network weights: PFNN reports 0.8-1.8 ms and 10-125 MB. Physics RL policies (DeepMimic/AMP) need PD-driven ragdolls plus small MLP inference at about 30 Hz, but they are trained in a different simulator and would not transfer to Karma.

### Cited Findings
- **Motion matching (Clavet, Ubisoft, GDC 2016, For Honor):** continuously finds the mocap frame matching the current pose and the desired future trajectory, then blends there with a short transition. The output looks almost like raw mocap while staying responsive. Data comes from long unstructured takes (5-10 minutes of someone running around) instead of authored transitions. — [GDC Vault listing](https://gdcvault.com/play/1022985/Motion-Matching-and-The-Road); [CG World GDC 2016 report](https://cgworld.jp/feature/1604-gdc2016-03-2.html); [Game Developer: 2016 animation tech talks](https://gamedeveloper.com/programming/most-inspiring-game-animation-tech-talks-of-2016)
- **Kristjan Zadziuk (Ubisoft):** gave a separate GDC 2016 motion matching talk (Animation Bootcamp). I found no content summary. — [gameanim.com motion matching tag](https://www.gameanim.com/tag/motion-matching/)
- **Learned Motion Matching (Holden, Kanoun, Perepichka, Popa, SIGGRAPH 2020):** replaces each MM component with a network (decompressor, stepper, projector). Memory is just the network weights and does not grow with data, whereas plain MM memory grows linearly with data. — [Holden: Learned Motion Matching](https://www.theorangeduck.com/page/learned-motion-matching); [SIGGRAPH history](https://history.siggraph.org/?p=78733)
- **2023 follow-up ("Learning Robust and Scalable Motion Matching"):** says LMM cut memory but raised CPU cost. The follow-up uses about 80% of LMM's memory with much lower CPU. — [ACM/unpaywall 10.1145/3623264.3624442](https://unpaywall.org/10.1145%2F3623264.3624442)
- **Reference implementation [orangeduck/Motion-Matching](https://github.com/orangeduck/Motion-Matching):**
  - MIT-licensed C++ with raylib/raygui and Python training scripts.
  - Contains plain MM (`database.h`), LMM networks, and `spring.h` (springs/inertialization used throughout Holden's articles).
  - The animation dataset is CC BY-NC-ND 4.0, separate from the code.
  — [GitHub](https://github.com/orangeduck/Motion-Matching)
- **PFNN (Holden, Komura, Saito, SIGGRAPH 2017):** "milliseconds of execution time and a few megabytes" even when trained on gigabytes of data. The slides give 1.8 ms at 10 MB, or 0.8 ms at 125 MB (precomputed phase-function interpolation). — [Holden: PFNN](https://theorangeduck.com/page/phase-functioned-neural-networks-character-control); [PFNN slides](https://www.theorangeduck.com/media/uploads/other_stuff/pfnn_slides.pdf)
- **DeepMimic (Peng et al., SIGGRAPH 2018):**
  - The policy outputs PD target orientations per joint at 30 Hz, using fully connected ReLU layers.
  - Training a single humanoid skill takes about 60 M samples, about 2 days on an 8-core CPU. Another paper reports 8 h (walk) to 16 h (backflip).
  — [arXiv 1804.02717](https://arxiv.org/abs/1804.02717); [SFU summary](https://www.sfu.ca/~kabhishe/posts/posts/summary_tog_deepmimic_2018/); [arXiv 2104.12365](https://arxiv.org/pdf/2104.12365)
- **AMP (Peng et al., 2021):** policy MLP with 1024 and 512 ReLU hidden units plus a linear output, trained with GAIL + PPO. — [arXiv 2104.02180](https://arxiv.org/pdf/2104.02180)

### Inferences
- **A small kinematic motion matcher could run in Advent:**
  - Feature vector of about 27 floats per frame (2 feet pos/vel, hip vel, 3 future trajectory points).
  - A few thousand frames, brute-forced every 0.1-0.2 s.
  - In C via the DLL that is trivial on any CPU; in UnrealScript it is slow but possibly tolerable at low rates.
  - The blocker is playback. UE2 plays named sequences at a frame, so "jump to frame N of sequence S and blend" maps to PlayAnim/SetAnimFrame (if exposed) plus TweenAnim, used as a crude inertialization. That makes MM-over-.psa plausible if the clip set is long, unstructured locomotion takes.
- **Neural variants (PFNN/LMM) are possible but poor value.** 1-2 ms on a modern CPU for one character would be a lot on a 2005-engine frame budget with many NPCs. They also need mocap data we lack, and they would write bone transforms for every bone, every frame.
- **DeepMimic/AMP policies would not transfer.** They are trained in Bullet/PhysX-like simulators with PD at a high rate. Running one would mean reimplementing the training sim to match Karma, or training against Karma itself. Neither is realistic.

### Gaps
- I did not confirm the DeepMimic network layer sizes or ASE details (not fetched).
- I have no numbers for MM search cost or database size from Clavet's talk (Vault-gated).
- I did not verify whether Advent build 2226 exposes a script function to set the animation frame position.

## 5. Synthesis per technique: what reads as "real", cost, stability, data needs, engine hooks (ranked for Advent Rising / UE2)

### Takeaway
In order of payoff per effort for Advent:
1. Script-side post-process layer: foot IK, pelvis drop, look-at, lean, additive hit springs.
2. Speed-matched playback / stride scaling plus foot locking.
3. Procedural stepping for creatures/hounds.
4. Partial physical hit reactions (kinematic springs, then Karma lifters/impulses).
5. Native PD-powered ragdoll via the DLL.
6. Kinematic motion matching only if long locomotion takes become available.

Skip SIMBICON-style walking bipeds and RL policies.

### Cited Findings
- **Feet are what players read:** motion matching works by matching mainly foot positions and velocities. — [Game Developer](https://gamedeveloper.com/programming/most-inspiring-game-animation-tech-talks-of-2016)
- **Sliding vs distortion:** small foot sliding often looks better than a badly distorted IK pose, and camera framing can hide feet. — [Holden](https://theorangeduck.com/page/code-vs-data-driven-displacement)
- **Capping corrections:** limit capsule-mesh corrections to a ratio of current speed, so standing characters don't skate. — [Holden](https://theorangeduck.com/page/code-vs-data-driven-displacement)
- **Few keyframes plus procedural layers can carry a game** (Overgrowth). — [Game Developer](https://gamedeveloper.com/design/video-an-indie-approach-to-procedural-animation)
- **Physical controllers need small steps and torque limits to stay stable.** SIMBICON used a 5 ms step in ODE, and below 90 Nm the walk fails. — [SIMBICON](https://www.cs.ubc.ca/~van/papers/2007-siggraph-simbicon.pdf)
- **Karma limits:** mass ratio ≤ 100, ragdoll queue limits, and KImpact destroy crashes. — [UDN KAT](https://udn.epicgames.com/Two/KarmaAuthoringTool.html); [Unreal Wiki](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Functions_And_Events.html)

### Inferences
Comparison table (my synthesis from the cited material above):

| Technique | Reads real because | Cost / frame | Stability risk | Data needs | Engine hooks needed in Advent |
|---|---|---|---|---|---|
| Foot IK + pelvis drop on slopes/stairs | feet touch ground, no floating/clipping | 2 traces + 2 analytic IK per biped | low (clamp reach, damp pelvis) | none | SetBoneRotation, bone world pos (GetBoneCoords), Trace |
| Foot locking | no skating during contact | tiny | medium (pops on unlock; use inertialize/damper) | contact flags per clip (auto from foot height/vel) | same + per-clip contact curve (precompute offline from .psa) |
| Speed/stride matching | cadence matches ground speed | ~0 | low | authored root speed per clip | anim rate control (already in script) |
| Orientation warp (legs vs spine) | strafing without 8-way clips | small | low-medium | none | spine/pelvis bone rotation |
| Lean/bank, look-at, breathing | body responds to accel/attention | tiny | low | none | SetBoneRotation/SetBoneDirection |
| Additive hit spring | instant directional reaction | tiny | low | none | spine/clavicle bone rotation |
| Procedural creature stepping | feet plant ahead, body rides terrain | traces + IK per leg | medium (step ordering, leg crossing) | rest pose only | bone rotation; per-leg state in script |
| Partial/powered ragdoll | real weight and collision | Karma sim per body | high in Karma (gains vs substep, mass ratios) | .ka asset | native: per-joint motors/torques via DLL; script: lifters/impulses only |
| SIMBICON walking | push recovery, stepping | sim at about 200 Hz+ | very high | FSM tuning | native control loop, joint torques, contact info |
| Motion matching (kinematic) | mocap-quality transitions | small search | low | long mocap takes | set sequence + frame, blend; C search in DLL |
| PFNN/LMM/MANN | smooth, data-rich | about 1-2 ms each | low | large mocap, training | full-pose write per frame (native) |
| DeepMimic/AMP | physically plausible skills | MLP at 30 Hz + sim | very high (sim mismatch) | mocap + GPU-days | full native physics control |

- **Licences:**
  - orangeduck/Motion-Matching code is MIT (dataset CC BY-NC-ND, so don't ship it; our mods are GPL/share-alike, and MIT code is compatible).
  - The UE5 AnimationWarping plugin is under the Unreal EULA. Use it as a design reference only; do not copy its code into a GPL mod.
  - Unity Animation Rigging is under the Unity Companion License; reference only.
  - SIMBICON and Hecker are papers, so the algorithms are free to reimplement.

### Gaps
- I did not verify which bone/animation script natives Advent build 2226 exposes beyond SetBoneRotation/SetBoneDirection (GetBoneCoords, SetAnimFrame, AnimBlendParams channels). Check this in Advent's Engine.u/Pawn.uc export before committing.
- I found no source quantifying player perception (e.g. a study on foot sliding thresholds).
