# U2Patches

Small fixes for Unreal II: The Awakening with
[SOverhaul](https://www.nexusmods.com/unreal2theawakening/mods/1) that no
mutator can make, because they live in regular player-controller functions or
class defaults. Each one is a same-size byte patch to a compiled package, and
you can apply or restore each patch on its own. Everything else SOverhaul adds
(shadows, recoil, HUD, restored weapons, ...) stays.

| Patch | What it does |
|---|---|
| `movement` | Undoes SOverhaul's movement changes: player speed 1000 → the original 263, and Shift walks again instead of sprinting |
| `nolean` | Removes leaning (Q/E and the other lean keys do nothing) |

## Use

Close the game, then:

```
python u2patch.py                            # show the state of every patch
python u2patch.py apply   movement nolean    # apply
python u2patch.py restore nolean             # undo one
```

Before the first change, each package is backed up to
`System/<name>.u.before-u2patch`. Edit `GAME` at the top of the script if the
game isn't in the default Steam folder. Saves keep working either way.

## movement

| | Original game | SOverhaul | Patched |
|---|---|---|---|
| Player speed (`U2PlayerSP.GroundSpeed`) | 263 | 1000 | 263 |
| Shift (the `Walking` key) | hold to walk | hold to sprint, walk otherwise | hold to walk |

**Why:** Unreal resolves collision after each move, as a matter of fact, not
predictively. At almost 4× the speed, each frame moves the player much further
into walls, ledges and props before the correction happens. You get snagging,
popping and overshooting that the level geometry was never built for. Dodges
scale with the default speed too, so they became huge.

- `System/U2Pawns.u`: in the `U2PlayerSP` class defaults, `GroundSpeed`
  1000.0 → 263.0. That is the `LicenseePawn` value the player inherited before
  SOverhaul, and Engine.u's `LicenseePawn` is byte-identical in both versions.
- `System/U2.u`: in `U2PlayerController.HandleWalking`, `GetRunFlag() < 1` →
  `GetRunFlag() > 0`. In bytecode that is `Less_IntInt`/`IntOne` →
  `Greater_IntInt`/`IntZero` (`96…26` → `97…25`), exactly what the original
  compiles to.

**Verified in-game** (U2Pilot `scripts/move_probe.txt`): the speed reads 263.
Walking forward covers about 255 units/s with no key held and about 77 with
Walking held, which is the original 30% walk speed.

## nolean

Leaning (Q/E, plus the forward/up lean keys) in a game with no stealth or
peeking design is a feature that makes no sense and gets in the way.

Every way into a lean (`ToggleLeanLeft/Right/Forward/Up`) first asks
`CanLean()`. The global version already returns false, and the three movement
states override it:

```
PlayerWalking:  return ViewingSelf() && Pawn.Physics == PHYS_Walking;   // 1
PlayerSwimming: return ViewingSelf() && Pawn.Physics == PHYS_Swimming;  // 3
PlayerClimbing: return ViewingSelf() && Pawn.Physics == PHYS_Ladder;    // 11
```

The patch changes each physics byte constant to 255, a physics mode that
doesn't exist, so `CanLean()` is always false. That is a 1-byte change in each
function, and the bytecode stays structurally valid.

**Verified in-game** (U2Pilot `scripts/lean_test.txt`):

| | Before | After |
|---|---|---|
| Hold Q | `Lean_Left`, view offset -48 | `Lean_None`, offset 0 |
| Hold E | `Lean_Right`, view offset +48 | `Lean_None`, offset 0 |

The crosshair and view stay normal while the keys are held.

## Safety

Each patch is looked up inside its own class or function through the package's
export table, and is only applied when the expected bytes match exactly once
there. A different game or SOverhaul version is refused instead of corrupted.
Built against SOverhaul 1.1.0's packages. The original non-SOverhaul packages
were compiled with debug info, so their bytecode differs and they are not
supported.

Found by exporting SOverhaul's packages and the original ones (from the
SOverhaul install backup) with `ucc batchexport`, diffing them, then comparing
the functions' compiled bytecode.
