# Native foot IK (K6 + K9)

Built 2026-10-09 from research/native-animation-hooks.md, hook point 1. Report: "Dynamic body
kinematics and adaptive animation", slices K6 (standing foot IK + pelvis) and K9 (the native layer).

## What it does

For every human within range of the player (the pawns ModMinds keeps posed; the player too), the
two legs are bent inside the engine's own pose build so each foot stands on the floor that is
really under it: a step edge, stairs, a slope. The body is lowered (PrePivot) so the lower foot
reaches its floor and the other foot is lifted to its own. Before: on a step edge one boot sank
into the step and the other hovered in the air (the collision cylinder is held up by the edge).

- `Classes/ModFeet.uc` (spawned by ModMoves): sweeps the pawns every 0.5 s, hooks and releases
  them in the DLL, lowers the pelvis each tick, and runs the foot-to-floor meter.
- `native/footik.c`: the hook and the solver (commands `FootIKConfig`, `FootIK`, `FootIKOff`
  through `DynamicLoadObject("AdventNative.…")`).

## How (the hook)

Per leg, three bone directors (`USkeletalMeshInstance::SetBoneDirection(name, rot 0, vec 0,
alpha 1, Space 99, boneIndex)`, vtbl 0x11C) and `SetWorldSpacerFunction(name, fn, boneIndex)`
(vtbl 0x120). Space 99 isn't one the engine knows, so during the hierarchy walk, right after the
bone's mesh-space coords are final and before its children are placed, it calls

    FCoords* __cdecl fn(FCoords* ret, AActor* owner, int bone, int director, USkeletalMeshInstance* inst)

and takes the axes it returns (the origin is kept). The three stages, in bone order:

1. thigh: the animated chain is rebuilt (knee from the thigh and the constant knee offset, ankle
   from the calf's local rotation of the previous frame), the ankle goes to world through
   `MeshToWorld` (vtbl 0x13C), `ULevel::SingleLineCheck` (TRACE_World 0x86) finds the floor under
   it; the ankle target is the clip's ankle moved by (floor under the foot) − (the body's base as
   drawn: Location.Z + PrePivot.Z − CollisionHeight), clamped to MaxDrop/MaxLift and eased at Gain/s;
   the knee that reaches it is solved in the clip's bend plane and the thigh rotated there;
2. calf: rotated so the ankle (the clip's, fresh this frame, with the thigh's turn undone) lands
   on the target;
3. foot: both turns undone, so the foot keeps the orientation the clip gave it; then (bFootTilt) it
   is turned level with the floor traced under its ankle: the smallest rotation taking world-up onto
   the floor's normal (its axis is level, so only pitch and roll change and the clip's yaw stays),
   at most 25 degrees, the normal eased at Gain like the lift and back to level where the trace
   found no ground to use (a ledge, a crate, a wall's side: n.z under 0.5). Applied about the ankle,
   so the toe follows the slope.

Nothing is changed while any doubt remains: the mesh instance's vtable slots must be the very
exports we resolved by name, the ref skeleton must say calf→thigh and foot→calf, the first
callback checks that `MeshToWorld` puts the hip near the pawn, the bone-coords convention is
learnt from the ref skeleton before the first correction, the callback is in `__try/__except`
and answers "as animated" on a fault (the pawn is dropped after 3), ragdolls (PHYS_KarmaRagDoll)
and deleted actors are left alone, and a surface the pawn couldn't step onto (higher than
MaxLift) or reach down to is not taken as ground. The pelvis is script-side (PrePivot), so Hips,
which EonEngine drives for orient-to-floor, is never touched.

## Config `[AdventMod.ModFeet]`

| key | default | |
|---|---|---|
| bFootIK | False | on/off (off until the user has played with it) |
| bPlayerFeet / bAIFeet | True / True | who gets it |
| MaxDrop / MaxLift | 12 / 35 | how far an ankle may go below / above the clip's (units) |
| Gain | 10 | 1/s: how fast the feet and the pelvis follow a change of floor |
| Range | 3500 | AI within this of the player |
| bPelvis / PelvisDrop | True / 30 | the body lowered to the lower foot's floor, at most this |
| bFeetLog | False | the DLL's per-pawn lines (hooks, 5-s stats, once-a-second ankle asked/got) |
| bFeetMeter / SlopeStep | False / 4 | the meter below; "step" = the two feet's floors differ by more |
| bFootTilt | True | the foot tilted to its floor's slope (pitch/roll, clamped +-25 degrees); added offline 2026-10-09, **not yet seen running** |

## Measured (2026-10-09, hidden harness, level03sectionb stairs and level03sectionc)

Meter: for the lower (planted) foot of every drawn biped, the ankle's height over the floor traced
under it (an ankle is about 8 over the sole), logged every 8 s.

