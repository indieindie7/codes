"""Our side of the FS2 gym: plans team 1 each turn through the smbridge.

  brain = fs2brain.BRAINS["rush"]; brain(fs2brain.units())  # before spSubmitTurn()

units() reads every unit id (1..15) in one bridge call: team (getTeamOfPlayerWithId,
1/2, 0 = no unit), alive (getUnitIdIsAlive), pos (getPosOfPlayerWithId). Ids per
team vary by map, so never assume 1-4 = team 1. Moves go in with
planNavigateTo(0, id, x, y) (10-30; planAddWaypoint is a straight line and gets stuck on walls).
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


# order call template. 10-30: planAddWaypoint is a straight line, units stop at the first wall (looked like "orders only act on turn 0");
# planNavigateTo(0, id, x, y) paths around walls. FS2_WP overrides for probes
WP = os.environ.get("FS2_WP", "planNavigateTo(0, {i}, {x}, {y});")
LAST = []  # orders sent this turn: (id, x, y)


def _go(moves):
    LAST[:] = moves
    if moves:
        run(" ".join(WP.format(i=i, x=f"{x:.1f}", y=f"{y:.1f}") for i, x, y in moves))


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


# ---- SwatMinds ideas (10-29): focus fire, bounding pairs, zone hunt ----
STEP = float(os.environ.get("FS2_STEP", 350))   # one bound per turn
SIGHT = 900.0  # no-cheat sight radius: foes farther than this from every friend are "unknown"
_mem = dict(turn=0, last=None, visited=set(), bbox=None)


def reset():
    _mem.update(turn=0, last=None, visited=set(), bbox=None)


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _toward(u, g, step):
    d = _d((u["x"], u["y"]), g) or 1
    k = min(1.0, step / d)
    return u["x"] + (g[0] - u["x"]) * k, u["y"] + (g[1] - u["y"]) * k


def _split(us):
    mine = sorted((u for u in us if u["team"] == TEAM and u["alive"]), key=lambda u: u["id"])
    foes = [u for u in us if u["team"] != TEAM and u["alive"]]
    return mine, foes


def focus(us):
    """All units to the one foe nearest the squad centroid: shots land together."""
    mine, foes = _split(us)
    if not (mine and foes):
        return
    c = (sum(u["x"] for u in mine) / len(mine), sum(u["y"] for u in mine) / len(mine))
    t = min(foes, key=lambda e: _d(c, (e["x"], e["y"])))
    _go([(u["id"], t["x"], t["y"]) for u in mine])


def bound(us, tgt=None):
    """Pairs leapfrog: per turn one of each pair advances a bound, the other holds
    (overwatch). Roles flip every turn. Lone unit just advances."""
    mine, foes = _split(us)
    tgt = tgt or [(e["x"], e["y"]) for e in foes]
    if not (mine and tgt):
        return
    moves = []
    for k in range(0, len(mine), 2):
        a, b = mine[k], (mine[k + 1] if k + 1 < len(mine) else None)
        mover, holder = (a, b) if (_mem["turn"] + k // 2) % 2 == 0 else (b, a)
        if mover is None:
            mover, holder = holder, None
        g = min(tgt, key=lambda p: _d((mover["x"], mover["y"]), p))
        moves.append((mover["id"], *_toward(mover, g, STEP)))
        if holder:  # hold = re-plan own position (no drift)
            moves.append((holder["id"], holder["x"], holder["y"]))
    _go(moves)
    _mem["turn"] += 1


def _cell(x, y):
    x0, y0, x1, y1 = _mem["bbox"]
    return min(2, max(0, int(3 * (y - y0) / ((y1 - y0) or 1)))) * 3 + min(2, max(0, int(3 * (x - x0) / ((x1 - x0) or 1))))


def _cellctr(c):
    x0, y0, x1, y1 = _mem["bbox"]
    return x0 + (x1 - x0) * (c % 3 + .5) / 3, y0 + (y1 - y0) * (c // 3 + .5) / 3


def hunt(us):
    """No-cheat zone hunt. Foes count only within SIGHT of a friend. Seen: bounding
    pairs at them, last contact remembered. Unseen: sweep last contact, then the
    unvisited cells of a 3x3 grid over the extent of the units."""
    mine, foes = _split(us)
    if not mine:
        return
    if _mem["bbox"] is None:
        xs, ys = [u["x"] for u in us], [u["y"] for u in us]
        _mem["bbox"] = (min(xs) - 300, min(ys) - 300, max(xs) + 300, max(ys) + 300)
    seen = [(e["x"], e["y"]) for e in foes if any(_d((e["x"], e["y"]), (m["x"], m["y"])) <= SIGHT for m in mine)]
    for m in mine:
        _mem["visited"].add(_cell(m["x"], m["y"]))
    if seen:
        _mem["last"] = seen[0]
        return bound(us, seen)
    goals = [_cellctr(c) for c in range(9) if c not in _mem["visited"]]
    if _mem["last"]:
        if _d(_mem["last"], (mine[0]["x"], mine[0]["y"])) < 250:
            _mem["last"] = None
        else:
            goals.insert(0, _mem["last"])
    if not goals:
        _mem["visited"].clear()
        goals = [_cellctr(c) for c in range(9)]
    bound(us, goals)


def mass(us):
    """Arrive together: if the squad is spread wider than SPREAD, everyone steps to the centroid
    (nearest-to-centroid unit holds); once massed, all advance a short step on the nearest foe."""
    mine, foes = _split(us)
    if not (mine and foes):
        return
    c = (sum(u["x"] for u in mine) / len(mine), sum(u["y"] for u in mine) / len(mine))
    if max(_d(c, (u["x"], u["y"])) for u in mine) > SPREAD:
        return _go([(u["id"], *_toward(u, c, 2 * STEP)) for u in mine])
    t = min(foes, key=lambda e: _d(c, (e["x"], e["y"])))
    _go([(u["id"], *_toward(u, (t["x"], t["y"]), STEP)) for u in mine])


SPREAD = 450.0
BRAINS = dict(mass=mass, idle=idle, rush=rush, pairs=pairs, focus=focus, bound=bound, hunt=hunt)

if __name__ == "__main__":
    for u in units():
        print(u)
