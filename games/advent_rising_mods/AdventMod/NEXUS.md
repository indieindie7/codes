# Nexus page for GoreOverhaul 3.0 (formerly AdventMod; draft, the user posts it)

Version 3.0. The mod was renamed GoreOverhaul on 2026-10-10, when its scope was cut to gore, graphics
and destruction (the enemy AI and the new enemy animations are shelved, off by default). Only the
release name changed: the files inside keep the AdventMod name (AdventMod.u, AdventMod.ini, the
[AdventMod.*] sections, the Install/Uninstall .bat), so old installs and settings carry over.
The second page, AdventGraphicalMod, is the same build with `package.py --graphics` and keeps its own
page text.

**Title:** GoreOverhaul - Gore, Graphics, Destruction and In-Game Options

**Category:** Visuals and Graphics (the 2.x pages sit there)

**Summary (short line):**
Blood that runs, pools, drips and dries, bodies that come apart, Seeker armour that dents and flies off, working character shadows, a modern post chain (bloom, LUT, CAS, SMAA, GI, AO, fog), foot IK, and the launcher's settings inside the game's menus. Formerly AdventMod.

**Files to upload:** `GoreOverhaul-3.0-nexus.zip` (no .bat inside; Nexus quarantines them).
The GitHub zip with the one-click installer: https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods/AdventMod

Before upload (RELEASE.md has the list): a fresh plain `build.ps1` (never the `-JiggleSkin` build: it
carries a game texture), the current gi-cascades `d3d8.dll` copied into `System\`, the stray `.asm` and
`.png` out of `U2Shaders\`, the licence texts in `Licenses\`. The FPS graph and the gizmos ship on
(the user's call, 2026-10-10).

If the old AdventMod page is kept, point it here ("renamed GoreOverhaul, same files") rather than
uploading 3.0 twice.

**Permissions / third-party content:** yes, third-party code under open licences:
d3d8to9 (BSD-2), SMAA (MIT), AMD CAS (MIT), Khronos PBR Neutral (Apache-2.0), Inigo Quilez's texture repetition / fog (CC BY-NC-SA 3.0), UnityPCSS (MIT), Dear ImGui (MIT) and stb_image_write (public domain) inside the d3d8.dll.
All credited in `Licenses\CREDITS.txt`. GoreOverhaul itself: GPL-3.0, non-commercial. No game textures are included; a few meshes are cut or re-rigged from the game's own models (gib pieces, the jiggle Seeker).

**Screenshots:** before/after pairs (crowd room, station, outdoors), the Graphics page, a blood scene
after a fight (pools, runs, prints), a Seeker with a plate knocked off, a severed limb.

---

## Description (BBCode)

```
[size=5][b]GoreOverhaul 3.0[/b][/size] (formerly AdventMod)
Blood that behaves like a liquid, bodies and armour that come apart, shadows that work, a modern post-processing chain, and the launcher's settings inside the game.

[size=4][b]Gore[/b][/size]
[list]
[*]Blood sprays and splats where people are hit; bodies bleed into pools that spread and join; wall sprays run down in rivulets
[*]Streaks run down wounded bodies, parts that come apart stay joined by sticky strings for a moment, drops fall from ledges and ceilings, everyone who walks through blood leaves prints
[*]Blood is wet and shiny, then dries matte and brown; deep pools reflect the room
[*]Gibs, severed limbs, stumps, blood-soaked skins, brass casings, rubble, bullet holes and breaches in walls
[*]Blood on Gideon's hands and gun after a close kill; drops on the lens
[*]Ragdolls with the mod's own joint limits
[*]Everything has a switch in System\AdventMod.ini
[/list]

[size=4][b]Destruction and armour[/b][/size]
[list]
[*]Seeker soldiers wear steel plates that dent and fly off; a hit on armour sparks instead of bleeding
[*]An energy blade some Seekers drop: three hand-keyed swings, cuts heads and limbs off at the joint
[*]Gideon barges breakable props out of the way and slams into walls on a dodge
[/list]

[size=4][b]Bodies[/b][/size]
[list]
[*]Gideon leans into turns and vaults waist-high cover at a run
[*]Seeker infantry flesh that lags and settles with the body and kicks on a hit; the armour never deforms
[*]Foot IK: feet stand on the real floor on stairs and step edges
[*]Hounds stand level on slopes
[/list]

