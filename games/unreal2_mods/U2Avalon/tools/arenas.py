"""Greybox plans of the four exterior fight areas E1-E4 (redesign 2026-10-09, level_designer.md s.4; plan s.7 Phase A
step 6). The interiors I1-I4 come from rooms.py.

    py tools/arenas.py [out dir=redesign/2026-10-09/greybox]

Each arena is a list of pieces in LOCAL UU (origin = the arena's lower-left corner, +y = away from the player's
arrival side as drawn in level_designer.md). Writes per arena:
  <id>.png   top view, 1 px = 4 UU, 256 UU grid, a 1024 UU ring round the arrival P (the fair hitscan range),
             full cover dark, half cover light, solids black, high spots with their height, spawns, entries
  arenas.json  the same pieces (the build places them on the graded ground with the arena's yaw and origin)
and prints the checks the level designer set: cover count and spacing, entries, and the share of sightlines that
full cover / solids / terrace steps break: between random pairs of open cells (the in-fight number the targets mean)
and from P to every open 128 UU cell (the opening view: E1 wants it LOW, the yard seen whole before the first shot).
Measured player: radius 28, half height 54, step 37 (AI 35): gaps between pieces >= 96 UU are walkable lanes.
"""
import json, math, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "redesign", "2026-10-09", "greybox")

# kind: deck (walkable floor drawn light), solid (building/wall, blocks sight + move), full (full cover >= 120 UU high), half (60-90 UU), water,
#       high (x, y, z), spawn, entry, exit, P (arrival), pillar (round solid: x, y, r), terrace (rect, z)
A = {
 "E1": dict(name="Dock Yard", size=(3200, 2400), target="breaks 50-60 %", pieces=[
    ("water", 0, 2000, 3200, 400, "sea"),
    ("deck", 150, 1700, 1300, 140, "jetty deck"),
    ("P", 250, 1770, "jetty"),
    ("pillar", 1650, 1780, 60, "crane leg"), ("pillar", 1900, 1780, 60, "crane leg"),
    ("pillar", 1650, 1530, 60, "crane leg"), ("pillar", 1900, 1530, 60, "crane leg"),
    ("high", 1775, 1655, 400, "crane cab (ladder)"),
    ("half", 500, 1450, 320, 90, "crates"),
    ("full", 1150, 1350, 480, 200, "container"),
    ("half", 2450, 1450, 360, 90, "pallets"),
    ("full", 2900, 1250, 160, 480, "container stack"),
    ("full", 1500, 300, 420, 160, "container"),
    ("solid", 150, 750, 520, 420, "quay shed"),
    ("half", 1050, 950, 200, 110, "forklift"),
    ("spawn", 1350, 800, "boat: Medium at +10 s"),
    ("half", 1650, 750, 260, 90, "barrels"),
    ("full", 2100, 950, 200, 480, "container"),
    ("solid", 2750, 700, 300, 300, "silo (hides the tower)"),
    ("half", 500, 450, 220, 80, "crates"),
    ("half", 2450, 450, 220, 80, "barrels"),
    ("spawn", 1200, 1150, "merc"), ("spawn", 1800, 1100, "merc"), ("spawn", 2300, 700, "merc"),
    ("entry", 60, 300, "shore path"), ("exit", 1600, 30, "dock gate (spine)"), ("entry", 3140, 300, "back lane"),
 ]),
 "E2": dict(name="Dorm Square", size=(2400, 2000), target="breaks 55-70 %", pieces=[
    ("solid", 100, 1350, 700, 550, "dorm_c (dark, door torn)"),
    ("solid", 1500, 1600, 300, 250, "memorial"), ("high", 1650, 1500, 160, "memorial plinth"),
    ("P", 80, 1100, "hall exit lane"),
    ("half", 900, 1050, 300, 80, "sandbags"),
    ("full", 1450, 1000, 450, 120, "barricade (faces the drainage)"),
    ("solid", 1950, 650, 400, 500, "checkpoint"), ("high", 2150, 900, 300, "checkpoint roof (stair)"),
    ("spawn", 1900, 1200, "checkpoint door: merc"), ("spawn", 1650, 1180, "merc"), ("spawn", 2150, 900, "Heavy (roof)"),
    ("solid", 100, 300, 800, 550, "dorm"),
    ("half", 1000, 600, 260, 90, "laundry carts"),
    ("half", 1200, 300, 200, 90, "carts"),
    ("half", 1300, 1450, 120, 220, "husk pile (half)"),
    ("entry", 30, 150, "back lane"), ("exit", 1400, 30, "road north (drainage path)"),
 ]),
 "E3": dict(name="Cooling-Tower Basin", size=(3600, 3000), target="bowl: pillars break 35-50 %", pieces=[
    ("terrace", 0, 2700, 3600, 300, 300, "rim (+300)"),
    ("high", 900, 2850, 300, "pipe-rack walkway"), ("high", 2700, 2850, 300, "rim: merc sniper"),
    ("P", 150, 2450, "sluice mouth (from I3)"),
    ("exit", 3500, 2450, "ramp to spine"),
    ("pillar", 1500, 1950, 220, "tower leg"), ("pillar", 1700, 1450, 220, "tower leg"), ("pillar", 1500, 950, 220, "tower leg"),
    ("water", 400, 1700, 600, 350, "puddles"),
    ("half", 2400, 1950, 360, 120, "pump skid"),
    ("half", 500, 1250, 200, 120, "valve"),
    ("solid", 2600, 1100, 450, 400, "control hut"), ("full", 2500, 1050, 100, 500, "hut wall"),
    ("spawn", 2550, 1300, "mercs: hut door"),
    ("spawn", 300, 800, "Skaarj: second culvert"), ("spawn", 3000, 300, "Skaarj: drain grate"),
    ("half", 2400, 550, 200, 100, "crates"),
    ("entry", 60, 300, "maintenance stair"), ("entry", 3000, 60, "drain grate (Skaarj only)"),
 ]),
 "E4": dict(name="Company Gate and Stair Cut-in", size=(2800, 2400), target="terrace edges = cover", pieces=[
    ("terrace", 0, 0, 2800, 800, 160, "terrace 1 (+160)"),
    ("terrace", 0, 800, 2800, 800, 360, "terrace 2 (+360)"),
    ("terrace", 0, 1600, 2800, 800, 600, "terrace 3 / tower plateau (+600)"),
    ("solid", 0, 780, 1200, 40, "terrace wall"), ("solid", 1500, 780, 1300, 40, "terrace wall"),
    ("solid", 0, 1580, 1250, 40, "battered company wall"), ("solid", 1450, 1580, 900, 40, "battered company wall"),
    ("entry", 1350, 1600, "STAIR CUT-IN (192 wide)"), ("entry", 1350, 800, "ramp"),
    ("entry", 2600, 1200, "side switchback (long, covered)"),
    ("P", 200, 300, "from the spine"),
    ("half", 1500, 300, 400, 90, "barrier"), ("spawn", 2200, 400, "drop pod 2 (visible streak)"),
    ("half", 300, 1100, 300, 100, "planters"),
    ("half", 1100, 1350, 220, 90, "dead mercs' crates"),
    ("half", 600, 500, 260, 90, "crates"),
    ("high", 2400, 1800, 600, "parapet corner"), ("solid", 1800, 1000, 600, 450, "company_store"),
    ("spawn", 900, 1200, "drop pod 1"),
    ("full", 300, 1800, 600, 120, "parapet"), ("solid", 1200, 1900, 500, 350, "generator_house"),
    ("half", 2000, 1800, 300, 100, "fuel drums"),
    ("spawn", 1350, 2000, "Berserker (charges the stair)"),
    ("exit", 700, 2340, "tower base, I1 door"),
 ]),
}


