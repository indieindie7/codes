# Nexus page for the next AdventMod release (draft; the user posts it)

Version: `package.py` is still at 2.1; **proposed 3.0** (new AI, body and combat systems). Bump `VER`,
the README.txt title line and the two "(new in 2.1)" anchors together (package.py --graphics keys on
them), then replace "3.0" below if another number is chosen. The second page, AdventGraphicalMod, is
the same build with `--graphics` (gore, combat and AI off) and keeps its own page text.

**Title:** AdventMod - Shadows, Post-Processing, Gore, Thinking Enemies and In-Game Options

**Category:** Gameplay (or Visuals and Graphics; the 2.x pages sit under Visuals)

**Summary (short line):**
Working character shadows, a modern post chain (bloom, LUT, CAS, SMAA, GI, AO, fog), blood that runs, pools, drips and dries, enemies with feelings and hound packs, Seeker armour and flesh, Gideon's vaults and leans, and the launcher's settings inside the game's menus.

**Files to upload:** `AdventMod-3.0-nexus.zip` (no .bat inside; Nexus quarantines them).
The GitHub zip with the one-click installer: https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods/AdventMod

Before upload (RELEASE.md has the list): a fresh plain `build.ps1` (never the `-JiggleSkin` build: it
carries a game texture), the current gi-cascades `d3d8.dll` copied into `System\`, the stray `.asm` and
`.png` out of `U2Shaders\`, the three missing licence texts in `Licenses\`, the FPS graph off.

**Permissions / third-party content:** yes, third-party code under open licences:
d3d8to9 (BSD-2), SMAA (MIT), AMD CAS (MIT), Khronos PBR Neutral (Apache-2.0), Inigo Quilez's texture repetition / fog (CC BY-NC-SA 3.0), UnityPCSS (MIT), Dear ImGui (MIT) and stb_image_write (public domain) inside the d3d8.dll.
All credited in `Licenses\CREDITS.txt`. AdventMod itself: GPL-3.0, non-commercial. No game textures are included; a few meshes are cut or re-rigged from the game's own models (gib pieces, the jiggle Seeker).

**Screenshots:** before/after pairs (crowd room, station, outdoors), the Graphics page, a blood scene
after a fight (pools, runs, prints), a hound pack mid-fight, a Seeker with a plate knocked off.

---

## Description (BBCode)

```
[size=5][b]AdventMod 3.0[/b][/size]
Shadows that work, a modern post-processing chain, blood that behaves like a liquid, enemies that think, and the launcher's settings inside the game.

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

[size=4][b]Gore[/b][/size]
[list]
[*]Blood sprays and splats where people are hit; bodies bleed into pools that spread and join; wall sprays run down in rivulets
[*]Streaks run down wounded bodies, parts that come apart stay joined by sticky strings for a moment, drops fall from ledges and ceilings, everyone who walks through blood leaves prints
[*]Blood is wet and shiny, then dries matte and brown; deep pools reflect the room
[*]Gibs, severed limbs, stumps, blood-soaked skins, brass casings, rubble, bullet holes and breaches in walls
[*]Blood on Gideon's hands and gun after a close kill; drops on the lens
[*]Ragdolls with the mod's own joint limits, death animations by where the hit landed, knockdowns and staggers
[*]Everything has a switch in System\AdventMod.ini
[/list]

[size=4][b]Enemies that think[/b][/size]
[list]
[*]Feelings: fear, anger and pressure from fire. Suppressed enemies duck into cover, frightened ones fall back or panic, angry ones charge; only a few shoot at once; the first shot after spotting you comes a beat late; squads push and flank along the level's paths
[*]Hound packs: one holds the front and feints, the others skip round to your sides, one leaps at a time; against a wall you get pinned; hounds leap off walls at you
[*]Needs: hungry hounds feed on fallen mates in a lull, tired creatures rest, curious ones investigate noises, frightened ones look for cover or a mate
[*]Seekers raise their arms in anger and pull them in when afraid; hounds snarl and cower and stand level on slopes
[*]Seeker soldiers wear steel plates that dent and fly off; a hit on armour sparks instead of bleeding
[/list]

[size=4][b]Gideon and the bodies[/b][/size]
[list]
[*]Leans into turns, vaults waist-high cover at a run, slams into walls on a dodge, barges breakable props
[*]An energy blade some Seekers drop: three hand-keyed swings, cuts heads and limbs
[*]Seeker infantry flesh that lags and settles with the body and kicks on a hit; the armour never deforms
[*]Foot IK (off by default, one ini line): feet stand on the real floor on stairs and step edges
[/list]

[size=4][b]Performance and fixes[/b][/size]
The game renders a few hundred frames a second for nothing; AdventMod caps it at your monitor's refresh rate. Raw mouse look, no camera spin from an idle gamepad, no lock-on jumps to floor weapons mid-fight, no freezes on the indoor/outdoor shadow switch.

[size=4][b]In-game options[/b][/size]
Options is a hub, one press from each page, from the title and the pause menu: [b]Gameplay[/b] (difficulty, damage dealt and taken, boss damage, running speed), [b]Camera[/b], [b]Audio[/b] (with Dialogue Volume), [b]Screen[/b] (real resolutions, fullscreen mode, VSync, frame cap), [b]Graphics[/b] (post preset, soft shadows, GI, ambient light, SMAA, shadow darkness, sharpening, FOV), [b]Quality[/b], [b]Accessibility[/b] (blood, colorblind modes with a strength slider, HUD fade, slow-mo weapon select, auto aim, toggle crouch), [b]Controls[/b]. Everything applies at once.

[size=4][b]Install[/b][/size]
Extract the zip, then copy everything in its [i]System[/i] folder into the game's [i]System[/i] folder (rename your own d3d8.dll first if you have one, e.g. dgVoodoo) and the [i]KarmaData[/i] folder next to it. Then add a few configuration lines to Mydefault.ini and MyDefUser.ini, as described step by step in the README.
Or take the GitHub version, which has a one-click installer and uninstaller that back up everything they change.

Works with the Steam/GOG version and Advent Revising (already included there). Tested on Steam, Windows 10, NVIDIA. Known limits are listed in the README (wall-kicks are rare, foot IK is new, hounds never ragdoll, light shafts and exclusive fullscreen unverified).

[size=4][b]How it works[/b][/size]
AdventMod is an UnrealScript package (compiled with AdventUCC, which runs the compiler hidden in the game's Editor.dll), a small native helper (shadow fixes, frame cap, foot IK and flesh springs inside the engine's pose build, the armour test), and a d3d8.dll: a fork of crosire's d3d8to9 with shader-based shadow filtering, post-processing, GI, live blood sheets and the rest. Full source on GitHub.

[size=4][b]Credits[/b][/size]
GlyphX Games / Majesco for Advent Rising; Mike Tyndall for Advent Revising; crosire for d3d8to9; Jorge Jimenez et al. for SMAA, the bloom technique and separable SSS; AMD for CAS; Khronos for PBR Neutral; Inigo Quilez for the texture repetition and fog techniques; Lucas Norr for UnityPCSS; Omar Cornut (Dear ImGui) and Sean Barrett (stb); McGuire, Mara and Luebke (SAO); Mikkelsen (hex tiling); Sannikov (radiance cascades); NVIDIA Kimodo for the generated death clips.
```
