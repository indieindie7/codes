# Advent Rising: how native code drives pawn animation (and where to hook it)

Read from a headless Ghidra 12.1.4 decompile of the game's own `Engine.dll`, `EonEngine.dll`
and `EonCharacters.dll` (UE2 build 2226, 32-bit), 2026-10-08. Nothing in the game folder was
changed and the game was not run. Everything here comes from reading the code. None of it
has been tested in the game yet.

## How to read the addresses

- `Engine.dll` loads at base 0x10300000 and `EonEngine.dll` at 0x10700000.
  `EonCharacters.dll` also has preferred base 0x10700000, so it gets relocated at load time.
  Its addresses are file addresses, so resolve them by RVA at run time.
- Each export (`?Name@Class@@...`, at 0x103xxxxx or 0x107xxxxx) is a 5-byte `jmp` thunk
  from the incremental linker. The body sits elsewhere. Vtables point at the **thunks**, so
  patching a thunk's `jmp` also catches virtual calls. Both addresses are given below as
  `thunk -> body`.
- Field offsets come from the decompiled code, matched to the declaration order in the
  `.uc` files. On this build `UObject` is 0x2C bytes, so Actor's first bool dword is at
  0x2C.

| Object | Offset | Field |
|---|---|---|
| Actor | 0x2C bit 0x200 | `bForceVisible` |
| Actor | 0x34 | bVerticleTranslationInRootMotion=1, bAllowRootMotionZToFall=2, bStasis=0x4000, bDeleteMe=0x80, bTearOff=0x10000000 |
| Actor | 0x38 | bCheckRootFalling=8, bUseRootRotation=0x10, bZeroRootMotion=0x20, bNoRootCollisionOnMove=0x40, bAnimByOwner=0x4000000 |
| Actor | 0x3C bit 0x4000000 | `bInterpolating` |
| Actor | 0x40 | bCanSkipFrames=0x200, bTickWasSkippedThisFrame=0x400, bSkipEvenFrames=0x800 |
| Actor | 0x44 / 0x48 | fMissedTickTime / fMissedTickTime_Special |
| Actor | 0x55 / 0x5D | Physics / Role |
| Actor | 0xB8 / 0xBC | Level / XLevel |
| Actor | 0xD4 / 0xD8 | Mesh / LastRenderTime |
| Actor | 0xF8 | MeshInstance |
| Actor | 0x120 | LatentFloat |
| Actor | 0x130 / 0x13C / 0x148 / 0x154 | Location / Rotation / Velocity / Acceleration |
| Actor | 0x1F8 / 0x1FC | CollisionRadius / CollisionHeight |
| Pawn | 0x254 | Controller |
| Pawn | 0x2D8 | GroundSpeed |
| Pawn | 0x324 / 0x330 / 0x33C | AimLocation / HeadAimLocation / shootLocation |
| Pawn | 0x348 bit 1 | `bAllowInput` |
| Pawn | 0x34C | moveTime |
| Pawn | 0x358 | bAnimateToStop=1, bWasStanding=2 |
| Pawn | 0x388 | Floor |
| Pawn | 0x420-0x42C | oldMaxSpeed / oldBaseMovementRate fields |
| Pawn | 0x490 | bPhysicsAnimUpdate=1, bWasCrouched=2, bWasWalking=4, bWasOnGround=8, bInitializeAnimation=0x10, bPlayedDeath=0x20 |
| Pawn | 0x4A4 / 0x4A8 / 0x4AC | OldPhysics / OldRotYaw / OldAcceleration |
| Pawn | 0x4B8 | BaseMovementRate |
| Pawn | 0x4BC | MovementAnims[4] |
| Pawn | 0x4CC | walkMovementAnims[4] |
| Pawn | 0x4DC / 0x4E0 | TurnLeftAnim / TurnRightAnim |
| Pawn | 0x4E4 / 0x4E8 / 0x4EC | BlendChangeTime / stopBlendChangeTime / MovementBlendStartTime |
| EonPawn | 0x548 | aim bone name for CalculateBoneLocations |
| EonPawn | 0x5C4 / 0x5C8 | headAlpha / headAlphaTarget |
| EonPawn | 0x5EC / 0x5F0 | SpeedChangeMax / SpeedChangeMin |
| EonPawn | 0x5F4 | GroundSpeedMax |
| EonPawn | 0x5F8 / 0x5FC | GroundSpeed_F / _B |
| EonPawn | 0x600 / 0x604 | BaseAnimSpeed_F / _B |
| EonPawn | 0x620 | bool dword: bRight/LeftWeaponWantsToAim=4/8, bHas180Turn=0x10, bUpdatingSpineRot=0x40, bOrientToFloor=0x80, bWantsToOrientToFloor=0x100 |
| EonPawn | 0x624 / 0x628 / 0x62C | spine / spine1 / spine2 bone indices |
| EonPawn | 0x640 | HeadTrackingVector |
| EonPawn | 0x684 / 0x690 / 0x69C | spine rotation current / target delta / timer |
| EonPawn | 0x6A8 | 180-turn timer |
| EonPawn | 0x710 | weapon/carry state byte |

