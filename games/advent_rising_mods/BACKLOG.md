# GoreOverhaul backlog (2026-10-10, project on a break)

Written when the user paused Advent Rising modding after GoreOverhaul 3.0 (Experimental).
Shelved code is still in the repo, switched off by default.

## Queue (user 2026-10-11: "lets queue up ragdolls improvements and ue4 ideas")

Ragdolls first (TENSION.md, `ModReact`; parts 1-2 built in 75f44ad, off by default):
1. Make the tension readable: option SpasmU=1.0 so a reflex always shows; wincap clips of
   10 human deaths with bTension on vs off, side by side, for the user to judge.
2. DONE 10-11: Seekers are powered too (bPoweredSeekers, default on when bPoweredRagdoll is):
   seeker skeleton, toward the game's own Death_Impact-family clips; front arms hang free.
3. DONE 10-11 (7298458): per-region timing, `RegionLimp[6]` scales LimpTime (legs 1.6, arms 0.6,
   head 0.7), so the knees buckle last; `DeathEffort` 0.8 humans, `SeekerDeathEffort` 1.0.
4. TENSION.md part 3: flesh springs (ModJiggle) on Seeker corpses, softer when limp, a
   wobble when a part hits the floor.
5. A 2-minute fight with no crash; then decide whether bPoweredRagdoll/bTension ship on.

Then graphics (`UE4-RENDER-IDEAS.md`, d3d8to9 fork, each off by default):
1. Lens flare and glare (the fork has none).
2. Half-res smoke/particle shading with a depth-aware upscale (Fox Engine: min/max depth,
   two half-res targets; video ljWylilACdI). Aimed at the smoke fps dips from the play-test.
3. Temporal SSAO using TAA's reprojection, plus GTAO's thickness heuristic.
4. Local exposure (UE5 5.1).
5. Temporal reject for the GI cascades.
6. Burley-style skin SSS (red radius wider than blue).
7. Small checks: MSAA edges vs our screen passes, linear-light MSAA resolve (video SxCMaTEoBoI).
8. Shadow caching (user 10-11, video Ls4QS3F8rJU): first measure what the game's own shadows
   cost per frame; then keep static shadows cached instead of redrawn each frame, and leave
   floors/terrain out of the shadow pass where they can't cast onto anything. Fox Engine trick
   (video aB5qxp6SPPQ): per-draw cull flip, floors front-face culled, characters back-face
   (front-face culling on faces gives light leaks/glow).
9. Geometric specular AA (user 10-11, video jNR5EiqA05c): Vlachos-style roughness boost from
   normal derivatives (ddx/ddy, a few lines) in the pbr shaders, so shiny edges stop sparkling.
10. Normal/roughness mip pre-filtering (same video): an offline texture pass that widens
   roughness where a normal map's mips average out its bumps, so distant surfaces don't shimmer.
Fox Engine / MGSV (user 10-11, video aB5qxp6SPPQ):
11. SSAO blur in one fetch: pack depth next to AO in the same target, so the bilateral blur
   reads both with one sample.
12. Rough SSR: blur reflections through a mip chain picked by roughness; stencil-mask the sky
   out of the trace.
13. One resolve pass: fog + AO + GT tonemap merged into a single full-screen pass, then the
   colour grade as a LUT lookup (fewer full-screen passes).
