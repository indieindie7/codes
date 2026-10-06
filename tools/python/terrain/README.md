# terrain: erosion and realism scoring for generated heightmaps

The formation model and the fidelity loop from `games/reports/Terrain look for generated
maps.md`, as a small NumPy library (Python 3.13 with numpy; `py` on this PC) that both
Unreal II terrain paths can call: the TutA G16 heightmap edited by the Avalon tools, and the
height function sampled by `make_avalon.py`.

## Use

```python
import sys; sys.path.insert(0, "tools/python/terrain")
import terrain_erode as te, terrain_score as ts

out = te.erode(h_metres, metres_per_cell=10.24, fixed=pads_mask, seed=1)
# out["h"] eroded heights (relief kept), out["flow"], out["deposit"], out["wear"],
# out["debris"], out["slope"], out["hardness"]: the state every layer mask is read from
masks = te.layer_masks(out)              # grass, wet, scree, rock, snow (+ sand with water_level)
ts.report(ts.score(out["h"], 10.24))     # the numbers below, with reference ranges
```

Command line, for the G16 BMP that UnrealEd exports (header kept, pixels replaced):

```
py tools/python/terrain/terrain_tool.py score <in.bmp|.npy> [--cell 512 --zstep 0.5 --unit 0.02]
py tools/python/terrain/terrain_tool.py erode <in.bmp> <out.bmp> [--freeze pads.png] [--steps 200]
      [--droplets 40000] [--thermal 40] [--seed 0] [--masks folder]
```

`--freeze` is a PNG/BMP whose non-black pixels are left untouched (building pads); the
Avalon cut-and-fill can also simply run after the erosion. `--masks` writes the layer masks
and the simulation state as 8-bit PNGs of the heightmap's size, which is exactly what a UE2
alpha map has to be.

## What it does

1. **Stream power with uplift** (Braun and Willett's implicit scheme, m = 0.5, n = 1, priority
   flood for depressions, D8 routing, hillslope diffusion): the valley network. 200 steps.
2. **Droplets** (Lague's port of Beyer: lifetime 30, radius 2, inertia 0.05, capacity 4,
   erode and deposit 0.3, evaporation 0.01, gravity 4), batched 4,000 at a time in NumPy,
   with forced deposition on ground flatter than 2.5 degrees for valley floors. Erosion is
   scaled by (1 - hardness).
3. **Thermal slumping** (Olsen's rule, c = 0.5) under a banded hardness field (thin hard
   strata by height, a hard cap near the top for mesas): angle of repose 32 degrees for loose
   material rising to 70 for hard rock. The moved volume is the scree.
4. The result is stretched back to the input's height range (`keep_relief`), so the erosion
   carves shape without flattening the map a designer sized.

Masks: grass from deposit thickness where slope < 25 degrees; wet from the top 10 % of flow
accumulation; scree from debris at 25 to 40 degrees; rock from wear with slope > 32 degrees
or any slope > 50, plus hard bands; snow above 82 % of relief; sand in a band at water level.

## The score

`score()` returns: the ten geomorphon fractions (search 3 cells, flat 1 degree) and the
landform share (valley + ridge + hollow + spur + shoulder + footslope, what real terrain has
and noise lacks), the PTRM regression value (relative only: the paper's scaling could not be
reproduced from the available text, so compare runs and reference DEMs scored here, not the
paper's 0.76), the radial spectrum exponent (natural about 2), slope statistics, Horton
bifurcation and length ratios of the D8 network (3 to 5 and 1.6 to 2.4), the hypsometric
integral (0.3 to 0.6 for mature hills) and drainage density. `emd(a, b)` compares two
histograms (slopes, geomorphons) against a reference set of DEM tiles.

## First numbers (TutA's island, 128 cells of 10.24 m)

| | before | after (200 steps, 40k droplets, 40 thermal) |
|---|---|---|
| landform share | 0.47 | 0.57 |
| flat fraction | 0.20 | 0.02 |
| slope mean / p90 (deg) | 18.9 / 47.9 | 16.8 / 37.5 |
| Horton Rb / Rl | 4.80 / 1.55 | 4.47 / 1.37 |
| drainage density | 0.033 | 0.047 |

The flow map after erosion is a dendritic network; the hand-painted plateau's small features
are smoothed (diffusion 0.03 over 200 steps plus droplets): lower `sp_diffusion` or the
step count to keep more of the original detail. 13 seconds end to end.

## Caveats and next

- No reference DEM set yet: download 20 to 50 public-domain tiles of the chosen landform
  class (USGS 3DEP or SRTM), resample to the map's grid, score them with the same functions
  and tune by EMD to their distributions (report step 9). Until then the ranges above are the
  published ones.
- The spectrum exponent of smooth generated bases (3 to 4) is far from natural (2); erosion
  moves it only a little. Rougher bases (more octaves, less smoothing) fix that at the source.
- Pure NumPy; 256 cells take about a minute, dominated by the stream-power loop in Python.
