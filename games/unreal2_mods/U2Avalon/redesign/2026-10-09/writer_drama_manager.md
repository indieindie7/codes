# The Writer, evolved: the drama manager (2026-10-09)

The user's brief: "lets do the drama manager that makes a safety net on those small agents and lets have for important
characters bigger agents. lets evolve the writer".

Background: good characters act as if they're immersed in the setting, with their own goals and conditions. The writer
should not script them. It can either plan arcs and constrain the characters into a natural flow, or "do like Tolkien":
build the world and explore where it ends. The evolved writer does both. The world and its people run; the writer
manages the drama around them.

## What changed in the writer

| Before (the redesign's WRITER) | Now (WRITER / DRAMA MANAGER) |
|---|---|
| Writes the parti, the beats, the citizens' sheets (wants, fears, routines), prop lists, prose | Still owns all of that: it is the world bible the agents live in |
| Decides what happens | Never decides what a character does. Changes conditions (a postponed drop, a late truck, a lamp in the drain, a rumour in one mouth) so the beats happen naturally |
| The cube test's blind spot: "nobody in my desert does anything" | Each day, gives one or two drifting characters a private urge rooted in their own want: action, not mood |
| One voice for every character | Three tiers of agents (below); the writer reads them all and only steps in as the safety net |

## The three tiers (tools/storysim.py)

1. **Small agents:** the minor citizens and the groups (dock gang, Tin Row families, the night line...), 22 of the
   binder's 28. A fast local model (Gemma 4 12B on llama-server), many in parallel.
2. **Big agents:** the six the story turns on:

   | Character | Role |
   |---|---|
   | Hawkins | the Authority, the catwalk figure |
   | Rook | the smuggler, the drain |
   | Oduya | Authority comms |
   | Nkemelu | the checkpoint and the company trucks |
   | Okafor | the plant director, the company's power |
   | Marau | the Tin Row teacher, the town's voice |

   They run on a bigger reasoning role-play model that thinks about the character before it acts
   (Pantheon-Reasoning 26B-A4B), or on Claude (`big=claude`).
3. **The drama manager:** the writer, once per in-game day, on a frontier model (Claude CLI, opus). It reads the
   whole day.

## The safety net (two layers)
- **Every turn, deterministic and instant:** valid JSON, a known place, routine respected unless the agent gives a
  reason, a short line, no invented named people. A failed turn is asked once more at a lower temperature, then
  replaced by the routine and logged as "fallback".
- **Every day, by the drama manager:**
  - **Vetoes** turns that break a character, the world, or continuity. A veto is a retcon: the turn is erased from
    every memory.
  - **Keeps the beats, not a plot:**

    | Beat | By day | What happens |
    |---|---|---|
    | catwalk | 1 | Hawkins at 19:30 |
    | supply_drop | 2 | The supply drop is postponed again |
    | census | 2 | The 380 vs 470 census gap shows |
    | drain_lamp | 3 | Rook's lamp in the drain, and something goes wrong |

    Status per beat: done / on track / at risk. At most 3 world nudges a day.
  - **Rewrites each character's memory** to at most 6 honest notes.
  - **Notices story:** what emerged that the level and dialogue can use (relationships, grudges, secrets, habits).

## How to run it
- Start the two local servers (see `Documents\Tools\llm\README.md`).
- `py tools/storysim.py days=3`: output goes to `Documents\U2_research\storysim\<time>\`, with story.md, day_N.md,
  day_N_review.json, log.jsonl and memories.json.
- `backend=dry` tests the plumbing with no models. `big=claude` runs the big six on Claude instead of the local model.

## Rules that still hold
- No AI voices: this produces text only. Any line chosen for the game is spliced from stock recordings, or cut.
- Remade characters keep their stock gender (Hawkins is male).
- The marks checklist still beats everyone's taste.
