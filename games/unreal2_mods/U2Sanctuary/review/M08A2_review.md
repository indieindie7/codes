# Creative team review: M08A2

**Total 0.69** (geometric mean of the five; one weak role sinks it)

Counts: actors 1811, nav 124, lights 272, meshes 371, enemies 14, bodies 1, water 13, walk_s 103

| role | score | checks |
|---|---|---|
| writer | 0.75 | W1 evidence first 1.00, W2 bodies tell 1.00, W3 story spread 1.00, W4 gore serves 0.00 |
| director | 0.58 | D1 compression/release 0.25, D2 reveal 1.00, D3 palette 0.75, D4 darkness 0.33 |
| engineer | 0.48 | E1 water 0.00, E2 light sources 0.45, E3 dead ends 1.00 |
| level | 0.81 | L1 route 1.00, L2 pacing 1.00, L3 arenas 0.83, L4 recovery 0.67, L5 first encounter 0.54 |
| artist | 0.93 | A1 art fatigue 1.00, A2 texture variety 1.00, A3 hero details 0.80 |

## WRITER
- W1: 19 signs (bodies, blood, scares) before the first fight at 11 s
- W2: 1 of 1 bodies placed with a reason nearby (door, prop, weapon, another body)
- W3: 111 story beats on the walk, longest quiet 25 s (want <= 90)
- W4: 0 of 1 bodies have blood scripted near them

## DIRECTOR
- D1: 1 of 4 30-s windows go from dark to bright
- D2: the first enemy (U2Izarian) stands in light 127 vs the approach 95
- D3: 204 of 272 lights in the brief's families (white, rust/amber, red)
- D4: 12 % of the walk in low light (want 20-50)

## ENGINEER
- E1: 13 water volumes, 0 nav points in water; WaterVolume0 gravity default friction default; WaterVolume2 gravity default friction default; WaterVolume1 gravity default friction default
- E2: 150 of 272 lights have no fixture mesh within 160 UU
- E3: 0 dead-end nav points off the route

## LEVEL
- L1 (the game's ReachSpecs (M08A2_zones.log); 2 islands joined by guessed lifts/doors, 1 of them on the route)
- L1: route found, 103 s of walking over 41 nav points to M08B
- L2: 110 beats, longest gap 25 s (want <= 60)
- L3: 5 of 6 fights have cover and two ways in
- L4: 4 of 6 fights have health within 30 s after
- L5: 11 s of quiet before the first fight (want >= 20)

## ARTIST
- A1: the most used mesh (Mission_08M.Lights.TinyAssLight_1Yellow) is 11 % of 371 placed
- A2: 11 zones, median 11 textures each, 0 with one
- A3: 8 of 10 zones have a mesh found nowhere else

## Redesign proposals

- gore vignettes: 4 (pool 1, spray 1, smear 2, claw_marks 1)
- lights: 0
- cover: 1
  - 2 waist-high cover pieces 256-1024 UU out at [-5196.0, -4154.0, 881.0]: arena at 11 s has 1
