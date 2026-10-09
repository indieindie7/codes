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
//   spawnpack [n] [ahead] [spread]   n hounds ahead of the player in a squad of their own (for the pack tests)
//   houndtest [SECONDS]      every hound's role, distance and bearing round the player's view twice a
//                            second, and the pack's measures (ModMinds.HoundStats) every 5 s and at the end
//   leaplinks                the level's wall-kick links (ModMinds.BuildLinks): ends, straight and route lengths, the wall
//   wallkick                 the hound nearest the player kicks off a wall at it now, if one fits (ModMinds.ForceKick)
//=============================================================================
class ModPilot extends Info
	config(AdventMod);

var config array<string> Steps;
var bool bDashed;
// BONETEST
var Pawn BoneAI;
var float BoneMinP, BoneMaxP, BoneMinA, BoneMaxA;
var int BoneN, BoneDrawnA, BoneLagStep;
var float BoneHead0, BoneHeadLag[4];                      // DASH: the dodge was pressed

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
var float HoundT;                        // HOUNDTEST: time since the last report
var int HoundN;                          // ... and reports so far

var int PrintsLeft, PrintPhase, PrintNo;  // RANDOMPRINTS
var float PrintT, PrintSettle;
var array<NavigationPoint> PrintNavs;
var name HurtBone;    // HURT's bone (a string can only become a name through SetPropertyText)

function string RouteStr(Controller C, out int N)
{
	local int i;
	local string S;

	N = 0;
	for (i = 0; i < 16; i++)
		if (C.RouteCache[i] != None)
		{
			S = S $ " " $ C.RouteCache[i].Name;
			N++;
		}
	return S;
}

function RouteTest(float Dist)
{
	local Controller C, Other;
	local int Seen;
	local NavigationPoint N, Goal, Mark[4];
	local Actor Step;
	local int i, j, k, Len, Marks, Mode, Tries;
	local float Best, D;
	local string Base, Got, ModeName;
	local bool bAvoided;
	local int OldInt[4];
	local byte OldBool[4];
	local ReachSpec R;

	// the engine's search from an AI controller (the player's own returns no routes): the
	// level's nearest living bot
	Best = 1000000000.0;
	for (Other = Level.ControllerList; Other != None; Other = Other.nextController)
	{
		Seen++;
		if (PlayerController(Other) == None && Other.Pawn != None && Other.Pawn.Health > 0 && PC() != None && PC().Pawn != None
			&& VSize(Other.Pawn.Location - PC().Pawn.Location) < Best)
		{
			Best = VSize(Other.Pawn.Location - PC().Pawn.Location);
			C = Other;
		}
	}
	if (C == None)
	{
		Note("routetest: no AI controller with a pawn (" $ Seen $ " controllers)");
		return;
	}
	Note("routetest: searching as " $ C.Name $ " (" $ C.Pawn.Name $ ")");
	// a goal about Dist away whose route has at least 5 steps (some tries)
	for (Tries = 0; Tries < 12 && Goal == None; Tries++)
	{
		Best = 1000000000.0;
		N = None;
		for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
		{
			D = Abs(VSize(N.Location - C.Pawn.Location) - Dist * (1 + 0.15 * Tries));
			if (D < Best && N.Tag != 'RouteTried')
			{
				Best = D;
				Goal = N;
			}
		}
		if (Goal == None)
			break;
		Step = C.FindPathToward(Goal);
		RouteStr(C, Len);
		if (Step == None || Len < 5)
		{
			Goal.Tag = 'RouteTried';
			Goal = None;
		}
	}
	if (Goal == None)
	{
		Note("routetest: no goal with a route of 5+ steps near " $ int(Dist));
		return;
	}
	Base = RouteStr(C, Len);
	// the nodes to make expensive: the route's middle (not its first two nor its last)
	for (i = 2; i < Len - 1 && Marks < 4; i++)
		if (NavigationPoint(C.RouteCache[i]) != None)
			Mark[Marks++] = NavigationPoint(C.RouteCache[i]);
	Note("routetest: goal " $ Goal.Name $ " " $ int(VSize(Goal.Location - C.Pawn.Location)) $ " away, base route (" $ Len $ "):" $ Base $ "; marking " $ Marks);
	for (Mode = 0; Mode < 5; Mode++)
	{
		// raise
		for (i = 0; i < Marks; i++)
		{
			switch (Mode)
			{
				case 0: OldInt[i] = Mark[i].ExtraCost; Mark[i].ExtraCost = 100000; ModeName = "ExtraCost"; break;
				case 1: OldInt[i] = Mark[i].TransientCost; Mark[i].TransientCost = 100000; ModeName = "TransientCost"; break;
				case 2: OldInt[i] = Mark[i].FearCost; Mark[i].FearCost = 100000; ModeName = "FearCost"; break;
				case 3: OldBool[i] = byte(Mark[i].bBlocked); Mark[i].bBlocked = true; ModeName = "bBlocked"; break;
				case 4:
					ModeName = "ReachSpec.Distance (into the marked nodes)";
					break;
			}
		}
		if (Mode == 4)
		{
			// every edge that ends at a marked node, made 100x longer
			k = 0;
			for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
				for (j = 0; j < N.PathList.Length; j++)
				{
					R = N.PathList[j];
					for (i = 0; i < Marks; i++)
						if (R != None && R.End == Mark[i])
							R.Distance *= 100;
				}
		}
		Step = C.FindPathToward(Goal);
		Got = RouteStr(C, Len);
		bAvoided = Step != None;
		for (i = 0; i < 16; i++)
			for (j = 0; j < Marks; j++)
				if (C.RouteCache[i] == Mark[j])
					bAvoided = false;
		Note("routetest: " $ ModeName $ ": " $ Eval2(Step == None, "NO ROUTE", Eval2(bAvoided, "AVOIDED (read by the search)", "same nodes (ignored)")) $ ", route (" $ Len $ "):" $ Got);
		// restore
		for (i = 0; i < Marks; i++)
		{
			switch (Mode)
			{
				case 0: Mark[i].ExtraCost = OldInt[i]; break;
				case 1: Mark[i].TransientCost = OldInt[i]; break;
				case 2: Mark[i].FearCost = OldInt[i]; break;
				case 3: Mark[i].bBlocked = OldBool[i] != 0; break;
			}
		}
		if (Mode == 4)
			for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
				for (j = 0; j < N.PathList.Length; j++)
				{
					R = N.PathList[j];
					for (i = 0; i < Marks; i++)
						if (R != None && R.End == Mark[i])
							R.Distance /= 100;
				}
	}
	// and after all of it: the base route again (nothing left changed)
	C.FindPathToward(Goal);
	Got = RouteStr(C, Len);
	Note("routetest: after restoring: " $ Eval2(Got == Base, "same as the base route", "DIFFERENT:" $ Got));
}

