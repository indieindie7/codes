r"""Playable areas: a fork of the town generator (U2Avalon/tools: layout_spine's plots + town.py's rerolls reviewed by
the co-directors) for COMBAT ARENAS (the user, 2026-10-08: "merge into the city generator the level design arena
concepts in a fork of playable areas and try to use it for this level").

Where the town generator lays plots along a spine for a believable town, this lays a place's buildings, cover and
spawn sheds so the place PLAYS, by the level designer's arena rules (games/research_notes/Level design practices
s.6, arenas.py) - and keeps the Manta's lanes open:
  entries      every road into the place is a way in (>= 2), and a vehicle lane (1100 UU) runs from each entry to
               the centre: nothing is built in it
  buildings    the place's program from the Liandri prefab kit (AvalonSM: the binder's footprints, B_<id> meshes),
               on the flattened pad, facing the centre
  spawn sheds  enemies come out of sheds on the far side from the player's first entry, doors facing the centre:
               a readable entrance, never a pop-in behind the player
  cover        clusters of half-height (crates, barrels) and full-height (containers, tanks) pieces 256-1024 UU
               round the centre, outside the lanes, until >= 4 pieces and 30-80 % of 16 sightlines are broken
               within 2048 UU (open ground past 20 m is where the hitscan mercs win)
  high spot    a tall piece (mast, tower, silo) near the edge: someone holds the high ground
Each place is laid out with N seeds and the best by the arena score is kept (the town generator's rerolls).

    py playable.py            -> playable.json (props + spawn doors per place) and playable.png (the plans)
    (make_open.py imports layout_all() and writes the props into the map)
"""
import json, math, os, random, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "U2Avalon", "tools"))
import plan as S  # noqa
import binder  # noqa

M = 50.0                    # UU per metre for the buildings (people-sized: full scale)
LANE = 1100
_, SHEETS = binder.load()
MESH = {"silos": "AvalonSM.ore_tank_2_kiln", "company_mast": "AvalonSM.radio_mast_1_kiln", "tank_farm": "AvalonSM.storage_tank_1_kiln",
        "cooling_towers": "AvalonSM.CoolingTower", "new_rig": "AvalonSM.DrillingRig"}
EXTRA = {   # kit pieces that aren't binder buildings: (mesh, w, d, h) in metres
    "chimney": ("AvalonSM2.ChimneyStack", 6, 6, 24), "pylon": ("AvalonSM.Pylon", 6, 6, 22), "piperack": ("AvalonSM2.PipeRack", 16, 3, 6),
    "dropship": ("AvalonSM.CargoDropship", 22, 30, 9), "floodmast": ("AvalonSM.Floodmasts", 3, 3, 14), "silocluster": ("AvalonSM2.SiloCluster", 14, 14, 18),
}
HALF = [("Terran_DecoM.Crates.Crate1Low", 1.3, 70), ("Terran_DecoM.Barrels.Metal_Barrel_01", 1.0, 45), ("Mission_08M.Crates.Boxnum2", 1.0, 70),
        ("Terran_DecoM.Crates.crate_pallet_01", 1.2, 80)]
FULL = [("Terran_DecoM.Crates.crate2_highfull", 1.2, 110), ("AvalonSM.ore_tank_1_kiln", 0.35, 160), ("Terran_DecoM.Misc.gas_tank", 1.4, 120)]

PROGRAM = {
    "plant": {"main": ["hall_b", "hall_a"], "support": ["intake", "pump_house", "silos", "tank_farm", "piperack"], "gate": "checkpoint",
              "spawn": ["shed_a", "shed_b"], "high": "company_mast"},
    "power": {"main": ["generator_house"], "support": ["plant_office", "chimney", "chimney", "pylon"], "gate": "checkpoint",
              "spawn": ["shed_a", "shed_b"], "high": "pylon"},
    "field": {"main": [], "support": ["piperack", "piperack", "tank_farm"], "gate": None, "spawn": ["shed_b"], "high": "silocluster"},
    "pit": {"main": ["new_rig"], "support": ["piperack"], "gate": None, "spawn": ["shed_a"], "high": None},
    "pad": {"main": ["cargo_pad"], "support": ["floodmast", "floodmast"], "gate": None, "spawn": ["shed_a"], "high": "floodmast",
            "cover_ring": (1300, 1800)},          # a hold-out on the deck: the cover rings its edge, the deck stays clear
    "lz": {"main": ["dropship"], "support": [], "gate": None, "spawn": [], "high": None},
}


def piece(pid):
    if pid in EXTRA:
        m, w, d, h = EXTRA[pid]
        return m, w * M, d * M, h * M
    s = SHEETS[pid]
    w, d, h = s["size"]
    return MESH.get(pid, "AvalonSM.B_" + pid), w * M, d * M, h * M


