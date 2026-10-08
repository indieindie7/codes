r"""The creative team reviews an EXISTING Unreal II map (the user, 2026-10-08: "a pass on all Sanctuary maps, with our
creative team initially scoring it and then helping redesign"). The same five co-directors as the Avalon town
generator (U2Avalon/tools/codirect.py), with their rules turned from a generated town to a built level:

  WRITER          the story the place tells (U2Seven/SANCTUARY_REDESIGN.md: "the colony is silent, the colonists are
                  dead where they stood"; the Unreal 1 first-Skaarj recipe; Smith & Worch "what happened here?")
                    W1 evidence before the first fight (bodies, blood, scares) >= 3
                    W2 bodies that tell something: near a door, a console/light, a weapon or another body (they fled,
                       they hid, they fought, they died together)
                    W3 the story beats spread along the walk (scenes, objectives, scripted scares): none quiet > 90 s
                    W4 the gore serves the story: every body has blood near it (the gore pass's first job)
  DIRECTOR        light and staging (cinematography report; Level design practices s.2)
                    D1 compression and release: the light level along the walk alternates (dark/bright windows)
                    D2 the reveal: the first enemies stand brighter than the approach to them
                    D3 the palette: lights in the brief's families (rust/amber, red, cold white)
                    D4 darkness: 20-50 % of the walk in low light (horror needs the dark, not all of it)
  ENGINEER        does the place work and hold together
                    E1 water: nav points in the water volumes (no nav = the AI can't follow you in) + the volume physics
                    E2 lights have sources: a static mesh within 160 UU of each light (no light from nowhere)
                    E3 dead ends off the route are few (degree-1 nav points)
  LEVEL DESIGNER  how it plays (Level design practices; gameplay_terrain.md; U2 GroundSpeed 263 UU/s)
                    L1 the critical route exists (player start -> the LevelChange) - else VETO
                    L2 pacing: a beat (enemy, body, trigger, pickup, door) at least every 60 s of walking
                    L3 arenas: each enemy group has >= 3 cover meshes 256-1024 UU out and >= 2 ways in
                    L4 recovery: health within 30 s of walking after each fight
                    L5 the first-encounter recipe: a quiet stretch (>= 20 s, no enemies) right before the first fight
  ARTIST          the look
                    A1 art fatigue: no single static mesh > 12 % of all placed meshes
                    A2 texture variety per zone (distinct brush textures), and no zone with 1
                    A3 hero details: zones with at least one mesh used only there

    py mapreview.py <map.t3d> [out_dir] [scenes=U2Sanctuary.ini]   -> <map>_review.md/.png, <map>_redesign.json
                                     (with scenes=: the map as the SanctuaryDirector redesigns it -> <map>_after_*;
                                      gm=<game>/System/U2GM.ini: the game master's journal applied too)

The T3D is an EDIT COPY of all actors from UnrealEd (MAP EXPORT writes nothing for the Sanctuary maps), e.g.
Documents\U2_research\sanctuary\M08A1.t3d. The redesign json is the team's proposals with world positions: the
gore vignettes (pool / spray / drag trail / smear per body, foreshadowing marks before the first fight), lights to
add or dim, cover to add. Nothing is placed in water (ADVENT-GORE-HANDOFF.md: projectors land on floors under water).
"""
import heapq, json, math, os, re, sys
from collections import Counter, defaultdict

import numpy as np

SPEED = 263.0                     # U2 GroundSpeed, UU/s
NAV = ("PathNode", "PlayerStart", "SpawnPoint", "PatrolPoint", "PatrolPointRed", "PatrolPointBlue", "PatrolPointGreen",
       "InventorySpot", "AlternatePath", "AutoLadder")
ENEMY = re.compile(r"U2(Izarian|Skaarj\w*|Araknid\w*|Aida\w*|Merc\w*|Drakk\w*|Strider\w*)$")   # (cockroaches are ambience: 1 health)
COLONIST = re.compile(r"U2(Civilian\w*|Colonist\w*)$")
PICKUP = re.compile(r"(Health\w*|ammo\w+|weapon\w+|Energy\w*|Shield\w*)$")
BLOOD = re.compile(r"blood|gore|gut|dead|kill|death|stab|scream", re.I)
SCARE = re.compile(r"scare|noise|growl|creak|laugh|something|howl|mating|scurry|breaking|amb", re.I)


