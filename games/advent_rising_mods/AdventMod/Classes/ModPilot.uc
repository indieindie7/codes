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
var float MouseX;                       // MOUSE step: added to the raw mouse axis (before the engine's sensitivity and curve)
var bool bHoldFire, bHoldFavoriteFire, bHoldWalk;

var int StepIndex;
var float StepTime, StepLength;
var string Cmd;
var array<string> Args;
var float TurnYaw, TurnPitch;          // degrees per second while turning
var float TargetYaw, TargetPitch;      // FACE/TURN: where the view should end up (degrees)
var bool bAimPitch;                    // FACE/TURN: steer the pitch too
var float OnTargetTime;
var string ReleaseCommand;             // console command that "lets go" of the held button
var bool bWantPause;
var float JumpStartZ, JumpTopZ;       // JUMPTEST
var float TopSpeed;                    // SPEEDTEST
var vector SpeedFrom;
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
	class'ModPilot'.default.MouseX = 0;
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

// the camera effects on the player right now, with their settings
function FxList()
{
	local int i;
	local PlayerController P;

	P = PC();
	if (P == None)
		return;
	Note("fx: " $ P.CameraEffects.Length $ " camera effects");
	for (i = 0; i < P.CameraEffects.Length; i++)
		if (P.CameraEffects[i] != None)
			Note("fx " $ i $ ": " $ P.CameraEffects[i].Class $ " alpha " $ P.CameraEffects[i].Alpha $ " enabled " $ P.CameraEffects[i].Enabled $ " final " $ P.CameraEffects[i].FinalEffect);
}

function Fx()
{
	local class<CameraEffect> C;
	local CameraEffect E;
	local int i, Eq;

	if (Args.Length < 2 || PC() == None)
		return;
	C = class<CameraEffect>(DynamicLoadObject(Args[1], class'Class', true));
	if (C == None)
	{
		Note("fx: no camera effect class " $ Args[1]);
		return;
	}
	E = new(PC()) C;
	for (i = 2; i < Args.Length; i++)
	{
		Eq = InStr(Args[i], "=");
		if (Eq > 0 && !E.SetPropertyText(Left(Args[i], Eq), Mid(Args[i], Eq + 1)))
			Note("fx: " $ C $ " has no property " $ Left(Args[i], Eq));
	}
	PC().AddCameraEffect(E);
	Note("fx: added " $ E $ " (" $ PC().CameraEffects.Length $ " effects now)");
}

function Tilt(float W)
{
	local EonPlayerController E;

	E = EonPlayerController(PC());
	if (E == None || E.Camera == None)
		return;
	E.Camera.fCustomCameraPitchWeight = W;
	E.Camera.fPitchWeight = W;
	if (E.Camera.MoveController != None)
		E.Camera.MoveController.fDesiredPitchWeight = W;
	Note("tilt: camera pitch weight " $ W);
}

function Aim(float YawDeg, float PitchDeg)
{
	local rotator R;
	local EonPlayerController E;

	if (PC() == None)
		return;
	R.Yaw = int(YawDeg * 65536.0 / 360.0);
	R.Pitch = int(PitchDeg * 65536.0 / 360.0) & 65535;
	PC().SetRotation(R);
	// the third-person camera keeps its own direction and drives the view from it
	E = EonPlayerController(PC());
	if (E != None && E.Camera != None && E.Camera.MoveController != None)
	{
		E.Camera.MoveController.DesiredXAxisRotation = R;
		E.Camera.MoveController.CurrentXAxisRotation = R;
	}
	Note("aim: view set to " $ R);
}

function Give(string ClassName)
{
	local class<Inventory> C;
	local Inventory I;

	C = class<Inventory>(DynamicLoadObject(ClassName, class'Class'));
	if (C == None || PC() == None || PC().Pawn == None)
	{
		Note("give: no class " $ ClassName);
		return;
	}
	I = Spawn(C,,, PC().Pawn.Location);
	if (I == None)
	{
		Note("give: didn't spawn");
		return;
	}
	I.GiveTo(PC().Pawn, true);
	Note("give: " $ I $ " right weapon now " $ PC().Pawn.RightWeapon);
}

