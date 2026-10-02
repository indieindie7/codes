"""Beat graph of an Unreal II level: its event wiring, from the "Beats:" lines of `hub beats`.

    py -3.13 beatgraph.py GAME.log [out_prefix]

Unreal levels are wired with names: an actor fires its Event, and every actor whose Tag matches
reacts (a door opens, a cutscene plays, a counter counts, AI wakes up). This links them into a
directed graph, follows each chain from where it starts (the player start, triggers the player
walks into, enemies whose death fires an event) and marks the chains that matter for the story:
the ones that reach a door, a cutscene, a counter (a kill-gate: "all of these dead") or a level
exit. Everything else (sounds, effects, ambience) is listed separately.

Writes out_prefix.md (chains, in rough path order: by distance from the player start) and
out_prefix.png (the chains drawn top-down over the level's navigation points, from `hub zones`).
"""
import collections
import math
import re
import sys

STORY_KINDS = {"door", "cutscene", "counter", "exit", "objective", "aiscript", "pawn"}
EXIT_WORDS = ("goesto", "travel", "nextlevel", "mapchange")
KIND_COLOUR = {"trigger": "tab:blue", "counter": "tab:purple", "door": "tab:brown", "cutscene": "tab:red",
               "pawn": "tab:orange", "exit": "black", "objective": "tab:green", "sound": "tab:gray",
               "other": "tab:olive", "aiscript": "tab:pink", "light": "gold", "effect": "tab:cyan"}


def parse(path):
    actors, navs, player, mapname = [], [], None, "?"
    for line in open(path, encoding="latin-1"):
        i = line.find("Beats: ")
        if i >= 0:
            f = line[i + 7:].split()
            if f[0] == "map":
                mapname = f[1]
                continue
            tag = re.search(r"tag=(\S*)", line).group(1)
            event = re.search(r"event=(\S*)", line).group(1)
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
                navs.append((int(f[1]), float(f[2]), float(f[3])))
            elif f[0] == "player":
                player = (float(f[2]), float(f[3]))
    return actors, navs, player, mapname


def main():
    log = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "beatgraph"
    actors, navs, player, mapname = parse(log)
    by_tag = collections.defaultdict(list)
    for a in actors:
        by_tag[a["tag"]].append(a)
    receives = {a["name"] for a in actors if any(b["event"] == a["tag"] for b in actors if b["event"])}

    def reach(a, seen):
        """Every actor downstream of a (through event -> tag links)."""
        for b in by_tag.get(a["event"], []) if a["event"] else []:
            if b["name"] not in seen:
                seen[b["name"]] = b
                reach(b, seen)
        return seen

    roots = [a for a in actors if a["event"] and a["name"] not in receives]
    chains = []
    for r in roots:
        down = reach(r, {})
        kinds = collections.Counter(b["kind"] for b in down.values())
        story = any(k in STORY_KINDS for k in kinds) or r["kind"] in ("exit", "objective")
        dist = math.dist((r["x"], r["y"]), player) if player else 0
        chains.append(dict(root=r, down=list(down.values()), kinds=kinds, story=story, dist=dist))
    chains.sort(key=lambda c: c["dist"])

    def label(a):
        return f"{a['kind']} {a['cls']}" + (f" [{a['tag']}]" if a["tag"] not in (a["cls"], "None", "") else "")

    with open(out + ".md", "w", encoding="utf-8") as f:
        story = [c for c in chains if c["story"]]
        f.write(f"# Beat graph: {mapname}\n\n{len(actors)} wired actors, {len(chains)} chains "
                f"({len(story)} reach a door, cutscene, counter, AI or exit; the rest are ambience).\n"
                "Chains are listed by the starting point's distance from the player start (a rough path order).\n\n")
        f.write("## Story chains\n\n")
        for c in story:
            r = c["root"]
            f.write(f"- **{r['event']}** from {label(r)} in zone {r['zone']} ({int(c['dist'])} from start)\n")
            for b in c["down"]:
                f.write(f"  - -> {label(b)} in zone {b['zone']}" + (f", fires {b['event']}" if b["event"] else "") + "\n")
        f.write("\n## Ambience chains (sounds, effects, props)\n\n")
        amb = collections.Counter(c["root"]["event"] for c in chains if not c["story"])
        f.write(", ".join(f"{e}" + (f" x{n}" if n > 1 else "") for e, n in amb.most_common()) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 11), dpi=110)
    ax.scatter([n[1] for n in navs], [-n[2] for n in navs], s=6, color="lightgray", label="AI path points")
    for c in chains:
        if not c["story"]:
            continue
        r = c["root"]
        for b in c["down"]:
            src = next((x for x in [r] + c["down"] if x["event"] == b["tag"]), r)
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
            ax.annotate(a["tag"] if a["kind"] != "counter" else a["event"], (a["x"], -a["y"]), fontsize=7,
                        xytext=(4, 4), textcoords="offset points")
    if player:
        ax.scatter(player[0], -player[1], marker="P", s=200, color="green", label="player start", zorder=4)
    ax.set_title(f"{mapname}: event wiring (story chains in red arrows), top-down")
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out + ".png")
    print(f"wrote {out}.md and {out}.png: {len(chains)} chains, {sum(c['story'] for c in chains)} story")


if __name__ == "__main__":
    main()
