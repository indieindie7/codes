//=============================================================================
// ModScreenOptions - "Screen" (one press from Options): how the picture reaches the monitor.
// Resolution (the sizes that fit the screen, applied at once with the stock "keep this
// setting?" prompt), Fullscreen Mode (Window / Borderless / Exclusive, one row instead of
// two switches that fought each other), VSync, Frame Cap, and the game's own Brightness,
// Contrast and Gamma sliders.
//=============================================================================
class ModScreenOptions extends MenuPauseOptionsVideo;

var localized string LstrResolution, LstrFullscreen, LstrVSync, LstrFrameCap, LstrMonitor, LstrNoCap;
var localized string FullscreenNames[3];
var string Candidates[7];
var array<string> Sizes;       // the resolutions offered (ascending, the current one among them)
var int Size, OldSize;         // the one chosen, and the one before a change (for the prompt)
var int FrameCaps[6];

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	Super.PreSetInitalPositions();
	NumBools = 4;
	// rows are toggles first, then sliders: the stock slider captions move below ours
	Labels[6].Caption = Labels[2].Caption;
	Labels[5].Caption = Labels[1].Caption;
	Labels[4].Caption = Labels[0].Caption;
	Labels[0].Caption = LstrResolution;
	Labels[1].Caption = LstrFullscreen;
	Labels[2].Caption = LstrVSync;
	Labels[3].Caption = LstrFrameCap;
	Button0.bActNormal = true;
	Button0.OnClick = ResolutionClick;
	Button1.bActNormal = true;
	Button1.OnClick = FullscreenClick;
	Button2.bActNormal = true;
	Button2.OnClick = VSyncClick;
	Button3.bActNormal = true;
	Button3.OnClick = FrameCapClick;
}

function SetupInitalPositions()
{
	local int i;

	Super.SetupInitalPositions();
	for (i = 0; i < NumSliders; i++)
		Sliders[i].SetAssociatedLabel(Labels[NumBools + i]);
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	Super.SetLocalGuiOptions(Reset);
	if (Reset)
	{
		class'ModSettings'.default.MaxFps = -1;
		class'ModSettings'.static.StaticSaveConfig();
		class'ModSettings'.static.NativeCall("MaxFps:-1");
	}
	ListSizes();
	Refresh();
}

// the sizes that fit the screen, and whatever the game runs at now
function ListSizes()
{
	local int i;
	local string Cur;

	Sizes.Length = 0;
	for (i = 0; i < ArrayCount(Candidates); i++)
		if (class'ModSettings'.static.NativeCall("Fits:" $ Candidates[i]))
			Sizes[Sizes.Length] = Candidates[i];
	Cur = GetPC().ConsoleCommand("GETCURRENTRES");
	Size = -1;
	for (i = 0; i < Sizes.Length; i++)
		if (Sizes[i] ~= Cur)
			Size = i;
	if (Size < 0)
	{
		Sizes.Insert(0, 1);
		Sizes[0] = Cur;
		Size = 0;
	}
	OldSize = Size;
}

function int FullscreenMode()
{
	if (class'ModSettings'.static.IsFullscreen(GetPC()))
		return 2;
	if (class'ModSettings'.static.NativeCall("IsBorderless"))
		return 1;
	return 0;
}

function Refresh()
{
	local int i;

	if (Size >= 0 && Size < Sizes.Length)
		Button0.Caption = Sizes[Size];
	Button1.Caption = FullscreenNames[FullscreenMode()];
	Button2.SetValueB(class'ModSettings'.default.bVSync);
	i = class'ModSettings'.default.MaxFps;
	if (i < 0)
		Button3.Caption = LstrMonitor;
	else if (i == 0)
		Button3.Caption = LstrNoCap;
	else
		Button3.Caption = string(i);
}

// the next size, applied at once; the stock prompt then asks whether to keep it
function bool ResolutionClick(GUIComponent Sender)
{
	if (Sizes.Length < 2)
		return false;
	OldSize = Size;
	Size = (Size + 1) % Sizes.Length;
	GetPC().ConsoleCommand("SETRES " $ Sizes[Size]);
	Refresh();
	bResetResolution = true;
	Super.OnReset(None);
	return false;
}

// the prompt's answer (the base class calls this): 0 = back to the old size, 1 = keep
function ResetResolution(int Reset)
{
	if (Reset == 0)
	{
		Size = OldSize;
		GetPC().ConsoleCommand("SETRES " $ Sizes[Size]);
		Refresh();
	}
	else
		OldSize = Size;
}

// Window -> Borderless -> Exclusive
function bool FullscreenClick(GUIComponent Sender)
{
	local string Best;

	switch ((FullscreenMode() + 1) % 3)
	{
	case 0:
		if (class'ModSettings'.static.IsFullscreen(GetPC()))
			GetPC().ConsoleCommand("ENDFULLSCREEN");
		class'ModSettings'.static.SetBorderless(false);
		break;
	case 1:
		if (class'ModSettings'.static.IsFullscreen(GetPC()))
			GetPC().ConsoleCommand("ENDFULLSCREEN");
		class'ModSettings'.static.SetBorderless(true);
		break;
	case 2:
		class'ModSettings'.static.SetBorderless(false);
		// the engine's own switch (what Alt+Enter does), at the screen's size instead of the saved 800x600
		Best = class'ModSettings'.static.BestResolution();
		GetPC().ConsoleCommand("set WinDrv.WindowsClient FullscreenViewportX " $ Left(Best, InStr(Best, "x")));
		GetPC().ConsoleCommand("set WinDrv.WindowsClient FullscreenViewportY " $ Mid(Best, InStr(Best, "x") + 1));
		GetPC().ConsoleCommand("TOGGLEFULLSCREEN");
		break;
	}
	Refresh();
	return false;
}

function bool VSyncClick(GUIComponent Sender)
{
	class'ModSettings'.default.bVSync = !class'ModSettings'.default.bVSync;
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.SetRenderBool(GetPC(), "UseVSync", class'ModSettings'.default.bVSync);
	class'ModSettings'.static.ResetDevice(GetPC());
	Refresh();
	return false;
}

// monitor refresh rate, 30, 60, 120, 144, no cap (ModMutator applies it)
function bool FrameCapClick(GUIComponent Sender)
{
	local int i;

	for (i = 0; i < 6; i++)
		if (FrameCaps[i] == class'ModSettings'.default.MaxFps)
			break;
	class'ModSettings'.default.MaxFps = FrameCaps[(i + 1) % 6];
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.NativeCall("MaxFps:" $ class'ModSettings'.default.MaxFps);
	Refresh();
	return false;
}

defaultproperties
{
     LstrLabelTitle="Screen"
     LstrResolution="Resolution"
     LstrFullscreen="Fullscreen Mode"
     LstrVSync="VSync"
     LstrFrameCap="Frame Cap"
     LstrMonitor="Monitor"
     LstrNoCap="None"
     FullscreenNames(0)="Window"
     FullscreenNames(1)="Borderless"
     FullscreenNames(2)="Exclusive"
     Candidates(0)="1024x768"
     Candidates(1)="1280x720"
     Candidates(2)="1366x768"
     Candidates(3)="1600x900"
     Candidates(4)="1920x1080"
     Candidates(5)="2560x1440"
     Candidates(6)="3840x2160"
     FrameCaps(0)=-1
     FrameCaps(1)=30
     FrameCaps(2)=60
     FrameCaps(3)=120
     FrameCaps(4)=144
     FrameCaps(5)=0
}
