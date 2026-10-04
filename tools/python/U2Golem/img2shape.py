"""image -> 3D shape (.glb) with Hunyuan3D-2 (shape only; fits a 12 GB GPU).
Usage: venv/Scripts/python img2shape.py <image> <out.glb> [mini|full] [steps]"""
import sys, time, torch
from PIL import Image
from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline, FloaterRemover, DegenerateFaceRemover, FaceReducer

src, out = sys.argv[1], sys.argv[2]
which = sys.argv[3] if len(sys.argv) > 3 else "mini"
steps = int(sys.argv[4]) if len(sys.argv) > 4 else 30
t0 = time.time()
img = Image.open(src).convert("RGBA")
img = BackgroundRemover()(img.convert("RGB"))
img.save(out.rsplit(".", 1)[0] + "_input.png")
if which == "mini":
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2mini", subfolder="hunyuan3d-dit-v2-mini", use_safetensors=True)
else:
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2", subfolder="hunyuan3d-dit-v2-0")
mesh = pipe(image=img, num_inference_steps=steps, octree_resolution=256, generator=torch.manual_seed(42))[0]
mesh = FloaterRemover()(mesh)
mesh = DegenerateFaceRemover()(mesh)
mesh = FaceReducer()(mesh, max_facenum=20000)
mesh.export(out)
print(f"IMG2SHAPE {out}: {len(mesh.faces)} faces, {time.time() - t0:.0f}s, peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
