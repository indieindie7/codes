r"""Co-direction: the town is designed by five collaborators who must agree (the user, 2026-10-08: "I want the town to
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
  LEVEL DESIGNER  how the town PLAYS (games/research_notes/Level design practices/report.md; Terrain generation methods
            for the pipeline/gameplay_terrain.md; the U2 mechanics measured in U2FairFights / U2Seven: GroundSpeed 263 UU/s
            = 5.3 m/s, NPC hit odds fall off past 1024 UU = 20 m, sight cap 6000 UU = 120 m, walkable floor ~45 deg)
              - LD1 the critical route (the spine, dock -> tower) walkable: grade <= 30 deg on the ground; < 80 % is a VETO
              - LD2 pacing (Bungie's 30 s of fun, the L4D build-up/relax): along the spine a beat (a junction, a landmark,
                the tower shown or lost) at least every 60 s of walking (315 m)
              - LD3 the weenie: from a station every 50 m of the walk, the tower OR a district landmark is in view
              - LD4 streets end on a view: each branch/lane's end looks at a building or toward the tower, never at nothing
              - LD5 arenas at the junctions: >= 2 entries, >= 3 cover pieces 10-40 m out, a high spot (+3 m), and the
                sightlines broken: 30-80 % of 16 rays blocked within 41 m (2048 UU: open ground past that is where the
                hitscan mercs win by volume of fire)
              - LD6 a local landmark per district: its tallest building >= 2x the district's median height
              - LD7 the Unreal 1 first-Skaarj recipe: somewhere on the walk a quiet stretch (25-60 s, no beat) that ends in
                a junction good enough to fight in (the space for a staged reveal)
  ARTIST    the drawings and the believability metrics
              - IMP (irregular, lived-in plots) and HIER (street hierarchy, loops, old core near the dock)
              - figure-ground grain: no building lost in the sea, the town compact (its built area within a radius)

    py tools/codirect.py <heightmap.bmp> <layout.json>            -> prints the five reviews
    (as a library: review(heightmap, layout) -> dict with writer/director/engineer/level/artist {score, notes, veto} + total)
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
SUN_AZ = 136.0            # where the sun IS (lowsun.py's az): the light travels toward SUN_AZ + 180
SUN_EL = 10.0             # the baked dusk sun's height (town.py passes this to lowsun.py; the director wants 6-9)
# the views the director scores the light in (redesign 2026-10-09, director s. 0.1, F1/F4/F5): each has a job.
#   window  - F1, the command room (yaw 300): ownership; the sun is behind the viewer (front light) and the job is
#             the tower's shadow lying over the housing while the hero stays lit
#   deck    - F4, the overhang deck (yaw ~171): back light, silhouettes and rim edges
#   catwalk - F5, the peak frame (yaw ~136-171): back light
VIEWS = (("window", LOOK, "shadow"), ("deck", 171.0, "back"), ("catwalk", 153.0, "back"))


def _cutfill_grade():
    """the one road-grade cap: terrain_cutfill.py's MAX_GRADE default (the grade it actually builds). It is read from
    that file's source because terrain_cutfill runs on import; fall back to its current value"""
    import re
    try:
        src = open(os.path.join(HERE, "terrain_cutfill.py"), encoding="utf-8").read()
        return float(re.search(r'MAX_GRADE\s*=\s*float\(o\.get\("max_grade",\s*([0-9.]+)\)\)', src).group(1))
    except (OSError, AttributeError, ValueError):
        return 0.12


MAX_GRADE = _cutfill_grade()
ROAD_GRADE = {"spine": MAX_GRADE, "branch": MAX_GRADE, "lane": 0.15}   # rise/run per class (paths: not checked)
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


def hero_id(B, sheets):
    """the parti's hero (binder/parti.json "hero"; liandri_tower since binder 1940260) when the layout placed it and its
    sheet has a size, else the Authority "tower" (its placement is a placeholder: a missing hero never vetoes)"""
    h = PARTI.get("hero", "tower")
    return h if (h in B and len(sheets.get(h, {}).get("size") or ()) > 2) else "tower"


