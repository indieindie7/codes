r"""Co-direction: the town is designed by four collaborators who must agree (the user, 2026-10-08: "I want the town to
be designed by the model we just created and the cinematography rules, like co-direction - writer and artist").
Each candidate (an island + a town layout on it) goes to three reviewers; each scores it 0..1, writes notes, and may
veto. The generator keeps the candidate they agree on best (the geometric mean of the three: one weak role sinks it).

  WRITER    the story and the town model: binder/parti.json (the sentence, the beats and their emotions) and the
            systems that make the town work
              - the town works: systems score; a core need unmet is a VETO
              - "the company holds the high ground": the tower's ground stands over the works plateau
              - "the town lives in its smoke": the shanty's mean nuisance (the plume model of layout_spine pass 1)
              - beat 1 "dread - compression, tower hidden" at the dock: the tower hidden from an early station
  DIRECTOR  the cinematography rules (games/reports/Cinematography and concept art for the Avalon town.md)
              - the window frame (compose.py): hero on a third, the town 30-60 % of the width, 12+ buildings,
                depth bands, a leading line into the hero; no hero in the frame is a VETO
              - three layers with air between them: land in the midground band (150-400 m along the view),
                then a gap (water or low ground), then the background (the far shore or the sea horizon)
              - the hour: the sun 90-180 deg off the view (side to back light)
              - the reveal: along the walk from the dock the tower is shown, hidden, then revealed (Cullen; Spielberg)
              - the hero reads as a silhouette against the sky (its top above the terrain's skyline in the frame)
  ENGINEER  civil engineering (games/research_notes/Civil engineering for the generator/report.md, s. 9): the checks
            that need only the layout and the natural ground - E1 road grades per class (natural ground the cut/fill
            must fight), E17 slope use (housing <= 14 deg, nothing > 17; the shanty perches to 17 on stilts), E21
            the buffer order (company housing upwind of the heavy works), E14 water head (the tank 28 m over what it
            serves), E12 the ore line downhill toward the port at <= 15 deg, E16 fuel tanks >= 100 m from housing
  ARTIST    the drawings and the believability metrics
              - IMP (irregular, lived-in plots) and HIER (street hierarchy, loops, old core near the dock)
              - figure-ground grain: no building lost in the sea, the town compact (its built area within a radius)

    py tools/codirect.py <heightmap.bmp> <layout.json>            -> prints the three reviews
    (as a library: review(heightmap, layout) -> dict with writer/director/artist {score, notes, veto} + total)
"""
import json, math, os, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import binder  # noqa
import compose  # noqa
import metrics  # noqa

LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, N, M, SEA_Z = 512.0, 128, 50.0, -4967.0
LOOK = 300.0
SUN_AZ = 136.0
PARTI = json.load(open(os.path.join(os.path.dirname(HERE), "binder", "parti.json")))


def _Z(bmp):
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    H = H[::-1] if h > 0 else H
    return LOC[2] + (H - 32768) * 0.5


def _g(Z, x, y):
    fi, fj = (x - LOC[0]) / CELL + N / 2 - 0.5, (y - LOC[1]) / CELL + N / 2 - 0.5
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return SEA_Z - 300
    tx, ty = fi - i0, fj - j0
    return (Z[j0, i0] * (1 - tx) * (1 - ty) + Z[j0, i0 + 1] * tx * (1 - ty) + Z[j0 + 1, i0] * (1 - tx) * ty + Z[j0 + 1, i0 + 1] * tx * ty)


def _boxes(L, sheets):
    out = []
    for bid, b in L["buildings"].items():
        s = sheets.get(bid)
        if not s or "size" not in s or bid == "tower" or s["kind"] in ("pad", "dock", "jetty", "rig", "islet", "barge", "wreck"):
            continue
        r = max(s["size"][0], s["size"][1]) * M * 0.5
        out.append((b["x"], b["y"], r, b.get("z", 0) + (s["size"][2] if len(s["size"]) > 2 else 6) * M))
    return out


