r"""Procedural layouts sent live as imposter cards (the user's scope: live edits = procedural generation +
imposter cards). Each pattern places cards round a point, keeps them off the sea and steep ground (the
town's final heightmap), apart from each other, and turned to face what they should face; the result
goes to the running game through live.py as "avalon cardat" lines (one undoable edit each).

    py tools/live_gen.py street  CARDS X Y DIR LEN N SIZE [LANE]   two rows facing a lane (DIR degrees)
    py tools/live_gen.py cluster CARDS X Y R N SIZE                spaced out round X Y, facing the window
    py tools/live_gen.py ring    CARDS X Y R N SIZE                round X Y, facing its middle
    py tools/live_gen.py row     CARDS X1 Y1 X2 Y2 N SIZE          along a line, facing the window

CARDS: one card name or several "A,B,C" (picked at random); see tools/asset_catalog.py card.
X Y may be "mark": the point the user's last "avalon mark" looked at. Works on any map; the sea and
slope checks only on the Avalon maps (elsewhere cards face where the user stood for the mark).
Options: seed=N, slope=25 (max degrees), dry=1 (print the commands, send nothing), face=X,Y.
"""
import json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import compose  # noqa  (the heightmap reader)
import live  # noqa

LAYOUT = r"C:\Users\john\Documents\U2_research\towns\TutA_Town5\isl_layout.json"
WINDOW = (-349.0, 1388.0)


def heights():
    L = json.load(open(LAYOUT))
    return compose._heights(L["heightmap"])


def ground(Z, x, y):
    return float(compose._bil(Z, np.array([x]), np.array([y]))[0])


def slope(Z, x, y, d=300.0):
    gx = (ground(Z, x + d, y) - ground(Z, x - d, y)) / (2 * d)
    gy = (ground(Z, x, y + d) - ground(Z, x, y - d)) / (2 * d)
    return math.degrees(math.atan(math.hypot(gx, gy)))


def ok(Z, x, y, placed, spacing, max_slope):
    if Z is None:
        return all(math.hypot(x - px, y - py) >= spacing for px, py in placed)
    if ground(Z, x, y) <= compose.SEA_Z + 60:
        return False
    if slope(Z, x, y) > max_slope:
        return False
    return all(math.hypot(x - px, y - py) >= spacing for px, py in placed)


def yaw_to(x, y, tx, ty):
    return int(math.degrees(math.atan2(ty - y, tx - x))) % 360


def last_mark():
    """(looking-at x, y), (player x, y) of the user's last mark"""
    text = open(live.LOG, "rb").read().decode("latin1", "replace") if os.path.exists(live.LOG) else ""
    m = [l for l in text.splitlines() if "Cards: edit MARK" in l]
    if not m:
        sys.exit("no mark in the game log yet (in game: avalon mark)")
    w = re.search(r"looking-at (-?\d+) (-?\d+) (-?\d+)", m[-1])
    p = re.search(r"MARK \d+ at (-?\d+) (-?\d+) (-?\d+)", m[-1])
    return (float(w.group(1)), float(w.group(2))), (float(p.group(1)), float(p.group(2)))


def on_avalon():
    """the map the game is on is one of the Avalon maps ("Cards: live on MAP, avalon True")"""
    text = open(live.LOG, "rb").read().decode("latin1", "replace") if os.path.exists(live.LOG) else ""
    m = re.findall(r"Cards: live on (\S+), avalon (\w+)", text)
    return (m[-1][1] == "True") if m else True


