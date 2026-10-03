//=============================================================================
// Clutter in the dusty places: after GrimeManager has placed its dust, small
// props are set down against the walls at the dustiest spots (corners, under
// things, away from the AI paths), a few per spot.
//
// Which props: the map's own. Every StaticMeshActor in the level is measured
// with traces (height, footprint, where its pivot sits) and the small ones that
// stand on a floor become the kinds to copy, so each map gets clutter in its own
// style without a list of asset names. ExtraMeshes adds named meshes
// ("Package.Group.Name") on top, measured the same way on a probe copy.
// Every kind is logged ("Grime: kind ..."), which doubles as a survey of the
// small props each map has.
//
// Live: walking into a piece kicks it (GrimeProp.Kick).
//
// Console: "set GrimeClutter bShow False" hides the clutter, "set GrimeClutter
// ViewProp N" stands in front of piece N. GrimeManager's bRebuild redoes both.
//=============================================================================
class GrimeClutter extends Info;

struct GrimeKind
{
	var StaticMesh Mesh;
	var float Scale;
	var vector Scale3D;
	var rotator Tilt;        // the source's pitch and roll (lying-down props stay lying down)
	var float Radius, Height, Lift;
	var Actor Source;        // for its skins (None for ExtraMeshes)
};

var() array<string> ExtraMeshes;   // more meshes to use, "Package.Group.Name"
var() bool bBorrowLevelProps;      // use the map's own small props
var() float MaxPropRadius;         // bigger props are not clutter
var() float MaxPropHeight;
var() float MinPropSize;           // smaller than this (radius) is too fiddly to see
var() int MaxKinds;
var() float MinScore;              // only dust spots at least this dusty get clutter
var() float Chance;                // share of those spots that get any
var() int MaxPerSpot;
var() int MaxPieces;
var() int MeasurePerTick;
var() bool bKick;

var bool bShow, bShown;
var int ViewProp, LastViewProp;

var GrimeManager Manager;
var int Phase;               // 0 collecting, 1 measuring, 2 placing, 3 live
var int Index, Measured, Unmeasured, TooBig, Floating;
var float KickClock;
var array<StaticMeshActor> Pending;
var array<GrimeKind> Kinds;
var array<GrimeProp> Pieces;

function StartClutter(GrimeManager M)
{
	local StaticMeshActor S;

	Manager = M;
	foreach AllActors(class'StaticMeshActor', S)
		if (S.Class == class'StaticMeshActor' && S.StaticMesh != None && !S.bHidden)
			Pending[Pending.Length] = S;
	Phase = 1;
	Index = 0;
	bShown = bShow;
	Log("Grime: clutter: "$Pending.Length$" level props to measure");
}

// size of A from traces against it alone: top, bottom, and the furthest of four sides
function bool Measure(Actor A, out float Radius, out float Height, out float Lift)
{
	local Actor Hit;
	local vector HitLoc, HitNorm, Mid, Dir, D;
	local float Top, Bottom;
	local bool bTop, bBottom, bSide;
	local int i;

	foreach TraceActors(class'Actor', Hit, HitLoc, HitNorm, A.Location - vect(0,0,400), A.Location + vect(0,0,400))
		if (Hit == A)
		{
			Top = HitLoc.Z;
			bTop = true;
			break;
		}
	foreach TraceActors(class'Actor', Hit, HitLoc, HitNorm, A.Location + vect(0,0,400), A.Location - vect(0,0,400))
		if (Hit == A)
		{
			Bottom = HitLoc.Z;
			bBottom = true;
			break;
		}
	if (!bTop || !bBottom || Top <= Bottom)
		return false;
	Height = Top - Bottom;
	Lift = A.Location.Z - Bottom;
	Mid = A.Location;
	Mid.Z = (Top + Bottom) / 2;
	Radius = 0;
	for (i = 0; i < 4; i++)
	{
		Dir.X = Cos(i * 1.5707963);
		Dir.Y = Sin(i * 1.5707963);
		Dir.Z = 0;
		foreach TraceActors(class'Actor', Hit, HitLoc, HitNorm, Mid, Mid + Dir * 400)
			if (Hit == A)
			{
				D = HitLoc - A.Location;
				D.Z = 0;
				Radius = FMax(Radius, VSize(D));
				bSide = true;
				break;
			}
	}
	return bSide;
}

// is there a floor right under A's lowest point?
function bool OnFloor(Actor A, float Lift)
{
	local Actor Hit;
	local vector HitLoc, HitNorm, Base;

	Base = A.Location - vect(0,0,1) * Lift;
	Hit = Trace(HitLoc, HitNorm, Base - vect(0,0,12), Base + vect(0,0,2), true);
	return Hit != None && Hit != A && HitNorm.Z > 0.7;
}

