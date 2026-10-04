"""image -> 3D shape (.glb) with Hunyuan3D-2 (shape only; fits a 12 GB GPU).
Usage: venv/Scripts/python img2shape.py <image> <out.glb> [mini|full] [steps] [octree=256] [faces=20000]
octree=384 faces=0 gives the true high-poly (see img2shape_mv.py)."""
import sys, time, torch
from PIL import Image
from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline, FloaterRemover, DegenerateFaceRemover, FaceReducer

kv = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
pos = [a for a in sys.argv[1:] if "=" not in a]
src, out = pos[0], pos[1]
which = pos[2] if len(pos) > 2 else "mini"
steps = int(pos[3]) if len(pos) > 3 else 30
octree, faces = int(kv.get("octree", 256)), int(kv.get("faces", 20000))
t0 = time.time()
img = Image.open(src).convert("RGBA")
img = BackgroundRemover()(img.convert("RGB"))
img.save(out.rsplit(".", 1)[0] + "_input.png")
if which == "mini":
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2mini", subfolder="hunyuan3d-dit-v2-mini", use_safetensors=True)
else:
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2", subfolder="hunyuan3d-dit-v2-0")
mesh = pipe(image=img, num_inference_steps=steps, octree_resolution=octree, generator=torch.manual_seed(42))[0]
mesh = FloaterRemover()(mesh)
mesh = DegenerateFaceRemover()(mesh)
if faces:
    mesh = FaceReducer()(mesh, max_facenum=faces)
mesh.export(out)
print(f"IMG2SHAPE {out}: {len(mesh.faces)} faces, {time.time() - t0:.0f}s, peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
