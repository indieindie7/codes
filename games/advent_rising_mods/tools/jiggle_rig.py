"""Jiggle bones for the Seeker infantry (JIGGLE.md): secondary flesh motion through added leaf
bones. Only flesh is weighted to them; the armour (the per-triangle flags of
<game>\\AdventMod\\Armour\\<mesh>.amesh, ARMOUR.md) keeps its ordinary bones, so the plates only
ever move with the skeleton (the user's rule). Asserted: no armour vertex carries any jiggle weight.

    py -I tools/jiggle_rig.py build <mesh.psk> <mesh.amesh> <out dir>
        writes <out>/<mesh>_jiggle.psk (the re-rigged mesh), <out>/regions.json (bones, parents,
        rest offsets, vertex lists and weights) and <out>/rig_report.md
    py -I tools/jiggle_rig.py skin <mesh.psk> <out dir>/regions.json <clips dir> <out dir>
        writes <out>/anim_<clip>.npz: the mesh skinned by the clip, every frame (the sim's goal)

Regions (mesh space: -Y up, +X the body's left, +Z forward; the Seeker walks on its front pair
of arms, the back pair holds the gun): belly and chest (front of the torso), hump (the back),
throat (neck), the four upper arms, the two thighs. A region's vertices are those with weight
on the region's parent bone inside its half-space; the jiggle weight is a smooth falloff from
the region's centre (MaxWeight at the centre, 0 at the edge) taken from the parent bone's
share, so the rest pose and every clip are unchanged until the bone itself moves.
"""
import json
import math
import os
import struct
import sys

import numpy as np

MAX_WEIGHT = 0.6
MAX_INFLUENCES = 4

# name, parent bone, half-space (axis index, sign: keep vertices with sign*(coord-centre) > 0 in
# the parent's local frame... measured in mesh space here, since the ref pose has identity
# rotations), radius scale (1 = the candidates' extent)
REGIONS = [
    ("J_Belly", "spine1", ("z", +1), 1.0),
    ("J_Chest", "spine2", ("z", +1), 1.0),
    ("J_Hump", "spine2", ("z", -1), 1.0),
    ("J_Throat", "Neck02", ("z", +1), 1.0),
    ("J_ArmR", "rightArm", None, 1.0),
    ("J_ArmL", "leftArm", None, 1.0),
    ("J_FrontArmR", "RightFrontArm", None, 1.0),
    ("J_FrontArmL", "LeftFrontArm", None, 1.0),
    ("J_ThighR", "rightUpLeg", None, 1.0),
    ("J_ThighL", "leftUpLeg", None, 1.0),
]
AXIS = {"x": 0, "y": 1, "z": 2}


# ---------------------------------------------------------------- psk / amesh

def read_chunks(path):
    d = open(path, "rb").read()
    o, ch, order = 0, {}, []
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        typ, size, count = struct.unpack_from("<iii", d, o + 20)
        ch[cid] = [typ, size, count, d[o + 32:o + 32 + size * count]]
        order.append(cid)
        o += 32 + size * count
    return ch, order


def write_chunks(path, ch, order):
    with open(path, "wb") as fh:
        for cid in order:
            typ, size, count, raw = ch[cid]
            fh.write(struct.pack("<20siii", cid.encode(), typ, size, count) + raw)


