# Water reference: Decima and Crimson Desert

Research date 2026-10-18. Public detail is thin for both; gaps are marked.

## Decima
- Primary source: Hugh Malan, "Rendering Water in Horizon Forbidden West" (SIGGRAPH 2022 Advances). It covers breaking waves only; the talk says waterfalls and underwater effects are not covered.
- Hybrid approach: no realtime wave sim. Offline Houdini sims are baked, instanced at runtime, played back and blended to fit the coastline.
- Breaking wave = one baked, animated cross-section. Each sim frame's cross-section is stored as a row of a 2D texture; XYZ offset from a flat surface is stored as RGB. The row is chosen by an animation parameter V (about 0.27 starts to rise, 0.4 steepens, 0.5 curls over and turns to foam).
- Runtime: artists draw wavefront curves in the editor; the animation is baked and streamed with the world tile data. Quads along the wavefront feed a compute shader that writes the water vertex buffer, applying the deformation along the front. The surface can stretch 2-3x or more, so tessellation is raised near wavefronts.
- Extra baked maps: partial derivatives of the displacement (for tangent/binormal normal mapping) and a UV-compensation map. Foam spawn info, relative height and deformation strength go through vertex colour.
- Foam is placed just after the breaking point of the animation curve. Malan lists foam popping (vertex-colour foam cannot be finer than a triangle) and surface foam quality as weak spots; he cites Weta's wet-foam paper as a future direction.
- Rivers/lakes: standing waves around rocks, eddies, whirlpools came from Houdini sims stored as a 3D volume (animated 2D region). River deformations stayed flat because triangle density was too low.
- Not found in any source: wave spectrum/FFT use, flow-map details, caustics, character wetness, interaction ripples, swim physics. Community talk of flow-map UV scroll plus flow-masked foam is unofficial.
- The Horizon Zero Dawn river tool (Houdini, curves snapped to terrain) and "World Data Maps" (queryable values such as distance to nearest river) were mentioned in 80.lv coverage (snippet only, not fetched).

## Crimson Desert
- Engine: BlackSpace, an expanded version of the Black Desert Online engine (2015).
- Pearl Abyss GDC 2025 press material names two water systems: FFT Ocean Simulation and Shallow Water Simulation, producing waves, flow and ripples. Also listed: a volumetric masking wetting system (name only, no detail found).
- Digital Foundry coverage (secondhand) mentions ray tracing plus screen-space reflections and volumetric water. Not verified.
- No details found on grid resolution, ocean/shallow-water coupling, foam, or character wetness. Anything beyond the above would be "seen in trailer" only; I did not watch trailers.
- Black Desert precursor: nothing found.

## Techniques worth copying in a D3D9 mod
- Baked animation indexed by a parameter: store a wave/ripple profile as a texture row per time step, sample by V in a shader. Cheap on SM3 (vertex texture fetch) and needs no runtime sim.
- Foam seeded by a local "breaking" signal: derive foam from solver height/velocity/divergence, write it to a vertex or texture channel, and place it just behind the crest. Avoid per-vertex-only foam on coarse meshes (Guerrilla saw popping); use a world-space foam texture masked per pixel.
- Raise mesh density only where the effect is (near fronts, near the player) instead of globally.
- Bake derivatives with the displacement so normals stay correct after displacement (or compute normals from the solver heightfield in the pixel shader).
- Shallow-water solver for interaction ripples, as Crimson Desert reportedly does (shallow water plus FFT ocean). That matches the existing HydroWater solver; keep the solver for local flow/ripples and layer a cheap texture-based wave on top.
- Player wetness: a masked wet-surface term (darker albedo, higher gloss) driven by time since water contact, decaying over seconds. Crimson's "volumetric masking wetting" suggests a mask of this kind; mechanism inferred, not documented.

## TrueBeam "Physical Water" for BeamNG.drive (video 2026-10-20)
Spealer, "BeamNG's NEW Water Physics is INSANE!" (youtu.be/HlJWs8ziz-o, 15 min, recorded before 0.40, mod alpha v0.39.4). The user: "check and also lets check if we can check the sourcecode of this mod".
- What it is: a shallow-water solver over the whole ocean and the rivers, replacing the stock water ("Physical runs the simulated ocean and rivers. Stock is the game's own water"). The settings panel gives the grid: "Surf grid size: low 50 cm, medium 40 cm, high 32 cm, ultra 25 cm", so about the cell size HydroWater uses (dx 20 units). Sea state: Wind (4 calm, 9 choppy, 15+ storm), Swell height, Swell follows the wind, Swell from (compass), Lee shelter ("how much the land calms the water downwind of it"). In the water: "Rocks, walls and dams: the water runs around them, piles up and pours over"; "Vehicles: water flows around the wheels and body, leaves a wake and throws spray"; a foam-from-current slider for rivers.
- Seen: waves rolling onto the beach and draining back, boat wakes with foam, splash rings from a drop, a flood level that tears through terrain, ripples on everything. Weak: vehicle-water contact glitches, the sim area does not follow a fast boat (bounded sim window around the player), horizontal flow only (a commenter notes vertical impact velocity is ignored at 2:10).
- Source: NOT released as of 2026-10-20 (description "Mod - N/A at the moment"; the author's Patreon page lists only Volumetric Particles, locked). The author said in a TikTok (@craigsimmon) that an alpha goes out free in their Discord (discord.gg/k3yKgtkbPq) before a free beta; the pinned comment says "coming out for FREE in Beta soon". BeamNG mods are zips of Lua + HLSL/GLSL shader files, so when it ships the solver and shader code will be readable unless the author ships compiled Lua. Re-check later; nothing to read yet.
- For us (HydroWater): already have the solver and foam; worth copying are (1) wind + swell as a cheap global wave layer over the solver (idea for the pool/ocean sheets: a sine/Gerstner swell added in the vertex shader, with "lee shelter" = damp it where a wall is upwind), (2) a "foam from current" term (foam_gain from |v| of the flow, which we have as hw_foam_stir), (3) the wheel/body wake = our idea 19 debris wakes, (4) user-facing quality presets by grid size.

## Sources
- https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-Water-Malan.pdf (fetched, text read)
- https://www.mynewsdesk.com/uk/swipe-right/pressreleases/pearl-abyss-showcases-blackspace-engine-at-gdc-2025-3376979 (fetched)
- https://thegameswiki.com/crimson-desert/wiki/blackspace-engine (fetch failed, search snippet only)
- https://80.lv/articles/horizon-zero-dawn-procedural-rivers-wires/ (search snippet only)
- https://gamingbolt.com/?p=639414 (search snippet only)
