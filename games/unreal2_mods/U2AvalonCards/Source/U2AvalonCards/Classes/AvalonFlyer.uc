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

event Tick(float DeltaTime)
{
	local vector P, Dir;
	local rotator Rot;

	if (StaticMesh == None)
		return;
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
