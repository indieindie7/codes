# HydroWater

A shallow-water sheet solver in the shape of Hydrophobia's, with the upgrade plan's first
milestone on top. Our own code, plain C99, no game data.

- `src/hydrowater.c`, `src/hydrowater.h`: the library. With every option off it is the scheme read
  out of HydroPC.exe (`games/hydrophobia-water-tech.md`): depth, momentum and bed per 20-unit
  cell with a two-cell border, Audusse hydrostatic reconstruction, Toro two-rarefaction wave
  speeds, HLL flux, `g/2 (h^2 - h*^2)` source, reflecting walls, momentum capped at 1000 h,
  `dt = min(remaining, 0.5 dx / max(|u| + c + |v|))`, two-stage midpoint step.
- The options switch on stages of `games/hydrophobia-water-upgrade.md`:
  - **1 displacement**: bodies rasterise the water column they replace into a `b` plane
    (`hw_body_box`, `hw_body_disc`); each frame the change `alpha (b - b_prev)` is taken from the
    cell and given to its neighbours (volume conserved), and `b` counts as bed for the pressure
    terms, so the hole under a body has no spurious gradient and nothing flows back into it.
    The rasterisers return the displaced volume: `rho g` times it is the body's buoyancy, exact
    for the shape and continuous in height (Thürey's per-column force).
  - **2 capped stamp**: `hw_stamp` blends the cell velocity toward the body's with
    `coeff = min(1, exp(-depth/h) c_adapt (depth/h) dt w)` and sweeps fast bodies along their
    path; off, it is the game's weighted overwrite.
  - **3 smooth buoyancy**: `hw_probe` (surface, slope and water velocity at a point) and
    `hw_body_force` (ramped buoyancy, quadratic drag against the moving water, damping while
    submerged) for the body side.
  - **4a face walls**: `wallX`/`wallY` face masks (`hw_wall_segment` rasterises a wall line),
    plus the dry-ledge rule (no flow up onto a dry step).
  - **8 clamps**: velocity capped at `0.5 dx / dt`, velocity scaled by 0.7 within two cells of a
    wet/dry edge, the 1000 h momentum cap dropped.
- `build.ps1`: builds `bin/hydrowater.dll` (64-bit, for the harness) and `bin/hydrowater32.dll`
  (the game's architecture) with Zig as the C compiler (`Documents\Tools\zig`).
- `tests/harness.py`: the milestone tests, baseline against upgraded, PNG frames and a
  `summary.txt` per test in `tests/out/`. Run with the kimodo venv (numpy, Pillow):

```bash
"C:\Users\john\Documents\Tools\kimodo\venv\Scripts\python.exe" tests\harness.py
```

## Results (2026-10-09, dx 20, g 980)

| test | baseline (the game's scheme) | upgraded |
|---|---|---|
| lake at rest on an uneven bed, 200 steps | max velocity 4.5e-5, zero volume drift | same |
| dam break onto dry stairs, 3 s | one front, no negative depth, no film | same, two sub-0.5 film cells |
| crate 60x60 lowered 15 into 30-deep water | nothing happens (velocity-only coupling) | one ring, crest at 172 units/s vs sqrt(g h) 171, volume drift 1e-9 |
| character r 15 wading at 120 units/s | mound +1.6 ahead, trough -1.2 behind (from the hard stamp) | mound +0.7, trough -1.2, V wake, from displacement |
| half-density box dropped into a tub | hard buoyancy: bobs forever (|vy| up to 121 after 1 s) | drag + near-critical damping: settles in 1.25 s at exactly half immersion |

Costs: a 120 x 60 sheet steps in well under a millisecond per frame in this unoptimised scalar
build; the five tests together run in about two seconds.

## Status: handed off (2026-10-25)

Development on this side stops here; the mod is published as is (release `HydroWater-0.1.0`, PR indieindie7/codes#16 merged). Anyone can pick it up. What works in game, tested 2026-10-25 (build 408fc87):

- The game's water runs on HydroWater: wading wake, foam from the field, drenched look, caustics and underwater fog, spray drops, swimmer wake (`swim_depth` 100; 150 never fired, the depth under a swimming Kate reads 115-117).
- Seen in the test videos: V wake and stirred surface behind Kate, faint foam wisps, heavy foam on the big scripted waves. Stroke spray is drawn (log "spray: matrix form A, ... drops drawn") but 1-8 drops at a time, too few and short-lived to see; no white water at the arms yet.
- Open: more and longer-lived stroke drops, arm white water, foam amount on breaking waves, the soft depth fade of spray (some water pixel shaders bind `s_DepthBuffer` at s2/s3, see the sampler log).
- Lesson: one build per in-game look is too slow. The next attempt (a separate project) rebuilds the water in Bevy and scores it against video automatically.

Pick up here: `mod/README.txt` (ini keys), `games/hydrophobia-water-upgrade.md` (every idea with its commit id), `HydroWater.log` lines "spray:", "swim:", "kate:". Build with `build.ps1`, `mod/build.ps1`, `mod/tests/build.ps1` (must print ALL PASSED), `mod/package.ps1`.

## Next

- 2026-10-25: ideas 20 (APIC spray landing), 22 (foam look: `foam_spec`, `foam_blur`, `depth_tint`, `shore_wet`), 23 + 12b part 2 (metaball spray, `spray_blob`), 24 (underwater `caustics`, `under_fog`), 25 (swimmer wake, `swim`, `swim_depth`, `swim_spray`) and the idea-13 sampler log are in one build, offline-tested only. Next: play with the default ini, read `HydroWater.log` for the "spray:" and "swim:" lines, then tune or turn off keys one at a time. The full list is in `games/hydrophobia-water-upgrade.md`, "Ideas not built yet".

- Stage 5 is in as `recon` (minmod-limited reconstruction of eta, u, v at faces; all five
  milestone tests pass with it on, dam front 1120 vs 1300 units at 3 s, still water exact).
  Stage 7 (splash and foam from the field) is the next visible gain; 9 (tile sleeping) and 10 (SSE/AVX2) once a real room is hooked up.
- Hooking into the game: done in `mod/` (a `dinput8.dll` proxy that detours `FUN_00d5c9d0`
  and copies the sheet planes through `hw_sheet` each step; `mod/README.txt` is the Nexus
  readme, `mod/build.ps1` builds, `mod/tests/build.ps1` runs the hook test,
  `mod/package.ps1` zips the release). The stamping (`FUN_00c12880`) and Havok buoyancy are
  the next two hook points (stages 1-3). Details in `games/REVERSE-ENGINEERING.md`.
