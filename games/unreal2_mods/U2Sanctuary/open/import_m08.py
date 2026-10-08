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
        # the gate conversation cut in three (cuts.json): the camera gag above, Miller's introduction once the gate's
        # Izarian is dead, the hatches to the basin once the yard is cleared
        ("gate2", gate, 2600, "Sanctuary_15G_006a", "", "", "gate!"),
        ("yard", (plant["x"], plant["y"]), 1900, "Sanctuary_18G_002,Sanctuary_16G_002", "", "yard", "gate2"),   # writer: the warning before the camera line
        ("hatches", (plant["x"], plant["y"]), 2600, "Sanctuary_15G_007", "", "", "yard!"),
        ("basin", (bx, by), 1700, "Sanctuary_10_002,Sanctuary_17G_002", "", "", "hatches"),
        ("drainage", (bx, by), 2600, "Sanctuary_20G_002", "", "drainage", "basin"),
        ("dark", (bx, by), 3200, "Sanctuary_19G_002", "", "", "drainage!"),   # writer: 22G (no security door) + its orphan 23G cut; 19G ("easy ride") moved here, inside the plant
        ("exit", pexit, 2200, "Sanctuary_98_002", "Get to the generator building", "", "dark"),
        ("field", (field["x"], field["y"]), 3600, "", "", "field", "exit"),   # writer: silent arrival, the Skaarj leap is the reveal
        ("field2", (field["x"], field["y"]), 3600, "Sanctuary_13_002", "", "", "field!"),   # Dalton's quip after the fight
        # the optional pocket (pacing research): off the spine, nests in the dig, the best cache on the map
        ("pit", (P("pit")["x"], P("pit")["y"]), 3800, "", "Optional: clear the dig site where the relic came out - the dig crew left a cache", "pit", ""),
        # writer: Miller's arrival, his death and the generator's shutdown on arrival (talk, then the Skaarj); the argument
        # with Aida and her warning after the fight; 17_003 ("Main terminal online") cut
        ("power", (power["x"], power["y"]), 3000, "Sanctuary_99_002,Sanctuary_15_001,Sanctuary_15_011", "", "power", "field"),
        ("power2", (power["x"], power["y"]), 3000, "Sanctuary_16_002,Sanctuary_18_002", "Find the generator control room", "", "power!"),
        ("shaft", (shaft["x"], shaft["y"]), 1600, "", "Reactivate the generator, retrieve the artifact", "shaft", "power2"),
        ("artifact", (shaft["x"], shaft["y"]), 2400, "Sanctuary_19_002", "Get to the pad and hold until the Marines land", "pad", "shaft!"),
        ("marines", (pad["x"], pad["y"]), 3000, "Sanctuary_XX_001", "", "", "hold"),   # after the timed hold
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
        # the hold-out: timed waves, N seconds of the player on the pad, whatever is left alive
        ("pad", "U2Izarian:3", doors("pad"), "t+5", 0.0),
        ("pad", "U2SkaarjLight:2", doors("pad", 3), "t+35", 0.0),
        ("pad", "U2Izarian:4", doors("pad", 3), "t+65", 0.0),
        ("pad", "U2SkaarjMedium:1,U2Izarian:2", doors("pad", 3), "t+95", 0.0),
        ("pad", "U2SkaarjLight:1,U2Izarian:3", doors("pad", 3), "t+120", 0.0),
    ]
    barks = "Sanctuary_16bG_002,Sanctuary_21G_002,Sanctuary_25G_002,Sanctuary_17bG_002"   # writer: 24G_002 = 16bG's "Behind you!" again
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
    # writer: the "control room" 16_008 sends Dalton to - a breaker box and a screen at the top of the shaft
    cx_, cy_ = mid((shaft["x"], shaft["y"]), (power["x"], power["y"]), 0.35)
    yaw_ = int(math.atan2(power["y"] - shaft["y"], power["x"] - shaft["x"]) * 32768 / math.pi) % 65536
    props += [("Mission_08M.M08_BControlRoomStuff.BreakerBox1", cx_, cy_, yaw_, 1.0),
              ("Mission_08M.M08_BControlRoomStuff.ScreenSkaarj1", cx_ + 120, cy_, yaw_, 1.0)]
    things = []
    for o in PL["plant"]["props"]:
        if o["kind"] == "cover" and rng.random() < 0.35:
            things.append(("U2Decorations.ExplosiveCannister", o["x"] + 140, o["y"]))   # "a lot of that stuff is unstable"
    # writer: make 18G's warning true where the yard fight is - canisters by the Izarian doors
    for s_ in PL["plant"].get("spawns", []):
        for k_ in range(3):
            a_ = rng.uniform(0, 2 * math.pi)
            things.append(("U2Decorations.ExplosiveCannister", s_["door_to"][0] + 300 * math.cos(a_), s_["door_to"][1] + 300 * math.sin(a_)))
    # supplies: cleared places become safe rooms (pacing research); the optional pit pays best
    HP, AM, SH, GL = "U2.HealthPickup", "U2.U2FullAmmoPickup", "U2.PowerSuitMediumPickup", "U2Weapons.weaponGrenadeLauncher"
    pit = P("pit")
    supplies = [
        ((lz["x"] + 900, lz["y"] + 500), "", "%s:1,%s:1" % (HP, AM), ""),
        ((plant["x"], plant["y"]), "drainage!", "%s:2,%s:2,%s:1" % (HP, AM, SH), "The plant is quiet. Supplies in the yard."),
        ((power["x"], power["y"]), "power!", "%s:2,%s:2" % (HP, AM), "Supplies at the generator building."),
        ((pit["x"], pit["y"]), "pit!", "%s:1,%s:2,%s:1,%s:1" % (GL, AM, SH, HP), "The dig crew's cache - a grenade launcher."),
        ((pad["x"] - 900, pad["y"]), "artifact", "%s:2,%s:2,%s:1" % (HP, AM, SH), "Supplies on the pad. Dig in."),
    ]
    # no bike in the boss arena and the drainage room while it's full of Izarians
    nobike = [((shaft["x"], shaft["y"]), max(1400, shaft["r"] * 0.9), ""), ((bx, by), 1800, "drainage")]
    L = ["[U2Sanctuary.OpenDirector]", "bEnabled=True", "bLog=True", "DialogDirs=PA_Sanctuary,M08A,M08B", "Barks=" + barks,
         "HiveMesh=mission_06M.Acheron.acheron_AlienPod_01", "DropMesh=Terran_DecoM.Vehicles.Terran_DropShipPod_01",
         "ShipMesh=CinemaM.Vehicles.DropshipBIGLoRes", "MaxAlive=12", "HoldBeat=artifact", "HoldSeconds=150", "HoldRadius=2400",
         "HoldAt=" + v(pad["x"], pad["y"], 0), "BarkEncounters=gate,yard,drainage"]   # writer: Miller sees only the plant
    # Miller's cameras (the writer's R23: his lines name a camera the open map didn't have): the shipped maps' own
    # CameraArm1a on the wall of the building nearest each beat he talks at, facing the beat; his voice plays from it
    import playlist
    nodes = playlist.load_nodes(["PA_Sanctuary", "M08A", "M08B"])
    L.append("CamMesh=Mission_08M.M08_BControlRoomStuff.CameraArm1a")
    for b in beats:
        ls = [l for t in b[3].split(",") if t for l in playlist.chain(nodes, t)]
        if not any(l["sound_actor"].startswith("LookTarget") for l in ls):
            continue
        bx_, by_ = b[1]
        walls = [o for pid in PL for o in PL[pid].get("props", []) if o["kind"] not in ("cover", "spawn") and o["h"] >= 250
                 and math.hypot(o["x"] - bx_, o["y"] - by_) < 3000]
        if not walls:
            # a mast by the beat, toward the plant, looking at the beat
            ax_, ay_ = plant["x"] - bx_, plant["y"] - by_
            d_ = math.hypot(ax_, ay_) or 1
            px_, py_ = bx_ + ax_ / d_ * 700, by_ + ay_ / d_ * 700
            yaw = int(math.atan2(-ay_, -ax_) * 32768 / math.pi) % 65536
            L.append('Cams=(Beat="%s",At=(X=%.0f,Y=%.0f,Z=%.0f),Yaw=%d,Post="Mission_08M.electronics.M08A_small_antenna1")' % (
                b[0], px_, py_, gz(px_, py_) + 380, yaw))
            continue
        o = min(walls, key=lambda o: math.hypot(o["x"] - bx_, o["y"] - by_))
        faces = [(o["x"] + o["w"] / 2 + 25, o["y"], 0), (o["x"] - o["w"] / 2 - 25, o["y"], 32768),
                 (o["x"], o["y"] + o["d"] / 2 + 25, 16384), (o["x"], o["y"] - o["d"] / 2 - 25, 49152)]
        fx, fy, yaw = min(faces, key=lambda f_: math.hypot(f_[0] - bx_, f_[1] - by_))
        L.append('Cams=(Beat="%s",At=(X=%.0f,Y=%.0f,Z=%.0f),Yaw=%d)' % (b[0], fx, fy, gz(o["x"], o["y"]) + o["h"] - 90, yaw))
    # dialogue cuts (cuts.json, built by make_cuts.py)
    cb = os.path.join(HERE, "cuts_built.json")
    for c in (json.load(open(cb)) if os.path.exists(cb) else []):
        L.append('Cuts=(Node="%s",Op="%s",To="%s",Text="%s",File="%s",Secs=%.2f)' % (
            c["node"], c["op"], c.get("to", ""), c.get("text", "").replace('"', "'"), c.get("file", ""), c.get("secs", 0)))
    for (x, y), after, items, msg in supplies:
        L.append('Supplies=(At=%s,After="%s",Items="%s",Message="%s")' % (v(x, y, 40), after, items, msg))
    for (x, y), r, enc in nobike:
        L.append('NoBike=(At=%s,Radius=%.0f,Encounter="%s")' % (v(x, y), r, enc))
    bj = os.path.join(OUT, "beacon.json")
    if os.path.exists(bj):
        b = json.load(open(bj))
        L.append("BeaconAt=(X=%.0f,Y=%.0f,Z=%.0f)" % (b["x"], b["y"], gz(b["x"], b["y"]) + b["h"] + 150))
    for b in beats:
        L.append('Beats=(Id="%s",At=%s,Radius=%.0f,Topics="%s",Objective="%s",Encounter="%s",After="%s")' % (
            b[0], v(b[1][0], b[1][1], 100), b[2], b[3], b[4], b[5], b[6]))
    for w in waves:
        L.append('Waves=(Encounter="%s",Pawns="%s",Doors="%s",When="%s",Delay=%.1f)' % w)
    for c, x, y, yaw in bodies:
        L.append('Bodies=(Kind="U2Pawns.%s",At=%s,Yaw=%d)' % (c, v(x, y, 90), yaw))
    for m, x, y, yaw, s in props:
        L.append('Props=(Mesh="%s",At=%s,Yaw=%d,Scale=%.2f)' % (m, v(x, y, 0), yaw, s))
    for c, x, y in things:
        L.append('Things=(Kind="%s",At=%s)' % (c, v(x, y, 40)))
    # merge into the ini, replacing only this section
    txt = open(INI, encoding="utf-8").read() if os.path.exists(INI) else ""
    txt = re.sub(r"\[U2Sanctuary\.OpenDirector\].*?(?=\n\[|\Z)", "", txt, flags=re.S).rstrip() + "\n\n"
    open(INI, "w", newline="\r\n").write(txt + "\n".join(L) + "\n")
    print("%d beats, %d waves, %d bodies, %d props, %d canisters -> %s" % (len(beats), len(waves), len(bodies), len(props), len(things), INI))


if __name__ == "__main__":
    main()
