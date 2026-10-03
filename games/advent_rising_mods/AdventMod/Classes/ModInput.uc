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
//  2. raw mouse look (bRawMouse): the engine scales slow mouse movement down
//     (below MouseAccelThreshold x sensitivity it squares the speed, below a tenth
//     of that it keeps 10%) and smooths it over frames, so small aiming moves lag
//     and then jump: the "acceleration" players feel. Both are switched off here
//     for this input only; the saved settings are not touched. On top of that the
//     third-person camera turns at 195 x sensitivity x input^3 degrees a second
//     (measured; capped near 365; the sensitivity is the controller yaw setting,
//     0.2 at the bottom of its slider, where it measured 39), a stick curve: half
//     the hand speed turns 8 times slower. The mouse's share of the turn is fed
//     through a cube root first, so the camera turns MouseTurnRate degrees a
//     second per unit of mouse speed, in a line.
//  3. ModPilot's "held keys", so a test script can play the game from inside it,
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
var float LogTime, LogRaw, LogKept;     // bMouseLog: one second of mouse movement before / after the engine's curve
var int LogFrames;
var bool bInAir;                       // bJumpLog
var float JumpBaseZ, JumpApexZ, JumpLaunchZ;
var int LastDesiredYaw, LastCurrentYaw;
var float LogDesired, LogCurrent;    // camera yaw turned in that second, degrees

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
	local float Raw;

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
	if (class'ModSettings'.default.bRawMouse)
	{
		MouseSmoothingMode = 0;
		MouseAccelThreshold = 0;
	}
	else
	{
		MouseSmoothingMode = default.MouseSmoothingMode;
		MouseAccelThreshold = default.MouseAccelThreshold;
	}
	if (class'ModPilot'.default.bActive)
		aMouseX += class'ModPilot'.default.MouseX;
	Raw = aMouseX;
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
	if (class'ModSettings'.default.bRawMouse && aMouseX != 0)
		aTurn += LinearTurn(aMouseX) - aMouseX;
	if (class'ModSettings'.default.bRawMouse && aMouseY != 0 && (bAlwaysMouseLook || bLook != 0))
		aLookUp += LinearTurn(aMouseY) * (1 - 2 * int(bInvertMouse)) - aMouseY * (1 - 2 * int(bInvertMouse));
	if (class'ModSettings'.default.bMouseLog)
		LogMouse(Raw, DeltaTime);
	if (class'ModSettings'.default.bJumpLog)
		LogJump();
}

// testing: each jump's launch speed, how high it went, and the settings that decide it
function LogJump()
{
	if (Pawn == None)
		return;
	if (!bInAir && Pawn.Physics == PHYS_Falling && Pawn.Velocity.Z > 100)
	{
		bInAir = true;
		JumpBaseZ = Pawn.Location.Z;
		JumpApexZ = JumpBaseZ;
		JumpLaunchZ = Pawn.Velocity.Z;
	}
	else if (bInAir)
	{
		JumpApexZ = FMax(JumpApexZ, Pawn.Location.Z);
		if (Pawn.Physics != PHYS_Falling)
		{
			bInAir = false;
			class'ModSettings'.static.Note("jump: launch " $ int(JumpLaunchZ) $ " up, rose " $ int(JumpApexZ - JumpBaseZ) $ ", JumpZ " $ Pawn.JumpZ $ ", jump power " $ Pawn.GetPowerLevel(POWERAFFECTOR_PLAYER_JUMPING) $ ", gravity " $ Pawn.PhysicsVolume.Gravity.Z $ ", dodge held " $ EonPlayerController(Outer).bHoldingDodge $ ", use held " $ EonPlayerController(Outer).bHoldingUse);
		}
	}
}

// the camera input that turns the third-person camera Rate x M degrees a second:
// it turns at 195 x the controller sensitivity x input^3
function float LinearTurn(float M)
{
	local float Sens, V;

	Sens = 1;
	if (EonPlayerController(Outer) != None && EonPlayerController(Outer).AimControl != None)
		Sens = FMax(EonPlayerController(Outer).AimControl.fControllerYawSensitivity, 0.01);
	V = class'ModSettings'.default.MouseTurnRate * Abs(M) / (195.0 * Sens);
	V = Exp(Loge(V) / 3.0);
	if (M < 0)
		return -V;
	return V;
}

// how much of the sideways mouse movement survives the engine's smoothing and curve,
// once a second while the mouse moves (after/before 1 = linear; the sensitivity is
// MouseSensitivity x a little for the FOV, so a straight line is about 3)
function LogMouse(float Raw, float DeltaTime)
{
	local EonPlayerController E;
	local int D, C;

	LogTime += DeltaTime;
	E = EonPlayerController(Outer);
	if (E != None && E.Camera != None && E.Camera.MoveController != None)
	{
		D = E.Camera.MoveController.DesiredXAxisRotation.Yaw;
		C = E.Camera.MoveController.CurrentXAxisRotation.Yaw;
		LogDesired += YawStep(D - LastDesiredYaw);
		LogCurrent += YawStep(C - LastCurrentYaw);
		LastDesiredYaw = D;
		LastCurrentYaw = C;
	}
	if (Raw != 0)
	{
		LogRaw += Abs(Raw);
		LogKept += Abs(aMouseX);
		LogFrames++;
	}
	if (LogTime < 1)
		return;
	if (LogFrames > 0)
		class'ModSettings'.static.Note("input: mouse " $ LogFrames $ " frames, raw " $ LogRaw / LogFrames $ " per frame, after the curve " $ LogKept / LogFrames $ " (x" $ LogKept / FMax(LogRaw, 0.0001) $ "), camera desired " $ int(LogDesired) $ " current " $ int(LogCurrent) $ " deg/s, controller sensitivity " $ LogSens() $ ", mouse sensitivity " $ MouseSensitivity $ ", raw mouse " $ class'ModSettings'.default.bRawMouse);
	LogTime = 0;
	LogRaw = 0;
	LogKept = 0;
	LogFrames = 0;
	LogDesired = 0;
	LogCurrent = 0;
}

function float LogSens()
{
	if (EonPlayerController(Outer) != None && EonPlayerController(Outer).AimControl != None)
		return EonPlayerController(Outer).AimControl.fControllerYawSensitivity;
	return -1;
}

// a yaw difference (65536 = 360 degrees) as degrees, the short way round
static function float YawStep(int R)
{
	R = R & 65535;
	if (R > 32768)
		R -= 65536;
	return R * 360.0 / 65536.0;
}

defaultproperties
{
}
