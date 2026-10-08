# Level designer: combat arenas and enemy AI, M08A1

**Arenas 0.67** (mean of 6 fights); pacing 0.70, teach 0.00, variety 1.00

| # | at | line-up | weight | score | cover | ways in | blocked | range | checks |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 s | U2Izarian x3 | 3 | 0.72 | 23 | 1 | 81 % | 444 | cover 1.0 entries 0.5 sightlines 0.5 range 1.0 reveal 1.0 height 0.0 recovery 1.0 |
| 2 | 23 s | U2Izarian x15 | 15 | 0.75 | 12 | 4 | 69 % | 282 | cover 1.0 entries 1.0 sightlines 1.0 range 1.0 reveal 0.0 arrival 0.0 height 1.0 recovery 1.0 |
| 3 | 51 s | U2Izarian x1 | 1 | 0.76 | 25 | 1 | 94 % | 303 | cover 1.0 entries 0.5 sightlines 0.3 range 1.0 reveal 0.5 height 1.0 recovery 1.0 |
| 4 | 63 s | U2Izarian x2 | 2 | 0.94 | 8 | 2 | 56 % | 233 | cover 1.0 entries 1.0 sightlines 1.0 range 0.6 reveal 1.0 height 1.0 recovery 1.0 |
| 5 | 72 s | U2Izarian x4 | 4 | 0.50 | 0 | 2 | 0 % | 800 | cover 0.0 entries 1.0 sightlines 0.0 range 1.0 reveal 0.0 arrival 0.0 height 1.0 recovery 1.0 |
| 6 | 88 s | U2Izarian x3 | 3 | 0.38 | 0 | 3 | 0 % | 843 | cover 0.0 entries 1.0 sightlines 0.0 range 1.0 reveal 0.0 arrival 0.0 height 1.0 recovery 0.0 |

**Pacing** (fight weight along the walk): 3 15 1 2 4 3

**First meetings**: U2Izarian at fight 1 (3 of it, alone)

## Enemy AI design

| class | role | weapon | health | speed | close / stationary / tactical | mobility | cover | signature | score |
|---|---|---|---|---|---|---|---|---|---|
| U2Izarian | shooter | weaponInvEnergyRifle | 100 | 450 | 0.14 / 0.57 / 0.29 | 0.29 | 1.00 | - | 0.71 |
- **U2Izarian**: no signature move: nothing for the player to learn and remember (Unreal recipe)
