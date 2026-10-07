//=============================================================================
// AutoCommands - the "autoplay" console command (added to the player's
// ExecManagers, as U2TestHub's HubCommands is).
//
//   autoplay on | off        start / stop playing
//   autoplay status          where it is, what it's going for, what it has seen
//   autoplay explore         forget the visited places and explore again
//   autoplay goto X Y Z      walk to a point (then back to exploring)
//=============================================================================
class AutoCommands extends Object;

var AutoBrain Brain;

exec function Autoplay(optional string Args)
{
	if (Brain != None)
		Brain.Command(Args);
}
