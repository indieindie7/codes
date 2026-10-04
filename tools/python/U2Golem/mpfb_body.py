"""Generate a human body with MPFB (MakeHuman for Blender, CC0 assets) and rig it with MPFB's
game-engine skeleton, ready for blend2psk.py + kitbash.py (which fits it onto an Unreal II
skeleton such as Dalton's).

Run:  blender -b --python mpfb_body.py -- <out.blend> [macros.json]
Skin, eyes and eyebrows come from the MakeHuman system asset pack (CC0) extracted into MPFB's user
data folder; choose them with "_skin", "_eyes", "_eyebrows" keys in macros.json.
macros.json (MPFB macro sliders, 0..1): {"gender": 1, "age": 0.5, "muscle": 0.8, "weight": 0.55,
"proportions": 0.7, "height": 0.6, "race": {"african": 1, "asian": 0, "caucasian": 0}}
"""
import json, os, sys
import bpy
import addon_utils

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0])
macros = json.load(open(args[1])) if len(args) > 1 else {}

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("bl_ext.blender_org.mpfb", default_set=True)
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService

info = TargetService.get_default_macro_info_dict()
for k, v in macros.items():
    if not k.startswith("_"):
        info[k] = v
body = HumanService.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=False,
                                 feet_on_ground=True, scale=0.1, macro_detail_dict=info)
HumanService.add_builtin_rig(body, "game_engine", import_weights=True)
# skin, eyes, brows from the MakeHuman system asset pack (CC0), if installed in MPFB's user data
from bl_ext.blender_org.mpfb.services.locationservice import LocationService
data = LocationService.get_user_data()
skin = macros.get("_skin", "middleage_african_male")
skin_file = os.path.join(data, "skins", skin, skin + ".mhmat")
if os.path.exists(skin_file):
    HumanService.set_character_skin(skin_file, body, skin_type="GAMEENGINE", material_instances=False)
for kind, name in (("eyes", macros.get("_eyes", "low-poly")), ("eyebrows", macros.get("_eyebrows", "eyebrow001"))):
    f = os.path.join(data, kind, name, name + ".mhclo")
    if os.path.exists(f):
        HumanService.add_mhclo_asset(f, body, asset_type=kind.capitalize(), subdiv_levels=0, material_type="MAKESKIN")
eye_mat = os.path.join(data, "eyes", "materials", macros.get("_eye_colour", "brown") + ".mhmat")
# bake the shape keys (the macro targets) into the mesh, and drop the helper geometry
bpy.context.view_layer.objects.active = body
if body.data.shape_keys:
    body.shape_key_add(name="baked", from_mix=True)
    for kb in list(body.data.shape_keys.key_blocks)[:-1]:
        body.shape_key_remove(kb)
    body.shape_key_remove(body.data.shape_keys.key_blocks[0])
for m in list(body.modifiers):
    if m.type == "MASK":
        bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.wm.save_as_mainfile(filepath=out)
arm = body.parent
print("MPFB_BODY", len(body.data.vertices), "verts", len(body.data.polygons), "faces, rig", arm.name if arm else None,
      "height", round(max(v.co.z for v in body.data.vertices) - min(v.co.z for v in body.data.vertices), 3))
