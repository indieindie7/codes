//=============================================================================
// Dust where nobody walks, worked out live when a map loads (no per-map work, so
// it runs on every stock map), and worn away where people do walk.
//
// 1. Corners (a cheap ambient occlusion): from every AI navigation point, rays
//    run out low across the floor; where one meets a wall, the wall's foot is a
//    candidate. Its score rises if another wall is close beside it (a corner),
//    if something hangs over it (a table, stairs) and if the opposite wall is
//    close (a narrow gap).
// 2. Traffic: the AI path network is where people walk. The further a candidate
//    is from the nearest path, the dustier; right beside a path it keeps only
//    OnPathDust of its score.
// The best candidates (spaced apart, at most MaxSpots) get a GrimeSpot.
// 3. Wear, the live part: a character walking over a spot steps it lighter, and
//    after the faintest step it is gone, so routes people actually use clear up.
// Then GrimeClutter sets small props down at the dustiest spots (bClutter).
//
// Console (also from U2Pilot scripts), e.g. "set GrimeManager bShow False":
//   bShow       False hides every spot, True shows them again (A/B screenshots)
//   bRebuild    True clears everything and runs the analysis again (after changing
//               the numbers below)
//   ViewSpot    N stands the player in front of spot N (0 = the dustiest) and logs it
// Results: "Grime:" lines in System\Unreal2.log.
//=============================================================================
class GrimeManager extends Info;

struct GrimeCand
{
	var vector Loc;          // floor point at the wall's foot
	var vector Wall;         // horizontal wall normal, into the room
	var float Score;         // 0-1
};

// analysis
var() int RaysPerNav;        // rays from each navigation point
var() float RayLength;       // how far they look for a wall
var() float RayHeight;       // above the floor: low, to find the wall's foot (and stair risers)
var() float WallInset;       // the spot's middle sits this far out from the wall
var() float CornerReach;     // a second wall this close beside = a corner
var() float CoverReach;      // something this close overhead = covered
var() float PathNear;        // closer than this to a path: OnPathDust only
var() float PathFar;         // further than this from a path: full dust
var() float OnPathDust;      // share of the dust kept right beside a path
var() float MinScore;        // weaker candidates are dropped
var() float MinSize, MaxSize;   // spot width for score 0 and 1
var() float Spacing;         // spots overlap at most this much (1 = edge to edge at half width)
var() int MaxSpots;
var() int NavsPerTick;       // spread the work so loading doesn't hitch
// wear
var() bool bScuff;
var() float ScuffRadius;     // share of the spot's width a foot must be within
var() float ScuffPerSecond;  // wear per second of walking over a spot (1 = one step)
var() bool bClutter;         // small props at the dustiest spots (GrimeClutter)

// console switches
var bool bShow, bShown;
var bool bRebuild;
var int ViewSpot, LastViewSpot;

// state
var int Phase;               // 0 waiting, 1 scanning, 2 placing, 3 done
var float PhaseTime, StartTime, ScuffClock;
var NavigationPoint Cur;
var int Navs, Rays, Walls, Bin;
var array<GrimeCand> Cands;
var array<GrimeSpot> Spots;
var GrimeClutter Clutter;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	StartOver();
}

function StartOver()
{
	local int i;

	if (Clutter != None)
		Clutter.Destroy();
	Clutter = None;
	for (i = 0; i < Spots.Length; i++)
		if (Spots[i] != None)
			Spots[i].Destroy();
	Spots.Length = 0;
	Cands.Length = 0;
	Navs = 0;
	Rays = 0;
	Walls = 0;
	Phase = 0;
	PhaseTime = Level.TimeSeconds + 1.0;   // let the level settle first
	bShown = bShow;
}

function float SmoothStep(float E0, float E1, float X)
{
	local float T;

	T = FClamp((X - E0) / (E1 - E0), 0, 1);
	return T * T * (3 - 2 * T);
}

function bool Blocked(vector A, vector B)
{
	local vector HitLoc, HitNorm;

	return Trace(HitLoc, HitNorm, B, A, false) != None;
}

// distance from P to the segment A-B
function float SegDist(vector P, vector A, vector B)
{
	local vector AB;
	local float T;

	AB = B - A;
	T = FClamp(((P - A) dot AB) / FMax(AB dot AB, 1.0), 0, 1);
	return VSize(P - (A + AB * T));
}

// distance from a floor point to the nearest AI path near N (N's own paths and its
// neighbours'); navigation points sit at body height, so the point is lifted to match
function float PathDistance(NavigationPoint N, vector P)
{
	local int i, j;
	local ReachSpec R, R2;
	local float Best;

	P.Z += 44;
	Best = VSize(P - N.Location);
	for (i = 0; i < N.PathList.Length; i++)
	{
		R = N.PathList[i];
		if (R == None || R.End == None)
			continue;
		Best = FMin(Best, SegDist(P, N.Location, R.End.Location));
		for (j = 0; j < R.End.PathList.Length; j++)
		{
			R2 = R.End.PathList[j];
			if (R2 != None && R2.End != None)
				Best = FMin(Best, SegDist(P, R.End.Location, R2.End.Location));
		}
	}
	return Best;
}

