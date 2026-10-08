# Physics-based ("dynamic") character bodies: from shipped active ragdolls to learned controllers, judged against Unreal Engine 2 / Karma (Advent Rising)

Research date: 2026-10-08. About 20 searches and fetches. Primary sources were used where they could be reached. Some items rest on secondary or blog sources and are marked as such. Anything without a source is under Inferences or Gaps.

## Active/powered ragdolls and physical animation (PD toward an animation pose, per-bone strength, partial ragdoll, get-up, balance; shipped games)

### Takeaway
Every shipped "active ragdoll" uses the same idea: each frame, drive every simulated bone toward the animated pose, using joint motors/springs (UE4/5, Jolt, Unity) or velocities/impulses (Jolt's kinematic mode; a CEDEC 2010 talk lists "impulses / joint motors"). Each bone has its own strength and maximum force, and a master multiplier fades between full ragdoll and full animation. Euphoria (GTA IV onward) adds a behaviour layer on top: balance, catching a fall, grabbing a wound. Get-up is usually done by matching the ragdoll to the closest get-up animation's first frame and then blending, not by simulating the stand-up.

### Cited Findings
- **UE4/5 Physical Animation Component.** Per-body motor settings are grouped into named "Physical Animation Profiles" stored in the Physics Asset. `ApplyPhysicalAnimationProfileBelow` applies a profile to a body and everything below it in the hierarchy, which gives partial ragdoll, e.g. "only the upper body". `ApplyPhysicalAnimationSettings(Below)` sets the values for a single body. — [UE 4.26 UPhysicalAnimationComponent API](https://docs.unrealengine.com/4.26/API/Runtime/Engine/PhysicsEngine/UPhysicalAnimationComponent/index.html); [Python API (current)](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PhysicalAnimationComponent)
- **UE `PhysicalAnimationData` fields.** Each bone has: position strength, orientation strength, velocity strength, angular-velocity strength, max linear force, max angular force, and an `IsLocalSimulation` flag (drive in joint space vs world space). The strengths act as PD gains and the max forces clamp the motor. — [PhysicalAnimationData Python API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PhysicalAnimationData)
- **UE strength fade.** `StrengthMultiplyer` (Epic's spelling) scales every active motor and is meant to be blended between 0 and 1 to fade between ragdoll and animation. Gotcha: setting the skeletal mesh afterwards erases the physical-animation data. — [UE 4.26 Blueprint API, Physical Animation](https://docs.unrealengine.com/4.26/en-US/BlueprintAPI/PhysicalAnimation/); [SetStrengthMultiplyer](https://docs.unrealengine.com/4.26/en-US/API/Runtime/Engine/PhysicsEngine/UPhysicalAnimationComponent/SetStrengthMulti-/index.html)
- **Jolt Physics (open source) has two pose-drive modes.**
  - `DriveToPoseUsingKinematics(pose, dt)` sets each body's velocity so it reaches the target pose within one time step. This is velocity-based and needs no motors.
  - `DriveToPoseUsingMotors(prevPose, pose, dt)` turns on the constraint motors with a target position and a target velocity taken from the previous pose.
  - `ResetWarmStart()` discards the solver's cached impulses after a pose snap.
  - This is the closest open reference to "impulse-only" driving. — [Jolt Ragdoll class docs](https://jrouwe.github.io/JoltPhysics/class_ragdoll.html)
- **CEDEC 2010 talk (Japanese conference, author not confirmed).** Slides list "Drive ragdoll towards animation pose (using impulses / joint motors)". Get-up recipe: compare the ragdoll's orientation with several get-up start frames, drive the ragdoll toward the closest one, and start that animation and blend to it once close enough. — [CEDEC 2010 C10_I0052 slides, via search snippet; the PDF now redirects](https://2018.cedec.cesa.or.jp:443/2010/archive/files/C10_I0052/C10_I0052.pdf)
- **Motor gains as spring parameters.** Houdini's APEX ragdoll solver exposes motor stiffness as a spring frequency and damping as a damping ratio: 1 = critically damped (just enough damping to stop oscillation), below 1 oscillates. S&box "Shrimple Ragdolls" likewise exposes MotorFrequency and MotorDamping. — [Houdini ragdoll::Solve](https://sidefx.com/docs/houdini/nodes/apex/ragdoll--Solve.html); [Shrimple Ragdolls](https://sbox.game/fish/shrimple_ragdolls)
- **Euphoria (NaturalMotion) is a runtime engine built on "Dynamic Motion Synthesis"**, which Wikipedia describes as not based on canned animation.
  - First shipped in GTA IV. Rockstar then licensed it for Red Dead Redemption, Max Payne 3, GTA V and RDR2.
  - LucasArts announced it in 2006 for Star Wars: The Force Unleashed and Indiana Jones and the Staff of Kings.
  - Backbreaker used NaturalMotion's Morpheme (blending, IK, rigid bodies), not Euphoria.
  - Zynga bought NaturalMotion in January 2014 for US$527M and closed the Oxford office in 2017.
  - [Wikipedia: NaturalMotion](https://en.wikipedia.org/wiki/NaturalMotion)
- **GDC 2008 Euphoria/GTA IV coverage** describes characters with a "muscular and nervous system" tied to physics and AI. Example: drunk Niko's gait becomes erratic and he falls, generated in real time. — [VidaExtra, GDC 2008 (Spanish)](https://www.vidaextra.com/ps3/gdc-2008-el-motor-euphoria-dotara-de-mayor-realismo-a-gta-iv). A fan write-up (lower reliability) lists the behaviours: a core "dynamic balancer", grabbing wounds, writhing, catching a fall, protective falls. — [cyber.sports.ru blog](https://cyber.sports.ru/games/blogs/3241029.html)
- **Overgrowth (Wolfire, David Rosen).**
  - GDC 2014 "An Indie Approach to Procedural Animation": the character uses about 13 keyframes in total, with spring-like interpolation and procedural layers.
  - The changelog mentions "faster active ragdoll animation" and ragdolls going to sleep sooner to save CPU.
  - Mostly secondary/forum sources. — [Unity forum thread on the talk](https://discussions.unity.com/t/an-indie-approach-to-procedural-animation-gdc-video-talk/538228); [DSOGaming Overgrowth alpha coverage](https://www.dsogaming.com/?p=8505)
- **Exanima (Bare Mettle, 2015).** Combat is physics-based with momentum, collision and locational damage. The claim of "200+ simulated muscles / motion synthesis" comes from a user review and is unverified. — [GOG user review](https://www.gog.com/u/SLNGRZ/reviews); [SteamData listing](https://steamdata.ai/game/362490)
- **Background reading.** The academic state-of-the-art review (Geijtenbeek & Pronost, CGF) frames the core difficulty: a physics character's pose can only be controlled indirectly, through internal actuator torques, so balance has no kinematic equivalent. — [Interactive Character Animation Using Simulated Physics: A State-of-the-Art Review](https://diglib.eg.org/items/580a30ec-21af-43ba-b49c-0ee70c32a02d/full); [Geijtenbeek thesis](https://dspace.library.uu.nl/handle/1874/289259)
- **Naughty Dog.** I found only "Enemy Hit Reactions in The Last of Us" (SIGGRAPH archive, speaker "Mach", no abstract) and a GDC21 rope-physics talk for Uncharted 4 / TLOU2. Nothing confirms how TLOU2 blends physics into hit reactions. — [SIGGRAPH History archive](https://history.siggraph.org/?p=144999); [GamePro on TLOU2 rope physics](https://www.gamepro.de/artikel/the-last-of-us-part-2-die-seilphysik-beeindruckt-die-spieler-und-andere-entwickler,3359110.html)

### Inferences
- **The standard hit-reaction recipe:**
  - Keep the animation playing.
  - On a hit, lower the strength of the bones from the hit bone downward (the UE "Below" idea).
  - Apply an impulse to the hit bone.
  - Ramp the strength back up over about 0.2–0.6 s.
  - Keep the legs and root at full strength, or animation-driven, so the character stays standing. Only past a damage threshold drop to a full ragdoll and use the get-up recipe.
  - The tuning values are plausible ranges, not sourced numbers.
- **Balance is the hard part.** Shipped non-Euphoria games mostly avoid true balance: the root/pelvis is kinematic or held by a strong spring until the character "falls". Euphoria-style balance is a large investment.
- **Gang Beasts / TABS-style "wobbly" bodies** are the opposite design: deliberately low gains plus an upright torque on the torso. Comedy, not realism. (No primary source found; see Gaps.)

### Gaps
- No primary GDC slides found for Euphoria internals, Max Payne 3, Force Unleashed, Uncharted 4/TLOU2 hit reactions, Gang Beasts or TABS.
- Unity PuppetMaster (RootMotion) "pin weight / muscle weight" docs did not show up in search, and Unity ConfigurableJoint slerp-drive tutorials were not fetched. Treat PuppetMaster details as unverified.
- The author of the CEDEC 2010 talk was not confirmed because the PDF now redirects.

## Control theory basics: PD gains, stable PD, SIMBICON, inverse dynamics vs PD, timestep, why old engines struggle

### Takeaway
A plain explicit PD controller, `tau = kp*(q_target - q) - kd*qdot`, goes unstable when `kp*dt^2` or `kd*dt` grow too large relative to the body's inertia. Stiff tracking therefore needs either very small timesteps (research typically simulates at about 1.2 kHz) or the implicit "Stable PD" formulation, which evaluates the PD law at the next step's state and allows arbitrarily high gains at large timesteps. SIMBICON shows that balance can come from simple feedback on foot placement plus mostly feedforward torques with low gains.

### Cited Findings
- **Stable PD (Tan, Liu, Turk, IEEE CG&A 2011).** It computes joint torques from the character's *predicted* position and velocity at the next time step. This "permits arbitrarily high gains, even at large time steps", and stays stable even with a simple Euler integrator. — [IEEE Xplore 5719567](https://ieeexplore.ieee.org/document/5719567/figures). The PDF on jie-tan.net could not be text-extracted here, so the exact formula and numbers were not checked.
- **AMP's settings.** The policy runs at 30 Hz and outputs target positions for PD controllers at each joint. The simulation runs at 1.2 kHz, a 40:1 substep ratio. This is typical of how much timestep research PD tracking assumes. — [AMP, Peng et al. 2021 (arXiv 2104.02180)](https://arxiv.org/pdf/2104.02180)
- **SIMBICON (Yin, Loken, van de Panne, SIGGRAPH 2007).**
  - Bipeds are "unstable, underactuated, high-dimensional dynamical systems".
  - Balance comes from simple linear feedback on swing-foot placement, using the centre of mass's position and velocity.
  - Torques are largely predictive feedforward, so only low-gain feedback is needed and there is "considerably less unnatural oscillation".
  - It produces walking in all directions, running, skipping and hopping in real time, and survives a 350 N, 0.2 s push.
  - Follow-ups include GENBICON (an inverted-pendulum model for foot placement) and a QP-based version for tracking motion that doesn't repeat in cycles.
  - [SIMBICON paper PDF](https://www.cs.ubc.ca/~van/papers/2007-siggraph-simbicon.pdf); [project page](https://www.cs.ubc.ca/~van/papers/Simbicon.htm); [SFU chapter](https://www2.cs.sfu.ca/~kkyin/papers/BipedController.pdf)
- **Solver stability.** A student physics engine (UCSD CSE125) reports that switching its joint solver from a velocity bias (PGS + Baumgarte) to position projection was more stable, and it ends each tick with "velocity clamp + sleep". This is anecdotal but matches common practice. — [UCSD CSE125 RagdollPbd docs](https://cse125.ucsd.edu/cse125/2026/cse125g2/docs/RagdollPbd_8hpp.html)

### Inferences
- **Why explicit PD blows up.** For one joint with inertia I, explicit PD stays roughly stable while `dt*sqrt(kp/I)` is well below 1. Light bodies (hands, feet) have tiny I, so they explode first.
  - Fixes: give each bone a gain proportional to its mass or inertia (UE-style strengths often behave like an acceleration, i.e. scaled by mass); raise the mass of small bones; or use SPD/implicit springs.
- **Why old engines struggle (Karma/MathEngine, early Havok, ODE).**
  - Fixed, fairly large timesteps; Karma in UE2 typically ticks at the frame rate, possibly with a few substeps.
  - Iterative or LCP solvers with soft constraints.
  - Ragdoll joints are passive limits only.
  - Any external drive (impulses from script) is one frame late and explicit, which is the unstable case. MathEngine's Karma is ODE-like (MdtBody/MdtConstraint), and its Kea solver supports limited motors on hinges.
- **Inverse dynamics vs PD.** Inverse dynamics computes the exact torques that produce the animation's accelerations (as Euphoria-class and QP controllers effectively do). It is much stiffer and needs the mass matrix and contact forces. PD needs no model and is "mushy". For a mod, PD/velocity drives plus feedforward ("gravity compensation", which cancels each bone's weight) is the practical middle ground.

### Gaps
- No source found for Karma's internal timestep or substep defaults in Advent Rising/UE2. Check the engine INI (e.g. `KarmaMaxSubsteps`-like settings) or the decompiled code.
- The exact SPD equations were not checked (PDF text extraction failed).

## Learning-based controllers (DeepMimic, AMP, ASE, CALM, PHC/PULSE, MaskedMimic, SuperTrack): cost and shipped use

### Takeaway
Learned controllers produce by far the best physical tracking and recovery, but they assume a modern, fast, high-rate simulator (Isaac Gym/Lab, MuJoCo, Bullet) with PD-servo joints. They take 100M+ simulation samples to train. At runtime the network is cheap (a small MLP at 30 Hz), but the physics must still run at kHz rates with motors. The one confirmed shipped use is ARC Raiders' robot enemies (Embark, 2025). Nothing like this shipped for humanoids in a big game was found. None of it ports to Karma without replacing the physics.

### Cited Findings
- **DeepMimic (Peng et al. 2018).** Imitation with a motion-tracking reward, one clip per policy. The code is **MIT-licensed** and uses **Bullet 2.88** in C++. — [xbpeng/DeepMimic](https://github.com/xbpeng/DeepMimic); [CALM paper's related work](https://arxiv.org/pdf/2305.02195)
- **AMP (2021).**
  - Uses an adversarial motion prior (a discriminator that rewards motion looking like the mocap data) plus a task reward.
  - Policy at 30 Hz, PD targets, simulation at 1.2 kHz.
  - 100–300M samples per policy.
  - It needs retraining when the data doesn't fit the task.
  - [AMP arXiv 2104.02180](https://arxiv.org/pdf/2104.02180)
- **ASE / AMP code (nv-tlabs/ASE).**
  - Runs on Isaac Gym.
  - The motion data (Reallusion) is "strictly for noncommercial use".
  - The README marks the repo as deprecated in favour of MimicKit.
  - The licence type was not stated on the page; check LICENSE.txt.
  - [nv-tlabs/ASE](https://github.com/nv-tlabs/ASE)
- **CALM (NVIDIA, SIGGRAPH 2023).** Encodes mocap into a latent space and decodes it into skills for a physics character. A later paper reports reconstruction rates of 94.6% (theirs) vs ASE 77.1% vs CALM 69.6%, but also says CALM tracks better than ASE, so the comparison is inconsistent. — [CALM arXiv 2305.02195](https://arxiv.org/pdf/2305.02195); [Neural Categorical Priors arXiv 2308.07200](https://arxiv.org/pdf/2308.07200)
- **PHC / PHC+ (Zhengyi Luo).**
  - "Real-time simulated avatars", driven from webcam, language or VR tracking.
  - Needs Isaac Gym plus SMPL body models, which carry their own licence terms.
  - PHC+ reaches 100% success on AMASS and is used in PULSE.
  - An IsaacLab evaluation script was added in August 2025.
  - The licence type is not shown on the README.
  - [ZhengyiLuo/PHC](https://github.com/ZhengyiLuo/PHC)
- **ProtoMotions3 (NVlabs).**
  - **Apache-2.0**; third-party notices (SMPL etc.) are in `legal/`.
  - Includes MaskedMimic, ADD, GPC/PEFT, and a general tracking policy.
  - Backends: IsaacGym, Isaac Lab, Newton, MuJoCo 3, and Genesis (untested).
  - [NVlabs/ProtoMotions](https://github.com/NVlabs/ProtoMotions)
- **SuperTrack (Fussell, Bergamin, Holden; Ubisoft La Forge; SIGGRAPH Asia 2021).**
  - Learns a "world model" (a network that approximates the simulator) and trains the policy by supervised gradient descent through it instead of PPO.
  - Reported to give higher quality in less training time and to scale to large motion sets.
  - The world model's errors compound over long horizons, so training uses short windows.
  - [Holden's SuperTrack page](https://theorangeduck.com/page/supertrack-motion-tracking-physically-simulated-characters-using-supervised-learning); [Ubisoft La Forge article](https://www.ubisoft.com/en-us/studio/laforge/news/7fMzaMaDgnd0gqPsCaJZYb/supertrack-motion-tracking-for-physically-simulated-characters-using-supervised-learning)
- **Shipped example: ARC Raiders (Embark, October 2025).**
  - The legged robot enemies' locomotion was built with physics simulation plus deep RL. GDC 2026 talk by Martin Singh-Blom.
  - Behaviour trees handle tactics.
  - No learning happens at runtime (secondary source).
  - [4Gamer GDC 2026 report (Japanese)](https://www.4gamer.net/games/609/G060942/20260312064/); [DonWeb blog (Spanish, secondary)](https://blog.donweb.com/ia-enemigos-arc-raiders-machine-learning/)

### Inferences
- **Runtime cost.**
  - Policy inference: an MLP of a few hundred thousand to a few million parameters at 30 Hz, well under 1 ms on CPU per character.
  - The real cost is the physics: around 1 kHz with PD motors, i.e. about 20–40 substeps per frame per character. That is fine for a handful of characters in modern PhysX/Jolt/MuJoCo, and not realistic in Karma.
- **Mod path.** The only learned option that could plausibly work on Advent Rising: a native DLL hosting its own simulator (e.g. Jolt or MuJoCo) for one or two hero characters, writing the bone transforms back to the UE2 skeleton. This replaces Karma for those characters rather than extending it. Training would also be required (GPU hours), and SMPL/mocap licences matter for distribution.

### Gaps
- No primary per-frame inference timings for CALM/ASE/PHC were found.
- No licence text was confirmed for PHC, PULSE, MaskedMimic's original repo, or the ASE code; check each LICENSE file.
- No confirmed shipped *humanoid* learned physics controller in a AAA game was found. EA's and Ubisoft's motion-matching work for physics was not located.

## Impulse-only approximations (driving ragdoll bodies with impulses toward target poses) and stability tricks; what is feasible in UE2/Karma

### Takeaway
Driving a ragdoll with impulses or velocities alone is a legitimate shipped technique. Jolt's `DriveToPoseUsingKinematics` sets velocities; a CEDEC 2010 talk lists "impulses / joint motors". It is stable only if it behaves like a damped, velocity-capped spring that respects each bone's mass. In UE2 the community pattern is `KAddImpulse` at the hit bone for reactions, and a scripted blend (`SetBoneDirection` with alpha 1 to 0) from the ragdoll pose to animation for recovery. Bone lifters are discouraged for recovery because they need collision disabled.

### Cited Findings
- **Unreal Wiki "Karma Ragdoll Injury System" (UT2004-era).**
  - Ragdoll the pawn on a hit, for a duration scaled by severity.
  - Apply `KAddImpulse` to the closest bone using the incoming momentum; this allows several hits in quick succession.
  - Recover by reading the ragdoll bones with `GetBoneCoords`, relinking the mesh, and blending with `SetBoneDirection` from alpha 1 to 0.
  - Advises against bone lifters for recovery because they need collision off.
  - Notes: ragdolls held too briefly "collapse into a ball"; `PlayAnim` in the same tick as the un-ragdoll may fail, so retry next tick; `bDestroyOnSimError` and `bKImportantRagdoll` flags; `SetBoneDirection` is not simulated; ragdolls replicate badly over the network.
  - [Legacy: Karma Ragdoll Injury System](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Ragdoll_Injury_System.html)
- **UE2 ragdoll setup.** `PHYS_KarmaRagDoll` with `KarmaParamsSkel`, and `KSkeleton` pointing to the .ka physics asset. Runtime ragdolling via a `KarmaMe()`-style script. — [UDN: Ragdolls in UT2003](https://docs.unrealengine.com/udk/Two/RagdollsInUT2003.html) (the fetch failed; details are from the search snippet); [Unreal Wiki Karma](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma.html)
- **Karma does have motorised constraints, but on KHinge actors, not on ragdoll skeleton joints.**
  - `KHingeType` can be motor mode, with `KDesiredAngVel` and a max torque.
  - `HT_Springy` drives to `KDesiredAngle` / `KAltDesiredAngle`.
  - So the MathEngine solver supports hinge motors and springs internally; they are simply not exposed for `KarmaParamsSkel` joints in script.
  - [UDN: Using Karma Actors](https://docs.unrealengine.com/udk/Two/UsingKarmaActors.html); [UDN: Karma example UT2003](https://docs.unrealengine.com/udk/Two/KarmaExampleUT2003.html)
- **Jolt's velocity drive.** Kinematic pose driving sets each body's velocity to reach the target within dt, and `ResetWarmStart` clears cached impulses after pose changes. — [Jolt Ragdoll docs](https://jrouwe.github.io/JoltPhysics/class_ragdoll.html)
- **General stability advice:** conservative joint limits and damping to stop jitter and twist; validate with fixed test impulses and recorded poses; lower solver iterations only after stability is confirmed. — [PulseGeek ragdoll stability tips](https://pulsegeek.com/articles/ragdoll-setup-and-stability-tips-for-reliable-collisions) (blog-grade source)

### Inferences
- **Impulse PD recipe, per simulated bone per tick.** Only standard physics, not tuned or tested values.
  - Read the bone's world rotation/position and its velocities (UE2: `KGetSkelBoneVel`-type natives or `GetBoneCoords` differencing, depending on what Advent exposes).
  - Compute the error to the animated target, which needs an un-ragdolled animation pose. Advent may need a hidden "ghost" mesh or a native call for this.
  - Desired velocity change: `dv = clamp(kp*err*dt - kd*v_rel*dt, maxDV)`. Apply the impulse as `m * dv` (linear) and `I * dw` (angular).
- **Key stability tricks:**
  1. Scale impulses by bone mass, i.e. treat gains as accelerations, so hands and feet don't explode.
  2. Use near-critical damping and damp *relative* to the parent bone, not world velocity.
  3. Cap per-bone velocity change per tick and total linear/angular speed.
  4. Equalise mass ratios between neighbouring bones to about 3:1 at most; raise hand/foot mass.
  5. Treat the drive as a velocity target ("set velocity" like Jolt kinematic) instead of adding impulses each tick, which avoids impulses accumulating.
  6. Make the drive frame-rate independent: substep it, or reduce gains at low fps.
  7. Fade strength per bone with a master multiplier, like UE.
- **Script-only impulses in Karma run one tick late and explicitly.** This is the worst case for stiffness, so expect "floppy follow" rather than crisp tracking. Hit reactions and drunk/limp effects are reachable; standing balance is not.
- **What a native DLL could unlock:**
  - Calling MathEngine's own constraint motors or limits on the ragdoll joints (the Kea solver has motors; KHinge proves it). That would make the drive implicit inside the solver.
  - Running the drive inside Karma's substep loop.
  - Swapping in Jolt for selected characters.
  - Ranked from cheapest to biggest: (a) a script impulse drive with the tricks above; (b) a DLL hook that applies the PD each Karma substep; (c) a DLL that enables MdtBSJoint/limit motors per joint; (d) an external solver (Jolt, MIT) driving UE2 bones.

### Gaps
- Exact Karma native functions available in Advent Rising script (`KGetSkelBoneVel`, `KSetSkelVel`, `KAddImpulse` per bone name, `KWake`) were not confirmed from Advent's own classes. Check the decompiled/exported source.
- No source found on whether the MathEngine SDK's ball-and-socket joints (the ragdoll joints) support angular motors, or only limits.
- No published numeric tuning (gains, velocity caps) for impulse-driven ragdolls was found in a primary source.

## Open-source code and licences

### Takeaway
For engine work, the useful permissive references are Jolt Physics (MIT, with ragdoll pose drives built in), DeepMimic (MIT, Bullet) and ProtoMotions3 (Apache-2.0). The research stacks (ASE, PHC) carry data licence restrictions (Reallusion noncommercial mocap, SMPL). That suits a noncommercial mod, but they should not be bundled into GPL releases without checking.

### Cited Findings
- **Jolt Physics:** ragdoll with `DriveToPoseUsingKinematics` / `DriveToPoseUsingMotors`. — [Jolt docs](https://jrouwe.github.io/JoltPhysics/class_ragdoll.html). Licence is MIT, from general knowledge; not re-checked in this session.
- **DeepMimic:** MIT, Bullet 2.88. — [GitHub](https://github.com/xbpeng/DeepMimic)
- **ProtoMotions3:** Apache-2.0; MaskedMimic and several simulator backends. — [GitHub](https://github.com/NVlabs/ProtoMotions)
- **ASE/AMP (nv-tlabs):** deprecated in favour of MimicKit; the Reallusion motion data is noncommercial only. — [GitHub](https://github.com/nv-tlabs/ASE)
- **PHC:** the README defers to upstream licences (IsaacGymEnvs, UHC, SMPL-X). — [GitHub](https://github.com/ZhengyiLuo/PHC)
- **Godot Active Ragdolls:** an open-source plugin; it warns that joints are hard to configure without prior knowledge. — [GitHub](https://github.com/R3X-G1L6AME5H/Godot-Active-Ragdolls)

### Inferences
- **For the Advent mod (GPL/share-alike):**
  - Jolt (MIT) and DeepMimic (MIT) code is compatible to borrow from.
  - SMPL-based models and Reallusion data are not redistributable in a mod.

### Gaps
- Licence texts were not opened for PHC, the ASE LICENSE.txt, MimicKit, PULSE, or the Godot Active Ragdolls plugin.
- Jolt's MIT licence is stated from memory, not verified here.
