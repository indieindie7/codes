# ResPlan measurements

From 8,061 residential plans (South Asian apartment listings) whose scale passed the door check (3,037 more dropped for a bad listed area). p10 / p50 / p90 = 10th percentile / median / 90th. Unreal units at 1 m = 50 uu (the repo's U2Blender scale).

Data: ResPlan (github.com/m-agour/ResPlan, arXiv:2508.14006), CC BY 4.0. These are statistics derived from it, with changes as described in resplan_stats.json `_source`.

## Rooms

| Room | n | Area m² p10 / p50 / p90 | Narrow side m p10 / p50 / p90 | Long:short p50 | Rect. fill p50 | Has a window | Window width m p50 | Steps from entrance (mean) |
|---|---|---|---|---|---|---|---|---|
| Living (incl. hall/corridor) | 8,222 | 20.39 / 33.45 / 52.35 | 4.61 / 6.56 / 8.75 | 1.33 | 0.56 | 75% | 1.56 | 0.02 |
| Bedroom | 21,493 | 10.93 / 14.62 / 19.92 | 3.08 / 3.54 / 4.23 | 1.2 | 1.0 | 82% | 1.37 | 1.01 |
| Bathroom / WC | 20,589 | 2.6 / 3.85 / 5.71 | 1.25 / 1.57 / 1.94 | 1.59 | 1.0 | 92% | 0.64 | 1.63 |
| Kitchen | 8,044 | 5.32 / 8.21 / 12.2 | 1.93 / 2.56 / 3.27 | 1.3 | 0.97 | 92% | 1.09 | 1.0 |
| Storage | 1,075 | 1.23 / 2.66 / 7.52 | 0.91 / 1.38 / 2.44 | 1.33 | 1.0 | 41% | 0.88 | 1.06 |
| Stair (in-unit) | 360 | 0.93 / 3.18 / 9.12 | 0.78 / 1.61 / 2.83 | 1.57 | 0.96 | 28% | 0.69 | 1.08 |
| Balcony | 11,653 | 2.23 / 4.33 / 9.13 | 0.91 / 1.42 / 2.19 | 2.29 | 1.0 | 50% | 1.16 | 1.64 |

Rect. fill: room area / its tightest bounding rectangle (1 = a plain rectangle; living areas are L-shaped because halls and corridors are part of them in this data).

In Unreal units (median narrow side × 50): bedroom ~177 uu wide, bathroom ~78, kitchen ~128, living ~328.

## Openings and walls

- Door width (all doors) p10 / p50 / p90: 0.74 / 0.86 / 0.99 m (~43 uu at the median).
- Wall thickness p10 / p50 / p90: 0.18 / 0.21 / 0.24 m (normalised per plan in the source: partitions and outer walls aren't told apart).

## Which rooms connect

**Through a door** (count of room pairs):

- bedroom – living: 20,471
- bathroom – bedroom: 12,696
- balcony – bedroom: 7,937
- bathroom – living: 7,315
- balcony – living: 4,014
- kitchen – living: 1,899
- living – storage: 435
- bedroom – kitchen: 84

**Open, no wall between (open plan)** (count of room pairs):

- kitchen – living: 6,085
- living – storage: 531
- bathroom – bedroom: 280
- living – stair: 184
- bathroom – living: 91
- bedroom – living: 81

**Side by side behind a wall (no opening)** (count of room pairs):

- bathroom – bedroom: 9,362
- bathroom – living: 6,864
- bedroom – bedroom: 5,543
- bedroom – kitchen: 4,188
- balcony – bathroom: 3,554
- balcony – bedroom: 3,387
- bathroom – bathroom: 3,202
- bathroom – kitchen: 3,119

- The front door opens into the living area in 100.0% of plans (halls count as living here).
- 62% of bathrooms are reached only from a bedroom (en-suite).

## Unit size by bedrooms

| Bedrooms | Plans | Net area m² p10 / p50 / p90 | Bathrooms (median) | Rooms (median) |
|---|---|---|---|---|
| 1 | 287 | 37.14 / 46.28 / 94.63 | 2 | 6 |
| 2 | 3,120 | 54.92 / 71.71 / 93.35 | 2.0 | 7.0 |
| 3 | 3,862 | 77.49 / 101.93 / 134.25 | 3.0 | 9.0 |
| 4 | 588 | 104.77 / 140.69 / 190.52 | 4.0 | 12.0 |
| 5 | 196 | 132.95 / 171.27 / 239.23 | 5.0 | 15.0 |

## How to read it (limits)

- One region (South Asia): many bathrooms, most of them en-suite, nearly all with windows, balconies off bedrooms. Other regions differ (the dataset's own authors show room-labelling models trained on it fail on Chinese and Swiss plans); this skill has no measured numbers for them.
- No corridor class: halls are inside 'living', so 'steps from entrance' is about one step for nearly everything; the real signal is that bathrooms and balconies sit deeper (often behind a bedroom) than kitchens.
- Single floor, no furniture, no heights. Listings (6.9% near-duplicates in the source).
- Connections are computed by this repo's script (door between two rooms; rooms touching with no wall = open), not the dataset's own graph code.