function MindOrder(string S)
{
	local ModMinds M;

	foreach DynamicActors(class'ModMinds', M)
	{
		M.SetOrder(Locs(S));
		return;
	}
	Note("mindorder: no ModMinds in this level");
}

function BoneStart()
{
	local Controller C;
	local float Best, D;

	BoneAI = None;
	Best = 100000000.0;
	if (PC() == None || PC().Pawn == None)
		return;
	for (C = Level.ControllerList; C != None; C = C.nextController)
		if (PlayerController(C) == None && C.Pawn != None && C.Pawn.Health > 0 && !C.Pawn.IsA('Vehicle'))
		{
			D = VSize(C.Pawn.Location - PC().Pawn.Location);
			if (D < Best)
			{
				Best = D;
				BoneAI = C.Pawn;
			}
		}
	BoneMinP = 100000; BoneMaxP = -100000; BoneMinA = 100000; BoneMaxA = -100000;
	BoneN = 0;
	BoneDrawnA = 0;
	BoneLagStep = -1;
}

// the foot's place along the pawn's forward axis (a posed run swings it back and forth)
static function float FootAlong(Pawn P)
{
	local vector X, Y, Z;

	GetAxes(P.Rotation, X, Y, Z);
	return (P.GetBoneCoords('leftFoot').Origin - P.Location) dot X;
}

static function float HeadSide(Pawn P)
{
	local vector X, Y, Z;

	GetAxes(P.Rotation, X, Y, Z);
	return (P.GetBoneCoords('head').Origin - P.GetBoneCoords('hips').Origin) dot Y;
}

function BoneTick()
{
	local Pawn P;
	local float F;

	P = PC().Pawn;
	if (P == None)
		return;
	BoneN++;
	F = FootAlong(P);
	BoneMinP = FMin(BoneMinP, F);
	BoneMaxP = FMax(BoneMaxP, F);
	if (BoneAI != None && !BoneAI.bDeleteMe)
	{
		F = FootAlong(BoneAI);
		BoneMinA = FMin(BoneMinA, F);
		BoneMaxA = FMax(BoneMaxA, F);
		if (Level.TimeSeconds - BoneAI.LastRenderTime < 0.1)
			BoneDrawnA++;
	}
	// the lag test, in the step's last half second: roll the spine, read the head
	if (BoneLagStep < 0 && StepTime > StepLength - 0.6)
	{
		BoneHead0 = HeadSide(P);
		P.SetBoneRotation('spine', rot(0,0,6000), 0, 1);
		BoneHeadLag[0] = HeadSide(P);
		BoneLagStep = 1;
	}
	else if (BoneLagStep >= 1 && BoneLagStep <= 3)
	{
		BoneHeadLag[BoneLagStep] = HeadSide(P);
		BoneLagStep++;
		if (BoneLagStep == 4)
		{
			P.SetBoneRotation('spine', rot(0,0,0), 0, 0);
			Note("bonetest: " $ BoneN $ " ticks. Player (drawn): left foot swung " $ int(BoneMaxP - BoneMinP) $ " units along the body"
				$ Eval2(BoneAI != None, "; nearest AI " $ BoneAI.Name $ " (drawn " $ BoneDrawnA $ "/" $ BoneN $ " ticks): " $ int(BoneMaxA - BoneMinA) $ " units", "; no AI")
				$ ". Spine rolled 33 deg: the head's sideways offset " $ int(BoneHead0) $ " before, " $ int(BoneHeadLag[0]) $ " the same tick, "
				$ int(BoneHeadLag[1]) $ " / " $ int(BoneHeadLag[2]) $ " / " $ int(BoneHeadLag[3]) $ " one, two, three ticks on");
		}
	}
}

function bool FaceTo(string Name, float Back)
{
	local Actor A, Found;
	local Pawn P;
	local vector Spot, Away;

	P = PC().Pawn;
	if (P == None)
		return false;
	foreach AllActors(class'Actor', A)
		if (string(A.Name) ~= Name)
		{
			Found = A;
			break;
		}
	if (Found == None)
	{
		Note("faceto: no actor " $ Name);
		return false;
	}
	if (Back > 0)
	{
		Away = (P.Location - Found.Location) * vect(1,1,0);
		if (VSize(Away) < 1)
			Away = vect(1,0,0);
		Spot = Found.Location + Normal(Away) * Back;
		Spot.Z = P.Location.Z;
		P.SetLocation(Spot);
	}
	TargetYaw = ViewDeg(rotator(Found.Location - P.Location).Yaw);
	TargetPitch = 0;
	Note("faceto: " $ Found.Name $ " from " $ int(VSize((Found.Location - P.Location) * vect(1,1,0))) $ " away, yaw " $ int(TargetYaw));
	return true;
}

