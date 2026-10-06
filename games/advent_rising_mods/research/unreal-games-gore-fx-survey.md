# Gore and hit-FX survey: Unreal-engine games on this PC, and what Advent can use

Date: 2026-10-03. Goal: collect the good gore and special-effects ideas from the Unreal-engine games installed here and rebuild them in AdventMod (Advent Rising is Unreal Engine 2, build 2226, from the UT2003 line, and our scripts compile with AdventUCC).
Licensing: everything below is notes on other people's code. **We take the ideas and write our own code. We use our own procedural textures, meshes and sounds, and we ship none of their assets or code.** See section 5.

## 0. What AdventMod already has (so we don't rebuild it)

`AdventMod/Classes` already contains:
- `ModGore` and `ModGoreRules`. `GameRules.NetDamage` sees every hit and makes these marks:
  - a spray on the wall or floor behind the victim, along the shot (within `SprayReach`);
  - drips;
  - a pool that spreads under each body;
  - scorch marks where shots hit walls and floors;
  - a cap of `MaxDecals`/`MaxHoles`, where the oldest mark goes first.
- `ModBloodDecal`: a Projector with a grow-over-time option.
- `ModCasing`: casings that land and stay, taken over from the game's own shell particles.

That covers the ideas from UT2004's BloodSpurt.WallSplat and Deus Ex's BloodPool. The list in section 6 therefore ranks only what is missing: gibs, dismemberment, ragdolls that react to shots, bleeding, wound skins, screen blood, cleaning up corpses and gibs, and a data-driven death-effect table.

## 1. Installed Unreal-engine games and where the source came from

