r"""One part GLB -> ASE on the SHARED palette, without touching the other meshes or Pal.tga:

    py tools/part_to_ase.py B_wall B_ctower ...

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
names = sys.argv[1:]
old = Image.open(os.path.join(ASE, "Pal.tga")).convert("RGB")
stripes = [old.getpixel((4 + 8 * i, 32)) for i in range(8)]


def nearest(c):
    return min(range(8), key=lambda k: sum((a - b) ** 2 for a, b in zip(stripes[k], c)))


bounds = json.load(open(os.path.join(ASE, "bounds.json")))
manifest = open(os.path.join(ASE, "manifest.txt")).read()
for name in names:
    tmp = tempfile.mkdtemp(prefix="part_")
    subprocess.run([BLENDER, "-b", "--python", os.path.join(HERE, "tools", "glb_to_ase.py"), "--", GLB, tmp, "pattern=%s.glb" % name],
                   capture_output=True, text=True)
    cols = json.load(open(os.path.join(tmp, "palette.json")))
    remap = {k: nearest(tuple(round(v * 255) for v in c[:3])) for k, c in enumerate(cols)}
    txt = open(os.path.join(tmp, name + ".ase")).read()
    txt = re.sub(r"(\*MESH_TVERT\s+\d+\s+)([\d.]+)", lambda m: "%s%.6f" % (m.group(1), (remap.get(int(float(m.group(2)) * 8), 0) + 0.5) / 8), txt)
    open(os.path.join(ASE, name + ".ase"), "w").write(txt)
    bounds[name] = json.load(open(os.path.join(tmp, "bounds.json")))[name]
    if not re.search(r"(?m)^%s " % re.escape(name), manifest):
        manifest += "%s Liandri \n" % name
    print(name, "->", remap, bounds[name])
json.dump(bounds, open(os.path.join(ASE, "bounds.json"), "w"), indent=1)
open(os.path.join(ASE, "manifest.txt"), "w").write(manifest)