### `USkeletalMeshInstance` layout (as used below)

- `+0x60/+0x64`: the GTicks of the last pose build.
- `+0x68`: the channel-0 frame used as part of the cache key.
- `+0xB4/+0xB8`: the per-bone `FCoords` array, stride 0x30, in mesh space.
- `+0xD4`: the mesh-to-world base coords.
- `+0x114/+0x118`: the anim channels. Each channel is a TArray of blend slots with stride
  0x7C:
  - +8 sequence name
  - +0xC rate
  - +0x10 frame
  - +0x30 looping
  - +0x4C real-time flag
  - +0x50 play-reversed flag
  - +0x54 alpha
  - +0x60 root-motion-ended flag
- `+0x12C/+0x130`: the bone rotators and translators.
- `+0x138/+0x13C`: the bone "directors", stride 0x3C:
  - +0 bone index
  - +4 name
  - +0x14 rotator
  - +0x20 translation
  - +0x2C Space
  - +0x30 rotation alpha
  - +0x34 translation alpha
  - +0x38 world-spacer callback
- `+0x1C4`: the root-motion lock mode.

## 1. Per-tick movement animation

### Call chain

The tick path is `AActor::Tick` (0x1030a920 -> 0x104a0df0), then the vtable slot at 0xE8,
`TickSpecial`.

`APawn::TickSpecial` (0x10305b0f -> 0x104a04f0):

```c
if (!bInterpolating && bPhysicsAnimUpdate && Mesh) this->UpdateMovementAnimation(dt); // vtbl 0x220
this->CalculateBoneLocations();                                                      // vtbl 0x228
if (bit 0x800000 @0x264 || IsHumanControlled()) eventUpdateEyeHeight(dt);
```

`AEonPawn::TickSpecial` (0x10701bd6) calls `APawn::TickSpecial` and then `FUN_1073d640`
(arm aiming and orient-to-floor, see section 2). `AHuman::TickSpecial` (EonCharacters 0x10701131)
goes through `AAdventPawn::TickSpecial` and then:

- `UpdateSpineRot` (vtbl 0x244), only while `bUpdatingSpineRot` is set.
- `UpdateHeadTracking` (vtbl 0x248), every tick.
- `eventCheckAnimTasks`, which is a **script event called every tick**.

`bControlAnimations` is not read anywhere in native code. It only matters in script.
`bNoTurnAnims` does not exist in Advent. The native switches are:

- `bPhysicsAnimUpdate`: no movement blending at all.
- `bInterpolating`: no movement blending.
- `bAllowInput`: movement channels fade to 0.
- `bTearOff`: the death branch.
- `Level+0x4CC == 1`: early return.

### `AEonPawn::UpdateMovementAnimation` (0x10701e1f -> 0x107395b0)

This is a wrapper that runs around the base engine version:

```c
speed = |Velocity|;
if (bAllowInput) {
  if (eventCanDo180TurnNow()) turnTimer(0x6A8) = 0.15; else turnTimer -= dt;
  if (turnTimer > 0 && Physics == PHYS_Walking && Controller) {
    if (!Controller->IsAPlayerController()) {             // AI path
      if (dot(Controller.Rotation.Vector(), Rotation.Vector()) < -0.8) eventDoRunTurn(...);
    } else if (!(Ctrl+0x770 & 0x40) && |Ctrl+0x708| > 225 &&
               dot(Normal(Acceleration), Rotation.Vector()) < -0.7)  eventDoRunTurn(Normal(Accel));
  }
}
if ((speed > SpeedChangeMax || speed < SpeedChangeMin) && Physics != PHYS_Falling)
    eventInputSpeedChange(speed);          // fires EVERY tick while outside the band
if (bAnimateToStop && Velocity != 0) Acceleration = Normal(Velocity);  // temporarily
APawn::UpdateMovementAnimation(dt);
Acceleration = saved;
```

