# Advent Rising physics: what Karma gives us, what later games did, and the plan

Written 2026-10-05. Advent Rising runs Unreal Engine 2 (build 2226), whose physics is **Karma**
by MathEngine: rigid bodies, ragdolls and vehicles, compiled into Engine.dll with no source. The
PC release shipped no ragdoll definitions at all (`KarmaData\*.ka`), so every ragdoll in the game
today is one we wrote (`tools/make_ka.py`, humanMale2 and seeker so far). This note collects what
the engine still lets us change, what the games after UE2 did better and why, and the order to
try things in.

## 1. The levers Karma exposes

From the exported script source (`Engine.Actor`, `Engine.KarmaParams`, `Engine.LevelInfo`).
Everything below is callable from our mod's UnrealScript, no native code needed.

### Per body (`KarmaParams`, set in the .ka or at run time)
| Lever | What it does |
|---|---|
| `KMass`, `KSetInertiaTensor` | Weight and how it resists turning. Advent's defaults are generic; heavier torsos and lighter limbs make falls read better. |
| `KLinearDamping`, `KAngularDamping` | Air resistance. Higher values calm jitter at the cost of floppiness. |
| `KFriction`, `KRestitution` | Slide and bounce on contact. |
| `KActorGravScale` | Per-body gravity. Slightly above 1 for bodies makes deaths feel heavier. |
| `KMaxSpeed`, `KMaxAngularSpeed`, `KVelDropBelowThreshold` | Caps that stop the solver from flinging a body across the room. |
| `bKDoubleTickRate` | Steps this body's physics twice per frame: fewer tunnelled limbs. |
| `bKStayUpright` + stiffness/damping | A spring that keeps a body upright (for vehicles and standing things, not corpses). |
| `Repulsors` | Simple ray "wheels": push the body away from the ground along a ray. Vehicles. |

### Per ragdoll (`KarmaParamsSkel` and `Actor` natives)
| Lever | What it does |
|---|---|
| `KSkeleton` | Which .ka file: the bones, their shapes and the joint limits. **Joint limits live here.** |
| `KScaleJointLimits(scale, stiffness)` | Scales every joint's range and limit stiffness on a live ragdoll. A quick way to test "stiffer, less rubbery" without rebuilding the .ka. |
| `KSetSimParams(KSimParams)` | The solver's own knobs for this body: `MaxTimestep` (smaller = steadier), `ContactSoftness`, `PenetrationOffset`/`PenetrationScale`/`MaxPenetration` (how hard the floor pushes back), `Epsilon`, `GammaPerSec`. |
| `KSetSkelVel(vel, angVel, add)` | Sets or adds velocity to every bone at once. |
| `KAddImpulse(impulse, position, bone)` | A kick on one bone. |
| `KAddTorque`, `KAddAngularImpulse` | Spin. |
| `KAddBoneLifter(bone, liftCurve, lateralFriction, softness)` / `KRemoveLifterFromBone` / `KRemoveAllBoneLifters` | Pulls a bone up along a curve over time. UT2004 used it for ragdolls that writhe and get up. Present in Advent, unused by the game. |
| `KFreezeRagdoll`, `KMakeRagdollAvailable`, `KIsRagdollAvailable` | Stop a ragdoll, hand its slot back. (Freezing leaves the pawn `PHYS_Falling` without world collision, the bug that dropped bodies through the floor; ModReact works around it.) |
| `bKDoConvulsions`, `KConvulseSpacing`, `bRubbery` | The stock twitch and a softer joint mode. |
| `KShotStart/End/Strength`, `bKImportantRagdoll` | The impulse the game applies on death, and whether the body survives the ragdoll cap. |

### Per level (`LevelInfo`)
| Setting | Default | Note |
|---|---|---|
| `KarmaTimeScale` | 0.9 | Physics runs 10% slow in Advent. 1.0 is worth a try. |
| `RagdollTimeScale` | 1.0 | Ragdolls only; 0.8 gives the slight slow-motion fall many games fake. |
| `MaxRagdolls` | 4 | Why bodies get taken so fast. 8-12 is fine on a modern PC. |
| `KarmaGravScale` | 1.0 | |
| `bKStaticFriction` | | |

### Events
`KImpact` (a body hit something hard; `KImpactThreshold` sets how hard) and `KVelDropBelow`:
hooks for impact sounds, blood on landing, and settling.

## 2. What games after UE2 did better, and the ideas behind it

