r"""Hillside shanty generator for TutA's shanty mountain (Avalon Q68/Q74, 2026-10-08), from
games/research_notes/Mountain living/report.md: company and rich houses on the summit, the shanty in wavy contour
rows two storeys apart below it, stair gaps lined up down the slope (and the spine stair toward the tower deck),
three empty drainage gullies, one switchback road at <= 12 % with its hairpins in the deck sector, density highest
near the spine and the road. Writes live.py commands (avalon prop I LINE) that clear the old shanty slots first.

    py -3.13 tools/hillside.py <out.txt>
"""
import sys, json, math, random, re
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\games\unreal2_mods\U2GM\tools")
from gm_commit import read_bmp16

INI = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System\U2AvalonCards.ini"
META = r"C:\Users\john\Documents\U2_research\tuta_terrain\meta.json"
SUMMIT = (-11000.0, 5800.0)
DECK = (-1703.0, 2891.0)
random.seed(74)

M = json.load(open(META))[0]
_, HM, _ = read_bmp16(M["bmp"])
HH, HW = HM.shape
LX, LY, LZ = M["loc"]


def g(x, y):
    i = (x - LX) / 512 + HW / 2
    j = (y - LY) / 512 + HH / 2
    i0, j0 = int(i), int(j)
    if not (0 <= i0 < HW - 1 and 0 <= j0 < HH - 1):
        return -5000.0
    fi, fj = i - i0, j - j0
    h = HM[j0, i0] * (1 - fi) * (1 - fj) + HM[j0, i0 + 1] * fi * (1 - fj) + HM[j0 + 1, i0] * (1 - fi) * fj + HM[j0 + 1, i0 + 1] * fi * fj
    return LZ + (h - 32768) * 128 / 256.0


def slope(x, y, d=200.0):
    gx = (g(x + d, y) - g(x - d, y)) / (2 * d)
    gy = (g(x, y + d) - g(x, y - d)) / (2 * d)
    return math.hypot(gx, gy)        # rise/run


def radius_at(a, z):
    """distance from the summit along angle a (deg) where the ground first drops to z"""
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    r = 100.0
    while r < 9000:
        if g(SUMMIT[0] + r * ca, SUMMIT[1] + r * sa) <= z:
            return r
        r += 40
    return None


def adiff(a, b):
    return abs((a - b + 180) % 360 - 180)


# the old shanty, road and spare slots of [TutA]
sec, lines = None, {}
for l in open(INI, errors="replace"):
    l = l.rstrip("\r\n")
    if l.startswith("["):
        sec = l
        continue
    m = re.match(r"Props\[(\d+)\]=(.*)", l)
    if m and sec == "[TutA]":
        lines[int(m.group(1))] = m.group(2)
tmpl = {}
for i, v in lines.items():
    w = v.split()
    if w:
        tmpl.setdefault(w[0], w)
slots = []
for i, v in sorted(lines.items()):
    w = v.split()
    if not w:
        if 150 <= i <= 255 and not 240 <= i <= 243:
            slots.append(i)
        continue
    x, y = float(w[1]), float(w[2])
    if (w[0].split(".")[-1] in ("B_shed_a", "B_shed_b", "B_old_camp", "B_pump_house") and math.hypot(x - SUMMIT[0], y - SUMMIT[1]) < 7000) \
            or (w[0].endswith("RoadSegment") and 150 <= i <= 239):
        slots.append(i)
slots = sorted(set(slots))
cmds = ["prop %d " % i for i in slots]          # clear first

def line(mesh, x, y, yaw, scale, lift=0):
    w = list(tmpl[mesh]) if mesh in tmpl else [mesh, "0", "0", "0", "1.00", "0", "0", "0", "0", "-", "300"]
    w[1], w[2], w[3], w[4] = "%d" % x, "%d" % y, "%d" % (yaw % 360), "%.2f" % scale
    w[5] = "%d" % lift
    return " ".join(w)

lane = math.degrees(math.atan2(DECK[1] - SUMMIT[1], DECK[0] - SUMMIT[0]))
gullies = [lane + 75, lane + 175, lane + 265]
stairs = [lane + k * 22.5 for k in range(16)]
out = []

