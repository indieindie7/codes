# Forward vs deferred: four videos, and what they mean for our wrapper

Notes on four videos the user shared on 2026-10-06, read from their transcripts, with the
takeaways for our d3d8-to-d3d9 layer (U2Shaders: soft shadows, PCSS, GI cascades, SSAO,
SMAA, post) that sits on top of two fixed-function, forward-rendered 2003-2005 games
(Unreal II, Advent Rising).

## 1. Ben Andrew, "Forward and Deferred Rendering" (Cambridge Computer Science Talks, 27 min)

The history and the shape of the argument.
- Multipass forward (one draw per mesh-light pair) was fine when the first GPUs made brute
  force cheaper than CPU-side culling (Doom's BSP, 1993 vs GeForce 256, 1999).
- Deferred (Shrek 2001 by Rich Geldreich as a software trick, STALKER as the first mainstream
  title) decouples meshes from lights: the attribute pass writes a G-buffer, the shading pass
  iterates lights. Cost scales linearly with meshes plus lights instead of their product.
- Its costs: no transparency (GTA V renders transparents with a separate forward renderer and
  blends them on top), one material model unless you store a material id and branch (which is
  fine because neighbouring pixels take the same branch), and a fat G-buffer that eats memory
  bandwidth, today's bottleneck.
- The pendulum: draw calls became cheap (DX12/Vulkan), memory became the limit, so heavy
  scene pre-processing plus forward (Doom Eternal) is as fast or faster. Renderers are tools
  to mix, not religions.

## 2. Kirill Bazhenov (bazhenovc), "Why you should never use deferred shading" (30 min)

An experienced graphics programmer's optimised-deferred vs optimised-forward comparison,
opinions marked as such.
- Shared parts: mesh clusters (up to 126 triangles, meshoptimizer, bounding cone back-face
  culling with one dot product), GPU-driven culling with a depth pyramid (min/max mips,
  reversed-Z "always"), pre-recorded command buffers, no CPU culling.
- His tight deferred G-buffer: 160 bits per pixel in two render targets (albedo + normal as
  11-10-11 + emissive as RGBE 9995; roughness 15 bits + metalness 1 bit + motion vectors), plus
  a 32-bit shaded HDR target. Lights clustered (Persson's practical clustered shading), never
  light volumes "that fetch the G-buffer" (bandwidth). Decals clustered too, resolved before
  shading, which enables parallax decals, alpha-cut decals and UV warping.
- Two performance traps of deferred: the G-buffer cannot shrink below ~160 bits, and running
  the shading pass in a compute shader disables render-target compression (DCC) for the
  frame, making later TAA and SSR passes markedly more expensive.
- His forward: 128 bits per pixel (HDR colour 11-10-11 + motion vectors, plus normal/roughness
  only when SSR is on), scaling down to 64 bits on low presets; translucency for free; any
  material model; mandatory depth pre-pass (cheap with no pixel shader), two-pass depth
  pyramid culling. Weakness: quad overshading on small triangles (Giesen's explanation), which
  he says the bandwidth saving outweighs.
- Don't run TAA over translucents (no correct motion vectors). Know the art direction before
  the renderer; pixel-sized triangles need a visibility buffer, not either of these.

## 3. bazhenovc, follow-up (8 min)

Answers to the objections: shader permutations mostly come from art (tiling breakers,
gameplay flags) and are better served by clustered decals plus uniform branching and
bindless textures (Doom shipped with ~100 shaders); occupancy is a latency-hiding tool, not a
goal, and high occupancy can thrash the cache, so profile before chasing it; "we're vertex
bound" usually means missing clustering, vertex compression, LOD or GPU occlusion culling;
tile-based deferred GPUs (mobile) need no depth pre-pass; visibility buffers bring real
costs (single vertex/index buffer, skinning three times or pre-skinning, one shader for all
materials, a senior team).

## 4. Threat Interactive, "Fake Optimization is Destroying 13 Years Work" (Warframe, 15 min)

A pipeline analysis of Warframe's deferred switch, polemical in tone, with specific findings:
- The Switch port lost SSR, DoF, bloom, SSAO, volumetric fog and motion blur after the
  deferred rewrite; the author's point is that deferred is not slow, this one is done badly.
- Concrete issues: alpha-tested geometry in the depth pre-pass costing almost half the
  pre-pass (and using BC3 albedo+opacity instead of BC4 opacity-only, twice the fetches);
  large occluders not pre-passed while alpha-tested clutter was; a separate motion-vector pass
  instead of writing them in the base pass; clustered deferred lighting costing 6 ms with
  no lights in view (pay for lights that aren't there) where stencil-marked light volumes
  would skip unlit pixels; soft-shadow filtering replaced by noise that depends on TAA, so
  the clarity-focused AA option became useless; SSAO (half-res scalable ambient obscurance,
  capsule AO on top) built from separate downscale, blur, upscale and apply passes that
  should be merged, with no Bayer-dithered sampling.
- Recommendation echoed from their other videos: SMAA T2x instead of smeary TAA or
  vendor upscalers.

## What this means for our wrapper

Our situation is the odd one: the games are forward, fixed-function, single material model,
and we cannot touch their draw submission, only intercept it. So the lessons that transfer
are about the screen-space passes we bolt on, not about choosing a renderer.

1. **We already have the right architecture.** The fork is "forward plus a thin G-buffer":
   the game's own forward pass, plus depth (INTZ) and the normals we reconstruct from it.
   Bazhenov's 64-bit low preset is the shape of what we have. We should not add more
   full-screen targets than needed: every pass we add is bandwidth, and 1920x1080 on a 2003
   game is still 8 MB per 32-bit target per read.
2. **Merge passes.** Threat Interactive's SSAO critique applies to ours: our ssao.hlsl runs a
   G-buffer pass, AO, two blur passes, and an apply pass with upsample. The upsample and the
   apply are already one pass; the blur-across and blur-down could become one pass with a
   dithered sample pattern, and the G-buffer pass could be folded into the AO pass (reading
   depth directly, reconstructing the normal from depth derivatives as GI does). Same for the
   GI chain: each cascade level is a full-screen target; a half-size cascade stack is where
   the cost is, and that is already the `gires=2` option.
3. **Stencil instead of shading everything.** The game's lights are fixed-function and not
   ours to touch, but our own passes shade every pixel: sky and far-fog pixels get SSAO and
   GI work that contributes nothing. A cheap depth test (skip pixels at the far plane, or
   beyond the GI reach) before the expensive samples is the equivalent of their stencil
   advice and costs one compare.
4. **Keep the anti-aliasing SMAA.** Both channels, from opposite temperaments, land on
   "no TAA smear": our SMAA 1x choice matches, and SMAA T2x would be the only upgrade worth
   considering, with motion vectors we do not have from a fixed-function game.
5. **Alpha-tested geometry is the hidden cost.** Unreal II and Advent draw masked textures
   (grates, foliage, decals) through the same path; our depth-based passes treat them as
   solid at the depth buffer, which is correct, but any future "weapon/decal mask" pass should
   avoid re-rendering alpha-tested geometry, the trap Warframe fell into.
6. **Decals before shading.** Bazhenov's clustered decals resolve before shading, which is
   what lets him do parallax decals and UV warping; our decal_parallax.hlsl does exactly that
   for projector decals because UE2 draws decals as a separate blended pass after the surface,
   which is the worst case for a deferred design and a natural fit for ours.
7. **No compute, by accident a virtue.** We are on Direct3D 9: no UAV writes, so the DCC
   decompression trap cannot bite; everything stays render-target to render-target.

Nothing here argues for changing the fork's design; it argues for pass merging and early
outs in SSAO and GI, which are the next cheap wins when we tune them.
