"""Blood drying, measured: a time-lapse of prints from a held camera (Advent's pilot: gibahead, then
shotp every few seconds) and what the blood does in them over time, against the curve the d3d8
fork's gloss pass is meant to follow (glossdry= wet seconds, dry seconds, darkening).

    blood_drying.py <prints dir> [--every 4] [--start 2.5] [--dry 10 40 0.4] [--out DIR]

--every: seconds between prints; --start: seconds from the blood appearing to the first print;
--dry: the run's glossdry= values. The blood is found in the first (wettest) print: pixels whose
red clearly leads green and blue (or red and blue lead green: the Seekers' purple), and the same
pixels are followed through the set. Per print, over those pixels:
  L         mean lightness (L*)
  chroma    mean colourfulness (C* in Lab): drying blood goes brown, less saturated
  gloss     lightness of the brightest 5% over the median: the highlights
  shine     share of pixels more than 15 L* over the median (the wet sparkle)
and the expected wetness (1 fresh .. 0 dry). Writes drying.json, drying.png (curves) and
drying_strip.png (the blood region at a few moments).
"""
import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from visual_qa import load, lab, frames_in   # noqa: E402


def blood_mask(img):
    f = img.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    red = (r > 25) & (r > 2.6 * g) & (r > 1.8 * b)
    purple = (r > 35) & (b > 35) & (r > 1.5 * g) & (b > 1.5 * g)
    m = ((red | purple).astype(np.uint8)) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m


def wetness(t, wet, dry):
    if t <= wet:
        return 1.0
    if t >= dry:
        return 0.0
    u = (t - wet) / (dry - wet)
    return 1 - u * u * (3 - 2 * u)


def chart(path, times, series, title):
    W, H, pad = 900, 420, 50
    im = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(im)
    d.text((pad, 12), title, fill=(20, 20, 30))
    x0, x1, y0, y1 = pad, W - 20, H - pad, 40
    d.line((x0, y0, x1, y0), fill=(120, 120, 130))
    d.line((x0, y0, x0, y1), fill=(120, 120, 130))
    tmax = max(times)
    for t in range(0, int(tmax) + 1, 10):
        x = x0 + (x1 - x0) * t / tmax
        d.line((x, y0, x, y0 + 4), fill=(120, 120, 130))
        d.text((x - 6, y0 + 8), "%ds" % t, fill=(80, 80, 90))
    colours = [(176, 18, 94), (31, 122, 77), (40, 90, 200), (154, 91, 0), (90, 90, 100)]
    for k, (name, vals) in enumerate(series.items()):
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1
        pts = [(x0 + (x1 - x0) * t / tmax, y0 - (y0 - y1) * (v - lo) / span) for t, v in zip(times, vals)]
        d.line(pts, fill=colours[k % 5], width=3)
        for p in pts:
            d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=colours[k % 5])
        d.text((x1 - 230, y1 + 4 + 16 * k), "%s  %.2f .. %.2f" % (name, vals[0], vals[-1]), fill=colours[k % 5])
    d.text((pad, H - 18), "each curve scaled to its own range", fill=(110, 110, 120))
    im.save(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prints")
    p.add_argument("--every", type=float, default=4.0)
    p.add_argument("--start", type=float, default=2.5)
    p.add_argument("--dry", type=float, nargs=3, default=[10, 40, 0.4])
    p.add_argument("--out")
    a = p.parse_args()
    out = a.out or a.prints
    files = [f for f in frames_in(a.prints) if not os.path.basename(f).startswith("drying")]
    imgs = [load(f) for f in files]
    mask = blood_mask(imgs[0])
    if (mask > 0).mean() < 0.0005:
        print("no blood found in the first print")
        return
    print("blood: %.2f%% of the frame" % (100 * (mask > 0).mean()))
    rows, times = [], []
    for i, img in enumerate(imgs):
        t = a.start + i * a.every
        L = lab(img)[mask > 0]
        lum = L[:, 0]
        chroma = np.hypot(L[:, 1], L[:, 2])
        med = float(np.median(lum))
        top = float(np.percentile(lum, 95))
        rec = {"t": round(t, 1), "L": round(float(lum.mean()), 2), "chroma": round(float(chroma.mean()), 2),
               "gloss": round(top - med, 2), "shine": round(float((lum > med + 15).mean()), 4),
               "expected_wet": round(wetness(t, a.dry[0], a.dry[1]), 3)}
        rows.append(rec)
        times.append(t)
        print(rec)
    json.dump(rows, open(os.path.join(out, "drying.json"), "w"), indent=1)
    series = {k: [r[k] for r in rows] for k in ("expected_wet", "gloss", "shine", "chroma", "L")}
    chart(os.path.join(out, "drying.png"), times, series,
          "Blood drying (glossdry=%g %g %g): measured on the blood pixels of %d prints" % (a.dry[0], a.dry[1], a.dry[2], len(rows)))
    # the blood region at a few moments
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = max(0, ys.min() - 20), ys.max() + 20, max(0, xs.min() - 20), xs.max() + 20
    picks = sorted(set([0, len(imgs) // 3, 2 * len(imgs) // 3, len(imgs) - 1]))
    tiles = [Image.fromarray(imgs[i][y0:y1, x0:x1]).resize((300, int(300 * (y1 - y0) / max(1, x1 - x0)))) for i in picks]
    strip = Image.new("RGB", (300 * len(tiles), tiles[0].height + 18), (250, 250, 248))
    dd = ImageDraw.Draw(strip)
    for k, (i, tile) in enumerate(zip(picks, tiles)):
        strip.paste(tile, (300 * k, 18))
        dd.text((300 * k + 4, 2), "t = %.0f s" % times[i], fill=(20, 20, 30))
    strip.save(os.path.join(out, "drying_strip.png"))
    print(os.path.join(out, "drying.png"))


if __name__ == "__main__":
    main()
