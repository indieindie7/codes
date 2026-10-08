# AdventMod

A mod framework for **Advent Rising** (Steam), built with [AdventUCC](../AdventUCC).
It brings the settings of the separate launcher ("Play Advent Rising") into the
game's own options menus, reachable from the title menu and from the pause menu.

> **Fixed 2026-10-03: slow motion and choppy gameplay.** AdventNative made a throwaway
> Direct3D 8 device (to find the game's device methods) without `D3DCREATE_FPU_PRESERVE`.
> Direct3D then drops the game thread's x87 FPU to single precision, and Unreal's frame
> timing (CPU cycle counter, in doubles) breaks: every frame's time step comes out wrong.
> At first it looked like the menu controller killed the frames, because the controller is
> what loads AdventNative; it was this. Measured after the fix: a 10 s wait in game takes
> 10.0 s of real time (before: 22-44 s). Any native code here that creates a device must
> pass FPU_PRESERVE.

| Page | Added |
|---|---|
| Options > Video | **Borderless Fullscreen** (the default: a window covering the screen), **Exclusive Fullscreen**, **VSync**, and a row that opens Display Options |
| Display Options (new page) | **Widescreen**, **Trilinear Filtering**, **Colorblind Mode** (Protanopia, Deuteranopia, Tritanopia: daltonization in the U2Shaders final pass, Machado et al. 2009 simulation + error shift) with a **Colorblind Correction** strength slider, **Field of View** (60-120), **Minimum Frame Rate** |
| Graphics (new page, from Display Options) | **Post Effects** preset (Off, Natural, Cinematic, Gritty, Clean), **Soft Shadows**, **Shadows for Others** (the 20 nearest characters on screen), **Anti-Aliasing (SMAA)**, **Frame Cap** (monitor, 30, 60, 120, 144, none), **Shadow Darkness**, **Sharpening**. The post-processing rows need the U2Shaders `d3d8.dll`: AdventNative writes `System\U2Shaders.ini`, which the layer re-reads while the game runs |
| Options > Graphics | **Resolution** lists the five largest common sizes that fit the screen (stock: 640x480 to 1600x1200, 4:3 only) |
| Options > Audio | **Dialogue Volume** (the game saves one and has a caption for it, but never showed the slider) |

Settings apply at once. Borderless, VSync, Trilinear, Widescreen and FOV are saved in
`System\AdventMod.ini` and re-applied at start (the render device never saves
its own); the rest are saved by the game.

**Field of View.** The game has no FOV setting: each camera (third person 75,
first person 85, vehicles 90-95) sets its own when it takes over. The slider is
the third-person value and every gameplay camera is scaled by FOV/75, so the
views keep their relation; scripted camera points keep their framing, and zooms
still return to the scaled value. Nothing is touched at 75. The launcher's own
FOV option is a key-binding hack (`W=MoveForward | OnRelease FOV 75`) that would
undo this on every key release, so the mod removes it from any key at start.

**Camera spinning on its own.** The game turns the camera with
`JoyR=AxisRaw aTurn` / `JoyU=AxisRaw aLookup`; an axis the pad doesn't have, a
receiver without a pad, or a pad that switched off reads -1, which the 0.25 dead
zone never catches. `ModInput` (always the player's input class) only counts a
pad axis after it has been near the centre, and drops it again after 1.5 s frozen
at one exact off-centre value. Mouse and keyboard are untouched (the mouse is
added after the filter). `bPadDriftFix=False` turns it off.

**Destructible armour (Seeker soldiers), rebuilt 2026-10-07.** The Seekers wear steel plates of
our own (helmet, chest, shoulders, thighs) attached to their bones; a plate dents at half its
points and is knocked off whole when it breaks. The first version's flesh repaint (a pink sheen
in play) is off. [ARMOUR.md](ARMOUR.md) has the history, lessons and the rebuild. The damage
model, as first built, the way the new Wolfenstein games do it:
Seeker infantry, elites, commanders and pilots carry six plates (head, torso, each arm,
each leg) with points of their own. While a plate holds, a hit on it loses 70 % of its
damage to the plate; when the points run out the plate
breaks: the region's own piece of the character's mesh (the gib parts) flies off as the plate,
a little smaller than the limb and in the body's skin, with a couple of chunks; the body
jerks and staggers, and from then on hits there do 1.5 x
(a bare head 2 x: break the helmet, then headshots count). Explosions rattle every plate
at once and hurt the body in full. Time to kill is preserved: the plate points are chosen
so that a region shot from full health takes the same total damage to kill as without
armour (helmet: 235 damage to break it, 165 after; torso 167 and 233; limbs are lighter
and a little faster), so the armour moves damage around in time rather than adding health.
`[AdventMod.ModArmor]` in `AdventMod.ini`: `bArmor`, `bPreserveTtk` and the region shares
(or the plain plate shares with it off), `Absorb`, `ExposedBonus`, `HeadBonus`,
`bArmorLog`, `bPlates`, `PlateScale`, `PlateStay`, `bExpose`. Under a broken plate the flesh
shows: one Combiner stage blends a flesh texture over the skin, a texture per set of broken
plates in the skin's own UV space with the meat in its colour and the region in its alpha
(`tools/make_armor_masks.py` cuts the regions from the character mesh by bone). It has to be
one stage with the texture as its own mask: a combiner inside a combiner, or a separate mask
texture, drew the whole Seeker as a flat colour. A blood coat comes off an exposed body. The
Seekers' left and right limbs share texels, so a broken arm shows flesh on both arms.

**Blood streaks down the bodies (2026-10-08, untested in game).** Blood from a wound runs
straight down the body under gravity, whatever the pose, in thin rivulets with a bead at each
front, then dries dark (brown-black, plum for Seekers). The skins can't carry it (UV "down" isn't
the body's down, and a projector on a skinned mesh draws one flat colour, see `ModBloodCoat`), so
the U2Shaders `d3d8.dll` draws it per pixel in world space (`streaks.hpp` in the fork):

- `ModGore` keeps the bleeding points: every wound (its `ModStump`), every cut (`ModSever`'s
  cap) and every bleeding hit, living or corpse (the nearest bone and an offset in its axes).
  Up to 4 a body; they go with the body (removed, gibbed, brought back) or after `StreakLife`
  (60 s, fading over the last 5). Each tick the 8 nearest the view are sent through
  AdventNative (`Blood:streak K x y z nx ny kind age strength seed`, then `Blood:streaks n`),
  with the body's outward direction there (from the hips' vertical line).