### The solver
Karma's joints drift and explode under stress because of how it solves constraints (a Lagrange
multiplier solver on forces). The next generation moved to **sequential impulses** and then to
**position-based** solving, which are simpler and far more stable:
- Erin Catto, **"Iterative Dynamics with Temporal Coherence"** (GDC 2005): sequential impulses,
  adopted by Havok, Bullet, PhysX and Box2D. Stable stacking, joints that hold.
- Müller, Heidelberger, Hennix, Ratcliff, **"Position Based Dynamics"** (2006) and Macklin,
  Müller, Chentanez, **"XPBD"** (2016): solve on positions; cloth, ropes, soft bodies and
  ragdolls all in one framework. Current engines' character physics lean on this.
- Catto, **"Soft Constraints"** and **"Solver2D"** (2024): a side-by-side of every solver type,
  with code.
- Featherstone, **Rigid Body Dynamics Algorithms**: articulated bodies solved as a chain
  (reduced coordinates) instead of separate bodies plus joints. PhysX 3 and UE4 use this for
  ragdolls that can never come apart.
- Jorrit Rouwé, **"Architecting Jolt Physics for Horizon Forbidden West"** (GDC 2022). Jolt is on
  GitHub (MIT), deterministic, fast, with ragdolls and character controllers built in. The engine
  to use if Karma is ever replaced.

### Ragdolls that look alive
- **NaturalMotion Euphoria** (GTA IV, Red Dead Redemption, Max Payne 3): the ragdoll is driven by
  muscle controllers and a balance model, so people stagger, grab, brace and fall believably.
  Closed, but the idea is simple to state: motors pull joints toward a target pose while physics
  resolves the rest.
- David Rosen, **"An Indie Approach to Procedural Animation"** (GDC 2014, Overgrowth): a few
  key poses plus physics and interpolation give convincing motion with tiny animation budgets.
- Michael Mach, **"Physics Animation in Uncharted 4"** (GDC 2017): blending animation and
  physics per body part, with powered ragdolls on hits.
- Surveys: Geijtenbeek and Pronost, **"Interactive Character Animation Using Simulated Physics"**
  (2012); Hodgins et al. on physics-based character control.

### The world
- **Red Faction: Guerrilla, GeoMod 2** (GDC 2010) and **Havok Destruction**: breakable
  structures.
- Fluids: see the BioShock note (Stam, SPH, position-based fluids, screen-space fluid rendering).

## 3. The plan, in order

### Step 1: fix the ragdolls we have (small)
- Joint limits per character in the .ka: knees and elbows one-way, hips and shoulders with
  believable cones, neck tight. Today's limits bend both ways.
- Solver settings on every ragdoll at spawn: smaller `MaxTimestep`, a little `ContactSoftness`,
  `bKDoubleTickRate` on, damping up a touch.
- `MaxRagdolls` to 8-12, `KarmaTimeScale` 1.0, `RagdollTimeScale` about 0.85.
- Measure with the pilot: bone heights over the floor after 3 s (ModReact's pose log already
  does this), and count of bodies that end up under the floor.

### Step 2: powered ragdolls (medium): the GTA IV look
For the first ~0.5 s after death, each frame: read the death clip's pose for that moment,
compare with the ragdoll's bone transforms, and apply `KAddImpulse` per bone toward the clip's
pose (position error times a gain, clamped), fading the gain to zero. The body follows the
animation while physics handles collisions, then goes limp. This replaces the clip-to-ragdoll
handoff that crashed on 2026-10-04 (starting a ragdoll from a mid-clip pose): here the ragdoll
starts from the live pose at the moment of death and is steered instead.
Variant for hits that don't kill: a short powered ragdoll on the hit limb only, then back to
animation (Uncharted 4's trick).

### Step 3: bone lifters and getting up (small once 2 works)
`KAddBoneLifter` on the spine and head of a wounded enemy makes them writhe and try to rise;
remove the lifters and they collapse. Good for the "not quite dead" moments the gore mod
already stages.

### Step 4: replace Karma with Jolt (large, only if 1-3 hit a wall)
Native: hook the engine's ragdoll update (the `PHYS_KarmaRagdoll` tick in Engine.dll, found by
tracing the way the shadow bugs were), run a Jolt ragdoll built from the same .ka data, write
bone transforms back into the mesh instance, keep Karma for everything else. Jolt's ragdoll
and skeleton pose APIs are built for exactly this. Weeks, not days.

## 4. Open questions
- Does Advent's Engine.dll honour `KSetSimParams` per body, or only the global defaults? (Test.)
- Does `KAddBoneLifter` work with our .ka skeletons? (UT2004 .ka files carried extra data for it.)
- The hound ragdoll crash is still unexplained; step 1 may or may not touch it.
