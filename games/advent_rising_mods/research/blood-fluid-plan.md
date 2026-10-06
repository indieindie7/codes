# Blood as a fluid (Advent Rising gore, from the Hydrophobia water reading)

User direction (2026-10-06): use the water system for blood on AI and floors, with parallaxed
gibs as unique high-detail ("Rage megatexture"-style) textures. Steps:

1. DONE (v1): floor pools that spread like a liquid. tools/make_blood_pool.py runs the
   Hydrophobia solver (HLL fluxes, Toro wave speeds, Audusse hydrostatic reconstruction, CFL
   sub-steps) offline on an 80x80 grid with a rough floor, blood poured in at the centre, then
   bakes 12 frames into Textures/blood_pool_fNN.tga + alien_pool_fNN.tga (50% grey = no
   blood, darker = deeper). ModGore hands the frames to the pool decal under a body;
   ModBloodDecal.Grow steps through them while it scales up (the shape spreads, not just the
   size). U2Shaders.ini decal rules give the frames the parallax shader (deep middle sinks).
   Only 9 distinct hashes: the fork hashes the top rows, grey in the early frames.
   Shots: research/img/blood_pool_frames.png (frames 1/4/7/11), blood_pool_ingame.png.
   Tuning knobs: G, DAMP, POUR_RATE/POUR_UNTIL, bed amplitude, T_END.
2. NEXT: a live version. The baked sequence can't react to slopes or to walking through it.
   A real-time 2D sim per pool (32x32 cells) needs a dynamic texture: UE2 has no script-side
   texture writes, so the fork would own the sheet (CPU sim in the d3d layer, UpdateTexture
   each frame, keyed by projector texture hash + position passed through NativeCall). Also
   lets footprints (parked idea) work: a boot stamps velocity into the sheet, and blood
   carried on the sole is a second small decal.
3. Blood on AI (characters): drips in the skin's UV space. Cheapest real route is in the
   fork's character shader (char_pbr.hlsl already runs per character texture): a drip mask
   scrolled down the tangent-space "down" direction from each hit point, fading with time;
   hits arrive through NativeCall (bone + UV). Heavier route: a per-character 2D sim in UV
   space (same solver, gravity = projected world down per texel, from a baked "flow map").
4. Gibs as "super textures": each gib class gets its own large texture (2048 or more, unique
   per piece, not a tiled meat texture) generated offline (make_pbr_maps.py style: colour +
   bump) and drawn through the fork's pbr rule with parallax on the mesh (the fork's
   decal_parallax is for projectors; a mesh parallax variant is needed, which is the pbr
   shader with the bump map read as height). Memory cost is the limit: budget 8 gib kinds x
   4 MB.