The player branch in the decompile may have AI and player swapped. The vtbl 0x1A4 check is
`IsAPlayerController`.

### `AEonPawn::GetMaxSpeed` (vtbl 0x1EC, 0x10702577)

This picks forward or backward values from the sign of `dot(facing, Normal(Accel))`:

- `GroundSpeedMax` (0x5F4) and therefore `GroundSpeed` (0x2D8) become `GroundSpeed_F` or
  `GroundSpeed_B`.
- `BaseMovementRate` (0x4B8) becomes `BaseAnimSpeed_F` or `BaseAnimSpeed_B`.

So `BaseAnimSpeed_*` reaches the engine through `BaseMovementRate`.

### `APawn::UpdateMovementAnimation` (Engine 0x1030646a -> 0x104db560, 7348 bytes)

**First run** (`bInitializeAnimation` is clear), it sets up the channels:

- Channel 2 gets TurnRightAnim (0x4E0) and channel 3 gets TurnLeftAnim (0x4DC).
- Channels 4-7 get MovementAnims[0..3]: 4 = forward, 5 = back, 6 and 7 = the strafes.
- Channels 8-11 get walkMovementAnims[0..3].
- All are looped at rate 1.0 with tween 0.1. Alphas start at 0 and notifies are off, except
  channel 4.

**Moving** (Accel != 0 or |V|² >= 50):

- Direction weights are **squared cosines**: `f = dot(Normal(Accel), facing2D)`,
  `s = dot(Normal(Accel), right2D)`.
  - Channel 4 alpha is f² when f > 0, otherwise channel 5 gets f².
  - Channel 6 or 7 gets s² by the sign of s.
  - Each alpha moves toward its target at the rate `dt / BlendChangeTime`
    (`UpdateBlendAlpha`).
- When moving backward, the two strafe slots swap and play **reversed** (the slot +0x50
  flag is set and the frame is mirrored as `1 - frame`), so the legs cross the right way.
- **Rate:** `rate = |V| / GetMaxSpeed() * BaseMovementRate * avg(GetAnimRateOnChannel(dominant
  channels))`. When two directions are active the base rates are averaged (×0.5). Channels 4
  and 5 get `SetAnimRate(ch, rate / GetAnimRateOnChannel(ch))`. Every other movement channel
  (4-11) is **frame-synced** to the master channel (4, or 5 when backward) with
  `SetAnimFrame` (vtbl 0x128), so all strides stay in phase. There is no stride or foot
  matching: speed and rate are only scaled linearly.
- **Walk/run blend:** channels 8-11 get alpha = `alpha(ch-4) * (1 - clamp((|V| - 280) / 70,
  0, 1))`. The walk anims are full below 280 uu/s and gone at 350. The constants are at
  0x106c9a54 (280.0) and 0x106c9a50 (1/70).
- Panic arms go on channel 0x1C when the byte at Pawn+0x53C is 4 and |V| > 500.

**Stopped** (no accel and |V|² < 50): this is turn in place.

- Channels 4-7 are zeroed. If MovementAnims moved, `eventChangeAnimation` fires.
- Only when `Physics == PHYS_Walking && Role > ROLE_SimulatedProxy`:
  - `yawRate = (Rotation.Yaw - OldRotYaw) / dt`, with OldRotYaw unwrapped by ±65536 when the
    difference is over 32768.
  - Above +1000 u/s, TurnRightAnim plays on channel 2 at alpha 1. Below -1000, TurnLeftAnim
    plays on channel 3. The constants are at 0x106c8c70 and 0x106c8c6c.
  - The turn rate is `|yawRate| * frames/rate / 16384`.
- Afterwards `OldRotYaw = Rotation.Yaw` and `bWasStanding` is set.

`PHYS_Riding` (13) and `PHYS_Levitate` (16) have their own branches that use Acceleration
directly. Any of these sets the movement alphas to 0: Falling, `Level.TimeSeconds <
MovementBlendStartTime`, or `!bAllowInput`.

## 2. AI and aim events called from native code

