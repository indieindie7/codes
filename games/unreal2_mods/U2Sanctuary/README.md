# U2Sanctuary: the Sanctuary pass (M08A1, M08A2, M08B)

The user, 2026-10-08: "we will next do a pass on all sanctuary maps, with our creative team initially scoring it and then helping redesign". The gore comes from the Advent chat's system (../U2Gore/ADVENT-GORE-HANDOFF.md).

- `tools/mapreview.py <map.t3d>` runs the five co-directors on a built map: writer, director, engineer, level designer, artist. The rules are the Avalon town's (U2Avalon/tools/codirect.py), turned to a level; the docstring lists the checks. It writes `<map>_review.md`, `<map>_review.png` and `<map>_redesign.json` (proposals with world positions: gore vignettes, key lights, cover).
- Inputs:
  - the T3D is an UnrealEd EDIT COPY of all actors (`select_class("Actor", True)` + `copy_selected()`). MAP EXPORT writes nothing for these maps.
  - `<map>_zones.log` is the `hub zones` lines from a U2Pilot run (`tools/python/U2Pilot/scripts/zones_<map>.txt`). It gives the game's own ReachSpecs; islands the graph leaves apart (lifts, doors) are joined by guessed bridges, and the report counts them.
- `review/` holds the first scoring (2026-10-08).
