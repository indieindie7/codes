AdventMod 2.0 - shadows, post-processing and in-game options for Advent Rising
==============================================================================

What it does:

  Shadows
      Characters' shadows work again: the stock game loses most of them
      (its sky pass draws over them, and the shadow bitmaps lose their alpha).
      Soft shadows from the real lamps around a character (up to 4 for you,
      one each for the 20 nearest people on screen, the crowds included);
      outdoors one shadow from the sun, as strong as the sun is bright.
      Indoors your shadow sharpens where it touches the ground and softens
      further away (contact-hardening shadows).

  Post-processing (replaces the game's own blur effects)
      Bloom in linear light with a soft highlight roll-off, colour grading
      through a LUT, contrast-adaptive sharpening (AMD CAS), SMAA
      anti-aliasing, a light vignette, film grain and dithering.
      Five presets: Off, Natural, Cinematic, Gritty, Clean.

  Terrain
      Outdoor ground blends its textures by height (sand settles between
      rocks instead of a soft cross-fade) and hides the tiling pattern.

  Fixes
      The game ran its frames at a few hundred a second; the frame rate is now
      capped at your monitor's refresh rate (much less GPU load).

  In-game options (the launcher's settings, in the game's own menus)
      Options > Video
          Fullscreen, Borderless Window, VSync, More Display Options
      Display Options (new page)
          Widescreen, Trilinear Filtering, Field of View (60 - 120),
          Minimum Frame Rate, Graphics
      Graphics (new page)
          Post Effects preset, Soft Shadows, Shadows for Others,
          Anti-Aliasing (SMAA), Frame Cap (monitor / 30 / 60 / 120 / 144 /
          none), Shadow Darkness, Sharpening
      Options > Graphics
          Resolution: the five largest common sizes that fit your screen
      Options > Audio
          Dialogue Volume (the game saves one but never showed the slider)

Everything on the option pages applies at once and is remembered.

No game file is replaced. The mod adds its files to System and a few lines of
configuration; the Direct3D layer is a d3d8.dll next to the game, so if you
already have one there (dgVoodoo, for example) it is backed up, and you can put
it back by uninstalling. It works alongside Advent Revising (which the Steam and
GOG versions already include) and with the launcher.

Tested with the Steam version on Windows 10 (NVIDIA). Needs a DirectX 9 card
with pixel shader 2.0b/3.0 (any GPU from the last 15 years).


INSTALL
-------
Easy way: extract the zip anywhere, close the game, and double-click
"Install AdventMod.bat". It finds the game (Steam libraries, GOG, or asks you
for the folder), backs up every file it changes (*.adventmod-backup), copies
the mod's files and adds the configuration lines. If Windows says it can't
write to the game folder, right-click the .bat and choose "Run as
administrator".

Manual way:

1. Close the game.

2. Copy everything in the zip's System folder into the game's System folder
   (e.g. ...\steamapps\common\Advent Rising\System):
       AdventMod.u   AdventMod.int   AdventNative.dll
       d3d8.dll      U2Shaders.ini   the U2Shaders folder
   If the game's System folder already has a d3d8.dll, rename it first
   (e.g. d3d8.dll.old) so you can put it back later.

3. Open System\Mydefault.ini. Under the line [Engine.Engine] add:

       GUIController=AdventMod.ModGUIController

   and at the end of the file add:

       [AdventMod.ModGUIController]
       bModAuthor=true
       bEmulatedJoypad=false
       bHideMousecursor=false
       bJoyMouse=false
       bJoyDeadZone=0.3

4. Open System\MyDefUser.ini. Under the line [DefaultPlayer] add:

       Mutator=AdventMod.ModMutator

5. Optional: make the same changes to the two files of the same name in
   System\Defaults. The launcher's "Default" button copies those over the live
   ones, which would otherwise switch the mod off.

Start the game as usual. If the new rows are missing from Options > Video,
the configuration lines are not in place.


GOOD TO KNOW
------------
- Settings: System\AdventMod.ini (the mod) and System\U2Shaders.ini (the
  post-processing look; the Graphics page writes it, and the game picks up
  changes while it runs, so you can also edit it by hand while playing).
- Field of View is the third-person camera's value. First person and vehicle
  cameras are widened by the same ratio. Cutscene cameras are left alone.
- The launcher's own FOV switch works by changing your "move forward" key so
  that it resets the view every time you release it. The mod removes that from
  the key when the game starts, so use the in-game slider instead.
- Camera spinning on its own: the game reads a missing or switched-off gamepad
  axis as full deflection. The mod ignores a pad axis until it has been near
  the centre, and again whenever it holds one exact value for 1.5 seconds.
  Off: bPadDriftFix=False under [AdventMod.ModSettings] in AdventMod.ini.
- Fullscreen and Borderless Window exclude each other: turning one on turns
  the other off.
- Less shadow work for a slower PC: Graphics > Shadows for Others off, or
  fewer of them in System\AdventMod.ini:
      [AdventMod.ModShadowManager]
      NpcShadows=20
- The panel behind the pages can be changed or switched off in
  System\AdventMod.ini:
      [AdventMod.ModPanel]
      bPanel=True
      PanelColor=(R=255,G=255,B=255,A=120)     (A = how solid, 0-255)
- System\AdventNative.log and System\U2Shaders.log are small logs the mod
  writes; useful if something doesn't work.


UNINSTALL
---------
Double-click "Uninstall AdventMod.bat": it removes the configuration lines and
the mod's files, puts back a d3d8.dll or U2Shaders.ini you had before, and
leaves everything else as it was. By hand: remove the lines from steps 3-5,
delete AdventMod.u, AdventMod.int, AdventNative.dll, d3d8.dll, U2Shaders.ini,
AdventMod.ini, the logs and the U2Shaders folder from System, and rename your
old d3d8.dll back if you had one.


HOW IT WORKS
------------
- AdventMod.u is an UnrealScript package. The game takes the class of its menu
  controller from its configuration; the mod's controller opens the mod's
  pages, which extend the game's own. A small mutator runs in every level: it
  gives characters their light-following shadows and keeps the settings
  applied.
- AdventNative.dll does what script cannot: the shadow fixes inside the
  engine, the borderless window, the frame cap, and writing the layer's
  settings. The game loads it by itself.
- d3d8.dll is a fork of d3d8to9 (the game's Direct3D 8 calls run on Direct3D 9)
  with "U2Shaders" added: the shadow filtering, the post-processing chain and
  the terrain shader. Its shaders are plain text in System\U2Shaders.
- The game shipped without a script compiler. The mod was compiled with
  AdventUCC, a small tool that runs the compiler hidden in the game's
  Editor.dll. Source for everything:
  https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods
  https://github.com/indieindie7/d3d8to9 (branch advent-post)
  The Source folder in this zip has the mod's script and C code.


CREDITS AND LICENCES
--------------------
- GlyphX Games / Majesco - Advent Rising
- Mike Tyndall - Advent Revising, the unofficial patch
- Patrick Mours (crosire) - d3d8to9 (BSD 2-clause, Licenses\d3d8to9-LICENSE.md)
- Jorge Jimenez et al. - SMAA (MIT, Licenses\SMAA-LICENSE.txt)
- AMD - FidelityFX CAS, ported in post_final.hlsl (MIT)
- Khronos Group - PBR Neutral tone mapper's highlight shoulder (Apache-2.0)
- Inigo Quilez - texture repetition (technique 3) and "better fog", in the
  terrain shader (CC BY-NC-SA 3.0)
- The bloom down/up sampling follows Jorge Jimenez's "Next Generation Post
  Processing in Call of Duty" (SIGGRAPH 2014).
AdventMod itself is free software under the GPL-3.0 and non-commercial:
share it, change it, keep the source open. See Licenses\CREDITS.txt.
