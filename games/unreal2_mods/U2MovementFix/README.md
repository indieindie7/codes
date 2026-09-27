# U2MovementFix

Puts Unreal II's original player movement back on top of
[SOverhaul](https://www.nexusmods.com/unreal2theawakening/mods/1), and keeps
everything else SOverhaul adds (shadows, recoil, HUD, restored weapons, ...).

SOverhaul makes two movement changes:

| | Original game | SOverhaul | With this fix |
|---|---|---|---|
| Player speed (`U2PlayerSP.GroundSpeed`) | 263 | 1000 | 263 |
| Shift (the `Walking` key) | hold to walk | hold to sprint, walk otherwise | hold to walk |

**Why undo it:** Unreal resolves collision after each move, as a matter of
fact, not predictively. At almost 4× the speed, each frame moves the player
much further into walls, ledges and props before the correction happens. You
get snagging, popping and overshooting that the level geometry was never
built for. Dodges scale with the default speed too, so they became huge.

## How it works

SOverhaul ships recompiled packages, and the walking rule lives in a regular
controller function that a mutator can't override. So this is a small patcher.
It makes two same-size byte patches, and nothing else in either file moves:

- `System/U2Pawns.u`: in the `U2PlayerSP` class defaults, `GroundSpeed`
  1000.0 → 263.0. That is the `LicenseePawn` value the player inherited before
  SOverhaul, and Engine.u's `LicenseePawn` is byte-identical in both versions.
- `System/U2.u`: in `U2PlayerController.HandleWalking`, `GetRunFlag() < 1` →
  `GetRunFlag() > 0`. In bytecode that is `Less_IntInt`/`IntOne` →
  `Greater_IntInt`/`IntZero` (`96…26` → `97…25`), exactly what the
  original compiles to.

Each patch is looked up inside its own class or function through the
package's export table, and only applied when the expected bytes match exactly
once. If they don't (a different SOverhaul or game version), it refuses.

## Use

Close the game, then:

```
python u2movefix.py            # show the current state
python u2movefix.py apply      # patch (first backs up to System/*.before-movefix)
python u2movefix.py restore    # put SOverhaul's movement back
```

Edit `GAME` at the top of the script if the game isn't in the default Steam
folder. Saves keep working either way.

Verified in-game with [U2Pilot](../../../tools/python/U2Pilot)
(`scripts/move_probe.txt`):
- `get U2PlayerSP GroundSpeed` reports 263.
- Walking forward covers about 255 units/s with no key held and about 77 with
  Walking held, which is the original 30% walk speed.

Found by exporting SOverhaul's packages and the original ones (from the
SOverhaul install backup) with `ucc batchexport` and diffing them.
