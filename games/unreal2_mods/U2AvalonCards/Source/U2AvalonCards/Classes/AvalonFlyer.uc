//=============================================================================
// AvalonFlyer - something moving through the command room's view: a static
// mesh (the game's own dropship) flying a slow circle over the town, nose
// along its path, banked into the turn. Motion pulls the eye and makes a still
// view read as a living place (games/reports/Cinematography and concept art
// for the Avalon town.md). Spawned and configured by AvalonCards (Flyer* keys).
//=============================================================================
class AvalonFlyer extends Actor;

var vector Centre;        // the circle's centre; Z = flight height
var float Radius;         // world units
var float Speed;          // world units per second along the circle
var float Angle;          // where on the circle (radians)
var int Bank;             // roll into the turn (rotator units)
var bool bPass;           // a one-shot straight pass (the staged reveal) instead of the circle
var vector PassFrom, PassTo;
var float PassT, PassTime;

function Setup(StaticMesh M, vector C, float R, float S, float Scale, float Start)
{
	StaticMesh = M;
	SetDrawScale(Scale);
	Centre = C;
	Radius = FMax(R, 500);
	Speed = S;
	Angle = Start;
	Tick(0);
}

// a straight pass from A to B at speed S, then gone; Snd plays once as it starts
function Pass(StaticMesh M, vector A, vector B, float S, float Scale, Sound Snd)
{
	StaticMesh = M;
	SetDrawScale(Scale);
	bPass = True;
	PassFrom = A;
	PassTo = B;
	PassTime = VSize(B - A) / FMax(S, 100);
	PassT = 0;
	SetLocation(A);
	SetRotation(rotator(B - A));
	if (Snd != None)
		PlaySound(Snd, SLOT_None, 2.0, false, 40000, 1.0, true);
}

event Tick(float DeltaTime)
{
	local vector P, Dir;
	local rotator Rot;

	if (StaticMesh == None)
		return;
	if (bPass)
	{
		PassT += DeltaTime;
		if (PassT >= PassTime)
		{
			Destroy();
			return;
		}
		P = PassFrom + (PassTo - PassFrom) * (PassT / PassTime);
		SetLocation(P);
		return;
	}
	Angle += DeltaTime * Speed / Radius;
	P = Centre;
	P.X += Radius * Cos(Angle);
	P.Y += Radius * Sin(Angle);
	SetLocation(P);
	Dir.X = -Sin(Angle);
	Dir.Y = Cos(Angle);
	if (Speed < 0)
		Dir = -Dir;
	Rot = rotator(Dir);
	Rot.Roll = Bank;
	SetRotation(Rot);
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bAlwaysRelevant=True
	bCollideActors=False
	bBlockActors=False
	bBlockPlayers=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
	Bank=-1600
	bUnlit=False
}
