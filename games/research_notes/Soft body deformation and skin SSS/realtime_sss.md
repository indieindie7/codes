# Real-time subsurface scattering and translucency for skin, flesh, wax and gore: techniques, costs, and how they could fit a D3D9 wrapper (ps_2_0 / ps_2_a / ps_2_b / ps_3_0)

Target context: Unreal Engine 2 games (Unreal II, Advent Rising). Characters are fixed-function and vertex-lit. A d3d8to9 fork can swap in a ps_2_a or ps_3_0 pixel shader for each texture hash and run a full-screen post chain that can read depth. Per-pixel normals are not available in post unless they are rebuilt from depth.

## Q1. Families of techniques: texture-space diffusion, screen-space separable SSS, Burley/Disney normalized diffusion, sum-of-Gaussians profiles

### Takeaway
- **Texture-space diffusion** (d'Eon & Luebke, GPU Gems 3 ch. 14) is the quality reference. It needs an irradiance texture for each mesh plus 6 separable blurs, and it used most of a GeForce 8800 Ultra. It does not fit our wrapper.
- **Jimenez's screen-space SSS** (2009, then separable in 2012/2015) needs only:
  - the lit colour buffer
  - linear depth
  - a skin mask (stencil or alpha)
  - two 1D blur passes
- That input list matches what our post chain already has, so screen-space separable SSS is the natural fit.
- **Burley/Disney normalized diffusion** (Unity HDRP, Unreal "Burley") is not separable. It needs disk sampling in a compute shader (21–55 samples) and temporal AA, so it is out of reach on D3D9.

### Cited Findings
**Texture-space diffusion (GPU Gems 3 ch. 14)**
- Approximates the 3-layer skin diffusion profile with **six Gaussians**. Uses six separable **7-tap** blurs: "84 texture accesses per output texel instead of the 4,096" for direct convolution — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)
- Stores six convolved irradiance textures. The irradiance texture holds about 4 texels/mm on the face; the red profile spans about 16 mm (64 texels) — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)
- Stretch-correction textures are computed each frame from screen-space derivatives, so deforming meshes are supported — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)
- Specular uses Kelemen/Szirmay-Kalos with a precomputed 512×512 Beckmann texture and F0 = 0.028 (IOR 1.4) — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)
- Translucent shadow maps store depth plus UV and reuse the convolved irradiance textures for ear-style transmission — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)
- Cost: the full system takes "most of the resources of an entire GeForce 8800 Ultra" — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)

