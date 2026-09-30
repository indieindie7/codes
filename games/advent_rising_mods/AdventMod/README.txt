AdventMod 1.0 - in-game options for Advent Rising
==================================================

Advent Rising's display settings live in a separate launcher window. This mod
puts them, and a few the game never had, into the game's own options menus:
the ones on the title screen and in the pause menu, so you can change them
while playing.

  Options > Video
      Fullscreen            on / off
      Borderless Window     fills the screen without a title bar
      VSync
      More Display Options  opens the page below
  Display Options (new page)
      Widescreen
      Trilinear Filtering
      Field of View         60 - 120 (the game's own is 75)
      Minimum Frame Rate
  Options > Graphics
      Resolution            the five largest common sizes that fit your screen
                            (the game's list is 640x480 to 1600x1200, 4:3 only)
  Options > Audio
      Dialogue Volume       the game saves one but never showed the slider

Everything applies at once and is remembered. The mod's pages also get a light
panel behind them, so the game's dark menu text stays readable over any scene.

No game file is replaced: the mod adds three files and four lines of
configuration. It works alongside Advent Revising (which the Steam and GOG
versions already include) and with the launcher.

Tested with the Steam version on Windows 10.


INSTALL
-------
Easy way: extract the zip anywhere, close the game, and double-click
"Install AdventMod.bat". It finds the game (Steam libraries, GOG, or asks you
for the folder), backs up every file it changes (*.adventmod-backup), copies
the three mod files and adds the configuration lines. If Windows says it can't
write to the game folder, right-click the .bat and choose "Run as
administrator".

Manual way:

1. Close the game.

2. Copy the three files from the zip's System folder into the game's System
   folder (e.g. ...\steamapps\common\Advent Rising\System):
       AdventMod.u   AdventMod.int   AdventNative.dll

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
- Field of View is the third-person camera's value. First person and vehicle
  cameras are widened by the same ratio. Cutscene cameras are left alone.
- The launcher's own FOV switch works by changing your "move forward" key so
  that it resets the view every time you release it. The mod removes that from
  the key when the game starts, so use the in-game slider instead.
- Fullscreen and Borderless Window exclude each other: turning one on turns
  the other off.
- VSync, Widescreen, Trilinear, Borderless and FOV are stored in
  System\AdventMod.ini. The game stores the rest itself.
- The panel behind the pages can be changed or switched off in
  System\AdventMod.ini:
      [AdventMod.ModPanel]
      bPanel=True
      PanelColor=(R=255,G=255,B=255,A=120)     (A = how solid, 0-255)
- System\AdventNative.log is a small log the mod writes; useful if something
  doesn't work.


UNINSTALL
---------
Double-click "Uninstall AdventMod.bat": it removes the configuration lines and
the mod's files and leaves everything else as it was. By hand: remove the
lines from steps 3-5 and delete AdventMod.u, AdventMod.int, AdventNative.dll,
AdventMod.ini and AdventNative.log from System.


HOW IT WORKS
------------
- AdventMod.u is an UnrealScript package. The game takes the class of its menu
  controller from its configuration; the mod's controller opens the mod's
  versions of the Video, Graphics and Audio pages, which extend the game's own.
  A small mutator runs in every level and keeps the field of view applied.
- AdventNative.dll does what script cannot: the borderless window and asking
  Windows which resolutions fit the screen. The game loads it by itself.
- The game shipped without a script compiler. The mod was compiled with
  AdventUCC, a small tool that runs the compiler hidden in the game's
  Editor.dll. Source for both:
  https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods
  The Source folder in this zip has the mod's script and C code.


CREDITS
-------
- GlyphX Games / Majesco - Advent Rising
- Mike Tyndall - Advent Revising, the unofficial patch
