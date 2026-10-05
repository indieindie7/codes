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

Also: the badly wounded leave drops where they go; a body the game removes leaves remains on the
floor; blood lands on the bodies near a hit (the body's skins are swapped for skin x blood combiners).

A port of the Advent Rising mod's gore system (games/advent_rising_mods, AdventMod/Classes/ModGore.uc).
The marks are projectors with procedural textures (tools/make_textures.py, which uses the Advent mod's
generator). State on 2026-10-05:
  seen in game   floor drips and pools (red), wall spray (green), marks on static meshes
  runs, unseen   blood on characters: only bodies that list their skins get it (Izarians, the named
                 crew); mercs, marines and Skaarj use their mesh's own materials, which script cannot
                 read, so they are skipped ("no blood coat" in the log). On the Izarian's dark skin the
                 stains do not show. Needs another method (a mesh-to-skins table from the .gem files,
                 or a projector on the body).
  not tested     bleeding trails (the test's burst hit a cockroach), remains (bodies were not removed
                 within the test's 14 s)
  not ported     wounds on bodies, scorch marks, screen blood, dismemberment

Build: copy Source\U2Gore into the game folder, add EditPackages=U2Gore to [Editor.EditorEngine] in
Unreal2.ini, run "UCC make" from System.
Install: add U2Gore.GoreMutator to the Mutator= line in User.ini's [DefaultPlayer] section
(comma-separated). Uninstall: remove it from that line.

Test: python u2pilot.py scripts/gore_look.txt --background (tools/python/U2Pilot); gore_more.txt for
coats, remains and trails. Dark grass hides red blood (the marks multiply the surface).

Console (any time in a level):
  set GoreManager bBlood False     no new marks
  set GoreManager MaxDecals 120    DecalSize 200 (widest mark, world units), PoolSize 190, SprayReach 260
  set GoreManager bBleedTrail False | bRemains False | bCoats False
  set GoreManager bLog True        every hit and mark in Unreal2.log

old-sketch\ holds an earlier, never compiled draft (kept for reference).
Gotcha found while porting: this engine's Atan takes one number (use a rotator's Yaw for atan2).
