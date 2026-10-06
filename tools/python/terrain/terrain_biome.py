"""Biome fields (report step 10): temperature by lapse rate, moisture from drainage and the
distance to water, insolation from aspect, tree line from temperature and exposure; from them
a forest density, a scrub density, a biome class map and the material-slot choice per biome.

    import terrain_biome as tb
    b = tb.fields(out, sea_level_temp=16.0, rain=0.6, latitude=45.0)
    b["temperature"] (deg C), b["moisture"] 0..1, b["insolation"] 0..1, b["treeline"] bool,
    b["forest"] 0..1, b["scrub"] 0..1, b["biome"] int8 (BIOMES order), b["slots"] per biome

Rules: temperature = sea_level_temp - 6.5 C per 1000 m (lapse rate) + 2 C on sunny aspects;
moisture = rain x (0.5 + 0.35 x normalised log drainage + 0.35 x nearness to wet cells) - 0.2 x
insolation excess; trees need temperature above 3 C (the alpine tree line), moisture above
0.3, slope under 38 deg and no snow, scree or rock; scrub takes the dry warm ground.
"""
import math

import numpy as np
from scipy import ndimage

BIOMES = ["water", "meadow", "forest", "scrub", "rock", "snow", "desert"]
# which of the painter's mask layers each biome uses (a UE2 terrain layer budget is small)
SLOTS = {
    "meadow": ["grass", "wet", "rock", "scree"], "forest": ["grass", "wet", "rock", "forest"],
    "scrub": ["scrub", "sand", "rock", "scree"], "rock": ["rock", "scree", "snow", "grass"],
    "snow": ["snow", "rock", "scree", "grass"], "desert": ["sand", "rock", "scree", "wet"], "water": ["wet", "sand", "grass", "rock"],
}


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / max(hi - lo, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def fields(out, sea_level_temp=16.0, rain=0.6, latitude=45.0, lapse=6.5):
    h = np.asarray(out["h"], dtype=np.float64)
    mpc = float(out.get("metres_per_cell", 10.0))
    masks = out.get("masks", {})
    n, m = h.shape
    gy, gx = np.gradient(h, mpc)
    slope = np.hypot(gx, gy); deg = np.degrees(np.arctan(slope))
    # insolation: the sun at noon sits toward the equator; a slope facing it gets more
    sun_elev = math.radians(max(10.0, 90.0 - abs(latitude) + 10.0))
    toward = -1.0 if latitude >= 0 else 1.0          # rows grow southward: a north-hemisphere sun is "down" the map
    nx = -gx; ny = -gy; nz = np.ones_like(gx); l = np.sqrt(nx * nx + ny * ny + nz * nz)
    insol = np.clip((ny * toward * math.cos(sun_elev) + nz * math.sin(sun_elev)) / l, 0, 1)
    insol = (insol - insol.min()) / max(insol.max() - insol.min(), 1e-9)
    temperature = sea_level_temp - lapse * (h - h.min()) / 1000.0 + 2.0 * (insol - 0.5)
    # moisture
    flow = np.log1p(np.asarray(out.get("flow", np.ones_like(h)), dtype=np.float64)); flow = flow / max(flow.max(), 1e-9)
    wet = np.asarray(masks.get("wet", smoothstep(flow, 0.7, 0.9)), dtype=np.float64) > 0.5
    near = np.exp(-ndimage.distance_transform_edt(~wet) * mpc / 150.0) if wet.any() else np.zeros_like(h)
    moisture = np.clip(rain * (0.5 + 0.35 * flow + 0.35 * near) - 0.2 * (insol - 0.5), 0, 1)
    snow = np.asarray(masks.get("snow", np.zeros_like(h)), dtype=np.float64)
    rock = np.asarray(masks.get("rock", np.zeros_like(h)), dtype=np.float64)
    scree = np.asarray(masks.get("scree", np.zeros_like(h)), dtype=np.float64)
    treeline = temperature > 3.0
    forest = (smoothstep(temperature, 3.0, 8.0) * smoothstep(moisture, 0.3, 0.6) * (1 - smoothstep(deg, 30, 38))
              * (1 - snow) * (1 - rock) * (1 - 0.7 * scree))
    forest = ndimage.gaussian_filter(forest, 1.0)
    scrub = (smoothstep(temperature, 10.0, 18.0) * (1 - smoothstep(moisture, 0.25, 0.5)) * (1 - smoothstep(deg, 28, 36))
             * (1 - snow) * (1 - rock))
    biome = np.full((n, m), BIOMES.index("meadow"), dtype=np.int8)
    biome[scrub > 0.4] = BIOMES.index("scrub")
    biome[(scrub > 0.4) & (moisture < 0.15) & (temperature > 16)] = BIOMES.index("desert")
    biome[forest > 0.4] = BIOMES.index("forest")
    biome[rock > 0.5] = BIOMES.index("rock")
    biome[snow > 0.5] = BIOMES.index("snow")
    biome[wet] = BIOMES.index("water")
    counts = np.bincount(biome.ravel(), minlength=len(BIOMES)) / biome.size
    return {"temperature": temperature, "moisture": moisture, "insolation": insol, "treeline": treeline,
            "forest": forest, "scrub": scrub, "biome": biome, "fractions": dict(zip(BIOMES, [float(c) for c in counts])),
            "slots": {b: SLOTS[b] for b in BIOMES if counts[BIOMES.index(b)] > 0.02}}


def report(b, log=print):
    f = b["fractions"]
    log("biomes: " + "  ".join("%s %.2f" % (k, v) for k, v in f.items() if v > 0.005))
    log("temperature %.1f..%.1f C, moisture mean %.2f, tree line covers %.0f%% of the map" % (b["temperature"].min(), b["temperature"].max(), b["moisture"].mean(), 100 * b["treeline"].mean()))
