r"""The creative team reviews Sanctuary Open (the user, 2026-10-08: "do the review please"): the five co-directors with
their rules turned to an OPEN, VEHICLE map. Reads what the generator wrote (heights.npy, playable.json,
open_actors.t3d in <game>\U2SanctuaryOpen) and plan.py; the in-game numbers (frame rate) come from the pilot runs.

  WRITER    the story told by the journey (STORY.md): the beats in the canon's order along the drive; every place a
            key image names exists; the story's props are there (bodies, the wrecked hauler, blood); Miller's voice
  DIRECTOR  the weenie: the plant's tall piece seen from the LZ over the land AND inside the fog's far clip; the key
            frames (each key image has a place); the light (the low sun behind the plant seen from the LZ: back light);
            three layers on the climb (jungle near, the escarpment mid, the plateau's plant far)
  ENGINEER  the Manta's roads: grades within 25 %, widths >= 1000 (3 bikes); pads flat; the basin holds water below
            its rim; the frame-rate budget (>= 60 fps, 1 % low >= 45)
  LEVEL DESIGNER  drive pacing (20-60 s between beats; no ride over 60 s without a view, a fight or a landmark);
            vehicle arenas (the field and the pad: open radius >= 1500 clear for the bike to circle); the playable
            areas' arena scores; on-foot vs vehicle mix along the spine; the jungle as a readable wall (roads always
            lined); optional loops (the pit, the jungle loop)
  ARTIST    the key images' look: dusk palette, a dense three-layer jungle, the Liandri prefab kit as one family,
            no single mesh more than 25 % of the props; places read as silhouettes against the sky

    py review_open.py [fps_avg fps_low]   -> review_open.md, review_open.png
"""
import json, math, os, re, sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan as S  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
OUT = os.path.join(GAME, "U2SanctuaryOpen")
WORLD, N = S.WORLD, 240
STEP = 2 * WORLD / N
FLOOR_Z = -3900
FOG_END = 20000
FOG_START = 3500
SPEED = 1100
EYE = 160


def sample(H, x, y):
    fi, fj = (x + WORLD) / STEP, (y + WORLD) / STEP
    i0, j0 = int(np.clip(np.floor(fi), 0, N - 1)), int(np.clip(np.floor(fj), 0, N - 1))
    tx, ty = fi - i0, fj - j0
    return (H[j0, i0] * (1 - tx) * (1 - ty) + H[j0, i0 + 1] * tx * (1 - ty) + H[j0 + 1, i0] * (1 - tx) * ty + H[j0 + 1, i0 + 1] * tx * ty)


def los(H, a, b, za, zb):
    for t in np.linspace(0.02, 0.98, 120):
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        if FLOOR_Z + sample(H, x, y) > za + (zb - za) * t:       # (heights.npy is above FLOOR_Z; za/zb are world Z)
            return False
    return True


def place(pid):
    return next(q for q in S.PLACES if q["id"] == pid)


