# Visual heuristics automation — sources

Research date: 2026-10-07. Goal: score random screenshots of UE2-era games (Unreal II, Advent Rising) in an
automated QA loop with design heuristics (squint test, saliency, figure-ground, silhouette, clutter, colour,
composition, HUD contrast, aesthetics, before/after diffs) plus game glitch detection.

Every repo below was checked through the GitHub API on 2026-10-07 (exists, stars, last push, licence).
"Licence" is the SPDX id GitHub reports; where GitHub said NOASSERTION I read the LICENSE file.
Licence flags for the user's GPL / non-commercial projects:
- **OK** = permissive or GPL-compatible, can be redistributed in a mod/tool.
- **NC** = non-commercial only. Fine for private analysis; for redistribution only non-commercially
  and only under that licence's terms (not GPL-compatible).
- **NONE** = no licence file. All rights reserved by default: run it privately, do not redistribute or vendor it.
- Model weights often carry their own licence separate from the code (noted where it matters).

All are Python unless noted. "CPU ok" = practical on a Windows PC without a GPU (seconds per image);
"GPU nice" = runs on CPU but slow; "GPU" = needs a consumer GPU (VRAM noted).

---

## 1. Swiss-army knife: AIM (Aalto Interface Metrics) — best single starting point

- **aalto-ui/aim** — https://github.com/aalto-ui/aim — ★66, last push 2023-06 (default branch `aim2`), **MIT** (OK)
  except metric m9 (UMSI weights + code, **NC**, MIT/Adobe research licence).
- Built for GUI screenshots but every metric is a plain function on a PNG, so it works on game frames.
  Metric modules in `backend/aim/metrics/`:
  - m1/m2 PNG/JPEG file size (cheap complexity proxy)
  - m3 distinct RGB values, m17 distinct H/S/V values, m19 per-cluster distinct values
  - m4 contour density, m6 contour congestion
  - **m5 figure-ground contrast**
  - **m7 subband entropy, m8 feature congestion** (Rosenholtz clutter)
  - m10 WAVE (weighted affective valence estimates — colour preference)
  - m11/m12 static/dynamic colour clusters
  - m13 luminance std, m14 Lab mean/std, m16 HSV mean/std
  - **m15 colourfulness (Hasler–Süsstrunk)**
  - **m18 NIMA aesthetic score** (DenseNet121 weights shipped)
  - **m20 colour harmony** (distance to nearest Cohen-Or 2006 hue template, port of tartarskunk/ColorHarmonization)
  - m21 grid quality, m22 white space, m23 colour-blindness simulation
  - m9 UMSI saliency/importance (Keras .h5 shipped; NC)
  - m24/m25 UI segmentation, m30 MDEAM
- Deps: numpy, opencv, scikit-image, pytorch (m18), tensorflow/keras (m9). The full web app wants MongoDB + Node,
  but the metric modules can be imported directly. **CPU ok** (feature congestion is the slow one, a few s/image).
- Game use: lift m5/m7/m8/m15/m20 into the QA loop as-is.

## 2. Saliency / attention prediction ("where does the eye land")

