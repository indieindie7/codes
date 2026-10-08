# Level designer: combat arenas and enemy AI, M08B

**Arenas 0.71** (mean of 5 fights); pacing 0.64, teach 0.88, variety 1.00

| # | at | line-up | weight | score | cover | ways in | blocked | range | checks |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 15 s | U2SkaarjLight x1 | 2 | 0.71 | 7 | 3 | 19 % | 167 | cover 1.0 entries 1.0 sightlines 0.3 range 0.6 reveal 0.0 height 1.0 recovery 1.0 |
| 2 | 38 s | U2SkaarjLight x1 | 2 | 0.81 | 2 | 4 | 0 % | 924 | cover 0.7 entries 1.0 sightlines 0.0 range 1.0 reveal 1.0 height 1.0 recovery 1.0 |
| 3 | 46 s | U2SkaarjMedium x1 | 3 | 0.46 | 0 | 3 | 12 % | 432 | cover 0.0 entries 1.0 sightlines 0.2 range 1.0 reveal 0.0 height 0.0 recovery 1.0 |
| 4 | 57 s | U2Izarian x1 | 1 | 0.90 | 21 | 2 | 100 % | 435 | cover 1.0 entries 1.0 sightlines 0.2 range 1.0 reveal 1.0 arrival 1.0 height 1.0 recovery 1.0 |
| 5 | 63 s | U2SkaarjHeavy x1, U2Izarian x1 | 6 | 0.66 | 18 | 3 | 44 % | 125 | cover 1.0 entries 1.0 sightlines 1.0 range 0.6 reveal 0.0 height 1.0 recovery 0.0 |

**Pacing** (fight weight along the walk): 2 2 3 1 6

**First meetings**: U2SkaarjLight at fight 1 (1 of it, alone); U2SkaarjMedium at fight 3 (1 of it, alone); U2Izarian at fight 4 (1 of it, alone); U2SkaarjHeavy at fight 5 (1 of it, mixed)

## Enemy AI design

| class | role | weapon | health | speed | close / stationary / tactical | mobility | cover | signature | score |
|---|---|---|---|---|---|---|---|---|---|
| U2Izarian | shooter | weaponInvEnergyRifle | 100 | 450 | 0.14 / 0.57 / 0.29 | 0.29 | 1.00 | - | 0.71 |
| U2SkaarjHeavy | tank | claws + seeking glove shots (projectile) | 600 | 130 | 0.54 / 0.45 / 0.00 | 0.00 | 1.00 | taunts, an acquisition roar | 0.75 |
| U2SkaarjLight | rusher | claws + ProjectileSkaarjLight (projectile) | 150 | 450 | 1.00 / 0.00 / 0.00 | 0.92 | 1.00 | leaps, dodges shots, taunts, an acquisition roar | 0.74 |
| U2SkaarjMedium | rusher | claws + ProjectileSkaarjMedium (projectile) | 150 | 450 | 1.00 / 0.00 / 0.00 | 0.92 | 1.00 | leaps, dodges shots, taunts, an acquisition roar | 0.74 |
- **U2Izarian**: no signature move: nothing for the player to learn and remember (Unreal recipe)
- **U2SkaarjLight**: behaves like U2SkaarjMedium (only health/looks differ): give it its own move
- **U2SkaarjMedium**: behaves like U2SkaarjLight (only health/looks differ): give it its own move
