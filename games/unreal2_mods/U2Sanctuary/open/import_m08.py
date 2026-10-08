r"""Import the shipped Sanctuary maps' story beats, encounters and story props into Sanctuary Open (the user,
2026-10-08: "lets import the levels props and story beats and encounters").

What is imported, from what:
  BEATS       the original conversations (Dialog\PA_Sanctuary, M08A, M08B: Aida, Dalton, Miller on the one-way
              cameras, the generator terminal, the Marines), in the canon order (STORY.md), each fired when the
              player reaches its place on the open map; the level objectives (System\M08a1/M08b.int) as status lines
  ENCOUNTERS  the three maps' fights (review/M08*_arenas.md line-ups: Izarians in A1/A2, the first Skaarj in A2,
              the Medium and Heavy Skaarj in B), re-paced as waves out of the playable areas' spawn sheds, held
              until the player arrives (SevenSanctuary's hold-and-release): each kind's first meeting alone (the
              level designer's "teach"), later waves mixing shooters and rushers (the review's combined arms)
  PROPS       the dead colonists (the maps' U2CivilianScientist / U2ColonistHumanMaleA bodies, now killed where they
              lie so U2Gore pools them), the "unstable stuff" (A1's U2Decorations.ExplosiveCannister), the wrecked
              ore hauler on the silent road (Mission_05M's Crashed_Transport, spawned at run time: map-imported it
              doesn't draw - U2Prairie)

    py import_m08.py      -> ../System/U2Sanctuary.ini [U2Sanctuary.OpenDirector] (merged; the other sections kept)
"""
import json, math, os, re, sys
# pacing: games/research_notes/Open map encounter pacing/report.md - a contact every <= 40 s of travel, waves at
# 25-50 % alive or after 60 s, 30-45 s of rest after a fight, <= 12 enemies near the player (OpenDirector enforces the
# timer and the rest)

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan as S  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
OUT = os.path.join(GAME, "U2SanctuaryOpen")
INI = os.path.join(HERE, "..", "System", "U2Sanctuary.ini")
FLOOR_Z = -3900
H = np.load(os.path.join(OUT, "heights.npy"))
PL = json.load(open(os.path.join(OUT, "playable.json")))
N, WORLD = 240, S.WORLD
STEP = 2 * WORLD / N


def gz(x, y):
    fi, fj = (x + WORLD) / STEP, (y + WORLD) / STEP
    i0, j0 = int(np.clip(np.floor(fi), 0, N - 1)), int(np.clip(np.floor(fj), 0, N - 1))
    tx, ty = fi - i0, fj - j0
    return FLOOR_Z + (H[j0, i0] * (1 - tx) * (1 - ty) + H[j0, i0 + 1] * tx * (1 - ty) + H[j0 + 1, i0] * (1 - tx) * ty + H[j0 + 1, i0 + 1] * tx * ty)


BUILT = json.load(open(os.path.join(OUT, "places.json"))) if os.path.exists(os.path.join(OUT, "places.json")) else S.PLACES


def P(pid):
    return next(q for q in BUILT if q["id"] == pid)


def v(x, y, up=0):
    return "(X=%.0f,Y=%.0f,Z=%.0f)" % (x, y, gz(x, y) + up)


def entry(pid, k=0):
    e = PL[pid]["entries"][k]["at"]
    return e[0], e[1]


def doors(pid, n_far=2):
    """the spawn sheds' doors (playable.json); places without sheds get points on the far side of the centre"""
    q = P(pid)
    out = []
    for s in PL.get(pid, {}).get("spawns", []):
        dx, dy = s["door_to"][0] - s["x"], s["door_to"][1] - s["y"]
        d = math.hypot(dx, dy) or 1
        out.append((s["x"] + dx / d * 450, s["y"] + dy / d * 450))
    if not out:
        ex, ey = entry(pid) if PL.get(pid, {}).get("entries") else (q["x"] - q["r"], q["y"])
        a = math.atan2(q["y"] - ey, q["x"] - ex)
        for k in range(n_far):
            b = a + (k - (n_far - 1) / 2) * 0.6
            out.append((q["x"] + math.cos(b) * q["r"] * 0.55, q["y"] + math.sin(b) * q["r"] * 0.55))
    return ";".join("%.0f,%.0f,%.0f" % (x, y, gz(x, y) + 120) for x, y in out)


