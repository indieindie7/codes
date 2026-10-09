r"""The remake's fights for AvalonDirector (U2Sanctuary): U2AvalonFights.ini [U2Sanctuary.AvalonDirector].

    py tools/avalon_fights.py <run folder> [out=<game>\System\U2AvalonFights.ini] [patch=patch2]

The greybox arenas E1-E4 as built into the map (remake_arenas.t3d: the Arena_<id>_spawn / _P nodes) with the plan's
casts (redesign/2026-10-09/plan.md s.5: E1 Rook's smugglers + a Medium from the boat; E2 security, 2 Light + a Heavy
on the checkpoint roof; E3 mercs at the hut door + 2 SkaarjLight; E4 Skaarj by drop pod + one charging the stair).
A beat per arena fires when the player comes within Radius of the arena's middle and starts its waves; mercs step out
of the spawn points (no hive), Skaarj come down in drop pods there. Each cleared arena lays out health + ammo at its
P (the player's way in). Z = the ground (+ the terrain patch's lift) + 100.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_export  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
run = sys.argv[1]
o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
gz = story_export.ground_fn(os.path.join(run, "isl_ec.bmp"))

lift = lambda x, y: 0.0
pp = os.path.join(run, o.get("patch", "patch2"))
if os.path.exists(pp + ".json"):
    import numpy as np
    info = json.load(open(pp + ".json"))
    n, cell = info["n"], info["TerrainScale"][0]
    PZ = np.frombuffer(open(pp + ".bmp", "rb").read()[54:54 + n * n * 2], dtype="<u2").reshape(n, n)[::-1].astype(float)
    PZ = info["Location"][2] + (PZ - 32768) * info["TerrainScale"][2] / 256

    def lift(x, y):
        fi, fj = (x - info["Location"][0]) / cell + n / 2, (y - info["Location"][1]) / cell + n / 2
        if not (0 <= fi < n - 1 and 0 <= fj < n - 1):
            return 0.0
        i, j = int(fi), int(fj)
        u, v = fi - i, fj - j
        z = PZ[j, i] * (1 - u) * (1 - v) + PZ[j, i + 1] * u * (1 - v) + PZ[j + 1, i] * (1 - u) * v + PZ[j + 1, i + 1] * u * v
        return max(0.0, z - gz(x, y))

nodes = {}
for b in re.findall(r"Begin Actor Class=PathNode.*?End Actor", open(os.path.join(run, "remake_arenas.t3d")).read(), re.S):
    tag = re.search(r"Tag=(\w+)", b).group(1)
    x, y = map(float, re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+)", b).groups())
    nodes.setdefault(tag, []).append((x, y))
L = json.load(open(os.path.join(run, "isl_layout.json")))


def pt(x, y, up=100):
    return "(X=%.0f,Y=%.0f,Z=%.0f)" % (x, y, gz(x, y) + lift(x, y) + up)


def doors(aid, extra=()):
    pts = nodes.get("Arena_%s_spawn" % aid, []) + list(extra)
    return ";".join("%.0f,%.0f,%.0f" % (x, y, gz(x, y) + lift(x, y) + 100) for x, y in pts)


def piece_spawns(aid, word):
    """spawn pieces of the arena plan whose label has `word` (the sea-side ones the build left out included)"""
    return [(p["x"], p["y"]) for p in L["arenas"][aid]["pieces"] if p["kind"] == "spawn" and word in p["label"].lower()
            and gz(p["x"], p["y"]) > story_export.SEA_Z + 40]


CAST = {   # arena: [(pawns, when, delay, door source)]
    "E1": [("U2MercJapLight:3", "enter", 1, None), ("U2MercJapMedium:1", "lasthalf", 10, "boat")],
    "E2": [("U2MercJapLight:2", "enter", 1, None), ("U2MercJapHeavy:1", "lasthalf", 4, "heavy")],
    "E3": [("U2MercJapLight:3", "enter", 1, None), ("U2SkaarjLight:2", "lasthalf", 6, "skaarj")],
    "E4": [("U2SkaarjLight:2", "enter", 2, None), ("U2SkaarjMedium:1", "lasthalf", 5, "berserker")],
}
NAMES = {"E1": "the dock yard", "E2": "the dorm square", "E3": "the cooling basin", "E4": "the company gate"}

lines = ["[U2Sanctuary.AvalonDirector]", "bEnabled=True", "bLog=True", "DialogDirs=", "Barks=", "HiveMesh=",
         "DropMesh=Terran_DecoM.Vehicles.Terran_DropShipPod_01", "DropHealth=400", "DropScale=1.0", "MaxAlive=8",
         "WaveTimeout=60", "RestAfterFight=15", "StoryAfterFight=4", "BarkCooldown=60", "FightRadius=3000", "HoldBeat="]
for aid, cast in CAST.items():
    A = L["arenas"][aid]
    cx, cy = A["centre"]
    P = nodes.get("Arena_%s_P" % aid, [(cx, cy)])[0]
    # the fight starts at the arena's way in (P), not its middle: E1's middle is 19 m from the PlayerStart since the
    # arena slide (anchors 3b315e5), a middle trigger would start it on spawn
    lines.append('Beats=(Id="%s",At=%s,Radius=500,Topics="",Objective="",Encounter="%s",After="")' % (aid, pt(P[0], P[1]), aid))
    for pawns, when, delay, src in cast:
        extra = piece_spawns(aid, src) if src else ()
        d = doors(aid, extra) if not src else (";".join("%.0f,%.0f,%.0f" % (x, y, gz(x, y) + lift(x, y) + 100) for x, y in extra) or doors(aid))
        lines.append('Waves=(Encounter="%s",Pawns="%s",Doors="%s",When="%s",Delay=%d)' % (aid, pawns, d, when, delay))
    lines.append('Supplies=(At=%s,After="%s!",Items="U2.HealthPickup:2,U2.U2FullAmmoPickup:1",Message="%s is quiet. Supplies by the way in.")'
                 % (pt(P[0], P[1], 60), aid, NAMES[aid][0].upper() + NAMES[aid][1:]))
# I2, the production line in hall_b (plan s.5 stop 3: 4 Light + a Medium on the gantry + a Heavy at the end): inside
# the hollow shell, so the points come from rooms.json in the hall's own frame (both gable ends, the mezzanine)
if o.get("indoor", "1") == "1":
    import binder, shells  # noqa
    R = json.load(open(os.path.join(run, "rooms.json")))
    _, sheets = binder.load()
    hp = R["hall_b"]
    S = shells.Shell(hp, sheets["hall_b"], shells.instances("hall_b", L["buildings"]["hall_b"], sheets["hall_b"])[0])
    W = hp["shell_m"][0]
    mz = next(r for r in hp["rooms"] if r["id"] == "mezzanine")
    at = lambda x, y, z: "%.0f,%.0f,%.0f" % (lambda w: (w[0], w[1], w[2] + 150))(S.world_of(x, y, z))
    ends = ";".join(at(sx * (W / 2 - 4), dy, 0) for sx in (1, -1) for dy in (-4, 4))
    cx, cy, cz = S.world_of(0, 0, 0)
    lines += ['Beats=(Id="I2",At=(X=%.0f,Y=%.0f,Z=%.0f),Radius=900,Topics="",Objective="",Encounter="I2",After="")' % (cx, cy, cz + 100),
              'Waves=(Encounter="I2",Pawns="U2MercJapLight:4",Doors="%s",When="enter",Delay=2)' % ends,
              'Waves=(Encounter="I2",Pawns="U2MercJapMedium:1",Doors="%s",When="lasthalf",Delay=3)' % at(10, mz["y"], mz["z"]),
              'Waves=(Encounter="I2",Pawns="U2MercJapHeavy:1",Doors="%s",When="cleared",Delay=4)' % at(W / 2 - 4, 0, 0),
              'Supplies=(At=(X=%.0f,Y=%.0f,Z=%.0f),After="I2!",Items="U2.HealthPickup:2,U2.U2FullAmmoPickup:1",Message="The production line is quiet. Supplies on the floor.")' % (cx, cy, cz + 80)]
out = o.get("out", os.path.join(GAME, "System", "U2AvalonFights.ini"))
open(out, "w", newline="\r\n").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("->", out)
