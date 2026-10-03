//=============================================================================
// ModDisplayOptions - "Display Options", opened from the Video Options page:
// the launcher settings the game's own menus never had, a row that opens the
// Graphics page (ModGraphicsOptions), and colourblind mode (a correction filter
// in the U2Shaders layer's last pass, with its strength).
//=============================================================================
class ModDisplayOptions extends MenuPauseOptionsBase;

var localized string LstrWidescreen, LstrTrilinear, LstrFOV, LstrMinFrameRate, LstrGraphics, LstrOpen;
var localized string LstrColorblind, LstrColorblindStrength;
var localized string ColorblindNames[4];
var bool bOpenGraphics;

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 4;
	NumSliders = 3;
	Labels[0].Caption = LstrWidescreen;
	Labels[1].Caption = LstrTrilinear;
	Labels[2].Caption = LstrGraphics;
	Labels[3].Caption = LstrColorblind;
	Labels[4].Caption = LstrFOV;
	Labels[5].Caption = LstrMinFrameRate;
	Labels[6].Caption = LstrColorblindStrength;
	Button0.bActNormal = true;
	Button0.OnClick = WidescreenClick;
	Button1.bActNormal = true;
	Button1.OnClick = TrilinearClick;
	Button2.bActNormal = true;
	Button2.OnClick = GraphicsClick;
	Button3.bActNormal = true;
	Button3.OnClick = ColorblindClick;
	Slider0.MinValue = 60;
	Slider0.MaxValue = 120;
	Slider0.bIntSlider = true;
	Slider0.OnChange = FOVChange;
	Slider1.MinValue = 0;
	Slider1.MaxValue = 60;
	Slider1.bIntSlider = true;
	Slider1.OnChange = FrameRateChange;
	Slider2.MinValue = 0;
	Slider2.MaxValue = 100;
	Slider2.bIntSlider = true;
	Slider2.OnChange = ColorblindStrengthChange;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Slider0.SetAssociatedLabel(Labels[4]);
	Slider1.SetAssociatedLabel(Labels[5]);
	Slider2.SetAssociatedLabel(Labels[6]);
	Button2.Caption = LstrOpen;
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
	{
		SetWidescreen(true);
		SetTrilinear(true);
		Slider0.SetValue(75);
		FOVChange(self);
		Slider1.SetValue(30);
		FrameRateChange(self);
		class'ModSettings'.static.ApplyColorblind(0, 1.0);
	}
	else
	{
		Slider0.SetValue(class'ModSettings'.default.FOV);
		Slider1.SetValue(float(GetPC().ConsoleCommand("get WinDrv.WindowsClient MinDesiredFrameRate")));
	}
	Button0.SetValueB(class'ModSettings'.default.bWidescreen);
	Button1.SetValueB(class'ModSettings'.default.bTrilinear);
	Slider2.SetValue(int(class'ModSettings'.default.ColorblindStrength * 100.0 + 0.5));
	ShowValues();
}

function ShowValues()
{
	Labels[4].Caption = LstrFOV $ ": " $ int(Slider0.Value);
	Labels[5].Caption = LstrMinFrameRate $ ": " $ int(Slider1.Value);
	Labels[6].Caption = LstrColorblindStrength $ ": " $ int(Slider2.Value) $ "%";
	Button3.Caption = ColorblindNames[Clamp(class'ModSettings'.default.Colorblind, 0, 3)];
}

// off, protanopia, deuteranopia, tritanopia
function bool ColorblindClick(GUIComponent Sender)
{
	class'ModSettings'.static.ApplyColorblind((class'ModSettings'.default.Colorblind + 1) % 4, class'ModSettings'.default.ColorblindStrength);
	ShowValues();
	return false;
}

function ColorblindStrengthChange(GUIComponent Sender)
{
	class'ModSettings'.static.ApplyColorblind(class'ModSettings'.default.Colorblind, Slider2.Value / 100.0);
	ShowValues();
}

// applies at once (the game is paused here, so ModMutator's timer isn't running)
function FOVChange(GUIComponent Sender)
{
	class'ModSettings'.default.FOV = int(Slider0.Value);
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.ApplyFOV(GetPC());
	ShowValues();
}

function SetWidescreen(bool bOn)
{
	if (class'ModSettings'.default.bWidescreen == bOn)
		return;
	class'ModSettings'.default.bWidescreen = bOn;
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.SetRenderBool(GetPC(), "Widescreen", bOn);
	class'ModSettings'.static.ResetDevice(GetPC());
}

function SetTrilinear(bool bOn)
{
	if (class'ModSettings'.default.bTrilinear == bOn)
		return;
	class'ModSettings'.default.bTrilinear = bOn;
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.SetRenderBool(GetPC(), "UseTrilinear", bOn);
	GetPC().ConsoleCommand("FLUSH");
}

function bool WidescreenClick(GUIComponent Sender)
{
	SetWidescreen(!class'ModSettings'.default.bWidescreen);
	Button0.SetValueB(class'ModSettings'.default.bWidescreen);
	return false;
}

function bool TrilinearClick(GUIComponent Sender)
{
	SetTrilinear(!class'ModSettings'.default.bTrilinear);
	Button1.SetValueB(class'ModSettings'.default.bTrilinear);
	return false;
}

function bool GraphicsClick(GUIComponent Sender)
{
	bOpenGraphics = true;
	bFadedOut = true;
	curState = MENU_STATE_EXIT;
	return false;
}

simulated function Timer()
{
	if (bLoadNextMenu && bOpenGraphics)
	{
		// the page has faded out: show the next one (the base class would open its reset prompt)
		bLoadNextMenu = false;
		bOpenGraphics = false;
		// by class, not by string: see ModGUIController.OpenMenu
		Controller.OpenMenu(string(class'ModGraphicsOptions'));
		curState = MENU_STATE_IDLE;
	}
	Super.Timer();
}

// the game saves this one itself (WinDrv.WindowsClient, in Mydefault.ini)
function FrameRateChange(GUIComponent Sender)
{
	GetPC().ConsoleCommand("set WinDrv.WindowsClient MinDesiredFrameRate " $ int(Slider1.Value));
	ShowValues();
}

defaultproperties
{
     LstrLabelTitle="Display Options"
     LstrWidescreen="Widescreen"
     LstrTrilinear="Trilinear Filtering"
     LstrFOV="Field of View"
     LstrMinFrameRate="Minimum Frame Rate"
     LstrGraphics="Graphics (shadows, post effects)"
     LstrOpen="Open"
     LstrColorblind="Colorblind Mode"
     LstrColorblindStrength="Colorblind Correction"
     ColorblindNames(0)="Off"
     ColorblindNames(1)="Protanopia"
     ColorblindNames(2)="Deuteranopia"
     ColorblindNames(3)="Tritanopia"
}