- **`GetFrameAimLocation` is never called for pawns.** Its only native caller is
  `AVehicle::UpdateWeaponBoneInfo` (Engine 0x1030b00a -> FUN_105b1520), which aims vehicle
  turrets. `Bot.GetFrameAimLocation` only runs when script calls it.
- **Arm aiming** is `FUN_1073b910` (EonEngine), run every tick from
  `AEonPawn::TickSpecial -> FUN_1073d640` when the weapon state byte 0x710 is 1-7. Where the
  target comes from (`FUN_1073b550`):
  - **Controller == None:** it uses `shootLocation` (0x33C), or a player pawn for turrets.
  - **AI:** it uses the Controller's FocalPoint (Ctrl+0x298). When the target actor is
    Ctrl+0x860, it calls `AActor::eventGetAimLocation(target)`, a **script event every
    tick**.
  - It calls the script events `GetWeaponAimTime`, `SetRight/LeftWeaponWantsToAim`,
    `SetRight/LeftWeaponIsAimed` and `SetUsingTwoHandsForPistolAiming`.
  - The pose comes from `FUN_10734420`, which blends the Target*_U/D/F/B/T aim anims plus
    `GetBoneCoords` reads on RightShoulder and LeftArm.
- **Spine:** `AEonPawn::UpdateSpineRot` (thunk 0x10701078). It calls
  `SetBoneDirection` on spine, spine1 and spine2 with alpha 1. The indices are cached in
  0x624-0x62C.
  - The rotation eases from 0x684 toward a target delta at 0x690, and a timer at 0x69C is
    reset to 15.0.
  - **Space 2 (world)** is used when the state byte 0x710 is 3, 4 or 8. Otherwise it uses
    **Space 50 (0x32)**.
  - The script `SetSpineRot` event body is empty. Native code writes 0x690 directly (for
    example `AHuman::TickSpecial` adds ±0xFFF yaw on hit reactions).
  - `ASeekerDogNative::UpdateSpineRot` (EonCharacters 0x10701186) uses per-dog rotators at
    0xB08/0xB14/0xB20 with Space 50.
  - `AHumanPlayable::UpdateSpineRot` zeroes the spine while Ctrl+0x770 & 0x100.
- **Head:** `AEonPawn::UpdateHeadTracking` (0x10701343) and `AHuman::UpdateHeadTracking`
  (EonCharacters 0x10701028) run every tick.
  - They call `Controller.eventGetHeadTrackingVector(&HeadTrackingVector)`. If that returns
    true, the script event `SetHeadTrackingToLookAtVector` runs every tick. `AHuman` turns
    this off while jogging or running with channel 4 alpha > 0.
  - `jknMoveHeadAlphaTo` eases headAlpha toward its target.
- **`AEonPawn::CalculateBoneLocations`** (vtbl 0x228, every tick):
  - `AimLocation = GetBoneCoords(name@0x548).Origin`
  - `HeadAimLocation = Location + (0, 0, 0.8 * CollisionHeight)`

  This `GetBoneCoords` call **builds the pawn's pose every tick** (see section 4).
- **`execSetEonBoneDirection`** (0x107015e1) is `SetBoneDirection` (vtbl 0x11C) plus
  `SetWorldSpacerFunction(bone, FUN_10743290)` (vtbl 0x120). It hooks the bone up to
  EonEngine's own callback, which handles the extended Space codes (see section 4).
- **Orient to floor** is `FUN_10737bc0`, also run every tick:
  - It needs `bOrientToFloor` or `bWantsToOrientToFloor`.
  - It tilts **`Hips`** with `SetBoneDirection(..., Space 2)` and moves it with
    `SetBoneLocation`.
  - `FUN_107375a0` counter-rotates `Right/LeftFrontShoulder` and `Right/LeftUpLeg` (the dog
    and quadruped legs) with Space 2.
  - The alpha (0x680) ramps at 5/s. The floor normal (0x674) follows `Floor` at 2·dt per
    tick, and the hip offset (0x668) at 1000 uu/s.
  - The anim group `NoFeetOrient` on channel 0 turns it off.

  This is the only native terrain adaptation in the game. It has no per-foot traces and no IK.

## 3. Root motion

