"""The creative team's redesign proposals (review/<map>_redesign.json, from mapreview.py) -> the scene list the
SanctuaryDirector places at map start (System/U2Sanctuary.ini, [U2Sanctuary.SanctuaryDirector] Scenes=...).

    py tools/make_scenes.py [review_dir] [out.ini]
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "review")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "System", "U2Sanctuary.ini")


def v(p):
    p = list(p) + [0, 0, 0]
    return "(X=%.1f,Y=%.1f,Z=%.1f)" % (p[0], p[1], p[2])


def main():
    lines = ["[U2Sanctuary.SanctuaryDirector]", "bEnabled=True", "bLog=False", "CoverMesh=Mission_08M.Crates.Boxnum2"]
    n = 0
    for f in sorted(glob.glob(os.path.join(REV, "*_redesign.json"))):
        m = os.path.basename(f).split("_")[0]
        P = json.load(open(f))["proposals"]
        for g in P["gore"]:
            for k in g["kinds"]:
                d = g.get("spray_dir", [0, 0]) + [0]
                to = g.get("trail_to", g["at"])
                lines.append('Scenes=(Map="%s",Kind="%s",At=%s,Dir=%s,To=%s)' % (m, k, v(g["at"]), v(d), v(to)))
                n += 1
        for x in P["lights"]:
            lines.append('Scenes=(Map="%s",Kind="keylight",At=%s)' % (m, v(x["at"])))
            n += 1
        for x in P["cover"]:
            lines.append('Scenes=(Map="%s",Kind="cover",At=%s)' % (m, v(x["at"])))
            n += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", newline="\r\n").write("\n".join(lines) + "\n")
    print(n, "scenes ->", OUT)


if __name__ == "__main__":
    main()
