"""U2Blender: Unreal II (Unreal Engine 2) T3D maps in Blender, in and out.

File > Import > Unreal T3D map: brushes become meshes (one object per brush, in its own
collection by CSG type), lights become Blender lights, static meshes become empties (or the
real mesh, when its OBJ is found in the mesh folder), every other actor an empty. Each object
keeps its original T3D text, so File > Export > Unreal T3D map writes back everything it does
not edit unchanged (see t3d.py). Texture alignment is kept per face (ue_* face attributes).
"""

bl_info = {
    "name": "U2Blender: Unreal T3D maps",
    "author": "indieindie7",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "File > Import/Export > Unreal T3D map (.t3d)",
    "description": "Edit Unreal Engine 2 (Unreal II) maps in Blender through UnrealEd's T3D text format",
    "category": "Import-Export",
}

import colorsys
import os

if "bpy" in locals():
    import importlib
    importlib.reload(t3d)
else:
    from . import t3d

import bpy
from bpy.props import FloatProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Matrix, Vector

# collections by kind, and how brushes are coloured (UnrealEd's own colours; set the viewport's
# Solid shading to Object colour to see them)
COLLECTIONS = ("UE Brushes Add", "UE Brushes Subtract", "UE Brushes Other", "UE Static Meshes", "UE Lights", "UE Actors")
CSG_COLOUR = {"CSG_Add": (0.3, 0.45, 1.0, 1.0), "CSG_Subtract": (1.0, 0.75, 0.2, 1.0)}


