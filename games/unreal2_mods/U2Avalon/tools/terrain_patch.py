r"""A finer terrain patch over part of the island (Avalon Q92, 2026-10-09: "could terrains become like quads of smaller
chunks ... a localized more detailed geometry?").

    py tools/terrain_patch.py <run folder with isl_ec.bmp> <out prefix> [cx=4000] [cy=-10000] [n=128] [cell=128]
                              [amp=70] [seed=3] [lift=4] [edge=12]

UE2 terrain is one even grid per TerrainInfo (TutA's island: 128 x 128 points, 512 UU apart), but a map can hold
several TerrainInfos. This writes a second, finer one (n x n points, `cell` UU apart: 128 x 128 at 128 UU = 16 km^2 /
16 = a ~330 m square, 4x the island's detail) that follows the island's ground and adds rock-and-gully detail where
the ground is steep (ridged value noise, `amp` UU at most, faded out over the `edge` outer points).

No holes: the patch is never below the island's own surface. Its heights are max(island surface + detail, island
surface + lift), where the island surface is taken as the higher of the two triangulations of each 512 UU quad (the
engine's diagonal is not known), so the coarse terrain stays under it everywhere and can't poke through.

Writes <prefix>.bmp (G16, the TerrainMap to import, MIPS=0) and <prefix>.json (Location, TerrainScale, the area) for
the editor step (terrain_patch_apply in remake_build-style: copy the island TerrainInfo's T3D, change TerrainMap,
Location, TerrainScale, import as a second TerrainInfo), and <prefix>_preview.png (shaded relief, island vs patch).
"""
import json, math, os, struct, sys
import numpy as np

LOC = (-14487.546875, 4835.837891, -131.845703)      # TutA's island TerrainInfo
SCALE = (512.0, 512.0, 128.0)

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
RUN, OUT = args[0], args[1]
CX, CY = float(o.get("cx", 4000)), float(o.get("cy", -10000))
N, CELL = int(o.get("n", 128)), float(o.get("cell", 128))
AMP, SEED, LIFT, EDGE = float(o.get("amp", 70)), int(o.get("seed", 3)), float(o.get("lift", 4)), int(o.get("edge", 12))