def read_psk(path):
    ch, order = read_chunks(path)
    raw, s, n = ch["PNTS0000"][3], ch["PNTS0000"][1], ch["PNTS0000"][2]
    pts = np.array([struct.unpack_from("<3f", raw, s * i) for i in range(n)], dtype=np.float64)
    raw, s, n = ch["VTXW0000"][3], ch["VTXW0000"][1], ch["VTXW0000"][2]
    wedges = [struct.unpack_from("<HHffB", raw, s * i) for i in range(n)]
    raw, s, n = ch["FACE0000"][3], ch["FACE0000"][1], ch["FACE0000"][2]
    faces = [struct.unpack_from("<HHHB", raw, s * i) for i in range(n)]
    raw, s, n = ch["REFSKELT"][3], ch["REFSKELT"][1], ch["REFSKELT"][2]
    bones = []
    for i in range(n):
        r = struct.unpack_from("<64sIii4f3ff3f", raw, s * i)
        bones.append(dict(name=r[0].split(b"\0")[0].decode("latin1"), flags=r[1], children=r[2], parent=r[3] if i else -1, quat=r[4:8], pos=r[8:11], length=r[11], size=r[12:15]))
    raw, s, n = ch["RAWWEIGHTS"][3], ch["RAWWEIGHTS"][1], ch["RAWWEIGHTS"][2]
    weights = [struct.unpack_from("<fii", raw, s * i) for i in range(n)]
    return dict(chunks=ch, order=order, points=pts, wedges=wedges, faces=faces, bones=bones, weights=weights)


def read_amesh_flags(path, nfaces):
    """the per-triangle armour flag of the .amesh (AMSH v1, tools/make_armour_data.py)"""
    d = open(path, "rb").read()
    tag, ver, nb, nv, nf = struct.unpack_from("<4siiii", d, 0)
    if tag != b"AMSH" or ver != 1:
        raise ValueError("not an AMSH v1 file: " + path)
    if nf != nfaces:
        raise ValueError("%s has %d faces, the psk %d" % (path, nf, nfaces))
    o = 20 + nb * (32 + 4 + 12 + 36 + 12) + nv * (12 + 4 * 8)
    flags = []
    for i in range(nf):
        flags.append(d[o + 6 + 24])
        o += 6 + 24 + 2
    return np.array(flags, dtype=bool)


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def pose(bones, local, conj_child=True):
    """mesh-space (R, O) per bone; local = [(quat, pos)] in ActorX form (children conjugated)"""
    R, O = [], []
    for i, b in enumerate(bones):
        q, p = local[i]
        q = np.array(q, dtype=np.float64)
        if i > 0 and conj_child:
            q = np.array([-q[0], -q[1], -q[2], q[3]])
        L = quat_mat(q)
        if i == 0:
            R.append(L)
            O.append(np.array(p, dtype=np.float64))
        else:
            par = b["parent"]
            R.append(R[par] @ L)
            O.append(O[par] + R[par] @ np.array(p, dtype=np.float64))
    return np.array(R), np.array(O)


def ref_pose(bones):
    return pose(bones, [(b["quat"], b["pos"]) for b in bones])


def skin(points, infl, Rref, Oref, R, O):
    """linear blend skinning: infl = per point list of (bone, weight)"""
    out = np.zeros_like(points)
    # per bone transform of ref-space points
    M = np.array([R[b] @ Rref[b].T for b in range(len(R))])
    T = np.array([O[b] - M[b] @ Oref[b] for b in range(len(R))])
    for i, lst in enumerate(infl):
        p = points[i]
        acc = np.zeros(3)
        for b, w in lst:
            acc += w * (M[b] @ p + T[b])
        out[i] = acc
    return out


def influences(weights, npts):
    infl = [[] for _ in range(npts)]
    for w, pt, b in weights:
        infl[pt].append((b, w))
    return infl


# ---------------------------------------------------------------- the rig

