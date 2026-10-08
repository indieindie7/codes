# Level designer: combat arenas and enemy AI, M08A2

**Arenas 0.67** (mean of 6 fights); pacing 0.80, teach 0.50, variety 1.00

| # | at | line-up | weight | score | cover | ways in | blocked | range | checks |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 11 s | U2Izarian x4 | 4 | 0.54 | 1 | 3 | 0 % | 938 | cover 0.3 entries 1.0 sightlines 0.0 range 1.0 reveal 1.0 arrival 0.0 height 0.0 recovery 1.0 |
| 2 | 22 s | U2Izarian x5 | 5 | 0.70 | 5 | 3 | 6 % | 654 | cover 1.0 entries 1.0 sightlines 0.1 range 1.0 reveal 0.5 arrival 0.0 height 1.0 recovery 1.0 |
| 3 | 28 s | U2Izarian x1 | 1 | 0.86 | 29 | 3 | 50 % | 769 | cover 1.0 entries 1.0 sightlines 1.0 range 1.0 reveal 0.0 height 1.0 recovery 1.0 |
| 4 | 33 s | U2Izarian x4 | 4 | 0.57 | 21 | 4 | 62 % | 339 | cover 1.0 entries 1.0 sightlines 1.0 range 1.0 reveal 0.0 height 0.0 recovery 0.0 |
| 5 | 71 s | U2SkaarjLight x1 | 2 | 0.76 | 3 | 4 | 19 % | 853 | cover 1.0 entries 1.0 sightlines 0.3 range 1.0 reveal 0.0 height 1.0 recovery 1.0 |
| 6 | 92 s | U2SkaarjLight x2, U2Izarian x1 | 5 | 0.57 | 30 | 3 | 69 % | 505 | cover 1.0 entries 1.0 sightlines 1.0 range 1.0 reveal 0.0 height 0.0 recovery 0.0 |

**Pacing** (fight weight along the walk): 4 5 1 4 2 5

**First meetings**: U2Izarian at fight 1 (4 of it, alone); U2SkaarjLight at fight 5 (1 of it, alone)

## Enemy AI design

| class | role | weapon | health | speed | close / stationary / tactical | mobility | cover | signature | score |
|---|---|---|---|---|---|---|---|---|---|
| U2Izarian | shooter | weaponInvEnergyRifle | 100 | 450 | 0.14 / 0.57 / 0.29 | 0.29 | 1.00 | - | 0.71 |
| U2SkaarjLight | rusher | claws + ProjectileSkaarjLight (projectile) | 150 | 450 | 1.00 / 0.00 / 0.00 | 0.92 | 1.00 | leaps, dodges shots, taunts, an acquisition roar | 0.90 |
- **U2Izarian**: no signature move: nothing for the player to learn and remember (Unreal recipe)
