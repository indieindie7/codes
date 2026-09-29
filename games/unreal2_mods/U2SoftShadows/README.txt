U2SoftShadows 1.2 - multi-light soft character shadows for Unreal II: The Awakening
===================================================================================

Every character gets up to 3 shadows, one per nearby light, instead of the
engine's single shadow. Shadows fade in and out as characters move between
lights (no snapping), are darker near a light and lighter far from it, and
fade from the feet towards the head. Outdoors the sun always casts a soft shadow.

Tested with the Steam version plus SOverhaul 1.1 and dgVoodoo2. It only uses
the stock Core/Engine packages, so it should also load on an unmodded game,
but that setup is untested.


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
registry entries, or asks you for the folder), backs up your ini files
(*.u2ss-backup), then does steps 2-4 below for you. It keeps any other
mutators you already use. If Windows says it can't write to the game folder,
right-click the .bat and choose "Run as administrator".

Manual way:

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

   With 3 shadows per character, 16 textures run out in busy scenes.

5. Make sure shadows are enabled in the game's video options.

Note: saves made BEFORE installing don't include the mod (loading a save
restores the level as it was saved, including its mods), so it starts working
at the next level change. New games and saves made afterwards have it.

To check that it works, open System\Unreal2.log after playing. It should have
lines like "U2SoftShadows: manager active on ..." and
"U2SoftShadows: multi-light shadows for ...".


SETTINGS (optional)
-------------------
Add this section to the end of System\User.ini and adjust it. The values shown
are the defaults:

[U2SoftShadows.SSShadowController]
MaxShadows=3              ; shadows per character (more = heavier)
MaxLightDistance=1300     ; lights further than this cast no shadow
UpdateFrequency=0.2       ; seconds between light re-checks
ShadowStrength=190        ; darkness 0-255
FadeRate=2.5              ; fade speed when switching lights (per second)
GradientLength=600        ; longest the feet-to-head fade may stretch
GradientScale=1.1         ; lower = the fade is stronger/shorter, higher = more shadow at the head
SunResolution=128         ; sun shadow softness: 64 very soft, 128 soft, 256 sharp
LightResolution=0         ; lamp shadow texture size, 0 = game setting
CullDistance=3000         ; characters further from you than this cast no shadows
UnseenTime=1              ; nor do characters off screen for this many seconds


UNINSTALL
---------
Double-click "Uninstall U2SoftShadows.bat", or by hand:
Remove the Mutator= line from User.ini (and the optional settings section),
then delete System\U2SoftShadows.u.


SOURCE / REBUILDING
-------------------
The UnrealScript source is in Source\U2SoftShadows\Classes. To rebuild, copy
the U2SoftShadows folder into the game folder, add
EditPackages=U2SoftShadows to the [Editor.EditorEngine] section of
Unreal2.ini, delete System\U2SoftShadows.u and run "UCC make" from System.


HOW IT WORKS
------------
SOverhaul ships SquirrelZero's UT2004 RealtimeShadows but has it switched off,
because it cannot draw in Unreal II's shadow renderer. This add-on is an
independent implementation of the same idea on top of Unreal II's own
ShadowProjector:
- a mutator spawns a manager that gives each live character a controller
- the controller scores lights by how strongly they light the character
  (brightness x falloff over the light's reach) and picks the strongest visible ones, and the sun whenever
  there is open sky in its direction
- each shadow stays on its light while that light remains in the top set, and
  fades out and back in when it changes lights
- the projector's depth gradient is fitted each frame to the shadow's length
  on the ground


CREDITS
-------
- SkacikPL - SOverhaul
- SquirrelZero - RealtimeShadows for UT2004, which inspired the idea of
  per-light character shadows (no code from it is included)
- Epic / Legend Entertainment - Unreal II


CHANGES
-------
1.2 - performance: no more stutter when enemies spawn, and higher frame rates
      in big fights. Characters far away (CullDistance) or off screen
      (UnseenTime) drop their shadows; lights are gathered once per level.
1.1 - added Install/Uninstall .bat files (no change to the add-on itself)
1.0 - first release