raw = open(os.path.join(RUN, "isl_ec.bmp"), "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * SCALE[2] / 256         # island Z per point [j, i]


def island_surface(x, y):
    """the island's rendered surface at (x, y), the higher of the quad's two triangulations"""
    fi, fj = (x - LOC[0]) / SCALE[0] + w / 2, (y - LOC[1]) / SCALE[1] + abs(h) / 2
    i0 = np.clip(np.floor(fi).astype(int), 0, w - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, abs(h) - 2)
    u, v = np.clip(fi - i0, 0, 1), np.clip(fj - j0, 0, 1)
    a, b, c, d = Z[j0, i0], Z[j0, i0 + 1], Z[j0 + 1, i0], Z[j0 + 1, i0 + 1]
    # diagonal a-d: triangles (a,b,d) for u>=v, (a,c,d) for u<v
    t1 = np.where(u >= v, a + (b - a) * u + (d - b) * v, a + (c - a) * v + (d - c) * u)
    # diagonal b-c: triangles (a,b,c) for u+v<=1, (b,c,d) beyond
    t2 = np.where(u + v <= 1, a + (b - a) * u + (c - a) * v, d + (c - d) * (1 - u) + (b - d) * (1 - v))
    return np.maximum(t1, t2)


def value_noise(x, y, scale, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((64, 64))
    fx, fy = x / scale, y / scale
    i0, j0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    u, v = fx - i0, fy - j0
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    G = lambda i, j: g[j % 64, i % 64]
    return (G(i0, j0) * (1 - u) * (1 - v) + G(i0 + 1, j0) * u * (1 - v) + G(i0, j0 + 1) * (1 - u) * v
            + G(i0 + 1, j0 + 1) * u * v)


# the patch's points in world space (same mapping as the island: point i -> Location.X + (i - N/2) * cell)
PLOC = (CX, CY, LOC[2])
ii, jj = np.meshgrid(np.arange(N), np.arange(N))
X = PLOC[0] + (ii - N / 2) * CELL
Y = PLOC[1] + (jj - N / 2) * CELL
base = island_surface(X, Y)

# steepness of the island there (per metre of run), from the coarse grid
gy, gx = np.gradient(base, CELL)
slope = np.hypot(gx, gy)
steep = np.clip((slope - 0.15) / 0.5, 0, 1)                    # flat ground (roads, pads) stays as it is

# ridged multi-octave noise: rock ribs and gullies, bigger on steep ground
ridge = np.zeros_like(X)
for k, (sc, wt) in enumerate(((1400, 0.55), (600, 0.3), (260, 0.15))):
    nz = value_noise(X, Y, sc, SEED + k)
    ridge += wt * (1 - np.abs(2 * nz - 1))                        # ridged: 1 at the crests
gully = value_noise(X + 913, Y - 377, 900, SEED + 9)
detail = AMP * steep * (ridge - 0.5 + 0.6 * (gully - 0.5))

# mask=1: no detail under or near a building (every copy of every placed building, footprint + 4 m, eased over 4 m):
# rock ribs must not come up through floors, and the floors keep the island's own graded pads
if o.get("mask") == "1":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import binder, shells  # noqa
    L = json.load(open(os.path.join(RUN, "isl_layout.json")))
    _, sheets = binder.load()
    keep = np.ones_like(X)
    for bid, b in L["buildings"].items():
        if bid not in sheets:
            continue
        W, D = (sheets[bid].get("size") or [8, 8])[:2]
        r = max(W, D) * 25 + 200
        for p in shells.instances(bid, b, sheets[bid]):
            d = np.hypot(X - p["x"], Y - p["y"])
            keep = np.minimum(keep, np.clip((d - r) / 200, 0, 1))
    detail = detail * keep
    print("  mask: %.0f %% of the patch kept flat (buildings)" % (100 * (keep < 1).mean()))

# fade to nothing at the edge so the patch meets the island with only the lift
d_edge = np.minimum(np.minimum(ii, N - 1 - ii), np.minimum(jj, N - 1 - jj)).astype(float)
fade = np.clip(d_edge / max(EDGE, 1), 0, 1)
fade = fade * fade * (3 - 2 * fade)
PZ = np.maximum(base + detail * fade, base + LIFT)

# back to G16 heights with the island's Z scale; Location.Z the island's
hv = np.clip(np.round(32768 + (PZ - PLOC[2]) * 256 / SCALE[2]), 0, 65535).astype("<u2")
rows = hv[::-1]                                                 # BMP rows bottom-up (positive height)
head = bytearray(b"BM" + struct.pack("<IHHI", 54 + N * N * 2, 0, 0, 54))
head += struct.pack("<IiiHHIIiiII", 40, N, N, 1, 16, 0, N * N * 2, 2835, 2835, 0, 0)
with open(OUT + ".bmp", "wb") as f:
    f.write(head + rows.tobytes())
info = {"Location": [PLOC[0], PLOC[1], PLOC[2]], "TerrainScale": [CELL, CELL, SCALE[2]], "n": N,
        "area_uu": [float(X.min()), float(Y.min()), float(X.max()), float(Y.max())],
        "lift": LIFT, "amp": AMP, "detail_range_uu": [float((PZ - base).min()), float((PZ - base).max())],
        "steep_share": float((steep > 0.5).mean())}
json.dump(info, open(OUT + ".json", "w"), indent=1)
print(json.dumps(info))

try:
    from PIL import Image
    def shade(z, cell):
        gy_, gx_ = np.gradient(z, cell)
        l = np.clip(0.55 + (-gx_ * 0.7 - gy_ * 0.7) * 0.35, 0, 1)
        return (l[::-1] * 255).astype(np.uint8)
    a = Image.fromarray(shade(base, CELL)).resize((384, 384))
    b = Image.fromarray(shade(PZ, CELL)).resize((384, 384))
    im = Image.new("L", (776, 384), 255)
    im.paste(a, (0, 0)); im.paste(b, (392, 0))
    im.save(OUT + "_preview.png")
except ImportError:
    pass


# ---- editor step: apply=<source map> out=<new map> (needs UnrealEd; the GPU protocol applies) -------------------
def apply(source, out):
    """copy <source> to <out>, import <prefix>.bmp as MyLevel.terrain_maps.<name>, paste a copy of the island's
    TerrainInfo pointing at it (Location / TerrainScale of the patch; the island's first layer only, its alpha map
    dropped and its UV scale x island/patch so the texture keeps its world size), save"""
    import re, shutil
    sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
    from uedlib import session, t3d_set  # noqa
    maps = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\Maps"
    shutil.copyfile(os.path.join(maps, source + ".un2"), os.path.join(maps, out + ".un2"))
    name = os.path.basename(OUT)
    k = SCALE[0] / CELL

    def job(ed):
        ed.exec("!answer yes")
        ed.load(out)
        ed.import_texture(os.path.abspath(OUT + ".bmp"), name, "MyLevel", "terrain_maps", MIPS=0)
        isl = [a for a in ed.actors("TerrainInfo") if "island" in a["props"].get("TerrainMap", "")]
        if not isl:
            sys.exit("no island TerrainInfo in " + out)
        blk = isl[0]["text"]
        print("  island TerrainInfo:\n" + "\n".join("    " + l for l in blk.splitlines() if "Layers" in l or "Terrain" in l)[:1500])
        blk = re.sub(r"Name=\w+", "Name=TerrainPatch_" + name, blk, count=1)
        blk = t3d_set(blk, "TerrainMap", "Texture'MyLevel.terrain_maps.%s'" % name)
        blk = t3d_set(blk, "Location", "(X=%f,Y=%f,Z=%f)" % tuple(info["Location"]))
        blk = t3d_set(blk, "TerrainScale", "(X=%f,Y=%f,Z=%f)" % tuple(info["TerrainScale"]))
        lines = []
        for l in blk.splitlines():
            m = re.match(r"\s*Layers\((\d+)\)=(.*)", l)
            if m and m.group(1) != "0":
                continue
            if m:
                l = re.sub(r"AlphaMap=[^,)]+,?", "", l)
                l = re.sub(r"(UScale|VScale)=([-\d.]+)", lambda q: "%s=%f" % (q.group(1), float(q.group(2)) * k), l)
            lines.append(l)
        path = os.path.abspath(OUT + "_terrain.t3d")
        open(path, "w").write("Begin Map\n" + "\n".join(lines) + "\nEnd Map\n")
        ed.deselect()
        ed.import_t3d(path, add=True)
        ed.light(selected=True)
        ed.deselect()
        ed.save(out)
        print("  %s: patch %s added (%s)" % (out, name, path))
    session(job)


if o.get("apply"):
    apply(o["apply"], o.get("out", o["apply"] + "_Patch"))
