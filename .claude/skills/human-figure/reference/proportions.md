# Measured proportions (ANSUR II)

Source: ANSUR II, the 2012 US Army anthropometric survey (4,082 men, 1,986 women, ages 17 to 58, median 28),
public release. Statistics only; recompute with `tools/ansur_stats.py`. Full numbers (p5, p10, p25, p50, p75,
p90, p95 for 43 measures and 12 ratios) are in `ansur_stats.json`.

**Who this is:** fit adults in service, measured standing straight in light clothing. Not children, not people
over 60, and somewhat leaner and more muscular than a general population (BMI is high because of muscle). For
other populations, see "Know the limits" in SKILL.md.

## The figure in head heights

Head height = chin to crown, derived (see the tool's docstring). Median adult: **7.4 heads** (p5 6.9, p95 8.1)
for men and **7.3** (6.8 to 7.9) for women. Drawing books use 7.5 for "average" and 8 for "ideal" (canons.md).
An 8-head figure is real but rare: about the 95th percentile.

Heights above the floor, median, as a fraction of stature and in heads:

| landmark | ANSUR measure | men, mm | of stature | heads | women, mm | of stature | heads |
|---|---|---|---|---|---|---|---|
| crown | stature | 1755 | 1.000 | 7.43 | 1626 | 1.000 | 7.33 |
| eyes | stature - (sitting height - eye height sitting) | 1640 | 0.935 | 6.95 | 1517 | 0.933 | 6.84 |
| neck base (C7) | cervicale height | 1517 | 0.864 | 6.41 | 1393 | 0.857 | 6.29 |
| shoulder point | acromial height | 1439 | 0.821 | 6.09 | 1332 | 0.820 | 6.01 |
| top of breastbone | suprasternale height | 1437 | 0.819 | 6.08 | 1326 | 0.817 | 5.99 |
| nipple line | chest height | 1289 | 0.735 | 5.46 | 1169 | 0.719 | 5.28 |
| navel | waist height (omphalion) | 1055 | 0.602 | 4.46 | 978 | 0.602 | 4.42 |
| hip bone top | iliocristale height | 1061 | 0.604 | 4.49 | 993 | 0.611 | 4.48 |
| hip joint (approx.) | trochanterion height | 899 | 0.512 | 3.81 | 844 | 0.519 | 3.80 |
| crotch | crotch height | 845 | 0.481 | 3.57 | 780 | 0.480 | 3.52 |
| wrist (arm hanging) | wrist height | 847 | 0.482 | 3.58 | 794 | 0.487 | 3.58 |
| knee joint | lateral femoral epicondyle height | 491 | 0.280 | 2.08 | 465 | 0.286 | 2.10 |
| ankle | lateral malleolus height | 73 | 0.042 | 0.31 | 63 | 0.039 | 0.28 |

What artists say, checked:
- **"The crotch is the halfway point":** no. The crotch is at 0.48; the halfway point is the hip joint
  (trochanter, 0.51).
- **"The wrist hangs at the crotch":** yes. Both are at 0.48.
- **"Arm span = height":** close. Span is 1.03 for men and 1.02 for women (p5 0.99, p95 1.08).
- **"The navel is at 3 heads from the top":** close. It is 2.97 heads for men and 2.91 for women.
- **"Women are not just smaller men":** stature 0.93, but hip breadth 1.03 and shoulder breadth 0.88 of men's.

## Widths, in heads (median)

| | men | women |
|---|---|---|
| shoulders, outside the deltoids (bideltoid) | 2.16 | 2.02 |
| shoulders, bone to bone (biacromial) | 1.76 | 1.64 |
| chest breadth | 1.22 | 1.21 |
| waist breadth | 1.38 | 1.34 |
| hip breadth (standing) | 1.46 | 1.59 |
| head breadth | 0.65 | 0.67 |

Shoulder-to-hip breadth (bideltoid / hip): men 1.48 (p5 1.37, p95 1.60), women 1.27 (1.16 to 1.40). That is
the most reliable sex difference in the silhouette. Waist-to-hip circumference: men 0.92, women 0.84 (p5 0.75).

## Segments (median, mm)

| | men | women | of stature |
|---|---|---|---|
| upper arm (acromion to radiale) | 335 | 311 | 0.19 |
| forearm (radiale to stylion) | 267 | 240 | 0.15 |
| hand | 193 | 180 | 0.11 |
| foot | 271 | 246 | 0.15 |
| sitting height (seat to crown) | 918 | 857 | 0.52 |

Hand = 0.82 heads and foot = 1.15 heads (the old rule "hand = face, foot = forearm" is about right).

## Variation: what to vary, and what goes with what

- **Range.** Stature p5 to p95 is 1648-1870 mm for men and 1525-1740 for women, about ±6.5%. Mass varies much
  more: 64-111 kg for men and 51-87 for women.
- **Allometry.** The log-log slope of each measure against stature (1 = grows in proportion):
  - Legs grow faster than stature: crotch height 1.21, knee 1.23. Tall people are leggy.
  - The trunk grows slower: sitting height 0.78.
  - The head barely grows: head height 0.50, head breadth 0.07. **Tall people have smaller heads for their
    size, so they are more heads tall.** A 1.87 m man is about 7.7 heads; a 1.65 m man about 7.2.
  - Breadths follow mass more than stature: shoulders 0.51-0.63, waist 0.68, hips 0.69.
  - Hands and feet are 0.9. Ankles are 0.9.
- **Correlation with stature:**
  - Leg and arm lengths are strongly tied to stature (r 0.8 to 0.9).
  - Breadths and circumferences are only loosely tied to it (r 0.2 to 0.4): they go with build, not height.
  - A generator should sample **height and build separately**, and lengths from height.
- **Easiest correct method.** Sample real people (or blend a few similar ones) instead of scaling one template.
  All the correlations come for free.
