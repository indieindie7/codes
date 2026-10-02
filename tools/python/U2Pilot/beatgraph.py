"""Beat graph of an Unreal II level: its event wiring, from the "Beats:" lines of `hub beats`
(and the "Zones:" lines of `hub zones` for the AI path network).

    py -3.13 beatgraph.py GAME.log [out_prefix]

Unreal levels are wired with names: an actor fires its Event (or a list of events: dispatchers,
cutscene trigger steps, spawners, stage triggers), and every actor whose Tag matches reacts (a
door opens, a cutscene plays, a counter counts, AI wakes up). This links them into a directed
graph, follows each chain from where it starts (the player start, triggers the player walks into,
enemies whose death fires an event) and marks the chains that matter for the story: the ones that
reach a door, a cutscene, a counter (a kill-gate: "all of these dead"), AI or a level exit.
Everything else (sounds, effects, ambience) is listed separately.

Chains are ordered by walking distance from the player start along the AI path network (the
order a player meets them, ignoring locked doors). Writes out_prefix.md and out_prefix.png.
"""
import collections
import heapq
import math
import re
import sys

player_zone = [-1]   # the zone the player starts in (from "Zones: player")
STORY_KINDS = {"door", "cutscene", "counter", "exit", "objective", "aiscript", "pawn"}
EXIT_WORDS = ("goesto", "travel", "nextlevel", "mapchange")
KIND_COLOUR = {"trigger": "tab:blue", "counter": "tab:purple", "door": "tab:brown", "cutscene": "tab:red",
               "pawn": "tab:orange", "exit": "black", "objective": "tab:green", "sound": "tab:gray",
               "other": "tab:olive", "aiscript": "tab:pink", "light": "gold", "effect": "tab:cyan"}


def parse(path):
    actors, navs, edges, player, mapname = [], [], [], None, "?"
    extra = collections.defaultdict(list)      # actor name -> events it fires besides Event
    for line in open(path, encoding="latin-1"):
        i = line.find("Beats: ")
        if i >= 0:
            f = line[i + 7:].split()
            if not f:
                continue
            if f[0] == "map":
                mapname = f[1]
                continue
            if f[0] == "fires":
                if len(f) >= 3:
                    extra[f[1]].append(f[2])
                continue
            mt, me = re.search(r"tag=(\S*)", line), re.search(r"event=(\S*)", line)
            if not mt or not me or len(f) < 7:
                continue                        # a progress line, or cut off
            tag, event = mt.group(1), me.group(1)
            url = re.search(r"url=(\S*)", line)
            kind = f[0]
            if any(w in event.lower() for w in EXIT_WORDS) or url:
                kind = "exit" if kind in ("trigger", "other") else kind
            if "objective" in (tag + event).lower() and kind in ("trigger", "other"):
                kind = "objective"
            actors.append(dict(kind=kind, zone=int(f[1]), x=float(f[2]), y=float(f[3]), z=float(f[4]),
                               cls=f[5], name=f[6], tag=tag, event=event if event != "None" else ""))
            continue
        i = line.find("Zones: ")
        if i >= 0:
            f = line[i + 7:].split()
            if f[0] == "nav":
                navs.append((int(f[1]), float(f[2]), float(f[3]), float(f[4]), f[6] if len(f) > 6 else f"nav{len(navs)}"))
            elif f[0] == "edge" and len(f) >= 4:
                edges.append((f[1], f[2], float(f[3])))
            elif f[0] == "player":
                player = (float(f[2]), float(f[3]))
                player_zone[0] = int(f[1])
    for a in actors:
        a["fires"] = ([a["event"]] if a["event"] else []) + extra.get(a["name"], [])
    return actors, navs, edges, player, mapname


def walking(navs, edges, player):
    """Path distance (along the AI path network) from the player start to every nav point."""
    graph = collections.defaultdict(list)
    for a, b, d in edges:
        graph[a].append((b, d))
    pos = {n[4]: (n[1], n[2], n[3]) for n in navs}
    if not player or not pos:
        return {}, pos
    # doors, lifts and ladders often aren't AI paths, which splits the network into islands:
    # bridge path points within 800 units with a straight link at 1.5x the cost
    keys = list(pos)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            d = math.dist(pos[a], pos[b])
            if d < 800:
                graph[a].append((b, d * 1.5))
                graph[b].append((a, d * 1.5))
    def search(start, offset):
        dist, todo = {start: offset}, [(offset, start)]
        while todo:
            d, n = heapq.heappop(todo)
            if d > dist.get(n, 1e18):
                continue
            for m, w in graph[n]:
                if d + w < dist.get(m, 1e18):
                    dist[m] = d + w
                    heapq.heappush(todo, (d + w, m))
        return dist

    # start from the path point nearest the player; if that one is cut off (Sanctuary's crash site:
    # the game moves the player on with a script), take the nearest one that reaches most of the
    # network, counting the gap to it as a straight line
    near = sorted(pos, key=lambda k: math.dist(pos[k][:2], player))[:25]
    first = search(near[0], math.dist(pos[near[0]][:2], player))
    if len(first) >= len(pos) // 2:
        return first, pos
    best = max((search(k, math.dist(pos[k][:2], player)) for k in near), key=len)
    return best, pos


