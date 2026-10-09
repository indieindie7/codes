AdventMod 2.1 - shadows, post-processing, gore and in-game options for Advent Rising
====================================================================================

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
      Up close it has grit and pebbles; the crash level's rocks and sky are
      graded toward real desert photos.

  Global illumination and ambient light (Graphics page)
      Light bounced off the surroundings (Off / On / Strong) and screen-space
      ambient occlusion (corners and the feet of walls darken), both in the
      Direct3D layer. Off unless you turn them on.

  Air and surfaces
      Height fog that thickens low down and far away, warm toward the sun;
      smoke, dust and sparks fade where they meet the floor instead of
      cutting through it (soft particles); a sheen on the station's metal
      panels and polished floors; skin gets a softer, warmer shading
      (subsurface scattering) on faces and alien hide.

  Gore (new in 2.1)
      Blood on walls and floors where people are hit; bodies bleed into real
      pools on the floor that spread, run together with the next body's and
      leave boot prints (left and right, in that blood's colour) when anyone
      walks through them (simulated in the Direct3D layer). Some plasma hits
      on walls glow white-hot and cool to soot. Bodies come apart under heavy hits into pieces that
      settle in the blood; stumps, blood-soaked skins, screen blood, rubble
      from explosions and brass from guns. Ragdolls on the mod's own joint
      limits, and new death animations by where the hit landed.
      Everything is adjustable in System\AdventMod.ini ([AdventMod.ModGore]).

  Blood that behaves like a liquid (new)
      Blood runs down walls in rivulets that branch and bead. Wounded bodies
      get streaks that run straight down whatever the pose, then dry dark.
      Parts that come apart stay joined by sticky strings for a moment, sag,
      stretch and snap. Drops fall from wounds, from bodies draped over
      ledges, from wall sprays and from anything on a ceiling, and pour into
      the pool below. Everyone who walks through fresh blood leaves prints
      for ten steps. Blood is wet and shiny for a minute and dries matte and
      brown over the next three; deep pools reflect the room. Kills up close
      put blood on Gideon's hands and gun, and blood spilt near the camera
      lands on the lens as drops that slide off. Bullets dig holes into walls
      and ceilings; clustered hits open a breach.

  Energy blade (new)
      Some Seekers drop an energy blade. Pick it up and it rides on Gideon's
      back; a melee attack swings it (three hand-keyed swings), with its own
      light, hum and sparks. A hit cuts: heads and limbs come off at the
      joint. It has 15 charges.

  Enemies that think (new)
      Enemies have feelings now: fear, anger and pressure from being shot at.
      Suppressed ones duck into cover, frightened ones fall back or panic,
      angry ones charge. Only a few shoot at once (the rest hold their fire
      and move), the first shot after spotting you comes a beat late, and
      squads push and flank along the level's own paths. Seekers raise their
      front arms when angry and pull them in when afraid.

  Hound packs (new)
      Seeker hounds hunt as a pack: one holds the front and feints, the
      others skip about to your sides, and only one leaps at a time. Backed
      against a wall, you get pinned and two come at once. Hounds sometimes
      leap to a wall and off it at you. Hounds snarl when angry, cower when
      afraid, and stand level on slopes.

  Needs (new)
      Creatures have slow drives: hunger, fatigue, curiosity, safety and
      aggression. In a lull a hungry hound feeds on a fallen mate (a starved
      pack attacks sooner and from the front, a fed one stalks longer), tired
      ones rest, curious ones walk toward a noise, frightened ones look for
      cover or a mate.

  Armour (new)
      Seeker soldiers wear steel plates (helmet, chest, shoulders, thighs)
      that dent and are knocked off whole. Every hit on an enemy is tested
      against its body: a hit on armour throws sparks instead of blood
      (damage is unchanged).

  Bodies (new)
      Gideon leans into turns and with changes of speed, vaults waist-high
      cover at a run, slams into a wall when a dodge runs into one, and
      shoulders breakable props out of the way. Seeker infantry have flesh
      that lags and settles with their movement and kicks on a hit (belly,
      chest, throat, arms, thighs); their armour never deforms. Walking
      characters' feet can stand on the floor that is really under them on
      stairs and step edges (foot IK; off by default, see GOOD TO KNOW).

  Fixes
      The game ran its frames at a few hundred a second; the frame rate is now
      capped at your monitor's refresh rate (much less GPU load).
      Gamepad axes stuck off-centre no longer spin the camera on their own.
      Mouse look without the engine's slow-speed damping (raw mouse).
      The lock-on no longer jumps to a gun on the floor in the middle of a
      fight. Gideon runs a quarter faster while no enemy is near.

  In-game options (the launcher's settings, in the game's own menus)
      Options is a hub, one press from each page, from the title menu and the
      pause menu:
      Gameplay      Difficulty, Damage You Deal / Take, the same for bosses,
                    Running Speed (no enemies near), Levitate Objects
      Camera        the game's own camera settings
      Audio         the game's sliders plus Dialogue Volume (the game saves
                    one but never showed the slider)
      Screen        Resolution (the five largest common sizes that fit your
                    screen), Fullscreen Mode (Borderless / Exclusive /
                    Window), VSync, Frame Cap (monitor / 30 / 60 / 120 / 144
                    / none)
      Graphics      Post Effects preset, Soft Shadows (Off / Yours /
                    Everyone's), Global Illumination, Ambient Light,
                    Anti-Aliasing (SMAA), Shadow Darkness, Sharpening,
                    Field of View (60 - 120)
      Quality       Dynamic Lights, Distortion Effects, Widescreen,
                    Trilinear Filtering, Draw Distance, Fog Distance,
                    Minimum Frame Rate
      Accessibility Blood, Colorblind Mode (Protanopia, Deuteranopia,
                    Tritanopia) and Colorblind Correction (strength), Fading
                    HUD, Slow-Mo Weapon Select, Auto Aiming, Toggle Crouch
      Controls      the game's key bindings

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
   Copy the zip's KarmaData folder (Advent.ka, the ragdoll skeletons) next to
   the game's System folder (...\Advent Rising\KarmaData).

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

Start the game as usual. If Options does not open as the hub of pages above,
the configuration lines are not in place.


GOOD TO KNOW
------------
- Settings: System\AdventMod.ini (the mod) and System\U2Shaders.ini (the
  Direct3D layer's look; the Graphics page writes it, and the game picks up
  changes while it runs, so you can also edit it by hand while playing).
  AdventMod.ini only holds what the game has written; a key you add under the
  right section overrides the built-in default.
- Field of View is the third-person camera's value. First person and vehicle
  cameras are widened by the same ratio. Cutscene cameras are left alone.
- The launcher's own FOV switch works by changing your "move forward" key so
  that it resets the view every time you release it. The mod removes that from
  the key when the game starts, so use the in-game slider instead.
- Camera spinning on its own: the game reads a missing or switched-off gamepad
  axis as full deflection. The mod ignores a pad axis until it has been near
  the centre, and again whenever it holds one exact value for 1.5 seconds.
  Off: bPadDriftFix=False under [AdventMod.ModSettings] in AdventMod.ini.
  Raw mouse look off: bRawMouse=False; the exploring speed: ExploreSpeed=1.0
  (same section).
- Borderless Fullscreen and Exclusive Fullscreen exclude each other: turning one on turns
  the other off.
- Less shadow work for a slower PC: Graphics > Soft Shadows "Yours", or
  fewer of them in System\AdventMod.ini:
      [AdventMod.ModShadowManager]
      NpcShadows=20
- Gore switches, all under [AdventMod.ModGore]: bBlood, bGibs, bWounds,
  bBleedTrail, bWallRuns, bBodyStreaks, bGooStrings, bDrips, bFootprints,
  bWallHoles, bBreaches, bCasings, bScreenBlood, bBlastShake, and the budgets
  MaxDecals (80), MaxGibs (60), MaxDrops (24), MaxFootprints (40). Blood on
  Gideon's hands and the lens: [AdventMod.ModPlayerBlood] bHands, bLens.
  Decapitation and limbs: [AdventMod.ModSever] bSever. Death animations:
  [AdventMod.ModReact] bDeathAnims (ragdolls: bDeathRagdoll). The blade:
  [AdventMod.ModMelee] bBlades. The wet look, drying and reflections of blood
  are in U2Shaders.ini (gloss=, glossdry=, glossreflect=, streaks=, strings=,
  hands=, lens=).
- Enemy AI: [AdventMod.ModMinds] bMinds=False gives you the stock AI back;
  bHoundPack, bHoundWallKick and bLeapLinks switch the pack behaviours;
  [AdventMod.ModNeeds] bNeeds switches the drives.
- Armour: [AdventMod.ModArmor] bArmor (the plates), bArmourHits and
  bArmourSparks (the per-hit armour test; ArmourFactor=1.0 means an armour
  hit does the same damage, lower it to make plates matter).
- Bodies: [AdventMod.ModMoves] bLean; [AdventMod.ModAction] bVault, bSlam,
  bBarge; [AdventMod.ModBody] bSeekerArms, bHoundBody, bGroundPitch;
  [AdventMod.ModJiggle] bJiggle (Gain for more or less).
- Foot IK is off by default; to try it add under [AdventMod.ModFeet]:
      bFootIK=True
  It bends the legs inside the engine so each foot stands on the floor under
  it on stairs and step edges (humans only). New: see KNOWN LIMITS.
- Fog, soft particles, terrain detail and sheen are lines in U2Shaders.ini
  (atmos=, soft=, terraindetail=, sheen=); set the first number to 0 to turn
  one off, or delete the line.
- The panel behind the pages can be changed or switched off in
  System\AdventMod.ini:
      [AdventMod.ModPanel]
      bPanel=True
      PanelColor=(R=255,G=255,B=255,A=120)     (A = how solid, 0-255)
- System\AdventNative.log and System\U2Shaders.log are small logs the mod
  writes; useful if something doesn't work. bGoreLog=True under
  [AdventMod.ModSettings] makes the first one log every hit (slow in a long
  fight; leave it off).


KNOWN LIMITS
------------
- Hound wall-kicks are rare: a hound needs a wall within reach at the right
  angle, and fights happen in the middle of rooms.
- The Seeker flesh jiggle's amounts are set by hand, not measured against a
  real body; if it reads as too much, lower Gain under [AdventMod.ModJiggle].
- Foot IK is new: the foot keeps the animation's tilt (it does not tilt to a
  slope), only humans get it, and running on stairs dips the whole body a
  little with each stride. It was not tried in cutscenes or vehicles.
