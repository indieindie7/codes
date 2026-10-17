# "AI-driven Dynamic Dialog through Fuzzy Pattern Matching" (GDC talk notes)

- Speaker: Elan Ruskin (Valve). Channel: GDC Festival of Gaming. Length: 58:02. URL: youtube.com/watch?v=tAbBID3N64A.
- Transcript source: whisper (small), because captions returned HTTP 429. Timestamps below are approximate (+-1 min).

**Important mismatch.** The requested topic was "Left 4 Dead AI". This video is the Valve contextual-dialogue talk, not the Director / bot / special-infected talk. It uses Left 4 Dead 2 only as its example material. The Director appears in one passage (about 16:30-18:30), described only as the thing that throws different situations, characters and enemies at you each run. Nothing here covers intensity tracking, build-up/peak/relax, bot covering or helping, special-infected tactics or navigation flow. Those would need a different talk (the Left 4 Dead AI systems talk by Michael Booth is the usual source). This file records what the talk does give us and maps it to SwatMinds.

## Techniques in the talk

1. **World state as a flat fact list (13:00-15:30).** Every query pulls all state into one key/value dictionary: speaker, concept ("I'm hit", "reloading"), the speaker's stats, nearby allies, map, and memory the writers stored. Hundreds of facts per query. Reason: a designer can write a new rule without asking a programmer to expose new data.
2. **Rules and best match (15:30-17:00).** A rule is a list of criteria (predicates on facts). All must pass. Among passing rules, the one with the most criteria wins (most specific); ties are random. A criterion naming a missing fact fails. Per-criterion weights were possible but never needed (~51:30).
3. **Responses (17:00).** A response is a payload: random pick among variants, sequences, or a whole script (turn, point, animate) bound to the query facts (~52:30).
4. **Write-back memory (9:00-10:30, 17:00).** A rule can write facts to the character or the world after firing (seen-count, "line already said", "someone is speaking") with optional expiry. This gives running gags, escalation and anti-spam.
5. **Follow-up chains (7:30-8:30, 17:00-19:00).** A line triggers a new query on another character, or a "who nearby has a reply" query. The best-scoring character answers. Each hop re-queries the live world, so a conversation dies by itself when a threat appears (no scripted lock-in). Long speeches are cut into short pieces for the same reason.
6. **Fallback to the general case (18:00).** Specific rules beat general ones, but general rules cover new characters with no extra authoring.
7. **Event-driven barks.** Characters poll the field of view every few seconds (9:30-11:00), plus idle-talk checks and event barks. AI teammates call out items and threats the same way human players do (~20:00).
8. **Transient facts need hysteresis (~53:30).** Store "time since last shot" instead of "is shooting this frame".
9. **Performance (40:00-46:00).** Partition rules by speaker/concept/map, sort by criteria count so the first match wins, and encode every test as an interval so it runs as one comparison. About 12-24 rules per bucket across 10,000 rules; ~100 ns per bucket. Do not use spatial indexes.
10. **Debug tools (~39:30).** Trace where a fact came from, list matching rules with scores, inspect "what would this entity's context be now", hot-reload.
11. **Pacing and emotion.** Mostly implicit. Characters react to state and to each other, so tone follows the situation. The Director passage (16:30) says varied runs are why canned lines cannot work.

## For SwatMinds (SWAT 4)

Our mod gives suspects fear/anger/stress/nerve emotions that change attack/cover/flee/regroup choices. Next planned step is officers that cover the player (see breach-cover-ai.md section 3). The talk is about dialogue, but the matching engine fits our decision layer.

| Talk technique | Use in SwatMinds |
|---|---|
| Flat fact dictionary (1) | Build one query struct per AI tick: emotion floats (fear, anger, stress, nerve), ammo, health, allies alive, distance to player, line-of-sight, last-shot-at time, breach state. Hive and Tyrion read the same dictionary, which is discoverable and easy to log. |
| Most-specific-rule-wins (2) | Replace hand-tuned weights in the section 3 utility scores with a rule table: general "flee when nerve low", overridden by "hold if cornered and has hostage". Rules are data, so tuning does not need recompiling UnrealScript. |
| Response variants and scripts (3) | Randomised action/bark pairs: same rule picks cover-left or cover-right, with the matching callout. Variety without duplicate rules. |
| Write-back memory (4) | Suspect memory facts: "heard breach", "saw teammate die", "was flashbanged", with expiry. These drive emotion decay and regroup. Officer memory: "player reloaded at T", "door X unwatched". Cooldowns for callouts (section 3.2) come free via expiry. |
| Follow-up and any-query (5, 6) | Officer callout chain: officer A says "Contact left", ask nearby officers who has the best reply ("Covering"). Best score answers; ties random. Re-query after each hop, so a chain breaks when the player moves into the line of fire. Same for suspect bark pairs. |
| Hysteresis facts (8) | Use "time since" facts (shot, seen player, damaged) so rules do not flicker per tick, important for UE2 tick order and cover-switch jitter. |
| Perf partitioning (9) | Bucket rules by role (officer/suspect) and concept (cover, flee, callout). UE2 script is slow, so bucket early and evaluate highest-criteria rules first. Keep rule counts to a few hundred. |
| Debug tools (10) | Add a console command that prints the winning rule and runner-ups for a pawn. This is our fastest way to tune emotions. |
| Pacing (11) | The Director idea in section 3.4 is not covered by this talk. Treat player stress as another fact in the dictionary, and write ambush/aggression rules that read it. |

Suggested build order addition to section 3.5: step 0, a rule-table evaluator with a trace command, then move claim-board, never-block and callout logic into it.

## Gaps
- No Director, bot or special-infected content. A second source is needed for those.
- Talk gives no numbers for emotion or stress, only the matching framework.
