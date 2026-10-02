# Beautifying Advent Rising terrain: papers, talks and code

Researched 2026-10-02. Every link was checked with an HTTP request on that date. "200" means it loaded. Pages marked *(bot-blocked)* returned 403 to scripts and should be opened in a browser.

## What we are working with

- UE2 `TerrainInfo`: a G16 heightmap (`TerrainMap`), sectors, up to 32 `Layers[]` (Texture, AlphaMap, UScale/VScale, rotation, `TextureMapAxis`), and `DecoLayers`.
- The game blends layers with ps.1.1/1.4 shaders (`PS_Terrain3Layer`/`4Layer`): an RGB weight map times 3-4 layer textures, times baked per-vertex colour plus dynamic vertex lights.
- Our hook is a d3d8->d3d9 wrapper that can swap the pixel shader of a draw (ps_2_0, ps_2_b or ps_3_0), bind extra samplers, set per-draw constants and get camera-space position via texcoord generation. We cannot change vertex data or level files.
- **Consequence:** anything that needs only what the draw already has (the layer textures, weights, vertex colour, position) is cheap. Anything that needs the heightmap or new textures means extracting them offline (UEViewer/umodel or UE Explorer, both MIT) and binding them on extra samplers, keyed per map and per sector.
- Background on UE2 terrain:
  - [UnrealWiki: Terrain](https://beyondunrealwiki.github.io/pages/terrain.html)
  - [UnrealWiki: TerrainInfo](https://beyondunrealwiki.github.io/pages/terraininfo.html)
  - [UnrealWiki: Terrain Texture Layer](https://beyondunrealwiki.github.io/pages/terrain-texture-layer.html)
  - [Unreal Archive: Legacy:Terrain](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Terrain.html)
  - The UDN "Two" terrain page `docs.unrealengine.com/udk/Two/TerrainTutorial.html` is *(bot-blocked)*.

---

## 1. Techniques

### Blending and tiling

| Technique | Source (year) | Relevance |
|---|---|---|
| **Height/depth-aware splat blending** | Andrey Mishkinis, [Advanced Terrain Texture Splatting](https://www.gamedeveloper.com/programming/advanced-terrain-texture-splatting) (Gamasutra, 2013) | Uses `ma = max(h_i + w_i) - depth; b_i = max(h_i + w_i - ma, 0)`, normalised. This turns mushy alpha blends into sand settling into rock cracks. Biggest visual win per instruction. With no height maps, use the layer texture's luminance as the height. |
| Original texture splatting | Charles Bloom, [Terrain Texture Compositing by Blending in the Frame-Buffer](https://www.cbloom.com/3d/techdocs/splatting.txt) (2000) | The model UE2 implements. Useful for vocabulary. |
| Procedural shader splatting (slope/height rules, layers computed in shader) | Johan Andersson, [Terrain Rendering in Frostbite Using Procedural Shader Splatting](https://advances.realtimerendering.com/s2007/Andersson-TerrainRendering(Siggraph07)-CourseNotes.pdf) (SIGGRAPH 2007) | The closest analogue to what we can do: derive masks in the shader from slope, height and noise on top of painted weights. Also covers dominant-layer and shader-permutation cost tricks. |
| Texture repetition (3 methods) | Inigo Quilez, [Texture Repetition](https://iquilezles.org/articles/texturerepetition/) (2015). Shadertoys: [lt2GDd](https://www.shadertoy.com/view/lt2GDd), [4tsGzf](https://www.shadertoy.com/view/4tsGzf), [Xtl3zf](https://www.shadertoy.com/view/Xtl3zf) *(Shadertoy bot-blocked; URLs taken from IQ's article)* | Technique 3 costs **2 samples** (per-tile offset variants picked by a low-frequency noise index) and is the cheapest fix for obvious layer tiling at ps_2_0. Technique 1 is 4 samples. Technique 2 is 9 samples (too costly). |
| Histogram-preserving tiling and blending | Heitz & Neyret, [High-Performance By-Example Noise using a Histogram-Preserving Blending Operator](https://eheitzresearch.wordpress.com/722-2/) (HPG 2018). [HAL](https://hal.inria.fr/hal-01824773) | Best-quality anti-tiling. Needs a precomputed Gaussianised texture plus an inverse LUT, which we could generate offline per layer texture. |
| Same method, practical version | Deliot & Heitz, [Procedural Stochastic Textures by Tiling and Blending](https://eheitzresearch.wordpress.com/738-2/) (GPU Zen 2, 2019). Unity blog: [Procedural Stochastic Texturing in Unity](https://unity.com/blog/engine-platform/procedural-stochastic-texturing-in-unity) (2019-02-14) | Includes a code listing. The 3-sample triangle-grid version fits ps_2_b/ps_3_0. |
| **Hex-tiling** | Morten Mikkelsen, [Practical Real-Time Hex-Tiling](https://jcgt.org/published/0011/03/05/) (JCGT 2022). [Paper PDF](https://jcgt.org/published/0011/03/05/paper-lowres.pdf). Code: [mmikk/hextile-demo](https://github.com/mmikk/hextile-demo) (**MIT**) | Samples the *original* texture (3 samples, no precompute), with a contrast-preserving blend. **The best anti-tiling choice for us.** Port `hextiling.h` to HLSL SM3, with gradients via `tex2Dgrad`. |
| Texture bombing | [GPU Gems ch. 20, Texture Bombing](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-20-texture-bombing) (2004) | Older relative of the above. Decals of pebbles and cracks without new geometry. |

### Lighting, slopes and procedural rules

| Technique | Source (year) | Relevance |
|---|---|---|
| Triplanar mapping for steep slopes | Ryan Geiss, [GPU Gems 3 ch. 1, Generating Complex Procedural Terrains Using the GPU](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-1-generating-complex-procedural-terrains-using-gpu) (2007). Ben Golus, [Normal Mapping for a Triplanar Shader](https://bgolus.medium.com/normal-mapping-for-a-triplanar-shader-10bf39dca05a) (2017) *(Medium bot-blocked)* | Fixes stretched cliff textures on heightmap terrain. Needs world position (we have camera-space position, so we need the inverse view matrix as a constant) and a normal (see the next row). Costs 3x the samples, so apply it only to the rock layer and only where the slope is above a threshold. |
| Normals from the heightmap | Central differences on the G16 `TerrainMap`. See IQ, [Terrain Raymarching](https://iquilezles.org/articles/terrainmarching/) (normal section) | Requires extracting `TerrainMap` per map (UEViewer) and binding it with sector UV/scale constants. Gives smooth per-pixel normals for lighting, slope masks, triplanar and AO. **Fallback without the heightmap:** `normalize(cross(ddx(P), ddy(P)))` from camera-space position on ps_2_a/ps_3_0. This gives faceted per-triangle normals: fine for slope masks, ugly for lighting. |
| Normal maps from albedo luminance | Offline tools: [Materialize](https://github.com/BoundingBoxSoftware/Materialize) (**GPL-3.0**), [NormalMap-Online](https://github.com/cpetry/NormalMap-Online) (**MIT**) | Generates detail normal and height maps for each layer texture offline, which also gives better heights for Mishkinis blending. Runtime alternative: a Sobel filter on luminance in the shader (4 extra taps per layer, which is costly). |
| Parallax occlusion mapping | Tatarchuk, [Dynamic Parallax Occlusion Mapping with Approximate Soft Shadows](https://advances.realtimerendering.com/s2006/Tatarchuk-POM.pdf) (2006) | ps_3_0 only and costly. It is the wrong fit for blended terrain because you have to march the *blended* height. Use it only near the camera on rocky layers, or skip it. |
| Horizon mapping / heightfield shadows / AO | Sloan & Cohen, [Interactive Horizon Mapping](https://www.ppsloan.org/publications/bs.pdf) (EGWR 2000). Timonen & Westerholm, [Scalable Height Field Self-Shadowing](http://wili.cc/research/hfshadow/) (EG 2010) | Bake an AO map and a sun-horizon/shadow map **offline** from the extracted heightmap (a Python script), then bind it as an extra texture. Big depth win for valleys and creases that vertex lighting misses. |
| Distance fog and aerial perspective | IQ, [Better Fog](https://iquilezles.org/articles/fog/) (height fog and sun-tinted fog). Bruneton, [Precomputed Atmospheric Scattering](https://github.com/ebruneton/precomputed_atmospheric_scattering) (2008, **BSD-3**, [docs](https://ebruneton.github.io/precomputed_atmospheric_scattering/)). Hillaire, [A Scalable and Production Ready Sky and Atmosphere Rendering Technique](https://sebh.github.io/publications/egsr2020.pdf) (EGSR 2020) with [code](https://github.com/sebh/UnrealEngineSkyAtmosphere) (**MIT**) | IQ's analytic height fog with sun in-scatter is about 10 ALU instructions and gives large depth-cue gains. Bruneton and Hillaire are overkill per draw, but their aerial-perspective LUT idea could be baked to a small 2D texture. |
| Slope/height auto-materials (snow, rock, moss) | Jeremy Moore, [Terrain Rendering in Far Cry 5](https://www.gdcvault.com/play/1025480/Terrain-Rendering-in-Far-Cry) (GDC 2018). Etienne Carrier, [Procedural World Generation of Far Cry 5](https://www.gdcvault.com/play/1025557/Procedural-World-Generation-of-Far) (GDC 2018). Mattias Widmark, Terrain in Battlefield 3 ([slides PDF](https://media.gdcvault.com/gdc2012/slides/Programming%20Track/Widmark_Mattias_Terrain_in_Battlefield3a.pdf), [video](https://gdcvault.com/play/1015414/Terrain-in-Battlefield-3-A), GDC 2012). [Ghost Recon Wildlands: Terrain Tools and Technology](https://www.gdcvault.com/play/1024029/GPU-Based-Procedural-Placement-in) (GDC 2017) | Rule-based masks from slope, height, curvature and noise. For us this means mixing a rock layer onto steep slopes and adding darkening or moss in concave areas, using textures already loaded in the draw. BF3 also covers the macro/detail split and procedural masks. |
| GPU procedural placement | Jaap van Muijden, [GPU-Based Procedural Placement in Horizon Zero Dawn](https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn) (GDC 2017) | Its density-from-rules ideas map onto UE2 DecoLayers. Mostly out of reach for us (vertex data), but it shows how to tint deco to match the terrain. |
| Macro colour plus near detail | Widmark BF3 and Andersson 2007 (above) | **Macro:** a low-frequency variation map multiplied in, generated procedurally (value noise in world XY) or from a downsampled average of the layer textures. This kills the "same green everywhere" look at distance. **Detail:** a second, higher-frequency sample of the same layer, faded in near the camera. |
| Virtual texturing | Sean Barrett, [Sparse Virtual Textures](https://silverspaceship.com/src/svt/) (2008). Chen, [Adaptive Virtual Texture Rendering in Far Cry 4](https://www.gdcvault.com/play/1021761/Adaptive-Virtual-Texture-Rendering-in) (GDC 2015) | **Out of scope.** It needs control of the render loop and feedback. Mentioned for completeness. |

## 2. Performance ideas for old splatting

1. **Do it in one pass.** UE2 draws a sector once per group of 3-4 layers. Our replacement shader can do the full lighting, fog and blend in the *first* pass. Where the later passes only add more layers, merge their weights into one ps_3_0 pass. That means binding all of the sector's alpha maps and layer textures, up to 16 samplers on SM3 (8 layers = 8 colour + 2 RGBA weight textures). This needs capturing the sector's layer list across passes. Reasonable if the wrapper caches per-sector state, but not trivial.
2. **Pack weights.** Use RGBA = 4 layer weights per texture. Use the A channel of each layer texture as height for Mishkinis blending (bake once offline into replacement DDS files, or compute luminance at runtime).
3. **Atlases instead of texture arrays.** D3D9 has no arrays. Pack the layer textures in a 2x2 or 4x4 atlas with padded tiles. Wrap addressing must then be done manually (`frac`) plus `tex2Dgrad` to avoid mip seams, so it is SM3 only. Usually not worth it below about 8 layers.
4. **Dominant-layer culling.** Sort weights and sample only the top 2-3 layers per pixel, using SM3 dynamic branching on `w > epsilon` (Andersson 2007 and Widmark 2012 do this per tile). This only pays on SM3 hardware with coherent branches, which terrain usually has.
5. **Layer LOD by distance.** Beyond about 50-100 m, skip anti-tiling, detail and triplanar, and fall back to a single sample per layer plus the macro map. Fade with `saturate((dist - a) * b)` to avoid a visible line.
6. **Cheap anti-tiling only on the 1-2 most visible layers** (grass/dirt), not all 32.
7. **Bake, don't compute.** AO, horizon shadows and normals come from offline heightmap processing and cost one sample at runtime.

## 3. Code to study or port

| Project | Licence | What to take |
|---|---|---|
| [mmikk/hextile-demo](https://github.com/mmikk/hextile-demo) | **MIT** | Hex-tiling HLSL, ready to port. |
| [TokisanGames/Terrain3D](https://github.com/TokisanGames/Terrain3D) ([shaders](https://github.com/TokisanGames/Terrain3D/tree/main/src/shaders)) | **MIT** | Height blending, detiling, macro variation, projection on slopes. A clean modern reference written in Godot shader language, which ports easily to HLSL. |
| [Zylann/godot_heightmap_plugin](https://github.com/Zylann/godot_heightmap_plugin) (HTerrain, [shaders](https://github.com/Zylann/godot_heightmap_plugin/tree/master/addons/zylann.hterrain/shaders)) | **MIT** | Has a "classic4" splat shader with depth blending plus a global colour map. Very close to our case. |
| [OGRECave/ogre](https://github.com/OGRECave/ogre) ([Components/Terrain](https://github.com/OGRECave/ogre/tree/master/Components/Terrain)) | **MIT** | SM2/SM3-era terrain material generator: layer blend, lightmap, colour map. Same hardware era as us. |
| [OpenMW](https://gitlab.com/OpenMW/openmw) ([shaders](https://gitlab.com/OpenMW/openmw/-/tree/master/files/shaders)) | **GPL-3.0** | Per-pixel lighting and parallax on an old-game blend-map terrain. A real-world "old game, new terrain shading" example. |
| [o3de/o3de](https://github.com/o3de/o3de) ([Terrain gem](https://github.com/o3de/o3de/tree/development/Gems/Terrain)) | **Apache-2.0 / MIT** | Modern macro/detail material terrain, the successor to Lumberyard. |
| [aws/lumberyard](https://github.com/aws/lumberyard) | **Lumberyard Terms (restrictive)**. Archived. | Avoid copying. Use O3DE instead. |
| CRYENGINE (official repo removed; mirrors such as [MergHQ/CRYENGINE](https://github.com/MergHQ/CRYENGINE)) | **[CRYENGINE licence](https://www.cryengine.com/ce-terms) (restrictive, engine-bound)** | **Do not reuse code.** Read only for ideas. |
| [UnityLabs/procedural-stochastic-texturing](https://github.com/UnityLabs/procedural-stochastic-texturing) | **No licence file found.** Treat as all rights reserved. | Reimplement from the Heitz/Deliot paper instead. |
| Unity [Graphics](https://github.com/Unity-Technologies/Graphics) (TerrainLit height blend) | **Unity Companion License** (Unity-dependent use only) | **Do not reuse.** |
| [MicroSplat](https://assetstore.unity.com/packages/tools/terrain/microsplat-96478) | Unity Asset Store EULA (commercial, closed) | **Do not reuse.** Its documentation is a useful feature checklist: height blend, stochastic sampling, triplanar, distance resampling, per-texture properties. |
| IQ Shadertoys (texture repetition) | Shadertoy default is **CC BY-NC-SA 3.0** unless the shader says otherwise | Fine for our non-commercial share-alike mods. Credit IQ. |
| [crosire/d3d8to9](https://github.com/crosire/d3d8to9) | BSD-2 | Base of our wrapper approach. |
| [elishacloud/dxwrapper](https://github.com/elishacloud/dxwrapper) | zlib (plus third-party parts) | d3d8to9 plus extras. The usual route for DX8 games into Remix and ReShade. |
| [crosire/reshade](https://github.com/crosire/reshade) | BSD-3 | Post-process only. It cannot target terrain draws (no per-draw hook without an add-on). An add-on API exists, but our wrapper already does more. |
| [martymcmodding/qUINT](https://github.com/martymcmodding/qUINT) | **"All rights reserved"** | **Do not copy code.** Mentioned because MXAO and its other effects are popular in old-game presets. |
| [NVIDIAGameWorks/rtx-remix](https://github.com/NVIDIAGameWorks/rtx-remix) / [dxvk-remix](https://github.com/NVIDIAGameWorks/dxvk-remix) / [bridge-remix](https://github.com/NVIDIAGameWorks/bridge-remix) | MIT (dxvk-remix: zlib/MIT) | Alternative path. Remix targets **fixed-function DX8/9** via a d3d8-to-9 wrapper ([compatibility](https://docs.omniverse.nvidia.com/kit/docs/rtx_remix/latest/docs/introduction/intro-compatibility.html), [wiki](https://github.com/NVIDIAGameWorks/rtx-remix/wiki/Compatibility)). AR's terrain uses **programmable ps.1.x shaders**, which Remix handles poorly or not at all. That makes it a large and risky detour, not a terrain fix. |
| [gildor2/UEViewer](https://github.com/gildor2/UEViewer) (umodel), [EliotVU/Unreal-Library](https://github.com/EliotVU/Unreal-Library) | MIT | Extract `TerrainMap`, alpha maps and layer textures from AR packages for offline baking. |

I found no published UT2004/UE2 community project that improved terrain *shading* through a wrapper. The UE2 community worked in-editor (more layers, detail textures via materials, DecoLayers). Our wrapper approach appears to be novel for UE2.

## 4. Prioritised recommendation (ps_2_b/ps_3_0 per-draw replacement)

Ranked by visual win per cost.

1. **Height-aware blending (Mishkinis)**, using layer luminance as height.
   - Content: none.
   - Cost: +~10 ALU, no extra samples.
   - The single biggest "looks like a newer game" change at layer borders.
2. **Analytic height fog / aerial perspective (IQ "Better Fog")** with a sun-direction tint.
   - Content: none (constants only).
   - Cost: very low.
   - Gives depth and cohesion. Match the game's existing fog colour.
3. **Anti-tiling on the 1-2 dominant ground layers**: hex-tiling (MIT) on SM3, or IQ technique 3 (2 samples) on ps_2_b.
   - Content: none, or an optional 64x64 noise texture.
   - Cost: medium.
4. **Macro variation**: world-space value-noise colour and brightness modulation at about 30-100 m scale, plus a near-camera detail resample of the same layer.
   - Content: none (procedural) or a tiny noise texture.
   - Cost: low.
5. **Slope-aware rock/moss mixing and curvature darkening**, using `ddx/ddy` face normals.
   - Content: none at first. Better with the heightmap.
   - Cost: low-medium.
6. **Baked heightmap AO and sun-shadow (horizon) map**, plus smooth per-pixel normals for lambert re-lighting.
   - Content: **needs** the `TerrainMap` extracted per level and an offline bake script, bound per sector with UV constants.
   - Cost: low at runtime, high in pipeline effort. Second-biggest win after #1 once it is in place.
7. **Triplanar on cliffs** and **detail normal maps per layer** (generated offline with NormalMap-Online or Materialize).
   - Content: **needs** the heightmap normals for #6, and new per-layer normal maps.
   - Cost: highest.
   - Do it last. POM and virtual texturing: skip.

**Cheap with no new content:** 1-5. **Need extracted or generated content:** 6-7.
