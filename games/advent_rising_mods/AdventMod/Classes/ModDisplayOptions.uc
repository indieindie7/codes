//=============================================================================
// ModDisplayOptions - "Display Options", opened from the Video Options page:
// the launcher settings the game's own menus never had.
//=============================================================================
class ModDisplayOptions extends MenuPauseOptionsBase;

var localized string LstrWidescreen, LstrTrilinear, LstrFOV, LstrMinFrameRate;

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 2;
	NumSliders = 2;
	Labels[0].Caption = LstrWidescreen;
	Labels[1].Caption = LstrTrilinear;
	Labels[2].Caption = LstrFOV;
	Labels[3].Caption = LstrMinFrameRate;
	Button0.bActNormal = true;
	Button0.OnClick = WidescreenClick;
	Button1.bActNormal = true;
	Button1.OnClick = TrilinearClick;
	Slider0.MinValue = 60;
	Slider0.MaxValue = 120;
	Slider0.bIntSlider = true;
	Slider0.OnChange = FOVChange;
	Slider1.MinValue = 0;
	Slider1.MaxValue = 60;
	Slider1.bIntSlider = true;
	Slider1.OnChange = FrameRateChange;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Slider0.SetAssociatedLabel(Labels[2]);
	Slider1.SetAssociatedLabel(Labels[3]);
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
	}
	else
	{
		Slider0.SetValue(class'ModSettings'.default.FOV);
		Slider1.SetValue(float(GetPC().ConsoleCommand("get WinDrv.WindowsClient MinDesiredFrameRate")));
	}
	Button0.SetValueB(class'ModSettings'.default.bWidescreen);
	Button1.SetValueB(class'ModSettings'.default.bTrilinear);
	ShowValues();
}

function ShowValues()
{
	Labels[2].Caption = LstrFOV $ ": " $ int(Slider0.Value);
	Labels[3].Caption = LstrMinFrameRate $ ": " $ int(Slider1.Value);
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
}
