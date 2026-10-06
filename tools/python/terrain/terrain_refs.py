"""Reference DEM set: real terrain of three landform classes, scored with the same functions as
the generated maps, so presets are tuned by distance to real statistics (report step 4).

Source: the AWS "elevation-tiles-prod" terrain tiles (Mapzen / Nextzen Terrarium PNGs, built
from USGS 3DEP 10 m inside the US, SRTM elsewhere; public bucket, no key). A site is a 2x2
block of zoom-13 tiles: 512 x 512 cells at about 15 m (lat 37) covering 7.5 km, decoded as
height = R * 256 + G + B / 256 - 32768 metres. US sites only, so the data under the tiles is
3DEP (public domain). The tiles stay out of git (refs/ is ignored); refs/stats.json is kept.

    py terrain_refs.py fetch            # downloads the sites below into refs/<class>/<site>.npy (~24 x 1 MB)
    py terrain_refs.py stats            # scores them, writes refs/stats.json and prints per-class ranges
    py terrain_refs.py compare <in.npy|.bmp> <class> [--cell 512 --zstep 0.5 --unit 0.02]

    import terrain_refs as tr
    d = tr.compare(h_metres, metres_per_cell, "alpine")   # EMD of slope and geomorphon histograms vs the class
"""
import io
import json
import math
import os
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import terrain_score as ts   # noqa: E402

REFS = os.path.join(HERE, "refs")
ZOOM = 13
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/%d/%d/%d.png"

# (name, lat, lon): the upper-left tile is the one containing lat/lon; 2x2 tiles from there
SITES = {
    "hills": [
        ("appalachian_plateau_wv", 38.05, -80.95), ("ozarks_ar", 35.95, -93.45), ("black_hills_sd", 44.05, -103.65),
        ("ridge_valley_pa", 40.65, -77.65), ("sierra_foothills_ca", 38.95, -120.65), ("hill_country_tx", 30.45, -99.15),
        ("oregon_coast_range", 44.65, -123.65), ("daniel_boone_ky", 37.55, -83.75),
    ],
    "alpine": [
        ("yosemite_high_ca", 37.80, -119.40), ("san_juans_co", 37.85, -107.75), ("glacier_mt", 48.65, -113.85),
        ("tetons_wy", 43.80, -110.85), ("north_cascades_wa", 48.55, -121.05), ("wind_rivers_wy", 43.15, -109.65),
        ("sawtooth_id", 44.15, -115.05), ("olympics_wa", 47.85, -123.65),
    ],
    "canyon": [
        ("monument_valley_az", 37.00, -110.15), ("canyonlands_ut", 38.35, -109.95), ("grand_staircase_ut", 37.45, -111.95),
        ("capitol_reef_ut", 38.35, -111.25), ("mesa_verde_co", 37.25, -108.55), ("badlands_sd", 43.85, -102.35),
        ("chaco_nm", 36.05, -107.95), ("painted_desert_az", 35.15, -109.85),
    ],
}


def tile_xy(lat, lon, z=ZOOM):
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def metres_per_pixel(lat, z=ZOOM):
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** z)


def fetch_tile(z, x, y):
    from PIL import Image
    data = urllib.request.urlopen(TILE_URL % (z, x, y), timeout=60).read()
    im = np.array(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.float64)
    return im[..., 0] * 256.0 + im[..., 1] + im[..., 2] / 256.0 - 32768.0


def fetch_site(lat, lon, z=ZOOM, tiles=2):
    x0, y0 = tile_xy(lat, lon, z)
    rows = []
    for j in range(tiles):
        rows.append(np.concatenate([fetch_tile(z, x0 + i, y0 + j) for i in range(tiles)], axis=1))
    return np.concatenate(rows, axis=0), metres_per_pixel(lat, z)


def fetch_all(log=print):
    for cls, sites in SITES.items():
        folder = os.path.join(REFS, cls)
        os.makedirs(folder, exist_ok=True)
        for name, lat, lon in sites:
            path = os.path.join(folder, name + ".npy")
            if os.path.exists(path):
                continue
            h, mpp = fetch_site(lat, lon)
            np.save(path, h.astype(np.float32))
            with open(os.path.join(folder, name + ".json"), "w") as f:
                json.dump({"lat": lat, "lon": lon, "zoom": ZOOM, "metres_per_cell": mpp, "source": "AWS elevation-tiles-prod (Mapzen Terrarium, USGS 3DEP)"}, f)
            log("%s/%s: %dx%d, %.1f m/cell, %.0f..%.0f m" % (cls, name, h.shape[0], h.shape[1], mpp, h.min(), h.max()))


def load_site(cls, name):
    h = np.load(os.path.join(REFS, cls, name + ".npy")).astype(np.float64)
    meta = json.load(open(os.path.join(REFS, cls, name + ".json")))
    return h, float(meta["metres_per_cell"])


def site_names(cls):
    folder = os.path.join(REFS, cls)
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".npy"))


