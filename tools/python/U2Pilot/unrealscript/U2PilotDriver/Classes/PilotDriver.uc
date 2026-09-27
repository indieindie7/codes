//=============================================================================
// U2Pilot background mode: plays a test script from inside the game, so the
// game can run unfocused without touching the real keyboard and mouse.
// Steps come from System\U2Pilot.ini ([U2PilotDriver.PilotDriver] Steps=...),
// written by u2pilot.py. Every step is logged as "PilotDriver: ..." so the
// runner can follow along through the (force-flushed) log.
//
// Steps:
//   waitcontrol [timeout]    until the player has a pawn and is walking normally
//   wait SECONDS
//   move FORWARD STRAFE SECONDS   (-1..1 each, e.g. "move 1 0 2" = hold W 2s)
//   turn YAW PITCH SECONDS   (degrees, spread over SECONDS)
//   fire SECONDS / altfire SECONDS / jump
//   crouch 1|0 / run 1|0     (run is on by default, like the real keyboard)
//   console COMMAND          any console command (cheats, summon, ...)
//   shots INTERVAL           take an in-game screenshot every INTERVAL s (0 = off)
//   shot                     take one screenshot now
//   mark TEXT                write a marker to the log
//   travel URL               switch level (e.g. travel DM-Labs?Mutator=...)
//   give WEAPONCLASS         give a weapon with full ammo and switch to it
//   spawnproj CLASS           spawn a projectile as if the player fired it
//   quit
//   @MAPNAME <step>          run the step only on that map
//=============================================================================
class PilotDriver extends Mutator
	config(U2Pilot);

var config array<string> Steps;

var PlayerController PC;
var PilotInput PI;
var int StepIndex;
var float StepTime, StepLength;
var string Cmd;
var array<string> Args;
var float TurnYaw, TurnPitch;   // degrees per second while turning
var float ShotInterval, NextShot;
var int ShotCount;
var bool bDone;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	Log("PilotDriver: loaded "$Steps.Length$" steps");
	StepIndex = -1;
}

function string MapName()
{
	local string M;

	M = GetURLMap();
	if (InStr(M, ".") >= 0)
		M = Left(M, InStr(M, "."));
	return M;
}

function bool AttachPilot()
{
	local Controller C;

	if (PC == None)
		for (C = Level.ControllerList; C != None; C = C.NextController)
			if (PlayerController(C) != None)
				PC = PlayerController(C);
	if (PC == None || PC.PlayerInput == None)
		return false;
	if (PilotInput(PC.PlayerInput) == None)
	{
		PI = new(PC) class'PilotInput';
		PI.MouseSensitivity = PC.PlayerInput.MouseSensitivity;
		PI.bInvertMouse = PC.PlayerInput.bInvertMouse;
		PC.PlayerInput = PI;
		Log("PilotDriver: input attached to "$PC);
	}
	else
		PI = PilotInput(PC.PlayerInput);
	return true;
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
	PI.Forward = 0;
	PI.Strafe = 0;
	PI.bHoldFire = false;
	PI.bHoldAltFire = false;
	PI.bHoldJump = false;
	// a real key-up clears these; our virtual buttons must do it themselves
	if (PC != None)
	{
		PC.bFire = 0;
		PC.bAltFire = 0;
	}
	TurnYaw = 0;
	TurnPitch = 0;
}

function bool InControl()
{
	return PC.Pawn != None && PC.IsInState('PlayerWalking');
}

