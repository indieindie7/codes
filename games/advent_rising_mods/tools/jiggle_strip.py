"""The Seeker without its plates (JIGGLE.md, phase A.3), headless Blender: the armour faces
(the .amesh flags) are deleted, the holes filled and triangulated, the fill's UVs taken from the
flesh ring around each hole, and a mask of the texels to regenerate (the plate UV islands,
dilated) written for the texture pass. Nothing from the game's texture pixels is read.

    blender -b --python tools/jiggle_strip.py -- <mesh.psk> <mesh.amesh> <armour mask.png> <out dir>

Writes <out>/<mesh>_stripped.blend, <mesh>_stripped.psk (same points, bones and weights; the
armour faces replaced by the fill), plate_mask.png (white = regenerate) and a workbench render
of the stripped mesh (stripped_render.png) for a look.
"""
import os
import struct
import sys

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "python", "U2Golem"))
import psk2blend  # noqa: E402


def amesh_flags(path, nfaces):
    d = open(path, "rb").read()
    tag, ver, nb, nv, nf = struct.unpack_from("<4siiii", d, 0)
    assert tag == b"AMSH" and ver == 1 and nf == nfaces, "amesh mismatch"
    o = 20 + nb * 96 + nv * 44
    out = []
    for i in range(nf):
        out.append(d[o + 30])
        o += 32
    return out


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    psk, amesh, maskpng, out = args
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, obj = psk2blend.load(psk, [], "seeker")
    me = obj.data
    flags = amesh_flags(amesh, len(me.polygons))
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    orig = bm.verts.layers.int.new("orig")
    for v in bm.verts:
        v[orig] = v.index + 1           # 0 = a vertex the fill adds
    armour = [bm.faces[i] for i, f in enumerate(flags) if f]
    # the flesh-side UV of every boundary vertex, before the plates go
    flesh_uv = {}
    for f in bm.faces:
        if flags[f.index]:
            continue
        for l in f.loops:
            flesh_uv.setdefault(l.vert.index, l[uv].uv.copy())
    n_before = len(bm.faces)
    bmesh.ops.delete(bm, geom=armour, context="FACES_ONLY")
    # loose vertices (only plates used them) go too
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    holes_before = sum(1 for e in bm.edges if e.is_boundary)
    res = bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    fill = res["faces"]
    bmesh.ops.recalc_face_normals(bm, faces=fill)
    bmesh.ops.triangulate(bm, faces=fill)
    bm.faces.ensure_lookup_table()
    fill_faces = [f for f in bm.faces if f.index >= n_before - len(armour)]
    # the fill's UVs: the flesh ring's (new vertices get theirs from the subdivision below)
    for f in fill_faces:
        f.smooth = True
        f.material_index = 0
        for l in f.loops:
            u = flesh_uv.get(l.vert[orig] - 1)
            if u is not None:
                l[uv].uv = u
    # a rounder fill: split its inner edges once and relax the new vertices
    inner = [e for e in {e for f in fill_faces for e in f.edges} if all(f in fill_faces for f in e.link_faces) and len(e.link_faces) == 2]
    if inner:
        res = bmesh.ops.subdivide_edges(bm, edges=inner, cuts=1, use_grid_fill=False)
        new_verts = [g for g in res["geom_inner"] if isinstance(g, bmesh.types.BMVert)]
        for _ in range(4):
            bmesh.ops.smooth_vert(bm, verts=new_verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        fill_faces = [f for f in bm.faces if f.index >= n_before - len(armour)]
        for f in fill_faces:
            f.smooth = True
            f.material_index = 0
        # the subdivided loops interpolate UVs; a vertex that got none takes a neighbour's
        for v in new_verts:
            for l in v.link_loops:
                if l[uv].uv.length == 0:
                    for e in v.link_edges:
                        o = e.other_vert(v)
                        for ol in o.link_loops:
                            if ol[uv].uv.length > 0:
                                l[uv].uv = ol[uv].uv.copy()
                                break
        bmesh.ops.recalc_face_normals(bm, faces=fill_faces)
        print("JIGGLE_STRIP: fill subdivided, %d new vertices relaxed" % len(new_verts))
    bm.to_mesh(me)
    bm.free()
    me.update()
    holes_after = sum(1 for e in me.edges if e.is_loose)
    print("JIGGLE_STRIP: %d faces, %d armour removed, %d loose points removed, %d boundary edges filled with %d faces" % (n_before, len(armour), len(loose), holes_before, len(fill_faces)))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, os.path.splitext(os.path.basename(psk))[0] + "_stripped.blend"))
    # the stripped psk: the original chunks with new wedges and faces (points, bones, weights as they were)
    d = open(psk, "rb").read()
    o, ch, order = 0, {}, []
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        typ, size, count = struct.unpack_from("<iii", d, o + 20)
        ch[cid] = [typ, size, count, d[o + 32:o + 32 + size * count]]
        order.append(cid)
        o += 32 + size * count
    # the vertices kept their psk indices unless loose ones were deleted (the psk needs all points: keep them)
    uvl = me.uv_layers.active.data
    wedges, faces = [], []
    for poly in me.polygons:
        tri = []
        for li in poly.loop_indices:
            v = me.loops[li].vertex_index
            u, w = uvl[li].uv
            tri.append(len(wedges))
            wedges.append(struct.pack("<HHffBBH", v, 0, u, 1.0 - w, 0, 0, 0))
        faces.append(struct.pack("<3HBBI", tri[0], tri[1], tri[2], 0, 0, 1))
    if len(me.vertices) != ch["PNTS0000"][2]:
        # points were removed: rewrite the point list and remap the weights to the kept points
        origs = [me.attributes["orig"].data[i].value - 1 for i in range(len(me.vertices))]
        newidx = {o: i for i, o in enumerate(origs) if o >= 0}
        pts = [struct.pack("<3f", *v.co) for v in me.vertices]
        raw, size, count = ch["RAWWEIGHTS"][3], ch["RAWWEIGHTS"][1], ch["RAWWEIGHTS"][2]
        ws, per_orig = [], {}
        for i in range(count):
            w, pt, b = struct.unpack_from("<fii", raw, size * i)
            per_orig.setdefault(pt, []).append((w, b))
            if pt in newidx:
                ws.append(struct.pack("<fii", w, newidx[pt], b))
        # a vertex the fill added: the weights of the nearest kept original vertex
        import mathutils
        kept = [(me.vertices[i].co.copy(), o) for i, o in enumerate(origs) if o >= 0]
        kd = mathutils.kdtree.KDTree(len(kept))
        for k, (co, o) in enumerate(kept):
            kd.insert(co, k)
        kd.balance()
        for i, o in enumerate(origs):
            if o < 0:
                _, k, _ = kd.find(me.vertices[i].co)
                for w, b in per_orig.get(kept[k][1], [(1.0, 0)]):
                    ws.append(struct.pack("<fii", w, i, b))
        print("JIGGLE_STRIP: note, %d points left of %d: %d of %d weights kept and remapped" % (len(pts), ch["PNTS0000"][2], len(ws), count))
        ch["PNTS0000"] = [ch["PNTS0000"][0], 12, len(pts), b"".join(pts)]
        ch["RAWWEIGHTS"] = [ch["RAWWEIGHTS"][0], 12, len(ws), b"".join(ws)]
    ch["VTXW0000"] = [ch["VTXW0000"][0], 16, len(wedges), b"".join(wedges)]
    ch["FACE0000"] = [ch["FACE0000"][0], 12, len(faces), b"".join(faces)]
    outpsk = os.path.join(out, os.path.splitext(os.path.basename(psk))[0] + "_stripped.psk")
    with open(outpsk, "wb") as fh:
        for cid in order:
            typ, size, count, raw = ch[cid]
            fh.write(struct.pack("<20siii", cid.encode(), typ, size, count) + raw)
    # the mask: the plate islands dilated by a few texels
    img = bpy.data.images.load(maskpng)
    W, H = img.size
    px = list(img.pixels)
    import numpy as np
    m = np.array(px, dtype=np.float32).reshape(H, W, 4)[:, :, 0] > 0.5
    dil = m.copy()
    for _ in range(6):
        dil = dil | np.roll(dil, 1, 0) | np.roll(dil, -1, 0) | np.roll(dil, 1, 1) | np.roll(dil, -1, 1)
    out_img = bpy.data.images.new("plate_mask", W, H)
    rgba = np.zeros((H, W, 4), dtype=np.float32)
    rgba[:, :, 0] = rgba[:, :, 1] = rgba[:, :, 2] = dil
    rgba[:, :, 3] = 1
    out_img.pixels = rgba.ravel().tolist()
    out_img.filepath_raw = os.path.join(out, "plate_mask.png")
    out_img.file_format = "PNG"
    out_img.save()
    print("JIGGLE_STRIP: mask %dx%d, %d texels to regenerate (%.1f%%), dilated from %d" % (W, H, int(dil.sum()), 100.0 * dil.sum() / dil.size, int(m.sum())))
    # a look: workbench render, front and side
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "SINGLE"
    sc.render.resolution_x, sc.render.resolution_y = 900, 900
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    import mathutils
    lo = mathutils.Vector([min(v.co[i] for v in me.vertices) for i in range(3)])
    hi = mathutils.Vector([max(v.co[i] for v in me.vertices) for i in range(3)])
    c = (lo + hi) / 2
    size = max(hi - lo)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size * 1.1
    cam.data.clip_end = 10000
    # the mesh is in psk axes (-Y up, +Z forward): look along -Z (front view) with -Y up
    cam.location = c + mathutils.Vector((0, 0, size * 3))
    cam.rotation_euler = (0, 0, 3.14159)      # looking along -Z, -Y up
    sc.render.filepath = os.path.join(out, "stripped_render.png")
    bpy.ops.render.render(write_still=True)
    print("JIGGLE_STRIP: wrote", outpsk)


if __name__ == "__main__":
    main()
