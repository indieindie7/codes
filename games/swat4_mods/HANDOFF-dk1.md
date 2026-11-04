# HANDOFF: Door Kickers 1 gym + SWAT 4 SwatMinds (2026-11-04)

## Index (read this only; open one section by line range)
1. State - what runs, last sweep (lines 12-17)
2. Paths and commands - paths, commands, preflight (lines 18-30)
3. DK1 results - sweep table, verdict (lines 31-40)
4. DK1 hook and brain facts (gotchas) - bridge, crashes, brain modes (lines 41-48)
5. DK1 what is left - tuning sweep, open questions (lines 49-54)
6. SWAT 4 SwatMinds state - flags, A/B numbers, build (lines 55-61)
7. SWAT 4 what is left - follow-ups (lines 62-67)

## 1 State
- DK1 gym works: dbghelp.dll proxy (`tools/dk1/dk1hook.c`) gives a file bridge into DoorKickers.exe; `dk1gym.py` runs headless-ish matches and writes one JSON line per match.
- Brain under test: `--brain swatminds` (`tools/dk1/squadbrain.py`), no-cheat zone HUNT (commit a755dc4). Baselines `--brain rush|pairs` are omniscient.
- Last sweep done: v4 HUNT, 2026-10-30. No tuning sweep has run since; `hunt_ticks` per-run logging was added after (eb430f3) but never exercised in a sweep.
- SWAT 4: SwatMinds A/B finished, flags stay off (commit 55d38a0). Nothing running.

## 2 Paths and commands
- Repo dir: `C:\Users\john\Documents\github\wt9\games\swat4_mods` (tools in `tools/dk1/`: dk1gym.py, dk1hook.c, dk1sym.py, dk1mods.py, squadbrain.py, build.bat, results/).
- Gym game copy: `C:\Games\DoorKickers` (env `DK1_GAME`, direct exe, `steam_appid.txt`). Original install `F:\SteamLibrary\steamapps\common\DoorKickers` (USB enclosure, dropped twice 10-29, do not use for sweeps).
- Bridge dir `<game>\dk1bridge\` (in.txt, out.txt, crash.txt). Mods list: `Documents\KillHouseGames\DoorKickers\options.xml`; `dk1mods.py on|off`.
- Install proxy: kill game, wait 6 s, `cmd /c <full path>\tools\dk1\build.bat` (relative path fails), copy `bin\dbghelp.dll` to the game dir, launch, `dk1gym.py launch`.
- Run: `dk1gym.py run N out.jsonl --brain idle|rush|pairs|swatminds --secs S --map L/I`.
- Sweep: `bash results/sweep.sh results/<out>.jsonl $(cat results/<cells>)` (90 s cap, one retry per cell).
- Symbols: `dk1sym.py fn|sig|type|xref|dis` on the shipped PDB.
- Before any sweep: Steam must be logged in (HKCU\Software\Valve\Steam\ActiveProcess ActiveUser != 0), else DK1 exits rc 1 ("SteamAPI_Init() failed"). Fix: `steam.exe -shutdown`, restart `-silent`.
- Bot mode (no focus steal) needs the focusguard `botlaunch/<exe>` marker (`dk1gym.mark_bot()`); never bring the window to front.
- Gates: heavy launches pass `~/.claude/hooks/hoggate.py status` first; DK1 gym is CPU-bound game sim, not GPU.
- Full detail: PORTS-HOOKS.md sections `## DK1 gym: ...` (grep `^## DK1`).

## 3 DK1 results
| run | brain | wins | mean win s | note |
|---|---|---|---|---|
| 10-24 map 0/0 | rush / pairs | 4/4, 1/1 | ~12 | map too easy |
| 10-27 sweep (maps 0/0..0/80) | rush / pairs / swatminds | 1/9, 1/9, 2/18 | | all wins on 0/0; 10 crashes (bridge timeouts) |
| 10-29 sweep v3 (57 rows) | swatminds omniscient push | 4/19 | 26.8 / 29.2 | rush 6/19 (19.3 s), pairs 5/19 (17.4 s) |
| 10-30 sweep v4 | swatminds zone HUNT, no cheat | 8/45 (18 %) | 53.0 | wins 0/0 x5, 0/50 x3; troopers alive 2.16 |
Verdict: HUNT costs ~no win rate vs omniscient push but takes ~2x longer; kept (AI must not cheat, memory feedback-ai-play-fair-director-balances). SwatMinds brain has never beaten rush/pairs on win rate.
Data: `tools/dk1/results/sweep_v4_hunt.ok.jsonl` (clean), `sweep_v3.jsonl`, `sweep_swatminds.jsonl`, `sweep_v2*.jsonl`.