function Hurt(int Damage, string TypeName)
{
	local Pawn P, Best;
	local PlayerController C;
	local class<DamageType> T;
	local vector Spot, Dir;

	C = PC();
	if (C == None || C.Pawn == None)
		return;
	T = class<DamageType>(DynamicLoadObject(TypeName, class'Class'));
	ForEach DynamicActors(class'Pawn', P)
		if (P != C.Pawn && P.Health > 0 && !P.IsA('Vehicle') && (Best == None || VSize(P.Location - C.Pawn.Location) < VSize(Best.Location - C.Pawn.Location)))
			Best = P;
	if (Best == None || T == None)
	{
		Note("hurt: no character near, or no damage type " $ TypeName);
		return;
	}
	Dir = Normal(Best.Location - C.Pawn.Location);
	Spot = Best.Location + vect(0,0,1) * Best.CollisionHeight * 0.4 - Dir * Best.CollisionRadius * 0.5;
	Note("hurt: " $ Best $ " (health " $ Best.Health $ ") " $ Damage $ " " $ T $ ", " $ int(VSize(Best.Location - C.Pawn.Location)) $ " away");
	Best.TakeDamage(Damage, C.Pawn, Spot, Dir * 20000, T);
	Aim(ViewDeg(rotator(Best.Location - C.Pawn.Location).Yaw), -12);
}

function NearEnemy(float Dist)
{
	local Pawn P, Best;
	local vector Spot, Dir;
	local PlayerController C;

	C = PC();
	if (C == None || C.Pawn == None)
		return;
	ForEach DynamicActors(class'Pawn', P)
		if (class'ModTargeting'.static.IsHostile(P) && (Best == None || VSize(P.Location - C.Pawn.Location) < VSize(Best.Location - C.Pawn.Location)))
			Best = P;
	if (Best == None)
	{
		Note("nearenemy: no hostile in the level");
		return;
	}
	Dir = C.Pawn.Location - Best.Location;
	Dir.Z = 0;
	Spot = Best.Location + Normal(Dir) * Dist + vect(0,0,60);
	if (!C.Pawn.SetLocation(Spot))
		Spot = Best.Location + vect(0,0,1) * (Best.CollisionHeight + C.Pawn.CollisionHeight + 20);
	C.Pawn.SetLocation(Spot);
	C.SetRotation(rotator(Best.Location - C.Pawn.Location));
	Aim(ViewDeg(C.Rotation.Yaw), 0);
	Note("nearenemy: " $ Best $ " (" $ Best.Controller $ "), player at " $ C.Pawn.Location $ ", " $ int(VSize(Best.Location - C.Pawn.Location)) $ " away");
}

function SpawnAhead(string ClassName, float Ahead, float Right)
{
	local class<Actor> C;
	local Actor A;
	local Pawn P;
	local vector X, Y, Z, Spot, HitLocation, HitNormal;

	C = class<Actor>(DynamicLoadObject(ClassName, class'Class'));
	if (C == None || PC() == None || PC().Pawn == None)
	{
		Note("spawn: no class " $ ClassName $ " (" $ C $ ") or no player");
		return;
	}
	GetAxes(PC().Rotation, X, Y, Z);
	X.Z = 0;
	Y.Z = 0;
	Spot = PC().Pawn.Location + Normal(X) * Ahead + Normal(Y) * Right;
	// stand it on the floor there, clear of the walls
	if (Trace(HitLocation, HitNormal, Spot - vect(0,0,1000), Spot + vect(0,0,200), false) != None)
		Spot = HitLocation + vect(0,0,1) * (C.default.CollisionHeight + 10);
	A = Spawn(C,,, Spot, rotator(PC().Pawn.Location - Spot), C.default.DrawScale, C.default.DrawScale3D, true);
	P = Pawn(A);
	if (P != None && P.Controller == None && P.ControllerClass != None)
	{
		P.Controller = Spawn(P.ControllerClass);
		if (P.Controller != None)
			P.Controller.Possess(P);
	}
	Note("spawn: " $ A $ " at " $ Spot $ Eval2(P != None, " controller " $ P.Controller, ""));
}

static function string Eval2(bool B, string T, string F)
{
	if (B)
		return T;
	return F;
}

