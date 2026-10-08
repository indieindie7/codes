# How UE2 games made Karma ragdolls behave (for AdventMod, build 2226)

2026-10-08.

**Sources:**
- [1] UT2004's own `KarmaData\*.ka` (local Steam install).
- [2] UT2004 script: `xPawn`, `KarmaParams*`, `LevelInfo` (Documents\UT2004_extract).
- [3] Advent's `AdventPawn` (AdventRising_src).
- [6] Unreal Wiki: [Karma](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma.html), [Ragdoll Injury System](https://unrealarchive.org/wikis/unreal-wiki/Legacy:Karma_Ragdoll_Injury_System.html), and the BeyondUnrealWiki GitHub mirror.

**Removed (2026-10-08, the user's call):**
- Everything that came from leaked Epic engine source, and from an unlicensed copy of another game's scripts.
- Engine-internal claims (crash mechanisms, KWake/KIsAwake/KAddImpulse internals, damping overrides, static-mesh Karma collision, what KFreezeRagdoll changes) are left out. They are to be re-established only from Advent's own binaries (our Engine.dll decompile), public docs and our own tests.

**Other notes:**
- The UDN pages (RagdollsInUT2003, KarmaAuthoringTool) now redirect, and archive.org is blocked.
- SWAT 4 and Tribes: Vengeance use Havok, so they don't apply.
- Unit: 1 Karma unit = 50 UU.

## 1. .ka authoring: Epic's Human.ka [1] compared with make_ka.py

**Bodies:**
- 15 bodies, with no head, hand or foot parts. The head sphere is geometry on the neck part.
- spine, spine2 and the clavicles are `dynamics_only` (mass, no contacts).

**Joint limits:**
- Knee hinge −0.29..1.29 rad; elbow −0.17..1.57.
- Neck and clavicles are hinges ±0.28.
- Skeletal cones are elliptical: thigh 0.79×0.40, upper arm 0.52×0.79, spine 0.31→0.15.
- Twist 1.57 everywhere; stiffness 1000, damping 1.

Ours use round cones of 1.0–1.3 and twists of 0.2–0.8.

**Mass:** about 0.19 in total; ours was 1.0.

**NO_COLLISION:**
- UT lists 19–25 pairs per ragdoll, including non-adjacent ones (l thigh–r thigh, upperarm–spine1, neck–spine1).
- Our note that sibling pairs crashed should be re-tested.

**Non-humans:** UT has no quadruped. Skaarj.ka is a biped plus a 3-part tail chain, so the human template is the nearest model for the hound.

## 2. Settings in UT2004 [2]

- KFriction 0.6, KRestitution 0.3, KImpactThreshold 500.
- RagDeathVel 200, RagDeathUpKick 150, RagShootStrength 8000.
- Damping 0.15 / 0.05, KVelDropBelowThreshold 50, KBuoyancy 1, KStartEnabled.
- Corpses de-res after 13 s.

**Ours:** friction 0.6, restitution 0.1, impact threshold 500, death velocity 250, upkick 60, shoot strength 8000.

**Level settings** (script-declared in both games):
- `RagdollTimeScale` (UT's slow-motion death mutator uses 0.3) and `MaxRagdolls`.
- Advent's LevelInfo declares `bKStaticFriction`, "better ragdoll/ground friction, more CPU" [3]. Worth trying.
- `bDestroyOnSimError` is a KarmaParams property in the script [2]. What it does in Advent has to be checked in our own decompile.

## 3. Get-up, from public documentation [6]

The Ragdoll Injury System's documented recovery:
1. KFreezeRagdoll.
2. Restore bCollideWorld and SetCollision.
3. Relink the mesh to a dummy, then back to the original.
4. Blend saved bone directions out with SetBoneDirection, alpha 1→0.

The wiki rejects bone lifters for this; Epic notes that collision must be off while lifters run. Very short ragdolls end as a "ball of limbs". No UE2 game shipped motor-driven Karma ragdolls.

## Next steps (only from these sources plus our own tests)

1. **make_ka.py:** twist 1.57 and mass about 0.2 (done, `MAKEKA_OLD=1` for the old values), then elliptical cones, neck and clavicle hinges, and a re-test of wider NO_COLLISION pairs.
2. **Corpse settings:** try friction 1.3 with restitution 0.2 (heavier, grippier corpses), `bKStaticFriction=True`, and `bDestroyOnSimError=False`. Measure each in game.
3. **Crashes:** log every Karma message in advent.log around a crash, and find the cause in our own decompile of Advent's Engine.dll.
