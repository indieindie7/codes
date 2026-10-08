# Creative team review: M08B

**Total 0.77** (geometric mean of the five; one weak role sinks it)

Counts: actors 2333, nav 382, lights 240, meshes 617, enemies 29, bodies 8, water 2, walk_s 67

| role | score | checks |
|---|---|---|
| writer | 0.72 | W1 evidence first 1.00, W2 bodies tell 0.88, W3 story spread 1.00, W4 gore serves 0.00 |
| director | 0.55 | D1 compression/release 0.67, D2 reveal 0.00, D3 palette 0.55, D4 darkness 1.00 |
| engineer | 0.86 | E1 water 1.00, E2 light sources 0.57, E3 dead ends 1.00 |
| level | 0.83 | L1 route 1.00, L2 pacing 1.00, L3 arenas 0.60, L4 recovery 0.80, L5 first encounter 0.73 |
| artist | 0.93 | A1 art fatigue 1.00, A2 texture variety 0.90, A3 hero details 0.89 |

## WRITER
- W1: 10 signs (bodies, blood, scares) before the first fight at 15 s
- W2: 7 of 8 bodies placed with a reason nearby (door, prop, weapon, another body)
- W3: 52 story beats on the walk, longest quiet 15 s (want <= 90)
- W4: 0 of 8 bodies have blood scripted near them

## DIRECTOR
- D1: 2 of 3 30-s windows go from dark to bright
- D2: the first enemy (U2SkaarjLight) stands in light 0 vs the approach 0
- D3: 132 of 240 lights in the brief's families (white, rust/amber, red)
- D4: 47 % of the walk in low light (want 20-50)

## ENGINEER
- E1: 2 water volumes, 10 nav points in water; WaterVolume0 gravity default friction default; WaterVolume2 gravity default friction default
- E2: 104 of 240 lights have no fixture mesh within 160 UU
- E3: 0 dead-end nav points off the route

## LEVEL
- L1 (the game's ReachSpecs (M08B_zones.log); 8 islands joined by guessed lifts/doors, 0 of them on the route)
- L1: route found, 67 s of walking over 39 nav points to PD_Sanctuary
- L2: 62 beats, longest gap 14 s (want <= 60)
- L3: 3 of 5 fights have cover and two ways in
- L4: 4 of 5 fights have health within 30 s after
- L5: 15 s of quiet before the first fight (want >= 20)

## ARTIST
- A1: the most used mesh (Mission_08M.Lights.Light_1) is 5 % of 617 placed
- A2: 10 zones, median 6 textures each, 1 with one
- A3: 8 of 9 zones have a mesh found nowhere else

## Redesign proposals

- gore vignettes: 11 (pool 8, spray 8, drag_trail 4, smear 2, claw_marks 1)
- lights: 1
  - a low warm key light on the first enemy's spot at [-3236.0, 4272.0, -128.0]: the reveal: lit creature, dark approach (Unreal 1 Skaarj)
- cover: 2
  - 1 waist-high cover pieces 256-1024 UU out at [-1492.0, -1143.0, -274.0]: arena at 38 s has 2
  - 3 waist-high cover pieces 256-1024 UU out at [653.0, -2617.0, -115.0]: arena at 46 s has 0
