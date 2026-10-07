# UE2 (Advent Rising / Unreal II) + d3d8to9 wrapper: feasibility of soft-body/jiggle, impact dents and skin shading

Evidence levels used below: **[LOCAL-VERIFIED]** = checked on this PC in the game binaries, the exported UnrealScript source, or our own probe logs (2026-10-07); **[DOC]** = official docs; **[WIKI/FORUM]** = community material; **[INFERENCE]** = reasoning, not tested.

Local paths used as evidence:
- Unreal II binaries: `C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System\` (Engine.dll, D3DDrv.dll, ini)
- Advent Rising exported script: `C:\Users\john\Documents\AdventRising_src\Engine\Classes\` (Actor.uc, KHinge.uc, KConeLimit.uc, KarmaParamsSkel.uc)
- Unreal II exported script: `C:\Users\john\Documents\Tools\u2_export\full_Engine\Classes\Actor.uc`
- Wrapper fork: `C:\Users\john\Documents\github\d3d8to9-gi\source\u2shaders.hpp`
- Probe logs: `C:\Users\john\Documents\AdventRising_research\pbr_probe\chars.txt`, `C:\Users\john\Documents\github\codes\test-results\2026-10-01-pc\02-char-probe\chars.txt`

## How UE2 skins and draws characters (CPU vs GPU skinning, vertex data at draw time)

### Takeaway
In these builds, skeletal meshes are skinned on the CPU (SSE path) and drawn as ordinary fixed-function lit draws with no vertex blending and no vertex shader. The vertices the wrapper sees are already-skinned positions and normals (mesh/actor space, with a world matrix set); bone matrices never reach the GPU.

### Cited Findings
- Unreal II `Engine.dll` contains the string `SSESkeletalSkinning` and no `HardwareSkinning` or GPU-skinning option string; the same string is in the Ghidra copy of Engine.dll — [LOCAL-VERIFIED] string scan of `...\Unreal II The Awakening\System\Engine.dll`
- Unreal II `D3DDrv.dll` exposes `UseHardwareTL` and `UseHardwareVS` (both `True` in the shipped ini), plus `FD3DVertexShader`, `FD3DFixedVertexShader`, `MaxVertexShaderConst` log lines; no skinning-specific setting exists — [LOCAL-VERIFIED] string scan of D3DDrv.dll and System\*.ini
- Engine.dll exports `USkinVertexBuffer` (class, Serialize) and `USkeletalMeshInstance::GetFrame(AActor*, FLevelSceneNode*, FVector*, int, int&, DWORD)` — GetFrame writes vertex positions into a caller buffer, the classic UE1/UE2 CPU skinning entry — [LOCAL-VERIFIED] export table of Engine.dll
- `UseHardwareVS` is described by tweak guides only as "makes use of the hardware Vertex Shader on modern graphics cards"; no source ties it to skinning — [TweakGuides UT2004](https://tweakguides.dmegaming.com/UT2004_11.html)
- Our character probe (charprobe=1) logged every opaque on-screen draw in Advent and U2: all character/weapon draws are `ff` (fixed function), `vblend 0/0` (D3DRS_VERTEXBLEND off, INDEXEDVERTEXBLENDENABLE off), `lighting 1` with up to 4-8 D3D point lights (type 1); FVF reported as 0 for most (a D3D8 vertex declaration handle used for fixed-function), some 0x112/0x212 — [LOCAL-VERIFIED] chars.txt probe logs (51 + 717 distinct keys, all `vblend 0/0`)
- Advent's character skins are drawn with a game ps_1_1 pixel shader over fixed-function vertices, at double brightness; our fork's charlight/pbr path already replaces that and carries camera-space normal and position to the pixel shader (TEXCOORD2/3) — [LOCAL-VERIFIED] comments at u2shaders.hpp ~1835-1855
- Unreal II also draws each character a second time as a flat silhouette into a small render target for its projected shadow — [LOCAL-VERIFIED] u2shaders.hpp ~948
- General principle: software skinning is a natural SSE target (van Waveren, Doom 3 era) — [Intel SSE skinning paper](https://www.quaddicted.com/webarchive/mrelusive.com_20170131/publications/papers/SIMD-Optimizing-the-Rendering-Pipeline-of-Animated-Models-Using-the-Intel-Streaming-SIMD-Extensions.pdf)

### Inferences
- Because no vertex blending and no vertex shader is active on character draws, skinning must happen before the data reaches D3D; positions in the vertex buffer are final per frame (in mesh/actor space; the World matrix carries actor placement, as the probe logs World matrices per draw).
- Bone matrices are not available to the wrapper at all. Any per-bone effect in the wrapper would have to be reconstructed from vertex motion.
- The CPU writes the skinned vertices each frame into a vertex buffer it locks (likely a dynamic, DISCARD-locked buffer shared by many dynamic draws). The fork already intercepts Lock in `d3d8to9_vertex_buffer.cpp`, so CPU-side vertex edits are mechanically possible.

### Gaps
- Not verified: whether UE2 writes skinned vertices into one shared dynamic VB (ring buffer with NOOVERWRITE) or a per-instance VB. Decompile `USkeletalMeshInstance::GetFrame` and the D3DDrv dynamic-VB code (Ghidra project already has Engine.dll) or log Lock calls by buffer and size.
- What `USkinVertexBuffer` is used for in this build (possibly a rigid-part or Xbox path); not traced.
- Official UDN "SkelAnim2" / "RagdollsInUT2003" pages (docs.unrealengine.com/udk/Two/...) returned HTTP 403 to the fetcher; UnrealWiki (wiki.beyondunreal.com) also 403. Mirror at unrealarchive.org works for some pages.
- Advent Rising's own Engine.dll/D3DDrv.dll were not string-scanned (install path not found in Steam folder); the probe logs show the same ff/vblend 0 pattern, so the conclusion holds empirically for Advent too.

## What a D3D wrapper can do with CPU-skinned characters

### Takeaway
Feasible: identify the draw by texture hash (already done), keep a per-character previous-frame vertex cache keyed by texture hash + vertex count, and either (a) displace vertices on the CPU before Unlock/draw or (b) bind a vs_2_0/vs_3_0 replacement vertex shader that emulates the fixed-function transform/lighting and adds displacement. (b) is cleaner because it never writes into the game's buffers; the fork already replaces fixed-function pixel stages for characters, so adding a matching vertex shader is the next step.

### Cited Findings
- d3d8to9 maps D3D8 `SetVertexShader(handle)` to D3D9 `SetFVF` for FVF handles or `SetVertexShader` for created shaders; the fork overrides `CreateVertexBuffer`, `Lock` (handling D3DLOCK_DISCARD on non-dynamic buffers) and `SetVertexShader` — [LOCAL-VERIFIED] d3d8to9_device.cpp ~382, ~1984; d3d8to9_vertex_buffer.cpp ~90
- The fork already: hashes textures per draw, swaps the pixel pipeline for lit solid draws (charlight/pbr rules), records lights, World matrix and FVF per draw, and has a depth-aware post pass — [LOCAL-VERIFIED] u2shaders.hpp header (lines ~25-34), ProbeDraw ~4490
- RTX Remix (closest precedent of a D3D9 interceptor that reconstructs scenes): "Skinning currently works for rendering only, but we can't replace skinned objects yet... Support for Fixed Function GPU skinning is a more tractable problem... Support for CPU or shader-based transforms is trickier and requires investigation." — [RTX Remix roadmap](https://github.com/NVIDIAGameWorks/rtx-remix/wiki/Roadmap)
- Remix docs: for GPU (fixed-function) skeleton animation, replacements adopt the original's bone transforms; for non-GPU skinning "Replacement occurs on the engine side" — [RTX Remix asset replacement docs](https://docs.omniverse.nvidia.com/kit/docs/rtx_remix/latest/docs/howto/learning-assets.html)
- Remix: "Older games frequently exhibit unstable hashes in world geometry"; geometry hashes are unstable on animated objects — [same docs](https://docs.omniverse.nvidia.com/kit/docs/rtx_remix/latest/docs/howto/learning-assets.html)
- Remix needs fixed-function pipelines; it has "experimental support for simple vertex shaders"; D3D8 games go through wrappers to fixed-function D3D9 — [RTX Remix compatibility](https://docs.omniverse.nvidia.com/kit/docs/rtx_remix/latest/docs/introduction/intro-compatibility.html)
- A UT2004 RTX Remix path-tracing mod exists (beta by "Rune_Storm", 2024), with visual issues and some maps not working — [DSOGaming](https://www.dsogaming.com/pc-performance-analyses/unreal-tournament-2004-rtx-remix-path-tracing-mod/)

### Inferences
- **Identification:** texture hash per draw (already stable in the fork) is the right key; geometry hashes would be useless because CPU-skinned positions change every frame (same problem Remix documents). Use key = (texture hash, vertex count, index count, BaseVertexIndex range) to tell multiple instances of the same character apart; add the World matrix translation as a tiebreaker for several same-skin enemies on screen.
- **Previous-frame data / velocity:** on each matching draw, copy the vertex range (positions+normals) into a per-key cache; next frame, per-vertex velocity = (pos_now - pos_prev) in world space after applying World. Upload prev positions as a second vertex stream (D3D9 SetStreamSource stream 1) so a vertex shader can do per-vertex lag/wobble. Vertex counts are identical frame to frame for the same LOD; LOD switches change counts, so reset the cache when count changes.
- **Reading the buffer:** the vertex data may not be readable (fork comment: "vertex buffers may not be readable" while capturing). Hook at Lock/Unlock instead: when the game unlocks, copy what it wrote (we know the locked range) into a CPU shadow; that avoids reading back from a write-only dynamic buffer. Cost: a few thousand vertices x 24-32 bytes per character per frame, trivial.
- **Option A, CPU displacement at Unlock:** displace written vertices before passing Unlock through. Problem: at Unlock we do not yet know which draw (texture) will use the range; the draw comes later. Would need to defer the real Unlock or keep our own copy VB and redirect the draw's stream source. Workable but invasive.
- **Option B, replacement vertex shader (recommended):** at a matched character draw, bind our own vs that reproduces the fixed-function transform (World*View*Proj), passes normal/position to our existing pixel shader (which already does the lighting per pixel from captured D3D lights), and adds displacement from: per-vertex velocity (stream 1 = previous positions), a per-key list of "dent" spheres (impact point, radius, depth, age) as vs constants, and a sine/spring wobble term. No writes to game buffers; normals can be bent approximately in the shader. Requires vs_2_0+ (D3D9 hardware is fine).
- **Jiggle mask:** the wrapper has no bone weights. Per-vertex jiggle needs a mask: either (1) a painted mask texture in the skin's UV space sampled in the vertex shader (vs_3_0 vertex texture fetch) or (2) a per-mesh table of vertex indices/weights generated offline from the .psk/.gem (we export meshes already) and uploaded as an extra stream. (2) is more robust and works on vs_2_0.
- **Dents:** wrapper-side dents need the hit location in mesh space. The wrapper cannot see gameplay hits; the script mod can pass them out (e.g. encode into a tiny dynamic texture or a known draw the wrapper watches, the same trick class as passing data via texture patching). Alternatively dents purely in the shader from a "dent texture" in UV space that the script cannot write; so a script-to-wrapper channel is the gating item.
- **Shadow silhouette pass:** U2 draws each character again into its shadow render target; any vertex displacement must be applied there too or shadows will not match (minor for small wobble).

### Gaps
- No public precedent found of a D3D8/9 wrapper adding per-vertex jiggle to CPU-skinned characters in an old game; RTX Remix explicitly calls CPU-skinned handling unsolved. This would be novel work.
- Exact UE2 vertex format for skinned meshes (position, normal, one UV; FVF 0x112 = XYZ|NORMAL|TEX1 seen in logs) needs one dump of the declaration to confirm.

## UnrealScript-side options (bone controllers, Karma)

### Takeaway
Script can rotate, translate and scale named bones each tick with alpha blending, and Karma offers springy/motorised hinges and cone limits. A velocity-driven spring per "jiggle bone" computed in Tick and applied with SetBoneRotation/SetBoneLocation is the cheapest believable soft body, but only on bones that exist in the mesh's skeleton; bones cannot be added at runtime.

### Cited Findings
- Advent Rising (build 2226) Actor.uc declares: `SetBoneDirection(name BoneName, rotator BoneTurn, optional vector BoneTrans, optional float Alpha, optional int Space, optional int preCalculatedBone)`, `SetBoneLocation(name BoneName, optional vector BoneTrans, optional float Alpha, optional int preCalculatedBone)`, `SetBoneRotation(name BoneName, optional rotator BoneTurn, optional int Space, optional float Alpha, optional int preCalculatedBone)`, `SetBoneScale(int Slot, optional float BoneScale, optional name BoneName, optional int preCalculatedBone)`, `SetBoneRotationOnly(...)`, `GetBoneCoords(name)`, `GetBoneRotation(name, optional int Space)`, `GetBoneRotationAtFrame(...)`, `AttachToBone(actor, name, optional bool bMaintainRelativeLocation)` — [LOCAL-VERIFIED] AdventRising_src\Engine\Classes\Actor.uc lines 1059-1083
- Unreal II Actor.uc has the same set without the `preCalculatedBone`/`Space` extras on SetBoneDirection; Engine.dll exports `USkeletalMeshInstance::SetBoneDirection/SetBoneLocation/SetBoneRotation/SetBoneScale` — [LOCAL-VERIFIED] Tools\u2_export\full_Engine\Classes\Actor.uc 1301-1317; Engine.dll exports
- Unreal II game code already uses bone controls on the Araknid (U2AraknidControllerHatched.uc), Advent in PlayerController and EonCameraSystem — [LOCAL-VERIFIED] grep of exported source
- SetBoneDirection rotation is absolute and replaces the animation's rotation for that bone; passing Alpha 0.0 clears it — [UDN SkelAnim2 via search snippet](https://docs.unrealengine.com/udk/Two/SkelAnim2.html) (page itself 403 to the fetcher)
- Advent KHinge: `KHingeType` = HT_Normal, HT_Springy, HT_Motor, HT_Controlled; fields KStiffness, KDamping, KDesiredAngVel, KMaxTorque, KDesiredAngle, KProportionalGap, KAltDesiredAngle, KCurrentAngle (read-only) — [LOCAL-VERIFIED] AdventRising_src KHinge.uc
- KConeLimit: KHalfAngle, KStiffness, KDamping — [LOCAL-VERIFIED] KConeLimit.uc; [UnrealWiki mirror: Karma](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma.html)
- Advent KarmaParamsSkel: KSkeleton, bKDoConvulsions, **bRubbery** (Advent addition), KConvulseSpacing, KShotStart/End/Strength, bKImportantRagdoll — [LOCAL-VERIFIED] KarmaParamsSkel.uc
- UE2 Karma ragdoll = a set of rigid bodies joined by KBS joints, defined per skeleton in a physics asset named in KarmaParamsSkel.KSkeleton — [UnrealWiki mirror: Karma Ragdoll](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Ragdoll.html)
- The community "Karma Ragdoll Injury System" briefly ragdolls living pawns on hit (KMakeRagdollAvailable, SetPhysics(PHYS_KarmaRagdoll), KAddImpulse on the nearest bone via GetClosestBone), then blends back with GetBoneCoords + SetBoneDirection alpha tweening and a double LinkMesh to restore animation; limits: about 3 ragdolls per zone, network problems, animation lock-out after returning from ragdoll — [UnrealWiki mirror](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Ragdoll_Injury_System.html) [WIKI/FORUM]
- Source engine precedent for the same idea: `$jigglebone` = per-bone spring-damper driven by bone motion (flexible/rigid/boing types with stiffness, damping, angle limits) — [Valve Developer Wiki: Jiggle Bone](https://developer.valvesoftware.com/wiki/Jiggle_Bone) (page 403 to the fetcher; parameter names from prior knowledge)

### Inferences
- **Script jiggle recipe:** in the pawn's Tick, for each jiggle bone keep a spring state (offset vector, velocity). Drive with the bone's world acceleration (from GetBoneCoords this frame vs last frame, or pawn Velocity delta), integrate `v += (-k*x - c*v - a_bone)*dt`, then SetBoneLocation/SetBoneRotation with Alpha 1. Cost is a few bones per pawn in UnrealScript; fine for a handful of on-screen characters.
- **Space parameter:** Advent's SetBoneRotation/SetBoneDirection take `Space`; check which values mean local vs component space before relying on additive offsets (UE2 controllers replace rather than add, so the script must read the animated pose first via GetBoneRotation and add the spring offset itself).
- **Bones after import:** UnrealScript cannot add bones. Jiggle bones (belly, cheeks, Izarian sacs, antennae, tails, armor flaps) must exist in the skeletal mesh at import; for our own meshes the Golem/.psk import pipeline can add them with skin weights. For stock meshes only existing bones can be wobbled (e.g. head, spine, clavicles: coarse "whole body sway", not flesh).
- **Karma route:** a partial ragdoll on a live pawn is not supported cleanly in UE2 (whole-skeleton ragdoll only; the injury-system workarounds show the pain). Springy KHinge/KConeLimit are for Karma actors, not for bones of an animated pawn. Keep Karma for death/knock-down; use script springs for living jiggle.
- **Dents via script:** UE2 script has no vertex access. "Dent" can only be faked with bone pushes (local bone offset at the hit bone decaying over time), a decal/overlay material, or the wrapper channel above.

### Gaps
- No specific UT2004 mod with jiggle bones / script soft-body was found in this pass (searches returned only Source/Godot). Treat as "probably exists but not located".
- Exact semantics of Advent's `preCalculatedBone` and `bRubbery` not traced (check C++ in Engine.dll via Ghidra).
- Number of bones a UE2 skeletal mesh may have and per-vertex influence limit not verified from docs (UDN pages blocked).

## Precedents in wrapper/injector projects

### Takeaway
Most injector projects (ReShade, SweetFX, ENB) work in screen space or replace existing shaders; none add deformation. RTX Remix is the only one that reconstructs geometry and it handles skinning only for fixed-function GPU skinning. Renderer replacements (Kentie D3D10, UTGLR) replace the whole render device DLL and do per-pixel effects but not deformation. Our fork already sits beyond ReShade-class tools because it swaps per-draw pipelines by texture hash.

### Cited Findings
- RTX Remix: custom D3D9 runtime intercepts draw calls and reassembles the scene; needs fixed-function; CPU/shader skinning replacement unsolved — [RTX Remix compatibility](https://docs.omniverse.nvidia.com/kit/docs/rtx_remix/latest/docs/introduction/intro-compatibility.html), [roadmap](https://github.com/NVIDIAGameWorks/rtx-remix/wiki/Roadmap)
- ENBSeries skin SSS (Skyrim): parameters Amount, Radius, Quality, epidermal/subdermal layers; depends on direct sunlight ("No sunlight/Direct Lighting = no SSS effect"); results depend on the installed skin textures — [STEP ENB INI reference: Subsurfacescattering](https://stepmodifications.org/wiki/SkyrimSE:ENBSeries_INI_Reference/Subsurfacescattering), [Skyrim LE version](https://stepmodifications.org/wiki/SkyrimLE:ENBSeries_INI_Guide/Subsurfacescattering)
- Kentie's Direct3D 10 renderer for Unreal/UT99/Deus Ex/Rune: written from scratch, replaces the render device, adds parallax occlusion mapping via pixel shaders; source provided — [Unreal Archive listing](https://unrealarchive.org/unreal-tournament/patches-updates/renderers/dirext3d-10-driver/index.html), [GameGPU news](https://en.gamegpu.com/news/igrovye-novosti/unreal-unreal-tournament-deus-ex-rune-directx-10)

### Inferences
- ENB's skin SSS works because the game (Skyrim) marks skin with a shader flag the injector can see; our equivalent is the texture-hash rule list (already used for pbr=). For UE2, a skin mask = list of skin texture hashes + optional per-texel mask texture.
- ReShade/SweetFX are post-only: they could do screen-space SSS only with a skin mask, which they lack; our fork has both depth and a per-draw mask opportunity (write a skin ID into an MRT or stencil during character draws).
- UE1 renderer replacements (Kentie, UTGLR/OldUnreal) are viable because UE1 render devices are pluggable DLLs with source headers; UE2 D3DDrv is also a pluggable render device, but no public UE2 SDK headers for writing one for build 2226/U2 exist to my knowledge, which is why wrapping D3D8 is the practical route.

### Gaps
- Did not find documentation on how ENB decides "skin" internally (the STEP page does not say); no source available (ENB is closed).
- No Unreal II- or UE2-specific renderer replacement or "UT2004 Remix-style" skin-shader project was found beyond the UT2004 RTX Remix beta.

## Practical recommendations: cheapest believable soft-body and skin shading

### Takeaway
Soft body: start with script-driven spring bones (only where bones exist or can be added to our own meshes); move to a wrapper vertex shader with prev-frame positions only if per-vertex flesh wobble or dents are needed. Skin: a light-warp ramp / pre-integrated wrap term plus thickness-based translucency in the existing character pixel shader, optionally screen-space SSS in the post pass masked by skin hashes.

### Cited Findings
- Fork already lights characters per pixel from captured D3D lights with camera-space normal/position — [LOCAL-VERIFIED] u2shaders.hpp ~1835-1880
- ENB-style SSS needs direct light to show; with UE2's few point lights per character this maps to the captured light list — [STEP ENB SSS](https://stepmodifications.org/wiki/SkyrimSE:ENBSeries_INI_Reference/Subsurfacescattering)

### Inferences
- **Soft body, ranked by cost:**
  1. Script spring bones (UnrealScript Tick + SetBoneLocation/Rotation): zero renderer work, correct shadows, works with Karma death; limited to existing bones. Best first step for Advent creatures/our own imported meshes where we can add jiggle bones in Golem.
  2. Wrapper vertex shader, velocity-lag wobble: per-vertex `offset = -k * (pos - pos_prev_smoothed) * mask`, mask from an offline per-vertex table; one extra stream; looks like flesh lag on fast moves. Must also be applied in U2's shadow silhouette pass.
  3. Wrapper dents: up to N (e.g. 4-8) dent spheres per character in vs constants, `pos -= n * depth * falloff(dist)` with decay; needs a script-to-wrapper hit channel. Highest effort.
- **Skin, ranked by cost:**
  1. Wrap/pre-integrated diffuse with a red-shifted terminator (Penner-style ramp, or a painted 1D light-warp like Source's `$lightwarptexture`) in the existing charlight pixel shader, per skin-texture rule: one texture lookup, no passes.
  2. Thickness-map translucency (back-lighting through ears/fins/thin membranes) from the same captured lights.
  3. Screen-space SSS blur in the post pass masked to skin pixels (needs a skin mask written during character draws; we have depth already).
- Matches the user's taste note that animation beats texture sharpness: the spring-bone path is higher value than skin SSS.

### Gaps
- None of the recommended paths has been built or measured in UE2 yet; performance numbers are unknown.
- The script-to-wrapper data channel (for dents and per-character jiggle intensity) is undesigned.
