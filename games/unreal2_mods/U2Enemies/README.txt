U2Enemies - Unreal II's iconic enemies, played up to their looks
================================================================

A mutator for Unreal II: The Awakening (singleplayer).

- Agile Skaarj: turns on the jump-dodges and leaps the stock AI holds back.
- Skaarj Berserkers: some light Skaarj never fall back or take cover; they
  close in, leap and slash with their wrist blades.
- Izarian dome breaches: a hit to an Izarian's liquid-filled dome does extra
  damage, sprays fluid, suffocates it over time and often makes it panic.
- Feral Izarians: some unarmoured Izarians (and some breached ones) fight like
  Rage's mutants - erratic jumping charges and melee, no cover.

INSTALL
  1. Copy System\U2Enemies.u into <game>\System.
  2. In <game>\System\User.ini, [DefaultPlayer] section, add
     U2Enemies.EnemyMutator to the Mutator= line (comma-separated).

SETTINGS ([U2Enemies.EnemyMutator] in User.ini, written after the first run)
  bAgileSkaarj=True, bIzarianDomes=True, DomeDamageScale=1.5,
  LeakDamagePerSecond=10, LeakSeconds=8, PanicOdds=0.7,
  BerserkerOdds=0.35, BerserkerSpeed=1.25,
  FeralOdds=0.3, BreachFeralOdds=0.5, FeralSpeed=1.4

UNINSTALL
  Remove U2Enemies.EnemyMutator from the Mutator= line.