- The layer draws every character draw (lit, solid, textured, an FVF with normals: the same
  test as the shot mask, plus no alpha test) a second time with the game's vertex processing and
  a streak pixel shader, two bleeding points a pass, only those within 220 units of the draw's
  world origin. The shader gets the world position from the camera-space position (texgen) and
  the inverse view; only surface close below a point (25 units across, 9 out of / 14 into the
  body) takes blood. It is multiplied by the lit colour, gets a small wet highlight while fresh,
  and is fogged like the game (the pass blends premultiplied "over").
- `U2Shaders.ini`: `streaks=1` (off when missing), `streakparams=` width length speed
  drysecs (2.5 40 6 50: a rivulet's width and longest run in world units, its starting speed,
  seconds until dry), `streakfx=` highlight, opacity, colour gain over the lit colour, reach
  across (1 0.92 2 25). `[AdventMod.ModGore]`: `bBodyStreaks`, `StreakLife`, `StreaksPerBody`.
- `py tools/streaks_sim.py [out.png] [width length speed drysecs]` renders the same maths on
  a cylinder at several ages (`tools/streaks_sim.png`), to tune without the game.

**Goo strings (2026-10-08, untested in game).** Sticky strands of blood (purple for Seekers)
stretch between body parts that just came apart, sag under gravity, thin as they stretch, wobble,
and snap once stretched past a limit, leaving two short dangling ends that drip. The U2Shaders
`d3d8.dll` draws them (`strings.hpp` in the fork); `ModGore` owns the pairs:

