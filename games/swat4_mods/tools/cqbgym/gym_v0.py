"""CQB gym v0: one room, one door, one suspect holding, one officer entering.

The suspect picks a hold spot by scoring features with 5 weights (same shape as a
SwatMinds scorer, so trained weights port 1:1 to UnrealScript config). The officer
is a scripted entry bot whose knobs model player habits. Outcomes for every
(room, spot, seed) are simulated once into a table; the cross-entropy method then
trains the weights by table lookup. Plan: research/combat-gym-plan.md.

Run: py -3.13 -I gym_v0.py [--rooms 120] [--seeds 3] [--out weights.json]
"""
import argparse, json, math, random, sys, time

FEATURES = ["depth", "off_axis", "hard_cover", "beside_frame", "door_line"]
DOOR_W = 90.0
DT = 0.05

# attacker styles = player-habit knobs (later fitted from SwatMinds habit logs)
STYLES = {
    # doctrine: no stop, near corners first, quick turn
    "doctrine": dict(stop=0.0, near_first=True, speed=260, turn=320, react=0.25),
    # sloppy: stops in the doorway, scans the middle first
    "sloppy": dict(stop=1.0, near_first=False, speed=200, turn=260, react=0.30),
    # rusher: no stop, fast, scans middle first
    "rusher": dict(stop=0.0, near_first=False, speed=380, turn=300, react=0.25),
}


def make_room(rng):
    W, H = rng.uniform(400, 800), rng.uniform(400, 700)
    dx = rng.uniform(120, W - 120)
    pillars = []
    for _ in range(rng.randint(0, 3)):
        pillars.append((rng.uniform(80, W - 80), rng.uniform(150, H - 80), rng.uniform(25, 45)))
    return dict(W=W, H=H, dx=dx, pillars=pillars)


def seg_hits_circle(a, b, c, r):
    ax, ay = a; bx, by = b; cx, cy = c
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / L2))
    px, py = ax + t * dx - cx, ay + t * dy - cy
    return px * px + py * py < r * r


def los(room, a, b):
    # outside the room (y<0) you only see in through the door gap
    if (a[1] < 0) != (b[1] < 0):
        t = -a[1] / (b[1] - a[1])
        x = a[0] + t * (b[0] - a[0])
        if abs(x - room["dx"]) > DOOR_W / 2:
            return False
    for (px, py, pr) in room["pillars"]:
        if seg_hits_circle(a, b, (px, py), pr):
            return False
    return True


def spots(room):
    out = []
    W, H = room["W"], room["H"]
    y = 40.0
    while y < H - 20:
        x = 40.0
        while x < W - 20:
            if all(math.hypot(x - px, y - py) > pr + 25 for px, py, pr in room["pillars"]):
                out.append((x, y))
            x += 60.0
        y += 60.0
    return out


def features(room, s):
    dx = room["dx"]
    vx, vy = s[0] - dx, s[1]
    depth = math.hypot(vx, vy) / math.hypot(room["W"], room["H"])
    off = abs(math.degrees(math.atan2(abs(vx), vy))) / 90.0  # 0 = straight in, 1 = along the door wall
    cover = 1.0 if any(math.hypot(s[0] - px, s[1] - py) < pr + 50 for px, py, pr in room["pillars"]) else 0.0
    frame = 1.0 if (s[1] < 100 and abs(vx) < 160) else 0.0
    line = 1.0 if abs(vx) < 60 else 0.0
    return [depth, off, cover, frame, line]


