//=============================================================================
// ModGore - procedural blood for AdventMod: one per level (ModMutator spawns it),
// fed every hit by ModGoreRules (GameRules.NetDamage, which Pawn.TakeDamage runs
// for every character through GameInfo.ReduceDamage).
//   - a spray on the wall or floor behind the victim, along the shot, if one is
//     within SprayReach: the bigger the hit, the bigger the spray;
//   - drips on the floor under the hit, sometimes;
//   - a pool spreading under each body, a moment after it falls.
// The marks are ModBloodDecal projectors with procedural textures (Textures\
// make_blood.py, imported by ModBloodTextures). At most MaxDecals at once: the
// oldest goes first. Only damage types that cause blood (DamageType.bCausesBlood)
// and only characters (not vehicles or turrets) bleed, in the colour the game's own
// hit particles give them (its surface table: humans red, Seekers purple, holograms
// and ShockTroopers nothing).
// Bodies near the player stay: the game fades corpses out (AlphaFadeKill, and the
// Dying state's timer for those out of sight); within HoldRange that is put off
// until the player has walked away.
//=============================================================================
class ModGore extends Info
	config(AdventMod);

var config bool bBlood;            // the Gameplay page's Blood switch
var config int MaxDecals;
var config float SprayReach;       // how far behind a victim a wall still catches the spray
var config float DecalScale;       // all marks' size
var config bool bImpacts;          // scorch marks where shots hit walls and floors
var config int MaxHoles;
var config bool bCasings;          // the game's shell particles become casings that land and stay
var config int MaxClutter;
var config bool bCorpseShots;      // corpses bleed and move when shot (a body still standing in its death pose goes limp)
var config float CorpseKick;       // the push a shot gives a ragdoll
var KarmaParamsSkel CorpseParams;  // ragdoll settings for corpses the level gave none (a subobject below, so saves can refer to it)
var array<Pawn> Corpses;
var float CorpseScan, LastCorpseLog;

var config bool bHoldCorpses;      // bodies near the player don't fade until the player moves away
var config float HoldRange;
var config int MaxHeld;
var array<Pawn> Held;              // corpses whose fade was put off, oldest first

var Material Splats[4], Sprays[2], Pool, Scorches[3], CasingTex;   // the textures, referenced so the package keeps them
var Material AlienSplats[4], AlienSprays[2], AlienPool;             // the same in the Seekers' purple
var array<ModBloodDecal> Decals, Holes, Clutter;
var StaticMesh ShellMesh;          // the game's own shell, taken from its shell particles
var float ShellScale;              // ...and the size those particles draw it at
var array<Pawn> Dying;             // bodies waiting for their pool
var array<float> DyingTime;
var int Hits;
var string LastGuns;                // bGoreLog
var array<Actor> Seen;
var array<Projectile> Shots;       // projectiles in flight: where they were and how fast,
var array<vector> ShotLoc, ShotVel;// to find the surface they hit when they vanish

event PostBeginPlay()
{
	local ModGoreRules R;
	local int i;

	Super.PostBeginPlay();
	if (Level.Game == None)
		return;
	// clamped, not tiled: a projector wider than its picture would repeat it
	for (i = 0; i < 4; i++)
	{
		ClampTex(Splats[i]);
		ClampTex(AlienSplats[i]);
	}
	for (i = 0; i < 2; i++)
	{
		ClampTex(Sprays[i]);
		ClampTex(AlienSprays[i]);
	}
	ClampTex(Pool);
	ClampTex(AlienPool);
	ClampTex(CasingTex);
	for (i = 0; i < 3; i++)
		ClampTex(Scorches[i]);
	R = Spawn(class'ModGoreRules');
	R.Gore = self;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = R;
	else
		Level.Game.GameRulesModifiers.AddGameRules(R);
	class'ModSettings'.static.Note("gore: watching hits");
}


static function ClampTex(Material M)
{
	if (BitmapMaterial(M) != None)
	{
		BitmapMaterial(M).UClampMode = TC_Clamp;
		BitmapMaterial(M).VClampMode = TC_Clamp;
	}
}