function Where()
{
	local PlayerController P;
	local EonPlayerController E;

	P = PC();
	if (P == None)
	{
		Note("where: no player");
		return;
	}
	if (P.Pawn == None)
		Note("where: controller " $ P.Name $ " state " $ P.GetStateName() $ ", no pawn");
	else
		Note("where: " $ P.Pawn.Location $ " rotation " $ P.Rotation $ " pawn " $ P.Pawn.Rotation $ " velocity " $ int(VSize(P.Pawn.Velocity)) $ " physics " $ P.Pawn.Physics $ " state " $ P.GetStateName());
	Note("where: time " $ Level.TimeSeconds $ " dilation " $ Level.TimeDilation $ " gamespeed " $ Level.Game.GameSpeed $ " paused " $ (Level.Pauser != None) $ " groundspeed " $ P.Pawn.GroundSpeed $ " velocity " $ VSize(P.Pawn.Velocity) $ " at " $ P.Pawn.Location);
	E = EonPlayerController(P);
	if (E != None && E.Camera != None && E.Camera.MoveController != None)
		Note("where: camera " $ E.Camera.MoveController.Name $ " desired " $ E.Camera.MoveController.DesiredXAxisRotation $ " current " $ E.Camera.MoveController.CurrentXAxisRotation $ " camera rot " $ E.Camera.Rotation);
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
	case "FACE":
		// steered until the view really points there: the third-person camera eases and
		// scales look input, so a fixed amount of input turns by an unpredictable angle.
		// TURN yaw pitch: by that much from here; FACE yaw [pitch]: to that direction
		if (Cmd == "TURN")
		{
			TargetYaw = ViewDeg(PC().Rotation.Yaw) + ArgF(1, 0);
			TargetPitch = ViewDeg(PC().Rotation.Pitch) + ArgF(2, 0);
			bAimPitch = ArgF(2, 0) != 0;
		}
		else
		{
			TargetYaw = ArgF(1, 0);
			TargetPitch = ArgF(2, 0);
			bAimPitch = Args.Length > 2;
		}
		OnTargetTime = 0;
		StepLength = 6;
		TurnYaw = 0;
		TurnPitch = 0;
		// UE2 turns the view by 32 * DeltaTime * aTurn rotation units (65536 = 360 degrees)
		class'ModPilot'.default.TurnAxis = TurnYaw * 65536.0 / 360.0 / 32.0;
		class'ModPilot'.default.LookAxis = TurnPitch * 65536.0 / 360.0 / 32.0;
		break;
	case "SPAWN":
		// SPAWN Package.Class ahead [right]: an actor that far in front of the player
		// (unreal units), a pawn with its own AI
		SpawnAhead(Args[1], ArgF(2, 300), ArgF(3, 0));
		break;
	case "NEARENEMY":
		// NEARENEMY [distance]: the player moved to that far from the level's nearest hostile, facing it
		NearEnemy(ArgF(1, 900));
		break;
	case "GIVE":
		// GIVE Package.WeaponClass: into the player's right hand
		Give(Args[1]);
		StepLength = 1.5;
		break;
	case "HURT":
		// HURT damage [Package.DamageType]: the nearest other character takes a shot from the player
		Hurt(int(ArgF(1, 30)), Args.Length > 2 ? Args[2] : "EonWeapons.dmgType_HumanPistolFire");
		break;
	case "SPEEDTEST":
		// SPEEDTEST [seconds] [walk]: run forward and log the top speed and what decides it
		class'ModPilot'.default.Forward = 1;
		class'ModPilot'.default.bHoldWalk = ArgF(2, 0) != 0;
		TopSpeed = 0;
		StepLength = ArgF(1, 3);
		break;
	case "JUMPTEST":
		// JUMPTEST: jump once and log how high the pawn rose (and the settings that decide it)
		JumpStartZ = PC().Pawn.Location.Z;
		JumpTopZ = JumpStartZ;
		Note("jumptest: JumpZ " $ PC().Pawn.JumpZ $ " default " $ PC().Pawn.default.JumpZ $ " gravity " $ PC().Pawn.PhysicsVolume.Gravity.Z $ " jump power " $ PC().Pawn.GetPowerLevel(POWERAFFECTOR_PLAYER_JUMPING) $ " fps cap " $ class'ModSettings'.default.MaxFps);
		PressButton("JUMP");
		StepLength = 2.5;
		break;
		// MOUSE x seconds: the mouse moving sideways at a steady raw rate
		class'ModPilot'.default.MouseX = ArgF(1, 0);
		StepLength = ArgF(2, 1);
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
	case "SHOTP":
		// the frame as presented, after anything a Direct3D layer adds (post effects);
		// the engine's own SHOT reads it before that
		class'ModSettings'.static.NativeCall("Capture");
		Note("shotp");
		break;
	case "SHOT":
		PC().ConsoleCommand("shot");
		Note("shot");
		break;
	case "WHERE":
		Where();
		break;
	case "FXLIST":
		FxList();
		break;
	case "FX":
		// FX Package.Class [Prop=Value ...]: add one of the engine's camera effects to the player
		Fx();
		StepLength = 0.2;
		break;
	case "TILT":
		// the third-person camera's pitch as its own weight: 0 level .. -1 as low as it goes
		// (it eases there itself; pitch look input is clamped and pulled back)
		Tilt(ArgF(1, -1));
		StepLength = 1.5;
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
	if (Cmd == "TURN" || Cmd == "FACE")
	{
		SteerView(P, DeltaTime);
		return;
	}
	if (Cmd == "SPEEDTEST" && P.Pawn != None)
	{
		TopSpeed = FMax(TopSpeed, VSize(P.Pawn.Velocity * vect(1,1,0)));
		if (StepTime < 1)
			SpeedFrom = P.Pawn.Location;
		if (StepTime >= StepLength)
			Note("speedtest: average after the first second " $ int(VSize((P.Pawn.Location - SpeedFrom) * vect(1,1,0)) / FMax(StepLength - 1, 0.1)) $ ", top " $ int(TopSpeed) $ ", GroundSpeed " $ P.Pawn.GroundSpeed $ ", GroundSpeedMax " $ EonPawn(P.Pawn).GroundSpeedMax $ ", default GroundSpeed " $ P.Pawn.default.GroundSpeed $ ", aForward " $ P.aForward);
	}
	if (Cmd == "JUMPTEST" && P.Pawn != None)
	{
		JumpTopZ = FMax(JumpTopZ, P.Pawn.Location.Z);
		if (StepTime > 0.15)
			class'ModPilot'.default.Up = 0;   // a tap, not a held jump
		if (StepTime >= StepLength)
			Note("jumptest: rose " $ int(JumpTopZ - JumpStartZ) $ " units (JumpZ now " $ P.Pawn.JumpZ $ ")");
	}
	if (StepTime >= StepLength)
		StartStep();
}

