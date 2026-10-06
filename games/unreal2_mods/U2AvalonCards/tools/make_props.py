"""A kit-bash layout -> the Props[] lines of System\\U2AvalonCards.ini (AvalonCards places them at map load).

    python make_props.py <layout.txt> <bounds.txt> <U2AvalonCards.ini>

layout.txt, one prop per line (# comments):  Package.Group.Name X Y Yaw Scale [Lift]
  X Y = where the mesh's centre goes, Yaw in degrees, Lift = units above the land / sea under it.
  or a plain box:  block X Y Yaw SizeX SizeY SizeZ [Lift] [Colour 0 grey/1 rust/2 pale/3 dark]
  or a baked building card:  card Name X Y Yaw Size [Frames] [Lift]   (Name = CoolingTower, DockCrane ...)
bounds.txt is mesh_bounds.py's output (gives each mesh's centre and bottom). The ini's old Props[] lines
are replaced; everything else in it is kept.
"""
import re, sys

layout, bounds, ini = sys.argv[1:4]
B = {}
for l in open(bounds):
    w = l.split()
    B[w[0].lower()] = [float(v) for v in w[1:7]]
props, blocks, cards = [], [], []
for l in open(layout):
    l = l.split("#")[0].split()
    if not l:
        continue
    if l[0] == "card":        # card Name X Y Yaw Size [Frames] [Lift]
        cards.append(" ".join((l[1:] + ["8", "0"])[:7]))
        continue
    if l[0] == "block":       # block X Y Yaw SizeX SizeY SizeZ [Lift] [Colour]
        blocks.append(" ".join((l[1:] + ["0", "0"])[:8]))
        continue
    mesh, x, y, yaw, scale = l[:5]
    lift = l[5] if len(l) > 5 else "0"
    b = B.get(mesh.lower())
    if b is None:
        sys.exit("no bounds for " + mesh)
    cx, cy, minz = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[2]
    props.append("%s %s %s %s %s %s %.0f %.0f %.0f" % (mesh, x, y, yaw, scale, lift, cx, cy, minz))
txt = open(ini, newline="").read().replace("\r\n", "\n")
txt = re.sub(r"(?m)^(Props|Blocks|Cards)\[\d+\]=.*\n", "", txt)
head = "[U2AvalonCards.AvalonCards]\n"
i = txt.index(head) + len(head)
txt = (txt[:i] + "".join("Props[%d]=%s\n" % (k, p) for k, p in enumerate(props))
       + "".join("Blocks[%d]=%s\n" % (k, b) for k, b in enumerate(blocks))
       + "".join("Cards[%d]=%s\n" % (k, c) for k, c in enumerate(cards)) + txt[i:])
open(ini, "w", newline="").write(txt.replace("\n", "\r\n"))
print(len(props), "props,", len(blocks), "blocks,", len(cards), "cards ->", ini)
