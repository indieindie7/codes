r"""A procedural factory district (the user's mark, 2026-10-08: "add some procedural roads and pipes please and
make some more normal look factories and some factory districts in the plateau"): a road of tiled segments,
factory lots on both sides, and a pipeline from the district toward a target, as Props lines of a map family's
section. Run with the GAME CLOSED (the running game rewrites U2AvalonCards.ini), or print with dry=1.

    py tools/district.py <Section> X1 Y1 X2 Y2 [pipe=X,Y] [slot=98] [seed=1] [dry=1]

X1 Y1 -> X2 Y2 = the district's main road. Meshes: AvalonSM2.Liandri.{RoadSegment, PipeRack, FactoryHall,
FactoryBlock, SiloCluster, ChimneyStack} (build_buildings.py -> glb_to_ase -> make_sm2). Segments are 1000 units
long along the mesh's Y axis, so a segment's yaw is the path direction minus 90 degrees.
"""
import json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import avalon_ini  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
B = json.load(open(os.path.join(HERE, "..", "..", "U2AvalonCards", "Models", "round2_ase", "bounds.json")))
SEG = 1000.0


def half(m):
    return int(max(B[m]["w"], B[m]["d"]) / 2)


def line(slot, m, x, y, yaw, s=1.0):
    return "Props[%d]=AvalonSM2.Liandri.%s %d %d %d %.2f 0 0 0 0 - %d" % (slot, m, x, y, int(yaw) % 360, s, half(m))


def tiles(x1, y1, x2, y2, m):
    """segments of mesh m end to end from (x1,y1) to (x2,y2)"""
    d = math.degrees(math.atan2(y2 - y1, x2 - x1))
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(1, int(L / SEG))
    return [(m, x1 + (x2 - x1) * (k + 0.5) / n, y1 + (y2 - y1) * (k + 0.5) / n, d - 90) for k in range(n)]


def main():
    a = [v for v in sys.argv[1:] if "=" not in v]
    o = dict(v.split("=", 1) for v in sys.argv[1:] if "=" in v)
    sec = a[0]
    x1, y1, x2, y2 = (float(v) for v in a[1:5])
    rnd = random.Random(int(o.get("seed", 1)))
    items = tiles(x1, y1, x2, y2, "RoadSegment")
    d = math.atan2(y2 - y1, x2 - x1)
    ux, uy, nx, ny = math.cos(d), math.sin(d), -math.sin(d), math.cos(d)
    L = math.hypot(x2 - x1, y2 - y1)
    lot = 2600.0
    kinds = ["FactoryHall", "FactoryHall", "FactoryBlock", "SiloCluster", "FactoryBlock"]
    k = 0
    t = lot / 2
    while t < L - lot / 2:
        for side in (-1, 1):
            m = rnd.choice(kinds)
            off = 1700 + (B[m]["w"] / 2 if m != "FactoryHall" else 600)
            cx, cy = x1 + ux * t + nx * side * off, y1 + uy * t + ny * side * off
            # front (+X at yaw 0) toward the road
            yaw = math.degrees(math.atan2(-ny * side, -nx * side))
            items.append((m, cx, cy, yaw))
            if m == "FactoryHall" and rnd.random() < 0.5:
                items.append(("ChimneyStack", cx + nx * side * 1200, cy + ny * side * 1200, 0))
            k += 1
        t += lot
    if "pipe" in o:
        px, py = (float(v) for v in o["pipe"].split(","))
        mx, my = (x1 + x2) / 2 + nx * 900, (y1 + y2) / 2 + ny * 900
        items += tiles(mx, my, px, py, "PipeRack")
    slot = int(o.get("slot", 98))
    if slot + len(items) > 256:
        items = items[:256 - slot]
        print("trimmed to the free slots")
    lines = [line(slot + i, m, x, y, yaw) for i, (m, x, y, yaw) in enumerate(items)]
    print("%s: %d props (%d road, %d factory/silo/stack, %d pipe)" % (sec, len(lines),
          sum(1 for i in items if i[0] == "RoadSegment"), sum(1 for i in items if i[0] not in ("RoadSegment", "PipeRack")),
          sum(1 for i in items if i[0] == "PipeRack")))
    if o.get("dry") == "1":
        print("\n".join(lines))
        return
    ini = o.get("ini", os.path.join(GAME, "System", "U2AvalonCards.ini"))
    # replace exactly these Props keys in the section (avalon_ini drops by key name, so do it by hand)
    txt = open(ini, newline="").read().replace("\r\n", "\n")
    m = re.search(r"(?msi)^\[%s\]\n(.*?)(?=^\[|\Z)" % re.escape(sec), txt)
    body = m.group(1)
    keys = {l.split("=")[0] for l in lines}
    body2 = "\n".join(l for l in body.split("\n") if l.split("=")[0] not in keys)
    txt = txt.replace(body, "\n".join(lines) + "\n" + body2, 1)
    open(ini, "w", newline="").write(txt.replace("\n", "\r\n"))
    print("written to [%s] in %s" % (sec, ini))


if __name__ == "__main__":
    main()