function bool Bleeds(Pawn P, class<DamageType> DamageType)
{
	if (!bBlood || P == None || DamageType == None || !DamageType.default.bCausesBlood)
		return false;
	if (P.IsA('Vehicle') || P.IsA('Turret'))
		return false;
	return BloodKind(P) != 0;
}

// the colour of a character's blood, as the game's hit particles have it (the level's
// SurfaceProperties table, read with ModPilot BLOODFX): 1 red (humans, Aurelians and
// anything unlisted), 2 purple (Seekers), 0 none (holograms spark blue, ShockTroopers
// are armour)
static function int BloodKind(Pawn P)
{
	switch (P.GetSurfaceType())
	{
	case EST_Seeker:
	case EST_SeekerBlocking:
		return 2;
	case EST_ShockTrooper:
	case EST_HologramGuyA:
	case EST_HologramGuyB:
	case EST_HologramGuyC:
	case EST_VehicleDefault:
	case EST_Metal:
		return 0;
	}
	return 1;
}

function Material SplatTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return AlienSplats[Rand(4)];
	return Splats[Rand(4)];
}

function Material SprayTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return AlienSprays[Rand(2)];
	return Sprays[Rand(2)];
}

function Material PoolTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return AlienPool;
	return Pool;
}

// a hit: Damage after the game's scaling, the victim still standing or not
function Hit(Pawn Victim, Pawn Instigator, vector HitLocation, vector Momentum, int Damage, class<DamageType> DamageType)
{
	local vector Dir, HitL, HitN;
	local float Size;

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: hit " $ Victim $ " " $ Damage $ " " $ DamageType $ " bleeds " $ Bleeds(Victim, DamageType));
	if (Damage <= 0 || !Bleeds(Victim, DamageType))
		return;
	Hits++;
	if (VSize(Momentum) > 1)
		Dir = Normal(Momentum);
	else if (Instigator != None)
		Dir = Normal(HitLocation - Instigator.Location);
	else
		Dir = vector(Victim.Rotation) * -1;
	if (VSize(HitLocation - Victim.Location) > Victim.CollisionRadius * 3)
		HitLocation = Victim.Location;
	// the bigger the hit, the bigger the mark (a pistol ~10-20, a launcher ~100)
	Size = DecalScale * FClamp(0.35 + Damage / 120.0, 0.35, 1.0);

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: dir " $ Dir $ " from " $ HitLocation $ " texture " $ Sprays[0] $ " floor " $ Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) $ " at " $ HitL);
	// the spray behind the victim, along the shot (a little downward: blood falls)
	Dir = Normal(Dir + vect(0,0,-0.25));
	if (Trace(HitL, HitN, HitLocation + Dir * SprayReach, HitLocation + Dir * Victim.CollisionRadius, false) != None)
		Mark(SprayTex(Victim), HitL, HitN, Dir, Size * (0.8 + 0.6 * VSize(HitL - HitLocation) / SprayReach));
	// drips under the hit
	if (FRand() < 0.85 && Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) != None)
		Mark(SplatTex(Victim), HitL + VRand() * vect(1,1,0) * 30, HitN, vect(0,0,0), Size * 0.6);
	// a pool under a fresh body
	if (Victim.Health <= 0 || Damage >= Victim.Health)
		AddDying(Victim);
}

function AddDying(Pawn P)
{
	local int i;

	for (i = 0; i < Dying.Length; i++)
		if (Dying[i] == P)
			return;
	Dying[Dying.Length] = P;
	DyingTime[DyingTime.Length] = Level.TimeSeconds + 1.2 + FRand() * 0.6;
}

