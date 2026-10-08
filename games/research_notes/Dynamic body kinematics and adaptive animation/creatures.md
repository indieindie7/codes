# Procedural and adaptive animation for non-humanoid creatures (quadrupeds, multi-legged, multi-armed, tentacled)

Context: Advent Rising mod (UE2). Hounds (4 legs) and four-armed Seekers. Clip-based skeletal animation plus script bone rotations, GetBoneCoords and traces. The notes favour techniques that work as a layer over existing clips.

## Procedural gaits: footfall timing, step triggering, foot target prediction, body suspension/tilt, spiders/insects

### Takeaway
Shipped systems use the same core recipe: a cyclic gait clock that gives each foot a duty factor and a phase offset, plus distance- or IK-failure-based step triggers. New foot targets are predicted from body velocity and snapped to the ground with a trace, and the body/hips are raised and tilted from the planted feet. Spore (Hecker et al. 2008) is the best-documented shipped example and handles any number of legs. Rain World shows how far you can get with soft point-chains plus a "paper doll" drawn on top.

### Cited Findings
**Quadruped footfall parameters (biology, used directly as gait tables)**
- Hildebrand classifies symmetric gaits (walk, trot, pace) by two variables: the **duty factor**, which is a foot's stance time as a fraction of the stride, and the **lateral phase**, which is how far through the stride the same-side forefoot lands after the hindfoot. Left and right legs are 180 degrees apart. — [eLife: Work minimization accounts for footfall phasing in slow quadrupedal gaits](https://elifesciences.org/articles/29495); [Cartmill et al. 2002, Support polygons and symmetrical gaits](https://www.originalwisdom.com/wp-content/uploads/bsk-pdf-manager/2019/10/Cartmill-et-al_2002_Support-polygons-and-symmetrical-gaits-in-mammals.pdf)
- **Walk:** duty factor > 0.5. **Trot:** diagonal pairs land together (phase 50%). **Pace:** same-side feet together (phase 0/100%). Duty factor falls as speed rises; at the horse walk-to-trot transition it drops from about 0.6 to about 0.5, and trots have an aerial phase. — [eLife 29495](https://elifesciences.org/articles/29495); [PMC2658658](https://pmc.ncbi.nlm.nih.gov/articles/PMC2658658)
- Gallops are asymmetric. In a **transverse** gallop each hind contact is followed by the same-side forelimb. A **rotary** gallop has a circular limb sequence; cheetahs use rotary for sprinting, horses transverse. Gallops are also left- or right-leading. — [16 Ways to Gallop (arXiv 2503.13716)](https://arxiv.org/html/2503.13716v2); [Sled-dog gait transitions (arXiv 2507.14727)](https://arxiv.org/pdf/2507.14727)
- Note: these findings come from secondary papers citing Hildebrand (1965); the original was not retrieved.

**Spore: gaits for any leg count (SIGGRAPH 2008, read from the paper PDF)**
- A leg is a path through the limb tree from the hip (a spine segment) to a foot leaf. Legs are **clustered into groups of roughly equal length**. The groups' length ratios are approximated by **small rational numbers**, and those ratios set each group's relative gait-cycle frequency. — [Hecker et al. 2008, PDF](https://www.cse.chalmers.se/edu/year/2011/course/TDA361/Advanced%20Computer%20Graphics/027-hecker%20copy.pdf)
- Per foot, the gait system sets a **duty factor** (fraction of the cycle on the ground, citing Alexander 2003) and a **step trigger**, the offset into the cycle at which the foot starts (citing Rotenberg 2004). "The hips are translated and rotated as the feet are moved for believable torso motion." Animators author the foot's flight-phase path in a normalized space, which is then scaled by leg length. — same PDF
- Animators authored speed-to-gait-parameter maps for groups of 1 to 6 feet; groups with 7 or more feet are generated procedurally. Gait styles can be **layered**, for example limping or a lumbering gait for large characters, and different leg groups can use different gaits at once ("two short legs could be running while four long legs are trotting"). Legless crawlers turn spine bodies into pseudo-feet and use an inch-worm gait. — same PDF
- Goals go to a **Particle IK solver** (underdetermined; spare DOF optimise secondary objectives). The paper names its biggest open problem as "believable locomotion with anticipation in the face of discontinuous player and code inputs." — same PDF
- Project page and lecture "How To Animate a Character You've Never Seen Before"; the site is marked "Copyright Chris Hecker, All Rights Reserved" and no code is released. — [chrishecker.com paper page](https://chrishecker.com/Real-time_Motion_Retargeting_to_Highly_Varied_User-Created_Morphologies); [lecture page](https://chrishecker.com/How_To_Animate_a_Character_You%27ve_Never_Seen_Before)

**Step triggering and foot target prediction (multi-legged walkers)**
- PhilS94 Unity wall-walking spider:
  - **Step trigger:** a leg asks to step when its IK can no longer reach the target within a tolerance.
  - **Timing:** a central manager grants steps, either through a queue that respects neighbouring legs or through an "Alternating Tetrapod Gait" (two groups stepping in alternate time windows).
  - **Target:** each new target comes from a local anchor point, extended slightly past the previous target and corrected for the body's predicted travel during the step.
  - **Ground finding:** multiple raycasts (down, outward, inward) find the surface.
  - **Body:** it is raised and rotated from the leg heights; fake gravity along the surface normal handles walls.
  - **Licence:** the repo is deprecated; licensing goes through the Unity Asset Store, sublicensing and selling are prohibited, copyright Philipp Schofield. Not open source, so treat it as reference only.
  - — [GitHub PhilS94/Unity-Procedural-IK-Wall-Walking-Spider](https://github.com/PhilS94/Unity-Procedural-IK-Wall-Walking-Spider)
- Godot 4.5 spider: each leg raycasts a "future position" from the hit point plus the player's velocity and steps when that point is farther than a threshold from the current IK foot. Legs move in **diagonal pairs**, and only one group can move at a time. — [80.lv Godot spider](https://80.lv/articles/ik-driven-procedural-spider-locomotion-in-godot-4-5)
- Spider Walker (Blender add-on, 2026): it estimates body velocity and predicts each foot's target as its rest position relative to the body, shifted forward by speed. When the planted foot drifts far enough, it raycasts down from that target for a landing point. Legs step one at a time, and the result can be baked to keyframes. Licence not stated. — [Digital Production](https://digitalproduction.com/2026/08/28/spider-walker-automates-multi-leg-animation/)
- Factorio's Spidertron write-up likewise predicts where the body will be when a step starts. — [Alt-F4 #12](https://alt-f4.blog/ALTF4-12/)

**Rain World (Joar Jakobsson / James Therrien)**
- GDC 2016 Animation Bootcamp talk "Rainworld Animation Process" (Jakobsson and Therrien, 30 min). — [GDC news listing](https://gdconf.com/news/animation_experts_share_tips_a); [GDC Vault](https://gdcvault.com/play/1023480/Animation-Bootcamp-Animation)
- Technique in Jakobsson's words: "a bunch of points in space" connected "at certain distances," with a "paper doll" of parts drawn over them. All creatures are built this way, so they are soft, bendable, and can get through almost any environment. — [Game Developer: Crafting the ecosystem of Rain World](https://gamedeveloper.com/design/crafting-the-complex-chaotic-ecosystem-of-i-rain-world-i-)
- Creatures are collections of physics points (for a lizard: body, head, legs, tail). Their motion comes from the creature's own drives, body constraints, and environment physics, with no list of prebuilt animations. The slugcat is two spherical chunks at a fixed distance, with cosmetic limbs and tail animated procedurally from input. — [Unity blog: Exploring procedural design in Rain World: The Watcher](https://unity.com/en/blog/exploring-procedural-design-rain-world)
- The sources do not detail how lizard feet find grip; see Gaps.

**Quadruped production talks (abstracts only; the Vault is members-only)**
- Far Cry 4, "Grounding Wildlife in the Mountains" (GDC 2015, Konieczny and Pelletier, Ubisoft): combines **additive animation, environment detection, IK and character physics** so quadrupeds adapt to rocky terrain, a "symbiosis between animation data and procedural techniques." — [GDC Vault 1022027](https://www.gdcvault.com/play/1022027/Grounding-Wildlife-in-the-Mountains)
- The Flame in the Flood, "Animating Quadruped Characters" (GDC 2016, Gwen Frey): a boar with a **rigid spine** and a wolf with a **procedural spine**. It tackles foot sliding and avoids authored gait-transition animations. — [GDC Vault 1023209](https://gdcvault.com/play/1023209/Animating-Quadruped-Characters-in-The)
- Wolfire, "An Indie Approach to Procedural Animation" (GDC 2014 Animation Bootcamp, David Rosen): very few keyframes plus interpolation and procedural layers (Overgrowth, Receiver). A forum claim of about 13 keyframes in total is unverified. A Texas A&M reimplementation uses 4 keys per walk/run cycle. Video is free. — [Game Developer video](https://gamedeveloper.com/design/video-an-indie-approach-to-procedural-animation); [TAMU reimplementation](https://people.engr.tamu.edu/sueda/courses/CSC474/2016W/demos/ismithgr/index.html)
- Assassin's Creed, "Fitting the World: A Biomechanical Approach to Foot IK" (GDC 2016, Ubisoft): moves from reactive foot IK to **predictive** foot IK modelled on biomechanics. It covers humans, but the idea transfers. — referenced in search results; Vault page not fetched (see Gaps).
- Horizon Zero Dawn, "Bringing Life to the Machines" (GDC 2018, Richard Oud, Guerrilla): covers reference, motion style, workflow, animation tech, AI behaviour and polish. The abstract does not state foot-IK specifics. — [GDC Vault 1025040](https://gdcvault.com/play/1025040/Animation-Bootcamp-Bringing-Life-to); [80.lv summary](https://80.lv/articles/horizon-zero-dawn-beasts-animation-production)
- Shadow of the Colossus: an analysis of Sony's making-of suggests the horse uses **two-bone leg IK** whose solver also **raises and angles the whole body**. It is partly speculative. The standout tech was deforming colossus collision. genDESIGN staff say they "tried procedural animation with some characters" in SotC. — [GameAnim analysis](https://www.gameanim.com/?p=135); [genDESIGN interview](https://www.gendesign.co.jp/qa_01/interview04en.html)

**Learned quadruped controllers**
- MANN (Zhang, Starke, Komura, Saito, SIGGRAPH 2018): a gating network blends "expert" weights, each specialising in a movement mode, and learns dog gaits from motion capture. — [80.lv](https://80.lv/articles/mode-adaptive-neural-networks-for-quadruped-motion-control); [HKU repository](https://hub.hku.hk/handle/10722/288761)
- Code is in AI4Animation, which is marked research/education only and "not freely available for commercial use or redistribution." The motion capture data is CC BY-NC 4.0. — [GitHub sebastianstarke/AI4Animation](https://github.com/sebastianstarke/AI4Animation)

### Inferences
- A UE2 hound needs no neural nets. A table of {duty factor, phase offset per foot} per gait, blended by speed (Spore-style), drives a 0..1 gait clock. Clips can stay authoritative for the "look" while the clock only times when foot IK is allowed to plant or lift. Suggested values from the biology: walk DF about 0.6–0.75 with the lateral sequence; trot DF about 0.5 with diagonals in sync; gallop rotary/transverse with a flight phase.
- Simplest robust step trigger for UE2 script: keep a world-space planted foot position. Each tick, compute an ideal foot spot (hip rest offset + velocity × half-step-time) and trace down to the floor. Step when the distance exceeds a threshold and the gait group is allowed (diagonal pairing for a quadruped). During flight, lerp along an arc.
- Body suspension: put the pelvis height at the average of the planted foot heights (front and rear pairs separately) and pitch the spine from the front-pair vs rear-pair height difference. This is the "hips translated and rotated as feet move" approach from Spore and the PhilS94 body adjustment.

### Gaps
- No primary detail on Rain World lizard leg-grip logic (TIGSource devlog not retrieved), Horizon machine foot IK, or Monster Hunter monster locomotion. The GDC Vault decks are members-only, and only abstracts were read.
- The Assassin's Creed "Fitting the World" Vault page was not opened; its description comes from a search snippet.
- Licence of the Spider Walker add-on and the Godot spider project not found.

## Layering procedural correction over clips: ground alignment, leg IK, spine bending in turns, head tracking, tails/springs

### Takeaway
The production pattern (Far Cry 4, Spore "Jiggles", Wolfire) is: clips first, then additive and IK corrections, then passive secondary motion on bones the clip does not drive. Spore's main lesson: secondary motion must be **one-way**. It reacts to the keyed pose and never feeds back into it, or the authored animation degrades.

### Cited Findings
- Far Cry 4 wildlife combines additive animation, environment detection, IK and character physics on top of animation data. — [GDC Vault 1022027](https://www.gdcvault.com/play/1022027/Grounding-Wildlife-in-the-Mountains)
- Quadrupeds have more points to correct than bipeds, because the pelvis and shoulders shift independently as each leg moves. — [Bryce Town: Rigging and animating a quadruped](https://brycetown.substack.com/p/deep-dive-rigging-and-animating)
- Flame in the Flood: a wolf with a procedural spine vs a boar with a rigid spine, a cheap way to fake bending in turns. — [GDC Vault 1023209](https://gdcvault.com/play/1023209/Animating-Quadruped-Characters-in-The)
- Spore "Jiggles":
  - Sub-trees not selected by the current animation (no IK goal) get a "very simple highly-damped pseudo-physical dynamics simulator", chosen by a heuristic for flexibility, placement and type.
  - It is "completely passive with respect to the keyed bodies and does not feed back to the rest of the character."
  - The earlier "Wiggles" system set IK goals instead, and that "negatively impacted the quality of the animators' work."
  - — [Hecker et al. 2008 PDF](https://www.cse.chalmers.se/edu/year/2011/course/TDA361/Advanced%20Computer%20Graphics/027-hecker%20copy.pdf)
- Tails and tentacles in practice:
  - **Verlet** point chains: store the current and previous position, then apply distance constraints with a pinned root and per-segment stiffness.
  - **Dynamic bones:** extra unkeyed bones are simulated, then drive skinning.
  - **Rotation springs:** delayed rotation that follows the parent.
  - Tail Animator (Unity, commercial) targets tentacles and squids.
  - — [Heathen Verlet Tools](https://kb.heathen.group/unity/physics/verlet-tools); [Tail Animator thread](https://discussions.unity.com/t/tail-animator-procedural-tail-animation-for-tentacles-simple-capes-squids-and-more/708463); [Rotation Spring video](https://vimeo.com/35477023); [Procedural Animation in Games overview](https://www.abratabia.com/game-animation/procedural-animation.php)
- Research on goal-directed tentacled locomotion: "Creating Procedural Animation for the Terrestrial Locomotion of Tentacled Digital Creatures." — [CORE](https://core.ac.uk/works/39545588)
- The Last Guardian (Trico): mostly hand-keyed, with procedural methods for the parts hand animation couldn't handle. They tried procedural animation "only partly" in SotC and more fully on Trico. The CEDEC 2017 talk by Masanobu Tanaka covered animal motion, quadruped walking, large size, and feathers. — [genDESIGN interview](https://www.gendesign.co.jp/qa_01/interview04en.html); [The Last Guardian, Wikipedia](https://en.wikipedia.org/wiki/The_Last_Guardian)

### Inferences
- UE2 mapping for the mod:
  - (1) Play the clip.
  - (2) Read foot bones with GetBoneCoords and trace down at each foot.
  - (3) Offset the pelvis/root by the average foot error and pitch/roll the spine bones from the front/rear and left/right height differences (SetBoneRotation-style additive).
  - (4) Two-bone analytic IK per leg (law of cosines) on thigh/shin, if the script can set per-bone rotations each tick.
  - (5) Bend the spine across 2–3 bones in proportion to yaw rate × speed.
  - (6) Point the head at the target with clamped yaw/pitch and a critically damped lerp.
  - (7) Run the tail as a damped spring per bone, lagging the parent's angular velocity. Keep it passive (Spore lesson).
- Steps (3), (5), (6) and (7) are cheap and need no foot IK. They likely give most of the visual gain for hounds.

### Gaps
- No public source gives the exact formulas of Far Cry 4 or Horizon. Spring constants and filter choices are design-tuned.

## Multi-arm / extra limbs (Goro, Grievous, Seekers): layering and per-arm aim

### Takeaway
Little technical material is public on game multi-arm rigs. Film work on Goro (Method Studios, 2021) treated the extra arms as an anatomy and choreography problem, and Spore shows the general approach: classify limbs by role and animate them by role ("graspers" and "feet") rather than by individual bone. For a mod, the practical answer is per-arm-pair layering: a lower pair from the clip and an upper pair overridden by an aim/IK layer, each with its own target and phase offset.

### Cited Findings
- Goro, Mortal Kombat (2021 film, Method Studios): the internal skeletal and muscular structure was worked out to decide how the extra arms work, which fed design and physically based muscle simulation. Motion capture was mixed with hand animation, and pre-viz tested fighting with four arms in tight sets. — [Ausfilm interview with Mr. X's Jason Billington](https://www.ausfilm.com/news/mr-xs-jason-billington-on-mortal-kombat/); [EventHubs on the 1995 film's animatronic Goro](https://eventhubs.com/news/2014/may/31/four-arms-fury-how-special-effects-team-brought-goro-life-first-mortal-kombat-movie)
- The 1995 film Goro was a 120 lb animatronic suit, not CG. — [EventHubs](https://eventhubs.com/news/2014/may/31/four-arms-fury-how-special-effects-team-brought-goro-life-first-mortal-kombat-movie)
- Game Goro rigs reduce complexity with 3 fingers per hand and 2 toes. A forum user notes that a naive four-arm rig needs 20 fingers to rig. — [DAZ forum](https://hpclscruffy.daz3d.com/forums/discussion/348376/multi-armed-gen-8-models)
- Spore lets channels share "variant groups" so a shoulder co-varies with its grasper. Motion is stored relative to limb roles (graspers, feet, spine), so one animation drives any number of arms. — [Hecker et al. 2008 PDF](https://www.cse.chalmers.se/edu/year/2011/course/TDA361/Advanced%20Computer%20Graphics/027-hecker%20copy.pdf)

### Inferences
- For Seekers:
  - Treat each arm pair as a separate layer.
  - Run aim-at-target per arm: clamped shoulder yaw/pitch, then an elbow bend from the distance to the target.
  - Stagger the pairs' timing (phase offset 0.1–0.25 of the action) so four arms never move in lockstep. This is the same "step trigger offset" idea as Spore gaits.
  - Give idle arms a tiny passive spring sway (Jiggles-style).

### Gaps
- No GDC or technical source found on game rigs for Goro (MK games), Grievous (Star Wars games) or other multi-armed game characters. Per-arm aim systems in shipped games are undocumented in the sources found.

## Reactive behaviour animation: hit reactions, limping, stagger, flinch, fear and aggression body language

### Takeaway
Reactive creature animation in games is mostly layered and state-driven. Spore treats limping as just another gait style layered on top. Monster Hunter's part-HP flinch/topple model and low-health limp are well known from players but not documented by Capcom. Modern procedural hit reactions are spring-driven additive rotations on the hit bone with distance falloff, which can be built from bone rotations alone. Readable emotion (Trico) comes from small channels like ears, tail and eye colour, not whole-body clips.

### Cited Findings
- Spore supports limping and lumbering as **gait styles layered on a character**, and different leg groups can be in different styles at once. — [Hecker et al. 2008 PDF](https://www.cse.chalmers.se/edu/year/2011/course/TDA361/Advanced%20Computer%20Graphics/027-hecker%20copy.pdf)
- Monster Hunter World (community observations, not Capcom docs):
  - Each body part has its own HP bar. Depleting it triggers a flinch, topple, or "dunk" for flyers.
  - Monsters limp when near death or capturable.
  - Broken parts are visible.
  - — [Steam discussion 1](https://steamcommunity.com/app/582010/discussions/0/3203652426719075545); [Steam discussion 2](https://steamcommunity.com/app/582010/discussions/0/595134572710073243)
  - An academic analysis credits MHW animation with clearly conveying information (rhythm, readability). — [UFMG paper](https://eba.ufmg.br/tccs/index.php/caad/article/view/204)
- Procedural additive hit reactions (UE "Easy Procedural Hit Reactions" plugin):
  - Inputs: impact location, direction, hit bone and strength.
  - Output: rotational and positional springs with influence radius and falloff, spring recovery, and per-bone max-rotation limits.
  - It runs after the normal pose, so it needs no hit clips.
  - — [UE forum](https://forums.unrealengine.com/t/kettunen-easy-procedural-hit-reactions/2741781); [Fab listing](https://www.fab.com/listings/b22e4f67-b581-4477-959c-7db19a7537b8)
- George Giokas prototype: heavy hits drive a partial ragdoll that wobbles and recovers through physics and curves, then becomes a full ragdoll on death. — [itch.io](https://george-giokas.itch.io)
- Trico (The Last Guardian):
  - Ears twitch and swivel at sounds, and eye colour signals mood (pink for anger or wariness). These come from reviews and developer statements.
  - Tail curling by mood is a user recollection only.
  - — [Wikipedia](https://en.wikipedia.org/wiki/The_Last_Guardian); [bit-tech review](https://bit-tech.net/reviews/gaming/the-last-guardian-review/1/); [TheSixthAxis: Ueda on animation](https://www.thesixthaxis.com/2010/09/02/fumito-ueda-talks-about-animation-in-the-last-guardian/)
- Rain World ties animation to AI: creatures have survival drives (food, shelter, territory), and their body motion results from those drives on a soft point-body. — [Game Developer](https://gamedeveloper.com/design/crafting-the-complex-chaotic-ecosystem-of-i-rain-world-i-)

### Inferences
- **Hound limp:** when a leg is damaged, raise its duty factor penalty (shorter stance), lower that hip during stance, and shift body weight to the other legs. In the Spore model this means changing gait parameters only, not adding clips.
- **Flinch:** add a damped-spring rotation impulse at the hit bone plus its parent (spine), with direction from the hit vector, then decay (about 0.2–0.4 s).
- **Stagger:** briefly add lateral root drift, and let the foot-step logic re-plant the feet.
- **Fear and threat displays as pose offsets blended by an emotion scalar:**
  - Fear: lower pelvis/head, tail down or tucked, ears back, slower gait (higher duty factor).
  - Threat: raised head and shoulders, spine arched up, frills/plumes up, a side-on turn to show size. This matches the user's "angry bird puff-up" reference.
  - These can be static additive rotations on 4–8 bones, using no new clips.

### Gaps
- No primary Capcom, Guerrilla or Ueda technical source describes the limp, flinch or emotion system architecture. The CEDEC 2017 Trico talk (Japanese) was not retrieved.
- No source found on game creature "threat display" animation systems specifically.

## Open-source code and licences

### Takeaway
Most notable creature-animation code is not freely reusable: AI4Animation/MANN is research-only (NC data), PhilS94's spider goes through the Asset Store, and Spore is proprietary. For a GPL/share-alike mod, the safe path is to re-implement the published algorithms (Spore gait parameters, raycast step prediction, Verlet/spring tails), which are ideas, not code.

### Cited Findings
- **AI4Animation** (PFNN, MANN, DeepPhase, Local Motion Phases, etc.): research/education only, "not freely available for commercial use or redistribution"; mocap data CC BY-NC 4.0. — [GitHub](https://github.com/sebastianstarke/AI4Animation)
- **mann-pytorch** (ami-iit/evelyd): a PyTorch MANN port; licence not verified. — [GitHub evelyd/mann-pytorch](https://github.com/evelyd/mann-pytorch)
- **PhilS94 Unity wall-walking spider:** deprecated, licensed through the Unity Asset Store, sublicensing and selling prohibited. — [GitHub](https://github.com/PhilS94/Unity-Procedural-IK-Wall-Walking-Spider)
- **OpenCat** (Petoi robot quadruped gaits): MIT. **open-quadruped:** Bezier gait plus 3-DOF leg IK; licence unverified. Both are robotics projects, useful for gait-curve math. — [awesome.ecosyste.ms OpenCat](https://awesome.ecosyste.ms/projects/github.com%2Fpetoicamp%2Fopencat); [open-quadruped](https://gittrend.io/repo/adham-elarabawy/open-quadruped)
- **Spore paper:** "Copyright Chris Hecker, All Rights Reserved"; no code. — [chrishecker.com](https://chrishecker.com/Real-time_Motion_Retargeting_to_Highly_Varied_User-Created_Morphologies)
- **Commercial UE/Unity plugins** (Easy Procedural Hit Reactions, Tail Animator, Procedural Spider asset): marketplace licences; reference only. — [Fab](https://www.fab.com/listings/b22e4f67-b581-4477-959c-7db19a7537b8); [Unity Asset Store Procedural Spider](https://assetstore-fallback.unity.com/packages/tools/animation/procedural-spider-267789)

### Inferences
- All the algorithms needed (gait clock, trace-based stepping, analytic two-bone IK, spring tails, additive flinch) are short and well described. Clean-room UnrealScript versions avoid licence issues and fit the user's GPL/share-alike modding rule.

### Gaps
- Licences for the Spider Walker add-on, the Godot 4.5 spider, the TAMU Wolfire reimplementation and open-quadruped were not confirmed. No permissively licensed, game-oriented quadruped procedural-locomotion library was found in these searches.
