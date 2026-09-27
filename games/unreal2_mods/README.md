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
| [U2MovementFix](U2MovementFix) | **For SOverhaul users:** undoes SOverhaul's movement changes (player speed 1000 back to 263, and Shift walks again instead of sprinting). A small patcher, not a mutator, with apply/restore. |
| [U2SkipScenes](U2SkipScenes) | The scenes-only version of U2SkipCutscenes: skips letterboxed cutscenes but leaves walk-around conversations alone. Install one or the other. |

Each folder contains:
- the compiled package (`System/*.u`)
- the UnrealScript source
- a README with manual install steps
- optional Install/Uninstall `.bat` files

The mods were built and tested with
[U2Pilot](../../tools/python/U2Pilot), a harness that plays and records the
game from inside.
