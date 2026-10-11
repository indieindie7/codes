# Voxel rendering optimisation: practical report (state of the art to 2026)

Targets: (a) D3D9 / SM3 post-process fork (pixel + vertex shaders, no compute, no SSBOs, no integer ops worth trusting); (b) Bevy / wgpu with compute. Numbers are the authors' own claims unless noted. Items marked "verify" came from memory, not a fetched page; check before relying on them. Licences marked "verify" likewise.

## 1. Storage

| Structure | Idea | Cost / numbers | Fit |
|---|---|---|---|
| Sparse voxel octree (SVO) | Laine & Karras, "Efficient Sparse Voxel Octrees" (I3D 2010, NVIDIA): child-mask + pointer nodes, plus contours and per-brick attachments. https://research.nvidia.com/publication/2010-02_efficient-sparse-voxel-octrees | ~8 B/node typical; ray-casts at interactive rates on 2010 GPUs | (b); pointer chasing is hostile to SM3 |
| Sparse voxel DAG (SVDAG) | Kampe, Sintorn, Assarsson, "High Resolution Sparse Voxel DAGs" (SIGGRAPH 2013): merge identical subtrees bottom-up | Orders of magnitude smaller than SVO on static scenes (128K^3 fits in GPU memory); read-only, edits are hard | (b) for static / far terrain |
| Compressed / symmetry DAGs | Villanueva et al., "Symmetry-aware SVDAGs" (2016); Dado et al., "Geometry and Attribute Compression for Voxel Scenes" (EG 2016); later "Compressing Color Data for Voxelized Surface Geometry" and 2024 SVDAG segmentation-volume work (KIT) | Symmetry adds ~2x-ish over plain DAG on some models | (b), offline-built only |
| Editable DAGs | Careil, Billeter, Eisemann, "Interactively Modifying Compressed Sparse Voxel Representations" (CGF 2020) | Edits by path-copy + re-hash, hundreds of thousands of voxel edits per second reported | (b) if destruction is needed on a DAG |
| Bricks / brickmaps | Grid of small dense bricks (e.g. 8^3) plus a coarse index. GigaVoxels (Crassin et al. 2009) streams bricks ray-guided; brickmap papers (Museth's NanoVDB/OpenVDB is the industrial cousin) | Brick = one texture fetch run; constant-time lookup via 3D texture atlas + indirection | (a) and (b); the only one that maps to SM3 (3D indirection texture + 3D atlas) |
| 64-tree (4x4x4 bitmask tree) | Each node = one u64 occupancy mask + child offset; popcount of lower bits gives child index. Dubiousdavid / Dolkar "64-tree" write-ups; used in several 2024-25 indie engines (verify names) | 16 B/node, tree depth for 4096^3 = 6, fast popcount traversal, cheap edits (flip a bit, free empty nodes) | (b); u64 needs two u32 in WGSL. Not SM3 (no bit ops) |
| Run-length columns | Per (x,z) column store runs of (type, length). Classic in Ace of Spades / Voxlap | Great on terrain, awful for random access in shaders; fine on CPU for meshing/storage | CPU / on-disk only |
| Palette compression | Per-chunk palette + bit-packed indices (Minecraft sections: 4-16 bit). Uniform chunk = 1 value | 4096-voxel chunk with <=16 types: 2 KB vs 4 KB at u8 | Both (disk, RAM, upload) |

Rule of thumb: dense chunk array (32^3 or 62^3 + padding) with palette for editable gameplay data; derive a render structure (bitmask tree, brickmap or DAG) from it.

## 2. Traversal (ray-marched path)

- 3D DDA: Amanatides & Woo, "A Fast Voxel Traversal Algorithm for Ray Tracing" (Eurographics 1987). One compare + add per step, no division in the loop. The baseline everywhere (Teardown, most indie engines). http://www.cse.yorku.ca/~amana/research/grid.pdf
- Hierarchical DDA: step in a coarse grid, descend only when occupied; 2-3 levels (e.g. 4^3 over 4^3 over 16^3) cut step counts by roughly 5-20x on sparse scenes (typical figures, scene dependent). A 64-tree gives this for free: each level is a 4x4x4 mask, and you skip to the next set bit in ray order with bit tricks.
- Beam / coarse pre-pass: Laine & Karras trace a low-res depth beam (e.g. 8x8 pixel tiles) first and start fine rays at the conservative hit distance; saves ~20-40% in their results (verify exact). Works on SM3 as a two-pass render to a 1/8-res target.
- Empty-space skipping with distance fields: per-brick or per-voxel min-distance (Chebyshev) lets rays leap; cost is the build/update of the DF (jump-flood or incremental). Good for static terrain, costly under edits. Alternative: just use the hierarchy (cheaper to update).
- Bitmask ray marching: occupancy as bits; to find the first hit along an axis inside a 64-voxel row, use ctz/clz on masked bits; to step through a 4^3 node, build the ray mask once. Several 2024-26 voxel engine devlogs report 2-4x over plain DDA (verify). Needs integer ops: (b) only.
- Ray-guided LOD and traversal early-out by pixel footprint: stop descending when the voxel is under about 1 pixel (as in Aokana, below).
- D3D9 SM3 reality: a 3D-texture DDA loop with `tex3Dlod` and a bounded `for` (sm 3.0 allows ~255-iteration static loops, with early `break` via dynamic flow) is feasible but slow. Budget 64-128 steps, half-resolution, and use it only for secondary rays (AO, shadows, GI) on a coarse voxelisation of the scene, never for primary visibility.

## 3. Mesh-based voxel rendering

- Face culling: only emit faces adjacent to air/transparent. Gets ~6x fewer faces than naive cubes on solid terrain.
- Greedy meshing: classic 0fps article (Mikola Lysenko, 2012), merges coplanar same-type faces into rectangles. https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/
- Binary greedy meshing: u64 occupancy columns; culling via `col & !(col >> 1)` style ops processes 64 voxels per instruction; merging via bit runs. cgerikj/binary-greedy-meshing (C++, MIT, verify) claims average 74 us per 62^3 chunk single-threaded on a Ryzen 3800X; noisy/checkerboard worst cases ~33-37 ms (author numbers). https://github.com/cgerikj/binary-greedy-meshing . Rust: `block-mesh-bgm` https://docs.rs/block-mesh-bgm (block_mesh-compatible call shape, offers AO-safe merging). Constraint: 64-bit rows => 62 interior voxels per axis plus 2 padding.
- Classic Rust mesher: bonsairobo/block-mesh-rs (visible_block_faces fast, greedy_quads ~1/3 the quads but ~3x slower on sphere-like input; licence MIT/Apache-2.0, verify). https://github.com/bonsairobo/block-mesh-rs
- Vertex packing to 32 bits: 6 bits each for x,y,z (0..63) = 18 bits, 3 bits normal/face id, 4-5 bits AO or light, remaining bits texture/palette index; or send one u32 per quad (position + w/h + face + material) and expand in the vertex shader (4 vertices/instance, or 6 from vertex_index). Cuts vertex bandwidth ~6-10x versus float pos/normal/uv. Fits (b) trivially; on D3D9 pack into one D3DCOLOR/UBYTE4 or two shorts and unpack with `frac`/`floor` math (no int ops, so use floats and exact small powers of two).
- Chunk LOD: downsample (min/mode) 2x per level; seams: Transvoxel (Lengyel 2010) handles smooth/Marching-Cubes terrain, http://transvoxel.org/ ; for blocky voxels use skirts (drop edge vertices) or render LOD borders with an overlap. Quadtree/clipmap chunk grids keep chunk counts around 200-1000 visible.
- Indirect draws and GPU culling (b): one big vertex/quad pool with a free list, per-chunk draw args in a buffer, compute pass does frustum + Hi-Z occlusion + back-face-direction culling (skip the 3 face groups facing away from camera: roughly halves quads), emits `DrawIndexedIndirect`. wgpu supports `multi_draw_indirect` (native feature, not WebGL); Bevy 0.1x+ has GPU-driven mesh preprocessing but a custom pool is simpler for voxels. Check features at runtime.
- (a): CPU frustum culling per chunk plus one DrawPrimitive per chunk (or static VB/IB per chunk in a managed pool). Keep chunk draws <= a few thousand; D3D9 draw-call overhead is the limit (~5-10k/frame typical). Hardware instancing (SM3, `SetStreamSourceFreq`) can render quads from a shared unit quad.

## 4. Lighting

- Voxel cone tracing: Crassin et al., "Interactive Indirect Illumination Using Voxel Cone Tracing" (Pacific Graphics 2011). Mip-mapped 3D radiance volume, 5-6 cones per pixel for diffuse, 1 for specular. Typical cost 3-6 ms at 1080p on a mid GPU with a 128^3-256^3 clipmap (indie reports, verify). https://research.nvidia.com/publication/2011-09_interactive-indirect-illumination-using-voxel-cone-tracing . Voxelisation was a geometry-shader/atomic pass; for the (b) path do it in compute.
- Teardown (Dennis Gustafsson): the scene is voxel models in a 3D texture per object; raymarches on the GPU for shadows, AO and reflections; post-process lighting + temporal accumulation; no meshes for rendering. His talks/blog: https://blog.voxagon.se/ and GDC/Handmade talks (verify exact titles). Closed source; ideas only.
- Enshrouded (Keen): voxel terrain with GI via voxel structure and screen-space; detail not public beyond talks (verify).
- Minecraft shader packs (SEUS PTGI, Continuum, BSL): SEUS PTGI voxelises the visible world into a 3D texture via fragment shader scatter and traces it. This is the closest existing proof that a rasterised voxel GI works without compute (OpenGL 4.x, but conceptually SM3-adjacent with a 2D-atlas-packed 3D volume).
- Radiance cascades (Alexander Sannikov, Path of Exile 2 team): cascaded probes with interval-length scaling; 2D version is cheap and noise-free; 3D version works on voxel grids with ray marching through the occupancy volume. Introduction: https://radiance-cascades.com/ ; Sannikov paper PDF on same site. (b) only realistically; a 2D screen-space cascade variant is feasible on SM3 as multi-pass ping-pong, expensive.
- Baked per-vertex AO (0fps): per-vertex AO from the 3 neighbouring voxels (0-3 levels, 2 bits), https://0fps.net/2013/07/03/ambient-occlusion-for-minecraft-like-worlds/ . Fix the anisotropy by flipping the quad diagonal when `a00+a11 > a01+a10`. Costs nothing at runtime; merge faces only when AO matches (or use the AO-safe mode). Best first lighting step on both paths.
- Cheap voxel light: flood-fill block/sky light (Minecraft style, 4+4 bits/voxel) in a 3D texture, sampled in the shader; incremental update via BFS on edits.
- (a) recommended: baked vertex AO + flood-fill light texture + the existing screen-space SSAO/GI. A coarse (e.g. 64^3 at 1m or 128^3) binary occupancy 3D texture feeds short ray-marched sun-shadow/AO rays in the pixel shader (<=32 steps, half-res).

## 5. Shipped / indie references

- Teardown: see above; closed source.
- John Lin (Voxel Tech devlogs on YouTube): voxel world with simulated fluid/physics, sparse voxel structure + ray tracing; closed source.
- Gabe Rundlett (Gabe's voxel engine, GabeVoxelGame), Douglas Dwyer (Voxel Engine / "Hex" style devlogs), Ethan Gore (voxel-engine devlogs, Voxel Tech): all long-running YouTube devlogs mostly on custom ray-marched or mesh+DAG engines. Titles and techniques per video not verified here; mine them for traversal and streaming approaches, treat as ideas, not code.
- Aokana (Fang, Wang, Wang 2025, PACMCGIT 8, Art. 10): SVDAG with LOD, GPU streaming, GPU-driven pipeline, up to tens of billions of voxels, claims up to 9x lower memory and 4.8x faster than prior SOTA, combinable with mesh rendering. https://arxiv.org/abs/2505.02017
- Veloren (Rust, wgpu): meshed voxel RPG, GPL-3.0 (verify): do not copy code into a non-GPL game. https://gitlab.com/veloren/veloren
- Bevy crates: bonsairobo/block-mesh-rs (above); `block-mesh-bgm` (binary greedy); splashdust/bevy_voxel_world (chunk streaming, meshing, MIT/Apache-2.0, verify) https://github.com/splashdust/bevy_voxel_world ; `voxelis` (SVO/DAG crate in Rust, licence verify) https://lib.rs/crates/voxelis ; `bevy_meshem`. Search results on 2026-10-10 did not surface bevy_voxel_world directly: confirm licence in its repo before depending.

## 6. Updates and streaming

- Dirty tracking: chunk `dirty` flag plus per-neighbour flags (edits on a border dirty the adjacent chunk's padding). Queue by distance to camera; remesh budget per frame (e.g. 2-4 ms of worker time). Binary greedy meshing at ~0.1 ms/chunk makes remeshing on the main frame budget viable for small edits.
- Mesh on worker threads (Bevy `AsyncComputeTaskPool`), keep generation counters so stale results are dropped.
- GPU upload batching (b): one persistent big buffer + sub-allocator; collect all chunk updates in a frame into one staging buffer and issue `write_buffer` / a copy per contiguous region; avoid per-chunk buffer creation. For quad-pool rendering, upload u32 quads only. (a): lock a dynamic VB with `D3DLOCK_NOOVERWRITE` and append; discard on wrap.
- Ray-march structures: update a 3D texture with `write_texture` for changed bricks only (b), `UpdateSubresource`/LockBox on dirty bricks (a).
- Edits in DAGs: path-copy + hash-consing (Careil et al. 2020); for gameplay-editable worlds keep a dense/palettized authoritative chunk store and rebuild the DAG for far LODs lazily. 64-trees: flip a bit, propagate empty status up, free the node.
- Streaming (Aokana, GigaVoxels): request nodes/bricks the rays touched (feedback buffer), load from disk compressed (LZ4/zstd + palette), evict by LRU. Aokana's streaming works at chunk granularity per LOD with a GPU-visible page table.

## What to use

(a) D3D9 / SM3 fork, no compute
1. Mesh chunks with binary greedy meshing (CPU, build-time or at load), 32-bit packed vertices, per-vertex AO: cheapest and fits the existing raster pipeline.
2. Flood-fill light volume as a 3D texture, sampled in the shader: gives cheap coloured GI-like bounce and AO without compute.
3. Coarse binary occupancy 3D texture + bounded DDA in the pixel shader for half-res shadow/AO rays: only if the screen-space techniques show artefacts; keep under ~32-64 steps.
4. Brickmap with a 3D indirection texture if a ray-marched path is truly needed; skip DAGs/SVOs/bitmask trees (need pointer chasing or integer ops).

(b) Bevy / wgpu with compute
1. Authoritative palettized chunk store (62^3 + padding) + binary greedy meshing on worker threads (`block-mesh-bgm` or a port of cgerikj's), quads as packed u32s in a pooled buffer: ships fastest and scales.
2. GPU-driven draw: one quad pool, compute culling (frustum + Hi-Z + facing), `multi_draw_indirect` where supported; fall back to per-chunk draws.
3. Per-vertex AO + 3D flood-fill light now; voxel-GI later via radiance cascades or cone tracing on a clipmapped occupancy/radiance volume (compute voxelisation).
4. For far distance or enormous worlds: 64-tree or brickmap ray marching with bitmask DDA, or SVDAG with LOD and streaming à la Aokana (read-only far field, meshes near field).
5. Licences: prefer MIT/Apache crates (block-mesh-rs, bevy_voxel_world; verify); never copy Veloren (GPL-3) or Teardown/devlog material.
