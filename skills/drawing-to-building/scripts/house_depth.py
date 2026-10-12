"""Fake depth pass on a perspective sketch: Depth Anything V2 (relative + metric) -> depth images.
venv/Scripts/python house_depth.py <img> <outdir>   (2026-10-11, housePlan1 crop_whole)"""
import sys, os, cv2, numpy as np
from PIL import Image
from transformers import pipeline
img, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
im = Image.open(img).convert("RGB")
for tag, name in [("rel", "depth-anything/Depth-Anything-V2-Small-hf"),
                  ("met", "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf")]:
    try:
        d = pipeline("depth-estimation", model=name, device="cpu")(im)["predicted_depth"].squeeze().numpy().astype(np.float32)
    except Exception as e:
        print(tag, "FAILED", e); continue
    d = cv2.resize(d, im.size)
    np.save(os.path.join(out, f"depth_{tag}.npy"), d)
    n = cv2.normalize(d, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    if tag == "met": n = 255 - n               # near = bright for both
    cv2.imwrite(os.path.join(out, f"depth_{tag}.png"), cv2.applyColorMap(n, cv2.COLORMAP_INFERNO))
    print(tag, d.min(), d.max())
