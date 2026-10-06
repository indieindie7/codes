# Terrain look: MotorStorm (Evolution Studios) and LEGO Star Wars (Traveller's Tales)

Research note for a modder building terrain in Unreal Engine 2. Scope: terrain shape, materials, lighting, art direction, and which ideas transfer. Everything under "Cited Findings" is from a fetched source; "Inferences" are mine, flagged as such. Research date: 2026-10-06.

Source-access caveat (important for the report writer): the two best primary sources for MotorStorm rendering tech, the Digital Foundry / Eurogamer "MotorStorm Apocalypse tech interview" (2011) and "The Making of MotorStorm Apocalypse", could not be fetched (eurogamer.net, gamesindustry.biz and web.archive.org are all blocked from this environment). Their existence is confirmed via N4G aggregator pages, but their content is NOT summarised here. No GDC Vault or Develop-conference talk by Evolution Studios on terrain deformation surfaced in any search. On the LEGO side, no developer talk about rendering, lighting or environment construction for the 2005-2011 games was found at all; TT Games' in-house engine is essentially undocumented in public developer-facing sources. The LEGO section is therefore thin on confirmed statements and heavy on clearly-labelled inference.

---

## MotorStorm Q1: Deformable terrain. How the mud/track deformation worked and what sources describe it

### Takeaway
Deformation is confirmed by Evolution and by contemporaneous coverage as real-time, persistent within a race, and physically meaningful (ruts affect handling), driven by the studio's own physics/Havok-on-SPU setup. No developer source found explains the actual representation (heightmap displacement vs. mesh vertex edit vs. texture-space), so that remains inference.