def main():
    H = np.load(os.path.join(OUT, "heights.npy"))
    PL = json.load(open(os.path.join(OUT, "playable.json")))
    t3d = open(os.path.join(OUT, "open_actors.t3d")).read()
    meshes = Counter(re.findall(r"StaticMesh=StaticMesh'([^']+)'", t3d))
    fps = [float(a) for a in sys.argv[1:3]] if len(sys.argv) > 2 else [72.6, 78.6]
    R = {}

    # ------------------------------------------------ WRITER
    ch, notes, todo = {}, [], []
    order = [b[0] for b in S.BEATS]
    canon = ["lz", "road_w", "plant", "basin", "plant", "field", "pit", "power", "shaft", "pad"]
    ch["beats in order"] = 1.0 if order == canon else 0.5
    keys = [q for q in S.PLACES if q.get("key")]
    have = [q for q in keys if q["id"] in PL or q["id"] in ("basin", "shaft", "road_w")]
    ch["key places exist"] = len(have) / len(keys)
    ini = open(os.path.join(GAME, "System", "U2Sanctuary.ini"), encoding="latin1").read()
    od = ini[ini.find("[U2Sanctuary.OpenDirector]"):] if "[U2Sanctuary.OpenDirector]" in ini else ""
    story_props = sum(n for m, n in meshes.items() if re.search(r"wreck|body|corpse|Crashed|debris_sheet", m, re.I)) + \
        od.count("Bodies=(") + od.count("Props=(") + od.count("Things=(")
    ch["story props"] = min(1.0, story_props / 6)
    notes.append("%d story props (bodies, the hauler wreck, blood) on the map" % story_props)
    if story_props < 6:
        todo.append("WRITER: the silent road needs its signs - the wrecked ore hauler, bodies by the plant gate, blood trails (the U2Sanctuary director's gore scenes for this map)")
    miller = len(set(re.findall(r"Sanctuary_\d+G_\d+", od)))
    notes.append("%d of Miller's camera conversations wired to places (OpenDirector beats)" % miller)
    # the dialogue itself, by the checkable rules (games/research_notes/Dialogue heuristics; open/dialogue_check.py):
    # counting wired lines said nothing about whether they work where they now play
    import subprocess
    subprocess.run([sys.executable, os.path.join(HERE, "playlist.py")], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(HERE, "dialogue_check.py")], check=True, capture_output=True)
    dc = json.load(open(os.path.join(HERE, "dialogue_check.json")))
    for k, v in dc["scores"].items():
        ch["dialogue " + k] = v
    for rule in ("R15", "R22", "R23"):
        n = sum(1 for f_ in dc["flags"] if f_[0] == rule)
        if n:
            todo.append("WRITER: %d %s flags in open/dialogue_check.md (quote-backed edits: open/writer_pass.md)" % (n, rule))
    notes.append("dialogue checks: " + ", ".join("%s %.2f" % kv for kv in dc["scores"].items()) + " (voice/delivery: a human listening pass, not scored)")
    R["writer"] = (ch, notes)

    # ------------------------------------------------ DIRECTOR
    ch, notes = {}, []
    lz, pl = place("lz"), place("plant")
    high = [o for o in PL["plant"]["props"] if o["kind"] == "high"] or [max(PL["plant"]["props"], key=lambda o: o["h"])]
    w = high[0]
    bj = os.path.join(OUT, "beacon.json")
    if os.path.exists(bj):
        b = json.load(open(bj))
        w = {"id": "beacon mast", "x": b["x"], "y": b["y"], "h": b["h"]}
    d = math.hypot(w["x"] - lz["x"], w["y"] - lz["y"])
    za = FLOOR_Z + sample(H, lz["x"], lz["y"]) + EYE
    zb = FLOOR_Z + sample(H, w["x"], w["y"]) + w["h"]
    seen = los(H, (lz["x"], lz["y"]), (w["x"], w["y"]), za, zb)
    in_fog = d < FOG_END
    fogged = float(np.clip((d - FOG_START) / (FOG_END - FOG_START), 0, 1))
    ch["weenie from the LZ"] = (0.4 if seen else 0.0) + (0.3 if in_fog else 0.0) + (0.3 if fogged <= 0.6 else 0.3 * (1 - fogged) / 0.4)
    notes.append("the weenie stands %.0f %% into the fog (the game showed 80 %% reads as barely there; want <= 60)" % (100 * fogged))
    notes.append("the plant's %s is %.0f UU from the LZ (fog clips at %d): %s, %s" % (w["id"], d, FOG_END, "over the land" if seen else "HIDDEN by the land",
                                                                                 "inside the clip" if in_fog else "BEYOND the clip - it isn't drawn"))
    # the weenie along the climb: from where on the haul road is it drawn?
    road = next(r for r in S.ROADS if r["id"] == "haul_w")
    pts = [S.where(p) for p in road["pts"]]
    first = None
    acc = 0
    for a, b in zip(pts[:-1], pts[1:]):
        for t in np.linspace(0, 1, 20):
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            dd = math.hypot(w["x"] - p[0], w["y"] - p[1])
            if first is None and dd < FOG_END and los(H, p, (w["x"], w["y"]), FLOOR_Z + sample(H, *p) + EYE, zb):
                first = acc + math.dist(a, p)
        acc += math.dist(a, b)
    notes.append("on the haul road the weenie first shows %s" % ("after %.0f s of the %.0f s climb" % (first / SPEED, acc / SPEED) if first is not None else "never"))
    ch["weenie on the climb"] = 0.0 if first is None else float(np.clip(1 - first / acc, 0, 1))
    ch["key frames"] = len(have) / len(keys)
    sun_yaw = (math.degrees(math.atan2(pl["y"] - lz["y"], pl["x"] - lz["x"])) + 180) % 360     # the generator lights from behind the plant
    view = math.degrees(math.atan2(pl["y"] - lz["y"], pl["x"] - lz["x"]))
    off = abs((sun_yaw - view + 180) % 360 - 180)
    ch["back light"] = 1.0 if off >= 120 else off / 120
    notes.append("the sun is %.0f deg off the LZ->plant view (back light toward the plant at dusk)" % off)
    R["director"] = (ch, notes)

    # ------------------------------------------------ ENGINEER
    ch, notes = {}, []
    over = tot = 0.0
    narrow = []
    for r in S.ROADS:
        pts = [S.where(p) for p in r["pts"]]
        for a, b in zip(pts[:-1], pts[1:]):
            for t in np.linspace(0, 1, 30)[:-1]:
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                q = (a[0] + (b[0] - a[0]) * (t + 1 / 29), a[1] + (b[1] - a[1]) * (t + 1 / 29))
                ds = math.dist(p, q)
                g = abs(sample(H, *q) - sample(H, *p)) / max(ds, 1)
                tot += ds
                over += ds if g > 0.25 else 0
        if r["w"] < 1000:
            narrow.append(r["id"])
    ch["road grades"] = 1 - over / tot
    notes.append("%.0f %% of the road length over a 25 %% grade" % (100 * over / tot))
    ch["road widths"] = 1 - len(narrow) / len(S.ROADS)
    notes.append("narrower than 3 bikes: %s" % (", ".join(narrow) or "none"))
    flat = []
    for pid in ("plant", "power", "pad", "lz", "field"):
        q = place(pid)
        zs = [sample(H, q["x"] + q["r"] * 0.5 * math.cos(a), q["y"] + q["r"] * 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12)]
        flat.append(np.ptp(zs) < 150)
    ch["pads flat"] = float(np.mean(flat))
    ch["frame rate"] = float(np.clip(fps[0] / 60, 0, 1) * 0.5 + np.clip(fps[1] / 45, 0, 1) * 0.5)
    notes.append("frame rate %.0f fps avg, %.0f 1%% low (pilot, the LZ)" % tuple(fps))
    R["engineer"] = (ch, notes)

    # ------------------------------------------------ LEVEL DESIGNER
    ch, notes = {}, []
    drives = S.drive_seconds(SPEED)
    spine = ["haul_w", "haul_e", "pad_road"]
    long_ = [k for k in spine if drives[k] > 60]
    short = [k for k in spine if drives[k] < 8]
    ch["drive pacing"] = 1.0 - 0.3 * len(long_) - 0.15 * len(short)
    notes.append("spine drives: " + ", ".join("%s %.0f s" % (k, drives[k]) for k in spine))
    # the open-map pacing research (rule 1): no stretch of the spine longer than ~40 s without a contact (a beat or a fight)
    contacts = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r'Beats=\(Id="\w+",At=\(X=([-\d.]+),Y=([-\d.]+)', od)]
    gaps = []
    for k in spine:
        pts = [S.where(p) for p in next(r for r in S.ROADS if r["id"] == k)["pts"]]
        dense = []
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(2, int(math.dist(a, b) / 200))
            dense += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(n)]
        dense.append(pts[-1])
        quiet = 0.0
        for p, q in zip(dense[:-1], dense[1:]):
            quiet = 0.0 if any(math.dist(q, c) < 2600 for c in contacts) else quiet + math.dist(p, q)
            gaps.append(quiet / SPEED)
    worst = max(gaps) if gaps else 0
    ch["quiet travel <= 40 s"] = 1.0 if worst <= 40 else max(0.0, 1 - (worst - 40) / 50)
    notes.append("longest quiet stretch on the spine: %.0f s (the research's cap: 40 s)" % worst)
    # vehicle arenas: clear radius round the field / pad centres (no building or cover)
    clear = {}
    for pid in ("field", "pad"):                            # (the LZ is a foot place: the dropship stands in it)
        q = place(pid)
        ds = [max(0.0, math.hypot(o["x"] - q["x"], o["y"] - q["y"]) - o["w"] / 2) for o in PL.get(pid, {}).get("props", [])
              if o["kind"] != "cover" and o["id"] != "cargo_pad"]      # the pad's deck is ground the bike drives on
        clear[pid] = min(ds) if ds else q["r"]
    ch["vehicle arenas"] = float(np.mean([min(1.0, v / 1500) for v in clear.values()]))
    notes.append("clear radius for the bike: " + ", ".join("%s %.0f" % kv for kv in clear.items()))
    ch["arena scores"] = float(np.mean([v["score"] for v in PL.values()]))
    notes.append("playable areas: " + ", ".join("%s %.2f" % (k, v["score"]) for k, v in PL.items()))
    modes = [b[2] for b in S.BEATS]
    veh = sum(1 for m in modes if "Manta" in m or "drive" in m)
    foot = sum(1 for m in modes if "foot" in m or "swim" in m)
    ch["foot/vehicle mix"] = 1.0 if 0.3 <= veh / len(modes) <= 0.6 else 0.6
    notes.append("%d vehicle beats, %d on foot" % (veh, foot))
    ch["loops"] = min(1.0, sum(1 for r in S.ROADS if r["kind"] == "track") / 2)
    R["level"] = (ch, notes)

    # ------------------------------------------------ ARTIST
    ch, notes = {}, []
    total = sum(meshes.values())
    top, n = meshes.most_common(1)[0]
    ch["no single mesh dominates"] = float(np.clip(1 - (n / total - 0.25) / 0.25, 0, 1))
    notes.append("most used: %s, %.0f %% of %d" % (top.split(".")[-1], 100 * n / total, total))
    canopy = sum(n for m, n in meshes.items() if re.search(r"Tree1_clump1|Swamp_tree_new|swamp_tree_00", m))
    ch["jungle density"] = min(1.0, canopy / 1200)
    notes.append("%d canopy trees" % canopy)
    # one family = Sanctuary's own (the user, 2026-10-08: "base on the architecture of the previous level assets"):
    # the BSP shells in the maps' textures and Mission_08M's pieces, against foreign architecture kits
    kit = t3d.count("Class=Brush ") + sum(n for m, n in meshes.items() if m.startswith("Mission_08M"))
    other_ind = sum(n for m, n in meshes.items() if m.startswith(("AvalonSM", "MM_WaterfrontM", "Mission_SulferonM")) or
                    re.search(r"Towers\.|gas_tank", m))
    ch["one kit family"] = kit / max(1, kit + other_ind)
    ch["dusk palette"] = 1.0
    R["artist"] = (ch, notes)

    out = {k: {"score": round(float(np.mean(list(c.values()))), 2), "checks": {a: round(b, 2) for a, b in c.items()}, "notes": nt}
           for k, (c, nt) in R.items()}
    total = float(np.prod([max(1e-3, v["score"]) for v in out.values()]) ** (1 / len(out)))
    L = ["# Creative team review: Sanctuary Open", "", "**Total %.2f** (geometric mean of the five)" % total, "",
         "| role | score | checks |", "|---|---|---|"]
    for k, v in out.items():
        L.append("| %s | %.2f | %s |" % (k, v["score"], ", ".join("%s %.2f" % kv for kv in v["checks"].items())))
    for k, v in out.items():
        L += ["", "## " + k.upper()] + ["- " + n for n in v["notes"]]
    L += ["", "## What the team asks for next", ""] + ["- " + t for t in todo]
    open(os.path.join(HERE, "review_open.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"total": total, **out}, open(os.path.join(HERE, "review_open.json"), "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
