U2Prairie - generated open map for U2Seven's chapter-1 vertical slice
=====================================================================

Work in progress (shelved 2026-09). Python generates a large prairie map for
Unreal II from scratch and builds it through U2EdBridge (UnrealEd driven by
script, tools/C/U2EdBridge):

  python make_prairie.py          terrain meshes + prairie_actors.t3d
  python build_prairie.py assets  -> StaticMeshes/PrairieSM.usx
  python build_prairie.py map     -> Maps/Prairie.un2 (+ paths)

Layout: the crash site in the west (the Atlantis in pieces, Aida at her
console = the mission board), a 2-minute Manta drive along a winding trail
lined with clutter and flora from the stock maps, a creek ford, a ridge with
the first view of the station, the station pad in the east and a tunnel notch
to the ruins. The crash props, Aida's board and the cinematics are spawned by
U2Seven (SevenPrairie, SevenBoard, SevenCinematic).

Open items: ship scale, a black-wedge prop near (2500,7500), station shell,
tunnel, crash cinematic, board flow. Generated files (meshes, .t3d, maps) are
not in the repo; run the scripts.
