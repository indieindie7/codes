//=============================================================================
// U2AutoPlay - a simple AI that plays the game through the player's own
// controls, for testing levels with nobody at the keyboard. It doesn't replace
// the player: the player's input object is swapped for AutoInput, which, while
// autoplay is on, presses the same virtual keys a person would (forward, strafe,
// jump, fire, use) and turns the view. So doors, triggers, pickups and scripted
// events see a normal player.
//
// Console:  autoplay on | off | status | explore | goto X Y Z
// Config:   System\U2AutoPlay.ini [U2AutoPlay.AutoPlayMutator] bStartOn
// Load:     add U2AutoPlay.AutoPlayMutator to the map URL (?Mutator=...) or to
//           User.ini's Mutator= line. Everything it does is logged ("AutoPlay:").
//=============================================================================
class AutoPlayMutator extends Mutator
	config(U2AutoPlay);

var config bool bStartOn;
var AutoBrain Brain;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(0.5, true);
}

// each local player gets the autoplay input and the command (players come and go: map start, respawn)
event Timer()
{
	local PlayerController PC;
	local AutoInput AI;
	local AutoCommands C;
	local int i;
	local bool bHas;

	PC = Level.PlayerControllerList;
	if (PC == None || PC.PlayerInput == None)
		return;
	if (Brain == None)
	{
		Brain = Spawn(class'AutoBrain');
		Brain.bOn = bStartOn;
		Log("AutoPlay: ready (type 'autoplay on'), start "$bStartOn);
	}
	Brain.PC = PC;
	if (AutoInput(PC.PlayerInput) == None)
	{
		AI = new(PC) class'AutoInput';
		AI.Brain = Brain;
		if (PC.PlayerInput.Class != PC.InputClass)
			AI.Inner = PC.PlayerInput;     // another mod's input: wrap it, don't throw it away
		AI.MouseSensitivity = PC.PlayerInput.MouseSensitivity;
		AI.bInvertMouse = PC.PlayerInput.bInvertMouse;
		PC.PlayerInput = AI;
	}
	bHas = false;
	for (i = 0; i < PC.ExecManagers.Length; i++)
		if (AutoCommands(PC.ExecManagers[i]) != None)
			bHas = true;
	if (!bHas)
	{
		C = new(PC) class'AutoCommands';
		C.Brain = Brain;
		PC.ExecManagers[PC.ExecManagers.Length] = C;
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
}
