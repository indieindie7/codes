//=============================================================================
// ModGraphicsOptions - "Graphics", opened from the Display Options page: the
// look the U2Shaders Direct3D layer adds (post-processing presets, anti-aliasing)
// and AdventMod's shadows and frame cap. Everything applies at once: the layer
// re-reads System\U2Shaders.ini while the game runs (written through AdventNative),
// and the shadow settings are picked up by ModMutator / ModShadowManager.
//=============================================================================
class ModGraphicsOptions extends MenuPauseOptionsBase;

var localized string LstrPost, LstrSoftShadows, LstrNpcShadows, LstrAA, LstrFrameCap, LstrShadowDark, LstrSharpen;
var localized string LstrMonitor, LstrNoCap;
var localized string PresetNames[5];
var int FrameCaps[6];

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 5;
	NumSliders = 2;
	Labels[0].Caption = LstrPost;
	Labels[1].Caption = LstrSoftShadows;
	Labels[2].Caption = LstrNpcShadows;
	Labels[3].Caption = LstrAA;
	Labels[4].Caption = LstrFrameCap;
	Labels[5].Caption = LstrShadowDark;
	Labels[6].Caption = LstrSharpen;
	Button0.bActNormal = true;
	Button0.OnClick = PostClick;
	Button1.bActNormal = true;
	Button1.OnClick = SoftShadowsClick;
	Button2.bActNormal = true;
	Button2.OnClick = NpcShadowsClick;
	Button3.bActNormal = true;
	Button3.OnClick = AAClick;
	Button4.bActNormal = true;
	Button4.OnClick = FrameCapClick;
	Slider0.MinValue = 0;
	Slider0.MaxValue = 100;
	Slider0.bIntSlider = true;
	Slider0.OnChange = ShadowDarkChange;
	Slider1.MinValue = 0;
	Slider1.MaxValue = 100;
	Slider1.bIntSlider = true;
	Slider1.OnChange = SharpenChange;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Slider0.SetAssociatedLabel(Labels[5]);
	Slider1.SetAssociatedLabel(Labels[6]);
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
	{
		class'ModSettings'.static.ApplyPostPreset(1);
		SetSoftShadows(true);
		SetNpcShadows(true);
		SetAA(true);
		class'ModSettings'.default.MaxFps = -1;
		class'ModSettings'.static.StaticSaveConfig();
		SetShadowDark(70);
	}
	Slider0.SetValue(int(class'ModShadowController'.default.ShadowStrength * 100.0 / 255.0 + 0.5));
	Slider1.SetValue(int(class'ModSettings'.default.Sharpen * 100.0 + 0.5));
	Refresh();
}

// the buttons that cycle through values show the value instead of On/Off
function Refresh()
{
	local int i;

	Button0.Caption = PresetNames[Clamp(class'ModSettings'.default.PostPreset, 0, 4)];
	Button1.SetValueB(class'ModSettings'.default.bSoftShadows);
	Button2.SetValueB(class'ModShadowManager'.default.NpcShadows > 0);
	Button3.SetValueB(class'ModSettings'.default.bSMAA);
	i = class'ModSettings'.default.MaxFps;
	if (i < 0)
		Button4.Caption = LstrMonitor;
	else if (i == 0)
		Button4.Caption = LstrNoCap;
	else
		Button4.Caption = string(i);
	Labels[5].Caption = LstrShadowDark $ ": " $ int(Slider0.Value) $ "%";
	Labels[6].Caption = LstrSharpen $ ": " $ int(Slider1.Value) $ "%";
}

function bool PostClick(GUIComponent Sender)
{
	class'ModSettings'.static.ApplyPostPreset((class'ModSettings'.default.PostPreset + 1) % 5);
	Slider1.SetValue(int(class'ModSettings'.default.Sharpen * 100.0 + 0.5));
	Refresh();
	return false;
}

function SetSoftShadows(bool bOn)
{
	class'ModSettings'.default.bSoftShadows = bOn;
	class'ModSettings'.static.StaticSaveConfig();
}

function bool SoftShadowsClick(GUIComponent Sender)
{
	SetSoftShadows(!class'ModSettings'.default.bSoftShadows);
	Refresh();
	return false;
}

function SetNpcShadows(bool bOn)
{
	class'ModShadowManager'.default.NpcShadows = 20 * int(bOn);
	class'ModShadowManager'.static.StaticSaveConfig();
}

function bool NpcShadowsClick(GUIComponent Sender)
{
	SetNpcShadows(class'ModShadowManager'.default.NpcShadows <= 0);
	Refresh();
	return false;
}

function SetAA(bool bOn)
{
	class'ModSettings'.default.bSMAA = bOn;
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.NativeCall("U2Set:smaa=" $ int(bOn));
}

function bool AAClick(GUIComponent Sender)
{
	SetAA(!class'ModSettings'.default.bSMAA);
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

// darkness of the characters' shadows; shadows already in the level follow at once
function SetShadowDark(int Pct)
{
	local ModLightShadow S;

	class'ModShadowController'.default.ShadowStrength = Pct * 255.0 / 100.0;
	class'ModShadowController'.static.StaticSaveConfig();
	foreach GetPC().DynamicActors(class'ModLightShadow', S)
		S.ShadowStrength = class'ModShadowController'.default.ShadowStrength;
	Slider0.SetValue(Pct);
}

function ShadowDarkChange(GUIComponent Sender)
{
	SetShadowDark(int(Slider0.Value));
	Refresh();
}

function SharpenChange(GUIComponent Sender)
{
	class'ModSettings'.default.Sharpen = Slider1.Value / 100.0;
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.NativeCall("U2Set:sharpen=" $ class'ModSettings'.static.Num(class'ModSettings'.default.Sharpen));
	Refresh();
}

defaultproperties
{
     LstrLabelTitle="Graphics"
     LstrPost="Post Effects"
     LstrSoftShadows="Soft Shadows"
     LstrNpcShadows="Shadows for Others"
     LstrAA="Anti-Aliasing (SMAA)"
     LstrFrameCap="Frame Cap"
     LstrShadowDark="Shadow Darkness"
     LstrSharpen="Sharpening"
     LstrMonitor="Monitor"
     LstrNoCap="None"
     PresetNames(0)="Off"
     PresetNames(1)="Natural"
     PresetNames(2)="Cinematic"
     PresetNames(3)="Gritty"
     PresetNames(4)="Clean"
     FrameCaps(0)=-1
     FrameCaps(1)=30
     FrameCaps(2)=60
     FrameCaps(3)=120
     FrameCaps(4)=144
     FrameCaps(5)=0
}
