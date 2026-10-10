# Impostor and billboard techniques for floating detritus on simulated water (D3D9 / SM3 target)

Scope of these notes: how shipped games and papers render many small floating things (leaves, paper, splinters, foam clumps, oil film) without rigid-body geometry, and how such things are advected from a 2D height-field / shallow-water velocity field. Target: 2011-era D3D9 Shader Model 3 renderer, CPU shallow-water sim with 20-unit cells; detail must be sub-cell.

Verification legend used throughout: **[V]** = read directly from the primary source (paper/slides/docs text); **[S]** = taken from a search-engine summary of a primary source I could not open (fetch blocked); **[I]** = my inference.

Local copies of extracted primary texts (for the report writer, not citable as URLs): scratchpad `webfetch-...fejqwl.pdf.txt` (Chentanez & Müller 2010), `...izs7xk.pdf.txt` (Vlachos 2010 slides), `...gmrzns.pdf.txt` (Sea of Thieves SIGGRAPH 2018 talk), `...q7ichc.pdf.txt` (Ottosson 2011 thesis), `cords2009.pdf.txt` (Cords 2009 dissertation, German), `vandongen.txt` (Interior Mapping 2008).

---

## Key question 1: Which shipped games / papers render floating debris, foam and detritus as impostors, billboards, particles or textures, and how?

### Takeaway
No shipped-game source I found renders floating *debris* as true 3D impostors; the production pattern is (a) a 2D scalar "foam/debris map" advected or diffused on the simulation grid and blended with artist textures, (b) a flow-map-distorted colour texture for debris in murky water (Valve), and (c) camera-independent sprite particles (disks/ellipses) for foam/spray in research systems. Large physical debris (ship fragments) is real geometry with a single buoyancy probe (AC3).

### Cited Findings

