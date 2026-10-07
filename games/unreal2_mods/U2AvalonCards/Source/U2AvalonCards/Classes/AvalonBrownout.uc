//=============================================================================
// AvalonBrownout - the Thursday power cut (binder: Oduya's complaint, the PA's
// "Authority facilities, third priority"). Every so often, while the player is
// inside the Authority's tower, the building powers down: the view dims with a
// flicker or two, stays dim a few seconds, and powers back up. The baked lights
// can't be switched, so it is done on the view (PlayerController's glow).
// Spawned and configured by AvalonCards (Brownout* keys).
//=============================================================================
class AvalonBrownout extends Actor;

var vector Centre;          // the tower; the cut only happens within Reach of it, above MinZ
var float Reach, MinZ, MinGap, MaxGap, Depth;
var Sound Down, Up;
var float T;                 // time into the current cut; < 0 = waiting
var float Applied;
var PlayerController PC;

function Begin(vector C, float R, float Z, float Lo, float Hi, float D, Sound SDown, Sound SUp)
{
	Centre = C;
	Reach = R;
	MinZ = Z;
	MinGap = Lo;
	MaxGap = Hi;
	Depth = D;
	Down = SDown;
	Up = SUp;
	T = -1;
	SetTimer(Lo * 0.5 + FRand() * Lo * 0.5, false);
}

function bool Inside()
{
	PC = Level.PlayerControllerList;
	return PC != None && PC.Pawn != None && PC.Pawn.Location.Z > MinZ
		&& VSize((PC.Pawn.Location - Centre) * vect(1,1,0)) < Reach;
}

event Timer()
{
	if (!Inside())
	{
		SetTimer(20, false);        // try again soon: it only happens to the people in the tower
		return;
	}
	T = 0;
	if (Down != None)
		PC.Pawn.PlaySound(Down, SLOT_None, 1.5, false, 4000);
	Log("Cards: brownout");
}

function Dim(float D)
{
	if (PC == None)
		return;
	if (Abs(D - Applied) > 0.005)
	{
		PC.ClientAdjustGlow(-(D - Applied), vect(0,0,0));
		Applied = D;
	}
}

event Tick(float DeltaTime)
{
	if (T < 0)
		return;
	T += DeltaTime;
	// down, a flicker back, down again, hold, and up
	if (T < 0.25)
		Dim(Depth * T / 0.25);
	else if (T < 0.45)
		Dim(Depth * 0.3);
	else if (T < 0.6)
		Dim(Depth);
	else if (T < 0.75)
		Dim(Depth * 0.5);
	else if (T < 5.0)
		Dim(Depth);
	else if (T < 6.5)
	{
		if (T - DeltaTime < 5.0 && Up != None && PC != None && PC.Pawn != None)
			PC.Pawn.PlaySound(Up, SLOT_None, 1.5, false, 4000);
		Dim(Depth * (6.5 - T) / 1.5);
	}
	else
	{
		Dim(0);
		T = -1;
		SetTimer(MinGap + FRand() * (MaxGap - MinGap), false);
	}
}

event Destroyed()
{
	Dim(0);
}

defaultproperties
{
	DrawType=DT_None
	bHidden=True
	bStatic=False
	bCollideActors=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
