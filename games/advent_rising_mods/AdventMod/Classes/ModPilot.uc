//=============================================================================
// ModPilot - plays a test script from inside the game (like U2Pilot's driver),
// so the game can run in the background while it is tested. Movement and
// buttons go through ModInput as if keys were held; nothing touches the real
// keyboard or mouse. Every step is written to System\AdventNative.log.
//
// Steps: [AdventMod.ModPilot] Steps=... in System\AdventMod.ini, in order.
//   waitcontrol [TIMEOUT]    until the player has a pawn (skips cutscenes on the way)
//   wait SECONDS
//   move FORWARD STRAFE SECONDS   -1..1 each: "move 1 0 2" = hold W for 2 s
//   turn YAW PITCH SECONDS   degrees, spread over SECONDS
//   hold BUTTON SECONDS      a game button, pressed and released like a key:
//                            fire favfire altfire jump duck walk use useright useleft
//                            dodge reload melee grenade flickleft flickright pause
//   press BUTTON             the same, held for 0.1 s
//   console COMMAND          any console command
//   menu CLASS               open a menu (e.g. Interface.MenuPause)
//   skipcutscene             skip the cutscene that is playing, if any
//   shot                     an engine screenshot (System\ShotNNNNN.bmp)
//   where                    log the player's position, rotation and state
//   mark TEXT                a line in the log
//=============================================================================
class ModPilot extends Info
	config(AdventMod);

var config array<string> Steps;

// what ModInput adds each frame (class defaults: ModInput has no reference to us)
var bool bActive;
var float Forward, Strafe, Up;
var float TurnAxis, LookAxis;          // added to aTurn / aLookUp while a turn step runs
var bool bHoldFire, bHoldFavoriteFire, bHoldWalk;

var int StepIndex;
var float StepTime, StepLength;
var string Cmd;
var array<string> Args;
var float TurnYaw, TurnPitch;          // degrees per second while turning
var string ReleaseCommand;             // console command that "lets go" of the held button
var bool bWantPause;
var float ControlTime;                   // the script itself paused the game (pause button, menu step)

function Note(string S)
{
	class'ModSettings'.static.Note("pilot: " $ S);
}

function PlayerController PC()
{
	return Level.GetLocalPlayerController();
}

event PostBeginPlay()
{
	Super.PostBeginPlay();
	StepIndex = -1;
	class'ModPilot'.default.bActive = true;
	Note("loaded " $ Steps.Length $ " steps");
}

event Destroyed()
{
	ReleaseAll();
	class'ModPilot'.default.bActive = false;
	Super.Destroyed();
}

function SplitStep(string S)
{
	local int i;

	Args.Length = 0;
	S = S $ " ";
	while (S != "")
	{
		i = InStr(S, " ");
		if (i > 0)
			Args[Args.Length] = Left(S, i);
		S = Mid(S, i + 1);
	}
}

function string RestOf(int From)
{
	local int i;
	local string S;

	for (i = From; i < Args.Length; i++)
		S = S $ Args[i] $ " ";
	return Left(S, Len(S) - 1);
}

function float ArgF(int i, float Fallback)
{
	if (i < Args.Length)
		return float(Args[i]);
	return Fallback;
}

function ReleaseAll()
{
	class'ModPilot'.default.Forward = 0;
	class'ModPilot'.default.Strafe = 0;
	class'ModPilot'.default.Up = 0;
	class'ModPilot'.default.bHoldFire = false;
	class'ModPilot'.default.bHoldFavoriteFire = false;
	class'ModPilot'.default.bHoldWalk = false;
	class'ModPilot'.default.TurnAxis = 0;
	class'ModPilot'.default.LookAxis = 0;
	TurnYaw = 0;
	TurnPitch = 0;
	if (ReleaseCommand != "" && PC() != None)
		PC().ConsoleCommand(ReleaseCommand);
	ReleaseCommand = "";
	if (PC() != None)
	{
		// a real key-up clears these; our virtual buttons must do it themselves
		PC().bFire = 0;
		PC().bFavoriteFire = 0;
		PC().bRun = 0;
	}
}

// press a game button the way its key binding (System\defuser.ini Aliases) does
function bool PressButton(string B)
{
	local string Press;

	B = Caps(B);
	switch (B)
	{
	case "FIRE":       class'ModPilot'.default.bHoldFire = true; Press = "Fire"; break;
	case "FAVFIRE":    class'ModPilot'.default.bHoldFavoriteFire = true; Press = "FavoriteFire"; break;
	case "ALTFIRE":    Press = "AltFire"; ReleaseCommand = "AltFireRelease"; break;
	case "JUMP":       Press = "Jump"; ReleaseCommand = "EndJump"; class'ModPilot'.default.Up = 1; break;
	case "DUCK":       Press = "Duck"; ReleaseCommand = "UnDuck"; class'ModPilot'.default.Up = -1; break;
	case "WALK":       class'ModPilot'.default.bHoldWalk = true; break;
	case "USE":        Press = "Use"; ReleaseCommand = "UseRelease"; break;
	case "USERIGHT":   Press = "Input_DoUseRight"; ReleaseCommand = "Input_DoUseRightRelease"; break;
	case "USELEFT":    Press = "Input_DoUseLeft"; ReleaseCommand = "Input_DoUseLeftRelease"; break;
	case "DODGE":      Press = "Input_DoDodge"; ReleaseCommand = "Input_DoDodgeRelease"; break;
	case "RELOAD":     Press = "Reload"; ReleaseCommand = "ReloadRelease"; break;
	case "MELEE":      Press = "Melee"; ReleaseCommand = "MeleeRelease"; break;
	case "GRENADE":    Press = "Grenade"; ReleaseCommand = "GrenadeRelease"; break;
	case "FLICKLEFT":  Press = "Input_FlickLeft"; break;
	case "FLICKRIGHT": Press = "Input_FlickRight"; break;
	case "PAUSE":      ReleaseCommand = "GuiPause"; bWantPause = true; break;
	default:
		Note("unknown button " $ B);
		return false;
	}
	if (Press != "")
		PC().ConsoleCommand(Press);
	return true;
}

