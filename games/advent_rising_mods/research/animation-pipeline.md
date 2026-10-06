# Making new character animations for Advent Rising

How the mod gets new skeletal animations into a 2005 Unreal Engine 2 game without the
original tools: two sources (text-to-motion generation, and hand-keyed poses), one path into
the game, and what we learned about making them read well. Written 2026-10-06.

## 1. The path into the game

```
clip (frames of bone rotations)  ->  tools/make_psa.py  ->  .psa (ActorX animation file)
    ->  #exec ANIM IMPORT in a .uc class  ->  AdventMod.u holds a MeshAnimation
    ->  at run time: Pawn.LinkSkelAnim(set); Pawn.PlayAnim(clip, rate, blend, channel)
```

- **Clip format** (what every source produces): a JSON file in `AdventMod/Anims*/`:
  `{fps, frames: [{root: [x,y,z], rot: {bone: [qx,qy,qz,qw]}}]}`. Rotations are per bone,
  relative to the mesh's reference pose (a T pose), local to the parent. Bones not listed keep
  the reference pose.
- **Skeleton**: `tools/make_psa.py` reads the bone tree from one of our exported meshes
  (`Documents\AdventRising_meshes\marine.psk`, the humanMale2 skeleton, 61 bones). Every human
  in the game, Gideon included (83 bones: the same core plus hair and face bones), shares the
  core bone names, so one .psa plays on all of them. Mesh space: -Y is up, +X the body's left,
  +Z forward, about centimetres.
- **The .psa**: `python tools/make_psa.py <out.psa> marine <clip folder>`. Without a folder it
  builds the death set (`AdventMod/Anims`) and also writes `ModDeathClips.uc` (which clip fits
  which hit zone). The build (`AdventMod/build.ps1`) runs it for both sets into the game's
  `AdventMod\Anims\`, where the `#exec ANIM IMPORT` lines of `ModDeathAnims.uc` and
  `ModBladeAnims.uc` find them (`COMPRESS=1 MAXKEYS=999999 IMPORTSEQS=1`, then
  `ANIM DIGEST USERAWINFO`).
- **Playing**: `LinkSkelAnim` adds our set to the pawn's mesh at run time (the game's own
  set stays). Full-body clips (deaths) go on channel 0 and replace the game's animation;
  partial clips go on a spare blend channel: `AnimBlendParams(9, 1.0, 0.12, 0.2, 'spine1')`
  makes channel 9 drive the bone `spine1` and everything above it, so the blade swings move
  the torso and arms while the game's own punch move keeps the legs, footwork, timing and
  hit checks. `AnimBlendParams(9, 0.0, 0.2, 0.2)` hands the body back.
- **Verifying**: hidden harness runs (`AdventMod/test_run.ps1`) with pilot steps
  (`press melee`, `shotp` every 0.1 s) and a contact sheet of the captures; the camera can be
  pitched down with `turn 0 55 0.4` (positive pitch looks down). Death clips log their pose in
  `AdventNative.log` (bone heights over the floor).

## 2. Source A: text-to-motion with KIMODO

NVIDIA's KIMODO (text to full-body motion, SOMA skeleton) is installed at
`Documents\Tools\kimodo` (venv, ~9 GB VRAM, about 45 s per prompt for 3 takes). The text
encoder is a local NF4 copy selected by environment variables; the scripts set them.

1. Prompts: one line per clip in a prompt file, `name|one sentence|seconds`
   (`tools/death_prompts.txt`, `tools/blade_prompts.txt`). One sentence: KIMODO splits at
   full stops. Say the whole action and the end state ("...and returns to a ready stance").
2. Generate: `bash tools/kimodo_deaths.sh` / `tools/kimodo_blade.sh` -> `out/<set>/<name>/
   <name>_00..02.npz` (3 takes, seed 7). Announce the GPU use to the other chats first.
3. Retarget: `<kimodo venv python> tools/kimodo_retarget.py <take.npz> <ClipName> [start end]`
   -> `AdventMod/Anims/<ClipName>.json`. SOMA and Advent both rest in a T pose with joint
   axes along the world's, so each Advent bone takes its SOMA joint's world rotation; the two
   spaces differ by a mirror (M = diag(1,-1,1): R becomes M R M). The root key is turned a half
   turn about Y and its position mirrored (-x, -y, z). Verified numerically in the game.
