//=============================================================================
// ModSettings - AdventMod's saved settings (System\AdventMod.ini), helpers for
// the engine's own settings, and the bridge to AdventNative.dll:
// NativeCall("Command") is a DynamicLoadObject on "AdventNative.Command",
// which the DLL answers (non-None = true).
//=============================================================================
class ModSettings extends Object
	config(AdventMod);

var config bool bBorderless;
// the render device never saves these itself, so we keep them and re-apply at start
var config bool bSaved;
var config bool bVSync, bTrilinear, bWidescreen;
var config int FOV;                   // the third-person camera's field of view (the game's own is 75)
var config bool bDebugFOV;            // testing: note every FOV change in AdventNative.log
var int DebugMovers;
var config string DebugCommands;      // testing: console commands (separated by |) run at the title menu, results in AdventNative.log
var config string DebugOpenMenu;      // testing: a menu class to open right after the title menu
var config string DebugActions;       // testing: steps run on that menu (see ModGUIController.RunDebug)

static function bool NativeCall(string Cmd)
{
	return DynamicLoadObject("AdventNative." $ Cmd, class'Class', true) != None;
}

static function Note(string S)
{
	NativeCall("Note:" $ S);
}

static function SetBorderless(bool bOn)
{
	if (bOn)
		NativeCall("BorderlessOn");
	else
		NativeCall("BorderlessOff");
	default.bBorderless = bOn;
	StaticSaveConfig();
}

static function bool IsFullscreen(PlayerController PC)
{
	return PC.ConsoleCommand("ISFULLSCREEN") ~= "true";
}

static function bool RenderBool(PlayerController PC, string Prop)
{
	return PC.ConsoleCommand("get D3DDrv.D3DRenderDevice " $ Prop) ~= "True";
}

static function SetRenderBool(PlayerController PC, string Prop, bool bOn)
{
	PC.ConsoleCommand("set D3DDrv.D3DRenderDevice " $ Prop $ " " $ bOn);
}

// how much wider than the game's 75 degrees: every gameplay camera is scaled by this
static function float FOVScale()
{
	if (default.FOV < 40 || default.FOV > 140)
		return 1.0;
	return default.FOV / 75.0;
}

// Field of view. The game has no FOV setting: each camera mover (third person
// 75, first person 85, vehicles 90-95) sets the camera's FOV when it takes
// over. We scale every gameplay mover by FOV/75, so the views keep their
// relation; scripted camera points keep their designed framing. A mover's own
// value is remembered in Buoyancy, an actor property these never use. Nothing
// is touched while the setting is 75. Called by ModMutator twice a second and
// by the options page when the slider moves.
static function ApplyFOV(PlayerController PC)
{
	local EonPlayerController P;
	local CameraMover M;
	local float Scale, Want, Old;
	local int N;

	P = EonPlayerController(PC);
	if (P == None)
		return;
	Scale = FOVScale();
	N = 0;
	foreach P.AllActors(class'CameraMover', M)
	{
		N++;
		if (M.IsA('CameraPointCameras'))
			continue;
		if (M.Buoyancy == 0)
		{
			if (Scale == 1.0)
				continue;
			M.Buoyancy = M.FOV_DesiredFOV;
		}
		Want = FMin(M.Buoyancy * Scale, 150.0);
		if (M.FOV_DesiredFOV != Want)
		{
			if (default.bDebugFOV)
				Note("FOV: " $ M.Name $ " " $ M.Buoyancy $ " -> " $ Want);
			M.FOV_DesiredFOV = Want;
		}
	}
	if (default.bDebugFOV && N != default.DebugMovers)
	{
		default.DebugMovers = N;
		Note("FOV: " $ N $ " camera movers, scale " $ Scale $ ", camera " $ P.Camera $ ", view " $ P.FOVAngle);
	}
	// the mover in charge set the camera when it took over, maybe before we scaled it
	if (P.Camera != None && P.Camera.MoveController != None && P.Camera.MoveController.Buoyancy != 0)
	{
		Want = P.Camera.MoveController.FOV_DesiredFOV;
		Old = P.Camera.fDefaultFOV;
		if (Old != Want)
		{
			P.Camera.SetDefaultFOV(Want);
			// not while the game is zooming (scope, scripted zoom)
			if (P.Camera.fDesiredFOV == Old)
				P.Camera.SetDesiredFOV(Want);
			if (default.bDebugFOV)
				Note("FOV: camera default " $ Old $ " -> " $ Want $ " (view now " $ P.FOVAngle $ ")");
		}
	}
}

// re-create the display at the same size so the render device picks up its settings
static function ResetDevice(PlayerController PC)
{
	local string Res;

	Res = PC.ConsoleCommand("GETCURRENTRES");
	if (IsFullscreen(PC))
		PC.ConsoleCommand("SETRES " $ Res $ "f");
	else
		PC.ConsoleCommand("SETRES " $ Res $ "w");
}

// the largest common resolution that fits the screen the game is on
static function string BestResolution()
{
	if (NativeCall("Fits:3840x2160")) return "3840x2160";
	if (NativeCall("Fits:2560x1440")) return "2560x1440";
	if (NativeCall("Fits:1920x1080")) return "1920x1080";
	if (NativeCall("Fits:1600x900")) return "1600x900";
	if (NativeCall("Fits:1366x768")) return "1366x768";
	if (NativeCall("Fits:1280x720")) return "1280x720";
	return "1024x768";
}

// The launcher's FOV option is a key-binding hack ("W=MoveForward | OnRelease FOV 75"):
// it would reset the view every time the key is released. Take it off any key that has it.
static function RemoveLauncherFOV(PlayerController PC)
{
	local int i, j;
	local string Key, Bind;

	for (i = 1; i < 255; i++)
	{
		Key = PC.ConsoleCommand("KEYNAME " $ i);
		if (Key == "")
			continue;
		Bind = PC.ConsoleCommand("KEYBINDING " $ Key);
		j = InStr(Caps(Bind), "ONRELEASE FOV");
		if (j < 0)
			continue;
		Bind = Left(Bind, j);
		while (Bind != "" && (Right(Bind, 1) == " " || Right(Bind, 1) == "|"))
			Bind = Left(Bind, Len(Bind) - 1);
		PC.ConsoleCommand("set Input " $ Key $ " " $ Bind);
		Note("removed the launcher's FOV binding from key " $ Key $ " (now: " $ Bind $ ")");
	}
}

// called once, when the first menu opens: the window and the render device exist
static function Startup(PlayerController PC)
{
	local bool bReset;

	NativeCall("Init");
	RemoveLauncherFOV(PC);
	if (!default.bSaved)
	{
		default.bVSync = RenderBool(PC, "UseVSync");
		default.bTrilinear = RenderBool(PC, "UseTrilinear");
		default.bWidescreen = RenderBool(PC, "Widescreen");
		default.bSaved = true;
		StaticSaveConfig();
	}
	else
	{
		bReset = RenderBool(PC, "UseVSync") != default.bVSync || RenderBool(PC, "Widescreen") != default.bWidescreen;
		SetRenderBool(PC, "UseVSync", default.bVSync);
		SetRenderBool(PC, "UseTrilinear", default.bTrilinear);
		SetRenderBool(PC, "Widescreen", default.bWidescreen);
		if (bReset)
			ResetDevice(PC);
	}
	if (default.bBorderless && !IsFullscreen(PC))
		NativeCall("BorderlessOn");
}

defaultproperties
{
     bTrilinear=True
     FOV=75
     DebugMovers=-1
     bWidescreen=True
}
