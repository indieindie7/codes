# Advent gore â†’ Unreal II: handoff

From the Advent chat, 2026-10-08, for the Sanctuary (M08A*) gore pass. The full design is in `games/advent_rising_mods/GORE-DESIGN.md`. This note covers only what matters for the port.

## 1. Where the source is

| what | where | commit |
|---|---|---|
| Design doc | `codes/games/advent_rising_mods/GORE-DESIGN.md` | codes c3a9871 |
| Script side | `codes/games/advent_rising_mods/AdventMod/Classes/` (ModGore, ModSever, ModBloodDrop, ModBloodDecal, ModBloodCoat, ModPlayerBlood, ModScreenBlood, ModStump, ModGib*, ModPilot) | codes c3a9871 |
| Native bridge | `codes/games/advent_rising_mods/native/adventnative.c` | codes c3a9871 |
| Offline sims | `AdventMod/tools/runs_sim.py`, `streaks_sim.py`, `strings_sim.py`, `lens_sim.py`, `make_blood_drops.py` | codes c3a9871 |
| d3d8 layer | `d3d8to9-gi`, branch `gi-cascades`: `source/blood.hpp` (pools), `runs.hpp` (wall runs), `streaks.hpp` (body streaks + hands), `strings.hpp` (goo), `lens.hpp`, `perf.hpp`; gloss in `u2shaders.hpp` (`gloss=`) | fork **76933c5** |

## 2. What carries over and what doesn't

**Game-agnostic** (it lives in the d3d8 layer and only needs commands):
- **Live pools** (`pool/pour/bed/stamp/stop`): a placeholder texture on a projector, swapped for a sheet that the layer simulates. Needs `bloodlive=HASH` lines for U2's own placeholder textures.
- **Wall runs** (`run/drip/rstop`): the same idea, with `bloodrun=HASH` lines.
- **Gloss and drying** (`gloss=HASH blood_gloss.hlsl`, `glossfx/glossenv/glossdry/glossreflect`): rules keyed on U2Gore's own decal texture hashes.
- **Goo strings** (`string/stringoff/stringclear`): world-space geometry. It needs only the view, projection and depth buffer.
- **Wet lens** (`lens/lensat/lensclear`): a post pass, so it needs `post=1`.
- **Body streaks and hands** (`streak/streaks/streakclear`, `hand/hands/handclear`): game-agnostic in principle, but see the gotchas.
- **The shader cache and warm-up, 30 Hz stepping, lagfix and perf lines**: automatic.