def walk_to(a, dist, pos):
    """Walking distance to an actor: path distance to a reachable nav point plus the last stretch."""
    best = None
    for k, p in pos.items():
        if k in dist:
            score = dist[k] + math.dist(p, (a["x"], a["y"], a["z"]))
            if best is None or score < best:
                best = score
    return best if best is not None else float("inf")


def label(a):
    return f"{a['kind']} {a['cls']}" + (f" [{a['tag']}]" if a["tag"] not in (a["cls"], "None", "") else "")


def main():
    log = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "beatgraph"
    actors, navs, edges, player, mapname = parse(log)
    dist, pos = walking(navs, edges, player)
    by_tag = collections.defaultdict(list)
    for a in actors:
        by_tag[a["tag"]].append(a)
    fired = {e for a in actors for e in a["fires"]}
    receives = {a["name"] for a in actors if a["tag"] in fired}
    actors = [a for a in actors if a["fires"] or a["name"] in receives or a["kind"] in ("cutscene", "exit")]

    def reach(a, seen):
        """Every actor downstream of a (through event -> tag links)."""
        for e in a["fires"]:
            for b in by_tag.get(e, []):
                if b["name"] not in seen:
                    seen[b["name"]] = b
                    reach(b, seen)
        return seen

    roots = [a for a in actors if a["fires"] and a["name"] not in receives]
    chains = []
    for r in roots:
        down = reach(r, {})
        kinds = collections.Counter(b["kind"] for b in down.values())
        story = any(k in STORY_KINDS for k in kinds) or r["kind"] in ("exit", "objective")
        if player and r["zone"] == player_zone[0]:
            d = math.dist((r["x"], r["y"]), player)      # the start area: often not on the path network
        else:
            d = walk_to(r, dist, pos) if dist else (math.dist((r["x"], r["y"]), player) if player else 0)
        chains.append(dict(root=r, down=list(down.values()), kinds=kinds, story=story, dist=d))
    chains.sort(key=lambda c: c["dist"])

    with open(out + ".md", "w", encoding="utf-8") as f:
        story = [c for c in chains if c["story"]]
        f.write(f"# Beat graph: {mapname}\n\n{len(actors)} wired actors, {len(chains)} chains "
                f"({len(story)} reach a door, cutscene, counter, AI or exit; the rest are ambience).\n"
                "Chains are listed by walking distance from the player start along the AI path network "
                "(the order a player meets them, ignoring locked doors).\n\n## Story chains\n\n")
        for c in story:
            r = c["root"]
            dd = "unreachable" if c["dist"] == float("inf") else f"{int(c['dist'])} walked"
            f.write(f"- **{', '.join(r['fires'])}** from {label(r)} in zone {r['zone']} ({dd})\n")
            for b in c["down"]:
                f.write(f"  - -> {label(b)} in zone {b['zone']}" + (f", fires {', '.join(b['fires'])}" if b["fires"] else "") + "\n")
        f.write("\n## Ambience chains (sounds, effects, props)\n\n")
        amb = collections.Counter(",".join(c["root"]["fires"]) for c in chains if not c["story"])
        f.write(", ".join(e + (f" x{n}" if n > 1 else "") for e, n in amb.most_common()) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 11), dpi=110)
    np_ = {n[4]: n for n in navs}
    for a_, b_, _ in edges:
        if a_ in np_ and b_ in np_:
            ax.plot([np_[a_][1], np_[b_][1]], [-np_[a_][2], -np_[b_][2]], color="lightgray", lw=0.5, zorder=0)
    ax.scatter([n[1] for n in navs], [-n[2] for n in navs], s=6, color="lightgray", label="AI path network")
    for c in chains:
        if not c["story"]:
            continue
        r = c["root"]
        for b in c["down"]:
            src = next((x for x in [r] + c["down"] if b["tag"] in x["fires"]), r)
            ax.annotate("", xy=(b["x"], -b["y"]), xytext=(src["x"], -src["y"]),
                        arrowprops=dict(arrowstyle="->", color="tab:red", alpha=0.45, lw=1))
    shown = set()
    for a in actors:
        if a["kind"] in ("sound", "effect", "light") or (a["kind"] == "other" and a["cls"] == "ExplosiveCannister"):
            continue
        lab = a["kind"] if a["kind"] not in shown else None
        shown.add(a["kind"])
        ax.scatter(a["x"], -a["y"], s=45, color=KIND_COLOUR.get(a["kind"], "tab:olive"), label=lab, zorder=3,
                   edgecolors="white", linewidths=0.5)
        if a["kind"] in ("cutscene", "door", "counter", "exit", "objective"):
            ax.annotate(a["tag"] if a["kind"] != "counter" else ",".join(a["fires"]), (a["x"], -a["y"]), fontsize=7,
                        xytext=(4, 4), textcoords="offset points")
    if player:
        ax.scatter(player[0], -player[1], marker="P", s=200, color="green", label="player start", zorder=4)
    ax.set_title(f"{mapname}: event wiring (story chains in red), AI path network in gray, top-down")
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out + ".png")
    print(f"wrote {out}.md and {out}.png: {len(chains)} chains, {sum(c['story'] for c in chains)} story, "
          f"{len(edges)} path links, {len(dist)} of {len(navs)} path points reachable")


if __name__ == "__main__":
    main()