// projectiles: a new one from the player's gun is a shot (a casing); a vanished one hit
// something (a bullet hole where its last step meets a surface)
function TrackShots()
{
	local Projectile P;
	local int i;
	local bool bKnown;

	for (i = Shots.Length - 1; i >= 0; i--)
	{
		if (Shots[i] == None || Shots[i].bDeleteMe)
		{
			ShotGone(ShotLoc[i], ShotVel[i]);
			Shots.Remove(i, 1);
			ShotLoc.Remove(i, 1);
			ShotVel.Remove(i, 1);
		}
		else
		{
			ShotThroughCorpses(ShotLoc[i], Shots[i].Location);
			ShotLoc[i] = Shots[i].Location;
			ShotVel[i] = Shots[i].Velocity;
		}
	}
	if (class'ModSettings'.default.bGoreLog)
		LogGuns();
	if (bCasings)
		FindShells();
	ForEach DynamicActors(class'Projectile', P)
	{
		bKnown = false;
		for (i = 0; i < Shots.Length; i++)
			if (Shots[i] == P)
			{
				bKnown = true;
				break;
			}
		if (bKnown)
			continue;
		Shots[Shots.Length] = P;
		ShotLoc[ShotLoc.Length] = P.Location;
		ShotVel[ShotVel.Length] = P.Velocity;
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: shot " $ P.Class $ " owner " $ P.Owner $ " instigator " $ P.Instigator $ " speed " $ int(VSize(P.Velocity)));
	}
}

function LogGuns()
{
	local Pawn P;
	local string S;

	P = Level.GetLocalPlayerController().Pawn;
	if (P == None)
		return;
	if (AdventWeapon(P.RightWeapon) != None)
		S = "right " $ P.RightWeapon.Class $ " " $ P.RightWeapon.GetStateName() $ " clip " $ AdventWeapon(P.RightWeapon).AmmoAmount[0].fCurrentClipAmmo $ "/" $ AdventWeapon(P.RightWeapon).AmmoAmount[1].fCurrentClipAmmo $ " shots " $ AdventWeapon(P.RightWeapon).iCurShotCount $ " burst " $ AdventWeapon(P.RightWeapon).iCurBurstCount $ " sound " $ AdventWeapon(P.RightWeapon).fLastFireSoundTime $ " effect " $ AdventWeapon(P.RightWeapon).fLastEffectTime $ " stop " $ AdventWeapon(P.RightWeapon).fStopFireTime;
	if (AdventWeapon(P.LeftWeapon) != None)
		S = S $ " left " $ P.LeftWeapon.Class $ " " $ P.LeftWeapon.GetStateName() $ " clip " $ AdventWeapon(P.LeftWeapon).AmmoAmount[0].fCurrentClipAmmo $ "/" $ AdventWeapon(P.LeftWeapon).AmmoAmount[1].fCurrentClipAmmo;
	if (S != LastGuns)
		class'ModSettings'.static.Note("gore: guns " $ S);
	LastGuns = S;
	LogNewActors(P);
}

// the game's shell particles (fx_HumanBlaster_Shells and the like, one burst per shot):
// each becomes one ModCasing thrown the same way, and the particles go
function FindShells()
{
	local Emitter E;
	local ModCasing C;
	local vector Dir;
	local int i;

	ForEach DynamicActors(class'Emitter', E)
	{
		if (E.Tag == 'ModShell' || InStr(Caps(string(E.Class.Name)), "_SHELLS") < 0)
			continue;
		E.Tag = 'ModShell';
		for (i = 0; i < E.Emitters.Length && ShellMesh == None; i++)
			if (MeshEmitter(E.Emitters[i]) != None)
			{
				ShellMesh = MeshEmitter(E.Emitters[i]).StaticMesh;
				ShellScale = (E.Emitters[i].StartSizeRange.X.Min + E.Emitters[i].StartSizeRange.X.Max) / 2;
			}
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: shells " $ E.Class $ " at " $ E.Location $ " mesh " $ ShellMesh $ " scale " $ ShellScale);
		C = Spawn(class'ModCasing',,, E.Location, RotRand());
		if (C == None)
			continue;
		C.Gore = self;
		C.SetStaticMesh(ShellMesh);
		C.SetDrawScale(FClamp(ShellScale, 0.02, 2));
		if (E.Skins.Length > 0)
			C.Skins[0] = E.Skins[0];
		Dir = vector(E.Rotation);
		C.Launch(Dir * (120 + 80 * FRand()) + vect(0,0,1) * (160 + 80 * FRand()) + VRand() * 30, PhysicsVolume.Gravity.Z * 0.6);
		E.Kill();
	}
}

