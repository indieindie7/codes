//=============================================================================
// U2SkipScenes - the scenes-only version of U2SkipCutscenes: press Space (or
// Fire) during a letterboxed cutscene to fast-forward it (dialogue inside the
// cutscene included). Conversations you can walk around in are left alone.
// Generated from U2SkipCutscenes/SkipCutscenes.uc with bSkipConversations=False;
// install one or the other, not both.
//
// Tunable in User.ini under [U2SkipScenes.SkipScenes].
//=============================================================================
class SkipScenes extends Mutator
	config(User);

var config float SkipSpeed;          // how much faster time runs while skipping
var config float MinSceneTime;       // ignore presses in the first moments of a scene
var config bool bMuteWhileSkipping;
var config bool bShowPrompt;
var config bool bSkipConversations;  // also skip conversations you can walk around in (not just cutscenes)         // "Press SPACE to skip" while a scene plays (UIScripts\SkipCutscenes.ui)
var config bool bMutedBySkip;        // set while muted, so a crash mid-skip can be undone next launch
var config float SavedSoundVolume;

var PlayerController PC;
var bool bInScene, bSkipping, bWasPressed, bShowing, bWasOnGround;
var float SceneTime, OldTimeDilation;
var ComponentHandle Prompt;
var DialogEngine DE;
var bool OldAllowSlomo;
var array<DialogSession> Tail;       // conversations still running when a skipped scene ended
var float TailTime;
var bool bPendingRestore;
var float ChainTime;                 // real seconds since a skipped scene ended (-1 = not chaining)
var array<SceneManager> Chain;       // scenes skipped in the current chain (attract loops repeat scenes)
var array<DialogSession> TalkChain;  // conversation chunks skipped in the current chain
var float TalkChainTime;             // real seconds since a skipped conversation ended (-1 = not chaining)        // looked for a prompt left over from the previous map
var array<DialogSession> WatchSession;   // lines being fast-forwarded, to rescue their dropped actions
var array<DialogNode> WatchNode;
var array<SceneManager> SkippedScenes;   // scenes fast-forwarded this skip, to rescue unfired triggers            // sound was left muted by a previous game session

event PostBeginPlay()
{
	Super.PostBeginPlay();
	// the game closed while we had the sound muted: put it back as soon as a
	// player exists (console commands need one)
	bPendingRestore = bMutedBySkip;
}

function PlayerController FindPlayer()
{
	local Controller C;

	if (PC == None || PC.bDeleteMe)
	{
		PC = None;
		for (C = Level.ControllerList; C != None; C = C.NextController)
			if (PlayerController(C) != None)
				PC = PlayerController(C);
	}
	return PC;
}

function bool SkipPressed()
{
	return PC.bFire != 0 || PC.bAltFire != 0 || PC.bPressedJump;
}

