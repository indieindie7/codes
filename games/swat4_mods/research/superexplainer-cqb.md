# TheSuperExplainer CQB shorts → SwatMinds rules

Source: youtube.com/@TheSuperExplainer/shorts. The user shared it on 2026-10-18 for its room-clearing tips. There are 8 shorts of about 40 s each, transcribed with faster-whisper small.en on the CPU because captions returned HTTP 429. Each short follows the same pattern: the naive move, then the obvious fix, then why that fix also fails, then the real answer. Most tips are about **defending** a room, which suits our suspects; the rest are about **attacking**, which suits officers and the player.

| id | title | naive / obvious-fix trap | answer |
|---|---|---|---|
| 5I6B_SCJeIM | Never Hide Behind This Wall | crouch behind thin drywall by the door | hold the door from hard cover (concrete pillar); the attacker sprays drywall, then walks in to check |
| DJcBPobxn9w | Never Peek Like This | peek one at a time / both through same gap | split to two gaps, swing at the same instant; defender gets one rushed shot |
| GiKkcUV4eow | Never Hold A Door Like This | stand facing the door / hide beside it (first corner checked) | far corner, off-axis of the door: attacker must fully enter and turn |
| 2N6MZxPoGVs | Never re-peek like this | re-swing the same corner; waiting makes him steadier | move low to the other end of the cover, swing wide; his aim is parked on the old corner |
| geMx6jOIKsI | Never Defend Stairs Like This | top step (grenade lands there) / around a corner (blind) | far wall in line with the stairs, aim at the top step; climbers show their head first |
| 8oyXrVGPUy8 | Never Cross The Hallway Like This | cross one after another / together | one kneels at the corner covering the threat doorway while the other crosses |
| IlFUhLO_7jM | Don't Team Up Like This | both in the back corner (one grenade) / ambusher beside the door | split: one back corner facing the door, one at far end of the door wall; the attacker can't face both |
| tA0-60mZWBc | Don't Go Through The Doorway Like This | stop in the doorway to scan / peek from the hall (corners unseen) | don't stop: one step through, turn straight to the blind corner, slide along the wall |

## Principles (engine-neutral)
1. **Fatal funnel.** The doorway is where every defender aims, so never stand in it. In the Ruskin comms rules (l4d-ai-talk.md) this becomes a fact: `in_funnel` scores as danger.
2. **The first corner checked loses.** The spot right beside the door is cleared first, at point-blank range.
3. **Make the attacker turn.** The best defender spot is off the door's axis and deep in the room: invisible from outside, and the attacker needs about 90° of turn after entering. That turn time is the defender's edge.
4. **Hard cover beats concealment.** Drywall blocks sight, not bullets. Prefer pillars and concrete.
5. **Aim memory.** A defender's aim stays parked where the enemy was last seen. Reappearing somewhere new costs them reaction time, so re-peeking the same spot is the error.
6. **Split angles.** Two guns from two directions force the enemy to pick one and turn their back on the other. Two guns in one spot is one target, and one grenade gets both.
7. **Stairs and elevation.** Hold back from the top step, in line with the stairs, aimed at head height on the top step.
8. **Overwatch instead of a second runner.** One gun covers the threat doorway while the other crosses.

## For us (SwatMinds)
- **Suspect barricade pick (main use).** When suspects hear officers (they already have HearRange 3000) or go barricaded, score the room's nav points:
  - plus for distance from the door and angle off the door axis (principle 3);
  - plus for hard-cover material, using the SWAT 4 material type on the trace hit (principle 4);
  - minus for the point right beside the door frame (principle 2);
  - minus for the door line itself (principle 1).

  With two or more suspects in one room, the second suspect must take a point at least about 60° away from the first, as seen from the door (principle 6). Hook point: the stock `BarricadedAction` / `TakeCover` goals choose cover points; replace their scoring with ours.
- **Stair defenders:** prefer a point in line with the top step, set back, never on the landing (principle 7). The stock flashbang lands on the landing, so this beats our own grenades fairly.
- **Re-peek memory:** a suspect who traded shots and missed moves to the other end of its cover before peeking again. This is a small timer plus a cover-point swap (principle 5).
- **Officer side (later, step 6 of the build order):** use overwatch-while-crossing (8), dual-gap simultaneous entry (6), and no stopping in the doorway (step in, turn to the blind corner).
- **Fairness:** these tips make suspects harder in ways a player can learn, because the same principles let the player counter them. Pair them with clear audio tells such as "heard" barks and shuffling, so a deep-corner suspect is fair rather than a cheap kill. That matches design-unreal-encounters: build-up, then reveal, then a fight that teaches.
- **Next step:** add a "room-hold" scoring rule after suspect comms v1. Test it in a pilot or user run: officers' first-entry deaths should go up only modestly, and suspects should no longer die beside the door frame.