// a settled casing, flattened into a mark on the floor
function AddClutter(vector Spot, int Yaw)
{
	local vector HitL, HitN;
	local ModBloodDecal D;
	local rotator R;

	if (Trace(HitL, HitN, Spot - vect(0,0,40), Spot + vect(0,0,10), false) == None)
		return;
	while (Clutter.Length > 0 && (Clutter.Length >= MaxClutter || Clutter[0] == None || Clutter[0].bDeleteMe))
	{
		if (Clutter[0] != None && !Clutter[0].bDeleteMe)
			Clutter[0].Destroy();
		Clutter.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, HitL + HitN * 16);
	if (D == None)
		return;
	R.Yaw = Yaw;
	D.Place(CasingTex, HitL, HitN, vector(R), 0.22);
	D.LifeSpan = 600;
	Clutter[Clutter.Length] = D;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: casing settled at " $ HitL $ " (" $ Clutter.Length $ " on the floor)");
}

// the dead lying around (refreshed twice a second): Health gone, in the Dying state
function ScanCorpses()
{
	local Pawn P;
	local int i;
	local bool bKnown;

	for (i = Corpses.Length - 1; i >= 0; i--)
		if (Corpses[i] == None || Corpses[i].bDeleteMe)
		{
			if (class'ModSettings'.default.bGoreLog)
				class'ModSettings'.static.Note("gore: a corpse is gone (" $ Corpses.Length - 1 $ " left)");
			Corpses.Remove(i, 1);
		}
		else if (class'ModSettings'.default.bGoreLog && Level.TimeSeconds - LastCorpseLog > 5)
			LogCorpse(Corpses[i]);
	if (Level.TimeSeconds - LastCorpseLog > 5)
		LastCorpseLog = Level.TimeSeconds;
	ForEach DynamicActors(class'Pawn', P)
	{
		if (P.Health > 0 || P.IsHumanControlled() || P.bDeleteMe || !P.IsInState('Dying'))
			continue;
		bKnown = false;
		for (i = 0; i < Corpses.Length; i++)
			if (Corpses[i] == P)
			{
				bKnown = true;
				break;
			}
		if (!bKnown)
			Corpses[Corpses.Length] = P;
	}
}

// a shot's path from A to B through a body: closest approach to the body's axis, within its width
function ShotThroughCorpses(vector A, vector B)
{
	local int i;
	local Pawn P;
	local vector D, C, Q, Dir;
	local float T, L, R;

	if (!bCorpseShots || Corpses.Length == 0)
		return;
	D = B - A;
	L = VSize(D);
	if (L < 1)
		return;
	Dir = D / L;
	for (i = 0; i < Corpses.Length; i++)
	{
		P = Corpses[i];
		if (P == None || P.bDeleteMe)
			continue;
		C = P.Location;
		T = FClamp((C - A) Dot Dir, 0, L);
		Q = A + Dir * T;
		R = FMax(P.CollisionRadius, 30) * 1.3;
		if (VSize((Q - C) * vect(1,1,0)) > R || Q.Z > C.Z + 25 || Q.Z < C.Z - P.CollisionHeight - 15)
			continue;
		CorpseHit(P, Q, Dir);
		return;
	}
}

function CorpseHit(Pawn P, vector Spot, vector Dir)
{
	local vector HitL, HitN;

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: corpse hit " $ P $ " physics " $ P.Physics $ " at " $ Spot);
	// it bleeds like the living do (they don't reach NetDamage any more: Dying.TakeDamage
	// doesn't pass hits on)
	if (bBlood && BloodKind(P) != 0)
	{
		if (Trace(HitL, HitN, Spot + Normal(Dir + vect(0,0,-0.4)) * SprayReach, Spot, false) != None)
			Mark(SprayTex(P), HitL, HitN, Dir, DecalScale * 0.6);
		if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,10), false) != None)
			Mark(SplatTex(P), HitL + VRand() * vect(1,1,0) * 20, HitN, vect(0,0,0), DecalScale * 0.45);
	}
	if (P.LifeSpan > 0)
		P.LifeSpan += 0.2;
	if (P.Physics == PHYS_KarmaRagdoll)
		P.KAddImpulse(Dir * CorpseKick, Spot);
	else
		Limp(P, Dir, Spot);
}