def parse(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for m in re.finditer(r"Begin Actor Class=(\w+) Name=(\w+)(.*?)\nEnd Actor", t, re.S):
        cls, name, body = m.group(1), m.group(2), m.group(3)
        head = re.sub(r"Begin Brush.*?End Brush", "", body, flags=re.S)
        a = {"cls": cls, "name": name}
        loc = re.search(r"\n\s*Location=\(([^)]*)\)", head)
        p = dict(re.findall(r"([XYZ])=([-\d.]+)", loc.group(1))) if loc else {}
        a["p"] = np.array([float(p.get("X", 0)), float(p.get("Y", 0)), float(p.get("Z", 0))])
        for k in ("Tag", "Event", "CommandFileName", "URL", "StaticMesh", "Mesh", "LightBrightness", "LightHue",
                  "LightSaturation", "LightRadius", "Prototype", "Capacity", "CsgOper", "Gravity", "FluidFriction", "bHidden", "Group"):
            mm = re.search(r"\n\s*%s=(.*)" % k, head)
            if mm:
                a[k] = mm.group(1).strip().strip('"')
        z = re.search(r"ZoneNumber=(\d+)", head)
        a["zone"] = int(z.group(1)) if z else -1
        if "Begin Polygon" in body:
            verts = np.array([[float(v) for v in vv] for vv in re.findall(r"Vertex\s+([-+\d.]+),([-+\d.]+),([-+\d.]+)", body)])
            pre = re.search(r"PrePivot=\(([^)]*)\)", head)
            pp = dict(re.findall(r"([XYZ])=([-\d.]+)", pre.group(1))) if pre else {}
            pv = np.array([float(pp.get("X", 0)), float(pp.get("Y", 0)), float(pp.get("Z", 0))])
            if len(verts):
                a["bbox"] = (verts.min(0) - pv + a["p"], verts.max(0) - pv + a["p"])
            a["tex"] = re.findall(r"Begin Polygon Texture=(\S+)", body)
        out.append(a)
    return out


def light_level(lights, q):
    """a rough brightness at q from the placed lights (UE2: world radius ~ 25 * (LightRadius + 1) UU)"""
    s = 0.0
    for L in lights:
        r = 25.0 * (float(L.get("LightRadius", 64)) + 1)
        d = np.linalg.norm(L["p"] - q)
        if d < r:
            s += float(L.get("LightBrightness", 64)) * (1 - d / r) ** 2
    return s


def inside(b, q, pad=0):
    return all(b[0][i] - pad <= q[i] <= b[1][i] + pad for i in range(3))


def overlay(A, scenes_ini, mapname):
    """the redesign as placed by U2Sanctuary's SanctuaryDirector (U2Sanctuary.ini Scenes=...), added as actors so the
    team can score the map after it: blood marks count as blood, key lights as lights, cover as three crates"""
    added = 0
    for m in re.finditer(r'Scenes=\(Map="([^"]+)",Kind="([^"]+)",At=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)', open(scenes_ini).read()):
        if m.group(1).upper() != mapname.upper():
            continue
        k, p = m.group(2), np.array([float(m.group(3)), float(m.group(4)), float(m.group(5))])
        if k == "keylight":
            A.append({"cls": "Light", "name": "SanctuaryLight%d" % added, "p": p + [0, 0, 170], "zone": -1, "LightBrightness": "150",
                      "LightRadius": "24", "LightHue": "24", "LightSaturation": "110"})
        elif k == "cover":
            for a in (0, 2.1, 4.2):
                A.append({"cls": "StaticMeshActor", "name": "SanctuaryCover%d" % added, "zone": -1,
                          "p": p + [400 * math.cos(a), 400 * math.sin(a), 0], "StaticMesh": "SanctuaryCover"})
        else:
            A.append({"cls": "Decal", "name": "SanctuaryBlood%d" % added, "p": p, "zone": -1, "Tag": "blood_" + k})
        added += 1
    return added


def gm_overlay(A, gm_ini, mapname):
    """the game master's journal (U2GM.ini, written by the game) for this map family, applied the way GMMaster
    replays it: hide/place a map actor by name, mesh = a placed static mesh, light = a light, gore = blood.
    Returns the counts and the GM's draw notes (routes and areas the GM drew for the level team)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "U2GM", "tools"))
    import gm_commit
    text = gm_commit.read_text(gm_ini)
    fam = mapname.lower()
    n = Counter()
    by_name = {a["name"].lower(): a for a in A}
    for slot, line in gm_commit.journal(text, fam):
        w = line.split()
        k = w[0].lower()
        try:
            if k == "hide" and w[1].lower() in by_name:
                A.remove(by_name.pop(w[1].lower()))
            elif k == "place" and w[1].lower() in by_name:
                by_name[w[1].lower()]["p"] = np.array([float(w[2]), float(w[3]), float(w[4])])
            elif k == "mesh":
                A.append({"cls": "StaticMeshActor", "name": "mesh#%d" % slot, "zone": -1, "StaticMesh": w[1],
                          "p": np.array([float(w[2]), float(w[3]), float(w[4])])})
            elif k == "light":
                g = lambda i, d: w[i] if len(w) > i else d
                A.append({"cls": "Light", "name": "light#%d" % slot, "zone": -1, "p": np.array([float(w[1]), float(w[2]), float(w[3])]),
                          "LightBrightness": g(4, "150"), "LightHue": g(5, "24"), "LightSaturation": g(6, "110"), "LightRadius": g(7, "24")})
            elif k == "gore":
                A.append({"cls": "Decal", "name": "gore#%d" % slot, "zone": -1, "Tag": "blood_" + w[1],
                          "p": np.array([float(w[2]), float(w[3]), float(w[4])])})
            else:
                continue
            n[k] += 1
        except (IndexError, ValueError):
            n["bad"] += 1
    _, arrays = gm_commit.section(text, "U2GM.GMMaster")
    draws = [v for v in arrays.get("draws", {}).values() if v.lower().startswith("@" + fam + " draw")]
    return n, draws


def review(path, scenes=None, gm=None):
    A = parse(path)
    name = os.path.splitext(os.path.basename(path))[0]
    if scenes:
        overlay(A, scenes, name)
    gm_note = None
    if gm:
        gm_note = gm_overlay(A, gm, name)
    by = defaultdict(list)
    for a in A:
        by[a["cls"]].append(a)
    nav = [a for a in A if a["cls"] in NAV]
    lights = [a for a in A if a["cls"] in ("Light", "TriggerLight", "Spotlight") and "LightBrightness" in a]
    smesh = [a for a in A if a["cls"] == "StaticMeshActor"]
    enemies = [a for a in A if ENEMY.match(a["cls"])] + [a for a in by["PawnFactory"] if "Prototype" in a and ENEMY.search(a["Prototype"].split(".")[-1].rstrip("'"))]
    movie = lambda a: a.get("CommandFileName", "").lower().startswith("movie")
    bodies = [a for a in A if COLONIST.match(a["cls"]) and not movie(a)]
    pickups = [a for a in A if PICKUP.match(a["cls"])]
    health = [a for a in pickups if a["cls"].startswith("Health")]
    water = [a for a in A if a["cls"] == "WaterVolume" and "bbox" in a]
    blood = [a for a in A if a["cls"] in ("ParticleSalamander", "AlarmTrigger", "U2Dispatcher", "Emitter", "Decal") and
             BLOOD.search(a.get("Tag", "") + " " + a.get("Event", ""))]
    scares = [a for a in A if a["cls"] in ("AmbientSound", "AlarmTrigger", "U2Dispatcher", "ParticleSalamander", "Trigger") and
              SCARE.search(a.get("Tag", "") + " " + a.get("Event", ""))]
    story = by["SceneManager"] + by["ObjectiveEvent"] + by["LookTarget"]
    doors = by["Mover"] + by["Door"] + by["DoorMover"]
    exits = [a for a in by["LevelChange"] if a.get("URL", "").lower() not in ("sidea", "sideb")]
    start = (by["PlayerStart"] or nav)[0]

    # ---- the nav graph: the game's own ReachSpecs from a U2Pilot "hub zones" dump (<map>_zones.log beside the T3D)
    # when there is one; else a guess (an EDIT COPY has no ReachSpecs): link points that are close and level enough
    G = defaultdict(list)
    zlog = os.path.splitext(path)[0] + "_zones.log"
    if os.path.exists(zlog):
        zt = open(zlog, encoding="latin1").read()
        nn = re.findall(r"Zones: nav (-?\d+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (\w+) (\w+)", zt)
        nav = [{"cls": c, "name": n, "zone": int(z), "p": np.array([float(x), float(y), float(zz)])} for z, x, y, zz, c, n in nn]
        idx = {a["name"]: i for i, a in enumerate(nav)}
        for u, v, w in re.findall(r"Zones: edge (\w+) (\w+) (\d+)", zt):
            if u in idx and v in idx:
                G[idx[u]].append((idx[v], float(w)))
        GRAPH = "the game's ReachSpecs (%s)" % os.path.basename(zlog)
    P = np.array([a["p"] for a in nav])
    real = bool(G)
    if not real:
        GRAPH = "guessed links (no zones log)"
    # guessed links, also over the real graph at 1.5x cost: ReachSpecs stop at lifts, movers and cutscene starts
    if True:
        for i in range(len(nav)):
            d = np.linalg.norm(P - P[i], axis=1)
            for j in np.argsort(d)[1:9]:
                dz = abs(P[j][2] - P[i][2])
                if d[j] < 900 and dz < max(120, 0.7 * math.hypot(*(P[j][:2] - P[i][:2]))):
                    w = d[j] * (1.5 if real else 1.0)
                    G[i].append((j, w))
                    G[j].append((i, w))
    for i in range(len(nav)):                          # isolated points (a start on a dropship): their two nearest
        if not G[i]:
            d = np.linalg.norm(P - P[i], axis=1)
            for j in np.argsort(d)[1:3]:
                if d[j] < 3000:
                    G[i].append((j, d[j] * 1.5))
                    G[j].append((i, d[j] * 1.5))
    # still apart: islands joined by lifts, doors, ladders and teleporters the graph doesn't show. Join each island
    # to its nearest other island (3x cost) until one is left, and say how many such bridges the route needs
    BRIDGES = []
    while True:
        comp, cid = {}, 0
        for i in range(len(nav)):
            if i in comp:
                continue
            st = [i]
            comp[i] = cid
            while st:
                u = st.pop()
                for v, _ in G[u]:
                    if v not in comp:
                        comp[v] = cid
                        st.append(v)
            cid += 1
        if cid <= 1:
            break
        ia = [i for i in range(len(nav)) if comp[i] == comp[0]]
        ib = [i for i in range(len(nav)) if comp[i] != comp[0]]
        D = np.linalg.norm(P[ia][:, None, :] - P[ib][None, :, :], axis=2)
        a_, b_ = np.unravel_index(np.argmin(D), D.shape)
        u, v = ia[a_], ib[b_]
        G[u].append((v, D[a_, b_] * 3))
        G[v].append((u, D[a_, b_] * 3))
        BRIDGES.append((u, v))
    i0 = int(np.argmin(np.linalg.norm(P - start["p"], axis=1)))
    dist, prev = {i0: 0.0}, {}
    h = [(0.0, i0)]
    while h:
        d0, i = heapq.heappop(h)
        if d0 > dist.get(i, 1e18):
            continue
        for j, w in G[i]:
            if d0 + w < dist.get(j, 1e18):
                dist[j], prev[j] = d0 + w, i
                heapq.heappush(h, (d0 + w, j))
    goal = None
    if exits:
        cand = sorted(dist, key=lambda i: np.linalg.norm(P[i] - exits[0]["p"]))
        goal = cand[0] if cand else None
    if goal is None:
        goal = max(dist, key=dist.get)
    route = [goal]
    while route[-1] in prev:
        route.append(prev[route[-1]])
    route = route[::-1]
    R = P[route]
    acc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))])
    walk_s = acc[-1] / SPEED

    def along(q, reach=700):
        d = np.linalg.norm(R - q, axis=1)
        k = int(np.argmin(d))
        return (acc[k], d[k]) if d[k] < reach else (None, d[k])

    def on_route(items, reach=700):
        out = []
        for a in items:
            s, _ = along(a["p"], reach)
            if s is not None:
                out.append((s, a))
        return sorted(out, key=lambda x: x[0])

    rows = {}
    props = {"gore": [], "lights": [], "cover": [], "notes": []}
    wet = lambda q: any(inside(w["bbox"], q, 32) for w in water)

    # ================================================================ WRITER
    notes, ch = [], {}
    en_r = on_route(enemies, 1200)
    first_fight = en_r[0][0] if en_r else acc[-1]
    ev = [s for s, a in on_route(bodies + blood + scares, 900) if s < first_fight]
    ch["W1 evidence first"] = min(1.0, len(ev) / 3.0)
    notes.append("W1: %d signs (bodies, blood, scares) before the first fight at %.0f s" % (len(ev), first_fight / SPEED))
    told = 0
    for b in bodies:
        near = lambda xs, r: any(0 < np.linalg.norm(x["p"] - b["p"]) < r for x in xs)
        if near(doors, 400) or near(smesh, 120) or near(pickups, 300) or near(bodies, 350) or near(lights, 200):
            told += 1
    ch["W2 bodies tell"] = told / len(bodies) if bodies else 0.0
    notes.append("W2: %d of %d bodies placed with a reason nearby (door, prop, weapon, another body)" % (told, len(bodies)))
    bs = sorted([0.0, acc[-1]] + [s for s, _ in on_route(story + scares + by["Trigger"], 900)])
    gap = max(np.diff(bs)) / SPEED if len(bs) > 1 else walk_s
    ch["W3 story spread"] = float(np.clip(90.0 / max(gap, 1), 0, 1))
    notes.append("W3: %d story beats on the walk, longest quiet %.0f s (want <= 90)" % (len(bs) - 2, gap))
    bled = sum(1 for b in bodies if any(np.linalg.norm(x["p"] - b["p"]) < 400 for x in blood))
    ch["W4 gore serves"] = bled / len(bodies) if bodies else 1.0
    notes.append("W4: %d of %d bodies have blood scripted near them" % (bled, len(bodies)))
    rows["writer"] = (ch, notes, None)
    # proposals: a vignette per body (pool under it; spray toward the nearest enemy entrance it fled from; a drag
    # trail when it lies near a door: it crawled there), and three foreshadowing marks before the first fight
    spawns = [a["p"] for a in enemies]
    for b in bodies:
        if wet(b["p"]):
            continue
        v = {"at": b["p"].round().tolist(), "body": b["name"], "kinds": ["pool"]}
        if spawns:
            e = min(spawns, key=lambda q: np.linalg.norm(q - b["p"]))
            u = (e - b["p"])[:2] / max(1, np.linalg.norm((e - b["p"])[:2]))
            v["kinds"].append("spray")
            v["spray_dir"] = [round(-u[0], 2), round(-u[1], 2)]          # the blow came from the creature's side
        dn = [d for d in doors if 0 < np.linalg.norm(d["p"] - b["p"]) < 600]
        if dn:
            d = min(dn, key=lambda d: np.linalg.norm(d["p"] - b["p"]))
            v["kinds"].append("drag_trail")
            v["trail_to"] = d["p"].round().tolist()                       # crawled for the door
        props["gore"].append(v)
    if en_r:
        for f in (0.45, 0.7, 0.9):
            s = first_fight * f
            k = int(np.searchsorted(acc, s))
            q = R[min(k, len(R) - 1)]
            if not wet(q):
                props["gore"].append({"at": q.round().tolist(), "kinds": ["smear" if f < 0.8 else "claw_marks"],
                                      "why": "foreshadow the first fight (%.0f s before it)" % ((first_fight - s) / SPEED)})

    # ================================================================ DIRECTOR
    notes, ch = [], {}
    S = np.arange(0, acc[-1], SPEED * 2)                                   # a sample every 2 s of walking
    pts = [R[min(int(np.searchsorted(acc, s)), len(R) - 1)] + np.array([0, 0, 60]) for s in S]
    lv = np.array([light_level(lights, q) for q in pts]) if pts else np.zeros(1)
    lo, hi = np.percentile(lv, 30), np.percentile(lv, 70)
    win = [lv[i:i + 15] for i in range(0, len(lv), 15)]                     # 30 s windows
    alt = sum(1 for w in win if (w <= lo).any() and (w >= hi).any())
    ch["D1 compression/release"] = alt / max(1, len(win))
    notes.append("D1: %d of %d 30-s windows go from dark to bright" % (alt, len(win)))
    rev = 0.5
    if en_r:
        e = en_r[0][1]
        k = max(0, int(np.searchsorted(S, max(0, en_r[0][0] - 600))) - 1)
        le, la = light_level(lights, e["p"] + np.array([0, 0, 60])), lv[min(k, len(lv) - 1)]
        rev = 1.0 if le > la * 1.2 else (0.5 if le > la * 0.8 else 0.0)
        notes.append("D2: the first enemy (%s) stands in light %.0f vs the approach %.0f" % (e["cls"], le, la))
        if rev < 1:
            props["lights"].append({"at": e["p"].round().tolist(), "add": "a low warm key light on the first enemy's spot",
                                    "why": "the reveal: lit creature, dark approach (Unreal 1 Skaarj)"})
    ch["D2 reveal"] = rev
    fam = 0
    for L in lights:
        hue, sat = float(L.get("LightHue", 0)), float(L.get("LightSaturation", 255))
        if sat >= 200 or 8 <= hue <= 40 or hue >= 240 or hue <= 8:
            fam += 1
    ch["D3 palette"] = fam / max(1, len(lights))
    notes.append("D3: %d of %d lights in the brief's families (white, rust/amber, red)" % (fam, len(lights)))
    dark = float(np.mean(lv < max(8.0, 0.25 * np.median(lv))))
    ch["D4 darkness"] = 1.0 if 0.2 <= dark <= 0.5 else max(0.0, 1 - abs(dark - 0.35) / 0.35)
    notes.append("D4: %.0f %% of the walk in low light (want 20-50)" % (100 * dark))
    rows["director"] = (ch, notes, None)

    # ================================================================ ENGINEER
    notes, ch = [], {}
    if water:
        inw = sum(1 for a in nav if wet(a["p"]))
        ch["E1 water"] = 1.0 if inw >= len(water) else inw / len(water)
        phys = ["%s gravity %s friction %s" % (w["name"], w.get("Gravity", "default"), w.get("FluidFriction", "default")) for w in water[:3]]
        notes.append("E1: %d water volumes, %d nav points in water; %s" % (len(water), inw, "; ".join(phys)))
    nos = [L for L in lights if not any(np.linalg.norm(m["p"] - L["p"]) < 160 for m in smesh)]
    ch["E2 light sources"] = 1 - len(nos) / max(1, len(lights))
    notes.append("E2: %d of %d lights have no fixture mesh within 160 UU" % (len(nos), len(lights)))
    deg1 = [i for i in dist if len(G[i]) == 1 and i not in route]
    ch["E3 dead ends"] = 1 - len(deg1) / max(1, len(dist))
    notes.append("E3: %d dead-end nav points off the route" % len(deg1))
    rows["engineer"] = (ch, notes, None)

    # ================================================================ LEVEL DESIGNER
    notes, ch, veto = [], {}, None
    near_exit = int(np.argmin(np.linalg.norm(P - exits[0]["p"], axis=1))) if exits else goal
    reached = goal in dist and (not exits or goal == near_exit or np.linalg.norm(P[goal] - P[near_exit]) < 600)
    ch["L1 route"] = 1.0 if reached else 0.0
    if not reached:
        veto = "no walkable route from the start to the exit"
    nb = sum(1 for u, v in BRIDGES if u in route and v in route)
    notes.append("L1 (%s; %d islands joined by guessed lifts/doors, %d of them on the route)" % (GRAPH, len(BRIDGES), nb))
    notes.append("L1: route %s, %.0f s of walking over %d nav points%s" % ("found" if reached else "NOT found (stops %.0f UU from the exit's nearest nav point)" % np.linalg.norm(P[goal] - P[near_exit]), walk_s, len(route),
                 "" if not exits else " to %s" % exits[0].get("URL")))
    bt = sorted([0.0, acc[-1]] + [s for s, _ in on_route(enemies + bodies + by["Trigger"] + pickups + doors, 700)])
    g2 = max(np.diff(bt)) / SPEED if len(bt) > 1 else walk_s
    ch["L2 pacing"] = float(np.clip(60.0 / max(g2, 1), 0, 1))
    notes.append("L2: %d beats, longest gap %.0f s (want <= 60)" % (len(bt) - 2, g2))
    groups = []
    for s, e in en_r:
        if not groups or s - groups[-1][0] > 1500:
            groups.append([s, [e]])
        else:
            groups[-1][1].append(e)
    good = 0
    for s, es in groups:
        c = np.mean([e["p"] for e in es], axis=0)
        cover = sum(1 for m in smesh if 256 < np.linalg.norm((m["p"] - c)[:2]) < 1024 and abs(m["p"][2] - c[2]) < 200)
        ways = {int((math.degrees(math.atan2(*(P[i] - c)[1::-1])) + 360) // 90) for i in dist if 600 < np.linalg.norm(P[i] - c) < 1400}
        ok = cover >= 3 and len(ways) >= 2
        good += ok
        if cover < 3:
            props["cover"].append({"at": c.round().tolist(), "add": "%d waist-high cover pieces 256-1024 UU out" % (3 - cover),
                                   "why": "arena at %.0f s has %d" % (s / SPEED, cover)})
    ch["L3 arenas"] = good / len(groups) if groups else 0.5
    notes.append("L3: %d of %d fights have cover and two ways in" % (good, len(groups)))
    hs = [s for s, _ in on_route(health, 900)]
    rec = sum(1 for s, _ in groups if any(0 <= h_ - s < 30 * SPEED for h_ in hs))
    ch["L4 recovery"] = rec / len(groups) if groups else 1.0
    notes.append("L4: %d of %d fights have health within 30 s after" % (rec, len(groups)))
    q5 = 0.0
    if groups:
        prior = [s for s, _ in on_route(enemies, 1200) if s < groups[0][0] - 1]
        quiet = (groups[0][0] - (max(prior) if prior else 0)) / SPEED
        q5 = 1.0 if quiet >= 20 else quiet / 20
        notes.append("L5: %.0f s of quiet before the first fight (want >= 20)" % quiet)
    ch["L5 first encounter"] = q5
    rows["level"] = (ch, notes, veto)

    # ================================================================ ARTIST
    notes, ch = [], {}
    mc = Counter(m.get("StaticMesh", "?") for m in smesh)
    top, n = mc.most_common(1)[0] if mc else ("-", 0)
    share = n / max(1, len(smesh))
    ch["A1 art fatigue"] = float(np.clip(1 - (share - 0.12) / 0.3, 0, 1))
    notes.append("A1: the most used mesh (%s) is %.0f %% of %d placed" % (top.split("'")[-2] if "'" in top else top, 100 * share, len(smesh)))
    zt = defaultdict(set)
    for a in A:
        for tx in a.get("tex", []):
            zt[a["zone"]].add(tx)
    zt = {z: s for z, s in zt.items() if z >= 0}
    poor = [z for z, s in zt.items() if len(s) <= 1]
    ch["A2 texture variety"] = 1 - len(poor) / max(1, len(zt))
    notes.append("A2: %d zones, median %d textures each, %d with one" % (len(zt), int(np.median([len(s) for s in zt.values()])) if zt else 0, len(poor)))
    zm = defaultdict(set)
    for m in smesh:
        zm[m["zone"]].add(m.get("StaticMesh"))
    hero = sum(1 for z, s in zm.items() if any(sum(1 for z2, s2 in zm.items() if x in s2) == 1 and mc[x] <= 2 for x in s))
    ch["A3 hero details"] = hero / max(1, len(zm))
    notes.append("A3: %d of %d zones have a mesh found nowhere else" % (hero, len(zm)))
    rows["artist"] = (ch, notes, None)

    out = {}
    for k, (c, nts, v) in rows.items():
        out[k] = {"score": round(float(np.mean(list(c.values()))) if c else 0.5, 3), "checks": {a: round(b, 2) for a, b in c.items()},
                  "notes": nts, "veto": v}
    vetoes = [r["veto"] for r in out.values() if r["veto"]]
    sc = [max(1e-3, out[k]["score"]) for k in ("writer", "director", "engineer", "level", "artist")]
    out["total"] = 0.0 if vetoes else round(float(np.prod(sc) ** (1 / len(sc))), 3)
    out["vetoes"] = vetoes
    out["proposals"] = props
    out["_draw"] = {"P": P, "route": R, "nav": [i for i in dist], "lights": lights, "enemies": enemies, "bodies": bodies,
                    "water": water, "pickups": pickups, "start": start["p"], "exit": exits[0]["p"] if exits else None}
    if gm_note:
        c, draws = gm_note
        out["gm"] = {"journal": dict(c), "draws": [d.split(" note ", 1)[-1] if " note " in d else d[:80] for d in draws]}
    out["counts"] = {"actors": len(A), "nav": len(nav), "lights": len(lights), "meshes": len(smesh), "enemies": len(enemies),
                     "bodies": len(bodies), "water": len(water), "walk_s": round(walk_s)}
    return out


def draw(Rv, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = Rv["_draw"]
    fig, ax = plt.subplots(figsize=(11, 11), facecolor="#111")
    ax.set_facecolor("#111")
    for w in d["water"]:
        (x0, y0, _), (x1, y1, _) = w["bbox"]
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color="#1d3c5a", alpha=0.6))
    P = d["P"]
    ax.scatter(P[:, 0], P[:, 1], s=4, c="#555")
    for L in d["lights"]:
        hue, sat = float(L.get("LightHue", 0)), float(L.get("LightSaturation", 255))
        import colorsys
        col = colorsys.hsv_to_rgb(hue / 255, max(0, 1 - sat / 255), 1)
        ax.scatter(L["p"][0], L["p"][1], s=float(L.get("LightBrightness", 64)) / 2, color=col, alpha=0.35, lw=0)
    ax.plot(d["route"][:, 0], d["route"][:, 1], "-", c="#e8c040", lw=2, label="critical route")
    for e in d["enemies"]:
        ax.scatter(e["p"][0], e["p"][1], s=40, marker="x", c="#ff4040")
    for b in d["bodies"]:
        ax.scatter(b["p"][0], b["p"][1], s=30, marker="s", c="#d0d0d0")
    for p in d["pickups"]:
        ax.scatter(p["p"][0], p["p"][1], s=12, marker="+", c="#40d040")
    for g in Rv["proposals"]["gore"]:
        ax.scatter(g["at"][0], g["at"][1], s=60, facecolors="none", edgecolors="#b00000", lw=1.5)
        if "trail_to" in g:
            ax.plot([g["at"][0], g["trail_to"][0]], [g["at"][1], g["trail_to"][1]], ":", c="#b00000")
    for c in Rv["proposals"]["cover"]:
        ax.scatter(c["at"][0], c["at"][1], s=200, facecolors="none", edgecolors="#40a0ff", lw=1.5)
    for L in Rv["proposals"]["lights"]:
        ax.scatter(L["at"][0], L["at"][1], s=200, marker="*", c="#ffb040")
    ax.scatter(*d["start"][:2], s=120, marker="^", c="#40ff80")
    if d["exit"] is not None:
        ax.scatter(*d["exit"][:2], s=120, marker="v", c="#ff80ff")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.tick_params(colors="#777")
    ax.set_title("route (yellow)  enemies x  bodies (grey sq)  pickups +  lights (dots by colour)  water (blue)\n"
                 "proposals: gore (red rings, dotted = drag trail)  cover (blue rings)  key light (star)", color="#ccc", fontsize=9)
    fig.savefig(png, dpi=90, bbox_inches="tight", facecolor="#111")
    plt.close(fig)


def report(Rv, name):
    L = ["# Creative team review: %s" % name, "",
         "**Total %.2f**%s (geometric mean of the five; one weak role sinks it)" % (Rv["total"], ("  VETO: " + "; ".join(Rv["vetoes"])) if Rv["vetoes"] else ""), "",
         "Counts: " + ", ".join("%s %s" % kv for kv in Rv["counts"].items()), "", "| role | score | checks |", "|---|---|---|"]
    for k in ("writer", "director", "engineer", "level", "artist"):
        L.append("| %s | %.2f | %s |" % (k, Rv[k]["score"], ", ".join("%s %.2f" % kv for kv in Rv[k]["checks"].items())))
    for k in ("writer", "director", "engineer", "level", "artist"):
        L += ["", "## %s" % k.upper()] + ["- " + n for n in Rv[k]["notes"]]
    if "gm" in Rv:
        L += ["", "## The game master's journal (applied before scoring)", "",
              "- lines: " + (", ".join("%s %d" % kv for kv in Rv["gm"]["journal"].items()) or "none for this map")]
        L += ["- the GM drew: " + d for d in Rv["gm"]["draws"]]
    p = Rv["proposals"]
    L += ["", "## Redesign proposals", "",
          "- gore vignettes: %d (%s)" % (len(p["gore"]), ", ".join("%s %d" % kv for kv in Counter(k for g in p["gore"] for k in g["kinds"]).items())),
          "- lights: %d" % len(p["lights"])] + ["  - %s at %s: %s" % (x["add"], x["at"], x["why"]) for x in p["lights"]] + \
         ["- cover: %d" % len(p["cover"])] + ["  - %s at %s: %s" % (x["add"], x["at"], x["why"]) for x in p["cover"]]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith(("scenes=", "gm="))]
    sc = [a[7:] for a in sys.argv[1:] if a.startswith("scenes=")]
    gm = [a[3:] for a in sys.argv[1:] if a.startswith("gm=")]
    src = args[0]
    out = args[1] if len(args) > 1 else os.path.dirname(os.path.abspath(src))
    name = os.path.splitext(os.path.basename(src))[0]
    Rv = review(src, sc[0] if sc else None, gm[0] if gm else None)
    if sc or gm:
        name += "_after"
    open(os.path.join(out, name + "_review.md"), "w", encoding="utf-8").write(report(Rv, name))
    draw(Rv, os.path.join(out, name + "_review.png"))
    json.dump({k: v for k, v in Rv.items() if k != "_draw"}, open(os.path.join(out, name + "_redesign.json"), "w"), indent=1, default=float)
    print(report(Rv, name))
