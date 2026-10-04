"""Kitbash a skinned character: swap body regions of a base mesh for the same regions of donor
characters (UT2004 / UC2 players share the Character Studio biped: Bip01 X == Merc X).

Usage:  py -3.13 kitbash.py <recipe.json>

Recipe:
{
 "base": "PlayerGame.psk", "base_textures": ["Limbs.tga", "Torso.tga", "Visor.tga"],
 "out": "DaltonMk2.psk",
 "swaps": [ {"donor": "JuggMaleB.psk", "textures": ["JuggMaleBBodyA.tga", "JuggMaleBHeadB.tga"],
             "bones": ["L Clavicle", "L UpperArm"], "scale": 1.05}, ... ]
}
Bone names are given without the rig prefix ("L UpperArm" matches "Merc L UpperArm" and
"Bip01 L UpperArm").

For each swap: the base's triangles whose corners all belong to those bones (strongest weight)
are removed; the donor's triangles whose corners all belong to them are added, carried from the
donor's rest pose into the base's by linear blend of per-bone rest matrices
(base_bone_world * scale * donor_bone_world^-1), keeping the donor's own weights (renamed to the
base rig's bones) and its UVs, on new material slots with the donor's textures.
Writes <out>.psk plus <out>.json (material slots -> texture files) for u2import.py.
"""
import json, os, re, struct, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
    pts = np.array([struct.unpack_from("<3f", b, s * i) for i in range(n)])
    b, s, n = get("VTXW0000")
    wedges = [struct.unpack_from("<HHffB", b, s * i) for i in range(n)]
    b, s, n = get("FACE0000")
    faces = [struct.unpack_from("<HHHB", b, s * i) for i in range(n)]
    b, s, n = get("MATT0000")
    mats = [b[s * i:s * i + 64].split(b"\0")[0].decode("latin1") for i in range(n)]
    b, s, n = get("REFSKELT")
    bones = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        parent = struct.unpack_from("<i", b, s * i + 72)[0]
        q = struct.unpack_from("<4f", b, s * i + 76)
        pos = struct.unpack_from("<3f", b, s * i + 92)
        bones.append(dict(name=name, parent=parent if i else -1, q=q, pos=pos, raw=b[s * i:s * i + s]))
    b, s, n = get("RAWWEIGHTS")
    weights = [struct.unpack_from("<fii", b, s * i) for i in range(n)]
    return dict(pts=pts, wedges=wedges, faces=faces, mats=mats, bones=bones, weights=weights)


def quat_matrix(x, y, z, w):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def world_matrices(bones):
    W = []
    for i, b in enumerate(bones):
        x, y, z, w = b["q"]
        if b["parent"] >= 0:
            x, y, z = -x, -y, -z                    # ActorX child rotations are inverted
        M = np.eye(4)
        M[:3, :3] = quat_matrix(x, y, z, w)
        M[:3, 3] = b["pos"]
        W.append(M if b["parent"] < 0 else W[b["parent"]] @ M)
    return W


def short(name):
    """rig-independent bone key: 'Bip01 L UpperArm' / 'merc l upperarm' -> 'l upperarm'"""
    return re.sub(r"^(bip01|merc)\s*", "", name.strip().lower()).strip()


def strongest(m):
    best = {}
    for w, p, b in m["weights"]:
        if p not in best or w > best[p][0]:
            best[p] = (w, b)
    return {p: b for p, (w, b) in best.items()}


def aligned_frames(m, W):
    """a frame per bone that both rigs agree on, whatever their local axes (Golem bones run
    along local Z, Character Studio/ActorX along X): origin at the joint, X toward the next
    joint (or on from the parent for end bones), twist from world forward (Y; world up for
    bones pointing forward). Both characters face the same way in their rest poses."""
    bones = m["bones"]
    kids = {}
    for j, b in enumerate(bones):
        if np.linalg.norm(b["pos"]) > 1e-3:
            kids.setdefault(b["parent"], []).append(j)
    F = []
    for i, b in enumerate(bones):
        o = W[i][:3, 3]
        if i in kids:
            x = W[kids[i][0]][:3, 3] - o
        elif b["parent"] >= 0:
            x = o - W[b["parent"]][:3, 3]
        else:
            x = np.array([0.0, 0.0, 1.0])
        if np.linalg.norm(x) < 1e-6:
            x = np.array([0.0, 0.0, 1.0])
        x = x / np.linalg.norm(x)
        ref = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
        z = np.cross(x, ref); z /= np.linalg.norm(z)
        y = np.cross(z, x)
        M = np.eye(4)
        M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, o
        F.append(M)
    return F


