U2WeaponTune - faster player projectiles
========================================

Unreal II's energy bolts fly at about UT speeds, but the player (especially
with SOverhaul) runs much faster on bigger maps, so enemies sidestep slow
bolts. This scales the speed of projectiles fired by the player only; enemies
sharing a projectile class are left alone.

INSTALL
  1. Copy System\U2WeaponTune.u into <game>\System.
  2. Add U2WeaponTune.WeaponTune to the Mutator= line in User.ini's
     [DefaultPlayer] section.

SETTINGS ([U2WeaponTune.WeaponTune] in User.ini): DispersionScale,
EnergyRifleScale, TakkraScale, SingularityScale, SkaarjGloveScale,
RocketScale, GrenadeScale (speed multipliers), bLogShots.
