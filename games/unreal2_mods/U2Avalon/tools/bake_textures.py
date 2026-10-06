"""Bake bounced sky light + occlusion into a texture per building (Cycles), so the flat palette colours get
the contact shadows and gradients UE2's vertex lighting cannot give. Direct light is NOT baked: the engine's
sun still lights the meshes, so one bake serves the day and the dusk map.

    blender -b --python bake_textures.py -- <glb_dir> <out_dir> [pattern=*.glb] [size=256] [samples=48] [only=a,b]

Per <stem>.glb: join the meshes, Smart-UV-unwrap, bake DIFFUSE (colour + indirect, no direct) under a warm
grey sky dome, denoise, write <out_dir>/<stem>.tga (top-down rows: UnrealEd does not flip TGAs) and
<out_dir>/<stem>.glb (the unwrapped mesh with the baked image as its material), which glb_to_ase.py
exports with uvs=mesh. Big buildings get size*2.
"""
import glob, math, os, sys
import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], os.path.abspath(a[1])
o = dict(x.split("=", 1) for x in a[2:])
SIZE, SAMPLES = int(o.get("size", 256)), int(o.get("samples", 48))
ONLY = set(o["only"].split(",")) if "only" in o else None
os.makedirs(out, exist_ok=True)
SKY = (1.0, 1.0, 1.0)      # a white dome: an open surface bakes to its own albedo (factor 1), crevices darker; the engine adds sun + its own ambient


def bake(path):
    stem = os.path.basename(path)[:-4]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
    for ob in bpy.context.scene.objects:
        ob.select_set(ob in meshes)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    # size by extent: anything over 25 m gets a bigger map
    dims = max(ob.dimensions)
    size = SIZE * 2 if dims > 25 else SIZE
    # unwrap: a lightmap pack (every face its own cell, uniform texel density, tiny margins); Smart UV made
    # ~1200 islands of a few texels each for a hall and the bake was mostly margin
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                             PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    bpy.ops.object.mode_set(mode="OBJECT")
    # the bake target image, linked into every material as the active node
    img = bpy.data.images.new(stem, size, size, alpha=False)
    for slot in ob.material_slots:
        m = slot.material
        if m is None:
            continue
        m.use_nodes = True
        node = m.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = img
        m.node_tree.nodes.active = node
    # world: a plain dome
    sc = bpy.context.scene
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = SKY + (1,)
    bg.inputs[1].default_value = 1.0
    sc.world = world
    # a ground plane so the undersides and feet darken like they stand on something
    bpy.ops.mesh.primitive_plane_add(size=dims * 6, location=(0, 0, -0.02))
    ground = bpy.context.object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.22, 0.18, 1)
    ground.data.materials.append(gm)
    ground.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
    # the dome's own light counts as DIRECT in Cycles' diffuse pass; there is no lamp in the scene, so
    # direct + indirect here = sky occlusion + bounce, which is exactly the factor we want baked
    sc.render.bake.use_pass_direct = True
    sc.render.bake.use_pass_indirect = True
    sc.render.bake.use_pass_color = True
    sc.render.bake.margin = 4
    bpy.ops.object.bake(type="DIFFUSE")
    # write the TGA top-down (UnrealEd does not flip), uncompressed
    px = np.array(img.pixels[:], np.float32).reshape(size, size, 4)
    px = px[::-1]                      # Blender's rows are bottom-up
    # the pixels come back LINEAR and the byte TGA stores them as-is. Kept linear on purpose: the palette
    # stripes (glb_to_ase.py) are stored the same way, and UE2's overbright sun (brightness 240 + ambient
    # 130) washes a properly sRGB-encoded texture out to cream. GAMMA below lifts the darks a little.
    GAMMA = 1.0      # 1.4 still washed out under the sun; 1.0 = exactly how the palette stripes are stored
    px[..., :3] = np.power(np.clip(px[..., :3], 0, 1), 1 / GAMMA)
    flipped = bpy.data.images.new(stem + "_tga", size, size, alpha=False)
    flipped.pixels = px.ravel()
    flipped.filepath_raw = os.path.join(out, stem + ".tga")
    flipped.file_format = "TARGA_RAW"
    flipped.save()
    # the unwrapped mesh with the baked image as its one material, for glb_to_ase uvs=mesh
    img.filepath_raw = os.path.join(out, stem + ".png")
    img.file_format = "PNG"
    img.save()
    one = bpy.data.materials.new("baked")
    one.use_nodes = True
    tex = one.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    one.node_tree.links.new(tex.outputs["Color"], one.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    ob.data.materials.clear()
    ob.data.materials.append(one)
    ground.select_set(False)
    bpy.data.objects.remove(ground)
    for x in bpy.context.scene.objects:
        x.select_set(x == ob)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, stem + ".glb"), use_selection=True, export_format="GLB",
                              export_apply=True, export_image_format="AUTO")
    print("BAKED", stem, size, "px", len(ob.data.polygons), "faces")


for f in sorted(glob.glob(os.path.join(src, o.get("pattern", "*.glb")))):
    stem = os.path.basename(f)[:-4]
    if ONLY and stem not in ONLY:
        continue
    bake(f)
