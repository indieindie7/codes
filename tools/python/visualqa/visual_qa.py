"""Visual QA for game screenshots: design heuristics as numbers, and a contact sheet that flags
the frames worth a look (see games/reports/visual-heuristics-qa.html for the why).

    visual_qa.py score <frames dir> [--out DIR] [--baseline baseline.json] [--masks DIR]
    visual_qa.py baseline <frames dir> --save baseline.json
    visual_qa.py compare <before dir> <after dir> [--out DIR]

Frames are .bmp/.png/.jpg. A character mask (white = character) may sit next to a frame as
<name>_mask.png, or in --masks DIR under the frame's name; with it come figure-ground,
silhouette and attention-on-character checks. Runs on CPU with numpy, scipy, Pillow, OpenCV
contrib (saliency) and NVIDIA FLIP (flip-evaluator) for compare; the venv is
Documents\\Tools\\visualqa.

What each metric is (all on the frame scaled to 640 px wide):
  squint_spread     std of the blurred luminance (0-100 L*): low = everything the same value
  squint_mid        share of the blurred frame in the mid-grey band (L* 35-65): high = muddy
  focus_contrast    L* difference between the most salient spot and the ring around it
  attention_peak    share of the saliency map's mass in its top 5% of pixels: high = one clear
                    place for the eye, low = attention spread everywhere
  thirds_dist       distance from the saliency peak to the nearest thirds crossing (0 on it, 1 far)
  clutter_edges     share of pixels on an edge (Canny)
  clutter_congest   mean local colour variance in Lab (a simple feature-congestion stand-in)
  colourfulness     Hasler-Susstrunk M
  palette           five main colours (k-means in Lab) with their shares
  with a mask:
  fg_contrast_L     L* difference between the character and a ring around it
  fg_contrast_dE    colour difference (Delta E 76) between them
  char_attention    share of the saliency mass on the character, over its share of the area
  sil_solidity      area over convex hull area: low = limbs stand out from the body
  sil_fill          the character's share of the frame
Flags: magenta (missing texture), black_character, muddy (squint_mid high and spread low),
no_focus (attention_peak low), and with a baseline any metric beyond 2 standard deviations.
"""
import argparse
import base64
import glob
import html
import io
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

W = 640
EXTS = (".bmp", ".png", ".jpg", ".jpeg")


def load(path):
    img = np.asarray(Image.open(path).convert("RGB"))
    h, w = img.shape[:2]
    if w != W:
        img = cv2.resize(img, (W, int(round(h * W / w))), interpolation=cv2.INTER_AREA)
    return img


def lab(img):
    """CIE L*a*b* as float (L 0-100)"""
    f = img.astype(np.float32) / 255.0
    return cv2.cvtColor(f, cv2.COLOR_RGB2Lab)


def saliency(img):
    s = cv2.saliency.StaticSaliencySpectralResidual_create()
    ok, m = s.computeSaliency(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 5)
    return m / max(float(m.max()), 1e-6)


def ring(mask, width):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * width + 1, 2 * width + 1))
    return cv2.dilate(mask, k) & ~mask


