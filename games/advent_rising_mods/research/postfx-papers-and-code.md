# Post-processing for Advent Rising (D3D8 -> D3D9 wrapper, color-only, ps_2_x / ps_3_0)

Researched 2026-10-02. Every link below was fetched and returned HTTP 200 on that date (a few vendor sites
block scripts with 403 - noted where so). Licences come from the GitHub API plus the actual LICENSE / file headers.

**Our constraints:** finished LDR 8-bit frame only (before HUD), no depth / motion vectors / normals,
HLSL ps_2_0 (64 ALU + 32 tex), ps_2_b (512 instr), ps_3_0 (512+ instr, dynamic branching, `tex2Dlod`).
No compute, no integer ops, no UAVs. Multi-pass with our own render targets is fine.

---

## Key insight before anything else

The game hands us an **already tonemapped, clipped 8-bit image**. That changes what each paper is worth:

- **Tonemapping** papers matter mainly for **how we composite bloom**: linearize (approx. `pow(c, 2.2)`),
  add bloom (which can go above 1.0), then run a filmic/AgX/Hable curve to roll highlights off instead of
  hard-clipping. Applying a filmic curve to the raw frame alone just flattens contrast.
- **LUT grading** is the ideal fit for LDR input: one fetch, artist-authored in Photoshop/Resolve/GIMP,
  and it can absorb our existing saturation/contrast/balance math into a single texture.
- **Anti-aliasing** must run **first** (before bloom, sharpening, grain), else edge detection sees noise.
- **Dither last**, after everything, to kill banding we ourselves introduce (8-bit RT round trips).

Suggested pass order: `SMAA/FXAA -> bloom (dual filter) -> linear composite + tonemap -> LUT grade -> CAS sharpen -> CA / vignette -> grain + dither -> (HUD)`.

---

## 1. Papers and talks

