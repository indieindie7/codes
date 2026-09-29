U2Hover - a drivable hover bike and a generated test map for Unreal II
=====================================================================

Work in progress, source only.

- HoverBike (KVehicle): a Manta-style hover bike. Three repulsor traces and a
  spring keep it floating over terrain and static meshes. Walk into it to
  board, Fire shoots plasma, Alt Fire hops, Jump gets off.
  The bike model comes from the XVehicles project (CC0).
- HoverMutator spawns the bike on HoverTest* maps.
- make_map.py / build_editor.py generate the HoverTest map (heightfield hills,
  river, sky box, scattered rocks and plants, a few Skaarj) and build it in
  UnrealEd through U2EdBridge (tools/C/U2EdBridge).
- Test tools: SquadTest (marines with the crew's faces), ModelLineup (spawns
  rows of models to inspect), FrameProbe (logs frame-time hitches; add
  ?Mutator=U2Hover.FrameProbe to the map URL).

NOT IN THIS REPO: the compiled package, the map, and the art (textures,
meshes, sounds, sky images). Some of it is extracted from Unreal II itself,
so only the code and generator scripts are published. The #exec lines in
HoverBike.uc expect Models\, Textures\ and Sounds\ folders next to Classes\.
