r"""The LEVEL DESIGNER's combat review of a built Unreal II map (the user, 2026-10-08: "have the level designer
rate the combat arenas and the enemy ai design"). Two parts:

ARENAS - every fight on the critical route (enemies within 1200 UU of it, grouped when < 1500 UU apart along the
walk), rated 0..1 on (Level design practices s.6 + gameplay_terrain.md + the U2 mechanics measured in U2FairFights):
  cover      >= 3 pieces 256-1024 UU out (waist/full height)              entries   >= 2 ways in (nav quadrants)
  sightlines 30-80 % of 16 rays blocked within 2048 UU (open ground past 20 m is where NPC hit odds still bite)
  range      the enemies 256-1024 UU off the route (medium: the fight is readable, the hit odds fair)
  reveal     the enemies stand in more light than the approach (readable silhouettes)
  arrival    spawned enemies come in through a door (factory/spawn point within 400 UU of a mover), never pop in
  height     a spot 3 m+ over the arena floor within 800 UU (someone holds the high ground)
  recovery   health within 30 s of walking after the fight
and the map as a whole:
  pacing     the fights' weight along the walk: real valleys between peaks (L4D build-up / relax), no flat line
  teach      each enemy kind's first fight is small (<= 2 of it) and that kind alone (Unreal 1's first Skaarj)
  variety    how many different line-ups the fights use

ENEMY AI - each enemy class's design from its own defaults (exported U2Pawns source, Documents\Tools\u2_export)
and its placed overrides, rated on: a ROLE (rusher / shooter / tank, from AttackClose vs Stationary odds, speed,
health), MOBILITY (tactical move + dodge + leap), COVER USE (passive cover behaviours), a SIGNATURE MOVE (the
Unreal recipe: silhouette + one move + one sound), DISTINCT from the others (behaviour vector distance), and
FAIR (projectile or melee rather than hitscan; tells before damage).

    py arenas.py <map.t3d> [out_dir]     -> <map>_arenas.md (+ <map>_arenas.json)
"""
import json, math, os, re, sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapreview  # noqa

SPEED = mapreview.SPEED
EXPORT = os.path.expanduser(r"~\Documents\Tools\u2_export\cur_U2Pawns")
ENEMY = re.compile(r"U2(Izarian|Skaarj\w*|Araknid\w*|Aida\w*|Merc\w*|Drakk\w*|Strider\w*)$")
WEIGHT = {"U2Izarian": 1.0, "U2SkaarjLight": 2.0, "U2SkaarjMedium": 3.0, "U2SkaarjHeavy": 5.0}


def class_defaults(cls, seen=None):
    """the defaultproperties of an exported U2Pawns class, merged down its parents that are exported too"""
    f = os.path.join(EXPORT, cls + ".uc")
    if not os.path.exists(f):
        return {}
    t = open(f, encoding="latin1").read()
    parent = re.search(r"class\s+\w+\s+extends\s+(\w+)", t)
    d = class_defaults(parent.group(1)) if parent else {}
    for k, v in re.findall(r"^\s*(\w+(?:\(\d+\))?)=(.*)$", t.split("defaultproperties")[-1], re.M):
        d[k] = v.strip()
    return d


def behaviours(d):
    """{list name: [(state, odds)]} from AttackXxxBehaviors(i)=(StateName=..,Odds=..)"""
    out = defaultdict(list)
    for k, v in d.items():
        m = re.match(r"(Attack\w+Behaviors)\(\d+\)", k)
        if m:
            st = re.search(r"StateName=(\w+)", v)
            od = re.search(r"Odds=([-\d.]+)", v)
            out[m.group(1)].append((st.group(1) if st else "?", float(od.group(1)) if od else 1.0))
    return out