### Bloom / blur
| Year | Work | Link | Why it matters for us |
|---|---|---|---|
| 2003 | Masaki Kawase, "Frame Buffer Postprocessing Effects in DOUBLE-S.T.E.A.L (Wreckless)", GDC 2003 | [ppt](http://www.daionet.gr.jp/~masa/archives/GDC2003_DSTEAL.ppt) | The original Kawase blur: iterated 4-tap bilinear blurs, designed for exactly our hardware era (SM1/2). |
| 2014 | Jorge Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH Advances | [page](https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/), [course page](https://advances.realtimerendering.com/s2014/index.html) | Mip-chain bloom (13-tap downsample, 3x3 tent upsample, Karis average against fireflies) - the modern standard; every pass fits ps_2_b/ps_3_0. Also covers DOF and motion blur (need depth/velocity). |
| 2015 | Marius Bjorge (ARM), "Bandwidth-Efficient Rendering", SIGGRAPH 2015 | [slides pdf](https://community.arm.com/cfs-file/__key/communityserver-blogs-components-weblogfiles/00-00-00-20-66/siggraph2015_2D00_mmg_2D00_marius_2D00_slides.pdf) | Introduces "dual filtering" (dual Kawase): 5-tap down / 8-tap up across a half-res chain. Cheapest wide, smooth blur; trivially ps_2_0. |
| 2010 | Daniel Rakos, "Efficient Gaussian blur with linear sampling" | [blog](https://www.rastergrid.com/blog/2010/09/efficient-gaussian-blur-with-linear-sampling/) | Halve the taps of a separable Gaussian using bilinear filtering - fits ps_2_0's 32-tex limit. |
| 2022 | LearnOpenGL, "Physically Based Bloom" (guest article) | [article](https://learnopengl.com/Guest-Articles/2022/Phys.-Based-Bloom) | Clean, readable walk-through of the Jimenez 2014 bloom with code - best porting reference. |

### Tonemapping
| Year | Work | Link | Why |
|---|---|---|---|
| 2002 | Reinhard et al., "Photographic Tone Reproduction for Digital Images" | [pdf](https://www-old.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf) | Source of Reinhard and *extended* Reinhard (white point) - simplest shoulder for bloom composite. |
| 2010 | John Hable, "Uncharted 2: HDR Lighting", GDC 2010 | [GDC Vault](https://gdcvault.com/play/1012459/Uncharted_2__HDR_Lighting), [slides mirror](https://www.slideshare.net/ozlael/hable-john-uncharted2-hdr-lighting), [blog: Filmic Tonemapping Operators](https://filmicworlds.com/blog/filmic-tonemapping-operators/) | The "Uncharted 2" filmic curve; also a clear explanation of linear-vs-gamma and SSAO. Few ALU ops. |
| 2017 | Hable, "Filmic Tonemapping with Piecewise Power Curves" + "Minimal Color Grading Tools" | [curves](https://filmicworlds.com/blog/filmic-tonemapping-with-piecewise-power-curves/), [grading](https://filmicworlds.com/blog/minimal-color-grading-tools/) | Artist-friendly curve (toe/shoulder params) and a minimal grading toolset - a good model for our config UI. Code is CC0 (below). |
| 2016 | Krzysztof Narkowicz, "ACES Filmic Tone Mapping Curve" | [blog](https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/) | 5-constant rational fit of ACES - one line of HLSL. Oversaturates/hue-shifts brights; fine as a "punchy" option. |
| 2016 | Timothy Lottes, "Advanced Techniques and Optimization of HDR Color Pipelines", GDC 2016 | [pdf](https://gpuopen.com/wp-content/uploads/2016/03/GdcVdrLottes.pdf) | Parametric tonemapper with explicit contrast/shoulder, plus notes on hue preservation and dithering. |
| 2017 | Alex Fry, "High Dynamic Range Color Grading and Display in Frostbite", GDC 2017 | [slides](https://www.slideshare.net/DICEStudio/high-dynamic-range-color-grading-and-display-in-frostbite) | Why grade in a log/LUT space before display mapping; hue-preserving display mapping. |
| 2019 | Matt Taylor, "Tone Mapping" | [blog](https://64.github.io/tonemapping/) | Best single survey with code: Reinhard, extended Reinhard, luminance-only variants, Hable, ACES fits. |
| 2021 | Jasmin Patry, "Real-Time Samurai Cinema" (Ghost of Tsushima), SIGGRAPH Advances | [page](https://advances.realtimerendering.com/s2021/jpatry_advances2021/index.html) | Modern, tasteful filmic tonemapping/grading from an art-directed game; also bloom/glare. |
| 2023 | AgX (Troy Sobotka) + "Minimal AgX implementation" (Iolite) | [AgX repo](https://github.com/sobotka/AgX), [minimal impl](https://iolite-engine.com/blog_posts/minimal_agx_implementation) | AgX desaturates highlights gracefully (no "neon" ACES hue skew). The Iolite polynomial fit is ~20 ALU, fits ps_2_b. |
| 2024 | Khronos PBR Neutral tonemapper | [repo](https://github.com/KhronosGroup/ToneMapping), [comparison](https://modelviewer.dev/examples/tone-mapping) | Keeps base colours accurate, only compresses highlights - the most "invisible" option for a bloom composite. |

### Color grading with LUTs
| Year | Work | Link | Why |
|---|---|---|---|
| 2005 | Selan, "Using Lookup Tables to Accelerate Color Transformations", GPU Gems 2 ch. 24 | [chapter](https://developer.nvidia.com/gpugems/gpugems2/part-iii-high-quality-rendering/chapter-24-using-lookup-tables-accelerate-color) | The canonical 3D-LUT-on-GPU reference, same era as our game. 3D (volume) textures work in ps_2_0; or a 2D strip with a manual slice lerp. |
| current | Unreal Engine docs, "Color Grading and the Filmic Tonemapper" | [docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/color-grading-and-the-filmic-tonemapper-in-unreal-engine) | Practical artist workflow: screenshot + neutral LUT -> grade in an image editor -> load LUT. Exactly the workflow we want. |

### Sharpening
| Year | Work | Link | Why |
|---|---|---|---|
| 2019 | AMD FidelityFX Contrast Adaptive Sharpening (CAS) | [GPUOpen page](https://gpuopen.com/fidelityfx-cas/) | 3x3 adaptive sharpen that limits itself near high contrast - no halos/ringing, unlike unsharp mask. ~9 taps, fits ps_2_b/ps_3_0. |
| 2021 | AMD FSR 1 (EASU + RCAS) | [GPUOpen page](https://gpuopen.com/fidelityfx-superresolution/) | RCAS is a lighter, sharper successor to CAS; worth A/B testing. |

### Anti-aliasing usable as post
| Year | Work | Link | Why |
|---|---|---|---|
| 2009/2011 | Timothy Lottes, FXAA white paper (NVIDIA); FXAA 3.11 source | [white paper](https://developer.download.nvidia.com/assets/gamedev/files/sdk/11/FXAA_WhitePaper.pdf) | Single pass, colour only, has an official `FXAA_HLSL_3` path. Softens textures somewhat. |
| 2012 | Jimenez, Echevarria, Sousa, Gutierrez, "SMAA: Enhanced Subpixel Morphological Antialiasing", Eurographics 2012 | [project page](https://www.iryoku.com/smaa/), [paper pdf](https://www.iryoku.com/smaa/downloads/SMAA-Enhanced-Subpixel-Morphological-Antialiasing.pdf) | 3 passes (edges, blend weights, blend), colour/luma edge detection, sharper than FXAA. Official `SMAA_HLSL_3` (D3D9) path. Best AA quality we can get without depth. |
| 2016 | Jimenez, "Filmic SMAA: Sharp Morphological and Temporal Antialiasing", SIGGRAPH Advances | [pptx](https://advances.realtimerendering.com/s2016/Filmic%20SMAA%20v7.pptx) | Improvements to SMAA 1x edge handling; temporal part needs velocity (skip). |
| 2018 | Strugar & Lake (Intel), "Conservative Morphological Anti-Aliasing 2.0" | [article](https://www.intel.com/content/www/us/en/developer/articles/technical/conservative-morphological-anti-aliasing-20.html) (403 to scripts, exists), [code](https://github.com/GameTechDev/CMAA2) | Preserves sharpness best, but CMAA2 is a DX11 **compute** shader - not portable to SM3. Reference only. |

### Film grain, chromatic aberration, lens effects
| Year | Work | Link | Why |
|---|---|---|---|
| 2016 | Mikkel Gjoel & Mikkel Svendsen, "Low Complexity, High Fidelity - INSIDE Rendering", GDC 2016 | [GDC Vault](https://www.gdcvault.com/play/1023002/Low-Complexity-High-Fidelity-INSIDE), [slides pdf](https://loopit.dk/rendering_inside.pdf) | Tasteful bloom, film grain, chromatic aberration and dithering used as one cohesive look - the best "taste" reference here. |
| 2013 | John Chapman, "Pseudo Lens Flare" | [blog](https://john-chapman-graphics.blogspot.com/2013/02/pseudo-lens-flare.html) | Ghosts + halo + lens dirt generated purely from a bright-pass of the colour buffer - no depth needed. Use very subtly. |
| 2017 | Newson, Delon, Galerne, "Realistic Film Grain Rendering", IPOL | [article](https://www.ipol.im/pub/art/2017/192/) | Physically based grain model; too heavy for runtime, but useful for what real grain looks like (luminance dependent, finer in highlights). |
| 2007 | Mitchell, "Volumetric Light Scattering as a Post-Process", GPU Gems 3 ch. 13 | [chapter](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process) | God rays by radial blur from the sun's screen position. Properly needs an occlusion mask (depth); a bright-pass-only version works on skies but leaks onto bright surfaces. |

### Dithering / banding
| Year | Work | Link | Why |
|---|---|---|---|
| 2016 | Mikkel Gjoel, "Banding in Games: A Noisy Rant" | [pdf](https://loopit.dk/banding_in_games.pdf) | The reference: triangular-PDF noise at +/-1 LSB before quantization removes banding invisibly. Must-do since we go through 8-bit RTs. |
| 2016 | Bart Wronski, "Dithering part three - real world 2D quantization dithering" | [blog](https://bartwronski.com/2016/10/30/dithering-part-three-real-world-2d-quantization-dithering/) | Compares white/blue/ordered noise for 8-bit output with images. |
| 2016 | Christoph Peters, "Free blue noise textures" | [page](https://momentsingraphics.de/BlueNoise.html) | CC0 blue-noise textures - drop-in source for dither and grain (a texture fetch is cheaper than hash noise on ps_2_0). |

### Depth of field and SSAO (need depth - wait)
| Year | Work | Link | Notes |
|---|---|---|---|
| 2004 | Demers, "Depth of Field: A Survey of Techniques", GPU Gems 1 ch. 23 | [chapter](https://developer.nvidia.com/gpugems/gpugems/part-iv-image-processing/chapter-23-depth-field-survey-techniques) | SM2-era techniques. **Needs depth.** |
| 2007 | Earl Hammon, "Practical Post-Process Depth of Field", GPU Gems 3 ch. 28 | [chapter](https://developer.nvidia.com/gpugems/gpugems3/part-iv-image-effects/chapter-28-practical-post-process-depth-field) | Shipped in Call of Duty 4, SM3-era budget. **Needs depth.** |
| 2018 | Dennis Gustafsson, "Bokeh depth of field in a single pass" | [blog](https://blog.voxagon.se/2018/05/04/bokeh-depth-of-field-in-single-pass.html) | Very pretty, short, but loops many taps -> ps_3_0 only. **Needs depth.** |
| 2008 | Bavoil & Sainz, "Image-Space Horizon-Based Ambient Occlusion" (HBAO), SIGGRAPH 2008 | [pdf](https://developer.download.nvidia.com/presentations/2008/SIGGRAPH/HBAO_SIG08b.pdf) | **Needs depth** (normals reconstructable from depth). |
| 2007 | Shanmugam/Bavoil et al., "High-Quality Ambient Occlusion", GPU Gems 3 ch. 12 | [chapter](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-12-high-quality-ambient-occlusion) | **Needs depth.** |
| 2016 | Jimenez, Wu, Pesce, Jarabo, "Practical Realtime Strategies for Accurate Indirect Occlusion" (GTAO) | [pdf](https://www.iryoku.com/downloads/Practical-Realtime-Strategies-for-Accurate-Indirect-Occlusion.pdf) | Current best-practice SSAO. **Needs depth.** Plausible on ps_3_0 at half res. |

---

## 2. Open-source implementations

Licence key: **OK** = permissive (MIT/BSD/Apache/zlib/CC0), safe to port and ship with credit.
**SA** = share-alike (GPL, CC BY-SA) - shippable in a non-commercial mod if our shader source is released under the same licence.
**Study only** = all-rights-reserved or restrictive; read for ideas, write our own code.

Porting note: ReShade FX compiles to SM3 HLSL for its D3D9 backend, so anything that runs in ReShade on a
D3D9 game is in principle portable to our ps_3_0 path (strip the FX annotations, write the pass setup in the wrapper).

### Shader collections
| Repo | Licence | What's useful | Depth? |
|---|---|---|---|
| [CeeJayDK/SweetFX](https://github.com/CeeJayDK/SweetFX) | **MIT** (repo); FXAA/SMAA files keep their own headers | Tiny, readable SM3-friendly shaders: [LumaSharpen](https://github.com/CeeJayDK/SweetFX/blob/master/Shaders/SweetFX/LumaSharpen.fx), [CAS.fx port](https://github.com/CeeJayDK/SweetFX/blob/master/Shaders/SweetFX/CAS.fx), FilmGrain, ChromaticAberration, Vibrance, LiftGammaGain, Curves, Tonemap, Vignette, FXAA.fx, SMAA.fx. **Best first port source.** | No |
| [prod80/prod80-ReShade-Repository](https://github.com/prod80/prod80-ReShade-Repository) | **MIT** | Pro-grade grading suite: [Bloom](https://github.com/prod80/prod80-ReShade-Repository/blob/master/Shaders/PD80_02_Bloom.fx), Filmic Adaptation, Curved Levels, Shadows/Midtones/Highlights, Selective Color, Color Temperature, Film Grain, Chromatic Aberration, Sharpening, **LUT Creator** + LUT packs, blend-mode and colour-space helpers. Good model for tasteful defaults. | No (except Depth Slicer) |
| [crosire/reshade-shaders](https://github.com/crosire/reshade-shaders) (`slim` branch) | No repo licence; **per file**. [Deband.fx](https://github.com/crosire/reshade-shaders/blob/slim/Shaders/Deband.fx) = MIT (haasn); [LUT.fx](https://github.com/crosire/reshade-shaders/blob/slim/Shaders/LUT.fx) = "Copyright Marty McFly", no explicit licence (treat as study only, the technique is trivial) | Deband, LUT, TriDither.fxh. The `legacy` branch holds older community shaders with mixed/unclear licences. | No |
| [martymcmodding/qUINT](https://github.com/martymcmodding/qUINT) | **Study only** ("All rights reserved", no licence file) | Excellent bloom, Lightroom-style grading, deband, sharpen; MXAO/SSR/DOF need depth. | Partly |
| [martymcmodding/iMMERSE](https://github.com/martymcmodding/iMMERSE) | **Study only** - custom licence: no redistribution, no use of parts without explicit permission | Modern successor of qUINT (SMAA-like AA, sharpen, MXAO, launchpad). Don't copy code. | Partly |
| [BlueSkyDefender/AstrayFX](https://github.com/BlueSkyDefender/AstrayFX) | No licence (files say so explicitly) - study only | Clarity (local contrast), Smart_Sharp, NFAA, DLAA_Plus, BloomingHDR. | Some |
| [Fubaxiusz/fubax-shaders](https://github.com/Fubaxiusz/fubax-shaders) | Mostly **CC BY-SA 4.0** per file (SA) | Filmic Anamorphic Sharpen, perspective/lens shaders. | Some |
| [LordOfLunacy/Insane-Shaders](https://github.com/LordOfLunacy/Insane-Shaders) | **CC0** | Misc ReShade effects (several need compute/DX10+). | Varies |
| [GarrettGunnell/AcerolaFX](https://github.com/GarrettGunnell/AcerolaFX) / [Post-Processing](https://github.com/GarrettGunnell/Post-Processing) | **MIT** | Well-commented tonemappers, bloom, grading, CA, Kuwahara etc. (AcerolaFX targets ReShade DX10+, so some ports need compute removed). | Some |
| [EndlesslyFlowering/ReShade_HDR_shaders](https://github.com/EndlesslyFlowering/ReShade_HDR_shaders) | GPL-3.0 (SA) | Inverse tonemapping / SDR-to-HDR; useful only if we later output HDR. | No |
| [AlucardDH/dh-reshade-shaders](https://github.com/AlucardDH/dh-reshade-shaders) | GPL-2.0 (SA) | Mostly depth-based GI/AO. | Yes |
| [Mortalitas/GShade-Shaders](https://github.com/Mortalitas/GShade-Shaders) | No licence; GShade history is messy - avoid | - | - |

### Specific algorithms
| Repo | Licence | What | Depth? |
|---|---|---|---|
| [iryoku/smaa](https://github.com/iryoku/smaa) ([SMAA.hlsl](https://github.com/iryoku/smaa/blob/master/SMAA.hlsl)) | **MIT** | Reference SMAA with `SMAA_HLSL_3` (D3D9) path; ship AreaTex/SearchTex as textures. Use luma/colour edge detection. | No (depth edge mode optional) |
| FXAA 3.11 - e.g. [gist mirror](https://gist.github.com/kosua20/0c506b81b3812ac900048059d2383126), also in [CMAA2 repo](https://github.com/GameTechDev/CMAA2/blob/master/Projects/CMAA2/FXAA/Fxaa3_11.h) and SweetFX | NVIDIA copyright with permissive disclaimer; redistributed freely for a decade (SweetFX, Unity, Godot) | Single header, `FXAA_HLSL_3` path, needs luma in alpha. | No |
| [GPUOpen-Effects/FidelityFX-CAS](https://github.com/GPUOpen-Effects/FidelityFX-CAS) | **MIT** | Reference CAS (`ffx_cas.h`); SweetFX's CAS.fx shows the SM3-friendly reduction. | No |
| [GPUOpen-Effects/FidelityFX-FSR](https://github.com/GPUOpen-Effects/FidelityFX-FSR) | **MIT** | FSR1 RCAS sharpener (can be used alone, no upscale). | No |
| [GameTechDev/CMAA2](https://github.com/GameTechDev/CMAA2) | Apache-2.0 | Compute only - not portable to SM3. | No |
| [keijiro/KinoBloom](https://github.com/keijiro/KinoBloom) | **MIT** | Small, clean mip-chain bloom (Unity, but the shader is plain HLSL/Cg). | No |
| [JujuAdams/Kawase](https://github.com/JujuAdams/Kawase), [Baedrick/Dual-Kawase-Blur-Demo](https://github.com/Baedrick/Dual-Kawase-Blur-Demo) | **MIT** | Dual Kawase (Bjorge 2015) implementations. | No |
| [butterw/bShaders](https://github.com/butterw/bShaders) | No licence stated | **ps_2_0/ps_3_0 HLSL for MPC-HC** incl. dual Kawase blur - closest to our target profile; study only. | No |
| [alex47/Dual-Kawase-Blur](https://github.com/alex47/Dual-Kawase-Blur) | GPL-3.0 (SA) | OpenGL/Qt dual Kawase. | No |
| [TheRealMJP/BakingLab](https://github.com/TheRealMJP/BakingLab) ([ACES.hlsl](https://github.com/TheRealMJP/BakingLab/blob/master/BakingLab/ACES.hlsl)) | **MIT** | Stephen Hill's more accurate ACES RRT+ODT fit in HLSL. | No |
| [johnhable/fw-public](https://github.com/johnhable/fw-public) | **CC0** | Hable's piecewise filmic curve source. | No |
| [KhronosGroup/ToneMapping](https://github.com/KhronosGroup/ToneMapping) | Apache-2.0 | PBR Neutral reference code. | No |
| [h3r2tic/tony-mc-mapface](https://github.com/h3r2tic/tony-mc-mapface) | Apache-2.0 (LUT may carry its own terms - check) | Tonemapper shipped as a 48^3 3D LUT (dds) - load as a volume texture, one fetch. | No |
| [sobotka/AgX](https://github.com/sobotka/AgX) | No licence file (OCIO config + LUTs) | AgX reference; use the Iolite polynomial fit for runtime. | No |
| [mrdoob/three.js tonemapping chunk](https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderChunk/tonemapping_pars_fragment.glsl.js) | **MIT** | Compact, maintained GLSL for Reinhard, Cineon, ACES, AgX, Neutral - trivial to transliterate to HLSL. | No |
| [Unity-Technologies/PostProcessing](https://github.com/Unity-Technologies/PostProcessing) (v2) | Unity Companion License (only for Unity-dependent projects) - **study only** | Very readable bloom/grain/LUT/AutoExposure shaders. | Some |
| [libretro/glsl-shaders](https://github.com/libretro/glsl-shaders), [slang-shaders](https://github.com/libretro/slang-shaders) | Per-shader (mixed GPL/public domain/MIT) | Huge library of scalers, CRT, NTSC, film effects - single-pass and old-hardware friendly. | No |

### Wrappers / tools for old D3D8/D3D9 games
| Project | Licence | Notes |
|---|---|---|
| [crosire/d3d8to9](https://github.com/crosire/d3d8to9) | **BSD-2-Clause** | D3D8 -> D3D9 translation layer (what our wrapper is / builds on). |
| [crosire/reshade](https://github.com/crosire/reshade) | BSD-3-Clause | The injector itself; can sit on top of d3d8to9 and gives depth-buffer heuristics for D3D9 - a ready path if we want to test depth effects before building our own depth access. |
| [elishacloud/dxwrapper](https://github.com/elishacloud/dxwrapper) | zlib (+ third-party notices incl. d3d8to9) | Bundles d3d8to9, ddraw fixes, and many compatibility hacks; good for reading how others hook old D3D. |
| [dege-diosg/dgVoodoo2](https://github.com/dege-diosg/dgVoodoo2) | Closed-source freeware (repo is releases/issues only) | D3D8/9 -> D3D11/12; forces MSAA/resolution, works with ReShade. Not a code source. |
| [doitsujin/dxvk](https://github.com/doitsujin/dxvk) | zlib | D3D8/9 -> Vulkan (includes a d3d8 frontend since 2.4); vkBasalt can then run CAS/SMAA. |
| [ENBSeries](https://enbdev.com/) | Closed-source freeware | The classic D3D8/D3D9 wrapper-with-post approach; good for ideas only. |
| [Blinue/Magpie](https://github.com/Blinue/Magpie) | GPL-3.0 | Windowed upscaler with many ported effects (FSR, CAS, CRT); HLSL sources useful to study. |

---

## 3. Recommendation (color-only, ps_2_x / ps_3_0)

Priority by visual win per hour of work:

1. **SMAA 1x (luma edge detection)** - from `iryoku/smaa`, MIT, `SMAA_HLSL_3`. UE2-era geometry is all hard
   edges and the game likely runs without MSAA through the wrapper; this is the biggest single quality jump.
   Fallback: FXAA 3.11 (one pass, ps_3_0) if SMAA's 3 passes are too much plumbing.
2. **Replace our threshold+blur bloom with a mip-chain bloom** (Jimenez 2014 down/upsample, or Bjorge dual
   filter as the cheap version), with a soft-knee threshold and Karis-average first downsample. Port from
   KinoBloom / LearnOpenGL / prod80 bloom (all MIT-compatible). Wide, stable, non-flickery glow.
3. **Linear-space bloom composite + tonemap shoulder** (Khronos PBR Neutral or AgX-fit or Hable piecewise).
   Lets bright bloom roll off to white instead of clipping; keeps midtones untouched. A few ALU.
4. **3D LUT grading** (GPU Gems 2 ch.24; prod80 LUT Creator for the neutral LUT). Bakes our
   saturation/contrast/balance into one texture and lets the user grade in any image editor. One fetch.
5. **CAS sharpening** (FidelityFX-CAS / SweetFX CAS.fx, MIT) replacing a plain unsharp mask - sharper with no halos.
   Run after AA and grading.
6. **Triangular dither (+ optional blue-noise grain)** at the very end (Gjoel 2016; Peters CC0 blue noise).
   Fixes banding from our own 8-bit passes and in the game's dark skies/fog. Nearly free.
7. **Subtle film grain + edge-only chromatic aberration + vignette** (INSIDE talk for taste; SweetFX/prod80 code).
   Luminance-weighted grain, CA scaled by distance from centre. Keep very low.
8. *(optional)* **Pseudo lens flare / lens dirt** (Chapman 2013) driven by the bloom bright-pass - only at low intensity.

**Wait for depth:** depth of field (Hammon GPU Gems 3, Gustafsson bokeh, Jimenez 2014), SSAO (HBAO, GTAO, MXAO),
proper god rays (needs an occlusion mask), fog/atmospheric post, depth-aware SMAA edges, and anything temporal
(TAA, motion blur, Filmic SMAA T2x also needs motion vectors). Once depth is reachable, a half-res GTAO on
ps_3_0 is the highest-value next step, then DOF for cutscenes.

**Licence summary for shipping:** SweetFX, prod80, SMAA, FidelityFX CAS/FSR, KinoBloom, BakingLab, three.js,
Khronos, fw-public, d3d8to9 are all safe to port with credit. qUINT, iMMERSE, AstrayFX, butterw, LUT.fx: study only,
write our own. GPL / CC BY-SA sources (Fubax, AlucardDH, Magpie, alex47) are fine for a non-commercial mod only if
we publish our shader source under the same licence.
