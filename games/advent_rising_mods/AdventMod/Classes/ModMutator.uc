//=============================================================================
// ModMutator - AdventMod's presence inside each level. The menu controller
// lives outside the levels and is never ticked, so anything that has to keep
// happening during play runs from here.
// Loaded by Mutator=AdventMod.ModMutator in [DefaultPlayer] (MyDefUser.ini):
// the game adds that section's keys to every level URL.
//=============================================================================
class ModMutator extends Mutator;

var float Wait, DebugTime;
var int DebugStage;

// ticks while the game is paused too (bAlwaysTick), so the FOV slider in the pause menu
// shows its effect at once
event Tick(float DeltaTime)
{
	Super.Tick(DeltaTime);
	Wait -= DeltaTime;
	if (Wait <= 0)
	{
		Wait = 0.5;
		Every();
	}
}

function Every()
{
	local PlayerController PC;
	local string Rest, Menu;
	local int i;

	PC = Level.GetLocalPlayerController();
	class'ModSettings'.static.ApplyFOV(PC);
	if (class'ModSettings'.default.DebugLevelMenu != "" && PC != None && DebugStage < 3)
	{
		// testing (see ModSettings): open a menu in this level, then take a screenshot of it
		DebugTime += 0.5;
		if (DebugStage == 0 && DebugTime >= class'ModSettings'.default.DebugMenuDelay)
		{
			// a level opened straight from the title still has the title menu (and its logo) on screen
			DebugStage = 1;
			PC.Player.GUIController.CloseAll(false);
		}
		else if (DebugStage == 1 && DebugTime >= class'ModSettings'.default.DebugMenuDelay + 2.0)
		{
			DebugStage = 2;
			// several menus separated by |: each opens on top of the one before
			Rest = class'ModSettings'.default.DebugLevelMenu;
			while (Rest != "")
			{
				i = InStr(Rest, "|");
				if (i < 0)
				{
					Menu = Rest;
					Rest = "";
				}
				else
				{
					Menu = Left(Rest, i);
					Rest = Mid(Rest, i + 1);
				}
				class'ModSettings'.static.Note("level menu " $ Menu $ ": " $ PC.Player.GUIController.OpenMenu(Menu));
			}
		}
		else if (DebugStage == 2 && DebugTime >= class'ModSettings'.default.DebugMenuDelay + 6.0)
		{
			DebugStage = 3;
			class'ModSettings'.static.Note("shot taken" $ PC.ConsoleCommand("shot"));
		}
	}
}

defaultproperties
{
     bAlwaysTick=True
}
