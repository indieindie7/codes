U2CombatOnly 1.0 - Unreal II: The Awakening as back-to-back combat missions
============================================================================

Unreal II spends a lot of time between its fights: the tutorial, walking
around the Atlantis between every mission, and a dropship cutscene map on the
way into and out of each planet - each one with its own load screen.

This mod skips all of that. New Game drops you straight into the first combat
mission (Sanctuary), and when a mission ends you go directly into the next
one, in the game's own order:

  Sanctuary -> Marsh -> Hell -> Acheron -> Severnaya (Waterfront)
  -> Kalydon (Obolus) -> Sulferon -> Janus -> Na Koja Abad
  -> Drakk hive -> Avalon -> the Dorian Gray -> ending

Skipped: the tutorial (TutA/TutB), the Avalon prologue scene, every Atlantis
stop, and the planet arrival/departure maps (PA_* / PD_*). Multi-part
missions still flow through all their parts, and every mission hands out its
own full loadout at the start, exactly as it does in the normal game (the
game never carries your inventory into a new mission anyway).

Good to know:
- You lose the Atlantis conversations and mission briefings - that's the
  point, but a later line of dialogue may refer to something said there.
- Saves made BEFORE installing this mod don't include it. Loading a save
  restores the mods it was made with, and they carry into New Game too - so
  after installing, launch the game fresh and pick New Game without loading
  a save first.
- If you load onto an Atlantis or cutscene map anyway, the mod moves you on
  to the next mission straight away.

Only uses the game's own packages. Works with or without SOverhaul, and
alongside other mutator mods (U2SoftShadows, U2SkipCutscenes, ...).

Tip, not part of the mod: if you use dgVoodoo2 and loads take close to a
minute, set ForceVerticalSync = false in the [DirectX] section of
System\dgVoodoo.conf. Unreal II's loading runs at the framerate, and forced
VSync made one level transition take 52 seconds instead of about 3.


INSTALL
-------
(If your download includes "Install U2CombatOnly.bat", close the game and
double-click it; it does the steps below for you. Otherwise do them by hand.)

1. Close the game.

2. Copy System\U2CombatOnly.u from this zip into the game's System folder, e.g.
   C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System\

3. Open <game>\System\User.ini and find the [DefaultPlayer] section. Add this
   line inside it:

       Mutator=U2CombatOnly.CombatOnly

   If a Mutator= line already exists there, add it to the end of that line
   with a comma instead, for example:

       Mutator=U2SoftShadows.SSShadowMutator,U2CombatOnly.CombatOnly

4. Launch the game and choose New Game (don't load a save first).


SETTINGS (optional)
-------------------
After the first run, System\User.ini has this section, which you can edit:

[U2CombatOnly.CombatOnly]
bSkipTutorial=true        ; New Game starts at Sanctuary
bSkipIntermissions=true   ; skip Atlantis and the arrival/departure maps


UNINSTALL
---------
Run "Uninstall U2CombatOnly.bat" if you have it, or by hand:
1. Remove U2CombatOnly.CombatOnly from the Mutator= line in User.ini (and
   delete the [U2CombatOnly.CombatOnly] section).
2. Delete System\U2CombatOnly.u.


SOURCE
------
Source\U2CombatOnly\Classes\CombatOnly.uc. The mission order comes from the
game's own Mission Log (UIScripts\U2Menus.ui).
