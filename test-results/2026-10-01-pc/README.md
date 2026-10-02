# PC test results, 2026-10-01 (SESSION_NOTES "Waiting on the PC" list)

Run on the PC by the "unreal modding" session with `tools/C/U2Shaders/d3d8-mingw.dll` installed as
`System\d3d8.dll` (the previous dll is in `<game>\Backup-before-cloudtest`). Each folder has the
`U2Shaders.ini` used, `U2Shaders.log` and screenshots. `00-baseline` = no new settings, same script
(`scripts/shader_look.txt`, M08A1, two marines, shooting a wall, then behind view).

| # | Item | Result |
|---|---|---|
| 1 | New d3d8.dll | Installed; game runs, PCSS shadows still on. |
| 2 | charprobe + depth probe | Works. `chars.txt`, log and pilot dumps in `02-char-probe`. Depth: format 77 960x540 no MSAA; INTZ/DF24/DF16 yes, RAWZ no, RESZ no. |
| 3 | Destruct probe | Built and ran (`03-destruct-probe`). Target was a canopy (StaticMeshActor135, CinemaM.Vehicles.CanopyBIGLoRes). Hide + collision off: works. Solid copy: spawned. The probe's check trace hit **nothing** at every stage (so blocking is unconfirmed: the trace probably misses the prop). Karma debris: PHYS_Karma but **dropped 0 units in 4 s**: hangs in the air (see shot3/4). |
| 4 | Floor-fitted shadow fade | Builds; no script errors; no stairs in the test spot, so the visual check is still open. |
| 5 | Bullet-hole parallax (`decal=20224f10`) | Applies, but holes become **bigger, blocky dark squares**, worse than stock (`05-09-decal-surface/zoom_compare.png`, left stock, right shader). |
| 6 | Light re-bake | Not written yet: skipped. |
| 7 | FairFights additions | Built; works: `hurt kick` on every hit taken, `kill beat 0.07s (start health 75, close call False)`. Heavy-hit beat not triggered (test killed outright). Lines in `07-fairfights`. |
| 8 | Post-processing (`post=1 postsplit=1`) | **Broken on real hardware.** First person: the whole screen shows the HUD texture atlas instead of the scene. Behind view: scene black, only particles and character silhouettes. Log: `post: applied before a 2D draw (fvf 0, pre-transformed 0, orthographic 1)`. |
| 9 | Wall parallax (`surface=bd9b21f2`, `surface=832f2d14`) | Shaders ready, levels measured (0.47/0.32 and 0.50/0.35); no "not supported" line, but no visible change in the shots. |
| 10 | charlight=1 | Every character draw setup is **not supported**, drawn as before (identical to baseline). Setups: `st0 op 3 2 0 / st1 op 1`, `5 2 0 / 5`, `5 2 0 / 3`, `2 2 1 / 10`, `5 2 0 / 18`, `4 2 0 / 3`, all `vertex colours as material 0`. |
| 11 | U2Blender round trip (HoverTest) | MAP EXPORT -> Blender 5.2 headless import (456 actors, 0 warnings) -> export (456) -> fresh UnrealEd MAP IMPORT -> MAP REBUILD -> saved `Maps\HoverTest_RT.un2`. Diff: 275 changed lines (brushes rewritten in world space, float noise like -10240.000153, `Texture=Engine.DefaultTexture` added to texture-less polys, `MainScale/PostScale` lines dropped). The saved map is **70 KB vs 705 KB**: HoverTest's terrain/height map and other myLevel content don't survive. Loading it in game hung on the loading screen (not yet known whether that's the map or the usual unfocused-load stall). |
| 12 | lmcapture=1 | Works: `lmcapture: 29 lightmaps, 11605 triangles` on M08A1; capture in `12-lmcapture-log/capture`. |
