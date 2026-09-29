//=============================================================================
// U2Gore - central gore spawner. One instance per level (via U2GoreMutator).
// Pawns don't call the engine's own gib code directly; instead your Pawn's
// Died() override (or wherever you already hook kills) calls
// SpawnGoreForDeath() here. Keeping it in one place lets us cap how many
// gibs/decals exist at once, same idea as SSShadowManager capping shadows.
//
// NOTE: base classes 'Gib' and 'Decal' and their exact spawn args are named
// from memory of the UE2 API - verify against the installed Unreal2 SDK
// headers before compiling.
//=============================================================================
class U2GoreManager extends Info;

var array<class<U2Gib> >     GibClasses;      // body-part variants, randomized per death
var array<class<U2BloodDecal> > DecalClasses; // splat variants, randomized per hit

var array<U2Gib>        LiveGibs;
var array<U2BloodDecal> LiveDecals;
var array<U2HitReactionController> HitControllers;

var int   MaxGibs;          // oldest is destroyed once this is exceeded
var int   MaxDecals;
var int   GibsPerDeath;
var float GibThreshold;     // overkill damage (damage - remaining health) needed to gib
var float GibSpeedMin;
var float GibSpeedMax;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	Log("U2Gore: manager active on "$Level.Title);
	SetTimer(2.0, true); // low-frequency: just pruning stale hit controllers
}

event Timer()
{
	local int i;

	for (i = HitControllers.Length - 1; i >= 0; i--)
		if (HitControllers[i] == None || HitControllers[i].Owner == None || HitControllers[i].Owner.bDeleteMe)
			HitControllers.Remove(i, 1); // GoToFullRagdoll() already Destroy()s itself; this just drops dangling refs
}

// One controller per living Pawn, created on first need rather than swept
// for like SSShadowManager does with shadows - we already have the Pawn
// reference at hand wherever damage is being dispatched.
function U2HitReactionController GetHitController(Pawn P)
{
	local int i;
	local U2HitReactionController C;

	for (i = 0; i < HitControllers.Length; i++)
		if (HitControllers[i] != None && HitControllers[i].Owner == P)
			return HitControllers[i];

	C = U2HitReactionController(Spawn(class'U2HitReactionController', P,, P.Location, P.Rotation));
	if (C != None)
		HitControllers[HitControllers.Length] = C;
	return C;
}

// Call this from Pawn.Died() (or your kill-notify hook) with the killing
// blow's numbers. OverkillDamage = Damage - (Health before the hit was
// applied), i.e. how far below zero health went; <= 0 means a clean kill.
function SpawnGoreForDeath(Pawn P, class<DamageType> DamageType, vector HitLocation, vector Momentum, float OverkillDamage)
{
	SpawnBloodDecal(HitLocation, Normal(Momentum) * -1);

	if (OverkillDamage < GibThreshold || GibClasses.Length == 0)
		return; // normal death anim/ragdoll handles it, no dismemberment

	SpawnGibs(P, HitLocation, Momentum);
}

function SpawnGibs(Pawn P, vector HitLocation, vector Momentum)
{
	local int i;
	local U2Gib G;
	local vector Spread, GibVel;
	local class<U2Gib> GibClass;

	for (i = 0; i < GibsPerDeath; i++)
	{
		GibClass = GibClasses[Rand(GibClasses.Length)];

		// scatter around the hit point rather than the pawn's origin so a
		// point-blank shot doesn't spawn every gib stacked in one spot
		Spread = VRand() * (P.CollisionRadius * 0.5);
		G = Spawn(GibClass,,, HitLocation + Spread, RotRand());
		if (G == None)
			continue;

		GibVel = Normal(Momentum + VRand() * 0.6) * (GibSpeedMin + FRand() * (GibSpeedMax - GibSpeedMin));
		G.Velocity = GibVel;
		G.Instigator = P;

		Track(G);
	}
}

function SpawnBloodDecal(vector HitLocation, vector HitNormal)
{
	local U2BloodDecal D;
	local class<U2BloodDecal> DecalClass;

	if (DecalClasses.Length == 0)
		return;

	DecalClass = DecalClasses[Rand(DecalClasses.Length)];
	D = Spawn(DecalClass,,, HitLocation, Rotator(HitNormal));
	if (D == None)
		return;

	Track(D);
}

function Track(Actor A)
{
	local U2Gib G;
	local U2BloodDecal D;

	G = U2Gib(A);
	if (G != None)
	{
		LiveGibs[LiveGibs.Length] = G;
		if (LiveGibs.Length > MaxGibs)
		{
			if (LiveGibs[0] != None)
				LiveGibs[0].Destroy();
			LiveGibs.Remove(0, 1);
		}
		return;
	}

	D = U2BloodDecal(A);
	if (D != None)
	{
		LiveDecals[LiveDecals.Length] = D;
		if (LiveDecals.Length > MaxDecals)
		{
			if (LiveDecals[0] != None)
				LiveDecals[0].Destroy();
			LiveDecals.Remove(0, 1);
		}
	}
}

defaultproperties
{
	MaxGibs=64
	MaxDecals=48
	GibsPerDeath=5
	GibThreshold=40.0
	GibSpeedMin=150.0
	GibSpeedMax=400.0
	RemoteRole=ROLE_None
}
