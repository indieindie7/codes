# visual_qa

Design heuristics as numbers on game screenshots: the squint test, where the eye lands, clutter,
colour, composition, and, with a character mask, figure-ground and silhouette. It writes an HTML
contact sheet that puts the frames failing the most checks first. Background and sources:
`games/reports/visual-heuristics-qa.html` and `games/research_notes/Visual heuristics automation/`.

## Setup

A venv of its own (about 200 MB):

```
python -m venv C:\Users\john\Documents\Tools\visualqa
C:\Users\john\Documents\Tools\visualqa\Scripts\python.exe -m pip install --no-cache-dir numpy scipy pillow opencv-contrib-python-headless flip-evaluator
```

## Use

```
visual_qa.py score <frames dir> [--out DIR] [--baseline base.json] [--masks DIR]
visual_qa.py baseline <frames dir> --save base.json
visual_qa.py compare <before dir> <after dir> [--out DIR]
```

- **score**: one record per frame in `metrics.json`, and `report.html` with the frame, its squint
  view (blurred, 9 values) and a saliency overlay.
- **baseline**: each metric's mean and spread over a set of normal frames (stock levels). With
  `--baseline`, `score` flags any metric more than 2 standard deviations from it, so a flag means
  "unusual for this level", not a grade from a model trained on photos.
- **compare**: frames with the same names in two folders (the same camera before and after a look
  edit): NVIDIA FLIP difference maps and the metric changes that pass a minimum per metric.

Masks: `<frame>_mask.png` or `_mask.bmp` next to a frame, or `--masks DIR`; white is the character.
The d3d8to9 fork writes them (`shotmask=1`, or AdventNative's `CaptureMask`), and Advent's pilot step
`randomprints N [settle]` takes N frames with masks from random places, every other one beside a character.

## Saliency

UNISAL (Apache-2.0, ECCV 2020, trained on human eye fixations) when `Documents\Tools\unisal` is there
(`git clone https://github.com/rdroste/unisal`, weights included; needs the CPU PyTorch in the venv:
`pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu`).
About 0.07 s a frame on the CPU. Otherwise, or with `--saliency spectral`, OpenCV's spectral residual.

## HUD contrast

With 4 or more frames, the HUD is found as the pixels that stay the same (and aren't dark) across
them, so frames from different places are needed. Each frame's HUD is checked against what is behind
it (WCAG contrast ratio; flagged under 3:1, the floor for large text and UI parts).

## Licences

Everything used here is permissive (OpenCV Apache-2.0, FLIP BSD-3, numpy/scipy/Pillow BSD-style).
Non-commercial or unlicensed models from the research notes (pyiqa, DeepGaze, UMSI...) are not used.

## Not yet

A random-prints step for Unreal II's pilot, and glitch checks that need two frames (z-fighting, shimmer).
