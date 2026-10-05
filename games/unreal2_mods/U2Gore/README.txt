U2Gore - blood that stays (work in progress, source only)
=========================================================

Unreal II's blood is a puff of particles that is gone in a second. U2Gore adds blood that stays:

  - a spray on the wall or floor behind whoever is hit, along the shot (bigger hit, bigger spray);
  - drips on the floor under the hit;
  - a pool that spreads under each body a moment after it falls;
  - a stain on the body where the shot went in (a small projector that paints characters only and
    rides with the body; it does not follow the limbs, but needs to know nothing about the skins);
  - the badly wounded leave drops where they go;
  - a body the game removes leaves remains on the floor;
  - a death close to the player splashes the screen for a few seconds (UIScripts/U2Gore.ui).

Humans and Skaarj bleed red, Izarians and Araknids green, Drakk and machines not at all (taken from
each character's gib set). Only damage types that have a blood effect in the game leave marks (bullets,
shrapnel; not fire, electricity, gas, EMP), but any death leaves a pool. The game's own blood particles
and gibs are untouched. At most 80 marks and 16 body stains at once; the oldest goes first.

A port of the Advent Rising mod's gore system (games/advent_rising_mods, AdventMod/Classes/ModGore.uc).
The marks are projectors with procedural textures (tools/make_textures.py, which uses the Advent mod's
generator); the screen layouts come from tools/make_ui.py.

State on 2026-10-05, all seen in game unless noted: floor drips and pools, wall sprays, marks on static
meshes, body stains (a merc's torso), remains after a body is removed, screen blood (red and green).
Bleeding trails: counted in the log (4 drops under a wounded merc), not looked at.

Not ported, and why:
  - skin x blood combiners (GoreCoat.uc, off: bCoats): only bodies that list their skins can wear one,
    and mercs, marines and Skaarj do not; the body stains replace it;
  - gibs, bullet holes: the game has its own;
  - dismemberment, ragdoll and flinch changes: Advent scales and turns bones from script, which these
    Golem meshes do not allow.

Build: copy Source/U2Gore into the game folder and UIScripts/U2Gore.ui into the game's UIScripts, add
EditPackages=U2Gore to [Editor.EditorEngine] in Unreal2.ini, run "UCC make" from System.
Install: add U2Gore.GoreMutator to the Mutator= line in User.ini's [DefaultPlayer] section
(comma-separated). Uninstall: remove it from that line.

Test (tools/python/U2Pilot): python u2pilot.py scripts/gore_look.txt --background; also gore_body.txt,
gore_more.txt (remains, trails), gore_screen.txt. Dark grass hides red blood (the marks multiply the
surface).

Console (any time in a level; note that "set" SAVES the setting to System/U2Gore.ini):
  set GoreManager bBlood False     no new marks
  set GoreManager bBodyBlood False | bBleedTrail False | bRemains False | bScreenBlood False
  set GoreManager MaxDecals 120    DecalSize 200 (widest mark, world units), PoolSize 190, SprayReach 260
  set GoreManager BodySize 85      widest body stain; ScreenBloodReach 320
  set GoreManager bLog True        every hit and mark in Unreal2.log

old-sketch/ holds an earlier, never compiled draft (kept for reference).
Gotchas found while porting:
  - this engine's Atan takes one number (use a rotator's Yaw for atan2);
  - a Trace without actors goes through static meshes, so marks landed on the level geometry hidden
    under floors and crates: GoreManager.Surface() walks TraceActors instead;
  - in a .ui file an Image section must be listed as a Component of the container that uses it.