function MindList()
{
	local ModMinds M;

	foreach DynamicActors(class'ModMinds', M)
	{
		Note("mindlist: " $ M.List());
		return;
	}
	Note("mindlist: no ModMinds in this level");
}

// HOUNDTEST: the hounds now, and (bStats) the pack's measures so far
function HoundTest(bool bStats)
{
	local ModMinds M;

	foreach DynamicActors(class'ModMinds', M)
	{
		Note("houndtest: t " $ int(StepTime * 10) / 10.0 $ " " $ M.HoundReport());
		if (bStats)
			Note("houndstats: " $ M.HoundStats());
		return;
	}
	Note("houndtest: no ModMinds in this level");
}

// LEAPLINKS: the wall-kick links ModMinds built for this level
function LeapLinks()
{
	local ModMinds M;

	foreach DynamicActors(class'ModMinds', M)
	{
		Note("leaplinks: " $ M.LinkList());
		return;
	}
	Note("leaplinks: no ModMinds in this level");
}

// WALLKICK: the nearest hound kicks off a wall at the player
function WallKick()
{
	local ModMinds M;

	foreach DynamicActors(class'ModMinds', M)
	{
		Note("wallkick: " $ M.ForceKick());
		return;
	}
	Note("wallkick: no ModMinds in this level");
}

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

function string Arg(int i)
{
	if (i < Args.Length)
		return Args[i];
	return "";
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

// what a shot through the nearest body does (ModGore.CorpseHit, the same call its
// projectile check makes); spawning a real projectile without a gun behind it crashes
function ShootCorpse(string ClassName)
{
	local Pawn P, Best;
	local ModGore G;
	local vector Dir;

	if (PC() == None || PC().Pawn == None)
		return;
	ForEach DynamicActors(class'Pawn', P)
		if (P != PC().Pawn && P.Health <= 0 && !P.bDeleteMe && (Best == None || VSize(P.Location - PC().Pawn.Location) < VSize(Best.Location - PC().Pawn.Location)))
			Best = P;
	ForEach DynamicActors(class'ModGore', G)
		break;
	if (Best == None || G == None)
	{
		ForEach PC().Pawn.RadiusActors(class'Pawn', P, 2000)
			if (P != PC().Pawn)
				Note("shootcorpse: near " $ P $ " health " $ P.Health $ " state " $ P.GetStateName() $ " physics " $ P.Physics $ " deleted " $ P.bDeleteMe);
		Note("shootcorpse: no body or no ModGore (" $ G $ ")");
		return;
	}
	Note("shootcorpse: " $ Best $ " (" $ Best.GetStateName() $ ", physics " $ Best.Physics $ ")");
	Dir = Normal(Best.Location - PC().Pawn.Location);
	G.CorpseHit(Best, Best.Location - Dir * Best.CollisionRadius * 0.5, Dir);
}

// a shot's impact where the view (offset by YawOff, PitchOff degrees) meets the level
function ShootWall(float YawOff, float PitchOff)
{
	local ModGore G;
	local rotator R;
	local vector Eye, Dir, HitL, HitN;
	local Actor A;

	if (PC() == None || PC().Pawn == None)
		return;
	ForEach DynamicActors(class'ModGore', G)
		break;
	if (G == None)
	{
		Note("shootwall: no ModGore");
		return;
	}
	R = PC().Rotation;
	R.Yaw += int(YawOff * 65536.0 / 360.0);
	R.Pitch += int(PitchOff * 65536.0 / 360.0);
	Dir = vector(R);
	Eye = PC().Pawn.Location + vect(0,0,1) * PC().Pawn.EyeHeight;
	A = PC().Pawn.Trace(HitL, HitN, Eye + Dir * 3000, Eye, false);
	Note("shootwall: " $ A $ " at " $ HitL $ " normal " $ HitN);
	if (A == None)
		return;
	G.ShotGone(HitL - Dir * 8, Dir * 2500);
}

function Hurt(int Damage, string TypeName, optional string BoneName)
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
	if (BoneName != "")
	{
		// a name from a string: through a property that takes text
		SetPropertyText("HurtBone", BoneName);
		Spot = Best.GetBoneCoords(HurtBone).Origin;
	}
	Note("hurt: " $ Best $ " (health " $ Best.Health $ ") " $ Damage $ " " $ T $ ", " $ int(VSize(Best.Location - C.Pawn.Location)) $ " away");
	Best.TakeDamage(Damage, C.Pawn, Spot, Dir * 20000, T);
	Aim(ViewDeg(rotator(Best.Location - C.Pawn.Location).Yaw), -12);
}