| case | IK off | IK on |
|---|---|---|
| player on a step edge, centre on the lower step, one foot over a 16-unit higher step | lower foot 19..25 over its floor (hovering), the other boot inside the step | lower foot 7..8, the other lifted +16.3 (asked −1078.1, got −1078.1), body lowered 23 |
| player centre on the higher step, one foot over the lower | the foot in the air (25 over its floor) | body lowered, the foot down on the lower step, 7..8 over it |
| AI walking on flat ground (marines, level03sectionc) | 12 (7..19) | 7 (3..10): their cylinders hover ~5 above the floor, the soles now touch it |
| player on flat ground | 13 | 7 |
| ankle under its surface | 0 % | 0 % (two earlier causes fixed: feet swung over props above MaxLift climbed onto them, now "not ground"; crouching marines had the base 23 off, see the crouch fact below) |
| AI foot slip (ModMoves, planted foot's slowest speed / body speed) | 43 % | 37-51 % over three runs: unchanged within the run-to-run noise. Foot IK isn't foot locking |
| cost | | 1.0-1.3 µs per callback with the trace, 6 callbacks + 2 traces per pawn per pose build (~8 µs per pawn per frame) |
| crashes / callback faults | | none in 11 runs, 0 faults |

Screenshot pairs (scratchpad, not in the repo): `footik_step0_off_on.png`, `footik_step1_off_on.png`
(off left, on right): with IK the foot on the higher step stands on it with a bent knee and the
body sits lower; without it the boot cuts through the step edge or floats.

Repeat: `test_run.ps1` with `[AdventMod.ModFeet] bFootIK=True bFeetLog=True` and the pilot steps
`goto -12488 -9578 -1036`, `face 0`, `tilt -0.7`, `shotp` on level03sectionb (the station
stairs: `floormap 200 10` prints the floor heights around the player). `goto X Y Z` and `floormap`
are new ModPilot steps.

## Engine facts learnt (this build)

- The bone FCoords in the instance (+0xB4, stride 0x30) have rows = the rows of the local→mesh
  rotation (mesh = R · local), not the basis vectors: decided by comparing the calf's offset in the
  thigh's frame with the ref skeleton's position (0.00 vs 30.44 error).
- `FMeshBone` is 0x40 here but not UT2004's order: FName +0, Flags +4, quat +8, position +0x18,
  length +0x24, +0x28..+0x30 (0 / a pointer / 0), **ParentIndex +0x34**, NumChildren +0x38, +0x3C a
  pointer. The ref skeleton is `USkeletalMesh+0x1DC/+0x1E0`.
- `MeshToWorld()` returns a row-vector matrix: world = (x, y, z, 1) · M. The mesh draws at
  Location + PrePivot (0x1B4); DrawScale 0x1A4, DrawScale3D 0x1A8.
- `ULevel::SingleLineCheck(Hit, Source, End, Start, flags, Extent)` returns 1 when nothing was hit;
  `FCheckResult.Location` at +8. `AActor::Trace` uses 0x86 (world) + 0x39 for actors.
- On a step edge the walking cylinder is held up by the edge: a trace under the pawn's centre
  reads the lower floor (29 below the cylinder's base). The clip stands on the cylinder's base.
- A crouch (AI marines in cover, CollisionHeight 78 -> 55) lowers Location by the difference and
  raises PrePivot by it, so the mesh stays where it stood and the crouch clip keeps its feet on the
  floor. Hence the clip's base is Location.Z + PrePivot.Z − the *standing* CollisionHeight (passed
  with the install), and the pelvis drop must be a change to PrePivot, never a value written over
  it (the first version wiped the crouch offset: crouched marines drawn 23 low, feet 16 under).

## Open

- The downhill foot only goes as far as the pelvis drop + the knee's bend allow (a straight idle
  leg gives ~5 of drop on its own); PelvisDrop 30 covers normal steps.
- The foot tilt (bFootTilt) is built but unseen: a GPU session should run the stairs/slope steps
  below with `bFeetLog` (the once-a-second ankle line now ends `tilt N deg`, the 5-s line has a
  `tilt` per leg) and look at a pawn on a ramp (level03sectionb's station has slopes by the
  stairs) for the sole lying on it rather than cutting in at the toe; and at a run on flat
  ground for any foot wobble (the normal is eased at Gain, so a trace that flicks between a
  floor and a step's riser should blend, not snap). The clamp is 25 degrees; the Seekers'
  and hounds' chains are still not hooked.
- Humans only (leftUpLeg/leftLeg/leftFoot). Seekers and hounds have other chains; a hound's
  UpLegs are EonEngine's (orient-to-floor): never hook those.
- The knee target uses the calf's local rotation of the previous frame (the correction lags a
  frame; the base pose doesn't).
- The pelvis is the whole drawn body (PrePivot): on stairs at a run it dips with each stride,
  eased at Gain. Anything else that moves PrePivot on a live human must go through ModFeet's
  Pivot base (ModReact.OnFloor only touches dead bodies).
- Not tried: cutscenes (CinematicPrePivot is applied by the game as a value: it would drop our
  delta and we would then subtract it back on release; harmless but worth a look), vehicles, the
  Seeker ragdoll handoff (the hook is released when
  Physics isn't Walking/Falling, and the DLL ignores PHYS_KarmaRagDoll anyway).
