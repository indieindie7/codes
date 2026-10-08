r"""A modular kit on a grid, built from U2Model shapes (the research's top pick: games/research_notes/3D modelling for
the UE2 editor, "Modular kit with grid metrics"): every piece fits one 512 x 512 cell, one 384 storey, so pieces snap
in any of the 4 turns, stack, and loop back. Level generators place them as static meshes (no CSG, no BSP holes).

    from kit import PIECES, building
    PIECES["wall_door"]()            -> a Model (origin = the cell's centre, on its floor; walls on the cell's -y edge)
    plan = building(["##.", "###"], doors={(0, 1, "s")}, windows={(2, 1, "n")}, storeys=1)
    plan -> [(piece, (x, y, z), yaw_deg)]  placements; plan_model(plan) -> one Model of it (preview / brushes)
"""
import math

from u2model import box, stairs, wedge, cylinder, Model

CELL, STOREY, WALL, SLAB = 512, 384, 32, 32
DOOR_W, DOOR_H, WIN_W, WIN_H, SILL = 160, 256, 192, 128, 128
WALLTEX = "Mission_06T.Surface_Wall.MetlWall_U06A500"
BASETEX = "Mission_06T.Surface_Wall.MetlBase_U06B459b"
FLOORTEX = "Mission_06T.Surface_Floor.MetlFloor_U06B500"
H = CELL / 2


def _wall_slab():
    """the wall on the cell's -y edge, inside the cell, from the floor slab to the storey top"""
    return box(CELL, WALL, STOREY).move(0, -H + WALL / 2, 0).textured(WALLTEX, 2)


def floor():
    return Model([("add", box(CELL, CELL, SLAB).move(0, 0, -SLAB).textured(FLOORTEX, 2))])


def ceiling():
    return Model([("add", box(CELL, CELL, SLAB).move(0, 0, STOREY).textured(BASETEX, 2))])


def wall():
    return Model([("add", _wall_slab())])


def wall_door():
    return _wall_slab() - box(DOOR_W, WALL * 3, DOOR_H).move(0, -H + WALL / 2, 0).textured(BASETEX, 2)   # a cut's faces take its texture


def wall_window():
    return _wall_slab() - box(WIN_W, WALL * 3, WIN_H).move(0, -H + WALL / 2, SILL).textured(BASETEX, 2)


def pillar():
    """the corner post at the cell's (-x, -y) corner (covers wall ends meeting there)"""
    return Model([("add", box(WALL * 2, WALL * 2, STOREY).move(-H + WALL, -H + WALL, 0).textured(BASETEX, 2))])


def stairs_up():
    """one storey up inside the cell, climbing toward +y along the cell's +x side"""
    n = 12
    return Model([("add", stairs(CELL / 2, n, rise=STOREY / n, run=(CELL - 32) / n).rotate(yaw=90).move(H / 2, -H + 16, 0).textured(BASETEX, 2))])


def ramp():
    """half a storey up across the cell (toward +x)"""
    return Model([("add", wedge(CELL, CELL, STOREY / 2).textured(FLOORTEX, 2))])


def railing():
    """a railing on the cell's -y edge (for an open edge upstairs)"""
    m = Model([("add", box(CELL, 16, 16).move(0, -H + 8, 96).textured(BASETEX, 1))])
    for k in range(5):
        m += cylinder(6, 96, 6).move(-H + 32 + k * (CELL - 64) / 4, -H + 8, 0).textured(BASETEX, 1)
    return m


PIECES = {"floor": floor, "ceiling": ceiling, "wall": wall, "wall_door": wall_door, "wall_window": wall_window,
          "pillar": pillar, "stairs_up": stairs_up, "ramp": ramp, "railing": railing}
SIDES = {"s": 0, "e": 90, "n": 180, "w": 270}            # the edge a wall piece sits on -> its yaw (it's built on -y = s)
STEP = {"s": (0, -1), "e": (1, 0), "n": (0, 1), "w": (-1, 0)}


def building(rows, doors=(), windows=(), storeys=1, roof=True):
    """rows: strings, '#' = a filled cell (row 0 = north/top, +y up); doors/windows: {(col, row, side)} on outside
    edges. Returns placements [(piece, (x, y, z), yaw)] with the grid's (0, 0) cell centred at the origin."""
    cells = {(c, len(rows) - 1 - r) for r, line in enumerate(rows) for c, ch in enumerate(line) if ch == "#"}
    def gy(c, r_row):                    # doors given in row-from-top terms -> grid y
        return len(rows) - 1 - r_row
    D = {(c, gy(c, r), s) for c, r, s in doors}
    W = {(c, gy(c, r), s) for c, r, s in windows}
    out = []
    for lvl in range(storeys):
        z = lvl * (STOREY + SLAB)
        for (c, r) in sorted(cells):
            x, y = c * CELL, r * CELL
            out.append(("floor", (x, y, z), 0))
            if roof and lvl == storeys - 1:
                out.append(("ceiling", (x, y, z), 0))
            for side, (dx, dy) in STEP.items():
                if (c + dx, r + dy) in cells:
                    continue
                piece = "wall_door" if (lvl == 0 and (c, r, side) in D) else "wall_window" if (c, r, side) in W else "wall"
                out.append((piece, (x, y, z), SIDES[side]))
            # a post at each outside corner of the cell (where two outside walls meet)
            for side_a, side_b, yaw in (("s", "w", 0), ("e", "s", 90), ("n", "e", 180), ("w", "n", 270)):
                (ax, ay), (bx, by) = STEP[side_a], STEP[side_b]
                if (c + ax, r + ay) not in cells and (c + bx, r + by) not in cells:
                    out.append(("pillar", (x, y, z), yaw))
    return out


def plan_model(plan):
    """the whole layout as one Model (each piece turned about its cell centre, then moved) - preview or brushes"""
    m = Model()
    for piece, (x, y, z), yaw in plan:
        m += PIECES[piece]().rotate(yaw=yaw).move(x, y, z)
    return m


if __name__ == "__main__":
    import os
    for k, f in PIECES.items():
        print("%-12s %s" % (k, f().check() or "ok"))
    plan = building(["###", "#.#", "###"], doors={(1, 2, "s")}, windows={(0, 1, "w"), (2, 1, "e"), (1, 0, "n")})
    print(len(plan), "pieces")
    plan_model(plan).preview(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_courtyard.png"),
                             title="kit: a courtyard building from 3x3 cells (door south, windows)")
