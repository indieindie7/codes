U2SoftShadows 1.3 - multi-light soft character shadows for Unreal II: The Awakening
===================================================================================

Every character casts soft shadows from the lights around it - up to three
lamps plus the sun - instead of the engine's single shadow, and a soft contact
shadow grounds them on the floor. Shadows are always soft, fade in and out as
characters move between lights, and are darker under bright nearby lamps than
under dim distant ones. Everything is adjustable in game (Options > MISC >
"Soft Shadows (mod): OPEN").

1.3 makes the lamp shadows actually visible (a fade bug hid most of them since
1.0), adds the contact shadow, and runs faster than 1.2 in big fights.

Tested with the Steam version plus SOverhaul 1.1 and dgVoodoo2. It only uses
the stock game packages, so it should also load on an unmodded game, but that
setup is untested.


REQUIREMENTS
------------
- Unreal II: The Awakening (Steam/GOG, patch 2001 / 1403)
- Recommended: SOverhaul (Nexus) + dgVoodoo2 (D3D8 wrapper).
  Without a D3D11 wrapper such as dgVoodoo2, dynamic shadows may render as
  black squares on modern GPUs.


INSTALL
-------
Easy way: extract the zip anywhere, close the game, and double-click
"Install U2SoftShadows.bat". It finds the game (Steam libraries, GOG/retail
registry entries, or asks you for the folder), backs up every file it changes
(*.u2ss-backup), then:
  - copies System\U2SoftShadows.u
  - adds the mod to the Mutator= line in User.ini (keeps your other mutators)
  - raises the shadow texture pool in Unreal2.ini
  - updates settings saved by an older version (see UPGRADING)
  - adds the options page to the game's menus
If Windows says it can't write to the game folder, right-click the .bat and
choose "Run as administrator".

Manual way (everything except the in-game options page):

1. Close the game.

2. Copy System\U2SoftShadows.u into the game's System folder, e.g.
   C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System

3. Open System\User.ini and find the [DefaultPlayer] section. Add this line
   anywhere inside it:

       Mutator=U2SoftShadows.SSShadowMutator

   (In singleplayer the game ignores ServerActors, but every key in
   [DefaultPlayer] is added to the map URL, so this loads the add-on on every map.)
   If a Mutator= line already exists there, join them with a comma instead:
       Mutator=Other.Mutator,U2SoftShadows.SSShadowMutator

4. Recommended: open System\Unreal2.ini, search for ShadowBitmapMaterial and
   raise the shadow texture pool from 16 to 48:

       ObjectPoolPrecacheList=(ObjectClass=Class'Engine.ShadowBitmapMaterial',NumObjects=48)

5. Make sure shadows are enabled in the game's video options.

Note: saves made BEFORE installing don't include the mod (loading a save
restores the level as it was saved, including its mods), so it starts working
at the next level change. New games and saves made afterwards have it.

To check that it works, open System\Unreal2.log after playing. It should have
lines like "U2SoftShadows: manager active on ..." and
"U2SoftShadows: multi-light shadows for ...".


UPGRADING FROM 1.0-1.2
----------------------
The installer does this for you. By hand: in System\User.ini, section
[U2SoftShadows.SSShadowController], delete the lines GradientLength,
GradientScale, LightResolution and UnseenTime (or the whole section). Values
saved by the older versions override the new defaults - the old fade values
are what kept lamp shadows nearly invisible.


SETTINGS
--------
In game: Options > MISC > "Soft Shadows (mod): OPEN" (installed by the .bat).
The game's own shadow settings stay on the MISC page; "Engine Shadows: OPEN"
takes you back.

Or in System\User.ini, section [U2SoftShadows.SSShadowController] (the values
shown are the defaults; the game writes the section after the first run):

