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
			class'ModSettings'.static.Note("live: reloading " $ Level.GetLocalURL());
			PC.ConsoleCommand("open " $ Level.GetLocalURL());
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

	if (!bResume)
		return;
	if (ResumeMap != MapName())
	{
		Disable('Tick');
		return;
	}
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
	Disable('Tick');
}

defaultproperties
{
     ResumeDelay=0.500000
}
