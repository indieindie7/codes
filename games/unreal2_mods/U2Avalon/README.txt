U2Avalon - Avalon remade as a real map (stage 1: the outside world)
===================================================================

The U2AvalonCards mutator only dressed TutA's view. This is the level itself, generated:

  make_avalon.py        terrain tiles (heightfield, 8x8 ASE meshes), the sea plane, the Authority's tower
                        shell, avalon_actors.t3d (ground, sea, tower, the Liandri plant, sky, sun, start)
  tools\glb_to_ase.py   Blender: the scripted buildings (U2AvalonCards\tools\build_buildings.py GLBs)
                        -> ASE static meshes sharing one 64x64 palette texture (Pal.tga)
  build_avalon.py       UnrealEd through U2EdBridge: assets -> StaticMeshes\AvalonSM.usx, map -> Maps\Avalon.un2

Coordinates are TutA's (sea at Z -4967, command room ~9200 above, player at (-250,1100) looking ~300),
so every U2AvalonCards layout carries over; the plant stands where layout_liandri_blocks.txt put its boxes,
scaled to those box heights. World is +-30720 (engine limit): the dead rig moved in to (26000,-11000).

Run: start map "Avalon" (tools\python\U2Pilot\scripts\avalon_look.txt photographs it).

Next: the real command room (stage 2), terrain texture blending, shore detail, the harbour quay, lights
on the plant at dusk, then the story beats from AVALON_BRIEF.md.

Idea to try later (user, 2026-10-06): import UT2004 Assault maps (T3D export) and run a spatial analysis
of their combat areas: room volumes, chokepoints, sightlines and objective spacing from the brushes and
the PathNode graph. The UT2004 extracts are private: analysis stays local, nothing uploaded.
