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
2. DONE (v1, 2026-10-06): the live version, in the d3d8 layer (fork gi-cascades, source/blood.hpp).
   The mod draws a pool with one of 8 placeholder textures (Textures/blood_live0..7.tga,
   tools/make_blood_live.py writes them and the `bloodlive=HASH` slot lines into U2Shaders.ini);
   the layer swaps in a 64x64 texture it fills from a CPU shallow-water sheet (the Hydrophobia
   scheme: HLL + hydrostatic reconstruction, CFL sub-steps, friction 0.9/s, speed cap 20 h,
   one frame per step). Commands go UnrealScript -> NativeCall("Blood:...") -> AdventNative ->
   the layer's exported U2BloodCommand: `pool K size gx gy` (floor slope along the texture
   axes = the decal axes' Z), `pour K u v rate secs`, `stamp K u v du dv r` (a pawn moving
   through: velocity blend + half the blood under it pushed to the ring), `stop K`. ModGore
   gives each dying human's pool the next slot (bLivePools, LivePour 3 over 2.6 s); the pool
   that loses its slot keeps the baked final frame. ModBloodDecal.Stamps sends pawns within
   the pool every 80 ms. Verified: research/img/blood_live_pool.png (1.5 / 3.5 / 5.5 s).
   GOTCHA found on the way: the game's TGA importer reads rows bottom-up whatever the
   orientation flag says, so generated TGAs must be written bottom-up (descriptor 8) for
   tools/tex_hash.py's hashes to match the layer's (the baked frame rules were wrong before).
   Then (same day): purple pools for Seekers (`pool ... kind`), a `wet K u v` query, and a
   verified walk-through: the player's steps stamp the sheet (one step moved 2.7 volume units
   to its ring) and leave FOOTPRINTS (ModGore.BloodyFeet / WalkPrints: 7 prints every 38 units,
   alternate feet, pointing the way, textures footprint_h0..2 fading; tools/make_blood_marks.py)
   and a hit body's coat DRIPS for 2.5 s (ModBloodCoat.Drip: a Combiner of the coat texture
   and a TexMatrix-panned streak texture drips_h/a, panned down by a 25 Hz timer). Footprints
   and drips are verified by log; the pilot's camera never looked back at them, so the look
   is for the user to judge.
   Open: no sleep/early-out yet (8 x 4096 cells per frame is still well under 0.1 ms).
2b. NEXT for the live version: The baked sequence can't react to slopes or to walking through it.
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