def mid(a, b, t=0.5):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def main():
    plant, field, power, shaft, pad, lz, basin = (P(i) for i in ("plant", "field", "power", "shaft", "pad", "lz", "basin"))
    road = [S.where(p) for p in next(r for r in S.ROADS if r["id"] == "haul_w")["pts"]]
    rmid = mid(road[1], road[2])
    gate = entry("plant", 0)
    pexit = entry("plant", 1) if len(PL["plant"]["entries"]) > 1 else (plant["x"] - 2000, plant["y"] - 2000)
    # the basin's real spot (make_open.py moves it to the lowest hollow near the plant)
    bx, by = basin["x"], basin["y"]
    beats = [
        # Id, at (x, y), radius, topics, objective, encounter, after
        ("arrival", (lz["x"], lz["y"]), 2500, "Sanctuary_06_001", "Investigate the installation on Sanctuary to discover the cause of the distress call", "", ""),
        ("road", rmid, 2600, "", "", "road", "arrival"),       # a roadblock by the hauler wreck: the drive gets its contact (pacing research rule 1)
        ("gate", gate, 2600, "Sanctuary_15G_002", "Rescue Miller", "gate", "arrival"),
        ("yard", (plant["x"], plant["y"]), 1900, "Sanctuary_16G_002,Sanctuary_18G_002", "", "yard", "gate"),
        ("basin", (bx, by), 1700, "Sanctuary_10_002,Sanctuary_17G_002", "", "", "yard"),
        ("drainage", (bx, by), 2600, "Sanctuary_20G_002", "", "drainage", "basin"),
        ("dark", (bx, by), 3200, "Sanctuary_22G_002,Sanctuary_23G_002", "", "", "drainage!"),
        ("exit", pexit, 2200, "Sanctuary_98_002", "Get to the generator building", "", "dark"),
        ("field", (field["x"], field["y"]), 3600, "Sanctuary_19G_002,Sanctuary_13_002", "", "field", "exit"),
        ("pit", (P("pit")["x"], P("pit")["y"]), 3800, "", "", "pit", ""),
        ("power", (power["x"], power["y"]), 3000, "Sanctuary_99_002,Sanctuary_15_001,Sanctuary_16_002", "Find the generator control room", "power", "field"),
        ("shaft", (shaft["x"], shaft["y"]), 1600, "Sanctuary_18_002,Sanctuary_17_003", "Reactivate the generator, retrieve the artifact", "shaft", "power!"),
        ("artifact", (shaft["x"], shaft["y"]), 2400, "Sanctuary_19_002", "Get to the pad and hold until the Marines land", "pad", "shaft!"),
        ("marines", (pad["x"], pad["y"]), 3000, "Sanctuary_XX_001", "", "", "artifact!"),
    ]
    # "X!" = after encounter X's last wave is cleared (not just after its beat fired)
    waves = [
        # encounter, pawns (Class:count,...), doors, when (enter | cleared | lasthalf), delay
        ("road", "U2Izarian:2", "%.0f,%.0f,%.0f;%.0f,%.0f,%.0f" % (rmid[0] + 1400, rmid[1] - 900, gz(rmid[0] + 1400, rmid[1] - 900) + 120,
                                                              rmid[0] + 1800, rmid[1] - 300, gz(rmid[0] + 1800, rmid[1] - 300) + 120), "enter", 1.0),
        ("gate", "U2Izarian:1", doors("plant"), "enter", 2.0),                       # teach: one Izarian, alone
        ("yard", "U2Izarian:3", doors("plant"), "enter", 1.0),
        ("yard", "U2Izarian:3", doors("plant"), "lasthalf", 1.5),                    # reinforcements before the last falls
        ("drainage", "U2Izarian:5", doors("plant", 3), "enter", 1.0),               # "chock-full of those creatures"
        ("field", "U2SkaarjLight:1", doors("field"), "enter", 4.0),                  # TheSkaarjEncounter: one, in the open
        ("field", "U2SkaarjLight:2,U2Izarian:2", doors("field"), "cleared", 6.0),    # combined arms
        ("pit", "U2Izarian:4", doors("pit"), "enter", 1.0),
        ("power", "U2SkaarjMedium:1", doors("power"), "enter", 3.0),                 # teach the Medium alone
        ("power", "U2Izarian:2,U2SkaarjLight:1", doors("power"), "cleared", 4.0),
        ("shaft", "U2SkaarjHeavy:1", doors("shaft", 1), "enter", 2.0),               # the end boss, alone first
        ("shaft", "U2Izarian:2", doors("power"), "lasthalf", 2.0),
        ("pad", "U2Izarian:3", doors("pad"), "enter", 8.0),                          # the hold-out
        ("pad", "U2SkaarjLight:2,U2Izarian:2", doors("pad", 3), "cleared", 6.0),
        ("pad", "U2SkaarjMedium:1,U2Izarian:2", doors("pad", 3), "cleared", 6.0),
    ]
    barks = "Sanctuary_16bG_002,Sanctuary_21G_002,Sanctuary_24G_002,Sanctuary_25G_002,Sanctuary_17bG_002"
    rng = np.random.default_rng(3)
    bodies = []

    def scatter(cx, cy, n, r, cls="U2CivilianScientist"):
        for _ in range(n):
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(r * 0.3, r)
            bodies.append((cls, cx + d * math.cos(a), cy + d * math.sin(a), int(rng.uniform(0, 65535))))
    scatter(rmid[0] + 300, rmid[1], 3, 500, "U2ColonistHumanMaleA")         # the hauler's crew
    scatter(gate[0], gate[1], 3, 700)                                       # they ran for the gate
    scatter(plant["x"], plant["y"], 3, 1200)
    scatter(bx, by, 2, 500)
    scatter(field["x"], field["y"], 2, 2500, "U2ColonistHumanMaleA")
    scatter(power["x"], power["y"], 2, 900)
    props = [("Mission_05M.debris_sheet_003.Crashed_Transport", rmid[0], rmid[1], 9000, 1.0)]
    things = []
    for o in PL["plant"]["props"]:
        if o["kind"] == "cover" and rng.random() < 0.35:
            things.append(("U2Decorations.ExplosiveCannister", o["x"] + 140, o["y"]))   # "a lot of that stuff is unstable"
    L = ["[U2Sanctuary.OpenDirector]", "bEnabled=True", "bLog=True", "DialogDirs=PA_Sanctuary,M08A,M08B", "Barks=" + barks]
    for b in beats:
        L.append('Beats=(Id="%s",At=%s,Radius=%.0f,Topics="%s",Objective="%s",Encounter="%s",After="%s")' % (
            b[0], v(b[1][0], b[1][1], 100), b[2], b[3], b[4], b[5], b[6]))
    for w in waves:
        L.append('Waves=(Encounter="%s",Pawns="%s",Doors="%s",When="%s",Delay=%.1f)' % w)
    for c, x, y, yaw in bodies:
        L.append('Bodies=(Class="U2Pawns.%s",At=%s,Yaw=%d)' % (c, v(x, y, 90), yaw))
    for m, x, y, yaw, s in props:
        L.append('Props=(Mesh="%s",At=%s,Yaw=%d,Scale=%.2f)' % (m, v(x, y, 0), yaw, s))
    for c, x, y in things:
        L.append('Things=(Class="%s",At=%s)' % (c, v(x, y, 40)))
    # merge into the ini, replacing only this section
    txt = open(INI, encoding="utf-8").read() if os.path.exists(INI) else ""
    txt = re.sub(r"\[U2Sanctuary\.OpenDirector\].*?(?=\n\[|\Z)", "", txt, flags=re.S).rstrip() + "\n\n"
    open(INI, "w", newline="\r\n").write(txt + "\n".join(L) + "\n")
    print("%d beats, %d waves, %d bodies, %d props, %d canisters -> %s" % (len(beats), len(waves), len(bodies), len(props), len(things), INI))


if __name__ == "__main__":
    main()