event Tick(float DeltaTime)
{
	local bool bPressed, bScene, bTalk;
	local float RealDelta;
	local DialogSession Talk;

	if (FindPlayer() == None)
		return;
	if (bPendingRestore)
		RestoreSound();
	if (LevelMayChange())
	{
		// leaving the level mid-skip: put speed and sound back before the load
		if (bSkipping && Level.NextURL != "")
			StopSkipping();
		if (bShowing || ~Prompt)
		{
			bShowing = false;
			ShowPrompt(false);
		}
		return;
	}
	RealDelta = DeltaTime / FMax(Level.TimeDilation, 0.01);
	if (ChainTime >= 0)
		ChainTime += RealDelta;
	if (TalkChainTime >= 0)
		TalkChainTime += RealDelta;

	if (bSkipping)
	{
		RescueDroppedActions();
		RescueSceneTriggers();
		// conversations also count their gaps between lines on real time
		AdvanceDialogue(RealDelta * (SkipSpeed - 1));
		// the player has a decision to make: hand control back right away
		if (ChoicePending())
		{
			StopSkipping();
			return;
		}
		if (PC.bInterpolating)
		{
			// scenes play on real time (to stay in sync with their audio), which the
			// time scale alone doesn't speed up: move the running scene's playhead too
			AdvanceScenes(RealDelta * (SkipSpeed - 1));
			bInScene = true;
			PC.bPressedJump = false;
			return;
		}
		// a conversation started by the scene may still gate the level (e.g. a
		// locked door waits for its exit event): keep going until it's over
		if (bInScene)
		{
			CollectTail();
			bInScene = false;
		}
		if (!TailRunning(RealDelta))
			StopSkipping();
		return;
	}

	// something skippable: a cutscene, or a conversation the player is in while
	// no enemy is after them (never fast-forward a fight)
	bScene = PC.bInterpolating;
	Talk = None;
	if (!bScene)
		Talk = PlayerConversation();
	bTalk = bSkipConversations && Talk != None && !InDanger() && !ChoicePending();

	if (bScene || bTalk)
	{
		if (!bShowing)
		{
			bShowing = true;
			SceneTime = 0;
			bWasPressed = SkipPressed();   // a button already held from gameplay isn't a skip
			ShowPrompt(true);
			if (bScene)
				Log("U2SkipScenes: skippable scene started: "$RunningScene()$" (len "$RunningSceneLength()$"s)");
			else
				Log("U2SkipScenes: skippable conversation started: "$Talk.Topic);
		}
		SceneTime += RealDelta;
		bPressed = SkipPressed() || (bTalk && JustJumped());
		// scenes chained back to back (like the intro) keep skipping after one press
		if (bScene && ChainTime >= 0 && ChainTime < 1.5 && ChainAllows(RunningSceneManager()))
		{
			Log("U2SkipScenes: next scene follows straight on - skipping it too");
			bPressed = true;
			bWasPressed = false;
			SceneTime = MinSceneTime;
		}
		// a conversation told in several chunks keeps skipping after one press
		if (bTalk && TalkChainTime >= 0 && TalkChainTime < 3.0 && TalkChainAllows(Talk))
		{
			Log("U2SkipScenes: conversation continues - skipping the next part too");
			bPressed = true;
			bWasPressed = false;
			SceneTime = MinSceneTime;
		}
		if (bPressed && !bWasPressed && SceneTime >= MinSceneTime)
		{
			bInScene = bScene;
			Tail.Length = 0;
			TailTime = 0;
			if (bTalk)
			{
				Tail[0] = Talk;
				if (TalkChainTime < 0 || TalkChainTime >= 3.0)
					TalkChain.Length = 0;
				TalkChain[TalkChain.Length] = Talk;
			}
			TalkChainTime = -1;
			StartSkipping();
		}
		bWasPressed = bPressed;
		if (bScene)
			PC.bPressedJump = false;   // don't carry the jump into gameplay
	}
	else if (bShowing)
	{
		bShowing = false;
		ShowPrompt(false);
	}
}

// in normal play the player's movement consumes the Space press (bPressedJump)
// before we see it, so during conversations watch for the jump itself
function bool JustJumped()
{
	local bool bJumped;

	if (PC.Pawn == None)
		return false;
	bJumped = bWasOnGround && PC.Pawn.Physics == PHYS_Falling && PC.Pawn.Velocity.Z > 100;
	bWasOnGround = PC.Pawn.Physics == PHYS_Walking;
	return bJumped;
}

// a running conversation the player takes part in
function DialogSession PlayerConversation()
{
	local int i, j;

	if (DE == None)
		DE = class'DialogEngine'.static.GetInstance(Self);
	if (DE == None)
		return None;
	for (i = 0; i < DE.Sessions.Length; i++)
		if (DE.Sessions[i] != None && !DE.Sessions[i].bSessionFinished)
			for (j = 0; j < DE.Sessions[i].DControllers.Length; j++)
				if (DialogControllerPlayer(DE.Sessions[i].DControllers[j]) != None)
					return DE.Sessions[i];
	return None;
}

// is the dialogue tray showing choices for the player to pick from?
function bool ChoicePending()
{
	local int i, j;
	local DialogControllerPlayer DCP;

	if (DE == None)
		return false;
	for (i = 0; i < DE.DControllers.Length; i++)
	{
		DCP = DialogControllerPlayer(DE.DControllers[i]);
		if (DCP != None)
			for (j = 0; j < ArrayCount(DCP.bShown); j++)
				if (DCP.bShown[j] != 0)
					return true;
	}
	return false;
}

// any enemy currently targeting the player?
function bool InDanger()
{
	local Controller C;

	if (PC.Pawn == None)
		return false;
	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (C != PC && C.Pawn != None && C.Pawn.Health > 0 && C.ControllerEnemy == PC.Pawn)
			return true;
	return false;
}