- **Entering:** whenever channel 0 starts an anim, `AEonPawn::CheckNewAnimGroup` (0x10701884
  -> FUN_1073d780) runs. `AActor::CheckNewAnimGroup` is at 0x10306fb9, vtbl 0x150, and is
  called from PlayAnim and PlayBlendedAnim. It reads the anim's **groups**:

  | Group | What it does |
  |---|---|
  | `RootMotion` | `LockRootMotion(1)` (4 if already in PHYS_RootMotion), then `setPhysics(PHYS_RootMotion=12)`. Sets bVerticleTranslationInRootMotion=1 and bCheckRootFalling=0. |
  | `RootMotionZ` | Same as above, with bCheckRootFalling=1 and bVerticleTranslation=0. |
  | `RootMotionRot` | Sets bUseRootRotation. |
  | `NoMotion` | Sets bZeroRootMotion. |
  | `NoRootCollision` | Sets bNoRootCollisionOnMove. |
  | `Reaction` | Sets bAllowRootMotionZToFall. |
  | `IgnoreRootMotionOffset` | Read in LockRootMotion: zeroes the start offset. |
  | `RealTime/Equip/Attack/Reaction/Pickup/NoInput/Power` | Set `bAllowInput = false`. |
  | `OverRideAllowFire` | Sends the `SetOverRideAllowFire` event. |
  | `CantFall` | Forces PHYS_Walking. |
  | `OrientToFloor` | Sets bWantsToOrientToFloor. |

  It always ends with the `SetHeadTracking(true)` and `SetSpineTracking(true)` events. A
  Pawn bool at 0x268 bit 0x400 blocks root motion.

  **So script can play a root-motion clip on demand:** import the sequence with `GROUP=RootMotion`
  (plus `RootMotionRot` to also take the turn) and play it on channel 0. The DLL does not
  need to do anything.
- **Leaving:**
  - When channel 0 starts a non-root-motion anim while in PHYS_RootMotion,
    `LockRootMotion(0)` and `setPhysics(PHYS_Walking)` run.
  - Any `setPhysics` away from 12 while locked (`AActor::setPhysics` 0x103113ab) runs
    `LockRootMotion(0)` and then **`eventRootMotionInterrupted(NewPhysics)`**.
  - `UpdateAnimation` sets slot+0x60 when the channel-0 anim ends while locked.
- **`LockRootMotion(mode)`** (0x1030b591 -> 0x105543e0) stores the mode in +0x1C4:
  - 1 = start: stores the actor location, the root bone coords from the last pose (+0x2A8)
    and the rotation.
  - 3 = snap/unlock.
  - 4 = continue from the current delta.
  - 5 = rebase.
  - 0 = off.
- **Extraction:** `AActor::physRootMotion` (0x1030d431) reads
  `USkeletalMeshInstance::GetRootLocation` and, if `bUseRootRotation`, `GetRootRotation`.
  - These read the skeleton's **root bone** (bone 0) as captured during `GetFrame` (+0x2A8 /
    +0x2D8).
  - `bZeroRootMotion` zeroes the movement.
  - The move goes through `XLevel->MoveActor` (vtbl 0x94) or FarMoveActor (0x98) when
    collision is off.
  - If the pawn steps off a ledge, it sends `eventMayFall`. With bAllowRootMotionZToFall
    or an AI fall check, it sends `eventFalling` and runs `setPhysics(PHYS_Falling)`.

## 4. Bone controllers, pose caching and off-screen skeletons

### Setting controllers

- `SetBoneRotation(name, rot, Space, alpha, preCalculatedBone)` (0x10307284) and
  `SetBoneLocation(name, trans, alpha, pre)` (0x10304b7e) write to the +0x12C array. They
  are applied in **parent-local space** before the hierarchy is accumulated:
  - The rotation is scaled by alpha and multiplied into the bone's local coords.
  - The translation is `alpha * trans`, added to the local origin.
  - **The `Space` argument of SetBoneRotation is stored but the pose build never reads it.**
- `SetBoneDirection(name, rot, trans, alpha, Space, pre)` (0x1030771b -> 0x10558590) writes
  to the +0x138 "director" array. Directors are applied **during the hierarchy walk**, after
  the bone's global coords are computed and before its children. The Space switch is in `GetFrame`
  around 0x10564233 (the callback call is at 0x1056427c). The rotator is scaled by alpha (rotation alpha 0x30), then
  combined according to `Space`:

  | Space | What it does |
  |---|---|
  | 0 | Rotation in mesh-component axes about the bone pivot (`R * Transpose(bone)`). |
  | 1 | Relative to the actor's mesh base coords (+0xD4). |
  | 2 | **World-space** rotation through `MeshToWorld` (the spine uses this when aiming, and so does Hips orient). |
  | 3 | World-space absolute (replaces the orientation). |
  | 50 | Rotation in the **bone's own local axes** (`bone * R`), used for the spine and dog spine. |
  | anything else | Calls the director's **world-spacer callback** (+0x38) if one is set, otherwise the identity. |

  The translation (+0x20) is converted to mesh space with `Inverse(+0xD4)` and added with
  alpha (+0x34).
