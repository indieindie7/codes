//=============================================================================
// ModAccessibilityOptions - "Accessibility" (one press from Options): comfort settings.
// Blood (ModGore), colourblind mode (a correction filter in the U2Shaders layer's last pass,
// with its strength and a swatch preview), and the game's own Fading HUD, Slow-Mo Weapon
// Select, Auto Aiming and Toggle Crouch switches (Controller.OptionsData, saved when Options
// closes).
//=============================================================================
class ModAccessibilityOptions extends MenuPauseOptionsBase;

var localized string LstrBlood, LstrColorblind, LstrHudFade, LstrWeaponSelect, LstrAutoAim, LstrCrouch, LstrColorblindStrength;
var localized string ColorblindNames[4];
var array<GUIImage> Swatches;          // colourblind preview: the palette, and under it the palette as corrected
var array<color> Palette;

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 6;
	NumSliders = 1;
	Labels[0].Caption = LstrBlood;
	Labels[1].Caption = LstrColorblind;
	Labels[2].Caption = LstrHudFade;
	Labels[3].Caption = LstrWeaponSelect;
	Labels[4].Caption = LstrAutoAim;
	Labels[5].Caption = LstrCrouch;
	Labels[6].Caption = LstrColorblindStrength;
	Button0.bActNormal = true;
	Button0.OnClick = BloodClick;
	Button1.bActNormal = true;
	Button1.OnClick = ColorblindClick;
	Slider0.MinValue = 0;
	Slider0.MaxValue = 100;
	Slider0.bIntSlider = true;
	Slider0.OnChange = ColorblindStrengthChange;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Slider0.SetAssociatedLabel(Labels[6]);
	class'ModPanel'.static.AddTo(self);
	AddSwatches();
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
	{
		class'ModGore'.default.bBlood = true;
		class'ModGore'.static.StaticSaveConfig();
		class'ModSettings'.static.ApplyColorblind(0, 1.0);
		Button2.SetValueB(true);
		Button3.SetValueB(false);
		Button4.SetValueB(false);
		Button5.SetValueB(false);
	}
	else
	{
		Button2.SetValue(Controller.OptionsData.HudFade);
		Button3.SetValue(Controller.OptionsData.WeaponSelectMode);
		Button4.SetValue(Controller.OptionsData.AutoAimMode);
		Button5.SetValue(Controller.OptionsData.CrouchMode);
	}
	Slider0.SetValue(int(class'ModSettings'.default.ColorblindStrength * 100.0 + 0.5));
	ShowValues();
}

function UpdateLocalGameOptions()
{
	Controller.OptionsData.HudFade = Button2.GetValue();
	Controller.OptionsData.WeaponSelectMode = Button3.GetValue();
	Controller.OptionsData.AutoAimMode = Button4.GetValue();
	Controller.OptionsData.CrouchMode = Button5.GetValue();
}

function ShowValues()
{
	Button0.SetValueB(class'ModGore'.default.bBlood);
	Button1.Caption = ColorblindNames[Clamp(class'ModSettings'.default.Colorblind, 0, 3)];
	Labels[6].Caption = LstrColorblindStrength $ ": " $ int(Slider0.Value) $ "%";
	UpdateSwatches();
}

// right of the Colorblind Mode row: a strip of colours as they are (top), and as the
// selected correction will show them (bottom). Menus are drawn after the U2Shaders pass,
// so the bottom row is computed here, with post_final.hlsl's Daltonize.
function AddSwatches()
{
	local int i, Row;
	local GUIImage S;

	for (Row = 0; Row < 2; Row++)
		for (i = 0; i < Palette.Length; i++)
		{
			S = new(None) class'GUIImage';
			S.Image = Texture'Engine.WhiteSquareTexture';
			S.ImageStyle = ISTY_Stretched;
			S.ImageRenderStyle = MSTY_Normal;
			S.WinLeft = 0.655 + i * 0.022;
			S.WinWidth = 0.019;
			S.WinTop = LinePositions[1] - 0.012 + Row * 0.03;
			S.WinHeight = 0.026;
			S.RenderWeight = 0.5;
			AppendComponent(S);
			Swatches[Swatches.Length] = S;
		}
	UpdateSwatches();
}

