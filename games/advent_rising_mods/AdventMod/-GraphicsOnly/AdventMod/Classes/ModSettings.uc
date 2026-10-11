//=============================================================================
// ModSettings - AdventMod's saved settings (System\AdventMod.ini), helpers for
// the engine's own settings, and the bridge to AdventNative.dll:
// NativeCall("Command") is a DynamicLoadObject on "AdventNative.Command",
// which the DLL answers (non-None = true).
//=============================================================================
class ModSettings extends Object
	config(AdventMod);

var config bool bBorderless;
var config bool bScreenModeSet;       // 2.1: borderless fullscreen became the default once (an older ini says bBorderless=False)
// the render device never saves these itself, so we keep them and re-apply at start
var config bool bSaved;
var config bool bVSync, bTrilinear, bWidescreen;
var config int FOV;                   // the third-person camera's field of view (the game's own is 75)
var config bool bDebugFOV;            // testing: note every FOV change in AdventNative.log
var int DebugMovers;
var config bool bShadowProbe;         // testing: run ShadowProbe on the player in a level
var config bool bShadowFix;           // character shadows: Engine.dll's sky pass ate them, and the shadow bitmaps lost their alpha (shadowfix.c, shadowalpha.c)
var config bool bNoGamePostFx;        // remove the game's own camera effects (blurs, distortion, DOF) every frame: the Direct3D layer's post effects replace them
var config bool bSoftShadows;         // multi-light character shadows (ModShadowManager, ported from U2SoftShadows)
var bool bStartedUp;                  // Startup has run (once per run of the game)
var config bool bGraphicsOnly;        // the AdventGraphicalMod build: no gore, armour or combat changes (ModMutator never spawns ModGore); build.ps1 -GraphicsOnly flips the default
var config bool bPadDriftFix;         // ignore stuck gamepad camera axes: the camera spinning on its own with a pad or receiver connected (ModInput)
var config float PadCentre;           // an axis counts once it has been this close to the centre
var config float StuckTime;           // an axis frozen off-centre this long (seconds) stops counting
var config float DebugStuckTurn;      // testing: add a phantom axis value to the camera turn
var config bool bRawMouse;            // mouse look without the engine's smoothing and slow-speed damping (ModInput)
var config float MouseTurnRate;       // raw mouse: camera degrees per second for one unit of mouse speed (after the game's sensitivity)
var config bool bCombatPickupFilter;  // no lock-on to weapons on the ground during a fight, unless at your feet (ModTargeting)
var config float CombatRange;         // a hostile this close (unreal units, 1 m = ~52) means a fight
var config float PickupReach;         // weapons this close stay targetable in a fight
var config bool bTargetLog;           // testing: log the lock-on target as it changes
var config bool bDebugCombat;         // testing: ModTargeting acts as if a hostile were near
var config float DamageDealt;         // Gameplay page: damage you deal, on top of the difficulty (ModTargeting)
var config float DamageTaken;         // damage you take
var config float BossDamageDealt;     // ...and on top of those while a boss is alive near you
var config float BossDamageTaken;
var config float ExploreSpeed;        // running speed while no enemy is near (ModInput)
var bool bInCombat;                   // a hostile within CombatRange (ModTargeting, twice a second)
var config bool bGoreLog;             // testing: log every hit and blood mark (ModGore)
var config string DebugDecalTexture;  // testing: every blood mark with this texture instead
var config bool bFpsGraph;            // the frame-time graph overlay (ModFpsGraph); on by default since 10-10 (user)
var config bool bGizmos;              // debug lines on the player (ModGizmos); "mutate gizmos" toggles
var config bool bJumpLog;             // testing: log every jump (ModInput)
var config bool bMouseLog;            // testing: log how much of the mouse movement the engine's curve keeps
var config int PostPreset;            // post-processing look (ModGraphicsOptions): 0 off, 1 Natural, 2 Cinematic, 3 Gritty, 4 Clean
var config float Sharpen;             // CAS sharpening 0..1 (the preset sets it; the Graphics page slider changes it)
var config bool bSMAA;                // the layer's SMAA anti-aliasing
var config int GiLevel;               // the layer's global illumination (gi.hlsl): 0 off, 1 on, 2 strong
var config bool bAmbientOcclusion;    // the layer's screen-space ambient occlusion (ssao.hlsl)
var config int Colorblind;            // colourblind correction in the U2Shaders layer: 0 off, 1 protanopia, 2 deuteranopia, 3 tritanopia
var config float ColorblindStrength;  // 0..1
var config int MaxFps;                // frame cap: -1 = the monitor's refresh rate, 0 = none (uncapped the GPU draws ~300 fps nobody sees)
var config bool bD3DTrace;            // testing: trace Direct3D calls (AdventNative d3dtrace.c) into AdventNative.log
var config string DebugLevelMenu;     // testing: a menu class ModMutator opens DebugMenuDelay seconds into a level,
var config string DebugLevelCommands; // testing: commands run DebugMenuDelay seconds into a level (RunCommands steps; a
                                      // step written "in:MAP:step" runs only in the map called MAP), e.g. a save load chain