// The UI layer outlives levels, so a prompt still showing when the map changes
// (or a save is loaded) would stay on screen. Searching the UI for it later is
// NOT safe (it can crash or deadlock during loads), so instead the prompt is
// hidden before anything can change the level: a travel is pending, or the game
// is paused (the menu is open, e.g. to load a save or quit).
function bool LevelMayChange()
{
	return Level.NextURL != "" || Level.Pauser != None;
}

function ShowPrompt(bool bShow)
{
	if (bShow && bShowPrompt && !(~Prompt))
	{
		// arrival/departure maps take Esc/Space themselves (Esc skips them natively)
		if (Level.Game != None && Level.Game.bCutsceneInputHandling)
			Prompt = class'UIConsole'.static.LoadComponent("SkipCutscenes", "SkipPromptEsc");
		else
			Prompt = class'UIConsole'.static.LoadComponent("SkipCutscenes", "SkipPrompt");
		if (~Prompt)
		{
			// owned by this mod (as weapons own their crosshairs) so the UI can
			// drop it when the level - and this actor - goes away
			class'UIConsole'.static.SetOwner(Prompt, Self);
			class'UIConsole'.static.AddComponent(Prompt);
		}
	}
	else if (!bShow && ~Prompt)
		Prompt = class'UIConsole'.static.DestroyComponent(Prompt);
}

// the SceneManager currently playing for the player
function SceneManager RunningSceneManager()
{
	local SceneManager SM;

	foreach AllActors(class'SceneManager', SM)
		if (SM.bIsRunning && SM.Viewer == PC)
			return SM;
	return None;
}

function string RunningScene()
{
	local SceneManager SM;

	SM = RunningSceneManager();
	if (SM == None)
		return "none";
	return string(SM.Name)$" looping="$SM.bLooping;
}

function float RunningSceneLength()
{
	local SceneManager SM;

	SM = RunningSceneManager();
	if (SM == None)
		return 0;
	return SM.TotalSceneTime;
}

function AdvanceScenes(float Extra)
{
	local SceneManager SM;
	local int i;
	local bool bKnown;

	// small steps, and never past the scene's last moment: the engine plays the
	// final frames itself, so its end-of-scene triggers still fire
	Extra = FMin(Extra, 0.25);
	foreach AllActors(class'SceneManager', SM)
		if (SM.bIsRunning && SM.Viewer == PC)
		{
			bKnown = false;
			for (i = 0; i < SkippedScenes.Length; i++)
				if (SkippedScenes[i] == SM)
					bKnown = true;
			if (!bKnown)
				SkippedScenes[SkippedScenes.Length] = SM;
			if (SM.CurrentTime + Extra < SM.TotalSceneTime - 0.1)
				SM.CurrentTime += Extra;
		}
}

// a scene we sped up has ended: fire any trigger / console command it never got to
function RescueSceneTriggers()
{
	local int i, j;
	local SceneManager SM;
	local MatSubAction SA;

	for (i = SkippedScenes.Length - 1; i >= 0; i--)
	{
		SM = SkippedScenes[i];
		if (SM != None && SM.bIsRunning)
			continue;
		if (SM != None)
			for (j = 0; j < SM.SubActions.Length; j++)
			{
				SA = SM.SubActions[j];
				if (SA == None || SA.Status != SASTATUS_Waiting)
					continue;
				if (SubActionTrigger(SA) != None && SubActionTrigger(SA).EventName != '')
				{
					Log("U2SkipScenes: rescuing skipped scene trigger "$SubActionTrigger(SA).EventName);
					SA.Status = SASTATUS_Expired;
					SM.TriggerEvent(SubActionTrigger(SA).EventName, SM, None);
				}
				else if (SubActionConsoleCommand(SA) != None && SubActionConsoleCommand(SA).Command != "")
				{
					Log("U2SkipScenes: rescuing skipped scene command "$SubActionConsoleCommand(SA).Command);
					SA.Status = SASTATUS_Expired;
					PC.ConsoleCommand(SubActionConsoleCommand(SA).Command);
				}
			}
		SkippedScenes.Remove(i, 1);
	}
}

