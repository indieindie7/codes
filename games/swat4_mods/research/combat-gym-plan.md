# Combat-AI gym + live adaptation plan (2026-10-19)

> **User (10-19):** "we will try doing some more dynamic ai study, one goal should be to create like a gym for training our combat ai to do goals by themselves and make so that it can be deployed during player gameplay and adapt to player or learn from player mistakes"

## Constraint that shapes everything
SWAT 4 (UE2.5) runs in real time, has no headless server for SP, and its officers only act on player orders; the pilot still cannot drive the menu. So **the game itself cannot be the training loop**. One mission = minutes, we need ~10^4-10^5 episodes.

So: **train fast outside, deploy small inside, adapt live inside.**

## Three layers
1. **Gym (Python, fast, offline).** A top-down 2D CQB sim (`tools/cqbgym/`): rooms, doors, cover (hard vs soft), line of sight by raycast, a turn-rate + reaction-time duel model (the thing CQB tips are about: whoever must turn more, or who re-appears where aim is parked, loses). Suspects pick *goals* (hold room, flee, call help, ambush, comply) and *spots*; attackers are scripted entry bots built from doctrine (research/breach-cover-ai.md, superexplainer-cqb.md) with **knobs that model player habits**: stop-in-doorway chance, which corner first, re-peek tendency, flash use, entry speed.
   - Rooms come from real SWAT maps later (export nav points / BSP from the SDK maps); v0 uses generated rooms.
   - Training: start with cross-entropy method / evolution over a **small feature-weight policy** (the same shape as SwatMinds `Score()`), because that deploys 1:1 into UnrealScript. A small net (or the TRM-style recurrent brain from goobi-rpg-future-ideas) only if CEM plateaus, then distil it back to weights / a decision table.
2. **Deploy (UnrealScript, SwatMinds).** The trained weights ship as `SwatMinds.ini` config values; the mutator's scorers (room-hold spot pick first, then goal pick) read them. No ML runtime in the game.
3. **Live adaptation (UnrealScript + ini persistence).** While the player plays:
   - **Player model:** the mutator logs the same habit knobs the gym uses (did the player stop in the doorway? which corner did they clear first? did they re-peek? flash before entry?). Running averages persist with `SaveConfig()` between missions.
   - **Tactic bandit:** per room type, Thompson-sampling over a few suspect tactics (deep off-axis hold, split angles, ambush-beside-door, flee + call help). Reward = officer hit / suspect survives longer; penalty = suspect downed without a shot. Persisted the same way.
   - **Learn from player mistakes:** when the player is hit or downed, log the situation (habit flags at that moment). Tactics that exploited a habit get weight; repeating the same mistake makes the exploiting tactic more likely *next* time, not instantly.
   - **Offline loop:** the habit averages feed back into the gym as the attacker knobs, so overnight retraining (autorun queue) produces weights tuned against *this* player.
   - **Fairness director (must have):** cap suspect win-rate (target the player clearing ~70-80% of rooms without a hit), keep audio tells (comms v1 lines, "heard" barks) so every adapted tactic is readable and counterable. Adapt toward *teaching*, not punishing (design-unreal-encounters).

## Build order
1. **gym v0**: one room, one door, one suspect, one entering officer; suspect chooses a hold spot from features (distance from door, angle off door axis, hard cover, beside-frame, in-door-line). CEM trains the 5 weights. Check that it rediscovers the CQB tips (deep off-axis corner wins) — that is the gym's sanity test.
2. Port the weights into a SwatMinds room-hold scorer (the next step already planned in superexplainer-cqb.md).
3. Habit logger in the mutator (`SwatMinds habit ...` log lines) + parser.
4. Multi-suspect (split angles), goals beyond holding, stairs.
5. Bandit + SaveConfig persistence, fairness director.
6. Real-map rooms in the gym; overnight retrain via autorun with the player's habit file.

## Measures
- Gym: suspect duel win-rate vs each attacker style; learned weights' signs match the tips.
- Game: from Swat4.log, officer-hits-per-room and suspects-dying-beside-door-frame before/after; player habit flags trending (are they learning too?).

## Gym v0 results (10-19, tools/cqbgym/gym_v0.py, weights_v0.json; 150 train + 50 test rooms x 4 seeds, ~9 s table + CEM)
Suspect win-rate on held-out rooms (1 = officer downed, 0.4 = nobody fell):

| attacker style | learned | hand CQB tips [1,1,.5,-1,-1] | random spot | door-facing |
|---|---|---|---|---|
| doctrine | 0.45 | 0.47 | 0.16 | 0.02 |
| sloppy (stops in door) | 0.97 | 0.67 | 0.24 | 0.03 |
| rusher | 0.99 | 0.67 | 0.21 | 0.00 |
| mixed | 0.80 | 0.60 | 0.20 | 0.01 |

- **off_axis is the top weight for every style**: the gym rediscovered "make the attacker turn" by itself (sanity test passed).
- **Weights differ by attacker habit** = the adaptation hook: vs the doorway-stopper the best hold is *shallow* (depth -1.0: punish the pause close up); vs doctrine/rusher it is *deep* (depth +0.5/+0.7). Live, the habit logger picks which weight set (or blends by the player's measured stop rate).
- Doctrine attacker is the hard case (0.45, learned ≈ hand tips): it is the good-player ceiling.
- Known model artefacts to fix in v1: hard_cover comes out negative (pillars sit mid-room, so "near cover" correlates with "in the open middle"; needs real cover-edge geometry + peeking); rusher too easy (its middle-first scan is exploited); suspects have perfect door knowledge (no hearing/surprise yet); no flashbangs.
- Next: v1 = cover edges, flash/stinger before entry, two suspects (split angles); then port the `mixed` weights to a SwatMinds room-hold scorer and add the habit logger.
