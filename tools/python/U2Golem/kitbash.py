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
"Bip01 L UpperArm"). Per swap also: "girth" (thickness factor), "mode": "overlay" (keep the base's
own triangles there, donor armour goes on top), "keep_top": 0..1 (only the donor's top part of the
region, e.g. 0.6 of a head = a hat), "keep_hue": [min, max] degrees (only faces whose texture
is that colour, e.g. [70, 170] = a green beret), "offset": [x, y, z] (nudge, base units),
"exact": true (only points skinned to those very bones; by default points of child bones that
still lie along a region bone are included, e.g. a forearm skinned to the hand - but in a biped
the clavicles hang off the neck, so a neck swap needs "stop": ["L Clavicle", "R Clavicle"]
(child chains not to follow) or "exact"), "fit_cap": {sit, back, overhang,
tilt} (sit a hat on the skull already in the mesh), "faces": "all"|"most"|"any" (how many corners of
a donor triangle must be in the region; "most" overlaps the seam), "extend": e (stretch the piece
toward its parent joint by e x bone length: a shin guard reaching the knee), "bridge": f (keep
the base's own mesh over the first f of each region bone: joint geometry under the armour).
Recipe-level "palette_from": [textures] (+ "palette_skip": {texture: [[x0,y0,x1,y1] in 0..1]})
and per swap "dye": [material slots] repaint those donor textures into the base's palette
(dye.py), so all parts share one colour language. The result is compacted (loose points dropped) and its open-edge count printed.

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


def main_child(bones, i, kids):
    """the child that continues a bone's chain: a spine/neck child for the pelvis and spine,
    else the first non-finger child (so rigs that list children in another order agree)"""
    ks = kids.get(i, [])
    if not ks:
        return None
    names = [short(bones[k]["name"]) for k in ks]
    for want in ("spine", "neck", "head"):
        for k, n in zip(ks, names):
            if n.startswith(want):
                return k
    for k, n in zip(ks, names):
        if "finger" not in n and "toe" not in n and "nub" not in n:
            return k
    return ks[0]


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
            x = W[main_child(bones, i, kids)][:3, 3] - o
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
    kids = {}
    for j, b in enumerate(bones):
        if np.linalg.norm(b["pos"]) > 1e-3:
            kids.setdefault(b["parent"], []).append(j)
    k = main_child(bones, i, kids)
    return np.linalg.norm(W[k][:3, 3] - W[i][:3, 3]) if k is not None else None


def region_points(m, W, region, exact=False, stop=(), margin=0.0):
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
        while r >= 0 and keys[r] not in region and keys[r] not in stop:
            r = bones[r]["parent"]
        if r < 0 or keys[r] in stop:
            continue
        if r != b and exact:
            continue
        ks = [k for k in kids.get(r, []) if np.linalg.norm(bones[k]["pos"]) > 1e-3]
        if not ks:
            if r == b:
                out.add(p)
            continue
        o = W[r][:3, 3]
        end = W[main_child(bones, r, {r: ks})][:3, 3]
        axis = end - o
        t = np.dot(m["pts"][p] - o, axis) / np.dot(axis, axis)
        # margin: leave the first part of the bone (the joint it hangs from) alone, so the
        # base's own joint geometry stays as a bridge under the donor armour
        if margin > 0 and t < margin:
            continue
        if r == b or t <= 0.97:
            out.add(p)
    return out


def fit_cap(opt, pts, weights, bshort, used, pmap, live):
    """sit a hat on the skull already in the mesh: the hat's footprint is centred over the top
    of the head (shifted "back" units toward the back of the head), scaled to the skull's width
    plus "overhang", its rim "sit" units below the crown, then tilted "tilt" degrees to the
    hat's own right (a beret's slouch). Head = points whose strongest bone is the head."""
    head = bshort["head"]
    strong = {}
    for w, p, b in weights:
        if p not in strong or w > strong[p][0]:
            strong[p] = (w, b)
    new = {pmap[p] for p in used}
    H = np.array([pts[p] for p, (w, b) in strong.items() if b == head and p not in new and p in live])
    hat = np.array([pts[pmap[p]] for p in used])
    ztop = H[:, 2].max()
    sit = opt.get("sit", 6.0)
    band = H[H[:, 2] > ztop - sit]
    c = band[:, :2].mean(0) + np.array([0.0, opt.get("back", 0.0)])
    span = band[:, :2].max(0) - band[:, :2].min(0)
    hc = (hat[:, :2].max(0) + hat[:, :2].min(0)) / 2
    hspan = hat[:, :2].max(0) - hat[:, :2].min(0)
    s = (span * (1.0 + opt.get("overhang", 0.15))) / hspan
    sz = s.mean()
    out = np.empty_like(hat)
    out[:, :2] = (hat[:, :2] - hc) * s + c
    out[:, 2] = (hat[:, 2] - hat[:, 2].min()) * sz + (ztop - sit)
    a = np.radians(opt.get("tilt", 0.0))            # roll about the front-back (Y) axis
    piv = np.array([c[0], c[1], ztop - sit])
    R = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])
    out = (out - piv) @ R.T + piv
    for p, q in zip(used, out):
        pts[pmap[p]] = tuple(q)
    print(f"  hat fit: crown z {ztop:.1f}, skull {span.round(1)}, hat scale {s.round(2)}")