| Repo | What | Licence | Notes |
|---|---|---|---|
| **opencv/opencv_contrib** (saliency module) https://github.com/opencv/opencv_contrib | Spectral residual (Hou & Zhang 2007), fine-grained static saliency, BING objectness, motion saliency | Apache-2.0 (OK) | ★10.2k, active 2026. `pip install opencv-contrib-python`, `cv2.saliency.StaticSaliencySpectralResidual_create()`. CPU, milliseconds. Classic baseline, no training. |
| **akisatok/pySaliencyMap** https://github.com/akisatok/pySaliencyMap | Itti-Koch-Niebur 1998 (intensity/colour/orientation/motion pyramids) | MIT (OK) | ★149, last push 2023. OpenCV+numpy, CPU. |
| **shreelock/gbvs** https://github.com/shreelock/gbvs | Graph-Based Visual Saliency (Harel/Koch/Perona) + Itti-Koch, Python port | **NONE** | ★61, last push 2019. CPU. Private use only. |
| **uoip/SpectralResidualSaliency** https://github.com/uoip/SpectralResidualSaliency | Spectral residual, C++/Python | **NONE** | ★34, 2016. Redundant with OpenCV. |
| **matthias-k/DeepGaze** https://github.com/matthias-k/DeepGaze | DeepGaze IIE / III — top MIT/Tuebingen saliency benchmark models; fixation density maps, DG III also scanpaths | **NONE** (no LICENSE file) | ★213, active (2026-08). PyTorch, weights auto-download. Needs a centre-bias prior (shipped MIT1003 one works). CPU ok (~seconds), GPU nice. Best-quality free-viewing predictor. Private use only. |
| **matthias-k/pysaliency** https://github.com/matthias-k/pysaliency | Saliency evaluation framework (AUC, NSS, CC, KLD, IG) + dataset loaders | MIT (OK) | ★179, active 2026. Use to compare predicted maps or validate against eye-tracking. |
| **rdroste/unisal** https://github.com/rdroste/unisal | UNISAL (ECCV 2020) unified image + video saliency, very small (MobileNetV2) | Apache-2.0 (OK) | ★158, last push 2024. Pretrained weights in repo. **CPU ok**, also does video (temporal saliency on gameplay clips). Best licence/quality trade-off. |
| **LJOVO/TranSalNet** https://github.com/LJOVO/TranSalNet | Transformer+CNN saliency (Neurocomputing 2022), "perceptually relevant" | MIT (OK) | ★72, last push 2024. Weights via Google Drive. CPU ok, GPU nice. |
| **alexanderkroner/saliency** https://github.com/alexanderkroner/saliency | MSI-Net contextual encoder-decoder (Neural Networks 2020) | MIT (OK) | ★216, last push 2024. TensorFlow; pretrained SALICON/MIT/CAT2000 graphs. CPU ok. |

Note: all these are trained on natural photos (SALICON/MIT1003). They are a reasonable proxy for game frames but
ignore task-driven attention (crosshair, objectives). For HUD-heavy frames the UI models below may fit better.

## 3. UI / graphic-design importance (visual hierarchy) — open "Attention Insight"-style

| Repo | What | Licence | Notes |
|---|---|---|---|
| **diviz-mit/predimportance-public** https://github.com/diviz-mit/predimportance-public | UMSI (UIST 2020): unified saliency/importance for posters, infographics, mobile UI, natural images | **NC** (MIT/Adobe research-only) | ★13, 2020. Keras. Also bundled as AIM m9. CPU ok. |
| **cvzoya/visimportance** https://github.com/cvzoya/visimportance | Bylinskii et al. UIST 2017 visual importance for graphic designs/data vis | **NC** (MIT/Adobe research-only) | ★176, 2017, Caffe (old). PyTorch ports: cydonia999/visimportance-in-pytorch (★18), egorabaturov/visimportance-in-pytorch (★16) — licences not checked, assume inherit NC. |
| **YueJiang-nj/UEyes-CHI2023** https://github.com/YueJiang-nj/UEyes-CHI2023 | UEyes (CHI 2023): eye-tracking dataset over UI types + saliency and scanpath model code, evaluation | **NONE** | ★40, last push 2024. Mainly for re-training; private use. |

## 4. Visual clutter / complexity

| Repo | What | Licence | Notes |
|---|---|---|---|
| **kargaranamir/visual-clutter** https://github.com/kargaranamir/visual-clutter | Python port of Rosenholtz et al. 2007 (JoV) **feature congestion** and **subband entropy**, returns scalar + clutter map | MIT (OK) | ★17, last push 2023. `pip install visual-clutter`. numpy/scipy/opencv, CPU. The clutter *map* is directly useful ("where is it busy"). |
| AIM m6/m7/m8 (above) | contour congestion, subband entropy, feature congestion | MIT | Same algorithms, maintained in AIM. |
| **tinglyfeng/IC9600** https://github.com/tinglyfeng/IC9600 | ICNet image-complexity regressor (TPAMI 2023) + IC9600 dataset; outputs score + complexity map | **NONE** | ★75, last push 2024. PyTorch, weights via Drive. CPU ok. Private use. |
| **esaraee/Savoias-Dataset** https://github.com/esaraee/Savoias-Dataset | Visual complexity dataset (7 categories incl. scenes, art) with human ratings | **NONE** | ★47, 2020. Data only — for calibrating whichever metric you pick. |

