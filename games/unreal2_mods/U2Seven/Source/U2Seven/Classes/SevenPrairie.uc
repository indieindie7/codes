//=============================================================================
// SevenPrairie - the director for the generated Prairie map: the crash site
// (the ship in pieces, spawned at start since the map import drops big
// meshes), Aida's console at the wreck (the mission board), and later the
// opening cinematic and the trail's encounters.
//
// Spawned by SevenStory on Prairie*. Settings: [U2Seven.SevenPrairie].
//=============================================================================
class SevenPrairie extends Info
	config(User);

var() config bool bEnabled;
var() config vector CrashSite;
var() config bool bLog;

struct WreckPiece
{
	var string Mesh;
	var vector Offset;
	var rotator Rot;
	var float Scale;
};
var array<WreckPiece> Pieces;
var array<SevenProp> Props;
var SevenBoard Board;
var bool bSetUp;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SaveConfig();
	if (!bEnabled)
	{
		Destroy();
		return;
	}
	SetTimer(0.5, true);
}

event Timer()
{
	if (!bSetUp && Level.TimeSeconds > 1.0)
	{
		bSetUp = true;
		SetUp();
	}
}

function float Ground(vector At)
{
	local vector HitLoc, HitNorm;
	if (Trace(HitLoc, HitNorm, At + vect(0,0,-6000), At + vect(0,0,3800), false) != None)
		return HitLoc.Z;
	return At.Z;
}

function SevenProp Place(string Mesh, vector Loc, rotator Rot, float Scale, bool bCollide)
{
	local SevenProp P;
	local StaticMesh M;

	M = StaticMesh(DynamicLoadObject(Mesh, class'StaticMesh'));
	if (M == None)
	{
		Log("SevenPrairie: no mesh "$Mesh);
		return None;
	}
	P = Spawn(class'SevenProp',,, Loc, Rot);
	if (P == None)
	{
		Log("SevenPrairie: blocked placing "$Mesh$" at "$Loc);
		return None;
	}
	P.StaticMesh = M;
	P.SetDrawScale(Scale);
	if (!bCollide)
		P.SetCollision(false, false, false);
	Props[Props.Length] = P;
	return P;
}

function SetUp()
{
	local int i;
	local vector L;
	local float G;
	local SevenProp P;

	// the ship, nose-down at the end of its scar, the hull pieces behind it
	AddPiece("Terran_DecoM.Crates.Terran_Dropship_01", vect(0,0,0), rot(-1500,33000,1200), 0.45);
	AddPiece("Mission_05M.debris_sheet_003.Crashed_Transport", vect(1500,-600,0), rot(0,41000,0), 1.0);
	AddPiece("Mission_05M.Misc.debris_sheet_001", vect(900,700,0), rot(0,9000,3000), 1.2);
	AddPiece("Mission_05M.Misc.debris_sheet_002", vect(2100,300,0), rot(0,52000,0), 1.2);
	AddPiece("Mission_05M.Misc.debris_misc_01", vect(600,-1000,0), rot(0,20000,0), 1.3);
	AddPiece("Mission_05M.Misc.debris_misc_02", vect(-700,500,0), rot(0,60000,0), 1.3);
	for (i = 0; i < Pieces.Length; i++)
	{
		L = CrashSite + Pieces[i].Offset;
		G = Ground(L + vect(0,0,500));
		L.Z = G + 20;
		P = Place(Pieces[i].Mesh, L, Pieces[i].Rot, Pieces[i].Scale, i == 0);
	}
	// Aida's console: a terminal beside the ship's hatch, usable
	L = CrashSite + vect(-500, 900, 500);
	L.Z = Ground(L) + 2;
	P = Place("Terran_DecoM.Consoles.Terran_Console_01", L, rot(0,49152,0), 1.0, true);
	if (P != None)
	{
		Board = Spawn(class'SevenBoard',,, L + vect(0,0,40));
		if (Board != None)
		{
			Board.bHidden = true;             // the prop is the visible console
			Board.SetCollision(false, false, false);
			P.Board = Board;
			P.SetCollisionSize(60, 60);
		}
	}
	if (bLog)
		Log("SevenPrairie: placed "$Props.Length$" props at the crash, board "$(Board != None));
}

function AddPiece(string Mesh, vector Off, rotator R, float S)
{
	local int i;
	i = Pieces.Length;
	Pieces.Length = i + 1;
	Pieces[i].Mesh = Mesh;
	Pieces[i].Offset = Off;
	Pieces[i].Rot = R;
	Pieces[i].Scale = S;
}

defaultproperties
{
	bEnabled=True
	CrashSite=(X=-25000,Y=0,Z=-2700)
	bLog=True
	RemoteRole=ROLE_None
}
