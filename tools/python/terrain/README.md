# terrain: designed landscapes from a sketch, erosion, realism scoring

NumPy + SciPy (Python 3.13, `py` on this PC). Two ways in:

- **form**: a sketch of ridges, valleys, plateaus, peaks and pads becomes a tectonic uplift
  field; stream power from a flat start turns it into a drainage network (Cordonnier 2016,
  Schott 2023), then strata, droplets, thermal slumping, fine detail and flat pads. Presets for
  three looks: `hills`, `alpine` (Decima / Horizon style ranges) and `canyon` (MotorStorm style
  mesa desert).
- **erode**: the older path, erosion of an existing heightmap (TutA G16 export, Avalon tools).

Both write the layer masks a UE2 painter needs, and both are scored by the same realism
metrics. The report behind it: `games/reports/Terrain generation methods for the pipeline.md`.

## Use

```
py tools/python/terrain/terrain_tool.py form  sketches/alpine.json out.npy --preview out.png --masks out_masks
py tools/python/terrain/terrain_tool.py form  sketches/alpine.json out.bmp --template TutA_export.bmp   # G16 for UnrealEd
py tools/python/terrain/terrain_tool.py preview <in.bmp|.npy> out.png [--masks folder]
py tools/python/terrain/terrain_tool.py score  <in.bmp|.npy> [--cell 512 --zstep 0.5 --unit 0.02]
py tools/python/terrain/terrain_tool.py erode  <in.bmp> <out.bmp> [--freeze pads.png] [--steps 200] [--masks folder]
```

From Python:

```python
import sys; sys.path.insert(0, "tools/python/terrain")
import terrain_form as tf_
out = tf_.form("sketches/canyon.json", seed=1)      # or a dict; preset=, size=, steps= override
out["h"]        # metres, (n, n) float32           out["masks"]   grass wet scree rock snow sand (0..1)
out["pads"]     # bool: the flat pads, for `fixed` in later edits   out["score"]  the metrics below
out["formed"]   # the stream-power result before the detail passes (for debugging a sketch)
```

The sketch (coordinates 0..1, x right, y down; see `terrain_sketch.py` for every field):

```json
{"size": 256, "metres_per_cell": 10.24, "relief": 450, "preset": "alpine",
 "outlet": "border", "base": 0.45, "roughness": 0.2, "roughness_kind": "ridged",
 "items": [
   {"type": "ridge",   "points": [[0.03, 0.38], [0.36, 0.46], [0.68, 0.3], [0.98, 0.3]], "width": 0.08, "strength": 1.0},
   {"type": "valley",  "points": [[0.2, 0.99], [0.33, 0.58]], "width": 0.05, "depth": 0.85},
   {"type": "plateau", "polygon": [[0.04, 0.04], [0.42, 0.06], [0.3, 0.42]], "strength": 1.0, "edge": 0.03},
   {"type": "peak",    "at": [0.36, 0.46], "height": 1.0, "radius": 0.025},
   {"type": "pad",     "at": [0.3, 0.88], "radius": 0.03}
 ]}
```

`relief` is the height of the highest point in metres; peak heights are fractions of it and
are enforced by a PID controller on the uplift (Schott) during the run and a final smooth bump blend, so they are exact. `outlet` is where
water leaves (uplift fades to zero there). `params` in the sketch overrides any preset value.

## What happens, in order (`terrain_form.form`)

1. **Rasterise** (`terrain_sketch`): distance fields from the polylines and polygons. Ridges
   raise uplift in a band, valleys multiply it down (the low-uplift corridor becomes the river),
   plateaus set a block and mark it as resistant (erodibility x 0.05, so the table survives),
   basins lower a block, peaks add a bump and a constraint; gradient noise roughens the field
   so nothing is straight.
2. **Form** (`terrain_flow.stream_power`): from a nearly flat start (a little noise, or every
   channel runs along one of the eight grid directions) under that uplift, 400 steps of Braun
   and Willett's implicit stream power with linear hillslope diffusion. The ratio
   diffusion / k sets the valley spacing: k 1.0 carves a channel into every cell, k 0.02 with
   diffusion 0.2 is a blob, 0.05 / 0.08 gives real hillslopes at 256 cells. For n = 1 the
   solver is linear in (height, uplift), so it runs in normalised units and the result is
   scaled so the highest point is `relief`.
3. **Strata** (canyon): shelves at `terrace.step` x relief, before the slumping turns them
   into cliff bands and talus.
4. **Droplets and thermal** (`terrain_erode`, the existing stages): gullies, deposition on the
   floors; slumping under banded hardness with the preset's two talus angles (loose, hard).
   The canyon hardness has the cap at the top (mesas keep their tables).
5. **Detail**: spectral noise at beta 2, 0.2 to 0.3 % of the relief, on steep ground only,
   any pit it makes shallower than a cell filled; then optionally the dictionary amplifier.
6. **Pads, roads, arenas**: pads flat at their mean height with a 4-cell halo re-solved by
   Laplace's equation (`terrain_sketch.harmonic_fill`); roads and arenas from `terrain_play`.
7. **Masks, biomes, score**: `terrain_erode.layer_masks` plus preset rules (meadows on gentle
   ground, snow only on alpine, sand on the canyon floor), the biome fields, `terrain_score.score`
   and the comparison against the reference class.

256 cells take 45 to 60 s (plus a few seconds each for amplification, roads and the comparison); the stream-power stage is about 0.05 s per step (flow routing is
vectorised by hop level in `terrain_flow`, identical results to the old per-cell loops).

## The presets