## 5. Colour: colourfulness, palette, harmony

| Repo | What | Licence | Notes |
|---|---|---|---|
| AIM m15 | Hasler–Süsstrunk 2003 colourfulness (rg/yb opponent std+mean) | MIT | ~10 lines of numpy; trivial to inline. |
| AIM m20 | Cohen-Or 2006 hue-template harmony distance | MIT | Port of tartarskunk/ColorHarmonization (not checked). |
| **colour-science/colour** https://github.com/colour-science/colour | Full colour science: CIELAB/CAM16/OKLab, ΔE2000, CVD simulation, contrast | BSD-3 (OK) | ★2.7k, active 2026. CPU. Foundation for palette distance and before/after colour shifts. |
| **obskyr/colorgram.py** https://github.com/obskyr/colorgram.py | Dominant palette extraction | MIT (OK) | ★470, 2021. CPU. |
| **fengsp/color-thief-py** https://github.com/fengsp/color-thief-py | Dominant colour / palette (MMCQ) | BSD-style (OK) | ★1.1k, 2022. CPU. |
| **profnote/color-harmony** https://github.com/profnote/color-harmony | Palette + harmony-scheme analysis of illustrations (notebook) | MIT (OK) | ★20, 2021. Small reference. |

## 6. Text / HUD contrast (WCAG)

- **gsnedders/wcag-contrast-ratio** — https://github.com/gsnedders/wcag-contrast-ratio — MIT, ★23, **archived** (2022).
  WCAG 2.x relative luminance + ratio. The formula is 5 lines; just inline it.
- For a screenshot: segment HUD text (OCR boxes via an OCR engine, or a fixed HUD mask since UE2 HUD positions
  are known), take the text colour vs a dilated ring of background pixels, compute ratio per glyph region,
  flag < 4.5:1 (or < 3:1 for large text). APCA (WCAG 3 draft) is a better perceptual fit for light-on-dark HUDs;
  `colour-science` does not ship APCA, small reference implementations exist on PyPI (`apca-w3`, not verified).
- AIM m23 colour-blindness simulation + re-run contrast = colour-blind HUD check.

## 7. Aesthetic quality predictors

| Repo | What | Licence | Notes |
|---|---|---|---|
| **christophschuhmann/improved-aesthetic-predictor** https://github.com/christophschuhmann/improved-aesthetic-predictor | CLIP ViT-L/14 embedding + MLP → 1-10 aesthetic score (LAION-Aesthetics v2) | Apache-2.0 (OK) | ★1.3k, 2024. Needs OpenAI CLIP (~900 MB). GPU nice; CPU ~1-2 s/image. |
| **LAION-AI/aesthetic-predictor** https://github.com/LAION-AI/aesthetic-predictor | Original linear head on CLIP | MIT (OK) | ★738, 2022. |
| **discus0434/aesthetic-predictor-v2-5** https://github.com/discus0434/aesthetic-predictor-v2-5 | SigLIP-based, trained to work on illustrations/renders too, not just photos | AGPL-3.0 (OK for GPL use) | ★439, 2024. GPU nice (~4 GB). Likely the best fit for CG frames. |
| **shunk031/simple-aesthetics-predictor** https://github.com/shunk031/simple-aesthetics-predictor | HF-transformers wrapper for the LAION predictors | MIT (OK) | ★47, 2025. Easiest install. |
| **idealo/image-quality-assessment** https://github.com/idealo/image-quality-assessment | NIMA (aesthetic + technical MobileNet heads) | Apache-2.0 (OK) | ★2.2k, **archived** 2024. Keras/Docker. CPU ok. |
| **truskovskiyk/nima.pytorch** https://github.com/truskovskiyk/nima.pytorch | NIMA in PyTorch | MIT (OK) | ★351, 2022. CPU ok. |
| **titu1994/neural-image-assessment** https://github.com/titu1994/neural-image-assessment | NIMA in Keras | MIT (OK) | ★824, 2019. |
| **Q-Future/Q-Align** https://github.com/Q-Future/Q-Align | LMM (mPLUG-Owl2 7B) scoring quality + aesthetics, ICML 2024 | **NC** (S-Lab Licence 1.0) | ★627, active 2026. GPU ~16 GB fp16 (less with 4-bit). Strong but heavy. |