4. Pick takes by numbers before looking: `posed_joints` in the .npz gives joint positions per
   frame; the right hand's sweep, height range, peak speed and its time tell a good swing
   from a timid one (the blade session printed a table of these for 15 takes).
5. Build (`build.ps1`) and check captures.

What KIMODO is good at: believable whole-body falls, staggers, collapses (the death clips),
root motion included. What it is not: stylised attacks. Its swings are motion-capture-polite,
with no anticipation, no snap and small arcs. `tools/anim_cool.py <in> <out> [exaggerate=1.5]
[snap=0.35] [anticipation=1.6]` re-times a generated clip (slow wind-up, fast strike window,
overshoot after it) and pushes poses away from the first frame, but it can only stretch what
is there: a timid swing stays timid.

## 3. Source B: hand-keyed poses on the animation principles

For attacks we key them ourselves (`tools/make_blade_clips.py`), the way an animator would:
a few extreme poses on a timeline, with the easing chosen per segment. Each bone channel is
a list of keys `(time 0..1, degrees, easing)` read by `key(t, keys)`:

- `out`: fast start, slow end (a wind-up arriving and settling),
- `in`: slow start, fast end,
- `snap`: nearly linear, for the strike,
- `smooth`: ease both ways (the settle).

The principles, as used in the blade swings:
- **Anticipation**: 0.28 s of wind-up the other way (arm back past the shoulder, torso twisted
  the opposite way, head leading), then held for a beat (two keys 0.02 s apart).
- **Snap**: the strike is 4 frames (0.12 s) over about 220 degrees of arm swing.
- **Follow-through and overshoot**: the arm and torso run 10-20 degrees past the end pose
  for 0.08 s, come back a little, then settle over the rest of the second.
- **Exaggeration**: torso twist 55-65 degrees from the lower spine, a back lean into the
  strike, the overhead chop folds the body past the knees and drops the root.
- **Arcs**: a swing is a rotation about one axis per bone, so the hand travels an arc by
  construction; the elbow bends in the wind-up and straightens through the strike.
- **Secondary action**: the free arm counters the swing, the head turns first.

Conventions for the numbers (measured in the game): right arm points -X; about Y, + swings it
forward then across the chest; about Z, - lowers it. Left arm points +X; about Y, - is forward;
about Z, + lowers it. Spine about Y twists the shoulders (+ turns the chest left); about X
pitches (+ leans back). Root +Y is down (a drop is positive).

Iteration loop: edit a key, run `make_blade_clips.py`, build, one hidden run with captures.

## 4. Using it elsewhere

- Deaths by hit zone: `ModReact.DeathAnim` picks a clip from `ModDeathClips` for the zone of
  the killing blow and plays it full body; the body then lies in the clip's last pose
  (`bDeathAnimRagdoll` off: starting a ragdoll mid-clip crashed the game).
- Powered ragdolls (physics plan step 2): `GetBoneLocationAtFrame(clip, bone, t)` returns the
  clip's bone positions in world space for a pawn that has the set linked, which is what the
  steering compares the ragdoll against.
- New sets: copy the `ModBladeAnims.uc` pattern (one class, one `#exec ANIM IMPORT`, one
  `MeshAnimation` default), add a `make_psa.py` call to `build.ps1`, play on the channel you
  want.
- Unreal II: the same .psa path works there through UnrealEd's import (see the U2 notes), the
  retarget differs only by skeleton.

## 5. Gotchas

- UnrealScript has no `1e9` literal: write `1000000000.0`. (It compiled and misbehaved.)
- `#exec` paths are relative to the package folder inside the game, not the repo: the build
  must write the .psa into `<game>\AdventMod\Anims\`.
- A clip plays on a pawn only after `LinkSkelAnim`; `HasAnim` checks it.
- Blend channel numbers the game uses are 0 (full body) and a few arm channels; 9 was free.
- Hidden captures from behind the player hide most of an attack; pitch the camera down.