def score_frame(path, mask_path=None):
    img = load(path)
    h, w = img.shape[:2]
    L = lab(img)
    lum = L[..., 0]
    out = {"frame": os.path.basename(path)}

    # the squint test: detail blurred away, what values are left
    blur = cv2.GaussianBlur(lum, (0, 0), w * 0.015)
    out["squint_spread"] = round(float(blur.std()), 2)
    out["squint_mid"] = round(float(((blur > 35) & (blur < 65)).mean()), 3)

    # where the eye lands
    sal = saliency(img)
    flat = np.sort(sal.ravel())[::-1]
    top = flat[: max(1, len(flat) // 20)].sum()
    out["attention_peak"] = round(float(top / max(flat.sum(), 1e-6)), 3)
    py, px = np.unravel_index(int(np.argmax(sal)), sal.shape)
    thirds = [(w * a, h * b) for a in (1 / 3, 2 / 3) for b in (1 / 3, 2 / 3)]
    d = min(math.hypot(px - tx, py - ty) for tx, ty in thirds)
    out["thirds_dist"] = round(d / (math.hypot(w, h) / 3), 3)
    peak = np.zeros((h, w), np.uint8)
    cv2.circle(peak, (int(px), int(py)), max(6, w // 40), 255, -1)
    pr = ring(peak, max(6, w // 30))
    out["focus_contrast"] = round(abs(float(blur[peak > 0].mean() - blur[pr > 0].mean())), 2)
    out["peak_xy"] = [int(px), int(py)]

    # clutter
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 140)
    out["clutter_edges"] = round(float((edges > 0).mean()), 4)
    var = 0.0
    for c in range(3):
        ch = L[..., c]
        m1 = cv2.blur(ch, (9, 9))
        m2 = cv2.blur(ch * ch, (9, 9))
        var += np.sqrt(np.maximum(m2 - m1 * m1, 0)).mean()
    out["clutter_congest"] = round(float(var / 3), 3)

    # colour
    r, g, b = [img[..., i].astype(np.float32) for i in range(3)]
    rg, yb = r - g, 0.5 * (r + g) - b
    out["colourfulness"] = round(float(math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())), 2)
    px_lab = L.reshape(-1, 3)[:: 7].astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centres = cv2.kmeans(px_lab, 5, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    shares = np.bincount(labels.ravel(), minlength=5) / len(labels)
    pal = []
    for i in np.argsort(-shares):
        c = cv2.cvtColor(centres[i].reshape(1, 1, 3), cv2.COLOR_Lab2RGB).reshape(3)
        pal.append(["#%02x%02x%02x" % tuple(int(max(0, min(1, v)) * 255) for v in c), round(float(shares[i]), 3)])
    out["palette"] = pal

    # glitches: missing textures
    magenta = (r > 200) & (g < 70) & (b > 200)
    out["magenta"] = round(float(magenta.mean()), 4)

    # with a character mask: figure-ground and silhouette
    if mask_path and os.path.exists(mask_path):
        m = np.asarray(Image.open(mask_path).convert("L"))
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        m = (m > 127).astype(np.uint8) * 255
        if m.any():
            rg_ = ring(m, max(4, w // 60))
            a, bkg = L[m > 0], L[rg_ > 0]
            if len(bkg) == 0:
                bkg = L[m == 0]                 # the character fills the frame's edge: the rest of the frame
            out["fg_contrast_L"] = round(abs(float(a[:, 0].mean() - bkg[:, 0].mean())), 2)
            out["fg_contrast_dE"] = round(float(np.linalg.norm(a.mean(0) - bkg.mean(0))), 2)
            area = (m > 0).mean()
            out["sil_fill"] = round(float(area), 4)
            out["char_attention"] = round(float(sal[m > 0].sum() / max(sal.sum(), 1e-6) / max(area, 1e-6)), 2)
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            big = max(cnts, key=cv2.contourArea)
            hull = cv2.convexHull(big)
            out["sil_solidity"] = round(float(cv2.contourArea(big) / max(cv2.contourArea(hull), 1)), 3)
            out["char_L"] = round(float(a[:, 0].mean()), 1)
            out["ring_L"] = round(float(bkg[:, 0].mean()), 1)

    # flags that need no baseline
    flags = []
    if out["magenta"] > 0.002:
        flags.append("magenta")
    if out["squint_mid"] > 0.8 and out["squint_spread"] < 8:
        flags.append("muddy")
    if out["attention_peak"] < 0.12:
        flags.append("no_focus")
    if "char_L" in out and out["char_L"] < 0.35 * max(out["ring_L"], 1):
        flags.append("black_character")
    if "fg_contrast_dE" in out and out["fg_contrast_dE"] < 6:
        flags.append("low_figure_ground")
    out["flags"] = flags
    return out, img, blur, sal


NUMERIC = ["squint_spread", "squint_mid", "focus_contrast", "attention_peak", "thirds_dist", "clutter_edges",
           "clutter_congest", "colourfulness", "fg_contrast_L", "fg_contrast_dE", "char_attention", "sil_solidity"]


# the smallest before/after change worth reporting, per metric (in its own units)
MIN_CHANGE = {"squint_spread": 2, "squint_mid": 0.05, "focus_contrast": 4, "attention_peak": 0.03, "thirds_dist": 0.2,
              "clutter_edges": 0.01, "clutter_congest": 0.5, "colourfulness": 4, "fg_contrast_L": 3, "fg_contrast_dE": 3,
              "char_attention": 0.3, "sil_solidity": 0.05}


def baseline_flags(rec, base):
    for k in NUMERIC:
        if k in rec and k in base and base[k]["std"] > 1e-6:
            z = (rec[k] - base[k]["mean"]) / base[k]["std"]
            if abs(z) > 2:
                rec["flags"].append("%s %+.1fsd" % (k, z))


def frames_in(d):
    return sorted(p for p in glob.glob(os.path.join(d, "*")) if p.lower().endswith(EXTS) and "_mask" not in os.path.basename(p))


def mask_for(frame, masks_dir):
    stem = os.path.splitext(os.path.basename(frame))[0]
    for cand in [os.path.join(os.path.dirname(frame), stem + "_mask" + e) for e in (".png", ".bmp")] + ([os.path.join(masks_dir, stem + ".png"), os.path.join(masks_dir, stem + "_mask.png")] if masks_dir else []):
        if os.path.exists(cand):
            return cand
    return None


def png_b64(arr, width=320):
    im = Image.fromarray(arr)
    im = im.resize((width, int(im.height * width / im.width)))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def views(img, blur, sal):
    q = np.clip(np.round(blur / 12.5) * 12.5, 0, 100)          # the squint view: 9 values (dark games need the finer steps)
    squint = (q / 100.0 * 255).astype(np.uint8)
    squint = np.dstack([squint] * 3)
    heat = cv2.applyColorMap((sal * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)[..., ::-1]
    over = (img * 0.45 + heat * 0.55).astype(np.uint8)
    return squint, over


CSS = """
:root{--bg:#f3f3f6;--card:#fff;--ink:#1b1c24;--muted:#5b5d6e;--rule:#d9dae3;--flag:#b0125e;--flagbg:#f6dbe8}
@media (prefers-color-scheme:dark){:root{--bg:#14151b;--card:#1c1d25;--ink:#e7e7ee;--muted:#a2a4b6;--rule:#33353f;--flag:#ff5ca7;--flagbg:#3a1a2b}}
body{background:var(--bg);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,sans-serif;margin:0;padding:24px 16px}
h1{font-size:24px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:12px;margin:0 0 16px;display:grid;gap:10px}
.imgs{display:flex;flex-wrap:wrap;gap:8px}.imgs figure{margin:0}.imgs img{width:320px;max-width:100%;display:block;border-radius:3px}
figcaption{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.flags span{display:inline-block;background:var(--flagbg);color:var(--flag);border-radius:3px;padding:1px 7px;margin:0 6px 4px 0;font-size:12px}
table{border-collapse:collapse;font:12px Consolas,monospace}td{padding:2px 12px 2px 0}
.pal span{display:inline-block;height:14px;vertical-align:middle;border:1px solid var(--rule)}
"""


def report(out_dir, title, rows):
    rows.sort(key=lambda r: -len(r[0]["flags"]))
    parts = ["<!doctype html><meta charset=utf-8><title>%s</title><style>%s</style>" % (html.escape(title), CSS),
             "<h1>%s</h1><p class=sub>%d frames, sorted by how many checks they fail. Scores are relative: compare frames of the same level, or before and after a change.</p>" % (html.escape(title), len(rows))]
    for rec, imgs in rows:
        figs = "".join("<figure><img src='data:image/png;base64,%s' alt='%s'><figcaption>%s</figcaption></figure>" % (png_b64(a), html.escape(n), html.escape(n)) for n, a in imgs)
        flags = "".join("<span>%s</span>" % html.escape(f) for f in rec["flags"]) or "<span style='background:none;color:var(--muted)'>no flags</span>"
        nums = "".join("<tr><td>%s</td><td>%s</td></tr>" % (k, rec[k]) for k in NUMERIC + ["magenta", "flip_mean"] if k in rec)
        pal = "".join("<span style='background:%s;width:%dpx' title='%s %d%%'></span>" % (c, max(4, int(s * 160)), c, int(s * 100)) for c, s in rec.get("palette", []))
        parts.append("<div class=card><b>%s</b><div class=flags>%s</div><div class=imgs>%s</div><div class=pal>%s</div><table>%s</table></div>" % (html.escape(rec["frame"]), flags, figs, pal, nums))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "report.html")
    open(path, "w", encoding="utf-8").write("".join(parts))
    json.dump([r for r, _ in rows], open(os.path.join(out_dir, "metrics.json"), "w"), indent=1)
    return path


def cmd_score(a):
    base = json.load(open(a.baseline)) if a.baseline else None
    rows = []
    for f in frames_in(a.frames):
        rec, img, blur, sal = score_frame(f, mask_for(f, a.masks))
        if base:
            baseline_flags(rec, base)
        squint, over = views(img, blur, sal)
        rows.append((rec, [("frame", img), ("squint (9 values)", squint), ("where the eye lands", over)]))
        print(rec["frame"], rec["flags"])
    print(report(a.out or os.path.join(a.frames, "visual_qa"), "Visual QA: " + os.path.basename(os.path.abspath(a.frames)), rows))


def cmd_baseline(a):
    recs = [score_frame(f, mask_for(f, a.masks))[0] for f in frames_in(a.frames)]
    base = {}
    for k in NUMERIC:
        v = [r[k] for r in recs if k in r]
        if len(v) >= 3:
            base[k] = {"mean": float(np.mean(v)), "std": float(np.std(v)), "n": len(v)}
    json.dump(base, open(a.save, "w"), indent=1)
    print("baseline of %d frames -> %s" % (len(recs), a.save))


def cmd_compare(a):
    import flip_evaluator as flip
    rows = []
    for fa in frames_in(a.before):
        fb = os.path.join(a.after, os.path.basename(fa))
        if not os.path.exists(fb):
            continue
        ra, ia, _, _ = score_frame(fa)
        rb, ib, blur, sal = score_frame(fb)
        if ia.shape != ib.shape:
            continue
        err, mean, _ = flip.evaluate(ia.astype(np.float32) / 255.0, ib.astype(np.float32) / 255.0, "LDR")
        rb["flip_mean"] = round(float(mean), 4)
        rb["flags"] = ["%s %+g" % (k, round(rb[k] - ra[k], 3)) for k in NUMERIC if k in ra and k in rb and abs(rb[k] - ra[k]) >= MIN_CHANGE[k]]
        errmap = cv2.applyColorMap((np.clip(err, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_MAGMA)[..., ::-1]
        rows.append((rb, [("before", ia), ("after", ib), ("FLIP difference", errmap)]))
        print(rb["frame"], "flip", rb["flip_mean"], rb["flags"])
    print(report(a.out or os.path.join(a.after, "visual_qa_compare"), "Before / after: " + os.path.basename(os.path.abspath(a.after)), rows))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score"); s.add_argument("frames"); s.add_argument("--out"); s.add_argument("--baseline"); s.add_argument("--masks")
    b = sub.add_parser("baseline"); b.add_argument("frames"); b.add_argument("--save", required=True); b.add_argument("--masks")
    c = sub.add_parser("compare"); c.add_argument("before"); c.add_argument("after"); c.add_argument("--out")
    a = p.parse_args()
    {"score": cmd_score, "baseline": cmd_baseline, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
