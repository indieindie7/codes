//=============================================================================
// GMCommands - the "gm" console command (added to the player's ExecManagers,
// as U2TestHub's HubCommands is).
//=============================================================================
class GMCommands extends Object;

var GMMaster Master;

exec function GM(optional string Args)
{
	if (Master != None)
		Master.Command(Args);
}
