# AdventMod hand-off (2026-10-12): Advent Rising modding on a break

> **ARCHIVED 2026-10-17.** The user moved all modding to SWAT 4. The tech stack hand-off is in
> `games/swat4_mods/HANDOFF-FROM-ADVENT.md`. Last Advent work: plasma sears + bullet pass-through (f47c3ec).

The user is moving most modding work to Scorcher (user, 10-12: "i am going to move right now to modding
mostly just scorcher"). They will still play Advent Rising. This file is the way back in. It has two parts:
**graphics** and **gameplay**. Each part lists what is built and what is not.

Last release: **GoreOverhaul 3.0 (Experimental)**, master 8713733. Everything since then is committed on wt9
`master` (last 4b37616) and the d3d8 fork branch `gi-cascades` (last b42bb53). None of it is in a zip yet.

## Read first
| What | Where |
|---|---|
| Main skill: injection, build/test/ship, ragdoll plan | `~/.claude/skills/advent-mod/SKILL.md` + `tree/01-how-code-gets-in.md`, `02-build-test-ship.md`, `03-ragdoll-physics-plan.md` |
| Gore system (decals, runs, streaks, gibs) | skill `gore-system` |
| Starting the game for the user | skill `advent-test-launch`; memory `advent-launch-for-user` |
| Method (research, export, pilot, patch, measure) | skill `old-game-mod-loop`; memory `old-game-modding-workflow` |
| Skin shading | skill `skin-shading`; memory `skin-shading-sss-notes` |
| Running log + **last STATE line** | memory `advent-rising-project` (big: read its headings and the last STATE lines) |
| Physics plan | memory `advent-physics-plan`; `research/physics-plan.md`; `research/karma-internals.md` (local only, never commit) |
| Render takeaways | memory `rendering-takeaways-threat-interactive`; `research/threat-interactive-videos.md` |
| Devastation (UE2 + Karma) ragdoll/AI study | skill `devastation-re`; `C:\re\devastation\NOTES.md` ("Port list"); `C:\re\devastation\FROM-ADVENT.md` |
| Backlog (the to-do source of truth) | `BACKLOG.md` |
| Enemy AI research (DOOM tokens, F.E.A.R. GOAP, Horizon HTN, L4D director) | `games/reports/Game enemy AI architectures.md` |
| Design docs | `GRAPHICS-PASS.md`, `UE4-RENDER-IDEAS.md`, `GORE-DESIGN.md`, `AI-MINDS-DESIGN.md`, `AdventMod/TENSION.md`, `FEET.md`, `JIGGLE.md`, `ARMOUR.md`, `AdventMod/RELEASE.md` (switch tables) |

Rules that still hold:
- Don't replace stock files. Never commit game pixels or decompiled source.
- Push the fork only to the `fork` remote (`git push fork HEAD:gi-cascades`). Push wt9 with `git push origin HEAD:master`.
- Never build while Advent is running.
- Uploads to Nexus and YouTube are the user's job, and Nexus page text has no GitHub links.

---

## Part 1: Graphics
All of it lives in the d3d8to9 fork (`Documents\github\d3d8to9-gi`, branch `gi-cascades`) plus shaders in `AdventMod/U2Shaders/`. It is
switched by `System\U2Shaders.ini` (live reload), with game-side switches in `ModSettings` / `ModShadow*`.

### Built and shipped (on in 3.0)
- Shadows: shadow fix, PCSS soft shadows (indoors), NPC/crowd shadows, sun-only outdoors, respect baked light.
- Post chain: Natural grading preset, sharpen 0.4, SMAA, film grain / chromatic aberration / highlight shoulder (`post_final.hlsl`), colour-blind filters.
- Trilinear + aniso 16, widescreen, borderless, FOV 75, LAA + lagfix, 30 Hz blood updates.
- Screen-space SSS on skin (`sss=1`), gloss, character SSAO normals (RT1, fork b1dca96).
- Height fog + sun inscatter (`atmos`), soft particles, close-up terrain detail texture, sheen on chosen metal/wood textures.
- Gore rendering in the fork: wall runs, body streaks, goo strings, blood on hands, wet lens, live blood pools (wet-box only, c57f349).

### Built, but off by default or not judged by the user
- GI cascades (`GiLevel`, off; the user plays with 1) and SSAO "Ambient Light" (off; the user plays with it on).
- MSAA in the fork with the whole post chain working (6540a83, 80c934f; ~58 fps level14sectiond). Not in a release.
- SDF craters for blasts and bullet holes (ModGore bSdfCraters/bSdfBulletHoles, `craters.hlsl`, wt9 55b9d1d + fork e260466). Valid at 60 fps, but the test camera (`craters.ps1`) misses the holes. Needs `-Wait 150` and better aim.
- Parallax that shows depth:
  - `world_parallax.hlsl` with self-shadow (fork b42bb53, `surfacelight=X Y Z S`; S<0 debug tint). The ship panels are too flat for it to show.
  - `rock_tone_parallax` / `sand_tone_parallax` (5817622, 0e50459): rock cracks are visibly deeper. The self-shadow is not seen at spawn distance (rocks sit inside FADE 1500-4000).
  - Rule `surface=58fc527c sand_tone_parallax.hlsl` is installed in the game but not in the repo.
- Terrain self-shadow (TERRAIN_SHADOW, 2-step march): the change is not proven by an A/B.
- Light shafts in the fog: the code runs, but they were never seen on camera.
- Needs the user's verdict: fog strength per level, sheen, terrain-detail strength.

### Gotchas
- ps_2_a: shaders above ~471-481 slots fail CreatePixelShader, and the game silently draws stock. Check with `fxc -Fc`.
- A shader file for rock meshes needs "_tone" in its name, or the fork refuses the TFACTOR stage setup (u2shaders.hpp ~5851).
- `Actor.DrawDebugLine` draws nothing in this renderer. Use an Interaction PostRender instead.

### Not built (ranked lists live in BACKLOG.md "Then graphics" 1-16 and "Try later" 1-7)
- Lens flare / glare.
- Half-res particles with a depth-aware upscale (aimed at smoke fps dips).
- Temporal SSAO / GTAO with a thickness term; HBAO small radius.
- Local exposure / eye adaptation (retest pending).
- GI temporal reject plus a better upsample (plane+normal weights, leak rejection, YCoCg clamp).
- Burley SSS; Burley/Oren-Nayar diffuse.
- MSAA edge checks; linear-light resolve.
- Shadow caching; floors out of the caster pass; ~30% more shadow texel density.
- Geometric specular AA; normal/roughness mip prefilter.
- SSAO blur in one fetch; rough SSR via a mip chain; floor SSR stretched by view angle.
- One merged resolve pass (fog + AO + tonemap) plus a LUT grade; GT tone curve.
- Cascade-edge dither; narrow SMAA T2x; TAA.
- Parallax that writes depth (item 16 steps a-c: oDepth, silhouette clip, distance fade).
- Contact shadows, motion blur, DOF (UE4-RENDER-IDEAS.md).
- Rain wetness, lens drops; texture upscale.

---

## Part 2: Gameplay (combat, physics, gore, AI, animation)
10-10 scope cut: AdventMod is **gore, graphics, destruction and foot IK** only. The AI and reaction work was built and then shelved: the code is kept, with defaults False.

### Built and shipped
- Gore (GORE-DESIGN.md):
  - blood, impacts, casings, corpse shots, remains, gibs + gib atlas cards, blood coats, dirt, wounds, bleed trails, screen blood, blast shake;
  - wall runs, live pools (LivePour 0.7, 7c1d983), wall holes, breaches;
  - footprints, drips, body streaks, goo strings;
  - severing + stumps (bones scaled to 0.01, never 0: 0 is a GPF under Karma).
- Armour: plate hits throw sparks (ModArmor bArmourHits/bArmourSparks); TTK is preserved.
- Death ragdolls (ModReact bDeathRagdoll); Epic-style ragdoll asset (f49a6bb); stuck-enemy fix (65b92a5).
- Foot IK, native (ModFeet bFootIK, default True; 5246655), stride match, lean for the player only.
- Pad drift fix, raw mouse, combat pickup filter, ExploreSpeed 1.25.
- Dev aids: FPS graph overlay (ModFpsGraph, bFpsGraph on), pilot (`ModPilot` Steps=, `FPS` step), `test_run.ps1` background runs.

### Built after 3.0 (committed, not in a zip)
- Powered ragdolls, step 2 of the plan:
  - humans: per-region timing RegionLimp (7298458);
  - Seeker soldiers: bPoweredSeekers (22e9a8d).
  - Release default undecided: needs the R5 2-minute fight with no crash.
- Muscle tension layer (bTension, 75f44ad, off).
- Corpse flesh jiggle on Seekers (bCorpseJiggle 3e9587b; fixed by jiggle.c Rehook in 5d3f296, verified).
- Dust per surface (`ImpactPuff` by SurfaceType, seen).
- Armour dust (ModArmor bArmourDust): built, **never seen in game**.

### Built, then shelved (switch back on in `System\AdventMod.ini`)
- ModMinds bMinds: fear/anger/pressure/stress, suppression, path-node cover, fall back, panic, charge, flanking, attack tokens, path cost profiles.
- ModMinds hound packs, wall-kicks, leap links; bWaveFight.
- ModNeeds bNeeds (feed, investigate, starve).
- ModReact bFlinch / bStagger / bKnockdown / bDeathAnims (Kimodo clips); bDeathAnimRagdoll (crashed).
- ModMelee bBlades, energy blade + swings (user: "remove the sword").
- ModMoves bAILean; ModAction vault/slam/barge; ModBody Seeker arms / hound body.
- ModGizmos (too distracting). ModArmor plate actors (the "pink sheen" look).
- Native KFreezeRagdoll byte patch (frozen bodies stood back up). Hound ragdolls crash.

### Not built
- Ragdoll queue (BACKLOG top):
  - SpasmU=1.0 readable tension + side-by-side tension clips for the user;
  - TENSION part 3 (springs softer when limp, wobble on floor hit);
  - the R5 fight and a decision on shipping defaults.
- Physics plan step 1 leftovers from Devastation (see `C:\re\devastation\NOTES.md` Port list 1-6):
  - weld the spine in make_ka.py;
  - 16-pair self-collision whitelist;
  - wrist/neck damping;
  - closest-bone shot impulse;
  - open-pose clip handoff;
  - ragdoll budget fade.
- Physics plan step 3 (bone lifters, wounded getting up) and step 4 (Jolt).
- Destruction (BACKLOG):
  - blast bloom flash;
  - cheap smoke;
  - cap the game's scorch marks;
  - per-surface sound sets;
  - breakable set pieces (pre-broken mesh swap);
  - gore menu switches / intensity slider;
  - 10-15 min soak;
  - blood fluid step 4 (gib textures).
- AI ideas never built: the AI report recommends no GOAP/HTN; it suggests threshold hysteresis on every task, stimulus windows, squad role facts, an encounter director that changes how often enemies attack (not how hard), perception timers, and barks. Its roadmap is nine small slices (`games/reports/Game enemy AI architectures.md`). Also from Devastation: cover scoring, friendly line-of-fire, and prop shoving.
- Animation ideas: smooth path following, landing crouch, speed-synced legs, hound leg IK (BACKLOG "Animation ideas").
- Never started: UniMate / PAMI death clips; the level03sectionb -> 03c door hang.
- Pilot tool bugs: SPIN is about 6x too fast; TURN is unreliable.

## Picking it back up
1. Read the last STATE line in memory `advent-rising-project`, then `BACKLOG.md`.
2. Cheapest wins first:
   - R5 2-minute fight, then decide powered ragdolls on or off;
   - armour dust check;
   - crater camera;
   - closer rock-shadow test.
3. Then cut a 3.1 zip with `package.py`. RELEASE.md's audit lists what to check.