function ScanNav(NavigationPoint N)
{
	local vector Start, Dir, HitLoc, HitNorm, Away;
	local Actor Hit;
	local int i;
	local float Ang;

	// the floor under the navigation point
	Hit = Trace(HitLoc, HitNorm, N.Location - vect(0,0,256), N.Location, false);
	if (Hit == None || HitNorm.Z < 0.7)
		return;
	Navs++;
	Start = HitLoc + vect(0,0,1) * RayHeight;
	Ang = FRand() * 6.2831853 / RaysPerNav;
	for (i = 0; i < RaysPerNav; i++)
	{
		Dir.X = Cos(Ang + i * 6.2831853 / RaysPerNav);
		Dir.Y = Sin(Ang + i * 6.2831853 / RaysPerNav);
		Dir.Z = 0;
		Rays++;
		Hit = Trace(HitLoc, HitNorm, Start + Dir * RayLength, Start, false);
		// a wall (not a door, which moves, nor terrain)
		if (Hit == None || Mover(Hit) != None || TerrainInfo(Hit) != None || Abs(HitNorm.Z) > 0.35)
			continue;
		Away = HitNorm;
		Away.Z = 0;
		Away = Normal(Away);
		TryFoot(N, HitLoc + Away * WallInset, Away);
	}
}

function TryFoot(NavigationPoint N, vector P, vector Away)
{
	local vector HitLoc, HitNorm, Foot, Low, Side;
	local Actor Hit;
	local float Occ, Traffic, Score;
	local GrimeCand C;

	// the floor at the wall's foot
	Hit = Trace(HitLoc, HitNorm, P - vect(0,0,64), P + vect(0,0,8), false);
	if (Hit == None || HitNorm.Z < 0.7 || Mover(Hit) != None)
		return;
	Walls++;
	Foot = HitLoc;
	Low = Foot + vect(0,0,10);

	// how enclosed (ambient occlusion, roughly)
	Occ = 0.45;
	Side = Away cross vect(0,0,1);
	if (Blocked(Low, Low + Side * CornerReach) || Blocked(Low, Low - Side * CornerReach))
		Occ += 0.3;
	if (Blocked(Low, Low + vect(0,0,1) * CoverReach))
		Occ += 0.2;
	if (Blocked(Low, Low + Away * CornerReach * 1.5))
		Occ += 0.1;
	Occ = FMin(Occ, 1.0);

	// how far from where people walk
	Traffic = SmoothStep(PathNear, PathFar, PathDistance(N, Foot));
	Score = Occ * (OnPathDust + (1 - OnPathDust) * Traffic);
	if (Score < MinScore)
		return;
	C.Loc = Foot;
	C.Wall = Away;
	C.Score = Score;
	Cands[Cands.Length] = C;
}

// one score band per call, dustiest first, so the strongest candidates win the space
function PlaceBin(int B)
{
	local int i, j, Lvl;
	local float Size;
	local bool bFree;
	local GrimeSpot S;

	for (i = 0; i < Cands.Length && Spots.Length < MaxSpots; i++)
	{
		if (Min(int(Cands[i].Score * 10), 9) != B)
			continue;
		Size = (MinSize + (MaxSize - MinSize) * Cands[i].Score) * (0.85 + 0.3 * FRand());
		bFree = true;
		for (j = 0; j < Spots.Length && bFree; j++)
			if (VSize(Spots[j].Foot - Cands[i].Loc) < Spacing * 0.5 * (Spots[j].Size + Size))
				bFree = false;
		if (!bFree)
			continue;
		S = Spawn(class'GrimeSpot', self,, Cands[i].Loc + vect(0,0,24));
		if (S == None)
			continue;
		if (Cands[i].Score >= 0.7)      Lvl = 0;
		else if (Cands[i].Score >= 0.5) Lvl = 1;
		else                            Lvl = 2;
		S.Place(Cands[i].Loc, Cands[i].Wall, Cands[i].Score, Size, Lvl);
		if (!bShown)
			S.Show(false);
		Spots[Spots.Length] = S;
	}
}

