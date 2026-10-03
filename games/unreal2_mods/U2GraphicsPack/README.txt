U2 Graphics Pack 1.0 - modern rendering for Unreal II: The Awakening
====================================================================

All of our Unreal II graphics work in one mod:

- Soft multi-light character shadows (U2SoftShadows 2.0): every character
  casts shadows from the lamps around it and the sun, not just one. They
  fade as characters move between lights and are lighter in brightly lit
  rooms.
- Contact-hardening shadows (PCSS): sharp where a character touches the
  floor, softer farther away.
- Fixed black characters: under modern drivers some characters rendered
  pitch black when the engine dropped their light. They are lit correctly
  again.
- Post-processing: bloom (mip-chain, no blocky halos), a filmic tone curve,
  a colour grade (LUT) made for Unreal II, contrast-adaptive sharpening, a
  light vignette and dithering against colour banding. It applies to
  cutscenes too.
- SMAA anti-aliasing (smooth edges, no blur).
- Borderless fullscreen: the game's Fullscreen option becomes a borderless
  window at your desktop resolution. Alt-Tab is instant and the fullscreen/
  windowed toggle works both ways.
- The Liandri heavy armour's glass dome gets a swirling plasma core with
  refraction.

All of it runs through a new System\d3d8.dll (a fork of crosire's d3d8to9)
that renders through the Direct3D 9 built into Windows. dgVoodoo2 is NOT
needed any more.


REQUIREMENTS
------------
- Unreal II: The Awakening (Steam or GOG).
- Windows 10 or 11.
- The DirectX 9 runtime (d3dx9_43.dll). Most PCs with games already have it.
  If the game shows "Failed to load d3dx9_43.dll", install the "DirectX
  End-User Runtime" from Microsoft:
  https://www.microsoft.com/download/details.aspx?id=35


INSTALL (manual, about a minute)
--------------------------------
1. Close the game.

2. Copy the System folder from this zip into the game folder and allow it to
   overwrite. The game folder is usually
   C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening
   It adds:
     System\d3d8.dll          the renderer (replaces dgVoodoo's d3d8.dll if you
                              had it: back that one up first if you want it)
     System\U2Shaders.ini     its settings
     System\U2Shaders\        the shaders, the colour grade, the SMAA tables
     System\U2SoftShadows.u   the shadow add-on

3. Turn the shadow add-on on: open System\User.ini, find the
   [DefaultPlayer] section and add this line anywhere inside it:

       Mutator=U2SoftShadows.SSShadowMutator

   If there is already a Mutator= line there, add it to the end of that line
   after a comma instead:

       Mutator=Other.Mutator,U2SoftShadows.SSShadowMutator

4. Recommended: open System\Unreal2.ini, search for ShadowBitmapMaterial and
   raise the shadow texture pool from 16 to 48:

       ObjectPoolPrecacheList=(ObjectClass=Class'Engine.ShadowBitmapMaterial',NumObjects=48)

5. In the game: Options > Video, make sure shadows are on. For fullscreen,
   turn the game's Fullscreen option on; it is borderless now.

Saves made before installing don't include the shadow add-on. A save
restores the level with the mods it was saved with, so the add-on starts
at the next level change. New games, and saves made after installing,
have it. The renderer part works right away.

How to check it works: System\U2Shaders.log is written at every start, and
System\Unreal2.log has "U2SoftShadows: manager active on ..." lines.


IF YOU USE dgVoodoo2
--------------------
You don't need it any more. This pack's d3d8.dll replaces dgVoodoo's
d3d8.dll. If dgVoodoo's D3D9.dll is still in System, the pack runs through
it and dgVoodoo keeps its own fullscreen handling. To use the pack's
borderless fullscreen and plain Windows Direct3D 9 (the tested setup),
remove dgVoodoo's D3D9.dll, D3DImm.dll, DDraw.dll and dgVoodoo.conf from
System.


SETTINGS
--------
System\U2Shaders.ini (the game re-reads it about once a second, so changes
show while you play):

  post=1                 post-processing on (0 = off)
  bloom=0.7 0.6          bloom threshold and strength
  grade=1.1 1.08 1.0 0.25   saturation, contrast, exposure, vignette
  colour=1 1 1           colour tint (red green blue)
  sharpen=0.3            sharpening (0 = off)
  lut=lut_u2.bmp         colour grade (lut_neutral.bmp = none)
  smaa=0                 add this line to turn SMAA off
  pcss=1                 contact-hardening shadows (0 = the engine's own blur)
  fullscreen=exclusive   add this line to use the game's real exclusive
                         fullscreen instead of borderless
  postfx=0 0 1 0.76      chromatic aberration, film grain, dither, tone
                         shoulder (e.g. postfx=0 0.5 1 0.76 adds grain)
  shader=cfdd1328 core.hlsl   the Liandri armour dome (delete the line to
                              turn it off)

System\User.ini, section [U2SoftShadows.SSShadowController] (appears after
the first run):

  bEnabled=true          the soft shadows (false = the game's single shadow)
  MaxShadows=3           lights per character (0-4; more costs more)
  PlayerMaxShadows=4     lights for your own character
  ShadowStrength=190     darkness at full strength
  bRespectBaked=true     lighter shadows in brightly lit places
  NearDistance=900       closer than this, characters get all their shadows;
  MidDistance=2000       up to this, one shadow; farther away, none

To turn the whole pack off, rename System\d3d8.dll (e.g. to d3d8.dll.off)
and remove U2SoftShadows.SSShadowMutator from the Mutator= line.


UNINSTALL
---------
Delete System\d3d8.dll, System\U2Shaders.ini, the System\U2Shaders folder
and System\U2SoftShadows.u, and remove U2SoftShadows.SSShadowMutator from
the Mutator= line in System\User.ini. If you used dgVoodoo before, put its
d3d8.dll back.


SOURCE
------
Everything is open source: https://github.com/indieindie7/codes
(games/unreal2_mods) and the renderer fork at
https://github.com/indieindie7/d3d8to9/tree/pcss-probe


CREDITS AND LICENCES
--------------------
- d3d8to9 by Patrick Mours (crosire), BSD 2-clause: LICENSES\d3d8to9.txt.
- SMAA by Jorge Jimenez, Jose I. Echevarria, Belen Masia, Fernando Navarro
  and Diego Gutierrez, MIT: System\U2Shaders\SMAA-LICENSE.txt.
- Contrast-adaptive sharpening: AMD FidelityFX CAS, MIT (ported).
- Value noise in core.hlsl by Inigo Quilez, MIT (header of core.hlsl).
- PBR Neutral tone curve: Khronos Group, Apache 2.0.
- U2SoftShadows was inspired by SquirrelZero's UT2004 shadow projector; it
  shares no code with it.
Made by indominator, with Claude (Anthropic). Free, non-commercial; share and
modify as you like with credit.
