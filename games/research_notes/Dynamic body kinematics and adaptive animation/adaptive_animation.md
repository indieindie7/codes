# Adaptive and data-driven animation systems (transfer study for an Unreal Engine 2 / Advent Rising mod)

Context for the reader: the target is Advent Rising (UE2-era). It has clip-based skeletal animation with channel blending, root motion, and script-side bone rotations, and a native DLL is possible. Every technique below is rated for whether it needs (a) mocap we do not have, (b) per-bone IK, or (c) only playrate and blend control, which UE2 already exposes.

## Motion matching (Clavet/For Honor, Zadziuk, TLOU2, UE5 Pose Search, Learned MM): data needs, runtime cost, minimal versions

### Takeaway
Motion matching runs a continuous nearest-neighbour search over every frame of a long mocap database. The query is a feature vector of the current pose (mostly foot positions and velocities) plus the desired future trajectory. After each pick the character blends briefly, or inertializes, into the chosen frame. It replaces hand-built transition graphs, but it only looks good with a dense, unstructured mocap set ("dance cards" = scripted capture-move lists). That data dependency is the blocker for us. A tiny version over a few hundred to a few thousand poses is cheap to compute, but it would have to search the game's existing clips, which were never shot for it.

### Cited Findings
- Simon Clavet (Ubisoft Montreal) presented "Motion Matching and The Road to Next-Gen Animation" at GDC 2016 (For Honor). Instead of placing small animations in a large structure, the team places small structured markup on top of long animations. Markup covers information the data cannot infer on its own, such as attack types and defence stances. — [GDC Vault](https://gdcvault.com/play/1022985/Motion-Matching-and-The-Road)
- Navigation data was "5 or 10 minutes of a person running around," imported directly. Starts, stops and turns come from the data, not from authored transitions. The runtime keeps searching for the frame that best matches the current pose and desired future trajectory, then blends briefly into it. The result is described as almost indistinguishable from raw mocap. — search summary of the [GDC Vault session](https://gdcvault.com/play/1022985/Motion-Matching-and-The-Road) (secondary summary; I did not watch the full video)
- The matched features are mostly the positions and velocities of the feet. For Honor also used the weapon position. — [Game Developer: most inspiring animation tech talks of 2016](https://gamedeveloper.com/programming/most-inspiring-game-animation-tech-talks-of-2016) (via search summary)
- Motion matching in a AAA game was first publicly discussed by Michael Büttner (Ubisoft Toronto) at nucl.ai 2015. Kristjan Zadziuk (Ubisoft Toronto animation director) presented applicable cases at GDC 2016. — [gameanim.com](https://www.gameanim.com/?p=14043); [gamingbolt](https://gamingbolt.com/the-last-of-us-part-2s-new-motion-mapping-technique-provides-incredible-next-gen-leap-in-animations)
- Zadziuk released a video on "the various different mocap actions that must be created via the 'dance cards'." These are scripted capture routines that cover the speed, turn and stop space, but no source I found defines them precisely. — [gameanim.com "Motion Matching Explained(ish)"](https://www.gameanim.com/?p=14043)
- The Last of Us Part II: GDC 2021 talk "Motion Matching in The Last of Us Part II" (Michal Mach, Maksym Zhuravlov) covers the adoption plus "frustrations and things that didn't go as planned." — [Naughty Dog blog](https://www.naughtydog.com/blog/naughty_dog_at_gdc_2021)
- Anthony Newman (TLOU2 co-director) said earlier Naughty Dog games used a rigid clip state machine. MM instead breaks a large library into small segments and picks those that fit the path, frame by frame. It was used for NPCs, horses and dogs, "with as little blending as possible at every foot plant and turn." — [PSU](https://www.psu.com/news/the-last-of-us-part-2-motion-matching/); [wccftech](https://wccftech.com/the-last-of-us-part-ii-motion-matching-tech/amp/)
- UE5 Pose Search (UE 5.8 docs):
  - A Schema defines channels (Trajectory, Pose, Position, Velocity, Heading, Phase, etc.), the sample rate and permutations. The default locomotion setup is one Trajectory channel (past and future time offsets) plus a Pose channel sampling the left and right foot bones.
  - Total cost is the sum of channel costs, with per-channel and per-property weights that are auto-normalised.
  - Search modes are Brute Force, PCA+KD-tree (approximate, KNN re-check) and VP-tree (experimental).
  - Locomotion clips must have root motion.
  - More channels, samples, permutations or a higher sample rate all raise memory and CPU cost. Epic's advice is to use as few samples and channels as possible.
  - The node has a "Use Inertial Blend" option, and "Block Transition" and "Exclude From Database" notify states mark protected or unusable ranges.
  - Source: [UE docs: Motion Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-matching-in-unreal-engine)
- Epic's Game Animation Sample ships 500+ free animations for motion matching. Its documentation discusses when a dense set of hundreds of animations beats a sparser set of fewer than 100. Selection relies mostly on Choosers/Proxy Tables, and Pose Warping fills coverage gaps. — [Unreal blog](https://www.unrealengine.com/en-US/blog/game-animation-sample). The licence was not found; it is presumably the UE EULA/Fab terms, which probably bar use outside Unreal Engine (unverified, see Gaps).
- Learned Motion Matching (Holden, Kanoun, Perepichka, Popa, SIGGRAPH 2020):
  - Three networks (decompressor, stepper, projector) replace the stored database and search.
  - MM memory "scales linearly with the amount of data", while LMM stores only network weights and claims to preserve MM's behaviour.
  - Sources: [Orange Duck LMM page](https://www.theorangeduck.com/page/learned-motion-matching); [Ubisoft La Forge](https://www.ubisoft.com/en-us/studio/laforge/news/3NWqwcMU9lMfumgfPAEfka/learned-motion-matching)
  - A later (2023) paper reported that LMM cut memory but raised compute cost. — search summary citing [unpaywall 10.1145/3623264.3624442](https://unpaywall.org/10.1145%2F3623264.3624442)
- orangeduck/Motion-Matching (GitHub):
  - Code is MIT. It contains basic MM (search in `database.h`) and LMM (`lmm.h`, `nnet.h`, PyTorch training scripts for decompressor, stepper and projector), using raylib/raygui with a Windows Makefile.
  - `features.bin` is regenerated each run. The repo omits some of the paper's storage optimisations and does not use walk/run tags.
  - The data is the Ubisoft La Forge Animation Dataset (LAFAN1), licensed CC BY-NC-ND 4.0, which is different from the code licence.
  - Source: [GitHub repo](https://github.com/orangeduck/Motion-Matching)
- Orange Duck "Code vs Data Driven Displacement" demo:
  - The search matches a simulated object's future trajectory relative to the character. The simulation object is a critically damped spring driven by gamepad velocity.
  - A procedural "simulation bone" is the upper spine projected to the ground, smoothed with a Savitzky-Golay filter, with the hip forward direction giving its rotation.
  - Character and simulation are reconciled with a damper and clamps (example `max_adjustment_ratio` 0.5).
  - Foot locking uses inertialization plus IK with an `unlock_radius`.
  - The mocap was sped up about 10% and mirrored to widen coverage. Measured speeds: run ~4 m/s forward, ~3 m/s strafe, ~2 m/s back; walk ~1.75 / 1.5 / 1.25 m/s.
  - The author argues MM's lack of blending means exact velocity or turn targets need correction, and that a large, interruptible dataset reduces how much correction is needed.
  - Source: [Orange Duck](https://theorangeduck.com/page/code-vs-data-driven-displacement)
- Inertialization records the position and velocity offset at the switch, then decays it with a spring-damper. It is "a more performant alternative to a cross-fade blend since it only needs to evaluate one animation at a time," at the cost of no fixed duration and possible overshoot. — [Orange Duck, Spring-It-On / spring roll call](https://theorangeduck.com/page/spring-roll-call)

### Inferences
- A few hundred to a few thousand poses with a ~20 to 30 float feature vector (2 feet pos+vel = 12, 3 future trajectory points pos+dir = 12, hip vel = 3) makes brute-force search trivially cheap in a native DLL at 10 Hz search intervals. This is my estimate from the feature-vector size, not a sourced benchmark. CPU is not the blocker; data coverage is.
- Advent Rising's shipped clips are short loops and transitions, not long unstructured mocap. MM over them would mostly re-pick loop frames and could not invent starts, plants or pivots that were never captured. The likely result is "clip selection with smarter entry points," which a hand state machine with phase-matched entry points already gives.
- The highest-value piece to steal from MM for UE2 is probably not the search. It is (1) the damped-spring trajectory prediction, (2) inertialization as a cheap transition (one evaluated pose plus a decaying per-bone offset, applied as script or native bone rotations), and (3) the simulation/character reconciliation. These need no new data.
- LAFAN1 (CC BY-NC-ND) cannot ship in a mod because of the NoDerivatives clause, which also conflicts with the user's share-alike preference. CMU mocap (free, commercial-OK, no raw resale) and possibly 100STYLE (reportedly CC BY 4.0) are the usable sources if retargeted to the Advent skeleton:
  - CMU terms: [CMU dataset terms via 4TU FBX conversion](https://data.4tu.nl/datasets/0448aab2-3332-449f-a8e2-d208cb58c7df)
  - 100STYLE: 4M+ frames, 100 locomotion styles, [Zenodo](https://zenodo.org/record/8127870). Licence reported by [reseller listing](https://booth.pm/en/items/8872633), unverified from the primary source.
- LMM is not worth it for us: it needs a working MM plus training data first, and its gain (memory) is not our problem.

### Gaps
- Exact Zadziuk talk title ("Animation Bootcamp: Motion Matching") and the dance-card contents could not be confirmed. The GDC Vault entries found are titled "Motion Matching and The Road to Next-Gen Animation" (two vault IDs: [1022985](https://gdcvault.com/play/1022985/Motion-Matching-and-The-Road), [1023280](https://gdcvault.com/play/1023280/Motion-Matching-and-The-Road)).
- LMM paper numbers (MB per database, frames, per-character cost) were not extracted; the PDF was too large to fetch.
- TLOU2-specific data volumes and runtime costs were not found in accessible text.
- The Game Animation Sample licence terms were not found.

## Animation warping: stride, orientation, slope, motion warping to targets, playrate, distance matching

### Takeaway
Warping keeps a small clip set and procedurally bends it to the situation:
- Stride warping scales foot spacing to capsule speed (scale = locomotion speed / root-motion speed) using leg IK plus a pelvis solver.
- Orientation warping twists legs and spine to cover the angle between the root-motion direction and the actual move direction, clamped near 90°.
- Slope warping re-plants feet on the floor normal.
- Motion warping skews root motion inside a marked time window so an attack, vault or climb ends exactly on a target transform.
- Distance matching drives a clip by distance (to a stop point, from a start, to the ground) instead of time.

Of these, distance matching, playrate matching and root-motion skew warping need no IK and map directly onto UE2-style clip time and root-motion control. Stride, orientation and slope warping need two-bone leg IK, which in UE2 would have to come from script bone rotations or the native DLL.

### Cited Findings
- UE Motion Warping:
  - A Motion Warping notify-state window in a montage carries a Warp Target Name. Gameplay calls Add/Update Warp Target with a location and rotation.
  - Skew Warp adjusts root motion so location and rotation hit the target by the end of the window. There is also Scale and rotation modes (match the target's rotation, or face it) with a Warp Rotation Time Multiplier, an "Ignore Z" option, and a warp-point provider (none, static transform, or bone).
  - The animation must have root motion enabled or nothing is warped.
  - Source: [UE docs: Motion Warping](https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-warping-in-unreal-engine)
- A forum account of Gears of War 4 says warping is applied in specific ranges between solid contacts, with extra attributes authored into clips so gameplay knows where adjustment is least visible. This is a from-memory forum post, low confidence. — [AWS re:Post (EmotionFX skewing)](https://repost.aws/questions/QURJZ_VL2NT2GjizmNOge4hw/emotionfx-animation-skewing)
- Distance matching drives a sequence by a distance value instead of time. Its data and nodes:
  - Data: a distance curve generated from root motion by the Distance Curve Modifier (sample rate, stop speed threshold, axis). The curve must be compressed with the Uniform Indexable codec so it can be read at runtime.
  - "Distance Match to Target" picks the pose for the remaining distance, e.g. stopping exactly on a point or a landing driven by height above the ground.
  - "Advance Time By Distance Matching" advances the clip by distance travelled.
  - "Set Playrate to Match Speed" scales playrate and assumes constant speed.
  - Caveat: a character may never fully "stop" in a pivot.
  - Source: [UE docs: Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine)
- Distance matching is widely attributed to Paragon. The only source I found for that is a forum post ([Mediavida](https://www.mediavida.com/foro/gamedev/motion-matching-animaciones-658181)), so treat it as unverified. Laurent Delayen's Paragon talk found was at nucl.ai 2016 (locomotion system, layers, trade-offs), not GDC. — [gameanim.com](https://www.gameanim.com/?p=14556)
- Stride Warping inputs and behaviour:
  - Inputs: locomotion speed (graph mode) or a manual Stride Scale = locomotion speed / root-motion speed; Min Locomotion Speed Threshold; Pelvis Bone; Foot Definitions (IK foot, FK foot, thigh per leg).
  - Clamps and smoothing: Clamp Result (min/max scale), separate interp speeds for increasing and decreasing scale, and "Clamp IK Using FK Limits" against overextension.
  - Pelvis IK Foot Solver: pulls the pelvis down as legs extend, with stiffness and damping, an Interp Alpha that keeps some of the original pelvis motion, a Max Distance, and Error Tolerance / Max Iter as the quality-versus-cost trade-off.
  - Graph mode requires root-motion clips.
  - Source: [UE docs: Pose Warping](https://dev.epicgames.com/documentation/en-us/unreal-engine/pose-warping-in-unreal-engine)
- Orientation Warping:
  - Inputs: an angle between root-motion direction and locomotion direction, a rotation axis, spine bones (rotation distributed by an alpha), IK foot bones with two-bone legs, a Rotation Interp Speed, and a Location Angle Delta Threshold (default 90°, 0 disables it).
  - It covers gaps so fewer interstitial clips and blend-space directions are needed.
  - Source: [UE docs: Pose Warping](https://dev.epicgames.com/documentation/en-us/unreal-engine/pose-warping-in-unreal-engine)
- Slope Warping: inputs are pelvis, feet (IK and FK, bone count, foot size), gravity direction, Max Step Height, "Pull Pelvis Down" and "Keep Mesh Inside Capsule". Epic marks it as still in development and not for production. — [UE docs: Pose Warping](https://dev.epicgames.com/documentation/en-us/unreal-engine/pose-warping-in-unreal-engine)

### Inferences
- UE2 transfer, cheapest first:
  1. Playrate = ground speed / clip root speed. UE2 already exposes per-channel rate, so this is pure script.
  2. Distance matching for starts, stops and landings. Precompute a root-distance table per clip offline (from root motion), then each tick set the clip frame from the remaining distance. This needs frame-setting on a channel; UE2's anim system exposes setting a channel's frame (AnimFrame / SetAnimFrame-style natives exist in UE2 variants; verify in Advent's script source).
  3. Root-motion skew warping for melee lunges and vault/ledge alignment. Compute the delta between the clip's authored end root position and the target, and spread it linearly (or ease it) over a marked frame window by adding it to the actor's movement. No bone work is needed.
  4. Orientation warping as a spine twist only, without leg IK. Script bone rotations on pelvis/spine counter-rotate so the upper body faces the aim while legs follow the move direction. This is what UE2-era games already did for aim offsets.
  5. Stride and slope warping need a two-bone analytic IK (trig on thigh, calf and foot) plus a pelvis drop. That is feasible in the native DLL if per-bone local transforms can be overridden after anim evaluation.

### Gaps
- No primary source found for Paragon's distance matching origin or Delayen's GDC slides.
- No primary sources found for Assassin's Creed Unity parkour alignment, cover transitions in Uncharted, or Ubisoft's IK/warping stack. The searches returned only previews and fan articles: Unity's parkour allowed climbing at non-right angles ([gamingtrend](https://gamingtrend.com/feature/previews/assassins-creed-unity-fresh-start-return-roots)), and an AC3 animation GDC 2013 write-up exists ([gameanim.com](https://www.gameanim.com/?p=5864)).

## Blend spaces, procedural layers, AAA locomotion stacks (Naughty Dog, Rockstar RDR2/Euphoria), responsiveness vs realism

### Takeaway
Modern stacks typically follow this layering:
1. A base selection: a state machine, blend space or motion matching.
2. Root-motion versus capsule reconciliation.
3. Procedural pose layers: stride and orientation warping, foot IK and slope, aim and look offsets, additive leans.
4. Physics or "active ragdoll" layers for reactions, e.g. Euphoria in RDR2.

Rockstar's own statement says Euphoria is used for physics-based reactions (hits, falls, horse falls), not core locomotion. I found no reliable public source on RDR2's base locomotion.

### Cited Findings
- Rockstar (Phil Hooker, director of technology) said Euphoria is used "to enhance the physics-based reactions of both humans and animals" and was evolved for RDR2. Examples include a rider rolling off a shot horse, being dragged in the stirrups, or being trapped under it. — [wccftech](https://wccftech.com/rockstar-euphoria-evolved-rdr2/amp/)
- NaturalMotion describes its Dynamic Motion Synthesis as real-time simulation of biomechanics and the motor nervous system. Euphoria is the runtime built on it. — [Wikipedia: NaturalMotion](https://en.wikipedia.org/wiki/NaturalMotion)
- RDR2's RAGE engine reportedly uses Bullet for physics, with Euphoria generating character reaction animation. — [iXBT (Russian)](https://www.ixbt.com/3dv/games-rdr2.html) (secondary)
- Epic's sample pairs Choosers/Proxy Tables (data-driven clip selection) with Pose Warping to fill coverage gaps. This is the "fewer clips + procedural correction" pattern. — [Unreal blog](https://www.unrealengine.com/en-US/blog/game-animation-sample)
- Motion matching itself trades exactness for naturalness. Hitting exact velocity or turn targets requires correction by warping or by clamping the simulation-to-character offset. — [Orange Duck](https://theorangeduck.com/page/code-vs-data-driven-displacement)

### Inferences
- For a responsive feel on old content, the usual control knob is where the truth lives:
  - Capsule-driven (gameplay is responsive, the animation is warped to fit): this is what stride, orientation and playrate warping enable.
  - Root-motion-driven (realistic, laggy).
  - Hybrid, as in the Orange Duck demo: a simulation object plus a damped pull of the character.
  - For an action shooter like Advent Rising, capsule-driven plus warping is the right default.
- A cheap "Euphoria-lite" for UE2: blend the karma ragdoll in only for hit reactions, then inertialize back to animation. This overlaps the Advent physics plan (powered ragdolls) and is noted here only as the layer that corresponds to Euphoria.

### Gaps
- No primary sources found on RDR2 locomotion (it is commonly believed to use motion-matching-like systems; unverified), Naughty Dog's IK and procedural layer stack, or Ubisoft's warping stack.
- The Sony/Naughty Dog GDC 2021 talk content is behind GDC Vault and was not accessed.

## Interaction/contact animation: reach, grab, props, traversal, cover

### Takeaway
The common pattern is an authored contact clip plus alignment. The clip carries markup: contact frames and a warp window. Gameplay supplies a target transform (ledge point, cover edge, enemy, prop). Root motion is skewed so the character arrives exactly, and hand or foot IK snaps the end effector to the contact point over the last frames. UE Motion Warping is the documented public example. I found no primary documentation for the AC/Uncharted specifics.

### Cited Findings
- UE Motion Warping: named warp windows in clips, targets supplied at runtime, skew warp of root translation and rotation, and an optional bone-based warp point (e.g. align a hand bone rather than the root). — [UE docs: Motion Warping](https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-warping-in-unreal-engine)
- Clavet's For Honor approach puts markup (attack types, stances) on long clips rather than building graphs. — [GDC Vault](https://gdcvault.com/play/1022985/Motion-Matching-and-The-Road)
- Gears of War 4 (forum, low confidence) applied warping only between solid contacts, with authored attributes marking where adjustment is least noticeable. — [AWS re:Post](https://repost.aws/questions/QURJZ_VL2NT2GjizmNOge4hw/emotionfx-animation-skewing)

### Inferences
- UE2 recipe:
  1. Tag clip frames offline (contact frame, warp start and end).
  2. At trigger time, trace for the target.
  3. Root-skew the warp window.
  4. In the last N frames, blend in a two-bone arm IK to the contact point via the DLL, or fake it with script bone rotations on the shoulder and elbow.
- Melee lunge or attack alignment and ledge grab are the highest payoff and need no new mocap: the existing clips are reused with skewing.

### Gaps
- No primary sources found for Assassin's Creed or Uncharted traversal alignment internals or cover-transition systems.

## Open-source code and licences

### Takeaway
The best directly reusable code is orangeduck's Motion-Matching repo (MIT): MM search, inertialization, springs, foot locking and LMM training, in compact C++ headers. Its default dataset, LAFAN1, is CC BY-NC-ND and must not be redistributed in derived form. CMU mocap is the safest free data. UE's Pose Search and Pose Warping are engine code under the UE EULA, useful only as design references.

### Cited Findings
- orangeduck/Motion-Matching: MIT code; LAFAN1 data is CC BY-NC-ND 4.0; dependencies are raylib/raygui and Emscripten for web; training is PyTorch plus TensorBoard. — [GitHub](https://github.com/orangeduck/Motion-Matching)
- Orange Duck's spring/inertialization article has no licence on the page itself; its demo code is in the linked repo. — [Orange Duck](https://theorangeduck.com/page/spring-roll-call)
- CMU mocap: free for research and may be included in commercial products, but not resold directly, even converted. Acknowledgment requested ("The data used in this project was obtained from mocap.cs.cmu.edu."). — [4TU FBX conversion](https://data.4tu.nl/datasets/0448aab2-3332-449f-a8e2-d208cb58c7df); [PapersWithCode](https://paperswithcode.com/dataset/cmu-motion-capture)
- 100STYLE: 4M+ frames, 100 locomotion styles. CC BY 4.0 is reported only by third-party resellers. — [Zenodo](https://zenodo.org/record/8127870); [booth.pm](https://booth.pm/en/items/8872633)

### Inferences
- Port order for a native DLL: `spring.h`-style dampers and inertialization (no data needed) → two-bone IK → optional brute-force MM over retargeted CMU locomotion.
- Retargeting CMU (31-joint, 120 fps BVH/ASF) onto Advent's skeleton and importing it as UE2 animation is the real cost of any data-driven path. This is a sizeable pipeline job and is flagged as a "needs mocap we don't have in usable form" item.

### Gaps
- No verified licence for Epic's Game Animation Sample assets outside UE.
- No primary 100STYLE licence page was fetched.
- No other open-source MM implementations (e.g. Unity community ones) were surveyed.
