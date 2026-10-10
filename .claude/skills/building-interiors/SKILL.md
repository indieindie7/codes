---
name: building-interiors
description: Real-world proportions and layout rules for designing building interiors and facades in games (rooms, doors, corridors, stairs, windows, which rooms connect to which), measured from 8,000 real floor plans (ResPlan) plus rules from building practice (Neufert-style dimensions, Blondel's stair rule, Alexander's pattern language, Lynch, shape grammars). Use when laying out or generating houses, apartments, offices, towns or facades for a level (U2Avalon, U2Prairie, Blender or T3D generators), or when checking that a building looks plausible.
---

# Building interiors

For making game buildings that read as real: sizes from real plans, connection patterns from real
plans, and the rules architects use. Converts to Unreal units at the repo's scale (1 m = 50 uu).

## How to use it

1. **Pick sizes from the measurements, not from memory.**
   [reference/resplan-measurements.md](reference/resplan-measurements.md) has p10 / median / p90 per
   room type: area, narrow side, proportions, windows. Draw from the p25 to p75 range for normal rooms,
   and use p10 or p90 for a deliberately cramped or grand one. The raw numbers are in
   `reference/resplan_stats.json`.
2. **Connect rooms the way real plans do:**
   - the entrance opens into the common room (living or hall);
   - bedrooms and the kitchen open off the common room;
   - about 3 kitchens in 4 are open to it (no wall);
   - about 60% of bathrooms are en-suite (reached only from a bedroom);
   - balconies are reached from bedrooms or the living room;
   - bedrooms sit next to each other behind walls, not through doors.
3. **Order by privacy** (intimacy gradient): public near the entrance, private deep.
4. **Check human-scale dimensions** against [reference/rules.md](reference/rules.md): doors,
   corridors, stairs, ceilings, windows, daylight depth.
5. **Scale for the game:** real sizes feel tight on screen. Choose an enlargement (often 1.2 to 1.5
   times, doors most) after measuring the player pawn and stock doorways (rules.md, "Game scale").
6. **For facades and blocks,** use the shape-grammar steps (mass → floors → bays → elements) and
   Lynch's five elements for a town (rules.md).

## Know the limits

- **One region:** ResPlan is South Asian apartment listings. Its many bathrooms, en-suites and
  bedroom balconies are regional. Other places differ, and this skill has no measured data for
  them; say so when it matters.
- **No hall class:** halls and corridors are inside "living", so corridor widths come from the
  rules, not the data.
- **Single floors:** no heights, no furniture, no multi-storey circulation.
- **Approximate rules:** the rules are generalisations that vary by building code. Never present
  them as engineering or code compliance.

## Re-measuring

`tools/analyse.py` (with `tools/load.py`, a pickle loader that accepts only the three classes the
data needs) recomputes everything:
1. Clone github.com/m-agour/ResPlan and unzip `ResPlan.zip`.
2. Run `python3 -I tools/analyse.py ResPlan.pkl split.json out.json` (needs shapely).
3. Then rebuild the tables.

Each plan's scale comes from its listed net area, checked against its own doors (median 0.7 to
1.05 m, or the plan is dropped). Connections are this repo's own geometry tests, not the
dataset's graph code.

## Credit

The measurements are statistics derived from **ResPlan** (github.com/m-agour/ResPlan,
arXiv:2508.14006), licensed CC BY 4.0. Keep this credit wherever the numbers are reused. No plan
geometry is included here.
