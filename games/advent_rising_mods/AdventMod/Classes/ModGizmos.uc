//=============================================================================
// ModGizmos - debug lines on the player (Gideon), redrawn every frame with the engine's
// DrawDebugLine (the stock bountyHunterB uses it the same way). ModMutator spawns it when
// ModSettings.bGizmos; "mutate gizmos" turns it on and off while playing.
//   white   collision cylinder
//   green   velocity (a quarter second ahead)
//   blue    facing (the pawn's yaw)
//   yellow  a cross on each foot bone (leftFoot / rightFoot, the bones ModFeet moves)
//   red     the trace from each foot down to its floor, cyan where it hits (what foot IK aims at)
//   magenta the spine bone's up axis (the lean ModMoves puts on it)
//=============================================================================
class ModGizmos extends Info;

var bool bOn;

function PostBeginPlay()
{
	bOn = true;
	class'ModSettings'.static.Note("gizmos: on (mutate gizmos toggles)");
}

function Toggle()
{
	bOn = !bOn;
	class'ModSettings'.static.Note("gizmos: " $ bOn);
}

function Cross(vector C, float S, byte R, byte G, byte B)
{
	DrawDebugLine(C - vect(1,0,0) * S, C + vect(1,0,0) * S, R, G, B);
	DrawDebugLine(C - vect(0,1,0) * S, C + vect(0,1,0) * S, R, G, B);
	DrawDebugLine(C - vect(0,0,1) * S, C + vect(0,0,1) * S, R, G, B);
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
		DrawDebugLine(A + Up, B + Up, 255, 255, 255);
		DrawDebugLine(A - Up, B - Up, 255, 255, 255);
		if (i % 3 == 0)
			DrawDebugLine(A + Up, A - Up, 255, 255, 255);
	}
}

function Foot(Pawn P, name Bone)
{
	local vector F, HitLoc, HitNorm;

	F = P.GetBoneCoords(Bone).Origin;
	if (F == vect(0,0,0))
		return;
	Cross(F, 4, 255, 255, 0);
	if (Trace(HitLoc, HitNorm, F - vect(0,0,150), F + vect(0,0,60), false) != None)
	{
		DrawDebugLine(F, HitLoc, 255, 0, 0);
		Cross(HitLoc, 3, 0, 255, 255);
		DrawDebugLine(HitLoc, HitLoc + HitNorm * 12, 0, 255, 255);
	}
}

function Tick(float DeltaTime)
{
	local PlayerController PC;
	local Pawn P;
	local coords S;

	if (!bOn)
		return;
	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None || PC.Pawn.bDeleteMe)
		return;
	P = PC.Pawn;
	Cylinder(P);
	DrawDebugLine(P.Location, P.Location + P.Velocity * 0.25, 0, 255, 0);
	DrawDebugLine(P.Location, P.Location + vector(rot(0,1,0) * P.Rotation.Yaw) * 60, 0, 0, 255);
	Foot(P, 'leftFoot');
	Foot(P, 'rightFoot');
	S = P.GetBoneCoords('spine');
	if (S.Origin != vect(0,0,0))
		DrawDebugLine(S.Origin, S.Origin + S.ZAxis * 30, 255, 0, 255);
}

defaultproperties
{
     bAlwaysTick=True
}