### Cited Findings
- Evolution's technical director Scott Kirkland describes MotorStorm as having "physically differentiated (and at times deformable) terrain" and lists the SPU workload as: Havok physics, object visibility determination, hierarchy concatenation, billboard object culling and vertex-buffer creation, particle and vertex-buffer updating, vehicle dynamics updating, vehicle suspension constraints, audio/video decoding. He also says "MotorStorm only uses between 15 and 20 percent of available SPU resource" and that "All of our lighting and transformation work is done in the RSX's pixel and vertex shaders." — [Beyond3D Q&A with Scott Kirkland (2007)](https://www.beyond3d.com/content/interviews/38/)
- Producer Simon Benson: Evolution "wanted to do dirt" — "Let's put mud everywhere and really emphasise the interplay of vehicles, the grunge atmosphere and the dirt of the track." The tech allowed "millions of mud pixels" to accumulate on vehicles on contact, contrasted with PS2-era "little puffs of dust that disappeared as soon as they arrived." — [Definition Magazine, "Making Of MotorStorm"](https://definitionmagazine.com/features/making-of-motorstorm/)
- Wikipedia (secondary, summarising reviews): "Tracks experience real-time deformation, which means each lap is different from the last; obstacles and other elements which are displaced from their original position will remain that way unless they are disturbed again"; "Larger vehicles can create sizeable holes or leave ruts that can easily disturb smaller, lighter vehicles." — [Wikipedia: MotorStorm (video game)](https://en.wikipedia.org/wiki/MotorStorm_(video_game))
- Player-facing review confirming the gameplay effect of ruts: "on each lap you'll find the deformation the mud has gone through can change how it influences your play... You may slip into a pit made by a large vehicle's wake or you can try to safely travel in a tire trench to avoid the sliding about." Mud also "splatters your screen a bit." — [The Game Hoard, MotorStorm (PS3) review](https://thegamehoard.com/2020/07/24/motorstorm-ps3/)
- A ResetEra thread exists on why track deformation is rare in arcade/rally racers, using MotorStorm as the reference example (useful as a pointer, no technical content fetched). — [ResetEra thread](https://www.resetera.com/threads/why-there-is-still-no-track-deformation-in-rally-arcade-games.34897/)
- Digital Foundry published a long-form tech interview with Evolution covering "their first impressions of PS3 hardware during the original MotorStorm period through to tech enhancements made to the sequels" plus 1080p and stereoscopic 3D support in Apocalypse. Content not fetched. — [N4G pointer to DF "Tech Focus: MotorStorm Apocalypse"](https://n4g.com/news/732397/digitalfoundry-tech-focus-motorstorm-apocalypse?info=true); [N4G pointer to DF "The Making of MotorStorm Apocalypse"](https://n4g.com/news/734259/the-making-of-motorstorm-apocalypse-digital-foundry?info=true)

### Inferences
- Because Kirkland lists "particle and vertex buffer updating" and "billboard... vertex buffer creation" as SPU jobs while lighting/transform stays on RSX, the most plausible implementation is CPU(SPU)-side modification of terrain vertex data in deformable zones (a localised height/offset field written by wheel contacts, then re-uploaded as vertex buffers), with the same data feeding the physics collision surface so ruts are driveable. This is inference; no source states it.
- Deformation was almost certainly confined to designated "mud" regions rather than the whole track (reviews only ever describe mud deforming; rock, sand and tarmac are described as fixed), which also fits the 15-20% SPU budget quoted.
- For a UE2 modder: the *readable* part of the effect is (a) ruts that persist and (b) mud mass on vehicles/screen. Both are achievable without true deformation: persistent projected decals (tyre tracks) on a mud material, plus a darker/wetter base texture where cars drive most, plus screen splatter. Persistent rut geometry is the hard part and is not needed for the look.

### Gaps
- No developer statement found on the deformation data structure (heightmap vs. mesh vs. texture-space), resolution, or how physics and visuals were kept in sync. The DF tech interview (blocked) is the most likely place this is answered.
- No GDC/Develop talk by Evolution on MotorStorm terrain was found; searches for "GDC", "SPU terrain" and "Develop" returned nothing relevant.
- Could not confirm whether Pacific Rift changed the deformation tech; its interviews (Kikizo, PSU, GamingNexus) are about gameplay and AI only.

---

## MotorStorm Q2: Materials and silhouettes. Wet vs dry mud, dust, specular, tyre tracks; how canyon-scale shapes were built

### Takeaway
Confirmed: Monument Valley was chosen for its mesa/butte silhouettes, the terrain was built as hand-modelled polygon meshes (not a heightmap) from reference footage, concept art, Google Earth elevation data and photographs, then "terraformed" for gameplay; vegetation was placed with ground-type consistency. Material specifics (wet-vs-dry shader behaviour, specular) were not found in developer sources.

### Cited Findings
- Location choice: Simon Benson wanted "an iconic location, somewhere you can't get to in real life"; Monument Valley, Arizona was picked for its "mesas and buttes" and cinematic heritage. Track designer Bickerstaff saw gameplay value in "contrasts of terrain, dried rivers beds and canyons ideal for varied gameplay." — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Construction method: the team "used HD footage, concept art, Google Earth elevation data, and photographs to rough out polygon meshes with basic textures." Benson: "Game play has to win over realism... we'll start off modelling a mesa correctly but if a corner is too tight for the speed we're travelling at we'll terraform it slightly." — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Ground/vegetation consistency: "If we select a piece of vegetation we'll ensure it's planted in the appropriate pebbly ground or surrounded by suitable plants" (Benson). — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Tooling: the team moved from 3ds Max to Maya and built "a whole new set of renderers, shaders and other tools from scratch"; Benson: "We wrote an engine and built the game at the same time with hardware that wasn't pinned down." — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Pacific Rift's terrain palette, per game director Nigel Kershaw: "'earth' tracks that are all jungle, rotting vegetation, mud, canyons and slimey stuff... 'water' tracks that feature a lot of beaches, rivers and waterfalls... 'air' tracks which tend to be really high up, sitting on the edges of cliffs or above the clouds... and then the fire tracks that have this lava theme." — [Kikizo Pacific Rift interview, p.3](http://games.kikizo.com/features/motorstorm-pacific-rift-interview-p3.asp)
- Pacific Rift adds water that "can cool down a vehicle's engine" and slows vehicles in deep water; tracks span "volcanic mountainsides, beaches, jungles, caves, and a run-down sugar factory." — [Wikipedia: MotorStorm: Pacific Rift](https://en.wikipedia.org/wiki/MotorStorm:_Pacific_Rift)
- Reviewer description of track composition: courses are built "around the natural buttes and mesas of the American Southwest" and are "a mix of the curated areas meant to encourage high speed racing and the unexpected obstacles the real world brings." — [The Game Hoard](https://thegamehoard.com/2020/07/24/motorstorm-ps3/)

### Inferences
- The big-silhouette lesson transfers directly to UE2: MotorStorm's canyon walls, mesas and buttes are *authored meshes* with real reference behind them, not noise-generated heightfield. UE2's TerrainInfo heightmap is fine for the driveable floor; the memorable skyline should be static meshes (or BSP) placed with a reference photo in hand, then exaggerated for readability.
- The "appropriate pebbly ground around each plant" rule is a cheap, high-impact material rule: tie each prop set to a specific ground layer so terrain layers read as *places* rather than blended noise.
- Mud readability (my inference from reviews + Benson's "mud everywhere"): the contrast that sells MotorStorm is dark wet churned mud against pale dry dust and warm rock. In UE2 terms: at least three deliberately different albedo values (dark wet, mid dry, pale dust) with hard-ish layer boundaries rather than smooth blends, and a specular-ish highlight on the wet layer (UE2 can fake this with an environment-mapped or cubemap "wet sheen" layer at low opacity).

### Gaps
- No developer source on wet/dry mud shading, specular on wet ground, or how tyre marks were rendered (decal vs. texture write). Not found in any fetched interview.
- No source on whether the driveable floor itself was a heightfield or a mesh (the Definition piece says "polygon meshes" for the landscape generally, which suggests mesh, but does not distinguish floor from walls).

---

## MotorStorm Q3: Lighting and atmosphere. Dust clouds, sun glare, colour grading

### Takeaway
Confirmed: the colour palette was captured from real sunrise/sunset aerial footage of Monument Valley shot in 10-bit RGB specifically for its "dark orange to burnt red" look, and ungraded frame grabs shipped in the game as reference. The dust/particle system ran on SPUs. Specific post-process choices (bloom, grading LUTs, lens effects) were not found in developer sources.

### Cited Findings
- Reference shoot: the team "shot around 10 hours of images at 30fps onto HDCAM SR at full 10-bit RGB" at sunrise and sunset to capture "the landscape's stunning dark orange to burnt red colouring"; DoP Mike Brennan: "Dynamic weather created beautiful and dramatic scenery, right out of the box." — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Evolution shipped ungraded HDCAM SR frame grabs in-game "just to prove that this was how the game was born." — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Low-res NTSC frames of the footage were used during early track design; full 1920x1080 clips pulled as needed for texture/reference. — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- Particles (which include dust and mud spray) are updated on SPU ("Particle and vertex buffer updating"), lighting on RSX. — [Beyond3D Kirkland Q&A](https://www.beyond3d.com/content/interviews/38/)
- Mud on the camera/screen is an explicit part of the look ("it splatters your screen"). — [The Game Hoard](https://thegamehoard.com/2020/07/24/motorstorm-ps3/)
- Pacific Rift's "choking volcanic clouds" and "searing lava pools" are listed as track hazards (atmosphere as gameplay). — [Wikipedia: Pacific Rift](https://en.wikipedia.org/wiki/MotorStorm:_Pacific_Rift)

### Inferences
- The transferable point is methodological, not technical: pick one real place and one time of day, gather reference at that time of day, and derive the terrain palette, sun angle and sky colour from it. MotorStorm's "look" is low-sun warm key light + long shadows + a narrow orange-to-red palette, which UE2's static lightmaps and a single DirectionalLight do well.
- Dust/mud particle volume is a large share of the perceived "terrain quality" in MotorStorm (every vehicle trails it, it catches the low sun). In UE2 this is emitter density + a sun-coloured, low-alpha dust sprite with a soft bottom, not a terrain-shader problem.
- The screen-splatter and sun-glare are camera-side cheats that make the ground read as physical; UE2 can do a HUD-layer splatter texture and a lens-flare on the sun corona.

### Gaps
- No developer statement on colour grading, bloom, or tone mapping pipeline for MotorStorm 1 or Pacific Rift. The DF tech interview (blocked) likely covers this for Apocalypse.
- No source on dust cloud rendering specifics (soft particles, lit particles, shadowing).

---

## LEGO Star Wars Q1: Art direction. How the clean stylised look is achieved; how terrain/ground planes were built; how texture noise was avoided

### Takeaway
Developer statements establish the *philosophy* (imagination over simulation; not a CAD/building sim; toy proportions deliberately kept) but no developer source was found describing environment construction, materials, DoF/bloom or how ground was built. Observationally the games mix LEGO-brick objects with non-LEGO, smooth, largely untextured ground and backdrop geometry; this is widely visible in the games but I found no developer quote confirming the method, so it is recorded as inference.

### Cited Findings
- Jonathan Smith (Giant Interactive / TT Games Publishing, 2005): "We are delivering imagination and not simulation." "It's not a 'CAD' experience... It's the imaginative exercise. It's exploration." — [Starwarz.com interview with Jonathan Smith, March 2005](https://starwarz.com/tbone/interview-with-jonathan-smith-giant-interactive-tt-games-lego-star-wars-original-posting-march-15-2005/)
- Smith on characters: "There was a big challenge in making the mini-figure into a videogame character. Animating them makes a videogame character, but it has to be done in a way that makes them a videogame and not a simulation." Chunky minifig proportions (Leia's "chunky legs") were kept on purpose. — [Starwarz.com interview](https://starwarz.com/tbone/interview-with-jonathan-smith-giant-interactive-tt-games-lego-star-wars-original-posting-march-15-2005/)
- Smith: "Lego Star Wars is about play, not about building" and "is not an attempt to simulate Lego itself." — [GameSpot Q&A (summary via search; full page returned 403)](https://www.gamespot.com/articles/qanda-lego-star-wars-producer-jonathan-smith/1100-6165669/)
- Tom Stone (ex-LEGO Interactive) on the brief for the first demo: construction/deconstruction as a core visual idea: "how would deconstruction be if you had a lightsaber slashing it through a pile of LEGO or something constructed of LEGO, what would that look like?"; the opening "chairs dance on their own" gag came from that demo. — [LEGO Bits N' Bricks S01E09 transcript (PDF)](https://www.lego.com/cdn/cs/set/assets/blt493e62cc4d8fbfa5/bits_n_bricks_s01e09_tt_games_feature_and_transcript.pdf)
- Credits: Jon Burton directed, James Cunliffe is credited as artist on the 2005 game; design/development was split between Giant Interactive's offices and Traveller's Tales (programming and rendering). — [Wikipedia: Lego Star Wars: The Video Game](https://en.wikipedia.org/wiki/Lego_Star_Wars:_The_Video_Game)
- TT Games concept artist Tim Hill's described job is to "provide mood and color palettes and sketch out lighting conditions" from level designs (indicates deliberate per-level palette/lighting planning). — [Creative Bloq, Traveller's Tales feature (summary via search; page body did not fetch)](https://www.creativebloq.com/3d/travellers-tales-4099123)
- Modern TT Games workflow note (post-2011, for context only): artists "use prefabricated parts to construct designs on a micro scale with a grid system" and TT has "over 4000 LEGO pieces in their virtual library." — [KeyShot: TT Games portfolio](https://www.keyshot.com/customers/tt-games/)
- Fan reverse-engineering community for TT's engine exists (ttmodding wiki, pages on normal maps etc.); content was paywalled/blocked (HTTP 402) so no facts extracted. — [ttmodding.fandom.com: Normal maps](https://ttmodding.fandom.com/wiki/Normal_maps)

### Inferences
- (Observation of the games, not sourced to a developer.) The 2005-2011 LEGO games sit interactive/LEGO objects on *non-LEGO* ground: smooth, low-frequency-textured or flat-coloured floors, rock and sand meshes, often with a single soft ambient/sky gradient and simple directional shading. The eye is drawn to the saturated plastic objects because the ground is deliberately quiet. This is the inverse of the UE2 default (busy tiled detail textures everywhere).
- The plastic read comes from shape and shading, not texture: flat albedo, a broad specular highlight, strong colour separation between parts, and bevelled/rounded edges that catch light. In UE2 terms: untextured or near-flat colour materials with a cubemap specular layer and good lightmap contrast will read as "plastic" far better than any detail map.
- Palette discipline (planned by a concept artist per level, per the Tim Hill job description) is the controllable part: pick 4-6 colours per level, assign ground a desaturated member of that set, give the hero objects the saturated members.
- Texture noise is avoided mostly by not having it: large untextured or lightly-gradiented surfaces, with detail carried by geometry (studs, bricks, bevels) and by baked shadow/AO contact.

### Gaps
- No developer interview, talk, postmortem or art book excerpt was found describing environment construction, ground materials, bloom/DoF or palette rules for the 2005-2011 LEGO games. Searches on Game Developer magazine postmortems, GDC, Creative Bloq, Brick Fanatics, GameSpot and MixNMojo returned either business/gameplay content or blocked pages.
- "Modelled environments rather than heightmaps" is almost certainly true from observation but is unconfirmed by any fetched source.

---

## LEGO Star Wars Q2: Engine facts, lighting (baked vs dynamic), developer talks

### Takeaway
TT Games' in-house engine for the 2005-2011 LEGO games is not described in any public developer-facing source I could reach; the only engine fact confirmed is that the 2022 Skywalker Saga moved to a new in-house engine ("NTT") and that the change was controversial. Baked vs dynamic lighting for the old games is unconfirmed.

### Cited Findings
- Skywalker Saga (2022) used a new engine called NTT; "many employees had been pushing to use Unreal Engine 5 instead," and NTT "turned out to be difficult to use." This implies the 2005-2011 games ran on a different, older in-house engine (the "old engine" referred to). — [Wikipedia: Lego Star Wars: The Skywalker Saga](https://en.wikipedia.org/wiki/Lego_Star_Wars:_The_Skywalker_Saga)
- Rendering/programming for the 2005 game was done at Traveller's Tales; design at Giant Interactive. — [Wikipedia: Lego Star Wars: The Video Game](https://en.wikipedia.org/wiki/Lego_Star_Wars:_The_Video_Game)
- Jon Burton founded Traveller's Tales in 1989, directed the LEGO games, and left TT in 2021 to found 10:10 Games. — [Wikipedia: Jon Burton](https://en.wikipedia.org/wiki/Jon_Burton)
- TT Games formed in 2005 from the merger of Traveller's Tales and Giant Interactive. — [Wikipedia: TT Games](https://en.wikipedia.org/wiki/TT_Games)

### Inferences
- Given PS2/GameCube/Xbox/PSP targets for the 2005-2007 games, lighting on the environments was almost certainly baked (vertex colour or lightmap) with a small number of dynamic lights for characters and effects; the Wii/360/PS3 Complete Saga and Clone Wars likely added per-pixel effects (bloom, DoF) on top. This is standard-practice inference, not sourced.
- Jon Burton's own YouTube channel ("GameHut") publishes technical breakdowns of his games; it may contain LEGO engine material. Not checked in this pass. — pointer only, no URL fetched.

### Gaps
- No GDC Vault, Develop or Gamasutra technical talk by TT Games on the 2005-2011 LEGO engine or lighting was found.
- Baked vs dynamic lighting, shadow technique, and post-process stack for each platform generation: unconfirmed.

---

## LEGO Star Wars Q3 / cross-game: What general principle a modder should take

### Takeaway
From the sourced material, the common thread is "decide the look first, then build only what serves it": MotorStorm chose one real place and one time of day and sculpted meshes toward it; LEGO chose imagination-over-simulation and planned palette/lighting per level. Both put shape and lighting ahead of texture detail. The texture-level recommendations below are inference.

### Cited Findings
- MotorStorm: hand-built polygon meshes from reference, "terraformed" for play; palette from real low-sun footage; ground-type consistency rule for props. — [Definition Magazine](https://definitionmagazine.com/features/making-of-motorstorm/)
- LEGO: "imagination and not simulation"; toy proportions kept deliberately. — [Starwarz.com interview](https://starwarz.com/tbone/interview-with-jonathan-smith-giant-interactive-tt-games-lego-star-wars-original-posting-march-15-2005/)
- LEGO: a concept artist supplies per-level "mood and color palettes" and "lighting conditions." — [Creative Bloq (via search summary)](https://www.creativebloq.com/3d/travellers-tales-4099123)

### Inferences (practical UE2 recommendations)
1. Big shapes are meshes, not noise. Author the skyline (mesas, cliffs, canyon walls) as static meshes from reference; use the UE2 heightmap only for the driveable/walkable floor. Exaggerate silhouettes for readability (MotorStorm's "terraform it slightly").
2. Fewer, cleaner terrain layers with hard-ish boundaries. Three or four layers whose albedo values are clearly separated (dark wet / mid dry / pale dust / rock), not eight similar ones blended smoothly. Tie each prop set to one layer.
3. Lighting over texture. One strong low-angle sun, warm key, cool sky fill, high lightmap contrast, long shadows; this is what both games lean on. UE2 static lighting handles this well if terrain is lit with the same sun as the meshes and lightmap resolution is raised on the floor.
4. Quiet ground, loud objects (LEGO lesson). If the terrain must be generated, make it the calmest thing on screen (low-frequency texture, low saturation) and spend detail on placed meshes and props with saturated colour.
5. Atmosphere is particles and camera, not terrain shader (MotorStorm lesson). Sun-lit dust emitters, lens flare on the sun, screen splatter/dirt as HUD texture, fog colour taken from the sky palette.
6. Fake wetness with a cubemap/specular layer at low opacity on the "wet" terrain layer and persistent track decals rather than real deformation.
7. Pick the reference first: one place, one hour of the day; derive palette, sun angle, fog from it. Ship nothing that was not checked against that reference (Evolution literally shipped the ungraded reference frames).

### Gaps
- All items 1-7 are inference drawn from the limited confirmed statements plus observation of the games; none is a quoted developer rule.
- The unfetched Digital Foundry Evolution interview and any Jon Burton/GameHut LEGO engine material are the two most promising sources to close the remaining technical gaps.
