r"""The redesign's architectural drawing set (Q36, 2026-10-08; the user approved the parti and asked for "architectural
plans for the whole redesign"). Sheets with a title block, drawn from a town run's layout + final heightmap + the
approved parti (binder/parti.json):

    py tools/plans.py <run folder> [sun=136] [sunel=9]        -> <run>\plans\A-*.png + plans_set.pdf when Pillow can write it

A-001 Parti            the sentence, the diagram (axis, hero, datum, downwind, gateways, beats), Ching's ordering
A-002 Site analysis    contours + hillshade, steep ground, the pollution plume downwind, the storm wind, the low sun,
                       what the player sees (viewshed), the best and the worst land
A-101 Framework plan   districts as transect zones (who owns what level: tissue / support / infill), the spine, lanes,
                       paths, gateways, the hero, the datum (ore line), the beat route with its emotions
A-102 Figure-ground    the figure-ground and the Nolli plan side by side (from drawings.py)
A-201 Sections         A/B/C at true scale (from drawings.py)
A-301 District codes   a form-based code per district: setbacks, gaps and party walls, wobble, storeys, character,
                       the patterns honoured or inverted - the measured values from this run beside the targets
A-401 Serial vision    stations every 35 m from the dock to the catwalk, eye height: is the tower seen or hidden from
                       each (terrain line of sight), the beats, the peak frame at the end
"""
import json, math, os, struct, subprocess, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

RUN = sys.argv[1]
o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
SUN_AZ, SUN_EL = float(o.get("sun", 136)), float(o.get("sunel", 9))
WIND = (0.83, -0.55)
OUT = os.path.join(RUN, "plans")
os.makedirs(OUT, exist_ok=True)
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, M, SEA_Z = 512.0, 50.0, -4967.0
PARTI = json.load(open(os.path.join(HERE, "binder", "parti.json")))
L = json.load(open(os.path.join(RUN, "isl_layout.json")))
B = L["buildings"]
_, SHEETS = binder.load()
NAME = os.path.basename(os.path.normpath(RUN))


def font(sz, bold=False):
    for f in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", f), sz)
        except OSError:
            continue
    return ImageFont.load_default()


F10, F12, F14, F18, F24, F32 = font(10), font(12), font(14), font(18, True), font(24, True), font(32, True)

