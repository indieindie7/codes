//=============================================================================
// ModGUIController - the game's menu controller with AdventMod's pages swapped
// in. Selected by GUIController=AdventMod.ModGUIController in [Engine.Engine].
//=============================================================================
class ModGUIController extends GUIController;

var bool bStarted, bDebugOpened;

event bool OpenMenu(string NewMenuName, optional string Param1, optional string Param2, optional Object Param3, optional bool bHide)
{
	if (!bStarted)
	{
		// the first menu (the title): the window exists now
		bStarted = true;
		class'ModSettings'.static.Startup(ViewportOwner.Actor);   // runs once, whoever calls first
	}
	// The pages are named through their classes, not strings, on purpose: a level change
	// collects every script class nothing refers to, and the engine then fails to load it
	// again (the page would silently not open from the pause menu). These references keep
	// the pages alive for as long as this controller is.
	if (NewMenuName ~= "ini:Engine.GameEngine.InitialMenuClass" || NewMenuName ~= "Interface.MenuTitle_pc")
		NewMenuName = string(class'ModTitle');
	else if (NewMenuName ~= "Interface.MenuPauseOptionsVideo")
		NewMenuName = string(class'ModVideoOptions');
	else if (NewMenuName ~= "Interface.MenuPCOptions")
		NewMenuName = string(class'ModPCOptions');
	else if (NewMenuName ~= "Interface.MenuPauseOptionsAudio")
		NewMenuName = string(class'ModAudioOptions');
	if (!Super.OpenMenu(NewMenuName, Param1, Param2, Param3, bHide))
		return false;
	if (!bDebugOpened)
	{
		// testing (see ModSettings): commands, then a menu, then actions on that menu
		bDebugOpened = true;
		RunDebug(class'ModSettings'.default.DebugCommands);
		if (class'ModSettings'.default.DebugOpenMenu != "")
		{
			OpenMenu(class'ModSettings'.default.DebugOpenMenu);
			RunDebug(class'ModSettings'.default.DebugActions);
		}
	}
	return true;
}

// steps separated by |: "clickN" presses row N's button on the open options page,
// "slideN=V" moves slider N, "native:X" calls AdventNative, anything else is a console command. Results go to AdventNative.log.
function RunDebug(string Rest)
{
	local string Cmd;
	local MenuPauseOptionsBase Page;
	local int i, N;

	while (Rest != "")
	{
		i = InStr(Rest, "|");
		if (i < 0)
		{
			Cmd = Rest;
			Rest = "";
		}
		else
		{
			Cmd = Left(Rest, i);
			Rest = Mid(Rest, i + 1);
		}
		Page = MenuPauseOptionsBase(ActivePage);
		if (Left(Cmd, 5) ~= "click" && Page != None)
		{
			N = int(Mid(Cmd, 5));
			Page.BoolButtons[N].OnClick(Page.BoolButtons[N]);
			class'ModSettings'.static.Note(Cmd $ " => " $ Page.Labels[N].Caption $ " = " $ Page.BoolButtons[N].Caption);
		}
		else if (Left(Cmd, 5) ~= "slide" && Page != None)
		{
			N = int(Mid(Cmd, 5, 1));
			Page.Sliders[N].SetValue(float(Mid(Cmd, 7)));
			Page.Sliders[N].OnChange(Page.Sliders[N]);
			class'ModSettings'.static.Note(Cmd $ " => " $ Page.Labels[Page.NumBools + N].Caption $ " = " $ Page.Sliders[N].Value);
		}
		else if (Left(Cmd, 7) ~= "native:")
			class'ModSettings'.static.Note(Cmd $ " => " $ class'ModSettings'.static.NativeCall(Mid(Cmd, 7)));
		else
			class'ModSettings'.static.Note(Cmd $ " => " $ ViewportOwner.Actor.ConsoleCommand(Cmd));
	}
}

defaultproperties
{
}
