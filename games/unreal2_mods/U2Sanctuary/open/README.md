# Sanctuary Open

The user, 2026-10-08:
- "use those [8 concept images] as key for the redesign; the goal is the whole of Sanctuary in a single map, with more vehicle movement and open terrain"
- "use some real life world locations as geographical references"

The key images are in `Documents\design-refs\sanctuary_concepts` (sheet_artist.jpg). The story is in `../STORY.md`.

- **The real place:** Serra dos Carajás, Pará, Brazil: the N4 iron mine on its plateau in the Amazon.
  - Elevation: Copernicus GLO-30, a 6.6 km window at 6.025–6.095°S, 50.225–50.155°W (`fetch_dem.py`; the user OK'd the download, 4.3 MB read by range requests).
  - Credit: "Copernicus DEM GLO-30, © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA". See `carajas_n4_dem.png`.
- **The layout** (`plan.py`, the site plan as data; `site_plan.png`):
  1. The LZ in the forest lowland.
  2. The jungle haul road up the escarpment.
  3. The ore plant at the plateau's edge (gate camera, hall of the dead, runoff basin, drainage room).
  4. The cleared field on the open plateau (the first Skaarj, in the open).
  5. The optional mine pit, where the real N4 pit is.
  6. The power plant on the NW tableland (Miller, the generator shaft).
  7. The Marines' pad.
  - Drives at the Manta's cruise: 9–38 s per road.
- **Build:** `make_open.py` (terrain tiles from the DEM plus the site plan, jungle, landmarks) → `build_open.py assets` → `build_open.py map` → `Maps\PrairieSanctuary.un2`. "Prairie*" maps get the Manta from U2Hover's mutator.
- **Test:** `tools/python/U2Pilot/scripts/sanctuary_open_drive.txt`.

## Status (phase 1, 2026-10-08)
Built and driven: the bike boards at the LZ and climbs ~1100 UU up the escarpment to the plateau at cruise speed (`drive_test_1.png`).

Next:
1. The jungle: far denser, with the right canopy. JungleM's Bumbershoot stacks read as stalks: survey Flora_M and JungleM trees at scale, or cards.
2. The places' shells: plant, power plant, pad, the pit's drill rig. Use the Mission_08M kit.
3. The creative team's open-map review: vehicle lanes, vehicle arenas, the weenie from the LZ, drive pacing.
4. Key-image cameras: one camera per concept image, compared with pilot shots.
5. The interiors and beats, the enemies.
