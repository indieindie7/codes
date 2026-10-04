# Hunyuan3D-2 helper scripts

Copies of the scripts that live in the local Hunyuan3D-2 checkout (`Documents\Tools\Hunyuan3D-2`).

- `img2shape_mv.py`: front/back/left views -> mesh. `octree=384 faces=0` gives the true high-poly (~290k faces).
- `paint_mesh.py`: Hunyuan3D-Paint: mesh + reference images -> textured mesh (4 min, ~7 GB VRAM with cpu offload).
- `custom_rasterizer_kernel.py`: pure numpy replacement for Hunyuan's compiled rasteriser (goes in
  `Hunyuan3D-2/pure_raster/`), so no CUDA toolkit or compiler is needed.

Setup notes (Windows, 12 GB GPU):
- weights: `hunyuan3d-paint-v2-0` (9 GB) and `hunyuan3d-delight-v2-0` (4 GB) from `tencent/Hunyuan3D-2`,
  placed in `~/.cache/hy3dgen/tencent/Hunyuan3D-2/`.
- `pip install diffusers==0.32.2` (0.40 needs a newer huggingface_hub than transformers 4.49 allows).
- one-line fix in `hy3dgen/texgen/hunyuanpaint/pipeline.py`: `self.unet.learned_text_clip_gen.to(self._execution_device)`
  (with cpu offload that parameter is still on the CPU).

Then bake onto the game mesh: `retopo_bake.py high=<painted.glb> low=<lowpoly.glb> cage=0.02`.