def ang(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def turn_to(cur, tgt, rate):
    d = (tgt - cur + 180) % 360 - 180
    step = rate * DT
    return tgt if abs(d) <= step else cur + math.copysign(step, d)


def adiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def duel(room, spot, style, rng):
    """1 = suspect wins, 0 = suspect downed, 0.4 = nobody fell (timeout)."""
    st = STYLES[style]
    W, H, dx = room["W"], room["H"], room["dx"]
    side = rng.choice([-1, 1])  # which side the officer clears first
    side_x = 40 if side < 0 else W - 40
    other_x = W - 40 if side < 0 else 40
    near = [(side_x, 30), (other_x, 30)]
    far = [(side_x, H - 30), (other_x, H - 30)]
    looks = near + far if st["near_first"] else [(dx, H - 30), far[0], far[1], near[0], near[1]]
    path = [(dx, -150), (dx, 40), (dx + side * min(150, abs(side_x - dx) * 0.6), 80), (W / 2, H / 2)]
    cover = any(math.hypot(spot[0] - px, spot[1] - py) < pr + 50 for px, py, pr in room["pillars"])

    a = list(path[0]); a_aim = 90.0; leg = 1; stop_left = st["stop"]; look_i = 0; dwell = 0.0
    d_aim = ang(spot, (dx, 0)); d_react = 0.55 + rng.uniform(-0.15, 0.15)  # suspects: untrained, unsure when entry comes
    a_seen = d_seen = None; a_shot = d_shot = 0.0
    t = 0.0
    while t < 8.0:
        t += DT
        # officer moves
        if leg < len(path):
            if leg == 2 and stop_left > 0 and a[1] >= 40:
                stop_left -= DT
            else:
                tx, ty = path[leg]
                ddx, ddy = tx - a[0], ty - a[1]
                dist = math.hypot(ddx, ddy)
                step = st["speed"] * DT * (0.5 if a_seen is not None else 1.0)
                if dist <= step:
                    a[0], a[1] = tx, ty; leg += 1
                else:
                    a[0] += ddx / dist * step; a[1] += ddy / dist * step
        vis = los(room, tuple(a), spot) and math.hypot(a[0] - spot[0], a[1] - spot[1]) > 1
        # officer: detection needs the suspect inside a 100-degree view cone
        if vis and a_seen is None and adiff(a_aim, ang(a, spot)) < 50:
            a_seen = t
        if a_seen is not None and t - a_seen >= st["react"]:
            a_aim = turn_to(a_aim, ang(a, spot), st["turn"])
        elif a[1] >= 0:
            if look_i < len(looks):
                tgt = ang(a, looks[look_i])
                a_aim = turn_to(a_aim, tgt, st["turn"])
                if adiff(a_aim, tgt) < 5:
                    dwell += DT
                    if dwell > 0.35:
                        look_i += 1; dwell = 0.0
        # suspect: aim parked on the door, sees anything in LOS (expecting entry)
        if vis and d_seen is None:
            d_seen = t
        if d_seen is not None and t - d_seen >= d_react:
            d_aim = turn_to(d_aim, ang(spot, a), 180)
        # fire
        if a_seen is not None and t - a_seen >= st["react"] and adiff(a_aim, ang(a, spot)) < 6 and t >= a_shot:
            a_shot = t + 0.12
            if rng.random() < (0.4 if cover else 0.75):
                return 0.0
        if d_seen is not None and t - d_seen >= d_react and adiff(d_aim, ang(spot, a)) < 6 and t >= d_shot:
            d_shot = t + 0.15
            if rng.random() < 0.35:
                return 1.0
    return 0.4


def build_table(n_rooms, seeds, styles, rng):
    table = []  # per room: (feature rows, {style: [mean outcome per spot]})
    for _ in range(n_rooms):
        room = make_room(rng)
        sp = spots(room)
        feats = [features(room, s) for s in sp]
        res = {}
        for style in styles:
            res[style] = [sum(duel(room, s, style, rng) for _ in range(seeds)) / seeds for s in sp]
        table.append((feats, res))
    return table


def evaluate(w, table, mix):
    tot = 0.0
    for feats, res in table:
        best = max(range(len(feats)), key=lambda k: sum(wi * fi for wi, fi in zip(w, feats[k])))
        tot += sum(p * res[s][best] for s, p in mix.items())
    return tot / len(table)


def cem(table, mix, rng, gens=40, pop=60, elite=8):
    mu = [0.0] * len(FEATURES); sd = [1.0] * len(FEATURES)
    best = (None, -1)
    for g in range(gens):
        cands = [[rng.gauss(m, s) for m, s in zip(mu, sd)] for _ in range(pop)]
        scored = sorted(((evaluate(c, table, mix), c) for c in cands), key=lambda x: -x[0])
        if scored[0][0] > best[1]:
            best = (scored[0][1], scored[0][0])
        el = [c for _, c in scored[:elite]]
        mu = [sum(c[i] for c in el) / elite for i in range(len(FEATURES))]
        sd = [max(0.05, (sum((c[i] - mu[i]) ** 2 for c in el) / elite) ** 0.5) for i in range(len(FEATURES))]
    n = max(abs(x) for x in best[0]) or 1.0
    return [round(x / n, 3) for x in best[0]], best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rooms", type=int, default=120)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default="weights_v0.json")
    a = ap.parse_args()
    rng = random.Random(7)
    t0 = time.time()
    train = build_table(a.rooms, a.seeds, list(STYLES), rng)
    test = build_table(max(40, a.rooms // 3), a.seeds, list(STYLES), rng)
    print(f"tables built in {time.time() - t0:.0f}s")
    out = {}
    baselines = {"door-facing (minus depth)": [-1, 0, 0, 0, 1], "cqb-tips (hand)": [1, 1, 0.5, -1, -1]}
    for style in list(STYLES) + ["mixed"]:
        mix = {s: 1 / len(STYLES) for s in STYLES} if style == "mixed" else {style: 1.0}
        w, tr = cem(train, mix, rng)
        te = evaluate(w, test, mix)
        base = {k: round(evaluate(v, test, mix), 3) for k, v in baselines.items()}
        base["random spot"] = round(sum(sum(p * sum(res[s]) / len(res[s]) for s, p in mix.items()) for _, res in test) / len(test), 3)
        out[style] = dict(weights=dict(zip(FEATURES, w)), train=round(tr, 3), test=round(te, 3), baselines=base)
        print(f"{style:9s} test={te:.3f} base={base} w={dict(zip(FEATURES, w))}")
    json.dump(out, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    sys.exit(main())