- Hounds never ragdoll (the game crashes when they do); they die and are
  knocked down with hand-keyed animations instead.
- The armour test needs data files for each enemy mesh that the release does
  not carry; without them it falls back to a per-bone table (less precise,
  same sparks).
- The fog's light shafts were never seen in testing (the sun sits too high
  for the third-person camera on the levels tried).
- Exclusive fullscreen, the GOG version and AMD/Intel GPUs were not tested.
- The pack and needs behaviours were measured in automated runs, not tuned
  by eye over a whole chapter; the switches above are there for a reason.


UNINSTALL
---------
Double-click "Uninstall AdventMod.bat": it removes the configuration lines and
the mod's files, puts back a d3d8.dll or U2Shaders.ini you had before, and
leaves everything else as it was. By hand: remove the lines from steps 3-5,
delete AdventMod.u, AdventMod.int, AdventNative.dll, d3d8.dll, U2Shaders.ini,
AdventMod.ini, the logs and the U2Shaders folder from System, delete
KarmaData\Advent.ka, and rename your
old d3d8.dll back if you had one.


HOW IT WORKS
------------
- AdventMod.u is an UnrealScript package. The game takes the class of its menu
  controller from its configuration; the mod's controller opens the mod's
  pages, which extend the game's own. A small mutator runs in every level: it
  gives characters their light-following shadows, runs the gore, the enemy
  minds and the body systems, and keeps the settings applied.
