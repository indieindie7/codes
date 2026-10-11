# GoreOverhaul backlog (2026-10-10, project on a break)

Written when the user paused Advent Rising modding after GoreOverhaul 3.0 (Experimental).
Shelved code is still in the repo, switched off by default.

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
- MSAA in the d3d8 fork (doesn't smooth; blocks GI). SMAA covers it.
- GI ships off by default.
- Squishing small gibs underfoot.

## Never started

- UniMate death clips for Seekers and hounds (not installed).
- PAMI death animations (weights unreleased).
- Hang at the level03sectionb -> 03c door transition (never reproduced).
