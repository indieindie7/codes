U2Avalon - Avalon remade as a real map, laid out from a binder of people and buildings
======================================================================================

The U2AvalonCards mutator only dressed TutA's view. This is the level itself, generated, and since 2026-10-06
it is driven by the binder (binder\): Shenmue-style biographies of the people who live on the island and a
sheet per building saying who uses it, for what, how worn it is, where its doors are. The sheets place and
shape the plant; the people bound it (a building with no users must be marked abandoned, doors must face
where its users arrive, routines may only go to places that exist). tools\binder.py checks all of that.

  binder\citizens\*.md     who lives here (header keys + prose); binder\buildings\*.md the building sheets
  tools\binder.py          parse + check the binder (exit 1 on a broken rule); `dump` for JSON
  tools\build_parts.py     Blender: the parts library; assembles hall/office/dorm/house/pump/jetty/pad from
                           panels, door types, bays, roofs, window strips, stairs, pipes; wear removes panels
                           and lamps -> Models\glb\B_<id>.glb
  tools\glb_to_ase.py      Blender: GLBs (parts buildings + the scripted ones from U2AvalonCards) -> ASE static
                           meshes in world units (scale=50) sharing one 8-stripe palette texture (Pal.tga)
  tools\floorplan.py       floor plans for the houses, offices and small buildings (directors_house, guest_house,
                           plant_office, staff_houses, clinic, checkpoint, tin_bar, company_store, shanties), from
                           real plans (.claude\skills\building-interiors: ResPlan sizes x1.25 for the 108 UU player)
                           and the kit's rules; rooms.py calls it, shells.py builds its walls. Pictures in data\floorplans
  tools\facade.py          facades for the same buildings by a shape grammar (sides -> floors -> bays -> elements;
                           the room behind each bay picks the window, wear boards some up, formal fronts mirrored,
                           canopies, cornices); rooms.py attaches it, shells.py builds it. Elevations in data\facades
  make_avalon.py           terrain tiles in three materials, sea, the tower shell + command room, the quay,
                           the pipeline, and avalon_actors.t3d placing every binder building (instances,
                           dressing: crates, barrels, dropships, pylons, trees), sky, sun, start
  build_avalon.py          UnrealEd through U2EdBridge: `assets` -> StaticMeshes\AvalonSM.usx, `map` -> Maps\Avalon.un2

Coordinates: tower at (0,0); the look is 300 degrees; building positions are (along, across) in that frame.
1 m = 50 units. Sea Z -4967; the command room floor 5200 above it, so the plant (along 12000..17500) sits
about 19 degrees below the window's horizon. The sky room is the same big room brush subtracted again at
Z 20000 (only the first BRUSH LOAD of an UnrealEd session takes effect; a "small" sky cube came out
room-sized, overlapped the room and merged the zones, which left everything unlit).

Rebuild: py make_avalon.py -> copy Models\ase\* and avalon_actors.t3d to <game>\U2Avalon -> py build_avalon.py
assets (when meshes changed) -> py build_avalon.py map -> pilot tools\python\U2Pilot\scripts\avalon_look.txt.
Kill a stale UnrealEd.exe first if a previous build crashed.

Silhouette check (U2AvalonCards\tools\fidelity.py) of the assembled halls against the processing-hall ref
sheet, 2026-10-06: hall_a 0.49, hall_b 0.48, hall_c 0.42, generator_house 0.39 (the scripted hall scored
0.73). The binder's halls are sized by usage, not by the sheet; the ref hall is wider and lower with a big
overhanging roof slab, which the parts library does not have yet (next: an overhang part, bigger roller doors).

Lessons: UnrealEd rejects RLE TGA; Blender writes TGA bottom-up and UnrealEd does not flip it (hence the
palette as column stripes); BRUSH RESET does not clear MainScale; a Brush actor in an imported T3D is not
carved by MAP REBUILD; a sun actor must stand in open air; a player mid-disc sees nothing below 4 degrees.

Next: roads from the routines (worn ground where people walk), the hall roof overhang, dusk lighting with
the plant lit and the tower dark (the one frame), the Authority corner, then the story beats.