- **`preCalculatedBone`** is the bone index. A value ≥ 1 skips `MatchRefBone(name)`, while
  0 or less makes it look up the name. The entry is still keyed by **name**, so one director
  exists per bone name, with a limit of 256 per instance. Root (index 0) can never be
  passed precalculated.
- The world-spacer callback is set with `SetWorldSpacerFunction(name, fn, pre)` (vtbl 0x120,
  0x10309a7a). It only works on a bone that already has a director. The call is at
  0x1056427c:

  ```c
  FCoords* __cdecl fn(FCoords* ret, AActor* owner, int boneIndex, int directorIndex,
                      USkeletalMeshInstance* inst);
  ```

  It returns the bone's new axes in mesh space. The engine keeps the bone's origin. Parents
  in `inst+0xB4` are already final, and children inherit the result. EonEngine's
  `FUN_10743290` uses this for Space 4-13 (bone-pair aim frames: 5/6/7, 8/9/10, 11/12/13)
  and 0x33-0x3F (a quaternion slerp by alpha toward precomputed aim frames).

### Pose caching

`USkeletalMeshInstance::GetFrame` (0x1030ab6e -> 0x10561670) rebuilds the pose at most once
per engine tick. The cache key is GTicks plus the channel-0 frame, unless +0x1B8 forces a
rebuild.

`GetBoneCoords` (0x1030562d -> 0x10553280) calls `GetFrame(actor, 0, 0, 0, &n, 2)` itself
when the cache is stale. **So `GetBoneCoords` returns this tick's pose and builds it if
needed.** The exception is a `bStasis` actor: then it returns the actor's Location and
Rotation, not a bone. `AActor::GetBoneCoords` returns zero coords if the actor is
`bDeleteMe`.

### Off-screen skeletons

1. **Pawns in `bStasis`** get no `AActor::Tick` at all and no anim time, and `GetBoneCoords`
   returns the actor's own coords. This matches what we measured ("off-screen not posed").
   - `Pawn.default.bStasis = True`, but UnrealPawn and therefore AdventPawn set it False.
   - `Controller.PendingStasis` and `SetStasis` can put a pawn back into stasis.
   - `AController::Tick` (0x10303535) only wakes it (`WakeFromStasis`) once the pawn has
     been rendered within 5 s.
2. **Frame skipping:** `Pawn` defaults to `bCanSkipFrames=True`. Each frame `ULevel::Tick`
   (0x1030bd2f) sets `bTickWasSkippedThisFrame` on every other frame for actors that are
   not player-controlled. `AActor::Tick` then skips the tick (saving dt in fMissedTickTime)
   when the actor has not been rendered for over 5 s (`XLevel time - LastRenderTime > 5.0`,
   double at 0x106c96d8). Its controller skips too. **Unrendered AI tick at half rate** with
   a doubled dt, and so do their anim updates.
3. **One frame late:** `CalculateBoneLocations` builds the pose early in TickSpecial. Bone
   controllers that script sets **later in the same tick** only show next tick, and the
   render reuses the cached pose. `BoneRefresh()` (ForceBoneRefresh 0x10310ac8) busts the
   cache and rebuilds.
4. **`bForceVisible`** (Actor 0x2C bit 0x200) makes
   `USkeletalMeshInstance::UpdateAnimation` (0x10305925 -> 0x10552970) call `GetFrame`
   **every tick**, and also forces `UpdateRenderData`. It does not force drawing. This is a
   script-only way to keep skeletons posed off-screen.

There is no other LOD skip for animation. `bAnimByOwner` makes the instance copy the owner's
pose (in GetFrame and UpdateAnimation).

## 5. Latent anims and AnimEnd

- `UpdateAnimation` advances every blend slot.
  - A negative rate means a speed-relative rate (`-rate * |Velocity|`).
  - Real-time slots use the unscaled level dt.
  - AnimNotifies fire through `notify->vtbl[0x64](inst, actor)`.
  - At the end of a non-looping anim with notify enabled (`EnableChannelNotify`) it calls
    `Actor->NotifyAnimEnd(channel)` (vtbl 0xC4).
