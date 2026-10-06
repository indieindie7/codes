# Interactive water in shipped games: simulation and coupling (developer talks and articles)

Scope: how shipped games (and the engines/middleware they use) make water *react* to characters, vehicles, objects and explosions, and how level geometry is handled. Rendering of oceans is only mentioned where it is inseparable from the interaction method. Every claim below carries a source link; items I could not source are listed under Gaps. "Inference" items are my reading of the sources, not statements by the developers.

Research date: 2026-10-06. Many primary PDFs (SIGGRAPH slides, master thesis) were fetched and text-extracted locally; quotes are from the extracted text.

---

## Key question 1 — Local interaction simulations in shipped games (per title)

### Takeaway
Across the shipped titles that have talked publicly, almost all local interaction is a **2D height-field (shallow-water or wave-equation) simulation on the GPU, in a texture that covers only the area near the camera/player**, with characters and objects injected either as depth-buffer/"custom depth" captures projected onto the water plane or as analytic capsules/spheres. Nobody has published a full 3D fluid coupling in a AAA shipped game; the one studio that claimed "true fluid dynamics" (Hydrophobia / HydroEngine) deliberately never disclosed its method.

### Cited Findings

**Naughty Dog — Uncharted 3 (GDC 2012 "Water Technology of Uncharted") and Uncharted 4 (SIGGRAPH 2016 "Rendering Rapids in Uncharted 4")**
- The GDC 2012 talk by Carlos Gonzalez-Ochoa covers the Uncharted water system "including the rendering techniques such as mesh generation and the flow shader", a new ocean system for the Uncharted 3 cruise-ship sequence, the mesh LOD system and wave generation — [GDC Vault session page](https://gdcvault.com/play/1015309/Water-Technology-of)
- Attendee notes from the 2012 talk record that "Wave particles is uncharted 3 solution", the ocean is a "composition of displacement grids at different scales, fade out by distance", a grid encodes "flow, foam, amplitude multiplier", the target was "open ocean, 100+ meters waves" and "Waves drive boats and ships"; the LOD mesh is "Modify[ed] from irregular geometry clipmaps" — [blog.dsmu.me notes](https://blog.dsmu.me/2012/03/water-technology-of-uncharted.html)
- The original Wave Particles method (Yuksel, House, Keyser 2007) "offers a simple, fast, and unconditionally stable approach to wave simulation"; particles are converted to a height field on the GPU, floating objects receive wave forces and moving objects (boats with propeller/rudder) generate waves; quoted performance: one boat at 170 fps and 1,681 boats at 4.8 fps on a GeForce 7900 GTX — [Cem Yuksel: Wave Particles](https://www.cemyuksel.com/research/waveparticles/)
- The SIGGRAPH 2016 Advances course lists "Rendering Rapids in Uncharted 4" (Gonzalez-Ochoa) with slides as a 143 MB PPTX; the talk describes "how we advanced the techniques to simulate oceans and created a new integrated system to handle rivers", using offline fluid sims to inform the look and a geometry "composite from separate procedural components that are inexpensive to compute and animate" — [Advances in Real-Time Rendering, SIGGRAPH 2016](https://advances.realtimerendering.com/s2016/)
- Secondary summary: "Wave particles are scrolled in the direction of river flow to help render rapids in Uncharted 4", and wave particles "were initially introduced into the game industry by Naughty Dog for Uncharted 3 to simulate local high frequency waves of oceans" — [wave-harmonic/water-resources (GitHub)](https://github.com/wave-harmonic/water-resources)
- Related Naughty Dog publication: "From a calm puddle to a stormy ocean - Rendering water in Uncharted" (SIGGRAPH 2012 talk) — [ResearchGate listing](https://www.researchgate.net/publication/254463329_From_a_calm_puddle_to_a_stormy_ocean_-_Rendering_water_in_Uncharted)

**Naughty Dog — The Last of Us Part II**
- GDC 2021 "Creative and Experimental VFX in 'The Last of Us Part II'" (Wataru Ikeda) covers "Edge Ripples" on the water surface and a "curl wave" beach effect as technical-VFX-art techniques — [GDC Vault](https://gdcvault.com/play/1027072/Creative-and-Experimental-VFX-in)
- 80.lv summary: TLOU2 effects are "GPU driven", "utilizing world information for spawning", with "more detailed interactions between effects and the rest of the world" — [80.lv](https://80.lv/articles/how-naughty-dog-created-the-immersive-world-of-the-last-of-us-part-ii)

**Rare — Sea of Thieves (SIGGRAPH 2018 Talk "The Technical Art of Sea of Thieves")**
- Open ocean is Tessendorf FFT; for shallow water "such as water splashing on the deck of a ship, we use a GPU water surface simulation based on [Mei et al. 2007]" (the virtual-pipes hydraulic-erosion shallow-water model). For "waterfalls and streams we supplement this by projecting the depth buffer from the perspective of the camera onto the surface of a mesh, into the texture space of its shallow water simulation. This allows e.g. a character intersecting with a waterfall to occlude the falling stream of water, and a character standing in a running stream to have foam interacting with their feet where they intersect with the water surface." — [Ang et al., SIGGRAPH 2018 Talks PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- Foam "is also added around objects that intersect [the surface]" using a "buffer with feedback to simulate the foam dispersing" — same PDF.
- The ACM abstract confirms "real-time surface fluid simulations to model incidental water behaviour on the GPU" — [ACM DL](https://dl.acm.org/doi/10.1145/3214745.3214820)

**Guerrilla — Horizon Forbidden West (SIGGRAPH 2022 Advances "Rendering Water in Horizon Forbidden West", Hugh Malan)**
- Core approach is baking Houdini sims (breaking waves as vector-displacement texture sequences) and instancing them at runtime with a compute shader that maps vertices through quads into the deformation texture; foam/flow data is in vertex colour and textures — [Malan slides PDF](https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-Water-Malan.pdf)
- Malan explicitly scoped out coupling: "I've only been able to touch on a small part of the water tech — for example I haven't talked about audio or physics or interaction at all." He also lists surface foam for "entity interactions, flow around rocks, and the breaking waves" as future work — same PDF (closing slides).
- Press description of the shipped behaviour: Aloy "bobs up and down" and "her movements cast gentle ripples" — [GamesRadar](https://www.gamesradar.com/horizon-forbidden-west-dev-explains-why-its-water-looks-so-unbelievably-good/)

**Ubisoft — Assassin's Creed III / IV and Skull and Bones**
- AC III ocean (Ubisoft Singapore, Georges Torres; Andrew Ellem on "ocean rendering and water interaction") uses Tessendorf FFT, two precomputed tiling displacement sets camera-projected; "given the fraction of a cycle time we are allowed, we could render at 200 frames per second if there was only water in shot" — [fxguide](https://www.fxguide.com/fxfeatured/assassins-creed-iii-the-tech-behind-or-beneath-the-action/)
- Ship–water coupling: "the boat's floatation is effectively determined by a bunch of giant buoyant spheres"; multiple partitions by ship size, separate spheres each side so sideways waves roll the ship; sample points along hulls produce drag/pushing forces from velocity-vs-surface-normal; "depth rods/probes along gunwales" detect wave height to trigger bow spray; stern wakes are "level particles"; debris impacts fire splash effects via individual depth probes; coastal foam density is baked from terrain topology at 512x512 (8 m precision on a 4 km map) — same fxguide article.
- Skull and Bones (Marlo Flor): the water tech "initially developed for Assassin's Creed 3 and refined through Assassin's Creed Origins"; dedicated servers were chosen partly "to make sure that we replicate the ocean perfectly across every single player"; no simulation details given — [Game Developer Q&A](https://www.gamedeveloper.com/design/water-water-everywhere-a-q-a-with-ubisoft-s-i-skull-and-bones-i-team)
- GDC 2013 "Rendering Assassin's Creed III" covers the ocean rendering — [GDC Vault](https://gdcvault.com/play/1017710/Rendering-Assassin-s-Creed)

**Ubisoft — Far Cry 5 (GDC 2018 "Water Rendering in Far Cry 5", Branislav Grujic + Cristian Cutocheras/AMD)**
- The talk is about material structure buffers, tessellation, procedural normal generation, foam "crowns" on rocks/coasts generated by spline and flood-fill routines, flow mapping and FP16 optimisation; no interaction simulation is described in the summaries — [80.lv summary](https://80.lv/articles/the-gdc-talk-water-rendering-in-far-cry-5); [YouTube](https://www.youtube.com/watch?v=4oDtGnQNCx4)

**Santa Monica Studio — God of War (2018) and Ragnarök**
- Paolo Surricchio (Senior Staff Rendering Programmer): "we render the water waves and ripples in both God of War (2018) and God of War Ragnarök with a similar technique as the old snow system." The old snow system was screen-space parallax over a deformation height field; the Ragnarök snow upgrade moved to hardware-tessellated geometry displacement. Characters/objects write into the system via "carving shapes attached to anything in the world, and they will push the snow down depending on how the object intersects with the snow plane." — [80.lv interview](https://80.lv/articles/santa-monica-s-senior-programmer-on-how-god-of-war-ragnar-k-s-snow-system-was-made)

**EA DICE — Frostbite / Battlefield 4**
- Björn Ottosson's KTH master thesis "Real-time Interactive Water Waves" was "prototyped inside the Frostbite engine developed at EA DICE and runs at 3 ms per time step on a single core of a Intel Xeon processor". Method: linear wave theory solved approximately with a Laplacian-pyramid of sub-grids (each handling a wavelength band, so dispersion is approximated), dynamic LOD (world split into "equal sized squares (for example 6 x 6 m)" cells; cells near the observer get high-resolution pyramids, far cells lower or none), phenomenological boundary conditions and a high-frequency detail layer — [EA-hosted thesis PDF](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)
- Interaction: "handled by displacing the height field. When an object is pulled out of water the water height is decreased and when pushed down height is increased"; the object–surface intersection "is approximated by an ellipse" and band-pass filtered analytically so each sub-grid receives only its wavelengths — same PDF, §3.3.
- Boundaries: Tessendorf's zero-displacement rigid boundary "generates reflected waves ... completely unphysical", so instead "water displacement is modeled by diffusion where there is no water", which is "physically very inaccurate" but cheap and dampening; waves in low-res grids are allowed to move into high-res grids near borders — same PDF, §4.8.
- Physics coupling with Frostbite's rigid-body/buoyancy system: "The bottom height is determined by checking vertical rays for intersection with static geometry"; simulation runs client-side only because "a server side simulation would have had substantially reduced resolution"; "Client side objects can interact fully ... They both generate waves and respond to them. Server side objects ... use the resting water height" but still generate waves — same PDF, §5.4–5.6.
- Implementation: Euler integration with velocity/height in two ping-pong buffers, dt clamped (slower waves rather than instability), SIMD 4-wide vectors, job split into "a simulation step and a border copy step" sized for the PS3 SPU's 256 kB local store; height field copied to GPU one frame late — same PDF, §5.
- Measured on an 8-core Xeon x5550 + GTX 470: 8 connected pyramids at 128² = 6.5 ms, 64² = 2.1 ms, 32² = 0.9 ms, 16² = 0.5 ms (propagation + border copy); a 52-pyramid LOD configuration (4×64², 12×32², 36×16²) = 3.1 ms sim + 0.7 ms render — same PDF, Table 6.1/6.2.
- Marketing for Battlefield 4 said Frostbite 3 has "networked water simulation, so that all players will be able to see the same waves and the same time--even when a fighter jet plops into the ocean" — [Shacknews](https://www.shacknews.com/article/79886/frostbite-3s-seamless-reality-highlighted-in-new-video); fan wiki: "players now face a real water surface that will react to all entities such as players and vehicles" — [Battlefield wiki](https://battlefield.fandom.com/wiki/Frostbite)

**Crytek — Crysis (GDC 2008 "Crysis Next-Gen Effects", Tiago Sousa)**
- The talk's agenda includes "camera and objects interaction with water" alongside surface animation, shore/foam, caustics; the ocean animation was a statistical Tessendorf model "computed on CPU for a 64x64 grid, with results uploaded into an FP32 texture for vertex displacement on GPU"; shore blending uses surface-depth vs world-depth — [GDC Vault](https://www.gdcvault.com/play/247/CRYSIS-Next-Gen); [Slideshare copy](https://www.slideshare.net/slideshow/crysis-nextgen-effects-gdc-2008/25051981) (slide PDF download failed for me; the interaction slide contents are not confirmed here)

**Dark Energy Digital / Blade Interactive — Hydrophobia (HydroEngine)**
- Announced 11 April 2007 for Xbox 360/PS3. Huw Lloyd (R&D Director, PhD astrophysics): "Water in games has so far been merely a flat plane with ripple effects and other graphical smoke and mirrors applied to it. The HydroEngine is different in one key respect - the water flows." "Our HydroEngine is the result of nearly 3 years intensive development work." — [Game Developer / Gamasutra](https://www.gamedeveloper.com/game-platforms/product-blade-announces-next-gen-fluid-dynamics-hydroengine)
- Rob Hewson (2010): it is "a true physics simulation of water, so it never repeats and is entirely emergent"; the engine outputs "direction and velocity" at every fluid point, which drives "objects, characters and even particle systems" and triggers foam/spray; multiple liquids (burning oil carried by current, blood dispersing); "will work just fine on any current-gen hardware"; the team deliberately withheld details: they don't "want to give away our secrets to other developers" — [HookedGamers interview](https://www.hookedgamers.com/features/2010/09/28/rob_hewson_about_hydrophobia.html)
- Studio went bankrupt in 2012 — [Wikipedia: Dark Energy Digital](https://en.wikipedia.org/wiki/Dark_Energy_Digital)

**Valve — Half-Life 2 / Left 4 Dead 2 / Portal 2**
- Portal 2 water "is an extension of the shader developed for Left 4 Dead 2": a flow map (2D vector field) warps normal-map UVs; flow vectors are generated offline in Houdini from the level geometry (surface normals of props projected onto the water with falloff; clipped level geometry projected as a mask to slow flow and accumulate foam at edges); "Painting flow for a typical Portal 2 map takes about 30 seconds." Gels are surface-embedded sprites via a UV layout map — not a fluid simulation — [Grimes, GDC 2011 "Making and Using Non-Standard Textures" PDF](https://cdn.akamai.steamstatic.com/apps/valve/2011/gdc_2011_grimes_nonstandard_textures.pdf); flow technique originally in [Vlachos, SIGGRAPH 2010 water flow](http://www.valvesoftware.com/publications/2010/siggraph2010_vlachos_waterflow.pdf)

**Nolla Games — Noita (GDC 2019 "Exploring the Tech and Design of Noita", Petri Purho)**
- "a very simple falling sand simulation algorithm" with "liquids and gases implemented similarly"; rigid bodies via marching squares into Box2D; world in 64×64 pixel chunks each with a dirty rectangle; chunks distributed across threads — [GDC Vault](https://www.gdcvault.com/play/1025695/Exploring-the-Tech-and-Design); [notes](https://braindump.jethro.dev/posts/gdc_vault_exploring_the_tech_and_design_of_noita/)

**The Chinese Room — Still Wakes the Deep (UE5, 2024)**
- "2D shallow water simulation for the surface using Unreal's Niagara"; "pumps" (capsules that inject velocities) attached "to the arms, hands, and feet of the protagonist" produce real-time flow; Niagara GPU readback is used to "query the simulation and know the flow direction, strength, and surface height at specific locations" to apply buoyancy and flow forces to objects; wall and floor meshes are "tagged so they can be baked into a heightmap texture" used as flow boundaries so water can "bounce and reflect upon impact" (programmer Joe Wheater) — [80.lv](https://80.lv/articles/learn-how-still-wakes-the-deep-used-unreal-engine-5-to-create-water-mechanics); original [Unreal Engine spotlight](https://www.unrealengine.com/en-US/spotlights/making-waves-developing-realistic-water-mechanics-for-still-wakes-the-deep-in-ue5) (403 for my fetch)

**Nintendo — Zelda: Breath of the Wild**
- Only fan analysis exists: a water plane under the whole terrain rises to fill basins when raining and evaporates afterwards; opacity/foam from distance between surface and floor — [ResetEra technical analysis thread](https://www.resetera.com/threads/zelda-breath-of-the-wild-the-technical-analysis.8197/page-7). No Nintendo statement on ripple simulation found.

### Inferences
- The industry-standard pattern (Sea of Thieves, GoW, Still Wakes the Deep, Ottosson/Frostbite, UE hobby systems) is: a 2D height/velocity field in a texture or grid; obstacles from a baked or rendered depth/height mask; injection from projected depth or analytic shapes; rendering reads the result as displacement + normals. Full 3D methods (Hydrophobia claimed, Noita's 2D CA) are outliers.
- GoW's "similar technique as the snow system" strongly implies a camera/player-following deformation height-field texture written by capsules, with Kass–Miller style propagation added for water; this is my inference, Surricchio gave no water specifics.
- Naughty Dog's ocean interaction appears to be one-way (waves drive boats via sampling the analytic/particle height field); I found no statement that characters inject wave particles in U3/U4.

### Gaps
- No primary technical disclosure of *how* Hydrophobia's HydroEngine worked (grid vs particles, CPU vs GPU); developers withheld it on purpose.
- Red Dead Redemption 2, Ghost of Tsushima, Spider-Man 2, Zelda BotW/TotK: no developer talks on water interaction found; Sucker Punch's GDC 2021 talks cover wind/grass only ([GDC Vault](https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating)); Spider-Man 2 coverage is about ray-traced water and haptics only.
- God of War 2018: no dedicated water talk; only the Ragnarök snow interview's one-sentence cross-reference.
- Horizon FW interaction/physics: explicitly excluded by Malan; Guerrilla has not published it.
- Uncharted 2012 slide deck itself: the SlideShare/Scribd copies could not be text-extracted; interaction specifics (per-object wave injection, costs) are not confirmed beyond attendee notes.
- Crysis GDC 2008 interaction slides: PDF download failed; only the agenda item is confirmed.
- Half-Life 2 (2004) ripple behaviour: no Valve document on water interaction found; the SIGGRAPH 2006 Source shading course does not cover it in the summaries I saw.

---

## Key question 2 — Techniques: GPU vs CPU, grid sizes, update rates, geometry/obstacles, forces, splashes

### Takeaway
Published numbers are sparse but consistent: height-field sims of 128²–1024² texels covering tens of metres around the player, 60 Hz or sub-stepped, costing sub-millisecond to a few milliseconds; obstacles come from baked height/mask textures or a depth capture at the water plane; forces on bodies are computed by sampling the height (and sometimes flow) field at pontoon/probe points, not by integrating pressure over the mesh.

### Cited Findings

**Simulation domain and resolution**
- Ottosson/Frostbite: pyramid of sub-grids per 6×6 m cell, finest 64²–128² near the observer; cost table above (0.5–6.5 ms CPU for 8 pyramids) — [thesis PDF](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)
- Elliot Gray's UE "Unified Interactive Water System": interaction capture 256×256 stretched over the interaction distance (60 m in demos), ripple height and normal render targets 1024×1024; C++ version ~0.7 ms CPU per water body on high-end hardware (earlier Blueprint prototype ~7.5 ms CPU); GPU cost "primarily shader-dependent" — [80.lv](https://80.lv/articles/unified-interactive-water-system-for-ue)
- Víctor Montero's UE5 ripple system: "a compute shader that calculates a 2D wave equation that can be sampled into a surface shader" in a single render target, moving with the player; it can "capture animated meshes, physic meshes and even particles out of the box" — [80.lv](https://80.lv/articles/an-impressive-unreal-engine-5-powered-system-for-creating-water-ripples)
- Community sizing rule reported in search summaries: 512×512 render target over 81.92×81.92 m around the player, or 128/256 over a smaller region with faster fade — [UE forums thread](https://forums.unrealengine.com/t/water-plugin-ripple-simulation-on-three-waterbodycustom-pools-at-different-elevations/756344) (secondary; exact origin not verified)
- Crest (Unity): dynamic wave sim runs per LOD cascade, results "accumulated up the LOD chain"; default Simulation Frequency 60 updates/s (lower "may limit wave speed or lead to visible jitter"), Damping 0.05, Courant number 0.7, optional horizontal displacement with clamp, gravity multiplier — [Crest docs: Ocean Simulation](https://crest.readthedocs.io/en/4.10/user/ocean-simulation.html)

**GPU vs CPU**
- GPU texture-space: Sea of Thieves (Mei et al. virtual pipes on GPU) — [SIGGRAPH 2018 PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf); Still Wakes the Deep (Niagara GPU sim with GPU readback) — [80.lv](https://80.lv/articles/learn-how-still-wakes-the-deep-used-unreal-engine-5-to-create-water-mechanics); Crest and the UE hobby systems above.
- CPU SIMD: Ottosson/Frostbite prototype (4-wide SIMD, SPU-sized jobs, 3 ms/step on one Xeon core) — [thesis PDF](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf); Crysis ocean FFT on CPU 64×64 uploaded to FP32 texture — [Slideshare](https://www.slideshare.net/slideshow/crysis-nextgen-effects-gdc-2008/25051981)
- Original Wave Particles: particles on CPU, height-field splat on GPU — [Yuksel](https://www.cemyuksel.com/research/waveparticles/)

**Injecting characters/objects**
- Depth-buffer projection into the sim's texture space (Sea of Thieves) — [PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- Scene capture at water height rendering "only custom depth with a very short draw distance" so ripples take the real silhouette of the object, inspired by Colin Barré-Brisebois's GDC Batman snow talk; objects need no logic of their own — [80.lv Gray](https://80.lv/articles/unified-interactive-water-system-for-ue)
- Analytic shapes: capsules "pushing the snow/water down" (GoW) — [80.lv](https://80.lv/articles/santa-monica-s-senior-programmer-on-how-god-of-war-ragnar-k-s-snow-system-was-made); ellipse approximation with analytic band-pass filter (Ottosson) — [thesis](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf); capsule "pumps" injecting velocity (Still Wakes the Deep) — [80.lv](https://80.lv/articles/learn-how-still-wakes-the-deep-used-unreal-engine-5-to-create-water-mechanics); Crest "Add Bump", "Object Interaction" and "Sphere-Water Interaction" shaders (sphere version accounts for submersion, spheres can be compounded) — [Crest docs](https://crest.readthedocs.io/en/4.10/user/ocean-simulation.html)

**Level geometry / obstacles / stairs and slopes**
- Baked height-map texture of tagged wall/floor meshes used as flow boundaries (Still Wakes the Deep) — [80.lv](https://80.lv/articles/learn-how-still-wakes-the-deep-used-unreal-engine-5-to-create-water-mechanics)
- Bottom depth from vertical ray casts against static geometry; dry cells handled by diffusion rather than zero-displacement (Ottosson) — [thesis](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)
- Offline: Portal 2 clips and projects level geometry onto the water plane to mask flow and foam (not runtime) — [Grimes GDC 2011](https://cdn.akamai.steamstatic.com/apps/valve/2011/gdc_2011_grimes_nonstandard_textures.pdf); AC III bakes coastal foam density from terrain at 512² — [fxguide](https://www.fxguide.com/fxfeatured/assassins-creed-iii-the-tech-behind-or-beneath-the-action/)

**Forces on bodies**
- Buoyancy spheres + hull sample points for drag (AC III) — [fxguide](https://www.fxguide.com/fxfeatured/assassins-creed-iii-the-tech-behind-or-beneath-the-action/)
- UE Water Buoyancy Component: "uses spheres (pontoons) to create a simplistic volumetric approximation of the object", with a Buoyancy Coefficient, damping, drag coefficients, angular drag and max drag speed; mass must be enabled — [Epic docs](https://dev.epicgames.com/documentation/unreal-engine/water-buoyancy-component-in-unreal-engine)
- Sampling GPU sim height + flow via readback for buoyancy and flow forces (Still Wakes the Deep) — [80.lv](https://80.lv/articles/learn-how-still-wakes-the-deep-used-unreal-engine-5-to-create-water-mechanics)
- Frostbite prototype: client objects both generate and respond to waves; server-mirrored objects only generate waves and float at rest height — [thesis](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)

**Splashes and foam from the sim**
- Foam from wave peaks plus around intersecting objects with a feedback (dispersion) buffer (Sea of Thieves) — [PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- Depth probes along gunwales trigger bow spray; wake as level particles (AC III) — [fxguide](https://www.fxguide.com/fxfeatured/assassins-creed-iii-the-tech-behind-or-beneath-the-action/)
- Ottosson adds a phenomenological high-frequency detail layer: each cell carries wave energy E and direction d, "exposed in a pixel shader to generate the actual details" — [thesis](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)

### Inferences
- Reported shipped/prototype budgets cluster around 1–4 ms total for interaction water on 2010–2024 hardware; nobody reports more than ~6.5 ms, suggesting that is the practical ceiling studios accept.
- Depth-capture injection (Sea of Thieves, Gray) handles arbitrary shapes and animation for free but loses velocity information; velocity-injecting capsules (Still Wakes the Deep, Crest) give flow but need manual placement. Combining both appears in none of the sources.
- Stairs/slopes: the only explicit handling of varying bottom depth is Ottosson's ray-cast bottom height and the baked boundary height map in Still Wakes the Deep; nobody discusses moving platforms.

### Gaps
- No studio stated a per-platform cost like "N×N texture at 60 Hz costs X ms on PS4/PS5"; the only hard numbers are Ottosson's PC CPU table and Gray's ~0.7 ms CPU figure.
- Moving platforms, water on slopes/stairs with explicit shallow-water treatment: not covered in any shipped-game source found.
- Update rates: only Crest's 60 Hz default is explicit; shipped games did not state substep counts.

---

## Key question 3 — Open-source and middleware

### Takeaway
Crest (Unity) and Unreal's Water plugin / Niagara shallow-water sim are the most documented options; both are LOD/texture-space height-field sims with sphere/capsule injection and sphere-pontoon buoyancy. Third-party UE systems (Fluid Flux, FluidNinja) are popular but their internals are only partly documented.

### Cited Findings
- Crest: "multi-resolution dynamic wave simulation, which allows objects like boats to interact with the water"; enable via "Create Dynamic Wave Sim" on OceanRenderer with a Dynamic Wave Sim Settings asset; ObjectWaterInteraction script distributes force across LODs "to prevent over-application" — [Crest docs](https://crest.readthedocs.io/en/4.10/user/ocean-simulation.html); [80.lv overview](https://80.lv/articles/crest-ocean-system-for-unity-m11)
- Unreal Water system: supports "fluid simulation with gameplay, such as ripples caused by footsteps or the wake behind a boat"; buoyancy via pontoon component — [Epic docs](https://dev.epicgames.com/documentation/unreal-engine/water-system-in-unreal-engine); [Buoyancy docs](https://dev.epicgames.com/documentation/unreal-engine/water-buoyancy-component-in-unreal-engine)
- Niagara "2D Shallow Water Simulation" (heightfield ripple solver for ponds) and "3D FLIP" are the engine-level options; particle-based approaches are typically limited to ~50k–100k particles at 60 fps — [StraySpark UE5 water guide](https://www.strayspark.studio/blog/ocean-water-simulation-ue5-guide) (secondary blog)
- Fluid Flux (Imaginary Blend) is a shallow-water-based UE system — [80.lv](https://80.lv/articles/fluid-flux-a-cool-water-simulation-system-for-unreal-engine); [docs](https://imaginaryblend.com/2025/01/10/fluid-flux-documentation/); a community plugin integrates Oceanology with FluidNinjaLIVE for interaction — [GitHub](https://github.com/Sartaq12/WaterInteractionPlugin)
- Curated list of water talks (incl. Naughty Dog, wave particles) — [wave-harmonic/water-resources](https://github.com/wave-harmonic/water-resources)
- Open-source ripple implementation note: OpenMW adds ripples as "Compute with fragment fallback compatibility" — [OpenMW MR 2641](https://gitlab.com/OpenMW/openmw/-/merge_requests/2641)

### Inferences
- Crest's design (per-LOD height-field with Courant control and sphere inputs) is effectively an open reimplementation of what Ottosson described for Frostbite in 2011 and what Sea of Thieves shipped; it is the most concrete reference implementation available for study.

### Gaps
- NVIDIA WaveWorks interaction, PhysX Flex water demos, Godot shallow-water plugins and Unity "Dynamic Water Physics" were not researched in this pass (tool budget); no shipped-game citations for them were encountered.
