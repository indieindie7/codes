"""Zone map of an Unreal II level, from the "Zones:" lines that `hub zones` (U2TestHub) logs.

    py -3.13 zonemap.py GAME.log [out_prefix]

Writes out_prefix.md (one row per zone: size, doorways, enemies, story scripting, and whether it
looks replaceable) and out_prefix.png (top-down: navigation points coloured by zone, doorways,
enemies, story triggers). A zone is a room (or set of rooms) between zone portals; its doorways
are where AI paths cross into another zone.

Replaceable = has enemies and no story scripting: a fight that can be regenerated without
breaking triggers, doors or dialogue. Default-tagged triggers (tag=Trigger) and exploding props
are ambience, not story.
"""
import collections
import math
import re
import sys

FRIENDLY = ("Civilian", "Scientist", "Marine", "Cockroach", "Bird", "Fish", "LevelMaster", "Player", "Critter")
AMBIENT_TAGS = {"Trigger", "ExplosiveCannister"}


def parse(path):
    navs, links, actors, zinfo = [], [], [], {}
    mapname, player = "?", None
    for line in open(path, encoding="latin-1"):
        i = line.find("Zones: ")
        if i < 0:
            continue
        f = line[i + 7:].split()
        kind = f[0]
        if kind == "nav":
            navs.append((int(f[1]), float(f[2]), float(f[3]), float(f[4]), f[5]))
        elif kind == "link":
            links.append((int(f[1]), int(f[2]), float(f[3]), float(f[4]), float(f[5])))
        elif kind == "actor":
            tag = re.search(r"tag=(\S*)", line).group(1)
            event = re.search(r"event=(\S*)", line).group(1)
            actors.append(dict(kind=f[1], zone=int(f[2]), x=float(f[3]), y=float(f[4]), z=float(f[5]), cls=f[6], tag=tag, event=event))
        elif kind == "zoneinfo":
            zinfo[int(f[1])] = f[2]
        elif kind == "map":
            mapname = f[1]
        elif kind == "player":
            player = (int(f[1]), float(f[2]), float(f[3]), float(f[4]))
    return navs, links, actors, zinfo, mapname, player


def is_enemy(a):
    return a["kind"] == "pawn" and not any(k.lower() in a["cls"].lower() for k in FRIENDLY)


def is_story(a):
    if a["kind"] == "mover":
        return True
    if a["kind"] in ("trigger", "event"):
        return a["tag"] not in AMBIENT_TAGS or (a["event"] not in ("None", "") and a["kind"] == "trigger")
    return False


def doorways(links):
    """Zone-crossing paths grouped into doorways: same zone pair, within 300 units."""
    doors = []
    for a, b, x, y, z in links:
        pair = tuple(sorted((a, b)))
        for d in doors:
            if d["pair"] == pair and math.dist((d["x"], d["y"], d["z"]), (x, y, z)) < 300:
                d["n"] += 1
                break
        else:
            doors.append(dict(pair=pair, x=x, y=y, z=z, n=1))
    return doors


def main():
    log = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "zonemap"
    navs, links, actors, zinfo, mapname, player = parse(log)
    doors = doorways(links)
    zones = sorted({n[0] for n in navs} | {a["zone"] for a in actors if a["zone"] > 0})
    rows = []
    for z in zones:
        pts = [n for n in navs if n[0] == z]
        za = [a for a in actors if a["zone"] == z]
        enemies = collections.Counter(a["cls"] for a in za if is_enemy(a))
        story = sorted({a["tag"] if a["tag"] not in AMBIENT_TAGS else a["event"] for a in za if is_story(a)})
        zd = [d for d in doors if z in d["pair"]]
        if pts:
            xs, ys, zs = [p[1] for p in pts], [p[2] for p in pts], [p[3] for p in pts]
            size = f"{int(max(xs) - min(xs))} x {int(max(ys) - min(ys))}, floor {int(min(zs))}..{int(max(zs))}"
        else:
            size = "(no nav points)"
        if enemies and not story:
            verdict = "REPLACEABLE: combat, no story scripting"
        elif enemies:
            verdict = "combat + scripting: careful"
        elif story:
            verdict = "story / scripted"
        else:
            verdict = "transit / empty"
        rows.append(dict(zone=z, name=zinfo.get(z, ""), navs=len(pts), size=size, doors=zd, enemies=enemies,
                         story=story, verdict=verdict, pts=pts))

    with open(out + ".md", "w", encoding="utf-8") as f:
        f.write(f"# Zone map: {mapname}\n\n")
        f.write(f"{len(navs)} navigation points, {len(zones)} zones, {len(doors)} doorways. ")
        if player:
            f.write(f"Player starts in zone {player[0]}.")
        f.write("\n\n| zone | name | nav | extent (x by y, floor z) | doorways to | enemies | story scripting | verdict |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            to = ", ".join(f"{d['pair'][1] if d['pair'][0] == r['zone'] else d['pair'][0]}" for d in r["doors"]) or "-"
            en = ", ".join(f"{n} {c}" for c, n in r["enemies"].items()) or "-"
            st = ", ".join(r["story"][:6]) + (" ..." if len(r["story"]) > 6 else "") or "-"
            f.write(f"| {r['zone']} | {r['name']} | {r['navs']} | {r['size']} | {to} | {en} | {st} | {r['verdict']} |\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 11), dpi=110)
    cmap = plt.get_cmap("tab20")
    for i, r in enumerate(rows):
        if not r["pts"]:
            continue
        col = cmap(i % 20)
        ax.scatter([p[1] for p in r["pts"]], [-p[2] for p in r["pts"]], s=14, color=col)
        cx = sum(p[1] for p in r["pts"]) / len(r["pts"])
        cy = -sum(p[2] for p in r["pts"]) / len(r["pts"])
        mark = "*" if r["verdict"].startswith("REPLACEABLE") else ""
        ax.annotate(f"{r['zone']}{mark}", (cx, cy), fontsize=13, weight="bold", color=col,
                    bbox=dict(boxstyle="round", fc="white", ec=col, alpha=0.85))
    for d in doors:
        ax.scatter(d["x"], -d["y"], marker="s", s=60, facecolors="none", edgecolors="black", linewidths=1.5)
    en = [a for a in actors if is_enemy(a)]
    ax.scatter([a["x"] for a in en], [-a["y"] for a in en], marker="x", s=40, color="red", label="enemy")
    st = [a for a in actors if is_story(a)]
    ax.scatter([a["x"] for a in st], [-a["y"] for a in st], marker="^", s=30, color="goldenrod", label="story trigger / mover")
    if player:
        ax.scatter(player[1], -player[2], marker="P", s=160, color="green", label="player start")
    ax.scatter([], [], marker="s", facecolors="none", edgecolors="black", label="doorway")
    ax.set_title(f"{mapname}: zones (number, * = replaceable combat zone), top-down (north up)")
    ax.set_aspect("equal")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out + ".png")
    print(f"wrote {out}.md and {out}.png: {len(zones)} zones, "
          f"{sum(1 for r in rows if r['verdict'].startswith('REPLACEABLE'))} replaceable")


if __name__ == "__main__":
    main()