- `APawn::NotifyAnimEnd` (0x10302f13) **sends `AnimEnd(channel)` to the Controller** if the
  Controller's current state probes `AnimEnd`. Otherwise it goes to the Pawn. This is the
  native link that lets AI states react to animation.
- `FinishAnim` (`execFinishAnim` 0x10303f30, then `StartAnimPoll`) is **time-based**. It sets
  `LatentFloat = 1 / GetActiveAnimRate(ch)`, the full length of the clip, and
  `PollFinishAnim` counts that down. So it waits a whole clip length from the moment it is
  called, whatever the current frame or a later rate change.
  - Latent code 0x181 is used when the channel is animating and not looping. 0x182 is used
    otherwise (not followed further).
  - `AController::StartAnimPoll` (0x10309061) does the same on the Pawn's mesh. Rate 0 gives
    a wait of 1e9 s, which is effectively forever.

## 6. Hook points, best first

1. **Foot IK and stride correction through the world-spacer callback.** No code patch is
   needed. From the DLL, for each pawn:
   1. Create a director on `LeftUpLeg/LeftLeg/LeftFoot` (and the right side) with
      `SetBoneDirection(bone, rot(0), vec(0), alpha=1, Space=99, pre)` (vtbl 0x11C).
   2. Call `SetWorldSpacerFunction(bone, MyFn, pre)` (vtbl 0x120).

   `MyFn` runs inside the hierarchy walk with the animated parent already final. It can:
   - trace the floor (`XLevel->SingleLineCheck`),
   - solve two-bone IK (thigh first, then calf, whose parent is already updated),
   - and return the new axes.

   Lower the pelvis with a director translation (+0x20/+0x34) or `SetBoneLocation`. This is
   applied before skinning, so the same frame shows the change. Do not use the names
   EonEngine already drives (`spine*`, `Hips`, shoulders and UpLegs on dogs, aim bones), or
   chain onto them. A hook after `GetFrame` returns would be too late: skinning happens
   inside `GetFrame`.
2. **Keep AI posed off-screen:** set `bForceVisible=True` and `bCanSkipFrames=False` on the
   AI pawn classes or per spawned pawn, and make sure nothing puts them in `bStasis`. A DLL
   alternative is to clear 0x40 bit 0x400 in a `ULevel::Tick` post-hook. For bone reads right
   after setting controllers, call `BoneRefresh()`.
3. **Locomotion:** hook `AEonPawn::UpdateMovementAnimation` (thunk 0x10701e1f, or vtbl slot
   0x220) and call the original. Afterwards, override:
   - the rate, from foot travel per cycle (`GetBoneLocationAtFrame` on the feet) and not
     the linear `|V|/GroundSpeed`, which stops foot sliding;
   - the weights, with smoothing or hysteresis on the cos² weights;
   - the walk/run window (280-350) and the turn threshold (±1000 yaw/s).

   Patch instruction operands, not the shared `.rdata` constants. 0x106c8c70 (1000.0) and
   friends are used elsewhere. Add a stride warp (stretch the legs with SetBoneLocation)
   when the anim rate is clamped.
4. **Fewer script events per tick:** `InputSpeedChange` re-fires every tick outside the
   band. `CheckAnimTasks`, `SetHeadTrackingToLookAtVector` and `GetAimLocation` are also
   called every tick per pawn. These are cheap wins if AI counts go up.
5. **Karma motors for powered ragdolls:** `KRPROJoint` (MdtRPROJoint) can bind two ragdoll
   bones through `KConstraintBone1/2`. It has soft linear and angular strengths
   (`KLinearStrength/KAngularStrength`; `LevitationJoint` uses 200). `KAnimatedBoneJoint`
   (used by AdventPawn.animatedJoint) is a subclass of it.
   - `AKRPROJoint::KUpdateConstraintParams` (0x103054a2) only pushes the strengths
     (FUN_105c3510 / FUN_105c34e0).
   - `physKarma` (0x103046e2) moves the position target to the joint actor's Location every
     tick (FUN_105c3390).
   - `KRelativeQuat` is only applied at creation.

   A DLL that calls the MathEngine "set relative quaternion" on the joint handle
   (`FUN_105c31d0(model)`) every tick, with each bone's animated local rotation, would give
   a PD-style orientation drive per bone. That is a powered ragdoll without Jolt. Next
   step: find the setter among FUN_105c3xxx, near the two strength setters.
