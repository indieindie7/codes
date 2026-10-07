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

## Licences

Everything used here is permissive (OpenCV Apache-2.0, FLIP BSD-3, numpy/scipy/Pillow BSD-style).
Non-commercial or unlicensed models from the research notes (pyiqa, DeepGaze, UMSI...) are not used.

## Not yet

A random-prints step for Unreal II's pilot, UNISAL saliency, HUD text contrast, and glitch checks beyond missing textures and black characters.