def blocks_sight(p):
    return p[0] in ("solid", "full", "pillar")


def hit(p, x, y):
    if p[0] == "pillar":
        return math.hypot(x - p[1], y - p[2]) <= p[3]
    if p[0] in ("solid", "full", "half", "water", "terrace", "deck"):
        return p[1] <= x <= p[1] + p[3] and p[2] <= y <= p[2] + p[4]
    return False


def check(aid, a):
    W, H = a["size"]
    ps = a["pieces"]
    P = next(p for p in ps if p[0] == "P")
    cover = [p for p in ps if p[0] in ("full", "half", "pillar")]
    solid = [p for p in ps if blocks_sight(p)]
    walk = [p for p in ps if p[0] in ("solid", "full", "half", "pillar")]
    # terrace steps: a ray from a lower terrace past a higher one's edge is blocked if the step is over eye height
    terr = [p for p in ps if p[0] == "terrace"]

    def zat(x, y):
        z = 0
        for t in terr:
            if hit(t, x, y):
                z = max(z, t[5])
        return z
    z0 = zat(P[1], P[2]) + 108
    n = blk = 0
    for gx in range(64, W, 128):
        for gy in range(64, H, 128):
            if any(hit(p, gx, gy) for p in walk) or math.hypot(gx - P[1], gy - P[2]) < 256:
                continue
            n += 1
            d = math.hypot(gx - P[1], gy - P[2])
            steps = int(d / 32)
            for k in range(1, steps):
                x = P[1] + (gx - P[1]) * k / steps
                y = P[2] + (gy - P[2]) * k / steps
                if any(hit(p, x, y) for p in solid) or zat(x, y) > z0:
                    blk += 1
                    break
    # the in-fight number: share of sightlines between random pairs of open cells (500 pairs, fixed seed)
    import random
    rnd = random.Random(7)
    cells = [(gx, gy) for gx in range(64, W, 128) for gy in range(64, H, 128) if not any(hit(p, gx, gy) for p in walk)]
    pb = 0
    for _ in range(500):
        (ax, ay), (bx, by) = rnd.sample(cells, 2)
        za, zb = zat(ax, ay) + 108, zat(bx, by) + 108
        steps = max(2, int(math.hypot(bx - ax, by - ay) / 32))
        for k in range(1, steps):
            x, y = ax + (bx - ax) * k / steps, ay + (by - ay) * k / steps
            if any(hit(p, x, y) for p in solid) or zat(x, y) > min(za, zb):
                pb += 1
                break
    ents = [p for p in ps if p[0] in ("entry", "exit")]
    gaps = []
    for i, c in enumerate(cover):
        cx = c[1] + (c[3] / 2 if c[0] != "pillar" else 0)
        cy = c[2] + (c[4] / 2 if c[0] != "pillar" else 0)
        best = 1e9
        for j, d in enumerate(cover):
            if i != j:
                dx = d[1] + (d[3] / 2 if d[0] != "pillar" else 0)
                dy = d[2] + (d[4] / 2 if d[0] != "pillar" else 0)
                best = min(best, math.hypot(cx - dx, cy - dy))
        gaps.append(best)
    return dict(cover=len(cover), entries=len(ents), sight_broken=round(pb / 500, 2), from_P=round(blk / max(1, n), 2),
                nearest_cover_uu=[int(min(gaps)), int(max(gaps))] if gaps else None,
                spawns=sum(1 for p in ps if p[0] == "spawn"), high=sum(1 for p in ps if p[0] == "high"))