function AddKind(StaticMesh M, float Scale, vector Scale3D, rotator Tilt, float Radius, float Height, float Lift, Actor Source)
{
	local int i;
	local GrimeKind K;

	for (i = 0; i < Kinds.Length; i++)
		if (Kinds[i].Mesh == M)
			return;
	if (Kinds.Length >= MaxKinds)
		return;
	K.Mesh = M;
	K.Scale = Scale;
	K.Scale3D = Scale3D;
	K.Tilt = Tilt;
	K.Tilt.Yaw = 0;
	K.Radius = Radius;
	K.Height = Height;
	K.Lift = Lift;
	K.Source = Source;
	Kinds[Kinds.Length] = K;
	Log("Grime: kind "$Kinds.Length - 1$" "$M$" radius "$int(Radius)$" height "$int(Height)$" lift "$int(Lift)$" scale "$Scale);
}

function MeasureLevelProp(StaticMeshActor A)
{
	local bool bCol, bBlock, bPlayers;
	local float R, H, L;
	local bool bOk;

	// props without collision can't be traced: switch it on just for the measuring
	bCol = A.bCollideActors;
	bBlock = A.bBlockActors;
	bPlayers = A.bBlockPlayers;
	if (!bCol)
		A.SetCollision(true, false, false);
	bOk = Measure(A, R, H, L);
	if (!bCol)
		A.SetCollision(bCol, bBlock, bPlayers);
	if (!bOk)
	{
		Unmeasured++;
		return;
	}
	Measured++;
	if (R > MaxPropRadius || H > MaxPropHeight || R < MinPropSize)
	{
		TooBig++;
		return;
	}
	if (!OnFloor(A, L))
	{
		Floating++;
		return;
	}
	AddKind(A.StaticMesh, A.DrawScale, A.DrawScale3D, A.Rotation, R, H, L, A);
}

function MeasureExtra(string Path)
{
	local StaticMesh M;
	local GrimeProp Probe;
	local float R, H, L;
	local vector Spot;

	M = StaticMesh(DynamicLoadObject(Path, class'StaticMesh'));
	if (M == None)
	{
		Log("Grime: extra mesh "$Path$" not found");
		return;
	}
	// a probe copy far above the first navigation point, traced against alone
	if (Level.NavigationPointList == None)
		return;
	Spot = Level.NavigationPointList.Location + vect(0,0,3000);
	Probe = Spawn(class'GrimeProp', self,, Spot);
	if (Probe == None)
		return;
	Probe.Setup(M, 1.0, vect(1,1,1), 0, 0, None);
	Probe.SetCollision(true, false, false);
	if (Measure(Probe, R, H, L))
		AddKind(M, 1.0, vect(1,1,1), rot(0,0,0), R, H, L, None);
	else
		Log("Grime: extra mesh "$Path$" could not be measured");
	Probe.Destroy();
}

function bool Blocked(vector A, vector B)
{
	local vector HitLoc, HitNorm;

	return Trace(HitLoc, HitNorm, B, A, false) != None;
}

// one piece of kind K near spot S, against the wall, on the same floor, clear of
// the walls, of what's overhead and of other pieces
function bool TryPiece(GrimeSpot S, int k)
{
	local vector Side, P, HitLoc, HitNorm, C, D;
	local Actor Hit;
	local rotator R;
	local GrimeProp G;
	local int i;

	Side = S.WallNormal cross vect(0,0,1);
	P = S.Foot + S.WallNormal * (Kinds[k].Radius + 2 + 24 * FRand()) + Side * ((FRand() * 2 - 1) * S.Size * 0.35);
	Hit = Trace(HitLoc, HitNorm, P - vect(0,0,48), P + vect(0,0,24), false);
	if (Hit == None || HitNorm.Z < 0.8 || Abs(HitLoc.Z - S.Foot.Z) > 16 || Mover(Hit) != None)
		return false;
	C = HitLoc + vect(0,0,6);
	if (Blocked(C, C - S.WallNormal * Kinds[k].Radius) || Blocked(C, C + Side * Kinds[k].Radius)
		|| Blocked(C, C - Side * Kinds[k].Radius) || Blocked(C, C + vect(0,0,1) * (Kinds[k].Height + 4)))
		return false;
	for (i = 0; i < Pieces.Length; i++)
	{
		D = Pieces[i].Location - HitLoc;
		D.Z = 0;
		if (VSize(D) < (Pieces[i].Radius + Kinds[k].Radius) * 0.9)
			return false;
	}
	R = Kinds[k].Tilt;
	R.Yaw = Rand(65536);
	G = Spawn(class'GrimeProp', self,, HitLoc + vect(0,0,1) * (Kinds[k].Lift + 0.5), R);
	if (G == None)
		return false;
	G.Setup(Kinds[k].Mesh, Kinds[k].Scale * (0.9 + 0.2 * FRand()), Kinds[k].Scale3D, Kinds[k].Radius, Kinds[k].Lift, Kinds[k].Source);
	G.Away = S.WallNormal;
	if (!bShown)
		G.bHidden = true;
	Pieces[Pieces.Length] = G;
	return true;
}