// a body still in its death pose goes ragdoll, pushed along the shot (its species' own
// ragdoll skeleton, AdventPawn.RagdollOverride; the engine allows MaxRagdolls at a time)
function Limp(Pawn P, vector Dir, vector Spot)
{
	local AdventPawn A;
	local KarmaParamsSkel K;

	A = AdventPawn(P);
	if (A == None || A.RagdollOverride == "")
		return;
	A.KMakeRagdollAvailable();
	if (!A.KIsRagdollAvailable())
		return;
	if (KarmaParamsSkel(A.KParams) == None)
		A.KParams = CorpseParams;
	K = KarmaParamsSkel(A.KParams);
	if (K == None)
		return;
	K.KSkeleton = A.RagdollOverride;
	K.KStartLinVel = Dir * 250 + vect(0,0,60);
	K.KStartAngVel = VRand() * 3000;
	K.KShotStart = Spot - Dir;
	K.KShotEnd = Spot + Dir * 100;
	K.KShotStrength = CorpseKick;
	A.KSetBlockKarma(true);
	A.SetPhysics(PHYS_KarmaRagdoll);
	A.StopAnimating(true);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ A $ " went limp (" $ A.RagdollOverride $ "), physics " $ A.Physics);
}

// corpses near the player stay until the player walks away: the game's fade (AlphaFadeKill
// sets bAllowAlphaFading, fAlphaFade then runs out) is undone and remembered, and let go
// once the player is farther than HoldRange; the Dying state's out-of-sight timer is put
// off the same way. Only bodies lying on a floor: the game also fades bodies left hanging
// on a ledge or a slope (CheckForQuickDeadFade), and those still go.
function HoldCorpses()
{
	local Pawn Me;
	local AdventPawn A;
	local int i;

	if (Level.GetLocalPlayerController() == None)
		return;
	Me = Level.GetLocalPlayerController().Pawn;
	if (Me == None)
		return;
	for (i = Held.Length - 1; i >= 0; i--)
	{
		A = AdventPawn(Held[i]);
		if (A == None || A.bDeleteMe)
		{
			Held.Remove(i, 1);
			continue;
		}
		if (VSize(A.Location - Me.Location) > HoldRange || Held.Length > MaxHeld)
		{
			if (class'ModSettings'.default.bGoreLog)
				class'ModSettings'.static.Note("gore: letting " $ A $ " fade, " $ int(VSize(A.Location - Me.Location)) $ " away (" $ Held.Length - 1 $ " held)");
			A.bAllowAlphaFading = true;
			Held.Remove(i, 1);
		}
	}
	for (i = 0; i < Corpses.Length; i++)
	{
		A = AdventPawn(Corpses[i]);
		if (A == None || A.bDeleteMe || A.default.bAllowAlphaFading)    // holograms and the like always fade
			continue;
		if (VSize(A.Location - Me.Location) >= HoldRange)
			continue;
		// out of sight for a while, the Dying state's Timer destroys it: keep that off
		if (A.TimerRate > 0 && A.TimerRate - A.TimerCounter < 1.0)
			A.SetTimer(2.0, false);
		if (A.LifeSpan > 0 && A.LifeSpan < 2.0)
			A.LifeSpan = 2.0;
		if (A.bAllowAlphaFading && !IsHeld(A) && OnFloor(A))
		{
			if (class'ModSettings'.default.bGoreLog)
				class'ModSettings'.static.Note("gore: holding " $ A $ " (fade " $ A.fAlphaFade $ "), " $ int(VSize(A.Location - Me.Location)) $ " away");
			Held[Held.Length] = A;
		}
		if (IsHeld(A))
		{
			A.bAllowAlphaFading = false;
			A.fAlphaFade = 1;
			A.SetColorOverride(1, 1, 1, 1);
		}
	}
}