def entries(q):
    """where each road crosses into the place (it may end there or pass through): (point, inward direction, road id),
    the first road in story order first"""
    out = []
    c = np.array([q["x"], q["y"]], float)
    rr = q["r"] * 0.9
    for r in S.ROADS:
        pts = [np.array(S.where(p), float) for p in r["pts"]]
        dense = []
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(2, int(np.linalg.norm(b - a) / 100))
            dense += [a + (b - a) * k / n for k in range(n)]
        dense.append(pts[-1])
        ins = [np.linalg.norm(p - c) < rr for p in dense]
        for k in range(1, len(dense)):
            if ins[k] != ins[k - 1]:
                p = dense[k] if ins[k] else dense[k - 1]
                d = c - p
                out.append((p, d / (np.linalg.norm(d) or 1), r["id"]))
    return out


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(1e-6, np.dot(ab, ab)), 0, 1)
    return np.linalg.norm(p - (a + ab * t))


def in_lane(p, rad, lanes):
    return any(seg_dist(p, a, b) < LANE / 2 + rad for a, b in lanes)


def layout(q, seed):
    rng = random.Random(seed)
    c = np.array([q["x"], q["y"]], float)
    R = q["r"] * 0.68
    ent = entries(q)
    lanes = [(e[0], c) for e in ent]
    prog = PROGRAM.get(q["id"], {"main": [], "support": [], "gate": None, "spawn": [], "high": None})
    placed = []                                    # dicts: id, mesh, x, y, yaw, w, d, h, kind

    def free(p, rad):
        if np.linalg.norm(p - c) + rad > R or in_lane(p, rad, lanes):
            return False
        return all(np.linalg.norm(p - np.array([o["x"], o["y"]])) > rad + o["rad"] + 150 for o in placed)

    def put(pid, p, kind, face=None):
        mesh, w, d, h = piece(pid)
        f = (c - p) if face is None else face
        th = math.degrees(math.atan2(f[1], f[0]))
        placed.append({"id": pid, "mesh": mesh, "x": float(p[0]), "y": float(p[1]), "yaw": (th + 90) % 360, "w": w, "d": d, "h": h,
                       "rad": 0.5 * math.hypot(w, d) * 0.8, "kind": kind})

    def try_put(pid, kind, ring=(0.25, 1.0), around=None, tries=80, face=None):
        _, w, d, _ = piece(pid)
        rad = 0.5 * math.hypot(w, d) * 0.8
        for _ in range(tries):
            if around is None:
                a, r = rng.uniform(0, 2 * math.pi), rng.uniform(ring[0], ring[1]) * R
                p = c + r * np.array([math.cos(a), math.sin(a)])
            else:
                p = around + rng.uniform(-1, 1) * np.array([600, 600])
            if free(p, rad):
                put(pid, p, kind, face)
                return True
        return False
    for pid in prog["main"]:
        if q["id"] in ("pad", "lz") and pid in ("cargo_pad", "dropship"):
            put(pid, c, "main")                    # the pad is the place itself; the lane runs onto it
            # nothing else on the deck (the review: the bike circles on it), so its footprint keeps the others off
            placed[-1]["rad"] = 0 if pid == "dropship" else 0.5 * min(placed[-1]["w"], placed[-1]["d"])
            continue
        try_put(pid, "main", (0.3, 0.75))
    first = ent[0] if ent else (c + np.array([R, 0]), np.array([-1.0, 0]), "")
    if prog["gate"] and ent:
        g = first[0] + first[1] * 400 + np.array([-first[1][1], first[1][0]]) * (LANE / 2 + 400)
        if free(g, 250):
            put(prog["gate"], g, "gate", face=-first[1])
    # spawn sheds: the far side from the player's first entry, doors to the centre
    far = c + first[1] * R * 0.75
    for pid in prog["spawn"]:
        try_put(pid, "spawn", around=far + rng.uniform(-1, 1) * np.array([900, 900]))
    for pid in prog["support"]:
        try_put(pid, "support")
    if prog["high"]:
        try_put(prog["high"], "high", (0.6, 1.0))
    # cover clusters until the arena rules hold
    for k in range(60):
        if len([o for o in placed if o["kind"] == "cover"]) >= 4 and 0.3 <= blocked(c, placed) <= 0.8:
            break
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(*prog.get("cover_ring", (256, 1024)))
        p0 = c + r * np.array([math.cos(a), math.sin(a)])
        full = rng.random() < 0.4
        mesh, s, rad = rng.choice(FULL if full else HALF)
        if free(p0, rad):
            placed.append({"id": "cover", "mesh": mesh, "x": float(p0[0]), "y": float(p0[1]), "yaw": rng.uniform(0, 360), "w": 2 * rad, "d": 2 * rad,
                           "h": 160 if full else 70, "rad": rad, "kind": "cover", "scale": s})
            for _ in range(rng.randint(1, 3)):     # a cluster, not a lone crate
                mesh2, s2, rad2 = rng.choice(HALF)
                p2 = p0 + rng.uniform(-1, 1) * np.array([180, 180])
                if free(p2, rad2):
                    placed.append({"id": "cover", "mesh": mesh2, "x": float(p2[0]), "y": float(p2[1]), "yaw": rng.uniform(0, 360), "w": 2 * rad2,
                                   "d": 2 * rad2, "h": 70, "rad": rad2, "kind": "cover", "scale": s2})
    return placed, ent, lanes


