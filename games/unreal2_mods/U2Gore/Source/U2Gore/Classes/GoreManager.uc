//=============================================================================
// U2Gore - blood that stays. One per level (GoreMutator spawns it), fed every
// hit by GoreRules. Ported from the Advent Rising mod's ModGore:
//   - a spray on the wall or floor behind the victim, along the shot, if one is
//     within SprayReach: the bigger the hit, the bigger the spray;
//   - drips on the floor under the hit, most of the time;
//   - a pool spreading under each body, a moment after it falls;
//   - the badly wounded leave drops where they go, fewer as the wound clots;
//   - when the game takes a body away, remains stay on the floor where it lay;
//   - blood lands on the bodies near a hit (GoreCoat): they look bloody.
// The marks are GoreDecal projectors with procedural textures (tools\
// make_textures.py). At most MaxDecals at once: the oldest goes first.
// Who bleeds, and in which colour, follows the game's own tables: the damage
// type must have a blood effect (bullets and shrapnel do; fire, electricity,
// gas and EMP don't), and the victim's gib set gives the species: humans and
// Skaarj red, Izarians and Araknids green, Drakk and machines nothing.
// The game's own blood particles and gibs are left as they are.
// LIVE BLOOD (2026-10-08, the Advent chat's d3d8 layer, fork gi-cascades acfbd43 with
// gorelink=1): a body's pool is a region the layer simulates (it spreads, finds the
// floor's slope, splashes when walked through) and a spray on a wall runs down it. The
// commands go out through GoreLink. Without the layer the placeholders are plain grey
// (no change under the x2 multiply): set bLive False to go back to the grown pools.
// No mark is laid in water (the probe asks the spot's PhysicsVolume).
// Console: set GoreManager bBlood False | MaxDecals 120 | DecalSize 150 | bLog True
//=============================================================================
class GoreManager extends Info
	config(U2Gore);

var config bool bBlood;
var config int MaxDecals;
var config float SprayReach;       // how far behind a victim a wall still catches the spray
var config float DecalSize;        // the biggest marks' width, world units
var config float PoolSize;
var config bool bBleedTrail;       // the wounded leave drops where they go
var config float BleedClot;        // seconds a wound takes to stop dripping
var config bool bRemains;          // a body the game takes away leaves remains on the floor
var config int MaxRemains;
var config float RemainsSize;
var config bool bBodyBlood;        // a hit leaves a stain on the body, where it hit (GoreBodyDecal)
var config int MaxBodyDecals;
var config float BodySize;         // the biggest stain's width, world units
var config bool bCoats;            // (the other way: skin x blood combiners, GoreCoat; only bodies that list their skins)
var config int MaxCoats;
var config bool bScreenBlood;      // a death close to the player splashes the screen (UIScripts/U2Gore.ui)
var config float ScreenBloodReach;
var config bool bLog;
var config bool bLive;             // pools and wall runs simulated by the d3d8 layer (GoreLink)
var config bool bWallRuns;
var config float RunChance, RunSize;
var config float RegionSize, LivePour, LivePourSecs;

var Texture Splats[4], Sprays[2], Pool, RemainsTex[2], CoatTex[3];
var Texture IchorSplats[4], IchorSprays[2], IchorPool, IchorRemains[2], IchorCoatTex[3];
var array<GoreDecal> Decals, Remains;
var array<Pawn> Dying;             // bodies waiting for their pool
var array<float> DyingTime;
struct Bleeder
{
	var Pawn P;
	var float Rate;        // 0..1: how hard it bleeds
	var float Next;        // seconds to the next drop
};
var array<Bleeder> Bleeders;
var array<Pawn> Corpses;           // the dead, where each lies and its blood,
var array<vector> CorpseLoc;       // kept for when the body is gone
var array<int> CorpseKind;
var float CorpseScan;
var array<GoreCoat> Coats;
var GoreDying DyingPhase;
var array<GoreBodyDecal> BodyDecals;
var ComponentHandle Screen;        // the splash on screen now
var float ScreenUntil;
var int ScreenCount;
var int Hits, Marks, CoatCount, RemainsCount, BodyCount, TrailCount, LiveCount, RunCount, WetSkips;
var GoreLink Link;
var GoreProbe Probe;
var Texture PoolLive[8], RunLive[8];
var GoreLive Pools[8], Runs[8];
var int NextRun;

