//=============================================================================
// ModVideoOptions - the Video Options page with the launcher's display
// switches above Brightness / Contrast / Gamma: Borderless Fullscreen (a
// window covering the screen: the default, Alt+Tab and other monitors just
// work), Exclusive Fullscreen (the engine's own), VSync, and a row that opens
// the Display Options page. Both off is a normal window.
//=============================================================================
class ModVideoOptions extends MenuPauseOptionsVideo;

var localized string LstrFullscreen, LstrBorderless, LstrVSync, LstrMore, LstrOpen;
var bool bOpenMore;

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	Super.PreSetInitalPositions();
	NumBools = 4;
	// rows are toggles first, then sliders: move the slider captions below them
	Labels[6].Caption = Labels[2].Caption;
	Labels[5].Caption = Labels[1].Caption;
	Labels[4].Caption = Labels[0].Caption;
	Labels[0].Caption = LstrBorderless;
	Labels[1].Caption = LstrFullscreen;
	Labels[2].Caption = LstrVSync;
	Labels[3].Caption = LstrMore;
	Button0.bActNormal = true;
	Button0.OnClick = BorderlessClick;
	Button1.bActNormal = true;
	Button1.OnClick = FullscreenClick;
	Button2.bActNormal = true;
	Button2.OnClick = VSyncClick;
	Button3.bActNormal = true;
	Button3.OnClick = MoreClick;
}

function SetupInitalPositions()
{
	local int i;

	Super.SetupInitalPositions();
	for (i = 0; i < NumSliders; i++)
		Sliders[i].SetAssociatedLabel(Labels[NumBools + i]);
	Button3.Caption = LstrOpen;
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	Super.SetLocalGuiOptions(Reset);
	if (!Reset)
		Refresh();
}

function Refresh()
{
	Button0.SetValueB(class'ModSettings'.static.NativeCall("IsBorderless"));
	Button1.SetValueB(class'ModSettings'.static.IsFullscreen(GetPC()));
	Button2.SetValueB(class'ModSettings'.default.bVSync);
}

function bool FullscreenClick(GUIComponent Sender)
{
	local string Best;

	if (class'ModSettings'.static.IsFullscreen(GetPC()))
		GetPC().ConsoleCommand("ENDFULLSCREEN");
	else
	{
		// exclusive fullscreen and the borderless window exclude each other
		if (class'ModSettings'.static.NativeCall("IsBorderless"))
			class'ModSettings'.static.SetBorderless(false);
		// the engine's own switch (what Alt+Enter does), at the screen's size instead of the saved 800x600
		Best = class'ModSettings'.static.BestResolution();
		GetPC().ConsoleCommand("set WinDrv.WindowsClient FullscreenViewportX " $ Left(Best, InStr(Best, "x")));
		GetPC().ConsoleCommand("set WinDrv.WindowsClient FullscreenViewportY " $ Mid(Best, InStr(Best, "x") + 1));
		GetPC().ConsoleCommand("TOGGLEFULLSCREEN");
	}
	Refresh();
	return false;
}

function bool BorderlessClick(GUIComponent Sender)
{
	if (class'ModSettings'.static.IsFullscreen(GetPC()))
		GetPC().ConsoleCommand("ENDFULLSCREEN");
	class'ModSettings'.static.SetBorderless(!class'ModSettings'.static.NativeCall("IsBorderless"));
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

function bool MoreClick(GUIComponent Sender)
{
	bOpenMore = true;
	bFadedOut = true;
	curState = MENU_STATE_EXIT;
	return false;
}

simulated function Timer()
{
	if (bLoadNextMenu && bOpenMore)
	{
		// the page has faded out: show the next one (the base class would open its reset prompt)
		bLoadNextMenu = false;
		bOpenMore = false;
		// by class, not by string: see ModGUIController.OpenMenu
		Controller.OpenMenu(string(class'ModDisplayOptions'));
		curState = MENU_STATE_IDLE;
	}
	Super.Timer();
}

defaultproperties
{
     LstrFullscreen="Exclusive Fullscreen"
     LstrBorderless="Borderless Fullscreen"
     LstrVSync="VSync"
     LstrMore="More Display Options"
     LstrOpen="Open"
}
