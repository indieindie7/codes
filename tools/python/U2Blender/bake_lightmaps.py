"""Bake new lightmaps for Unreal II in Blender (Cycles), from what U2Shaders' lmcapture=1 recorded.

    blender -b -P bake_lightmaps.py -- --capture <System\\U2Shaders\\capture> [options]
    (or: python bake_lightmaps.py ... with Blender's Python module, pip install bpy)

Reads capture\\scene.obj (the level's lightmapped triangles, world space, lightmap coordinates)
and capture\\lightmaps.txt (each lightmap's size and how the game multiplies it in), lights the
scene with the lights of the map's T3D (--t3d, through U2Blender's importer; other actors and
brushes are ignored, the captured triangles are the real level) and/or a test light (--point,
--sun), bakes the light reaching each surface (direct + bounced, without the surface's own
colour: a lightmap) into an image per lightmap, and writes them as DDS files with mip levels to
--out (default: capture\\..\\baked), plus replace_lines.txt with the U2Shaders.ini lines.

The game multiplies a lightmap in (x2 for most: 0.5 in the texture = unchanged), so the baked
light is divided by that factor. --match (default on when the game's own lightmap was saved
in U2Shaders\\dump) then scales each bake so its average brightness (after clipping to what a
texture can hold) equals the original's: the new one keeps the level's overall exposure, only
where light falls changes. A bake with much more contrast than the original clips its brightest
spots doing so; lower --exposure or use --no-match to see it unscaled.

Options: --samples N (64), --margin N (4 texels), --albedo X (0.6: how much light surfaces
bounce), --exposure X (1), --scale X (0.02, as the T3D importer), --no-match.
"""

import argparse
import math
import os
import struct
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import U2Blender                      # noqa: E402  (the add-on package, for import_t3d and t3d)
from U2Blender import t3d             # noqa: E402

MODULATE_FACTOR = {4: 1.0, 5: 2.0, 6: 4.0}   # D3DTOP_MODULATE, MODULATE2X, MODULATE4X


# ---- capture files -----------------------------------------------------------------------

def read_lightmaps(path):
    out = {}
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            h, w, hh, op, tris = line.split()[:5]
            out[h] = {"w": int(w), "h": int(hh), "op": int(op), "tris": int(tris)}
    return out


