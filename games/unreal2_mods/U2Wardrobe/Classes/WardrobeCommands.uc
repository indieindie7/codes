//=============================================================================
// WardrobeCommands - the "wardrobe" console command (added to the player's
// ExecManagers by WardrobeMutator). The F6 menu's buttons run these too.
//=============================================================================
class WardrobeCommands extends Object;

var WardrobeMutator WM;          // (a var may not share the exec function's name)
var PlayerController PC;

exec function Wardrobe(optional string Args)
{
	local string Cmd, Rest;
	local int i;

	i = InStr(Args, " ");
	if (i >= 0)
	{
		Cmd = Caps(Left(Args, i));
		Rest = Mid(Args, i + 1);
	}
	else
		Cmd = Caps(Args);

	if (Cmd == "WEAR")
		WM.Wear(Rest, PC);
	else if (Cmd == "NEXT")
		WM.Step(1, PC);
	else if (Cmd == "PREV")
		WM.Step(-1, PC);
	else if (Cmd == "VIEW")
		PC.ClientSetBehindView(!PC.bBehindView);
	else if (Cmd == "LIST")
		WM.List(PC);
	else if (Cmd == "MEASURE")
		WM.StartMeasure(PC);
	else if (Cmd == "BODY")
		WM.SetBody(!WM.bFirstPersonBody, PC);
	else if (Cmd == "OPENED" || Cmd == "CLOSED")
	{
		// the F6 menu pauses the game (that hands it the mouse); keep the HUD's
		// big PAUSED message from covering it while it's open
		if (PC.myHUD != None && Cmd == "OPENED")
			PC.myHUD.PausedMessage = "";
		else if (PC.myHUD != None)
			PC.myHUD.PausedMessage = PC.myHUD.default.PausedMessage;
	}
	else
		PC.ClientMessage("wardrobe wear NAME | next | prev | view | list | body | measure   (F6: menu)");
}
