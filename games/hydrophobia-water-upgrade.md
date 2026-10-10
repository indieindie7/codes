# Upgrading a Hydrophobia-style water solver: an implementation plan

A design document for the water simulation read out of *Hydrophobia* (see
`hydrophobia-water-tech.md` for what it is), written as if we were the team upgrading it
for a game today. Everything here is built on the research report
`reports/Shallow water with bodies for games.md`, which carries the sources; this document
turns its proposals into data layouts, step-by-step algorithms, parameter values, costs and
tests. Written 2026-10-06.

The order is payoff per effort. Stages 1 to 3 change how the water and the bodies talk to
each other and are where the visible gain is. Stages 4 to 8 make the solver itself more
robust and more faithful to the room. Stages 9 to 12 are performance and appearance.

## 0. The baseline we start from

Per room ("sheet"), a grid of 20-unit cells, two-cell border, double buffered. Per cell:
depth `h`, momentum `hu`, `hv`, bed `B`, derived velocity `u`, `v`, wave speed `c`, a wall
flag. One step:

1. Prepare: clamp momentum to 1000 h, derive `u = hu/h`, `c = sqrt(g h)`, find
   `smax = max(|u| + c + |v|)`; `dt = min(remaining, 0.5 dx / smax)`.
2. Fluxes: for every face, hydrostatic reconstruction `h* = max(0, h + min(B_this - B_other, 0))`,
   Toro two-rarefaction wave speeds, HLL flux on `(h*, h* u, h* v)`, hydrostatic source
   `g/2 (h^2 - h*^2)` per side, wall faces zero the flux and leave `g/2 h^2` pressure.
3. Two passes (midpoint): half step into the scratch buffer, recompute `u`, `c`, full step.

Then, outside the solver: object velocities are stamped into `u`, `v` within a radius
(weight `1 - d^2/r^2`), buoyancy is Havok's, the mesh and spray are built on render jobs.

Units below: `dx = 20`, `g` the sheet's gravity, `dt` the sub-step the CFL rule produced.

## 1. Bodies displace volume (the biggest visible gain)

**Problem.** Stamping only velocity drags water along; it makes no bow wave, no wake, and a
submerged body leaves a hole above itself. Real interaction is displacement.

**Add** one plane per sheet: `b[i][j]`, the length of the water column replaced by bodies
(units of depth), and keep the previous frame's `b_prev`.

**Each step, before the fluxes:**

```
for each body touching the sheet:
    rasterise its collision shape top-down into the cells it covers:
        for each covered cell: b[i][j] += clamp(min(top, eta) - max(bottom, B), 0, h)
          (eta = B + h is the surface; only the part of the body inside the water counts)
for each cell:
    d = alpha * (b[i][j] - b_prev[i][j])              # volume that appeared or vanished this step
    h[i][j]   -= d                                    # (never below 0; clamp and spread the rest)
    h[i±1][j] += d/4;  h[i][j±1] += d/4               # to the four neighbours: volume is conserved
swap b, b_prev
```

`alpha` is the only knob (0.5 to 1.0): it scales wave amplitude, never breaks conservation.
A body entering pushes a ring outward; a body leaving pulls water back in; a body sitting
still does nothing after the first step. Cost: a rasterisation per body (capsules and boxes
cover a handful of cells) and one pass over the sheet.

**Test.** Drop a crate: one ring, radius growing at `sqrt(g h)`; total volume constant to
float precision. Walk a character through a pool: a V wake behind, a mound in front.

## 2. Stamp velocity with a cap and along the path

**Problem.** The current stamp overwrites the cell velocity with the body's. A fast body
skips cells between frames; a slow body in deep water should barely move it.

**Replace** the overwrite with a blend, and sweep fast bodies:

```
n = max(1, floor(|v_horizontal| * dt / dx + 0.5))      # sub-positions along this step's path
for k in 0..n-1:
    pos = pos_prev + (pos - pos_prev) * (k + 1) / n
    for each covered cell:
        depth_below = eta - body_bottom                # how deep the body sits in the column
        coeff = min(1, exp(-depth_below / h) * 0.2 * (depth_below * dt / h) * A_cell / dx^2)
        u += coeff * (v_body.x - u)
        v += coeff * (v_body.z - v)
```