var config float DebugMenuDelay;      // then takes a screenshot (console "shot") 4 seconds later
var config string DebugCommands;      // testing: console commands (separated by |) run on the title screen, results in AdventNative.log
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

// a float as U2Shaders.ini wants it ("0.4", not "0.40")
static function string Num(float F)
{
	local string S;

	S = string(F);
	if (InStr(S, ".") >= 0)
		while (Right(S, 1) == "0")
			S = Left(S, Len(S) - 1);
	if (Right(S, 1) == ".")
		S = Left(S, Len(S) - 1);
	return S;
}

// the post-processing presets of the Graphics page, written to System\U2Shaders.ini (the
// Direct3D layer picks them up at once). grade = saturation contrast exposure vignette,
// postfx = chromatic aberration, film grain, dither, highlight shoulder
static function ApplyPostPreset(int N)
{
	local string Bloom, Grade, Colour, Fx, Lut;
	local float Sharp;

	default.PostPreset = N;
	switch (N)
	{
	case 0:
		if (default.Colorblind == 0)
		{
			NativeCall("U2Set:post=0");
			StaticSaveConfig();
			return;
		}
		// colourblind mode lives in the post pass: keep the pass, with every effect off
		Bloom = "0.75 0"; Grade = "1.0 1.0 1.0 0.0"; Colour = "1 1 1"; Fx = "0 0 0 1"; Lut = "lut_neutral.bmp"; Sharp = 0;
		break;
	case 2:   // Cinematic: more bloom and vignette, warmer, more grain
		Bloom = "0.55 0.8"; Grade = "1.05 1.08 1.0 0.45"; Colour = "1.02 1 0.97"; Fx = "0.0025 0.035 1 0.7"; Lut = "lut_advent.bmp"; Sharp = 0.3;
		break;
	case 3:   // Gritty: desaturated, harder contrast, heavy grain
		Bloom = "0.7 0.35"; Grade = "0.75 1.15 0.95 0.5"; Colour = "1.03 1 0.94"; Fx = "0.001 0.05 1 0.72"; Lut = "lut_neutral.bmp"; Sharp = 0.5;
		break;
	case 4:   // Clean: no film effects, neutral colour
		Bloom = "0.75 0.3"; Grade = "1.0 1.0 1.0 0.0"; Colour = "1 1 1"; Fx = "0 0 1 0.8"; Lut = "lut_neutral.bmp"; Sharp = 0.35;
		break;
	default:  // 1 Natural: the tested look
		N = 1;
		Bloom = "0.6 0.5"; Grade = "1.0 1.0 1.0 0.25"; Colour = "1 1 1"; Fx = "0.0015 0.02 1 0.76"; Lut = "lut_advent.bmp"; Sharp = 0.4;
	}
	// (assigned after the switch: inside it, "default." starting a statement reads as the default: label)
	default.PostPreset = N;
	default.Sharpen = Sharp;
	NativeCall("U2Set:post=1");
	NativeCall("U2Set:bloom=" $ Bloom);
	NativeCall("U2Set:grade=" $ Grade);
	NativeCall("U2Set:colour=" $ Colour);
	NativeCall("U2Set:sharpen=" $ Num(default.Sharpen));
	NativeCall("U2Set:postfx=" $ Fx);
	NativeCall("U2Set:lut=" $ Lut);
	StaticSaveConfig();
}

// global illumination (radiance cascades and a world cache in the Direct3D layer): bounce
// light and darker corners. It runs in the post pass, so "Post Effects: Off" switches it off too.
// gifx = bounce strength, corner darkening, reach, debug view; gilights = how much the
// game's own lamps light the world cache, how many lamps (measured 2026-10-05: below
// strength ~2 the bounce can't be told from no GI in a dark room; 2.5 + lamps 0.4 washed the
// outdoors out for the user (2026-10-05), so On sits below that and Strong is the old On)
static function ApplyGi(int Level)
{
	Level = Clamp(Level, 0, 2);
	default.GiLevel = Level;
	if (Level == 2)
	{
		NativeCall("U2Set:gifx=2.5 0.7 300 0");
		NativeCall("U2Set:gilights=0.4 16");
	}
	else
	{
		NativeCall("U2Set:gifx=1.5 0.6 300 0");
		NativeCall("U2Set:gilights=0.25 16");
	}
	NativeCall("U2Set:gi=" $ int(Level > 0));
	StaticSaveConfig();
}

