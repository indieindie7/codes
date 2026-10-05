U2Gore - blood that stays (work in progress, source only)
=========================================================

Unreal II's blood is a puff of particles that is gone in a second. U2Gore adds marks that stay:

  - a spray on the wall or floor behind whoever is hit, along the shot (bigger hit, bigger spray);
  - drips on the floor under the hit;
  - a pool that spreads under each body a moment after it falls.

Humans and Skaarj bleed red, Izarians and Araknids green, Drakk and machines not at all (taken from
each character's gib set). Only damage types that have a blood effect in the game leave marks (bullets,
shrapnel; not fire, electricity, gas, EMP), but any death leaves a pool. The game's own blood particles
and gibs are untouched. At most 80 marks at once; the oldest goes first.

This is the first slice of a port of the Advent Rising mod's gore system (games/advent_rising_mods,
AdventMod/Classes/ModGore.uc). Not ported yet: wounds on bodies, blood on characters (skin combiner),
bleeding trails, scorch marks, screen blood, remains, dismemberment. The marks are projectors with
procedural textures (tools/make_textures.py, which uses the Advent mod's generator).

Build: copy Source\U2Gore into the game folder, add EditPackages=U2Gore to [Editor.EditorEngine] in
Unreal2.ini, run "UCC make" from System.
Install: add U2Gore.GoreMutator to the Mutator= line in User.ini's [DefaultPlayer] section
(comma-separated). Uninstall: remove it from that line.

Test: python u2pilot.py scripts/gore_test.txt --background (tools/python/U2Pilot). Seen working
2026-10-05: red splat on a metal floor in M08A1; marks logged for Skaarj, mercs and Izarians.
Not checked yet: sprays on walls, the green marks and the pools by eye; dark grass hides red blood.

Console (any time in a level):
  set GoreManager bBlood False     no new marks
  set GoreManager MaxDecals 120    DecalSize 200 (widest mark, world units), PoolSize 190, SprayReach 260
  set GoreManager bLog True        every hit and mark in Unreal2.log

old-sketch\ holds an earlier, never compiled draft (kept for reference).
Gotcha found while porting: this engine's Atan takes one number (use a rotator's Yaw for atan2).