# ---- terrain
raw = open(os.path.join(RUN, "isl_ec.bmp"), "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
Hm = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
if h > 0:
    Hm = Hm[::-1]
Z = LOC[2] + (Hm - 32768) * 0.5
N = Z.shape[0]


def ground(x, y):
    fi, fj = (x - LOC[0]) / CELL + N / 2 - 0.5, (y - LOC[1]) / CELL + N / 2 - 0.5
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return SEA_Z - 200
    tx, ty = fi - i0, fj - j0
    return (Z[j0, i0] * (1 - tx) * (1 - ty) + Z[j0, i0 + 1] * tx * (1 - ty) + Z[j0 + 1, i0] * (1 - tx) * ty
            + Z[j0 + 1, i0 + 1] * tx * ty)


# ---- the drawing frame: the town + margin, 1 px = 1 m scaled to fit the sheet's drawing area
town = [(p["x"], p["y"]) for bid, p in B.items() if SHEETS.get(bid, {}).get("kind") not in ("rig", "islet", "wreck", "barge")]
X0, X1 = min(p[0] for p in town) - 90 * M, max(p[0] for p in town) + 90 * M
Y0, Y1 = min(p[1] for p in town) - 90 * M, max(p[1] for p in town) + 90 * M
SW, SH = 1700, 1200                    # sheet
DX, DY, DW, DH = 30, 70, 1240, 1060    # drawing area (left); the right column is notes + title block
K = min(DW / (X1 - X0), DH / (Y1 - Y0))  # px per world unit


def P(x, y):
    return (DX + (x - X0) * K + (DW - (X1 - X0) * K) / 2, DY + (Y1 - y) * K + (DH - (Y1 - Y0) * K) / 2)


def sheet(no, title, scale_note=""):
    img = Image.new("RGB", (SW, SH), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    dr.rectangle([10, 10, SW - 10, SH - 10], outline=(0, 0, 0), width=2)
    dr.rectangle([DX - 6, DY - 6, DX + DW + 6, DY + DH + 6], outline=(0, 0, 0), width=1)
    dr.text((DX, 22), title.upper(), font=F24, fill=(0, 0, 0))
    # title block (bottom right)
    tx, ty = DX + DW + 30, SH - 250
    dr.rectangle([tx - 10, ty - 10, SW - 22, SH - 22], outline=(0, 0, 0), width=2)
    dr.text((tx, ty), "AVALON", font=F32, fill=(0, 0, 0))
    dr.text((tx, ty + 40), "Liandri mining colony - redesign", font=F14, fill=(0, 0, 0))
    dr.text((tx, ty + 62), "run %s" % NAME, font=F12, fill=(80, 80, 80))
    dr.line([tx - 10, ty + 86, SW - 22, ty + 86], fill=(0, 0, 0))
    dr.text((tx, ty + 96), title, font=F14, fill=(0, 0, 0))
    if scale_note:
        dr.text((tx, ty + 118), scale_note, font=F12, fill=(80, 80, 80))
    dr.line([tx - 10, ty + 146, SW - 22, ty + 146], fill=(0, 0, 0))
    dr.text((tx, ty + 156), "SHEET", font=F12, fill=(80, 80, 80))
    dr.text((tx, ty + 172), no, font=F32, fill=(0, 0, 0))
    dr.text((tx + 190, ty + 156), "2026-10-08", font=F12, fill=(80, 80, 80))
    dr.text((tx + 190, ty + 180), "parti approved", font=F12, fill=(80, 80, 80))
    return img, dr


def notes(dr, lines, y=80):
    x = DX + DW + 30
    for ln in lines:
        if ln.startswith("#"):
            dr.text((x, y), ln[1:].strip(), font=F18, fill=(0, 0, 0))
            y += 26
        else:
            for part in wrap(ln, 52):
                dr.text((x, y), part, font=F12, fill=(30, 30, 30))
                y += 16
            y += 4
    return y


def wrap(t, n):
    out, line = [], ""
    for wd in t.split():
        if len(line) + len(wd) + 1 > n:
            out.append(line)
            line = wd
        else:
            line = (line + " " + wd).strip()
    return out + ([line] if line else [])


def scale_bar(dr):
    x0, y0 = DX + 20, DY + DH - 30
    for k, metres in enumerate((0, 50, 100)):
        pass
    px100 = 100 * M * K
    dr.rectangle([x0, y0, x0 + px100, y0 + 6], outline=(0, 0, 0))
    dr.rectangle([x0, y0, x0 + px100 / 2, y0 + 6], fill=(0, 0, 0))
    dr.text((x0, y0 - 16), "0", font=F10, fill=(0, 0, 0))
    dr.text((x0 + px100 / 2 - 6, y0 - 16), "50", font=F10, fill=(0, 0, 0))
    dr.text((x0 + px100 - 14, y0 - 16), "100 m", font=F10, fill=(0, 0, 0))
    nx, ny = DX + DW - 40, DY + 40
    dr.polygon([(nx, ny - 26), (nx - 9, ny), (nx + 9, ny)], fill=(0, 0, 0))
    dr.text((nx - 5, ny + 4), "N", font=F14, fill=(0, 0, 0))


# ---- base drawing: contours every 10 m, sea, hillshade (light)
GX = np.linspace(X0, X1, 260)
GY = np.linspace(Y0, Y1, 260)
ZG = np.array([[ground(x, y) for x in GX] for y in GY]) / M        # metres


def base(dr, shade=True, contours=True):
    gy, gx = np.gradient(ZG)
    if shade:
        lx, ly = math.cos(math.radians(SUN_AZ)), math.sin(math.radians(SUN_AZ))
        hs = np.clip(0.5 + (-gx * lx - gy * ly) * 0.08, 0, 1)
        cw, ch = (GX[1] - GX[0]) * K + 1, (GY[1] - GY[0]) * K + 1
        for j in range(len(GY)):
            for i in range(len(GX)):
                x, y = P(GX[i], GY[j])
                if ZG[j, i] <= SEA_Z / M:
                    c = (226, 236, 246)
                else:
                    v = int(236 + 16 * (hs[j, i] - 0.5))
                    c = (v, v, v - 4)
                dr.rectangle([x, y - ch, x + cw, y], fill=c)
    if contours:
        lv = np.floor(ZG / 10)
        for j in range(len(GY) - 1):
            for i in range(len(GX) - 1):
                if ZG[j, i] <= SEA_Z / M:
                    continue
                if lv[j, i] != lv[j, i + 1] or lv[j, i] != lv[j + 1, i]:
                    x, y = P(GX[i], GY[j])
                    major = int(max(lv[j, i], lv[j, i + 1], lv[j + 1, i])) % 5 == 0
                    dr.point((x, y), fill=(150, 150, 150) if major else (200, 200, 200))


RCLS = L.get("road_class") or ["spine"] + ["branch"] * (len(L["roads"]) - 1)
RW = {"spine": 8, "branch": 6, "lane": 3.5, "path": 1.8}


def roads(dr, col=(170, 160, 150), only=None):
    for r, c in zip(L["roads"], RCLS):
        if only and c not in only:
            continue
        wpx = max(1, int(RW.get(c, 4) * M * K))
        dr.line([P(*p) for p in r], fill=col if c != "path" else (190, 175, 150), width=wpx)


def footprints():
    out = []
    for bid, Pp in B.items():
        b = SHEETS.get(bid)
        if b is None or "size" not in b:
            continue
        W, D = b["size"][0] * M, b["size"][1] * M
        gap = max(W, D) * 1.5
        spec = b.get("count", "1").split()
        pts = [(0, 0)]
        if "x" in spec[0].lower():
            na_, nc_ = (int(v) for v in spec[0].lower().split("x"))
            pts = [((ka - (na_ - 1) / 2) * gap, (kc - (nc_ - 1) / 2) * gap) for kc in range(nc_) for ka in range(na_)]
        elif len(spec) == 2:
            n = int(spec[0])
            pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
        a = math.radians(Pp["yaw"])
        ca, sa = math.cos(a), math.sin(a)
        for da, dc in pts:
            cx, cy = Pp["x"] + da * ca - dc * sa, Pp["y"] + da * sa + dc * ca
            out.append((bid, [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in
                              ((D / 2, W / 2), (D / 2, -W / 2), (-D / 2, -W / 2), (-D / 2, W / 2))], b))
    return out


FP = footprints()


def buildings(dr, fill=(0, 0, 0), ground_works=(120, 120, 120)):
    for bid, poly, b in FP:
        if b["kind"] in ("pad", "dock", "jetty", "islet", "rig", "barge", "wreck"):
            dr.polygon([P(*p) for p in poly], outline=ground_works)
        else:
            dr.polygon([P(*p) for p in poly], fill=fill)


# ---- districts (transect zones) and the parti's places
def district(bid, b):
    k, fn = b["kind"], b.get("function")
    if bid.startswith(("shanty", "old_camp")) or (k == "house" and b.get("layer") == "decline"):
        return "T2 shanty"
    if k in ("tower", "office", "mast") or bid in ("authority_pad", "checkpoint", "beacon", "directors_house") or fn in ("clinic", "store"):
        return "T5 company"
    if k in ("hall", "tank", "silo", "cooling", "pump", "pad", "wellhead") or bid.startswith(("shed", "generator", "intake", "water_t", "fuel", "wellhead")):
        return "T4 works"
    if k in ("dock", "jetty", "barge") or bid in ("boat_landing",):
        return "T1 shore"
    return "T3 housing"


ZONES = {"T1 shore": (120, 170, 210), "T2 shanty": (200, 120, 60), "T3 housing": (230, 190, 80), "T4 works": (130, 130, 140), "T5 company": (190, 40, 40)}
LEVEL = {"T1 shore": "tissue (company)", "T2 shanty": "infill (residents)", "T3 housing": "support (company), infill growing",
         "T4 works": "support (company)", "T5 company": "tissue + support (company)"}


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def cross(o_, a, b):
        return (a[0] - o_[0]) * (b[1] - o_[1]) - (a[1] - o_[1]) * (b[0] - o_[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def zone_blobs(img, alpha=60, outline=False):
    """each district as the union of 25 m buffers round its own buildings (convex hulls of scattered members lie)"""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    do = ImageDraw.Draw(ov)
    cent = {}
    for bid, poly, b in FP:
        if b["kind"] in ("rig", "islet", "wreck"):
            continue
        z = district(bid, b)
        cx = sum(p[0] for p in poly) / 4
        cy = sum(p[1] for p in poly) / 4
        r = (max(math.dist(poly[0], poly[1]), math.dist(poly[1], poly[2])) / 2 + 25 * M) * K
        x, y = P(cx, cy)
        do.ellipse([x - r, y - r, x + r, y + r], fill=ZONES[z] + (alpha,))
        cent.setdefault(z, []).append((x, y))
    out = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    img.paste(out)
    return {z: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for z, v in cent.items()}


def zone_hulls():
    groups = {}
    for bid, poly, b in FP:
        if b["kind"] in ("rig", "islet", "wreck"):
            continue
        z = district(bid, b)
        for x, y in poly:
            for dx_, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                groups.setdefault(z, []).append((x + dx_ * 15 * M, y + dy_ * 15 * M))
    return {z: hull(p) for z, p in groups.items()}


SP = [tuple(p) for p in L["spine"]]
S_ACC = [0.0]
for a, b_ in zip(SP[:-1], SP[1:]):
    S_ACC.append(S_ACC[-1] + math.dist(a, b_))
DOCK = tuple(L["sites"]["dock"])
TOWER = (B["tower"]["x"], B["tower"]["y"]) if "tower" in B else tuple(L["sites"]["tower"])
k_t = min(range(len(SP)), key=lambda k: math.dist(SP[k], TOWER))
S_T = S_ACC[k_t]


def spine_at(s):
    k = max(0, min(len(SP) - 2, int(np.searchsorted(S_ACC, s) - 1)))
    t = (s - S_ACC[k]) / max(1e-6, S_ACC[k + 1] - S_ACC[k])
    return (SP[k][0] + (SP[k + 1][0] - SP[k][0]) * t, SP[k][1] + (SP[k + 1][1] - SP[k][1]) * t)


s_gate = next((S_ACC[k] for k in range(len(SP)) if math.dist(SP[k], TOWER) < 150 * M), S_T * 0.85)
PLACES = {"dock": DOCK, "dock_gate": spine_at(80 * M), "spine_mid": spine_at(S_T * 0.5),
          "company_gate": spine_at(s_gate), "catwalk": TOWER}
EMO_COL = {"dread": (60, 60, 90), "exposure": (200, 140, 30), "smallness": (150, 40, 40), "melancholy": (70, 90, 150)}
ORE = [c for c in L.get("connections", []) if c.get("carrier") == "conveyor"]


def star(dr, x, y, r, col):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    dr.polygon(pts, fill=col)


def arrow(dr, x, y, ang_deg, length, col, width=3, label=None):
    a = math.radians(ang_deg)
    x2, y2 = x + math.cos(a) * length, y - math.sin(a) * length
    dr.line([(x, y), (x2, y2)], fill=col, width=width)
    for s_ in (150, -150):
        b = a + math.radians(s_)
        dr.line([(x2, y2), (x2 + math.cos(b) * 14, y2 - math.sin(b) * 14)], fill=col, width=width)
    if label:
        dr.text((x2 + 6, y2 - 8), label, font=F12, fill=col)


def beats(dr, numbered=True):
    for k, bt in enumerate(PARTI["beats"]):
        x, y = P(*PLACES[bt["at"]])
        col = EMO_COL.get(bt["emotion"], (0, 0, 0))
        dr.ellipse([x - 13, y - 13, x + 13, y + 13], fill=col)
        dr.text((x - 4, y - 8), str(k + 1), font=F14, fill=(255, 255, 255))
        ly = y + 16 if bt["at"] == "catwalk" else y - 9
        dr.text((x + 17, ly), "%s - %s" % (bt["emotion"].upper(), bt["at"].replace("_", " ")), font=F12, fill=col)


# ============================================================================== A-001 parti
img, dr = sheet("A-001", "Parti", "diagram, not to scale")
dr.rectangle([DX, DY, DX + DW, DY + DH], fill=(250, 248, 244))
# a simplified island: the coast as a soft blob from the terrain
for j in range(len(GY)):
    for i in range(len(GX)):
        if ZG[j, i] > SEA_Z / M:
            x, y = P(GX[i], GY[j])
            dr.rectangle([x, y - 5, x + 5, y], fill=(232, 228, 220))
CENT = zone_blobs(img, 45)
dr = ImageDraw.Draw(img)
for z, (x, y) in CENT.items():
    dr.text((x - 30, y + 14), z, font=F12, fill=ZONES[z])
# the axis
ax0, ax1 = P(*DOCK), P(*TOWER)
dr.line([ax0, ax1], fill=(0, 0, 0), width=7)
dr.text(((ax0[0] + ax1[0]) / 2 + 12, (ax0[1] + ax1[1]) / 2), "AXIS", font=F18, fill=(0, 0, 0))
# the datum: the ore line, straight
for c in ORE:
    dr.line([P(*c["path"][0]), P(*c["path"][-1])], fill=(90, 90, 90), width=4)
if ORE:
    x, y = P(*ORE[0]["path"][-1])
    dr.text((x + 8, y), "DATUM - the ore line", font=F12, fill=(90, 90, 90))
# downwind: the smoke drifts over the shanty
cx_, cy_ = P(*(B["cooling_towers"]["x"], B["cooling_towers"]["y"])) if "cooling_towers" in B else ax0
for k in range(5):
    dr.arc([cx_ - 30 - k * 28, cy_ - 30 - k * 28, cx_ + 30 + k * 28, cy_ + 30 + k * 28],
           math.degrees(math.atan2(-WIND[1], WIND[0])) - 20, math.degrees(math.atan2(-WIND[1], WIND[0])) + 20, fill=(150, 120, 90), width=2)
arrow(dr, cx_, cy_, math.degrees(math.atan2(WIND[1], WIND[0])), 170, (150, 120, 90), 3, "smoke, downwind")
# hero + second
hx, hy = P(*TOWER)
star(dr, hx, hy, 30, (190, 40, 40))
dr.text((hx + 34, hy - 20), "HERO - the tower (the high ground)", font=F14, fill=(190, 40, 40))
# gateways
for g in ("dock_gate", "company_gate"):
    x, y = P(*PLACES[g])
    dr.rectangle([x - 9, y - 9, x + 9, y + 9], outline=(0, 0, 0), width=3)
    dr.text((x - 60, y + 12), g.replace("_", " ").upper(), font=F12, fill=(0, 0, 0))
beats(dr)
notes(dr, ["# The sentence", PARTI["sentence"], "",
           "# Beats (emotion x action)"] + ["%d. %s - %s: %s" % (k + 1, b["at"].replace("_", " "), b["emotion"], b["move"]) for k, b in enumerate(PARTI["beats"])]
      + ["", "# Ordering (Ching)"] + ["%s: %s" % (k, v) for k, v in PARTI["ordering"].items()]
      + ["", "# Levels (Habraken)"] + ["%s: %s" % (k, v) for k, v in PARTI["levels"].items()])
img.save(os.path.join(OUT, "A-001_parti.png"))

# ============================================================================== A-002 site analysis
img, dr = sheet("A-002", "Site analysis", "see the scale bar")
base(dr)
# steep ground: hatch slopes over 25 degrees
gy, gx = np.gradient(ZG, (GY[1] - GY[0]) / M, (GX[1] - GX[0]) / M)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
for j in range(0, len(GY), 2):
    for i in range(0, len(GX), 2):
        if slope[j, i] > 25 and ZG[j, i] > SEA_Z / M:
            x, y = P(GX[i], GY[j])
            dr.line([(x - 3, y + 3), (x + 3, y - 3)], fill=(200, 80, 60))
# the plume (same model as layout_spine pass 1)
EM = {"cooling": 0.35, "hall": 0.2, "tank": 0.15, "silo": 0.12, "pump": 0.05}
nu = np.zeros_like(ZG)
for bid, Pp in B.items():
    q = EM.get(SHEETS.get(bid, {}).get("kind"))
    if not q:
        continue
    for j in range(len(GY)):
        dyv = (GY[j] - Pp["y"]) / M
        dxv = (GX - Pp["x"]) / M
        down = dxv * WIND[0] + dyv * WIND[1]
        cross = -dxv * WIND[1] + dyv * WIND[0]
        sig = 0.08 * np.maximum(down, 0) + 20
        nu[j] += np.where(down > 0, q * np.exp(-cross ** 2 / (2 * sig ** 2)) * 20 / sig, 0) + 0.5 * q * np.exp(-np.hypot(dxv, dyv) / 50)
ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
do = ImageDraw.Draw(ov)
cw_, ch_ = (GX[1] - GX[0]) * K + 1, (GY[1] - GY[0]) * K + 1
for j in range(len(GY)):
    for i in range(len(GX)):
        a_ = int(min(1.0, nu[j, i] / 0.8) * 150)
        if a_ > 12:
            x, y = P(GX[i], GY[j])
            do.rectangle([x, y - ch_, x + cw_, y], fill=(215, 120, 40, a_))
# viewshed (what the player sees): green dots where seen by many points
try:
    vis = np.load(os.path.join(RUN, "isl_vis.npz"))["score"]
    vs = vis / max(1e-6, np.percentile(vis[vis > 0], 95))
    for j in range(N):
        for i in range(N):
            if vs[j, i] > 0.85:
                x, y = P(LOC[0] + (i + 0.5 - N / 2) * CELL, LOC[1] + (j + 0.5 - N / 2) * CELL)
                r_ = CELL * K / 2
                if DX < x < DX + DW and DY < y < DY + DH:
                    do.rectangle([x - r_, y - r_, x + r_, y + r_], outline=(60, 140, 70, 160))
except Exception as e:
    print("  (viewshed: %s)" % e)
img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"))
dr = ImageDraw.Draw(img)
roads(dr, (200, 190, 180))
buildings(dr, (90, 90, 90), (160, 160, 160))
# sun and wind
sx_, sy_ = DX + 120, DY + 120
dr.ellipse([sx_ - 18, sy_ - 18, sx_ + 18, sy_ + 18], outline=(220, 150, 30), width=3)
arrow(dr, sx_, sy_, SUN_AZ + 180, 80, (220, 150, 30), 3, "low sun az %d, el %d (light travels this way)" % (SUN_AZ, SUN_EL))
arrow(dr, DX + 120, DY + 260, math.degrees(math.atan2(WIND[1], WIND[0])), 90, (90, 110, 160), 4, "storm wind")
scale_bar(dr)
notes(dr, ["# Reading", "Hillshade and 10 m contours (bold every 50 m). Sea pale blue.",
           "Red hatch: ground steeper than 25 degrees - stairs, retaining walls or nothing.",
           "Orange wash: the pollution plume from the cooling towers, halls, tanks and silos, carried downwind (the model pass 1 of the spine layout uses). Worst land = steep + in the plume: the shanty's land.",
           "Green squares: the ground the player sees most (viewshed, top 15 %) - dress it first.",
           "Sun low from az %d: long shadows across the town at dusk; the tower's silhouette against it from the catwalk." % SUN_AZ,
           "", "# Opportunities", "The high ground near the tower: the company, the view, the hero.",
           "The dock's flat apron: arrival, compression (beat 1).",
           "The plume's shadow downwind: where the town that nobody planned grows."])
img.save(os.path.join(OUT, "A-002_site_analysis.png"))

# ============================================================================== A-101 framework plan
img, dr = sheet("A-101", "Framework plan", "see the scale bar")
base(dr, shade=False)
CENT = zone_blobs(img, 60)
dr = ImageDraw.Draw(img)
for z, (x, y) in CENT.items():
    dr.text((x - 40, y - 34), z.upper(), font=F14, fill=ZONES[z])
roads(dr)
for c in ORE:
    pts = [P(*p) for p in c["path"]]
    dr.line(pts, fill=(60, 60, 60), width=5)
for rk in L.get("racks", []):
    dr.line([P(*rk[0]), P(*rk[1])], fill=(80, 120, 160), width=4)
buildings(dr)
# the beat route: dock -> tower along the spine
route = [p for p, s_ in zip(SP, S_ACC) if s_ <= S_T]
dr.line([P(*p) for p in route], fill=(190, 40, 40), width=3)
for g in ("dock_gate", "company_gate"):
    x, y = P(*PLACES[g])
    dr.rectangle([x - 9, y - 9, x + 9, y + 9], outline=(0, 0, 0), width=3)
    dr.text((x + 12, y + 8), g.replace("_", " ").upper(), font=F12, fill=(0, 0, 0))
hx, hy = P(*TOWER)
star(dr, hx, hy, 22, (190, 40, 40))
beats(dr)
scale_bar(dr)
notes(dr, ["# Framework (frozen first)", "The tissue the company owns and later passes may not move: the spine and its branches, the terraces, the gateways, the hero, the ore line (datum), the district boundaries. Codes (A-301) fill each district; infill grows inside them.",
           "", "# Districts = transect zones"] + ["%s: %s" % (z, LEVEL[z]) for z in ZONES]
      + ["", "# Legend", "Red line: the beat route, dock to tower. Squares: gateways. Star: the hero.",
         "Dark line: the ore conveyor (datum). Blue: pipe racks (shared utility trunks).",
         "Roads by class: spine, branch, lane (narrow), worn paths (sand)."])
img.save(os.path.join(OUT, "A-101_framework_plan.png"))

# ============================================================================== A-102 figure-ground / Nolli, A-201 sections
if not os.path.exists(os.path.join(RUN, "isl_sections.png")):
    subprocess.run(["py", os.path.join(HERE, "tools", "drawings.py"), os.path.join(RUN, "isl_ec.bmp"), os.path.join(RUN, "isl_layout.json"),
                    os.path.join(RUN, "isl")], check=True)
img, dr = sheet("A-102", "Figure-ground and Nolli plan", "1 px = 1 m (scaled to fit)")
fg = Image.open(os.path.join(RUN, "isl_figureground.png"))
no = Image.open(os.path.join(RUN, "isl_nolli.png"))
k2 = min((DW / 2 - 10) / fg.size[0], DH / fg.size[1])
fg2, no2 = fg.resize((int(fg.size[0] * k2), int(fg.size[1] * k2))), no.resize((int(no.size[0] * k2), int(no.size[1] * k2)))
img.paste(fg2, (DX, DY))
img.paste(no2, (DX + DW // 2 + 10, DY))
notes(dr, ["# Figure-ground", "Built mass black, all else white. Reads the grain: the tight shanty blocks downwind, the big works, the tower's footprint on the high ground, the spaces left between.",
           "", "# Nolli plan", "The same, with the town's shared interiors - mess, clinic, store, office, altar - left white: they belong to the open space. Few of them, and all company-held: a town with nowhere of its own."])
img.save(os.path.join(OUT, "A-102_figure_ground.png"))
img, dr = sheet("A-201", "Sections A, B, C", "true scale, no vertical exaggeration")
sc = Image.open(os.path.join(RUN, "isl_sections.png"))
k3 = min(DW / sc.size[0], DH / sc.size[1])
img.paste(sc.resize((int(sc.size[0] * k3), int(sc.size[1] * k3))), (DX, DY))
notes(dr, ["# Cuts", "A - the parti axis: from the sea off the dock, through the town, to the tower and past it.",
           "B - across the spine at its busiest junction (space syntax).",
           "C - the command room's view along the window (yaw 300): the catwalk beat.",
           "", "# Reading", "Solid black: buildings cut. Pale: buildings just behind the cut. Dark grey: the ground cut. The red figure is 1.8 m; marks at 25 m (faces) and 100 m (figures) - Gehl's distances. The peak frame's lone figure belongs between them."])
img.save(os.path.join(OUT, "A-201_sections.png"))

# ============================================================================== A-301 district codes
img, dr = sheet("A-301", "District codes", "form-based code per transect zone")
plots = {p["id"]: p for p in L.get("plots", [])}
stats = {}
for bid, Pp in B.items():
    b = SHEETS.get(bid)
    if not b:
        continue
    z = district(bid, b)
    s_ = stats.setdefault(z, {"n": 0, "setback": [], "yard": [], "add": 0, "aband": 0})
    s_["n"] += 1
    if bid in plots:
        s_["setback"].append(plots[bid].get("setback", 4))
        s_["yard"].append(plots[bid].get("yard", 0))
    s_["add"] += Pp.get("additions", 0) or 0
    s_["aband"] += 1 if Pp.get("abandoned") else 0
CODE = {
    "T1 shore": ("—", "—", "—", "1", "quay, cranes, barge; the arrival", "Main Gateway (dock gate)"),
    "T2 shanty": ("1-6 m", "35 % party walls", "10 deg", "1, + lean-tos", "the company kit, transformed by additions; laundry, cables", "honoured: nodes, small squares, refuge, building edge"),
    "T3 housing": ("1-6 m", "15 % party walls", "6 deg", "1-2", "company prefab rows, back yards and back lanes", "honoured: paths and goals"),
    "T4 works": ("3-6 m", "5 % party walls", "3 deg", "1-3 (tall stacks)", "halls, tanks, silos, racks; the datum", "inverted: blank edges, no staying"),
    "T5 company": ("high ground", "detached", "planned", "tower 110 m", "battered walls, stepped base, red domes", "inverted: parade ground, prospect without refuge"),
}
cols = ["zone", "setback", "gaps", "wobble", "storeys", "character", "patterns (Alexander)", "measured here"]
cw = [110, 90, 120, 70, 110, 260, 280, 200]
x0, y0 = DX + 10, DY + 20
xx = x0
for c, wdt in zip(cols, cw):
    dr.text((xx + 4, y0), c.upper(), font=F12, fill=(0, 0, 0))
    xx += wdt
dr.line([x0, y0 + 22, x0 + sum(cw), y0 + 22], fill=(0, 0, 0), width=2)
yy = y0 + 32
for z in ZONES:
    st = stats.get(z, {"n": 0, "setback": [], "yard": [], "add": 0, "aband": 0})
    meas = "%d bldgs, setback %s, yard %s, +%d additions%s" % (
        st["n"], ("%.1f m" % np.mean(st["setback"])) if st["setback"] else "-", ("%.0f m" % np.mean(st["yard"])) if st["yard"] else "-",
        st["add"], (", %d abandoned" % st["aband"]) if st["aband"] else "")
    row = [z] + list(CODE[z]) + [meas]
    xx = x0
    hmax = 1
    for c, wdt in zip(row, cw):
        lines = wrap(c, max(8, wdt // 7))
        for k, ln in enumerate(lines):
            dr.text((xx + 4, yy + k * 15), ln, font=F12, fill=ZONES[z] if c == z else (30, 30, 30))
        hmax = max(hmax, len(lines))
        xx += wdt
    yy += hmax * 15 + 14
    dr.line([x0, yy - 6, x0 + sum(cw), yy - 6], fill=(200, 200, 200))
notes(dr, ["# How to read", "Each district is a transect zone with its own small code (CNU form-based codes; Habraken's levels). The code fixes only what the framework (A-101) leaves open.",
           "The dystopia is in the inversion: Alexander's patterns for places people stay are honoured where the residents build (shanty) and broken on purpose where the company builds (works, company high ground).",
           "", "# Source of the numbers", "The code values are the generator's own (layout_spine.py passes 2-3); 'measured here' is this run."])
img.save(os.path.join(OUT, "A-301_district_codes.png"))

# ============================================================================== A-401 serial vision
img, dr = sheet("A-401", "Serial vision - dock to catwalk", "stations every 35 m, eye height 1.6 m")
base(dr, shade=False)
roads(dr, (215, 210, 205))
buildings(dr, (150, 150, 150), (190, 190, 190))
tz = (ground(*TOWER) + 110 * M)                                     # the tower's top


def inside(poly, x, y):
    c = False
    for k in range(len(poly)):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


BOXES = [(bid, poly, b, (B[bid].get("z") or ground(*poly[0])) + (b["size"][2] if len(b["size"]) > 2 else 6) * M)
         for bid, poly, b in FP if bid != "tower" and b["kind"] not in ("pad", "dock", "jetty", "rig", "islet", "barge", "wreck")]
stations = []
s_ = 0.0
while s_ <= S_T:
    p = spine_at(s_)
    e = ground(*p) + 1.6 * M
    seen = True
    for t in np.linspace(0.02, 0.98, 60):                           # line of sight to the tower top: terrain + buildings
        q = (p[0] + (TOWER[0] - p[0]) * t, p[1] + (TOWER[1] - p[1]) * t)
        ray = e + (tz - e) * t
        if ground(*q) > ray:
            seen = False
            break
        for bid_, poly_, b_, top_ in BOXES:
            if top_ > ray and min(x_ for x_, _ in poly_) <= q[0] <= max(x_ for x_, _ in poly_) and                     min(y_ for _, y_ in poly_) <= q[1] <= max(y_ for _, y_ in poly_) and inside(poly_, *q):
                seen = False
                break
        if not seen:
            break
    stations.append((s_, p, seen))
    s_ += 35 * M
prev = None
for k, (s_, p, seen) in enumerate(stations):
    x, y = P(*p)
    nxt = stations[min(k + 1, len(stations) - 1)][1]
    ang = math.degrees(math.atan2(nxt[1] - p[1], nxt[0] - p[0])) if nxt != p else 0
    col = (190, 40, 40) if seen else (120, 120, 120)
    # the view cone along the route
    for sgn in (-1, 1):
        a = math.radians(ang + sgn * 25)
        dr.line([(x, y), (x + math.cos(a) * 26, y - math.sin(a) * 26)], fill=col, width=1)
    dr.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col)
    dr.text((x + 8, y + 4), str(k + 1), font=F10, fill=(0, 0, 0))
hx, hy = P(*TOWER)
star(dr, hx, hy, 22, (190, 40, 40))
beats(dr)
scale_bar(dr)
runs, cur = [], None
for s_, p, seen in [st for st in stations if math.dist(st[1], TOWER) > 40 * M]:     # at its foot you look up its wall
    if cur is None or cur[0] != seen:
        cur = [seen, 1]
        runs.append(cur)
    else:
        cur[1] += 1
hidden = sum(1 for s_, p, seen in stations if not seen)
pattern = " ".join(("SEEN x%d" if r[0] else "hidden x%d") % r[1] for r in runs)
rule = "pass" if any(not r[0] for r in runs) and runs[-1][0] else "FAIL - the tower should hide at least once, then be revealed"
notes(dr, ["# The walk", "%d stations, %d m from the dock to the tower. Red: the tower top is seen from there (line of sight over terrain and buildings). Grey: hidden." % (len(stations), int(S_T / M)),
           "Sequence: " + pattern,
           "Cullen's rule (show, hide, reveal): " + rule,
           "", "# The beats"] + ["%d. %s - %s" % (k + 1, b["emotion"], b["move"]) for k, b in enumerate(PARTI["beats"])]
      + ["", "# Next", "The pilot flies these stations in game and pins the film strip under this plan; the last frame is judged against the peak frame (dark frame, grated catwalk, lone figure 40-100 m, dusk rain)."])
img.save(os.path.join(OUT, "A-401_serial_vision.png"))

# ---- the set as one PDF
pages = [Image.open(os.path.join(OUT, f)).convert("RGB") for f in sorted(os.listdir(OUT)) if f.endswith(".png") and f.startswith("A-")]
try:
    pages[0].save(os.path.join(OUT, "plans_set.pdf"), save_all=True, append_images=pages[1:])
except Exception as e:                     # this Pillow has no JPEG encoder for PDF pages: the PNG sheets stand
    print("  (no PDF: %s)" % e)
print("plans: %d sheets -> %s (stations %d, tower hidden at %d; %s)" % (len(pages), OUT, len(stations), hidden, rule))
