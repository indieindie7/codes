# pose: drawing-practice vision tools

Small scripts used while practising figure and head drawing. They run pose and face models on a reference image (a photo of a statue, for example) and on a drawing, then draw construction overlays or a rough 3D point cloud.

| Script | What it does |
|---|---|
| `drawcheck.py` | NLF body pose + SAM2.1 silhouette + part map. Modes: `ref` (analyse a reference), `over` (strokes drawn over the reference), `paper` (separate drawing). Reports head-heights and joint angles. |
| `facecheck.py` | MediaPipe FaceLandmarker → Loomis head overlay (ball, side cuts, brow line, centre line, thirds, jaw) + yaw/pitch/roll. |
| `ddfa_run.py` | 3DDFA_V2 dense 3D face fit on a manual face box → mesh overlay + yaw/pitch/roll. |
| `fuse3d.py` | Fuses the NLF SMPL body, the 3DDFA face and the SAM mask (from `drawcheck ref`) into one coloured point cloud, then renders a splat turntable (`sheet.png`, `turntable.gif`, `cloud.npz`). |
| `multiview.py` | Several photos of one subject → one coloured point cloud + `viewer.html` (plain WebGL, no libraries: orbit, zoom, pan, view buttons, "Which photo" colouring). Geometry is the NLF SMPL body of the first photo; each photo gets its own NLF fit, aligned to the first (similarity fit on the 6890 verts). Colour = z-buffer visibility x facing weight, blended over photos; b&w photos are tinted to the first photo's mean. Points no photo sees take their neighbours' colour, shaded. |

## Limits (measured)
- Works on photos and on strokes drawn over a photo. On plain pencil drawings, NLF results change with the crop box (6.0 to 11.9 heads on the same drawing), and MediaPipe found no face.
- `fuse3d` uses a single image, so the back reuses the front colours ("false render"). Side views look see-through because the points are sparse. The urn and drapery are not modelled.
- `multiview` needs `viewer_template.html` next to it. NLF vertices are in mm; the viewer scales the body to 1.7 units.
- The two face models disagreed on pitch for the test statue. Which one is right is unverified.

## Setup
Python 3.13, CUDA GPU. Packages: `torch torchvision transformers opencv-python pillow scipy pyyaml mediapipe`.
- `NLF_MODEL`: path to `nlf_l_multi_0.3.2.torchscript` ([NLF](https://github.com/isarandi/nlf)). Default `models/...`.
- `DDFA_DIR`: clone of [3DDFA_V2](https://github.com/cleardusk/3DDFA_V2), which includes the `mb1_120x120` weights. Default `./3ddfa`.
- `facecheck.py` expects `face_landmarker.task` next to it ([MediaPipe models](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)).
- SAM2.1-small loads from Hugging Face (`facebook/sam2.1-hiera-small`).
- Import torchvision before `torch.jit.load` on NLF, because it registers `nms`.

## Example
```
py -3.13 drawcheck.py ref statue.png statue.npz
py -3.13 facecheck.py statue.png head.png --box 50,0,140,110
py -3.13 ddfa_run.py statue.png face3d.png 72,22,119,96
py -3.13 fuse3d.py statue.png statue.npz 72,22,119,96 out
py -3.13 drawcheck.py ref side.jpg side.npz
py -3.13 multiview.py out_mv statue.png statue.npz side.jpg side.npz   # first photo = geometry
```

## Next
- `multiview`: add the 3DDFA face and the drapery/urn; points are body-only, and the back is filled in when no photo sees it.
