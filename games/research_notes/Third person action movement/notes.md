# Third-person action movement: Max Payne 3 + Stranglehold

Researched 2026-10-08 for AdventMod (UE2). Confidence notes: no GDC talk specific to either game's player animation turned up; sources are press interviews, Rockstar material, and reviews. Items marked (obs) come from reviews or play observation, not from the developers.

## 1. Max Payne 3 (Rockstar, 2012, RAGE + Euphoria)

**Locomotion / Euphoria on the player**
- Euphoria runs *on top of* RAGE's animation + physics and "controls the physical characters" (Torsten Reil, NaturalMotion). Keyframed clips plus real-time physics: Rob Nelson (art director) gave the dodge as the example. The player steers the direction, and the body still reacts to the world (vaulting cover, slamming into a wall or bus). https://www.techradar.com/news/gaming/the-technology-of-max-payne-3-1082751 , https://www.gamepro.de/artikel/max-payne-3-neue-infos-zu-gameplay-und-technik,2562362.html
- Nelson describes Euphoria as "a set of behaviours that you can tune". Most of the effort went into Max, and new behaviours were built for this game, including Shootdodge. https://primagames.com/news/rockstar-adds-cover-zoom-aiming-to-max-payne-3-142
- Shootdodge: Max reaches toward the floor while diving and reacts to obstacles in his path. He can stay prone after landing and aim 360 degrees, and the torso twists to any aim direction mid-dive. A dive into a wall makes him crumple (obs). Some moves have separate bullet-time and real-time animations. https://www.pcworld.com/article/464763/max_payne_3_pc_developer_interview.html , https://www.critic.co.nz/culture/article/1936/max-payne-3
- Free aim while moving: people describe the swing-around to shoot behind you as "startling" (obs). Weight comes from blended starts, stops, and pivots rather than instant velocity changes. https://expertreviews.com/?p=51916
- Rockstar's "Design and Technology" video series covers targeting, movement/animation, bullet time and AI. https://gameinformer.com/games/max_payne_3/b/xbox360/archive/2011/11/17/see-what-makes-max-payne-tick-in-new-video-series.aspx , https://www.gamingnexus.com/News/26211/The-evolution-of-bullet-time-in-Max-Payne-3
- **Last Man Standing**: lethal damage with a painkiller in stock forces bullet time (even with an empty meter). The screen desaturates except for the shooter, and if you kill him you survive, at the cost of one painkiller. If you miss, Max dies. https://www.trueachievements.com/max-payne-3-walkthrough.htm?page=2 , https://gamesradar.com/max-payne-3-review/2
- The last kill in a fight gets a kill cam that varies by weapon and situation. (Same Newswire coverage.)

**Gun carry**
- The loadout is 2 one-handed + 1 two-handed weapon ("Max is not Mary Poppins"). Every carried weapon is visible on the body, with no inventory menu. https://www.thesixthaxis.com/2012/02/13/rockstar-answer-some-questions/ , https://giantbomb.com/articles/the-slow-motion-ballet-of-death-in-max-payne-3/1100-3721/
- With a pistol out, Max dangles the long gun in his off hand. He tucks it under his arm to reload the pistol, then grips it again. Dual-wielding drops the long gun (obs, Edge). https://en.wikipedia.org/wiki/Max_Payne_3 , https://imfdb.org/wiki/Max_Payne_3
- Aiming: the left trigger gives an over-the-shoulder aim that trades speed for precision. Cover is an add-on to run-and-gun (Nelson), refined from RDR/L.A. Noire. Blind fire shows a visible recoil on each shot (obs). Rockstar never said how it does aim layering or hand IK. The likely setup is an upper-body aim-offset layered over locomotion. https://www.gamespot.com/articles/max-payne-3-first-impressions/1100-6338560/

**Why it feels weighty:** the body never teleports between states. Collisions are real (diving into walls hurts), the guns are physically present, and slow-mo is paired with the camera and audio.