def bone_length(m, W, i):
    bones = m["bones"]
    ks = [j for j, b in enumerate(bones) if b["parent"] == i and np.linalg.norm(b["pos"]) > 1e-3]
    return np.linalg.norm(W[ks[0]][:3, 3] - W[i][:3, 3]) if ks else None


def region_points(m, W, region):
    """points belonging to a set of bones: their strongest bone is one of them, or it hangs
    below one of them but the point still lies before that bone's next joint (UT2004 skins most
    of the forearm to the hand, the lower shin to the foot)"""
    bones = m["bones"]
    keys = [short(b["name"]) for b in bones]
    strong = strongest(m)
    kids = {}
    for j, b in enumerate(bones):
        kids.setdefault(b["parent"], []).append(j)
    out = set()
    for p, b in strong.items():
        r = b
        while r >= 0 and keys[r] not in region:
            r = bones[r]["parent"]
        if r < 0:
            continue
        if r == b:
            out.add(p)
            continue
        ks = [k for k in kids.get(r, []) if np.linalg.norm(bones[k]["pos"]) > 1e-3]
        if not ks:
            continue
        o = W[r][:3, 3]
        end = W[ks[0]][:3, 3]
        axis = end - o
        t = np.dot(m["pts"][p] - o, axis) / np.dot(axis, axis)
        if t <= 0.97:
            out.add(p)
    return out


def height(m):
    names = {short(b["name"]): i for i, b in enumerate(m["bones"])}
    W = world_matrices(m["bones"])
    top = W[names["head"]][:3, 3]
    foot = (W[names["l foot"]][:3, 3] + W[names["r foot"]][:3, 3]) / 2
    return np.linalg.norm(top - foot)