def draw(aid, a, path):
    W, H = a["size"]
    S = 0.25
    M = 40
    img = Image.new("RGB", (max(1250, int(W * S) + 2 * M + 200), int(H * S) + 2 * M + 30), (236, 233, 226))
    d = ImageDraw.Draw(img)

    def px(x, y):
        return M + x * S, M + (H - y) * S

    for t in [p for p in a["pieces"] if p[0] == "terrace"]:
        g = 236 - int(t[5] / 6)
        x0, y1 = px(t[1], t[2]); x1, y0 = px(t[1] + t[3], t[2] + t[4])
        d.rectangle([x0, y0, x1, y1], fill=(g, g - 4, g - 12))
        d.text((x0 + 3, y0 + 3), t[6], fill=(90, 80, 60))
    for g in range(0, W + 1, 256):
        d.line([px(g, 0), px(g, H)], fill=(215, 212, 205))
    for g in range(0, H + 1, 256):
        d.line([px(0, g), px(W, g)], fill=(215, 212, 205))
    d.rectangle([px(0, H), px(W, 0)], outline=(120, 120, 120))
    col = {"deck": (180, 170, 150), "solid": (40, 40, 40), "full": (90, 60, 50), "half": (200, 160, 110), "water": (120, 160, 200)}
    for p in a["pieces"]:
        k = p[0]
        if k in col:
            x0, y1 = px(p[1], p[2]); x1, y0 = px(p[1] + p[3], p[2] + p[4])
            d.rectangle([x0, y0, x1, y1], fill=col[k])
            d.text((x0 + 2, y0 + 1 if y1 - y0 > 12 else y1 + 1), p[5][:28], fill=(255, 255, 255) if k in ("solid", "full") else (60, 40, 20))
        elif k == "pillar":
            x, y = px(p[1], p[2]); r = p[3] * S
            d.ellipse([x - r, y - r, x + r, y + r], fill=(40, 40, 40))
        elif k == "high":
            x, y = px(p[1], p[2])
            d.polygon([(x, y - 7), (x - 6, y + 5), (x + 6, y + 5)], fill=(0, 150, 200))
            d.text((x + 8, y - 6), "^+%d %s" % (p[3], p[4]), fill=(0, 100, 150))
        elif k == "spawn":
            x, y = px(p[1], p[2])
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(200, 30, 30))
            d.text((x + 8, y - 6), "S " + p[3], fill=(170, 20, 20))
        elif k in ("entry", "exit"):
            x, y = px(p[1], p[2])
            d.rectangle([x - 6, y - 6, x + 6, y + 6], fill=(30, 140, 60) if k == "entry" else (120, 60, 160))
            d.text((x + 8, y - 6), (">" if k == "entry" else "EXIT ") + p[3], fill=(20, 100, 40) if k == "entry" else (90, 40, 130))
        elif k == "P":
            x, y = px(p[1], p[2]); r = 1024 * S
            d.ellipse([x - r, y - r, x + r, y + r], outline=(30, 90, 200))
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(30, 90, 200))
            d.text((x + 10, y - 6), "P " + p[3], fill=(20, 60, 160))
    c = a["check"]
    d.text((M, img.height - 26), "%s %s  %dx%d UU  grid 256  ring 1024 (fair hitscan)  | cover %d, entries %d, spawns %d, high %d, "
           "sightlines broken %d%% (target %s), from P %d%%" % (aid, a["name"], W, H, c["cover"], c["entries"], c["spawns"],
                                                   c["high"], c["sight_broken"] * 100, a["target"], c["from_P"] * 100), fill=(0, 0, 0))
    img.save(path)


os.makedirs(OUT, exist_ok=True)
for aid, a in A.items():
    a["check"] = check(aid, a)
    draw(aid, a, os.path.join(OUT, aid + ".png"))
    print(aid, a["name"], a["check"])
json.dump({k: dict(name=v["name"], size=v["size"], target=v["target"], check=v["check"], pieces=v["pieces"])
           for k, v in A.items()}, open(os.path.join(OUT, "arenas.json"), "w"), indent=1)
