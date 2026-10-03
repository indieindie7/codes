"""Cut a skinned character (.psk) into gib parts: one static mesh (.ase) per body part, each cut
closed with a flat "meat" cap, plus a manifest (part, source bone, size, mass guess).

Usage:  py -3.13 gibsplit.py <mesh.psk> <out dir> [--space mesh|zup] [--meat NAME]

How a part is chosen: every point goes to its strongest bone; from that bone we walk up the
skeleton to the first bone that starts a part (RULES, by name). Triangles go to the part most of
their corners belong to. Edges that a part shares with another part are the cut: each closed
loop of them gets a fan of triangles on the meat material, facing out.

Output space: "zup" (default) turns a Y-down mesh into Z up, (x, y, z) -> (x, z, -y), a plain
rotation; "mesh" keeps the .psk's own axes. Every part is centred on its own centre (its pivot),
and the manifest gives that pivot in the original mesh space, so a gib can spawn where it was.
UVs are the character's own (the skin texture still fits); caps get a planar UV on the meat slot.
"""
import json, math, os, re, struct, sys
from collections import Counter, defaultdict

# first match wins, so the more specific names come first
RULES = [
    (r"head$", "head"),
    (r"(left|right).*forearm", "{side}_lowerarm"),
    (r"(left|right)front(elbow|wrist)", "{side}_front_lower"),
    (r"(left|right)front(arm|shoulder)", "{side}_front_upper"),
    (r"(left|right)arm$", "{side}_upperarm"),
    (r"(left|right)upleg|(left|right)thigh", "{side}_upperleg"),
    (r"(left|right)(leg|calf)$", "{side}_lowerleg"),
    (r"spine2|spine3|neck|shoulder|clavicle|chest", "torso_upper"),
]
TORSO = "torso_lower"                      # anything else: hips, spine, props
UNIT_M = 1.8 / 220.0                       # metres per unit: Advent's marine is 220 tall
DENSITY = 2800.0                           # kg per cubic metre, calibrated so Advent's marine totals ~90 kg


# ---- .psk ----------------------------------------------------------------------------------
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
    wedges = []
    for i in range(n):
        p, _, u, v, m = struct.unpack_from("<HHffB", b, s * i)
        wedges.append((p if len(pts) <= 65536 else struct.unpack_from("<I", b, s * i)[0], u, v, m))
    b, s, n = get("FACE0000")
    faces = [struct.unpack_from("<HHHB", b, s * i) for i in range(n)]
    b, s, n = get("MATT0000")
    mats = [b[s * i:s * i + 64].split(b"\0")[0].decode("latin1") for i in range(n)]
    b, s, n = get("REFSKELT")
    bones = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        parent = struct.unpack_from("<i", b, s * i + 72)[0]
        bones.append((name, parent if i else -1))
    b, s, n = get("RAWWEIGHTS")
    weights = [struct.unpack_from("<fii", b, s * i) for i in range(n)]
    return pts, wedges, faces, mats, bones, weights


# ---- parts ---------------------------------------------------------------------------------
def bone_parts(bones):
    out = []
    for i in range(len(bones)):
        j, part = i, None
        while j >= 0 and part is None:
            name = bones[j][0].lower()
            for pat, label in RULES:
                m = re.search(pat, name)
                if m:
                    side = "l" if "left" in name else "r"
                    part = label.format(side=side)
                    break
            j = bones[j][1]
        out.append(part or TORSO)
    return out


def part_root_bone(bones, parts, part):
    """the highest bone of a part (the one a gib should spawn at)"""
    for i, (name, parent) in enumerate(bones):
        if parts[i] == part and (parent < 0 or parts[parent] != part):
            return name
    return bones[0][0]


# ---- geometry helpers ----------------------------------------------------------------------
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def norm(a):
    l = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


def loops(edges):
    """chain directed boundary edges (a, b) into closed loops of points"""
    nxt = defaultdict(list)
    for a, b in edges:
        nxt[a].append(b)
    used, out = set(), []
    for a, b in edges:
        if (a, b) in used:
            continue
        loop, cur, start = [a], b, a
        used.add((a, b))
        guard = 0
        while cur != start and guard < 10000:
            loop.append(cur)
            cands = [c for c in nxt[cur] if (cur, c) not in used]
            if not cands:
                break
            used.add((cur, cands[0]))
            cur = cands[0]
            guard += 1
        if len(loop) >= 3:                    # closed, or an open chain (still worth a lid)
            out.append(loop)
    return out