# 1. the road: switchbacks in the deck sector, 12 % grade, from the shanty's foot to below the summit
road = []
a, z, d = lane, -200.0, 1
while z < 2500 and len(road) < 44:
    r = radius_at(a, z)
    if r is None:
        break
    road.append((SUMMIT[0] + r * math.cos(math.radians(a)), SUMMIT[1] + r * math.sin(math.radians(a)), a))
    a += d * math.degrees(670.0 / max(r, 600))
    z += 80
    if adiff(a, lane) > 45:
        d = -d
        a += d * 4
for (x0, y0, _), (x1, y1, _) in zip(road, road[1:]):
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
    out.append(line("AvalonSM2.Liandri.RoadSegment", (x0 + x1) / 2, (y0 + y1) / 2, yaw, 0.6))

# 2. the summit: company and rich houses on the flattest spots within 1700 of the top
rich = ["AvalonSM.B_directors_house", "AvalonSM.B_directors_house", "AvalonSM.B_hall_a", "AvalonSM.B_plant_office",
        "AvalonSM2.Liandri.WaterTower", "AvalonSM.B_hall_c"]
spots = []
for k in range(36):
    ang = k * 10.0
    for r in (700, 1100, 1500):
        x, y = SUMMIT[0] + r * math.cos(math.radians(ang)), SUMMIT[1] + r * math.sin(math.radians(ang))
        spots.append((slope(x, y), x, y, ang))
spots.sort()
placed = []
for mesh in rich:
    for s, x, y, ang in spots:
        if all(math.hypot(x - px, y - py) > 900 for px, py in placed) and adiff(ang, lane) > 15:
            placed.append((x, y))
            out.append(line(mesh, x, y, ang, 1.0))
            break

# 3. the shanty: contour rows every 2 storeys (350 UU) from just below the rich band down to the foot
homes = []
meshes = ["AvalonSM.B_shed_a", "AvalonSM.B_shed_b", "AvalonSM.B_old_camp", "AvalonSM.B_shed_a", "AvalonSM2.Liandri.TinShack"]
for zl in range(2150, -500, -350):
    ang = random.uniform(0, 8)
    while ang < 360:
        a = lane + ang
        r = radius_at(a, zl)
        if r is None:
            ang += 6
            continue
        step = math.degrees(520.0 / r)                     # a house and a gap along the contour
        x, y = SUMMIT[0] + r * math.cos(math.radians(a)), SUMMIT[1] + r * math.sin(math.radians(a))
        ok = all(adiff(a, gu) > 8 for gu in gullies)
        ok = ok and all(adiff(a, st) > math.degrees(260.0 / r) for st in stairs)
        ok = ok and slope(x, y) < 0.7
        ok = ok and all(math.hypot(x - rx, y - ry) > 420 for rx, ry, _ in road)
        ok = ok and all(math.hypot(x - px, y - py) > 900 for px, py in placed)
        if ok:
            near = min([adiff(a, lane) * math.pi / 180 * r] + [math.hypot(x - rx, y - ry) for rx, ry, _ in road])
            keep = 1.0 - 0.55 * min(1.0, near / 7500.0)          # dense near the spine and the road
            if random.random() < keep:
                wob = random.uniform(-150, 150)
                x += wob * math.cos(math.radians(a)); y += wob * math.sin(math.radians(a))
                homes.append(line(random.choice(meshes), x, y, a + random.uniform(-15, 15), random.uniform(0.85, 1.1)))
        ang += step * random.uniform(0.9, 1.25)
random.shuffle(homes)
need = len(slots)
body = out + homes
if len(body) > need:
    keep_homes = need - len(out)
    body = out + homes[:keep_homes]
for i, l in zip(slots, body):
    cmds.append("prop %d %s" % (i, l))
cmds += ["rebuild", "say Q68/Q74: hillside remade - company and rich houses on the summit, %d homes in contour rows, stair gaps, 3 gullies, a switchback road (%d segments)" % (len(body) - len(out), len(road) - 1)]
open(sys.argv[1], "w").write("\n".join(cmds) + "\n")
print("slots", len(slots), "road", len(road) - 1, "rich", len(placed), "homes candidates", len(homes), "placed", len(body) - len(out))