14. Shadow cascade edges: noise-dither the cascade blend so the seams stop banding.
Destruction look (user 10-11, video il-TXbn5iMA, Mike Turitzin's dynamic SDF engine):
15. SDF craters, wanted as a better replacement for our parallax holes ("our parallax system is
   not that great"). Each hit/blast adds an SDF edit (sphere/capsule carve) in a small list; a
   fork pass ray-marches the edits against the depth buffer and redraws the pixels inside as a
   crater with a fake interior (own normals, depth-correct, lit, rim and debris shading).
   Visual only: no see-through holes, game collision unchanged (visual hole and physics hole are
   separate things, his main lesson). Start with craters on walls/floors from explosions;
   compare against `decal_parallax` and the blood-fluid parallax plan. Real breakables stay
   destruction item 7 (pre-broken mesh swap).
16. Parallax that writes depth (user 10-11, video TUAyiCswYt4, Crimson Desert: most likely
   silhouette parallax occlusion mapping). Our `decal_parallax.hlsl` and the world parallax only
   shift the colour: the depth they show never reaches the depth buffer, so edges stay flat, SSAO,
   fog, SSR and the SDF craters see a flat wall, and the effect holds at any distance. Steps:
   (a) output the marched depth (`DEPTH` register; ps_2_0 has oDepth) where the parallax hit lands,
   only on draws that write depth (decals usually don't: then feed the hit depth to the fork's
   kept depth copy instead); (b) silhouettes: `clip()` pixels whose march leaves the texture's
   0..1 range at a decal/surface edge, so edges show real notches; (c) fade the depth scale and
   step count with distance (full near, flat past ~1500 u), which also saves cost. Check
   that early-Z is lost only on the parallax draws. Pairs with item 15: a crater's rim can then
   use the same depth.
   10-12 step 0 done: world_parallax self-shadow (fork `surfacelight=X Y Z S`, S<0 = debug tint).
   Works, but the level-1 ship panels have so little relief that the shadow is a thin line at
   the strip edges; overhead light gives almost none. Needs deeper height textures to pay off.
   10-12 rocks + terrain (level04sectiona): rock_tone_parallax.hlsl (rock_tone grading + depth + self-shadow; the name needs `_tone` for the fork to take the TFACTOR stage setup) and sand_tone_parallax.hlsl (same, no grading, for texgrade= textures). The spawn's rocks are 58fc527c (8ba83c44/0847dd68 are drawn elsewhere on the level); ini rule `surface=58fc527c sand_tone_parallax.hlsl`. Terrain: TERRAIN_SHADOW in terrain_src.hlsl, 2 steps toward the fixed sun (4 steps = 485/495 slots and the driver's CreatePixelShader fails, so the stock terrain draws; 471/481 load). Result: rocks get the depth; the self-shadow is faint (the texture spans only 0.51-0.32 brightness), terrain change barely visible. Ini rules not shipped yet.
Maybe later: rain wetness (lower roughness outdoors from a top-down depth map), lens drops.
Animation ideas (video 52Zw5eHHjgQ, Skyrim "Fluid Motion"): smooth path following (no
stop-and-go when fleeing), landing crouch, speed-synced legs, per-leg IK on surfaces for
hounds (extends ModFeet). Comments: big leans and bendy player legs read as goofy, so keep subtle.

## Destruction and gore still missing (feasible, cheapest first)

Sources: `research/black-ps2-destruction.md` (ranked list) and `GORE-DESIGN.md` ("Still to do").

1. **Dust per surface**: every hit throws the same grey puff (`ModImpactPuff`). Pick an
   emitter by hit material: concrete grey, dirt brown, wood tan. Small script job.
   DONE 10-12: `ImpactPuff` tints/sizes by `Material.SurfaceType`, skips metal/glass/water/shield/lava; seen on terrain dirt in a pilot run.
2. **Armour dust**: a dust/padding puff on Seeker armour hits, next to the sparks.
   BUILT 10-12 (`ModArmor.bArmourDust`, `Dust()` after `Sparks`), not yet seen in game: needs an armour-plate hit.
3. **Blast bloom flash**: brief post-shader bloom gain spike (~0.5 s) on explosions.
4. **Cheap smoke**: smaller, shorter-lived sprites, fade near the camera, cap explosion
   emitters, early alpha discard. Aimed at the big-explosion fps dips (cause unconfirmed).
5. **Cap the game's own scorch marks**, which stack into black blotches in Seeker fights.
6. **Sound layering**: random impact sample sets per surface, harsher hit sounds.
7. **Breakable set pieces**: pillars/walls swap to a pre-broken (or chipped) mesh after N
   hits or a blast, plus a dust burst. Biggest item: needs broken meshes per object.
8. **Gore polish**: menu switches per effect or one gore-intensity slider; 10-15 min soak
   fight (caps, fps, memory); edge cases: cutscenes, save/load mid-fight, level changes.
9. **Blood fluid step 4**: unique parallax gib textures ("rage super textures"),
   `research/blood-fluid-plan.md`.

## Shelved in the scope cut (2026-10-10: gore / graphics / destruction only)

- Enemy AI psychology: ModMinds `bMinds` (fear/anger, fall back, flanking), hound packs,
  wall-kicks, ModNeeds `bNeeds`. Design: `AI-MINDS-DESIGN.md`.
- Hit reactions: ModReact `bFlinch`, `bKnockdown`, `bStagger`.
- Generated death animations: ModReact `bDeathAnims` (Kimodo clips).
- Energy blade + swings: ModMelee `bBlades` (user: "remove the sword").
- AI leaning: ModMoves `bAILean` (Gideon keeps `bLean`).
- Debug overlay: ModSettings `bGizmos` ("too distracting").

## Parked earlier

- Seeker armour plate look (user: "pink sheen"); hits and sparks still work. `AdventMod/ARMOUR.md`.
- Light shafts in the atmos fog (never seen on camera). `GRAPHICS-PASS.md`.
- MSAA in the d3d8 fork: smooths since fork ba7b9df (stand-in padded 32 px past the NVIDIA screen-size cut-off). Fork 6540a83: the whole post chain (bloom, grading, SMAA, gi, ssao) had been dead under msaa (Offscreen() saw the wider stand-in); fixed. Fork 80c934f: depth-writing draws are replayed into a readable INTZ depth (no RESZ, StretchRect refused on the 4070 Ti), so gi/ssao/atmos/sss run with msaa=4 (~58 fps level14sectiond). Not in a release yet.
- UE4 4.27 render read (ideas only, own words): see UE4-RENDER-IDEAS.md. Top picks: contact shadows, height fog with sun inscatter, eye adaptation, filmic curve + 3D LUT strip.
- GI ships off by default.
- Squishing small gibs underfoot.

## Never started

- UniMate death clips for Seekers and hounds (not installed).
- PAMI death animations (weights unreleased).
- Hang at the level03sectionb -> 03c door transition (never reproduced).

- 2026-10-10: SSAO uses characters' own normals (RT1 char-info target; ssaonormals=1 default). Fork b1dca96, shaders 38b60fe. Not in a release yet; only pbr=-ruled characters gain (world/terrain shaders have no normals).
