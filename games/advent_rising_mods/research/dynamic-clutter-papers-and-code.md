# Dynamic clutter: persistent decals, casings, debris (papers, talks, code)

Research for AdventMod (Advent Rising, UE2, D3D8 via our d3d8to9 layer). Goal: Brutal-Doom-style
persistent battle damage (blood, bullet holes, casings, gibs) that accumulates cheaply.
Compiled 2026-10-03. Links verified by search on that date unless marked "(unverified)".

---

## 1. Papers and talks

### Decal rendering (how shipped games did it)

| Source | What's useful for us |
|---|---|
| **Max Payne 2 (Remedy, 2003)** — [PCGamesN "The Gunsmiths: Max Payne 2"](https://www.pcgamesn.com/max-payne-2-the-fall-of-max-payne/the-gunsmiths-max-payne-2) | The closest era match. Programmer Olli Tervo gave **every room its own decal buffer**, saved in the savegame, and **merged all of a room's decals into one mesh** to keep GPU cost down. There was a per-room cap, set high enough that you rarely hit it. This is the model to copy: a per-area pool, one draw per area, a cap per area. |
| **Rendering Wounds in Left 4 Dead 2**, Alex Vlachos, GDC 2010 — [PDF](https://alex.vlachos.com/graphics/Vlachos-GDC10-Left4Dead2Wounds.pdf) | Wounds on characters: pose-space ellipsoids cull pixels out of the body, wound models fill the holes, and a projected texture blends the edges and adds blood. The point was to put it on the GPU and use **no extra per-instance texture memory**. Useful for gore on bodies, not for floor clutter. |
| **The Devil is in the Details: idTech 666** (DOOM 2016), Sousa & Geffroy, SIGGRAPH 2016 — [Advances course page](https://advances.realtimerendering.com/s2016/); breakdown in [Adrian Courrèges' DOOM graphics study](https://www.adriancourreges.com/blog/2016/09/09/doom-2016-graphics-study/) | Decals are boxes binned into the same clustered-forward grid as lights, and their textures live in **one decal atlas**. Takeaway for us: put every decal texture (holes, blood, casing sprites) in **one atlas** so they can batch. |
| **Screen Space Decals in Warhammer 40k: Space Marine**, Pope Kim (Relic), GDC 2012 — [PDF](https://www.gamedevs.org/uploads/screenspace-decals-space-marine.pdf) | Deferred and screen-space decals: draw a box, rebuild the position from depth, project. Needs readable depth, which D3D8-era Advent doesn't have unless our layer adds a depth pass, so this is a later option. Bart Wronski's [fixing screen-space deferred decals](https://bartwronski.com/2015/03/12/fixing-screen-space-deferred-decals/) covers the artefacts (edge stretching, mip problems at depth edges). |
| **Volume Decals**, Emil Persson, *GPU Pro 2* — [chapter](https://www.taylorfrancis.com/chapters/edit/10.1201/b11325-13/volume-decals-emil-persson) | Projects a 3D volume texture through the depth buffer so a decal wraps over edges and corners. Same depth requirement as above. |
| **Destruction Masking in Frostbite 2 using Volume Distance Fields**, Robert Kihl (DICE), SIGGRAPH 2010 — [slides](https://www.slideshare.net/DICEStudio/siggraph10-arrdestruction-maskinginfrostbite2) | Damage is a set of **spheres → a signed distance field in a volume texture**, sampled in the surface shader, with an early-out branch when a pixel is outside every sphere. This is the idea behind "a few numbers instead of many decals": one shader constant array of hit spheres per surface could also drive a "scorch near hits" effect in our layer. |
| **Overgrowth blood (Wolfire blog)** — [late June 2017](https://www.wolfire.com/blog/2017/06/Overgrowth-Progress-Late-June-2017/), [early July 2017](https://www.wolfire.com/blog/2017/07/previous-two-weeks-in-overgrowth---early-july/) | A clustered decal limit (256 per cluster) caused glitches. Their fixes: **merge pooling blood decals into one decal**, don't merge spatters, and clear blood on level reset. The same merge-when-overlapping rule applies to our pools. |
| **Portal 2 paint / gels** — [Valve Developer Wiki: Gel](https://developer.valvesoftware.com/wiki/Gel_(Portal_2)); Grimes, *Making and Using Non-Standard Textures*, GDC 2011 [PDF](https://cdn.akamai.steamstatic.com/apps/valve/2011/gdc_2011_grimes_nonstandard_textures.pdf) | Paint is stored in a **per-surface "paintmap" at lightmap resolution**, with noise and embedded sprites hiding the low resolution. This is the closest shipped precedent for "splat into a runtime texture that lives in lightmap UV space". UE2 BSP has lightmap UVs too, so it's possible in principle. Splatoon is widely believed to work the same way, but there is no primary source (Unity thread [here](https://forum.unity.com/threads/how-do-they-do-the-painting-in-splatoon.460663/)). |
| **Soldier of Fortune GHOUL** (Raven) — [Wikipedia](https://en.wikipedia.org/wiki/Soldier_of_Fortune_(video_game)) | 26 gore zones in SoF and 36 in SoF2 ("bolt-on gore" swapped in per zone). No technical talk found. It's a design reference for gibs and dismemberment, not for clutter. |
| **Project Zomboid corpse sprites** — [Indie Stone blog: "Sprite of the Living Dead" (2014)](https://projectzomboid.com/blog/news/2014/01/body-movin/) (403 to bots; read in a browser) and [Steam thread "Zombies change to blurry sprites when dead"](https://steamcommunity.com/app/108600/discussions/0/4366878147920681568/) | When a zombie dies its 3D model is **rendered once into a sprite** and the corpse becomes a flat image. Players notice it looks blurry, so bake at a decent resolution. The corpse's *inventory* is still a live object; only the rendering is flattened. Keep that split (logic object vs. baked visual) for anything lootable. |
| **Red Faction: Guerrilla MP level design**, GDC 2010 — [GDC Vault](https://gdcvault.com/play/1012330/Multiplayer-Level-Design-in-Red) | Covers debris-management constraints in a destruction game. Mostly design; debris is culled or cleaned on budgets. |
| **Octahedral Impostors**, Ryan Brucks (Fortnite), 2018 — shaderbits.com/blog/octahedral-impostors (unverified URL; referenced [here](https://twitter.com/non_manifold/status/1092803852888350721)) | How to bake a 3D object into view-dependent sprites. Too much for casings, which are tiny enough that one top-down sprite works. Relevant only if we ever flatten **bodies** PZ-style but still want them to look 3D from low angles. |

### Accumulation and weathering (academic, for "dirt builds up")

- **Visual Simulation of Dust Accumulation**, Hsu & Wong, IEEE CG&A 1995 — [PDF](https://ttwong12.github.io/papers/dust/dust.pdf). Dust amount = f(surface slope, stickiness), adjusted by exposure and scraping. This maps directly to a shader: `dirt *= saturate(normal.z)` so dirt and blood land on floors, not walls.
- **Visual Simulation of Weathering by γ-ton Tracing**, Chen et al., SIGGRAPH 2005 — [PDF](https://ttwong12.github.io/papers/gammaton/gammaton.pdf). Fires "aging particles" through the scene like photons and records where they land. Offline, but the idea (stamp where particles land, store it in a texture) is exactly the runtime splat-map approach.
- **Time-varying weathering in texture space** (SIGGRAPH) — [entry](https://history.siggraph.org/learning/time-varying-weathering-in-texture-space/). Background reading only.

---

## 2. Techniques for an old engine

### 2.1 Bounded decal pools with eviction (do this first)

Every shipped engine caps decals with a ring buffer and evicts the oldest:
- **Quake 3** `cg_marks.c`: fixed `cg_markPolys[MAX_MARK_POLYS]` (256), a free list and an active list, and the oldest mark is recycled when full. Marks fade by alpha near end of life. Code: id's GPL release ([cg_marks.c mirror](https://git.okseby.com/okseby/Quake-III-Arena/src/commit/d4c6711e5138e4198a9e6e990d41d7e5b305989c/code/cgame/cg_marks.c), canonical `id-Software/Quake-III-Arena` on GitHub).
- **GZDoom** `cl_maxdecals`: when the cap is hit the oldest *spawned* decal is removed. Mapper-placed decals don't count and are never removed. Decals can be flagged permanent. ([ZDoom wiki: Decal](https://zdoom.org/wiki/Decal))
- **DarkPlaces**: `cl_decals_max`, `cl_decals_fadetime`, `cl_decals_bias` (depth-fight offset), `r_drawdecals_drawdistance`, and a "new system" that splats decals onto models per entity ([feature list](https://hemebond.gitlab.io/darkplaces-www/engine/features/)).
- **Source**: tempent brass defaults to about 2.5 s life; `cl_ejectbrass 0` turns it off ([TF2 issue noting the cvar path in `c_te_legacytempents.cpp`](https://github.com/ValveSoftware/Source-1-Games/issues/5949)).
- **UT2004**: `LevelInfo.DecalStayScale` (config, 0–2) scales every decal's stay time ([wiki](https://wiki.beyondunreal.com/UE2:LevelInfo_internal_variables_(UT2004))).

Refinements that matter:
- **Per-type caps**, e.g. holes 64, blood 48, casings-on-floor 96, gibs 24. Then a minigun burst can't evict the blood pools.
- **Evict by "importance × age"**, not pure FIFO. Prefer evicting decals that are far from the player or out of view, and fade over 0.5 s rather than popping. Pools under corpses get high importance.
- **Spatial merge**: if a new splat lands within r of an existing same-type decal, grow or replace that one instead of adding a new one (Overgrowth's pooling-blood rule). For bullet holes, a "cluster" texture variant (3–5 holes) replaces 3+ nearby holes.
- **Spatial hash** (cell = 256 uu) for the merge lookup, so it isn't O(n).

### 2.2 One damage texture per surface or area (render-to-texture splatting)

Instead of N decal draws, keep one texture per area and **stamp** splats into it. The decal count becomes free; only texture memory grows.
- **Shipped precedent**: Portal 2 paintmaps (lightmap-UV space), Max Payne 2 (one merged mesh per room; the same "one draw per room" idea done with geometry).
- **Lightmap-UV space** (Portal 2 style) gives exact placement on any surface, but you need each hit's lightmap UV. In UE2 that's hard from script, and possible from the native/D3D side only if we can identify surfaces.
- **World top-down projection** (simplest for floors): one texture covering the level's XY bounds (or a 4096 uu tile around the player). The floor shader samples it with `worldXY / tileSize`, masked by `saturate((N.z - 0.7) * 4)`. Multi-storey levels: store the **floor height** in the RT's alpha or a second channel and reject when `|worldZ - storedZ| > 32`. Open-source equivalent: [nomand/RevealShader](https://github.com/nomand/RevealShader) (MIT), which draws world positions into a RenderTexture over world bounds and maps it back as a mask.
- **Mesh-UV painting** for props: [IRCSS/TexturePaint](https://github.com/IRCSS/TexturePaint) (MIT) and its [write-up](https://shahriyarshahrabi.medium.com/mesh-texture-painting-in-unity-using-shaders-8eb7fc31221c) render the mesh in UV space to find the texels a hit touches. [VFX Mike: Splatoon in Unity](https://vfxmike.blogspot.com/2017/04/splatoon-in-unity.html) does lightmap-UV paint with noise to break up the low resolution.
- **Resolution budget**: at 4 uu per texel a 1024² RT covers 4096×4096 uu, which is plenty for blood and soot. Bullet holes and casings need about 1 uu per texel, so they stay as real decals near the player and are only *baked* once they're far away or old.
- **Persistence**: RTs are lost on D3D device reset (alt-tab, resolution change). Keep a **CPU-side log of stamps** (type, pos, rot, scale; about 16 bytes each), replay it on reset and on savegame load. This also makes the clutter savable, as Max Payne 2's was.

### 2.3 Baking settled physics objects into decals or sprites (the Project Zomboid trick)

Lifecycle used by PZ and essentially by Brutal Doom's flat blood pools:
1. **Live**: real mesh actor, moving.
2. **Settled**: physics off, still a mesh. Keep only the last K (e.g. 24) as meshes.
3. **Baked**: mesh destroyed, replaced by a **top-down sprite** of the same object. That's either one projector, one GZDoom-style `FLATSPRITE`, or best, one stamp into the area's damage texture (2.2). Bake when the object is evicted from the mesh pool, or when it's more than about 1500 uu away and out of view, so the swap is never seen.
- Casings are tiny and almost flat when lying down, so **one pre-rendered top-down sprite per casing type plus random roll** is enough. No impostor atlas is needed.
- Bodies or large gibs: pre-render a few top-down poses offline, or render the ragdoll's final pose once into a sprite (PZ). Octahedral impostors only if they're seen from low angles.
- Match lighting: bake sprites with neutral lighting and let the projector or splat modulate with the surface's lightmap. Under UE2 `PB_Modulate`, the floor's lighting already applies.

### 2.4 Cheap ballistic casings (analytic arc + one bounce)

No per-tick collision. Do everything at spawn:
1. Ejection velocity `v0 = Owner.Velocity + R(eject dir ± 15°) * (150..220 uu/s) + up * (60..120)`. Inheriting player velocity is something Insurgency: Sandstorm patched in because it looked wrong without it ([IMFDB note](https://www.imfdb.org/wiki/Insurgency:_Sandstorm)).
2. Predict the arc `p(t) = p0 + v0·t + ½g·t²`. Trace it as **2–3 line segments** (t = 0→0.15→0.35→0.6 s) and take the first hit. That's 2–3 traces per casing, once.
3. At the hit (point P, normal N, time t1): reflect `v' = (v − (1+e)(v·N)N)` with restitution **e ≈ 0.3–0.45**, and scale the tangent part by **0.6–0.7** for friction. Then do **one** more short predicted hop (t2 ≈ 2·v'·N / |g|, one trace) and settle at the second landing.
4. Between events, move the casing by evaluating the parabola in `Tick` (`SetLocation`, no collision; `bCollideWorld=false`). Spin it with a constant `RotationRate`. On landing, snap to flat with random yaw and play a tink sound with pitch variation (Brutal Doom's casing sounds sell it more than the visuals).
5. If the predicted landing is over a ledge or a mover, the lie is invisible: no casing ever falls through a floor, because the final position is a traced floor hit.
- Alternative using UE2's native path: `Physics=PHYS_Falling, bBounce=true`, `HitWall`/`Landed` → reflect and `SetPhysics(PHYS_None)` after the 2nd bounce. Native collision per tick is cheap for ~20 live casings, but the analytic version scales to hundreds and is deterministic.

### 2.5 What shooters do with casings

- **Source / CS**: tempent brass with about 2.5 s life, always deleted ([cvar refs](https://www.gamerconfig.eu/command/counter-strike-source/cl_ejectbrass/)).
- **Insurgency: Sandstorm**: physical casings that inherit player velocity; short lifetime.
- **Brutal Doom**: casings are actors that bounce with sound and stay, and performance add-ons exist mainly to delete gibs, casings and decals after seconds ([ModDB Ultimate Performance Mod](https://www.moddb.com/mods/brutal-doom/addons/ultimate-performance-mod-for-pb-203); [Doomworld lag thread](https://www.doomworld.com/forum/topic/85373-gzdoombrutal-doom-lagsi-think-its-caused-by-gibs/)). This is the lesson: **unbounded persistent actors are the main perf cost in Brutal Doom**. Baking is how we keep the look without that cost.
- **Max Payne 2**: Havok casings and debris. Decals were persistent per room (above).
- **Receiver (Wolfire)**: physical casings at small counts. No technical write-up found.

---

## 3. Open-source code (with licences)

| Project | What to read | Licence / reuse |
|---|---|---|
| **GZDoom** ([github.com/ZDoom/gzdoom](https://github.com/ZDoom/gzdoom)) | `src/playsim/a_decals.cpp` (wall decal spawn, `cl_maxdecals` eviction, spreading across adjacent lines); `wadsrc/static/zscript/` for blood and flat-sprite actors; DECALDEF ([wiki](https://zdoom.org/wiki/Decal), [SpawnDecal](https://zdoom.org/wiki/SpawnDecal)); `+FLATSPRITE` for floor blood pools and settled casings ([forum notes on flatsprite floor flicker](https://forum.zdoom.org/viewtopic.php?t=56345&p=996465)) | GPL-3.0. Fine for our GPL mod. |
| **Brutal Doom forks** — [BrutalDoomPlatinum](https://github.com/EmeraldCoasttt/BrutalDoomPlatinum) (GPL-3.0, plus per-component LICENSE.* files) and [Brootal-Doomb](https://github.com/MekBoss/Brootal-Doomb) (states MIT; BD v20 ported to ZScript, has `sfx/CASING.zc` and DECALDEF) | Casing actors (bounce counts, sounds, `BounceFactor`, stop-and-rest states), blood pools, gib lifetimes | **Caution**: original Brutal Doom has no formal licence. Sgt Mark IV asks for credit when his assets are reused ([Doom Wiki](https://doomwiki.org/wiki/Marcos_Abenante_(Sergeant_Mark_IV))), and the forks' MIT/GPL can't relicense his assets. **Read for ideas and numbers; don't copy sprites or sounds.** Rewriting the logic in UnrealScript is fine. |
| [dodopod/ZScript-Weapons-Library](https://github.com/dodopod/ZScript-Weapons-Library) | Reusable casing ejection in ZScript | Check repo LICENSE before copying. |
| **Quake III Arena** (id GPL release) | `code/cgame/cg_marks.c`: `CG_ImpactMark` clips a quad to the world with `trap_CM_MarkFragments`, then stores it in a 256-entry ring with fade. The classic bounded mark pool. | GPL-2.0. |
| **DarkPlaces** ([github.com/DarkPlacesEngine/darkplaces](https://github.com/DarkPlacesEngine/darkplaces)) | `cl_particles.c` (decal particles, `cl_decals_*`), `gl_rmain.c` decal system (`R_DecalSystem_*`: per-entity decal triangles clipped to the model, max count, fade) | GPL-2.0. |
| **Doom 3 / idTech 4** (id GPL release) | `renderer/ModelDecal.cpp` (per-model decal fragments with fade and limits), `ModelOverlay.cpp` (blood on skinned meshes) | GPL-3.0 plus id's additional terms. |
| **UT2004 / UE2 script** — [Engine.Projector (UnCodex)](http://ericdives.com/UT2004-UnCodex/engine/projector.html), [UE2:Projector wiki](https://wiki.beyondunreal.com/UE2:Projector_(UT2004)), [UDN ProjectorsTutorial](https://docs.unrealengine.com/udk/Two/ProjectorsTutorial.html), [UDN projector properties](https://docs.unrealengine.com/udk/Two/MainProjectorProperties.html), [Wumpus2112/UT2004 script dump](https://github.com/Wumpus2112/UT2004) | `xScorch` (runtime bullet and scorch projector), `AbandonProjector(Lifetime)` (leave the projection on the surface and drop the actor), `AttachProjector/DetachProjector`, `MaxTraceDistance`, `bClipBSP`, `FadeInTime`. UDN says a runtime projector actor can be destroyed right after spawning and its projection stays. | Epic's script is under the UT2004 EULA, not GPL. Use it as a **reference only** and write our own. |
| [nomand/RevealShader](https://github.com/nomand/RevealShader) | World-bounds RT mask (the top-down accumulation idea) | MIT |
| [IRCSS/TexturePaint](https://github.com/IRCSS/TexturePaint) | Paint into a mesh's UV-space RT | MIT |
| [naelstrof/SkinnedMeshDecals](https://github.com/naelstrof/SkinnedMeshDecals) | Decals on skinned meshes by rendering into a per-mesh texture | Check LICENSE (GPL-compatible as of last look, not verified) |
| [antzGames/Godot-Compatibility-Decal-Node](https://github.com/antzGames/Godot-Compatibility-Decal-Node) | Instanced bullet-hole decals, about 1000 per draw call | Check LICENSE |
| [GarbajYT/godot-bullet-decals](https://github.com/GarbajYT/godot-bullet-decals) | Minimal bullet-hole spawn and align | MIT |
| [daniel-ilett/decals-urp](https://github.com/daniel-ilett/decals-urp), [ColinLeung-NiloCat/UnityURPUnlitScreenSpaceDecalShader](https://github.com/ColinLeung-NiloCat/UnityURPUnlitScreenSpaceDecalShader) | Short screen-space decal shaders (depth → position → box UV) | MIT (check each) |
| [Alfred Baudisch: Godot splat-map painting](https://alfredbaudisch.com/godot-engine/godot-engine-in-game-splat-map-texture-painting-dirt-removal-effect/) | Runtime splat-map RT tutorial | Blog (ideas only) |

Licence note: everything above except UT2004 script and original Brutal Doom assets is MIT or GPL, so it's fine to adapt into a GPL mod. Avoid copying Brutal Doom sprites or sounds, and anything from Unity Asset Store packs (no-reuse EULAs).

---

## 4. What to use for Advent (ranked by payoff ÷ effort)

Context from our code: `ModBloodDecal` is an orthographic `Projector` using **PB_Modulate (2× modulate, 50% grey = no change)**. UE2's alpha-blend projector path came out pink here, and `ModGore` already caps the count.

1. **Bullet holes = same projector class as blood, with a per-type pool** (low effort, high payoff).
   - Generalise `ModBloodDecal` into a `ModDecal` with a type, and give `ModGore` a manager with **per-type ring buffers** (holes ~64, blood ~48, settled casings ~64), oldest-first eviction, and fade-out by lerping toward 50% grey over 0.5 s if the texture can be swapped. Otherwise pop it while the player isn't looking.
   - Small `MaxTraceDistance` (8–16 for holes, already 40 for blood), `bProjectActor=False`, `bClipBSP=True`. One shared **atlas texture** won't batch in UE2 projectors, but it keeps the texture count down.
   - **Merge**: a new hole within ~6 uu of an existing one replaces it with a "cluster" texture variant. Blood within the pool radius grows the existing pool (already done for pools).
   - Try **`AbandonProjector`/destroy-after-attach** (the UDN/UT2004 trick) to see whether Advent's build keeps the projection after the actor dies. If it does, each decal costs a surface projector entry but no actor or tick. Test that the cap still works (we'd need to track and remove abandoned projections, so maybe keep actors).

2. **Shell casings: analytic arc + one bounce → settle → bake** (medium effort, high payoff).
   - Live casing: a tiny StaticMesh actor with no collision, moved along a precomputed parabola (2.4), 2–4 traces total, a tink sound per landing. Cap live casings at about 16.
   - Settled: keep the last ~16–24 as meshes. Older or far ones are **baked**: destroy the mesh and spawn a small projector with a top-down casing sprite (step 1's pool, type "casing").
   - Pitfall: under **2× modulate a brass sprite can only tint the floor** (texel 255 = 2× surface brightness). On dark floors a casing reads as a dark-orange smudge, not brass. Options: (a) accept it, since at baking distance it reads as clutter; (b) fix projector alpha-blend in our d3d8to9 layer (find why PB_AlphaBlend went pink; probably the texture stage alpha/colour args for the projector pass); (c) step 3.

3. **Floor "dirt" accumulation texture in the d3d8to9 layer** (high effort, highest ceiling).
   - One RT (1024², 4 uu/texel) over the level's XY bounds, or a scrolling 4096 uu window around the player. Each blood pool, scorch or baked casing becomes a **stamp** (a textured quad drawn into the RT) instead of a projector. The floor's pixel shader samples it by world XY, masked by `N.z > 0.7` and a stored floor height for multi-level maps.
   - Needs: (a) world position and normal in the pixel shader for BSP floors. Our layer must recognise the world-geometry draw calls and get the world matrix; Advent's BSP is drawn in world space, so the vertex position may already be world. (b) A channel to send stamps from UnrealScript to native. The existing native hook path (AdventNative) can expose a `Stamp(type, x, y, z, rot, scale)` call. (c) A CPU stamp log to replay on device reset and on load.
   - Payoff: unlimited persistent blood and soot at fixed cost (one texture fetch per floor pixel), and it can be saved like Max Payne 2's per-room buffers.
   - Check first: does Advent's Engine.u have **`ScriptedTexture`** (UE2's canvas-to-texture, with `DrawTile` into a texture)? If so, a script-only prototype is possible: one big downward projector per room with a ScriptedTexture as `ProjTexture`, stamping sprites with `Canvas.DrawTile`. Not checked: no exported Engine classes on disk. Run `AdventUCC batchexport Engine.u class uc ...` and grep for `ScriptedTexture`.

4. **Gibs** (medium effort): same life cycle as casings (live mesh with an arc and bounce → settled mesh, cap ~12 → baked top-down sprite projector). Pre-render 4–6 gib sprites offline.

5. **Bodies, Project Zomboid style** (high effort, optional): only if corpse count is a perf problem. Swap long-dead, far-away ragdolls for a pre-rendered top-down sprite projector plus a blood pool. Keep any gameplay object (pickups) as an invisible actor.

### Pitfalls

- **Projector cost scales with the geometry they touch.** UE2 re-clips a projector's frustum against BSP and static meshes on attach, and every attached projector adds a render pass over the triangles it covers. Keep `MaxTraceDistance` and DrawScale small. Never project onto actors. Avoid `bProjectStaticMesh` on dense meshes. Re-attach rarely (we already throttle pool growth to 6 Hz).
- **Z-fighting/flicker**: projectors re-render the surface's own triangles, so the depth matches. Flat sprites and decal quads need a bias (DarkPlaces `cl_decals_bias`; GZDoom's FLATSPRITE floor flicker).
- **Eviction pop**: evict out of view or fade. Don't evict pools under visible corpses.
- **Device reset / savegames**: anything living in an RT must be replayable from a CPU log.
- **Licences**: no Brutal Doom assets. UT2004 script is reference only.
- **Scope** (per our workflow notes): ship items 1 and 2 first. Item 3 is the "if it's fun" upgrade.