// colourblind mode: the type (0 off) and the correction's strength (0..1)
// ambient occlusion (ssao.hlsl): radius 150 units and intensity 3 suit Advent's scale (the
// layer's own defaults, 40 and 1, are for Unreal II's smaller rooms and barely showed here)
static function ApplyAo(bool bOn)
{
	default.bAmbientOcclusion = bOn;
	NativeCall("U2Set:ssaofx=0.8 150 3 0");
	NativeCall("U2Set:ssao=" $ int(bOn));
	StaticSaveConfig();
}

static function ApplyColorblind(int Type, float Strength)
{
	local bool bWasOn;

	bWasOn = default.Colorblind != 0;
	default.Colorblind = Clamp(Type, 0, 3);
	default.ColorblindStrength = FClamp(Strength, 0, 1);
	NativeCall("U2Set:colorblind=" $ default.Colorblind $ " " $ Num(default.ColorblindStrength));
	// with post effects off, the pass has to run (or stop) for it
	if (default.PostPreset == 0 && bWasOn != (default.Colorblind != 0))
		ApplyPostPreset(0);
	StaticSaveConfig();
}

// called once per run of the game, by ModMutator in the first level (the title): the
// window and the render device exist
// testing: the steps of the game's own Load Game path, so the harness can replay a save load:
// "slot:N" makes slot N (0-based) the active one, "travel:URL" loads it the way MenuFade does
// (checkpoint restore on). Returns false for anything else.
static function bool DebugStep(PlayerController PC, string Cmd)
{
	if (Left(Cmd, 5) ~= "slot:")
	{
		PC.SetActiveSlotIndex(int(Mid(Cmd, 5)));
		Note(Cmd $ " => active slot set");
		return true;
	}
	if (Left(Cmd, 7) ~= "travel:")
	{
		PC.bRestoringCheckPointMutex = true;
		PC.Level.bPendingLoadCheckPoint = false;
		Note(Cmd $ " => ServerTravel with checkpoint restore");
		PC.Level.ServerTravel(Mid(Cmd, 7), false);
		return true;
	}
	return false;
}

static function Startup(PlayerController PC)
{
	local bool bReset;

	if (default.bStartedUp || PC == None)
		return;
	default.bStartedUp = true;
	NativeCall("Init");
	if (default.bShadowFix)
	{
		NativeCall("ShadowFix");
		NativeCall("ShadowAlpha");
	}
	if (default.bD3DTrace)
		NativeCall("D3DTrace");
	// ModInput (stuck gamepad axes ignored; the test pilot's keys) on the player controllers of
	// the levels to come: a class reference (not a console "set", which can't resolve a class it
	// hasn't loaded yet), on Advent's controller class too: it keeps its own copy of the default
	class'PlayerController'.default.InputClass = class'ModInput';
	class'EonPlayerController'.default.InputClass = class'ModInput';
	if (PC.PlayerInput == None || PC.PlayerInput.Class != class'ModInput')
	{
		PC.InputClass = class'ModInput';
		PC.InitInputSystem();
	}
	Note("input class set to " $ class'EonPlayerController'.default.InputClass);
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
	if (!default.bScreenModeSet)
	{
		default.bScreenModeSet = true;
		default.bBorderless = true;
		StaticSaveConfig();
	}
	if (default.bBorderless)
	{
		// borderless fullscreen instead of the engine's exclusive mode (the launcher's "fullscreen")
		if (IsFullscreen(PC))
			PC.ConsoleCommand("ENDFULLSCREEN");
		NativeCall("BorderlessOn");
	}
}

defaultproperties
{
     bFpsGraph=True
     bGizmos=False
     bShadowFix=True
     bSoftShadows=True
     bNoGamePostFx=True
     bTrilinear=True
     FOV=75
     MaxFps=-1
     ColorblindStrength=1.000000
     bGraphicsOnly=False
     bPadDriftFix=True
     PadCentre=0.100000
     StuckTime=1.500000
     bRawMouse=True
     MouseTurnRate=80.000000
     bCombatPickupFilter=True
     DamageDealt=1.000000
     DamageTaken=1.000000
     BossDamageDealt=1.000000
     BossDamageTaken=1.000000
     ExploreSpeed=1.250000
     CombatRange=2500.000000
     PickupReach=250.000000
     PostPreset=1
     Sharpen=0.400000
     bSMAA=True
     DebugMovers=-1
     bWidescreen=True
}