def kitbash(recipe_path):
    R = json.load(open(recipe_path))
    here = os.path.dirname(os.path.abspath(recipe_path))
    path = lambda p: p if os.path.isabs(p) else os.path.join(here, p)
    base = read_psk(path(R["base"]))
    bnames = [b["name"] for b in base["bones"]]
    bshort = {short(n): i for i, n in enumerate(bnames)}
    bW = world_matrices(base["bones"])
    bstrong = strongest(base)
    textures = list(R.get("base_textures", []))
    mats = list(base["mats"])

    pts = list(map(tuple, base["pts"]))
    wedges = list(base["wedges"])
    faces = list(base["faces"])
    weights = list(base["weights"])
    removed = set()

    for sw in R["swaps"]:
        region = {short(b) for b in sw["bones"]}
        d = read_psk(path(sw["donor"]))
        dW = world_matrices(d["bones"])
        dstrong = strongest(d)
        dshort = [short(b["name"]) for b in d["bones"]]
        scale = height(base) / height(d)
        girth = scale * sw.get("girth", sw.get("scale", 1.0))

        # donor bone -> base bone (same name, else its nearest named parent)
        def target(i):
            while i >= 0:
                if dshort[i] in bshort:
                    return bshort[dshort[i]]
                i = d["bones"][i]["parent"]
            return 0
        tgt = [target(i) for i in range(len(d["bones"]))]
        # per bone: in the shared bone frames, stretched along the bone to the base bone's
        # length and scaled across it by girth
        bF, dF = aligned_frames(base, bW), aligned_frames(d, dW)
        M = []
        for i in range(len(d["bones"])):
            ld, lb = bone_length(d, dW, i), bone_length(base, bW, tgt[i])
            along = lb / ld if ld and lb and dshort[i] == short(bnames[tgt[i]]) else girth
            S = np.diag([along, girth, girth, 1.0])
            M.append(bF[tgt[i]] @ S @ np.linalg.inv(dF[i]))

        # base triangles in the region go ("overlay" keeps them: donor armour on top)
        if sw.get("mode", "replace") == "replace":
            breg = region_points(base, bW, region)
            for fi, (a, b, c, m) in enumerate(faces):
                if fi < len(base["faces"]) and all(base["wedges"][w][0] in breg for w in (a, b, c)):
                    removed.add(fi)

        # donor triangles in the region come in
        dreg = region_points(d, dW, region)
        keep = [f for f in d["faces"] if all(d["wedges"][w][0] in dreg for w in (f[0], f[1], f[2]))]
        used = sorted({d["wedges"][w][0] for f in keep for w in f[:3]})
        dweights = {}
        for w, p, b in d["weights"]:
            dweights.setdefault(p, []).append((w, b))
        pmap = {}
        for p in used:
            v = np.append(d["pts"][p], 1.0)
            moved = sum(w * (M[b] @ v) for w, b in dweights.get(p, [(1.0, 0)]))
            pmap[p] = len(pts)
            pts.append(tuple(moved[:3]))
            merged = {}
            for w, b in dweights.get(p, [(1.0, 0)]):
                merged[tgt[b]] = merged.get(tgt[b], 0.0) + w
            for b, w in merged.items():
                weights.append((w, pmap[p], b))
        mat0 = len(mats)
        dmats_used = sorted({f[3] for f in keep})
        mslot = {}
        for dm in dmats_used:
            mslot[dm] = len(mats)
            mats.append(f"{os.path.splitext(os.path.basename(sw['donor']))[0]}_{d['mats'][dm] or dm}")
            tex = sw.get("textures", [])
            textures.append(path(tex[dm]) if dm < len(tex) else "")
        wmap = {}
        for a, b, c, m in keep:
            new = []
            for w in (a, b, c):
                if w not in wmap:
                    p, _, u, v, _m = d["wedges"][w]
                    wmap[w] = len(wedges)
                    wedges.append((pmap[p], 0, u, v, mslot[m]))
                new.append(wmap[w])
            faces.append((new[0], new[1], new[2], mslot[m]))
        print(f"{os.path.basename(sw['donor'])}: {sorted(region)} -> {len(keep)} faces in, size {scale:.3f}, girth {girth:.3f}")

    faces = [f for i, f in enumerate(faces) if i not in removed]
    print(f"base faces removed: {len(removed)}; result {len(pts)} points, {len(faces)} faces, {len(mats)} materials")

    def chunk(cid, size, recs):
        return struct.pack("<20siii", cid.encode(), 1999801, size, len(recs)) + b"".join(recs)
    out = [struct.pack("<20siii", b"ACTRHEAD", 1999801, 0, 0)]
    out.append(chunk("PNTS0000", 12, [struct.pack("<3f", *p) for p in pts]))
    out.append(chunk("VTXW0000", 16, [struct.pack("<HHffBBH", p, 0, u, v, m, 0, 0) for p, _, u, v, m in wedges]))
    out.append(chunk("FACE0000", 12, [struct.pack("<HHHBBI", a, b, c, m, 0, 1) for a, b, c, m in faces]))
    out.append(chunk("MATT0000", 88, [struct.pack("<64siiiiii", n.encode()[:63], i, 0, 0, 0, 0, 0) for i, n in enumerate(mats)]))
    out.append(chunk("REFSKELT", 120, [b["raw"] for b in base["bones"]]))
    out.append(chunk("RAWWEIGHTS", 12, [struct.pack("<fii", w, p, b) for w, p, b in weights]))
    dst = path(R["out"])
    open(dst, "wb").write(b"".join(out))
    json.dump(dict(materials=mats, textures=textures), open(os.path.splitext(dst)[0] + ".json", "w"), indent=1)
    print("wrote", dst)


if __name__ == "__main__":
    kitbash(sys.argv[1])