## 4 DK1 hook and brain facts (gotchas)
- Bridge: `in.txt` "seq N" + commands, answer `out.txt` "seq N", lines, "END". Seq is ms. Commands: humans, state, load L I, setstate N, toggle N, pause/resume, move, goto, path, cmd, dbg, poke, restart, cgrid, chist, c2g, los, route, opendoors, maps.
- `load` straight from ENDING (11) crashes; `setstate 5`, wait 3 s, then load.
- `GeneratePath` hangs when the goal is in a wall/foreign region: `dk1gym.components()` drops such orders.
- "Crashes" are bridge timeouts (AV handler logs to crash.txt, process stays alive); map loads block the bridge 10-60 s; state 11 stale right after load is ignored for 4 s.
- Level XML has no wall data; walls come from `cgrid`, LOS from the game raycast `los`.
- Brain modes: CLEAR (paint 32 px grid, train follows leader), HUNT (zones, BFS from anchor, relay in 2 tiers, HUNT_HOPS=3), ENGAGE (contact within CONTACT_R=260; half the team holds as LOS shooters). Offline self-test: `py -3.13 -I tools/dk1/squadbrain.py`.

## 5 DK1 what is left
- Run a tuning sweep with `hunt_ticks` logging on the same 45 cells (`results/sweep_v4_hunt.cells`) and tune HUNT for speed (wins take 53 s vs 29 s), keeping the no-cheat rule. Accept a change only if win rate >= last accepted - 0.005 (falsifier rule from the JEPA note in PORTS-HOOKS "Parked: skill-jepa methods").
- Open question: why rush wins the fast-fail maps (0/10, 0/40) where swatminds loses.
- Workshop maps: 89 unpacked in `<game>\mods\ws<id>\` (92 downloaded to `F:\DK1Workshop`); the `dk1mods.py on` list was not swept; 2743310779 bad zip, 3494161399 no mod.xml.
- Port target (squad-ai-port-games memory): SwatMinds ideas into DK1 and FS2; FS2 is a separate gym (`fs2brain.py`, planAddOrder/WaitOrder blockers in PORTS-HOOKS).

## 6 SWAT 4 SwatMinds state
- Live source `F:\gogGames\SWAT 4\SwatMinds\Source\Game\SwatMinds\Classes\SwatMindsMutator.uc` (original saved as `.uc.bak-1029`), built to `System\SwatMinds.u` (UCC make in `BuildSystem`; `CompileSwatMinds.bat` did not rebuild on 10-29, run UCC by hand, copy .u to System). Repo copy `SwatMinds/Classes/SwatMindsMutator.uc`.
- Best suspect AI: bTwoMode + bAlerts (+ bPropagate for realism): about 2.6x stock officer losses on SP-JewelryHeist.
- New flags, all default off, A/B 36 games each (mean offDown / susDown / susFree): base 1.25/3.34/9.39, pincer 1.17/2.92/9.94, stances 0.92/3.58/9.20, alarm 1.25/3.17/9.78, curiosity 0.89/3.06/9.98. None improves on base. Stock suspects 0.39 offDown (10-26).
- Gym: `tools/swat4_gymrun.py` (`--rng-seeds`, `?SMSeed`, `-fixedfps=30`, NullRenderDevice, muted). Driver arms in session scratchpad only; results `F:\gogGames\SWAT 4\SwatMinds\gym_1029\<arm>`. Noise about +-0.17 offDown per arm at 36 games.
- Caveat: auto-officers barely clear JewelryHeist, hostages almost never secured; gym only measures suspect lethality.

## 7 SWAT 4 what is left
- Stances: need a map-marker source for HOLD (not a random roll).
- Curiosity: lower range or noise scaling (0.15 / 800 cut officer losses, likely too noisy).
- Pincer: untested with a smarter holder-engaged signal; current one is `GetCurrentState() >= 2` within 1500 uu.
- Do not start new gyms without a user go-ahead (user stopped them twice on 10-29).