event PostBeginPlay()
{
	local GoreRules R;

	Super.PostBeginPlay();
	if (Level.Game == None)
		return;
	R = Spawn(class'GoreRules');
	R.Gore = Self;
	Link = Spawn(class'GoreLink');
	Probe = Spawn(class'GoreProbe');
	DyingPhase = Spawn(class'GoreDying', self);
	if (DyingPhase != None)
		DyingPhase.Gore = self;
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
	{
		AddDying(Victim);
		if (bScreenBlood && !Victim.IsRealPlayer())
			ScreenSplash(Victim);
	}
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

	if (bBodyBlood)
		BodyMark(Victim, HitLocation, Dir, Size);
	// the spray behind the victim, along the shot (a little downward: blood falls)
	Dir = Normal(Dir + vect(0,0,-0.25));
	if (Surface(HitL, HitN, HitLocation + Dir * SprayReach, HitLocation + Dir * Victim.CollisionRadius))
	{
		Mark(SprayTex(Victim), HitL, HitN, Dir, Size * (0.8 + 0.6 * VSize(HitL - HitLocation) / SprayReach));
		if (bLive && bWallRuns && Abs(HitN.Z) < 0.5 && FRand() < RunChance)
			WallRun(HitL, HitN, LayerKind(Victim), FClamp(Damage / 60.0, 0.3, 1.5));
	}
	// drips under the hit
	if (FRand() < 0.85 && Surface(HitL, HitN, HitLocation - vect(0,0,400), HitLocation))
		Mark(SplatTex(Victim), HitL + VRand() * vect(1,1,0) * 30, HitN, vect(0,0,0), Size * 0.6);
	if (bBleedTrail && Victim.Health > Damage && !Victim.IsRealPlayer())
		Bleed(Victim, Damage);
	if (bCoats)
		Spatter(Victim, HitLocation, 0.2 + Damage / 150.0, 130);
}

