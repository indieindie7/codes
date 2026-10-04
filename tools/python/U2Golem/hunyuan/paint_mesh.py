"""Texture a mesh from reference images with Hunyuan3D-Paint (multi-view diffusion + bake to UVs).
Usage: venv/Scripts/python paint_mesh.py <mesh.glb> <out.glb> <ref1.png> [ref2.png ...] [faces=40000] [offload=1]
The first image is the main (front) reference; further ones (back, side) are extra references.
The mesh is reduced to `faces` (0 = keep) and re-unwrapped; bake the result onto a game mesh afterwards
(retopo_bake.py). Uses pure_raster/custom_rasterizer_kernel.py instead of the compiled rasteriser."""
import os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "pure_raster"))
sys.path.insert(0, os.path.join(here, "hy3dgen", "texgen", "custom_rasterizer"))
import torch, trimesh
from PIL import Image
from hy3dgen.shapegen import FaceReducer
from hy3dgen.texgen import Hunyuan3DPaintPipeline

mesh_path, out = sys.argv[1], sys.argv[2]
refs, opt = [], {"faces": "40000", "offload": "1"}
for a in sys.argv[3:]:
    if "=" in a:
        k, v = a.split("=", 1)
        opt[k] = v
    else:
        refs.append(a)
t0 = time.time()
mesh = trimesh.load(mesh_path, force="mesh")
if int(opt["faces"]) and len(mesh.faces) > int(opt["faces"]):
    mesh = FaceReducer()(mesh, max_facenum=int(opt["faces"]))
pipe = Hunyuan3DPaintPipeline.from_pretrained("tencent/Hunyuan3D-2", subfolder="hunyuan3d-paint-v2-0")
if int(opt["offload"]):
    pipe.enable_model_cpu_offload()
images = [Image.open(r).convert("RGBA") for r in refs]
mesh = pipe(mesh, image=images)
mesh.export(out)
print(f"PAINT_MESH {out}: {len(mesh.faces)} faces, {len(refs)} reference(s), {time.time() - t0:.0f}s, "
      f"peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
