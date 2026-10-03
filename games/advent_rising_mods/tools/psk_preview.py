"""Quick look at a .psk without a 3D tool: front and side views, flat-shaded, each
triangle coloured by the bone that moves most of it (so you can see where gib cuts
would fall). Writes a .bmp next to the .psk.

    python psk_preview.py <mesh.psk> [size]
"""
import math, struct, sys
from collections import defaultdict


def read_psk(path):
    d = open(path, "rb").read()
    q = 0
    out = {}
    while q < len(d):
        cid, _, size, count = struct.unpack_from("<20sIii", d, q)
        q += 32
        out[cid.rstrip(b"\0").decode()] = (d[q:q + size * count], size, count)
        q += size * count
    pts = [struct.unpack_from("<3f", out["PNTS0000"][0], 12 * i) for i in range(out["PNTS0000"][2])]
    wed = [struct.unpack_from("<HHff", out["VTXW0000"][0], 16 * i)[0] for i in range(out["VTXW0000"][2])]
    faces = [struct.unpack_from("<3H", out["FACE0000"][0], 12 * i) for i in range(out["FACE0000"][2])]
    bones = [struct.unpack_from("<64s", out["REFSKELT"][0], 120 * i)[0].split(b"\0")[0].decode() for i in range(out["REFSKELT"][2])]
    best = {}
    for i in range(out["RAWWEIGHTS"][2]):
        w, pt, b = struct.unpack_from("<fii", out["RAWWEIGHTS"][0], 12 * i)
        if w > best.get(pt, (0, 0))[0]:
            best[pt] = (w, b)
    return pts, wed, faces, bones, {k: v[1] for k, v in best.items()}


def colour(b):
    h = (b * 0.61803) % 1.0
    k = lambda n: max(0.0, min(1.0, abs((h * 6 + n) % 6 - 3) - 1))
    return (k(5), k(3), k(1))


def render(pts, wed, faces, bone_of, W, H, view):
    img = [[(40, 40, 46)] * W for _ in range(H)]
    zb = [[-1e9] * W for _ in range(H)]
    # the mesh's Y is down (feet near 0, head near -220): screen up = -Y
    proj = (lambda p: (p[0], -p[1], p[2])) if view == "front" else (lambda p: (p[2], -p[1], -p[0]))
    P = [proj(p) for p in pts]
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    s = 0.9 * min(W / (max(xs) - min(xs) + 1e-6), H / (max(ys) - min(ys) + 1e-6))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    S = [(W / 2 + (p[0] - cx) * s, H / 2 - (p[1] - cy) * s, p[2]) for p in P]
    light = (0.4, 0.6, 0.7)
    for f in faces:
        a, b, c = (wed[i] for i in f)
        pa, pb, pc = P[a], P[b], P[c]
        u = [pb[i] - pa[i] for i in range(3)]
        v = [pc[i] - pa[i] for i in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(sum(x * x for x in n)) or 1
        shade = 0.35 + 0.65 * abs(sum(n[i] * light[i] for i in range(3)) / ln)
        col = colour(bone_of.get(a, 0))
        rgb = tuple(int(255 * shade * k) for k in col)
        A, B, C = S[a], S[b], S[c]
        x0, x1 = max(0, int(min(A[0], B[0], C[0]))), min(W - 1, int(max(A[0], B[0], C[0])) + 1)
        y0, y1 = max(0, int(min(A[1], B[1], C[1]))), min(H - 1, int(max(A[1], B[1], C[1])) + 1)
        den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
        if abs(den) < 1e-9:
            continue
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                l1 = ((B[1] - C[1]) * (x - C[0]) + (C[0] - B[0]) * (y - C[1])) / den
                l2 = ((C[1] - A[1]) * (x - C[0]) + (A[0] - C[0]) * (y - C[1])) / den
                l3 = 1 - l1 - l2
                if l1 < 0 or l2 < 0 or l3 < 0:
                    continue
                z = l1 * A[2] + l2 * B[2] + l3 * C[2]
                if z > zb[y][x]:
                    zb[y][x] = z
                    img[y][x] = rgb
    return img


def main():
    path = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    pts, wed, faces, bones, bone_of = read_psk(path)
    views = [render(pts, wed, faces, bone_of, size, size, v) for v in ("front", "side")]
    W, H = size * 2, size
    rows = [views[0][y] + views[1][y] for y in range(H)]
    rs = (W * 3 + 3) & ~3
    with open(path[:-4] + ".bmp", "wb") as fh:
        fh.write(b"BM" + struct.pack("<IHHI", 54 + rs * H, 0, 0, 54) + struct.pack("<IiiHHIIiiII", 40, W, H, 1, 24, 0, rs * H, 2835, 2835, 0, 0))
        for y in range(H - 1, -1, -1):
            fh.write(b"".join(bytes((c[2], c[1], c[0])) for c in rows[y]) + b"\0" * (rs - W * 3))
    print(path[:-4] + ".bmp", len(faces), "faces,", len(set(bone_of.values())), "bones used")


if __name__ == "__main__":
    main()