# ---- .ase ----------------------------------------------------------------------------------
def write_ase(path, name, verts, faces, tverts, tfaces, mats):
    L = ["*3DSMAX_ASCIIEXPORT\t200", '*COMMENT "gibsplit.py"', "*MATERIAL_LIST {", "\t*MATERIAL_COUNT 1",
         "\t*MATERIAL 0 {", f'\t\t*MATERIAL_NAME "{name}_mat"', '\t\t*MATERIAL_CLASS "Multi/Sub-Object"',
         f"\t\t*NUMSUBMTLS {len(mats)}"]
    for i, m in enumerate(mats):
        L += [f"\t\t*SUBMATERIAL {i} {{", f'\t\t\t*MATERIAL_NAME "{m}"', '\t\t\t*MATERIAL_CLASS "Standard"',
              "\t\t\t*MAP_DIFFUSE {", f'\t\t\t\t*MAP_NAME "{m}"', f'\t\t\t\t*BITMAP "{m}.bmp"', "\t\t\t}", "\t\t}"]
    L += ["\t}", "}", "*GEOMOBJECT {", f'\t*NODE_NAME "{name}"', "\t*MESH {", "\t\t*TIMEVALUE 0",
          f"\t\t*MESH_NUMVERTEX {len(verts)}", f"\t\t*MESH_NUMFACES {len(faces)}", "\t\t*MESH_VERTEX_LIST {"]
    L += [f"\t\t\t*MESH_VERTEX {i}\t{p[0]:.5f}\t{p[1]:.5f}\t{p[2]:.5f}" for i, p in enumerate(verts)]
    L += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
    L += [f"\t\t\t*MESH_FACE {i}: A: {a} B: {b} C: {c} AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID {m}"
          for i, (a, b, c, m) in enumerate(faces)]
    L += ["\t\t}", f"\t\t*MESH_NUMTVERTEX {len(tverts)}", "\t\t*MESH_TVERTLIST {"]
    L += [f"\t\t\t*MESH_TVERT {i}\t{u:.6f}\t{v:.6f}\t0.0000" for i, (u, v) in enumerate(tverts)]
    L += ["\t\t}", f"\t\t*MESH_NUMTVFACES {len(tfaces)}", "\t\t*MESH_TFACELIST {"]
    L += [f"\t\t\t*MESH_TFACE {i}\t{a}\t{b}\t{c}" for i, (a, b, c) in enumerate(tfaces)]
    L += ["\t\t}", "\t}", "\t*MATERIAL_REF 0", "}", ""]
    open(path, "w").write("\n".join(L))