// the first solid surface along a line: the level itself, terrain or a static mesh. (A plain Trace without
// actors goes through static meshes, and floors and crates are often those: the mark would land on the
// level geometry hidden underneath. One with actors stops at the bodies themselves.)
function bool Surface(out vector HitL, out vector HitN, vector End, vector Start)
{
	local Actor A;

	foreach TraceActors(class'Actor', A, HitL, HitN, End, Start)
		// (a face seen from behind is the inside of something the line started in: go on)
		if ((A == Level || A.bWorldGeometry || TerrainInfo(A) != None || StaticMeshActor(A) != None) && (HitN Dot (End - Start)) < 0)
			return true;
	return false;
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

	if ((~Screen) && Level.TimeSeconds > ScreenUntil)
		Screen = class'UIConsole'.static.DestroyComponent(Screen);
	CorpseScan -= DeltaTime;
	if (CorpseScan <= 0)
	{
		CorpseScan = 0.5;
		if (bRemains)
			ScanCorpses();
	}
	if (bBleedTrail)
		BleedTrails(DeltaTime);
	for (i = Dying.Length - 1; i >= 0; i--)
	{
		if (Dying[i] != None && !Dying[i].bDeleteMe && Level.TimeSeconds < DyingTime[i])
			continue;
		// (a gibbed body is gone by now: no pool; one that survived after all gets none either)
		if (Dying[i] != None && !Dying[i].bDeleteMe && Dying[i].Health <= 0)
		{
			Spot = Dying[i].Location;
			if (Surface(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20)) && HitN.Z > 0.6 &&
				!(bLive && PourInto(HitL, HitN, LayerKind(Dying[i]))))
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

// ---- blood on the screen -------------------------------------------------------------------
// something died within ScreenBloodReach of the player: a few splats near the screen's edges, fading
// out (one of three layouts per colour in UIScripts/U2Gore.ui; one at a time)
function ScreenSplash(Pawn Victim)
{
	local Controller C;
	local Pawn Me;
	local string Layout;

	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None && C.Pawn != None)
			Me = C.Pawn;
	if (Me == None || VSize(Me.Location - Victim.Location) > ScreenBloodReach)
		return;
	if (~Screen)
		Screen = class'UIConsole'.static.DestroyComponent(Screen);
	if (BloodKind(Victim) == 2)
		Layout = "ScreenIchor" $ Rand(3);
	else
		Layout = "ScreenBlood" $ Rand(3);
	Screen = class'UIConsole'.static.LoadComponent("U2Gore", Layout);
	if (~Screen)
	{
		class'UIConsole'.static.SetOwner(Screen, Self);
		class'UIConsole'.static.AddComponent(Screen);
		ScreenUntil = Level.TimeSeconds + 4.6;
		ScreenCount++;
	}
	if (bLog)
		Log("U2Gore: screen "$Layout$" shown "$(~Screen));
}

event Destroyed()
{
	if (~Screen)
		Screen = class'UIConsole'.static.DestroyComponent(Screen);
	Super.Destroyed();
}

// ---- bleeding trails -----------------------------------------------------------------------
function Bleed(Pawn P, int Damage)
{
	local int i;
	local Bleeder B;
	local float Add;

	Add = Damage / (0.3 * FMax(P.default.Health, 100));
	for (i = 0; i < Bleeders.Length; i++)
		if (Bleeders[i].P == P)
		{
			Bleeders[i].Rate = FMin(Bleeders[i].Rate + Add, 1.0);
			return;
		}
	if (Bleeders.Length >= 16)
		return;
	B.P = P;
	B.Rate = FMin(Add, 1.0);
	B.Next = 0.3;
	Bleeders[Bleeders.Length] = B;
}

// drops under the wounded, fewer as the wound clots; none from the dead (they pool)
function BleedTrails(float DeltaTime)
{
	local int i;
	local Pawn P;
	local vector HitL, HitN;

	for (i = Bleeders.Length - 1; i >= 0; i--)
	{
		P = Bleeders[i].P;
		Bleeders[i].Rate -= DeltaTime / BleedClot;
		if (P == None || P.bDeleteMe || P.Health <= 0 || P.bHidden || Bleeders[i].Rate <= 0.05)
		{
			Bleeders.Remove(i, 1);
			continue;
		}
		Bleeders[i].Next -= DeltaTime;
		if (Bleeders[i].Next > 0)
			continue;
		// a drop every 0.25 s at the worst, every 1.5 s when nearly clotted
		Bleeders[i].Next = 0.25 + 1.25 * (1 - Bleeders[i].Rate) + 0.2 * FRand();
		if (Surface(HitL, HitN, P.Location - vect(0,0,1) * (P.CollisionHeight + 120), P.Location))
		{
			TrailCount++;
			Mark(SplatTex(P), HitL + VRand() * vect(1,1,0) * 14, HitN, vect(0,0,0), DecalSize * (0.14 + 0.16 * Bleeders[i].Rate));
		}
	}
}

// ---- remains -------------------------------------------------------------------------------
// the dead are remembered with where they lie; one that is gone (the game removes bodies after a
// while, and gibs them at once) leaves remains there
function ScanCorpses()
{
	local Pawn P;
	local int i;
	local bool bKnown;

	for (i = Corpses.Length - 1; i >= 0; i--)
	{
		P = Corpses[i];
		if (P == None || P.bDeleteMe || P.Health > 0)
		{
			if (P == None || P.bDeleteMe)
				AddRemains(CorpseLoc[i], CorpseKind[i]);
			Corpses.Remove(i, 1);
			CorpseLoc.Remove(i, 1);
			CorpseKind.Remove(i, 1);
		}
		else
			CorpseLoc[i] = P.Location;
	}
	foreach DynamicActors(class'Pawn', P)
	{
		if (P.Health > 0 || P.bDeleteMe || P.bHidden || P.IsRealPlayer() || BloodKind(P) == 0)
			continue;
		bKnown = false;
		for (i = 0; i < Corpses.Length; i++)
			if (Corpses[i] == P)
			{
				bKnown = true;
				break;
			}
		if (!bKnown)
		{
			Corpses[Corpses.Length] = P;
			CorpseLoc[CorpseLoc.Length] = P.Location;
			CorpseKind[CorpseKind.Length] = BloodKind(P);
		}
	}
}

// flat on the floor under where the body lay, turned any way
function AddRemains(vector Spot, int Kind)
{
	local vector HitL, HitN;
	local GoreDecal D;
	local Texture T;

	if (!Surface(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20)) || HitN.Z < 0.6)
		return;
	while (Remains.Length > 0 && (Remains.Length >= MaxRemains || Remains[0] == None || Remains[0].bDeleteMe))
	{
		if (Remains[0] != None && !Remains[0].bDeleteMe)
			Remains[0].Destroy();
		Remains.Remove(0, 1);
	}
	if (Kind == 2)
		T = IchorRemains[Rand(2)];
	else
		T = RemainsTex[Rand(2)];
	D = Spawn(class'GoreDecal',,, HitL + HitN * 16);
	if (D == None)
		return;
	D.Place(T, HitL, HitN, vect(0,0,0), RemainsSize * (1.0 + 0.25 * FRand()));
	D.LifeSpan = 600;
	Remains[Remains.Length] = D;
	RemainsCount++;
	if (bLog)
		Log("U2Gore: remains at "$HitL$" ("$Remains.Length$")");
}

