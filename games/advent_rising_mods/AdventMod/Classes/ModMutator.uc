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
var bool bProbed, bPiloted;
var ModShadowManager Shadows;

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
	if (class'ModSettings'.default.bShadowFix)
		class'ModSettings'.static.NativeCall("ShadowAlpha");  // follows the game to a new device
	if (class'ModSettings'.default.bSoftShadows && Shadows == None)
		Shadows = Spawn(class'ModShadowManager');
	if (class'ModSettings'.default.bD3DTrace)
		class'ModSettings'.static.NativeCall("D3DTrace");     // testing: follows the game to a new device
	if (!bPiloted && class'ModPilot'.default.Steps.Length > 0 && PC != None && Level.Game != None && !Level.Game.IsInFrontEnd)
	{
		// testing: a pilot script plays this level (see ModPilot)
		bPiloted = true;
		// the player's controller copied its input class when it spawned: give it ours
		// and have it rebuild its input object from it
		PC.InputClass = class'ModInput';
		PC.InitInputSystem();
		Spawn(class'ModPilot');
	}
	if (class'ModSettings'.default.bShadowProbe && !bProbed && PC != None && PC.Pawn != None && (DebugStage >= 1 || (bPiloted && Level.TimeSeconds > 15)))
	{
		bProbed = true;
		Spawn(class'ShadowProbe').Start(PC.Pawn);
	}
	if ((class'ModSettings'.default.DebugLevelMenu != "" || class'ModSettings'.default.DebugMenuDelay > 0) && PC != None && DebugStage < 3)
	{
		// testing (see ModSettings): open a menu in this level, then take a screenshot of it
		DebugTime += 0.5;
		if (DebugStage == 0 && DebugTime >= class'ModSettings'.default.DebugMenuDelay)
		{
			// a level opened straight from the title still has the title menu (and its logo) on screen
			DebugStage = 1;
			SkipCutscene();
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
			SkipCutscene();
			DebugStage = 3;
			class'ModSettings'.static.Note("shot taken" $ PC.ConsoleCommand("shot"));
		}
	}
}

// testing: a level loaded straight from the title may be in its intro cutscene
function SkipCutscene()
{
	if (CinematicEvent(Level.CinematicToSkip) != None)
	{
		class'ModSettings'.static.Note("skipping cutscene " $ Level.CinematicToSkip);
		CinematicEvent(Level.CinematicToSkip).SkipCinematic();
	}
}

defaultproperties
{
     bAlwaysTick=True
}
