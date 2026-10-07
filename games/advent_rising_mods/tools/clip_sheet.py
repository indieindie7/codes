"""A stick-figure contact sheet of clips on a skeleton, to check poses and signs before a game run.

    <python with PIL> tools/clip_sheet.py <mesh> <clip folder> <out.png> [frames per clip=6]

Forward kinematics as make_psa.py assumes it (reference rotations identity, a bone's rotation
local to its parent, the root offset in mesh space). Two views per frame: from the side (the
body's left; forward to the right of the picture) and from behind; up is up.
"""
import glob
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_psa import read_skeleton, qmul, MESHES   # noqa: E402


def rotate(q, v):
    x, y, z, w = q
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return p[:3]


def pose(bones, frame):
    root, rots = frame
    wr, wp = [], []
    for i, b in enumerate(bones):
        q = tuple(rots.get(b["name"], (0, 0, 0, 1)))
        if i == 0:
            wr.append(q)
            wp.append(tuple(b["pos"][k] + root[k] for k in range(3)))
        else:
            p = b["parent"]
            wr.append(qmul(wr[p], q))
            off = rotate(wr[p], b["pos"])
            wp.append(tuple(wp[p][k] + off[k] for k in range(3)))
    return wp


def main():
    from PIL import Image, ImageDraw     # only the sheet needs it (pose() is used by make_hound_clips.py)
    mesh, folder, out = sys.argv[1:4]
    per = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    bones = read_skeleton(os.path.join(MESHES, mesh + ".psk"))
    files = sorted(glob.glob(os.path.join(folder, "*.json")))
    cell, scale = 150, 0.5
    img = Image.new("RGB", (cell * 2 * per, cell * len(files) + 4), (250, 250, 248))
    d = ImageDraw.Draw(img)
    for r, fn in enumerate(files):
        clip = json.load(open(fn))
        fr = clip["frames"]
        if clip.get("spine_half_turn"):        # make_hound_clips.py: undo the in-game correction for the picture
            for f in fr:
                f["rot"]["spine"] = list(qmul((0.0, 0.0, -1.0, 0.0), tuple(f["rot"]["spine"])))
                for b in ("spine1", "spine2", "neck", "Neck02", "head", "jaw"):
                    if b in f["rot"]:
                        x, y, z, w = f["rot"][b]
                        f["rot"][b] = [-x, -y, z, w]
        d.text((4, r * cell + 2), os.path.basename(fn)[:-5], fill=(0, 0, 0))
        for c in range(per):
            f = fr[round(c * (len(fr) - 1) / (per - 1))]
            wp = pose(bones, (f["root"], f["rot"]))
            for v, (ax, sign) in enumerate([(2, 1), (0, -1)]):     # side: z right; back: -x right (the body's left on the left)
                ox, oy = (2 * c + v) * cell + cell // 2, r * cell + cell - 14
                d.line((ox - cell // 2 + 4, oy, ox + cell // 2 - 4, oy), fill=(200, 190, 170))
                P = lambda p: (ox + sign * p[ax] * scale, oy + p[1] * scale)
                for i, b in enumerate(bones):
                    if i == 0:
                        continue
                    left = b["name"].lower().startswith("left")
                    col = (40, 90, 200) if left else (200, 60, 40) if b["name"].lower().startswith("right") else (30, 30, 30)
                    d.line((*P(wp[b["parent"]]), *P(wp[i])), fill=col, width=2)
                d.ellipse((P(wp[0])[0] - 3, P(wp[0])[1] - 3, P(wp[0])[0] + 3, P(wp[0])[1] + 3), fill=(0, 150, 0))
        # how far the clip's lowest bone goes through the floor (mesh +Y is down; the floor is y=0)
        worst = []
        for k in range(0, len(fr), max(1, len(fr) // 12)):
            wp = pose(bones, (fr[k]["root"], fr[k]["rot"]))
            i = max(range(len(wp)), key=lambda j: wp[j][1])
            worst.append("%.2f:%s %+d" % (k / (len(fr) - 1), bones[i]["name"], round(wp[i][1])))
        print(os.path.basename(fn)[:-5].ljust(16), " ".join(worst))
    img.save(out)
    print(out, len(files), "clips")


if __name__ == "__main__":
    main()