function NearEnemy(float Dist, string Filter)
{
	local Pawn P, Best;
	local vector Spot, Dir;
	local PlayerController C;

	C = PC();
	if (C == None || C.Pawn == None)
		return;
	ForEach DynamicActors(class'Pawn', P)
		if (class'ModTargeting'.static.IsHostile(P) && (Filter == "" || InStr(Caps(string(P.Class)), Caps(Filter)) >= 0)
			&& (Best == None || VSize(P.Location - C.Pawn.Location) < VSize(Best.Location - C.Pawn.Location)))
			Best = P;
	if (Best == None)
	{
		Note("nearenemy: no hostile" $ Eval2(Filter != "", " of class " $ Filter, "") $ " in the level");
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

// SPAWNPACK: a squad made here, the way the level's own are set up at load (FinishGameInitialization
// finds its group and team), then the hounds join it (the first leads)
function SpawnPack(int N, float Ahead, float Spread)
{
	local SquadAI S;
	local int i, Joined;
	local Pawn P;
	local Bot B;

	S = Spawn(class'SquadAI');
	if (S == None)
	{
		Note("spawnpack: no squad");
		return;
	}
	S.Tag = 'ModPack';
	S.bAutoStasis = false;
	S.DesiredSquadSize = N;
	S.FinishGameInitialization();
	S.SetStasis(false);
	for (i = 0; i < N; i++)
	{
		P = Pawn(SpawnAhead("EonCharacters.SeekerDog", Ahead + 120 * (i % 2), (i - (N - 1) * 0.5) * Spread));
		if (P == None)
			continue;
		B = Bot(P.Controller);
		if (B == None)
			continue;
		if (B.Squad == None)
		{
			if (S.SquadLeader == None)
				S.SetLeader(B);
			else
				S.AddBot(B);
		}
		if (B.Squad == S)
			Joined++;
		// they know the player at once (a repeatable fight: the game's own sighting can take 1-10 s or not come)
		B.AssignEnemy(PC().Pawn, true);
	}
	S.AddEnemy(PC().Pawn);
	Note("spawnpack: " $ N $ " hounds, " $ Joined $ " in squad " $ S $ " (group " $ S.MyGroup $ ", leader " $ S.SquadLeader $ ", stasis " $ S.bStasis $ ")");
}

function Actor SpawnAhead(string ClassName, float Ahead, float Right)
{
	local class<Actor> C;
	local Actor A;
	local Pawn P;
	local vector X, Y, Z, Spot, HitLocation, HitNormal;

	C = class<Actor>(DynamicLoadObject(ClassName, class'Class'));
	if (C == None || PC() == None || PC().Pawn == None)
	{
		Note("spawn: no class " $ ClassName $ " (" $ C $ ") or no player");
		return None;
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
	return A;
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

// the dead: physics, state, and how high the head is above the feet (a body frozen
// standing has its head high)
function CorpseList()
{
	local Pawn P;
	local int n;
	local coords C;
	local vector Floor, HitL, HitN;

	foreach DynamicActors(class'Pawn', P)
	{
		if ((P.Health > 0 && P.Physics != PHYS_KarmaRagdoll) || P.IsHumanControlled())
			continue;
		n++;
		C = P.GetBoneCoords('head');
		Floor = P.Location - vect(0,0,1) * (P.CollisionHeight + 200);
		Trace(HitL, HitN, Floor, P.Location + vect(0,0,10), false);
		Note("corpselist: " $ P $ " health " $ P.Health $ " physics " $ P.Physics $ " state " $ P.GetStateName() $ " head above floor " $ int(C.Origin.Z - HitL.Z) $ " (standing " $ int(2 * P.default.CollisionHeight) $ ") z " $ int(P.Location.Z) $ " head z " $ int(C.Origin.Z) $ " hidden " $ P.bHidden);
	}
	Note("corpselist: " $ n $ " dead, ragdoll cap " $ Level.MaxRagdolls);
	n = 0;
	foreach DynamicActors(class'Pawn', P)
		if (P.Health > 0 && !P.IsHumanControlled() && P.Controller != None && !P.Controller.SameTeamAs(PC().Pawn))
			n++;
	Note("corpselist: " $ n $ " hostiles alive, player at " $ PC().Pawn.Location);
}

function Dogs()
{
	local Pawn P;

	foreach AllActors(class'Pawn', P)
		if (P.IsA('SeekerDog') || InStr(Caps(string(P.Mesh)), "HOUND") >= 0)
			Note("dogs: " $ P $ " class " $ P.Class $ " mesh " $ P.Mesh $ " drawscale " $ P.DrawScale $ " 3d " $ P.DrawScale3D $ " prepivot " $ P.PrePivot $ " ragdoll " $ AdventPawn(P).RagdollOverride $ " kparams " $ P.KParams $ " health " $ P.Health $ " collision " $ P.CollisionRadius $ "/" $ P.CollisionHeight);
}

function GibList()
{
	local ModGib G;
	local int n;

	foreach DynamicActors(class'ModGib', G)
	{
		n++;
		if (n <= 6)
			Note("giblist: " $ G $ " at " $ G.Location $ " mesh " $ G.StaticMesh $ " scale " $ G.DrawScale $ " hidden " $ G.bHidden $ " settled " $ G.bSettled $ " vel " $ G.Vel $ " skins " $ G.Skins[0] $ "/" $ G.Skins[1] $ " drawtype " $ G.DrawType);
	}
	Note("giblist: " $ n $ " gibs, player at " $ PC().Pawn.Location);
}

function GooList()
{
	local ModGore G;

	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None)
		Note("goolist: no ModGore");
	else
		G.GooList();
}

// DRIPTEST [ahead]: blood that drips, three ways at once: a spray on the ceiling over a spot
// `ahead` units in front of the player (if there is a ceiling within 1200), a spray high on the
// wall straight ahead (within 800) with drops off its lower edge, and the nearest other living
// character bleeding hard (a trail of falling drops from its wound)
function DripTest(float Ahead)
{
	local ModGore G;
	local Pawn P, Best;
	local vector X, Y, Z, Spot, Eye, HitL, HitN;

	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None || PC() == None || PC().Pawn == None)
	{
		Note("driptest: no ModGore or no player");
		return;
	}
	GetAxes(PC().Rotation, X, Y, Z);
	X.Z = 0;
	X = Normal(X);
	Spot = PC().Pawn.Location + X * Ahead;
	if (G.Trace(HitL, HitN, Spot + vect(0,0,1200), Spot, false) != None && HitN.Z < -0.5)
	{
		G.Mark(G.KindSpray(1), HitL, HitN, vect(0,0,0), G.DecalScale * 0.8);
		Note("driptest: ceiling spray at " $ HitL $ " (" $ int(HitL.Z - PC().Pawn.Location.Z) $ " over the player)");
	}
	else
		Note("driptest: no ceiling within 1200 over " $ Spot);
	Eye = PC().Pawn.Location + vect(0,0,1) * (PC().Pawn.EyeHeight + 50);
	if (G.Trace(HitL, HitN, Eye + X * 800, Eye, false) != None && Abs(HitN.Z) < 0.5)
	{
		G.Mark(G.KindSpray(1), HitL, HitN, vect(0,0,-1), G.DecalScale);
		G.WallDrip(HitL, HitN, G.WallBelow(G.DecalScale), 1, 10);
		Note("driptest: wall spray at " $ HitL $ " normal " $ HitN);
	}
	else
		Note("driptest: no wall within 800 ahead");
	foreach DynamicActors(class'Pawn', P)
		if (P != PC().Pawn && P.Health > 0 && !P.IsA('Vehicle') && G.BloodKind(P) != 0 && (Best == None || VSize(P.Location - PC().Pawn.Location) < VSize(Best.Location - PC().Pawn.Location)))
			Best = P;
	if (Best != None)
	{
		G.AddStreak(Best, Best.Location + vect(0,0,1) * Best.CollisionHeight * 0.3, None, 1.5);
		G.Bleed(Best, 200);
		Note("driptest: " $ Best $ " bleeds, " $ int(VSize(Best.Location - PC().Pawn.Location)) $ " away");
	}
	else
		Note("driptest: no living character to bleed");
}

// WALKBLOOD [ahead] [kind]: a pool of blood on the floor `ahead` units in front of the player
// (kind 2: purple), fresh, for the player to walk through (then MOVE 1 0 2 and STEPLIST)
function WalkBlood(float Ahead, int Kind)
{
	local ModGore G;
	local vector X, Y, Z, Spot, HitL, HitN;

	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None || PC() == None || PC().Pawn == None)
	{
		Note("walkblood: no ModGore or no player");
		return;
	}
	GetAxes(PC().Rotation, X, Y, Z);
	X.Z = 0;
	Spot = PC().Pawn.Location + Normal(X) * Ahead;
	if (G.Trace(HitL, HitN, Spot - vect(0,0,400), Spot, false) == None)
	{
		Note("walkblood: no floor at " $ Spot);
		return;
	}
	if (Kind == 2)
		G.Mark(G.AlienPool, HitL, HitN, vect(0,0,0), G.DecalScale);
	else
		G.Mark(G.Pool, HitL, HitN, vect(0,0,0), G.DecalScale);
	Note("walkblood: a pool at " $ HitL $ " (kind " $ Kind $ "), " $ G.FloorMarks.Length $ " wet floor marks");
}

function DropList()
{
	local ModGore G;

	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None)
		Note("droplist: no ModGore");
	else
		G.DropList();
}

