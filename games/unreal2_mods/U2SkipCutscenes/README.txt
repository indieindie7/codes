U2SkipCutscenes 1.0 - skippable cutscenes and conversations for Unreal II: The Awakening
=========================================================================================

Press SPACE (or Fire) to fast-forward:
- letterboxed cutscenes, including the intro and the landing scenes
- conversations you're part of, as long as no enemy is targeting you

A "Press SPACE to skip" prompt appears whenever a skip is possible.

Scenes are FAST-FORWARDED, not cut off. Everything a scene or conversation
triggers still happens in order: doors unlock, characters swap in and out,
objectives update. Skipping can't break progression. Sound is muted while
skipping, and your volume is restored afterwards.

One press also skips scenes that follow straight on from the one you skipped
(up to 6 in a row), so chained sequences clear in one go.
Conversations told in several parts (like Aida's welcome back on the
Atlantis) likewise keep skipping part after part.

Skipping stops by itself:
- as soon as a dialogue choice appears, so you always make your own choices
- when an enemy is after you, so a fight is never sped up

Good to know:
- Planet arrival and departure scenes (dropship flights) are skipped with
  ESC - the game handles those keys itself there - and the prompt says so.
- The game's opening intro is an attract loop that runs until you press
  Escape. Space fast-forwards it, but only Escape leaves it (as in the
  original game).
- Saves made BEFORE installing this mod don't include it. Loading a save
  restores the level exactly as it was saved, including which mods were
  running, so the mod starts working at the next level change. Saves made
  with the mod installed have it straight away.

Prefer to only skip cutscenes and never conversations? Use U2SkipScenes
instead (a separate download), or set bSkipConversations=false below.

Only uses the game's own packages. Works with or without SOverhaul and with
U2SoftShadows.


INSTALL
-------
(If your download includes "Install U2SkipCutscenes.bat", close the game and
double-click it; it does the steps below for you. Otherwise do them by hand.)

1. Close the game.

2. Copy the files from this zip into the game folder, e.g.
   C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening
       System\U2SkipCutscenes.u      ->  <game>\System\
       UIScripts\SkipCutscenes.ui    ->  <game>\UIScripts\

3. Open <game>\System\User.ini and find the [DefaultPlayer] section. Add this
   line inside it:

       Mutator=U2SkipCutscenes.SkipCutscenes

   If a Mutator= line already exists there (for example from U2SoftShadows),
   add it to the end of that line with a comma instead:

       Mutator=U2SoftShadows.SSShadowMutator,U2SkipCutscenes.SkipCutscenes

   (Singleplayer ignores ServerActors, but every key in [DefaultPlayer] is
   added to the map URL, so this loads the mod on every map.)

To check that it works, start a New Game and watch for the prompt in the
bottom black bar of the intro. System\Unreal2.log also shows lines starting
with "U2SkipCutscenes:".


SETTINGS (optional)
-------------------
After the first run, System\User.ini has this section, which you can edit:

[U2SkipCutscenes.SkipCutscenes]
SkipSpeed=12.0           ; how many times faster a skipped scene plays
MinSceneTime=0.5         ; presses in the first half-second of a scene are ignored
bMuteWhileSkipping=true  ; mute sound effects/voices while fast-forwarding
bShowPrompt=true         ; show "Press SPACE to skip"
bSkipConversations=true  ; false = only skip cutscenes, not walk-around conversations
(bMutedBySkip / SavedSoundVolume are internal - leave them alone)

The prompt's position and text are in UIScripts\SkipCutscenes.ui.


UNINSTALL
---------
Run "Uninstall U2SkipCutscenes.bat" if you have it, or by hand:
1. Remove U2SkipCutscenes.SkipCutscenes from the Mutator= line in User.ini
   (and delete the [U2SkipCutscenes.SkipCutscenes] section).
2. Delete System\U2SkipCutscenes.u and UIScripts\SkipCutscenes.ui.


HOW IT WORKS
------------
Unreal II keeps cutscenes and dialogue in sync with their audio by running
parts of them on real time, so simply speeding up the game isn't enough. While
you skip, the mod:
- runs game time faster
- moves the scene's playhead forward in small steps
- lets dialogue lines and the gaps between them speed up, using the game's
  own AllowSlomo switch

It also watches for anything that fast-forwarding would make the game miss,
and fires it: timed dialogue actions such as NPC pause/unpause, and scene
triggers such as the tutorial's actor swap.

The source is in Source\U2SkipCutscenes\Classes.