def _collection(scene, name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    return coll


def _ue_matrix(location, rotator, scale3, scale):
    """matrix_world for an actor: Unreal location/rotation/scale to Blender."""
    r = t3d.rotation_to_blender(t3d.rotator_matrix(*rotator))
    m = Matrix([r[0] + [0], r[1] + [0], r[2] + [0], [0, 0, 0, 1]])
    m = m @ Matrix.Diagonal(Vector((scale3[0], scale3[1], scale3[2], 1)))
    m.translation = Vector(t3d.to_blender(location, scale))
    return m


def _material(texture):
    name = texture or "None"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat["ue_texture"] = texture
        # a stable, distinct colour per texture so walls can be told apart
        h = (hash(name) % 1000) / 1000.0
        mat.diffuse_color = colorsys.hsv_to_rgb(h, 0.35, 0.8) + (1.0,)
    return mat


def _brush_object(actor, order, scale, tex_size):
    polys = actor.world_polys()
    loc = t3d.to_blender(actor.location, scale)
    verts, index, faces = [], {}, []
    for p in polys:
        face = []
        for v in reversed(p.verts):          # mirroring reverses the winding: undo it
            b = t3d.sub(t3d.to_blender(v, scale), loc)
            key = tuple(round(c, 4) for c in b)
            if key not in index:
                index[key] = len(verts)
                verts.append(b)
            face.append(index[key])
        faces.append(face)
    mesh = bpy.data.meshes.new(actor.name)
    mesh.from_pydata(verts, [], faces)

    # per-face texture alignment, in the object's own (Blender) space. All layers are made first:
    # adding one moves the others, so no attribute is held across an add.
    for name, kind in (("ue_origin", "FLOAT_VECTOR"), ("ue_texu", "FLOAT_VECTOR"), ("ue_texv", "FLOAT_VECTOR"),
                       ("ue_pan", "FLOAT2"), ("ue_flags", "INT")):
        mesh.attributes.new(name, kind, "FACE")
    mesh.uv_layers.new(name="UVMap")
    flat = lambda rows: [c for r in rows for c in r]
    mesh.attributes["ue_origin"].data.foreach_set("vector", flat(t3d.sub(t3d.to_blender(p.origin, scale), loc) for p in polys))
    mesh.attributes["ue_texu"].data.foreach_set("vector", flat(t3d.gradient_to_blender(p.texture_u, scale) for p in polys))
    mesh.attributes["ue_texv"].data.foreach_set("vector", flat(t3d.gradient_to_blender(p.texture_v, scale) for p in polys))
    mesh.attributes["ue_pan"].data.foreach_set("vector", flat(p.pan for p in polys))
    mesh.attributes["ue_flags"].data.foreach_set("value", [p.flags for p in polys])
    for p in polys:
        mat = _material(p.texture)
        if mat.name not in mesh.materials:
            mesh.materials.append(mat)
    names = [m.name for m in mesh.materials]
    mesh.polygons.foreach_set("material_index", [names.index(_material(p.texture).name) for p in polys])
    # UVs for the viewport only (Unreal's alignment is the attributes above); the texture size
    # is a guess, as the textures themselves are not in the T3D
    uvs = []
    for fi, p in enumerate(polys):
        for li in mesh.polygons[fi].loop_indices:
            w = t3d.from_blender(t3d.add(tuple(mesh.vertices[mesh.loops[li].vertex_index].co), loc), scale)
            d = t3d.sub(w, p.origin)
            uvs += [(t3d.dot(d, p.texture_u) + p.pan[0]) / tex_size, -(t3d.dot(d, p.texture_v) + p.pan[1]) / tex_size]
    mesh.uv_layers["UVMap"].data.foreach_set("uv", uvs)
    mesh.update()
    obj = bpy.data.objects.new(actor.name, mesh)
    obj.location = loc
    csg = actor.props.get("CsgOper", "")
    if csg in CSG_COLOUR:
        obj.color = CSG_COLOUR[csg]
    return obj, csg


def _static_mesh_data(ref, mesh_dir):
    """The mesh of StaticMesh'Pkg.Group.Name' from <mesh_dir>/<Name>.obj or <Pkg.Group.Name>.obj."""
    if not mesh_dir or not ref:
        return None
    inner = ref.split("'")[1] if "'" in ref else ref
    for fname in (inner + ".obj", inner.split(".")[-1] + ".obj"):
        path = os.path.join(bpy.path.abspath(mesh_dir), fname)
        cached = bpy.data.meshes.get("UE " + inner)
        if cached is not None:
            return cached
        if os.path.isfile(path):
            before = set(bpy.data.objects)
            bpy.ops.wm.obj_import(filepath=path, forward_axis="X", up_axis="Z")
            new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
            if not new:
                return None
            data = new[0].data
            data.name = "UE " + inner
            for o in [o for o in bpy.data.objects if o not in before]:
                bpy.data.objects.remove(o)
            return data
    return None


def import_t3d(context, path, scale=0.02, tex_size=256, mesh_dir=""):
    """Import a T3D map into the current scene. Returns (objects made, warnings)."""
    umap = t3d.read(path)
    scene = context.scene
    scene["ue_scale"] = scale
    scene["ue_head"] = "\n".join(umap.head)
    scene["ue_tail"] = "\n".join(umap.tail)
    colls = {name: _collection(scene, name) for name in COLLECTIONS}
    made, warnings = 0, []
    for order, actor in enumerate(umap.actors):
        props = actor.props
        if actor.polys is not None:
            obj, csg = _brush_object(actor, order, scale, tex_size)
            coll = colls["UE Brushes Add" if csg == "CSG_Add" else "UE Brushes Subtract" if csg == "CSG_Subtract" else "UE Brushes Other"]
            if actor.sheered():
                warnings.append("%s: sheared brush, the sheer was ignored" % actor.name)
        elif "light" in actor.cls.lower() and actor.cls != "LevelInfo":
            light = bpy.data.lights.new(actor.name, "POINT")
            bright = float(props.get("LightBrightness", 64))
            hue = float(props.get("LightHue", 0)) / 255.0
            sat = float(props.get("LightSaturation", 255)) / 255.0
            light.color = colorsys.hsv_to_rgb(hue, 1.0 - sat, 1.0)   # Unreal: saturation 255 = white
            radius = float(props.get("LightRadius", 64))
            light.energy = bright * 20.0 * (radius / 64.0) ** 2       # rough: brightness and reach
            light["ue_note"] = "energy is an estimate from LightBrightness/LightRadius"
            obj = bpy.data.objects.new(actor.name, light)
            obj.matrix_world = _ue_matrix(actor.location, actor.rotation, (1, 1, 1), scale)
            coll = colls["UE Lights"]
        else:
            ds = float(props.get("DrawScale", 1) or 1)
            ds3 = t3d.parse_vector(props.get("DrawScale3D"), (1.0, 1.0, 1.0))
            scale3 = (ds * ds3[0], ds * ds3[1], ds * ds3[2])
            data = _static_mesh_data(props.get("StaticMesh"), mesh_dir) if actor.cls == "StaticMeshActor" else None
            obj = bpy.data.objects.new(actor.name, data)
            if data is None:
                obj.empty_display_type = "CUBE" if actor.cls == "StaticMeshActor" else "ARROWS"
                obj.empty_display_size = 32 * scale
            obj.matrix_world = _ue_matrix(actor.location, actor.rotation, scale3, scale)
            coll = colls["UE Static Meshes" if actor.cls == "StaticMeshActor" else "UE Actors"]
        obj["ue_class"] = actor.cls
        obj["ue_name"] = actor.name
        obj["ue_order"] = order
        obj["ue_t3d"] = "\n".join(actor.lines)
        if "CsgOper" in props:
            obj["ue_csg"] = props["CsgOper"]
        coll.objects.link(obj)
        made += 1
    context.view_layer.update()
    return made, warnings


# ---- export -------------------------------------------------------------------------------

def _actor_values(obj, scale):
    """(location, rotator, scale3) of an object, in Unreal terms."""
    m = obj.matrix_world
    r = m.to_3x3()
    cols = [r.col[i] for i in range(3)]
    scale3 = tuple(c.length for c in cols)
    rot = [[cols[c][rr] / (scale3[c] or 1) for c in range(3)] for rr in range(3)]
    return (t3d.from_blender(tuple(m.translation), scale),
            t3d.matrix_rotator(t3d.rotation_from_blender(rot)), scale3)


def _default_alignment(normal_ue):
    """Texture axes for a face with none (a new face): planar, along its main axis, 1 texel per unit."""
    ax = max(range(3), key=lambda i: abs(normal_ue[i]))
    if ax == 2:
        return (1.0, 0.0, 0.0), (0.0, -1.0, 0.0)
    if ax == 0:
        return (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)
    return (1.0, 0.0, 0.0), (0.0, 0.0, -1.0)


def _brush_polys(obj, scale, location_ue):
    """The object's faces as T3D polygons, relative to location_ue (Unreal coordinates)."""
    mesh = obj.data
    mw = obj.matrix_world
    g = mw.to_3x3().inverted_safe().transposed()     # gradients transform by the inverse transpose
    attr = lambda name: mesh.attributes.get(name)
    polys = []
    for f in mesh.polygons:
        p = t3d.Poly()
        world = [t3d.from_blender(tuple(mw @ mesh.vertices[i].co), scale) for i in f.vertices]
        p.verts = [t3d.sub(v, location_ue) for v in reversed(world)]   # mirroring: reverse back
        p.normal = p.computed_normal()
        tu = attr("ue_texu") and Vector(attr("ue_texu").data[f.index].vector)
        tv = attr("ue_texv") and Vector(attr("ue_texv").data[f.index].vector)
        if tu is not None and tu.length > 0 and tv.length > 0:
            p.origin = t3d.sub(t3d.from_blender(tuple(mw @ Vector(attr("ue_origin").data[f.index].vector)), scale), location_ue)
            p.texture_u = t3d.gradient_from_blender(tuple(g @ tu), scale)
            p.texture_v = t3d.gradient_from_blender(tuple(g @ tv), scale)
            pan = attr("ue_pan").data[f.index].vector
            p.pan = (int(round(pan[0])), int(round(pan[1])))
        else:
            p.origin = (0.0, 0.0, 0.0)
            p.texture_u, p.texture_v = _default_alignment(p.normal)
            p.origin = t3d.sub(p.origin, location_ue)
        mat = obj.material_slots[f.material_index].material if f.material_index < len(obj.material_slots) else None
        texture = mat.get("ue_texture", mat.name) if mat else ""
        if texture:                          # no texture in, none out (UnrealEd picks its default)
            p.header["Texture"] = texture
        flags = attr("ue_flags")
        if flags and flags.data[f.index].value:
            p.header["Flags"] = str(flags.data[f.index].value)
        p.verts = [tuple(t3d.clean(c) for c in v) for v in p.verts]
        p.origin = tuple(t3d.clean(c) for c in p.origin)
        p.texture_u = tuple(t3d.clean(c, 6) for c in p.texture_u)
        p.texture_v = tuple(t3d.clean(c, 6) for c in p.texture_v)
        polys.append(p)
    return polys


def _close(a, b, eps):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


def _new_name(base, used):
    i = 0
    while "%s%d" % (base, i) in used:
        i += 1
    used.add("%s%d" % (base, i))
    return "%s%d" % (base, i)


def export_t3d(context, path):
    """Write the scene's Unreal objects back to a T3D map. Actors keep their own text; only
    what changed is rewritten (brush polygons always). Returns the number of actors written."""
    scene = context.scene
    scale = scene.get("ue_scale", 0.02)
    used = {o.get("ue_name") for o in scene.objects if o.get("ue_name")}
    models = {o.get("ue_name") for o in scene.objects}
    entries = []
    for obj in scene.objects:
        colls = {c.name for c in obj.users_collection}
        if "ue_t3d" in obj:
            actor = t3d.parse("\n".join(["Begin Map", obj["ue_t3d"], "End Map"])).actors[0]
            order = obj.get("ue_order", 1 << 30)
        elif obj.type == "MESH" and colls & {"UE Brushes Add", "UE Brushes Subtract"}:
            name = _new_name("Brush", used)
            model = _new_name("Model", models)
            csg = "CSG_Add" if "UE Brushes Add" in colls else "CSG_Subtract"
            actor = t3d.parse("\n".join(["Begin Map", "Begin Actor Class=Brush Name=" + name,
                                         "    Begin Brush Name=" + model, "       Begin PolyList", "       End PolyList",
                                         "    End Brush", "    Brush=Model'myLevel.%s'" % model, "    CsgOper=" + csg,
                                         '    Name="%s"' % name, "End Actor", "End Map"])).actors[0]
            order = 1 << 30
        elif obj.type == "LIGHT":
            name = _new_name("Light", used)
            actor = t3d.parse("\n".join(["Begin Map", "Begin Actor Class=Light Name=" + name,
                                         '    Name="%s"' % name, "End Actor", "End Map"])).actors[0]
            order = 1 << 30
        else:
            continue
        entries.append((order, obj.name, obj, actor))
    entries.sort(key=lambda e: (e[0], e[1]))

    blocks = []
    for _, _, obj, actor in entries:
        loc, rot, scale3 = _actor_values(obj, scale)
        props = {}
        if actor.polys is not None and obj.type == "MESH":
            # brushes: unchanged ones go back word for word; edited ones as world-space polygons
            # around the object's origin, with no rotation, scale or pivot left on them
            loc = tuple(t3d.clean(c) for c in loc)
            polys = _brush_polys(obj, scale, loc)
            moved = [t3d.Poly() for _ in polys]
            for m, p in zip(moved, polys):
                m.header, m.pan = p.header, p.pan
                m.verts = [t3d.add(v, loc) for v in p.verts]
                m.origin, m.texture_u, m.texture_v = t3d.add(p.origin, loc), p.texture_u, p.texture_v
            if actor.lines and t3d.same_polys(moved, actor.world_polys()):
                blocks.append(actor.lines)
                continue
            props["Location"] = t3d.fmt_vector(loc)
            blocks.append(actor.to_text(props, polys,
                                        drop=("Rotation", "PrePivot", "MainScale", "PostScale", "TempScale")))
            continue
        if not _close(loc, actor.location, 0.01):
            props["Location"] = t3d.fmt_vector(loc)
        if rot != actor.rotation and not _close(t3d.rotator_matrix(*rot)[0] + t3d.rotator_matrix(*rot)[1],
                                               t3d.rotator_matrix(*actor.rotation)[0] + t3d.rotator_matrix(*actor.rotation)[1], 1e-4):
            props["Rotation"] = t3d.fmt_rotator(rot)
        if obj.type != "LIGHT":
            ds = float(actor.props.get("DrawScale", 1) or 1)
            ds3 = t3d.parse_vector(actor.props.get("DrawScale3D"), (1.0, 1.0, 1.0))
            if not _close(scale3, (ds * ds3[0], ds * ds3[1], ds * ds3[2]), 1e-4):
                props["DrawScale3D"] = t3d.fmt_vector(tuple(c / ds for c in scale3))
        blocks.append(actor.to_text(props))

    umap = t3d.Map()
    umap.head = scene.get("ue_head", "Begin Map").split("\n")
    umap.tail = scene.get("ue_tail", "End Map").split("\n")
    with open(path, "w", newline="") as f:
        f.write(umap.to_text(blocks))
    return len(blocks)


class EXPORT_OT_ue_t3d(bpy.types.Operator, ExportHelper):
    """Export the scene's Unreal actors as a T3D map, for UnrealEd's MAP IMPORT"""
    bl_idname = "export_scene.ue_t3d"
    bl_label = "Export Unreal T3D map"
    filename_ext = ".t3d"
    filter_glob: StringProperty(default="*.t3d", options={"HIDDEN"})

    def execute(self, context):
        n = export_t3d(context, self.filepath)
        self.report({"INFO"}, "Exported %d actors" % n)
        return {"FINISHED"}


class IMPORT_OT_ue_t3d(bpy.types.Operator, ImportHelper):
    """Import an Unreal Engine 2 map exported from UnrealEd as T3D"""
    bl_idname = "import_scene.ue_t3d"
    bl_label = "Import Unreal T3D map"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".t3d"
    filter_glob: StringProperty(default="*.t3d", options={"HIDDEN"})
    scale: FloatProperty(name="Scale", default=0.02, min=0.0001, max=100.0,
                         description="Blender units per Unreal unit (0.02: about 1 m per 50 Unreal units)")
    tex_size: IntProperty(name="Texture size", default=256, min=1,
                          description="Assumed texture size, for the viewport UVs only")
    mesh_dir: StringProperty(name="Static mesh folder", subtype="DIR_PATH", default="",
                             description="Folder with static meshes as <Name>.obj (e.g. exported with umodel)")

    def execute(self, context):
        made, warnings = import_t3d(context, self.filepath, self.scale, self.tex_size, self.mesh_dir)
        for w in warnings:
            self.report({"WARNING"}, w)
        self.report({"INFO"}, "Imported %d actors" % made)
        return {"FINISHED"}


def menu_import(self, context):
    self.layout.operator(IMPORT_OT_ue_t3d.bl_idname, text="Unreal T3D map (.t3d)")


def menu_export(self, context):
    self.layout.operator(EXPORT_OT_ue_t3d.bl_idname, text="Unreal T3D map (.t3d)")


CLASSES = (IMPORT_OT_ue_t3d, EXPORT_OT_ue_t3d)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
