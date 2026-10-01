//=============================================================================
// U2TestHub - console commands for testing the mods in any level ("live game
// doc"). Type "hub help" in the console. Lights and shadows for now.
//
// The commands live in HubCommands, which is added to the player's
// ExecManagers list (Unreal II's own hook for extra console commands, used by
// its CheatManager and AdminManager), so no stock class is replaced.
// Add U2TestHub.HubMutator to the Mutator= line in User.ini's [DefaultPlayer].
//=============================================================================
class HubMutator extends Mutator;

var array<TestLamp> Lamps;
var Actor Probe;
var array<Pawn> ShadowOffPawns;   // pawns 'hub shadows off' switched off, to switch back

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(0.5, true);
}

// players come and go (level start, respawn): make sure each one has the commands
event Timer()
{
	local Controller C;
	local PlayerController PC;
	local HubCommands H;
	local int i;
	local bool bHas;

	for (C = Level.ControllerList; C != None; C = C.NextController)
	{
		PC = PlayerController(C);
		if (PC == None)
			continue;
		bHas = false;
		for (i = 0; i < PC.ExecManagers.Length; i++)
			if (HubCommands(PC.ExecManagers[i]) != None)
				bHas = true;
		if (!bHas)
		{
			H = new(PC) class'HubCommands';
			H.HubMut = Self;
			H.PC = PC;
			PC.ExecManagers[PC.ExecManagers.Length] = H;
			Log("U2TestHub: commands ready for "$string(PC)$" (type: hub help)");
		}
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
}