Caution: all are trained on photos (AVA / LAION). On low-poly 2003 frames they mostly measure "photo-likeness".
Use them for **relative** before/after deltas on the same view, not absolute grades.

## 8. Image-quality toolboxes (no-reference and full-reference)

- **chaofengc/IQA-PyTorch (pyiqa)** — https://github.com/chaofengc/IQA-PyTorch — ★3.4k, active 2026-08,
  **PolyForm Noncommercial 1.0.0** (NC; changed from the earlier S-Lab licence). One API (`pyiqa.create_metric`)
  for ~50 metrics: FR (PSNR, SSIM, MS-SSIM, LPIPS, DISTS, FSIM, VIF, …), NR (NIQE, BRISQUE, MUSIQ, MANIQA,
  CLIP-IQA, TOPIQ, Q-Align, …), aesthetics (NIMA, LAION aes, TOPIQ-IAA). Weights auto-download. CPU ok for most,
  GPU nice. The fastest way to try many scores; private use (NC).
- **photosynthesis-team/piq** — https://github.com/photosynthesis-team/piq — ★1.6k, last push 2024, **Apache-2.0** (OK).
  SSIM/MS-SSIM, LPIPS, DISTS, FID, BRISQUE, CLIP-IQA, HaarPSI, GMSD, VIF, etc. The permissive alternative to pyiqa.

## 9. Perceptual before/after diffs (graphics changes, e.g. the U2 fork shadows/post)

| Repo | What | Licence | Notes |
|---|---|---|---|
| **NVlabs/flip** https://github.com/NVlabs/flip | ꟻLIP: perceptual error map for rendered images, LDR and HDR, models flicker-viewing between two images | BSD-3-Clause (OK) | ★652, last push 2025-11. `pip install flip-evaluator`; C++/CUDA/Python/PyTorch. CPU ok. **Best fit for renderer A/B** — designed exactly for this. |
| **richzhang/PerceptualSimilarity** https://github.com/richzhang/PerceptualSimilarity | LPIPS learned perceptual distance + spatial map | BSD-2-Clause (OK) | ★4.3k, 2024. `pip install lpips`. CPU ok. |
| **dingkeyan93/DISTS** https://github.com/dingkeyan93/DISTS | DISTS structure+texture similarity (tolerates texture resampling) | MIT (OK) | ★489, 2020. CPU ok. Good for texture-upscale comparisons. |
| **scikit-image/scikit-image** https://github.com/scikit-image/scikit-image | `skimage.metrics.structural_similarity` (SSIM with `full=True` diff map), PSNR | BSD-3 (OK) | ★6.6k, active 2026. CPU. |

Caveat: repeatable A/B needs identical camera + frame (the U2 pilot harness / demo playback), otherwise animation
and particles dominate the diff.

## 10. Composition (rule of thirds, focal point, leading lines)

- **bcmi/Image-Composition-Assessment-Dataset-CADB** — https://github.com/bcmi/Image-Composition-Assessment-Dataset-CADB —
  ★176, active 2026-02, **MIT** (OK). CADB dataset + SAMP-Net (saliency-augmented multi-pattern pooling) composition
  score, predicts which composition pattern (thirds, centre, diagonal, symmetric, …) fits. PyTorch, CPU ok, weights via link.
  Trained on photos.
- No good open "leading lines" scorer found. DIY from parts: OpenCV `createLineSegmentDetector` / `HoughLinesP`
  → cluster lines → vanishing point(s) → check that dominant lines converge on the saliency peak / target.