def ai_profile(cls):
    d = class_defaults(cls)
    b = behaviours(d)
    act = dict(b.get("AttackActiveBehaviors", []))
    tot = sum(act.values()) or 1
    close = act.get("AttackClose", 0) / tot
    stat = act.get("AttackStationary", 0) / tot
    tac = act.get("AttackTacticalMove", 0) / tot
    f = lambda k, dflt=0.0: float(d.get(k, dflt))
    dodge = max(f("DodgeProjectileOdds"), f("DodgeInsteadofStrafeOdds") * 0.5)
    leap = f("LeapOdds") + 0.5 * f("LeapToMeleeOdds")
    cover = len(b.get("AttackPassiveUseCoverBehaviors", [])) / 5.0 + dict(b.get("AttackPassiveBehaviors", [])).get("AttackMoveToCoverCombat", 0)
    speed, health = f("GroundSpeed", 440), f("Health", 100)
    weapon = d.get("DefaultWeapon", "").strip('"').split(".")[-1]
    if not weapon and "RangedProjectileClass" in d:
        weapon = "claws + " + d["RangedProjectileClass"].split(".")[-1].rstrip("'") + " (projectile)"
    if not weapon and cls.startswith("U2Skaarj"):
        weapon = "claws + seeking glove shots (projectile)"
    weapon = weapon or ("melee" if f("MeleeOdds") >= 1 else "?")
    role = "tank" if health >= 400 and speed < 250 else ("rusher" if close > 0.5 else "shooter")
    taunt = dict(b.get("AttackActiveBehaviors", [])).get("AttackTaunt", 0) > 0 or f("TauntAnimationOdds") > 0
    sig = []
    if leap > 0.3:
        sig.append("leaps")
    if dodge >= 1:
        sig.append("dodges shots")
    if taunt:
        sig.append("taunts")
    if f("AcquisitionAnimationOdds") > 0:
        sig.append("an acquisition roar")
    return {"class": cls, "role": role, "weapon": weapon, "health": health, "speed": speed,
            "close": round(close, 2), "stationary": round(stat, 2), "tactical": round(tac, 2),
            "mobility": round(min(1.0, tac + dodge * 0.5 + leap * 0.5), 2), "cover": round(min(1.0, cover), 2),
            "melee": f("MeleeOdds"), "signature": sig, "vec": [close, stat, tac, min(1, dodge), min(1, leap), min(1, cover), speed / 600, health / 600]}


def rate_ai(profiles):
    out = []
    for p in profiles:
        others = [q for q in profiles if q["class"] != p["class"]]
        dist = min((np.linalg.norm(np.array(p["vec"]) - np.array(q["vec"])) for q in others), default=1.0)
        hitscan = any(w in p["weapon"].lower() for w in ("assaultrifle", "sniper", "machine"))
        r = {"role": 1.0,
             "mobility": p["mobility"],
             "cover use": p["cover"] if p["role"] == "shooter" else 1.0 - 0.5 * p["cover"],   # rushers shouldn't hide
             "signature move": min(1.0, len(p["signature"]) / 2.0),
             "distinct": float(np.clip(dist / 0.6, 0, 1)),
             "fair": 0.4 if hitscan else 1.0}
        notes = []
        if dist < 0.15:
            twin = min(others, key=lambda q: np.linalg.norm(np.array(p["vec"]) - np.array(q["vec"])))["class"]
            notes.append("behaves like %s (only health/looks differ): give it its own move" % twin)
        if not p["signature"]:
            notes.append("no signature move: nothing for the player to learn and remember (Unreal recipe)")
        if p["role"] == "shooter" and p["cover"] < 0.3:
            notes.append("a shooter that doesn't use cover stands in the open")
        if hitscan:
            notes.append("hitscan: fairness rests on TryToHit odds (U2FairFights tunes them)")
        out.append({**{k: v for k, v in p.items() if k != "vec"}, "rating": {k: round(v, 2) for k, v in r.items()},
                    "score": round(float(np.mean(list(r.values()))), 2), "notes": notes})
    return out


