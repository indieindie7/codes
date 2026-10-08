# Advent Rising: graphics pass (2026-10-08)

This covers the four looks added after the optimization round (LAA, lagfix, 30 Hz blood, aniso 16). All four live in the d3d8 layer (`d3d8to9-gi`, branch `gi-cascades`). Each one is off unless `System\U2Shaders.ini` turns it on, and the mod's ini does turn them on. The ini reloads live while the game runs.

| look | what it does | settings | shader |
|---|---|---|---|
| **Height fog + light shafts** | Fog that is thick low down and far away, warm toward the sun. The horizon hazes and the sky straight up stays clear. Shafts come from the bright sky around the sun. | `atmos=1`, `atmosfog=r g b density`, `atmosfog2=falloff height most skydist`, `atmosshafts=strength length threshold suntint`, `atmossun=az el` (by hand), `atmosdebug=1/2/3` | `atmos.hlsl` |
| **Soft particles** | Smoke, dust, sparks and beams fade where they meet the floor or a wall, instead of a hard cut line. | `soft=1`, `softparams=distance debug` | `soft.hlsl` |
| **Close-up terrain detail** | Grit and pebbles up close, plus stones and dried-mud cracks a little further out. It fades out with distance and on steep rock. | `terraindetail=terrain_detail.dds`, `terraindetailfx=strength near far fade` | `terrain_src.hlsl` (section 6), `make_terrain_detail.py` |
| **Sheen on metal and floors** | A second pass over chosen world textures. It adds highlights from the game's lights near the camera, plus a Fresnel reflection that is as bright as the baked light at that spot. | `sheen=HASH sheen.hlsl [strength sharpness metal]`, `sheenfx=`, `sheenenv=` | `sheen.hlsl` |

## How each works

- **Fog and shafts** run as a post pass after SSAO/SSS and before SMAA, from the readable depth that GI/SSAO already set up.
  - The fog follows IQ's "better fog" integral along the view ray.
  - The densest air sits a fixed height below the camera (`atmosfog2` height). Advent's levels sit at any world z, so a world-fixed base was ten times too thick on the crash level.
  - The sun is the brightest directional light the game sets for lit draws. On level04sectiona it was found at about 49° elevation.
  - With the fog on, the terrain shader's own fog is off (`terrainfog` density 0). Rocks and meshes now get the same haze as the ground.
- **Soft particles** take only the draws they can redo exactly:
  - blended, depth-tested, unlit, fixed-function, no depth write;
  - stage 0 only, with texture/diffuse in select or multiply ops;
  - no projected coordinates, so decals keep their old path.
  - The fade goes where the blend mode reads it: alpha for alpha blending, colour for additive, toward neutral for multiply.
  - It reads the bound INTZ depth while depth writes are off.
- **Terrain detail** is our own generated texture, with no game pixels.
  - Channel R is read at a 200-unit repeat and channel G at 700. They come in within 1200 units of the camera.
  - The fork binds the texture on s6 for the `psreplace` terrain shaders, with settings in c9.
- **Sheen** rules are per texture.
  - Metal panels and doors use `metal` 0.3–0.5, which tints the reflection with the texture's colour. The wood floors use 0, a plain dielectric.
  - Fabric wall panels were tried and dropped: they became coloured blobs, because the game's character lights are strongly coloured.
  - Highlights use half-saturated light colours.
  - The hashes come from level03sectionb and the ship (`log=2` dumps, looked at locally, never shipped).

## Test results (hidden runs, prints toggled live at fixed views)

| | result |
|---|---|
| **Fog** (level04sectiona, density 0.00002, most 0.4) | Reads as desert haze: distant hills and the bridge sink into warm air, the foreground is unchanged. The first try (base at world z 0, density 0.00004, most 0.6) washed everything grey. |
| **Light shafts** | **Not yet seen.** The level's sun is high and the third-person camera can't pitch up to it. The shaft path ran but had nothing to draw. To check: `atmossun=` with a low sun, or an outdoor level with a low sun. |
| **Soft particles** | Take the crash-site smoke (debug green on exactly the smoke). No breakage in the station or on the crash level. |
| **Terrain detail** | Close ground goes from a smeared blur to visible grit and pebbles. A 40-unit repeat was too fine to see; 200 works. |
| **Sheen** | Grey pillars, door frames and metal panels catch light near the lamps, and wood floors get a faint sheen. It is subtle by design. |

## Still to do

- See the shafts at least once, with a low-sun view or `atmossun=`.
- Measure the frame-time cost of each look one at a time with `perf:` lines. The test runs mixed loading into the 30 s windows.
- Collect sheen hashes for more levels: the ship (level01), the Seeker levels, Tarkum.
- Have a person playtest: fog strength by level, detail strength, the overall look.
- Not done: TAA (item 8 on the survey's shortlist). The film grain, chromatic aberration and highlight shoulder already existed in `post_final.hlsl`.
