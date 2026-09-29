U2UTWeapons 1.0 - Unreal Tournament's Flak Cannon, Ripper and GES Bio Rifle
==========================================================================
                  for Unreal II: The Awakening

Three classic weapons from Unreal Tournament (1999), with their original
models, textures, animations and sounds, rebuilt to run in Unreal II. Each one
takes the place of an Unreal II weapon and uses that weapon's ammo, so they
fit the campaign without new pickups:

FLAK CANNON - replaces the Grenade Launcher
  Primary: UT's flak burst - eight hot chunks in a spread - using shotgun
           shells.
  Alt:     fires the grenade launcher's own grenades, all six types, using
           grenade ammo. MIDDLE MOUSE cycles the grenade type.

RIPPER - replaces the Assault Rifle
  Primary: the Assault Rifle's bullets.
  Alt:     UT's razor disc - ricochets off walls up to six times, extra damage
           on headshots. Uses 3 rifle rounds per disc.

GES BIO RIFLE - replaces the Dispersion Pistol (your starting weapon)
  Primary: lobs toxic gel that sticks to what it hits and bursts after a few
           seconds, or when something walks into it.
  Alt:     hold to charge a big glob; it splashes into smaller gels on impact.
           Uses the pistol's recharging ammo, so it never runs dry.

The weapons swap in wherever you'd get the originals: pickups, level starts,
saved inventory. The tutorial's special versions are left alone.

Only needs Unreal II. Works with or without SOverhaul, and alongside other
mutator mods (U2CombatOnly, U2SoftShadows, ...).


INSTALL
-------
(If your download includes "Install U2UTWeapons.bat", close the game and
double-click it; it does the steps below for you. Otherwise do them by hand.)

1. Close the game.

2. Copy the two files from this zip into the game folder, keeping the folders:
     System\U2UTFlak.u             -> <game>\System\
     StaticMeshes\U2UTFlakSM.usx   -> <game>\StaticMeshes\
   <game> is e.g. C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening

3. Open <game>\System\User.ini.
   a) In the [DefaultPlayer] section add this line:
          Mutator=U2UTFlak.UTFlakMutator
      If a Mutator= line already exists there, add it to the end of that line
      with a comma instead, for example:
          Mutator=U2SoftShadows.SSShadowMutator,U2UTFlak.UTFlakMutator
   b) In the [Engine.Input] section change
          MiddleMouse=AltFire
      to
          MiddleMouse=NextGrenadeType
      (or bind any other key to NextGrenadeType) - that's the Flak Cannon's
      grenade switch.

4. Start the game. Saves made before installing restore the mods they were
   made with, so start a New Game (or launch fresh) to see the new weapons.


SETTINGS (optional)
-------------------
After the first run, System\User.ini has this section:

[U2UTFlak.UTFlakMutator]
bReplaceGrenadeLauncher=true   ; Flak Cannon instead of the Grenade Launcher
bReplaceAssaultRifle=true      ; Ripper instead of the Assault Rifle
bReplaceDispersion=true        ; GES Bio Rifle instead of the Dispersion Pistol
bGiveOnSpawn=false             ; testing: hand out the Flak Cannon on every spawn


UNINSTALL
---------
Run "Uninstall U2UTWeapons.bat" if you have it, or by hand:
1. Remove U2UTFlak.UTFlakMutator from the Mutator= line in User.ini (and
   delete the [U2UTFlak.UTFlakMutator] section).
2. Set MiddleMouse=AltFire again in [Engine.Input].
3. Delete System\U2UTFlak.u and StaticMeshes\U2UTFlakSM.usx.


HOW IT'S DONE
-------------
Unreal II never draws textures on vertex-animated meshes (the format UT99's
weapons use), so every animation frame of each weapon was converted into a
textured static mesh and the mod plays them back as a flip-book. The weapon
behaviour is written on top of Unreal II's own weapons. UnrealScript source is
in Source\U2UTFlak\Classes.


CREDITS
-------
Weapon models, textures, animations and sounds: Unreal Tournament (1999) by
Epic Games and Digital Extremes. Unreal, Unreal II and Unreal Tournament are
trademarks of Epic Games, Inc. Unreal II: The Awakening by Legend
Entertainment. This is a free, unofficial fan mod.

SOURCE IN THIS REPO
  Only the UnrealScript source and the import-script generator are here. The
  weapons' models, textures and sounds are Unreal Tournament's and are not
  published in this repository; the #exec lines in the classes expect them in
  Models\, Textures\ and Sounds\ next to Classes\. The ready-to-install
  release (U2UTWeapons-1.0) is distributed separately.
