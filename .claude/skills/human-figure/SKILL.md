---
name: human-figure
description: Human body proportions and figure rules for concept art and procedural characters, measured from 6,068 real adults (ANSUR II) plus the classical and drawing canons (Polykleitos, Vitruvius, Dürer, Richer, Loomis), what attractiveness research does and doesn't support, and concept-art rules (silhouette, shape language, exaggeration budget, crowds). Use when drawing or generating characters or NPC bodies, setting proportions for a cast, checking a figure looks plausible, or choosing how stylised a body should be.
---

# Human figure

For figures that read as real people, or that depart from real on purpose. The numbers come from measured
bodies, not memory.

## How to use it

1. **Start from the measured figure.** [reference/proportions.md](reference/proportions.md) has:
   - landmark heights as fractions of stature and in head heights;
   - widths, segments and p5 to p95 ranges;
   - how each measure scales with height (allometry).

   Raw percentiles are in `reference/ansur_stats.json`.
2. **Pick a canon on purpose.** [reference/canons.md](reference/canons.md):
   - real adults are 7.4 heads;
   - 7.5 is the drawing-book average, 8 is "ideal" (the measured p95), 8.5 to 9 is heroic.

   It also covers children and ageing.
3. **Treat beauty as evidence, not folklore.** [reference/beauty.md](reference/beauty.md) says what is strong
   (averageness), what is small (symmetry) and what is contested (waist-to-hip 0.7). It also explains why a
   believable cast is mostly ordinary.
4. **Design the cast.** [reference/concept-art.md](reference/concept-art.md):
   - whole shape first;
   - silhouette per group;
   - shape language;
   - push 1 or 2 traits;
   - vary height and build separately;
   - posture before the model.
5. **Generate bodies by sampling real people, not by scaling a template.** Blend a few similar ANSUR records,
   then scale for the game. This keeps every correlation: tall people are leggy and small-headed, and breadth
   follows build, not height.
6. **Convert to game scale last.** In this repo's Unreal 2 work, 1 m = 50 UU. The building work here used a 1.25
   game scale for the 108 UU player, which makes a median man 110 UU tall: check the player pawn first.

## Know the limits

- **One population:** US Army personnel, ages 17 to 58, fitter and more muscular than average. No children,
  no older people, no other populations. Children and ageing in canons.md are approximate artist guides, not
  measurements.
- **Standing, unclothed or lightly clothed.** No measures of posture, movement or clothing bulk.
- **Approximate canons.** The canon figures are as commonly cited; sources differ.
- **Narrow research.** The beauty research is mostly Western student raters rating photos; treat it as
  tendencies.
- **No faces.** Head and face measures are coarse (breadth, length, a few arcs).

## Re-measuring

`tools/ansur_stats.py` recomputes everything from the two public CSVs.
- Get `ANSUR II MALE Public.csv` and `ANSUR II FEMALE Public.csv`. The official host is the US Army's Defense
  Centers for Public Health; a mirror is github.com/senihberkay/US-Army-ANSUR-II.
- Run `python3 -I tools/ansur_stats.py <dir> reference/ansur_stats.json`.
- Units: millimetres, except `weightkg`, which is in tenths of a kilogram.

## Credit

The measurements come from **ANSUR II** (Gordon et al. 2014, "2012 Anthropometric Survey of U.S. Army
Personnel", NATICK/TR-15/007). The US Army cleared the working databases for unlimited public release. Only
statistics are kept here, with no individual records.
