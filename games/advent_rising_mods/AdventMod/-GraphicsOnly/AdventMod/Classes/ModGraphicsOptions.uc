//=============================================================================
// ModGraphicsOptions - "Graphics" (one press from Options): the look the U2Shaders Direct3D
// layer adds (post-processing presets, global illumination, anti-aliasing, sharpening) and
// AdventMod's shadows, plus the field of view. Everything applies at once: the layer
// re-reads System\U2Shaders.ini while the game runs (written through AdventNative), and the
// shadow settings are picked up by ModMutator / ModShadowManager.
//=============================================================================
class ModGraphicsOptions extends MenuPauseOptionsBase;

var localized string LstrPost, LstrSoftShadows, LstrGi, LstrAA, LstrShadowDark, LstrSharpen, LstrFOV;
var localized string ShadowNames[3];      // soft shadows: off, the player's, everyone's
var localized string GiNames[4];   // the ambient light row: off, occlusion, illumination (+occlusion), strong
var localized string PresetNames[5];

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 4;
	NumSliders = 3;
	Labels[0].Caption = LstrSoftShadows;
	Labels[1].Caption = LstrGi;
	Labels[2].Caption = LstrPost;
	Labels[3].Caption = LstrAA;
	Labels[4].Caption = LstrShadowDark;
	Labels[5].Caption = LstrSharpen;
	Labels[6].Caption = LstrFOV;
	Button0.bActNormal = true;
	Button0.OnClick = SoftShadowsClick;
	Button1.bActNormal = true;
	Button1.OnClick = GiClick;
	Button2.bActNormal = true;
	Button2.OnClick = PostClick;
	Button3.bActNormal = true;
	Button3.OnClick = AAClick;
	Slider0.MinValue = 0;
	Slider0.MaxValue = 100;
	Slider0.bIntSlider = true;
	Slider0.OnChange = ShadowDarkChange;
	Slider1.MinValue = 0;
	Slider1.MaxValue = 100;
	Slider1.bIntSlider = true;
	Slider1.OnChange = SharpenChange;
	Slider2.MinValue = 60;
	Slider2.MaxValue = 120;
	Slider2.bIntSlider = true;
	Slider2.OnChange = FOVChange;
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
		class'ModSettings'.static.ApplyPostPreset(1);
		SetShadows(2);
		class'ModSettings'.static.ApplyGi(0);
		SetAA(true);
		SetShadowDark(70);
		Slider2.SetValue(75);
		FOVChange(self);
	}
	Slider0.SetValue(int(class'ModShadowController'.default.ShadowStrength * 100.0 / 255.0 + 0.5));
	Slider1.SetValue(int(class'ModSettings'.default.Sharpen * 100.0 + 0.5));
	Slider2.SetValue(class'ModSettings'.default.FOV);
	Refresh();
}

// the buttons that cycle through values show the value instead of On/Off
function Refresh()
{
	Button0.Caption = ShadowNames[ShadowLevel()];
	Button1.Caption = GiNames[AmbientState()];
	Button2.Caption = PresetNames[Clamp(class'ModSettings'.default.PostPreset, 0, 4)];
	Button3.SetValueB(class'ModSettings'.default.bSMAA);
	Labels[4].Caption = LstrShadowDark $ ": " $ int(Slider0.Value) $ "%";
	Labels[5].Caption = LstrSharpen $ ": " $ int(Slider1.Value) $ "%";
	Labels[6].Caption = LstrFOV $ ": " $ int(Slider2.Value);
}

function bool PostClick(GUIComponent Sender)
{
	class'ModSettings'.static.ApplyPostPreset((class'ModSettings'.default.PostPreset + 1) % 5);
	Slider1.SetValue(int(class'ModSettings'.default.Sharpen * 100.0 + 0.5));
	Refresh();
	return false;
}

// soft shadows in one setting: 0 off, 1 the player's only, 2 everyone's
function int ShadowLevel()
{
	if (!class'ModSettings'.default.bSoftShadows)
		return 0;
	if (class'ModShadowManager'.default.NpcShadows > 0)
		return 2;
	return 1;
}

function SetShadows(int Level)
{
	class'ModSettings'.default.bSoftShadows = Level > 0;
	class'ModSettings'.static.StaticSaveConfig();
	class'ModShadowManager'.default.NpcShadows = 20 * int(Level > 1);
	class'ModShadowManager'.static.StaticSaveConfig();
}

function bool SoftShadowsClick(GUIComponent Sender)
{
	SetShadows((ShadowLevel() + 1) % 3);
	Refresh();
	return false;
}

// the ambient light row: 0 off, 1 occlusion only, 2 illumination with occlusion, 3 strong
function int AmbientState()
{
	if (class'ModSettings'.default.GiLevel > 0)
		return Clamp(class'ModSettings'.default.GiLevel, 1, 2) + 1;
	if (class'ModSettings'.default.bAmbientOcclusion)
		return 1;
	return 0;
}

function bool GiClick(GUIComponent Sender)
{
	local int S;

	S = (AmbientState() + 1) % 4;
	class'ModSettings'.static.ApplyAo(S > 0);
	class'ModSettings'.static.ApplyGi(Max(S - 1, 0));
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

// applies at once (the game is paused here, so ModMutator's timer isn't running)
function FOVChange(GUIComponent Sender)
{
	class'ModSettings'.default.FOV = int(Slider2.Value);
	class'ModSettings'.static.StaticSaveConfig();
	class'ModSettings'.static.ApplyFOV(GetPC());
	Refresh();
}

defaultproperties
{
     LstrLabelTitle="Graphics"
     LstrPost="Post Effects"
     LstrSoftShadows="Soft Shadows"
     LstrGi="Global Illumination"
     LstrAA="Anti-Aliasing (SMAA)"
     LstrShadowDark="Shadow Darkness"
     LstrSharpen="Sharpening"
     LstrFOV="Field of View"
     ShadowNames(0)="Off"
     ShadowNames(1)="Yours"
     ShadowNames(2)="Everyone's"
     GiNames(0)="Off"
     GiNames(1)="On"
     GiNames(2)="Strong"
     PresetNames(0)="Off"
     PresetNames(1)="Natural"
     PresetNames(2)="Cinematic"
     PresetNames(3)="Gritty"
     PresetNames(4)="Clean"
}
