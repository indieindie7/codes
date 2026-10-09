# RAGE-style wall and ceiling traversal for Unreal II Skaarj

Research 2026-10-09. The user's ask: "do some research how rage hopping mutants use the wall and ceiling for navigation,
would love to import it here". No game files changed.

## Summary

1. **RAGE:** there is no published technical talk or postmortem. The one dev quote (Matt Hooper, 2010) describes placed
   spots that the AI picks at runtime: "opportunities for the AI to dynamically grab a rafter to flip around, or do a
   running wall kick off", played with over-the-top canned animations.
2. **id's later AI (DOOM 2016)** uses one jump animation warped at runtime to its target ("motion warping"), checks
   that the clip fits the arc, and uses per-attack tokens for fairness. id engines precompute jump links
   (van Waveren's AAS "reachabilities").
3. **Other games:**
   - Left 4 Dead climbing is procedural: hull traces find the ledge, then the closest of dozens of climb clips plays.
   - Half-Life 2 fast zombies use placed jump and climb nodes.
   - Prey uses placed wall-walk surfaces.
   - AvP 2010 and Dying Light: no public source on how their AI climbs.
4. **Cheapest version that reads well:** a telegraphed hop to a placed spot, a visible 0.5-1 s hold (the attack
   window), then a pounce. No real surface crawling.
5. **Unreal II already has most of the parts:**
   - the Skaarj leap state, with a trajectory solver and an anim notify;
   - mid-air `NotifyHitWall` during leaps;
   - `JumpSpot` (a jump link in the path network);
   - `PHYS_Spider`, which no U2 script uses (UnrealWiki: one plane only).
6. **Jump solving:** `SuggestFallVelocity` is UT2004-only. Use `EAdjustJump`, `UtilGame.VerifyTrajectory`, or a
   20-line solver of our own.
7. **Skaarj clips:** they have `MantleHang01` (a hang pose for gripping a beam), `Climb01`, side and forward flips,
   the leap's flip-slash, and jump-start and land clips per direction. There is no wall-cling or ceiling-crawl clip.
8. **Smallest playable version (about 1 day):** a "wall-kick". A leaping Skaarj that hits a wall in mid-air
   side-flips and re-aims at the player. Done as a controller subclass that U2Enemies swaps in; no map changes.
9. **Next (2-3 days):** the Avalon generator places cling markers under beams and on pillars and walls. A Skaarj
   picks one, hops on, hangs and roars, then pounces. The fuller version, routed through the path network with
   chained hops, is 1-2 weeks.
10. **Risks:**
    - getting stuck while hanging (needs a watchdog);
    - the stock behaviour controller fighting the new state;
    - hooking up the clips through the animation agent;
    - fairness: a roar cue, one leaper at a time, a short hold.

    Skaarj fire projectiles, so the U2 hitscan problem doesn't apply unless human NPCs get this.

## 1. How RAGE's mutants and Ghost bandits move

**Documented:**
- **Matt Hooper**, id design director, Game Developer, 6 Aug 2010
  (https://www.gamedeveloper.com/design/technology-design-i-rage-i-):
  - the Ghost clan is "thin and agile";
  - the AI programmers built a system with "opportunities for the AI to dynamically grab a rafter to flip around, or
    do a running wall kick off";
  - the look comes from the animators' "over-the-top animation treatment".
- **Previews and reviews:**
  - GamesRadar: "ceiling-slides and leaps from pole to pole" (https://gamesradar.com/updated-impressions-of-rage/2).
  - GamePro.de: wall runs, railing swings, cartwheel dodges
    (https://www.gamepro.de/artikel/rage-vorschau-fuer-playstation-3-und-xbox-360,1965582,seite2.html).
  - PC Gamer: mutants use "walls and railings to get the purchase necessary for an attacking leap"
    (https://www.pcgamer.com/rage-review/).
  - Game Informer dev diary
    (https://gameinformer.com/games/rage/b/ps3/archive/2011/07/28/do-you-know-your-enemies-you-will-after-watching-this-dev-diary.aspx).
  - Willits on AI that keeps moving
    (https://gameinformer.com/games/rage/b/ps3/archive/2011/08/18/rage-s-amazing-ai-is-no-accident.aspx).
- **Not found:** any GDC talk, slides or postmortem on RAGE or id Tech 5 traversal.

**What that means technically (inference):**
- **Placed markup, not procedural.** id engines precompute jump links, because sampling a detailed world at runtime
  is too expensive (van Waveren's AAS: https://www.cs.rochester.edu/u/brown/242/docs/QuakeIII.pdf).
- **Animation-driven.** A canned flip, kick or swing plays, and the body is nudged to land on the target. Unreal
  Engine 5 calls this motion warping (https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-warping-in-unreal-engine).
  DOOM 2016 imps use one jump clip adjusted at runtime, with fit checks
  (https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-).
- **Route choice.** A link is just another path edge with a cost, so a shortcut over a rafter wins when it is shorter.
- **Fairness (id's later rules).** Attack tokens per attack type, exaggerated distinct animations, and pain reactions
  that interrupt attacks. The flip is the telegraph, and nobody shoots mid-flip
  (GDC 2018 "Embracing Push Forward Combat in DOOM": https://gdcvault.com/play/1024940/Embracing-Push-Forward-Combat-in).

## 2. Other games

- **Left 4 Dead** (Mike Booth, slides 29-36:
  https://cdn.fastly.steamstatic.com/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf). Climbing is algorithmic:
  1. hull traces from low to high find the first clear height;
  2. a downward trace finds the ledge;
  3. stepping back finds the ledge's front edge;
  4. the closest of dozens of climb clips plays.

  Robust, but up only. The Hunter's wall pounce behaves like a mid-air wall hit that redirects the jump, behind a loud
  telegraph.
- **Half-Life 2 fast zombie:** placed `info_node` jumps and `info_node_climb` climbs
  (https://developer.valvesoftware.com/wiki/Npc_fastzombie).
- **Prey (2006):** placed wall-walk paths and gravity pads.
- **AvP 2010, Aliens: Colonial Marines:** no developer write-up found.
- **Dying Light:** only the player's parkour is documented
  (https://www.mcvuk.com/development-news/the-vaulting-dead-implementing-first-person-parkour-in-dying-light/).
- **Game AI Pro 2, "Dynamic Obstacle Navigation in Fuse":** traversal needs markup plus special animation states,
  which is why many games avoid it.

**Cheapest that reads well:** hop to a placed spot, a visible hold with a roar, then pounce. The hold is the "one
good frame": a Skaarj silhouette hanging off a beam.

## 3. Building it in Unreal II (checked in `Documents\Tools\u2_export`)

### Physics
- **`PHYS_Spider` (9)** (`Actor.uc:155`):
  - `Pawn.Floor` is the surface normal;
  - jumping off sets `Velocity = JumpZ*Floor`;
  - the Controller counts it as on-ground;
  - no U2 script uses it;
  - per UnrealWiki it works on one plane only and the pawn falls at the edge.

  A lab test for later (Araknids), not the base for the Skaarj version.
- **Scripted cling:** `PHYS_None` + `Velocity=0` + `SetLocation` (optionally `SetBase`), then back to
  `PHYS_Falling` to leap off.

### Jump solving
- `Controller.EAdjustJump(TargetLocation, BaseZ, XYSpeed)` (`Controller.uc:478`), used by `U2NPCControllerBot.BigJump`.
- **`UtilGame.VerifyTrajectory` / `VerifyLeapParameters`:** the stock Skaarj leap's solver
  (`U2NPCControllerBasic.uc` ~1314-1535). It solves the launch angle at a fixed speed and sweeps the arc.
- `Pawn.FitActorAt` checks that the landing spot fits.
- **Fallback solver:** `t = dist2D/speed`, `Vz = dz/t - 0.5*g*t`, then trace the arc in 4-6 segments.

### The stock Skaarj leap (`U2AI/U2NPCControllerBasic.uc`, AttackLeapState, ~3724-4004)
1. The engine fires `EnemyInLeapRange`.
2. If `LeapOdds` and `CanAttemptLeapAttack` pass, the Skaarj turns to face the player.
3. `GetLeapParameters` picks a high, low or max-range arc.
4. `SpecialAnimationLeap` plays the Golem action `U2_Leap`.
5. The `LeapBegin` notify (or a 1 s fallback) triggers `DoLeapAttack`: `Velocity = LeapSpeed*vector(LeapRotation)`,
   then `PHYS_Falling`.
6. In flight, `bFallingHitWallNotifications` is on, so **`NotifyHitWall` fires mid-air** (~3804). Stock code only
   plays a sound there.
7. A bump does damage. On landing the Skaarj waits, then `FinishedLeap`, which `SkaarjController` chains into an
   impale.

Tunables on `U2PawnBasic`: `LeapOdds`, `LeapMin/MaxRange`, `LeapHigh/LowSpeed`, `LeapHighOdds`, `OnlyLeapLowRange`,
`LeapDelay*`, `LeapMaxDamage`, `LeapToMeleeOdds`, `bLeapRequiresLOS`. U2SkaarjLight: odds 0.33, range 256-512,
speed 1024.

### Jump links in the path network
- **`JumpSpot extends LiftCenter`:** `SpecialCost` is 300 only for a big JumpZ or low gravity; otherwise it is
  effectively blocked. `SuggestMovePreparation` calls `BigJump`. So the engine can route through jump links, and a
  subclass that is cheap for our Skaarj and runs our leap is a UE2 traversal link.
- **`ReachSpec.reachFlags`:** jump is 8 in UT2004; check U2's value by printing.
- **Ladders:** `PHYS_Ladder` exists, player only.
- **Our generator already writes PathNode T3D** (`pathnodes.py`, `pathlinks.py`); the new markers can come from the
  same place.

### Skaarj animations (`Meshes\Characters\Biped\SkaarjAnims.gem`, `SkaarjAnimsAgent.gem`)
**Agent actions:**
- `U2_Leap` = `FlipFrwdSlash_Fr01/Fr03_SM`
- `U2_Jump`, `U2_Land`
- `U2_Dodge`/`U2_DodgeFlip`, `U2_DodgeStrafe`
- `U2_Mantle` -> `MantleClimbOver`

**Clips:**
- flips: `FlipFrwd01`, `FlipBack01`, `FlipLeft01-03`, `FlipRght01-03`, `FlipFrwdSlash_Fr01-03`, `StillSpinSlash_Fr01`
- jumps: `JumpStart{Frwd,Back,Left,Rght}01`, `Jump{...}01`
- landings: `Land{...}01`, `LandHard01/02`
- falls: `Fall01`, `FallFar_Fr01`
- hanging and climbing: **`MantleHang01`** (the cling pose), `MantleClimbOver01`, **`Climb01`**
- other: `M08_Leap`, `ProneCrawl`, `RunFrwd_HeadButt01`
- the notify `LeapBegin`

**Missing:** a sideways wall cling and a ceiling crawl. Use `MantleHang01` under beams, and side flips off walls.

**Playing clips:** `MeshAgentImmediateAction("set AnimAll { script \"MantleHang01\"; ... }")`, as proven in U2Wardrobe
`hub agentdo`, or `CallSpecialAnimAction`.

## 4. Plan

### Step 0: lab checks (0.5 day, U2TestHub)
- Play `MantleHang01`, `FlipLeft01`, `JumpStartFrwd01` and `LandFrwd01` on a spawned Skaarj.
- Hang one in `PHYS_None` 300 uu up, launch it with a solved velocity, and check that the controller recovers.

### Step 1: "wall-kick" (1 day + 0.5 day tuning, mutator only)
1. `SkaarjTraversalController extends SkaarjController`, given to agile and Berserker Skaarj by
   `EnemyMutator.CheckReplacement`.
2. Override `NotifyHitWall` in AttackLeapState. When the Skaarj is mid-leap, the wall is near-vertical
   (`abs(HitNormal.Z) < 0.3`) and it hasn't kicked yet this leap: side flip, solve a new arc to the player's predicted
   spot, set the velocity, stay Falling.
3. Make kicks happen on purpose: when the direct leap is blocked, or at ~30 % odds, trace sideways 150-400 uu for a
   wall and leap at a point ~80 uu up it.

Fairness: a crouch-and-hiss telegraph of at least 0.3 s, no firing in the air, the stock cooldown, one leaper at a
time (a FairFights-style token).

### Step 2: "rafter / pillar cling" (2-3 days)
**Marker:** a hidden `ClingPoint` actor with a normal, a kind (Wall / Beam / PillarTop) and an "occupied" flag.
- The Python generator places them under beams and catwalks, on pillar tops, and on walls 200-350 uu up.
- At least 400 uu apart, each with a capsule-clearance check.
- They are not NavigationPoints, so no path rebuild is needed.

**Choosing one, every 0.5 s in combat:**
- Candidate: within 900 uu, in line of sight, free, with a clear arc.
- Score = gain toward the player + height + flank bonus − a penalty if the player is aiming at it.
- Use the best positive score at ~40 % odds, behind the token check.

**Sequence:**
1. Hop: `JumpStartFrwd01` + a solved arc.
2. Cling: `PHYS_None`, snap to the marker, face the player, loop `MantleHang01`, roar.
3. Hold 0.6-1.2 s; damage drops it (`Fall01` -> `LandHard01`).
4. Pounce: `GotoState(AttackLeapState)`.

**Abort rules:** player within 200 uu, a blocked arc, a 2 s stuck watchdog, at most two clings in a row.

### Step 3: fuller version (1-2 weeks total)
- A `TraversalJumpSpot extends JumpSpot`, cheap for traversal Skaarj and running our leap; placed in pairs by the
  generator, so Skaarj route over walls and ledges.
- Beam-to-beam chains in rooms built for it (Avalon catwalks, the crane tower).
- A ceiling crawl for Araknids via `PHYS_Spider`, after the lab test.
- Dust at kick points, and rim light near cling spots.

### Risks
- **Getting stuck:** check the fit with `FitActorAt`, add a `PHYS_None` watchdog, sweep arcs with extents.
- **The behaviour controller fighting the new state:** `BehaviorController.SetBCEnabled(false)` while clinging, as
  AttackLeapState does.
- **Clip hookup:** the agent may override clips. Use `force(n) AnimAll` + `keepset` like `U2_Leap`.
- **Fairness:** always roar, cling only in or near view at normal difficulty, one leaper at a time, a real hold window.
- **Hitscan:** Skaarj fire projectiles, so it's fine, but never fire while clinging or airborne. A clinging Skaarj is
  a still target for the player; that's intended, so keep holds short.

### Local files
- `u2_export\all\U2AI\U2NPCControllerBasic.uc`, `U2Pawns\SkaarjController.uc`, `U2Pawns\U2SkaarjLight.uc`
- `U2AI\JumpSpot.uc`, `U2AI\U2NPCControllerBot.uc`
- `U2\AnimationControllerBase.uc`
- `full_Engine\Classes\Pawn.uc`, `Controller.uc`
- `<game>\Meshes\Characters\Biped\SkaarjAnims.gem`, `SkaarjAnimsAgent.gem`
- `U2Avalon\tools\pathnodes.py`, `pathlinks.py`