**Screen-space SSS (Jimenez 2009)**
- Moves the diffusion from texture space to a screen-space blur. This scales better when several characters are on screen.
- The kernel width is scaled by 1/depth ("the closer the pixel, the stronger the effect").
- The demo shader blurs with a small Gaussian tap set around the pixel.
- Source: [iryoku SSSSS page](https://www.iryoku.com/sssss/) and [paper PDF](https://graphics.unizar.es/papers/Screen-Space-Perceptual-Rendering-of-Human-Skin.pdf)

**Separable SSS (Jimenez et al. 2015, code released 2012)**
- Uses **a single separable kernel** applied as two 1D convolutions.
- Runs in **under 0.5 ms**, needing about 7 samples per pixel with importance sampling and jitter.
- The released demo/code (v1.0, Feb 2012) is from the earlier tech report and does not include the 2015 paper's importance-sampled kernel or artist UI.
- Source: [iryoku separable-sss page](https://www.iryoku.com/separable-sss/)

Code facts, read from `SeparableSSS.h` (repo root) and `Demo/Code/SeparableSSS.cpp` in [github.com/iryoku/separable-sss](https://github.com/iryoku/separable-sss):
- Precomputed kernels ship for **25, 17 and 11 samples**. The demo default is `nSamples=17`.
- Each kernel entry is a `float4`: rgb weight plus offset.
- The kernel range is ±2 for fewer than 20 samples and ±3 otherwise, with offsets spaced by `pow(o,2)`.
- The kernel is built from 5 of the 6 d'Eon Gaussians. Variances: 0.0484, 0.187, 0.567, 1.99, 7.41. Red weights: 0.100, 0.118, 0.113, 0.358, 0.078.
- The narrowest Gaussian (0.0064) is left out of the blur and handled by a per-channel "strength" mix with the unblurred image.
- A per-channel "falloff" vector recolours the gradients.

The blur pixel shader:
- Inputs: point-sampled colour (SSS strength in alpha), point-sampled **linear depth**, `sssWidth` (world units), FOV, and blur direction (1,0) then (0,1).
- Step size: `sssWidth * (1/tan(fov/2)) / depth * strength * dir / 3`.
- It runs a loop of N taps of `colour * kernel.rgb`.
- With `SSSS_FOLLOW_SURFACE=1` it also fetches depth at every tap. When the depth difference is large it lerps back to the centre colour: `saturate(300*dist*sssWidth*|dM-d|)`.
- Masking: either a stencil `id` (only marked pixels are processed in both passes), or `discard` on alpha==0 in the first pass to build the stencil for the second.
- Render targets must not be multisampled.
- Source: [separable-sss SeparableSSS.h](https://github.com/iryoku/separable-sss/blob/master/SeparableSSS.h)

D3D9 path:
- The header has a ready **`SSSS_HLSL_3`** path that uses `tex2D`/`tex2Dlod`, so it targets **ps_3_0**. It also has HLSL_4 and GLSL_3 paths. The demo itself is D3D10 (ps_4_0) — [SeparableSSS.h](https://github.com/iryoku/separable-sss/blob/master/SeparableSSS.h); [Demo/Shaders/SeparableSSS.fx](https://github.com/iryoku/separable-sss/blob/master/Demo/Shaders/SeparableSSS.fx)

**Burley normalized diffusion (Unity HDRP, Golubev, SIGGRAPH 2018)**
- Unity implemented Burley's normalized diffusion ("Disney SSS"). It has two parameters, volume albedo A and shape s, and s is exposed as scattering distance.
- The profile's sharp peak and long tail "cannot be modeled with a single Gaussian", and the filter "is clearly non-separable".
- The profile is normalized, so it can serve directly as a PDF for importance sampling.
- Sampling: precomputed importance-sampled radial distances with Fibonacci-distributed angles on a disk, bilateral re-weighting, and random per-pixel rotation.
- Runs as a full-screen **compute shader** using LDS.
- Sample count by footprint: none for sub-pixel disks, **21** for medium, **55** otherwise. **PS4 uses 21: 1.16 ms**, including the merge of diffuse and specular.
- Source: [Golubev, Efficient Screen-Space SSS Using Burley's Normalized Diffusion (SIGGRAPH 2018 Advances)](https://www.advances.realtimerendering.com/s2018/Efficient%20screen%20space%20subsurface%20scattering%20Siggraph%202018.pdf)
- HDRP docs describe a screen-space blur driven by diffusion profiles. Earlier HDRP versions used "a linear combination of two normalized 1D Gaussians as suggested by Jimenez et al." — [Unity HDRP SSS docs](https://docs.unity3d.com/Packages/hdrp/manual/Subsurface-Scattering.html)

**Unreal Engine "Burley" profile**
- A checkbox in the Subsurface Profile asset. Parameters: MeanFreePathColor and MeanFreePathDistance (cm), plus FalloffColor.
- Aims for a "cleaner, more accurate fall off" than the older separable SSS.
- **Requires Temporal AA to display properly.**
- Source: [UE Subsurface Profile docs](https://docs.unrealengine.com/4.26/RenderingAndGraphics/Materials/LightingModels/SubSurfaceProfile); [SubsurfaceProfileStruct](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SubsurfaceProfileStruct)

**Godot 4 SSS**
- A compute shader (`subsurface_scattering.glsl`) with 11/17/25-sample variants and a hard-coded `skin_kernel`. The layout and sample counts match Jimenez's separable kernels.
- Reads `source_image` plus `source_depth` and stops at pixels whose alpha is about 0.
- Godot is MIT-licensed, but this is a Vulkan compute shader, so it would have to be ported.
- Source: [godot subsurface_scattering.glsl](https://github.com/godotengine/godot/blob/master/servers/rendering/renderer_rd/shaders/effects/subsurface_scattering.glsl)

**Activision**
- Jimenez's GDC 2013 "Next-Generation Character Rendering" talk covered SSS, eyes, AA, DoF and film grain. Slides are on iryoku.com and GDC Vault — [GDC Vault](https://gdcvault.com/play/1018270/Next-Generation-Character); [iryoku](https://www.iryoku.com/?p=1595)

### Inferences
**Best fit for the wrapper: Jimenez separable SSS as a post pass**
- It needs only colour, linear depth, a mask and the FOV.
- No per-pixel normals, no light direction and no shadow maps are needed for the diffuse blur. Every lit pixel is blurred, so it works even on vertex-lit characters.
- Cost: 2 full-screen passes, limited by stencil to skin pixels.
  - Without follow-surface: N colour reads per pass.
  - With follow-surface: 2N reads (colour plus depth).

**Fit against D3D9 shader limits**
- 17 taps with follow-surface is about 34 texture reads and about 70–90 ALU per pass.
- **ps_2_0** (96 slots: 64 ALU + 32 tex) cannot run 17-tap follow-surface. 11 taps without follow-surface (11 tex reads) fits.
- **ps_2_a / ps_2_b** (512 slots) fit 17 or 25 taps with follow-surface. Loops must be unrolled.
- **ps_3_0** fits everything. The ready `SSSS_HLSL_3` path compiles nearly as-is if the D3D10 stencil-init `discard` trick is replaced with D3D9 stencil or alpha test.

**Getting linear depth**
- The post chain has a readable depth surface (likely INTZ or similar).
- Linear depth has to be reconstructed from the projection (near/far), because the shader expects linear depth.
- `sssWidth` must be converted to UE2 units: 1 UU ≈ 1.9 cm in UT-scale content (an assumption; verify for Unreal II and Advent Rising).

**Building the skin mask**
- When a skin, flesh or gore texture hash is bound, the per-texture replacement shader writes SSS strength into **alpha** of the backbuffer. Alternatively the wrapper sets a stencil ref.
- Both are simple because the wrapper already intercepts texture binds.
- Caveat: UE2 may use framebuffer alpha for other things (translucency, fog). A stencil reference set by the wrapper during skin draws is safer, if the depth/stencil format has stencil bits.

**Specular separation**
- Jimenez's design blurs diffuse only.
- In a fixed-function game, specular is usually absent or baked into vertex colour, so blurring the whole lit colour is acceptable.
- Rim or specular added by our own replacement shader should be added **after** the SSS pass or written to a separate target. In practice, add it in a cheap pass afterwards, or accept slight blurring.

**Burley and texture-space diffusion are out of reach**
- Burley: compute shader, many samples, temporal AA.
- Texture-space diffusion: needs render-to-UV-space of each mesh, which the wrapper cannot easily do with UE2's vertex-lit fixed-function draw calls.

### Gaps
- No ms figures were found for the 2012 code at 17 taps on D3D9-class GPUs. The only figure is the "<0.5 ms" claim from the 2015 paper (modern GPU, 7 importance-sampled taps).
- The GDC 2013 Activision slides were not opened, so their cost figures are not recorded here.

## Q2. Pre-integrated skin shading (Penner & Borshukov, GPU Pro 2 / SIGGRAPH 2011)

### Takeaway
- Pre-integrated skin is a **single-pass pixel-shader** technique.
- It uses a 2D LUT indexed by (N·L, curvature 1/r), plus blurred normals for small detail and a shadow-penumbra LUT. There are no blur passes.
- It needs per-pixel N·L and curvature (from `ddx`/`ddy` or a baked texture). Gradient instructions mean **ps_2_a or ps_3_0**; ps_2_b has no gradients.
- Our characters are vertex-lit and have no per-pixel normals. A faithful version would need the wrapper to supply light constants and an interpolated normal. A cheap "fake" can drive the LUT with vertex-lighting luminance.

### Cited Findings
- Penner & Borshukov, "Pre-Integrated Skin Shading", GPU Pro 2 (A K Peters, 2011), pp. 41–55; talk at SIGGRAPH 2011 Advances in Real-Time Rendering — [Game Engine Gems DB](https://gameenginegems.com/gemsdb/article.php?id=1103); [SlideShare slides](https://www.slideshare.net/slideshow/penner-preintegrated-skin-rendering-siggraph-2011-advances-in-realtime-rendering-course/13966747)
- Three parts: scattering due to curvature, scattering on small details (bump map), and scattering in shadow falloff — [lousodrome reading list](https://lousodrome.net/blog/light/2012/11/05/reading-list-on-skin-rendering/); [SlideShare](https://www.slideshare.net/slideshow/penner-preintegrated-skin-rendering-siggraph-2011-advances-in-realtime-rendering-course/13966747)
- Design goal: a simple pixel shader whose inputs all live locally in texture or bump maps, with **no blur passes** — [SlideShare](https://www.slideshare.net/slideshow/penner-preintegrated-skin-rendering-siggraph-2011-advances-in-realtime-rendering-course/13966747)
- LUT axes are N·L and 1/d (curvature), so "the falloff at the nose [can] differ from that in the forehead" — [Game Developer, In-depth skin shading in Unity3D](https://www.gamedeveloper.com/programming/in-depth-skin-shading-in-unity3d)
- Curvature from derivatives, in a typical implementation: `curvature = saturate(length(fwidth(N))) / (length(fwidth(worldPos)) * tune)`. It needs `ddx`/`ddy` — [Game Developer](https://www.gamedeveloper.com/programming/in-depth-skin-shading-in-unity3d)
- Detail scattering: instead of separate R/G/B normal maps, the normal map is sampled with a **mip/LOD bias** (about 3) for the softer diffuse channels, while specular keeps the sharp normal — [Game Developer](https://www.gamedeveloper.com/programming/in-depth-skin-shading-in-unity3d)
- The same article notes that texture-space diffusion has "a serious limitation" as a per-mesh cost, and that screen-space approaches are cheaper but still "reasonably expensive" — [Game Developer](https://www.gamedeveloper.com/programming/in-depth-skin-shading-in-unity3d)
- LUT generators on GitHub: [codewings/PreIntegrated-Skin](https://github.com/codewings/PreIntegrated-Skin) (66★), [Nuomi-Chobits/Unity-URP-SkinSSSLUTGenerator](https://github.com/Nuomi-Chobits/Unity-URP-SkinSSSLUTGenerator) (72★), [XINWUYA/Pre-IntegratedSkinLUT](https://github.com/XINWUYA/Pre-IntegratedSkinLUT) (Python), [LiangYue1981816/PreIntegratedSkinTextureTool](https://github.com/LiangYue1981816/PreIntegratedSkinTextureTool), [faiguago/PI_SS](https://github.com/faiguago/PI_SS). **All of them show no licence in GitHub metadata** (checked with `gh search repos`, Oct 2026).

### Inferences
**The LUT integral**
- From the GPU Pro 2 chapter, as recalled; check against the book or slides before relying on it.
- Each LUT texel (θ, r) is a ring integral of the diffusion profile R around a circle of radius r:
  - D(θ, r) = ∫ cos(θ+x)·R(2r·sin(x/2)) dx / ∫ R(2r·sin(x/2)) dx, over x from −π to π
  - cos is clamped to ≥ 0. R is the d'Eon 6-Gaussian skin profile.
- The Gaussian variances and RGB weights are published in GPU Gems 3 and repeated in Jimenez's `SSSSTransmittance` code (see Q4). Generating our own LUT from those published constants means **we need no unlicensed repo**. A ~30-line Python script can write a 256×256 PNG.

**Fit inside the wrapper**
- The LUT read is one dependent texture fetch. The whole shader is about 20–40 instructions.
- Curvature from `ddx`/`ddy` needs **ps_2_a** (gradient instructions are optional caps in ps_2_x) or ps_3_0. Otherwise bake a per-texture curvature map, or use a constant curvature per material.
- The fixed-function vertex stage gives the pixel shader only the interpolated diffuse colour (vertex lighting already summed), not N or L.
- Option (a), cheapest: replace the per-texture pixel shader with `lum = luminance(vertexDiffuse)` → `LUT(lum, constCurvature)` × albedo. This reddens the terminator, but it is a heuristic: vertex lighting has already clamped N·L and summed several lights.
- Option (b), faithful: the wrapper replaces the vertex shader too (or uses a programmable VS emulating UE2's transform), passes normal and light vectors from the intercepted `SetLight` and `SetTransform`, and does per-pixel lighting. This is a much bigger project.

**What it looks like**
- The pre-integrated look is mostly a red-shifted, softened terminator.
- That is almost exactly what Valve's hand-painted lightwarp ramp does (Q3). The cheap path is therefore one shared "skin ramp" texture.

### Gaps
- The original GPU Pro 2 chapter text, equations and its exact shadow-penumbra LUT were not accessed. The SIGGRAPH slides' text could not be fetched.
- No permissively licensed (MIT/BSD/GPL) LUT generator was found. Recommended path: write our own from the published Gaussian constants.

## Q3. Wrap lighting and Valve/Source skin (Half-Lambert, $lightwarptexture, Phong Fresnel, rim)

### Takeaway
- Valve's "soft" skin comes from five ingredients:
  - **Half-Lambert**: (0.5·N·L + 0.5)², which keeps shape on the dark side
  - a 1D **warp ramp** indexed by the Half-Lambert value, often with a reddish band at the terminator and overbright ×2
  - an **ambient cube**
  - **Phong with an artist Fresnel**
  - a broad, masked **rim light** using fr = (1 − N·V)⁴
- These are the cheapest skin-like techniques and run in ps_2_0. With vertex lighting, the warp can be applied to a luminance proxy.

### Cited Findings
**Half-Lambert (Mitchell, Francke & Eng, NPAR 2007)**
- Since Half-Life (1998), Valve scales N·L by 0.5, biases by 0.5 and squares it (α=0.5, β=0.5, γ=2). This "prevent[s] characters from losing a sense of shape on the back side". Valve does it even in photoreal games.
- In TF2, γ is set to 1 because the warp texture supplies the shaping.
- Source: [Mitchell et al., Illustrative Rendering in Team Fortress 2 (NPAR 2007)](https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf)

**Warp function w()**
- A 1D texture lookup that maps the 0..1 Half-Lambert value to RGB.
- The shader multiplies by 2 after the lookup, so artists can paint "up to two times overbright".
- A typical ramp has a greyscale gradient, a cool shadow region and "a small reddish terminator region". This matches the observation of "a slight reddening at the terminator".
- Source: [same paper](https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf)

**View-dependent terms**
- The Phong term is multiplied by fs, an artist-tuned Fresnel.
- Rim lobes use a lower exponent k_rim. They are masked by fr (typically (1 − n·v)⁴) and by a rim mask texture kr.
- A dedicated rim term = ambient cube evaluated along the view vector × kr × fr × saturate(n·up). It adds indirect-looking light only on upward-facing normals.
- Source: [same paper](https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf); [NPAR07 slides](https://cdn.fastly.steamstatic.com/apps/valve/2007/NPAR07_IllustrativeRenderingInTeamFortress2_Slides.pdf); [GDC 2008 Stylization With A Purpose](https://cdn.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf)

**Source engine parameters**
- `$phong` is a VertexLitGeneric parameter in all Source games since Source 2006. It "provides Alyx's skin, hairband and lip highlights" — [VDC $phong](https://developer.valvesoftware.com/wiki/$phong)
- `$phongfresnelranges` defaults to `[0 0.5 1]`, the Fresnel at grazing, mid and facing angles. It also drives the x coordinate of a `$phongwarptexture` — [VDC](https://developer.valvesoftware.com/wiki/$phong)
- `$lightwarptexture` requires `$phong`. A `$phongboost 0` is used to enable lightwarp without visible phong — [VDC $phongboost](https://developer.valvesoftware.com/wiki/$phongboost)

### Inferences
**Why it reads as soft**
- Half-Lambert moves the shadow terminator around to the back. The ramp then paints in a red-orange band where light is grazing.
- This imitates the light bleeding that SSS produces at the terminator, which is the same thing Penner's LUT does at high curvature.
- The Fresnel rim adds a backlit, translucent edge.

**Fit with vertex lighting**
- UE2 fixed-function computes clamped Lambert per vertex, so true Half-Lambert cannot be recovered in the pixel shader.
- Proxy: pass vertex diffuse luminance through a ramp texture painted to lift dark values with a warm band. This is about 4–6 instructions plus one dependent texture read and fits **ps_2_0**.
- Real Half-Lambert and rim need a per-pixel or per-vertex normal plus light and view vectors. That requires a custom vertex shader, or rim approximated in post from depth-reconstructed normals.

**Rim in post**
- A screen-space rim on masked skin pixels can be built from the depth-derived normal: (1 − |n_view.z|)⁴ × mask × ambient tint.
- Depth-reconstructed normals are faceted on low-poly UE2 meshes. Blurring them, or using the depth-gradient magnitude only near silhouettes, may be needed.

**Wax and gore**
- The same ramp idea works for wax (strong warm band, low contrast) and gore/flesh (deep red band, high specular).
- Per-texture ramps chosen by texture hash are a natural fit for the wrapper's per-texture shader rules.

### Gaps
- Valve Developer Community pages for `$lightwarptexture` and `$rimlight` were blocked: 403, then an Anubis bot challenge. Their exact wording, shader-model requirements, and the list of games that ship lightwarp (L4D, Dota 2, HL2 episodes) are unverified here.
- No source found describing Dota 2's skin specifically.

## Q4. Translucency and transmission: DICE thickness maps and Jimenez shadow-map transmittance

### Takeaway
- DICE/EA's approach (Barré-Brisebois & Bouchard, GDC 2011 / GPU Pro 2) is a cheap per-light term from three inputs:
  - a pre-baked **local thickness map** (made by inverted-normal AO)
  - a "distorted" back-light vector
  - power, scale and ambient constants
- It runs on DX9-era consoles and needs no shadow maps.
- Jimenez 2010 instead derives thickness from the **shadow-map depth difference**, then evaluates the 6-Gaussian transmittance profile with a wrapped (0.3 + N·−L).
- Both need per-pixel normal, light direction and view. For our wrapper, a per-texture thickness/translucency mask + light constants from `SetLight` is the realistic route.

### Cited Findings
- "Approximating Translucency for a Fast, Cheap and Convincing Subsurface Scattering Look", Colin Barré-Brisebois, GDC 2011, with Marc Bouchard. The companion article is "Real-Time Approximation of Light Transport in Translucent Homogenous Media" in GPU Pro 2. It is described as fast and scalable on "current and next generation" consoles. Slides plus an addendum are on the author's blog — [EA/Frostbite news (redirect)](https://frostbite.com/frostbite/news/approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look); [author blog post](https://colinbarrebrisebois.com/2011/03/07/gdc-2011-approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look/); [realtimerendering GDC 2011](https://www.realtimerendering.com/blog/tag/gdc-2011/)

**Jimenez, Whelan, Sundstedt & Gutierrez, "Real-Time Realistic Skin Translucency" (IEEE CG&A, July/Aug 2010)**
- Thickness = |shadow-map depth − fragment light-space depth|.
- Vertices are shrunk along the normal (`pos − 0.005·N`) before the shadow lookup to avoid silhouette artifacts.
- Wrapped back-lighting is `max(0.3 + dot(−N, L), 0)`.
- Claimed cost: "no additional memory usage, minimal extra processing power".
- Source: [iryoku translucency page](https://www.iryoku.com/translucency/); [paper PDF](https://graphics.unizar.es/papers/Real-Time-Realistic-Skin-Translucency.pdf)

Transmittance profile, verbatim from `SSSSTransmittance` (BSD-2 code, see Q6), where dd = −s²:

```
profile = float3(0.233,0.455,0.649)*exp(dd/0.0064) + float3(0.1,0.336,0.344)*exp(dd/0.0484)
        + float3(0.118,0.198,0.0)*exp(dd/0.187) + float3(0.113,0.007,0.007)*exp(dd/0.567)
        + float3(0.358,0.004,0.0)*exp(dd/1.99)  + float3(0.078,0.0,0.0)*exp(dd/7.41);
return profile * saturate(0.3 + dot(light, -worldNormal));
```

- The thickness scale is `8.25*(1-translucency)/sssWidth` — [SeparableSSS.h](https://github.com/iryoku/separable-sss/blob/master/SeparableSSS.h)

**Unity HDRP**
- Thin objects: Jimenez's slab model, with constant thickness from an **artist-authored thickness texture** and one shared shadow fetch.
- Thick objects: thickness = **max(shadow-map distance, baked thickness)**, because shadow-map-only thickness "does not work well for fine geometric features due to the limited precision of shadow maps".
- Source: [Golubev 2018](https://www.advances.realtimerendering.com/s2018/Efficient%20screen%20space%20subsurface%20scattering%20Siggraph%202018.pdf)

### Inferences
**DICE formula**
- The widely reproduced DICE formula, recalled and not verified from the slides this session:
  - `H = normalize(L + N*distortion)`
  - `I = pow(saturate(dot(V, -H)), power) * scale`
  - `T = atten * (I + ambient) * thickness`
  - `colour += albedo * lightColour * T`
- That is about 10 ALU and one texture read for the thickness map, so it fits ps_2_0 for 1–2 lights.
- Verify this against the GDC slides before quoting it.

**Thickness map**
- A "local thickness" map is made by baking ambient occlusion with inverted normals and inverting the result.
- It can be baked offline in Blender for each UE2 character texture and bound by the wrapper's per-texture rule as an extra sampler. Thin areas (ears, fingers, nostrils) come out bright.
- The same maps serve Unity-style thin-slab transmission.

**Shadow-map transmittance**
- UE2 has no character shadow maps in the main pass, and the U2 fork's shadow system uses projected shadow textures, not depth maps.
- Jimenez's shadow-map thickness would need a new light-space depth render of characters. That is costly to retrofit, so prefer baked thickness.

**Inputs the wrapper must supply**
- Light direction and colour: available because d3d8to9 intercepts `SetLight`/`LightEnable`. UE2 fixed-function uses D3D lights for actor lighting; this should be verified per game.
- View vector and normal: these require a vertex shader replacement or a post-pass reconstruction.
- Cheapest viable hack: in post, on masked skin pixels, use the depth-reconstructed normal plus one dominant light direction (sun or a key light from constants) for a DICE-style back-light. Modulate by a thickness value the per-texture shader wrote into a spare channel, or by a constant.

### Gaps
- The exact DICE slide formula, instruction counts and platform list were not retrievable: the EA page returned 404 and the blog text lacked the code.
- GPU Pro 2 article text was not accessed.

## Q5. Requirements matrix (inputs, passes, reads, shader model fit)

### Takeaway
Ranked by fit for UE2 through the wrapper:
1. Per-texture ramp/lightwarp on vertex lighting (ps_2_0)
2. Post separable SSS with depth + stencil/alpha mask (ps_2_a/2_b/3_0)
3. Baked-thickness DICE translucency (needs normals; post-reconstructed or custom VS)
4. Pre-integrated LUT (needs per-pixel N·L; ps_2_a+ for curvature)
5. Texture-space diffusion or Burley: not feasible

### Cited Findings
- ps_2_x instruction slots range from 96 to 512 (`MaxPixelShaderInstructionSlots`). Gradient instructions (`dsx`/`dsy`/`texldd`), arbitrary swizzle, predication, no dependent-read limit and no texture-instruction limit are all **optional caps** (D3DPSHADERCAPS2_0). Temp registers range from 12 to 32. There are 16 samplers — [Microsoft Learn ps_2_x](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx9-graphics-reference-asm-ps-2-x)
- Separable SSS: 2 passes; N = 11/17/25 colour taps per pass, plus N depth taps with follow-surface; needs non-MSAA targets, linear depth and stencil or alpha — [SeparableSSS.h](https://github.com/iryoku/separable-sss/blob/master/SeparableSSS.h)
- Texture-space diffusion: 6 irradiance textures × 7-tap separable blurs (84 reads per texel), stretch maps, and optionally translucent shadow maps — [GPU Gems 3 ch.14](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-14-advanced-techniques-realistic-real-time-skin)
- Burley: compute shader with LDS, 21–55 samples, 1.16 ms on PS4 — [Golubev 2018](https://www.advances.realtimerendering.com/s2018/Efficient%20screen%20space%20subsurface%20scattering%20Siggraph%202018.pdf). Unreal's Burley needs temporal AA — [UE docs](https://docs.unrealengine.com/4.26/RenderingAndGraphics/Materials/LightingModels/SubSurfaceProfile)

### Inferences
Summary table (the ps fit and per-game feasibility columns are our estimates):

| Technique | Lighting | Normals | Light dir | Depth | Shadow map | Mask | Passes / reads | Min SM | Wrapper feasibility |
|---|---|---|---|---|---|---|---|---|---|
| Lightwarp ramp on vertex-lit luminance | per-vertex (existing) | no | no | no | no | per-texture rule | 1 / 2 tex | ps_2_0 | Easy; do first |
| Half-Lambert + warp + Fresnel rim (Valve) | per-pixel | yes | yes | no | no | per-texture | 1 / 2–4 tex | ps_2_0 (1–2 lights) | Needs custom VS or normal reconstruction |
| Separable SSS (Jimenez) | any (blurs lit image) | no | no | **linear depth** | no | **stencil or alpha** | 2 full-screen / 11–25 (+depth) per pass | 11-tap: ps_2_0; 17–25 + follow: ps_2_a/2_b; HLSL_3 path: ps_3_0 | Good fit with existing post chain |
| Pre-integrated LUT (Penner) | per-pixel N·L | yes (+blurred) | yes | no | optional (penumbra LUT) | per-texture | 1 / LUT + normal (+mip-biased normal) | ps_2_a (ddx curvature) or ps_2_0 with baked curvature | Only a luminance-proxy hack without VS work |
| DICE thickness translucency | per-pixel | yes | yes | no | no | per-texture | 1 / +1 tex | ps_2_0 | Bake thickness; needs N, L, V |
| Jimenez transmittance | per-pixel | yes | yes | light-space | **yes** | per-texture | +1 shadow read, 6 exp | ps_2_a/3_0 | Poor: no character depth shadow maps |
| Texture-space diffusion | per-pixel in UV space | yes | yes | — | TSM optional | per-mesh | ~13 passes per mesh | ps_3_0 | Not feasible |
| Burley disk (HDRP/UE) | any | (tangent-plane option) | no | yes | for thick transmission | material ID | compute, 21–55 samples, TAA | CS 5.0 | Not feasible on D3D9 |

**Order of work**
1. Per-texture skin, flesh, wax or gore ramp shader that also marks the mask.
2. 11- or 17-tap separable SSS post pass reusing the existing bloom/SSAO chain's depth.
3. Optional back-light from baked thickness, using light constants pulled from `SetLight`.

### Gaps
- The ps_2_0 / ps_2_a / ps_2_b specific limits (ps_2_0 = 64 ALU + 32 tex; ps_2_a = 512 slots with gradients and no texture limit; ps_2_b = 512 slots without gradients) come from general D3D9 knowledge. The fetched MS page lists them only as ranges and caps, so verify against the HLSL profile table.
- Not verified whether UE2's D3D8 renderer uses D3D lights for character lighting or pre-lit vertex colours. This decides whether light vectors are available.

## Q6. Open-source code and licences

### Takeaway
- **Jimenez's separable-sss is BSD-2-Clause plus a required binary attribution line**. It is usable in GPL/non-commercial mods if we include the attribution.
- GPU Gems 3 text is free to read online. No licence for reusing its code was verified.
- Godot (MIT) has a port of the separable kernels.
- Unity HDRP and Unreal source come with licences that rule out copying into a GPL mod.
- No licensed pre-integrated LUT generator was found. Write our own from published constants.

### Cited Findings
**iryoku/separable-sss**
- Copyright (C) 2011/2012 Jorge Jimenez & Diego Gutierrez. BSD-style 2-clause licence.
- Clause 2 requires binary redistributions to reproduce: **"Uses Separable SSS. Copyright (C) 2012 by Jorge Jimenez and Diego Gutierrez."**
- GitHub's licence detector reports `NOASSERTION` because of the custom clause. Last push was 2018-01-18.
- Repo contents: the root `SeparableSSS.h` (portable shader, HLSL3/HLSL4/GLSL3 paths), a D3D10 demo with `Demo/Code/SeparableSSS.cpp` (kernel generation), and `Demo/Shaders/*.fx`.
- Source: [github.com/iryoku/separable-sss](https://github.com/iryoku/separable-sss); [LICENSE](https://github.com/iryoku/separable-sss/blob/master/LICENSE.txt)
- The demo's DXUT folder is Microsoft sample code under its own licence and is not needed — [repo tree](https://github.com/iryoku/separable-sss)

**Other code**
- Translucency (2010) shader on iryoku.com: no explicit licence on the page. The same transmittance function is included in the BSD-2 `SeparableSSS.h` — [iryoku translucency](https://www.iryoku.com/translucency/); [SeparableSSS.h](https://github.com/iryoku/separable-sss/blob/master/SeparableSSS.h)
- Godot engine (MIT) `subsurface_scattering.glsl` with 11/17/25-sample skin kernels — [Godot source](https://github.com/godotengine/godot/blob/master/servers/rendering/renderer_rd/shaders/effects/subsurface_scattering.glsl)
- Pre-integrated LUT repositories (codewings, Nuomi-Chobits, XINWUYA, LiangYue1981816, faiguago, dwcookies, Allenz5): **no licence declared**, so all rights are reserved by default. Do not copy — [gh search results](https://github.com/codewings/PreIntegrated-Skin)
- TF2 shader re-implementation exists at [SamsonStarmerLee/TF2_Shaders](https://github.com/SamsonStarmerLee/TF2_Shaders). Licence not checked.

### Inferences
**Recommended code base**
- Port `SeparableSSS.h` (HLSL_3 path) into the d3d8to9 fork's post chain. Keep the BSD header and add the attribution line to the mod's README or credits.
- The licence is compatible with GPL distribution (BSD-2 is GPL-compatible).
- Generate the 11/17-tap kernels with the BSD `calculateKernel()` logic, or copy the pre-baked arrays from the header.

**Licences to flag**
- Unreal Engine source is under the Epic EULA, which forbids redistribution outside UE projects. **Do not port Burley code from UE.**
- Unity Graphics/HDRP is under the Unity Companion License, tied to Unity use. Treat it as **no-reuse** for our mods.
- GPU Pro 2 book code: publisher terms unknown. Treat as **no-reuse** unless verified.
- NVIDIA GPU Gems 3: the chapter is free to read online. Its sample-code licence was not verified, so re-derive the math rather than copy code.

**Self-written LUT and ramps**
- Pre-integrated LUT and Valve-style ramps can be generated by our own script from the published Gaussian constants (math is not copyrightable). Release them under the mod's GPL.

### Gaps
- No licence text was found for NVIDIA's Human Head demo or the GPU Gems 3 companion code.
- The Unity Companion License and Epic EULA wording was not fetched this session. The constraints above are general knowledge and should be verified if we ever consider using those sources.
- No CC BY-SA or GPL implementation of the DICE translucency was located. The formula is simple enough to write from the talk.
