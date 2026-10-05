U2AvalonCards - dresses the outside of the Avalon command tower (TutA) at map load
=================================================================================

A mutator (U2AvalonCards.AvalonCards). Nothing in the map changes; take the mutator out and it's gone.

- A landing pad (Mission_AvalonM.Structuron2.M10_LandingPadNew1a) with the game's own Atlantis dropship
  (Martins.Dropship.AtlantisDropship) on it: real static meshes, spawned as CardMesh.
- Tree clusters: one-picture imposter cards (CardSprite, STY_Alpha) on the hills.
- An oil rig out at sea: an 8-direction imposter card (CardSprite, STY_Masked so the translucent sea
  can't paint over it); it shows the picture baked from the side the player is on.

Every placement is in System\U2AvalonCards.ini (the one here is the tested layout); "set AvalonCards
bRebuild True" rebuilds after "set AvalonCards ..." tweaks. bSurvey=True logs a height grid round the
tower ("Cards: grid" lines) to choose spots. TutA's sea is a surface at Z -4967, not a water volume;
the tower's command room is ~9200 units above it, so things meant for the window must be far out
(the rig is ~24 km away to be above the bottom of the view). Player stands at (-250,1100) facing ~282.

Pictures:
  tools\prep_cards.py   a cut-out picture -> square TGA card (trees; pictures from Sana + rembg)
  tools\bake_cards.py   Blender: a model -> N views round it (rig: Hunyuan img2shape + paint_mesh)
                        water=0.15 cuts the part under the sea off first.

Install: copy Source\U2AvalonCards to <game>\U2AvalonCards, add EditPackages=U2AvalonCards to
Unreal2.ini, ucc make, start TutA with ?Mutator=U2AvalonCards.AvalonCards.
