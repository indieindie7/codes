U2Seven - "The Seven": Unreal II retold as nine voiced combat episodes
======================================================================

A new story arc and level flow for Unreal II: The Awakening. The maps are
untouched; the mod changes the order you play them in and adds a voiced radio
story between and during the fights.

LEVEL FLOW
  New Game starts at Sanctuary. The tutorial, the Atlantis hub and the
  dropship arrival/departure maps are skipped (like U2CombatOnly), and three
  missions are cut so the story stays tight:

    1 Sanctuary  2 Marsh  3 Hell  4 Acheron  5 Janus  6 Na Koja Abad
    7 Drakk hive  8 Avalon  9 Dorian Gray  (+ an epilogue line on the outro)

  Cut: Severnaya, Kalydon and Sulferon - after Acheron you go straight to Janus.

THE STORY
  Seven artifacts, a liaison called Hawkins who speaks for "Command" and never
  has static on his line, and a crew that starts to doubt him. Each episode
  opens like an episode of a show, once you have control: the radio chatter
  from the end of the last episode, Dalton's captain's log, then the cold
  open. A few episodes add a line or a found recording mid-mission.
  89 voiced lines (Piper TTS, with radio / recording effects), with subtitles.

  An intro plays once: dying and reloading the same episode doesn't repeat it.

INSTALL
  1. Close the game.
  2. Copy System\U2Seven.u into <game>\System.
  3. In <game>\System\User.ini, [DefaultPlayer] section, add
     U2Seven.SevenStory to the Mutator= line (with a comma if the line already
     has entries), e.g.
       Mutator=U2SoftShadows.SSShadowMutator,U2Seven.SevenStory
     If U2CombatOnly is installed you can leave it: U2Seven switches it off
     while it runs.
  4. Launch the game and start a New Game (don't load an old save first).

SETTINGS ([U2Seven.SevenStory] in User.ini, written after the first run)
  bSevenFlow=True     the Seven level order and skipping
  bSkipTutorial=True  New Game starts at Sanctuary
  bStory=True         the voiced story
  LastIntroEp=0       the last episode whose intro played (set to 0 to hear
                      them all again)

BUILDING
  story.py            the script: every line, grouped per episode
  build_voices.py     voices it with Piper (voices in Documents\Tools\piper_voices)
                      and writes Classes\SevenScript.uc
  Classes\SevenStory.uc  the mutator: level flow + playback
  Then compile with UCC (EditPackages=U2Seven).

WORK IN PROGRESS (shelved 2026-09)
  SevenSanctuary   Sanctuary redesign: quiet arrival, gore without creatures,
                   a dying survivor, scripted encounters
  SevenCinematic   simple camera-path cinematics
  SevenPrairie     the generated Prairie map (see ../U2Prairie): crash site,
                   the ship in pieces, Aida's console
  SevenBoard / SevenMissions  Aida's mission board: replay missions/dungeons
  SevenProp        static meshes spawned at level start
  Design docs: CONCEPT_ART.md, SANCTUARY_REDESIGN.md, SANCTUARY_REFERENCES.md

NOT IN THIS REPO: the compiled U2Seven.u and the voice WAVs. The voices are
generated locally with Piper TTS: build_voices.py renders every line from
story.py and writes Classes\SevenScript.uc; then compile with ucc make.
