"""Armour sections for AdventMod's per-hit armour test (ARMOUR.md, "where the plates are").

Every enemy mesh in Advent is one material section, so the armour/flesh split is made per
triangle from the texture: the game's own chrome mask (the Red channel of the *_rgb / *_rg
texture the HWSkinShader uses as SpecularMaskMaterial: where the renderer draws the chrome
reflection, the surface is hard) sampled over each face's UV triangle. The Seeker infantry's
material has no mask; its sheet shares the elite's UV islands, so the elite's mask serves it
(the script measures how many faces match before trusting that).

For each mesh it writes
  <out>/<mesh>.amesh      the skinned-hit data the native test loads (ref skeleton, vertices
                          with up to 4 weights, faces with UVs and the armour flag)
  <out>/<mesh>_mask.png   a 1-bit mask (armour faces rasterised in UV space; no texture pixels)
  <out>/<mesh>_faces.png  a check sheet: the diffuse with armour faces tinted (game pixels: scratchpad only)
and prints the inventory table and the per-bone armour shares (the script-side fallback).

    py -I make_armour_data.py <meshes dir> <utx dir> <out dir> [mesh ...]
"""
import math
import os
import struct
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\games\advent_rising_mods\tools")
import utx_tex  # noqa: E402
from ukx import Package  # noqa: E402

# mesh -> (package, material, mask texture or None, mask channel, diffuse); None mask = borrow from 'borrow'
ENEMIES = {
    "seekerinfantry": dict(pkg="seekercharacters_tx.utx", mat="seekerinfantry_hsh", mask=None, borrow="SeekerElite", diffuse="seeker_infantry", pawn="SeekerInfantry"),
    "SeekerElite": dict(pkg="seekercharacters_tx.utx", mat="eliteu_hsh", mask="seekerelite_rgb", ch=0, diffuse="seeker_elite", pawn="SeekerElite"),
    "SeekerCommander": dict(pkg="seekercharacters_tx.utx", mat="comanderu_hsh", mask="seeker_commander_rgb", ch=0, diffuse="seeker_commander", pawn="SeekerCommander, SeekerRanhor"),
    "seekerpilot": dict(pkg="seekercharacters_tx.utx", mat="skrspace_hsh", mask="seekerspace_rg", ch=0, diffuse="seeker_space", pawn="SeekerPilot"),
    "SeekerScanner": dict(pkg="seekercharacters_tx.utx", mat="seekerscanner_hsh", mask="seeker_scanner_rgb", ch=0, diffuse="seeker_scanner", pawn="SeekerScanner, SeekerClayPigeon"),
    "seekerhound": dict(pkg="seekercharacters_tx.utx", mat="seekerhound_hsh", mask="seekerhound_rg", ch=0, diffuse="seekerhound", pawn="SeekerDog"),
    "seekershocktrooper": dict(pkg="seekercharacters_tx.utx", mat="shocktrooper_hsh", mask="shocktrooper_rg", ch=0, diffuse="ShockTrooper", pawn="ShockTrooper"),
    "kchell": dict(pkg="seekercharacters_tx.utx", mat="Ambassador_HSH", mask="ambassador_rgb", ch=0, diffuse="ambassador", pawn="SeekerKchell"),
    "specops": dict(pkg="humancharacters_tx.utx", mat="specops_hsh", mask="specops_rg", ch=0, diffuse="specops", pawn="SpecOpsSoldier"),
}
MASK_LEVEL = 0.35      # a texel is "hard" above this much chrome mask
FACE_LEVEL = 0.5       # a face is armour when this share of its samples are hard


def read_psk(path):
    d = open(path, "rb").read()
    o, ch = 0, {}
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        size, count = struct.unpack_from("<ii", d, o + 24)
        ch[cid] = (d[o + 32:o + 32 + size * count], size, count)
        o += 32 + size * count
    get = lambda cid: ch.get(cid, (b"", 0, 0))
    b, s, n = get("PNTS0000")
    pts = [struct.unpack_from("<3f", b, s * i) for i in range(n)]
    b, s, n = get("VTXW0000")
    wedges = [struct.unpack_from("<HHffB", b, s * i) for i in range(n)]   # point, pad, u, v, mat
    b, s, n = get("FACE0000")
    faces = [struct.unpack_from("<HHHB", b, s * i) for i in range(n)]      # 3 wedges, material
    b, s, n = get("MATT0000")
    mats = [b[s * i:s * i + 64].split(b"\0")[0].decode("latin1") for i in range(n)]
    b, s, n = get("REFSKELT")
    bones = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        flags, children, parent = struct.unpack_from("<Iii", b, s * i + 64)
        q = struct.unpack_from("<4f", b, s * i + 76)
        pos = struct.unpack_from("<3f", b, s * i + 92)
        bones.append(dict(name=name, parent=parent if i else -1, quat=q, pos=pos))
    b, s, n = get("RAWWEIGHTS")
    weights = [struct.unpack_from("<fii", b, s * i) for i in range(n)]     # weight, point, bone
    return pts, wedges, faces, mats, bones, weights