def serial(Z, L, sheets, step_m=35.0):
    """the walk dock -> tower: per station, is the tower's top seen (terrain + buildings as round prisms)?"""
    sp = L.get("spine") or []
    T = L["buildings"].get("tower")
    if not sp or not T:
        return []
    tz = T.get("z", _g(Z, T["x"], T["y"])) + sheets["tower"]["size"][2] * M
    boxes = _boxes(L, sheets)
    acc, k_t = [0.0], min(range(len(sp)), key=lambda k: math.dist(sp[k], (T["x"], T["y"])))
    for a, b in zip(sp[:-1], sp[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    out, s = [], 0.0
    while s <= acc[k_t]:
        k = max(0, min(len(sp) - 2, int(np.searchsorted(acc, s) - 1)))
        t = (s - acc[k]) / max(1e-6, acc[k + 1] - acc[k])
        p = (sp[k][0] + (sp[k + 1][0] - sp[k][0]) * t, sp[k][1] + (sp[k + 1][1] - sp[k][1]) * t)
        if math.dist(p, (T["x"], T["y"])) > 40 * M:
            e = max(_g(Z, *p), SEA_Z) + 1.6 * M
            seen = True
            for u in np.linspace(0.03, 0.97, 50):
                q = (p[0] + (T["x"] - p[0]) * u, p[1] + (T["y"] - p[1]) * u)
                ray = e + (tz - e) * u
                if _g(Z, *q) > ray or any(math.hypot(q[0] - bx, q[1] - by) < br and bt > ray for bx, by, br, bt in boxes):
                    seen = False
                    break
            out.append(seen)
        s += step_m * M
    return out


def review(heightmap, layout_path):
    Z = _Z(heightmap)
    L = json.load(open(layout_path))
    _, sheets = binder.load()
    B = L["buildings"]
    R = {}

    # ---------------------------------------------------------------- the WRITER
    notes, veto = [], None
    sysd = L.get("systems", {})
    sys_s = float(sysd.get("score", 0.0))
    core_unmet = [u for u in sysd.get("unmet", []) if u[1] in ("power", "water", "ore", "workers")]
    if core_unmet:
        veto = "the town doesn't work: %s" % "; ".join("%s needs %s" % (u[0], u[1]) for u in core_unmet)
    notes.append("systems %.2f" % sys_s)
    tower_g = _g(Z, B["tower"]["x"], B["tower"]["y"]) if "tower" in B else 0
    works = [b for bid, b in B.items() if sheets.get(bid, {}).get("kind") in ("hall", "tank", "silo", "cooling")]
    works_g = np.mean([_g(Z, b["x"], b["y"]) for b in works]) if works else tower_g
    high = float(np.clip((tower_g - works_g) / M / 20.0, 0, 1))          # 20 m over the works = full marks
    notes.append("high ground: the tower stands %.0f m over the works" % ((tower_g - works_g) / M))
    poor = [b.get("nuisance", 0.0) for bid, b in B.items() if bid.startswith(("shanty", "old_camp"))]
    smoke = float(np.clip(np.mean(poor) / 0.5, 0, 1)) if poor else 0.0
    notes.append("smoke over the shanty: mean nuisance %.2f" % (np.mean(poor) if poor else 0))
    walk = serial(Z, L, sheets)
    beat1 = 1.0 if any(not v for v in walk[:5]) else 0.0
    notes.append("beat 1 (dread: tower hidden at the dock): %s" % ("yes" if beat1 else "NO - the tower shows from the quay"))
    R["writer"] = {"score": round(0.35 * sys_s + 0.2 * high + 0.25 * smoke + 0.2 * beat1, 3), "notes": notes, "veto": veto}

    # ---------------------------------------------------------------- the DIRECTOR
    notes, veto = [], None
    fr = compose.score(heightmap, layout_path)
    if not fr.get("hero"):
        veto = "no hero in the window"
    notes.append("frame %.2f: hero %s at u=%s (thirds %s), span %s, %s buildings, depth %s, lead %s" % (
        fr.get("total", 0), fr.get("hero"), fr.get("hero_u"), fr.get("thirds"), fr.get("span"), fr.get("in_frame"), fr.get("depth"), fr.get("lead")))
    # three layers along the view axis: land 150-400 m, then a gap, then something beyond (far shore / sea horizon)
    ex, ey = compose.EYE[0], compose.EYE[1]
    prof = []
    for r in range(100, 1300, 20):
        a = math.radians(LOOK)
        prof.append((r, _g(Z, ex + r * M * math.cos(a), ey + r * M * math.sin(a)) > SEA_Z + 30))
    mg = any(l for r, l in prof if 150 <= r <= 400)
    gap_r = next((r for r, l in prof if r > 200 and not l), None)
    gap = gap_r is not None and any(l for r, l in prof if 150 <= r < gap_r)
    layers = (0.4 if mg else 0) + (0.4 if gap else 0) + 0.2                # the background: the sea horizon is always there
    notes.append("layers: midground land %s, gap of air %s" % ("yes" if mg else "NO", ("at %d m" % gap_r) if gap else "NO"))
    off = abs((SUN_AZ - LOOK + 180) % 360 - 180)
    light = 1.0 if 90 <= off <= 180 else off / 90.0
    notes.append("light: the sun %.0f deg off the view (%s)" % (off, "back/side light" if off >= 90 else "front light - flat"))
    reveal = 0.0
    if walk:
        runs = []
        for v in walk:
            if not runs or runs[-1][0] != v:
                runs.append([v, 1])
            else:
                runs[-1][1] += 1
        if any(not r[0] for r in runs) and runs[-1][0]:
            reveal = 1.0
        notes.append("reveal along the walk: " + " ".join(("SEEN x%d" if r[0] else "hidden x%d") % r[1] for r in runs))
    sil = 0.5
    if fr.get("hero") and fr["hero"] in B:
        h = B[fr["hero"]]
        top = _g(Z, h["x"], h["y"]) + sheets[fr["hero"]]["size"][2] * M
        p = compose.project(h["x"], h["y"], top)
        if p:
            a = math.radians(LOOK + math.degrees(math.atan((p[0] - 0.5) * 2 * math.tan(math.radians(compose.HALF_W)))))
            sky = 1.0
            hd = math.hypot(h["x"] - ex, h["y"] - ey)
            for r in np.linspace(hd + 200, 60000, 120):          # the skyline behind the hero
                x_, y_ = ex + r * math.cos(a), ey + r * math.sin(a)
                pr = compose.project(x_, y_, _g(Z, x_, y_))
                if pr:
                    sky = min(sky, pr[1])
            sil = 1.0 if p[1] < sky else 0.2
            notes.append("hero silhouette: %s" % ("against the sky" if p[1] < sky else "against the land behind it"))
    R["director"] = {"score": round(0.4 * fr.get("total", 0) + 0.15 * layers + 0.1 * light + 0.2 * reveal + 0.15 * sil, 3),
                     "notes": notes, "veto": veto}

    # ---------------------------------------------------------------- the ENGINEER
    notes, checks = [], {}
    WIND = (0.83, -0.55)
    cls = L.get("road_class") or (["spine"] + ["branch"] * (len(L.get("roads", [])) - 1))
    over = tot = 0.0
    for r, c in zip(L.get("roads", []), cls):
        if c == "path":
            continue
        cap = 0.10 if c in ("spine", "branch") else 0.15
        for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
            d = math.hypot(bx - ax, by - ay)
            if d < 1:
                continue
            g = abs(max(_g(Z, bx, by), SEA_Z) - max(_g(Z, ax, ay), SEA_Z)) / d
            tot += d
            over += d if g > cap else 0.0
    checks["E1 road grades"] = 1.0 - (over / tot if tot else 0.0)
    notes.append("E1: %.0f %% of the road length climbs over its class's grade cap" % (100 * (1 - checks["E1 road grades"])))
    gy, gx = np.gradient(Z / M, CELL / M)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))

    def sl(x, y):
        i, j = int((x - LOC[0]) / CELL + N / 2), int((y - LOC[1]) / CELL + N / 2)
        return float(slope[min(max(j, 0), N - 1), min(max(i, 0), N - 1)])
    bad = []
    for bid, b in B.items():
        k = sheets.get(bid, {}).get("kind")
        if k in (None, "rig", "islet", "wreck", "barge", "dock", "jetty", "tower"):
            continue
        lim = 17.0 if (bid.startswith(("shanty", "old_camp")) or k in ("mast", "wellhead")) else (14.0 if k in ("house", "dorm") else 17.0)
        if sl(b["x"], b["y"]) > lim:
            bad.append(bid)
    checks["E17 slope use"] = 1.0 - len(bad) / max(1, len(B))
    notes.append("E17: %s" % ("all on buildable ground" if not bad else "too steep: " + ", ".join(bad[:5])))
    heavy = [b for bid, b in B.items() if sheets.get(bid, {}).get("kind") in ("hall", "cooling", "tank", "silo") or bid.startswith("generator")]
    company = [b for bid, b in B.items() if bid in ("dorm", "dorm_b", "dorm_c", "staff_houses", "directors_house")]
    pairs = [(h_, s_) for h_ in company for s_ in heavy]
    upw = sum(1 for h_, s_ in pairs if (h_["x"] - s_["x"]) * WIND[0] + (h_["y"] - s_["y"]) * WIND[1] < 0)
    checks["E21 buffer order"] = upw / max(1, len(pairs))
    notes.append("E21: company housing upwind of the works in %.0f %% of pairs" % (100 * checks["E21 buffer order"]))
    tanks = [b for bid, b in B.items() if bid in ("water_tower", "water_tanks")]
    if tanks:
        t_ = max(tanks, key=lambda b: _g(Z, b["x"], b["y"]))
        tz_ = _g(Z, t_["x"], t_["y"]) + (sheets.get("water_tower", {}).get("size", [0, 0, 0])[2] * M if "water_tower" in B else 0)
        served = [_g(Z, b["x"], b["y"]) for bid, b in B.items() if sheets.get(bid, {}).get("kind") in ("house", "dorm", "office") and
                  math.hypot(b["x"] - t_["x"], b["y"] - t_["y"]) < 300 * M]
        head = (tz_ - max(served)) / M if served else 99
        checks["E14 water head"] = float(np.clip(head / 28.0, 0, 1))
        notes.append("E14: the water tank stands %.0f m over the highest house it serves (want 28)" % head)
    ore = [c for c in L.get("connections", []) if c.get("carrier") == "conveyor"]
    if ore:
        ok = 0
        for c in ore:
            (ax, ay), (bx, by) = c["path"][0], c["path"][-1]
            za, zb_ = _g(Z, ax, ay), _g(Z, bx, by)
            inc = math.degrees(math.atan(abs(za - zb_) / max(1.0, math.hypot(bx - ax, by - ay))))
            ok += 1 if inc <= 15 else 0
        checks["E12 conveyor incline"] = ok / len(ore)
        notes.append("E12: %d of %d ore runs within 15 deg" % (ok, len(ore)))
    fuel = [b for bid, b in B.items() if bid in ("tank_farm", "fuel_depot")]
    homes = [b for bid, b in B.items() if sheets.get(bid, {}).get("kind") in ("house", "dorm")]
    if fuel and homes:
        dmin = min(math.hypot(f_["x"] - h_["x"], f_["y"] - h_["y"]) for f_ in fuel for h_ in homes) / M
        checks["E16 fuel set-back"] = float(np.clip(dmin / 100.0, 0, 1))
        notes.append("E16: fuel tanks %.0f m from the nearest home (want 100)" % dmin)
    R["engineer"] = {"score": round(float(np.mean(list(checks.values()))) if checks else 0.5, 3), "notes": notes, "veto": None,
                     "checks": {k: round(v, 2) for k, v in checks.items()}}

    # ---------------------------------------------------------------- the ARTIST
    notes = []
    try:
        imp, _ = metrics.imperfection(L)
        hier, th = metrics.hierarchy(L)
    except Exception as e:
        imp = hier = 0.0
        notes.append("metrics failed: %s" % e)
    notes.append("IMP %.2f, HIER %.2f" % (imp, hier))
    pts = [(b["x"], b["y"]) for bid, b in B.items() if sheets.get(bid, {}).get("kind") not in ("rig", "islet", "wreck", "barge")]
    cx, cy = np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts])
    spread = np.percentile([math.hypot(p[0] - cx, p[1] - cy) / M for p in pts], 80)
    compact = float(np.clip(1 - (spread - 250) / 300, 0, 1))
    notes.append("figure-ground: 80 %% of the buildings within %.0f m of the centre" % spread)
    R["artist"] = {"score": round(0.4 * imp + 0.35 * hier + 0.25 * compact, 3), "notes": notes, "veto": None}

    vetoes = [r["veto"] for r in R.values() if r["veto"]]
    sc = [max(1e-3, R[k]["score"]) for k in ("writer", "director", "engineer", "artist")]
    R["total"] = 0.0 if vetoes else round(float(np.prod(sc) ** (1 / len(sc))), 3)
    R["vetoes"] = vetoes
    return R


def report(R, label=""):
    lines = ["co-direction %s: %.3f%s" % (label, R["total"], ("  VETO: " + "; ".join(R["vetoes"])) if R["vetoes"] else "")]
    for k in ("writer", "director", "engineer", "artist"):
        lines.append("  %-8s %.2f  %s" % (k.upper(), R[k]["score"], " | ".join(R[k]["notes"])))
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(review(sys.argv[1], sys.argv[2])))