def read_capture(path):
    """{lightmap hash: (vertices [(x,y,z)], uvs [(u,v)], faces [(i,j,k)])} from scene.obj."""
    groups, cur = {}, None
    vs, vts = [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == "o":
                cur = groups.setdefault(p[1][3:], ([], [], []))
            elif p[0] == "v":
                vs.append(tuple(float(c) for c in p[1:4]))
            elif p[0] == "vt":
                vts.append((float(p[1]), float(p[2])))
            elif p[0] == "f" and cur is not None:
                idx = [tuple(int(x) - 1 for x in c.split("/")[:2]) for c in p[1:4]]
                base = len(cur[0])
                for vi, ti in idx:
                    cur[0].append(vs[vi])
                    cur[1].append(vts[ti])
                cur[2].append((base, base + 1, base + 2))
    return groups


# ---- DDS ---------------------------------------------------------------------------------

def write_dds(path, pixels, w, h):
    """pixels: rows top first, each [(r, g, b)] in 0..1. 32-bit BGRA with a full mip chain."""
    levels = [pixels]
    while w > 1 or h > 1:
        src = levels[-1]
        nw, nh = max(1, w // 2), max(1, h // 2)
        lvl = []
        for y in range(nh):
            row = []
            for x in range(nw):
                acc, n = [0.0, 0.0, 0.0], 0
                for dy in (0, 1):
                    for dx in (0, 1):
                        sy, sx = min(y * 2 + dy, h - 1), min(x * 2 + dx, w - 1)
                        for c in range(3):
                            acc[c] += src[sy][sx][c]
                        n += 1
                row.append(tuple(a / n for a in acc))
            lvl.append(row)
        levels.append(lvl)
        w, h = nw, nh
    w0, h0 = len(pixels[0]), len(pixels)
    header = [0] * 32
    header[0], header[1] = 0x20534444, 124
    header[2] = 0x1007 | 0x8 | 0x20000
    header[3], header[4], header[5], header[7] = h0, w0, w0 * 4, len(levels)
    header[19], header[20], header[22] = 32, 0x40, 32
    header[23], header[24], header[25] = 0xFF0000, 0xFF00, 0xFF
    header[27] = 0x1000 | 0x400000 | 0x8
    with open(path, "wb") as f:
        f.write(struct.pack("<32I", *header))
        for lvl in levels:
            buf = bytearray()
            for row in lvl:
                for r, g, b in row:
                    buf += bytes((int(min(max(b, 0), 1) * 255 + 0.5), int(min(max(g, 0), 1) * 255 + 0.5),
                                  int(min(max(r, 0), 1) * 255 + 0.5), 255))
            f.write(buf)


def dds_mean(path):
    """Average brightness (0..1) of a DDS's top level: 32-bit or DXT1/3/5 (block end colours).
    None if it can't be read."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        hd = struct.unpack("<32I", data[:128])
        if hd[0] != 0x20534444:
            return None
        h, w, flags, fourcc, bits = hd[3], hd[4], hd[20], hd[21], hd[22]
        total, n = 0.0, 0
        if flags & 0x4:
            size = 8 if fourcc == 0x31545844 else 16 if fourcc in (0x33545844, 0x35545844) else 0
            if not size:
                return None
            blocks = max(1, w // 4) * max(1, h // 4)
            for b in range(blocks):
                at = 128 + b * size + (0 if size == 8 else 8)
                c0, c1 = struct.unpack("<HH", data[at:at + 4])
                for c in (c0, c1):
                    total += ((c >> 11 & 31) / 31 * 0.3 + (c >> 5 & 63) / 63 * 0.59 + (c & 31) / 31 * 0.11)
                    n += 1
        elif bits == 32:
            for i in range(w * h):
                b, g, r = data[128 + i * 4:128 + i * 4 + 3]
                total += (r * 0.3 + g * 0.59 + b * 0.11) / 255
                n += 1
        else:
            return None
        return total / n if n else None
    except (OSError, struct.error):
        return None


def match_scale(rows, want):
    """The factor k for which the average brightness of the bake times k, clipped at 1 as the
    texture will be, equals want (bisection; a sample of the pixels for big lightmaps)."""
    step = max(1, (len(rows) * len(rows[0])) // 16384)
    px = [p for row in rows for p in row][::step]
    if not px:
        return None
    mean = lambda k: sum(min(r * k, 1) * 0.3 + min(g * k, 1) * 0.59 + min(b * k, 1) * 0.11 for r, g, b in px) / len(px)
    lo, hi = 0.0, 1.0
    while mean(hi) < want and hi < 1e6:
        hi *= 2
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mean(mid) < want else (lo, mid)
    return hi if mean(hi) > 0 else None


# ---- scene -------------------------------------------------------------------------------

def build_scene(args, lightmaps, groups):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    world = bpy.data.worlds.new("bake world")
    world.color = (0, 0, 0)
    scene.world = world

    if args.t3d:
        U2Blender.import_t3d(bpy.context, args.t3d, scale=args.scale)
        for o in list(scene.objects):
            if o.type != "LIGHT":
                o.hide_render = True
    for spec in args.point or []:
        x, y, z, energy = (float(c) for c in spec.split(","))
        o = bpy.data.objects.new("test point", bpy.data.lights.new("test point", "POINT"))
        o.data.energy = energy
        o.location = t3d.to_blender((x, y, z), args.scale)
        scene.collection.objects.link(o)
    for spec in args.sun or []:
        x, y, z, strength = (float(c) for c in spec.split(","))
        o = bpy.data.objects.new("test sun", bpy.data.lights.new("test sun", "SUN"))
        o.data.energy = strength
        d = t3d.normalize(t3d.to_blender((x, y, z), 1.0))   # the direction the light travels
        from mathutils import Vector
        o.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(o)

    targets = []
    for h, (verts, uvs, faces) in groups.items():
        info = lightmaps.get(h)
        if info is None or not faces:
            continue
        mesh = bpy.data.meshes.new("lm_" + h)
        # mirrored into Blender's space: reverse each face, as for T3D brushes
        mesh.from_pydata([t3d.to_blender(v, args.scale) for v in verts], [], [(c, b, a) for a, b, c in faces])
        uv = mesh.uv_layers.new(name="Lightmap")
        loop_uv = []
        for a, b, c in faces:
            for i in (c, b, a):
                loop_uv += [uvs[i][0], 1.0 - uvs[i][1]]   # Direct3D v runs down, Blender's up
        uv.data.foreach_set("uv", loop_uv)
        img = bpy.data.images.new("lm_" + h, info["w"], info["h"], float_buffer=True)
        mat = bpy.data.materials.new("lm_" + h)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (args.albedo, args.albedo, args.albedo, 1)
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        nodes.active = tex                              # the bake target
        mesh.materials.append(mat)
        obj = bpy.data.objects.new("lm_" + h, mesh)
        scene.collection.objects.link(obj)
        targets.append((h, obj, img, info))
    return targets


def bake(args, targets):
    bpy.ops.object.select_all(action="DESELECT")
    for _, obj, _, _ in targets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = targets[0][1]
    s = bpy.context.scene.render.bake
    s.use_pass_direct, s.use_pass_indirect, s.use_pass_color = True, True, False
    s.margin = args.margin
    bpy.ops.object.bake(type="DIFFUSE")


def write_results(args, targets, dump_dir):
    os.makedirs(args.out, exist_ok=True)
    lines = []
    for h, _, img, info in targets:
        w, hgt = info["w"], info["h"]
        px = list(img.pixels)
        factor = MODULATE_FACTOR.get(info["op"], 2.0)
        rows = []
        for y in range(hgt - 1, -1, -1):                 # Blender's rows run bottom up
            row = []
            for x in range(w):
                i = (y * w + x) * 4
                row.append(tuple(px[i + c] * args.exposure / factor for c in range(3)))
            rows.append(row)
        note = ""
        orig = os.path.join(dump_dir, "%s_%dx%d.dds" % (h, w, hgt)) if dump_dir else None
        if args.match and orig and os.path.isfile(orig):
            want = dds_mean(orig)
            k = match_scale(rows, want) if want else None
            if k:
                rows = [[tuple(c * k for c in p) for p in row] for row in rows]
                note = " (matched to the original's average %.3f, x%.3g)" % (want, k)
        path = os.path.join(args.out, h + ".dds")
        write_dds(path, rows, w, hgt)
        lines.append("replace=%s baked\\%s.dds" % (h, h))
        print("baked %s %dx%d -> %s%s" % (h, w, hgt, path, note))
    with open(os.path.join(args.out, "replace_lines.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return lines


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--capture", required=True, help="the U2Shaders\\capture folder")
    ap.add_argument("--t3d", help="the map as T3D, for its lights")
    ap.add_argument("--point", action="append", help="test point light: x,y,z,watts (game units)")
    ap.add_argument("--sun", action="append", help="test sun: direction x,y,z (game units), strength")
    ap.add_argument("--out", help="output folder (default: capture\\..\\baked)")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--margin", type=int, default=4)
    ap.add_argument("--albedo", type=float, default=0.6)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--scale", type=float, default=0.02)
    ap.add_argument("--no-match", dest="match", action="store_false")
    args = ap.parse_args(argv)
    args.out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.capture)), "baked")
    lightmaps = read_lightmaps(os.path.join(args.capture, "lightmaps.txt"))
    groups = read_capture(os.path.join(args.capture, "scene.obj"))
    targets = build_scene(args, lightmaps, groups)
    if not targets:
        print("nothing to bake (no lightmapped triangles in the capture)")
        return 1
    if not (args.t3d or args.point or args.sun):
        print("warning: no lights given (--t3d, --point or --sun): the bake will be black")
    bake(args, targets)
    dump = os.path.join(os.path.dirname(os.path.abspath(args.capture)), "dump")
    write_results(args, targets, dump if os.path.isdir(dump) else None)
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
