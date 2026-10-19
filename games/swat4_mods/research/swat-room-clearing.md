# How SWAT teams clear rooms and cover each other → AutoOfficers rules (2026-10-19)

> **User (10-19):** "also lets research how swat teams clear rooms and cover each other"

Source: Strata research run `Documents/Tools/llm/research/runs/swat-cqb-doctrine` (28 steps, 16 sources, 36 notes; report.md there). Spot-checked by Claude: ufpro.com ITCQB article (fatal funnel 45-135°, angles 45/90/150/180) and police1.com slicing-vs-buttonhook (first and third officers "may" have cleared 75%+ before entry, hedged) both say what the report claims. Report claims with **no source** (treat as common knowledge, not cited): T-intersection/stair cover, the call words ("Clear", "Coming in", "Moving"), contact man / cover man roles.

## Doctrine in short
| topic | what teams do | src |
|---|---|---|
| Stack | stack at the door, knock/announce, breach, enter | police1 dynamic-vs-deliberate |
| Deep vs shallow | in a 4-stack, #1 and #2 go deep (dominate), #3 and #4 go shallow (cover threshold + near corners) | specialtactics.me limited penetration |
| Dynamic entry | surprise + speed + domination; used when surprise is lost or time is critical; less time in the funnel, but risk of open-ground fights | police1, highthreatcover |
| Deliberate / limited penetration | default; clear from outside or just past the threshold, never commit; stay a few metres back from the door; doorway as concealment | specialtactics.me, highthreatcover |
| Slice the pie | clear the room from outside in angle steps (45/90/150/180°), a foot or two off the wall, muzzle not past the frame | ufpro, dailyshooting |
| Buttonhook | wrap tight round the jamb; faster, more exposed if not pre-cleared | police1 |
| Fatal funnel | 45-135° in front of the door; don't stop in it | ufpro |
| Domination | pair enters, takes opposing corners, overlapping sectors; center-fed rooms have hard corners not clearable from the threshold | police1, highthreatcover |
| Flashbang | when noncombatants are likely or for surprise; incapacitate for capture | wikipedia M84, police1 |
| Compliant suspect | contact man cuffs, cover man keeps the gun on him and the room (unsourced) | — |

## Mapping to SwatMinds AutoOfficers
Already in (bScoreDoors, 10-19): intel behind a door → flash entry (BangAndClear / BreachBangAndClear); no intel → MoveAndClear / BreachAndClear. Matches "flash when threat/noncombatants likely, quiet when nothing known".

Next rules, in build order:
1. **Contact + cover on secure.** When ordering a secure, also give a second officer a cover order (SWAT 4 squad "Cover" / fall-in near the target) so one officer is never cuffing alone. Measure: offDown during secures.
2. **Deliberate by default, dynamic when contact.** No intel + door already open → mirror/peek first (MirrorRoom or Mirror under door, if the squad command works for AI giver) before MoveAndClear. Intel fresh (< 10 s, gunfire/seen) → dynamic BangAndClear immediately, no mirror.
3. **Don't idle in the funnel.** After a clear completes, if an officer stands within ~150 uu of the door axis inside 45-135°, order a small move off-axis (FallIn or MoveTo a stack point). Measure: officers hit while standing in doorways (log hit position vs door).
4. **Hall / stair overwatch.** When the team stacks on a door and a corridor or stairs is in view of the stack (LOS from stack point, > 800 uu long), send one officer of the other element to Cover it instead of joining the stack (red/blue split). Unsourced in the run; keep as a design rule, test with the gym.
5. **Calls.** Officer barks already exist in stock lines (no TTS, no new voices): pair rule 3/4 moves with the stock "moving"/"covering" lines if present; clear calls are played by the game.
6. **Center-fed rooms.** If the door is mid-wall (door within 30% of the room centre line), prefer Bang entry even without intel: hard corners can't be seen from the threshold. Needs room geometry; later, from the gym's real-map export.

## Ties to the suspect side (gym)
The doctrine attacker in gym v0 already encodes rules 2-3 (no stop, near corners first); the gym's sloppy/rusher styles are what these rules prevent. Officer rule success should show as lower suspect win-rate in gym v1 and lower offDown in the in-game tally.