def open_edges(pts, wedges, faces):
    """edges used by only one triangle, on points welded by position (holes and cut seams)"""
    from collections import Counter
    key = {}
    weld = [key.setdefault(tuple(np.round(p, 2)), i) for i, p in enumerate(pts)]
    c = Counter()
    for a, b, cc, m in faces:
        P = [weld[wedges[w][0]] for w in (a, b, cc)]
        for i in range(3):
            c[frozenset((P[i], P[(i + 1) % 3]))] += 1
    return sum(1 for e, n in c.items() if n == 1 and len(e) == 2)


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
    pal = None
    if "palette_from" in R:
        # one palette for the whole suit (dye.py): sampled from the base's armour textures
        import dye
        pal = dye.palette_from([path(p) for p in R["palette_from"]],
                               {path(k): v for k, v in R.get("palette_skip", {}).items()})
        print("palette:", {k: tuple(round(x, 2) for x in v) for k, v in pal.items() if v})
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
            ext = sw.get("extend", 0.0)
            if ext and lb and dshort[i] in region:
                # stretch toward the parent joint: x' = lb + (x - lb) * (1 + ext), so the
                # piece's far end stays put and its near end reaches ext * length further up
                S[0, 0] *= 1.0 + ext
                S[0, 3] = -ext * lb
            M.append(bF[tgt[i]] @ S @ np.linalg.inv(dF[i]))

        # base triangles in the region go ("overlay" keeps them: donor armour on top)
        if sw.get("mode", "replace") == "replace":
            breg = region_points(base, bW, region, sw.get("exact", False), {short(s) for s in sw.get("stop", [])}, sw.get("bridge", 0.0))
            for fi, (a, b, c, m) in enumerate(faces):
                if fi < len(base["faces"]) and all(base["wedges"][w][0] in breg for w in (a, b, c)):
                    removed.add(fi)

        # donor triangles in the region come in
        dreg = region_points(d, dW, region, sw.get("exact", False), {short(s) for s in sw.get("stop", [])})
        if "keep_bottom" in sw:
            # only the bottom of the region: points up to this fraction from the region's
            # lowest joint to its highest point (e.g. a donor's upper neck under the jaw)
            P = np.array([d["pts"][p] for p in dreg])
            j0 = min(dW[i][2, 3] for i, k in enumerate(dshort) if k in region)
            ztop = P[:, 2].max()
            dreg = {p for p in dreg if (d["pts"][p][2] - j0) <= sw["keep_bottom"] * (ztop - j0)}
        if "keep_top" in sw:
            # only the top of the region (a hat): points at least this far from the region's
            # lowest joint to its highest point, measured straight up
            P = np.array([d["pts"][p] for p in dreg])
            j0 = min(dW[i][2, 3] for i, k in enumerate(dshort) if k in region)
            ztop = P[:, 2].max()
            dreg = {p for p in dreg if (d["pts"][p][2] - j0) >= sw["keep_top"] * (ztop - j0)}
        # a donor triangle comes in when enough of its corners are in the region: "most" (2 of
        # 3, default) or "any" lets pieces reach across the joint and overlap the neighbour, so
        # seams hide under the armour instead of opening into holes; "all" = strict
        need = {"all": 3, "most": 2, "any": 1}[sw.get("faces", "most")]
        keep = [f for f in d["faces"] if sum(d["wedges"][w][0] in dreg for w in (f[0], f[1], f[2])) >= need]
        if "materials" in sw:
            keep = [f for f in keep if f[3] in sw["materials"]]     # only these donor slots
        if "keep_hue" in sw:
            # only faces whose texture is in a hue range (degrees), e.g. a green beret [70, 170]
            from PIL import Image
            import colorsys
            lo, hi = sw["keep_hue"]
            imgs = {}
            def hue_ok(f):
                tex = sw.get("textures", [])
                if f[3] >= len(tex):
                    return False
                if f[3] not in imgs:
                    imgs[f[3]] = Image.open(path(tex[f[3]])).convert("RGB")
                im = imgs[f[3]]
                u = sum(d["wedges"][w][2] for w in f[:3]) / 3 % 1.0
                v = sum(d["wedges"][w][3] for w in f[:3]) / 3 % 1.0
                r, g, b = [c / 255 for c in im.getpixel((min(int(u * im.width), im.width - 1), min(int(v * im.height), im.height - 1)))]
                h, s, val = colorsys.rgb_to_hsv(r, g, b)
                return lo <= h * 360 <= hi and s > 0.2
            keep = [f for f in keep if hue_ok(f)]
        used = sorted({d["wedges"][w][0] for f in keep for w in f[:3]})
        dweights = {}
        for w, p, b in d["weights"]:
            dweights.setdefault(p, []).append((w, b))
        pmap = {}
        for p in used:
            v = np.append(d["pts"][p], 1.0)
            moved = sum(w * (M[b] @ v) for w, b in dweights.get(p, [(1.0, 0)]))
            moved[:3] += np.array(sw.get("offset", [0, 0, 0]))
            pmap[p] = len(pts)
            pts.append(tuple(moved[:3]))
            merged = {}
            for w, b in dweights.get(p, [(1.0, 0)]):
                merged[tgt[b]] = merged.get(tgt[b], 0.0) + w
            for b, w in merged.items():
                weights.append((w, pmap[p], b))
        if "fit_cap" in sw:
            live = {wedges[w][0] for fi, f in enumerate(faces) if fi not in removed for w in f[:3]}
            fit_cap(sw["fit_cap"], pts, weights, bshort, used, pmap, live)
        mat0 = len(mats)
        dmats_used = sorted({f[3] for f in keep})
        mslot = {}
        for dm in dmats_used:
            mslot[dm] = len(mats)
            mats.append(f"{os.path.splitext(os.path.basename(sw['donor']))[0]}_{d['mats'][dm] or dm}")
            tex = sw.get("textures", [])
            tpath = path(tex[dm]) if dm < len(tex) and tex[dm] else ""
            if tpath and pal and dm in sw.get("dye", []):
                import dye
                dyed = os.path.join(os.path.dirname(path(R["out"])), "dyed",
                                    os.path.splitext(os.path.basename(tpath))[0] + "_dyed.tga")
                os.makedirs(os.path.dirname(dyed), exist_ok=True)
                tpath = dye.dye(tpath, pal, dyed, sw.get("dye_strength", 1.0))
            textures.append(tpath)
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

    # compact: drop points (and their weights) no remaining face uses, and unused wedges
    used_w = sorted({w for f in faces for w in f[:3]})
    wnew = {w: i for i, w in enumerate(used_w)}
    used_p = sorted({wedges[w][0] for w in used_w})
    pnew = {p: i for i, p in enumerate(used_p)}
    loose = len(pts) - len(used_p)
    pts = [pts[p] for p in used_p]
    wedges = [(pnew[wedges[w][0]],) + tuple(wedges[w][1:]) for w in used_w]
    faces = [(wnew[a], wnew[b], wnew[c], m) for a, b, c, m in faces]
    weights = [(w, pnew[p], b) for w, p, b in weights if p in pnew]
    print(f"compacted: {loose} loose points removed; open edges {open_edges(pts, wedges, faces)}")
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
