//=============================================================================
// ModQualityOptions - "Quality" (one press from Options): the game's own detail settings
// that lived on its PC Graphics page (dynamic lights, distortion effects, draw and fog
// distance; projectors are kept on, the mod's shadows need them) with the launcher's
// Widescreen, Trilinear Filtering and Minimum Frame Rate. The game's settings apply when
// the page closes (SetPCOptions), ours at once.
//=============================================================================
class ModQualityOptions extends MenuPauseOptionsBase;

var localized string LstrDynamicLights, LstrDistortion, LstrWidescreen, LstrTrilinear, LstrDrawDistance, LstrFogDistance, LstrMinFrameRate;

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 4;
	NumSliders = 3;
	GetPC().GetPCOptions(Controller.PCOptionsData);     // the game's current settings (the hub loads them too)
	Labels[0].Caption = LstrDynamicLights;
	Labels[1].Caption = LstrDistortion;
	Labels[2].Caption = LstrWidescreen;
	Labels[3].Caption = LstrTrilinear;
	Labels[4].Caption = LstrDrawDistance;
	Labels[5].Caption = LstrFogDistance;
	Labels[6].Caption = LstrMinFrameRate;
	Button2.bActNormal = true;
	Button2.OnClick = WidescreenClick;
	Button3.bActNormal = true;
	Button3.OnClick = TrilinearClick;
	Slider2.MinValue = 0;
	Slider2.MaxValue = 60;
	Slider2.bIntSlider = true;
	Slider2.OnChange = FrameRateChange;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Slider0.SetAssociatedLabel(Labels[4]);
	Slider1.SetAssociatedLabel(Labels[5]);
	Slider2.SetAssociatedLabel(Labels[6]);
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
	{
		Button0.SetValueB(true);
		Button1.SetValueB(true);
		Slider0.SetValue(1.0);
		Slider1.SetValue(1.0);
		SetWidescreen(true);
		SetTrilinear(true);
		Slider2.SetValue(30);
		FrameRateChange(self);
	}
	else
	{
		Button0.SetValue(Controller.PCOptionsData.DynamicLights);
		Button1.SetValue(Controller.PCOptionsData.Distortion);
		Slider0.SetValue((Controller.PCOptionsData.ClipPlane - 0.5) / 3.5);
		Slider1.SetValue((Controller.PCOptionsData.CullDistance - 0.5) / 3.5);
		Slider2.SetValue(float(GetPC().ConsoleCommand("get WinDrv.WindowsClient MinDesiredFrameRate")));
	}
	Button2.SetValueB(class'ModSettings'.default.bWidescreen);
	Button3.SetValueB(class'ModSettings'.default.bTrilinear);
	ShowValues();
}

function ShowValues()
{
	Labels[6].Caption = LstrMinFrameRate $ ": " $ int(Slider2.Value);
}

// the game's own settings, as its Graphics page applied them
function UpdateLocalGameOptions()
{
	Controller.PCOptionsData.DynamicLights = Button0.GetValue();
	Controller.PCOptionsData.Distortion = Button1.GetValue();
	Controller.PCOptionsData.Projectors = 1;
	Controller.PCOptionsData.ClipPlane = Slider0.Value * 3.5 + 0.5;
	Controller.PCOptionsData.CullDistance = Slider1.Value * 3.5 + 0.5;
	GetPC().SetPCOptions(Controller.PCOptionsData);
	GetPC().GetPCOptions(Controller.PCOptionsData);
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
	Button2.SetValueB(class'ModSettings'.default.bWidescreen);
	return false;
}

function bool TrilinearClick(GUIComponent Sender)
{
	SetTrilinear(!class'ModSettings'.default.bTrilinear);
	Button3.SetValueB(class'ModSettings'.default.bTrilinear);
	return false;
}

// the game saves this one itself (WinDrv.WindowsClient, in Mydefault.ini)
function FrameRateChange(GUIComponent Sender)
{
	GetPC().ConsoleCommand("set WinDrv.WindowsClient MinDesiredFrameRate " $ int(Slider2.Value));
	ShowValues();
}

defaultproperties
{
     LstrLabelTitle="Quality"
     LstrDynamicLights="Dynamic Lights"
     LstrDistortion="Distortion Effects"
     LstrWidescreen="Widescreen"
     LstrTrilinear="Trilinear Filtering"
     LstrDrawDistance="Draw Distance"
     LstrFogDistance="Fog Distance"
     LstrMinFrameRate="Minimum Frame Rate"
}