function StepList()
{
	local ModGore G;

	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None)
		Note("steplist: no ModGore");
	else
		G.StepList();
}

function GooSever(int c)
{
	local ModGore G;
	local Pawn P, Best;
	local float D, BestD;

	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None || G.Severer == None || PC() == None || PC().Pawn == None || c < 0 || c >= G.Severer.Cuts.Length)
	{
		Note("goosever: no ModGore, no player or no cut " $ c);
		return;
	}
	BestD = 1000000;
	foreach DynamicActors(class'Pawn', P)
	{
		if (P == PC().Pawn || P.bHidden || G.GibSet(P) < 0)
			continue;
		D = VSize(P.Location - PC().Pawn.Location);
		if (P.Health > 0)
			D += 5000;                   // a corpse first
		if (D < BestD)
		{
			BestD = D;
			Best = P;
		}
	}
	if (Best == None)
	{
		Note("goosever: no character with a gib set");
		return;
	}
	G.Severer.Sever(Best, c, Normal(Best.Location - PC().Pawn.Location));
	Note("goosever: " $ Best $ " loses " $ G.Severer.Cuts[c].Bone $ "; " $ G.Goo.Length $ " goo strings");
}

function Blade(bool bDrop, float Dist)
{
	local ModGore G;

	ForEach DynamicActors(class'ModGore', G)
		break;
	if (G == None || G.Melee == None || PC() == None || PC().Pawn == None)
	{
		Note("blade: no ModMelee or no player");
		return;
	}
	if (bDrop)
		G.Melee.Drop(PC().Pawn.Location + vector(PC().Pawn.Rotation) * Dist);
	else
		G.Melee.Equip(PC().Pawn, G.Melee.BladeCharges);
	Note("blade: " $ G.Melee.Carried $ " charges " $ G.Melee.Charges $ " pickups " $ G.Melee.Pickups.Length);
}

function GibAhead(float Dist, string SetName)
{
	local ModGore G;
	local int i, Set;
	local vector X, Y, Z, Feet;

	Set = -1;
	for (i = 0; i < class'ModGibParts'.default.Sets.Length; i++)
		if (string(class'ModGibParts'.default.Sets[i].Name) ~= SetName)
			Set = i;
	foreach DynamicActors(class'ModGore', G)
		break;
	if (G == None || Set < 0 || PC() == None || PC().Pawn == None)
	{
		Note("gibahead: no ModGore, no set " $ SetName $ " or no player");
		return;
	}
	GetAxes(PC().Rotation, X, Y, Z);
	X.Z = 0;
	Feet = PC().Pawn.Location + Normal(X) * Dist - vect(0,0,1) * PC().Pawn.CollisionHeight;
	Note("gibahead: " $ G.SpawnGibs(Set, 1 + int(SetName ~= "seekerinfantry"), Feet, rotator(-X).Yaw, 1.0, Normal(X), 500) $ " parts of " $ SetName);
}