def main():
    a = [x for x in sys.argv[1:] if "=" not in x]
    o = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    rnd = random.Random(int(o.get("seed", 1)))
    max_slope = float(o.get("slope", 25))
    avalon = on_avalon()
    face = WINDOW if avalon else None       # elsewhere: cards face where the user stood for the mark
    kind, cards = a[0], a[1].split(",")
    if a[2] == "mark":
        (x0, y0), stood = last_mark()
        if face is None:
            face = stood
        rest = a[3:]
    else:
        x0, y0 = float(a[2]), float(a[3])
        rest = a[4:]
    if "face" in o:
        face = tuple(float(v) for v in o["face"].split(","))
    if face is None:
        face = (x0 - 1000.0, y0)
    # the terrain checks (sea, slope) use the Avalon town's heightmap: only on the Avalon maps
    Z = heights() if avalon else None
    out = []                                  # (card, x, y, yaw, size)

    def add(x, y, yaw, size, placed, spacing):
        if ok(Z, x, y, placed, spacing, max_slope):
            placed.append((x, y))
            out.append((rnd.choice(cards), x, y, yaw, size))
            return True
        return False

    placed = []
    if kind == "street":
        d, length, n, size = float(rest[0]), float(rest[1]), int(rest[2]), float(rest[3])
        lane = float(rest[4]) if len(rest) > 4 else size * 1.4
        ux, uy = math.cos(math.radians(d)), math.sin(math.radians(d))
        for i in range(n):
            t = (i + 0.5) / n - 0.5
            cx, cy = x0 + ux * t * length, y0 + uy * t * length
            for side in (-1, 1):                # a card on each side of the lane, facing across it
                x, y = cx - uy * side * lane / 2, cy + ux * side * lane / 2
                add(x + rnd.uniform(-1, 1) * size * 0.1, y + rnd.uniform(-1, 1) * size * 0.1,
                    yaw_to(x, y, cx, cy), size * rnd.uniform(0.9, 1.1), placed, size * 0.7)
    elif kind == "cluster":
        r, n, size = float(rest[0]), int(rest[1]), float(rest[2])
        tries = 0
        while len(out) < n and tries < n * 60:
            tries += 1
            ang, rad = rnd.uniform(0, 2 * math.pi), r * math.sqrt(rnd.random())
            x, y = x0 + rad * math.cos(ang), y0 + rad * math.sin(ang)
            add(x, y, yaw_to(x, y, *face) + rnd.randint(-15, 15), size * rnd.uniform(0.85, 1.15), placed, size * 1.2)
    elif kind == "ring":
        r, n, size = float(rest[0]), int(rest[1]), float(rest[2])
        for i in range(n):
            ang = 2 * math.pi * i / n
            x, y = x0 + r * math.cos(ang), y0 + r * math.sin(ang)
            add(x, y, yaw_to(x, y, x0, y0), size, placed, size * 0.6)
    elif kind == "row":
        x1, y1, n, size = float(rest[0]), float(rest[1]), int(rest[2]), float(rest[3])
        for i in range(n):
            t = (i + 0.5) / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            add(x, y, yaw_to(x, y, *face), size, placed, size * 0.6)
    elif kind == "shanty":
        # 3D primitive buildings (AvalonSM.B_*), not cards: shacks packed on the slope, each turned to face
        # downhill (the view), sunk a little on its uphill side; they go into the Props slots from slot=10
        r, n = float(rest[0]), int(rest[1])
        slot = int(o.get("slot", 10))
        tries = 0
        props = []
        while len(props) < n and tries < n * 80:
            tries += 1
            rmin = float(o.get("rmin", 0))                      # rmin= a ring round a summit, not a disc
            ang, rad = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.uniform(rmin * rmin, r * r))
            x, y = x0 + rad * math.cos(ang), y0 + rad * math.sin(ang)
            m = rnd.choice(cards)
            s = rnd.uniform(0.85, 1.2)
            foot = 520 * s
            if not ok(Z, x, y, placed, foot, max_slope):
                continue
            if "avoid" in o:                                      # avoid=X,Y,R: keep out of an earlier group
                ax_, ay_, ar_ = (float(v) for v in o["avoid"].split(","))
                if math.hypot(x - ax_, y - ay_) < ar_:
                    continue
            placed.append((x, y))
            if Z is not None:
                d = 300.0
                gx = ground(Z, x + d, y) - ground(Z, x - d, y)
                gy = ground(Z, x, y + d) - ground(Z, x, y - d)
                down = math.degrees(math.atan2(-gy, -gx))
                lift = -min(150, 0.5 * foot * math.tan(math.radians(slope(Z, x, y))))
            else:
                down, lift = yaw_to(x, y, *face), -40
            yaw = int(down + rnd.randint(-12, 12)) % 360          # AvalonSM meshes face +X at yaw 0 (glb_to_ase)
            props.append("prop %d AvalonSM.%s %d %d %d %.2f %d 0 0 0" % (slot + len(props), m, x, y, yaw, s, lift))
        print("shanty: %d of %d shacks placed" % (len(props), n))
        for p in props:
            print("  ", p)
        if o.get("dry") != "1" and props:
            live.send(["say shanty town: %d shacks" % len(props)] + props + ["rebuild", "save"], float(o.get("wait", 25)))
        return
    else:
        sys.exit(__doc__)
    cmds = ["cardat %s %d %d %d %d" % (c, x, y, yaw, size) for c, x, y, yaw, size in out]
    print("%s: %d of the asked cards placed (the rest fell on sea, steep ground or too close)" % (kind, len(out)))
    for c in cmds:
        print("  ", c)
    if o.get("dry") != "1" and cmds:
        live.send(["say " + kind + ": " + str(len(cmds)) + " " + ",".join(cards)] + cmds, float(o.get("wait", 20)))


if __name__ == "__main__":
    main()
