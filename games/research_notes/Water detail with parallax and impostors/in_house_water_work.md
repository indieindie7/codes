# In-house water and liquid work (from the Advent Rising session, 2026-10-09)

Collected from the "advent rising modding" session on request; paths under `Documents\github\`.
This is what already exists in our own code and notes, as context for the report's recipe.

## Hydrophobia solver and upgrade plan
- `codes/games/REVERSE-ENGINEERING.md` (water section), `codes/games/hydrophobia-water-tech.md`,
  `codes/games/hydrophobia-water-upgrade.md` (12 stages: displaced volume, capped path stamping,
  buoyancy, face walls + porosity, Kurganov–Petrova, waterfall faces, splash/foam, clamps and
  volume audit, tile sleeping, AVX2, appearance above physics, nested fine window).

## Built with the same equations: Advent Rising blood (a viscous liquid)
- `codes/games/advent_rising_mods/research/blood-fluid-plan.md`: plan and results. Step 1 an
  offline bake (`tools/make_blood_pool.py`: HLL / Toro / Audusse on an 80x80 grid with a rough
  floor, 12 frames baked to TGA height maps, drawn through a parallax decal shader so the deep
  middle sinks). Step 2 live pools in the d3d8 layer. Gotchas: TGA rows bottom-up for the texture
  hash to match; only 9 distinct hashes from grey early frames.
- `d3d8to9-gi/source/blood.hpp` (branch gi-cascades): the live CPU shallow-water sheet, 64x64 per
  pool, 8 slots, one step per frame, friction 0.9/s, speed cap 20·h, commands
  pool/pour/bed/stamp/wet/stop. A pawn walking through stamps its velocity and pushes half the
  blood under it into a ring. The texture is painted from depth each frame and swapped in for the
  decal's placeholder texture by hash. Cost: 8 x 4096 cells per frame, well under 0.1 ms.
  Verified in game (`research/img/blood_live_pool.png`); footprints and drips verified by log only.
- `d3d8to9-gi/source/runs.hpp`: blood running down walls (drops with mass under gravity across a
  sheet; trails thin, slow, stop and branch); same placeholder-swap trick; the gloss pass makes
  trails wet and lets them dry.
- `d3d8to9-gi/source/u2shaders.hpp`: `gloss=` (~line 1695) wet highlights over decals (additive),
  `glossenv=` grazing reflection colour, `glossdry=` wet-to-dry timing and darkening,
  `glossreflect=` puddle reflections from a scene copy: the cheap wet-surface look. `sheen=`
  (~1940) grazing highlights on solids. `zwrite=` (line 12) depth-only pass so smoke at sea is not
  painted over by the translucent sea drawn later.
- AdventMod script side: `Classes/ModGore.uc` (pours, slots, bLivePools), `ModBloodDecal.uc`
  (grow through baked frames, stamps), `ModBloodCoat.uc` (drips on a hit body: a Combiner with a
  panned streak texture); `tools/make_blood_live.py`, `make_blood_marks.py`, `tex_hash.py`.
- Memory notes in that session: `bioshock-mod-ideas.md` (fluid papers parked for a BioShock water
  mod), `skin-shading-sss-notes.md` (light-warp ramp via replace rules, screen-space SSS in the
  post pass: relevant to layered materials).

## Unreal II / Avalon, water-adjacent
- U2Avalon's storm (rain cylinders, splash pool on open ground via AvalonStorm / RainSplash,
  NoRain boxes under glass roofs); the sea is a TerrainInfo with WetTexture; the fork's `atmos=`
  height fog and shafts. Nothing simulates the sea.

## Open problems recorded there
- Live pools have no sleeping or early-out; the baked sequence cannot react to slope or walking
  (hence the live version); the walk-through look was judged by log, not by eye.
- Solver limits learnt: first order in space smears thin films (the pool's edge); the speed cap
  and friction are what make it read as blood rather than water.

## That session's take on ripples and detritus as materials (not built)
- Small ripples: a parallax-offset or parallax-occlusion material over the water plane driven by
  an animated height map, far cheaper than geometry; for a solver-driven surface write the
  sheet's depth into the height map each frame (as `blood.hpp` does) and derive the normal from
  it; real geometry only for the big waves.
- Imposter cubes / interior mapping: a layered material with the parallax ripple surface on top
  and an interior-mapped or parallax-offset bed below, refracted by the surface normal; detritus
  as a thin floating layer, a sprite atlas sampled with a parallax offset from the height field
  so bits ride the ripples. Limits: breaks at grazing angles and silhouettes; keep real meshes
  for anything the player walks through or that must cast shadows.
- Pointers given: Interior Mapping (van Dongen 2008), Parallax Occlusion Mapping (Tatarchuk
  2006), Relief Mapping (Policarpo 2005), depth-based refraction of the bed, and Vlachos's flow
  maps (Portal 2) to advect a detritus texture along the solver's velocity field.

## How this bears on the report
- The report's Stage A (flow ripples from the solver's velocity) and Stage B (refracted slab
  stack with a floor and detritus planes) are exactly what the Advent session proposed
  independently, and `blood.hpp` is a working CPU sheet that already paints its height into a
  texture each frame and swaps it in by hash: the prototype path for a Hydrophobia d3d9 proxy is
  to lift that loop and put the slab shader on the water draw.
