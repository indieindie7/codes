//=============================================================================
// U2Gore - blood that stays. One per level (GoreMutator spawns it), fed every
// hit by GoreRules. Ported from the Advent Rising mod's ModGore (first slice):
//   - a spray on the wall or floor behind the victim, along the shot, if one is
//     within SprayReach: the bigger the hit, the bigger the spray;
//   - drips on the floor under the hit, most of the time;
//   - a pool spreading under each body, a moment after it falls.
// The marks are GoreDecal projectors with procedural textures (tools\
// make_textures.py). At most MaxDecals at once: the oldest goes first.
// Who bleeds, and in which colour, follows the game's own tables: the damage
// type must have a blood effect (bullets and shrapnel do; fire, electricity,
// gas and EMP don't), and the victim's gib set gives the species: humans and
// Skaarj red, Izarians and Araknids green, Drakk and machines nothing.
// The game's own blood particles and gibs are left as they are.
// Console: set GoreManager bBlood False | MaxDecals 120 | DecalSize 150 | bLog True
//=============================================================================
class GoreManager extends Info
	config(U2Gore);

var config bool bBlood;
var config int MaxDecals;
var config float SprayReach;       // how far behind a victim a wall still catches the spray
var config float DecalSize;        // the biggest marks' width, world units
var config float PoolSize;
var config bool bLog;

var Texture Splats[4], Sprays[2], Pool;
var Texture IchorSplats[4], IchorSprays[2], IchorPool;
var array<GoreDecal> Decals;
var array<Pawn> Dying;             // bodies waiting for their pool
var array<float> DyingTime;
var int Hits, Marks;

event PostBeginPlay()
{
	local GoreRules R;

	Super.PostBeginPlay();
	if (Level.Game == None)
		return;
	R = Spawn(class'GoreRules');
	R.Gore = Self;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = R;
	else
		Level.Game.GameRulesModifiers.AddGameRules(R);
	Log("U2Gore: watching hits (blood "$bBlood$", at most "$MaxDecals$" marks)");
}

// 1 red, 2 green, 0 none: by the victim's gib set (the game's own species table)
static function int BloodKind(Pawn P)
{
	local string S;

	if (U2Pawn(P) == None || U2Pawn(P).GibSetClass == None)
		return 0;
	S = Caps(string(U2Pawn(P).GibSetClass.Name));
	if (InStr(S, "HUMAN") >= 0 || InStr(S, "SKAARJ") >= 0 || InStr(S, "GENERIC") >= 0)
		return 1;
	if (InStr(S, "IZARIAN") >= 0 || InStr(S, "ARAKNID") >= 0 || InStr(S, "COCKROACH") >= 0)
		return 2;
	return 0;
}

function bool Bleeds(Pawn P, class<DamageType> DamageType)
{
	if (!bBlood || P == None || BloodKind(P) == 0)
		return false;
	if (class<DamageTypeImpl>(DamageType) != None && class<DamageTypeImpl>(DamageType).default.ParticleEffect == None)
		return false;
	return true;
}

function Texture SplatTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return IchorSplats[Rand(4)];
	return Splats[Rand(4)];
}

function Texture SprayTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return IchorSprays[Rand(2)];
	return Sprays[Rand(2)];
}

