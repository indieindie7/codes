"""A kit-bash layout -> the Props[] lines of System\\U2AvalonCards.ini (AvalonCards places them at map load).

    python make_props.py <layout.txt> <bounds.txt> <U2AvalonCards.ini>

layout.txt, one prop per line (# comments):  Package.Group.Name X Y Yaw Scale [Lift]
  X Y = where the mesh's centre goes, Yaw in degrees, Lift = units above the land / sea under it.
bounds.txt is mesh_bounds.py's output (gives each mesh's centre and bottom). The ini's old Props[] lines
are replaced; everything else in it is kept.
"""
import re, sys

layout, bounds, ini = sys.argv[1:4]
B = {}
for l in open(bounds):
    w = l.split()
    B[w[0].lower()] = [float(v) for v in w[1:7]]
props = []
for l in open(layout):
    l = l.split("#")[0].split()
    if not l:
        continue
    mesh, x, y, yaw, scale = l[:5]
    lift = l[5] if len(l) > 5 else "0"
    b = B.get(mesh.lower())
    if b is None:
        sys.exit("no bounds for " + mesh)
    cx, cy, minz = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[2]
    props.append("%s %s %s %s %s %s %.0f %.0f %.0f" % (mesh, x, y, yaw, scale, lift, cx, cy, minz))
txt = open(ini, newline="").read().replace("\r\n", "\n")
txt = re.sub(r"(?m)^Props\[\d+\]=.*\n", "", txt)
head = "[U2AvalonCards.AvalonCards]\n"
i = txt.index(head) + len(head)
txt = txt[:i] + "".join("Props[%d]=%s\n" % (k, p) for k, p in enumerate(props)) + txt[i:]
open(ini, "w", newline="").write(txt.replace("\n", "\r\n"))
print(len(props), "props ->", ini)