def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def build(psk_path, amesh_path, out):
    os.makedirs(out, exist_ok=True)
    m = read_psk(psk_path)
    pts, bones, faces, wedges = m["points"], m["bones"], m["faces"], m["wedges"]
    flags = read_amesh_flags(amesh_path, len(faces))
    armour_pts = set()
    for f, fl in zip(faces, flags):
        if fl:
            for w in f[:3]:
                armour_pts.add(wedges[w][0])
    infl = influences(m["weights"], len(pts))
    bone_index = {b["name"].lower(): i for i, b in enumerate(bones)}
    Rref, Oref = ref_pose(bones)
    dom = np.array([max(lst, key=lambda bw: bw[1])[0] for lst in infl])
    new_bones = []
    regions = []
    report = ["# Jiggle rig report: %s" % os.path.basename(psk_path), "",
              "%d points, %d faces, %d armour faces -> %d armour points (never jiggled)" % (len(pts), len(faces), int(flags.sum()), len(armour_pts)), "",
              "| bone | parent | candidates | weighted | armour skipped | 4-influence skipped | weight mean | weight max | centre (mesh) | radius | lever |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    weights = list(m["weights"])
    assert_hits = 0
    for name, parent, half, rscale in REGIONS:
        pb = bone_index[parent.lower()]
        cand = []
        for i, lst in enumerate(infl):
            wp = dict(lst).get(pb, 0.0)
            if wp <= 0.0:
                continue
            if dom[i] != pb and wp < 0.3:
                continue
            cand.append(i)
        cand = np.array(cand)
        centre0 = pts[cand].mean(axis=0)
        if half is not None:
            ax, sg = AXIS[half[0]], half[1]
            # the half-space through the parent bone's own origin, not the centroid: the front of
            # the torso is what sits in front of the spine
            cand = cand[sg * (pts[cand][:, ax] - Oref[pb][ax]) > 0]
        centre = pts[cand].mean(axis=0)
        radius = np.max(np.linalg.norm(pts[cand] - centre, axis=1)) * rscale
        arm_skip = full_skip = 0
        wsum, wmax, nw = 0.0, 0.0, 0
        verts = []
        for i in cand:
            if i in armour_pts:
                arm_skip += 1
                continue
            d = np.linalg.norm(pts[i] - centre) / radius
            w = MAX_WEIGHT * smoothstep(1.0 - d)
            lst = infl[i]
            wp = dict(lst).get(pb, 0.0)
            w = min(w, wp)
            if w < 0.02:
                continue
            if len(lst) >= MAX_INFLUENCES:
                # room for the new influence: drop the smallest if it is negligible
                small = min(lst, key=lambda bw: bw[1])
                if small[1] < 0.05 and small[0] != pb:
                    lst.remove(small)
                    big = max(lst, key=lambda bw: bw[1])
                    lst[lst.index(big)] = (big[0], big[1] + small[1])
                else:
                    full_skip += 1
                    continue
            # take it from the parent's share
            for k, (b, bw) in enumerate(lst):
                if b == pb:
                    lst[k] = (b, bw - w)
            lst.append((len(bones) + len(new_bones), w))
            verts.append((int(i), float(w)))
            wsum += w
            wmax = max(wmax, w)
            nw += 1
        # the bone: a leaf at its PARENT's origin (the joint), no rotation: the live route can only
        # turn a bone (the world-spacer callback returns axes, the engine keeps the origin), so the
        # flesh swings about the joint like a pendulum, with the region's centre as the lever
        local = np.zeros(3)
        lever = Rref[pb].T @ (centre - Oref[pb])
        new_bones.append(dict(name=name, parent=pb, pos=local.tolist(), centre=centre.tolist(), radius=float(radius)))
        regions.append(dict(name=name, parent=parent, parent_index=pb, index=len(bones) + len(new_bones) - 1, pos=local.tolist(), lever=lever.tolist(), centre=centre.tolist(), radius=float(radius), verts=verts))
        report.append("| %s | %s | %d | %d | %d | %d | %.3f | %.3f | %.0f %.0f %.0f | %.0f | %.0f |" % (name, parent, len(cand), nw, arm_skip, full_skip, wsum / max(nw, 1), wmax, centre[0], centre[1], centre[2], radius, np.linalg.norm(lever)))
    # the assert: no armour point carries any jiggle weight
    first_new = len(bones)
    for i in armour_pts:
        for b, w in infl[i]:
            if b >= first_new and w > 0:
                assert_hits += 1
    if assert_hits:
        raise AssertionError("%d armour points carry jiggle weight" % assert_hits)
    # rebuild the weights, renormalised
    new_weights = []
    for i, lst in enumerate(infl):
        s = sum(w for _, w in lst)
        for b, w in lst:
            if w > 1e-6:
                new_weights.append((w / s, i, b))
    # the psk: bones appended (leaf bones, so every parent stays earlier than its child)
    recs = []
    for b in bones:
        recs.append(struct.pack("<64sIii4f3ff3f", b["name"].encode("latin1"), b["flags"], b["children"], max(b["parent"], 0), *b["quat"], *b["pos"], b["length"], *b["size"]))
    kids = {}
    for nb in new_bones:
        kids[nb["parent"]] = kids.get(nb["parent"], 0) + 1
    for pb, n in kids.items():
        b = bones[pb]
        recs[pb] = struct.pack("<64sIii4f3ff3f", b["name"].encode("latin1"), b["flags"], b["children"] + n, max(b["parent"], 0), *b["quat"], *b["pos"], b["length"], *b["size"])
    for nb in new_bones:
        recs.append(struct.pack("<64sIii4f3ff3f", nb["name"].encode("latin1"), 0, 0, nb["parent"], 0.0, 0.0, 0.0, 1.0, *nb["pos"], 1.0, 1.0, 1.0, 1.0))
    ch = m["chunks"]
    ch["REFSKELT"] = [ch["REFSKELT"][0], 120, len(recs), b"".join(recs)]
    ch["RAWWEIGHTS"] = [ch["RAWWEIGHTS"][0], 12, len(new_weights), b"".join(struct.pack("<fii", w, pt, b) for w, pt, b in new_weights)]
    mesh = os.path.splitext(os.path.basename(psk_path))[0]
    out_psk = os.path.join(out, mesh + "_jiggle.psk")
    write_chunks(out_psk, ch, m["order"])
    report += ["", "Armour assert: %d armour points with jiggle weight (must be 0). Max weight %.2f, influences per point capped at %d." % (assert_hits, MAX_WEIGHT, MAX_INFLUENCES),
               "Bones: %d + %d jiggle = %d. Weights: %d -> %d records." % (len(bones), len(new_bones), len(recs), len(m["weights"]), len(new_weights)),
               "Written: %s" % out_psk]
    open(os.path.join(out, "rig_report.md"), "w").write("\n".join(report) + "\n")
    json.dump(dict(mesh=mesh, psk=out_psk, bones=[b["name"] for b in bones] + [nb["name"] for nb in new_bones], armour_points=sorted(armour_pts), regions=regions),
              open(os.path.join(out, "regions.json"), "w"))
    print("\n".join(report))


def skin_clips(psk_path, regions_path, clips_dir, out):
    """the ORIGINAL mesh skinned by each clip (one key per frame): the goal the soft body follows"""
    m = read_psk(psk_path)
    bones = m["bones"]
    infl = influences(m["weights"], len(m["points"]))
    Rref, Oref = ref_pose(bones)
    reg = json.load(open(regions_path))
    import glob
    for fn in sorted(glob.glob(os.path.join(clips_dir, "*.json"))):
        c = json.load(open(fn))
        if [n.lower() for n in c["bones"]] != [b["name"].lower() for b in bones]:
            print("skip", fn, "(other skeleton)")
            continue
        frames = []
        bone_R, bone_O = [], []
        for row in c["frames"]:
            local = [(r[0:4], r[4:7]) for r in row]
            R, O = pose(bones, local)
            frames.append(skin(m["points"], infl, Rref, Oref, R, O))
            bone_R.append(R)
            bone_O.append(O)
        frames = np.array(frames)
        np.savez_compressed(os.path.join(out, "anim_%s.npz" % c["name"]), verts=frames.astype(np.float32), bone_R=np.array(bone_R, dtype=np.float32), bone_O=np.array(bone_O, dtype=np.float32), rate=c["rate"])
        lo, hi = frames.min(axis=(0, 1)), frames.max(axis=(0, 1))
        print("%s: %d frames, mesh extent y %.0f..%.0f (floor at 0, up is -y), x %.0f..%.0f z %.0f..%.0f" % (c["name"], len(frames), lo[1], hi[1], lo[0], hi[0], lo[2], hi[2]))


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "skin":
        skin_clips(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
