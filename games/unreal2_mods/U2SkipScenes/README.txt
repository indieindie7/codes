U2SkipScenes 1.0 - skippable cutscenes (scenes only) for Unreal II: The Awakening
===================================================================================

The scenes-only version of U2SkipCutscenes. Press SPACE (or Fire) to
fast-forward letterboxed cutscenes, including the intro, the landing scenes
and any dialogue that plays inside a cutscene. Conversations you can walk
around in (crew talks on the Atlantis, the Commander at the start) are NOT
skipped - they play normally.

Use this OR U2SkipCutscenes (which also skips those walk-around
conversations), not both. The .bat installers swap one for the other.

Scenes are FAST-FORWARDED, not cut off: everything a scene triggers still
happens in order (doors, character swaps, objectives), so skipping can't break
progression. Sound is muted while skipping and restored afterwards. A "Press
SPACE to skip" prompt shows during a skippable scene.

One press also skips scenes that follow straight on from the one you skipped
(up to 6 in a row), so chained sequences clear in one go.

Good to know:
- Planet arrival and departure scenes (dropship flights) are skipped with
  ESC - the game handles those keys itself there - and the prompt says so.
- The game's opening intro is an attract loop that runs until you press
  Escape. Space fast-forwards it, but only Escape leaves it.
- Saves made BEFORE installing this mod don't include it. Loading a save
  restores the level exactly as it was saved, including which mods were
  running, so the mod starts working at the next level change.

Only uses the game's own packages. Works with or without SOverhaul and with
U2SoftShadows.


INSTALL
-------
(If your download includes "Install U2SkipScenes.bat", close the game and
double-click it; it does the steps below for you. Otherwise do them by hand.)

1. Close the game.

2. Copy the files from this zip into the game folder, e.g.
   C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening
       System\U2SkipScenes.u        ->  <game>\System\
       UIScripts\SkipCutscenes.ui   ->  <game>\UIScripts\

3. Open <game>\System\User.ini and find the [DefaultPlayer] section. Add this
   line inside it:

       Mutator=U2SkipScenes.SkipScenes

   If a Mutator= line already exists there (for example from U2SoftShadows),
   add it to the end of that line with a comma instead:

       Mutator=U2SoftShadows.SSShadowMutator,U2SkipScenes.SkipScenes

   If that line contains U2SkipCutscenes.SkipCutscenes, remove it - use one
   version or the other.


SETTINGS (optional)
-------------------
After the first run, System\User.ini has this section, which you can edit:

[U2SkipScenes.SkipScenes]
SkipSpeed=12.0           ; how many times faster a skipped scene plays
MinSceneTime=0.5         ; presses in the first half-second of a scene are ignored
bMuteWhileSkipping=true  ; mute sound effects/voices while fast-forwarding
bShowPrompt=true         ; show "Press SPACE to skip"
bSkipConversations=false ; true = also skip walk-around conversations (like U2SkipCutscenes)
(bMutedBySkip / SavedSoundVolume are internal - leave them alone)


UNINSTALL
---------
Run "Uninstall U2SkipScenes.bat" if you have it, or by hand:
1. Remove U2SkipScenes.SkipScenes from the Mutator= line in User.ini (and
   delete the [U2SkipScenes.SkipScenes] section).
2. Delete System\U2SkipScenes.u, and UIScripts\SkipCutscenes.ui unless
   U2SkipCutscenes is installed (they share it).


SOURCE
------
Source\U2SkipScenes\Classes. It's the same code as U2SkipCutscenes with
bSkipConversations defaulting to false.