def quat_mat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(a, v):
    return tuple(sum(a[i][k] * v[k] for k in range(3)) for i in range(3))


def vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def vsub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def vlen(a):
    return math.sqrt(sum(x * x for x in a))


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def ref_pose(bones, conj_root, conj_child):
    """mesh-space (R, O) per bone: O = O_p + R_p pos, R = R_p * local"""
    R, O = [], []
    for i, b in enumerate(bones):
        q = b["quat"]
        if (i == 0 and conj_root) or (i > 0 and conj_child):
            q = (-q[0], -q[1], -q[2], q[3])
        L = quat_mat(q)
        if i == 0:
            R.append(L); O.append(tuple(b["pos"]))
        else:
            p = b["parent"]
            R.append(mm(R[p], L)); O.append(vadd(O[p], mv(R[p], b["pos"])))
    return R, O


def pick_convention(bones, pts, dom):
    """the quaternion convention whose ref pose puts every bone at its own vertices (the
    centroid of the points it drives most); printed, and the best is used"""
    best = None
    for cr in (False, True):
        for cc in (False, True):
            R, O = ref_pose(bones, cr, cc)
            err, n = 0.0, 0
            for b in range(len(bones)):
                idx = [i for i in range(len(pts)) if dom[i] == b]
                if len(idx) < 4:
                    continue
                c = tuple(sum(pts[i][k] for i in idx) / len(idx) for k in range(3))
                err += vlen(vsub(c, O[b])); n += 1
            err /= max(n, 1)
            print("  convention root%s child%s: bone->vertex centroid %.1f units" % (" conj" if cr else "", " conj" if cc else "", err))
            if best is None or err < best[0]:
                best = (err, cr, cc, R, O)
    return best


def face_uv_key(wedges, f, W, H):
    return tuple(sorted((round(wedges[w][2] * W), round(wedges[w][3] * H)) for w in f[:3]))


