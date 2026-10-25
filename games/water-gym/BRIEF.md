# Water gym: recreate filmed water in Bevy, scored automatically

## Index
1. Goal (l8-12): video in, Bevy water out, score up each round.
2. Why (l14-18): the HydroWater lesson, one build per look is too slow.
3. Loop (l20-30): capture, simulate, render, score, tune.
4. Scorers (l32-42): pixel/flow metrics, CLIP/VLM look score, physics checks.
5. Starting assets (l44-52): HydroWater solver, reference videos, local models.
6. First milestone (l54-58): one clip, one scene, score curve.

## 1. Goal
A new Bevy 0.20 project (own repo or `Documents\github\commercial`) that takes a short video of real or game water (swimmer wake, waterfall into a pool, breaking wave, splash) and recreates it in real time at high fps. An automatic scorer compares the render to the clip; a tuner changes the sim and render parameters and keeps what scores higher. Parameters, not hand-tweaking, drive the look.

## 2. Why
HydroWater (games/hydrophobia_mods/HydroWater, done and published 2026-10-25) was tuned by playing the game after each build: about one look per hour, judged by eye. User 10-25: "make something similar to the ai gyms but in this case for realistic approximation scoring" and "get a video, try to recreate with high fps the water and get increasingly higher scores there".

## 3. Loop
1. Clip in: `Documents\Tools\whisper\vidgrab.py` or a local file; cut 3-10 s, fixed camera; store frames + optical flow (OpenCV Farneback or RAFT).
2. Scene: a matching blockout (pool, wall, inflow) in Bevy; camera matched by hand once (FOV, position), stored in a scene file.
3. Sim: start from the HydroWater C library (shallow water + foam + spray, `src/hydrowater.c`, GPL-3.0) behind a Rust FFI, or a Rust port; later SPH/FLIP where shallow water fails (waterfalls, splashes).
4. Render: headless Bevy, same frame count and size as the clip, write PNGs.
5. Score (section 4), log a row per run (params, scores) to a CSV.
6. Tune: random search, then CMA-ES or Optuna over the parameter vector; best set saved as the scene's preset. Runs queue through `Documents/Tools/llm/autorun/autorun.py` overnight, models stopped after.

## 4. Scorers
- Motion: optical-flow histogram distance clip vs render (direction and speed of the surface), wake angle, front speed.
- Look: SigLIP/CLIP embedding similarity per frame and over time; a local VLM (Qwen3-VL on the free GPU, see skill local-gpu-ai) rubric 1-10 for wake, spray, foam; LPIPS when the camera matches well.
- Physics sanity: volume kept, Kelvin wake 19.5 deg, drop ballistics, foam decay 2-5 s; fail = score 0.
- Human: the user A/B picks now and then, used to fit the weights of the above.
Weights start equal; the loop only needs the ordering to be right.

## 5. Starting assets
- HydroWater solver + harness (`games/hydrophobia_mods/HydroWater/src`, `tests/harness.py`): shallow water with HLL, reconstruction, foam, spray, APIC landing; milestone tests with PNGs.
- Reference clips already listed: games/hydrophobia-water-upgrade.md idea 25 (swimming refs youtu.be/m3BsRGK9RSQ, hi3SlJwvVUo), the 10-25 test recordings in `C:\Users\john\Videos\2026-10-25 16-2*.mp4` (game water, for a first same-source test).
- Skills: avalon-bevy (Bevy 0.20 setup, PS1 look is optional here), game-fluid-sim, local-gpu-ai, video-grab, mm-search.
- Rules: Bevy only (no Unreal/Unity), everything launched hidden, local models off when idle, GPU 0 free while the user games.

## 6. First milestone
One clip (the 16-24-45 swim recording, 5 s), a flat pool scene, shallow water + wake stamp, headless renders, flow + CLIP score, 50 random parameter sets, a score curve PNG. If the curve rises and the best render looks better to the user than the first, the gym works; then add SPH for splashes and real-footage clips.