**Valve, Portal 2 / Left 4 Dead 2 (SIGGRAPH 2010, Vlachos) — flowed colour map for debris** [V]
- Goals/constraints slide: "Min hardware ps2.0b (6-year-old hardware) & Xbox 360"; "Our water shader had limited instructions left for our low end hardware ps2.0b". — [Vlachos, Water Flow in Portal 2, SIGGRAPH 2010 slides](https://www.advances.realtimerendering.com/s2010/Vlachos-Waterflow(SIGGRAPH%202010%20Advanced%20RealTime%20Rendering%20Course).pdf)
- "Pixel shader flow, not geometric flow"; "Artists author a flow map (a texture containing 2D flow vectors)"; "Relatively low resolution: ~4 texels/meter"; generated in Houdini because it is "Impractical to paint directly". — same source
- Max & Becker observation adopted: "The beginning of the distortion looks convincing. Only distort a small amount. In general, distortion looks reasonable for the first 1/3 of uv space"; "Blend the short animated segment in two layers. Each layer is offset half a phase so we can hide the restart for each layer." — same source
- Two problems and fixes: "Repetition – The same normals will flow through the same point on the mesh" (solved by offsetting each phase), "Pulsing – The surface appears to pulse in a repeating pattern" (solved by a noise texture). — same source
- Debris: "Wanted to also flow debris in dirty water. Needed to modify our algorithm to support flowing a color map." "Flowing normals would repeat an interval from zero to some fraction with the peak (center) of the interval at half distortion." "Flowing colors works better by offsetting the interval from –fraction to +fraction so the peak of the interval is at zero (the at-rest position)." Summary: "Flowing debris uses an offset distortion range that favors less distortion than the normal flow." — same source
- Cost: "Compared to scrolling two normal maps: Additional texture fetches: 2 - flow & noise; Additional arithmetic pixel shader instructions: 21". — same source
- Future work slide (not shipped): "Use flow map with our physics simulation to have objects flow on the water surface using the same data". — same source

**Rare, Sea of Thieves (SIGGRAPH 2018 Talks) — foam feedback buffer** [V]
- "Foam is generated at wave peaks using the method described in the reference paper [Tessendorf 2001]. It is also added around objects that intersect the water surface within a camera centered window using depth buffer comparisons. We progressively blur the result of the foam buffer with feedback to simulate the foam dispersing and to give us a softer mask, more in keeping with the style of the game. The resulting mask is blended with artist-authored textures to give a more stylized appearance to the foam." — [Ang et al., The Technical Art of Sea of Thieves, SIGGRAPH 2018 Talks PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- "Foam generation, dispersion and blending with the artist-authored textures is modified based on whether the water is calm, normal or stormy... calm water will only show foam generation around intersecting objects." — same source
- Shallow water: "we use a GPU water surface simulation based on [Mei et al. 2007]... we supplement this by projecting the depth buffer from the perspective of the camera onto the surface of a mesh, into the texture space of its shallow water simulation... a character standing in a running stream to have foam interacting with their feet". — same source
- The 2-page talk gives no buffer resolution/format numbers.

**Ubisoft, Assassin's Creed III (fxguide write-up of the ocean tech)** [V from fxguide; GDC Vault slides are members-only]
- Foam: wave-edge foam is precomputed per frame with real-time dispersal rate; coastal foam built offline by sampling terrain height "roughly 512×512 for a 4 km × 4 km map, or about 8 m precision", spread with Gaussian blurs and Perlin noise; "Three grayscale foam maps (coarse, sparse, medium) sit in the R, G, and B channels, and a color ramp blends them." — [fxguide, Assassin's Creed III: The tech behind (or beneath) the action](https://www.fxguide.com/?p=38193)
- Debris: "Debris uses a single probe and fires a splash effect when it hits the water." Stern wake "is particle-based, tuned with sustain, decay, and density"; Torres: the wake "needs to be cheap". — same source
- The red targeting band on the water "is drawn by projecting particles from the camera so they intersect the waves" (a camera-projected particle decal on the wave surface). — same source
- Budget: "we could render at 200 frames per second if there was only water in shot"; two shader LODs, "LOD 0 transparent" with refraction near shore and an opaque LOD 1 without refraction in deep water, blended over roughly 400 m. — same source

**Naughty Dog, Uncharted 3 (GDC 2012, Gonzalez-Ochoa & Holder)** [V via Slideshare text]
- Flow shader: "Scroll uvs (per pixel/vertex) of normal map by a vector field"; two flow textures blended, one offset half a cycle, to hide the loop reset; authored in Maya with splines for direction and colour maps for magnitude. — [Water Technology of Uncharted, GDC 2012 slides](https://www.slideshare.net/slideshow/water-technologyofunchartedgdc2012/12977478)
- Foam data lives in the flow grid: "A flow grid encodes flow vectors, wave amplitude multipliers, and foam data"; "The foam modulation is outputed as a vertex color when we generate the final mesh"; river foam from "a threshold operation on a gradient field"; churn: "Use foam texture to modulate water depth, blend again" for a pseudo-volumetric look. — same source
- Not covered in the slides: floating debris objects, surface particles, sorting, ms budgets.

**Naughty Dog, Uncharted 4 "Rendering Rapids" (SIGGRAPH 2016 Advances course)** [S]
- Course page lists the talk; only a 143 MB PPTX is offered (no PDF). Abstract: river rapids "use offline fluid simulations for the river's overall look and surface and flow data"; motion split into geometric and visual parts. — [Advances in Real-Time Rendering 2016 course page](https://www.advances.realtimerendering.com/s2016/index.html)
- A third-party reimplementation says U4 replaced noise/blend anti-repetition with a "Wave Profile Buffer". — [ACskyline GitHub reimplementation](https://github.com/acskyline/wave-particles-with-interactive-vortices) (secondary; not confirmed against the slides)

**The Chinese Room / Sumo, Still Wakes the Deep (Unreal blog)** [S — unrealengine.com returned HTTP 403 on every fetch]
- "we developed a two-dimensional shallow water simulation using Unreal's Niagara VFX system"; "The 2D simulation only simulates the surface of the water"; "We used Niagara for the simulation itself and also for many of the particle systems—from burst pipes to debris in water"; "Our water system reads back simulation data from Niagara using a Niagara data interface". — [Unreal Engine blog: Making waves](https://www.unrealengine.com/en-US/blog/making-waves-developing-realistic-water-mechanics-for-still-wakes-the-deep-in-ue5)
- Collision meshes are tagged and baked "into a heightmap texture" used as a flow boundary; shading starts from UE's Single Layer Water model with texture effects layered over the sim data. — same source (search summary)

**Chentanez & Müller 2010 (research, NVIDIA) — foam particles as surface-aligned disks** [V]
- "Foam particles represent foam that floats on the surface of the water. Spray, splash and foam particles are generated within our simulation framework from breaking waves, waterfalls and interaction of solids with the fluid." — [Chentanez & Müller, Real-time Simulation of Large Bodies of Water with Small Scale Details, SCA 2010](https://matthias-research.github.io/pages/publications/hfFluid.pdf)
- "When a splash particle hits the surface we create a foam particle with some probability, depending on the impact speed of the droplet." — same
- "Foam is advected by the velocity field of the fluid simulation and projected onto the fluid surface. Its lifetime is a user-defined parameter modulated with some noise. It nicely conveys the horizontal swirling water motion". — same
- Rendering: "Foam particles are rendered as diffuse disks with normals perpendicular to the height field water surface." Spray: "rendered as an elongated ellipse along the direction of their velocity to emulate the motion blur effect". Splash: screen-space fluid rendering [VdLGS09] with a world-space bilateral filter. — same
- Counts (Table 1, average foam+spray+splash particles active per frame): Boat 900x135 grid, 250K particles; Waterfall 128x128, 56K; PML 128x128, 2K; Beach 128x128, 220K; Ocean 256x256, 83K. GPU (CUDA, GTX 480): Beach total 9.88 ms/frame incl. rendering, Ocean 13.13 ms, Boat 18.05 ms; CPU 4-thread boat 69.75 ms. — same

**Cords 2009 (Rostock dissertation, German) — foam map as cellular automaton** [V]
- Foam properties modelled: amount depends on motor speed; density decreases with time; "Schaum verweilt an seiner Position und breitet sich sehr langsam aus" (foam stays in place and spreads very slowly). "Diese Eigenschaften werden mit einem zellulären Automaten repräsentiert." — [Cords, Dissertation 2009, Univ. Rostock (PDF)](https://rosdok.uni-rostock.de/file/rosdok_disshab_0000000334/rosdok_derivate_0000004116/Dissertation_Cords_2009.pdf), section 5.2.2.1
- "Innerhalb des Schaumgeneratorbereiches wird neuer Schaum der Intensität f mit f∈[0,1] in Abhängigkeit der Motorengeschwindigkeit in einer foam map generiert. Diese beinhaltet die aktuelle Schaumintensität für jedes Gitterelement. Anhand der Intensitätswerte wird später pro Gitterzelle eine Schaumtextur eingeblendet." Spread by slow diffusion with filter f_new(i,j) = d·f(i,j) + (1−d)/4·(f(i+1,j)+f(i,j+1)+f(i−1,j)+f(i,j−1)), eq. 5.12, where d∈[0,1] sets fade and spread speed. The generator can be placed anywhere, "zum Beispiel wenn ein Objekt ins Wasser fällt". Different foam textures + differently parameterised generators give different foam kinds in one scene. — same
- Spray ("Gischt") for breaking waves is particle-based; figure caption: "200 Schichten mit jeweils 700 Partikeln, 53,1 FPS" (200 layers of 700 particles each at 53.1 fps). — same, section 5.2.2.2
- Note: I could not open the 2009 NPH paper "Real-Time Open Water Environments with Interacting Objects" (diglib 403); its abstract mentions moving-grid wave equation, boat coupling and "most parts of our method can be implemented efficiently on GPUs" but not foam. — [Cords & Staadt 2009 abstract page](https://vca.informatik.uni-rostock.de/~ostaadt/publication/cords-real-time-open-water-2009/)

**Ottosson 2011 (KTH / EA DICE Frostbite thesis)** [V]
- Abstract: multi-resolution Laplacian-pyramid height-field solver; "runs at 3 ms per time step on a single core of a Intel Xeon processor". Related-work note: "Height field simulation lack foam and splashes... [JG01] add foam from particles and steep waves and render it by blending in a foam texture. They also generate particles from the height field simulation to simulate splashes. [Vla10] use flow to animate a texture with good result." — [Ottosson, Real-time Interactive Water Waves (EA-hosted PDF)](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)
- Rendering section is explicitly "only a short overview... not the focus of this thesis": height field rendered from a vertex buffer at lower resolution than the simulation plus a height texture for normals. Client-only simulation; server objects use resting water height. — same

**Bagar, Scherzer, Wimmer 2010 (EGSR) — volumetric foam via layers** [S]
- "Foam formation is simulated through Weber number thresholding"; fluid partitioned into "a foam layer and two water layers, one in front and one behind the foam"; 64k particles, 1280x720, Q9450 + GTX 280; "even foam does not significantly increase running time". — [TU Wien project page](https://www.cg.tuwien.ac.at/research/publications/2010/bagar2010/); poster/thesis at same site. (PDF exceeded fetch size limit; details from the abstract/poster summaries.)

### Inferences
- [I] Across AC3, Sea of Thieves, Uncharted 3 and Cords, foam/detritus is a per-cell *scalar* (R, G, B channels for several foam types in AC3; vertex colour in U3; a blurred feedback buffer in SoT; a diffused cellular-automaton map in Cords) multiplied against a tiling artist texture. That is exactly what a 20-unit-cell CPU sim can emit cheaply, with the sub-cell detail coming from the tiled texture, not the sim.
- [I] Valve's debris flow is the only shipped example found of advecting a *colour* (not just normal) texture with flow; its "offset the interval so the peak is the at-rest position" rule is the key detail for detritus: colour content is far less tolerant of stretch than normals, so keep the distortion range centred on zero.
- [I] Chentanez's "diffuse disks with normals perpendicular to the height field" is a surface-aligned (not camera-facing) sprite; it is the right default for flat detritus (leaves, paper, oil clumps), while spray uses velocity-stretched camera-facing ellipses.

### Gaps
- Could not open GDC Vault "Rendering Assassin's Creed III" (members-only) or the Uncharted 4 PPTX; no verified per-sprite counts or ms costs for shipped-game surface debris.
- No source found describing a shipped game that renders floating debris as octahedral/multi-view impostors.
- Still Wakes the Deep details are from search summaries only (403 on fetch).

---

## Key question 2: Octahedral / multi-view impostors — cost, D3D9 feasibility, orientation on a tilted surface

### Takeaway
Octahedral impostors (Brucks/Epic Impostor Baker) are a single 2D atlas (e.g. 2048², 12×12 or 16×16 frames) sampled with 3-frame blending on an 8-triangle card; nothing in the shipped technique requires texture arrays, geometry or compute shaders, so it fits SM3 in principle, but the pixel cost (3 frame samples × maps, optional parallax) is high relative to a plain sprite and no source describes tilting the impostor to a surface normal.

### Cited Findings
- Impostor types: "Full Sphere Impostor: Capture and render views for all angles around the object"; "Upper Hemisphere Impostor" captures only views above the terrain; "Traditional Billboards" use fixed horizontal angles plus a top-down image and "Cards facing away fade using a dither effect." — [Epic, Impostor Baker Plugin docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine)
- Frame counts: FramesXY=16 gives 256 sub-frames; for foliage "we use a value of 12 for the imposter's XY frame distribution" (144 frames); billboards capture 9 views in a 3×3 grid. — same
- Resolution: "Epic Games uses a resolution of 2048 for its projects, such as Fortnite Battle Royal"; Fortnite uses "Upper Hemisphere Imposters for all of our trees when Nanite is disabled". Scene capture should be ≥2× sub-frame size for supersampling; "a 4096 texture with 16 XY frames uses 256×256 subframes." — same
- Maps: BaseColor + Normal are usually enough; depth is a channel-packed scalar option (not default); choosing None for the alpha channel yields DXT1 instead of DXT5. — same
- Parallax modes: "No Parallax, Single Sample Parallax (like Bump Offset, no extra triangles), or Iterative Parallax (most expensive)"; iterative uses "Depth Derived Weights" and "chooses the best ray result for each pixel from a neighbor frame"; "Use Sprite Vertex Shader" is needed only with parallax and "worsens masked overdraw". — same
- Cost: "Impostors use 8 triangles and 9 vertices per card"; "the pixel shader is more expensive for imposters due to blending the three nearest frames"; "On mobile, impostors fall back to a single frame sample"; billboards (8 cards, 72 tris) have worse overdraw for masked materials but higher per-view texel density. — same
- Orientation: the page says impostors render "a single blended sprite frame from the perspective of the viewer" and does not describe behaviour when the actor is rotated or tilted. — same
- Hemisphere rationale from other implementations: Pixyz says hemisphere baking concentrates the same number of views where the viewer looks, "roughly doubles the effective quality"; Godot plugin: grid size 16 recommended, full sphere "Only useful when the object is visible from below". — [Godot-Octahedral-Impostors README](https://github.com/SIsilicon/Godot-Octahedral-Impostors); [search summary of Pixyz/Unity docs](https://www.pixyz-software.com/documentations/archives/plugin/2021.1/CreateImpostor.html)
- Ryan Brucks' original post (shaderbits.com/blog/octahedral-impostors) could not be fetched (page body not served to the fetcher; archive.org blocked). The Godot README credits "a shaderbits article" and xraxra/IMP as its sources. — [Godot README](https://github.com/SIsilicon/Godot-Octahedral-Impostors)

### Inferences
- [I] D3D9 feasibility: all inputs are ordinary 2D atlases (DXT1/DXT5) plus per-instance constants; the octahedral frame lookup and 3-frame blend are pure pixel-shader ALU + 3 (or 6 with normals) texture fetches, well within SM3 limits. Iterative parallax is a short ray-march loop; SM3 supports loops but it is the expensive option and unnecessary at detritus scale.
- [I] Tilted surface: the impostor's view-direction lookup is computed in the impostor's object space, so rotating the card's object matrix to the water normal (local frame from the height-field gradient) would make the baked views follow the tilt; however, the card quad itself in Epic's material is view-oriented and no source confirms this works for arbitrary tilts, so treat as unverified.
- [I] Scale mismatch: a 2048² atlas with 144 frames yields ~170 px per frame — for objects covering a handful of screen pixels (leaves at 1080p) a single-frame or 4-view sprite sheet is almost certainly cheaper and visually indistinguishable; octahedral impostors earn their cost for near-camera, larger floating items (crates, barrels, bodies) only.
- [I] Count scaling: because impostors are one quad each, instancing (D3D9 hardware instancing on SM3 cards) or CPU-batched quad VBs apply directly; the per-pixel 3-frame blend, not draw calls, is the limiting cost.

### Gaps
- No ms or fill-rate figures for octahedral impostors on any hardware in the sources opened.
- No primary source on orienting an octahedral impostor to a surface normal.

---

## Key question 3: Box / cube impostors, parallax-corrected impostor volumes, and a per-cell "cube of stuff under the surface"

### Takeaway
Two shipped SM2/SM3-era techniques already do "a textured box you ray-cast in the pixel shader": Interior Mapping (van Dongen 2008, fits ps2.0's 64 instructions) and Lagarde's parallax-corrected (box-projected) cubemaps (2012, PS3/360-measured). A per-water-cell interior-mapped volume holding a "suspended detritus" cubemap/atlas is a plausible SM3 construction, but I found no source using it for water or for debris, and no source linking a "distorted cube" look to Burnout Paradise.

### Cited Findings
- Interior Mapping: "raycasting in the pixel shader is used to calculate the positions of floors and walls behind the windows"; "The number of rooms rendered does not influence the framerate or memory usage"; "Because the interior walls are regularly spaced, the ray can be collided in constant time". — [van Dongen, Interior Mapping, CGI 2008](http://interiormapping.oogst3d.net/) (text from local copy `vandongen.txt`)
- SM2 fit: the paper states the instruction count is "small enough to be able to calculate the effect within the 64 instructions allowed in pixel shader model 2.0"; walls can be rotated by rotating object space. — same
- Objects inside the volume: "Furniture and characters can be added through the use of furniture planes" — a plane parallel to the surface inside the room, ray-tested against it; "the intersection of the ray with the furniture plane is closer... furniture plane is visible"; animated textures on the furniture plane; distortion grows the deeper the plane is on curved surfaces, "it is not advisable to add furniture planes" there. — same
- Box-projected cubemaps: a cubemap "represents an infinite box"; fix is to intersect the reflection ray with a proxy box (AABB or OBB slab test) and look up the cubemap with (hitPoint − probePos); OBB "is better to use" because AABB "is rather restricted". Only exact for mirror surfaces; "artists must ensure that the reflected camera will always remain within the box volume." — [Lagarde, Image-based lighting approaches and parallax-corrected cubemap (2012)](https://seblagarde.wordpress.com/2012/09/29/image-based-lighting-approaches-and-parallax-corrected-cubemap/)
- Cost measured on PS3: per-pixel correction ≈ 0.25 ms per extra cubemap at 25 % screen coverage, ≈ 0.75 ms at 75 %; mixing approach ≈ 0.08 ms per cubemap; Xbox 360 better with one cubemap but drops faster with more. Talk: [Lagarde & Zanuttini, SIGGRAPH 2012](https://history.siggraph.org/?p=140207)
- Classic layered impostors (Jeschke 2002) bound parallax error by layer placement: "A special layer placement is derived which bounds the geometric error introduced by parallaxes to a defined value." — [TU Wien TR-186-2-02-04](https://www.cg.tuwien.ac.at/research/publications/2002/TR-186-2-02-04/)
- A 2021 VRST paper does ray-marched parallax correction for impostors with cost "distributed over multiple frames". — [TH Köln impostor page](https://cg.web.th-koeln.de/impostor-based-rendering-acceleration-for-virtual-augmented-and-mixed-reality/)
- Burnout Paradise: two searches found no technical source on its impostor or "distorted cube" rendering; only general game pages. — [search results summary](https://en.wikipedia.org/wiki/Burnout_Paradise)

### Inferences
- [I] "Box impostor" for suspended detritus = Interior Mapping applied downward from the water plane: each 20-unit cell is a room whose "ceiling" is the water surface; the ray from the refracted eye vector is intersected with the cell's side/bottom planes (constant-time, regular spacing) and with one or more horizontal "furniture planes" at chosen depths carrying a detritus atlas (leaves just under the film, silt lower). Van Dongen's constraint — only one ray/plane test per plane, growing distortion on tilted surfaces — applies.
- [I] Advection in that scheme is a per-cell texture offset: scroll the furniture-plane UVs by the cell's accumulated displacement (integral of velocity), with Valve-style two-phase reset to avoid unbounded drift; the cubemap/atlas itself is static.
- [I] Lagarde's box projection is the same slab intersection, usable with a cubemap of "underwater stuff" per cell; but a cubemap per cell is memory-heavy and his own caveat (reflected ray must stay inside the box; only exact for mirror lookups) applies equally to refracted lookups, so expect visible warping at grazing angles.
- [I] Nothing in the sources connects box impostors to Burnout Paradise; the "distorted cube" look the question refers to is more likely parallax-corrected cubemap reflections on cars (Lagarde cites Half-Life 2 per-object cubemaps as the predecessor) than a debris technique.

### Gaps
- No source using interior mapping or box projection for water or debris; everything in this section about water is inference.
- Burnout Paradise rendering talk not found.

---

## Key question 4: Texture-space approaches — detritus/foam maps advected by the simulation velocity, keeping them from smearing, sprites at wet/dry edges and splash sites

### Takeaway
The verified recipe is Max & Becker's advected texture coordinates as used by Valve (2 phases, noise offset, half-phase stagger) and Chentanez & Müller (3 phases reset every τ ≤ 3 s, blend weights ⅓(1−cos), displacement weight ω = e^(−Ω·strain) that fades detail where the field stretches it). Scalar foam/detritus maps are instead *diffused/decayed* on the grid (Cords, Sea of Thieves) and then multiplied by a tiling texture; splash-site sprites are spawned from particle impacts (Chentanez) or a probe hit (AC3).

### Cited Findings
- Chentanez & Müller requirements for sub-grid detail: "1. They should be advected with the velocity field. 2. They must not be distorted excessively over time. 3. They disappear if being stretched too much. 4. The method must be relatively cheap." — [Chentanez & Müller 2010](https://matthias-research.github.io/pages/publications/hfFluid.pdf)
- Mechanism: "For each grid cell (i, j) we additionally store 3 sets of texture coordinates (s^k, t^k), k = 1..3 which are initialized with (iΔx, jΔx). They are transported with the velocity field using semi-Lagrangian advection. We reset (s^k, t^k) to (iΔx, jΔx) every τ seconds with a phase shift of τ/3 between k and (k+1) mod 3." — same
- Stretch fade: "ω = e^(−Ω μ)", μ the max-magnitude eigenvalue of the Green strain ½(DDᵀ − I) of the texture-coordinate Jacobian; "Ω > 0 controls how fast the small waves disappear with stretching, for which we use values between 0.5 to 2". Blend: final = ω Σ w_k F(s^k, t^k), "w_k = ⅓(1 − cos(2π (t − t0^k)/τ))"; "The phase shift ensures a constant blending weight." "We use τ ≤ 3 seconds in our examples." Neyret's regeneration would avoid the trade-off "but it is more expensive." — same
- Where it is evaluated: "The texture coordinates and the weights... are computed on the simulation grid points. They are then bi-linearly interpolated for per-pixel bump mapping or for displacing the rendering grid." Rendering grid in the boat example at ¼ Δx. — same
- Valve: two layers offset half a phase; distortion "reasonable for the first 1/3 of uv space"; noise fixes pulsing; per-phase UV offset fixes repetition; colour/debris flow offsets the distortion range to be centred at the rest position. — [Vlachos 2010](https://www.advances.realtimerendering.com/s2010/Vlachos-Waterflow(SIGGRAPH%202010%20Advanced%20RealTime%20Rendering%20Course).pdf)
- Catlike Coding's formulation of the same scheme: `uv - flowVector * progress`, `progress = frac(time)`, triangle-wave weight `w(p) = 1 - |1 - 2p|`, low-frequency noise in the flow map's A channel added to time so the reset "has changed into a wave that spreads across the surface in an organic way", phase B offset 0.5, per-phase jump `uvw.xy += (time - progress) * jump` with jump magnitudes 0.2–0.25, `flowOffset = -0.5` so the peak of each phase is undistorted; warns DXT1 compression of the flow map causes blocky artifacts. — [Catlike Coding, Texture Distortion](https://catlikecoding.com/unity/tutorials/flow/texture-distortion/)
- Scalar foam diffusion (Cords): f_new = d·f + (1−d)/4·Σ neighbours, d∈[0,1] sets both fade and spread; foam texture blended per cell by intensity. — [Cords 2009](https://rosdok.uni-rostock.de/file/rosdok_disshab_0000000334/rosdok_derivate_0000004116/Dissertation_Cords_2009.pdf)
- Scalar foam feedback blur (Sea of Thieves): "We progressively blur the result of the foam buffer with feedback to simulate the foam dispersing"; foam seeded at wave peaks and at depth-buffer intersections in a camera-centred window. — [Ang et al. 2018](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- AC3 coastal foam: offline 512×512 over 4 km (≈8 m/texel) with Gaussian blur + Perlin noise; three foam types in RGB blended by a colour ramp. — [fxguide](https://www.fxguide.com/?p=38193)
- Sprites at splash sites: Chentanez creates a foam particle with probability depending on droplet impact speed when a splash particle lands; particle start positions jittered by a random fraction of a time step; foam lifetime noise-modulated. AC3 debris fires a splash effect from a single probe on water hit. — sources above
- Wet/dry edges: Chentanez's solver has "wet-dry region tracking"; the breaking-wave criterion spawns particles where the height-field gradient is large, with particle count ∝ |∇η|. — [Chentanez & Müller 2010](https://matthias-research.github.io/pages/publications/hfFluid.pdf)

### Inferences
- [I] For the user's CPU sim: store per cell 2 or 3 advected UV pairs (semi-Lagrangian, reset every τ with staggered phase) and upload them as vertex attributes of the water mesh; the pixel shader fetches a detritus RGBA atlas 2–3 times and blends with the cosine/triangle weights. This is exactly Valve's SM2.0b budget (+2 fetches, +21 ALU per layer pair), so SM3 has headroom for a detritus layer plus the normal layer.
- [I] Keep detritus from smearing: (a) Valve's rule — colour content uses a narrower, zero-centred distortion range; (b) Chentanez's strain-fade ω — compute Green strain from the stored UV Jacobian on the CPU grid and fade detritus to zero where μ is large (so stretched leaves vanish rather than streak); (c) Catlike's per-phase jump so the same leaf is not seen cycling at one spot.
- [I] A scalar "detritus density" channel can share the foam map: Cords' diffusion kernel is a 5-tap stencil per cell per frame on the CPU — negligible for grids of 128² to 256².
- [I] Sprite spawning at wet/dry edges can be driven by the CPU wet-dry mask: emit surface-aligned disks where the mask changes state and where |∇η| exceeds a threshold, with lifetime noise as in Chentanez.

### Gaps
- No source quantifies how long colour (as opposed to normal-map) content survives advection before looking smeared; Valve's "first 1/3 of uv space" is the only number.
- Neyret 2003 "Advected textures" (the regeneration scheme that avoids the τ trade-off) not opened.

---

## Key question 5: Interaction with the water material — sorting against refraction, soft fading, surface-aligned vs camera-facing, partly-submerged look

### Takeaway
Verified pieces: foam disks are surface-aligned (Chentanez); spray is velocity-stretched camera-facing; soft-particle depth fade is `saturate(scale*(myDepth-sceneDepth))` on D3D9 (GPU Gems 3); AC3's targeting band is a camera-projected particle decal on the wave surface; Sea of Thieves and Uncharted 3 fold foam into the water shader itself (so it sorts trivially with refraction). No source describes clipping a sprite by the height field for a half-submerged look — that is inference.

### Cited Findings
- Surface-aligned foam vs camera-facing spray: "Foam particles are rendered as diffuse disks with normals perpendicular to the height field water surface"; spray "as an elongated ellipse along the direction of their velocity". — [Chentanez & Müller 2010](https://matthias-research.github.io/pages/publications/hfFluid.pdf)
- Soft particles (D3D9 era): pixel shader computes `zFade = saturate(scale * (myDepth - sceneDepth))` and multiplies alpha, replacing the hard depth discard; "Harsh, sharp intersections are thus avoided"; "zFade is zero where the particle is entirely occluded." — [GPU Gems 3 ch. 23, Cantlay](https://developer.nvidia.com/gpugems/gpugems3/part-iv-image-effects/chapter-23-high-speed-screen-particles)
- Off-screen particle compositing states for D3D9: SrcBlend=SrcAlpha, DestBlend=InvSrcAlpha, SrcBlendAlpha=Zero, DestBlendAlpha=InvSrcAlpha with SeparateAlphaBlendEnable and black clear; max-of-4 depth downsample to shrink halos ("There is absolutely no physical or theoretical basis for this"); suits "soft, low-frequency effects like smoke and fog", "less suited to high-frequency effects like flying debris". — same
- Foam inside the water shader (no separate sorting): Sea of Thieves blends its foam mask "with artist-authored textures" in the water material; Uncharted 3 outputs foam modulation as vertex colour and uses "foam texture to modulate water depth" for churn. — [Ang et al. 2018](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf); [GDC 2012 Uncharted](https://www.slideshare.net/slideshow/water-technologyofunchartedgdc2012/12977478)
- Camera-projected decal on waves: AC3's red aiming band "is drawn by projecting particles from the camera so they intersect the waves." — [fxguide](https://www.fxguide.com/?p=38193)
- Refraction LOD split: AC3 uses a transparent refracting shader (LOD 0) only in shallow water "because it is costly" and an opaque non-refracting shader in deep water, cross-faded over ~400 m. — same
- Depth-buffer intersection foam: Sea of Thieves adds foam "around objects that intersect the water surface within a camera centered window using depth buffer comparisons". — [Ang et al. 2018](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- Unity's particle renderer offers a "Horizontal Billboard" mode where the particle plane is parallel to the XZ floor (generic engine support for surface-aligned sprites). — [Unity Renderer module docs](https://docs.unity.com/en-us/engine/6000.3/manual/visual-effects/particle-systems/particle-system-modules/part-sys-renderer-module.md)

### Inferences
- [I] Sorting with a D3D9 forward water pass (opaque scene → copy backbuffer for refraction → draw water): anything *in* the water material (foam/detritus map, flowed debris colour) is free of sorting problems and is also correctly refracted/reflected only if included in the reflection pass. Anything drawn as separate sprites must be drawn after the water with depth-test-only (no write); floating sprites just above the surface then overdraw the water correctly, but will be missing from the reflection render target unless the sprite pass is also run into it.
- [I] Partly-submerged look without clipping: draw two layers per sprite — an "above" surface-aligned sprite after the water, and a "below" copy drawn *before* the water into the scene so the water's refraction copy and fog/tint attenuate it; both are cheap quads. Alternatively, pass the local water height (sampled from the CPU grid) into the sprite's pixel shader and `clip()` texels whose reconstructed height is below it — SM3 `clip`/texkill is available; no source does this for water, so this is design inference.
- [I] Soft fading against the *water* rather than the opaque scene requires the water's depth; since D3D9 cannot read the depth buffer directly, write water depth to a small R32F/R16F target (or use the sprite's height above the CPU height field as the fade term, which costs nothing on the GPU).
- [I] Surface-aligned sprites should take their orientation from the height-field normal (finite-difference of η on the CPU, or the water normal map at a coarser level); Chentanez's "normals perpendicular to the height field" implies exactly this.

### Gaps
- No primary source on depth-sorting sprites against a refracting water surface in a D3D9 forward renderer; all sorting guidance here is inference.
- No source on height-field clipping of sprites.

---

## Key question 6: Numbers — counts, draw calls, fill cost, texture sizes on 2010–2012 hardware

### Takeaway
Hard numbers are sparse and mostly from research or adjacent techniques: flow adds +2 fetches/+21 ALU on ps2.0b; GPU Gems 3 measured a 73-instruction particle shader at 46.9 M particle-pixels costing 25 fps at 1600×1200 on an 8800 GTX vs 51–61 fps at ¼ resolution; Chentanez runs 83K–250K surface/spray particles per frame with whole-frame times of 10–18 ms on a GTX 480 (CUDA); Lagarde's per-pixel box projection costs ≈0.25–0.75 ms per cubemap on PS3; impostor atlases are 2048² with 144–256 frames.

### Cited Findings
- Flow-map shader cost: "+2 texture fetches (flow & noise), +21 arithmetic pixel shader instructions" vs. two scrolling normal maps; flow map "~4 texels/meter"; target ps2.0b / Xbox 360. — [Vlachos 2010](https://www.advances.realtimerendering.com/s2010/Vlachos-Waterflow(SIGGRAPH%202010%20Advanced%20RealTime%20Rendering%20Course).pdf)
- Particle fill cost (GeForce 8800 GTX, 1600×1200, 73-instruction shader): full-res 25 fps at 46.9 M particle pixels; mixed-res 4×4 51 fps (3.5 M px); low-res max-z 4×4 61 fps (2.9 M px); 2×2 mixed 44 fps (12.0 M px). With 9-instruction shader: 44 / 50 / 57 fps (high / mixed / low). At 3.5 M high-res pixels the overhead outweighs savings (64.4 vs 63.3 fps). A game in development cited "20 million particle pixels and a 16-instruction shader". — [GPU Gems 3 ch. 23](https://developer.nvidia.com/gpugems/gpugems3/part-iv-image-effects/chapter-23-high-speed-screen-particles)
- Simulation-side particle counts and frame times (GTX 480, CUDA): Beach 128×128 grid, 220K particles, 9.88 ms total incl. rendering; Ocean 256×256, 83K, 13.13 ms; Boat 900×135, 250K, 18.05 ms GPU / 69.75 ms CPU 4 threads. Δt = 16.66 ms. — [Chentanez & Müller 2010](https://matthias-research.github.io/pages/publications/hfFluid.pdf)
- Cords spray: 200 layers × 700 particles at 53.1 fps (2009 hardware, unspecified in the caption). — [Cords 2009](https://rosdok.uni-rostock.de/file/rosdok_disshab_0000000334/rosdok_derivate_0000004116/Dissertation_Cords_2009.pdf)
- Bagar 2010: 64k particles at 1280×720 on Q9450 + GTX 280; foam "does not significantly increase running time". — [TU Wien page](https://www.cg.tuwien.ac.at/research/publications/2010/bagar2010/)
- Box projection: ≈0.25 ms per extra cubemap at 25 % coverage, ≈0.75 ms at 75 % on PS3; mixing approach ≈0.08 ms per cubemap. — [Lagarde 2012](https://seblagarde.wordpress.com/2012/09/29/image-based-lighting-approaches-and-parallax-corrected-cubemap/)
- Interior mapping fits "within the 64 instructions allowed in pixel shader model 2.0"; a standard texture of the same dimension "requires only 48kb of memory, or 8kb if DXT1". — [van Dongen 2008](http://interiormapping.oogst3d.net/)
- Impostor atlas sizes: 2048 (Fortnite), 12×12 frames for foliage, 16×16 = 256 frames max shown, 4096 with 16 XY frames → 256×256 sub-frames; 8 tris / 9 verts per impostor card. — [Epic Impostor Baker docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine)
- Foam-map resolutions: AC3 coastal foam 512×512 over 4 km × 4 km (≈8 m/texel); Valve flow ~4 texels/m. — [fxguide](https://www.fxguide.com/?p=38193); [Vlachos 2010](https://www.advances.realtimerendering.com/s2010/Vlachos-Waterflow(SIGGRAPH%202010%20Advanced%20RealTime%20Rendering%20Course).pdf)
- Ottosson sim: 3 ms per step on one Xeon core (Frostbite prototype). — [Ottosson 2011](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/water-interaction-ottosson-bjorn.pdf)

### Inferences
- [I] Texture-space detritus is essentially free in fill terms (it rides on the water pass: ~3 extra fetches + the blend ALU per layer); sprite detritus is bounded by overdraw, and GPU Gems' numbers say a 2007 GPU handles tens of millions of particle-pixels per frame only at reduced resolution — but leaves/paper are *small*, so a few thousand surface-aligned sprites of ~10–30 px each is ≈1 M pixels, far below those budgets.
- [I] Draw calls: with SM3 hardware instancing or a CPU-built dynamic VB (D3DUSAGE_DYNAMIC, NOOVERWRITE), thousands of sprites are one draw per atlas; the only reasons to split are above/below-water layering (2 draws) and reflection-pass inclusion (+1–2 draws).
- [I] Texture budget: one 1024² DXT5 detritus/foam atlas (≈1.3 MB) plus one 512² or 1024² flow/noise map for the whole water body is comparable to Valve's shipped budget; octahedral atlases at 2048² DXT5 (≈5.3 MB each) are only justified for a handful of large floating props.

### Gaps
- No shipped-game numbers for surface debris sprite counts or ms; the only particle counts are research systems.
- No 2010–2012 PC measurement of octahedral impostor fill cost.

---

## D3D9 / SM3 feasibility flags (cross-cutting)

- Chentanez & Müller's crest-aligned diagonal choice "can be implemented efficiently on the GPU using a geometric shader" and their sim is CUDA — **not SM3**; but the texture-coordinate advection and weights are computed "on the simulation grid points" (CPU-friendly) and interpolated per vertex, so the rendering side needs no GS/compute. [V] — [Chentanez & Müller 2010](https://matthias-research.github.io/pages/publications/hfFluid.pdf)
- Valve flow: ps2.0b. Interior mapping: ps2.0. Lagarde box projection: PS3/360 (SM3-class). GPU Gems 3 off-screen particles: D3D9 render states listed. Octahedral impostors: 2D atlas + ALU; iterative parallax uses a loop (SM3 OK, costly). [V/I]
- Sea of Thieves depth-buffer-projected foam and Still Wakes the Deep's Niagara sim are GPU-simulation techniques (DX11+/UE5); their *outputs* (a blurred scalar mask, a readback of sim data into the material) are reproducible by a CPU grid + texture upload. [I]
