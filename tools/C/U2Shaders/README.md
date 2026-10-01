# U2Shaders (d3d8to9 fork for Unreal II)

A fork of [crosire/d3d8to9](https://github.com/crosire/d3d8to9) (BSD 2-clause, see
`LICENSE-d3d8to9.md`) that injects HLSL pixel shaders into Unreal II: The Awakening.

- `0001-...patch`: the fork as one commit on top of d3d8to9 `255338f` (apply with `git am`).
- `u2shaders.hpp`: the new code (also in the patch).
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

Probe, logging only: `charprobe=1` records how every opaque on-screen draw is lit (fixed-function
lighting, lights, material, ambient, vertex blending, texture stages) and whether shadow
silhouettes were drawn earlier in the frame, in `System\U2Shaders\dump\chars.txt`, and saves each
texture once as a `.dds` to tell character skins apart. Run it with U2Pilot's
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

## Checking shaders without the game

`./hlslcheck.sh` compiles `shaders/*.hlsl` (or the files given) the way the fork does at runtime:
Microsoft's `d3dcompiler_47`, entry `main`, `ps_2_a` then `ps_2_b`. It prints the profile that
took and the budget used, e.g.

    OK    pcss_proj    ps_2_b  slots 353/512  temps 31/32  constants 19/32

It fetches `fxc.exe` + `d3dcompiler_47.dll` once from the Windows SDK NuGet package into
`~/.cache/u2shaders-fxc` (`FXC_DIR` to change). Linux runs them under Wine (`apt install wine64`);
Git Bash runs them natively. This proves a shader compiles and fits, not that it looks right.