function Aim(float YawDeg, float PitchDeg)
{
	local rotator R;

	if (PC() == None)
		return;
	R.Yaw = int(YawDeg * 65536.0 / 360.0);
	R.Pitch = int(PitchDeg * 65536.0 / 360.0) & 65535;
	PC().SetRotation(R);
	Note("aim: view set to " $ R);
}

function Where()
{
	local PlayerController P;

	P = PC();
	if (P == None)
	{
		Note("where: no player");
		return;
	}
	if (P.Pawn == None)
		Note("where: controller " $ P.Name $ " state " $ P.GetStateName() $ ", no pawn");
	else
		Note("where: " $ P.Pawn.Location $ " rotation " $ P.Rotation $ " velocity " $ int(VSize(P.Pawn.Velocity)) $ " physics " $ P.Pawn.Physics $ " state " $ P.GetStateName());
}

function bool SkipCutscene()
{
	if (CinematicEvent(Level.CinematicToSkip) == None)
		return false;
	Note("skipping cutscene " $ Level.CinematicToSkip);
	CinematicEvent(Level.CinematicToSkip).SkipCinematic();
	return true;
}

function StartStep()
{
	local string S;

	ReleaseAll();
	StepIndex++;
	StepTime = 0;
	StepLength = 0;
	if (StepIndex >= Steps.Length)
	{
		Note("done");
		Destroy();
		return;
	}
	S = Steps[StepIndex];
	SplitStep(S);
	if (Args.Length == 0)
		return;
	Cmd = Caps(Args[0]);
	Note("step " $ (StepIndex + 1) $ ": " $ S);
	switch (Cmd)
	{
	case "WAIT":
		StepLength = ArgF(1, 1);
		break;
	case "WAITCONTROL":
		StepLength = ArgF(1, 120);
		break;
	case "MOVE":
		class'ModPilot'.default.Forward = FClamp(ArgF(1, 0), -1, 1);
		class'ModPilot'.default.Strafe = FClamp(ArgF(2, 0), -1, 1);
		StepLength = ArgF(3, 1);
		break;
	case "TURN":
		StepLength = FMax(ArgF(3, 0.5), 0.05);
		TurnYaw = ArgF(1, 0) / StepLength;
		TurnPitch = ArgF(2, 0) / StepLength;
		// UE2 turns the view by 32 * DeltaTime * aTurn rotation units (65536 = 360 degrees)
		class'ModPilot'.default.TurnAxis = TurnYaw * 65536.0 / 360.0 / 32.0;
		class'ModPilot'.default.LookAxis = TurnPitch * 65536.0 / 360.0 / 32.0;
		break;
	case "HOLD":
		if (Args.Length > 1)
			PressButton(Args[1]);
		StepLength = ArgF(2, 0.5);
		break;
	case "PRESS":
		if (Args.Length > 1)
			PressButton(Args[1]);
		StepLength = 0.1;
		break;
	case "CONSOLE":
		Note("console: " $ PC().ConsoleCommand(RestOf(1)));
		break;
	case "MENU":
		bWantPause = true;
		Note("menu " $ Args[1] $ ": " $ PC().Player.GUIController.OpenMenu(Args[1]));
		break;
	case "SKIPCUTSCENE":
		SkipCutscene();
		break;
	case "SHOT":
		PC().ConsoleCommand("shot");
		Note("shot");
		break;
	case "WHERE":
		Where();
		break;
	case "AIM":
		// the view straight to a yaw and pitch in degrees (pitch < 0 looks down): the
		// third-person camera eases and clamps TURN's look input, this doesn't
		Aim(ArgF(1, 0), ArgF(2, 0));
		break;
	case "MARK":
		break;
	default:
		Note("unknown step " $ Cmd);
	}
}

event Tick(float DeltaTime)
{
	local PlayerController P;

	P = PC();
	if (P == None)
		return;
	if (StepIndex < 0)
	{
		StartStep();
		return;
	}
	// the game pauses itself when its window loses focus (DoGuiPause), and a test runs in the background
	if (Level.Pauser != None && !bWantPause)
	{
		Note("the game paused itself (window not in focus): unpausing");
		if (P.myHUD != None)
			P.myHUD.bHideHUD = false;
		P.Player.GUIController.CloseAll(false);
		P.SetPause(false);
	}
	StepTime += DeltaTime;
	// a test has no use for cutscenes: skip any that starts (a level's intro starts a moment after the player has a pawn)
	SkipCutscene();
	if (Cmd == "WAITCONTROL")
	{
		// control means a pawn, no cutscene and no pause, for 3 seconds in a row
		if (P.Pawn != None && Level.CinematicToSkip == None && Level.Pauser == None)
			ControlTime += DeltaTime;
		else
			ControlTime = 0;
		if (ControlTime > 3)
		{
			Where();
			StartStep();
		}
		else if (StepTime > StepLength)
		{
			Note("waitcontrol timed out");
			StartStep();
		}
		return;
	}
	if (StepTime >= StepLength)
		StartStep();
}

defaultproperties
{
     bAlwaysTick=True
     RemoteRole=ROLE_None
}