# ---- the split -----------------------------------------------------------------------------
def split(psk, outdir, space="zup", meat="meat"):
    pts, wedges, faces, mats, bones, weights = read_psk(psk)
    mesh = os.path.splitext(os.path.basename(psk))[0]
    os.makedirs(outdir, exist_ok=True)
    bparts = bone_parts(bones)

    best = {}
    for w, p, b in weights:
        if p not in best or w > best[p][0]:
            best[p] = (w, b)
    ppart = [bparts[best[p][1]] if p in best else TORSO for p in range(len(pts))]

    # topology on welded points: .psk files repeat a point along UV/normal seams
    canon = {}
    weld = [canon.setdefault((round(q[0], 2), round(q[1], 2), round(q[2], 2)), i) for i, q in enumerate(pts)]

    fpart = []
    for a, b, c, m in faces:
        votes = Counter(ppart[wedges[w][0]] for w in (a, b, c))
        fpart.append(votes.most_common(1)[0][0])

    # edges of the whole mesh: a cut edge is shared by faces of two different parts
    edge_parts = defaultdict(set)
    for (a, b, c, m), part in zip(faces, fpart):
        P = [weld[wedges[w][0]] for w in (a, b, c)]
        for i in range(3):
            edge_parts[frozenset((P[i], P[(i + 1) % 3]))].add(part)

    conv = (lambda q: (q[0], q[2], -q[1])) if space == "zup" else (lambda q: q)
    meat_id = len(mats)
    manifest = []
    for part in sorted(set(fpart)):
        F = [f for f, p in zip(faces, fpart) if p == part]
        used = sorted({wedges[w][0] for f in F for w in f[:3]} | {weld[wedges[w][0]] for f in F for w in f[:3]})
        centre = tuple(sum(pts[p][k] for p in used) / len(used) for k in range(3))
        vidx = {p: i for i, p in enumerate(used)}
        verts = [conv(sub(pts[p], centre)) for p in used]
        tverts, tfaces, out_faces = [], [], []
        for a, b, c, m in F:
            t0 = len(tverts)
            for w in (a, b, c):
                tverts.append((wedges[w][1], 1.0 - wedges[w][2]))
            out_faces.append((vidx[wedges[a][0]], vidx[wedges[b][0]], vidx[wedges[c][0]], m))
            tfaces.append((t0, t0 + 1, t0 + 2))

        # caps: directed edges of this part that are cut edges and used once in the part
        directed = Counter()
        for a, b, c, m in F:
            P = [weld[wedges[w][0]] for w in (a, b, c)]
            for i in range(3):
                directed[(P[i], P[(i + 1) % 3])] += 1
        cut = [(a, b) for (a, b), n in directed.items()
               if (b, a) not in directed and len(edge_parts[frozenset((a, b))]) > 1]
        caps = 0
        for loop in loops([(b, a) for a, b in cut]):          # reversed: the cap faces out
            ring = [pts[p] for p in loop]
            c = tuple(sum(q[k] for q in ring) / len(ring) for k in range(3))
            n = (0.0, 0.0, 0.0)
            for i in range(len(ring)):
                n = tuple(n[k] + cross(sub(ring[i], c), sub(ring[(i + 1) % len(ring)], c))[k] for k in range(3))
            n = norm(n)
            u = norm(cross(n, (0, 0, 1) if abs(n[2]) < 0.9 else (1, 0, 0)))
            v = cross(n, u)
            ci = len(verts)
            verts.append(conv(sub(c, centre)))
            for i in range(len(loop)):
                a, b = loop[i], loop[(i + 1) % len(loop)]
                t0 = len(tverts)
                for q in (c, pts[a], pts[b]):
                    d = sub(q, c)
                    tverts.append((0.5 + dot(d, u) / 40.0, 0.5 + dot(d, v) / 40.0))
                out_faces.append((ci, vidx[a], vidx[b], meat_id))
                tfaces.append((t0, t0 + 1, t0 + 2))
            caps += 1

        # size and a mass guess from the closed volume (signed tetrahedra)
        vol = 0.0
        for a, b, c, m in out_faces:
            vol += dot(verts[a], cross(verts[b], verts[c])) / 6.0
        lo = [min(p[k] for p in verts) for k in range(3)]
        hi = [max(p[k] for p in verts) for k in range(3)]
        mass = abs(vol) * UNIT_M ** 3 * DENSITY
        name = f"{mesh}_{part}"
        write_ase(os.path.join(outdir, name + ".ase"), name, verts, out_faces, tverts, tfaces, mats + [meat])
        manifest.append(dict(part=part, file=name + ".ase", bone=part_root_bone(bones, bparts, part),
                             pivot_mesh=[round(x, 3) for x in centre], size=[round(h - l, 2) for l, h in zip(lo, hi)],
                             faces=len(out_faces), caps=caps, mass_kg=round(mass, 2)))
    json.dump(dict(mesh=mesh, space=space, materials=mats + [meat], parts=manifest),
              open(os.path.join(outdir, mesh + "_gibs.json"), "w"), indent=1)
    return manifest


if __name__ == "__main__":
    args = sys.argv[1:]
    space = args[args.index("--space") + 1] if "--space" in args else "zup"
    meat = args[args.index("--meat") + 1] if "--meat" in args else "meat"
    for p in split(args[0], args[1], space, meat):
        print(f"{p['part']:18s} bone {p['bone']:18s} faces {p['faces']:5d} caps {p['caps']} size {p['size']} mass {p['mass_kg']} kg")