def _boxes(L, sheets, skip=()):
    out = []
    for bid, b in L["buildings"].items():
        s = sheets.get(bid)
        if not s or "size" not in s or bid == "tower" or bid in skip or s["kind"] in ("pad", "dock", "jetty", "rig", "islet", "barge", "wreck"):
            continue
        r = max(s["size"][0], s["size"][1]) * M * 0.5
        out.append((b["x"], b["y"], r, b.get("z", 0) + (s["size"][2] if len(s["size"]) > 2 else 6) * M))
    return out


def serial(Z, L, sheets, step_m=35.0):
    """the walk dock -> tower: per station, is the hero's top seen (terrain + buildings as round prisms)? The walk
    runs along the spine to the Authority tower; the target is the parti's hero (hero_id)"""
    sp = L.get("spine") or []
    T0 = L["buildings"].get("tower")
    if not sp or not T0:
        return []
    hid = hero_id(L["buildings"], sheets)
    T = L["buildings"][hid]
    tz = T.get("z", _g(Z, T["x"], T["y"])) + sheets[hid]["size"][2] * M
    boxes = _boxes(L, sheets, skip=(hid,))
    acc, k_t = [0.0], min(range(len(sp)), key=lambda k: math.dist(sp[k], (T0["x"], T0["y"])))
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


WALK_MS = 263.0 / M                       # U2 GroundSpeed in m/s
BEAT_S = 60.0                              # the longest walk without a beat
FIGHT_M = 2048.0 / M                       # past this, open ground belongs to the hitscan mercs


def _height(bid, b, sheets):
    s = sheets.get(bid, {})
    return (s["size"][2] if len(s.get("size", [])) > 2 else 6.0)


def _seen(Z, boxes, p, tx, ty, tz, skip=None):
    e = max(_g(Z, *p), SEA_Z) + 1.6 * M
    for u in np.linspace(0.03, 0.97, 40):
        q = (p[0] + (tx - p[0]) * u, p[1] + (ty - p[1]) * u)
        ray = e + (tz - e) * u
        if _g(Z, *q) > ray:
            return False
        for bx, by, br, bt in boxes:
            if (bx, by) != skip and math.hypot(q[0] - bx, q[1] - by) < br and bt > ray:
                return False
    return True