def class_stats(cls, log=print):
    """score every site of the class on 256-cell windows (two per site: the four quadrants
    averaged would hide variety; the centre window and the top-left quadrant are used)"""
    entries = []
    for name in site_names(cls):
        h, mpc = load_site(cls, name)
        n = h.shape[0]
        windows = [h[n // 4:n // 4 + 256, n // 4:n // 4 + 256], h[:256, :256]]
        for wi, w in enumerate(windows):
            s = ts.score(w, mpc)
            entries.append({"site": name, "window": wi, "metres_per_cell": mpc, "landform_share": s["landform_share"],
                            "ptrm": s["ptrm"], "psd_slope": s["psd_slope"], "slope_mean": s["slope_deg"]["mean"],
                            "slope_median": s["slope_deg"]["median"], "slope_p90": s["slope_deg"]["p90"],
                            "slope_hist": [float(x) for x in s["slope_deg"]["hist"]],
                            "geomorphon_hist": [float(x) for x in s["geomorphon_hist"]],
                            "horton_rb": s["horton_rb"], "horton_rl": s["horton_rl"], "hypsometric": s["hypsometric"],
                            "drainage_density": s["drainage_density"], "relief_m": s["relief_m"]})
        if log:
            e = entries[-2]
            log("%s/%s: landform %.2f slope median %.1f p90 %.1f Rb %.2f hyps %.2f beta %.2f relief %.0f" % (cls, name, e["landform_share"], e["slope_median"], e["slope_p90"], e["horton_rb"], e["hypsometric"], e["psd_slope"], e["relief_m"]))
    return entries


def build_stats(log=print):
    stats = {}
    for cls in SITES:
        entries = class_stats(cls, log)
        if not entries:
            continue
        agg = {"n": len(entries)}
        for k in ("landform_share", "ptrm", "psd_slope", "slope_mean", "slope_median", "slope_p90", "horton_rb", "horton_rl", "hypsometric", "drainage_density"):
            v = np.array([e[k] for e in entries], dtype=float); v = v[np.isfinite(v)]
            agg[k] = {"mean": float(v.mean()), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90))} if v.size else None
        agg["slope_hist"] = [float(x) for x in np.mean([e["slope_hist"] for e in entries], axis=0)]
        agg["geomorphon_hist"] = [float(x) for x in np.mean([e["geomorphon_hist"] for e in entries], axis=0)]
        agg["metres_per_cell"] = float(np.mean([e["metres_per_cell"] for e in entries]))
        stats[cls] = {"aggregate": agg, "entries": entries}
    with open(os.path.join(REFS, "stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    return stats


def load_stats():
    p = os.path.join(REFS, "stats.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def resample(h, mpc, target_mpc):
    from scipy import ndimage
    f = mpc / target_mpc
    if abs(f - 1) < 0.05:
        return h
    return ndimage.zoom(h, f, order=3)


def compare(h, mpc, cls, stats=None):
    """Distance of a heightmap from the class: the map is resampled to the references' cell
    size first (slope statistics depend on resolution), then EMD of the slope histogram and
    of the geomorphon histogram, and the landform-share / Horton / hypsometric differences."""
    stats = stats or load_stats()
    if not stats or cls not in stats:
        raise RuntimeError("no reference stats for %s: run terrain_refs.py fetch, then stats" % cls)
    agg = stats[cls]["aggregate"]
    hr = resample(np.asarray(h, dtype=np.float64), mpc, agg["metres_per_cell"])
    s = ts.score(hr, agg["metres_per_cell"])
    out = {
        "emd_slope": ts.emd(s["slope_deg"]["hist"], agg["slope_hist"]),
        "emd_geomorphon": ts.emd(s["geomorphon_hist"], agg["geomorphon_hist"]),
        "landform_share": (s["landform_share"], agg["landform_share"]["mean"]),
        "slope_median": (s["slope_deg"]["median"], agg["slope_median"]["mean"]),
        "horton_rb": (s["horton_rb"], agg["horton_rb"]["mean"] if agg["horton_rb"] else float("nan")),
        "hypsometric": (s["hypsometric"], agg["hypsometric"]["mean"]),
        "psd_slope": (s["psd_slope"], agg["psd_slope"]["mean"]),
        "resampled_cells": hr.shape[0],
    }
    return out


def report_compare(d, cls, log=print):
    log("vs %s references (%d cells at the references' spacing): EMD slope %.3f, EMD geomorphon %.3f" % (cls, d["resampled_cells"], d["emd_slope"], d["emd_geomorphon"]))
    for k in ("landform_share", "slope_median", "horton_rb", "hypsometric", "psd_slope"):
        a, b = d[k]
        log("  %-16s map %.2f   real mean %.2f" % (k, a, b))


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    if cmd == "fetch":
        fetch_all()
    elif cmd == "stats":
        st = build_stats()
        for cls, v in st.items():
            a = v["aggregate"]
            print("%s (%d windows, %.1f m/cell): landform %.2f [%.2f..%.2f]  slope median %.1f [%.1f..%.1f]  p90 %.1f  Rb %.2f  hyps %.2f  beta %.2f" % (
                cls, a["n"], a["metres_per_cell"], a["landform_share"]["mean"], a["landform_share"]["p10"], a["landform_share"]["p90"],
                a["slope_median"]["mean"], a["slope_median"]["p10"], a["slope_median"]["p90"], a["slope_p90"]["mean"],
                a["horton_rb"]["mean"] if a["horton_rb"] else float("nan"), a["hypsometric"]["mean"], a["psd_slope"]["mean"]))
    elif cmd == "compare":
        import terrain_tool as tt
        H, raw, off = tt.load(sys.argv[2])
        cell = tt.arg("--cell", 512.0); zstep = tt.arg("--zstep", 0.5); unit = tt.arg("--unit", 0.02)
        metres = (H - 32768.0) * zstep * unit if raw is not None else H
        report_compare(compare(metres, cell * unit if raw is not None else tt.arg("--mpc", 10.24), sys.argv[3]), sys.argv[3])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
