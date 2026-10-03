//=============================================================================
// ModInput - the player's input, always in place (ModSettings.Startup selects it
// through PlayerController.InputClass):
//  1. stuck gamepad axes are ignored. The game turns the camera with
//     "JoyR=AxisRaw aTurn" / "JoyU=AxisRaw aLookup" (MyDefUser.ini). An axis the
//     pad doesn't have, a wireless receiver without a pad, or a pad that switched
//     itself off reads as the axis' minimum, -1: a full deflection the 0.25 dead
//     zone never catches, so the camera spins left/up on its own (the game's
//     best-known PC bug; the controls menu rewrites the bindings, so editing them
//     doesn't last). A real stick passes through the centre first and never holds
//     one exact value for long, so an axis only counts after it has been near the
//     centre, and one frozen off-centre for StuckTime seconds stops counting until
//     it comes back.
//  2. ModPilot's "held keys", so a test script can play the game from inside it,
//     without Windows input or focus. The engine fills the input axes every
//     frame and then calls PlayerInput(); adding our values here is exactly what
//     a held key does.
// At the start of PlayerInput aTurn and aLookUp hold only the joystick's axes:
// the mouse is added inside Super.PlayerInput.
//=============================================================================
class ModInput extends PlayerInput within PlayerController;

var bool bAnnounced;
var bool bTurnLive, bLookLive;          // seen near the centre since the last stuck spell
var float LastTurn, LastLook;
var float TurnStill, LookStill;         // seconds the axis has held one exact value

// one gamepad axis: its value if it is live, else 0
function float Filter(float V, out float Last, out float Still, out byte bLive, string AxisName, float DeltaTime)
{
	local bool bWasLive;

	bWasLive = bLive != 0;
	if (Abs(V) < class'ModSettings'.default.PadCentre)
	{
		bLive = 1;
		Still = 0;
	}
	else if (V == Last)
	{
		Still += DeltaTime;
		if (Still >= class'ModSettings'.default.StuckTime)
			bLive = 0;
	}
	else
		Still = 0;
	Last = V;
	if (bWasLive && bLive == 0 && V != 0)
		class'ModSettings'.static.Note("input: " $ AxisName $ " stuck at " $ V $ " (no gamepad, or it switched off): ignored until it returns to the centre");
	if (bLive == 0)
		return 0;
	return V;
}

event PlayerInput(float DeltaTime)
{
	local byte B;

	if (!bAnnounced)
	{
		bAnnounced = true;
		class'ModSettings'.static.Note("input: ModInput is the input of " $ Outer);
	}
	// testing: a phantom axis (what a missing / switched-off pad axis reads)
	aTurn += class'ModSettings'.default.DebugStuckTurn;
	if (class'ModSettings'.default.bPadDriftFix)
	{
		B = byte(bTurnLive);
		aTurn = Filter(aTurn, LastTurn, TurnStill, B, "camera turn axis", DeltaTime);
		bTurnLive = B != 0;
		B = byte(bLookLive);
		aLookUp = Filter(aLookUp, LastLook, LookStill, B, "camera look axis", DeltaTime);
		bLookLive = B != 0;
	}
	if (class'ModPilot'.default.bActive)
	{
		// the default bindings' axis speeds (MoveForward = Axis aBaseY Speed=+1200, ...)
		aBaseY += 1200.0 * class'ModPilot'.default.Forward;
		aStrafe += 1200.0 * class'ModPilot'.default.Strafe;
		aUp += 1200.0 * class'ModPilot'.default.Up;
		// turning like the mouse does (the camera system owns the view rotation)
		aTurn += class'ModPilot'.default.TurnAxis;
		aLookUp += class'ModPilot'.default.LookAxis;
		if (class'ModPilot'.default.bHoldFire)
			bFire = 1;
		if (class'ModPilot'.default.bHoldFavoriteFire)
			bFavoriteFire = 1;
		if (class'ModPilot'.default.bHoldWalk)
			bRun = 1;
	}
	Super.PlayerInput(DeltaTime);
}

defaultproperties
{
}