def arenas(path):
    A = mapreview.parse(path)
    Rv = mapreview.review(path)
    d = Rv["_draw"]
    R, P = d["route"], d["P"]
    acc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))])
    smesh = [a for a in A if a["cls"] == "StaticMeshActor"]
    lights = d["lights"]
    movers = [a for a in A if a["cls"] in ("Mover", "Door", "DoorMover")]
    health = [a for a in A if a["cls"].startswith("Health")]
    factories = [a for a in A if a["cls"] == "PawnFactory" and ENEMY.search(a.get("Prototype", "").split(".")[-1].rstrip("'"))]
    placed = [a for a in A if ENEMY.match(a["cls"])]
    for fct in factories:
        fct["kind"] = fct["Prototype"].split(".")[-1].rstrip("'")
        fct["n"] = int(fct.get("Capacity", 1))
    for e in placed:
        e["kind"], e["n"] = e["cls"], 1
    items = []
    for e in placed + factories:
        dd = np.linalg.norm(R - e["p"], axis=1)
        k = int(np.argmin(dd))
        if dd[k] < 1200:
            items.append((acc[k], dd[k], e))
    items.sort(key=lambda x: x[0])
    groups = []
    for s, dist, e in items:
        if not groups or s - groups[-1]["s1"] > 1500:
            groups.append({"s0": s, "s1": s, "members": []})
        groups[-1]["s1"] = s
        groups[-1]["members"].append((dist, e))
    rows, first_seen = [], {}
    for gi, g in enumerate(groups):
        es = [e for _, e in g["members"]]
        c = np.mean([e["p"] for e in es], axis=0)
        comp = Counter()
        for e in es:
            comp[e["kind"]] += e["n"]
        ch = {}
        cover = sum(1 for m in smesh if 256 < np.linalg.norm((m["p"] - c)[:2]) < 1024 and abs(m["p"][2] - c[2]) < 200)
        ch["cover"] = min(1.0, cover / 3)
        quads = {int((math.degrees(math.atan2(*(P[i] - c)[1::-1])) + 360) // 90) for i in range(len(P)) if 600 < np.linalg.norm(P[i] - c) < 1400}
        ch["entries"] = min(1.0, len(quads) / 2)
        blocked = 0
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            u = np.array([math.cos(a), math.sin(a), 0])
            hit = any(np.linalg.norm(np.cross(m["p"] - c, u)) < 120 and 0 < np.dot(m["p"] - c, u) < 2048 for m in smesh)
            blocked += hit
        fb = blocked / 16
        ch["sightlines"] = 1.0 if 0.3 <= fb <= 0.8 else max(0.0, 1 - abs(fb - 0.55) / 0.55)
        rng = np.median([dist for dist, _ in g["members"]])
        ch["range"] = 1.0 if 256 <= rng <= 1024 else (0.6 if rng < 256 else max(0.2, 1 - (rng - 1024) / 1500))
        k0 = max(0, int(np.searchsorted(acc, max(0, g["s0"] - 600))) - 1)
        le = mapreview.light_level(lights, c + [0, 0, 60])
        la = mapreview.light_level(lights, R[k0] + [0, 0, 60])
        ch["reveal"] = 1.0 if le > la * 1.2 else (0.5 if le > la * 0.8 else 0.0)
        spawned = [e for e in es if e["cls"] == "PawnFactory"]
        if spawned:
            ch["arrival"] = sum(1 for e in spawned if any(np.linalg.norm(m["p"] - e["p"]) < 400 for m in movers)) / len(spawned)
        hi = [m["p"][2] for m in smesh + es if np.linalg.norm((m["p"] - c)[:2]) < 800]
        ch["height"] = 1.0 if hi and max(hi) - c[2] > 150 else 0.0
        ch["recovery"] = 1.0 if any(0 <= (acc[int(np.argmin(np.linalg.norm(R - h["p"], axis=1)))] - g["s1"]) < 30 * SPEED and
                                    np.min(np.linalg.norm(R - h["p"], axis=1)) < 900 for h in health) else 0.0
        weight = sum(WEIGHT.get(k, 1.5) * n for k, n in comp.items())
        new = [k for k in comp if k not in first_seen]
        for k in new:
            first_seen[k] = (gi, comp[k], len(comp))
        rows.append({"fight": gi + 1, "at_s": round(g["s0"] / SPEED), "line_up": dict(comp), "weight": weight,
                     "spawned": len(spawned), "range_uu": int(rng), "cover": cover, "ways_in": len(quads),
                     "blocked": round(fb, 2), "checks": {k: round(v, 2) for k, v in ch.items()},
                     "score": round(float(np.mean(list(ch.values()))), 2), "new_enemy": new,
                     "centre": c.round().tolist()})
    # the map as a whole
    W = [r["weight"] for r in rows]
    valleys = sum(1 for i in range(1, len(W) - 1) if W[i] < W[i - 1] and W[i] < W[i + 1])
    peaks = sum(1 for i in range(1, len(W) - 1) if W[i] > W[i - 1] and W[i] > W[i + 1])
    flat = len(W) > 2 and np.std(W) < 0.25 * np.mean(W)
    pacing = 0.3 if flat else min(1.0, 0.4 + 0.3 * (valleys + peaks) / max(1, len(W) / 2))
    teach = [1.0 if n <= 2 and kinds == 1 else (0.5 if n <= 2 else 0.0) for gi, n, kinds in first_seen.values()]
    whole = {"pacing": round(pacing, 2), "teach": round(float(np.mean(teach)) if teach else 0.5, 2),
             "variety": round(min(1.0, len({tuple(sorted(r["line_up"].items())) for r in rows}) / max(1, len(rows)) * 1.5), 2)}
    kinds = sorted({k for r in rows for k in r["line_up"]})
    ai = rate_ai([ai_profile(k) for k in kinds])
    return {"map": os.path.splitext(os.path.basename(path))[0], "fights": rows, "whole": whole,
            "first_seen": {k: {"fight": v[0] + 1, "count": v[1], "alone": v[2] == 1} for k, v in first_seen.items()},
            "ai": ai, "arena_score": round(float(np.mean([r["score"] for r in rows])) if rows else 0, 2)}


def report(X):
    L = ["# Level designer: combat arenas and enemy AI, %s" % X["map"], "",
         "**Arenas %.2f** (mean of %d fights); pacing %.2f, teach %.2f, variety %.2f" % (
             X["arena_score"], len(X["fights"]), X["whole"]["pacing"], X["whole"]["teach"], X["whole"]["variety"]), "",
         "| # | at | line-up | weight | score | cover | ways in | blocked | range | checks |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in X["fights"]:
        L.append("| %d | %d s | %s | %.0f | %.2f | %d | %d | %.0f %% | %d | %s |" % (
            r["fight"], r["at_s"], ", ".join("%s x%d" % kv for kv in r["line_up"].items()), r["weight"], r["score"], r["cover"],
            r["ways_in"], 100 * r["blocked"], r["range_uu"], " ".join("%s %.1f" % kv for kv in r["checks"].items())))
    L += ["", "**Pacing** (fight weight along the walk): " + " ".join("%.0f" % r["weight"] for r in X["fights"]),
          "", "**First meetings**: " + "; ".join("%s at fight %d (%d of it, %s)" % (k, v["fight"], v["count"], "alone" if v["alone"] else "mixed")
                                                 for k, v in X["first_seen"].items()), "", "## Enemy AI design", "",
          "| class | role | weapon | health | speed | close / stationary / tactical | mobility | cover | signature | score |", "|---|---|---|---|---|---|---|---|---|---|"]
    for a in X["ai"]:
        L.append("| %s | %s | %s | %.0f | %.0f | %.2f / %.2f / %.2f | %.2f | %.2f | %s | %.2f |" % (
            a["class"], a["role"], a["weapon"], a["health"], a["speed"], a["close"], a["stationary"], a["tactical"],
            a["mobility"], a["cover"], ", ".join(a["signature"]) or "-", a["score"]))
    for a in X["ai"]:
        if a["notes"]:
            L.append("- **%s**: %s" % (a["class"], "; ".join(a["notes"])))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(src))
    X = arenas(src)
    name = os.path.splitext(os.path.basename(src))[0]
    open(os.path.join(out, name + "_arenas.md"), "w", encoding="utf-8").write(report(X))
    json.dump(X, open(os.path.join(out, name + "_arenas.json"), "w"), indent=1, default=float)
    print(report(X))
