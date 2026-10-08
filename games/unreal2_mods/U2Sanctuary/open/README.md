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

## Phase 2 (2026-10-08): jungle, playable areas, frame rate
- **Frame rate:** the zone's distance fog end is UE2's far clip. At the LZ: 38000 gives 63 fps, 16000 gives 163, 10000 gives 253. U2 has no per-actor cull distance. The map uses 3500..20000: a humid jungle haze (the key art's look) plus the clip.
  After the pass, with twice the vegetation: LZ 73 fps (1% low 79), touring and driving 120 fps (1% low 82). It was 62/101 before.
- **Jungle:** three layers chosen by an in-game canopy survey (`tools/python/U2Pilot/scripts/sanctuary_open_trees.txt`):
  - Flora_M Tree1_clump1 + Mission_05M Swamp_tree_new_001 (canopy);
  - JungleM Bumbershoot + high-poly ferns (middle);
  - Elephantine / Plant_1 / ferns / grass (floor).
  - Densest within 3500 UU of the roads and places, thin deep inside. Flora_M's Tree_S meshes are bare dead branches floating in the air: not used.
- **Playable areas:** `playable.py` is a fork of the town generator (layout_spine plots + town.py rerolls) for combat arenas. Per place:
  - the Liandri prefab kit (AvalonSM B_<id> buildings, binder footprints);
  - the Manta's lanes kept clear from every entry to the centre;
  - enemy spawn sheds on the far side from the player's first entry, doors to the centre;
  - cover clusters 256-1024 UU out until >= 4 pieces and 30-80 % of the 16 sightlines are broken;
  - a high spot;
  - the best of 24 seeds by the level designer's arena score.
  - Scores: plant 0.94, field 1.00, pit 1.00, power 0.88, pad 0.92, LZ 0.83. See `playable.png` and `playable.json` (spawn doors for the enemy pass).
- Shots: `drive_test_2.png` (the places), `lz_start.png` (the start, off the dropship).

## Status (phase 1, 2026-10-08)
Built and driven: the bike boards at the LZ and climbs ~1100 UU up the escarpment to the plateau at cruise speed (`drive_test_1.png`).

Next:
1. The jungle: far denser, with the right canopy. JungleM's Bumbershoot stacks read as stalks: survey Flora_M and JungleM trees at scale, or cards.
2. The places' shells: plant, power plant, pad, the pit's drill rig. Use the Mission_08M kit.
3. The creative team's open-map review: vehicle lanes, vehicle arenas, the weenie from the LZ, drive pacing.
4. Key-image cameras: one camera per concept image, compared with pilot shots.
5. The interiors and beats, the enemies.

## Dialogue cuts (2026-10-08)

The shipped conversations can be cut up without new recordings:

- **cuts.json** lists the cuts, each with the reason:
  - `end`: the conversation stops after a node;
  - `jump`: skip to another node;
  - `clip`: keep some sentences of a line;
  - `mute`: the node says nothing.
- **make_cuts.py** builds the `clip` lines with `tools/python/VoiceSplice/dlgcut.py`. It cuts the actor's own take at its pauses, writes `<game>\Voice\U2Cut\...ogg`, and lets whisper check what is heard. A clip with a match under 0.8 is left out. The Oggs are derived from game audio and stay local.
- **import_m08.py** writes OpenDirector's `Cuts=` lines.
- **OpenDirector** applies the cuts after loading the dialogue: `NextNodes` for end and jump; `Filename`, `LongText` and `AudioDuration` for clip and mute.
- **Splitting a conversation:** a later beat names a mid node as its topic. The dialogue engine only starts conversations at a tree's topic, so `StartTalk` points the tree's first node at the mid node.
- **Verified in game:** the gate conversation now plays in three parts (gate / after the gate fight / after the yard), and the drainage line is clipped. Subtitles were checked; the pilot runs with `-nosound`, so the audio still needs a listen.
