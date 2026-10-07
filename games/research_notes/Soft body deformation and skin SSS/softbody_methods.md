# Real-time soft-body and flesh simulation methods for game characters (for a UE2-era mod target)

Target context: Unreal Engine 2 (2004-05), CPU skinning or D3D9 SM2/SM3 vertex shaders, modded from outside. "Fits UE2" below means: a small per-frame CPU pass over a few hundred to a few thousand points, or a stateless vertex-shader term fed by per-bone constants.

## 1. Jiggle / secondary-motion bones (Source $jigglebone, UE AnimDynamics, Kawaii Physics, Unity spring bones)

### Takeaway
Jiggle bones are per-bone damped springs (or a verlet chain with fixed lengths) that lag behind the animated pose; they are the cheapest, most stable and most art-controllable option (tens of bones, microseconds of CPU), and they fit UE2 best because they only change bone transforms that the existing skinning already consumes. Their limit: deformation is only as rich as the bone placement and skin weights (no volume preservation, no collision of flesh against flesh, belly/breast/cheek need dedicated helper bones).

### Cited Findings
- Source's `$jigglebone` is a QC command (all Source games since Source 2007) that marks skeleton bones to be dynamically simulated at runtime for secondary motion such as "bouncy flesh, floppy ears" — [Valve Developer Community: $jigglebone](https://developer.valvesoftware.com/wiki/$jigglebone) (via search snippet; page itself returned HTTP 403 to the fetcher).
- Four property groups: `is_rigid`, `is_flexible`, `has_base_spring`, `is_boing` (Source 2013 only); `has_base_spring` and `is_boing` cannot be combined — [VDC $jigglebone](https://developer.valvesoftware.com/wiki/$jigglebone).
- `stiffness` range 1-1000 (10 = very loose, 500 = stiff and springy); `damping` is spring friction, 0 = oscillates forever; `tip_mass` belongs to `is_rigid`; `is_boing` takes `impact_speed`, `impact_angle`, `damping_rate`, `frequency`, `amplitude` (a squash-and-stretch "boing" along the bone on impact) — [VDC $jigglebone](https://developer.valvesoftware.com/wiki/$jigglebone), [VDC Jiggle Bone](https://developer.valvesoftware.com/wiki/Jiggle_Bone).
- UE AnimDynamics: a "low-performance cost" solver that simulates its own box-shaped bodies per segment (not the physics asset), has no collision detection, and uses linear, angular (angle or cone) and planar constraints, with optional springs on linear/angular constraints; collision substitutes are planar limits and spherical limits; parameters include Bound Bone, Box Extents, Local Joint Offset, gravity scale/override and pre/post solver iterations; single bodies are cheap, chains much more expensive — [Epic: AnimDynamics](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-animdynamics-in-unreal-engine).
- Kawaii Physics (pafuhana1213): "pseudo-physics" UE plugin for hair/skirts/flesh-like sway, "simple, PhysX-free algorithm", parameters Damping, Stiffness, WorldDamping, LimitAngle, Gravity and custom forces; sphere/capsule/plane colliders; keeps bone lengths fixed so it cannot stretch or collapse "even if simulation breaks down"; supports UE 5.3-5.8 (v1.11.1 for UE 4.27); **MIT licence**; algorithm based on the "Next Idolmaster Graphics & Animation Programming Preview" talk — [GitHub KawaiiPhysics](https://github.com/pafuhana1213/KawaiiPhysics).
- Unity VRM SpringBone (in UniVRM) is the common open-source Unity spring-bone implementation; UniVRM is **MIT** — [GitHub vrm-c/UniVRM](https://github.com/vrm-c/UniVRM) (licence via GitHub API).

### Inferences
- Algorithm common to all of these (Kawaii/VRM style): per bone keep previous and current tip position; each frame do a verlet step `p += (p - p_prev)*(1-damping) + gravity*dt^2`, pull toward the animated tip by `stiffness`, push out of sphere/capsule colliders, then re-project to the fixed bone length and clamp the angle to LimitAngle; write the bone rotation that points at the new tip. Source's flexible mode is the same idea with separate pitch/yaw springs and angle limits.
- For UE2: this is the first thing to build. A UnrealScript or native hook that offsets helper bones (belly, breast L/R, cheek L/R, butt, thigh fat) after animation is evaluated, with a few dozen bones, costs effectively nothing. The modding problem is not maths but whether bone overrides can be injected after animation in UE2 (cross-reference: user's memory notes that script bone posing was blocked in U2; a native/dll route may be needed).
- "is_boing"-style squash along the bone axis (scale the bone along its length on impacts, inverse on other axes) is a cheap volume-preserving trick for belly/breast impacts and wound hits.

### Gaps
- Exact Source jiggle integrator (explicit spring vs verlet) not confirmed; VDC pages blocked direct fetch (403).
- No primary licence check for Unity's own (Asset Store) "Dynamic Bone" — it is a paid Asset Store package, presumably not redistributable; not verified.

## 2. Mass-spring, shape matching, PBD / XPBD, projective dynamics, FEM-lite, Vivace: what each gives for flesh, cost and stability

### Takeaway
For a modding team on CPU, the practical winners are (a) shape matching (unconditionally stable, constant-cost 3x3 per cluster, ideal for a few blobs per body part) and (b) XPBD with substeps on a coarse tet cage (one solver, any constraint, stable at game timesteps, stiffness independent of iteration count). Projective dynamics / fast mass-spring are stable at large steps but need a prefactored sparse solve (Eigen-class code) and fixed topology; Vivace and VBD are GPU/compute-shader methods (modern only). Plain explicit mass-spring is the worst choice: unstable when stiff.

### Cited Findings
**Shape matching (Müller, Heidelberger, Teschner, Gross, SIGGRAPH 2005)**
- Replaces energies by geometric constraints: each step, finds the optimal rigid (or linear/quadratic) transform matching rest shape to current particles, then pulls each particle toward its goal position `g_i`; points are always drawn toward well-defined goals so explicit-integration overshoot is eliminated; "unconditionally stable", no pre-processing, no connectivity needed — [Müller et al. 2005 PDF](https://matthias-research.github.io/pages/publications/MeshlessDeformations_SIG05.pdf).
- Per step the 3x3 matrix `Apq = sum m_i p_i q_i^T` is assembled and its rotation extracted via 5-10 Jacobi rotations (constant cost); with alpha = 1 it behaves as a rigid body; extensions: linear and quadratic deformation modes and overlapping clusters for larger deformation — [same](https://matthias-research.github.io/pages/publications/MeshlessDeformations_SIG05.pdf).
- Only a small subset of render vertices needs to be simulated; remaining vertices can be moved by the computed transform — [same](https://matthias-research.github.io/pages/publications/MeshlessDeformations_SIG05.pdf).
- Performance on a 2005 Pentium 4 3.2 GHz: 100 objects x 100 points x 8 clusters, quadratic model, at 50 fps; quadratic matching 0.008-0.096 ms per object per frame; a game-like head = 8 clusters, 66 points driving a 6,460-face surface mesh; collision handling (penalty based) was the bottleneck, not the deformation — [same](https://matthias-research.github.io/pages/publications/MeshlessDeformations_SIG05.pdf).
- Limitation stated by the authors: geometrically, not physically, motivated; higher-order modes do not necessarily add accuracy — [same](https://matthias-research.github.io/pages/publications/MeshlessDeformations_SIG05.pdf).

**PBD (Müller et al. 2006/2007) and XPBD (Macklin, Müller, Chentanez, MIG 2016)**
- PBD paper: Müller, Heidelberger, Hennix, Ratcliff, VRIPhys 2006 (J. Vis. Comm. 2007); XPBD: Macklin, Müller, Chentanez, Motion in Games 2016 — [Müller publications list](https://matthias-research.github.io/pages/publications/publications.html).
- XPBD fixes PBD's dependence of stiffness on iteration count and timestep by adding a compliance per constraint, with time-step-scaled compliance alpha~ = alpha/dt^2 in the Lagrange-multiplier update; cost is essentially the same as PBD — [XPBD PDF](https://matthias-research.github.io/pages/publications/XPBD.pdf).
- "Small Steps in Physics Simulation" (Macklin, Storey, Lu, Terdiman, Chentanez, Jeschke, Müller, SCA 2019): n substeps with one XPBD iteration each beats one large step with n iterations; lower constraint error and damping than implicit large-step integrators, more stable than explicit over a wide stiffness range, insensitive to matrix conditioning and over-constraint — [Eurographics DL](https://diglib.eg.org/handle/10.1145/3309486-3340247).
- "A Constraint-based Formulation of Stable Neo-Hookean Materials" (Macklin, Müller, MIG 2021) gives an XPBD tet constraint for a stable Neo-Hookean material (better flesh/volume behaviour than edge+volume constraints), with a browser demo — [Müller publications](https://matthias-research.github.io/pages/publications/publications.html).
- "Solid Simulation with Oriented Particles" (Müller, Chentanez, SIGGRAPH 2011): shape matching generalised with particle orientations so very sparse particle sets can drive skinned meshes — [Müller publications](https://matthias-research.github.io/pages/publications/publications.html).

**PBD applied to character skin (closest published precedent for "LBS then flesh pass")**
- Abu Rumman and Fratarcangeli, "Position Based Skinning of Skeleton-driven Deformable Characters", SCCG 2014: LBS first, then PBD stretch (edge) + tet volume constraints adjust vertices; "jiggle zone" = vertices further from their nearest bone than average, where LBS is disabled and stretch stiffness tuned, giving passive jiggle; LBS lost ~14 % volume, PBS kept within 0.5 % with 24 iterations — [Brunel full text](https://bura.brunel.ac.uk/bitstream/2438/21211/1/FullText.pdf).
- Cost: tet meshes of ~1.6-3.2K vertices and ~5-14K tets, 10 ms timestep, 24 iterations, Intel i5 2.5 GHz laptop (single model) — reported total compute times roughly 33-90 ms per measured unit (table reports "avg. skinning computation time for running a 1 sec simulation"; the PDF table text was garbled on extraction, so read the original before quoting exact numbers); no self-collision handling — [same](https://bura.brunel.ac.uk/bitstream/2438/21211/1/FullText.pdf). Follow-up: "Position-Based Skinning for Soft Articulated Characters", CGF 2015 — [Eurographics DL](https://diglib.eg.org/handle/10.1111/cgf12533).

**Fast mass-spring / projective dynamics**
- Liu, Bargteil, O'Brien, Kavan, "Fast Simulation of Mass-Spring Systems", ACM TOG 32(6), 2013: implicit Euler solved by block coordinate descent; the system is globally linear in positions, nonlinear spring directions are strictly local, so the global matrix is pre-factored once and iterations are very fast — [project page](https://users.cs.utah.edu/~ladislav/liu13fast/liu13fast.html).
- Projective Dynamics (Bouaziz, Martin, Liu, Kavan, Pauly, ACM TOG 2014) generalises this local/global scheme to arbitrary constraint projections; reference implementation ShapeOp is C++ and **MPL-2.0** (file headers "subject to the terms of the Mozilla Public License v. 2.0") — [ShapeOp source on GitHub, EPFL-LGG/ShapeOp](https://github.com/EPFL-LGG/ShapeOp); paper record [EPFL Infoscience](https://infoscience.epfl.ch/entities/publication/00c49830-4e0c-485d-a752-939abba0e2a6).
- ADMM ⊇ Projective Dynamics (Overby et al.) reference code `mattoverby/admm-elastic` is **MIT** — [GitHub](https://github.com/mattoverby/admm-elastic) (licence via GitHub API).

**Vivace / GPU solvers (modern-only)**
- Vivace (Fratarcangeli, Tibaldo, Pellacini, ACM TOG 2016, SIGGRAPH Asia): randomized graph colouring each frame, then parallel Gauss-Seidel per colour; runs entirely on the GPU, used as solver for both Projective Dynamics and PBD; faster and more stable than prior work at very small time budgets — [Chalmers record](https://research.chalmers.se/en/publication/507089).
- Vertex Block Descent (Chen et al. 2024) is a newer GPU-friendly solver; its engine "Gaia" is **Apache-2.0** — [arXiv 2403.06321](https://arxiv.org/pdf/2403.06321), [GitHub AnkaChan/Gaia](https://github.com/AnkaChan/Gaia).

**Reduced FEM for characters**
- Kim and Pollard, "Fast Simulation of Skeleton-Driven Deformable Body Characters", ACM TOG 30(5), 2011: reduced deformable body with nonlinear FEM + linear-time skeleton dynamics + explicit integration, orders of magnitude faster than prior work, passive jiggle from kinematic skeleton motion, real-time or near real-time, optional GPU — [CMU project page](https://www.cs.cmu.edu/~junggon/projects/fastsimuldbody/fastsimuldbody.htm), [SIGGRAPH archive](https://history.siggraph.org/?p=113220).

### Inferences
- Rough 2026 CPU cost (my estimate, scaled from the 2005/2014 numbers above, not measured): XPBD over a ~500-2,000 particle tet cage with ~10 substeps x 1 iteration is on the order of 0.2-2 ms single-threaded scalar; shape matching with 10-30 clusters is well under 0.1 ms. Both comfortably fit a per-character budget for a handful of on-screen characters.
- Stability ranking at a fixed 30-60 Hz game step: shape matching (unconditional) ≈ XPBD with substeps > projective dynamics (stable but damps stiff material) > PBD without substeps (soft, iteration dependent) >> explicit mass-spring (blows up when stiff).
- Quality ranking for flesh: Neo-Hookean XPBD tets / reduced FEM > PD tets > PBD edge+volume > shape-matching clusters > mass-spring; jiggle bones sit beside, not on, this scale (art controlled, no volume).
- Best fit for UE2 flesh: shape matching per region (belly, each breast, each cheek, gibs as standalone soft chunks), driven by bone-attached rest frames; XPBD tet cage if the team wants wound/impact dents with volume preservation.

### Gaps
- No modern (2024-26) benchmark found comparing these methods on CPU at "a few thousand vertices"; costs above are extrapolated.
- Vivace code availability/licence not found (no public repository located).
- Projective Dynamics paper's own timing numbers not retrieved.

## 3. Embedding a coarse cage/proxy, and volume-preservation skinning tricks (delta mush, implicit skinning, velocity skinning)

### Takeaway
Standard practice is to simulate a coarse tet cage or a sparse particle set and move the render mesh by barycentric (tet) or cluster-transform embedding; the render mesh is then just "skinned" to the cage. Geometric correctors (delta mush, implicit skinning) fix LBS collapse and add bulges/contact but are not dynamic; velocity skinning adds dynamic-looking floppy/squashy motion with no state at all.

### Cited Findings
- Shape matching: only a subset of vertices are simulated, the rest follow the cluster transforms — [Müller 2005](https://matthias-research.github.io/pages/publications/MeshlessDeformations_SIG05.pdf).
- Abu Rumman/Fratarcangeli 2014: triangle render mesh assigned to the tet mesh; tet mesh used for simulation and volume preservation, triangle mesh for rendering; tets generated with CGAL — [Brunel full text](https://bura.brunel.ac.uk/bitstream/2438/21211/1/FullText.pdf).
- Ten Minute Physics lesson 12 "softBodySkinning" (HTML demo + PDF) and lesson 13 "Tetrahedralize" (+ a `BlenderTetPlugin.py`) cover embedding a high-res visual mesh in a simulated tet mesh and generating tets from a surface — file listing of [matthias-research/pages/tenMinutePhysics](https://github.com/matthias-research/pages/tree/master/tenMinutePhysics); lesson 10 "softBodies" is a tet XPBD soft body.
- Delta Mush (Mancewicz et al. 2014): skin with simple weights, smooth the mesh to remove artifacts, then add back stored rest-pose detail "deltas"; a low-pass post-corrector usable after any deformer; adopted in Maya — [Autodesk Maya Delta Mush docs](https://help.autodesk.com/cloudhelp/2016/ENU/Maya/files/GUID-139B703C-28E7-4787-8FD4-C2991BD6C990.htm), [EA SEED Direct Delta Mush slides (Le 2019)](https://media.contentapi.ea.com/content/dam/ea/seed/presentations/le2019-siggraph2019-direct-delta-mush-skinning-and-variants.pdf).
- Implicit Skinning (Vaillant et al., SIGGRAPH 2013): mesh approximated by per-bone implicit surfaces (HRBF) composed each frame to correct geometric skinning; handles skin contact and muscle bulges in real time, purely geometric, no collision detection — [Rohmer publication page](https://imagine.inrialpes.fr/people/Damien.Rohmer/documents/publications/13_siggraph_implicit_skinning/13_siggraph_implicit_skinning.html).
- Velocity Skinning (Rohmer et al., "Velocity Skinning for Real-time Stylized Skeletal Animation"): adds deformations from bone linear and angular velocities along the hierarchy; two components: drag (from linear and rotational motion) and stretch/squash (from velocity magnitude relative to joint centroids); reuses existing skinning weights, no rig preprocessing; "single pass vertex shader", also interactive on CPU — [velocityskinning.com](https://velocityskinning.com/).

### Inferences
- For UE2 the cheapest embedding is per-region shape matching where every render vertex in a region stores rest offset in the cluster frame (like an extra bone); this is literally "extra bones whose transforms come from the simulation", so it can piggyback on the existing skinning path.
- Delta mush needs neighbourhood smoothing each frame (multi-pass over adjacency) — a CPU pass, not a vertex-shader term in SM2/3; Direct Delta Mush precomputes it into per-vertex matrices but these are 4x4-per-bone-per-vertex style data (heavy for SM2/3 constant limits). Implicit skinning needs field evaluation/gradient marching per vertex: CPU or modern GPU.

### Gaps
- Implicit Skinning code licence not checked (no repository located in this pass).
- Velocity Skinning venue: believed to be Computer Graphics Forum / Eurographics 2021, not confirmed on the fetched page.

## 4. Stateless vertex-shader methods vs methods needing CPU state

### Takeaway
Stateless (pure vertex shader, SM2/3 viable): velocity skinning drag/squash and any procedural wobble driven by per-bone velocity/acceleration constants (e.g. `offset = mask * sin(t*f + phase) * amp(|bone accel|)`), plus static corrective tricks. Everything that "rings out" after motion stops (true jiggle, shape matching, PBD/XPBD, PD, FEM) needs persistent state, so it must live on the CPU in a UE2-era engine (no compute shaders or render-to-vertex-buffer readback worth relying on).

### Cited Findings
- Velocity skinning GPU reference is a GLSL 330 vertex shader: per vertex, LBS first, then for each joint with angular velocity omega it rotates the vertex about the joint's angular-velocity axis by `-0.1*|omega|*|p - joint|`, weighted by a per-vertex "velocity weight"; inputs are bone matrices, rest matrices, per-joint angular velocity and per-vertex skinning + velocity weights (stored in texture buffers) — [drohmer/velocity_skinning_gpu shader.vert.glsl](https://github.com/drohmer/velocity_skinning_gpu/blob/master/scenes/shared_assets/shaders/velocity_skinning/shader.vert.glsl).
- The method is "implemented as a single pass vertex shader" and "works out-of-the-box on existing skinning data" — [velocityskinning.com](https://velocityskinning.com/).

### Inferences
- The shader needs no previous-frame vertex data: only current bone transforms and bone velocities (computed on CPU by differencing last frame's bone transforms and uploaded as constants). So it is stateless on the GPU side; the only CPU "state" is the previous bone pose.
- SM2/SM3 port: the reference loops over all joints and reads texture buffers (not available in D3D9 SM2/3). A port should upload per-bone angular velocity + joint position as vertex shader constants (SM2 has 256 float4 constants; UE2 already uses many for bone palettes), store 1-4 velocity-weight indices/weights per vertex as an extra vertex stream (like skin weights), and apply only those influences. The CPU version (velocity_skinning_cpp, MIT) avoids the issue entirely and is a natural fit if UE2 skins on the CPU.
- Velocity skinning reacts instantly and stops instantly when the bone stops (no overshoot) unless the CPU low-pass filters/springs the uploaded velocities; giving each bone a damped spring on its "effective velocity" on the CPU (a few floats per bone) yields a convincing settle/overshoot cheaply — this is the hybrid recommended for UE2: CPU springs per bone (state), GPU or CPU velocity-skinning term (stateless per vertex).
- Wound/gib deformation: dents can be done statelessly as a vertex-shader term with a few "impact" constants (position, radius, depth, decay time) per character; persistent wounds need a CPU-side list but no simulation.

### Gaps
- No source found documenting whether UE2's (Unreal II) skinning runs on CPU or in vertex shaders in the retail build; this determines whether the term goes in a shader or a native CPU pass (check the U2 fork notes).

## 5. Open-source implementations and licences

### Takeaway
Plenty of permissive code: Ten Minute Physics (MIT), PositionBasedDynamics (MIT), velocity skinning C++/GPU (MIT), Kawaii Physics (MIT), UniVRM spring bones (MIT), Bullet soft bodies (zlib), ShapeOp (MPL-2.0), admm-elastic (MIT), PhysX (BSD-3), Gaia/VBD (Apache-2.0). libigl is MPL-2.0 core with GPL-3 parts. FleX is under NVIDIA's "1-Way Commercial" source licence and GPU-only — avoid. All licences found are compatible with the user's GPL/share-alike non-commercial mods except caution on FleX.

### Cited Findings
| Code | What it gives | Licence | Source |
|---|---|---|---|
| Ten Minute Physics (Matthias Müller) | Single-file JS demos: XPBD tet soft body (10), soft-body skinning / embedding (12), tetrahedralizer + Blender plugin (13), cloth, self-collision | MIT (header in each HTML: "Copyright 2021 Matthias Müller - Ten Minute Physics", standard MIT text) | [GitHub matthias-research/pages](https://github.com/matthias-research/pages/tree/master/tenMinutePhysics) |
| PositionBasedDynamics (Jan Bender, InteractiveComputerGraphics) | C++ library: shape matching, FEM-based PBD, XPBD, strain-based dynamics, tet models, joints; deps Eigen, json, pybind11, glfw, imgui, Discregrid | MIT | [GitHub](https://github.com/InteractiveComputerGraphics/PositionBasedDynamics) |
| velocity_skinning_cpp / _gpu / _web (Rohmer) | Reference velocity skinning (CPU C++, GLSL 330 shader, web) | MIT (cpp, gpu verified via GitHub API; web not checked) | [velocityskinning.com](https://velocityskinning.com/), [GitHub drohmer](https://github.com/drohmer/velocity_skinning_cpp) |
| Kawaii Physics | UE spring-bone chains with colliders | MIT | [GitHub](https://github.com/pafuhana1213/KawaiiPhysics) |
| UniVRM (VRM SpringBone) | Unity spring bones | MIT | [GitHub](https://github.com/vrm-c/UniVRM) |
| Bullet Physics (btSoftBody) | CPU soft bodies (tet/cluster/shape-matching-ish), mature C++ | zlib (except `Extras` and `examples/ThirdPartyLibs`) | [GitHub bullet3 LICENSE.txt](https://github.com/bulletphysics/bullet3/blob/master/LICENSE.txt) |
| ShapeOp | Projective-dynamics solver, C++ | MPL-2.0 | [GitHub EPFL-LGG/ShapeOp](https://github.com/EPFL-LGG/ShapeOp) |
| admm-elastic | ADMM / projective-dynamics hyperelastic | MIT | [GitHub](https://github.com/mattoverby/admm-elastic) |
| libigl | Geometry processing (tets via TetGen bindings, ARAP, etc.) | Repo has LICENSE.MPL2 and LICENSE.GPL: MPL-2.0 core, GPL-3 for copyleft modules (GitHub detects GPL-3.0) | [GitHub libigl](https://github.com/libigl/libigl) |
| NVIDIA PhysX SDK (5.x) | Engine incl. soft bodies (GPU) | BSD-3-Clause | [GitHub NVIDIA-Omniverse/PhysX](https://github.com/NVIDIA-Omniverse/PhysX) |
| NVIDIA FleX | GPU unified particle solver (CUDA/D3D11) | "Nvidia Source Code License (1-Way Commercial)": allows reproduce/derive/distribute, but the Work must stay under that licence with notices; terminates on patent claims | [GitHub NVIDIAGameWorks/FleX LICENSE.txt](https://github.com/NVIDIAGameWorks/FleX) |
| Gaia (Vertex Block Descent) | Modern GPU solver | Apache-2.0 | [GitHub AnkaChan/Gaia](https://github.com/AnkaChan/Gaia) |

### Inferences
- For a UE2 native plugin: lift algorithms (not libraries) from Ten Minute Physics (MIT, tiny, readable) and Kawaii Physics (MIT); use PositionBasedDynamics or Bullet only as reference — both pull in modern C++/Eigen which may be awkward to build against a 2004 MSVC ABI (the user builds with Zig as C compiler, so a self-contained C port is likely easiest).
- FleX: GPU-only and its licence is not a standard OSI licence; it is modern-only anyway. Flag: not fit.
- libigl: only safe if restricted to MPL modules; GPL-3 parts are fine for a GPL mod but contaminate otherwise.

### Gaps
- Kawaii Physics source is MIT, but its basis talk (Idolmaster) is not open; fine for use.
- velocity_skinning_web licence not checked.
- NVIDIA Flow licence not checked (it is a fluid/smoke tool, not relevant to flesh).
- Vivace and Implicit Skinning code: no public repositories located.

## Summary comparison (for the report writer)

| Method | Flesh quality | CPU cost (est. 2026, per character) | Stability at 30-60 Hz | State? | UE2 fit | Code (licence) |
|---|---|---|---|---|---|---|
| Jiggle/spring bones | Good for belly/breast/cheek if rigged; no volume | ~µs, dozens of bones | Very stable (fixed length, clamped) | Per-bone CPU state | Best | Kawaii (MIT), UniVRM (MIT), TMP (MIT) |
| Velocity skinning | Stylised drag/squash, no overshoot unless velocities are sprung | Per-vertex loop over few bones | Stateless, unconditional | None (prev bone pose) | Excellent (VS or CPU) | drohmer (MIT) |
| Procedural wobble / impact dents | Cartoony to OK | Trivial | Stateless | None | Excellent | write own |
| Shape matching (clusters) | Good blobby jiggle, volume-ish | <0.1 ms | Unconditionally stable | Particles | Very good | PBD lib (MIT), Bullet (zlib) |
| PBD / XPBD + substeps on tet cage | Good; Neo-Hookean very good; dents, volume | ~0.2-2 ms for 0.5-2K particles (est.) | Stable with substeps | Particles | Good (native CPU pass) | TMP (MIT), PBD lib (MIT) |
| Mass-spring explicit | Poor, wobbly, unstable stiff | cheap | Poor | Particles | Avoid | Bullet (zlib) |
| Fast mass-spring / projective dynamics | Good | Prefactored sparse solve | Stable, damps | Particles + factorisation | Possible, heavier | ShapeOp (MPL-2.0), admm-elastic (MIT) |
| Reduced FEM (Kim & Pollard) | Very good | Real-time 2011 | Explicit, needs care | Reduced coords | Research-grade effort | none found |
| Delta mush / implicit skinning | Fixes LBS collapse, bulges/contact; not dynamic | CPU smoothing / field eval | Static | None | Delta mush OK on CPU | Maya (commercial); none checked |
| Vivace, VBD, FleX, PhysX GPU soft bodies | High | GPU compute | Stable | GPU state | Modern-only | Gaia (Apache-2.0), PhysX (BSD-3), FleX (NVIDIA 1-way) |
