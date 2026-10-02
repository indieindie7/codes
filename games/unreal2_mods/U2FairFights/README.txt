U2FairFights - "Fair Fights & Punch" for Unreal II: The Awakening
=================================================================

Fixes the two things players complain about most in Unreal II's combat:
enemies that hit you instantly and from anywhere, and weapons that feel weak.

FAIR FIGHTS (enemies)
  - a short reaction delay after an enemy spots you before it can fire
  - wider enemy hitscan spread, extra spread at the start of each burst:
    the first shots miss, sustained fire finds you
  - the game's own per-shot hit odds scaled down, longer grace after an enemy
    acquires you or gets hurt
  - sight radius capped (some mercs see 35000 units)
  - attack tokens: only a few enemies shoot at once, the rest reposition
  - visible tracers along enemy hitscan shots, so you can read where fire
    comes from

PUNCH (feedback)
  - a beat of slow motion on kills (hitstop), longer for tough enemies and
    when you were nearly dead: the payoff grows with what was at stake
  - a shorter beat on heavy hits that don't kill (rate-limited)
  - the view flinches when you get hurt, harder for bigger hits
  - view kick per shot of your own weapon
  - a hit tick at the crosshair and a click when you hit something
  - easier knock-downs, more ragdolls, bodies that stay

INSTALL
  Copy System\U2FairFights.u into the game's System folder and add
  U2FairFights.FairFights to the Mutator= line in User.ini's [DefaultPlayer]
  section (comma-separated with any others).

SETTINGS ([U2FairFights.FairFights] in User.ini)
  bFairFights=True  ReactionDelay=0.6  NPCSpreadMul=1.5  BurstSpread=3
  BurstSettle=1.2   SightRadiusCap=6000  HitOddsScale=0.7  AcquireGrace=1.5
  HitGrace=0.8      bTokens=True  RangedTokens=2  TokensPer=4  TokenTime=2
  bPunch=True       KillHitstop=0.07  HitstopDilation=0.25  KnockDownScale=0.6
  MaxRagdolls=12    BodyTime=90  KickScale=1  bHitTick=True  HitTickTime=0.12
  bEnemyTracers=True  bLog=True (test lines in Unreal2.log)
  KillToughMax=2  CloseCallHealth=0.3  CloseCallMul=1.6
  HeavyHitDamage=40  HeavyHitstop=0.03  HeavyHitCooldown=0.4
  HurtKick=0.15  HurtKickMax=6

Status of the stakes/heavy-hit/hurt-kick additions: written without the game
(not compiled yet); they only use calls the rest of this mod already uses.

Status: works and tested with U2Pilot runs; not packaged for Nexus.