- A cut (`ModSever.Sever`) makes a string from the cut bone to the thrown piece (40%: a second,
  thinner one), and 60% one between the upper and lower arm/leg when both fly. A body blown apart
  (`SpawnGibs`) makes 1-3, each from a random piece to its nearest neighbour on the body. At most
  12 at once (the layer's slots).
- Each starts slack: its rest length is `GooRestMin`-`GooRestMax` (18-30, scaled with the body)
  or the gap if that is longer. It snaps past rest x `GooStretchMin`-`GooStretchMax` (1.6-3, random
  per string), after `GooLifeMin`-`GooLifeMax` seconds (6-12), or when an end is hidden; a small
  splat lands under its middle. While stretched it pulls on a flying piece (`GooPull`). The halves
  are drawn for `GooDangle` seconds (3.2), then the slot is freed.
- Every tick each live string goes through AdventNative: `Blood:string K ax ay az bx by bz kind
  radius rest age snap seed` (snap: seconds since it snapped, -1 whole), `Blood:stringoff K` when
  done, `Blood:stringclear` at level start.
- The layer draws them once a frame after the world, before the post chain and the HUD (at the
  first HUD draw), with the scene's view, projection, viewport and fog, depth tested against the
  game's depth: a camera-facing strip of 16 segments along a curve that sags with the slack
  (the middle on a damped spring, so it wobbles when the ends jerk), thinner in the middle when
  stretched, a blob at each end. Shading: a wet cylinder (dark body, specular stripe, wet rim, the
  thin middle translucent) times a scene light level. Snapped: each half whips back, falls to
  hang, shortens to a stub over ~1 s, and drips (a bead swells and drops fall).
- `U2Shaders.ini`: `strings=1` (off when missing), `stringparams=` thickness sag stretch life
  (multipliers on radius, sag and middle thinning; the halves' shortening time in seconds; 1 1 1 1),
  `stringfx=` light gloss opacity rim (0.55 1 0.9 0.5). `[AdventMod.ModGore]`: `bGooStrings`,
  `GooRestMin/Max`, `GooStretchMin/Max`, `GooLifeMin/Max`, `GooThick` (radius, 0.9), `GooDangle`,
  `GooPull`.
- Pilot: `GOOSEVER [cut]` (the nearest other character, a corpse first, loses part `cut` of
  `ModSever.Cuts`, default 3: the right arm), `GOOLIST` (the live strings), `GIBAHEAD` (gibs, with
  strings).
- `py tools/strings_sim.py [out.png] [thickness sag stretch life]` renders the same maths from the
  side, a piece thrown off a stump, over time (`tools/strings_sim.png`).

## How it works

No stock game file is replaced.

- **`AdventMod.u`** (UnrealScript, `Classes\`)
  - `ModGUIController` extends the game's menu controller. The game picks that
    class from its config (`GUIController=` in `[Engine.Engine]`), so ours takes
    over `OpenMenu` and swaps in modded pages by name.
  - `ModVideoOptions`, `ModPCOptions`, `ModAudioOptions` extend the stock pages;
    `ModDisplayOptions` is a new page. An options page has at most 7 rows
    (toggles first, then up to 3 sliders).
  - `ModPanel` adds a translucent panel behind a page (the game's labels are dark
    grey and unreadable over a dark scene); colour in `[AdventMod.ModPanel]`.
  - `ModSettings` holds the saved settings, the FOV code and the bridge to native code.
  - `ModMutator` runs in every level (the menu controller is never ticked), also
    while paused (`bAlwaysTick`), and keeps the FOV applied. The game adds the keys of `[DefaultPlayer]` to every
    level URL and its GameInfo loads `Mutator=` from it.
  - `ModTestCommandlet`: `AdventUCC AdventMod.ModTestCommandlet` returns 7 when
    the native bridge works.
- **`AdventNative.dll`** (C, `native\`) does what script can't: the window.
  The engine loads it by itself: a `DynamicLoadObject("AdventNative.X")` finds
  no `AdventNative.u` and falls back to the package's DLL. The DLL then
  redirects Core's `UObject::StaticLoadObject`, so
  `DynamicLoadObject("AdventNative.<Command>", class'Class', true)` becomes a
  call into the DLL; non-None means true. Commands: `BorderlessOn`,
  `BorderlessOff`, `IsBorderless`. It writes `System\AdventNative.log`.

## Install

Players: `Install AdventMod.bat` (see `README.txt`, the player's readme). It
finds the game, backs up what it changes, copies `System\AdventMod.u`,
`AdventMod.int` and `AdventNative.dll`, and adds the configuration lines to
`Mydefault.ini` and `MyDefUser.ini` (and to their copies in `System\Defaults`,
which the launcher's "Default" button restores from). `Uninstall AdventMod.bat`
removes exactly those lines and files. The launcher itself only rewrites its
own settings line by line, so the mod's lines survive it.

Developers: `build.ps1` compiles with AdventUCC, builds the DLL and installs
into the game; `package.py` makes the release zips (with and without the .bat
files) in Downloads.

## Tested

Steam version, Windows 10, 1920x1080, by running the game (`test_run.ps1`) and
pressing the rows from inside through the debug settings:

- Borderless on/off: window measured 1920x1080 without caption, and back.
- VSync, Trilinear, Widescreen: the render device's value changes each way.
- Minimum Frame Rate: the slider sets it and the game saves it.
- Resolution: the list cycles 1024x768, 1280x720, 1366x768, 1600x900, 1920x1080.
- Dialogue Volume: the slider shows and moves.
- Field of View: in a level at 100, the third-person camera goes 75 -> 100
  (log) and the view is visibly wider (screenshot); the launcher's binding is
  removed from W.
- All four pages checked by screenshot.

Not verified: **Fullscreen** (exclusive fullscreen was not run), whether VSync
and Widescreen visibly change the picture, and reaching the pages by hand.

Debug settings, under `[AdventMod.ModSettings]` in `AdventMod.ini`:
`DebugCommands` (console commands at the title menu), `DebugOpenMenu` (a menu
class opened right after the title menu) and `DebugActions` (`clickN`,
`slideN=V`, `native:X` or console commands on that menu). Results are written
to `System\AdventNative.log`.