| | hills | alpine | canyon |
|---|---|---|---|
| k / diffusion / steps | 0.05 / 0.18 / 400 | 0.05 / 0.15 / 400 | 0.08 / 0.02 / 400 |
| hardness | 3 thin bands, weak | 4 bands, medium | 5 thick bands + cap |
| talus loose / hard (deg) | 30 / 55 | 34 / 72 | 31 / 80 |
| droplets (per 128 sq) / thermal | 40k / 40 | 15k / 25 | 25k / 90 |
| extras | | snow | terraces, sand floor |
| default relief | 160 m | 380 m | 280 m |

Examples (`sketches/*.json` -> `examples/*.png`, shaded with a low sun, masks as colour):
`examples/alpine.png`, `examples/canyon.png`, `examples/hills.png`.

## The score (`terrain_score`)

The ten geomorphon fractions (search 3 cells, flat 1 degree) and the landform share
(valley + ridge + hollow + spur + shoulder + footslope), the PTRM regression value (relative
only), the radial spectrum exponent (unreliable below 256 cells; fbm gain 0.5 reads 4, gain
0.707 reads 3, spectral noise at beta 2 reads 1.8 with this estimator), slope statistics,
Horton bifurcation and length ratios (3 to 5 and 1.6 to 2.4), hypsometric integral (0.3 to
0.6 mature hills) and drainage density. `emd(a, b)` compares two histograms against a
reference set.


## Reference DEM set and the comparison (`terrain_refs`)

`py terrain_refs.py fetch` downloads 24 US sites (8 per class: hills, alpine, canyon) from
the public AWS terrain tiles (Mapzen Terrarium PNGs over USGS 3DEP, no key): 512 x 512 cells
at about 15 m each, into `refs/<class>/` (ignored by git); `stats` scores two 256-cell
windows per site and writes `refs/stats.json`. `form()` then reports the distance of the
result from its class: the map is resampled to the references' cell size and the earth
mover's distance of the slope and geomorphon histograms is printed with the landform share,
slope median, Horton Rb, hypsometric integral and spectrum exponent side by side.

What the real tiles say (means over 16 windows per class):

| | hills | alpine | canyon |
|---|---|---|---|
| landform share | 0.41 | 0.31 | 0.43 |
| slope median / p90 (deg) | 11.5 / 24 | 29 / 45 | 8.3 / 23 |
| Horton Rb | 4.8 | 4.6 | 4.6 |
| hypsometric | 0.50 | 0.43 | 0.43 |
| spectrum exponent | 4.3 | 4.4 | 3.8 |

So the "natural 2" for the spectrum does not hold for this estimator (real 15 m DEMs read
3.7 to 4.4), real terrain has a LOWER landform share than our busy formed maps, and a higher
hypsometric integral. The presets were tuned against these: hills EMD slope 2.9 -> 0.86 by
raising the base uplift and diffusion (relief 160 m), alpine 2.5 -> 2.0 (diffusion 0.15,
relief 380 m), canyon floor given relief (base 0.3, roughness 0.35). The remaining gap is
structural: the outlet border pulls every map's edge to zero, which real windows do not have.

## Roads, arenas and playability (`terrain_play`)

Sketch items `road` (points, width, max_grade) and `arena` (at, radius, kind bowl | berm |
pad). Roads: Dijkstra over (cell, heading) states with cost length x (1 + 30 slope^2) +
0.6 x turn, then the profile smoothed with the grade clamped at 18 % and the ground blended
to it with a cosine halo; the corridor joins the frozen pads. Arenas: a bowl with a low rim,
a ring berm, or a flat pad. Metrics in `out["play"]`: route length and grades, the fraction
of the map reachable from the first pad under 30 deg, and the fraction visible from it.
Routes come out as 45-degree grid segments; smoothing the path is a later step.

## Dictionary amplification (`terrain_amplify`)

`--amplify <class>[/<site>]` or `"amplify"` in the sketch: 8 x 8 coarse patches and their
16 x 16 fine residuals are cut from a reference tile resampled to the map's cell size, every
coarse patch of the map picks its two best atoms (orthogonal matching pursuit) and their
residuals are blended in under a Hann window, scaled by the local slope ratio (Guerin 2016).
It adds the 1 to 2 cell band a formed map lacks (high-band power x2 to x5) from real ground
of the same class. Pure NumPy/SciPy, a few seconds at 256 cells.

## Biome fields (`terrain_biome`)

Temperature by lapse rate (6.5 C per km from the sketch's `climate.sea_level_temp`, plus
2 C on sunny aspects), moisture from drainage, nearness to wet cells and insolation,
tree line at 3 C, forest and scrub densities, a biome class map (water, meadow, forest,
scrub, rock, snow, desert) and the four material slots each biome should use. `forest` and
`scrub` join the masks; `--masks` also writes `biome_class.png`, temperature, moisture and
insolation.

## Caveats and next

- Steep ranges: alpine slopes come out around 36 deg median against 29 for the real tiles;
  the rest of the gap is the border fade (hypsometric 0.31 against 0.43).
- A G16 output needs a template export of the same size (the header is copied); the editor
  side of the Avalon pipeline (`uedlib`) takes it from there, and the masks are written at the
  heightmap's size, which is exactly what a UE2 alpha map has to be.
- Not done from the report's plan: Hnaidi gradient/cliff constraints (only Dirichlet fills),
  Genevaux rivers (8), learned detail (9), road path smoothing, the arena macros beyond
  bowl/berm/pad.
- Old demo files (`demo_*.png/npy`) are from the erode path on an fBm base.