function UpdateSwatches()
{
	local int i, n;

	n = Palette.Length;
	if (Swatches.Length < 2 * n)
		return;
	for (i = 0; i < n; i++)
	{
		Swatches[i].ImageColor = Palette[i];
		Swatches[n + i].ImageColor = Daltonized(Palette[i], class'ModSettings'.default.Colorblind, class'ModSettings'.default.ColorblindStrength);
	}
}

// post_final.hlsl's Daltonize (Machado et al. 2009 simulation, severity 1, then the error shift)
static function color Daltonized(color In, int Type, float Strength)
{
	local vector L, Sim, E, Sh;
	local color C;

	if (Type == 0)
		return In;
	L.X = Square(In.R / 255.0);
	L.Y = Square(In.G / 255.0);
	L.Z = Square(In.B / 255.0);
	if (Type == 1)
	{
		Sim.X = 0.152286 * L.X + 1.052583 * L.Y - 0.204868 * L.Z;
		Sim.Y = 0.114503 * L.X + 0.786281 * L.Y + 0.099216 * L.Z;
		Sim.Z = -0.003882 * L.X - 0.048116 * L.Y + 1.051998 * L.Z;
	}
	else if (Type == 2)
	{
		Sim.X = 0.367322 * L.X + 0.860646 * L.Y - 0.227968 * L.Z;
		Sim.Y = 0.280085 * L.X + 0.672501 * L.Y + 0.047413 * L.Z;
		Sim.Z = -0.011820 * L.X + 0.042940 * L.Y + 0.968881 * L.Z;
	}
	else
	{
		Sim.X = 1.255528 * L.X - 0.076749 * L.Y - 0.178779 * L.Z;
		Sim.Y = -0.078411 * L.X + 0.930809 * L.Y + 0.147602 * L.Z;
		Sim.Z = 0.004733 * L.X + 0.691367 * L.Y + 0.303900 * L.Z;
	}
	E = L - Sim;
	if (Type < 3)
	{
		Sh.Y = 0.7 * E.X + E.Y;
		Sh.Z = 0.7 * E.X + E.Z;
	}
	else
	{
		Sh.X = E.X + 0.7 * E.Z;
		Sh.Y = E.Y + 0.7 * E.Z;
	}
	L += Sh * Strength;
	C.R = 255.0 * Sqrt(FClamp(L.X, 0, 1)) + 0.5;
	C.G = 255.0 * Sqrt(FClamp(L.Y, 0, 1)) + 0.5;
	C.B = 255.0 * Sqrt(FClamp(L.Z, 0, 1)) + 0.5;
	C.A = 255;
	return C;
}

// blood decals on walls and floors (ModGore); marks already made stay until they fade
function bool BloodClick(GUIComponent Sender)
{
	local ModGore G;

	class'ModGore'.default.bBlood = !class'ModGore'.default.bBlood;
	class'ModGore'.static.StaticSaveConfig();
	foreach GetPC().DynamicActors(class'ModGore', G)
		G.bBlood = class'ModGore'.default.bBlood;
	ShowValues();
	return false;
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
	class'ModSettings'.static.ApplyColorblind(class'ModSettings'.default.Colorblind, Slider0.Value / 100.0);
	ShowValues();
}

defaultproperties
{
     LstrLabelTitle="Accessibility"
     LstrBlood="Blood"
     LstrColorblind="Colorblind Mode"
     LstrHudFade="Fading HUD"
     LstrWeaponSelect="Slow-Mo Weapon Select"
     LstrAutoAim="Auto Aiming"
     LstrCrouch="Toggle Crouch"
     LstrColorblindStrength="Colorblind Correction"
     ColorblindNames(0)="Off"
     ColorblindNames(1)="Protanopia"
     ColorblindNames(2)="Deuteranopia"
     ColorblindNames(3)="Tritanopia"
     Palette(0)=(R=220,G=40,B=40,A=255)
     Palette(1)=(R=240,G=140,B=30,A=255)
     Palette(2)=(R=240,G=220,B=40,A=255)
     Palette(3)=(R=60,G=190,B=60,A=255)
     Palette(4)=(R=40,G=200,B=210,A=255)
     Palette(5)=(R=50,G=90,B=220,A=255)
     Palette(6)=(R=150,G=60,B=200,A=255)
     Palette(7)=(R=230,G=110,B=170,A=255)
}
