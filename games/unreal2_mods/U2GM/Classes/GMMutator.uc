//=============================================================================
// U2GM - a game master mode for Unreal II: change the level while it is
// played. "gm" in the console toggles GM mode (a free camera through walls);
// then pick what's under the crosshair, move, turn, scale, hide, spawn from a
// palette (snapped to a grid and the ground), possess a character, freeze the
// world, undo and redo. Every change is one line in a journal (System\U2GM.ini,
// written only by the game), replayed when the map loads, in AvalonEditor's
// format ("place NAME X Y Z YAW SCALE", "hide NAME", "mesh PATH X Y Z YAW SCALE")
// so the editor can bake a session into the map later.
//
// Console:  gm help (all commands)
// Load:     ?Mutator=U2GM.GMMutator on the map URL, or User.ini's Mutator= line
//=============================================================================
class GMMutator extends Mutator;

var GMMaster Master;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(0.5, true);
}

// the local player gets the "gm" command (players come and go: map start, respawn)
event Timer()
{
	local PlayerController PC;
	local GMCommands C;
	local int k;

	PC = Level.PlayerControllerList;
	if (PC == None)
		return;
	if (Master == None)
	{
		Master = Spawn(class'GMMaster');
		Master.Replay();
		Log("GM: ready on "$Master.Family()$" ("$Master.CountOps()$" journal lines), type 'gm help'");
	}
	Master.PC = PC;
	for (k = 0; k < PC.ExecManagers.Length; k++)
		if (GMCommands(PC.ExecManagers[k]) != None)
			return;
	C = new(PC) class'GMCommands';
	C.Master = Master;
	PC.ExecManagers[PC.ExecManagers.Length] = C;
}

defaultproperties
{
	RemoteRole=ROLE_None
}