| Game | Location | Engine | Script source used for this survey |
|---|---|---|---|
| Unreal (Gold) | F:\...\Unreal Gold | UE1 | Same UnrealShare/UnrealI code as the copies inside UT99 |
| Unreal Tournament (GOTY) | H:\...\Unreal Tournament (and C:) | UE1 (v436) | **Dumped** to `Documents\UT99_src` (Engine, UnrealShare, UnrealI, BotPack: 1,099 classes) |
| Deus Ex | F:\...\Deus Ex | UE1 (v1112) | **Dumped** to `Documents\DeusEx_src` (DeusEx, Engine: 1,247 classes) |
| Rune Classic | F:\...\Rune Classic | UE1 (heavily modified) | **Dumped** to `Documents\Rune_src` (RuneI, Engine: 832 classes) |
| X-COM: Enforcer | F:\...\XCom Enforcer | UE1 | Partly dumped to `Documents\XCom_src` (XPawn, ParticleSystems, Engine; source stripped from Enforcer.u) |
| Unreal II: The Awakening | C:\...\Unreal II The Awakening | UE2 (2003) | Already exported: `Documents\Tools\u2_export\cur_U2*` |
| UT2004 | H:\ (and F:) | UE2.5 (3369) | Already exported: `Documents\UT2004_extract\code` |
| Star Wars Republic Commando | F:\ | UE2 (licensee) | Source stripped, and the package format is a licensee variant. I used the **name tables** (class, function and property names) |
| Brothers in Arms: Road to Hill 30 / Earned in Blood | F:\ | UE2 (licensee) | Same: name tables only |
| Splinter Cell (via `github\EnhancedSC`) | (repo, not installed) | UE2 (licensee) | Full script in `EnhancedSC\UnrealScript` |
| Unreal Tournament 3 | H:\ | UE3 | `UTGame.u` is compressed. I pulled 78 classes out of `UTGameContent.u` into `Documents\UT3_src`. Everything else about UT3 comes from known UT3 script and is marked (k) |
| Thief: Deadly Shadows, Deus Ex: Invisible War | H:\ / F:\ | UE2-derived "Flesh" engine plus Havok | No UnrealScript gore layer. Skipped |
| BioShock Remastered | H:\ | UE2.5 (Vengeance) plus Havok | No readable script. Skipped |
| UE3 titles (Borderlands, Batman AA, Alice MR, Alien Breed 1-3, Spec Ops, Remember Me, Alpha Protocol, BiA Hell's Highway, Deadlight, StrikeVector, Killer is Dead, Afterfall) | various | UE3 | Cooked and compressed, so out of scope. UE3 features are physics assets and constraint breaking, which Advent cannot do |

Not installed: Postal 2, Killing Floor, Red Orchestra, SWAT 4, America's Army and Unreal Championship. The Killing Floor and Postal ideas mentioned here come from general knowledge and are marked (k).

**How the dump worked.** UT99's own `ucc batchexport` asserts on classes whose source text was stripped, so I wrote a read-only extractor, `Documents\UT99_src\uscript_dump.py`. It parses the UE1/UE2 package header and name, import and export tables, then writes each `TextBuffer 'ScriptText'` out as `<Class>.uc`. It never writes to game folders. It works on package versions 61–69, and it should also work on standard UE2 packages that keep their source text. `pkgstrings.py` (name scan) and `textruns.py` (UE3 plain-text runs) sit next to it.
These dumps hold other companies' code. They are for private reference only: **do not commit them to GitHub or Nexus.**

## 2. Per-game findings

### 2.1 Unreal / UT99 (UE1): carcasses you can keep shooting
- **The gib decision on death** is `Bot.Gibbed(damageType)`:
  - never for `'decapitated'` or `'shot'`;
  - always if `Health < -80`;
  - with 60% odds if `Health < -40` (65% in Unreal's `Bots`).
  - Then `SpawnGibbedCarcass()` or the normal carcass.
  - The overkill is simply how far Health has gone negative.
- **Corpses are damageable** (`UTHumanCarcass.TakeDamage`):
  - every hit spawns `UT_BloodHit` (with a `GreenBlood()` variant) and pushes the body: `Velocity += 3*Momentum/(Mass+200)`. `'shot'` damage is multiplied by 0.4.
  - The body accumulates `CumulativeDamage`. `ChunkUp()` runs when `(Damage>30 || !IsAnimating()) && CumulativeDamage > 0.8*Mass`, or when `Damage > 0.4*Mass`.
  - Landing faster than `Velocity.Z < -1000` also chunks it, and so does a corpse that cannot fit back after `SetCollisionSize`.
  - Being stepped on by a pawn calls `gibbedBy`.
- **Decapitation is cheap.** `TournamentMale.PlayDecap()` plays a headless death animation, `'Dead4'` (the mesh has the head folded away in those frames). It also spawns a separate `UT_HeadMale` carcass at `Location + 0.8*CollisionHeight*Z`, gives it random velocity, and has the head inherit the body's velocity.
- **Hit FX on the living** (`TournamentPlayer.PlayDeathHit`):
  - `UT_BloodHit` aimed along the momentum, with Z halved, for `shot`, `decapitated` and `shredded`;
  - otherwise `UT_BloodBurst`;
  - skipped one time in three under `bDropDetail`.
- **Other classes:**
  - gibs: `UTPlayerChunks`, `UTHeart`, `UTLiver`, `UT_Thigh`;
  - `UT_BloodTrail` on flying gibs;
  - `UTBloodPool`/`UTBloodPool2` under corpses;
  - `BloodSplat` decal, plus `BlastMark` and `ImpactMark` scorches.
- **Shells** (`UT_ShellCase`, a Projectile):
  - LifeSpan 1.5 under drop-detail;
  - each bounce reflects with `0.5*(V - 2N(V·N))` plus `RandSpin(100000)`;
  - it stops bouncing after more than 3 bounces, or with 85% odds once it has bounced, or once it is moving upward slower than −50.
- Portability: 100% script. Advent has no carcass actor, but its dead Pawn (or ragdoll) can play the same role.

### 2.2 Deus Ex (UE1): bleeding and growing pools
- **Locational health.** The pawn has `HealthHead`, `HealthTorso`, `HealthArmLeft` and so on. A destroyed limb's damage carries over into the torso (`HealthTorso += HealthLegLeft`), and head hits count double.
- **Bleeding over time** (`ScriptedPawn`):
  - each hit adds `bleedRate += (origHealth-Health)/(0.3*Default.Health)`, so losing a third of max health means heavy bleeding;
  - `Tick` drops `BloodDrop` particles at up to 10 per second, scaled by `bleedRate`;
  - `bleedRate` decays by `dt/ClotPeriod`.
  - The result is a trail on the floor that shows where a wounded enemy went.
- **Gib on overkill.** When `Health < -100` and the pawn is not a Robot:
  - no carcass;
  - `size/4` `FleshFragment` chunks, where `size = (radius+height)/2`;
  - chunk `DrawScale = size/25`, so chunks scale with the creature.
- **Carcass damage.** Only `Shot`, `Sabot`, `Exploded`, `Munch` and `Tantalus` gib a corpse. Each such hit spawns one `BloodSpurt` and one `BloodDrop` per 10 damage.
- **BloodPool** (a DeusExDecal) is spawned under the carcass with `maxDrawScale = CollisionRadius/40` and grows linearly over `spreadTime`. AdventMod already does this.
- **Shells:** `ShellCasing`, `ShellCasing2` and `ShellCasingSilent` are physical debris. `DeusExFragment` covers flesh, metal, glass, wood, paper and plastic, so debris type matches the material.
- Portability: all script and all portable. The bleed trail is the standout idea.

### 2.3 Rune (UE1, melee): true per-limb dismemberment
- **Per-limb health:**
  - `BodyPartHealth[15]`;
  - `BodyPartForJoint(joint)` and `BodyPartForPolyGroup(polygroup)` map a hit to a body part;
  - `BodyPartSeverable(part)` and `BodyPartCritical(part)` decide what can come off, and the head is critical.
- **Damage splits into blunt and sever.** `GetDamageValues(Damage, DamageType, Blunt, Sever)` divides each hit. Sever damage drains the limb's health. At 0:
  - a critical part converts the hit to `'decapitated'` with `PassThrough = Max(Health, Damage)`;
  - unless `bLowGore`, the limb is hidden: `BodyPartVisibility(false)` hides its polygroup, and `BodyPartCollision(false)` removes its collision;
  - `LimbSevered(part, Momentum)` then spawns the limb actor (`SeveredLimbClass(part)`, e.g. `BerserkerLArm`, `BerserkerHead`);
  - **an arm that carried a weapon drops the weapon.**
- **Gore caps.** `ApplyGoreCap(part)` makes a hidden "stump" polygroup visible and gives it a gore texture (`runefx.gore_bone`, `ragnarb_neckgore`). Severed limbs therefore show a cap, not a hole.
- **Sever chips.** Sever damage spawns `(Damage/15 + 1) * DebrisPercentage` small gibs (size 0.1–0.4, momentum ×−0.08) on every hit, not only kills.
- **Gibbing:**
  - when `Health < -Default.Health` (overkill equal to the full health pool) and `bGibbable`;
  - when you keep hitting a corpse;
  - always for `'crushed'`.
- **`SpawnBodyGibs`** first throws every limb that is still attached as its real severed-limb actor, with velocity `(Normal(Mom)*2 + VRand + Z) * 50..300`. Generic chunks fill the rest, sized `0.8 * ((r²h)/(n*600))^(1/3)`, so the gibs' total volume roughly matches the body's.
- **Gameplay link:** hits that land give the player a `BoostStrength(0.2*Damage)` "bloodlust" bonus, so gore feeds the combat loop.
- Portability: the logic is all script. Rune hides parts with polygroup flags (`SkelGroupFlags`/`POLYFLAG_INVISIBLE`, Rune-only natives), so **Advent would use `SetBoneScale(slot, 0, bone)` instead** (section 3). The stump cap becomes a small mesh or emitter attached to the parent bone.

### 2.4 X-COM: Enforcer (UE1)
Each alien has a carcass class with its own gib meshes (`SectoidCarcass`: SectgibA/B/C, and so on). `ParticleSystems.DecaySpray` and `ParticleSprayer` are used for dissolving and "appear" effects. Nothing new beyond UT99, except the idea of one carcass and gib set per species.

### 2.5 Unreal II (UE2, 2003; same generation as Advent)
- **The gib decision is in the engine Pawn.** Defaults are `GibForSureHealth=-250`, `GibMaybeHealth=-100` and `GibMaybeOdds=0.5`. `ShouldGib` also checks `GibSet.GoreLevel` against the player's gore setting.
- **GibSet** is a data-only Object, and an elegant one. `Gibs` is an array of `GibDesc`:
  - `MeshName`, `Odds`, `PctParentMass` (how far the piece flies), `ExtraCount`;
  - `bNoBlood` (bone pieces don't bleed), `bNoDamage`;
  - collision size and a `PrePivot` so the piece lies flat.
  - Gibs spawn at random points inside the collision cylinder.
  - Variants include `GibSetGeneric` and `GibSetAraknidLight/Medium/Heavy`.
- **Gib lifetime.** This is the best cleanup scheme in the survey:
  - `bShouldSink`: after 4–5 s (random), **if no player can see it** (`PlayerCanSeeMe`), the gib sinks into the floor at 1–4 units per second through `PrePivot.Z`, then is destroyed;
  - if the player is looking, it checks again later;
  - an alternative fades `ScaleGlow` over `FadeDurationSeconds=1`;
  - the fallback destroys the gib after 10 s, rechecking every 4 s.
  - Flying gibs leave a `ParticleSalamander` blood trail.
- **Gibbed burst.** `DoGibbedEffect` spawns a ParticleRadiator that **uses the dead pawn's own mesh as its emitter shape**. Its volume is scaled by `CollisionHeight*R²/42336` (the size of a normal pawn).
- **ImpactHandler** (native-backed) is a per-weapon table of `TMaterialEffects`, keyed by `Material.ETextureType`. Each entry has:
  - `DecalTexture` and `DecalScale`;
  - `HitEffectClass` and `ParticleEffect`;
  - **ricochet**: `RicochetProbability`, an incidence threshold, `MaxRicochetCount`, damping and spread angle, spawning a `RicochetProjectile`.
  - `CustomImpactSurface` is a Material modifier that overrides the decal or effect for one surface and can fire an Event when hit, e.g. shootable glass.
- **`U2ShellCase`** uses the same bounce code as UT99, plus a splash sound in water and a muzzle-lit shell whose light switches off after 0.1 s.
- **`U2Decal`** is a Projector (FOV 5, MaxTraceDistance 16, BSP only).
- Portability: the GibSet data idea and the sink-when-unseen logic are pure script. Ricochet can be done in script with a trace. Advent's `SurfaceProperties` already plays the ImpactHandler role.

### 2.6 UT2004 (UE2.5; Advent's closest relative)
- **DamageType fields** (Engine.DamageType). Advent's DamageType has only `bAlwaysGibs` and `bCausesBlood`. The rest are worth copying into our own per-damage table:
  - `bAlwaysSevers`, `bNeverSevers`, `GibModifier`, `GibPerterbation` (0.06 = random spread of gib directions);
  - `bThrowRagdoll`, `bRagdollBullet`, `KDeathVel`, `KDeathUpKick`, `bKUseTearOffMomentum`;
  - `bFlaming` (gibs burn instead of bleed), `bSkeletize`;
  - `DamageOverlayMaterial` and `DeathOverlayMaterial` with their times (6 s by default);
  - `PawnDamageEmitter` plus `LowGore*` variants.
- **The locational sever system** (`xPawn.DoDamageFX`) is the best-tuned one here:
  1. Each hit records `{bone, damtype, rotDir, bSever}` in an 8-slot ring buffer (`HitFX[]`, replicated through `HitFxTicker`). Clients replay it in `ProcessHitFX`. The bone comes from `GetClosestBone(hitLoc, hitRay)`.
  2. An effect only fires when `FRand()>0.3 || Damage>30 || dead`.
  3. On a killing hit, hands and feet remap to their parent limb (`lfoot→lthigh`, `rhand→rfarm`, `shoulder→spine`). Then:
     - **total gib** if `bAlwaysSevers || Damage==1000`, or if `Damage*GibModifier > 50 + 120*FRand()` and `Damage+Health > 0`;
     - otherwise a **limb sever** with probability `|Health − Damage*GibModifier| / 130` for thighs, forearms and head (×0.3 for spine).
     - 25% of spine severs also take both legs, and a further share take one leg (`bExtraGib`).
  4. `GameInfo.PreventSever(...)` and `GameRules.PreventSever` can veto any sever. Advent has both hooks.
  5. **The sever itself:**
     - `HideBone(bone)` is just `SetBoneScale(slot 0..5, 0.0, bone)`;
     - a bleeding `BloodEmit` xEmitter is attached at the bone;
     - typed gibs (`EGT_Calf`, `Forearm`, `UpperArm`, `Head`, `Torso`, `Hand`) are thrown from the bone origin;
     - per-body budgets cap the gibs: `GibCountCalf=4`, `GibCountForearm=2`, `GibCountHead=2`, `GibCountTorso=2`, `GibCountUpperArm=2`.
- **Gib** (`XEffects.Gib`):
  - PHYS_Falling, LifeSpan 8 ±1, Mass 30, `DampenFactor 0.65`;
  - velocity `pawnVel + dir*(250..510)`;
  - each bounce faster than 150 (250 on low detail) spawns a small blood hit and a wet sound;
  - it settles below speed 20;
  - while flying, a `BloodJet` trail drips splats on the floor below (one in five chance, trace 200 units down).
- **Ragdoll death** (`xPawn.PlayDying` and the `Dying` state). `RagdollLifeSpan=13`, `RagDeathVel=200`, `RagShootStrength=8000`, `RagDeathUpKick=150`, `RagSpinScale=2.5`.
  - **Corpses react to shots.** In `Dying.TakeDamage`, a ragdoll gets `KAddImpulse(RagShootStrength*Normal(Momentum), HitLocation)`.
  - `bRagdollBullet` adds a spin kick: angular velocity from `Momentum × Z * −8000`, Z axis ×4, 65% of the time.
  - Each such hit adds +0.2 s of life.
  - `bThrowRagdoll` launches the body: linear velocity `RagDeathVel*dir + (0,0,250)`.
  - Bone-impact sounds play at `RagImpactSoundInterval=0.5`.
  - `LevelInfo.MaxRagdolls=4`, and `bKImportantRagdoll` protects the corpse in view.
- **De-res** replaces a pop-out. In the last `DeResTime=6` s the body lifts with reduced gravity (`DeResLiftVel` curve, `DeResGravScale`) inside a `DeResPart` emitter that uses the skeletal mesh as its spawn surface, while the skin swaps to a wireframe material.
- **Decals** (`xScorch` extends Projector):
  - each is placed `PushBack=24` along the normal;
  - it gets a random roll and lifespan `±2`, halved under `bDropDetail`;
  - `AbandonProjector(LifeSpan*Level.DecalStayScale)` hands it to the engine, after which the actor destroys itself;
  - culled with `BeyondViewDistance(CullDistance)` and in `bNoDecals` volumes.
  - `BloodSplatter`: 3 textures, FOV 6, CullDistance 7000, LifeSpan 5. `BulletDecal`: LifeSpan 3.2 (75% of them halved), DrawScale 0.18, CullDistance 3000.
- **Wall hit** (`xHeavyWallHitEffect`): it picks one of 10 sounds, and places a decal only if the spot is within `1600*FOVBias` and in front of the camera. Then:
  - 50%: `pclImpactSmoke`, otherwise `WallSparks`;
  - no smoke in water.
- **Shells** (`ShellSpewer`): mesh particles (PT_Mesh), up to 150 alive, life 0.5–1 s, speed 200–250, direction deviation (0.5, 0.2, 0.6), `mColMakeSound` (a sound on each collision).
- Portability:
  - all of the logic is script;
  - `xEmitter` does not exist in Advent, so rebuild those effects as `Emitter`/`SpriteEmitter`;
  - `GetClosestBone` and `SetOverlayMaterial` are missing (workarounds in section 3);
  - `SetBoneScale`, `AttachToBone`, `KAddImpulse`, `KSetSkelVel`, `KFreezeRagdoll`, `AbandonProjector` and `DecalStayScale` **all exist in Advent**.

### 2.7 Star Wars Republic Commando (UE2 licensee; from the name tables)
- **A data-driven death-effect table.** `DeathEffectContainer_<Species>` objects (BattleDroid, SBDHalf, Elite, Warrior, Scav, Slaver, Grievous and others) hold `DeathEffectPair`s that combine a **condition** with an **effect**.
  - Conditions are composable objects: `DeathCondition_And`, `_Or`, `_Not`, `_BoneName`, `_DamageType`, `_MinForce`, `_Physics`, `_Random`.
  - Effects are `DeathEffect_PlayDying`, `_PartialDismemberment`, `_TotalDismemberment` and `_DestroyBody`.
  - Example: "DamageType = shotgun AND bone = spine2 AND force > X AND Random 0.5 → PartialDismemberment".
  - Supporting names: `DismembermentThreshold`, `DismembermentParts`, `SeverInfo`, `PreventSever`, `DeathSplit` (droids split in half), `RagdollOnDeathProbability`, `MaxRagdolls`, `PriorityRagdoll`, `RagdollLifeSpan`, `KBreakRagdollJoint`.
- **Visor (screen) blood:** `VisorBloodSplatters`, `VisorHitDecals`, `SplatterWiperDelay`/`BloodWipeDelay`, `SplattersPerMinute`. Blood lands on your helmet visor and a wiper clears it.
- **Effects** (cteffects): species blood (`Blood_Spray_Wookiee`, `_Trandoshan`, `_Geonosian`, droid sparks), `DeathExplode_<Type>`, `NewDecap`, `BloodMist`, and per-weapon shell meshes (`Shell_Uzi`, `Shell_Shotgun`, `WookieeRocketShellCase`).
- Wounded movement: `AnimateWoundedWalking`/`Running`, with `Wounded07`/`40`/`62` run sets chosen by health.
- Portability: the condition/effect table is pure script and is the best way to organise all of this (rank 2). `KBreakRagdollJoint` is native and RC-only, so Advent can't do it. Visor blood is portable (HUD canvas or a camera-attached emitter).

### 2.8 Brothers in Arms RtH30 / EiB (UE2 licensee; from the name tables)
- **Wound textures** (`EDEBodyGore`). The pawn swaps skins to pre-painted wound variants per unit, weapon and hit side: `GORE_<UNIT>_<K98|MP40|STURM>_<LEFTSIDE|RIGHTSIDE|...MASS|LEGS|NONE>`. Related names: `GorePackSetup`, `GetPackGoreTexture`, `fUseGorePackShader`, `DEGoreHead`/`LeftArm`/`RightLeg`.
  - The result is that **the corpse shows where it was shot**, with no decals on the skinned mesh.
- **ImpactManager** with an `ImpactHandler<Surface>` per surface (Dirt, Grass, Hay, Metal, Plaster, Shrubbery, Stone, Water, Wood, AirExplosions), separate `HandleBulletImpact`, `HandleExplosionImpact` and `HandleMeleeImpact`, and `bImpactMustBeVisible`.
  - `BulletDecalList` is a ring buffer of `MaxBulletDecals`, with `DrawDecalSquaredDist` distance culling.
- **Shells:** `AnimNotify_EjectShell` puts ejection on an animation notify, so the shell flies at the right frame. Also `SHELL_CULL_DIST` and `bNoShellCasings`.
- Also `CreateHudBloodEffect`/`HudEffectBlood`, `RagImpactCue` (bodies thud), `UseLowGore`.
- Portability: skin swaps are script (`Skins[i]=`). The wound masks themselves would need our own procedural shader. Advent has `Shader`/`Combiner` materials, so a blood mask can be overlaid in script.

### 2.9 Splinter Cell (EnhancedSC script)
- `EBloodSplat` is a SpriteEmitter burst: 160 particles in one shot, speed 400, gravity −100, size scaling 0.5→3, life up to 2 s, alpha blend, lit by the scene. It is a good template for an Advent `Emitter` blood puff.
- **Impacts make AI noise according to surface.** `EWallHit.Noise()` classes the hit surface:
  - hard or resonant (concrete, metal, glass) → full ricochet noise radius;
  - soft (grass, dirt, carpet, snow, water) → −700;
  - other → −400.
  - Gunfire impacts therefore alert enemies by material. This is a gameplay idea, not a gore one.

### 2.10 UT3 (UE3; (k) = from known UT3 script, since `UTGame.u` is compressed)
- Confirmed in `UTGameContent`:
  - `GetDeathCameraEffectInstigator`: a **killer standing close to a gib kill gets a screen blood splatter** (`UTEmitCameraEffect_*`), and oil for robots (`UTFamilyInfo_Liandri`);
  - `SpawnExtraGibEffects`/`PS_AttachToGib` (a particle attached to each gib);
  - setting `ThePawn.bGibbed` so a corpse can't gib twice.
- (k) The rest comes from known UT3 script:
  - `UTPawn` gibs per `UTGib` class from `GibInfo` (bone-based);
  - `UTDamageType.bCausesBlood`, `GibThreshold`, `MinAccumulateDamageThreshold`, `AlwaysGibDamageThreshold`, `bThrowRagdoll`;
  - headshots spawn a head gib and hide the head (`HeadShotGib`);
  - blood decals are material instances with a fade parameter.
- UE3 constraint breaking (`BreakConstraint`) is not portable. The thresholds and the camera splatter idea are.

### 2.11 Not installed, for reference only (k)
- **Killing Floor** (UE2.5): decapitation through `HideBone(HeadBone)` plus a "headless" state where the zed keeps walking for a few seconds before dying. There is a head health pool separate from the body.
- **Postal 2** (UE2): per-limb removal with a stump mesh attached, a head that can be exploded or kicked as a separate actor, and urine and blood puddles as growing decals.

Both confirm the UT2004 SetBoneScale method on a UE2 build.

## 3. What Advent's engine can and cannot do (checked in `Documents\AdventRising_src`)

| Feature | Advent | Notes |
|---|---|---|
| `SetBoneScale(slot, scale, bone)` | **Yes** (native, Actor.uc) | Use it like UT2004's HideBone. Scaling a bone to 0 also collapses its children, so sever at the joint above (`leftForeArm`, `leftLeg`, `head`). Advent bone names: `hips, spine, spine1, spine2, neck, neck02, head, leftArm, leftForeArm, leftHand, leftUpLeg, leftLeg, leftFoot` (and the right-side equivalents) |
| `GetClosestBone` | **No** | Script replacement: loop about 12 named bones through `GetBoneCoords` and take the nearest to the hit point or ray. Cheap enough, since it only runs on hits |
| Karma ragdolls | **Yes** | `PHYS_KarmaRagdoll`, `KarmaParamsSkel`, `KMakeRagdollAvailable`, `KIsRagdollAvailable`, `KAddImpulse`, `KSetSkelVel`, `KFreezeRagdoll`, `bKImportantRagdoll`, `LevelInfo.MaxRagdolls=4`. `AdventPawn` already has the `bUseRagDollPhysics` path, and `Human` sets `RagdollOverride="humanMale2"`. Still to test: whether every species has a ragdoll asset |
| `Emitter` (Sprite/Mesh/Spark/Beam/Trail/Ribbon) | **Yes** | Use these for all particles |
| `xEmitter` (UT2003/2004's) | **No** | Rebuild those effects as Emitter subclasses with `defaultproperties` sub-objects (AdventUCC must handle `Begin Object`) |
| `Projector`, `AbandonProjector`, `DecalStayScale`, `HitEffectProjector` | **Yes** | Already used by ModBloodDecal |
| `SetOverlayMaterial` | **No** | For a hit flash or burn tint, swap `Skins[i]` to a script-built `Shader`/`Combiner` for a short time, then restore it |
| `AttachToBone` | **Yes** | For stump caps, bone-attached bleeding emitters and burning gibs |
| Surface-type impacts | **Yes, native** | `Level.GetSurfaceProperties().ResolveSurfaceType(mat, actor)` and `SpawnSurfaceProperties(...)` (a weapon × surface matrix). We only add decals and debris per `ESurfaceTypes` |
| GameRules hooks | **Yes** | `NetDamage` (in use), `PreventDeath` (gives us the killing blow, so it can drive the gib/sever decision), `PreventSever` |
| DamageType gore fields | Partial | `bAlwaysGibs`, `bCausesBlood`. `GibModifier`, `bAlwaysSevers` and the others become a lookup table in our mod keyed by damage-type class |
| Carcass actor | No (UE2 has none) | The dead Pawn or ragdoll is the corpse. Its `Dying` state `TakeDamage` is where shots on corpses land; we need to check that NetDamage still fires for dead pawns, and if not, hook from the weapon trace instead |
| Existing shell emitters | Yes | `fx_HumanBlaster_Shells`, `fx_HumanPistol_Shells`, `fx_HumanXJ9_Shells`, `fx_Scythe_Shells`. ModCasing already converts these |

## 4. How the systems hook damage (summary)
- **UE1:**
  - `Pawn.TakeDamage` → `Died` → `Gibbed(damageType)` → `SpawnGibbedCarcass` or `SpawnCarcass`;
  - `Carcass.TakeDamage` → `ChunkUp`;
  - Rune adds per-body-part health inside `JointDamaged`/`TakeDamage`.
- **UE2:**
  - `Pawn.TakeDamage` → `GameInfo.ReduceDamage` → `GameRules.NetDamage` → `PlayHit` → `DoDamageFX` (records the bone and the sever decision) → `Died` → `PreventDeath` → `PlayDying`, which picks ragdoll, anim or gib;
  - the `Dying` state's `TakeDamage` handles corpse impulses and gibbing.
  - Decisions read DamageType defaults, `Health` after the hit (overkill = −Health), and `Damage*GibModifier`.
- **Our hook for Advent:**
  - `ModGoreRules.NetDamage` already sees every hit. It records the bone, damage type and damage per pawn.
  - `PreventDeath` (which returns false) sees the killing blow and asks the death-effect table what to do.
  - A watcher (ModGore's Tick, which already tracks dying bodies) handles corpses.

## 5. Licensing
- **The games' code and assets stay theirs.** All of these games' code, meshes, textures and sounds are under their EULAs (Epic, Human Head, Ion Storm, Gearbox, LucasArts, Ubisoft and others).
- **Our mod is public and GPL/non-commercial.** We can read their code to learn how it works, and then we write our own code.
- **Nothing gets copied in:**
  - no copied functions;
  - no texture, mesh or sound references (`XEffects.BloodSplat1`, `GeneralImpacts.Wet.Breakbone_01` and the like);
  - no exported `.uc` files in our repo.
- **The numbers above are tuning references.** They are facts about behaviour, and we set our own values.
- **We make our own assets.** Blood splats, sprays, pools, scorches and casings come from Python generators, as `make_blood.py` already does. Gib chunks would be our own low-poly procedural meshes (Blender script → ASE/PSK through our importer), and stump caps would be a procedural disc mesh with a generated texture.
- **The dump folders stay private:** `Documents\UT99_src`, `DeusEx_src`, `Rune_src`, `XCom_src`, `UT3_src` and `UT2004_extract`.

## 6. What to steal (ideas) for Advent, ranked

These are ranked by impact over effort. Advent's capabilities are checked, and it's all script with our own assets unless noted.

1. **Ragdolls that react to shots, with impulse, spin and a life extension** (UT2004 `Dying.TakeDamage`).
   - What: in the dying or ragdoll state, `KAddImpulse(Strength*Normal(Momentum), HitLocation)`; for bullets, a spin kick 65% of the time; each hit adds +0.2 s of life.
   - Also: a spray decal behind the corpse (ModGore already has that code), and `MaxRagdolls` respected with `bKImportantRagdoll` on the corpse in view.
   - Why first: the biggest feel win, nearly all native support already exists, and it needs no new assets.
2. **One data-driven "death effect" table** (Republic Commando DeathEffectContainer, plus U2's GibSet as data).
   - What: a config or default-properties array of {conditions: damage-type class, bone group, min overkill, min momentum, random odds, species} → {effect: ragdoll, ragdoll+throw, sever bone X, total gib, disintegrate (energy weapons/powers)}.
   - Inputs: the bone and damage come from NetDamage, and the decision is made in `PreventDeath`.
   - Per-species sets: Human red, Seeker or alien colours, robots sparks and oil (UT3's oil-for-robots idea).
   - Why second: every later item plugs into it. Note that Advent's psychic powers deserve their own effects (e.g. the shatter power gibs, lift-and-throw sends the ragdoll flying).
3. **Limb sever through `SetBoneScale(…,0,…)`** (UT2004 DoDamageFX/HideBone, Rune's stump caps and dropped weapons).
   - Odds: on a killing hit, `p = |Health − Damage*GibMod| / 130` for limbs and head (×0.3 for spine), and total gib above `50 + 120*FRand()` damage.
   - Implementation: hand and foot hits remap to the parent bone; a bleeding Emitter and a procedural stump cap attach with `AttachToBone`; one procedural limb chunk is thrown.
   - Rune touch: a severed weapon arm drops the weapon.
   - Caveats: nearest-bone has to be done in script, and we need to test whether SetBoneScale holds on Karma ragdolls in build 2226. If it doesn't, sever before going to ragdoll.
4. **Gibs that sink or fade when unseen, with per-body budgets** (Unreal II Gib, UT2004 GibCount\*).
   - Pieces: about 6 procedural chunk meshes, with `PctParentMass`-style throw speed (UT2004: 250–510 plus the pawn's velocity, `GibPerterbation 0.06`).
   - Bounces: `DampenFactor 0.65`, a blood hit and splat when a bounce is faster than 150, settling below 20.
   - Budgets: Calf 4 / Forearm 2 / Head 2 / Torso 2.
   - Cleanup: after 4–5 s, sink at 1–4 u/s only while `!PlayerCanSeeMe()`. A global cap with oldest-first removal (as ModGore already does).
   - Size: chunk volume scaled to the body, as in Rune's `0.8*((r²h)/(n*600))^(1/3)`.
5. **Bleeding trail on wounded enemies** (Deus Ex).
   - What: `bleedRate += lost/(0.3*MaxHealth)`, drops at up to 10/s in Tick, `bleedRate -= dt/ClotPeriod`, with each drop a small ModBloodDecal on the floor.
   - Cost: about 40 lines on top of ModGore. It also tells the player at a glance which enemy is hurt.
6. **Screen and visor blood for close kills** (UT3 DeathCameraEffectInstigator, RC VisorBloodSplatters with a wiper delay).
   - What: draw a few procedural splats on the HUD canvas, or use a camera-attached Emitter, when the player gibs or melees something within about 300 units, then fade or wipe them after about 2–4 s. Oil or sparks for robots.
   - Advent's HUD is script, so this is low effort.
7. **Wound skins on bodies** (Brothers in Arms gore packs).
   - What: when hit, swap the body's `Skins[i]` to a `Combiner` of the original skin plus a procedural blood mask for that body region (front or back, left or right, legs).
   - Effect: corpses show where they were hit, which decals can't do on skinned meshes. This replaces `SetOverlayMaterial` too, as a 0.15 s red hit flash.
   - Effort: medium (material building in script, per-mesh UV knowledge).
8. **Shots on corpses: punch and pulp** (UT99 carcass rules).
   - What: accumulate damage on the corpse and pulp it into gibs when `CumulativeDamage > 0.8*Mass` or a single hit is over `0.4*Mass`. Explosions and falls faster than 1000 also pulp it.
   - Rule: once gibbed, a body never gibs again (UT3 `bGibbed`).
9. **Ricochets and surface debris** (Unreal II ImpactHandler, Deus Ex fragment types, Splinter Cell surface noise).
   - What: on hard surfaces (`ResolveSurfaceType` = metal or rock) at a grazing angle, a chance of a ricochet tracer and spark, plus a material-matched chip mesh (wood, stone, metal, glass).
   - Optional gameplay: louder impacts alert AI (`MakeNoise` by surface).
10. **Animation-timed shell ejection** (BiA `AnimNotify_EjectShell`, UT2004 ShellSpewer collision sounds).
    - What: ModCasing already makes casings persist. Add a bounce "tink" per surface type, and spawn on the fire animation's frame instead of from the particle.
    - Polish only.
11. **A de-res or dissolve cleanup instead of popping corpses** (UT2004 DeRes, XCom DecaySpray).
    - What: when a ragdoll's life ends while the player is looking, play a short Emitter at the body (sparks for robots, fading mist for organics) before `Destroy()`. Prefer the U2 "only when unseen" rule first.
12. **Decapitation as its own case** (UT99 PlayDecap, KF/U2 head hide).
    - What: a head shot with high overkill → `SetBoneScale` on `head`, a neck-stump emitter, and a procedural head chunk thrown with the body's velocity. Optional KF touch: the enemy staggers on for about 1 s before falling.
    - This needs item 3 first.

Skip: UE3 constraint breaking and physics assets, Havok (BioShock/Thief), RC's `KBreakRagdollJoint` (native-only), and anything that needs `xEmitter` or `SetOverlayMaterial` (rebuilt above with Emitter and Skins swaps instead).