- AdventNative.dll does what script cannot: the shadow fixes inside the
  engine, the borderless window, the frame cap, writing the layer's settings,
  the foot IK and flesh springs inside the engine's pose build, and the
  armour test against the skinned mesh.
- d3d8.dll is a fork of d3d8to9 (the game's Direct3D 8 calls run on Direct3D 9)
  with "U2Shaders" added: the shadow filtering, the post-processing chain, the
  terrain shader, global illumination, the live blood sheets, streaks, strings,
  hands, lens, fog, soft particles and sheen. Its shaders are plain text in
  System\U2Shaders.
- The game shipped without a script compiler. The mod was compiled with
  AdventUCC, a small tool that runs the compiler hidden in the game's
  Editor.dll. Source for everything:
  https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods
  https://github.com/indieindie7/d3d8to9 (branch gi-cascades)
  The Source folder in this zip has the mod's script and C code.


CHANGES
-------
Next release (2026-10), everything since 2.1:
- Enemy minds: feelings, cover, suppression, fall-backs, panic, charges,
  attack turns, a late first shot, pushes and flanks along the level's paths.
- Hound packs: holder, flankers, one leaper at a time, pinning; wall-kicks.
- Needs: hunger, fatigue, curiosity, safety, aggression; hounds feed on
  fallen mates, marines investigate noises.
- Blood as a liquid: wall runs, streaks down bodies, goo strings, falling
  drops, bloody footprints, blood on Gideon's hands and gun, lens drops, wet
  and drying blood, reflecting pools; wall bullet holes and breaches.
- Bodies: leaning, vaults, wall slams, barging props; Seeker arms and hound
  snarls that show feelings; hounds level on slopes; Seeker flesh jiggle;
  foot IK (off by default).
- Armour: steel plates on Seekers that dent and fly off; sparks on armour
  hits.
- Energy blade with hand-keyed swings; death animations by hit zone; hound
  knockdowns and deaths; gib snapshots on the floor.
- Graphics: height fog, soft particles, close-up terrain detail, sheen on
  metal and floors, skin shading with subsurface scattering, ambient
  occlusion, the crash level graded toward desert photos, 16x anisotropic
  filtering, smoother frame pacing.
- Options: the hub (Gameplay, Camera, Audio, Screen, Graphics, Quality,
  Accessibility, Controls), damage and running-speed sliders, Ambient Light
  row, Fullscreen Mode row.
- Fixes: raw mouse look, the lock-on ignoring floor weapons mid-fight, no
  shader recompiles on the indoor/outdoor shadow switch (the 1 s freezes).
2.1 (2026-10-06): gore, ragdolls, destructible armour (first version), GI.
2.0 (2026-10-03): the d3d8 layer (shadows, post-processing, terrain), presets.
1.0 (2026-09-30): the launcher's settings in the game's menus, FOV, fixes.


CREDITS AND LICENCES
--------------------
- GlyphX Games / Majesco - Advent Rising
- Mike Tyndall - Advent Revising, the unofficial patch
- Patrick Mours (crosire) - d3d8to9 (BSD 2-clause, Licenses\d3d8to9-LICENSE.md)
- Jorge Jimenez et al. - SMAA (MIT, Licenses\SMAA-LICENSE.txt)
- AMD - FidelityFX CAS, ported in post_final.hlsl (MIT)
- Khronos Group - PBR Neutral tone mapper's highlight shoulder (Apache-2.0)
- Inigo Quilez - texture repetition (technique 3) and "better fog", in the
  terrain shader and the height fog (CC BY-NC-SA 3.0)
- Lucas Norr - UnityPCSS, the contact-hardening method pcss_proj.hlsl
  follows (MIT)
- Omar Cornut - Dear ImGui, and Sean Barrett - stb_image_write, built into
  the d3d8.dll's debug panel (MIT / public domain)
- The bloom down/up sampling follows Jorge Jimenez's "Next Generation Post
  Processing in Call of Duty" (SIGGRAPH 2014); the ambient occlusion follows
  McGuire, Mara and Luebke's Scalable Ambient Obscurance; the skin blur
  follows Jimenez's Separable Subsurface Scattering; the terrain tiling
  follows Mikkelsen's hex tiling; the global illumination follows Sannikov's
  radiance cascades.
- The death animations were generated with NVIDIA's Kimodo and retargeted;
  the blade swings and hound clips are hand-keyed.
AdventMod itself is free software under the GPL-3.0 and non-commercial:
share it, change it, keep the source open. See Licenses\CREDITS.txt.
