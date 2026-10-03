# Unreal II: The Awakening mods

Singleplayer add-ons for Unreal II: The Awakening (2003). Each is a mutator
that loads through the `Mutator=` line in `User.ini`'s `[DefaultPlayer]`
section; every key there is added to the map URL, so this works in
singleplayer. Each mod uses only the game's own packages and works with or
without SOverhaul.

| Mod | What it does |
|---|---|
| [U2SoftShadows](U2SoftShadows) | Every character gets soft shadows from up to 3 nearby lamps plus the sun, a soft contact shadow at the feet, and darker shadows under bright lamps. Only characters the camera sees get shadows; in-game options page. Built on the engine's own ShadowProjector. |
| [U2SkipCutscenes](U2SkipCutscenes) | Press Space to fast-forward cutscenes and conversations. They are sped up, never cut short, so every event still fires. Skipping stops at dialogue choices and never happens mid-fight. |
| [U2Patches](U2Patches) | **For SOverhaul users:** byte patches no mutator can make, each applied or restored on its own. `movement` undoes SOverhaul's movement (speed 1000 back to 263, Shift walks instead of sprinting); `nolean` removes leaning. |
| [U2CombatOnly](U2CombatOnly) | Unreal II as back-to-back combat missions: New Game starts at Sanctuary, and the tutorial, every Atlantis stop and the planet arrival/departure maps are skipped, following the game's own mission order through to the ending. |
| [U2SkipScenes](U2SkipScenes) | The scenes-only version of U2SkipCutscenes: skips letterboxed cutscenes but leaves walk-around conversations alone. Install one or the other. |
| [U2Enemies](U2Enemies) | Rule-of-cool enemies: agile Skaarj that jump-dodge, melee Skaarj Berserkers, Izarian domes that breach (extra damage, fluid spray, suffocation, panic) and feral Izarians that charge like Rage's mutants. |
| [U2Seven](U2Seven) | "The Seven": a new story arc and level flow over the untouched maps. Nine combat episodes with Piper-voiced radio lines and subtitles, plus work-in-progress directors: a redesigned Sanctuary (dying survivor, encounters, cinematics) and the Prairie chapter-1 slice with Aida's mission board. Source only; the voices are generated locally. |
| [U2UTWeapons](U2UTWeapons) | Unreal Tournament's Flak Cannon, Ripper and Bio Rifle rebuilt for Unreal II, each replacing a stock weapon. Source only; UT's models, textures and sounds are not in this repo. |
| [U2WeaponTune](U2WeaponTune) | Faster player projectiles, so bolts keep up with the game's fast movement. Enemy shots are unchanged. |
| [U2FairFights](U2FairFights) | Fair Fights & Punch: enemy reaction delay, burst spread, attack tokens and visible tracers; hitstop, view kick and hit ticks for your own shots. |
| [U2TestHub](U2TestHub) | Developer tool: `hub ...` console commands (test lamps, dummies, shadow A/B, teleports) that U2Pilot scripts also use. |
| [U2Prairie](U2Prairie) | Work in progress: a generated open prairie map for U2Seven's chapter-1 slice (crash site, Manta drive, station). Scripts only. |
| [U2Grime](U2Grime) | Work in progress: dust at wall feet, in corners and under things, away from the AI paths, worked out live on any map; walking over it wears it away. Source only. |
| [U2Hover](U2Hover) | Work in progress: a drivable Manta-style hover bike and a generated hills test map built through U2EdBridge. Source only. |

Each folder contains (the source-only ones are marked above):
- the compiled package (`System/*.u`)
- the UnrealScript source
- a README with manual install steps
- optional Install/Uninstall `.bat` files

The mods were built and tested with
[U2Pilot](../../tools/python/U2Pilot), a harness that plays and records the
game from inside. [U2EdBridge](../../tools/C/U2EdBridge) drives UnrealEd from
scripts (map import/export, rebuild, save) without clicking through the editor.