// ---- blood on characters -------------------------------------------------------------------
// Blood from a hit lands on the bodies around it: the victim's own, and whoever stands within
// Reach (the player too). Each body has one coat (GoreCoat), which gets heavier with more blood;
// the blood's colour is the first bleeder's.
function Spatter(Pawn From, vector Spot, float Amount, float Reach)
{
	local Pawn P;
	local int Kind;

	Kind = BloodKind(From);
	if (Kind == 0)
		return;
	Amount = FMin(Amount, 1.5);
	AddCoat(From, Amount, Kind);
	foreach RadiusActors(class'Pawn', P, Reach, Spot)
		if (P != From && !P.bHidden && P.Health > 0)
			AddCoat(P, Amount * 0.6 * (1 - VSize(P.Location - Spot) / (Reach + P.CollisionRadius + 1)), Kind);
}

function AddCoat(Pawn P, float Amount, int Kind)
{
	local int i, Lightest;
	local GoreCoat C;

	if (Amount <= 0.02 || P == None || P.bHidden)
		return;
	for (i = Coats.Length - 1; i >= 0; i--)
	{
		if (Coats[i] == None || Coats[i].bDeleteMe)
		{
			Coats.Remove(i, 1);
			continue;
		}
		if (Coats[i].Wearer == P)
		{
			Coats[i].More(Amount);
			return;
		}
	}
	if (Coats.Length >= MaxCoats)
	{
		// the lightest coat that isn't the player's makes room
		Lightest = -1;
		for (i = 0; i < Coats.Length; i++)
			if (!Coats[i].Wearer.IsRealPlayer() && (Lightest < 0 || Coats[i].Amount < Coats[Lightest].Amount))
				Lightest = i;
		if (Lightest < 0)
			return;
		Coats[Lightest].Destroy();
		Coats.Remove(Lightest, 1);
	}
	C = Spawn(class'GoreCoat',,, P.Location);
	if (C == None)
		return;
	C.Gore = Self;
	if (!C.Wear(P, Kind, Amount))
	{
		if (bLog)
			Log("U2Gore: no blood coat for "$P$": "$P.Skins.Length$" skins, mesh "$P.Mesh);
		C.Destroy();
		return;
	}
	CoatCount++;
	if (bLog)
		Log("U2Gore: blood coat on "$P$" (kind "$Kind$", amount "$Amount$", skin "$C.OwnSkin[0]$", "$C.Slots$" slots, "$(Coats.Length + 1)$" coats)");
	Coats[Coats.Length] = C;
}