function LogCorpse(Pawn P)
{
	local float D;

	if (Level.GetLocalPlayerController().Pawn != None)
		D = VSize(P.Location - Level.GetLocalPlayerController().Pawn.Location);
	class'ModSettings'.static.Note("gore: corpse " $ P $ " " $ int(D) $ " away, fading " $ P.bAllowAlphaFading $ " " $ (AdventPawn(P) != None ? string(AdventPawn(P).fAlphaFade) : "") $ " timer " $ P.TimerCounter $ "/" $ P.TimerRate $ " life " $ P.LifeSpan $ " unseen " $ (Level.TimeSeconds - P.LastRenderTime) $ " held " $ IsHeld(P) $ " floor " $ OnFloor(P) $ " state " $ P.GetStateName() $ " physics " $ P.Physics);
}

function bool IsHeld(Pawn P)
{
	local int i;

	for (i = 0; i < Held.Length; i++)
		if (Held[i] == P)
			return true;
	return false;
}

function bool OnFloor(Pawn P)
{
	local vector HitL, HitN;
	local Actor A;

	A = Trace(HitL, HitN, P.Location - vect(0,0,1) * (P.CollisionHeight + 60), P.Location, false);
	return A != None && HitN.Z > 0.9 && (A == Level || A.bWorldGeometry);
}

// testing: actors the player's gun or pawn just made (what marks a shot)
function LogNewActors(Pawn P)
{
	local Actor A;
	local int i;
	local bool bKnown;

	ForEach DynamicActors(class'Actor', A)
	{
		if (A.Owner == None || (A.Owner != P.RightWeapon && A.Owner != P && A.Owner != P.LeftWeapon && A.Instigator != P))
			continue;
		if (A == P.RightWeapon || A == P.LeftWeapon || A == P.Controller)
			continue;
		bKnown = false;
		for (i = 0; i < Seen.Length; i++)
			if (Seen[i] == A)
			{
				bKnown = true;
				break;
			}
		if (bKnown)
			continue;
		Seen[Seen.Length] = A;
		class'ModSettings'.static.Note("gore: new " $ A.Class $ " owner " $ A.Owner $ " at " $ A.Location $ " t " $ Level.TimeSeconds);
	}
}

function ShotGone(vector Loc, vector Vel)
{
	local vector HitL, HitN;
	local Actor A;

	ShotThroughCorpses(Loc, Loc + Vel * 0.1);

	A = Trace(HitL, HitN, Loc + Vel * 0.1, Loc - Normal(Vel) * 20, false);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: shot gone at " $ Loc $ " hit " $ A $ " at " $ HitL);
	// a scorch on walls, floors and level meshes; nothing on characters (they bleed instead)
	if (bImpacts && A != None && (A == Level || A.bWorldGeometry || A.bStatic) && Pawn(A) == None)
		AddHole(Scorches[Rand(3)], HitL, HitN, DecalScale * (0.3 + 0.12 * FRand()));
}

event Tick(float DeltaTime)
{
	local int i;
	local vector HitL, HitN, Spot;
	local ModBloodDecal D;

	CorpseScan -= DeltaTime;
	if (CorpseScan <= 0)
	{
		CorpseScan = 0.5;
		ScanCorpses();
	}
	if (bHoldCorpses)
		HoldCorpses();
	TrackShots();
	for (i = Dying.Length - 1; i >= 0; i--)
	{
		if (Dying[i] != None && !Dying[i].bDeleteMe && Level.TimeSeconds < DyingTime[i])
			continue;
		if (Dying[i] != None && !Dying[i].bDeleteMe)
		{
			// where the body lies: ragdolls move their mesh, not always the actor; the
			// actor is still the best guess the script has
			Spot = Dying[i].Location;
			if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20), false) != None && HitN.Z > 0.6)
			{
				D = Mark(PoolTex(Dying[i]), HitL, HitN, vect(0,0,0), DecalScale * 0.6);
				if (D != None)
				{
					D.Grow(DecalScale * 0.2, DecalScale * (0.9 + FRand() * 0.4), 5 + FRand() * 3);
					D.LifeSpan = 300;
				}
			}
		}
		Dying.Remove(i, 1);
		DyingTime.Remove(i, 1);
	}
}

