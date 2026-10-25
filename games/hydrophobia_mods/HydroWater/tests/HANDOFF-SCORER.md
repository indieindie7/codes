# HydroWater IRL scorer: handoff to the local models (2026-10-23)

Purpose: let the local models (Coder on 127.0.0.1:8091, Strata on 8090) improve the solver's
match to measured water without a Claude chat in the loop. Claude only adds references and
reads the ops report.

## What is measured
`tests/score_irl.py` runs the shipped solver defaults (alpha 1.0, c_adapt 0.2, edge_damp 0.7,
cfl 0.5, recon on; `bin/hydrowater.dll`, rebuilt by `build.ps1`) through each reference in
`tests/irl_refs.json` and prints as its LAST line

    VERDICT {"gain": <score_now - baseline>, "rows": <measurements>, "score": <0..1>}

- Reference row = `{name, source, metric, mean, band_lo, band_hi, ...metric fields}`.
- Metric `front_speed`: dry-bed dam break, column 20 cells long, front speed v/sqrt(gH) by
  least squares over `t_window` (t* = t*sqrt(g/H)), one measurement per `columns` x
  `wet_thresholds` entry. The only reference so far: Lobovsky et al. 2014 Table 1, mean 1.47,
  band 1.14-1.74 (24 rows; the ops approval rule needs >= 20 rows).
- Row score = clip(1 - |x - mean| / half_band, 0, 1); score = mean over rows.
- Baseline `tests/irl_baseline.json` (score 0.8199 on 10-23). Rewritten only by
  `score_irl.py --write-baseline` after an approved round, or on first run when missing.

Command (about 1 min, CPU only, cwd = HydroWater/):

    "C:/Users/john/Documents/Tools/kimodo/venv/Scripts/python.exe" tests/score_irl.py [--json] [--write-baseline]

## One round
1. `py -3.13 tests/propose.py [--dry] [--model coder|strata]` sends Coder the doc section
   "IRL reference: lab dam break", the defaults, the last 5 verdicts
   (`Tools/llm/autorun/logs/idea*.verdict.json`) and the solver lines around the knobs, and asks
   for ONE change (a default value or <= 30 changed lines) to `src/hydrowater.c|.h` only.
2. The reply's ```diff block is checked (allowed files, size, `git apply --check`) and saved as
   `tests/proposals/<date>.patch` with `.prompt.txt`, `.reply.txt` and `.test.json`.
3. `.test.json` is an autorun step list: backup solver files -> `git apply` -> `build.ps1` ->
   postcheck `score_irl.py` (min_rows 20; gain <= 0 restores the backups) -> rebuild.
   Without `--dry` it is queued: `ideas.py add "hydro scorer: <title>" quality Hydrophobia ...`.
4. opsd runs it when the machine is free; gain > 0 -> APPROVED (patch stays, run
   `score_irl.py --write-baseline` in the rollout), else the solver is reverted.
   `tests/write_verdict.py <id> <score log>` turns the VERDICT line into
   `logs/idea<id>.verdict.json` if a queue needs it explicitly.

## Protected (Goodhart guard)
`tests/score_irl.py`, `tests/irl_refs.json`, `tests/irl_baseline.json` are the target: no
proposal may touch them (propose.py refuses patches outside src/), and the ops edit-guard
list in the hooks folder blocks edits by chats. The target moves only when a human adds a
reference row from a published table.

## Adding a reference
One JSON row in `irl_refs.json`. For a new metric, add a branch in `score_all()` and say in
the row's `source` where the numbers come from (paper, table, page). Candidates: Lobovsky
H1-H4 gauge depths (plots, need digitising), Martin & Moyce 1952 Z-T, Koshizuka 1996 front.

## Reading results
`Tools/llm/autorun/REPORT.md` (or `idea<id>_REPORT.md`), `ops/ideas.log`, `ideas.py list`.
A stop of `reverted` = tried, no gain. `partial` = scorer printed too few rows.
