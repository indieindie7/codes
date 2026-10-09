"""The armour test's contact sheet: every "armour hit:" line of a run's AdventNative.log as a dot
(orange = armour, blue = flesh) over (1) the enemy's ref-pose render, front and side, using the
hit's mesh-space point, and (2) the screenshot, using the world point and the camera the grid
logged ("armourcam: (X,Y,Z) (Pitch,Yaw,Roll) fov F ...").

    py -I armour_sheet.py <run.log> <mesh name> <screenshot.png or -> <out.png>
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\games\advent_rising_mods\tools")
from PIL import Image, ImageDraw  # noqa: E402
import psk_preview  # noqa: E402
import make_armour_data as mad  # noqa: E402
psk_preview.colour = lambda b: (0.6, 0.6, 0.65)

HIT = re.compile(r"armour hit: (\S+) (\S+) armour=(yes|no) uv=([\d.-]+),([\d.-]+) tri=(\d+) section=(\S+) at ([\d.-]+) ([\d.-]+) ([\d.-]+) mesh ([\d.-]+) ([\d.-]+) ([\d.-]+)")
CAM = re.compile(r"armourcam: ([\d.-]+),([\d.-]+),([\d.-]+) \[P=(-?\d+),Y=(-?\d+),R=(-?\d+)\] fov ([\d.]+)")


def rot_axes(pitch, yaw, roll):
    """UE2 rotator (65536 units) -> forward, right, up (left-handed world, Z up)"""
    k = math.pi / 32768.0
    p, y, r = pitch * k, yaw * k, roll * k
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
    # UE2's GetAxes at roll 0: X forward, Y right (+Y at yaw 0), Z up; roll turns Y and Z about X
    fwd = (cp * cy, cp * sy, sp)
    right0 = (-sy, cy, 0.0)
    up0 = (-sp * cy, -sp * sy, cp)
    right = tuple(right0[i] * cr + up0[i] * sr for i in range(3))
    up = tuple(up0[i] * cr - right0[i] * sr for i in range(3))
    return fwd, right, up


def project(p, cam, W, H):
    (cx, cy, cz), (pitch, yaw, roll), fov = cam
    fwd, right, up = rot_axes(pitch, yaw, roll)
    d = (p[0] - cx, p[1] - cy, p[2] - cz)
    x = sum(d[i] * fwd[i] for i in range(3))
    if x < 1:
        return None
    y = sum(d[i] * right[i] for i in range(3))
    z = sum(d[i] * up[i] for i in range(3))
    f = (W / 2.0) / math.tan(math.radians(fov) / 2.0)
    return (W / 2.0 + y / x * f, H / 2.0 - z / x * f)


def main():
    log, mesh, shot, out = sys.argv[1:5]
    hits, cam = [], None
    for line in open(log, encoding="utf-8", errors="replace"):
        m = HIT.search(line)
        if m:
            hits.append(dict(pawn=m.group(1), bone=m.group(2), armour=m.group(3) == "yes", uv=(float(m.group(4)), float(m.group(5))),
                             world=tuple(float(m.group(i)) for i in (8, 9, 10)), mesh=tuple(float(m.group(i)) for i in (11, 12, 13))))
        c = CAM.search(line)
        if c:
            cam = (tuple(float(c.group(i)) for i in (1, 2, 3)), tuple(int(c.group(i)) for i in (4, 5, 6)), float(c.group(7)))
    print("%d hits (%d armour), camera %s" % (len(hits), sum(h["armour"] for h in hits), cam))
    # the ref-pose render, front and side, hit points projected the way psk_preview projects
    pts, wedges, faces, mats, bones, weights = mad.read_psk(os.path.expanduser("~/Documents/AdventRising_meshes/%s.psk" % mesh))
    S = 512
    panels = []
    for view in ("front", "side"):
        img = psk_preview.render(pts, [w[0] for w in wedges], [f[:3] for f in faces], {}, S, S, view)
        im = Image.new("RGB", (S, S)); px = im.load()
        for y in range(S):
            for x in range(S):
                px[x, y] = img[y][x]
        proj = (lambda p: (p[0], -p[1], p[2])) if view == "front" else (lambda p: (p[2], -p[1], -p[0]))
        P = [proj(p) for p in pts]
        xs, ys = [p[0] for p in P], [p[1] for p in P]
        s = 0.9 * min(S / (max(xs) - min(xs) + 1e-6), S / (max(ys) - min(ys) + 1e-6))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        d = ImageDraw.Draw(im)
        for h in hits:
            q = proj(h["mesh"])
            x, y = S / 2 + (q[0] - cx) * s, S / 2 - (q[1] - cy) * s
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 120, 0) if h["armour"] else (60, 140, 255), outline=(0, 0, 0))
        d.text((6, 6), "%s %s: %d hits, %d armour" % (mesh, view, len(hits), sum(h["armour"] for h in hits)), fill=(255, 255, 255))
        panels.append(im)
    sheet_w = 2 * S
    shot_im = None
    if shot != "-" and os.path.exists(shot) and cam:
        shot_im = Image.open(shot).convert("RGB")
        W, H = shot_im.size
        d = ImageDraw.Draw(shot_im)
        for h in hits:
            q = project(h["world"], cam, W, H)
            if q:
                d.ellipse((q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6), fill=(255, 120, 0) if h["armour"] else (60, 140, 255), outline=(0, 0, 0))
        shot_im = shot_im.resize((int(W * (2 * S) / W), int(H * (2 * S) / W)))
    sheet = Image.new("RGB", (sheet_w, S + (shot_im.size[1] if shot_im else 0)), (30, 30, 30))
    sheet.paste(panels[0], (0, 0)); sheet.paste(panels[1], (S, 0))
    if shot_im:
        sheet.paste(shot_im, (0, S))
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