// At high speed a line's end timer and its timed actions (NPC unpause, events,
// animations) can expire in the same frame; if the line ends first, the game
// starts the next line and silently drops the rest - e.g. a cutscene actor stays
// paused forever and never cleans itself up. Fire those leftovers right away.
function RescueDroppedActions()
{
	local int i, j;
	local bool bFound;
	local DialogSession S;

	if (DE == None)
		return;
	// sessions we were watching: did they move to a new line (or end)?
	for (i = WatchSession.Length - 1; i >= 0; i--)
	{
		S = WatchSession[i];
		bFound = false;
		for (j = 0; j < DE.Sessions.Length; j++)
			if (DE.Sessions[j] == S)
				bFound = true;
		if (!bFound || S == None || S.CurNode != WatchNode[i])
		{
			if (WatchNode[i] != None && WatchNode[i].NumPendingActions() > 0 && S != None)
				ForceActions(WatchNode[i], S);
			WatchSession.Remove(i, 1);
			WatchNode.Remove(i, 1);
		}
	}
	// start watching current lines
	for (j = 0; j < DE.Sessions.Length; j++)
	{
		S = DE.Sessions[j];
		if (S == None || S.CurNode == None)
			continue;
		bFound = false;
		for (i = 0; i < WatchSession.Length; i++)
			if (WatchSession[i] == S)
				bFound = true;
		if (!bFound)
		{
			WatchSession[WatchSession.Length] = S;
			WatchNode[WatchNode.Length] = S.CurNode;
		}
	}
}

// process every still-pending action of node N now, leaving the node's data as it was
function ForceActions(DialogNode N, DialogSession S)
{
	local int i;
	local array<float> A, B, C, D, E;

	Log("U2SkipScenes: rescuing "$N.NumPendingActions()$" dropped dialogue action(s) from "$N.Name);
	for (i = 0; i < N.NodeEvents.Length; i++)  { A[i] = N.NodeEvents[i].PercentDelay;  N.NodeEvents[i].PercentDelay = -1000; }
	for (i = 0; i < N.NodeAnims.Length; i++)   { B[i] = N.NodeAnims[i].PercentDelay;   N.NodeAnims[i].PercentDelay = -1000; }
	for (i = 0; i < N.NPCControls.Length; i++) { C[i] = N.NPCControls[i].PercentDelay; N.NPCControls[i].PercentDelay = -1000; }
	for (i = 0; i < N.Satellites.Length; i++)  { D[i] = N.Satellites[i].PercentDelay;  N.Satellites[i].PercentDelay = -1000; }
	for (i = 0; i < N.Gestures.Length; i++)    { E[i] = N.Gestures[i].PercentDelay;    N.Gestures[i].PercentDelay = -1000; }
	N.ProcessActions(S);
	for (i = 0; i < N.NodeEvents.Length; i++)  N.NodeEvents[i].PercentDelay = A[i];
	for (i = 0; i < N.NodeAnims.Length; i++)   N.NodeAnims[i].PercentDelay = B[i];
	for (i = 0; i < N.NPCControls.Length; i++) N.NPCControls[i].PercentDelay = C[i];
	for (i = 0; i < N.Satellites.Length; i++)  N.Satellites[i].PercentDelay = D[i];
	for (i = 0; i < N.Gestures.Length; i++)    N.Gestures[i].PercentDelay = E[i];
}

function AdvanceDialogue(float Extra)
{
	local int i;

	if (DE == None)
		return;
	for (i = 0; i < DE.Sessions.Length; i++)
		if (DE.Sessions[i] != None && !DE.Sessions[i].bSessionFinished)
			DE.Sessions[i].TimeElapsed += Extra;
}

function CollectTail()
{
	local int i;

	Tail.Length = 0;
	TailTime = 0;
	if (DE == None)
		return;
	for (i = 0; i < DE.Sessions.Length; i++)
		if (DE.Sessions[i] != None && !DE.Sessions[i].bSessionFinished)
			Tail[Tail.Length] = DE.Sessions[i];
}

function bool TailRunning(float DeltaTime)
{
	local int i, j;
	local bool bStillThere;

	TailTime += DeltaTime;   // real seconds
	if (TailTime > 30)
		return false;   // safety net: never fast-forward gameplay for long
	for (i = 0; i < Tail.Length; i++)
	{
		bStillThere = false;
		for (j = 0; j < DE.Sessions.Length; j++)
			if (DE.Sessions[j] == Tail[i])
				bStillThere = true;
		if (bStillThere && Tail[i] != None && !Tail[i].bSessionFinished)
			return true;
	}
	return false;
}

