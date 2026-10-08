//=============================================================================
// Places the creative team's redesign for the map being played, a moment after it
// starts (once U2Gore's GoreManager is there):
//   pool        dried blood under a body (it died here, long ago)
//   spray       blood on the wall behind a body, thrown away from where the creature came
//   drag_trail  smears from a body toward the door it crawled for
//   smear       blood on the floor before the first fight (the sign before the creature)
//   claw_marks  streaks down the nearest wall (the same)
//   keylight    a warm light on the first creature's spot (SanctuaryLight)
//   cover       three of the map's crates round an arena that had too little (SanctuaryCover)
// The marks are U2Gore's own decals, kept for good (LifeSpan 0) and out of its cap;
// nothing is laid in water (GoreManager.Wet).
// Scenes=(Map="M08A1",Kind="pool",At=(X=..,Y=..,Z=..),Dir=(..),To=(..)) in U2Sanctuary.ini.
// Console: set SanctuaryDirector bLog True (saves the ini).
//=============================================================================
class SanctuaryDirector extends Info
	config(U2Sanctuary);

struct Scene
{
	var string Map;
	var string Kind;
	var vector At;
	var vector Dir;
	var vector To;
};
var config array<Scene> Scenes;
var config string CoverMesh;
var config bool bEnabled, bLog;

var GoreManager Gore;
var string MapName;
var int Placed, Skipped;

event PostBeginPlay()
{
	local string S;

	Super.PostBeginPlay();
	S = string(Level);
	MapName = Caps(Left(S, InStr(S, ".")));
	SetTimer(0.5, false);
}

event Timer()
{
	local int i;

	foreach DynamicActors(class'GoreManager', Gore)
		break;
	if (!bEnabled)
		return;
	for (i = 0; i < Scenes.Length; i++)
		if (Caps(Scenes[i].Map) == MapName)
		{
			if (Stage(Scenes[i]))
				Placed++;
			else
				Skipped++;
		}
	Log("U2Sanctuary: "$MapName$": "$Placed$" scenes placed, "$Skipped$" skipped (gore "$(Gore != None)$")");
}

function bool Stage(Scene S)
{
	switch (S.Kind)
	{
		case "keylight":   return KeyLight(S);
		case "cover":      return Cover(S);
	}
	if (Gore == None)
		return false;
	switch (S.Kind)
	{
		case "pool":       return Pool(S);
		case "spray":      return Spray(S);
		case "drag_trail": return Trail(S);
		case "smear":      return Smear(S);
		case "claw_marks": return Claws(S);
	}
	return false;
}

// a permanent mark through U2Gore's decal (not its capped list), never in water
function bool Lay(Texture T, vector Spot, vector N, vector Along, float Size)
{
	local GoreDecal D;

	if (T == None || Gore.Wet(Spot + N * 8))
		return false;
	D = Spawn(class'GoreDecal',,, Spot + N * 16);
	if (D == None)
		return false;
	D.Place(T, Spot, N, Along, Size);
	D.LifeSpan = 0;
	if (bLog)
		Log("U2Sanctuary: "$T.Name$" at "$Spot);
	return true;
}

function bool Floor(vector At, out vector HitL, out vector HitN)
{
	return Gore.Surface(HitL, HitN, At - vect(0,0,400), At + vect(0,0,60)) && HitN.Z > 0.6;
}

function bool Pool(Scene S)
{
	local vector HitL, HitN;

	if (!Floor(S.At, HitL, HitN))
		return false;
	return Lay(Gore.Pool, HitL, HitN, vect(0,0,0), 170 + FRand() * 70);
}

function bool Spray(Scene S)
{
	local vector HitL, HitN, From, D;

	D = S.Dir;
	D.Z = 0;
	if (VSize(D) < 0.1)
		D = VRand() * vect(1,1,0);
	D = Normal(D);
	From = S.At + vect(0,0,40);
	if (Gore.Surface(HitL, HitN, From + D * 320 + vect(0,0,30), From))
		return Lay(Gore.Sprays[Rand(2)], HitL, HitN, D, 230);
	// no wall in reach: it went on the floor, thrown that way
	if (Floor(S.At + D * 110, HitL, HitN))
		return Lay(Gore.Sprays[Rand(2)], HitL, HitN, D, 200);
	return false;
}

