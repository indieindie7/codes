# Friday 2026-10-23: what to test (SwatMinds AI + ports)

User, 2026-10-21: "friday we will also make so we can train our ideas in the other 2 tactical games frozen synapse and door kickers"
User, 2026-10-22: "compile all of what we are thinking on testing friday. its this missing, the ai plays paintball ideas and later when ai gets good the constrain ai skils to be fun aka human level capability skill , almost like the atv pack racing idea."

Order: **make it good first, then make it fun.** Phases 1-3 push skill up; phase 4 only starts once the AI clears its maps reliably.
Where things come from: NOTES.md sections "Idea notes (parked 10-20)", "10-20 c", "10-21 ROE review", "10-21 eve: bubble"; skill video-notes tree/159 (paintball), tree/201 (cross-entropy); memory squad-ai-port-games.

## 0. Carry-over checks (morning, cheap)
- Bubble escort (commit 14f91f9) playtest: does the squad spread out, restrain, bag evidence, and drop jobs when a threat shows? Read the `SwatMinds bubble` log lines. Also test on a gym map: bubble on vs. train, comparing offDown, clears and arrests.
- Gym state: REPORT.md best ComplyWait per map; first `CURRICULUM unlocked` yet? (675 games 10-21, 0 promotions.)

## 1. Training in Frozen Synapse 2 + Door Kickers 1 (the new part)
Goal: the same "idea -> knob -> gym test -> verdict" loop as SWAT 4 (autogym + ideas.py), in two more games.
- Recon first (nothing known yet, all unverified): how each game can be driven headless/fast. Look for:
  - mod/script hooks (DK1 XML/Lua mod folder; FS2 data files);
  - a way to start a mission from the command line and read the result (win/lose, units lost, time);
  - a speed-up or turn-based fast path (both are turn/pause based, so they may be easier to batch than SWAT 4).
  Fallback: a small Python sim of the game's rules on its maps (grid + LOS + doors) to train in, then check the trained knobs in the real game.
- Port the squad logic as engine-neutral rules (it is written up in NOTES, not tied to UnrealScript): coverage paint / dead-space aim, bubble jobs (guard / secure / evidence), comply-wait ROE, curriculum + KL map order.
- Done for Friday = in each game, one scripted/baseline AI mission runs unattended and logs a result line the autogym can score.

## 2. AI Plays Paintball lessons (b2studios, tree/159)
- **Hard rules beat penalty terms.** Keep turning score penalties into rules (ComplyWait hold, OrderTimeout, cooldowns). Audit the score `-2*offDown` etc. for things the search can game.
- **Watch for reward hacks.** For example, suspects counted "free" because of a timeout, or officers idling safely to avoid losses. Spot-check top-scoring games by hand.
- **Curriculum.** Easy maps first, unlock at a 0.8 clear rate (built 10-20); "assist that fades" = start with a stronger squad or weaker suspects and lower the assist as the clear rate rises (not built).
- **Policy library + simple selector.** Separate small behaviours (entry, hold, escort bubble, secure) picked by a simple rule rather than one do-everything brain.
- **Mass + physics = fun more than clever tactics** (matters for phase 4).

## 3. Missing perception pieces (from the 10-20 idea notes + 10-22 chat)
- **Noise-refresh vision rays.** Each tick, a blue-noise subset of rays in the view cone (dense fovea, sparse periphery), accumulated over ticks, gives a natural "takes a moment to take in a room".
- **Surfel knowledge map per side** (officers share one; suspects share one per group). Surfels decay over time and record kind: wall / clutter / door / pawn.
- **Floor-plan prior knob:** none / walls only / full map. Furniture is unknown until seen.
- **Exposure field.** Stale or unknown frontier next to openings = where an enemy may come from; officers cover the highest-exposure directions nobody is watching (generalises paint + dead-space aim).
- **Human-like perception:**
  - the periphery sees only motion ("something there"); the fovea identifies;
  - attention budget of 3-5 targets, one focus (a gunshot outranks footsteps);
  - reaction time grows with angle off the view direction, clutter, darkness and surprise (~200-300 ms base);
  - last-known position that fades instead of true position.
- Test in the gym: prior none / walls / full vs paint share, time-to-face, offDown, clears. The director keeps its god view as the probe.

## 4. Later, once the AI is good: constrain it to human level for fun ("ATV pack racing")
Idea: like a MotorStorm-style ATV pack, the AI should stay around the player's level and make readable, well-timed mistakes, not win at all costs. Like ranked matchmaking, but without visible rubber-banding.
- **Skill estimate of the player** from steady signals (clear rate, officers lost, time-to-face, accuracy over recent missions), not single outcomes.
- **Director** sets suspect (and squad) skill, reaction delay and accuracy so the result lands in a target band (e.g. 60-75 % clear). The gym's objective changes from "max clears" to "hit the band", with some easy and some hard runs mixed in so improvement is still felt.
- **Constraint layers** (the same knobs as phase 3, turned down): reaction-time floor, aim wobble/overcorrection, attention budget, memory fade, stress (worse under fire).
- **Staged, readable mistakes:**
  - a fumbled reload, flinch, hesitation or wrong-door check, with a bark or visible head turn;
  - placed where the player can see them;
  - some independent of the player's situation, so it never reads as charity.
- **No physics cheating.** Never speed/accuracy boosts the player can feel; only perception/decision limits.
- Test: human playtests (the user) rate fun/fairness per mission, plus a bot proxy: the autoplay player at 2-3 skill levels should each land near the target band.

## Measures (all phases)
clear (susFree 0 and offDown 0), offDown/game, arrests/game, kills vs arrests, time-to-face, paint share. Ideas with a test go in `ideas.py add` so opsd runs them and logs a verdict.
