"""Get a UT2004-style character (.psk + textures, optional .psa) ready for Unreal II's Golem.

What it changes, so the game's own animations and weapon code work on the model:
  * scale: to Unreal II human size (the marines are 108 units tall, foot to crown)
  * bones: "Bip01 ..." -> "Merc ..." (Unreal II's biped is the same Character Studio
    rig with a different prefix, so its animations drive the renamed bones)
  * weapon mount: UT2004's "Bone_weapon" becomes "handpointR02" (where Unreal II
    hangs the weapon); handpointR01/L01/L02 are added next to the hands
  * materials: renamed to the texture file names, so Golem finds the skins
  * textures: saved as plain uncompressed TGA (Golem's importer rejects RLE)
"""
import os
from PIL import Image
from psk import Mesh, Anims

MARINE_HEIGHT = 108.0          # U2MarineLight: CollisionHeight 54 -> 108 units, feet to crown
ORIGIN_SCALE = 0.7027          # the marine blueprints' OriginScale: their skeleton data is 1/0.7027 bigger
                               # than in game; a model sharing their animations must use the same units


def unreal2_bone_name(name):
    low = name.lower()
    if not low.startswith("bip01"):
        return name
    rest = name[5:].split()
    parts = [p.upper() if p.lower() in ("l", "r") else p[:1].upper() + p[1:] for p in rest]
    return " ".join(["Merc"] + parts)


def rename_bones(bones):
    renamed = {}
    for b in bones:
        new = unreal2_bone_name(b.name)
        if new != b.name:
            renamed[b.name] = new
            b.name = new
    return renamed


def add_handpoints(mesh):
    """handpointR02 carries the weapon in Unreal II. UT2004 rigs have Bone_weapon in the same role."""
    names = [b.name for b in mesh.bones]
    right = names.index("Merc R Hand") if "Merc R Hand" in names else None
    left = names.index("Merc L Hand") if "Merc L Hand" in names else None
    added = []
    if "handpointR02" in names:          # already an Unreal II skeleton (a mesh rigged on Dalton's own bones)
        return ["handpointR02 (already there)"]
    if "Bone_weapon" in names:
        mesh.bones[names.index("Bone_weapon")].name = "handpointR02"
        added.append("handpointR02 (was Bone_weapon)")
        wb = mesh.bones[names.index("Bone_weapon")]
        offset, quat = wb.pos, wb.quat
    elif right is not None:
        offset, quat = [mesh.bones[right].length * 0.5 or 5.0, 0.0, 3.0], [0.0, 0.0, 0.0, 1.0]
        mesh.add_bone("handpointR02", right, offset, quat); added.append("handpointR02")
    else:
        return added
    names = [b.name for b in mesh.bones]
    if right is not None and "handpointR01" not in names:
        mesh.add_bone("handpointR01", right, offset, quat); added.append("handpointR01")
    if left is not None:
        mirrored = [offset[0], offset[1], -offset[2]]
        for n in ("handpointL01", "handpointL02"):
            if n not in names:
                mesh.add_bone(n, left, mirrored, quat); added.append(n)
    return added


def height_of(mesh):
    lo, hi = mesh.bounds()
    return hi[2] - lo[2]


def save_tga(src, dst):
    im = Image.open(src)
    im = im.convert("RGBA") if "A" in im.getbands() else im.convert("RGB")
    w, h = im.size
    pw, ph = 1 << (w - 1).bit_length(), 1 << (h - 1).bit_length()
    if (pw, ph) != (w, h):
        im = im.resize((pw, ph), Image.LANCZOS)
    im.save(dst, compression=None)


def prepare(psk, out_dir, name, textures=(), psa=None, height=MARINE_HEIGHT / ORIGIN_SCALE, log=print):
    """Writes <out_dir>/<name>.psk (+ .psa) and the textures. Returns (psk, psa, texture names, scale)."""
    os.makedirs(out_dir, exist_ok=True)
    mesh = Mesh(psk)
    scale = height / height_of(mesh)
    mesh.scale(scale)
    # Unreal II meshes are centred on the pawn (feet at -height/2); UT2004's stand on their origin
    lo, hi = mesh.bounds()
    drop = (lo[2] + hi[2]) / 2
    for p in mesh.points:
        p[2] -= drop
    for b in mesh.bones:
        if b is mesh.bones[0]:
            b.pos[2] -= drop
    renamed = rename_bones(mesh.bones)
    hands = add_handpoints(mesh)
    log(f"mesh: {len(mesh.points)} points, {len(mesh.bones)} bones, scaled x{scale:.3f} to {height:.0f} units")
    log(f"  renamed {len(renamed)} bones to Unreal II names; weapon mounts: {', '.join(hands) or 'none'}")

    tex_names = []
    if textures:
        if len(textures) != len(mesh.materials):
            log(f"  warning: {len(mesh.materials)} materials but {len(textures)} textures; matching in order")
        for i, t in enumerate(textures):
            tn = os.path.splitext(os.path.basename(t))[0]
            save_tga(t, os.path.join(out_dir, tn + ".tga"))
            tex_names.append(tn)
            if i < len(mesh.materials):
                mesh.materials[i] = tn
    else:
        tex_names = list(mesh.materials)
    log(f"  materials -> textures: {mesh.materials}")
    out_psk = os.path.join(out_dir, name + ".psk")
    mesh.save(out_psk)

    out_psa = None
    if psa:
        anims = Anims(psa)
        anims.scale(scale)
        rename_bones(anims.bones)
        for b in anims.bones:
            if b.name == "Bone_weapon":
                b.name = "handpointR02"
        out_psa = os.path.join(out_dir, name + "Anims.psa")
        anims.save(out_psa)
        log(f"animations: {len(anims.seqs)} sequences, scaled and renamed")
    return out_psk, out_psa, tex_names, scale
