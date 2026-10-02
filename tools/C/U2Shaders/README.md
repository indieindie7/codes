# U2Shaders (d3d8to9 fork for Unreal II)

A fork of [crosire/d3d8to9](https://github.com/crosire/d3d8to9) (BSD 2-clause, see
`LICENSE-d3d8to9.md`) that injects HLSL pixel shaders into Unreal II: The Awakening.

- `0001-...patch`: the fork as one commit on top of d3d8to9 `255338f` (apply with `git am`).
- `u2shaders.hpp`: the new code (also in the patch).
- `0002-...patch`: optional experimental borderless window (`borderless.hpp`, off by default; `borderless=1` in U2Shaders.ini). Apply after 0001.
- `0003-...patch`: post=1 fix (restores the game's vertex streams, indices, textures, samplers and shaders after the post pass; posttrace=N). Apply after 0001. Tested on the PC 2026-10-02.
- `shaders/`: the HLSL files (installed to `<game>\System\U2Shaders\`):
  - `core.hlsl`: the Liandri heavy's translucent core (plasma noise after Inigo Quilez, MIT; rim glow; refraction).
  - `pcss_map.hlsl` / `pcss_proj.hlsl`: contact-hardening character shadows (PCSS, after NVIDIA /
    UnityPCSS, MIT): sharp where the body meets the ground, softer higher up.
- `d3d8.dll`: the built fork (Release, Win32).

## Install

Game `System` folder: this `d3d8.dll` + dgVoodoo 2's `D3D9.dll` (as `d3d9.dll`), the shaders in
`System\U2Shaders\`, and `System\U2Shaders.ini`:

    pcss=1
    shader=cfdd1328 core.hlsl

Optional, with `pcss=1`: `shadowtint=R G B` sets how strongly the shadow darkens each colour
channel. `1 1 1` (default) is the engine's grey; lowering blue gives cool, bluish shadows, e.g.

    shadowtint=1.1 1.0 0.75

Needs a `d3d8.dll` built from this source (the one in this folder predates it). With an older
dll the new `pcss_proj.hlsl` still works and draws grey shadows.

Post-processing: `post=1` adds bloom, sharpening and colour grading to the finished 3D frame,
applied just before the HUD (the first 2D draw of the frame) so the HUD stays crisp; menu-only
frames are left alone. Settings (defaults shown):

    bloom=0.75 0.5            threshold (brightness that starts to glow), intensity
    grade=1.05 1.05 1.0 0.25  saturation, contrast, exposure, vignette
    colour=1 1 1              colour balance (r g b multipliers)
    sharpen=0.25              0 = off
    postsplit=1               only the left half is processed, to compare

`U2Shaders.log` says how the HUD start was detected ("post: applied before a 2D draw ...").
If the HUD gets bloomed in game, that detection missed and needs a look.

Parallax bullet holes: `decal=<hash> decal_parallax.hlsl` draws that decal texture as if sunken
into the wall (parallax occlusion, as in F.E.A.R.): the depth shows when the wall is seen at an
angle, and the inside darkens with depth. No light direction needed. Unlike `shader=`, a
`decal=` rule keeps the draw's own blending, so overlapping decals still layer. The texture
doubles as its depth map: `ALPHA_DECAL 1` (alpha decals, more opaque = deeper) or `0`
(modulating decals, darker = deeper); `DEPTH` sets how deep it looks, in world units. Projector
decals work (their projected coordinates are kept). To find a decal's hash, run with `log=1`,
shoot a wall, and look in `U2Shaders\dump\` (each alpha-blended texture is saved as
`<hash>_<w>x<h>.dds`). Needs `ps_2_a` (ddx/ddy).

Parallax walls and floors: `surface=<hash> world_parallax.hlsl` gives a solid level surface
depth the same way: mortar, tile gaps, panel seams and grates look recessed when seen at an
angle. The texture's brightness is its height (dark = deep), so use it on textures whose dark
parts are gaps, not on ones whose dark parts are just colour (signs, dirt). The fork measures
each texture once (its typical brightness = the surface, its darkest few percent = the bottom;
`U2Shaders.log`: "surface <hash>: brightness levels ..."), so there is nothing to tune per
texture; `DEPTH` in the shader sets how deep, in world units, and the effect fades out with
distance (`FADE_START`/`FADE_END`), where it would only shimmer. A pixel shader replaces the
texture stages, so the shader redoes them: the texture, times the vertex lighting, times the
lightmap on stage 1. Other stage setups are drawn as before and logged once ("stage setup not
supported", with the setup: send me that line). It only works if the surface's own texture is
on stage 0; if Unreal II puts the lightmap there, the rule never matches. To find a wall's
hash, run with `charprobe=1`: every texture of a solid on-screen draw is saved in
`U2Shaders\dump\`, and `chars.txt` lists how each was drawn.

Character lighting: `charlight=1` lights every solid, lit draw (characters, weapons, pickups: the
level itself is lightmapped and unlit) per pixel instead of per vertex, from the game's own D3D
lights, with Valve's character tricks ("Shading in Valve's Source Engine", 2006): wrapped
diffuse, so the side away from a light falls off gradually and the body's shape still reads;
ambient lighter from above than below; a faint rim along the silhouette. `WRAP`, `HEMI` and
`RIM` at the top of `char_light.hlsl` set how much of each (0 = as the game). Draws it can't
redo exactly (vertex colours as material, a second texture stage) are left alone and logged
once ("charlight: setup not supported ..."). Assumes the game's world is Z-up, as Unreal is; if
characters look lit from below, that's wrong and needs a look. No self-shadowing yet: that is
the next step (from the shadow maps the PCSS code already keeps).

Texture replacement: `replace=<hash> file.dds` draws `System\U2Shaders\file.dds` wherever the
game uses that texture, on texture stages 0-3, so lightmaps (stage 1) can be swapped too: the
way in for lighting baked elsewhere (Blender) or reworked skins. The game's files are not
touched; the swap happens per draw and is undone after it. The DDS must be 32-bit (BGRA) or
DXT1/3/5 and carry its own mip levels; `U2Shaders.log` says "replace <hash>: ... loaded" or why
not. Find hashes with `log=1` (see-through textures) or `charprobe=1` (solid ones). Rules keyed by
the original hash (`surface=`, `decal=`) still apply on top of the replacement.

Lightmap capture, for baking elsewhere: `lmcapture=1` records the level's lightmapped geometry
as it is drawn (every draw with a lightmap multiplied in on stage 1): world-space triangles with
their lightmap coordinates, worked out the way Direct3D does, each triangle once however often
it is drawn. Every few seconds it writes `System\U2Shaders\capture\scene.obj` (one object per
lightmap) and `lightmaps.txt`, and saves each lightmap in `U2Shaders\dump\`. Walk through the
level (only what is drawn is recorded), then bake with `tools/python/U2Blender/bake_lightmaps.py`
in Blender (lights from the map's T3D), and put its `replace=` lines in `U2Shaders.ini`. While
capturing the dll keeps a copy of every vertex and index buffer the game writes (memory, and a
little time): leave it off otherwise. Not known yet: whether Unreal II draws its lightmaps on
stage 1 at all (the log's "lmcapture: 0 lightmaps" would say not; `charprobe=1` shows how it
draws instead), and whether its world space is Unreal's (the T3D's lights would then line up).

Probe, logging only: `charprobe=1` records how every opaque on-screen draw is lit (fixed-function
lighting, lights, material, ambient, vertex blending, texture stages) and whether shadow
silhouettes were drawn earlier in the frame, in `System\U2Shaders\dump\chars.txt`, and saves each
texture once as a `.dds` to tell character skins apart. It also checks whether the scene's depth
can be read as a texture (`INTZ`/`DF24`/`DF16`/`RAWZ`, needed for screen-space contact shadows)
and writes the answer to `U2Shaders.log` ("depth probe: ..."). Run it with U2Pilot's
`scripts/char_probe.txt`. It is the groundwork for character lighting and self-shadowing: the
per-surface rules only reach alpha-blended draws, and character skins are opaque.

## How Unreal II's character shadows work (what the PCSS hooks)

1. The silhouette is drawn into a sharp render target A (flat colour 128, shadow in **alpha**).
2. Nine additive passes blur A into B (0.502 x alpha); one more pass fades B's border.
3. The projector multiplies B onto the world.

The fork writes the silhouette's world height into A's unused red channel, snapshots A per
shadow when the engine blurs it (A is shared scratch), and in the projector pass samples the
snapshot on sampler 3: blocker search, then a filter whose radius grows with the height gap.
Needs ps_2_b (falls back from ps_2_a automatically). Debug: `pcssdebug=1` (gap colour) ... `6`.

Build: `MSBuild d3d8to9.vcxproj -p:Configuration=Release -p:Platform=Win32 -p:PlatformToolset=v145`.

Or without Visual Studio: `./build-mingw.sh` (Linux/WSL with `g++-mingw-w64-i686`) clones
d3d8to9, applies the patch and builds `build/d3d8.dll`, standalone (no VC++ runtime needed).
`d3d8-mingw.dll` in this folder is that build of the current source (shadow tint, probes,
decal rule, post-processing, parallax walls, replace=, charlight=, lmcapture=). It has only been run under Wine (`test/run.sh`), not yet in the game; `d3d8.dll`
is the older MSVC build that has been. To try it, install it as `d3d8.dll`.

`test/run.sh` runs the built DLL outside the game under 32-bit Wine with a virtual display:
a small Direct3D 8 program (`test/probe_test.cpp`) draws a shadow silhouette, a lit textured
wall and a bullet-hole decal, so the probes log and the decal rule compiles and draws, then
post-processing, then a lightmapped brick wall with and without `surface=`, and with its lightmap swapped by
`replace=`, then a lit sphere with and without `charlight=`, then the wall with `lmcapture=`. It
proves the code runs, not that it looks right in Unreal II (Wine's d3d9 is not dgVoodoo).

## Checking shaders without the game

`./hlslcheck.sh` compiles `shaders/*.hlsl` (or the files given) the way the fork does at runtime:
Microsoft's `d3dcompiler_47`, entry `main`, `ps_2_a` then `ps_2_b`. It prints the profile that
took and the budget used, e.g.

    OK    pcss_proj    ps_2_b  slots 353/512  temps 31/32  constants 19/32

It fetches `fxc.exe` + `d3dcompiler_47.dll` once from the Windows SDK NuGet package into
`~/.cache/u2shaders-fxc` (`FXC_DIR` to change). Linux runs them under Wine (`apt install wine64`);
Git Bash runs them natively. This proves a shader compiles and fits, not that it looks right.