- Rule-of-thirds DIY: saliency map (UNISAL/DeepGaze) → centroid and top-k peaks → distance to the four
  thirds intersections and to frame centre (FPS games are centre-weighted by the crosshair, so score both).

## 11. Squint/blur test, value structure, figure-ground

No dedicated repo needed — it is a recipe on OpenCV/scikit-image:
1. Convert to luminance (CIELAB L*), Gaussian blur at a sigma ~1-2% of image width (the squint), posterize to 3-5 value
   bands (k-means or fixed thresholds) → the "notan" / value-structure image.
2. Score: number and area of value masses, largest-mass share, and whether the brightest/darkest mass overlaps the
   saliency peak or the character mask.
3. Figure-ground: with a character mask (section 12), compute ΔL* and ΔE2000 between the masked figure and a dilated
   background ring, Weber/Michelson contrast, and AIM m5 figure-ground contrast for the whole frame.
4. Silhouette readability: fill the mask black on white, compute solidity, convexity defects, aspect, and
   compare silhouettes across poses (IoU / Hu moments) — an unreadable pose is one whose filled mask is a blob
   (high solidity, no limbs separated). Also check how much of the silhouette edge has low ΔL* against the
   background (fraction of "lost edges").

## 12. Segmentation to isolate characters (for silhouette / figure-ground)

| Repo | What | Licence | Notes |
|---|---|---|---|
| **danielgatis/rembg** https://github.com/danielgatis/rembg | Background removal; models u2net, isnet, BiRefNet, SAM via ONNX | MIT (OK); model weights have own licences (u2net Apache-2.0) | ★25k, active 2026-09. **CPU ok** (onnxruntime). Easiest one-liner for "the main subject". |
| **ZhengPeng7/BiRefNet** https://github.com/ZhengPeng7/BiRefNet | High-res dichotomous segmentation (crisp outlines) | MIT (OK) | ★4.3k, active 2026. GPU nice, CPU slow-ish. Best edges for silhouettes. |
| **facebookresearch/segment-anything** https://github.com/facebookresearch/segment-anything | SAM: promptable masks (point/box) or automatic all-masks | Apache-2.0 (OK) | ★55k, last push 2024. ViT-B fine on CPU (slow) / any GPU. |
| **facebookresearch/sam2** https://github.com/facebookresearch/sam2 | SAM 2: images + video mask tracking | Apache-2.0 (OK) | ★20k, active 2026. GPU. Track an enemy across a clip. |
| **ultralytics/ultralytics** https://github.com/ultralytics/ultralytics | YOLO detection/instance segmentation ("person" class finds Skaarj/marines decently) | AGPL-3.0 (OK for GPL) | ★62k, active. CPU ok. Gives the prompt boxes for SAM. |

Best for this project: since the engine is ours (fork/mutators), render an **ID/mask pass** of pawns from the game
itself (e.g. draw pawns flat-white in a second capture) — exact masks, no ML. Use rembg/SAM only for Advent Rising
or retail captures.

## 13. Game-specific: glitch detection and game screenshot QA

