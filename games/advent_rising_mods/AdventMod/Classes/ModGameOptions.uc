//=============================================================================
// ModGameOptions - the game's Game Options page with a seventh row that opens
// AdventMod's Gameplay page (ModGameplayOptions): difficulty sliders, boss
// tuning and exploring speed.
//=============================================================================
class ModGameOptions extends MenuPauseOptionsGame;

var localized string LstrMore, LstrOpen;
var bool bOpenMore;

function PreSetInitalPositions()
{
	Super.PreSetInitalPositions();
	NumBools = 7;
	Labels[6].Caption = LstrMore;
	Button6.bActNormal = true;
	Button6.OnClick = MoreClick;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Button6.Caption = LstrOpen;
	class'ModPanel'.static.AddTo(self);
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
		Controller.OpenMenu(string(class'ModGameplayOptions'));
		curState = MENU_STATE_IDLE;
	}
	Super.Timer();
}

defaultproperties
{
     LstrMore="More Gameplay Options"
     LstrOpen="Open"
}