## 2. Stranglehold (Midway Chicago + Tiger Hill, 2007, UE3)

- **Interactivity trigger** (Brian Eddy, producer): usable objects are **highlighted**. Pressing interact on a highlighted object always performs that stunt, and with nothing highlighted the same button dives. Chandelier: leap on, swing while aiming and firing, drop onto an enemy's head, or use the swing to reach the 2nd floor. Also runs along rails and dives onto roll carts. Woo directed animation and asked for moves to be more dramatic. https://www.shacknews.com/article/45555/john-woo-presents-stranglehold-interview
- Previews mention running up railings, swinging on chandeliers, and leaping onto moving objects "without interrupting" gun battles. https://worthplaying.com/article/2007/8/31/news/44738-stranglehold-all-goes-gold/ . Interactions also give bonus attack and defence (obs). https://outnow.ch/en/Games/2007/JohnWoosStranglehold/Review/
- **Tequila Time**: **automatic** when you dive or interact while an enemy is targeted, and can also be triggered manually. A meter drains while it runs and regenerates over time. You aim at normal speed while enemies are slowed (Eddy).
- **Tequila Bombs** (style-star meter): Health Boost (cheapest), Precision Aim (slow-mo first-person zoomed shot), Barrage (unlimited ammo + near-invulnerability), Spin Attack (360-degree kill of nearby enemies, the most expensive). https://giantbomb.com/wiki/Games/John_Woo_Presents_Stranglehold
- **Massive D**: Havok physics on a modified UE3. Nearly everything breaks, enemies chew through cover, and bodies get blown into props. https://en.wikipedia.org/wiki/Stranglehold_(video_game)
- No postmortem or GDC talk was found (gap). The chaining logic is inferred: each stunt is a self-contained traversal anim on a spline or anchor, upper-body aim stays live on top, and the stunt exits into a dive, landing, or the next highlighted prop.

**Why it feels cinematic:** one button, guaranteed success, slow-mo for free, and stunts that score points. The environment is the choreographer.

## 3. Cheap vs expensive in UE2 (anims, script bone rotation, root motion, TimeDilation, traces)

**Cheap**
- Slow-mo on dive or interaction with an enemy in view (Stranglehold's rule): set `Level.TimeDilation` and scale the player's anim rate and speed back up so they act in near real time. Add a meter.
- Last Man Standing: hook lethal damage. If a painkiller is in stock, keep health at 1, slow time, desaturate the post pass, and give the player a short timer to kill `Instigator`.
- Highlighted interaction props: placed actors with a trace or radius check, plus an outline or glow. One button runs the stunt and falls back to a dive. Rails and banisters are a spline of nav points with a slide anim, while chandeliers use a pivot actor with pendulum math that moves the player.
- Upper-body aim during any stunt: rotate the spine and neck bones toward the aim (`SetBoneRotation`) over whatever full-body anim is playing. This covers 360-degree dive aiming.
- Visible carried weapons: attach the long gun to the off-hand or back bone, with no inventory menu, and cap the loadout at 2+1.
- Procedural recoil: a spine and clavicle bone kick plus a camera kick, decaying over ~0.15 s.
- Weapon-specific kill cam on the last enemy.

**Medium**
- Dive collision: trace along the dive path, and on a hit play a "slam" anim, cut speed, and add camera shake (a fake of Euphoria's wall reaction).
- Starts, stops, and pivot turns: short transition anims selected by velocity change. Root motion where UE2 supports it, otherwise scripted acceleration curves.
- Destructible props (Massive D lite): swap meshes plus Karma debris.

**Expensive**
- True Euphoria-style active ragdoll on the player (balance, reaching for the floor, stumble recovery). Needs powered Karma ragdolls; see advent-physics-plan.
- Hand IK so the off hand grips the long gun while reloading, and real two-bone IK in general (UE2 has none built in).
- A full chaining system with mid-air re-targeting between props.
