# Robot-learning methods for the SwatMinds gym (10-19)

Source: Strata research.py (8 sources, run "robot-gym" in Tools/llm/research/runs), 2 spot-checked against the abstracts.

## Findings
- **Domain randomization** (Frontiers Robotics&AI 2022 review, doi 10.3389/frobt.2022.799893): randomize sim parameters, observations, actions, delays, noise; acts as regularizer so the policy does not overfit sim quirks; more sim accuracy alone does not close the gap.
- **Curriculum** (Narvekar et al., arXiv 2003.04960): sequence tasks easy -> hard so things too hard to learn from scratch become learnable. SPOT-CHECK: the abstract does NOT say it cuts costly interaction (Strata overclaimed); it ties that to transfer learning.
- **Self-play / populations** (arXiv 2408.01072 survey): train against past/concurrent versions; league of opponents avoids cycling.
- **Reward shaping** (arXiv 2408.10215): potential-based shaping keeps the optimum; risk = reward hacking.
- **Sim-to-real**: DR, adaptation, imitation, distillation (arXiv 2009.13303).
- **Distilling into rules** (arXiv 2603.13257): fuzzy IF-THEN distillation 81 % fidelity vs trees ~60 % on Lunar Lander (not re-checked).
- **Knob search**: CMA-ES is a derivative-free alternative to grid/random/Bayesian search and "friendly to parallel evaluations" (arXiv 1604.07269, SPOT-CHECK confirmed). BO suits expensive objectives (arXiv 2508.13121, game testing).

## What to do in SwatMinds
1. Fast loop (gym_v0): randomize layout every generation (room size, door pos/width, pillars), train both sides by alternating CMA-ES (self-play, suspect vs league of fixed styles + current trained officer). Done: `gym_v0.py --train`.
2. Hold out fresh rooms to measure transfer; never report train fitness.
3. Slow loop (engine): only 4 hot knobs, 3 parallel games per candidate = natural CMA-ES/(1+lambda) batch. Score is noisy (n=3, level time 60-150 s): use random start, then mutate best; re-evaluate the best before trusting it. Done: `swat4_gymrun.py --search`.
4. Reward: keep the sparse outcome score (arrests + hostSecured - 2 offDown - susFree); add a shaped term only if noise blocks search (e.g. suspects downed early, orders issued) and always report the raw score.
5. Curriculum for the engine: shorten to the first room (stop at first tally of hostSecured) before full-level runs; add suspects count later.
6. Sim-to-real: check the python gym's officer knobs against engine habit logs; if python ranking of weights disagrees with engine A/B, fix the gym first.
7. Final brain stays rules: weights ship as config (SwatMinds.ini), no net to distill.
