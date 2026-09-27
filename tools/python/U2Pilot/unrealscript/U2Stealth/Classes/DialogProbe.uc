//=============================================================================
// Development probe: once a second, logs whether a cutscene is running and
// every active dialogue session (who's in it, whether the player is, whether
// it's finished) to map out how scenes and conversations gate level events.
//=============================================================================
class DialogProbe extends Mutator;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(1.0, true);
}

event Timer()
{
	local DialogEngine DE;
	local DialogSession S;
	local PlayerController PC;
	local Controller C;
	local string Who;
	local int i, j;
	local Pawn P;
	local string Ctx;

	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
			PC = PlayerController(C);
	// cutscene stand-ins / commanders: where their scripts are and whether they're in stasis
	foreach DynamicActors(class'Pawn', P)
		if (P.Controller != None && (InStr(string(P.Name), "Commander") >= 0 || InStr(string(P.Name), "CutscenePlayer") >= 0))
		{
			Ctx = "";
			if (U2NPCControllerScriptable(P.Controller) != None && ScriptControllerBase(U2NPCControllerScriptable(P.Controller).ScriptController) != None)
				Ctx = ScriptControllerBase(U2NPCControllerScriptable(P.Controller).ScriptController).GetScriptContextStr();
			Log("DialogProbe: pawn "$P.Name$" loc="$int(P.Location.X)$","$int(P.Location.Y)$" hidden="$P.bHidden$" stasis="$P.bStasis$"/"$P.Controller.bStasis$" state="$P.Controller.GetStateName()$" script: "$Ctx);
		}
	DE = class'DialogEngine'.static.GetInstance(Self);
	if (DE == None || PC == None)
		return;
	Log("DialogProbe: t="$int(Level.TimeSeconds)$" interp="$PC.bInterpolating$" sessions="$DE.Sessions.Length$" slomo="$DE.AllowSlomo);
	if (PC.Pawn != None)
		Log("DialogProbe: player state="$PC.GetStateName()$" behind="$PC.bBehindView$" viewtarget="$PC.ViewTarget$" pawnInterp="$PC.Pawn.bInterpolating$" phys="$PC.Pawn.Physics$" speed="$int(VSize(PC.Pawn.Velocity))$" hidden="$PC.Pawn.bHidden$" hud="$Level.Game.bDisplayHud);
	else
		Log("DialogProbe: player state="$PC.GetStateName()$" NO PAWN viewtarget="$PC.ViewTarget$" hud="$Level.Game.bDisplayHud);
	for (i = 0; i < DE.Sessions.Length; i++)
	{
		S = DE.Sessions[i];
		if (S == None)
			continue;
		Who = "";
		for (j = 0; j < S.DControllers.Length; j++)
			if (S.DControllers[j] != None)
				Who = Who $ S.DControllers[j].DCSpeaker $ "(" $ S.DControllers[j].Class.Name $ ") ";
		Log("DialogProbe:   #"$i$" trigger="$S.Trigger$" topic="$S.Topic$" finished="$S.bSessionFinished$" audio="$S.bAudioPlaying
			$" speaking="$S.WhoIsSpeaking()$" exits="$S.ExitEvents.Length$" who: "$Who);
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
}
