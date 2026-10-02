//=============================================================================
// PostFXHelper - the post-processing rows on Options > HUD.
// Saves into System\U2Shaders.ini (section [U2SoftShadows.PostFXHelper]), which
// the d3d8 fork (U2Shaders) reads again within a second while the game runs:
// post=1 on/off, bloom="threshold intensity", grade="saturation contrast
// exposure vignette", colour="r g b", sharpen. The fork reads any case.
// Registered in the menu script itself ([PostFXHelper] RegisterObj), like
// SSMenuHelper. Looks: the presets the user compared on 2026-10-02.
//=============================================================================
class PostFXHelper extends UIHelper config(U2Shaders);

var config int post;
var config string bloom, grade, colour;
var config float sharpen;

var array<string> Looks;           // menu names of the presets, then "Custom"
var array<string> LookBloom, LookGrade, LookColour;
var array<float> LookSharpen;

// the n-th number in a space-separated list
function float Num(string S, int n)
{
	local int i, k;

	for (i = 0; i < n; i++)
	{
		k = InStr(S, " ");
		if (k < 0)
			return 0;
		S = Mid(S, k + 1);
	}
	k = InStr(S, " ");
	if (k >= 0)
		S = Left(S, k);
	return float(S);
}

// the list with its n-th number replaced
function string SetNum(string S, int Count, int n, float V)
{
	local int i;
	local string Out;

	for (i = 0; i < Count; i++)
	{
		if (i > 0)
			Out = Out $ " ";
		if (i == n)
			Out = Out $ V;
		else
			Out = Out $ Num(S, i);
	}
	return Out;
}

function Save()
{
	class'PostFXHelper'.static.StaticSaveConfig();
}

// copies between this menu object and the class defaults (what StaticSaveConfig writes)
function bool GetPostEnabled()          { return class'PostFXHelper'.default.post != 0; }
function SetPostEnabled(bool B)         { if (B) class'PostFXHelper'.default.post = 1; else class'PostFXHelper'.default.post = 0; Save(); }

function float GetBloomAmount()         { return Num(class'PostFXHelper'.default.bloom, 1); }
function SetBloomAmount(float F)        { class'PostFXHelper'.default.bloom = SetNum(class'PostFXHelper'.default.bloom, 2, 1, F); Save(); }
function float GetSaturation()          { return Num(class'PostFXHelper'.default.grade, 0); }
function SetSaturation(float F)         { class'PostFXHelper'.default.grade = SetNum(class'PostFXHelper'.default.grade, 4, 0, F); Save(); }
function float GetContrast()            { return Num(class'PostFXHelper'.default.grade, 1); }
function SetContrast(float F)           { class'PostFXHelper'.default.grade = SetNum(class'PostFXHelper'.default.grade, 4, 1, F); Save(); }
function float GetVignette()            { return Num(class'PostFXHelper'.default.grade, 3); }
function SetVignette(float F)           { class'PostFXHelper'.default.grade = SetNum(class'PostFXHelper'.default.grade, 4, 3, F); Save(); }
function float GetSharpen()             { return class'PostFXHelper'.default.sharpen; }
function SetSharpen(float F)            { class'PostFXHelper'.default.sharpen = F; Save(); }

// the look dropdown: a preset sets every value at once; changing a slider makes it "Custom"
function array<string> GetLookList()    { return Looks; }

function string GetLook()
{
	local int i;

	for (i = 0; i < LookBloom.Length; i++)
		if (Same(class'PostFXHelper'.default.bloom, LookBloom[i], 2) && Same(class'PostFXHelper'.default.grade, LookGrade[i], 4)
			&& Same(class'PostFXHelper'.default.colour, LookColour[i], 3) && Abs(class'PostFXHelper'.default.sharpen - LookSharpen[i]) < 0.01)
			return Looks[i];
	return Looks[Looks.Length - 1];
}

function bool Same(string A, string B, int Count)
{
	local int i;

	for (i = 0; i < Count; i++)
		if (Abs(Num(A, i) - Num(B, i)) > 0.01)
			return false;
	return true;
}

function SetLook(string L)
{
	local int i;

	for (i = 0; i < LookBloom.Length; i++)
		if (Looks[i] ~= L)
		{
			class'PostFXHelper'.default.bloom = LookBloom[i];
			class'PostFXHelper'.default.grade = LookGrade[i];
			class'PostFXHelper'.default.colour = LookColour[i];
			class'PostFXHelper'.default.sharpen = LookSharpen[i];
			Save();
			return;
		}
}

defaultproperties
{
	post=1
	bloom="0.7 0.6"
	grade="1.1 1.08 1.0 0.25"
	colour="1 1 1"
	sharpen=0.300000
	Looks(0)="Clean"
	Looks(1)="Cold sci-fi"
	Looks(2)="Warm film"
	Looks(3)="Punchy"
	Looks(4)="Custom"
	LookBloom(0)="0.7 0.6"
	LookGrade(0)="1.1 1.08 1.0 0.25"
	LookColour(0)="1 1 1"
	LookSharpen(0)=0.300000
	LookBloom(1)="0.6 0.9"
	LookGrade(1)="1.05 1.15 1.0 0.4"
	LookColour(1)="0.92 1.0 1.12"
	LookSharpen(1)=0.400000
	LookBloom(2)="0.55 1.1"
	LookGrade(2)="0.95 1.1 1.05 0.45"
	LookColour(2)="1.08 1.0 0.9"
	LookSharpen(2)=0.200000
	LookBloom(3)="0.5 1.4"
	LookGrade(3)="1.3 1.2 1.05 0.3"
	LookColour(3)="1 1 1"
	LookSharpen(3)=0.500000
}