6. **Root motion** needs no hook. Use anim groups (section 3). Watch the `RootMotionInterrupted`
   event and the bool at Pawn 0x268 bit 0x400.

## Reproducing

The work files are in `%TEMP%\claude\...\scratchpad\decomp_anim\`. They are not in git
because they come from game binaries:

- `proj/`: Ghidra projects AdvEngine, AdvEonEngine and AdvEonCharacters, fully analysed.
- `out/*.c`: every function decompiled, one file per DLL, with a `.index.txt` beside it.
- `out/e_*.c`: excerpts.
- `getframe.asm` and `cnag.asm`: disassembly.

Scripts:

- `scripts/DumpAll.java`: decompile everything into one file.
- `InstrDump.java`: disassemble a range with symbol names.
- `exports.py`, `vt.py` (resolve vtable slots to export names) and `rd.py` (read float
  constants).

Running headless needs `JAVA_HOME=Documents\Tools\jdk\jdk-21.0.12.1+1`.

## Tested in game: foot IK (2026-10-09)

Hook point 1 works as written. AdventMod/native/footik.c + Classes/ModFeet.uc (write-up with
the numbers: AdventMod/FEET.md). What the game confirmed or corrected:

- `SetBoneDirection(name, rot 0, vec 0, alpha 1, Space 99, boneIndex)` (vtbl 0x11C) then
  `SetWorldSpacerFunction(name, fn, boneIndex)` (vtbl 0x120) on leftUpLeg/leftLeg/leftFoot and
  the right side: the callback runs inside the hierarchy walk in bone order (thigh, calf, foot),
  with the signature above (`FCoords* __cdecl fn(FCoords* ret, AActor*, int bone, int director,
  USkeletalMeshInstance*)`; EonEngine's own FUN_10743290 has the same prototype). The engine
  copies the 12 floats and keeps the bone's origin. Children follow the returned axes in the same
  frame: the lift asked for is the lift drawn (asked z -1078.1, got -1078.1).
- The vtable slots 0x11C/0x120/0x124/0x13C of a pawn's mesh instance are exactly the export
  thunks (SetBoneDirection, SetWorldSpacerFunction, MatchRefBone, MeshToWorld): a strict check.
- The per-bone FCoords (+0xB4, stride 0x30): rows are the rows of the local-to-mesh rotation
  (mesh = R * local). Decided at run time from the ref skeleton's child position (0.00 vs 30.44).
- `FMeshBone` (USkeletalMesh +0x1DC, count +0x1E0, stride 0x40) is not UT2004's layout: FName +0,
  Flags +4, quat +8, position +0x18, length +0x24, ParentIndex **+0x34**, NumChildren +0x38, two
  pointers at +0x2C and +0x3C.
- `MeshToWorld()` (vtbl 0x13C, returns an FMatrix through a hidden pointer) is safe to call from
  the callback; world = (x, y, z, 1) * M as row vectors. The mesh draws at Location + PrePivot
  (0x1B4). DrawScale 0x1A4, DrawScale3D 0x1A8.
- `ULevel::SingleLineCheck` (export 0x1030106e; `(FCheckResult&, Source, End, Start, flags,
  FVector Extent)`, returns 1 for no hit, Hit.Location at +8) is safe from inside the pose build:
  2 traces per pawn per pose build cost ~1 us each (whole callback 1.0-1.3 us).
- Alpha 0 on the director plus a NULL world-spacer makes it inert (the removal path).
- Director translation (+0x20) is a mesh-space move of one bone; a pelvis through it would detach
  the thigh skin from the hips, so the pelvis drop is PrePivot from script. Hips stays
  EonEngine's.
- Sanity rules that turned out to matter: the clip stands on the collision cylinder's base, not
  on a trace under the pawn's centre (on a step edge the cylinder is held up by the edge, 29
  above the floor under its centre); a surface higher than MaxLift above the base (a crate, a
  bench) must not count as ground, or a foot swung over it climbs onto it; a crouch lowers
  Location by (78 - 55) and raises PrePivot by the same, so the base is Location + PrePivot - the
  standing height, and anything that moves PrePivot from script must add to it, not set it.