The `min(1, ...)` is what keeps it stable: the water can at most take the body's velocity,
never overshoot it. `0.2` is the adaptation rate (Chentanez's value). Cost: negligible.

## 3. Buoyancy that does not fight the surface

**Problem.** Buoyancy from a hard surface test flips on and off as a body bobs, and a body
in moving water does not ride the current.

**Per body, each physics step** (replacing or feeding Havok's water modifier):

```
for each probe point p of the body (4 to 16 points on the hull, or per covered column):
    eta  = bilinear(surface, p.x, p.z)
    sub  = eta - p.y                                   # how far under the surface
    ramp = clamp(sub / d_t, 0, 1)                      # d_t = 0.25..0.5 cells: no step at the surface
    F_buoy += up * rho * g * V_p * ramp                # V_p = the probe's share of the volume
    v_water = (u, u*deta/dx + v*deta/dz, v) at p       # the water moves with the surface too
    v_rel = p.velocity - v_water
    F_drag += -0.5 * rho * C_D * A_eff * |v_rel| * v_rel
A_sub_ratio = submerged_probes / probes
F_damp = -k_damp * body.velocity * A_sub_ratio          # extra damping only while in the water
```

For furniture and debris, the per-column force `F = rho g dx^2 b + rho h b u` (Müller/
Thürey) is enough and reuses the `b` plane from stage 1; triangle prisms only for hulls.
`C_D` 0.5 to 1.0, `A_eff` the body's cross-section scaled by 0.5 to 1.0 to taste.

**Test.** A box dropped in a tub settles without bobbing forever; a crate on a current drifts
with it; a character wading feels drag proportional to speed squared.

## 4. Walls on faces, then porosity for furniture

**Problem.** A per-cell wall flag cannot represent a thin wall between two wet cells, a
diagonal partition, or a room half-filled with furniture. Finer grids are the wrong answer.

**4a. Face flags.** Two bitmasks per sheet, `wallX[i][j]` (face between `(i,j)` and `(i+1,j)`)
and `wallY`. At load, rasterise the room's collision edges with Bresenham into the face
masks; walls thinner than a cell now block exactly. In the flux loop a flagged face has
`F = 0` and both sides keep the `g/2 h^2` pressure term (as the cell flag does today).

Add Chentanez's automatic dry-ledge rule: a face is a wall for this step if one side has
`h <= 1e-4 dx` and that side's bed is above the other side's surface (water cannot climb a
dry step; it can flow down it).

**4b. Porosity.** Per cell a storage fraction `phi` (how much of the cell is not furniture,
clamp `>= 0.05`), per face a conveyance fraction `psi` (how much of the face is open).
Both come from supersampling the room's collision geometry or signed distance field once at
load (16 samples per cell, 8 per face). Then:

```
flux across a face      F *= psi_face
cell update             h  += dt/dx * (sum of fluxes) / phi
momentum source         hu += dt * g/2 * h^2 * (phi_right - phi_left) / dx     (same for hv)
furniture drag          hu -= dt * c_D_b * |v| * hu                            (c_D_b ~ 0.5..2 per unit)
```

Wave speeds are unchanged, so the CFL rule is unchanged. A face with `psi = 0` is a wall;
a cell with `phi = 0.3` holds a third of the water and slows the flow: a table, a bank of
seats. This replaces the "flat sheet" special cases for cluttered rooms.

**Test.** A thin partition with a door: water held back until the door cell's face opens.
A room of chairs floods slower than an empty one of the same footprint, same final level.

## 5. Second order where it shows: the Kurganov–Petrova package

**Problem.** First-order HLL smears waves and, on stairs and shallow films, produces
chattering wet/dry edges and the "racing film" that runs ahead of the real front.

**Change the flux inputs, keep the flux.** For each face, instead of the cell-centre states,
reconstruct left and right states at the face:

```
w = B + h                                              # reconstruct the SURFACE, not the depth
slope_w = minmod(theta*(w_i - w_im1), (w_ip1 - w_im1)/2, theta*(w_ip1 - w_i)),  theta = 1.3
w_face_left  = w_i + slope_w/2 ;  w_face_right = w_ip1 - slope_w_ip1/2
bed clamp:  if w_face < B_face:  raise w_face to B_face and lower the opposite face value
            by the same amount (so the cell's mean is kept)            # KP07's two cases
h_face = w_face - B_face
same minmod reconstruction for hu and hv
velocity:  u = sqrt(2) * h * hu / sqrt(h^4 + max(h^4, eps^4)),  eps = 0.01 * dx = 0.2 units
           then hu := h * u                           # keep momentum consistent with the velocity
dry snap:  if h < 1e-6: h = 0, hu = hv = 0
```

Feed these face states into the existing HLL (the hydrostatic reconstruction still applies
between the two face states). Time stepping: Heun (predict with Euler, average) instead of
the midpoint, or plain Euler if the budget is tight; keep CFL 0.5.

Cost: about twice the flux arithmetic, no new planes (slopes are computed on the fly).
Gain: sharp fronts, no thin-film racing, stable wet/dry edges.

**Test.** Dam break on dry stairs: one front, no film ahead of it, no oscillating edge.
Lake at rest on an uneven bed: zero velocity to float precision after 1000 steps.

## 6. Waterfall faces

**Problem.** Water pouring over a tub rim or a ledge should fall as a sheet, not slide down
the face as a thin layer.

At a face with a bed drop steeper than `3` (`(B_i - B_ip1)/dx > 3`) and the upper bed above
the lower surface (`B_i > eta_ip1`): treat the lower side as reflecting for the solver,
correct the face velocity by `u -= g dt (-h_i - 3)/dx`, and emit the volume that would have
crossed as spray particles seeded between the upper bed height and the lower surface. The
particles are the existing spray system's; they deposit their volume back into the cell they
land in.

## 7. Splash and foam from the field

Keep `h_prev`. Spawn splash particles in cells where all three hold:

```
|grad eta| > 0.45 * g * dt / dx        # steep
(h - h_prev) / dt > 4                  # rising fast
laplacian(eta) < -4                    # a crest
```

with volume proportional to `|grad eta|` and a deposit constant 1 to 10 when they land.
Body splashes: when a covered column's depth rises faster than `v_thres dt`, spawn with
velocity `0.86 * body velocity + 0.15 * random + 0.4 * up`. Foam: one scalar plane `f`,
added where splashes land and where `|grad eta|` is high, advected by `(u, v)`, and relaxed
each step by `f <- d f + (1 - d)/4 * sum(neighbours)` with `d` about 0.9. The renderer reads
`f` as a texture.

## 8. Safety clamps and a volume audit

Cheap insurance that the explicit scheme never explodes on a bad frame:

- `|u|, |v| <= 0.5 dx / dt` (replaces the fixed 1000 h momentum cap with one that follows dt).
- Integrate no deeper than `h_max = 2 dx / (g dt)` (very deep columns are static anyway).
- Edge overshoot damping at fronts: within `2 dx` of a wet/dry edge scale velocity by `0.7`.
- Every N frames: sum `phi h` over each connected wet region; redistribute the difference
  against the region's known inflow/outflow evenly over its wet cells. The coupling in
  stages 1 to 3 is explicit and does not conserve volume exactly; this keeps rooms honest.

## 9. Tile sleeping and the job layout

Split each sheet into 8x8-cell tiles with two bits each: `wet` and `active`.

```
each step:
    active(t) = wet(t) and (max |u|,|v|,|dh| in t > threshold during the last N steps
                            or a stamp or emitter touched t)
    step the set S = active tiles + their 8 neighbours        # water moves at most 1 cell/step
    if |S| > 75% of tiles: step the whole sheet (the branchy path costs more than it saves);
                           re-probe every 100 steps
    stamps from gameplay threads go into a queue; the step applies them first, into the
    write buffer, so the solver never reads a half-written cell
```

Thresholds: velocity `0.02 dx/s`, depth change `1e-4`, N = 10 steps. A still bath costs
nothing; a character wading costs its tiles. Stay on the CPU: sheets of about 1200 cells are
below the point where a GPU dispatch pays (a 128x128 step is launch-bound at under a
millisecond; the whole CPU step of such a sheet is less).

## 10. SSE to AVX2

Rows padded to a multiple of 8 plus a 2-cell halo; structure-of-arrays planes
(`h, hu, hv, B, b, phi, psiX, psiY, f`); the select-by-mask idioms become `blendv`; no
approximate `rsqrt` in `sqrt(g h)` if lockstep determinism matters; fixed sub-step count per
frame, `/fp:strict`, per-frame checksums. Expected 1.6 to 1.9x over 4-wide on the flux loop.

## 11. Appearance above physics

Render the surface at `dx/4` with a ripple texture advected by `(u, v)`: three texture
coordinate sets reset every 3 s, phased a second apart, blended by a strain weight
`exp(-mu * gamma)` with `mu = 1` so stretched regions fade before they tear. Foam from
stage 7 and the normals from the height field complete the look. This is the "physics at
low resolution, appearance at high resolution" split; it costs the solver nothing.

## 12. Only then: a nested fine window

If the player's immediate surroundings still want finer waves, run one 2 to 4 times finer
window that follows the player: ghost cells interpolated in space and time from the coarse
sheet each fine sub-step, coarse cells under the window corrected by the fine fluxes each
coarse step, the window padded by a few cells of expected movement before re-centring. Do
this last; stages 1 to 11 are where the money is.

## Order, cost and the first measurable milestone

| Stage | What changes | Cost | Visible result |
|---|---|---|---|
| 1 | displaced volume plane | 1 pass + rasterisation | wakes, bow waves, no holes |
| 2 | capped, swept stamp | negligible | fast bodies behave |
| 3 | smooth buoyancy + drag | per body | no bobbing, bodies ride currents |
| 4 | face walls, porosity | 2 bitmasks, 3 planes, load-time sampling | thin walls, furniture |
| 5 | KP reconstruction | ~2x flux arithmetic | sharp fronts, calm wet/dry edges |
| 6 | waterfall faces | per flagged face | pouring sheets |
| 7 | splash, foam | 1 plane + particles | reads as water |
| 8 | clamps, audit | negligible | never explodes |
| 9 | tile sleeping | bookkeeping | idle water is free |
| 10 | AVX2 | rewrite of the loop | 1.6-1.9x |
| 11 | ripple texture | render side | detail without solver cost |
| 12 | fine window | new solver mode | finer waves near the player |

First milestone: stages 1 to 3 in a test room with a tub, a crate and a walking character,
judged by eye and by a volume plot. Everything after that is measurable against the tests
written into each stage.

## Status (2026-10-09)

Stages 1 to 3, 4a and 8 are implemented as our own library, `games/hydrophobia_mods/HydroWater`
(C99, baseline switchable to the game's exact scheme), with the first-milestone tests in its
harness: crate ring at sqrt(g h), wading wake, box settling at Archimedes' depth. One change to
stage 1 found in testing: the displaced column `b` must also count as bed for the pressure terms,
or the hole under a body refills from its neighbours before the ring can leave.

Stage 7 (2026-10-10): library side done (foam, entrained air and spray planes, commit 71cecd1).
Game side implemented in `mod/src/hwmod.c` (`foam = 1`): the foam and air go into the water
mesh's vertex colour, and the water shader is patched at compile time to draw lace foam and
milky aerated water from it (shaders cached in `shaderCacheHW.bin`). Offline tests pass
(mesh writer, a real `ps_3_0` compile of the patched shader). In the game (2026-10-10 run): the cache rename, the compile hook
(1 slot), the mesh hook at 0xbf1448 and "foam shader patched (main ps_3_0)" all logged, and
the game ran on 41 HydroWater sheets; `shaderCacheDX.bin` unchanged. Second run (2026-10-10, direct launch, off-screen): loading
chapter 2 logged "foam: first water mesh coloured (sheet 30 x 15)", so the whole path runs in
the game, with no errors over chapters 1–4. Still to do: look at the foam in a frame (the chapter
starts are dry lift shafts, and without camera control a scripted run couldn't reach visible water).
Main-menu A/B (2026-10-10, foam=1 vs foam=0, three frames each): the backdrop water looks the same
either way. The on/off difference (mean 3.6–4.4 per channel in the water strip) is no bigger than
two frames of the same run (4.2–5.1), and the mean colour matches. So the patched shader leaves
unfoamed water untouched. It shows no foam either: the menu runs on 20+ HydroWater sheets, but its
water mesh never passes the 0xbf1448 builder ("first water mesh coloured" is not logged). The foam
look still needs a level shot.
Level run (2026-10-10, direct launch, off-screen): `chapter 1` from a fresh menu renders normally (Kate on
the lift-shaft ladder), and `look` is verified there. Chapter 1 starts dry, so a foam frame needs a scripted
walk to water or a save near it.
Spray drops are not drawn in the game yet.

Foam on real water (2026-10-10), corrected: the Practice pool runs 80 sheets on HydroWater, but the simulated foam stays at 0 there (the water is calm and water powers do not touch the sheets). With `foam_test = 1` (moving bands at full foam) nothing shows on the pool either, and the mesh hook at 0xbf1448 colours only one 20 x 38 mesh. The lace seen earlier was the game's own shading. Traced further (mesh-hook counters in the log): the pool IS drawn with the patched foam shader (`foam_test = 2` draws bands in the shader from world position and they cover the whole pool), but its vertex colours never carry foam. The rebuild dispatcher FUN_00bf2470 walks the render list at manager(DAT_012f5428)+0x5088 (next at +0x1ac) and queues job_00bf2460 -> FUN_00bf0e20 for entries with job+8 == 0; in the pool only one sheet (20 x 38) is ever rebuilt (one rebuild per step), so the other sheets keep the vertex buffers built at load. Next: give the shader foam without the vertex colour (a world-space foam texture filled from the sheets each frame), then foam sources (stamp hook FUN_00c12880, bodies). Shader ideas to borrow (licence-safe for GPL): Crest (MIT) foam feather + foam-gradient normals, nvjob water shaders v2 (MIT).
