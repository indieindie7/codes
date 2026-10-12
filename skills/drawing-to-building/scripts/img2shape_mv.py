"""multi-view images -> 3D shape (.glb) with Hunyuan3D-2mv (shape only; fits a 12 GB GPU).
Usage: venv/Scripts/python img2shape_mv.py <out.glb> front=<img> [left=<img>] [back=<img>] [right=<img>] [steps] [octree=256] [faces=20000]
octree = the surface grid (256 coarse, 384 fine, 512 finest; more VRAM/time); faces=0 keeps every face (the true high-poly
for baking), otherwise the mesh is reduced to that many.
Views are the character seen from the front, from its left side, from behind (and right).
Background is removed from each view."""
import sys, time, torch
from PIL import Image
from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline, FloaterRemover, DegenerateFaceRemover, FaceReducer

out = sys.argv[1]
views, steps, octree, faces = {}, 30, 256, 20000
for a in sys.argv[2:]:
    if "=" in a:
        k, v = a.split("=", 1)
        if k == "octree":
            octree = int(v)
        elif k == "faces":
            faces = int(v)
        else:
            views[k] = v
    else:
        steps = int(a)
t0 = time.time()
rm = BackgroundRemover()
images = {}
for k, path in views.items():
    img = rm(Image.open(path).convert("RGB"))
    img.save(out.rsplit(".", 1)[0] + f"_input_{k}.png")
    images[k] = img
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2mv", subfolder="hunyuan3d-dit-v2-mv")
mesh = pipe(image=images, num_inference_steps=steps, octree_resolution=octree, num_chunks=20000,
            generator=torch.manual_seed(42), output_type="trimesh")[0]
mesh = FloaterRemover()(mesh)
mesh = DegenerateFaceRemover()(mesh)
if faces:
    mesh = FaceReducer()(mesh, max_facenum=faces)
mesh.export(out)
print(f"IMG2SHAPE_MV {out}: views {sorted(images)}, {len(mesh.faces)} faces, {time.time() - t0:.0f}s, "
      f"peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