function BloodFx()
{
	local SurfaceProperties S;

	S = Level.GetSurfaceProperties();
	if (S == None)
	{
		Note("bloodfx: no surface table");
		return;
	}
	BloodFxEvent("HumanBlaster", S.SurfaceEvent_HumanBlaster);
	BloodFxEvent("HumanPistol", S.SurfaceEvent_HumanPistol);
	BloodFxEvent("HumanXJ9", S.SurfaceEvent_HumanXJ9);
	BloodFxEvent("SeekerPulse", S.SurfaceEvent_SeekerPulse);
	BloodFxEvent("Default", S.SurfaceEvent_DefaultWeaponEffect);
}

function BloodFxEvent(string Ev, SurfaceTypes T)
{
	if (T == None)
	{
		Note("bloodfx: " $ Ev $ " none");
		return;
	}
	BloodFxList(Ev $ " Human", T.SurfaceType_Human);
	BloodFxList(Ev $ " Seeker", T.SurfaceType_Seeker);
	BloodFxList(Ev $ " Aurelian", T.SurfaceType_Aurelian);
	BloodFxList(Ev $ " ShockTrooper", T.SurfaceType_ShockTrooper);
	BloodFxList(Ev $ " PawnDefault", T.SurfaceType_PawnDefault);
	BloodFxList(Ev $ " HoloA", T.SurfaceType_HologramGuyA);
}

