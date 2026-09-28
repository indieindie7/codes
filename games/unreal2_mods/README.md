# Unreal II: The Awakening mods

Singleplayer add-ons for Unreal II: The Awakening (2003). Each is a mutator
that loads through the `Mutator=` line in `User.ini`'s `[DefaultPlayer]`
section; every key there is added to the map URL, so this works in
singleplayer. Each mod uses only the game's own packages and works with or
without SOverhaul.

| Mod | What it does |
|---|---|
| [U2SoftShadows](U2SoftShadows) | Every character gets up to 3 soft shadows, one per nearby light. Shadows fade in and out as characters move between lights and fade from the feet to the head, and outdoors the sun always casts one. Built on the engine's own ShadowProjector. |
| [U2SkipCutscenes](U2SkipCutscenes) | Press Space to fast-forward cutscenes and conversations. They are sped up, never cut short, so every event still fires. Skipping stops at dialogue choices and never happens mid-fight. |
| [U2Patches](U2Patches) | **For SOverhaul users:** byte patches no mutator can make, each applied or restored on its own. `movement` undoes SOverhaul's movement (speed 1000 back to 263, Shift walks instead of sprinting); `nolean` removes leaning. |
| [U2CombatOnly](U2CombatOnly) | Unreal II as back-to-back combat missions: New Game starts at Sanctuary, and the tutorial, every Atlantis stop and the planet arrival/departure maps are skipped, following the game's own mission order through to the ending. |
| [U2SkipScenes](U2SkipScenes) | The scenes-only version of U2SkipCutscenes: skips letterboxed cutscenes but leaves walk-around conversations alone. Install one or the other. |

Each folder contains:
- the compiled package (`System/*.u`)
- the UnrealScript source
- a README with manual install steps
- optional Install/Uninstall `.bat` files

The mods were built and tested with
[U2Pilot](../../tools/python/U2Pilot), a harness that plays and records the
game from inside. [U2EdBridge](../../tools/C/U2EdBridge) drives UnrealEd from
scripts (map import/export, rebuild, save) without clicking through the editor.
