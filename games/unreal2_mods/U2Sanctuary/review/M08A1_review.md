# Creative team review: M08A1

**Total 0.73** (geometric mean of the five; one weak role sinks it)

Counts: actors 2302, nav 140, lights 267, meshes 680, enemies 36, bodies 12, water 5, walk_s 93

| role | score | checks |
|---|---|---|
| writer | 0.83 | W1 evidence first 1.00, W2 bodies tell 1.00, W3 story spread 1.00, W4 gore serves 0.33 |
| director | 0.61 | D1 compression/release 0.50, D2 reveal 0.50, D3 palette 0.90, D4 darkness 0.55 |
| engineer | 0.56 | E1 water 0.00, E2 light sources 0.67, E3 dead ends 1.00 |
| level | 0.76 | L1 route 1.00, L2 pacing 1.00, L3 arenas 0.62, L4 recovery 0.88, L5 first encounter 0.32 |
| artist | 0.96 | A1 art fatigue 1.00, A2 texture variety 1.00, A3 hero details 0.87 |

## WRITER
- W1: 4 signs (bodies, blood, scares) before the first fight at 6 s
- W2: 12 of 12 bodies placed with a reason nearby (door, prop, weapon, another body)
- W3: 145 story beats on the walk, longest quiet 7 s (want <= 90)
- W4: 4 of 12 bodies have blood scripted near them

## DIRECTOR
- D1: 2 of 4 30-s windows go from dark to bright
- D2: the first enemy (U2Izarian) stands in light 274 vs the approach 282
- D3: 239 of 267 lights in the brief's families (white, rust/amber, red)
- D4: 19 % of the walk in low light (want 20-50)

## ENGINEER
- E1: 5 water volumes, 0 nav points in water; WaterVolume0 gravity default friction default; WaterVolume1 gravity default friction default; WaterVolume3 gravity default friction default
- E2: 87 of 267 lights have no fixture mesh within 160 UU
- E3: 0 dead-end nav points off the route

## LEVEL
- L1 (the game's ReachSpecs (M08A1_zones.log); 2 islands joined by guessed lifts/doors, 1 of them on the route)
- L1: route found, 93 s of walking over 57 nav points to M08a2
- L2: 100 beats, longest gap 14 s (want <= 60)
- L3: 5 of 8 fights have cover and two ways in
- L4: 7 of 8 fights have health within 30 s after
- L5: 6 s of quiet before the first fight (want >= 20)

## ARTIST
- A1: the most used mesh (Mission_08M.M08AX.Service6e) is 10 % of 680 placed
- A2: 15 zones, median 8 textures each, 0 with one
- A3: 13 of 15 zones have a mesh found nowhere else

## Redesign proposals

- gore vignettes: 14 (pool 11, spray 11, drag_trail 5, smear 2, claw_marks 1)
- lights: 1
  - a low warm key light on the first enemy's spot at [-1566.0, 4423.0, 6491.0]: the reveal: lit creature, dark approach (Unreal 1 Skaarj)
- cover: 2
  - 3 waist-high cover pieces 256-1024 UU out at [792.0, -9504.0, 6689.0]: arena at 72 s has 0
  - 3 waist-high cover pieces 256-1024 UU out at [4240.0, -11458.0, 6689.0]: arena at 88 s has 0