def blocked(c, placed, reach=2048):
    n = 0
    for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
        u = np.array([math.cos(a), math.sin(a)])
        for o in placed:
            v = np.array([o["x"], o["y"]]) - c
            t = np.dot(v, u)
            if 0 < t < reach and np.linalg.norm(v - u * t) < max(o["rad"], 60) and o["h"] > 60:
                n += 1
                break
    return n / 16


def score(q, placed, ent):
    c = np.array([q["x"], q["y"]])
    lo, hi = PROGRAM.get(q["id"], {}).get("cover_ring", (256, 1024))
    cover = [o for o in placed if o["kind"] == "cover" and lo < np.linalg.norm(np.array([o["x"], o["y"]]) - c) < hi]
    fb = blocked(c, placed)
    ch = {"cover": min(1.0, len(cover) / 4), "entries": min(1.0, len(ent) / 2),
          "sightlines": 1.0 if 0.3 <= fb <= 0.8 else max(0.0, 1 - abs(fb - 0.55) / 0.55),
          "high": 1.0 if any(o["kind"] in ("high", "main") and o["h"] >= 600 for o in placed) else 0.0,
          "spawns": 1.0 if any(o["kind"] == "spawn" for o in placed) or not PROGRAM.get(q["id"], {}).get("spawn") else 0.0,
          "program": sum(1 for o in placed if o["kind"] in ("main", "support", "gate", "spawn", "high")) /
          max(1, sum(len(PROGRAM.get(q["id"], {}).get(k, []) or []) for k in ("main", "support", "spawn")) +
              (1 if PROGRAM.get(q["id"], {}).get("gate") else 0) + (1 if PROGRAM.get(q["id"], {}).get("high") else 0))}
    ch["program"] = min(1.0, ch["program"])
    return float(np.mean(list(ch.values()))), ch, fb


def layout_all(seeds=24):
    out = {}
    for q in S.PLACES:
        if q["id"] not in PROGRAM:
            continue
        best = None
        for sd in range(seeds):
            pl, ent, lanes = layout(q, 1000 + sd)
            sc, ch, fb = score(q, pl, ent)
            if best is None or sc > best[0]:
                best = (sc, ch, fb, pl, ent, lanes, sd)
        sc, ch, fb, pl, ent, lanes, sd = best
        spawns = [{"x": o["x"], "y": o["y"], "door_to": [q["x"], q["y"]]} for o in pl if o["kind"] == "spawn"]
        out[q["id"]] = {"score": round(sc, 2), "checks": {k: round(v, 2) for k, v in ch.items()}, "blocked": round(fb, 2), "seed": sd,
                        "props": [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in o.items() if k != "rad"} for o in pl],
                        "spawns": spawns, "entries": [{"at": e[0].round().tolist(), "road": e[2]} for e in ent]}
    return out


def draw(L, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    ids = list(L)
    fig, axs = plt.subplots(2, 3, figsize=(15, 10), facecolor="#111")
    col = {"main": "#c8a060", "support": "#9a8a70", "gate": "#60a0c0", "spawn": "#d04040", "high": "#e0e060", "cover": "#70c070"}
    for ax, pid in zip(axs.flat, ids):
        q = next(x for x in S.PLACES if x["id"] == pid)
        ax.set_facecolor("#1a2a1a")
        ax.add_patch(Circle((q["x"], q["y"]), q["r"] * 0.68, fill=False, ec="#888", ls="--"))
        for e in L[pid]["entries"]:
            ax.plot([e["at"][0], q["x"]], [e["at"][1], q["y"]], "-", c="#d8b060", lw=6, alpha=0.35)
        for o in L[pid]["props"]:
            if o["kind"] == "cover":
                ax.add_patch(Circle((o["x"], o["y"]), o["w"] / 2, color=col["cover"]))
            else:
                t = matplotlib.transforms.Affine2D().rotate_deg_around(o["x"], o["y"], o["yaw"]) + ax.transData
                ax.add_patch(Rectangle((o["x"] - o["w"] / 2, o["y"] - o["d"] / 2), o["w"], o["d"], color=col[o["kind"]], alpha=0.85, transform=t))
                ax.text(o["x"], o["y"], o["id"], fontsize=6, color="w", ha="center")
        ax.set_title("%s  score %.2f  %s" % (pid, L[pid]["score"], " ".join("%s %.1f" % kv for kv in L[pid]["checks"].items())), color="#ddd", fontsize=8)
        ax.set_aspect("equal")
        ax.set_xlim(q["x"] - q["r"], q["x"] + q["r"])
        ax.set_ylim(q["y"] + q["r"], q["y"] - q["r"])
        ax.tick_params(colors="#666", labelsize=6)
    fig.savefig(png, dpi=75, bbox_inches="tight", facecolor="#111")


if __name__ == "__main__":
    L = layout_all()
    json.dump(L, open(os.path.join(HERE, "playable.json"), "w"), indent=1)
    draw(L, os.path.join(HERE, "playable.png"))
    for k, v in L.items():
        print("%-6s %.2f  %s  props %d spawns %d" % (k, v["score"], v["checks"], len(v["props"]), len(v["spawns"])))
