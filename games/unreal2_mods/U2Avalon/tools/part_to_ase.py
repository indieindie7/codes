r"""One part GLB -> ASE on the SHARED palette, without touching the other meshes or Pal.tga:

    py tools/part_to_ase.py B_wall B_ctower ...
    py tools/part_to_ase.py scale=50 zero=1 hulls=1 B_culvert B_k_wall ...     (the story/kit parts, kit_parts.py)

scale=50 writes the ASE in world units (the importer's safe path: no material block, scale=50, zero=<name>);
zero=1 keeps the model's z = 0 as the pivot (slabs whose top is z = 0, the culvert's invert) instead of its bottom;
hulls=1 writes the MCDCX_* collision objects. The default (no options) is the old metre-unit behaviour.

glb_to_ase.py numbers palette stripes in order of first appearance, so a run over a single GLB gets its own
stripe order. This runs it into a scratch folder, reads that run's palette.json (linear 0..1 colours), maps
each colour to the nearest stripe of Models/ase/Pal.tga (the shared texture every building uses), rewrites the
ASE's U coordinates, copies the ASE into Models/ase, adds the bounds entry and the manifest row.
"""
import json, os, re, subprocess, sys, tempfile

from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASE = os.path.join(HERE, "Models", "ase")
GLB = os.path.join(HERE, "Models", "glb")
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
names = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
old = Image.open(os.path.join(ASE, "Pal.tga")).convert("RGB")
stripes = [old.getpixel((4 + 8 * i, 32)) for i in range(8)]


def nearest(c):
    return min(range(8), key=lambda k: sum((a - b) ** 2 for a, b in zip(stripes[k], c)))


bounds = json.load(open(os.path.join(ASE, "bounds.json")))
manifest = open(os.path.join(ASE, "manifest.txt")).read()
for name in names:
    tmp = tempfile.mkdtemp(prefix="part_")
    extra = ["scale=%s" % o["scale"]] if "scale" in o else []
    extra += ["zero=%s" % name] if o.get("zero") == "1" else []
    extra += ["hulls=1"] if o.get("hulls") == "1" else []
    r = subprocess.run([BLENDER, "-b", "--python", os.path.join(HERE, "tools", "glb_to_ase.py"), "--", GLB, tmp, "pattern=%s.glb" % name] + extra,
                       capture_output=True, text=True)
    if not os.path.exists(os.path.join(tmp, name + ".ase")):
        raise SystemExit("glb_to_ase failed for %s: %s" % (name, r.stdout[-3000:] + r.stderr[-3000:]))
    cols = json.load(open(os.path.join(tmp, "palette.json")))
    remap = {k: nearest(tuple(round(v * 255) for v in c[:3])) for k, c in enumerate(cols)}
    txt = open(os.path.join(tmp, name + ".ase")).read()
    txt = re.sub(r"(\*MESH_TVERT\s+\d+\s+)([\d.]+)", lambda m: "%s%.6f" % (m.group(1), (remap.get(int(float(m.group(2)) * 8), 0) + 0.5) / 8), txt)
    open(os.path.join(ASE, name + ".ase"), "w").write(txt)
    bounds[name] = json.load(open(os.path.join(tmp, "bounds.json")))[name]
    if not re.search(r"(?m)^%s " % re.escape(name), manifest):
        manifest += "%s Liandri \n" % name
    print(name, "->", remap, bounds[name], "(%s)" % (" ".join(extra) or "metres"))
json.dump(bounds, open(os.path.join(ASE, "bounds.json"), "w"), indent=1)
open(os.path.join(ASE, "manifest.txt"), "w").write(manifest)