// a stain on the body where the shot went in; the oldest goes when there are too many
function BodyMark(Pawn P, vector Spot, vector Dir, float Size)
{
	local GoreBodyDecal D;

	while (BodyDecals.Length > 0 && (BodyDecals.Length >= MaxBodyDecals || BodyDecals[0] == None || BodyDecals[0].bDeleteMe))
	{
		if (BodyDecals[0] != None && !BodyDecals[0].bDeleteMe)
			BodyDecals[0].Destroy();
		BodyDecals.Remove(0, 1);
	}
	D = Spawn(class'GoreBodyDecal',,, Spot);
	if (D == None)
		return;
	D.Place(SplatTex(P), P, Spot, Dir, BodySize * Size / DecalSize);
	BodyDecals[BodyDecals.Length] = D;
	BodyCount++;
	if (bLog)
		Log("U2Gore: body stain on "$P$" ("$BodyDecals.Length$")");
}

function Texture CoatMaterial(int Kind, int Level)
{
	if (Kind == 2)
		return IchorCoatTex[Clamp(Level, 0, 2)];
	return CoatTex[Clamp(Level, 0, 2)];
}

function GoreDecal Mark(Texture T, vector Spot, vector N, vector Along, float Size)
{
	local GoreDecal D;

	if (Wet(Spot + N * 8))
		return None;
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

// ---- live blood (the d3d8 layer through GoreLink) -------------------------------------------
// 0 red, 1 the layer's other colour (its purple stands in for Izarian green)
function int LayerKind(Pawn P)
{
	if (BloodKind(P) == 2)
		return 1;
	return 0;
}

function bool Wet(vector Spot)
{
	if (Probe == None)
		return false;
	Probe.SetLocation(Spot);
	if (Probe.PhysicsVolume != None && Probe.PhysicsVolume.bWaterVolume)
	{
		WetSkips++;
		return true;
	}
	return false;
}

// a body's blood goes into the live region under it; if none covers the spot a new one is laid there
// (a free slot, else the region farthest from the player, which the layer freezes as it is)
function bool PourInto(vector Spot, vector N, int Kind)
{
	local int i, K;
	local float D, Far;
	local Pawn Me;
	local Controller C;
	local GoreLive R;

	if (Link == None || Wet(Spot + N * 8))
		return false;
	for (i = 0; i < 8; i++)
		if (Pools[i] != None && !Pools[i].bDeleteMe && Pools[i].PourAt(Spot, LivePour, LivePourSecs, Kind))
			return true;
	K = -1;
	for (i = 0; i < 8 && K < 0; i++)
		if (Pools[i] == None || Pools[i].bDeleteMe)
			K = i;
	if (K < 0)
	{
		for (C = Level.ControllerList; C != None; C = C.NextController)
			if (PlayerController(C) != None && C.Pawn != None)
				Me = C.Pawn;
		Far = -1;
		for (i = 0; i < 8; i++)
		{
			D = float(i);
			if (Me != None)
				D = VSize(Pools[i].Location - Me.Location);
			if (D > Far)
			{
				Far = D;
				K = i;
			}
		}
		Pools[K].EndLive();
	}
	R = Spawn(class'GoreLive',,, Spot + N * 16);
	if (R == None)
		return false;
	R.Place(PoolLive[K], Spot, N, vect(0,0,0), RegionSize);
	R.GoLive(Link, K, PoolLive[K], RegionSize, LivePour, LivePourSecs, Kind);
	Pools[K] = R;
	LiveCount++;
	if (bLog)
		Log("U2Gore: live pool slot "$K$" at "$Spot);
	return true;
}

// blood on a wall runs down it: into the run region already there, or a new one with the spot near its top
function WallRun(vector Spot, vector N, int Kind, float Amount)
{
	local int i, K;
	local float U, W;
	local vector Down, Across, Center;
	local GoreLive R;

	for (i = 0; i < 8; i++)
		if (Runs[i] != None && !Runs[i].bDeleteMe && Runs[i].RunLocal(Spot, U, W))
		{
			Runs[i].Drip(U, W, Amount);
			return;
		}
	K = -1;
	for (i = 0; i < 8 && K < 0; i++)
		if (Runs[i] == None || Runs[i].bDeleteMe)
			K = i;
	if (K < 0)
	{
		K = NextRun;
		NextRun = (NextRun + 1) % 8;
		Runs[K].EndRun();
	}
	// down along the wall; the region's middle below the spot (the blood has room to run)
	Down = Normal(vect(0,0,-1) - N * (vect(0,0,-1) Dot N));
	Across = Normal(N Cross Down);
	Center = Spot + Down * RunSize * 0.3;
	if (Wet(Center + N * 8))
		return;
	R = Spawn(class'GoreLive',,, Center + N * 16);
	if (R == None)
		return;
	R.Place(RunLive[K], Center, N, Across, RunSize);
	R.GoRun(Link, K, RunLive[K], RunSize, Kind);
	Runs[K] = R;
	RunCount++;
	if (R.RunLocal(Spot, U, W))
		R.Drip(U, W, Amount);
	if (bLog)
		Log("U2Gore: wall run slot "$K$" at "$Spot);
}

defaultproperties
{
	bLive=True
	bWallRuns=True
	RunChance=0.800000
	RunSize=150.000000
	RegionSize=640.000000
	LivePour=1.400000
	LivePourSecs=2.600000
	PoolLive(0)=Texture'BloodLive0'
	PoolLive(1)=Texture'BloodLive1'
	PoolLive(2)=Texture'BloodLive2'
	PoolLive(3)=Texture'BloodLive3'
	PoolLive(4)=Texture'BloodLive4'
	PoolLive(5)=Texture'BloodLive5'
	PoolLive(6)=Texture'BloodLive6'
	PoolLive(7)=Texture'BloodLive7'
	RunLive(0)=Texture'BloodRun0'
	RunLive(1)=Texture'BloodRun1'
	RunLive(2)=Texture'BloodRun2'
	RunLive(3)=Texture'BloodRun3'
	RunLive(4)=Texture'BloodRun4'
	RunLive(5)=Texture'BloodRun5'
	RunLive(6)=Texture'BloodRun6'
	RunLive(7)=Texture'BloodRun7'
	bBlood=True
	MaxDecals=80
	SprayReach=260.000000
	DecalSize=200.000000
	PoolSize=190.000000
	bBleedTrail=True
	BleedClot=12.000000
	bRemains=True
	MaxRemains=12
	RemainsSize=220.000000
	bBodyBlood=True
	MaxBodyDecals=16
	BodySize=85.000000
	bCoats=False
	bScreenBlood=True
	ScreenBloodReach=320.000000
	MaxCoats=10
	Splats(0)=Texture'BloodSplat0'
	Splats(1)=Texture'BloodSplat1'
	Splats(2)=Texture'BloodSplat2'
	Splats(3)=Texture'BloodSplat3'
	Sprays(0)=Texture'BloodSpray0'
	Sprays(1)=Texture'BloodSpray1'
	Pool=Texture'BloodPool0'
	RemainsTex(0)=Texture'BloodRemains0'
	RemainsTex(1)=Texture'BloodRemains1'
	CoatTex(0)=Texture'BloodCoat0'
	CoatTex(1)=Texture'BloodCoat1'
	CoatTex(2)=Texture'BloodCoat2'
	IchorSplats(0)=Texture'IchorSplat0'
	IchorSplats(1)=Texture'IchorSplat1'
	IchorSplats(2)=Texture'IchorSplat2'
	IchorSplats(3)=Texture'IchorSplat3'
	IchorSprays(0)=Texture'IchorSpray0'
	IchorSprays(1)=Texture'IchorSpray1'
	IchorPool=Texture'IchorPool0'
	IchorRemains(0)=Texture'IchorRemains0'
	IchorRemains(1)=Texture'IchorRemains1'
	IchorCoatTex(0)=Texture'IchorCoat0'
	IchorCoatTex(1)=Texture'IchorCoat1'
	IchorCoatTex(2)=Texture'IchorCoat2'
	RemoteRole=ROLE_None
}