function BloodFxList(string What, array<SurfaceEventArray> L)
{
	local int i, j, k, m;
	local class<Emitter> E;
	local ParticleEmitter P;
	local string S;

	for (i = 0; i < L.Length; i++)
	{
		if (L[i] == None)
			continue;
		Note("bloodfx: " $ What $ " [" $ i $ "] use " $ L[i].UseSurfaceType $ " ref " $ L[i].ReferenceArrayEntry $ " events " $ L[i].EventsToPlayArray.Length);
		for (j = 0; j < L[i].EventsToPlayArray.Length; j++)
		{
			if (L[i].EventsToPlayArray[j] == None)
				continue;
			E = L[i].EventsToPlayArray[j].Emitter;
			Note("bloodfx:   " $ E $ " projector " $ L[i].EventsToPlayArray[j].Projector $ " tex " $ L[i].EventsToPlayArray[j].ProjectorTexture);
			if (E == None)
				continue;
			for (k = 0; k < E.default.Emitters.Length; k++)
			{
				P = E.default.Emitters[k];
				if (P == None)
					continue;
				S = "";
				if (P.UseColorScale)
					for (m = 0; m < P.ColorScale.Length; m++)
						S = S $ " " $ P.ColorScale[m].Color.R $ "/" $ P.ColorScale[m].Color.G $ "/" $ P.ColorScale[m].Color.B;
				Note("bloodfx:     " $ P.Name $ " tex " $ P.Texture $ " style " $ P.DrawStyle $ " mult " $ P.ColorMultiplierRange.X.Min $ "-" $ P.ColorMultiplierRange.X.Max $ "," $ P.ColorMultiplierRange.Y.Min $ "-" $ P.ColorMultiplierRange.Y.Max $ "," $ P.ColorMultiplierRange.Z.Min $ "-" $ P.ColorMultiplierRange.Z.Max $ " scale" $ S);
			}
		}
	}
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
	case "GOTO":
		// GOTO X Y Z: the player set down there (a repeatable stand on a step or a slope; the game
		// then drops it to the floor)
		if (PC().Pawn != None)
			Note("goto " $ ArgF(1, 0) $ " " $ ArgF(2, 0) $ " " $ ArgF(3, 0) $ ": " $ PC().Pawn.SetLocation(vect(1,0,0) * ArgF(1, 0) + vect(0,1,0) * ArgF(2, 0) + vect(0,0,1) * ArgF(3, 0)));
		StepLength = 0.5;
		break;
	case "FLOORMAP":
		// FLOORMAP [reach] [step]: the floor's height on a grid around the player (rows along Y, columns
		// along X, relative to the player's floor; "." = nothing within 300 below), to find steps and slopes
		FloorMap(ArgF(1, 600), ArgF(2, 100));
		break;
	case "WAITCONTROL":
		StepLength = ArgF(1, 120);
		break;
	case "BONETEST":
		// BONETEST [SECONDS]: what reading bones from script gives (report "Dynamic body kinematics",
		// slice K0). The player runs forward while, every tick, the left foot's place relative to the
		// pawn is sampled for the player (drawn) and the nearest AI (drawn or not): a posed skeleton
		// swings the foot by tens of units, an unposed one barely moves it. Then a lag test: the spine
		// is rolled from script and the head's sideways offset read the same tick, one and two ticks on.
		class'ModPilot'.default.Forward = 1;
		StepLength = ArgF(1, 3);
		BoneStart();
		break;
	case "DASH":
		// DASH FORWARD STRAFE SECONDS: move like MOVE, and press dodge 0.25 s into it (a dodge
		// needs a direction held)
		class'ModPilot'.default.Forward = FClamp(ArgF(1, 0), -1, 1);
		class'ModPilot'.default.Strafe = FClamp(ArgF(2, 0), -1, 1);
		StepLength = ArgF(3, 1);
		bDashed = false;
		break;
	case "MOVE":
		class'ModPilot'.default.Forward = FClamp(ArgF(1, 0), -1, 1);
		class'ModPilot'.default.Strafe = FClamp(ArgF(2, 0), -1, 1);
		StepLength = ArgF(3, 1);
		break;
	case "FACETO":
		// FACETO ACTORNAME [BACK]: the player is put BACK units from that actor (on the side it
		// stands, 0 = stays), then turns to face it like FACE (for repeatable run-ups at a prop)
		if (!FaceTo(Args[1], ArgF(2, 0)))
			break;
		Cmd = "FACE";
		OnTargetTime = 0;
		StepLength = 6;
		TurnYaw = 0;
		TurnPitch = 0;
		bAimPitch = false;
		class'ModPilot'.default.TurnAxis = 0;
		class'ModPilot'.default.LookAxis = 0;
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
	case "SPAWNPACK":
		// SPAWNPACK [n] [ahead] [spread]: n hounds that far in front of the player, that far apart, in a
		// squad of their own (a pawn spawned alone has no squad, and the Bot's Do* need one)
		SpawnPack(int(ArgF(1, 3)), ArgF(2, 700), ArgF(3, 250));
		break;
	case "NEARENEMY":
		// NEARENEMY [distance] [class]: the player moved to that far from the level's nearest hostile
		// (of a class whose name contains the word, e.g. SeekerDog), facing it
		NearEnemy(ArgF(1, 900), Arg(2));
		break;
	case "HEALTH":
		// HEALTH N: the player's health set (a long fight that must not end in a death)
		if (PC().Pawn != None)
		{
			PC().Pawn.Health = int(ArgF(1, 1000));
			Note("health " $ PC().Pawn.Health);
		}
		break;
	case "GIVE":
		// GIVE Package.WeaponClass: into the player's right hand
		Give(Args[1]);
		StepLength = 1.5;
		break;
	case "SHOOTCORPSE":
		// SHOOTCORPSE [Package.ProjectileClass]: a shot from beside the player through the nearest body
		ShootCorpse(Args.Length > 1 ? Args[1] : "EonWeapons.HumanXJ9Fire_Proj");
		StepLength = 0.5;
		break;
	case "SHOOTWALL":
		// SHOOTWALL [yaw] [pitch]: a shot's impact on whatever the view (offset by that much, in
		// degrees) looks at: ModGore's impact marks (holes, scorches, burns, chips) without a weapon
		ShootWall(ArgF(1, 0), ArgF(2, 0));
		StepLength = 0.2;
		break;
	case "HURT":
		// HURT damage [Package.DamageType] [bone]: the nearest other character takes a shot from
		// the player (at that bone if one is given)
		Hurt(int(ArgF(1, 30)), Args.Length > 2 ? Args[2] : "EonWeapons.dmgType_HumanPistolFire", Args.Length > 3 ? Args[3] : "");
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
	case "DOGS":
		// every hound in the level: how it's drawn (ragdoll trouble hunting)
		Dogs();
		break;
	case "BONETEST":
		Note("bonetest: player at " $ PC().Pawn.Location $ " hips " $ PC().Pawn.GetBoneCoords('hips').Origin $ " nosuchbone " $ PC().Pawn.GetBoneCoords('nosuchbone').Origin $ " leftArm " $ PC().Pawn.GetBoneCoords('leftArm').Origin);
		break;
	case "CORPSELIST":
		CorpseList();
		break;
	case "GIBLIST":
		GibList();
		break;
	case "ROUTETEST":
		// ROUTETEST [distance]: does the engine's own path search read the path-cost fields script
		// can set (NavigationPoint ExtraCost, TransientCost, FearCost, bBlocked; ReachSpec Distance)?
		// A route from the player to a node about that far, then the same search with each field
		// raised on the route's middle nodes; it passes if the route goes round them
		RouteTest(ArgF(1, 2500));
		break;
	case "MINDORDER":
		// MINDORDER push|hidden|flank|fallback|none: a strategy for the creatures fighting the player
		MindOrder(Args[1]);
		break;
	case "MINDLIST":
		// the creatures' minds (ModMinds): feelings, task, shots past and hits
		MindList();
		break;
	case "LEAPLINKS":
		// the level's wall-kick links (see the header)
		LeapLinks();
		break;
	case "WALLKICK":
		// the hound nearest the player kicks off a wall at it now (see the header)
		WallKick();
		StepLength = 0.5;
		break;
	case "HOUNDTEST":
		// HOUNDTEST [seconds]: the hound pack watched (see the header)
		StepLength = ArgF(1, 20);
		HoundT = 0;
		HoundN = 0;
		HoundTest(true);
		break;
	case "GOOLIST":
		// the live goo strings (ModGore): ends, length against rest, age, snapped
		GooList();
		break;
	case "GOOSEVER":
		// GOOSEVER [cut]: the nearest other character (a corpse first) loses a part (ModSever.Cuts
		// index, default 3: the right arm at the shoulder), with its goo strings
		GooSever(int(ArgF(1, 3)));
		break;
	case "DRIPTEST":
		// DRIPTEST [ahead]: a ceiling spray over a spot ahead, a wall spray ahead and the nearest
		// character bleeding: falling drops from all three (ModGore drips)
		DripTest(ArgF(1, 150));
		break;
	case "WALKBLOOD":
		// WALKBLOOD [ahead] [kind]: a fresh pool ahead of the player to walk through (footprints)
		WalkBlood(ArgF(1, 120), int(ArgF(2, 1)));
		break;
	case "DROPLIST":
		// the drops in the air, the dripping places, counts
		DropList();
		break;
	case "STEPLIST":
		// the walkers with bloody feet, the fresh floor blood, the prints down
		StepList();
		break;
	case "BLADE":
		// BLADE: the energy blade in the player's hands; BLADE DROP [distance]: one lying ahead
		Blade(Args.Length > 1 && Args[1] ~= "DROP", ArgF(2, 200));
		break;
	case "GIBAHEAD":
		// GIBAHEAD [distance] [set]: a set of gib parts thrown apart that far in front of the player
		GibAhead(ArgF(1, 250), Args.Length > 2 ? Args[2] : "marine");
		break;
	case "BLOODFX":
		// the level's hit effects per species (the surface table), with their particle colours
		BloodFx();
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
	case "RANDOMPRINTS":
		// RANDOMPRINTS N [settle]: N frames from random places for visual QA
		// (tools/python/visualqa): every other one beside a random character, looking at it,
		// the rest at random navigation points; a random yaw and a slightly lowered view, a
		// moment to settle, then the frame and its character mask (NativeCall CaptureMask)
		PrintsLeft = int(ArgF(1, 10));
		PrintSettle = ArgF(2, 1.2);
		PrintPhase = 0;
		PrintNo = 0;
		PrintNavs.Length = 0;
		StepLength = 100000;
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
	if (Cmd == "BONETEST")
		BoneTick();
	if (Cmd == "HOUNDTEST")
	{
		HoundT += DeltaTime;
		if (HoundT >= 0.5)
		{
			HoundT = 0;
			HoundN++;
			HoundTest(HoundN % 10 == 0);
		}
		if (StepTime >= StepLength)
			HoundTest(true);
	}
	if (Cmd == "DASH" && !bDashed && StepTime >= 0.25)
	{
		bDashed = true;
		PressButton("DODGE");
	}
	if (Cmd == "TURN" || Cmd == "FACE")
	{
		SteerView(P, DeltaTime);
		return;
	}
	if (Cmd == "RANDOMPRINTS")
	{
		RandomPrints(P, DeltaTime);
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

// FLOORMAP: the floor's height around the player, relative to the floor under it
function FloorMap(float Reach, float Step)
{
	local Pawn P;
	local vector HitLoc, HitNorm, Base, At;
	local float X, Y, Floor;
	local string Row;

	P = PC().Pawn;
	if (P == None)
		return;
	Base = P.Location;
	Floor = Base.Z - P.CollisionHeight;
	Note("floormap: around " $ Base $ " (floor " $ int(Floor) $ "), " $ int(Step) $ " units per cell, X across, Y down");
	for (Y = -Reach; Y <= Reach; Y += Step)
	{
		Row = "floormap: y" $ int(Y) $ ":";
		for (X = -Reach; X <= Reach; X += Step)
		{
			At = Base + vect(1,0,0) * X + vect(0,1,0) * Y;
			if (Trace(HitLoc, HitNorm, At - vect(0,0,300), At + vect(0,0,40), false) == None)
				Row = Row $ " .";
			else
				Row = Row $ " " $ int(HitLoc.Z - Floor);
		}
		Note(Row);
	}
}

// RANDOMPRINTS: place, settle, capture, next
function RandomPrints(PlayerController P, float DeltaTime)
{
	local NavigationPoint N;
	local Pawn O, Pick;
	local array<Pawn> Others;
	local vector Spot, Dir;
	local float Yaw, Pitch;
	local int i, Tries;

	if (P.Pawn == None)
	{
		StartStep();
		return;
	}
	PrintT += DeltaTime;
	if (PrintPhase == 1)
	{
		if (PrintT >= PrintSettle)
		{
			class'ModSettings'.static.NativeCall("CaptureMask");
			PrintPhase = 2;
			PrintT = 0;
		}
		return;
	}
	if (PrintPhase == 2)
	{
		if (PrintT < 0.4)
			return;
		PrintsLeft--;
		PrintPhase = 0;
		if (PrintsLeft <= 0)
		{
			Note("randomprints: done, " $ PrintNo $ " frames");
			StartStep();
			return;
		}
	}
	// phase 0: a new place
	if (PrintNavs.Length == 0)
		ForEach AllActors(class'NavigationPoint', N)
			if (!N.IsA('PlayerStart'))
				PrintNavs[PrintNavs.Length] = N;
	ForEach DynamicActors(class'Pawn', O)
		if (O != P.Pawn && O.Health > 0 && !O.bHidden && O.Mesh != None)
			Others[Others.Length] = O;
	PrintNo++;
	if (PrintNo % 2 == 0 && Others.Length > 0)
	{
		// beside a character, looking at it
		Pick = Others[Rand(Others.Length)];
		for (Tries = 0; Tries < 6; Tries++)
		{
			Dir = VRand();
			Dir.Z = 0;
			Spot = Pick.Location + Normal(Dir) * (180 + FRand() * 220) + vect(0,0,40);
			if (P.Pawn.SetLocation(Spot))
				break;
		}
		Dir = Pick.Location - P.Pawn.Location;
		Yaw = ViewDeg(rotator(Dir).Yaw) + (FRand() - 0.5) * 30;
		Pitch = -5 - FRand() * 12;
		Note("randomprints: " $ PrintNo $ " beside " $ Pick $ " at " $ P.Pawn.Location $ " yaw " $ int(Yaw) $ " pitch " $ int(Pitch));
	}
	else if (PrintNavs.Length > 0)
	{
		for (Tries = 0; Tries < 8; Tries++)
		{
			i = Rand(PrintNavs.Length);
			if (P.Pawn.SetLocation(PrintNavs[i].Location + vect(0,0,1) * P.Pawn.CollisionHeight))
				break;
		}
		Yaw = FRand() * 360 - 180;
		Pitch = -3 - FRand() * 20;
		Note("randomprints: " $ PrintNo $ " at " $ PrintNavs[i] $ " " $ P.Pawn.Location $ " yaw " $ int(Yaw) $ " pitch " $ int(Pitch));
	}
	P.Pawn.Velocity = vect(0,0,0);
	Aim(Yaw, Pitch);
	PrintPhase = 1;
	PrintT = 0;
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
