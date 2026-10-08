r"""The co-GM: the creative team proposes, the game master decides (U2GM research, end goal "Claude as co-GM proposes
ops for approval"; the user, 2026-10-08: "fold the game master tools and agent into the agents and the director").

Each role's redesign proposals (mapreview.py's <map>_redesign.json) become GM commands in
<game>\System\U2GMProposals_<family>.txt:

    gm propose writer gore pool X Y Z DX DY # why
    gm propose director light X Y Z 150 24 110 24 # why
    gm propose level mesh Mission_08M.Crates.Boxnum2 X Y Z YAW 1 # why

In the game: "gm proposals load", "gm proposals", "gm goto N", "gm accept N|all|writer|director|level",
"gm reject ...". An accepted proposal is an ordinary journal line, so undo, the panel and gm commit (which bakes
lights and crates into <Map>_LiveN) all work on it. The team's next review sees the journal (mapreview.py gm=).

    py cogm.py [review_dir] [--game GAME_DIR]
"""
import glob, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
CRATE = "Mission_08M.Crates.Boxnum2"


def lines_for(P):
    out = []
    for g in P["gore"]:
        x, y, z = g["at"]
        d = g.get("spray_dir", [0, 0])
        for k in g["kinds"]:
            if k == "drag_trail" and "trail_to" in g:
                tx, ty = g["trail_to"][0] - x, g["trail_to"][1] - y
                n = math.hypot(tx, ty) or 1
                d = [round(tx / n, 2), round(ty / n, 2)]
            why = g.get("why") or ("%s's body: %s" % (g.get("body", "a colonist"), k.replace("_", " ")))
            out.append("gm propose writer gore %s %d %d %d %.2f %.2f # %s" % (k, x, y, z, d[0], d[1], why))
    for L in P["lights"]:
        x, y, z = L["at"]
        out.append("gm propose director light %d %d %d 150 24 110 24 # %s" % (x, y, z + 170, L["why"]))
    for c in P["cover"]:
        x, y, z = c["at"]
        for i, a in enumerate((0.3, 2.4, 4.5)):
            # nav points stand ~50 over the floor: the crate goes there (gm goto, then gm moveto here to fix)
            out.append("gm propose level mesh %s %d %d %d %d 1 # %s (crate %d of 3)" % (
                CRATE, x + 400 * math.cos(a), y + 400 * math.sin(a), z - 50, (i * 120 + 30) % 360, c["why"], i + 1))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    game = GAME
    if "--game" in sys.argv:
        game = sys.argv[sys.argv.index("--game") + 1]
        args = [a for a in args if a != game]
    rev = args[0] if args else os.path.join(HERE, "..", "review")
    for f in sorted(glob.glob(os.path.join(rev, "*_redesign.json"))):
        if "_after_" in f:
            continue
        m = os.path.basename(f).split("_")[0]
        L = lines_for(json.load(open(f))["proposals"])
        out = os.path.join(game, "System", "U2GMProposals_%s.txt" % m.lower())
        open(out, "w", newline="\r\n").write("\n".join(L) + "\n")
        print("%s: %d proposals -> %s" % (m, len(L), out))


if __name__ == "__main__":
    main()
