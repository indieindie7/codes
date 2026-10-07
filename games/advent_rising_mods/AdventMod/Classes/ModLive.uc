//=============================================================================
// ModLive - seamless reload for live sessions: a map rebuilt in the editor (geometry, lighting)
// or a changed mod comes back with the player where they were, so a QA session goes on.
//
//   live save             the player's place, view and health saved (AdventMod.ini, [AdventMod.ModLive])
//   live reload           saved, then the same map opened again (its own URL, options kept)
//   live forget           the saved place dropped
// On the next load of that map (a reload, or a restart through tools/live_reload.py), the
// level's intro cutscene is skipped and the player put back, once.
// Console commands (ModInput.Live; "mutate live ..." too): typed, or through the d3d8 layer's command channel
// (live=1 in U2Shaders.ini; tools/live_reload.py writes them).
//=============================================================================
class ModLive extends Info
	config(AdventMod);

var config bool bResume;
var config string ResumeMap;
var config vector ResumeLocation;
var config rotator ResumeRotation;
var config int ResumeHealth;
var config float ResumeDelay;       // seconds after the player has a pawn before putting it back

var float Waited;
var float Poll;                     // seconds to the next look at AdventLive.req
var string PendingOpen;             // a reload asked for: opened at the next tick, in the game's own loop

function string MapName()
{
	local string S;

	S = string(Level);
	if (InStr(S, ".") >= 0)
		S = Left(S, InStr(S, "."));
	return S;
}

function Command(string Args, PlayerController PC)
{
	Args = Caps(Args);
	if (Args == "SAVE" || Args == "RELOAD")
	{
		if (!Save(PC))
			return;
		if (Args == "RELOAD")
		{
			// not from here: a command can arrive from a window message (the d3d8 layer's
			// channel), and opening a map from inside one left the game stuck
			PendingOpen = Level.GetLocalURL();
			Enable('Tick');
			class'ModSettings'.static.Note("live: reloading " $ PendingOpen);
		}
	}
	else if (Args == "FORGET")
	{
		bResume = false;
		SaveConfig();
		class'ModSettings'.static.Note("live: saved place dropped");
	}
	else
		class'ModSettings'.static.Note("live: unknown command '" $ Args $ "' (save, reload, forget)");
}

function bool Save(PlayerController PC)
{
	if (PC == None || PC.Pawn == None)
	{
		class'ModSettings'.static.Note("live: no player pawn to save");
		return false;
	}
	bResume = true;
	ResumeMap = MapName();
	ResumeLocation = PC.Pawn.Location;
	ResumeRotation = PC.Rotation;
	ResumeHealth = PC.Pawn.Health;
	SaveConfig();
	class'ModSettings'.static.Note("live: saved " $ ResumeMap $ " at " $ ResumeLocation $ " view " $ ResumeRotation $ " health " $ ResumeHealth);
	return true;
}

event Tick(float DeltaTime)
{
	local PlayerController PC;

	// tools/live_reload.py's requests: a word in System\AdventLive.req (AdventNative LiveReq:)
	Poll -= DeltaTime;
	if (Poll <= 0)
	{
		Poll = 0.5;
		PC = Level.GetLocalPlayerController();
		if (class'ModSettings'.static.NativeCall("LiveReq:reload"))
			Command("RELOAD", PC);
		else if (class'ModSettings'.static.NativeCall("LiveReq:save"))
			Command("SAVE", PC);
		else if (class'ModSettings'.static.NativeCall("LiveReq:forget"))
			Command("FORGET", PC);
		else if (class'ModSettings'.static.NativeCall("LiveReq:quit") && PC != None)
		{
			Save(PC);
			PC.ConsoleCommand("exit");
		}
	}
	if (PendingOpen != "")
	{
		PC = Level.GetLocalPlayerController();
		if (PC != None)
			PC.ConsoleCommand("open " $ PendingOpen);
		PendingOpen = "";
		return;
	}
	if (!bResume)
		return;
	if (ResumeMap != MapName())
		return;
	// the level's intro would move the player and the camera: skip it
	if (Level.CinematicToSkip != None && CinematicEvent(Level.CinematicToSkip) != None)
		CinematicEvent(Level.CinematicToSkip).SkipCinematic();
	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return;
	Waited += DeltaTime;
	if (Waited < ResumeDelay)
		return;
	if (!PC.Pawn.SetLocation(ResumeLocation))
		PC.Pawn.SetLocation(ResumeLocation + vect(0,0,40));
	PC.Pawn.Velocity = vect(0,0,0);
	PC.SetRotation(ResumeRotation);
	if (ResumeHealth > 0)
		PC.Pawn.Health = ResumeHealth;
	bResume = false;
	SaveConfig();
	class'ModSettings'.static.Note("live: resumed " $ ResumeMap $ " at " $ PC.Pawn.Location $ " (saved " $ ResumeLocation $ ")");
}

defaultproperties
{
     ResumeDelay=0.500000
}