// a rotation component (65536 = 360 degrees) as degrees, -180..180
static function float ViewDeg(int R)
{
	R = R & 65535;
	if (R > 32768)
		R -= 65536;
	return R * 360.0 / 65536.0;
}

static function float WrapDeg(float D)
{
	while (D > 180) D -= 360;
	while (D < -180) D += 360;
	return D;
}

// look input proportional to how far the view still is from the target; done once it has
// stayed within 2 degrees for a moment (or after StepLength seconds)
function SteerView(PlayerController P, float DeltaTime)
{
	local float EYaw, EPitch;

	EYaw = WrapDeg(TargetYaw - ViewDeg(P.Rotation.Yaw));
	EPitch = 0;
	if (bAimPitch)
		EPitch = WrapDeg(TargetPitch - ViewDeg(P.Rotation.Pitch));
	if (Abs(EYaw) < 2 && Abs(EPitch) < 2)
		OnTargetTime += DeltaTime;
	else
		OnTargetTime = 0;
	if (OnTargetTime > 0.3 || StepTime > StepLength)
	{
		if (StepTime > StepLength)
			Note("turn: stopped " $ int(EYaw) $ " / " $ int(EPitch) $ " degrees short");
		class'ModPilot'.default.TurnAxis = 0;
		class'ModPilot'.default.LookAxis = 0;
		StartStep();
		return;
	}
	// degrees per second toward the target, as aTurn/aLookUp units (32 rotation units per unit)
	// gentle: the camera follows the input with a lag, so a strong push overshoots
	class'ModPilot'.default.TurnAxis = FClamp(EYaw * 1.5, -120, 120) * 65536.0 / 360.0 / 32.0;
	class'ModPilot'.default.LookAxis = FClamp(EPitch * 3.0, -120, 120) * 65536.0 / 360.0 / 32.0;
}

defaultproperties
{
     bAlwaysTick=True
     RemoteRole=ROLE_None
}
