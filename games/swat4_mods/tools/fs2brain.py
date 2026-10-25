"""Our side of the FS2 gym: plans team 1 each turn through the smbridge.

  brain = fs2brain.BRAINS["rush"]; brain(fs2brain.units())  # before spSubmitTurn()

units() reads every unit id (1..15) in one bridge call: team (getTeamOfPlayerWithId,
1/2, 0 = no unit), alive (getUnitIdIsAlive), pos (getPosOfPlayerWithId). Ids per
team vary by map, so never assume 1-4 = team 1. Moves go in with
planAddWaypoint(0, id, x, y, 0) (verified 10-24: 2nd arg = unit id, 0 for the rest).
Brains: idle (no plans, the old soak baseline), rush (each unit to the nearest
enemy), pairs (units pair up; the leader goes for the nearest enemy, the buddy
follows a step behind so both arrive together).
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs2soak import ask, run

TEAM = 1  # Charon plans team 2


def units():
    s = ask("%s", '%s=""; for(%i=1;%i<16;%i++) %s=%s @ %i SPC getTeamOfPlayerWithId(%i) SPC '
                  'getUnitIdIsAlive(%i) SPC getPosOfPlayerWithId(%i) @ ";";', 60)
    out = []
    for rec in s.split(";"):
        f = rec.split()
        if len(f) == 5 and f[1] in ("1", "2"):
            out.append(dict(id=int(f[0]), team=int(f[1]), alive=f[2] == "1", x=float(f[3]), y=float(f[4])))
    return out


def _go(moves):
    if moves:
        run(" ".join(f"planAddWaypoint(0, {i}, {x:.1f}, {y:.1f}, 0);" for i, x, y in moves))


def _near(u, others):
    return min(others, key=lambda o: math.hypot(o["x"] - u["x"], o["y"] - u["y"]))


def idle(us):
    pass


def rush(us):
    mine = [u for u in us if u["team"] == TEAM and u["alive"]]
    foes = [u for u in us if u["team"] != TEAM and u["alive"]]
    if foes:
        _go([(u["id"], *(lambda e: (e["x"], e["y"]))(_near(u, foes))) for u in mine])


def pairs(us):
    mine = sorted((u for u in us if u["team"] == TEAM and u["alive"]), key=lambda u: u["id"])
    foes = [u for u in us if u["team"] != TEAM and u["alive"]]
    if not foes:
        return
    moves = []
    for k in range(0, len(mine), 2):
        lead, buddy = mine[k], (mine[k + 1] if k + 1 < len(mine) else None)
        e = _near(lead, foes)
        moves.append((lead["id"], e["x"], e["y"]))
        if buddy:  # 60 units behind the leader's goal, on the leader's approach line
            d = math.hypot(e["x"] - lead["x"], e["y"] - lead["y"]) or 1
            moves.append((buddy["id"], e["x"] - 60 * (e["x"] - lead["x"]) / d, e["y"] - 60 * (e["y"] - lead["y"]) / d))
    _go(moves)


BRAINS = dict(idle=idle, rush=rush, pairs=pairs)

if __name__ == "__main__":
    for u in units():
        print(u)