bEnabled=True             ; off = the game's own single shadow
MaxShadows=3              ; lamp/sun shadows per character (0 = contact shadow only)
ShadowStrength=190        ; darkness 0-255
GradientScale=3.0         ; fade length as a multiple of the shadow's length
GradientLength=2048       ; longest the fade may reach
bFitToFloor=True          ; end the fade where the shadow really lands (stairs, slopes), not on flat ground
bContactShadow=True       ; soft dark patch on the floor under the feet
bHardToSoft=True          ; a crisper copy at the feet, fading fast, under the soft one
LampResolution=128        ; lamp shadow texture size: 64 very soft, 128 soft
SunResolution=128         ; sun shadow texture size
MinStrength=0.2           ; darkness from the faintest lamp, relative to the darkest
FullIntensity=128         ; lamp brightness x closeness that casts the darkest shadow
MaxSteepness=60           ; overhead lamps are tilted so the shadow falls where you see it
bCameraCull=True          ; only characters the camera can see get shadows
CullFOVMargin=20          ; degrees beyond the view before a character is dropped
UnseenTime=0.3            ; ...or after this many seconds unrendered
CullDistance=3000         ; no shadows beyond this distance
NearDistance=900          ; within this: every shadow
MidDistance=2000          ; within this: one lamp shadow + contact; beyond: contact only
MaxLightDistance=1300     ; lights further than this cast no shadow
UpdateFrequency=0.2       ; seconds between light re-checks
FadeRate=2.5              ; fade speed when switching lights (per second)
SunClearance=1000         ; the sun casts when nothing is this close above, toward it
bCapsules=False           ; experimental: soft per-limb ovals from the skeleton (~20 fps in big fights)
bWeightedPick=False       ; pick lamps at random weighted by strength (variety between characters)
bPerLightSoftness=False   ; crisper texture for bright near lamps (little visible effect)


UNINSTALL
---------
Double-click "Uninstall U2SoftShadows.bat". It removes the Mutator entry, the
settings section, the options page and its labels (the menu files come back
exactly as they were), and U2SoftShadows.u. By hand: remove the Mutator entry
and the settings section from User.ini, then delete System\U2SoftShadows.u.


SOURCE / REBUILDING
-------------------
The UnrealScript source is in Source\U2SoftShadows (Classes and Textures). To
rebuild, copy the U2SoftShadows folder into the game folder, add
EditPackages=U2SoftShadows to the [Editor.EditorEngine] section of
Unreal2.ini, delete System\U2SoftShadows.u and run "UCC make" from System.


HOW IT WORKS
------------
SOverhaul ships SquirrelZero's UT2004 RealtimeShadows but has it switched off,
because it cannot draw in Unreal II's shadow renderer. This add-on is an
independent implementation of the same idea on top of Unreal II's own
ShadowProjector:
- a mutator spawns a manager that gives each live character a controller;
  the manager collects the level's lights once and shares them
- the controller scores lights by how strongly they light the character
  (brightness x falloff over the light's reach) and picks the strongest
  visible ones, and the sun whenever there is open sky in its direction
- each shadow stays on its light while that light remains in the top set, and
  fades out and back in when it changes lights
- the projector's depth fade is fitted to the shadow's length on the ground
- the contact shadow is a fixed soft texture projected straight down, like a
  decal, so it costs almost nothing
- characters off camera or far away drop to fewer shadows, then none
- the options page is a UIHelper (SSMenuHelper) registered by the menu script


CREDITS
-------
- SkacikPL - SOverhaul
- SquirrelZero - RealtimeShadows for UT2004, which inspired the idea of
  per-light character shadows (no code from it is included)
- Epic / Legend Entertainment - Unreal II


CHANGES
-------
1.3 - lamp shadows now show: the depth fade ended at the character's middle,
      so most of each lamp shadow was faded out before it reached the floor
      (present since 1.0). Shadows are darker under bright near lamps.
    - Unreal II's sun (a SunLight actor) is now recognised; sun shadows cast
      outdoors.
    - new: soft contact shadow under the feet (lightens and spreads in jumps)
    - new: hard-to-soft - a crisper copy at the feet under the soft shadow
    - all shadows soft: lamp shadows use the same soft texture as the sun
    - faster: shadows only for characters the camera can see, fewer shadows
      at a distance (full within 900 units, one lamp + contact within 2000)
    - new: in-game options page (Options > MISC > "Soft Shadows (mod): OPEN");
      changes apply immediately
    - experimental, off by default: capsule shadows, weighted light choice
    - the installer migrates settings saved by older versions
1.2 - performance: no more stutter when enemies spawn, and higher frame rates
      in big fights. Characters far away (CullDistance) or off screen
      (UnseenTime) drop their shadows; lights are gathered once per level.
1.1 - added Install/Uninstall .bat files (no change to the add-on itself)
1.0 - first release