// a hit: Damage after the game's scaling, before it is taken off the victim's health
function Hit(Pawn Victim, Pawn Instigator, vector HitLocation, vector Momentum, int Damage, class<DamageType> DamageType)
{
	local vector Dir, HitL, HitN;
	local float Size;

	if (bLog)
		Log("U2Gore: hit "$Victim$" "$Damage$" "$DamageType$" bleeds "$Bleeds(Victim, DamageType));
	// a body still gets its pool when fire or a blast killed it
	if (bBlood && BloodKind(Victim) != 0 && Damage >= Victim.Health)
		AddDying(Victim);
	if (!Bleeds(Victim, DamageType))
		return;
	Hits++;
	if (VSize(Momentum) > 1)
		Dir = Normal(Momentum);
	else if (Instigator != None && Instigator != Victim)
		Dir = Normal(HitLocation - Instigator.Location);
	else
		Dir = vector(Victim.Rotation) * -1;
	if (VSize(HitLocation - Victim.Location) > Victim.CollisionRadius * 3)
		HitLocation = Victim.Location;
	// the bigger the hit, the bigger the mark (a rifle bullet ~10, a shotgun blast or grenade ~100)
	Size = DecalSize * FClamp(0.35 + Damage / 120.0, 0.35, 1.0);

	// the spray behind the victim, along the shot (a little downward: blood falls)
	Dir = Normal(Dir + vect(0,0,-0.25));
	if (Trace(HitL, HitN, HitLocation + Dir * SprayReach, HitLocation + Dir * Victim.CollisionRadius, false) != None)
		Mark(SprayTex(Victim), HitL, HitN, Dir, Size * (0.8 + 0.6 * VSize(HitL - HitLocation) / SprayReach));
	// drips under the hit
	if (FRand() < 0.85 && Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) != None)
		Mark(SplatTex(Victim), HitL + VRand() * vect(1,1,0) * 30, HitN, vect(0,0,0), Size * 0.6);
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

event Tick(float DeltaTime)
{
	local int i;
	local vector HitL, HitN, Spot;
	local GoreDecal D;
	local Texture T;

	for (i = Dying.Length - 1; i >= 0; i--)
	{
		if (Dying[i] != None && !Dying[i].bDeleteMe && Level.TimeSeconds < DyingTime[i])
			continue;
		// (a gibbed body is gone by now: no pool; one that survived after all gets none either)
		if (Dying[i] != None && !Dying[i].bDeleteMe && Dying[i].Health <= 0)
		{
			Spot = Dying[i].Location;
			if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20), false) != None && HitN.Z > 0.6)
			{
				if (BloodKind(Dying[i]) == 2)
					T = IchorPool;
				else
					T = Pool;
				D = Mark(T, HitL, HitN, vect(0,0,0), PoolSize * 0.3);
				if (D != None)
				{
					D.Grow(PoolSize * 0.3, PoolSize * (0.9 + FRand() * 0.4), 5 + FRand() * 3);
					D.LifeSpan = 300;
				}
			}
		}
		Dying.Remove(i, 1);
		DyingTime.Remove(i, 1);
	}
}

function GoreDecal Mark(Texture T, vector Spot, vector N, vector Along, float Size)
{
	local GoreDecal D;

	while (Decals.Length > 0 && (Decals.Length >= MaxDecals || Decals[0] == None || Decals[0].bDeleteMe))
	{
		if (Decals[0] != None && !Decals[0].bDeleteMe)
			Decals[0].Destroy();
		Decals.Remove(0, 1);
	}
	D = Spawn(class'GoreDecal',,, Spot + N * 16);
	if (D == None)
		return None;
	D.Place(T, Spot, N, Along, Size);
	Decals[Decals.Length] = D;
	Marks++;
	if (bLog)
		Log("U2Gore: "$T.Name$" at "$Spot$" normal "$N$" size "$Size$" ("$Decals.Length$" marks)");
	return D;
}

defaultproperties
{
	bBlood=True
	MaxDecals=80
	SprayReach=260.000000
	DecalSize=200.000000
	PoolSize=190.000000
	Splats(0)=Texture'BloodSplat0'
	Splats(1)=Texture'BloodSplat1'
	Splats(2)=Texture'BloodSplat2'
	Splats(3)=Texture'BloodSplat3'
	Sprays(0)=Texture'BloodSpray0'
	Sprays(1)=Texture'BloodSpray1'
	Pool=Texture'BloodPool0'
	IchorSplats(0)=Texture'IchorSplat0'
	IchorSplats(1)=Texture'IchorSplat1'
	IchorSplats(2)=Texture'IchorSplat2'
	IchorSplats(3)=Texture'IchorSplat3'
	IchorSprays(0)=Texture'IchorSpray0'
	IchorSprays(1)=Texture'IchorSpray1'
	IchorPool=Texture'IchorPool0'
	RemoteRole=ROLE_None
}
