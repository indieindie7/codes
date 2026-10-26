# Ray-traced / geometric audio for SWAT 4 (research, 2026-10-17)

Not verified by running anything; items marked (unverified) were not confirmed in sources.

## 1 Options

| Project | Licence | 32-bit ok? | What it gives | URL |
|---|---|---|---|---|
| Steam Audio (Valve) | Apache-2.0 (open since v4.5.2) | Repo page says Windows 32 and 64 bit supported; confirm x86 DLL in releases (unverified) | C API; occlusion, transmission, raytraced reflections/reverb, per-band material absorption/scattering/transmission, HRTF | https://github.com/ValveSoftware/steam-audio |
| OpenAL Soft + EFX / EAX | LGPL | Yes (32-bit builds common) | EFX reverb/filters, legacy EAX API since 1.22; no geometry, you feed it parameters | https://github.com/kcat/openal-soft |
| DSOAL | LGPL-style, see repo | Yes (DirectSound DLL, 32-bit) | DS3D+EAX to OpenAL Soft. Not useful here: SWAT 4 already uses OpenAL | https://github.com/kcat/dsoal |
| Resonance Audio (Google) | Apache-2.0 | C++ lib, likely buildable (unverified) | Ambisonics, shoebox room model; no scene raytracing | https://developers.googleblog.com/en/open-sourcing-resonance-audio/ |
| Project Acoustics (Microsoft) | Proprietary EULA; downloads discontinued 2024-07-01 | n/a | Baked wave simulation; dead end | https://developer.microsoft.com/en-us/games/blog/research-spotlight-project-acoustics/ |
| Vercidium Audio | Commercial C# SDK (Patreon); not open | n/a (C#) | Raytraced reverb/occlusion, the video's tech | https://www.patreon.com/posts/vercidium-audio-153487929 |
| whoStoleMyCoffee raytraced-audio | MIT | n/a (Godot GDScript) | Small reference for echo/outdoor/muffle via rays; good to read, not to link | https://www.godotengine.org/asset-library/asset/edit/17966 |
| GSound (Schissler) | Not found in search | ? | Academic geometric propagation; could not locate a repo | - |

## 2 Technique notes