def level_designer(Z, L, sheets, walk):
    """how the town plays: the critical route, pacing, wayfinding, arenas (see the module notes, LD1-LD7)"""
    notes, checks, veto = [], {}, None
    B = L["buildings"]
    sp = L.get("spine") or []
    T = B.get("tower")
    if len(sp) < 2 or not T:
        return {"score": 0.0, "notes": ["no spine or no tower"], "veto": "no critical route", "checks": {}}
    boxes = _boxes(L, sheets)
    # LD1 the critical route: along-path grade on the ground
    tot = ok = 0.0
    for a, b in zip(sp[:-1], sp[1:]):
        d = math.dist(a, b)
        if d < 1:
            continue
        g = math.degrees(math.atan(abs(max(_g(Z, *b), SEA_Z) - max(_g(Z, *a), SEA_Z)) / d))
        tot += d
        ok += d if g <= 30 else 0
    checks["LD1 route walkable"] = ok / tot if tot else 0.0
    if checks["LD1 route walkable"] < 0.8:
        veto = "the critical route can't be walked (%.0f %% over 30 deg)" % (100 * (1 - checks["LD1 route walkable"]))
    notes.append("LD1: %.0f %% of the spine walkable (<= 30 deg)" % (100 * checks["LD1 route walkable"]))
    # the spine's arc length, and where things project onto it
    acc = [0.0]
    for a, b in zip(sp[:-1], sp[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    k_t = min(range(len(sp)), key=lambda k: math.dist(sp[k], (T["x"], T["y"])))
    s_end = acc[k_t]

    def s_of(x, y):
        k = min(range(k_t + 1), key=lambda k: math.dist(sp[k], (x, y)))
        return acc[k], math.dist(sp[k], (x, y))
    # junctions: ends of other roads (not paths) that touch another road
    roads, cls = L.get("roads", []), L.get("road_class") or ["spine"] + ["branch"] * (len(L.get("roads", [])) - 1)
    junc = []
    for i, (r, c) in enumerate(zip(roads, cls)):
        if c == "path" or c == "spine" or len(r) < 2:
            continue
        for end in (r[0], r[-1]):
            for j, r2 in enumerate(roads):
                if j != i and cls[j] != "path" and min(math.dist(end, q) for q in r2) < 15 * M:
                    if all(math.dist(end, (jx, jy)) > 30 * M for jx, jy, _ in junc):
                        legs = 0
                        for k, r3 in enumerate(roads):
                            if cls[k] == "path" or min(math.dist(end, q) for q in r3) >= 15 * M:
                                continue
                            legs += 1 if min(math.dist(end, r3[0]), math.dist(end, r3[-1])) < 15 * M else 2
                        junc.append((end[0], end[1], legs))
                    break
    # LD2 pacing: beats along the spine
    beats = [0.0, s_end]
    for jx, jy, _ in junc:
        s_, d_ = s_of(jx, jy)
        if d_ < 20 * M and s_ <= s_end:
            beats.append(s_)
    hts = {bid: _height(bid, b, sheets) for bid, b in B.items()}
    for bid, b in B.items():
        if hts[bid] >= 20 and sheets.get(bid, {}).get("kind") not in ("rig", "islet", "mast"):
            s_, d_ = s_of(b["x"], b["y"])
            if d_ < 40 * M and s_ <= s_end:
                beats.append(s_)
    st = 35.0 * M
    for k in range(1, len(walk)):
        if walk[k] != walk[k - 1]:
            beats.append(k * st)
    beats = sorted(beats)
    gaps = [(b2 - b1) / M / WALK_MS for b1, b2 in zip(beats[:-1], beats[1:])]
    longest = max(gaps) if gaps else 0
    checks["LD2 pacing"] = float(np.clip(BEAT_S / max(longest, 1e-3), 0, 1))
    notes.append("LD2: %d beats over %.0f s of walking, longest quiet %.0f s (want <= 60)" % (len(beats) - 2, s_end / M / WALK_MS, longest))
    # LD3 the weenie: the tower or a district landmark in view every 50 m
    marks = {}
    for bid, b in B.items():
        lay = b.get("layer", "-")
        if bid != "tower" and sheets.get(bid, {}).get("kind") not in ("rig", "islet", "wreck", "barge", "pad", "dock", "jetty"):
            if lay not in marks or hts[bid] > hts[marks[lay]]:
                marks[lay] = bid
    targets = [(T["x"], T["y"], T.get("z", _g(Z, T["x"], T["y"])) + _height("tower", T, sheets) * M)]
    hid = hero_id(B, sheets)
    if hid != "tower":                        # the parti's hero is a weenie too (liandri_tower)
        targets.append((B[hid]["x"], B[hid]["y"], _g(Z, B[hid]["x"], B[hid]["y"]) + _height(hid, B[hid], sheets) * M))
    targets += [(B[m]["x"], B[m]["y"], _g(Z, B[m]["x"], B[m]["y"]) + hts[m] * M) for m in marks.values()]
    seen = n = 0
    s_ = 0.0
    while s_ <= s_end:
        k = max(0, min(len(sp) - 2, int(np.searchsorted(acc, s_) - 1)))
        t = (s_ - acc[k]) / max(1e-6, acc[k + 1] - acc[k])
        p = (sp[k][0] + (sp[k + 1][0] - sp[k][0]) * t, sp[k][1] + (sp[k + 1][1] - sp[k][1]) * t)
        n += 1
        seen += 1 if any(_seen(Z, boxes, p, tx, ty, tz, skip=(tx, ty)) for tx, ty, tz in targets) else 0
        s_ += 50 * M
    checks["LD3 weenie"] = seen / max(1, n)
    notes.append("LD3: tower or a landmark in view at %d of %d stations" % (seen, n))
    # LD4 streets end on a view: a landmark in a +-20 deg cone within 400 m, or a vista over the sea within 200 m
    lms = targets + [(b["x"], b["y"], 0) for bid, b in B.items() if b.get("interest", 0) >= 0.8 and bid != "tower"]
    ends = good = 0
    done = []
    for r, c in zip(roads, cls):
        if c not in ("branch", "lane") or len(r) < 2 or r in done:
            continue
        done.append(r)
        for (ax, ay), (bx, by) in ((r[-2], r[-1]), (r[1], r[0])):
            d = math.hypot(bx - ax, by - ay)
            if d < 1:
                continue
            ux, uy = (bx - ax) / d, (by - ay) / d
            ends += 1
            hd = math.atan2(uy, ux)
            lm = any(0 < math.hypot(x - bx, y - by) < 400 * M and
                     abs((math.degrees(math.atan2(y - by, x - bx) - hd) + 180) % 360 - 180) < 20 for x, y, _ in lms)
            sea = any(_g(Z, bx + ux * r_ * M, by + uy * r_ * M) < SEA_Z for r_ in range(20, 200, 10))
            good += 1 if lm or sea else 0
    checks["LD4 street ends"] = good / ends if ends else 0.5
    notes.append("LD4: %d of %d street ends look at a landmark or the sea" % (good, ends))
    # LD5 arenas at the junctions
    ar = []
    for jx, jy, legs in junc:
        z0 = max(_g(Z, jx, jy), SEA_Z)
        cover = sum(1 for x, y, rr, _ in boxes if 10 * M < math.hypot(x - jx, y - jy) < 40 * M)
        high = max(_g(Z, jx + 40 * M * math.cos(a), jy + 40 * M * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12)) > z0 + 3 * M
        blocked = 0
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            e = z0 + 1.6 * M
            for rr_ in np.arange(4, FIGHT_M, 3):
                q = (jx + rr_ * M * math.cos(a), jy + rr_ * M * math.sin(a))
                if _g(Z, *q) > e + 0.4 * M or _g(Z, *q) < SEA_Z or any(math.hypot(q[0] - x, q[1] - y) < r2 for x, y, r2, _ in boxes):
                    blocked += 1
                    break
        fb = blocked / 16
        sub = [legs >= 2, cover >= 3, high, 0.3 <= fb <= 0.8]
        ar.append((sum(sub) / 4.0, jx, jy, cover, fb, high))
    checks["LD5 arenas"] = float(np.mean([a[0] for a in ar])) if ar else 0.0
    best = max(ar) if ar else None
    notes.append("LD5: %d junctions, mean arena %.2f%s" % (len(ar), checks["LD5 arenas"],
                 (" (best: %d cover, %.0f %% rays blocked, high spot %s)" % (best[3], 100 * best[4], "yes" if best[5] else "no")) if best else ""))
    # LD6 a landmark per district
    okd = 0
    for lay, m in marks.items():
        hs = sorted(hts[bid] for bid, b in B.items() if b.get("layer", "-") == lay)
        okd += 1 if hts[m] >= 2 * hs[len(hs) // 2] else 0
    checks["LD6 district landmarks"] = okd / max(1, len(marks))
    notes.append("LD6: %d of %d districts have a landmark 2x their median (%s)" % (okd, len(marks), ", ".join("%s: %s" % kv for kv in marks.items())))
    # LD7 the first-encounter space: a quiet stretch ending in a fightable junction
    quiet = 0.0
    for b1, b2, g in zip(beats[:-1], beats[1:], gaps):
        if 25 <= g <= 60:
            for a in ar:
                s2, d2 = s_of(a[1], a[2])
                if a[0] >= 0.75 and abs(s2 - b2) < 20 * M and d2 < 20 * M:
                    quiet = 1.0
    checks["LD7 reveal space"] = quiet
    notes.append("LD7: %s" % ("a quiet stretch ends in a fightable junction (the reveal)" if quiet else "no quiet stretch leads into a good arena"))
    return {"score": round(float(np.mean(list(checks.values()))), 3), "notes": notes, "veto": veto,
            "checks": {k: round(v, 2) for k, v in checks.items()}}


def light_off(view_yaw):
    """the angle between a view's direction and the sun's position: 0-60 back light (silhouettes, rim), 60-120 side
    light (form), 120-180 front light (flat; everything shown, nothing hidden)"""
    return abs((SUN_AZ - view_yaw + 180) % 360 - 180)


def light_kind(off):
    return "back light" if off <= 60 else ("side light" if off <= 120 else "front light")


def back_score(off):
    """1 for back light, 0.5 for side light at 120, 0 for the sun straight behind the viewer"""
    return 1.0 if off <= 60 else (1.0 - 0.5 * (off - 60) / 60.0 if off <= 120 else max(0.0, 0.5 - 0.5 * (off - 120) / 60.0))


def in_tower_shadow(Z, T, sheets, x, y, z, tid="tower"):
    """is the point (x, y, z) in the tower's shadow? march toward the sun (SUN_AZ, SUN_EL) and see if the ray passes
    through the tower tid (a round prism of its sheet's footprint) under its top"""
    tsz = sheets[tid]["size"]
    tr = max(tsz[0], tsz[1]) * M * 0.5
    tz = T.get("z", _g(Z, T["x"], T["y"])) + tsz[2] * M
    a, e = math.radians(SUN_AZ), math.tan(math.radians(SUN_EL))
    ux, uy = math.cos(a), math.sin(a)
    # the ray's closest approach to the tower axis
    t = (T["x"] - x) * ux + (T["y"] - y) * uy
    if t <= 0:
        return False
    if math.hypot(x + ux * t - T["x"], y + uy * t - T["y"]) > tr:
        return False
    return z + e * max(0.0, t - tr) < tz


def lit_by_sun(Z, x, y, z, max_r=60000.0):
    """no terrain between the point and the low sun"""
    a, e = math.radians(SUN_AZ), math.tan(math.radians(SUN_EL))
    for r in np.arange(4 * CELL, max_r, CELL):
        if _g(Z, x + r * math.cos(a), y + r * math.sin(a)) > z + e * r:
            return False
    return True


def review(heightmap, layout_path, graded=None):
    """graded: the cut-and-filled heightmap (isl_ec.bmp) when there is one; the engineer's road grades, ore line
    and quay are read on it (what ships). A heightmap named *_ec.bmp is taken as graded itself."""
    Z = _Z(heightmap)
    if graded is None and os.path.basename(heightmap).lower().endswith("_ec.bmp"):
        graded = heightmap
    ZG = _Z(graded) if graded else None
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
    hid = hero_id(B, sheets)                  # "the company holds the high ground": the parti's hero
    tower_g = _g(Z, B[hid]["x"], B[hid]["y"]) if hid in B else 0
    works = [b for bid, b in B.items() if sheets.get(bid, {}).get("kind") in ("hall", "tank", "silo", "cooling")]
    works_g = np.mean([_g(Z, b["x"], b["y"]) for b in works]) if works else tower_g
    high = float(np.clip((tower_g - works_g) / M / 20.0, 0, 1))          # 20 m over the works = full marks
    notes.append("high ground: %s stands %.0f m over the works" % (hid, (tower_g - works_g) / M))
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
    # the background: the sea horizon counts only when the frame shows it, best on the upper third (director s. 0.2)
    hv = 0.5 - 0.5 * math.tan(math.radians(-compose.PITCH)) / math.tan(math.radians(compose.HALF_H))
    bg = float(np.clip(1 - abs(hv - 1 / 3) / 0.17, 0, 1)) if 0 <= hv <= 1 else 0.0
    layers = (0.4 if mg else 0) + (0.4 if gap else 0) + 0.2 * bg
    notes.append("layers: midground land %s, gap of air %s, horizon %s" % (
        "yes" if mg else "NO", ("at %d m" % gap_r) if gap else "NO", ("at v=%.2f" % hv) if 0 <= hv <= 1 else "OUT OF FRAME"))
    # the light, per view (director s. 0.1): the decks and the catwalk want back light; the window is front-lit by
    # design (the sun behind the viewer), and its job is the tower's shadow over the housing with the hero lit
    lparts = []
    for vname, vyaw, job in VIEWS:
        off = light_off(vyaw)
        if job == "back":
            lparts.append(back_score(off))
            notes.append("light %s (yaw %.0f): the sun %.0f deg off, %s" % (vname, vyaw, off, light_kind(off)))
            continue
        tid = hero_id(B, sheets)              # "the town lives in its shadow": the company's tower
        T = B.get(tid)
        housing = [(bid, b) for bid, b in B.items() if not b.get("abandoned") and (
            sheets.get(bid, {}).get("kind") == "dorm" or bid.startswith(("shanty", "old_camp")))]
        hero = fr.get("hero")
        if not T or tid not in sheets:
            lparts.append(0.5)
            continue
        shad = [bid for bid, b in housing if in_tower_shadow(Z, T, sheets, b["x"], b["y"], max(_g(Z, b["x"], b["y"]), SEA_Z) + 3 * M, tid)]
        frac = len(shad) / max(1, len(housing))
        hero_lit = 0.5
        if hero and hero in B:
            h = B[hero]
            hz = max(_g(Z, h["x"], h["y"]), SEA_Z) + 0.75 * sheets[hero]["size"][2] * M
            hero_lit = 1.0 if ((hero == tid or not in_tower_shadow(Z, T, sheets, h["x"], h["y"], hz, tid)) and lit_by_sun(Z, h["x"], h["y"], hz)) else 0.0
        lparts.append(0.5 * min(1.0, frac / 0.3) + 0.5 * hero_lit)
        notes.append("light %s (yaw %.0f): the sun %.0f deg off, %s; %s's shadow (el %.0f) over %d of %d homes%s, hero %s" % (
            vname, vyaw, off, light_kind(off), tid, SUN_EL, len(shad), len(housing), (" (" + ", ".join(shad[:4]) + ")") if shad else "",
            "lit" if hero_lit == 1.0 else ("in shadow" if hero_lit == 0.0 else "-")))
    light = float(np.mean(lparts)) if lparts else 0.5
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
    notes, checks, warns = [], {}, []
    WIND = (0.83, -0.55)
    ZE = ZG if ZG is not None else Z          # the ground that ships (cut and filled) when there is one
    gname = "graded" if ZG is not None else "natural (not graded yet)"
    cls = L.get("road_class") or (["spine"] + ["branch"] * (len(L.get("roads", [])) - 1))
    over = tot = 0.0
    for r, c in zip(L.get("roads", []), cls):
        if c == "path":
            continue
        cap = ROAD_GRADE.get(c, ROAD_GRADE["lane"])     # one cap table, shared with terrain_cutfill's MAX_GRADE
        for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
            d = math.hypot(bx - ax, by - ay)
            if d < 1:
                continue
            g = abs(max(_g(ZE, bx, by), SEA_Z) - max(_g(ZE, ax, ay), SEA_Z)) / d
            tot += d
            over += d if g > cap else 0.0
    checks["E1 road grades"] = 1.0 - (over / tot if tot else 0.0)
    notes.append("E1: %.0f %% of the road length climbs over its class's grade cap (%.0f %% spine/branch, %.0f %% lane; %s ground)" % (
        100 * (1 - checks["E1 road grades"]), 100 * ROAD_GRADE["spine"], 100 * ROAD_GRADE["lane"], gname))
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
    # E12 the ore line: each run must FALL along its direction (provider -> consumer, the process order of systems.py)
    # and stay within 15 deg; an uphill run fails however gentle (the engineer: Cine8's silos -> halls rose 8 m)
    ore = [c for c in L.get("connections", []) if c.get("carrier") == "conveyor" and c.get("from") in B and c.get("to") in B]
    if ore:
        ok, up = 0, []
        for c in ore:
            fa, tb = B[c["from"]], B[c["to"]]
            za, zb_ = max(_g(ZE, fa["x"], fa["y"]), SEA_Z), max(_g(ZE, tb["x"], tb["y"]), SEA_Z)
            inc = math.degrees(math.atan(abs(za - zb_) / max(1.0, math.hypot(tb["x"] - fa["x"], tb["y"] - fa["y"]))))
            falls = zb_ <= za + 0.5 * M
            ok += 1 if (falls and inc <= 15) else 0
            if not falls:
                up.append("%s->%s +%.1f m" % (c["from"], c["to"], (zb_ - za) / M))
        checks["E12 ore downhill"] = ok / len(ore)
        notes.append("E12: %d of %d ore runs fall toward the port within 15 deg%s" % (ok, len(ore), ("; uphill: " + ", ".join(up[:4])) if up else ""))
    # E16 fuel: only real fuel stores (fuel_depot, any sheet of kind fuel) - the tank farm holds concentrate; homes are
    # dwellings (kind house/dorm) minus the social places and the altar, plus the shanty and the old camp (engineer E16')
    fuel = [b for bid, b in B.items() if bid == "fuel_depot" or sheets.get(bid, {}).get("kind") == "fuel"]
    homes = [(bid, b) for bid, b in B.items() if not b.get("abandoned") and (
        bid.startswith(("shanty", "old_camp")) or (sheets.get(bid, {}).get("kind") in ("house", "dorm") and
                                                   sheets.get(bid, {}).get("function") not in ("social", "altar", "clinic")))]
    if fuel and homes:
        dmin, near = min((math.hypot(f_["x"] - h_["x"], f_["y"] - h_["y"]) / M, hid) for f_ in fuel for hid, h_ in homes)
        checks["E16 fuel set-back"] = float(np.clip(dmin / 100.0, 0, 1))
        notes.append("E16: the fuel store %.0f m from the nearest home, %s (want 100)" % (dmin, near))
    # warnings (not scored yet, never a veto): the engineer's cheap new checks that need only the layout
    dk = B.get("dock")
    if dk:                                    # E23 the quay deck 1.5-4 m over the sea
        qh = (max(_g(ZE, dk["x"], dk["y"]), SEA_Z) - SEA_Z) / M
        if not 1.5 <= qh <= 4.0:
            warns.append("E23 quay deck %.1f m over the sea (want 1.5-4)" % qh)
    for bid, b in B.items():                  # E25 a rig is supplied by boat from the dock or the boat landing (3 km)
        if sheets.get(bid, {}).get("kind") == "rig" and not bid.startswith("wellhead") and not b.get("abandoned") and bid != "dead_rig":
            ports = [B[p] for p in ("dock", "boat_landing") if p in B]
            dm = min((math.hypot(p["x"] - b["x"], p["y"] - b["y"]) / M for p in ports), default=None)
            if dm is None or dm > 3000:
                warns.append("E25 %s: no dock or landing within 3 km by sea%s" % (bid, (" (%.0f m)" % dm) if dm else ""))
    notes += ["WARN " + w for w in warns]
    R["engineer"] = {"score": round(float(np.mean(list(checks.values()))) if checks else 0.5, 3), "notes": notes, "veto": None,
                     "checks": {k: round(v, 2) for k, v in checks.items()}, "warnings": warns}

    # ---------------------------------------------------------------- the LEVEL DESIGNER
    R["level"] = level_designer(Z, L, sheets, walk)

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
    sc = [max(1e-3, R[k]["score"]) for k in ("writer", "director", "engineer", "level", "artist")]
    R["total"] = 0.0 if vetoes else round(float(np.prod(sc) ** (1 / len(sc))), 3)
    R["vetoes"] = vetoes
    return R


def report(R, label=""):
    lines = ["co-direction %s: %.3f%s" % (label, R["total"], ("  VETO: " + "; ".join(R["vetoes"])) if R["vetoes"] else "")]
    for k in ("writer", "director", "engineer", "level", "artist"):
        lines.append("  %-8s %.2f  %s" % (k.upper(), R[k]["score"], " | ".join(R[k]["notes"])))
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(review(sys.argv[1], sys.argv[2])))
