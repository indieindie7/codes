//=============================================================================
// ModGizmos - debug lines on the player (Gideon), drawn on the HUD canvas every frame.
// (Actor.DrawDebugLine compiles but draws nothing in the shipping renderer: tested 10-10.)
// Points are projected with the Interaction's WorldToScreen from the game's camera
// (EonPlayerController.Camera), and each line is a row of small squares.
// ModMutator adds it to the player's interactions when ModSettings.bGizmos;
// "mutate gizmos" turns it on and off while playing.
//   white   collision cylinder
//   green   velocity (a quarter second ahead)
//   blue    facing (the pawn's yaw)
//   yellow  a cross on each foot bone (leftFoot / rightFoot, the bones ModFeet moves)
//   red     the trace from each foot down to its floor, cyan where it hits (what foot IK aims at)
//   magenta the spine bone's up axis (the lean ModMoves puts on it)
//=============================================================================
class ModGizmos extends Interaction;

var bool bAdded;           // (default) one per player, for the whole run
var bool bOn;              // (default) "mutate gizmos" flips it
var Canvas Can;
var vector CamLoc, CamDir;
var rotator CamRot;

event Initialized()
{
	default.bAdded = true;
	default.bOn = true;
	class'ModSettings'.static.Note("gizmos: on (mutate gizmos toggles)");
}

static function Toggle()
{
	default.bOn = !default.bOn;
	class'ModSettings'.static.Note("gizmos: " $ default.bOn);
}

// a 3D line as dots on the screen; skipped when an end is behind the camera
function Line(vector A, vector B, byte R, byte G, byte Bl)
{
	local vector SA, SB, D;
	local float Len, T;

	if (((A - CamLoc) dot CamDir) < 10 || ((B - CamLoc) dot CamDir) < 10)
		return;
	SA = WorldToScreen(A, CamLoc, CamRot);
	SB = WorldToScreen(B, CamLoc, CamRot);
	D = SB - SA;
	D.Z = 0;
	Len = VSize(D);
	if (Len > 4000)
		return;
	Can.SetDrawColor(R, G, Bl);
	for (T = 0; T <= Len; T += 3)
	{
		Can.SetPos(SA.X + D.X * T / FMax(Len, 1) - 1, SA.Y + D.Y * T / FMax(Len, 1) - 1);
		Can.DrawTile(Texture'Engine.WhiteSquareTexture', 2, 2, 0, 0, 2, 2);
	}
}

function Cross(vector C, float S, byte R, byte G, byte B)
{
	Line(C - vect(1,0,0) * S, C + vect(1,0,0) * S, R, G, B);
	Line(C - vect(0,1,0) * S, C + vect(0,1,0) * S, R, G, B);
	Line(C - vect(0,0,1) * S, C + vect(0,0,1) * S, R, G, B);
}

function Cylinder(Pawn P)
{
	local int i;
	local vector A, B, Up;
	local float R;

	R = P.CollisionRadius;
	Up = vect(0,0,1) * P.CollisionHeight;
	for (i = 0; i < 12; i++)
	{
		A = P.Location + R * vector(rot(0,1,0) * (i * 5461));
		B = P.Location + R * vector(rot(0,1,0) * ((i + 1) * 5461));
		Line(A + Up, B + Up, 255, 255, 255);
		Line(A - Up, B - Up, 255, 255, 255);
		if (i % 3 == 0)
			Line(A + Up, A - Up, 255, 255, 255);
	}
}

function Foot(Pawn P, name Bone)
{
	local vector F, HitLoc, HitNorm;

	F = P.GetBoneCoords(Bone).Origin;
	if (F == vect(0,0,0))
		return;
	Cross(F, 4, 255, 255, 0);
	if (P.Trace(HitLoc, HitNorm, F - vect(0,0,150), F + vect(0,0,60), false) != None)
	{
		Line(F, HitLoc, 255, 0, 0);
		Cross(HitLoc, 3, 0, 255, 255);
		Line(HitLoc, HitLoc + HitNorm * 12, 0, 255, 255);
	}
}

function PostRender(Canvas C)
{
	local PlayerController PC;
	local EonPlayerController E;
	local Pawn P;
	local coords S;

	if (!default.bOn || !class'ModSettings'.default.bGizmos || C == None || ViewportOwner == None)
		return;
	PC = ViewportOwner.Actor;
	if (PC == None || PC.Level == None || PC.Level.Game == None || PC.Level.Game.IsInFrontEnd
		|| PC.Pawn == None || PC.Pawn.bDeleteMe)
		return;
	P = PC.Pawn;
	E = EonPlayerController(PC);
	if (E != None && E.Camera != None)
	{
		CamLoc = E.Camera.Location;
		CamRot = E.Camera.Rotation;
	}
	else
	{
		CamLoc = P.Location + vect(0,0,1) * P.EyeHeight;
		CamRot = PC.Rotation;
	}
	CamDir = vector(CamRot);
	Can = C;
	C.Style = 1;    // STY_Normal
	Cylinder(P);
	Line(P.Location, P.Location + P.Velocity * 0.25, 0, 255, 0);
	Line(P.Location, P.Location + vector(rot(0,1,0) * P.Rotation.Yaw) * 60, 0, 0, 255);
	Foot(P, 'leftFoot');
	Foot(P, 'rightFoot');
	S = P.GetBoneCoords('spine');
	if (S.Origin != vect(0,0,0))
		Line(S.Origin, S.Origin + S.ZAxis * 30, 255, 0, 255);
	Can = None;
}

defaultproperties
{
     bOn=True
     bVisible=True
     bActive=False
}