[size=4][b]Shadows[/b][/size]
[list]
[*]Character shadows work again. The stock game loses most of them: its sky pass draws over them and the shadow bitmaps lose their alpha.
[*]Soft shadows from the real lamps around each character (up to 4 for Gideon), fading smoothly as you walk between lights.
[*]The 20 nearest people on screen cast shadows too, the background crowds included.
[*]Outdoors: one shadow from the sun, as strong as the sun is bright.
[*]Indoors: contact-hardening shadows, sharp at the feet and softer further away.
[/list]

[size=4][b]Post-processing and light[/b][/size] (replaces the game's own blur effects)
[list]
[*]Bloom in linear light with a soft highlight roll-off, colour grading through a LUT, AMD CAS sharpening, SMAA anti-aliasing, a light vignette, film grain, dithering
[*]Five presets: [b]Off, Natural, Cinematic, Gritty, Clean[/b]
[*]Global illumination (Off / On / Strong) and ambient occlusion, both off until you turn them on
[*]Height fog that thickens low and far, soft particles (smoke no longer cuts through the floor), a sheen on metal panels and polished floors, subsurface skin shading on faces and alien hide
[*]Terrain blends its layers by height, hides the tiling, has grit and pebbles up close; the crash level's rocks and sky are graded toward desert photos
[/list]

[size=4][b]Performance and fixes[/b][/size]
The game renders a few hundred frames a second for nothing; GoreOverhaul caps it at your monitor's refresh rate. Raw mouse look, no camera spin from an idle gamepad, no lock-on jumps to floor weapons mid-fight, no freezes on the indoor/outdoor shadow switch.
A frame-time graph and debug lines on Gideon are on by default; bFpsGraph=False and bGizmos=False under [AdventMod.ModSettings] turn them off (or "mutate gizmos" in the console).

[size=4][b]In-game options[/b][/size]
Options is a hub, one press from each page, from the title and the pause menu: [b]Gameplay[/b] (difficulty, damage dealt and taken, boss damage, running speed), [b]Camera[/b], [b]Audio[/b] (with Dialogue Volume), [b]Screen[/b] (real resolutions, fullscreen mode, VSync, frame cap), [b]Graphics[/b] (post preset, soft shadows, GI, ambient light, SMAA, shadow darkness, sharpening, FOV), [b]Quality[/b], [b]Accessibility[/b] (blood, colorblind modes with a strength slider, HUD fade, slow-mo weapon select, auto aim, toggle crouch), [b]Controls[/b]. Everything applies at once.

[size=4][b]Install[/b][/size]
Extract the zip, then copy everything in its [i]System[/i] folder into the game's [i]System[/i] folder (rename your own d3d8.dll first if you have one, e.g. dgVoodoo), and the [i]KarmaData[/i] and [i]AdventMod[/i] folders next to it. Then add a few configuration lines to Mydefault.ini and MyDefUser.ini, as described step by step in the README. The files keep the old AdventMod name, so an existing AdventMod install is simply overwritten.
Or take the GitHub version, which has a one-click installer and uninstaller that back up everything they change.

Works with the Steam/GOG version and Advent Revising (already included there). Tested on Steam, Windows 10, NVIDIA. Known limits are listed in the README (foot IK keeps the animation's foot tilt, hounds never ragdoll, light shafts and exclusive fullscreen unverified).

[size=4][b]How it works[/b][/size]
GoreOverhaul is an UnrealScript package (compiled with AdventUCC, which runs the compiler hidden in the game's Editor.dll), a small native helper (shadow fixes, frame cap, foot IK and flesh springs inside the engine's pose build, the armour test), and a d3d8.dll: a fork of crosire's d3d8to9 with shader-based shadow filtering, post-processing, GI, live blood sheets and the rest. Full source on GitHub.

[size=4][b]Credits[/b][/size]
GlyphX Games / Majesco for Advent Rising; Mike Tyndall for Advent Revising; crosire for d3d8to9; Jorge Jimenez et al. for SMAA, the bloom technique and separable SSS; AMD for CAS; Khronos for PBR Neutral; Inigo Quilez for the texture repetition and fog techniques; Lucas Norr for UnityPCSS; Omar Cornut (Dear ImGui) and Sean Barrett (stb); McGuire, Mara and Luebke (SAO); Mikkelsen (hex tiling); Sannikov (radiance cascades).
```