// characters walking over spots wear them lighter
function Scuff(float Seconds)
{
	local Pawn P;
	local vector Feet, D;
	local int i, Steps;

	foreach DynamicActors(class'Pawn', P)
	{
		if (P.Health <= 0 || P.Physics != PHYS_Walking || VSize(P.Velocity) < 60)
			continue;
		Feet = P.Location;
		Feet.Z -= P.CollisionHeight;
		for (i = 0; i < Spots.Length; i++)
		{
			if (Spots[i] == None || Spots[i].Stage > 2)
				continue;
			D = Spots[i].Foot - Feet;
			if (Abs(D.Z) > 48)
				continue;
			D.Z = 0;
			if (VSize(D) > Spots[i].Size * ScuffRadius)
				continue;
			Steps = int(Spots[i].Wear);
			Spots[i].Wear += Seconds * ScuffPerSecond;
			if (int(Spots[i].Wear) > Steps)
			{
				Spots[i].Step(bShown);
				Log("Grime: spot "$i$" walked over by "$P.Name$", now stage "$Spots[i].Stage);
			}
		}
	}
}

function ShowAll(bool bNewShown)
{
	local int i;

	bShown = bNewShown;
	for (i = 0; i < Spots.Length; i++)
		if (Spots[i] != None)
			Spots[i].Show(bShown);
	Log("Grime: "$Spots.Length$" spots "$OnOff(bShown));
}

function ViewAt(int i)
{
	local PlayerController PC;
	local vector Stand, Eye;
	local rotator R;
	local GrimeSpot S;

	if (i < 0 || i >= Spots.Length || Spots[i] == None)
	{
		Log("Grime: no spot "$i$" (there are "$Spots.Length$")");
		return;
	}
	S = Spots[i];
	foreach DynamicActors(class'PlayerController', PC)
		break;
	if (PC == None || PC.Pawn == None)
		return;
	Stand = S.Foot + S.WallNormal * 200 + vect(0,0,1) * (PC.Pawn.CollisionHeight + 8);
	if (!PC.Pawn.SetLocation(Stand))
		Log("Grime: view spot "$i$": blocked where the player would stand");
	Eye = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	R = rotator(S.Foot - Eye);
	PC.SetRotation(R);
	PC.Pawn.SetRotation(R);
	PC.ClientSetRotation(R);
	Log("Grime: viewing spot "$i$" score "$S.Score$" stage "$S.Stage$" size "$int(S.Size)$" at ("$int(S.Foot.X)$","$int(S.Foot.Y)$","$int(S.Foot.Z)$")");
}

function string OnOff(bool b)
{
	if (b)
		return "shown";
	return "hidden";
}

event Tick(float DeltaTime)
{
	local int i;

	if (bRebuild)
	{
		bRebuild = false;
		Log("Grime: rebuild");
		StartOver();
		return;
	}
	if (bShow != bShown)
		ShowAll(bShow);
	if (ViewSpot != LastViewSpot)
	{
		LastViewSpot = ViewSpot;
		if (ViewSpot >= 0)
			ViewAt(ViewSpot);
	}

	if (Phase == 0)
	{
		if (Level.TimeSeconds < PhaseTime)
			return;
		StartTime = Level.TimeSeconds;
		Cur = Level.NavigationPointList;
		Phase = 1;
	}
	if (Phase == 1)
	{
		for (i = 0; i < NavsPerTick && Cur != None; i++)
		{
			ScanNav(Cur);
			Cur = Cur.nextNavigationPoint;
		}
		if (Cur == None)
		{
			Log("Grime: scanned "$Navs$" navigation points, "$Rays$" rays, "$Walls$" wall feet, "$Cands.Length$" candidates");
			Bin = 9;
			Phase = 2;
		}
		return;
	}
	if (Phase == 2)
	{
		PlaceBin(Bin);
		Bin--;
		if (Bin < 0 || Spots.Length >= MaxSpots)
		{
			Log("Grime: placed "$Spots.Length$" spots (max "$MaxSpots$") in "$Level.TimeSeconds - StartTime$" s");
			Phase = 3;
			if (bClutter)
			{
				Clutter = Spawn(class'GrimeClutter', self);
				if (Clutter != None)
					Clutter.StartClutter(self);
			}
		}
		return;
	}
	if (bScuff && Phase == 3)
	{
		ScuffClock += DeltaTime;
		if (ScuffClock >= 0.25)
		{
			Scuff(ScuffClock);
			ScuffClock = 0;
		}
	}
}

event Destroyed()
{
	local int i;

	if (Clutter != None)
		Clutter.Destroy();
	for (i = 0; i < Spots.Length; i++)
		if (Spots[i] != None)
			Spots[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	RaysPerNav=16
	RayLength=768.000000
	RayHeight=14.000000
	WallInset=6.000000
	CornerReach=96.000000
	CoverReach=160.000000
	PathNear=48.000000
	PathFar=224.000000
	OnPathDust=0.350000
	MinScore=0.300000
	MinSize=96.000000
	MaxSize=176.000000
	Spacing=0.700000
	MaxSpots=160
	NavsPerTick=2
	bScuff=True
	ScuffRadius=0.450000
	ScuffPerSecond=0.500000
	bClutter=True
	bShow=True
	bShown=True
	ViewSpot=-1
	LastViewSpot=-1
	RemoteRole=ROLE_None
}