function StartStep()
{
	StepIndex++;
	StepTime = 0;
	StepLength = 0;
	ReleaseAll();
	if (StepIndex >= Steps.Length)
	{
		Log("PilotDriver: done");
		bDone = true;
		return;
	}
	SplitStep(Steps[StepIndex]);
	// "@MAP step" only runs on that map (the driver restarts its list on every map)
	if (Left(Args[0], 1) == "@")
	{
		if (Caps(Mid(Args[0], 1)) != Caps(MapName()))
		{
			StartStep();
			return;
		}
		Args.Remove(0, 1);
	}
	Cmd = Caps(Args[0]);
	Log("PilotDriver: step "$(StepIndex + 1)$": "$Steps[StepIndex]);

	switch (Cmd)
	{
	case "WAIT":
		StepLength = ArgF(1, 1);
		break;
	case "WAITCONTROL":
		StepLength = ArgF(1, 120);
		break;
	case "MOVE":
		PI.Forward = ArgF(1, 0);
		PI.Strafe = ArgF(2, 0);
		StepLength = ArgF(3, 1);
		break;
	case "TURN":
		StepLength = FMax(ArgF(3, 0.5), 0.01);
		TurnYaw = ArgF(1, 0) / StepLength;
		TurnPitch = ArgF(2, 0) / StepLength;
		break;
	case "FIRE":
		PI.bHoldFire = true;
		PC.Fire();
		StepLength = ArgF(1, 0.1);
		break;
	case "ALTFIRE":
		PI.bHoldAltFire = true;
		PC.AltFire();
		StepLength = ArgF(1, 0.1);
		break;
	case "JUMP":
		PI.bHoldJump = true;
		PC.Jump();   // what the Space binding does
		StepLength = 0.2;
		break;
	case "CROUCH":
		PI.WantCrouch = byte(ArgF(1, 1) != 0);
		break;
	case "RUN":
		PI.WantRun = byte(ArgF(1, 1) != 0);
		break;
	case "CONSOLE":
		Log("PilotDriver: console -> "$PC.ConsoleCommand(RestOf(1)));
		break;
	case "TRAVEL":
		Log("PilotDriver: travelling to "$RestOf(1));
		PC.ClientTravel(RestOf(1), TRAVEL_Absolute, false);
		StepLength = 120;
		Cmd = "WAIT";
		break;
	case "SERVERTRAVEL":
		Log("PilotDriver: server-travelling to "$RestOf(1));
		Level.Game.ProcessServerTravel(RestOf(1), false);
		StepLength = 120;
		Cmd = "WAIT";
		break;
	case "GIVE":
		GiveWeaponWithAmmo(RestOf(1));
		StepLength = 1.5;   // let the weapon come up
		Cmd = "WAIT";
		break;
	case "STATUS":
		if (PC.Pawn != None)
			Log("PilotDriver: status weapon="$PC.Pawn.Weapon$" pending="$PC.Pawn.PendingWeapon$" ammo="$Eval2(PC.Pawn.Weapon != None && PC.Pawn.Weapon.AmmoType != None, PC.Pawn.Weapon.AmmoType)$" hasammo="$(PC.Pawn.Weapon != None && PC.Pawn.Weapon.HasAmmo()));
		break;
	case "SPAWNPROJ":
		SpawnPlayerProjectile(RestOf(1));
		break;
	case "SHOTS":
		ShotInterval = ArgF(1, 0);
		NextShot = 0;
		break;
	case "SHOT":
		TakeShot();
		break;
	case "MARK":
		break;
	case "QUIT":
		Log("PilotDriver: done");
		bDone = true;
		PC.ConsoleCommand("exit");
		break;
	default:
		Log("PilotDriver: unknown step '"$Args[0]$"' - skipped");
	}
}

// give a weapon (full ammo) and switch to it
function GiveWeaponWithAmmo(string ClassName)
{
	local class<Weapon> WC;
	local Inventory Inv;

	if (PC.Pawn == None)
		return;
	WC = class<Weapon>(DynamicLoadObject(ClassName, class'Class', true));
	if (WC == None)
	{
		Log("PilotDriver: no weapon class "$ClassName);
		return;
	}
	PC.Pawn.GiveWeapon(ClassName);
	for (Inv = PC.Pawn.Inventory; Inv != None; Inv = Inv.Inventory)
		if (Weapon(Inv) != None && Weapon(Inv).AmmoType != None)
			Weapon(Inv).AmmoType.AmmoAmount = Weapon(Inv).AmmoType.MaxAmmo;
	PC.GetWeapon(WC);
	Log("PilotDriver: gave "$ClassName);
}

function string Eval2(bool b, Object O)
{
	if (b && O != None)
		return string(O.Name)$"("$Ammunition(O).AmmoAmount$")";
	return "none";
}

// spawn a projectile as if the player had fired it (for testing projectile mods)
function SpawnPlayerProjectile(string ClassName)
{
	local class<Projectile> PCl;
	local Projectile P;

	if (PC.Pawn == None)
		return;
	PCl = class<Projectile>(DynamicLoadObject(ClassName, class'Class', true));
	if (PCl == None)
	{
		Log("PilotDriver: no projectile class "$ClassName);
		return;
	}
	P = Spawn(PCl, PC.Pawn,, PC.Pawn.Location + vector(PC.Rotation) * 80 + vect(0,0,30), PC.Rotation);
	if (P != None)
	{
		P.Instigator = PC.Pawn;
		Log("PilotDriver: spawned "$P.Class.Name$" speed="$int(VSize(P.Velocity)));
	}
}

function TakeShot()
{
	ShotCount++;
	PC.ConsoleCommand("shot");
	Log("PilotDriver: shot "$ShotCount$" at "$Level.TimeSeconds);
}

event Tick(float DeltaTime)
{
	local rotator R;

	if (bDone || !AttachPilot())
		return;

	if (ShotInterval > 0 && Level.TimeSeconds >= NextShot)
	{
		NextShot = Level.TimeSeconds + ShotInterval;
		TakeShot();
	}

	if (StepIndex < 0)
	{
		StartStep();
		return;
	}

	StepTime += DeltaTime;
	if (TurnYaw != 0 || TurnPitch != 0)
	{
		R = PC.Rotation;
		R.Yaw += TurnYaw * DeltaTime * 65536.0 / 360.0;
		R.Pitch += TurnPitch * DeltaTime * 65536.0 / 360.0;
		PC.SetRotation(R);
	}

	if (Cmd == "WAITCONTROL")
	{
		if (InControl())
		{
			Log("PilotDriver: in control after "$StepTime$"s");
			StartStep();
		}
		else if (StepTime >= StepLength)
		{
			Log("PilotDriver: waitcontrol timed out");
			StartStep();
		}
		return;
	}
	if (StepTime >= StepLength)
		StartStep();
}

defaultproperties
{
	RemoteRole=ROLE_None
}
