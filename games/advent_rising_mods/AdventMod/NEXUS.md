# Nexus page for AdventMod 2.0 (draft; the user posts it)

**Title:** AdventMod - Shadows, Post-Processing and In-Game Options

**Category:** Visuals and Graphics (or Utilities)

**Summary (short line):**
Working character shadows from real lights, a modern post-processing chain (bloom, LUT grading, CAS sharpening, SMAA), better terrain, a frame cap, and the launcher's settings inside the game's menus.

**Files to upload:** `AdventMod-2.0-nexus.zip` (no .bat inside; Nexus quarantines them).
The GitHub zip with the one-click installer: https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods/AdventMod

**Permissions / third-party content:** yes, third-party code under open licences:
d3d8to9 (BSD-2), SMAA (MIT), AMD CAS (MIT), Khronos PBR Neutral (Apache-2.0), Inigo Quilez's texture repetition / fog (CC BY-NC-SA 3.0).
All credited in `Licenses\CREDITS.txt`. AdventMod itself: GPL-3.0, non-commercial.

**Screenshots:** before/after pairs (crowd room, station, outdoors) + the Graphics page.

---

## Description (BBCode)

```
[size=5][b]AdventMod 2.0[/b][/size]
Shadows that work, a modern post-processing chain and the launcher's settings inside the game.

[size=4][b]Shadows[/b][/size]
[list]
[*]Character shadows work again. The stock game loses most of them: its sky pass draws over them and the shadow bitmaps lose their alpha.
[*]Soft shadows from the real lamps around each character (up to 4 for Gideon), fading smoothly as you walk between lights.
[*]The 20 nearest people on screen cast shadows too, the background crowds included.
[*]Outdoors: one shadow from the sun, as strong as the sun is bright.
[*]Indoors: contact-hardening shadows, sharp at the feet and softer further away.
[/list]

[size=4][b]Post-processing[/b][/size] (replaces the game's own blur effects)
[list]
[*]Bloom in linear light with a soft highlight roll-off (mip-chain, wide and smooth)
[*]Colour grading through a LUT
[*]AMD CAS contrast-adaptive sharpening
[*]SMAA anti-aliasing
[*]Light vignette, film grain, dithering against banding
[*]Five presets: [b]Off, Natural, Cinematic, Gritty, Clean[/b]
[/list]

[size=4][b]Terrain[/b][/size]
Outdoor ground blends its textures by height (sand settles between rocks instead of a soft cross-fade) and hides the tiling pattern.

[size=4][b]Performance[/b][/size]
The game renders a few hundred frames a second for nothing; AdventMod caps it at your monitor's refresh rate (much lower GPU load).

[size=4][b]In-game options[/b][/size]
[list]
[*][b]Options > Video:[/b] Fullscreen, Borderless Window, VSync, More Display Options
[*][b]Display Options:[/b] Widescreen, Trilinear Filtering, Field of View (60-120), Minimum Frame Rate
[*][b]Graphics:[/b] Post Effects preset, Soft Shadows, Shadows for Others, Anti-Aliasing, Frame Cap, Shadow Darkness, Sharpening
[*][b]Options > Graphics:[/b] real resolutions for today's screens
[*][b]Options > Audio:[/b] Dialogue Volume
[/list]
Everything applies at once, also from the pause menu.

[size=4][b]Install[/b][/size]
Extract the zip, then copy everything in its [i]System[/i] folder into the game's [i]System[/i] folder (rename your own d3d8.dll first if you have one, e.g. dgVoodoo). Then add a few configuration lines to Mydefault.ini and MyDefUser.ini, as described step by step in the README.
Or take the GitHub version, which has a one-click installer and uninstaller that back up everything they change.

Works with the Steam/GOG version and Advent Revising (already included there). Tested on Steam, Windows 10, NVIDIA.

[size=4][b]How it works[/b][/size]
AdventMod is an UnrealScript package (compiled with AdventUCC, which runs the compiler hidden in the game's Editor.dll), a small native helper, and a d3d8.dll: a fork of crosire's d3d8to9 with shader-based shadow filtering, post-processing and a terrain shader. Full source on GitHub.

[size=4][b]Credits[/b][/size]
GlyphX Games / Majesco for Advent Rising; Mike Tyndall for Advent Revising; crosire for d3d8to9; Jorge Jimenez et al. for SMAA and the bloom technique; AMD for CAS; Khronos for PBR Neutral; Inigo Quilez for the texture repetition and fog techniques.
```
