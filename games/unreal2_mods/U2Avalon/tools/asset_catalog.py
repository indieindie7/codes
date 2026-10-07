r"""What can be placed live: every static mesh in Unreal II's StaticMeshes packages and every imposter card
in U2AvalonCards, as one searchable list for the live editor (avalon spawn / row / scatter / cardat).

    py tools/asset_catalog.py            -> data/asset_catalog.txt (+ a summary per package)
    py tools/asset_catalog.py crate      -> print the matches for a word

Lines: "mesh Package.Group.Name" (for spawn/row/scatter) and "card Name" (for cardat; the 8 views
Name0..Name7 exist).
"""
import glob, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u2pkg  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
OUT = os.path.join(os.path.dirname(HERE), "data", "asset_catalog.txt")
PRIVATE = ("U2UTFlakSM",)       # built from UT2004 assets: those stay private, not listed in the repo


def build():
    lines, per = [], Counter()
    for f in sorted(glob.glob(os.path.join(GAME, "StaticMeshes", "*.usx"))):
        pkg = os.path.splitext(os.path.basename(f))[0]
        if pkg in PRIVATE:
            continue
        try:
            for cls, path, size in u2pkg.load(f):
                if cls == "StaticMesh":
                    lines.append("mesh %s.%s" % (pkg, path))
                    per[pkg] += 1
        except Exception as e:                      # one odd package shouldn't stop the list
            print("skip", pkg, e)
    cards = set()
    for pkgfile, prefix in ((os.path.join(GAME, "System", "U2AvalonCards.u"), ""),
                            (os.path.join(GAME, "StaticMeshes", "AvalonSM.usx"), "AvalonSM.")):
        try:
            for cls, path, size in u2pkg.load(pkgfile):
                m = re.match(r"(.*?)([0-7])$", path)
                if cls == "Texture" and m and m.group(2) == "0" and (not prefix or path.startswith("Cards.")):
                    cards.add(prefix + m.group(1))
        except Exception as e:
            print("cards:", e)
    lines += ["card %s" % c for c in sorted(cards)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(lines) + "\n")
    print("%d meshes in %d packages, %d cards -> %s" % (sum(per.values()), len(per), len(cards), OUT))
    for p, n in per.most_common():
        print("  %5d %s" % (n, p))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if not os.path.exists(OUT):
            build()
        w = sys.argv[1].lower()
        for l in open(OUT):
            if w in l.lower():
                print(l.rstrip())
    else:
        build()