- Occlusion: cast N rays (8-32) from source to listener with jitter; fraction blocked drives a low-pass/gain per source. Transmission through a blocker multiplies by the material's transmission per band.
- Reverb estimate (Vercidium-style, also what the Godot plugin does): from the listener cast ~32-128 rays in random directions, bounce 2-4 times. Record hit distances and material absorption. Mean free path L = average segment length; RT60 via Sabine/Eyring, T = 0.161 V / (A) with A = sum(S*alpha); ray version: energy decays by (1-alpha) per bounce, RT60 = time for -60 dB using path length / 343 m/s. Fraction of rays escaping to sky gives "outdoor-ness" (cut reverb send). Early-echo delay from first-bounce distances. Map result to EFX reverb (decay time, density, gain, late delay).
- Per-source reflections: Steam Audio does this with an impulse response, which is heavier. Cheaper: one shared listener-centred reverb plus per-source occlusion.
- Diffraction: cheap approximation is path-around-edge detection (extra rays offset left/right/up of the direct line; if any passes, blend occlusion toward partial). Steam Audio models partial occlusion and transmission (https://partner.steamgames.com/doc/features/steam_audio).
- Cost: reverb probe 64 rays x 3 bounces ~200 traces; occlusion 16 rays x ~20 sources = 320 traces. Few hundred traces per frame against a BSP/triangle BVH is well under 1 ms; run at 10-20 Hz and smooth parameters. (My estimate, unmeasured.)
- Absorption (alpha, random incidence) per octave band; values from the cited tables, rounded:

| Material | 125 Hz | 500 Hz | 2 kHz | Source |
|---|---|---|---|---|
| Concrete (smooth) | 0.01 | 0.02 | 0.02 | akustik table via search; see https://book.baux.com/book-of-acoustics/2-2-4-sound-absorption/ |
| Drywall (1/2" plasterboard) | 0.29 | 0.05 | 0.07 | https://sengpielaudio.com/calculator-RT60Coeff.htm |
| Wood (smooth/floor) | 0.12-0.15 | 0.08-0.10 | 0.05-0.06 | https://sengpielaudio.com/calculator-RT60Coeff.htm ; https://acta-acustica.edpsciences.org/articles/aacus/full_html/2021/01/aacus200072/T1.html |
| Glass (window) | 0.18 | 0.05 | 0.02 | https://acta-acustica.edpsciences.org/articles/aacus/full_html/2021/01/aacus200072/T1.html |
| Carpet on concrete | 0.02 | 0.14 | 0.60 | https://sengpielaudio.com/calculator-RT60Coeff.htm |
| Metal (steel) | ~0.03 | ~0.03 | ~0.03 | No source found; engineering guess, treat as reflective. Replace with a datasheet value |

Sources disagree (a commercial chart lists carpet lower: 0.01/0.06/0.25), so treat as tunable. Steam Audio uses 3 bands (low/mid/high) per material, so these map directly (Steam Audio docs: https://valvesoftware.github.io/steam-audio/doc/capi/reference.html; preset values not retrieved).

## 3 Recommended path for SWAT 4

1. Confirm the audio path first: load DefOpenAL32.dll in a debugger/with a logging shim; check whether it exposes EFX (alGenEffects etc., alcIsExtensionPresent "ALC_EXT_EFX"). Easiest first experiment: swap in OpenAL Soft's 32-bit soft_oal.dll as DefOpenAL32.dll (renamed) and see what the engine already does. OpenAL Soft supports EFX reverb and legacy EAX, so SWAT 4's EAX zones may already work.
2. Geometry/material source (UnrealScript side, no DLL needed first): SWAT 4's script has FastTrace/Trace and Material surface types (footstep/bullet-hit surface class on the hit Material). Prototype a mutator or Actor that does the ray casts in UnrealScript at ~10 Hz (listener probe for RT60/outdoor, per-source occlusion rays) and writes results to a small shared memory/INI/console command. Surface type to alpha table from section 2.
3. Apply: proxy DefOpenAL32.dll (32-bit, forwards all exports, hooks alSourcef/alSourcei/alListener*): read the script-produced params and set an EFX auxiliary reverb slot, per-source direct filter (low-pass) and gain. Keep forwarding for everything else.
4. Only if script tracing is too slow or too coarse: move tracing to the proxy DLL or an external 32-bit process with a baked BSP+static mesh dump (exported once per map) and a BVH; or embed Steam Audio (Apache-2.0, 32-bit listed) with a scene built from the exported mesh. Large effort; use for per-source reflections.
5. Ship as a mod with the proxy DLL as an opt-in file; ask before replacing audio DLLs on the user's install.

Risks: script traces cost VM time and BSP traces ignore static meshes unless blocked by collision (bTraceStaticMeshes-style flags vary; verify in the SDK source); surface type may be missing on BSP/mesh without a material assignment; DefOpenAL32 may be an older OpenAL 1.1 build lacking EFX; proxy DLL must match the exact call signatures and 32-bit calling convention (stdcall/cdecl) and the engine may anti-cheat-check files in multiplayer; Steam Audio's 32-bit build and its dependencies (Embree/IPP, may need disabling) unverified; hot-swapping reverb presets causes audible pops, so crossfade.

## 4 Step 1 results (10-26)
- DefOpenAL32.dll (Content + ContentExpansion System) = Creative DS3D wrapper 0.993, OpenAL 1.0, EAX 1-3, no EFX. Swat4.ini has UseEAX=False, Use3DSound=False.
- Next: drop OpenAL Soft x86 in as DefOpenAL32.dll (back up stock), set UseEAX=True + Use3DSound=True, alsoft.ini hrtf=true; OpenAL Soft maps EAX calls to its EFX reverb, so the game's own per-zone EAX presets come back without a proxy. Per-source occlusion still needs a proxy later (mutator writes occlusion per sound to a file the proxy polls).
