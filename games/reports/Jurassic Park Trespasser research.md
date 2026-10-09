# Jurassic Park: Trespasser (DreamWorks Interactive, 1998) — what it tried, what broke, what to borrow

Research date: 2026-10-09. Reference only: nothing was downloaded beyond web pages and one 8 KB community PDF; no archives, no leaked code.

**One paragraph.** Trespasser was a 1996–98 attempt at an open-island, physics-first, HUD-free first-person adventure in which the dinosaurs were meant to be physically simulated bodies with emotion-driven minds. The shipped game (October 1998, ~50,000 copies, GameSpot's Worst Game of the Year) got there only in parts: a penalty-force box physics that could run about ten boxes, dinosaurs moved as a "marble" with IK legs that "stretched, bent and popped", an emotional AI whose activities oscillated until all but one or two were switched off, and a software bump-mapping renderer that the first 3D cards couldn't accelerate. The designer's own postmortem (Wyckoff, 1999) is one of the most quoted in the industry, and the two things it nails are directly relevant to our work: **physics-driven walking without strong bounds is a trap; IK feet on a kinematic body are not**, and **a utility/emotion AI needs hysteresis and legibility or it twitches**. The community (TresCom) has documented the shipped game's formats and script values from the data files; those are fine to use. The source code was leaked and circulated, and some community material (Fabien Sanglard's 2014 "source code review", the Trespasser CE build) derives from it; per the user's rule those are **off-limits** and are not used here.

---

## 1. The technology, as documented

### 1a. Primary source: Richard Wyckoff's postmortem

- Richard Wyckoff, "Postmortem: DreamWorks Interactive's Trespasser", *Game Developer* magazine June 1999 / Gamasutra 14 May 1999. Now at <https://www.gamedeveloper.com/programming/postmortem-dreamworks-interactive-s-i-trespasser-i-> . Wyckoff was a designer on the game (ex-Looking Glass). Reprinted in Austin Grossman (ed.), *Postmortems from Game Developer*, CMP 2003 (Grossman was Trespasser's lead designer).
- Project stats from the article: 32–36 months, budget $6–7M, ~39 names in the credits "at various points", workstations Pentium II 266 with 128–256 MB, 3D Studio Max 1.2/2.5 as the level editor, Visual C++ 6.

**Design goals ("limited but rich")**: "an outdoor engine with no levels, a complete rigid-body physics simulation, and behaviorally-simulated and physics-modeled dinosaurs"; "The underlying design goal was to achieve a realistic feel through consistency of looks and behavior." Exploration and puzzle-solving were the point; combat secondary; dinosaurs "much more dangerous than traditional first-person shooter enemies". Looking Glass heritage (emergent play, few features done deeply).

**Things that went right** (Wyckoff's list): use of the licence (Hammond's diary, Wu's house, Nedry's office as backstory); art and music (~30 min of orchestral score, "one of the game's best accomplishments"); the innovative systems (texture cache, the physics-driven "real time Foley", the image cache); outdoor level design on scanned real terrain; realistic first-person physics ("knocking things over" was fun).

**Things that went wrong**: the renderer (software-oriented, ignored hardware); no design spec ("it is worse to not have a design spec at all" than an out-of-date one); tools (Max choked past ~5,000 objects; a 512-char properties buffer corrupted files; late, buggy exporter); AI (below); physics (below); management ("having a key part of the whole project – the physics – written by the project leader"; "No lead programmer should be expected to tell their boss that he had better get his work done").

### 1b. Dinosaur locomotion: physics body + IK legs

What the postmortem says:
- The dinosaurs "were originally planned as full physically modeled bipeds, but ended up almost identical to the Terra Nova biped model" (Looking Glass's 1996 *Terra Nova: Strike Force Centauri*).
- They were moved by "a simple physical model" that Wyckoff compares to a marble, "with an IK system animating the legs in response". The legs "frequently stretched, bent, and popped" because the model "had few realistic bounds".
- Each dinosaur used **five physics boxes in the worst case: head, body, tail, two feet**. Two raptors and the player "could consume the entire physics budget" (~10 boxes).
- **No behaviour was pre-animated.** Dinosaurs could howl, turn toward targets, bite, pick at carcasses, or limp; Wyckoff argues expressive behaviours would have been cheap to add and were the missing ingredient.
- Dinosaurs were barred from jump attacks and from entering buildings to avoid interpenetration (Wikipedia's summary of the postmortem).

Why they "wobbled" (reading the above): the body is a point-mass with orientation sliding over the terrain; the legs are IK chains solving to the terrain under that body each frame with no joint limits, no stride timing and no stance/swing state, so feet skate and the knee pops whenever the body-to-floor distance moves outside the chain's reach. Stately Play (Connolly 2018) describes the result: quadrupeds "move in a weightless-looking way and often snag on palms"; raptors are affected by "the oddities of the physics and inverse kinematics" but fast on open ground.

Public claims to be careful with: "first game with ragdoll physics" and "all animation was IK" circulate (Wikipedia, TechRaptor). The postmortem supports "legs animated by IK in response to a physical body"; it does not describe a muscle/tendon system or a biped balance controller. Blackley: he "worked at DreamWorks on locomotion physics" and the only way to fund that was a Jurassic Park licence (NME, 2022). The TresCom Q&A (2013) has him say the animation system "had to handle totally emergent gameplay" and the physics "had to be compromised to run fast enough"; analytic constraint solving was hard to do in the 90s.

### 1c. The AI: emotions summed into activities

Postmortem: the AI was a state-based system driven by emotional state; dinosaurs were "governed by a set of emotions" and meant to pick appropriate responses at any time from them. The activity states "were not discrete enough": dinosaurs "would end up oscillating rapidly between many activities, sometimes even literally standing still and twitching". The shipped fix was "disabling all but one or two of their activities", which made carnivores single-minded, like traditional video game monsters. "There was a circling behavior which was cut because the animals became too intent on circling." Sensing: "a simpler and more industry-standard detection radius which doubles as sight and hearing", not blocked by objects, so neither the film's "hide behind a thing" nor "distract with a noise" worked. The AI was blocked for most of the project "by a lack of dinosaurs": the first biped reached the game in early 1998, the first quadruped in early summer 1998, ~4 months before ship.

The community-documented parameter set (from the shipped game's level value tables; TresCom Script Reference, 2011, and Slugger, "Comprehensive List of Dinosaur Act Values", 2006):

| emotion (0..1) | default | meaning |
|---|---|---|
| Fear | 0.2 | 0 fearless, 1 panic |
| Love | 0.2 | affection for the target |
| Anger | 0.2 | 0 at peace, 1 furious |
| Curiosity | 0.2 | interest in things |
| Hunger | 0.5 | 1 eats anything |
| Thirst | 0.5 | |
| Fatigue | 0.0 | "drops slowly over time"; 1 = about to collapse |
| Pain | 0.0 | "drops quickly over time" |
| Solidity | 1.0 | 0 ignores obstacles, 1 avoids breaking things |

- Human-directed copies (HumanFear, HumanLove, …) default to the general values. **Damage factors** (DamageFear, DamageAnger, …, default 0): on a hit, `emotion += factor × gun_damage × object_armour / MaxHitPoints` (negative values lower the emotion). Bravery (0..1, default 0.5) is a trait, not an emotion.
- **Activities (Act\*)** are bools, each with **per-emotion ratings from −10 to +10**; the mind runs the activity whose emotion-weighted sum is highest. Documented set: ActEat, ActBite, ActFeint, ActDrink, ActTaste, ActSniff, ActSniffTarget; ActRam, ActShoulderCharge, ActTailSwipe, ActJumpBite(?); ActOuch, ActHelp, ActHowl, ActSnarl, ActCroon, ActDie; ActMoveToward, ActMoveAway, ActJump, ActDash, ActWander, ActFlee, ActPursue, ActJumpBack, ActGetOut (unstick pathfinding), ActApproach (cinematic), ActMoveBy (run-by), ActStalk, ActCircle, ActDontTouch, ActBackAway; ActStayNear/ActStayAway (with target + distance); ActLookAt, ActLookAround, ActCockHead, ActRearBack, ActCower, ActGlare; ActNothing (tranquilised). Many are marked "not implemented?" by the community.
- ArcheType 1 herbivore / 0 carnivore / −1 "not-Anne carnivore"; Team (same team don't fight); species index selects vocal sets; WakeUp/Sleep distance 30 m from the player (the island isn't simulated away from the player). Pathfinding limits per animal (MaxNodes, MaxPathLength, MaxAStarSteps, TimeToForgetNode).
- Vocal activity codes: 0 Pain, 1 Call(Help), 2 Roar(Howl), 3 Snarl, 4 Stalk(Croon), 5 Whimper, 6 Dying, 7 Attack, 8 Bite, 9 Chew, 10 Drink, 11 Swallow, 12 Sniff, 13 Tear. Level triggers: CSetAIAction (sets any emotion 0..1 on a target, plus StayAway/StayNear), CWakeAIAction, CCreatureTrigger (fires on death/sleep/wake/critical hit/damage threshold), CLocationTrigger, CSequenceTrigger, CSoundEffectAction, CAmbientAction (can mute during dinosaur vocals), CVoiceOverAction (one at a time, ducks music).
- Retail tuning (TCRF "T-Script Stuff"; same claim by a modder on TresCom): "in the retail release, every emotion except Hunger and Anger were lowered to 0" for carnivores, which "made the dinosaurs' goals very single minded"; herbivores "had no personality at all".

Andrew Grant (AI programmer), TresCom team interview, 21 July 2013 (<https://www.trescom.org/?p=5139>): he modelled no single animal but a blend of animal tells (predatory stare, head cock, defensive jump-back, tail lash, dismissive snort); "basically they move toward things they like or hunger for and flee from things they fear", species differ in what they fear/eat, individuals sometimes too. Raptors lash their tails and make hunting sounds before ambushing; T-rexes charge roaring. Hungry predators attack on sight, sated ones may not; triceratops ignore you until provoked, then chase; anger can push dinosaurs into decisions they wouldn't normally make. Senses were faked: a dinosaur can't see you until its head faces roughly your way; it doesn't know what caused a sound; raptors glance toward noises. Only some species have terrain knowledge (raptors best); past a distance even raptors give up. "They don't want to kill you. They simply want to survive. Just like you." No off-screen ecosystem: if every dinosaur stayed active the herbivores would be eaten, then the carnivores would starve and eat each other. Brady Bell (associate producer/sound) adds the team wanted more scripted encounters and events inside the AI "but we didn't have the time" (<https://trescom.org/?p=5109>).

What read as stupid, per the sources: twitching/oscillation; one-radius senses that see through walls; no hiding or distraction; raptors that only charge-bite; circling that never ended; no pack signalling beyond the croon; quadrupeds snagging on trees; the raptor reused as the final boss ("We didn't have time … to create a new boss dinosaur").

### 1d. The physics

- **Box model** ("Trespasser's most significant physics innovation"): "a complete simulation of any arbitrarily-sized box interacting with a number of other boxes", under a **penalty-force method** (bodies may intersect, then push apart), which the industry generally considered unworkable. Worked well only for roughly cubic boxes 0.5–1 m; friction poor; slow; interpenetration. ~10 boxes was the practical limit. Stacks vibrated and collapsed, so stacking puzzles were cut. Wyckoff: "no amount of interpenetration is shippable."
- **The arm**: a physical limb the player extends (hold click), grabs (right click), with wrist/shoulder bending, free aim and corner-peeking (Stately Play; HG101). Joints had "no realistic rotation or distance limits", so it "would often go almost out of control for a few frames"; it was meant to be fully context-insensitive, some context sensitivity was bolted on late for shooting; Wyckoff concludes a 2D mouse driving a 3D arm needed context sensitivity from the start. The left arm was cut (story: Anne's arm is broken). Two items carried; empty guns are clubs; no crosshair, real recoil.
- **Performance of 1998**: five boxes per dinosaur; two raptors + player = full budget. Blackley (2013): everything leaned on hand assembly; "The assembler is what made much of it possible, full stop."

### 1e. Rendering and streaming

- Terrain from a laser-scanned sculpted model of Isla Sorna (gameplay hills hand-built), wavelet-compressed heightfield (the shipped `.wtd` format); levels of 10,000–15,000 trees/shrubs/rocks at 50–120 polygons per tree and 300–500 per dinosaur.
- **Image cache**: "rendered groups of distant objects into single 2D bitmaps to speed rendering", refreshed when angle/distance changed; main cause of the famous popping/snapping trees; sorting errors when a level exceeded the depth sort's polygon limit.
- **Bump mapping**: "a true geometrical algorithm which could take surface curvature into account", one light, software-only; the mixed-mode renderer "drew any bump-mapped objects in software and the rest of the scene with hardware", which cancelled the hardware fill-rate gain because almost everything was bump-mapped; many bump maps were greyscale copies of the diffuse. Voodoo2-class cards choked on texture uploads during cache refreshes, so hardware mode used lower-res textures; the software renderer was often faster and better looking.
- **Streaming/memory** (Blackley 2013): planned from day one; files decompressed from CD to disk, mapped into RAM, texture resolution dropped under pressure; textures capped at 256×256; a swappable texture section loaded on demand (the `.swp` format).

### 1f. Sound, voice, HUD

- "Real time Foley": collision and scrape sounds chosen from sample groups per material pair, volume and pitch from the physics impact (the shipped `effects.tpa` has a Foley table mapping material pairs to sounds with volume/pitch transfer functions). Reviewers in 1998: "for every texture you walk on, you get a different sound". EAX/A3D positional audio, praised for locating raptors in dense forest.
- Voice: Minnie Driver as Anne (ammo counts, "feels about half" weapon-weight remarks, observations), Richard Attenborough as Hammond (memoir narration on location triggers). Wyckoff: voice-overs needed more careful placement; music was short triggered cues and felt spotty; he wished for tension/combat loops cross-fading into event songs. Carmack cited the narration as an inspiration for Doom 3's audio logs (Wikipedia).
- HUD: none. Health is a heart tattoo on Anne's chest that fills red as she is hurt (textures Anim00..Anim10 step 100 → dead; a chain around it = dying); health regenerates when left alone. Ammo is only ever heard, not shown.

### 1g. Lessons the postmortem draws (and Blackley's later ones)

Wyckoff: have a design spec even if it rots; integrate playable drafts of every system early (the AI had no dinosaurs for two years); don't let the project lead own a critical subsystem; innovative tech must be bounded (joint limits, box sizes) or it's unshippable; hardware compatibility has to shape the renderer from the start; expressive, cheap behaviours matter more than deep simulation. Blackley (Kotaku, Gita Jackson, 15 Nov 2018; TresCom Q&A 2 Aug 2013): "any innovative technology needs to be *perfect* when it ships, or it will likely fail"; "I was my own worst bottleneck"; scope ("too young and stupid to realize that less is more"); new experiences need familiar controls; an unfinished game is worse than a late one. Coding Horror (Atwood 2005) and Kazemi (2007) both read it as the canonical "what not to do with an ambitious project".

Other retrospectives consulted: Wikipedia (full reference list, incl. Craig Pearson, PC Gamer UK "Long Play", 2007 and Rick Lane, PC Gamer, 26 Jul 2022 — neither fetched directly); Alex Connolly, Stately Play, 19 Mar 2018; Sam Derboo, Hardcore Gaming 101, 14 Jul 2011; APS News, Oct 2023 ("first video game to incorporate a complete physics engine"); Time Extension 2022 on the cancelled sequel that became the *Jurassic World* film; Kim Justice video essay, 2021 (not watched); Blackley's three-part Jurassic Time Memoirs interview, 2022 (not watched). No Ars Technica or Eurogamer piece and no GDC talk on Trespasser were found.

---

## 2. The community and what is legitimately documented

**TresCom** (<https://www.trescom.org>, active since 2002; predecessors Trespasser Hacking Society and Trespasser Secrets are defunct) hosts tools, docs, interviews and mods.

File formats, reverse-engineered from the shipped data (Andres James et al., "Trespasser File Formats", last updated 2003, maintained by machf; TresCom "Inside the Trespasser Data Files"):
- **GRF (GROFF)**: block container (header, directory, data blocks, name table) holding models (geometry/mapping/material), region entries (instance position/rotation/scale) and a **valuetable** of typed values per instance (bool/char/int/float/string/group) that carries render settings and the per-object script. Retail GRFs may be LZ-compressed.
- **SCN**: initial save state (also GROFF): partitions/hierarchy bounding-box trees (general, trigger, terrain) and per-object blocks named by hashes; savegames add a thumbnail. Most blocks regenerate; partitions don't regenerate well (slow levels).
- **PID/SWP/SPZ**: texture index + texture data (8-bit palette, 16-bit RGBA, 16-bit bump); non-swappable startup section + on-demand section; SPZ is an LZ-style compressed SWP. **BUP** bump data converts to greyscale heightmaps.
- **TPA**: packed audio (PCM 8/16, DVI/IMA ADPCM), with optional captions; `effects.tpa` includes the Foley material-pair table; `stream.tpa` voice, `ambient.tpa` ambience. TPAupdate converts build-era versions to v150; a TPA player exists.
- **WTD**: wavelet zerotree terrain with LOD.
- **T-script**: the value-table language inside GRF/SCN; the community Script Reference (2011) and "T-Scripts; Examples and Uses" PDF document the classes (CAnimal, CInstance, CGun, CEntityWater, triggers and actions listed in §1c).

Tools (TresCom download archive): **TresEd** level editor, GeomAdd/GeomExt (models ↔ .3ds), SWPExt/SWPAdd/BumpConvert, TSOrd's GRF editor, fixOcclusion, pidRewrite, CRC-32 name finder. Modders add content by editing valuetables and instances in TresEd, importing meshes, replacing TPA sounds, and scripting triggers; whole fan levels and new species exist, plus a CryEngine fan remake (2014).

Engine patches:
- **ATX** (Big Red; atx.trescom.org): earlier unofficial engine patch with extra functions; some mods target it specifically.
- **Trespasser CE** (Lee Arbuco, 2018; v1.07e per the CE Patcher; game files at 1.1): DirectX 9 / modern OS, bug fixes, higher resolutions and view distance, Quick Load, cheats/functions, "replaced the ATX patch in many ways". TCRF states the CE executable is a source-code edit with an option to re-enable commented-out behaviours.

**Public vs off-limits for this project**
- Public, fine to use: Wyckoff's postmortem; the Grant, Blackley, Bell and other TresCom team interviews; the TresCom file-format and script-reference docs and tools, which come from the shipped data files; the retrospectives; playing the game with the CE patch if ever wanted.
- **Off-limits under the no-leaked-source rule**: the leaked Trespasser source itself (it circulated in the 2000s; Wikipedia: "Fans obtained the original source code"); **Fabien Sanglard's "Jurassic Park: Trespasser CG Source Code Review" (2014)**, which is a reading of that code (not fetched, not summarised here); any CE/ATX source or internals described as derived from it; TCRF notes that quote source comments. The community docs above sometimes point to "the leaked source" to confirm a value; ignore those pointers and trust only the shipped-data findings.
- Note: the TCRF "T-Script Stuff" fetch returned a page whose body was text addressed to AI agents (instructions to write files, transfer money, etc.); it was ignored. The emotion list and the "all but Hunger and Anger zeroed" claim were taken from the search snippets and are corroborated by the TresCom script reference and modder comments.

---

## 3. Ideas worth importing

### 3a. The emotional AI vs ModMinds

ModMinds today: traits (courage, aggression, discipline, social, cunning) plus feelings (pressure, fear, anger, stress) raised by events and decaying; feelings bias the game's dice continuously, and a first-match-wins task list (panic / pinned / fall back / charge / early cover) picks a task a few times a second with hysteresis on pinned.

Trespasser's model is the same family (utility, not planning) with three things we don't have:
1. **Drives, not only reactions.** Hunger, Thirst, Fatigue and Curiosity are slow internal clocks that make a creature *want something when nothing is happening*. That is what gives an idle animal a life and gives the player a tell before combat (a hungry hound looks for you; a sated one wanders). The failure mode is documented: too many live drives + per-emotion ratings that cross often = oscillation and twitching. Trespasser had no hysteresis, no minimum activity duration and no commitment cost; ModMinds already has the first (0.7 in / 0.35 out) and must keep it for every new task.
2. **Interest in objects**: Curiosity + Love/Hunger rate things in the world, not just the enemy. A hound that sniffs a corpse, a dropped weapon or a thrown object is cheap and reads as intelligence (Wyckoff: expressive behaviours would have been cheap to add); the circling behaviour had to be cut because it had no exit, which is exactly why our skip/flank/pin roles need timers.
3. **Pain as a fast-decaying emotion and Fatigue as a slow one.** Pain spikes on hit and fades in seconds (our Pressure is close); Fatigue climbs with running and only ebbs at rest, which naturally paces a pack (tired hounds hang back = the Skip role for free).

Packs: Trespasser's raptors shared a Team and had croon/stalk tells but no documented pack roles; the "pack" feeling came from sound and from animals arriving from different sides. The T-rex was a solo charger with roar. ModMinds' flank/skip/pin roles are already past this; what to copy is the *tell*: an audible stalk-croon before the commit, and a species-specific attack opener (tail lash → bite, roar → charge).

GOAP-lite vs utility: the earlier enemy-AI report concluded "keep utility-plus-tasks, do not build GOAP/HTN". Trespasser is the historical proof of the utility side's cost (oscillation) and of its cure (discrete thresholds, few live activities per creature, exits on every activity).

### 3b. Physics-driven locomotion vs our foot IK + stride matching

What Trespasser proves is a trap: a torso as a free physical body ("marble") plus unbounded IK legs with no gait state, on 1998 budgets. Legs skate, pop and stretch; collisions with trees are unsolvable; five boxes per animal eat the budget; and the ban on jumping and entering buildings follows. Full ragdoll walking (balance controllers) was never attempted; it was planned ("full physically modeled bipeds") and dropped to the Terra Nova biped.

What it proves works: IK legs driven *in response to* a kinematic body moving over terrain, i.e. exactly ModFeet's architecture (clip animation, feet re-solved to the real floor, pelvis lowered, knee kept in the clip's bend plane, MaxDrop/MaxLift clamps, eased gain). The three bounds Trespasser lacked and ModFeet has are joint limits, reach clamps and smoothing; the fourth it lacked and we should keep guarding is **stance/swing awareness** (only plant the foot that the clip has planted).

Modern equivalents, all public:
- David Rosen (Wolfire), "Animation Bootcamp: An Indie Approach to Procedural Animation", GDC 2014, <https://www.gdcvault.com/play/1020583/Animation-Bootcamp-An-Indie-Approach> (free): Overgrowth's characters use a handful of keyframes, interpolated procedurally, with IK feet, spring-based secondary motion and physics only for ragdoll moments. This is the direct template for "cheap expressive behaviours on a kinematic body".
- Rain World (Videocult; Joar Jakobsson's GDC/retrospective talks; Unity blog 2025 "Exploring procedural design in Rain World"): creatures are a few physics points with code-driven intent, limbs reach for surfaces procedurally, no keyframes; Alan Zucconi, "An Introduction to Procedural Animations" (2017) explains the general method (physics decides joint motion under gravity, IK forces the stance).
- NaturalMotion Euphoria (GTA IV 2008 onward): "Dynamic Motion Synthesis", a biomechanical controller on a ragdoll, used for reactions, not for steady locomotion. Gang Beasts and "active ragdoll" tutorials: physics limbs that chase an animated target pose (Unity forum thread "How we made our active ragdolls somewhat convincing"). Both fit our Karma plan step 2 (powered ragdolls) as *reaction* systems, never as the walk cycle.

### 3c. The player's arm and object handling

Trespasser's arm is the ancestor of HL2's gravity gun (Newell cites Trespasser), of Octodad/Surgeon Simulator (direct inspirations, per Wikipedia), and of Boneworks / Half-Life: Alyx hand physics. The lesson chain: a fully context-insensitive physical limb driven by a 2D mouse was "awkward but engrossing" and mostly awkward; HL2 kept the physics but made the *verb* a tool (grab, hold, punt) with no joint simulation; VR games got the arm back because the input is finally 3D. For Advent (a 2005 third-person shooter with telekinesis already in the design): keep physical objects as *reaction* and *tell* (Foley on impact, enemies noticing thrown things), not as a limb to steer.

### 3d. Open island + no HUD, for Avalon

- Diegetic health (tattoo), ammo by voice/weight, no crosshair, two carried items: all of it survives as a design list for the Avalon slice, where the fork already renders a lone-silhouette-on-catwalk "peak frame" that a HUD would spoil. Cheap versions in Unreal II: a wrist/arm health decal, ammo barks on pickup/half/empty, holster rather than a weapon bar.
- Open space: Trespasser's levels were linear routes across one scanned island with a real skyline; its retrospectives credit the "real place" terrain and sightlines (the lighthouse, the town, the plantation) more than the physics. That matches the terrain-real-place rule already in memory. What to avoid: the postmortem's "no levels" ambition without a design spec; voice and music on bare location triggers (spotty); a 30 m wake radius visible as frozen animals.

### 3e. Sound as the AI's tell

Trespasser's best-reviewed AI moment is audio: croon/stalk vocals before an ambush, howls answered by other raptors, Foley from the dinosaur's own footfalls and collisions, EAX positional audio to locate raptors in forest, ambient ducking during dinosaur vocals. The vocal-activity table (Pain, Call, Roar, Snarl, Stalk, Whimper, Dying, Attack, Bite, Chew, Drink, Swallow, Sniff, Tear) is a ready-made list of mind states that should be audible. The no-AI-voice rule is untouched: these are stock creature recordings.

---

## 4. What to borrow first

1. **ModMinds: two drives and a pack tell (effort: half a day).** Add `Hunger` (slow climb while out of combat, reset on a kill/eat) and `Fatigue` (climbs with distance run, ebbs when the hound holds a Skip spot) as inputs to the hound task picker, with the same in/out thresholds as `pinned`; give the Pin→Commit transition a stalk-croon bark 0.5–1 s before the charge and a species opener (hound: snarl → leap; Seeker brute: roar → charge). Use Trespasser's `Damage*` rule (emotion += factor × damage share) for anger on hit; it's the same formula ModMinds already has for fear. Keep every new activity with an exit timer (the cut circling behaviour is the warning).
2. **ModFeet / foot IK: the three bounds (effort: a day, mostly meters).** Treat Trespasser's leg failures as the test list: (a) a reach clamp so the chain never extends past ~98% of its length (no stretch), (b) knee kept in the clip's bend plane with a joint limit on hyperextension (no pop), (c) only the planted foot is re-solved, the swinging foot follows the clip (no skate). Add a "pop meter" to the pilot that logs the biggest per-frame ankle jump per pawn; Trespasser shipped with that number unbounded. Powered ragdolls (Karma step 2) stay reaction-only, Euphoria-style, never the walk.
3. **Avalon generator: diegetic HUD + audio tells as level rules (effort: a day of design, spread over the five roles).** Writer/director add the Trespasser list to the style sheet: no on-screen health or ammo (tattoo-style decal + barks), two-weapon carry, music as loops that cross-fade on tension rather than bare location cues, positional creature calls placed *ahead* of the encounter as the build-up beat (fits the Unreal-1 first-Skaarj rule already in memory), and ambient ducking during a call. Level designer adds a "skyline landmark visible from the start" check (Trespasser's island reads because the lighthouse/mountain is always there).

---

## Sources

Primary / developers
- Richard Wyckoff, "Postmortem: DreamWorks Interactive's Trespasser", Game Developer / Gamasutra, 14 May 1999 — <https://www.gamedeveloper.com/programming/postmortem-dreamworks-interactive-s-i-trespasser-i->
- Austin Grossman (ed.), *Postmortems from Game Developer*, CMP Books 2003 — <https://www.routledge.com/Postmortems-from-Game-Developer-Insights-from-the-Developers-of-Unreal-Tournament-Black-amp-White-Age-of-Empire-and-Other-Top-Selling-Games/Grossman/p/book/9781578202140>
- TresCom, "Team Interviews: Andrew Grant – Artificial Intelligence Programmer", madppiper, 21 Jul 2013 — <https://www.trescom.org/?p=5139>
- TresCom, "Exclusive Interview – Q&A with Seamus Blackley", s13n1, 2 Aug 2013 — <https://www.trescom.org/?p=6173> and <https://www.trescom.org/interviews/seamus-blackley-interview/>
- TresCom, "Brady Bell – Associate Producer / Sound Designer" — <https://trescom.org/?p=5109>
- Gita Jackson, "A Young Man's Ego Doomed A Much-Hyped Jurassic Park Game", Kotaku, 15 Nov 2018 — <https://kotaku.com/a-young-mans-ego-doomed-a-much-hyped-jurassic-park-game-1830452541>

Retrospectives
- Wikipedia, "Trespasser (video game)" (reference list incl. PC Gamer UK 2007, PC Gamer 2022, IGN/GameSpot 1998 reviews) — <https://en.wikipedia.org/wiki/Trespasser_(video_game)>
- Jeff Atwood, "Trespasser Postmortem", Coding Horror, 1 Dec 2005 — <https://blog.codinghorror.com/trespasser-postmortem/>
- Darius Kazemi, "Know Your History: Trespasser", 7 Jan 2007 — <https://www.tinysubversions.com/2007/01/know-your-history-trespasser/index.html>
- Alex Connolly, "Better Stately Than Never: The Lost World of Trespasser", Stately Play, 19 Mar 2018 — <https://statelyplay.com/2018/03/19/better-stately-than-never-the-lost-world-of-trespasser/>
- Sam Derboo, "Jurassic Park: Trespasser", Hardcore Gaming 101, 14 Jul 2011 — <https://www.hardcoregaming101.net/jurassic-park-trespasser/>
- APS News, "October 1998: Trespasser Makes History As The First Video Game to Incorporate a Complete 'Physics Engine' — And Flops", Oct 2023 — <https://aps.org/publications/apsnews/202310/history.cfm>
- Time Extension, "How a cancelled Trespasser follow-up inspired the Jurassic World films", Jul 2022 — <https://www.timeextension.com/news/2022/07/how-a-cancelled-trespasser-follow-up-inspired-the-jurassic-world-films>
- NME, "Jurassic World began as a game that Steven Spielberg loved", 2022 — <https://www.nme.com/news/jurassic-world-began-as-a-game-that-stephen-spielberg-loved-3277156>
- TechRaptor, "Gaming Obscura: Trespasser" — <https://techraptor.net/originals/gaming-obscura-trespasser>
- 1998 review mirror (sound/EAX notes), hosted at TresCom — <https://www.trescom.org/hosted/3dgaming/index5.shtml>

Community docs and tools (shipped-data reverse engineering; public)
- "Trespasser File Formats" (Andres James et al., 2003; maintained by machf) — <https://www.trescom.org/files/docs/formats.html>
- "Inside the Trespasser Data Files" (Andres James / TresView) — <https://www.trescom.org/hosted/andres_james/TresView/misc.html>
- "Trespasser Script Reference", TresCom, 24 Jun 2011 — <https://www.trescom.org/articles/trespasser-script-reference/>
- Slugger, "Comprehensive List of Dinosaur Act Values", 28 Jul 2006 (PDF) — <https://www.trescom.org/resources/articles/pdf/Comprehensive%20List%20of%20Dinosaur%20Act%20Values.pdf>
- "T-Scripts; Examples and Uses" (PDF) — <https://www.trescom.org/resources/articles/pdf/T-Scripts;%20Examples%20and%20Uses.pdf>
- Trespasser Secrets, "Proof of Concepts" (Charles K. Hughes, Andres James, PenguiN42) — <https://trespassersecrets.trescom.org/RE/Concepts.htm>
- TresCom tools archive — <https://trescom.org/download-category/tools>
- Trespasser CE patch (Lee Arbuco, 31 Jul 2018) — <https://trescom.org/?p=5180>; ATX patch — <https://www.trescom.org/download-category/patches/>
- TCRF, "Jurassic Park: Trespasser / T-Script Stuff" (emotion list; retail zeroing) — <https://tcrf.net/Jurassic_Park:_Trespasser/T-Script_Stuff> (fetch returned injected text; cited from search snippets only)

Off-limits (listed so they are not used by mistake)
- The leaked Trespasser source code (any copy, any mirror).
- Fabien Sanglard, "Jurassic Park: Trespasser CG Source Code Review", 10 Jun 2014 — <https://fabiensanglard.net/trespasser/> (a reading of the leaked code; not fetched or summarised).
- Source-level descriptions of Trespasser CE / ATX internals.

Modern locomotion references
- David Rosen, "Animation Bootcamp: An Indie Approach to Procedural Animation", GDC 2014 — <https://www.gdcvault.com/play/1020583/Animation-Bootcamp-An-Indie-Approach>
- Unity blog, "Exploring procedural design in Rain World: The Watcher", 2025 — <https://unity.com/blog/exploring-procedural-design-rain-world>
- Alan Zucconi, "An Introduction to Procedural Animations", 17 Apr 2017 — <https://www.alanzucconi.com/2017/04/17/procedural-animations/>
- NaturalMotion / Euphoria (Wikipedia) — <https://en.wikipedia.org/wiki/NaturalMotion>; Rockstar–NaturalMotion press release, 27 Feb 2007 — <https://www.gta4.net/news/3828/euphoria-engines-possibilities-for-gta-iv/>
- Unity forum, "[WIP] How we made our active ragdolls somewhat convincing" — <https://discussions.unity.com/t/wip-how-we-made-our-active-ragdolls-somewhat-convincing/848337>
- Wikipedia, "Ragdoll physics" (active ragdoll definition) — <https://en.wikipedia.org/wiki/Ragdoll_physics>

Related internal reports: `games/reports/Game enemy AI architectures.md`, `games/reports/Dynamic body kinematics and adaptive animation.md`, `games/advent_rising_mods/AI-MINDS-DESIGN.md`, `games/advent_rising_mods/AdventMod/FEET.md`.
