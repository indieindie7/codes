//=============================================================================
// ModOptionsHub - the Options screen (in place of Interface.MenuPauseOptions): every page
// one press away, grouped by what a player is looking for, and each row showing the page's
// main settings as they are (menu UX pass, research/menu-ux-pass.md). The base page holds
// seven rows; the eighth, Controls, takes the Reset button's place at the bottom.
//=============================================================================
class ModOptionsHub extends MenuPauseOptionsBase;

var localized string LstrGameplay, LstrCamera, LstrAudio, LstrScreen, LstrGraphics, LstrQuality, LstrAccessibility, LstrControls;
var localized string DifficultyNames[4], ShadowNames[3], GiNames[3], ColorblindNames[4], FullscreenNames[3];
var localized string LstrOn, LstrOff, LstrSubtitles, LstrInverted, LstrNormal;
var int Open;                  // the page to show once this one has faded out (1..8)

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 7;
	NumSliders = 0;
	GetGameOptions();
	Labels[0].Caption = LstrGameplay;
	Labels[1].Caption = LstrCamera;
	Labels[2].Caption = LstrAudio;
	Labels[3].Caption = LstrScreen;
	Labels[4].Caption = LstrGraphics;
	Labels[5].Caption = LstrQuality;
	Labels[6].Caption = LstrAccessibility;
	Button0.bActNormal = true;
	Button0.OnClick = OpenGameplay;
	Button1.bActNormal = true;
	Button1.OnClick = OpenCamera;
	Button2.bActNormal = true;
	Button2.OnClick = OpenAudio;
	Button3.bActNormal = true;
	Button3.OnClick = OpenScreen;
	Button4.bActNormal = true;
	Button4.OnClick = OpenGraphics;
	Button5.bActNormal = true;
	Button5.OnClick = OpenQuality;
	Button6.bActNormal = true;
	Button6.OnClick = OpenAccessibility;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	ResetButton.Caption = LstrControls;
	class'ModPanel'.static.AddTo(self);
}

function GetGameOptions()
{
	Controller.ViewportOwner.Actor.GetActiveSlotOptions(Controller.OptionsData);
	if (!IsConsole())
		Controller.ViewportOwner.Actor.GetPCOptions(Controller.PCOptionsData);
}

function SetLocalGuiOptions(bool Reset)
{
	Refresh();
}

function MenuOnShow()
{
	Super.MenuOnShow();
	Refresh();
}

// each row's button shows where its page stands
function Refresh()
{
	local string S;
	local int i;

	Button0.Caption = DifficultyNames[Clamp(Controller.OptionsData.Difficulty, 0, 3)] $ ", " $ int(class'ModSettings'.default.DamageTaken * 100 + 0.5) $ "%";
	Button1.Caption = Either(Controller.OptionsData.InvertVerticle != 0, LstrInverted, LstrNormal);
	Button2.Caption = LstrSubtitles $ " " $ Either(Controller.OptionsData.Subtitles != 0, LstrOn, LstrOff);
	i = 0;
	if (class'ModSettings'.static.IsFullscreen(GetPC()))
		i = 2;
	else if (class'ModSettings'.static.NativeCall("IsBorderless"))
		i = 1;
	Button3.Caption = GetPC().ConsoleCommand("GETCURRENTRES");
	i = 0;
	if (class'ModSettings'.default.bSoftShadows)
		i = 1 + int(class'ModShadowManager'.default.NpcShadows > 0);
	Button4.Caption = ShadowNames[i] $ ", GI " $ GiNames[Clamp(class'ModSettings'.default.GiLevel, 0, 2)];
	Button5.Caption = "Draw " $ int((Controller.PCOptionsData.ClipPlane - 0.5) / 3.5 * 100 + 0.5) $ "%";
	S = ColorblindNames[Clamp(class'ModSettings'.default.Colorblind, 0, 3)];
	if (!class'ModGore'.default.bBlood)
		S = S $ ", no blood";
	Button6.Caption = S;
}

static function string Either(bool B, string T, string F)
{
	if (B)
		return T;
	return F;
}

function bool OpenGameplay(GUIComponent Sender) { return Go(1); }
function bool OpenCamera(GUIComponent Sender) { return Go(2); }
function bool OpenAudio(GUIComponent Sender) { return Go(3); }
function bool OpenScreen(GUIComponent Sender) { return Go(4); }
function bool OpenGraphics(GUIComponent Sender) { return Go(5); }
function bool OpenQuality(GUIComponent Sender) { return Go(6); }
function bool OpenAccessibility(GUIComponent Sender) { return Go(7); }

// the Reset button's slot is the Controls row
function bool OnReset(GUIComponent Sender)
{
	return Go(8);
}

function bool Go(int Page)
{
	Open = Page;
	bFadedOut = true;
	curState = MENU_STATE_EXIT;
	return false;
}

simulated function Timer()
{
	local int Page;

	if (bLoadNextMenu && Open > 0)
	{
		// faded out: the page (the base class would open its reset prompt here)
		bLoadNextMenu = false;
		Page = Open;
		Open = 0;
		// our pages by class, not by string: see ModGUIController.OpenMenu
		switch (Page)
		{
		case 1: Controller.OpenMenu(string(class'ModGameplayOptions')); break;
		case 2: Controller.OpenMenu("Interface.MenuPauseOptionsCamera"); break;
		case 3: Controller.OpenMenu(string(class'ModAudioOptions')); break;
		case 4: Controller.OpenMenu(string(class'ModScreenOptions')); break;
		case 5: Controller.OpenMenu(string(class'ModGraphicsOptions')); break;
		case 6: Controller.OpenMenu(string(class'ModQualityOptions')); break;
		case 7: Controller.OpenMenu(string(class'ModAccessibilityOptions')); break;
		case 8: Controller.OpenMenu("Interface.MenuPauseKeyBoardConfig"); break;
		}
		curState = MENU_STATE_IDLE;
	}
	Super.Timer();
}

// the pages wrote into Controller.OptionsData: saved when this screen closes (as the stock one)
function OptionsClose(optional bool bCancelled)
{
	Controller.ViewportOwner.Actor.SetActiveSlotOptions(Controller.OptionsData, 1, 1, -1);
}

defaultproperties
{
     LstrLabelTitle="Options"
     LstrGameplay="Gameplay"
     LstrCamera="Camera"
     LstrAudio="Audio"
     LstrScreen="Screen"
     LstrGraphics="Graphics"
     LstrQuality="Quality"
     LstrAccessibility="Accessibility"
     LstrControls="Controls"
     LstrOn="On"
     LstrOff="Off"
     LstrSubtitles="Subtitles"
     LstrInverted="Inverted"
     LstrNormal="Normal"
     DifficultyNames(0)="Easy"
     DifficultyNames(1)="Normal"
     DifficultyNames(2)="Hard"
     DifficultyNames(3)="Ultra"
     ShadowNames(0)="Shadows off"
     ShadowNames(1)="Your shadow"
     ShadowNames(2)="Shadows"
     GiNames(0)="off"
     GiNames(1)="on"
     GiNames(2)="strong"
     ColorblindNames(0)="Colorblind off"
     ColorblindNames(1)="Protanopia"
     ColorblindNames(2)="Deuteranopia"
     ColorblindNames(3)="Tritanopia"
     FullscreenNames(0)="window"
     FullscreenNames(1)="borderless"
     FullscreenNames(2)="fullscreen"
}
