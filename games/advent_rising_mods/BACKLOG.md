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
Maybe later: rain wetness (lower roughness outdoors from a top-down depth map), lens drops.

## Destruction and gore still missing (feasible, cheapest first)

Sources: `research/black-ps2-destruction.md` (ranked list) and `GORE-DESIGN.md` ("Still to do").

1. **Dust per surface**: every hit throws the same grey puff (`ModImpactPuff`). Pick an
   emitter by hit material: concrete grey, dirt brown, wood tan. Small script job.
2. **Armour dust**: a dust/padding puff on Seeker armour hits, next to the sparks.
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