function ModBloodDecal AddHole(Material T, vector Spot, vector N, float Size)
{
	local ModBloodDecal D;

	while (Holes.Length > 0 && (Holes.Length >= MaxHoles || Holes[0] == None || Holes[0].bDeleteMe))
	{
		if (Holes[0] != None && !Holes[0].bDeleteMe)
			Holes[0].Destroy();
		Holes.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, Spot + N * 16);
	if (D == None)
		return None;
	D.Place(T, Spot, N, vect(0,0,0), Size);
	Holes[Holes.Length] = D;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ T.Name $ " at " $ Spot $ " (" $ Holes.Length $ " holes)");
	return D;
}

function ModBloodDecal Mark(Material T, vector Spot, vector N, vector Along, float Size)
{
	local ModBloodDecal D;

	if (class'ModSettings'.default.DebugDecalTexture != "")
		T = Material(DynamicLoadObject(class'ModSettings'.default.DebugDecalTexture, class'Material'));
	if (T == None)
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: no texture");
		return None;
	}
	while (Decals.Length > 0 && (Decals.Length >= MaxDecals || Decals[0] == None || Decals[0].bDeleteMe))
	{
		if (Decals[0] != None && !Decals[0].bDeleteMe)
			Decals[0].Destroy();
		Decals.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, Spot + N * 16);
	if (D == None)
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: the decal didn't spawn");
		return None;
	}
	D.Place(T, Spot, N, Along, Size);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ T.Name $ " at " $ Spot $ " normal " $ N $ " size " $ Size $ " (" $ Decals.Length + 1 $ " marks)");
	Decals[Decals.Length] = D;
	return D;
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Decals.Length; i++)
		if (Decals[i] != None)
			Decals[i].Destroy();
	for (i = 0; i < Holes.Length; i++)
		if (Holes[i] != None)
			Holes[i].Destroy();
	for (i = 0; i < Clutter.Length; i++)
		if (Clutter[i] != None)
			Clutter[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
     Splats(0)=Texture'AdventMod.Blood.BloodSplat0'
     Splats(1)=Texture'AdventMod.Blood.BloodSplat1'
     Splats(2)=Texture'AdventMod.Blood.BloodSplat2'
     Splats(3)=Texture'AdventMod.Blood.BloodSplat3'
     Sprays(0)=Texture'AdventMod.Blood.BloodSpray0'
     Sprays(1)=Texture'AdventMod.Blood.BloodSpray1'
     Pool=Texture'AdventMod.Blood.BloodPool0'
     AlienSplats(0)=Texture'AdventMod.Blood.AlienSplat0'
     AlienSplats(1)=Texture'AdventMod.Blood.AlienSplat1'
     AlienSplats(2)=Texture'AdventMod.Blood.AlienSplat2'
     AlienSplats(3)=Texture'AdventMod.Blood.AlienSplat3'
     AlienSprays(0)=Texture'AdventMod.Blood.AlienSpray0'
     AlienSprays(1)=Texture'AdventMod.Blood.AlienSpray1'
     AlienPool=Texture'AdventMod.Blood.AlienPool0'
     bHoldCorpses=True
     HoldRange=2500.000000
     MaxHeld=16
     Scorches(0)=Texture'AdventMod.Blood.Scorch0'
     Scorches(1)=Texture'AdventMod.Blood.Scorch1'
     Scorches(2)=Texture'AdventMod.Blood.Scorch2'
     CasingTex=Texture'AdventMod.Blood.Casing0'
     bCasings=True
     MaxClutter=150
     bCorpseShots=True
     CorpseKick=8000.000000
     Begin Object Class=KarmaParamsSkel Name=CorpseRagdoll
         KConvulseSpacing=(Max=2.200000)
         KLinearDamping=0.150000
         KAngularDamping=0.050000
         KBuoyancy=1.000000
         KStartEnabled=True
         KVelDropBelowThreshold=50.000000
         bHighDetailOnly=False
         bClientOnly=True
         bKDoubleTickRate=True
         bKStayUpright=False
         bKAllowRotate=False
         bDestroyOnWorldPenetrate=True
         bDoSafetime=True
         KFriction=0.600000
         KImpactThreshold=500.000000
     End Object
     CorpseParams=KarmaParamsSkel'AdventMod.ModGore.CorpseRagdoll'
     bImpacts=True
     MaxHoles=60
     bBlood=True
     MaxDecals=80
     SprayReach=260.000000
     DecalScale=1.600000
}