| Repo | What | Licence | Notes |
|---|---|---|---|
| **GlitchBench/Benchmark** https://github.com/GlitchBench/Benchmark | GlitchBench (CVPR 2024, Taesiri et al.): 593 glitch images from Reddit, evaluates whether VLMs can spot "what's unusual" | **NONE** | ★13, 2024. Eval code + HF dataset. Useful as a test set for any VLM-based checker. (GlitchBench/GlitchBench is an empty placeholder, ★0.) |
| **SandyyyZheng/GliDe** https://github.com/SandyyyZheng/GliDe | GliDe (ACM MM 2026): agentic LangGraph pipeline (scanner → analyzer w/ advocate/skeptic/judge debate → temporal grounder) for open-ended glitch detection in gameplay video; VideoGlitchBench dataset | MIT (OK) | ★3, active 2026-07. Calls cloud or local VLMs; needs a strong VLM. Architecture is a good template for our loop. |
| **asgaardlab/videogameqa-bench** https://github.com/asgaardlab/videogameqa-bench | VideoGameQA-Bench (Taesiri/Bezemer 2025): VLM tasks for game QA incl. visual unit tests, glitch detection, screenshot-vs-reference regression, UI checks | CC0-1.0 (OK) | ★0, 2025-12. Benchmark/data. |
| **asgaardlab/CLIPxGamePhysics** https://github.com/asgaardlab/CLIPxGamePhysics | CLIP zero-shot retrieval of gameplay videos by bug description (MSR 2022) | **NONE** | ★25, 2023. |
| **asgaardlab/LLMxBugs** https://github.com/asgaardlab/LLMxBugs | LLMs as zero-shot game bug detectors (text descriptions) | **NONE** | ★12, 2022. Text, not pixels. |
| **asgaardlab/canvas-visual-bugs-testbed** https://github.com/asgaardlab/canvas-visual-bugs-testbed | Visual testing framework injecting rendering bugs into PixiJS canvas apps (snapshot + oracle) | MIT (OK) | ★10, 2024. JS. Reference design for bug injection + detection evaluation. |
| asgaardlab/godot-glitch-injection, godot-tps-buggy, TempGlitch | 2026 repos: Godot games with injected glitches (benchmarks) | NONE / NOASSERTION / MIT | ★0, very new; content not inspected. |
| **PhysGame/PhysGame** https://github.com/PhysGame/PhysGame | Benchmark + model for physical-commonsense violations in gameplay videos | Apache-2.0 (OK) | ★49, 2025. Video-LLM, GPU. |
| **videogamebunny/VideoGameBunnyModel** https://github.com/videogamebunny/VideoGameBunnyModel | VideoGameBunny: LLaVA-style model fine-tuned on game screenshots (Taesiri 2024) | **NONE** | ★0, 2024. Weights on HF. GPU ~8-16 GB. |

Industry papers without public code (searched, none found on GitHub): EA SEED — García Ling, Tollmar & Gisslén,
"Using deep convolutional neural networks to detect rendered glitches in video games" (AIIDE 2020) — they trained
on synthetic injected glitches (stretched polygons, missing/low-res textures, placeholder textures, Z-fighting-like
stretches) and found classification works; Ubisoft La Forge and King have talks but no code. The EA method is
reproducible: inject the glitch types into our own UE2 captures (we control the renderer), train a small ResNet.

Cheap non-ML glitch heuristics worth writing ourselves (no repo needed):
- Missing texture / default material: detect large regions matching the engine's default texture (UE2
  "DefaultTexture" checker or bright magenta) via template matching / colour histogram.
- Black-character bug class: per-mask mean L* far below the scene average (we already hit this one).
- Stretched polygons: long thin high-contrast streaks → LSD line detector, lines spanning >40% of frame that are
  not in the reference.
- Z-fighting / flicker: capture 2-3 consecutive frames from a static camera, per-pixel temporal variance in
  areas with no motion → flicker map (FLIP between consecutive frames works well for this).
- Reference regression: same pilot camera, FLIP/LPIPS vs a golden image, threshold on the error map's 95th percentile.

## 14. VLM as heuristic judge (glue)

Most of the subjective checks (is the enemy readable, does the composition lead to the door) can also be asked of a
VLM given the computed maps as extra images (saliency overlay, value-structure image, clutter map). GliDe and
VideoGameQA-Bench show both the prompting patterns and the failure modes (VLMs miss subtle glitches, hallucinate
on dark frames). Treat numeric metrics as primary, VLM as tie-breaker/explainer.

## Suggested minimal stack (all permissive, all CPU-ok, offline)

opencv-contrib-python (spectral residual, LSD, blur/posterize) + UNISAL (saliency) + visual-clutter or AIM m7/m8
(clutter) + AIM m5/m15/m20 (figure-ground, colourfulness, harmony) + colour-science (ΔE, CVD) + inline WCAG formula
+ rembg or engine mask pass (silhouette) + FLIP + LPIPS + skimage SSIM (A/B) + piq (NR scores) +
improved-aesthetic-predictor (relative aesthetic delta). Add DeepGaze, pyiqa, UMSI, IC9600 only for private
analysis (NONE/NC licences).