// follow-on scenes are only skipped automatically if they're new: a scene that
// repeats or loops (like the intro's attract loop, which waits for Escape) ends
// the chain, and a chain never runs longer than 6 scenes
function bool TalkChainAllows(DialogSession S)
{
	local int i;

	if (S == None || TalkChain.Length >= 6)
		return false;
	for (i = 0; i < TalkChain.Length; i++)
		if (TalkChain[i] == S)
			return false;
	return true;
}

function bool ChainAllows(SceneManager SM)
{
	local int i;

	if (SM == None || SM.bLooping || Chain.Length >= 6)
		return false;
	for (i = 0; i < Chain.Length; i++)
		if (Chain[i] == SM)
			return false;
	return true;
}

function StartSkipping()
{
	local float Volume;
	local SceneManager SM;

	// a manual press starts a new chain; an automatic follow-on extends it
	if (ChainTime < 0 || ChainTime >= 1.5)
		Chain.Length = 0;
	SM = RunningSceneManager();
	if (SM != None)
		Chain[Chain.Length] = SM;
	ChainTime = -1;
	bSkipping = true;
	bShowing = false;
	ShowPrompt(false);
	// let dialogue lines fast-forward too (the game otherwise stretches lines to
	// keep real-time sync with the voice audio while a cutscene is sped up)
	DE = class'DialogEngine'.static.GetInstance(Self);
	if (DE != None)
	{
		OldAllowSlomo = DE.AllowSlomo;
		DE.AllowSlomo = true;
	}
	OldTimeDilation = Level.TimeDilation;
	Level.TimeDilation = SkipSpeed;
	if (bMuteWhileSkipping && !bMutedBySkip && !bPendingRestore)
	{
		Volume = float(PC.ConsoleCommand("get ini:Engine.Engine.AudioDevice SoundVolume"));
		if (Volume > 0)   // sound already off (or no audio device): nothing to mute or restore
		{
			SavedSoundVolume = Volume;
			bMutedBySkip = true;
			SaveConfig();   // before muting, so a crash mid-skip can be undone next launch
			PC.ConsoleCommand("set ini:Engine.Engine.AudioDevice SoundVolume 0");
		}
	}
	Log("U2SkipScenes: skipping scene (x"$SkipSpeed$") fire="$PC.bFire$" alt="$PC.bAltFire$" jump="$PC.bPressedJump$" after "$SceneTime$"s");
}

function StopSkipping()
{
	bSkipping = false;
	// a finished skip can chain into what follows - but never past a choice
	if (!ChoicePending())
	{
		if (bInScene || !PC.bInterpolating)
			ChainTime = 0;
		if (Tail.Length > 0 || TalkChain.Length > 0)
			TalkChainTime = 0;
	}
	RescueDroppedActions();
	RescueSceneTriggers();
	WatchSession.Length = 0;
	WatchNode.Length = 0;
	Tail.Length = 0;
	Level.TimeDilation = FMax(OldTimeDilation, 1.0);
	if (DE != None)
		DE.AllowSlomo = OldAllowSlomo;
	if (bMutedBySkip)
		RestoreSound();
	Log("U2SkipScenes: scene over, back to normal speed");
}

function RestoreSound()
{
	if (FindPlayer() == None)
	{
		bPendingRestore = true;   // retried from Tick once a player exists
		return;
	}
	if (SavedSoundVolume > 0)
		PC.ConsoleCommand("set ini:Engine.Engine.AudioDevice SoundVolume "$SavedSoundVolume);
	bMutedBySkip = false;
	bPendingRestore = false;
	SaveConfig();
	Log("U2SkipScenes: sound volume restored to "$SavedSoundVolume);
}

event Destroyed()
{
	ShowPrompt(false);
	if (bSkipping)
		StopSkipping();
	Super.Destroyed();
}

defaultproperties
{
	SkipSpeed=12.000000
	MinSceneTime=0.500000
	bMuteWhileSkipping=True
	ChainTime=-1.000000
	TalkChainTime=-1.000000
	bShowPrompt=True
	bSkipConversations=False
	RemoteRole=ROLE_None
}