function PlaceAll()
{
	local int i, n, Tries;

	if (Kinds.Length == 0)
	{
		Log("Grime: clutter: no small props to copy on this map (add ExtraMeshes)");
		return;
	}
	for (i = 0; i < Manager.Spots.Length && Pieces.Length < MaxPieces; i++)
	{
		if (Manager.Spots[i] == None || Manager.Spots[i].Score < MinScore || FRand() > Chance)
			continue;
		n = 1 + Rand(MaxPerSpot);
		for (Tries = 0; Tries < n * 3 && n > 0 && Pieces.Length < MaxPieces; Tries++)
			if (TryPiece(Manager.Spots[i], Rand(Kinds.Length)))
				n--;
	}
	Log("Grime: clutter: "$Pieces.Length$" pieces from "$Kinds.Length$" kinds (props measured "$Measured
		$", unmeasurable "$Unmeasured$", too big or small "$TooBig$", not on a floor "$Floating$")");
}

// characters walking into a piece kick it
function KickCheck()
{
	local Pawn P;
	local vector Feet, D;
	local int i;

	foreach DynamicActors(class'Pawn', P)
	{
		if (P.Health <= 0 || P.Physics != PHYS_Walking || VSize(P.Velocity) < 100)
			continue;
		Feet = P.Location;
		Feet.Z -= P.CollisionHeight;
		for (i = 0; i < Pieces.Length; i++)
		{
			if (Pieces[i] == None || Pieces[i].Physics != PHYS_None)
				continue;
			D = Pieces[i].Location - Feet;
			if (Abs(D.Z - Pieces[i].Lift) > 30)
				continue;
			D.Z = 0;
			if (VSize(D) < Pieces[i].Radius + P.CollisionRadius * 0.5)
				Pieces[i].Kick(P.Velocity);
		}
	}
}

function ShowAll(bool bNewShown)
{
	local int i;

	bShown = bNewShown;
	for (i = 0; i < Pieces.Length; i++)
		if (Pieces[i] != None)
			Pieces[i].bHidden = !bShown;
}

function ViewAt(int i)
{
	local PlayerController PC;
	local vector Stand, Eye;
	local rotator R;

	if (i < 0 || i >= Pieces.Length || Pieces[i] == None)
	{
		Log("Grime: no clutter piece "$i$" (there are "$Pieces.Length$")");
		return;
	}
	foreach DynamicActors(class'PlayerController', PC)
		break;
	if (PC == None || PC.Pawn == None)
		return;
	Stand = Pieces[i].Location + Pieces[i].Away * 160 + vect(0,0,1) * (PC.Pawn.CollisionHeight + 8);
	if (!PC.Pawn.SetLocation(Stand))
		Log("Grime: view piece "$i$": blocked where the player would stand");
	Eye = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	R = rotator(Pieces[i].Location - Eye);
	PC.SetRotation(R);
	PC.Pawn.SetRotation(R);
	PC.ClientSetRotation(R);
	Log("Grime: viewing piece "$i$" "$Pieces[i].StaticMesh$" at ("$int(Pieces[i].Location.X)$","$int(Pieces[i].Location.Y)$","$int(Pieces[i].Location.Z)$")");
}

event Tick(float DeltaTime)
{
	local int i;

	if (bShow != bShown)
		ShowAll(bShow);
	if (ViewProp != LastViewProp)
	{
		LastViewProp = ViewProp;
		if (ViewProp >= 0)
			ViewAt(ViewProp);
	}
	if (Phase == 1)
	{
		for (i = 0; i < MeasurePerTick && Index < Pending.Length; i++)
		{
			if (bBorrowLevelProps && Pending[Index] != None)
				MeasureLevelProp(Pending[Index]);
			Index++;
		}
		if (Index >= Pending.Length)
		{
			for (i = 0; i < ExtraMeshes.Length; i++)
				MeasureExtra(ExtraMeshes[i]);
			Pending.Length = 0;
			Phase = 2;
		}
		return;
	}
	if (Phase == 2)
	{
		PlaceAll();
		Phase = 3;
		return;
	}
	if (Phase == 3 && bKick)
	{
		KickClock += DeltaTime;
		if (KickClock >= 0.1)
		{
			KickClock = 0;
			KickCheck();
		}
	}
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Pieces.Length; i++)
		if (Pieces[i] != None)
			Pieces[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	bBorrowLevelProps=True
	MaxPropRadius=40.000000
	MaxPropHeight=56.000000
	MinPropSize=4.000000
	MaxKinds=12
	MinScore=0.550000
	Chance=0.500000
	MaxPerSpot=3
	MaxPieces=80
	MeasurePerTick=20
	bKick=True
	bShow=True
	bShown=True
	ViewProp=-1
	LastViewProp=-1
	RemoteRole=ROLE_None
}
