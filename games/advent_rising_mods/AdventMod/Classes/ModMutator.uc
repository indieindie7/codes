//=============================================================================
// ModMutator - AdventMod's presence inside each level, the title screen included.
// It also runs the mod's one-time start-up (ModSettings.Startup) in the first level, in
// case ModGUIController (which runs it at the first menu) isn't installed.
// Loaded by Mutator=AdventMod.ModMutator in [DefaultPlayer] (MyDefUser.ini):
// the game adds that section's keys to every level URL.
//=============================================================================
class ModMutator extends Mutator;

var ModLive Live;
var float Wait, DebugTime;
var int DebugStage;
var bool bProbed, bPiloted;
var int RemovedFx;
var ModShadowManager Shadows;
var ModTargeting Targeting;
var ModGore Gore;

// ticks while the game is paused too (bAlwaysTick), so the FOV slider in the pause menu
// shows its effect at once
event Tick(float DeltaTime)
{
	Super.Tick(DeltaTime);
	if (class'ModSettings'.default.bNoGamePostFx)
		NoGamePostFx();
	Wait -= DeltaTime;
	if (Wait <= 0)
	{
		Wait = 0.5;
		Every();
	}
}

// the game adds camera effects on the fly (motion blur in attacks, scripted blurs and
// focus): take every one off the player as soon as it appears
function NoGamePostFx()
{
	local PlayerController PC;
	local int Removed;

	PC = Level.GetLocalPlayerController();
	if (PC == None)
		return;
	while (PC.CameraEffects.Length > 0)
	{
		if (Removed++ == 0 || RemovedFx < 20)
			class'ModSettings'.static.Note("post fx: removed the game's " $ PC.CameraEffects[0].Class);
		RemovedFx++;
		PC.CameraEffects.Remove(0, 1);
	}
}

function Every()
{
	local PlayerController PC;
	local string Rest, Menu;
	local int i;

	PC = Level.GetLocalPlayerController();
	if (PC != None && !class'ModSettings'.default.bStartedUp)
	{
		class'ModSettings'.static.Startup(PC);
		// testing: console commands on the title screen (e.g. open a level)
		RunCommands(PC, class'ModSettings'.default.DebugCommands);
	}
	// the player's controller in a level (a loaded save brings its own input class with it):
	// ModInput, for the stuck-pad and mouse fixes
	if (PC != None && (PC.PlayerInput == None || PC.PlayerInput.Class != class'ModInput'))
	{
		PC.InputClass = class'ModInput';
		PC.InitInputSystem();
		class'ModSettings'.static.Note("input: ModInput given to " $ PC);
	}
	class'ModSettings'.static.ApplyFOV(PC);
	if (class'ModSettings'.default.bShadowFix)
		class'ModSettings'.static.NativeCall("ShadowAlpha");  // follows the game to a new device
	if (class'ModSettings'.default.bSoftShadows && Shadows == None)
		Shadows = Spawn(class'ModShadowManager');
	else if (!class'ModSettings'.default.bSoftShadows && Shadows != None)
	{
		// switched off on the Graphics page: the game's own shadows come back
		Shadows.Destroy();
		Shadows = None;
	}
	if (Targeting == None && PC != None && Level.Game != None && !Level.Game.IsInFrontEnd)
		Targeting = Spawn(class'ModTargeting');
	if (Targeting != None)
		Targeting.Update(PC);
	if (class'ModSettings'.default.bFpsGraph && !class'ModFpsGraph'.default.bAdded && PC != None && PC.Player != None && Level.Game != None && !Level.Game.IsInFrontEnd)
		PC.Player.InteractionMaster.AddInteraction(string(class'ModFpsGraph'), PC.Player);
	if (!class'ModSettings'.default.bGraphicsOnly && !class'ModScreenBlood'.default.bAdded && PC != None && PC.Player != None && Level.Game != None && !Level.Game.IsInFrontEnd)
		PC.Player.InteractionMaster.AddInteraction(string(class'ModScreenBlood'), PC.Player);
	if (!class'ModSettings'.default.bGraphicsOnly && Gore == None && PC != None && Level.Game != None && !Level.Game.IsInFrontEnd)
		Gore = Spawn(class'ModGore');
	if (Live == None && PC != None && Level.Game != None && !Level.Game.IsInFrontEnd)
		Live = Spawn(class'ModLive');      // live sessions: "mutate live reload" and the place it puts the player back
	if (class'ModSettings'.default.bD3DTrace)
		class'ModSettings'.static.NativeCall("D3DTrace");     // testing: follows the game to a new device
	class'ModSettings'.static.NativeCall("MaxFps:" $ class'ModSettings'.default.MaxFps);  // follows the game to a new device
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
	if ((class'ModSettings'.default.DebugLevelMenu != "" || class'ModSettings'.default.DebugLevelCommands != "" || class'ModSettings'.default.DebugMenuDelay > 0) && PC != None && DebugStage < 3)
	{
		// testing (see ModSettings): open a menu in this level, then take a screenshot of it
		DebugTime += 0.5;
		if (DebugStage == 0 && DebugTime >= class'ModSettings'.default.DebugMenuDelay)
		{
			// a level opened straight from the title still has the title menu (and its logo) on screen
			DebugStage = 1;
			SkipCutscene();
			PC.Player.GUIController.CloseAll(false);
			RunCommands(PC, class'ModSettings'.default.DebugLevelCommands);
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

// testing: console commands separated by |, results in AdventNative.log
function RunCommands(PlayerController PC, string Rest)
{
	local string Cmd;
	local int i;

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
		if (!class'ModSettings'.static.DebugStep(PC, Cmd))
			if (Left(Cmd, 3) ~= "in:")
		{
			Cmd = Mid(Cmd, 3);
			i = InStr(Cmd, ":");
			if (i < 0 || !(Left(Cmd, i) ~= string(Level.Outer.Name)))
			{
				class'ModSettings'.static.Note(Cmd $ " skipped in " $ Level.Outer.Name);
				continue;
			}
			Cmd = Mid(Cmd, i + 1);
		}
		if (!class'ModSettings'.static.DebugStep(PC, Cmd))
			class'ModSettings'.static.Note(Cmd $ " => " $ PC.ConsoleCommand(Cmd));
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

// console "mutate ...": "mutate live save|reload|forget" (ModLive)
function Mutate(string MutateString, PlayerController Sender)
{
	if (Caps(Left(MutateString, 5)) == "LIVE " && Live != None)
		Live.Command(Mid(MutateString, 5), Sender);
	Super.Mutate(MutateString, Sender);
}

defaultproperties
{
     bAlwaysTick=True
}
