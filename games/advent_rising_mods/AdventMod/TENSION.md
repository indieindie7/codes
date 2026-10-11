# Muscle tension layer (design 2026-10-11; parts 1-2 built in ModReact, part 3 not)

Built notes: powered ragdolls only start on the humanMale2 skeleton (humans, not Seekers).
The force cap is `PowerMaxAccel * max(A_r, PassiveDamp)` so the passive damping still acts when
limp. Ragdoll shots reach `Spasm` through ModGore.CorpseHit (Dying pawns skip NetDamage).
Tested 10-11 on a spawned Marine in level04sectiona: tension 90 -> 3 over 0.7 s; a shot at
0.2 s logs a reflex (only a small bump while A is still above SpasmU); bTension=False keeps the
old linear fade. To kill without gibbing in a pilot test, keep the hit under health + GibOverkill
(the pilot's HURT is scaled x1.5: HURT 275 on the 400-health Marine).

User 2026-10-11: "lets go with the muscle tension layer first, we will do some more softbody
animation testing in advent there. specially for ragdolls".

Idea taken from Terra (EPFL, MyoFullBody: Hill-type muscles drive a rigid skeleton). We don't simulate
muscles or tissue. Each body gets a few **tension** values (0 = limp, 1 = fully tensed) with
muscle-like rise and fall times, and that one value drives the two systems we already have:
the powered ragdoll push (ModReact, physics plan step 2) and the flesh springs (ModJiggle, JIGGLE.md).

## 1. The tension value

Per ragdoll, per region: torso (hips, spine1, Spine3), head, left arm, right arm, left leg, right
leg (map the 12 `PowerBones` to 6 regions).

- Drive `u` (what the body "wants") is set by events; activation `A` follows it (first-order
  activation dynamics, Zajac 1989):
  `A += (u - A) * Dt / tau`, with `tau = TauUp` (0.025 s) when `u > A`, else `TauDown` (0.08 s).
- Death: `u = DeathEffort` (0.9) for `EffortTime` (0.15 s): the body still fights for a moment.
  Then `u` falls linearly to 0 over `LimpTime` (0.45 s); `A` lags it, so the fade is a curve, not a line.
- Shot while dying (the region's `A > 0.05`): a reflex spike, `u = max(u, SpasmU)` (0.7) for
  `SpasmTime` (0.06 s) in the hit region only. A body that is already limp stays limp.
- Optional, later: legs keep `u` a little longer than arms (knees buckle last), a per-class
  `DeathEffort` (Seekers 1.0, humans 0.8).

## 2. Powered ragdoll (ModReact.PoweredTick, the loop around `KAddImpulse`)

Today: `Fade = 1 - T / PowerTime` multiplies the whole push.
With tension, per part `b` in region `r`:
- spring   `PowerSpring * A_r` (muscles pull toward the clip's pose only while tensed)
- damping  `PowerDamp * (PassiveDamp + (1 - PassiveDamp) * A_r)`, PassiveDamp 0.3
  (tissue still resists motion when limp; stops the flail at the end of the fade)
- force cap `PowerMaxAccel * A_r` (a weak muscle can't throw the limb)
- `PowerTime` becomes "until every `A_r` < 0.02", with the old 0.7 s as the upper limit.

Config: `bTension` (False until tested; False = today's linear fade, unchanged), TauUp, TauDown,
DeathEffort, EffortTime, LimpTime, SpasmU, SpasmTime, PassiveDamp.

## 3. Flesh springs on dying bodies (ModJiggle + native/jiggle.c)

Today ModJiggle releases a pawn when it dies or goes ragdoll (`JiggleOff`), so corpses don't
jiggle. Proposal:
- keep the hook on Seeker infantry ragdolls (only they have the jiggle mesh);
- a new native command `JiggleTension <pawn> <class> <A>`: scales that pawn's k by
  `(LimpStiff + (1 - LimpStiff) * A)`, LimpStiff 0.35, and its gain by `1 + LimpGain * (1 - A)`,
  LimpGain 0.5: relaxed flesh is softer and swings more. Torso A for belly/chest/hump/throat, the
  arm and leg regions for J_Arm*/J_FrontArm*/J_Thigh*;
- the landing hit: when a part's speed drops by > 150 u/s in one tick (it hit the floor), send
  `JiggleHit` with that drop, so the belly wobbles on impact.

Unknown, test first: whether the bone director still runs, and looks right, on a pawn in
PHYS_KarmaRagdoll (Karma writes the bone transforms; the jiggle bones are leaf bones outside the
.ka, so it should, but nothing has tried it). If it doesn't, parts 1-2 still stand alone.

## Test list

1. `bTension=False`: deaths identical to today (log lines unchanged).
2. `bTension=True`, `bGoreLog`: the per-0.1 s "powered" log line gains the 6 A values; check
   the curve (rises within ~0.05 s, about 0.6 s to limp).
3. Side by side, 10 Seeker and 10 human deaths, wincap clips: does the collapse read as
   "fighting, then going limp" instead of a puppet with its strings fading?
4. Shooting a falling body: the hit limb jerks once; shooting a limp body: nothing.
5. Part 3 only after 1-4: the jiggle director on a ragdoll, then corpses landing.
6. The usual: a 2-minute fight, no crash, AdventNative.log tail clean.