**Advent-only** (don't port):
- ModSever (bone scaling: you found Golem bones aren't scriptable).
- Gibs and ModGibAtlas (U2 has GibSets).
- ModReact, death anims and ragdoll bones.
- ModBloodCoat (Combiner skins: U2 Golem pawns have 0 Skins; your projector on the body works better).
- ModScreenBlood (you have U2Gore.ui).

**Portable script logic:**
- Footprints (`WetFeetScan`/`PrintAt`) and falling drops (`ModBloodDrop`) are plain decals and sprites, with no layer dependency.
- Ceiling drips work by trace.
- Wall-run placement: `|N.Z| < 0.5`, with "down" projected onto the decal axes.

## 3. The d3d8 wrapper

- Take **gi-cascades 76933c5**: build `d3d8.dll` Release Win32 with v145, plus the `U2Shaders\*.hlsl` it ships.
- Every effect is **off by default**. Turn them on in U2Shaders.ini; the ini reloads live while the game runs.

  ```
  gloss=<hash> blood_gloss.hlsl      ; one line per U2Gore decal texture
  glossfx=... glossenv=... glossdry=60 240 0.5 glossreflect=...
  bloodlive=<hash>                   ; pool placeholders, slot order
  bloodrun=<hash>                    ; wall-run placeholders, slot order
  streaks=1
  streakparams=2.5 40 6 50
  streakfx=1 0.92 2 25               ; gain 2 is for Advent's 2x skins: try 1 in U2
  strings=1
  stringparams=1 1 1 1
  stringfx=0.4 0.5 0.95 0.3
  hands=1
  handsparams=1 0.8 0.75 1.2
  lens=1
  lensparams=0.8 120 4.5 0.75
  lensfx=1.8 0.3 0.7 0.4
  post=1
  lagfix=1                           ; default on: lagfix=0 if U2's mouse feels off
  ```
- Advent's live lines are in `games/advent_rising_mods/AdventMod/System/U2Shaders.ini`. Its hashes are Advent textures, so log your own (the `gloss: first draw (hash ...)` lines).
- Shader files: copy `codes/games/advent_rising_mods/AdventMod/U2Shaders/blood_gloss.hlsl` into `<U2>\System\U2Shaders\`. Streaks, strings, hands and the lens are compiled from source inside the dll.

## 4. âš  The blocker: how script reaches the layer in U2

- In Advent, script calls `NativeCall("Blood:<cmd>")` â†’ **AdventNative.dll** â†’ the exported `U2BloodCommand(const char*)` in d3d8.dll. **Unreal II has no AdventNative.**
- Streaks, strings and hands are sent **every tick**, so file channels (U2Live.cmd is toolâ†’game; the U2GM.ini journal) are too slow.
- **Options:**
  - **(a)** The layer reads a known script object's string property each frame. It already finds `GObjects` for the live channel, so a `GoreLink` actor with `var string Cmds` the layer drains would work. â† my pick, about half a day of work in the fork.
  - **(b)** A tiny U2 native package (needs the U2 SDK headers we don't have).
  - **(c)** Port only what needs no per-tick commands first: gloss, footprints, drops, ceiling drips. Pools and runs need only a few commands per event, so a file channel would survive for those.
- Tell me which, and I'll add (a) to the fork if you want it.

## 5. The script side and how it was tested

- **Hits feed in from** `ModGoreRules` (a GameRules `NetDamage`) â†’ `ModGore.Mark` (bone, momentum, damage) â†’ decals plus layer commands. Your GoreRules already plays this role.
- **The streak sources** are wounds, hits on corpses and cuts: at most 8 per tick, each sent as `streak K x y z nx ny kind age str seed`, then `streaks n`.
- **Tests:**
  - **Hidden ModPilot runs** with `bGoreLog=True`: `spawn`, `hurt`, `gibahead`, `driptest`, `walkblood`, `goolist`/`droplist`/`steplist`, and `shotp` prints.
  - **A good result:**
    - runs visibly crawl for about 10 s and end in beads;
    - streaks run straight down whatever the pose and stay on the wounded body;
    - prints alternate left and right;
    - drops are counted thrown equal to landed;
    - the `perf:` lines show frames > 50 ms at 0â€“1 during a fight.
  - **Offline:** the `*_sim.py` tools draw each effect as a strip, so you can tune without the game.
  - **Drying:** `tools/python/visualqa/blood_drying.py`.

## 6. Gotchas

- **Perf:**
  - Pools and runs simulate on the CPU, now at 30 Hz (a fight's end-of-frame work went from 5.1 to 1.1 ms).
  - Every new shader compiles once at load; WarmShaders covers streaks and strings.
  - Check that `perf:` lines appear in U2Shaders.log.
- **Streak pass draw filter** (`U2Streaks::Wants`): it only re-draws **fixed-function, lit, opaque, depth-tested, non-alpha-tested draws whose FVF has normals**. Advent's skinned characters match. **Not checked for U2 Golem meshes.** If streaks never appear, log FVF and lighting for a merc draw first.
- **Colour gain:** Advent draws skins at double brightness, so `streakfx` gain 2 and `handsparams` gain 1.2 are tuned for that. U2 probably wants about 1.
- **Water and translucency (Sanctuary):**
  - The streak and hands passes skip blended draws, so nothing gets painted onto water. Good.
  - **Pools and runs are projectors:** UE2 projects them onto BSP under shallow water and onto FluidSurfaceInfo. Have `Surface()` skip water volumes and fluid surfaces: no pool where `PhysicsVolume.bWaterVolume`, and a cloud or tint particle instead if you want one.
  - **Goo strings** are depth-tested but not depth-written, and water doesn't write depth. So a string behind a water surface draws **on top of it, unfogged** by the water. Rare, but cap strings to bodies out of water.
  - **Drops and footprints:** stop the landing trace at water (`TraceActors` with volumes) so drops don't splat on the pool floor through the water.
  - **gloss reflect** on deep pools samples the screen. Near water planes it may pick up the water's own reflection, which is harmless.
- **Lens** needs `post=1`, and it replaces the HUD splats only when the mod honours the command's return value (1 = the layer draws the drops).
- **The ini reloads live:** rule changes no longer recompile everything, but a changed `gloss=` line does recompile that rule.