def main():
    meshes, utxdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    only = sys.argv[4:]
    os.makedirs(out, exist_ok=True)
    pkgs = {}
    masks = {}
    rows = []
    shares_all = {}
    for mesh, info in ENEMIES.items():
        if only and mesh not in only:
            continue
        psk = os.path.join(meshes, mesh + ".psk")
        if not os.path.exists(psk):
            print(mesh, ": no psk"); continue
        pts, wedges, faces, mats, bones, weights = read_psk(psk)
        print("== %s: %d points, %d faces, %d bones, materials %s" % (mesh, len(pts), len(faces), len(bones), mats))
        # weights per point (top 4), dominant bone
        per = {}
        for w, p, b in weights:
            per.setdefault(p, []).append((w, b))
        dom = [0] * len(pts)
        infl = [[(0, 0.0)] * 4 for _ in pts]
        for p in range(len(pts)):
            l = sorted(per.get(p, [(1.0, 0)]), reverse=True)[:4]
            s = sum(w for w, b in l)
            for k, (w, b) in enumerate(l):
                infl[p][k] = (b, w / s)
            dom[p] = l[0][1]
        err, cr, cc, R, O = pick_convention(bones, pts, dom)
        # ActorX stores every bone but the root conjugated (make_psa.py; the shock trooper, whose
        # ref quats aren't near identity, confirms it: 7.0 against 15.9 units). The Seekers' ref
        # rotations are near identity, so the test can't tell there and the known convention is used.
        R, O = ref_pose(bones, False, True)
        print("  using root as-is, children conjugated (test's best: root%s child%s, %.1f)" % (" conj" if cr else "", " conj" if cc else "", err))
        # the mask
        if info["pkg"] not in pkgs:
            pkgs[info["pkg"]] = Package(os.path.join(utxdir, info["pkg"]))
        p = pkgs[info["pkg"]]
        mask_name = info["mask"] or ENEMIES[info["borrow"]]["mask"]
        ch = info.get("ch", ENEMIES.get(info.get("borrow", ""), {}).get("ch", 0))
        if mask_name not in masks:
            e = utx_tex.export_by_name(p, mask_name)
            props, fmt, w, h, nm, im = utx_tex.read_texture(p, e)
            masks[mask_name] = im.convert("RGBA").getchannel("RGBA"[ch])
        M = masks[mask_name]
        W, H = M.size
        hard = M.point(lambda v: 255 if v >= MASK_LEVEL * 255 else 0).load()
        if info["mask"] is None:
            # borrowed layout: how many faces have a UV twin in the lender's mesh
            lp = read_psk(os.path.join(meshes, info["borrow"] + ".psk"))
            keys = set(face_uv_key(lp[1], f, W, H) for f in lp[2])
            same = sum(1 for f in faces if face_uv_key(wedges, f, W, H) in keys)
            print("  mask borrowed from %s (%s): %d of %d faces have the same UV triangle (within a texel)" % (info["borrow"], mask_name, same, len(faces)))
        # per face: samples over the UV triangle (barycentric grid)
        samples = [(a / 6.0, b / 6.0) for a in range(7) for b in range(7 - a)]
        flag = [0] * len(faces)
        area = [0.0] * len(faces)
        fdom = [0] * len(faces)
        for i, f in enumerate(faces):
            uv = [(wedges[w][2], wedges[w][3]) for w in f[:3]]
            n_hard = 0
            for a, b in samples:
                c = 1 - a - b
                u = (a * uv[0][0] + b * uv[1][0] + c * uv[2][0]) % 1.0
                v = (a * uv[0][1] + b * uv[1][1] + c * uv[2][1]) % 1.0
                if hard[min(int(u * W), W - 1), min(int(v * H), H - 1)]:
                    n_hard += 1
            flag[i] = int(n_hard >= FACE_LEVEL * len(samples))
            P = [pts[wedges[w][0]] for w in f[:3]]
            area[i] = 0.5 * vlen(vcross(vsub(P[1], P[0]), vsub(P[2], P[0])))
            votes = [dom[wedges[w][0]] for w in f[:3]]
            fdom[i] = max(set(votes), key=votes.count)
        total = sum(area)
        arm_area = sum(a for a, fl in zip(area, flag) if fl)
        print("  armour faces %d of %d (%.0f%% of the surface)" % (sum(flag), len(faces), 100 * arm_area / total))
        # per-bone shares (area-weighted), bones with surface only
        shares = {}
        for b in range(len(bones)):
            sel = [i for i in range(len(faces)) if fdom[i] == b]
            tot = sum(area[i] for i in sel)
            if tot > 0:
                shares[bones[b]["name"]] = (sum(area[i] for i in sel if flag[i]) / tot, len(sel))
        shares_all[mesh] = shares
        top = sorted(shares.items(), key=lambda kv: -kv[1][1])[:16]
        print("  per bone (armour share, faces): " + ", ".join("%s %.2f/%d" % (n, s, c) for n, (s, c) in top))
        rows.append((mesh, info["pawn"], mats, len(faces), sum(flag), 100 * arm_area / total, mask_name + ("" if info["mask"] else " (borrowed)")))
        # the 1-bit mask (armour faces in UV space) and the check sheet
        mk = Image.new("1", (W, H), 0)
        dr = ImageDraw.Draw(mk)
        for i, f in enumerate(faces):
            if flag[i]:
                dr.polygon([((wedges[w][2] % 1.0) * W, (wedges[w][3] % 1.0) * H) for w in f[:3]], fill=1, outline=1)
        mk.save(os.path.join(out, mesh + "_mask.png"))
        de = utx_tex.export_by_name(p, info["diffuse"])
        _, _, dw, dh, _, dim = utx_tex.read_texture(p, de)
        dim = dim.convert("RGB").resize((W, H))
        tint = Image.new("RGB", (W, H), (255, 60, 0))
        sheet = Image.composite(Image.blend(dim, tint, 0.55), dim, mk.convert("L"))
        sheet.save(os.path.join(out, mesh + "_faces.png"))
        # the native data
        with open(os.path.join(out, mesh + ".amesh"), "wb") as fh:
            fh.write(b"AMSH" + struct.pack("<iiii", 1, len(bones), len(pts), len(faces)))
            for b, bn in enumerate(bones):
                fh.write(struct.pack("<32s", bn["name"].encode("latin1")[:31]))
                fh.write(struct.pack("<i3f", bn["parent"], *bn["pos"]))
                fh.write(struct.pack("<9f", *[x for row in R[b] for x in row]))
                fh.write(struct.pack("<3f", *O[b]))
            for i in range(len(pts)):
                fh.write(struct.pack("<3f", *pts[i]))
                for k in range(4):
                    fh.write(struct.pack("<if", int(infl[i][k][0]), float(infl[i][k][1])))
            for i, f in enumerate(faces):
                fh.write(struct.pack("<3H", wedges[f[0]][0], wedges[f[1]][0], wedges[f[2]][0]))
                for w in f[:3]:
                    fh.write(struct.pack("<2f", wedges[w][2], wedges[w][3]))
                fh.write(struct.pack("<BB", int(flag[i]), f[3]))
            for m in mats:
                fh.write(struct.pack("<32s", m.encode("latin1")[:31]))
        print()
    print("| mesh | pawn classes | material sections | faces | armour faces | armour surface | mask |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print("| %s | %s | %d: %s | %d | %d | %.0f%% | %s |" % (r[0], r[1], len(r[2]), ", ".join(r[2]), r[3], r[4], r[5], r[6]))
    # the script fallback table: every bone with surface, its share
    with open(os.path.join(out, "bone_shares.txt"), "w") as fh:
        for mesh, shares in shares_all.items():
            fh.write("%s %s\n" % (mesh, " ".join("%s=%.2f" % (n, s) for n, (s, c) in sorted(shares.items(), key=lambda kv: -kv[1][1]))))


if __name__ == "__main__":
    main()