function bool Trail(Scene S)
{
	local vector HitL, HitN, D, P;
	local float L, T;
	local int n;

	D = S.To - S.At;
	D.Z = 0;
	L = VSize(D);
	if (L < 60)
		return false;
	D = D / L;
	// smears from the body most of the way to the door, thinner as they go
	for (T = 40; T < L * 0.8; T += 60 + FRand() * 30)
	{
		P = S.At + D * T + (D Cross vect(0,0,1)) * (FRand() - 0.5) * 30;
		if (Floor(P, HitL, HitN) && Lay(Gore.Splats[Rand(4)], HitL, HitN, D, 120 - 50 * T / L))
			n++;
	}
	return n > 0;
}

function bool Smear(Scene S)
{
	local vector HitL, HitN;
	local int i;

	if (!Floor(S.At, HitL, HitN) || !Lay(Gore.Sprays[Rand(2)], HitL, HitN, VRand() * vect(1,1,0), 180))
		return false;
	for (i = 0; i < 3; i++)
		if (Floor(S.At + VRand() * vect(1,1,0) * 120, HitL, HitN))
			Lay(Gore.Splats[Rand(4)], HitL, HitN, vect(0,0,0), 60 + FRand() * 40);
	return true;
}

function bool Claws(Scene S)
{
	local vector HitL, HitN, BestL, BestN, From, D;
	local float Best;
	local int i;
	local rotator R;

	// the nearest wall, at chest height
	From = S.At + vect(0,0,60);
	Best = 1e9;
	for (i = 0; i < 8; i++)
	{
		R.Yaw = i * 8192;
		D = vector(R);
		if (Gore.Surface(HitL, HitN, From + D * 500, From) && Abs(HitN.Z) < 0.5 && VSize(HitL - From) < Best)
		{
			Best = VSize(HitL - From);
			BestL = HitL;
			BestN = HitN;
		}
	}
	if (Best > 1e8)
		return Smear(S);
	// three streaks raked down the wall
	D = Normal(BestN Cross vect(0,0,1));
	for (i = -1; i <= 1; i++)
		Lay(Gore.Sprays[Rand(2)], BestL + D * i * 22 + vect(0,0,1) * (FRand() * 20), BestN, vect(0,0,-1), 140);
	return true;
}

function bool KeyLight(Scene S)
{
	local SanctuaryLight L;

	L = Spawn(class'SanctuaryLight',,, S.At + vect(0,0,170));
	return L != None;
}

function bool Cover(Scene S)
{
	local StaticMesh M;
	local SanctuaryCover C;
	local vector HitL, HitN, D, From, Spot;
	local int i, n;
	local float Free;
	local rotator R;

	M = StaticMesh(DynamicLoadObject(CoverMesh, class'StaticMesh'));
	if (M == None || Gore == None)
		return false;
	From = S.At + vect(0,0,50);
	for (i = 0; i < 8 && n < 3; i++)
	{
		R.Yaw = i * 8192 + Rand(2000);
		D = vector(R);
		Free = 900;
		if (Gore.Surface(HitL, HitN, From + D * 900, From))
			Free = VSize(HitL - From);
		if (Free < 360)
			continue;
		Spot = S.At + D * FMax(280, Free * 0.5);
		if (!Floor(Spot, HitL, HitN) || Gore.Wet(HitL + vect(0,0,20)))
			continue;
		R.Yaw = Rand(65536);
		C = Spawn(class'SanctuaryCover',,, HitL + vect(0,0,4), R);
		if (C == None)
			continue;
		C.StaticMesh = M;
		C.SetCollision(false, false, false);
		C.SetCollision(true, true, true);
		n++;
		i++;          // the next one a quarter turn on, not next to it
	}
	return n > 0;
}

defaultproperties
{
	bEnabled=True
	CoverMesh="Mission_08M.Crates.Boxnum2"
	RemoteRole=ROLE_None
}
