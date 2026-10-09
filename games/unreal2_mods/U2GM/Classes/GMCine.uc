//=============================================================================
// GMCine - a transport for Unreal II's cinematics (Matinee SceneManagers):
// pause, play, stop, seek, step and speed, from the console or the d3d8
// fork's panel ("gm cine ..." q-lines). Design: games/research_notes/
// Cinematic transport/design.md.
//
//   gm cine [status]      what plays: scene, time, length, world head, speed
//   gm cine pause | play | toggle
//   gm cine stop          finish the scene now (fast-forwarded, muted: every event still fires)
//   gm cine seek T        T at or before the world head: the camera only (the world stays paused);
//                         past the head: the world runs there (fast and muted if far), then pauses
//   gm cine step [DT]     one step (StepTime, negative goes back)
//   gm cine speed S       0.05..16; above 1.5 voices are muted and dialogue keeps up
//   gm cine release       let go: unpause, normal speed, sound back
//   gm cine auto 1|0      pause by itself when the console opens during a scene
//
// How it works (Engine.dll decompiled: ASceneManager::Tick, UMatSubAction::Update):
// - The scene clock is SceneManager.CurrentTime, advanced natively by DeltaTime * SceneSpeed;
//   camera and sub actions are re-evaluated from it every tick, so setting it is a seek.
//   SubActionSceneSpeed rewrites SceneSpeed while it runs, so a hold rewrites 0 every tick.
// - Sub actions only go forward (Waiting -> Running -> Ending -> Expired): a jump forward fires
//   every skipped trigger on the next tick; a jump back fires nothing again. The world (NPCs,
//   dialogue, doors, spawns) is driven by those triggers and can't be rewound, so anything
//   before the "world head" (the furthest time the world has played) is a camera preview.
// - Pause = the game's own pause (GameInfo.SetPause with our lock key: Pauser + PauseAudio).
//   Paused, only bAlwaysTick actors tick: this actor, and the held SceneManager (set through
//   SetPropertyText, bAlwaysTick is const) so its camera follows seeks. GMMaster's timer is
//   frozen too, so while we hold the pause we exec the panel's file and save PanelState here.
// - CineState (this ini section) tells the fork's panel what plays, for the transport bar.
//=============================================================================
class GMCine extends Info
	config(U2GM);

const CineKey = 4141;       // our SetPause lock (U2's menus use 314, 278 and 777)

const M_IDLE = 0;           // not holding a scene (one may still play, untouched)
const M_LIVE = 1;           // holding it, the world runs (speed applies)
const M_PAUSED = 2;         // game paused, the camera held at PinT
const M_PREVIEW = 3;        // game paused, the camera replays from PinT up to the world head
const M_RUN = 4;            // the world runs to RunTarget (fast and muted when far), then pauses or plays

var config float FastSpeed;     // stop / far seeks run this many times faster
var config float FastFrom;      // a run further than this (seconds) past the head goes fast
var config float StepTime;      // gm cine step without a number
var config bool bAutoPause;     // the console opens during a scene: pause
var config bool bResumeOnClose; // the console closes after an automatic pause (nothing pressed): play
var config bool bPauseMusic;    // a pause stops the music as well
var config bool bMuteFast;      // mute while running fast
var config bool bMutedByCine;   // set while muted, so a crash mid-run can be undone next time
var config float SavedSoundVolume;
var config string CineState;    // for the fork: "seq=N st=... scene=NAME t=T len=L head=H spd=S loop=0|1 ev=t,t,..."

var GMMaster Master;
var PlayerController PC;
var SceneManager SM;            // the scene the transport holds
var SceneManager Watched;       // the scene playing for the player (held or not)
var int CMode;
var float PinT;                 // the camera's time while paused / previewing
var float WHead;                 // the furthest the world has played in this scene
var float CSpeed;                // the user's speed
var float SceneBase;                 // the scene's own SceneSpeed
var float RunTarget, LastCT;
var bool bRunThenPause, bRunFast, bRanFast, bFastOn;
var bool bWePaused, bAutoPaused, bWasCon, bPendingRestore;
var bool bTDHeld;
var float AuthoredTD, OurTD;
var DialogEngine DE;
var bool OldAllowSlomo;
var float PumpWait, StateWait, SearchWait;
var int StateSeq;
var string LastKey, EvList;
var SceneManager EvScene;
var array<DialogSession> WatchSession;   // lines being fast-forwarded, to rescue their dropped actions
var array<DialogNode> WatchNode;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	CSpeed = 1;
	bPendingRestore = bMutedByCine;   // the game closed while we had the sound muted
}

event Tick(float DeltaTime)
{
	local float RealDelta;
	local bool bCon;

	if (Master == None || Master.bDeleteMe)
		return;
	PC = Master.PC;
	if (PC == None)
		return;
	if (bPendingRestore)
		RestoreSound();
	RealDelta = DeltaTime / FMax(Level.TimeDilation, 0.01);
	if (Level.NextURL != "")
	{
		if (SM != None)
			Unhold();
		return;
	}
	if (SM != None && (SM.bDeleteMe || !SM.bIsRunning || SM.Viewer != PC))
		SceneOver();
	FindWatched(RealDelta);
	bCon = Master.bConBig || Master.bConQuick;
	if (bCon != bWasCon)
	{
		bWasCon = bCon;
		ConChanged(bCon);
		StateWait = 0;
	}
	if (SM != None)
		Drive(RealDelta);
	if (bWePaused)
		Pump(RealDelta);
	StateWait -= RealDelta;
	if (StateWait <= 0)
	{
		StateWait = 0.25;
		WriteState();
	}
}

// ---- the scene

function FindWatched(float RealDelta)
{
	local SceneManager S;

	if (SM != None)
	{
		Watched = SM;
		return;
	}
	if (Watched != None && !Watched.bDeleteMe && Watched.bIsRunning && Watched.Viewer == PC)
		return;
	Watched = None;
	if (!PC.bInterpolating)
		return;
	SearchWait -= RealDelta;
	if (SearchWait > 0)
		return;
	SearchWait = 0.25;
	foreach AllActors(class'SceneManager', S)
		if (S.bIsRunning && S.Viewer == PC)
			Watched = S;
}

// U2SkipCutscenes / U2SkipScenes fast-forwarding right now: leave the scene to them
function bool SkipBusy()
{
	local Mutator M;

	foreach DynamicActors(class'Mutator', M)
		if ((M.IsA('SkipCutscenes') || M.IsA('SkipScenes')) && M.GetPropertyText("bSkipping") ~= "True")
			return true;
	return false;
}

// take hold of the playing scene (true: SM is set)
function bool Hold()
{
	if (SM != None)
		return true;
	if (Watched == None)
	{
		CineSay("no cinematic is playing");
		return false;
	}
	if (SkipBusy())
	{
		CineSay("U2SkipCutscenes is fast-forwarding this scene");
		return false;
	}
	SM = Watched;
	SceneBase = SM.SceneSpeed;
	if (SceneBase <= 0)
		SceneBase = 1;
	WHead = SM.CurrentTime;
	PinT = WHead;
	LastCT = WHead;
	CMode = M_LIVE;
	bRanFast = false;
	EvScene = None;
	Log("GM: cine holds "$SM.Name$" at "$F2(WHead)$" of "$F2(SM.TotalSceneTime)$"s");
	return true;
}

function CaptureBase()
{
	if (SM.SceneSpeed > 0)
		SceneBase = SM.SceneSpeed;
}

// the game's pause, with our lock (menus and Fire can't undo it), and the held scene ticking through it
function Freeze(bool B)
{
	if (B)
	{
		if (!bWePaused)
		{
			if (Level.Pauser != None)
				CineSay("the game is paused already: holding the camera only");
			else
			{
				Level.Game.SetPause(true, PC, CineKey);
				bWePaused = Level.Pauser != None;
				if (bWePaused && bPauseMusic)
					PauseAudio(true);
				if (!bWePaused)
					CineSay("the game wouldn't pause: holding the camera only");
			}
		}
		if (SM != None && !SM.bDeleteMe)
		{
			CaptureBase();
			SM.SetPropertyText("bAlwaysTick", "True");
			SM.SceneSpeed = 0;
		}
		PumpWait = 0;
	}
	else
	{
		if (bWePaused)
		{
			Level.Game.SetPause(false, PC, CineKey);
			bWePaused = false;
		}
		if (SM != None && !SM.bDeleteMe)
		{
			SM.SetPropertyText("bAlwaysTick", "False");
			SM.SceneSpeed = SceneBase;
		}
	}
}

function Drive(float RealDelta)
{
	if (CMode == M_LIVE)
	{
		CaptureBase();
		WHead = FMax(WHead, SM.CurrentTime);
		if (CSpeed != 1)
		{
			HoldTD(CSpeed);
			Fast(CSpeed > 1.5);
			Pace(RealDelta, CSpeed);
			if (bFastOn)
			{
				AdvanceDialogue(RealDelta * (CSpeed - 1));
				RescueDroppedActions();
			}
		}
		LastCT = SM.CurrentTime;
	}
	else if (CMode == M_PAUSED)
	{
		CaptureBase();
		SM.SceneSpeed = 0;
		SM.CurrentTime = PinT;
	}
	else if (CMode == M_PREVIEW)
	{
		CaptureBase();
		SM.SceneSpeed = 0;
		PinT += RealDelta * CSpeed * SceneBase;
		if (PinT >= WHead)
		{
			PinT = WHead;
			SM.CurrentTime = WHead;
			GoLive();
		}
		else
			SM.CurrentTime = PinT;
	}
	else if (CMode == M_RUN)
	{
		CaptureBase();
		if (bRunFast)
		{
			HoldTD(FastSpeed);
			Fast(true);
			Pace(RealDelta, FastSpeed);
			AdvanceDialogue(RealDelta * (FastSpeed - 1));
			RescueDroppedActions();
		}
		WHead = FMax(WHead, SM.CurrentTime);
		LastCT = SM.CurrentTime;
		if (SM.CurrentTime >= RunTarget - 0.001)
		{
			EndRun();
			if (bRunThenPause)
			{
				PinT = SM.CurrentTime;
				Freeze(true);
				CMode = M_PAUSED;
			}
			else
				GoLive();
		}
	}
}

// keep the scene's clock at Rate x its own speed, however the engine scales a scene's time
// (U2SkipCutscenes found game speed alone doesn't speed scenes up; the decompile says it should)
function Pace(float RealDelta, float Rate)
{
	local float Want, Got, T;

	Want = RealDelta * Rate * SceneBase;
	Got = SM.CurrentTime - LastCT;
	if (Got < Want * 0.8)
		T = SM.CurrentTime + FMin(Want - Got, 0.25);
	else if (Rate < 1 && Got > Want * 1.25)
		T = LastCT + Want;
	else
		return;
	// never past the last moment: the engine plays the end itself, so its end events fire
	T = FMin(T, SM.TotalSceneTime - 0.1);
	if (T > LastCT)
		SM.CurrentTime = T;
}

// the world's speed: the scene's own (SubActionGameSpeed) times ours
function HoldTD(float S)
{
	if (!bTDHeld)
	{
		AuthoredTD = Level.TimeDilation;
		bTDHeld = true;
	}
	else if (Level.TimeDilation != OurTD)
		AuthoredTD = Level.TimeDilation;
	OurTD = AuthoredTD * S;
	Level.TimeDilation = OurTD;
}

function FreeTD()
{
	if (!bTDHeld)
		return;
	if (Level.TimeDilation == OurTD)
		Level.TimeDilation = AuthoredTD;
	bTDHeld = false;
}

// fast: voices muted, dialogue lines allowed to speed up (U2SkipCutscenes' method)
function Fast(bool B)
{
	if (B == bFastOn)
		return;
	bFastOn = B;
	if (B)
	{
		DE = class'DialogEngine'.static.GetInstance(Self);
		if (DE != None)
		{
			OldAllowSlomo = DE.AllowSlomo;
			DE.AllowSlomo = true;
		}
		if (bMuteFast)
			Mute();
		bRanFast = true;
	}
	else
	{
		RescueDroppedActions();
		WatchSession.Length = 0;
		WatchNode.Length = 0;
		if (DE != None)
			DE.AllowSlomo = OldAllowSlomo;
		if (bMutedByCine)
			RestoreSound();
	}
}

function GoLive()
{
	Freeze(false);
	CMode = M_LIVE;
	LastCT = SM.CurrentTime;
}

function EndRun()
{
	Fast(false);
	FreeTD();
	bRunFast = false;
}

function RunTo(float T, bool bThenPause, bool bForceFast)
{
	if (CMode == M_PAUSED || CMode == M_PREVIEW)
	{
		// the world is at the head: the camera goes back there first
		if (SM.CurrentTime < WHead)
		{
			PinT = WHead;
			SM.CurrentTime = WHead;
		}
		Freeze(false);
	}
	EndRun();
	RunTarget = T;
	bRunThenPause = bThenPause;
	bRunFast = bForceFast || T - FMax(WHead, SM.CurrentTime) > FastFrom;
	CMode = M_RUN;
	LastCT = SM.CurrentTime;
}

// a jump back: camera sub actions (orientation, FOV, fade, scene speed) evaluate again from
// the start, so the camera at T is right; triggers and console commands stay done
function RewindCamera()
{
	local int i;
	local MatSubAction SA;

	for (i = 0; i < SM.SubActions.Length; i++)
	{
		SA = SM.SubActions[i];
		if (SA == None)
			continue;
		if (SubActionOrientation(SA) != None || SubActionFOV(SA) != None || SubActionFade(SA) != None || SubActionSceneSpeed(SA) != None)
			SA.Status = SASTATUS_Waiting;
	}
}

// the held scene is over (or gone)
function SceneOver()
{
	local SceneManager S;

	S = SM;
	EndRun();
	if (bWePaused)
		Freeze(false);
	if (S != None && !S.bDeleteMe)
	{
		S.SetPropertyText("bAlwaysTick", "False");
		if (S.SceneSpeed == 0)
			S.SceneSpeed = SceneBase;
		if (bRanFast)
			RescueSceneTriggers(S);
	}
	if (S != None)
		Log("GM: cine scene over: "$S.Name);
	SM = None;
	Watched = None;
	CMode = M_IDLE;
	CSpeed = 1;
	bAutoPaused = false;
	StateWait = 0;
}

// let go of the scene where it is: it plays on as the game made it
function Unhold()
{
	EndRun();
	if (bWePaused || CMode == M_PAUSED || CMode == M_PREVIEW)
	{
		if (SM != None && !SM.bDeleteMe && SM.CurrentTime < WHead)
			SM.CurrentTime = WHead;
		Freeze(false);
	}
	if (SM != None && !SM.bDeleteMe)
	{
		SM.SetPropertyText("bAlwaysTick", "False");
		if (SM.SceneSpeed == 0)
			SM.SceneSpeed = SceneBase;
	}
	SM = None;
	CMode = M_IDLE;
	CSpeed = 1;
	bAutoPaused = false;
	StateWait = 0;
}

// ---- the transport

function DoPause()
{
	if (!Hold())
		return;
	if (CMode == M_RUN || CMode == M_LIVE)
	{
		EndRun();
		WHead = FMax(WHead, SM.CurrentTime);
		PinT = SM.CurrentTime;
	}
	Freeze(true);
	CMode = M_PAUSED;
}

function DoPlay()
{
	if (!Hold())
		return;
	if (CMode == M_RUN || CMode == M_LIVE)
		return;
	if (PinT < WHead - 0.05)
		CMode = M_PREVIEW;     // the camera replays to the head, the world waits there
	else
		GoLive();
}

function DoStop()
{
	if (!Hold())
		return;
	RunTo(SM.TotalSceneTime + 1, false, true);
}

function Seek(float T)
{
	local bool bWasPlaying;

	if (!Hold())
		return;
	T = FClamp(T, 0, FMax(SM.TotalSceneTime - 0.1, 0));
	if (T > WHead + 0.01)
	{
		RunTo(T, !(CMode == M_LIVE || (CMode == M_RUN && !bRunThenPause)), false);
		return;
	}
	bWasPlaying = CMode == M_LIVE || CMode == M_PREVIEW || (CMode == M_RUN && !bRunThenPause);
	if (CMode == M_LIVE || CMode == M_RUN)
	{
		EndRun();
		WHead = FMax(WHead, SM.CurrentTime);
		Freeze(true);
	}
	if (T < SM.CurrentTime - 0.001)
		RewindCamera();
	PinT = T;
	SM.CurrentTime = T;
	if (bWasPlaying)
		CMode = M_PREVIEW;
	else
		CMode = M_PAUSED;
}

function Step(float DT)
{
	if (!Hold())
		return;
	if (CMode != M_PAUSED)
		DoPause();
	Seek(PinT + DT);
}

function SetSpeed(float S)
{
	if (S <= 0)
	{
		CineSay("speed "$F2(CSpeed)$" (gm cine speed 0.05..16)");
		return;
	}
	CSpeed = FClamp(S, 0.05, 16);
	if (CSpeed == 1 && CMode == M_LIVE)
	{
		Fast(false);
		FreeTD();
	}
	if (Watched != None && SM == None && CSpeed != 1)
		Hold();
}

function Command(string Args)
{
	local string C, A1;

	C = Locs(class'GMMaster'.static.Word(Args, 0));
	A1 = class'GMMaster'.static.Word(Args, 1);
	if (C == "" || C == "status")
	{
		ShowStatus();
		return;
	}
	if (C == "auto")
	{
		bAutoPause = A1 != "0";
		SaveConfig();
		CineSay("auto pause on console "$PickS(bAutoPause, "on", "off"));
		return;
	}
	bAutoPaused = false;    // the user took over: the console closing changes nothing
	if (C == "pause")
		DoPause();
	else if (C == "play")
		DoPlay();
	else if (C == "toggle")
	{
		if (CMode == M_PAUSED)
			DoPlay();
		else
			DoPause();
	}
	else if (C == "stop")
		DoStop();
	else if (C == "seek")
		Seek(float(A1));
	else if (C == "step")
	{
		if (A1 == "")
			Step(StepTime);
		else
			Step(float(A1));
	}
	else if (C == "speed")
		SetSpeed(float(A1));
	else if (C == "release" || C == "off")
		Unhold();
	else
	{
		CineSay("gm cine [status] | pause | play | toggle | stop | seek T | step [DT] | speed S | release | auto 1|0");
		return;
	}
	StateWait = 0;
	if (C != "seek")
		ShowStatus();
}

function ShowStatus()
{
	local SceneManager W;

	W = Watched;
	if (SM != None)
		W = SM;
	if (W == None)
	{
		CineSay("cine: none playing");
		return;
	}
	CineSay("cine: "$ModeName()$" "$W.Name$" "$F2(CurT(W))$" / "$F2(W.TotalSceneTime)$"s, world at "$F2(HeadT(W))$", speed "$F2(CSpeed)$PickS(W.bLooping, " (looping)", ""));
}

// ---- the console

// each Console.ui trigger as an event (GMMaster's "gm con"): an open pauses even when con= was stuck at open
// from a missed close (Avalon Q72, 2026-10-08); the Tick's change test stays for the panel's own state
function ConEvent(bool bOpen)
{
	bWasCon = Master.bConBig || Master.bConQuick;
	ConChanged(bOpen);
	StateWait = 0;
}

function ConChanged(bool bCon)
{
	if (bCon)
	{
		if (bAutoPause && Watched != None && (CMode == M_IDLE || CMode == M_LIVE) && Level.Pauser == None && !SkipBusy())
		{
			DoPause();
			bAutoPaused = CMode == M_PAUSED;
		}
	}
	else
	{
		if (bAutoPaused && bResumeOnClose && CMode == M_PAUSED)
			DoPlay();
		bAutoPaused = false;
	}
}

// while we hold the game paused GMMaster's timer is frozen: run the panel's lines and keep
// PanelState (q-line acks, con=) fresh from here
function Pump(float RealDelta)
{
	PumpWait -= RealDelta;
	if (PumpWait > 0)
		return;
	PumpWait = 0.25;
	if (Master.PanelPoll > 0 && Master.PanelFile != "")
		PC.ConsoleCommand("exec "$Master.PanelFile);
	Master.SaveState();
}

// ---- what the panel shows

function string ModeName()
{
	if (SM == None)
		return "free";
	if (CMode == M_LIVE)
		return "play";
	if (CMode == M_PAUSED)
		return "pause";
	if (CMode == M_PREVIEW)
		return "preview";
	if (CMode == M_RUN)
		return PickS(bRunFast, "ff", "run");
	return "free";
}

function float CurT(SceneManager W)
{
	if (W == SM && (CMode == M_PAUSED || CMode == M_PREVIEW))
		return PinT;
	return W.CurrentTime;
}

function float HeadT(SceneManager W)
{
	if (W == SM)
		return FMax(WHead, W.CurrentTime);
	return W.CurrentTime;
}

// the times the scene fires events (triggers, console commands), for marks on the slider
function string Events(SceneManager W)
{
	local int i, n;
	local MatSubAction SA;

	if (W == EvScene)
		return EvList;
	EvScene = W;
	EvList = "";
	for (i = 0; i < W.SubActions.Length && n < 24; i++)
	{
		SA = W.SubActions[i];
		if (SA != None && (SubActionTrigger(SA) != None || SubActionConsoleCommand(SA) != None))
		{
			if (n > 0)
				EvList = EvList$",";
			EvList = EvList$F2(SA.PctStarting * W.TotalSceneTime);
			n++;
		}
	}
	if (EvList == "")
		EvList = "-";
	return EvList;
}

function WriteState()
{
	local SceneManager W;
	local string Key, S;
	local bool bCon;

	W = Watched;
	if (SM != None)
		W = SM;
	bCon = Master.bConBig || Master.bConQuick;
	if (W == None)
		Key = "st=none";
	else
		Key = "st="$ModeName()$" scene="$W.Name$" len="$F2(W.TotalSceneTime)$" spd="$F2(CSpeed)$" loop="$PickS(W.bLooping, "1", "0")$" ev="$Events(W);
	// the time only matters while someone looks (console open) or we hold the scene:
	// otherwise write on changes only, not four times a second through every cutscene
	if (!bCon && SM == None && Key == LastKey)
		return;
	LastKey = Key;
	if (W == None)
		S = Key;
	else
		S = Key$" t="$F2(CurT(W))$" head="$F2(HeadT(W));
	StateSeq++;
	S = "seq="$StateSeq$" "$S;
	if (S == CineState)
		return;
	CineState = S;
	SaveConfig();
}

// ---- rescue (from U2SkipCutscenes): what a fast run can make the game miss

function AdvanceDialogue(float Extra)
{
	local int i;

	if (DE == None)
		return;
	for (i = 0; i < DE.Sessions.Length; i++)
		if (DE.Sessions[i] != None && !DE.Sessions[i].bSessionFinished)
			DE.Sessions[i].TimeElapsed += Extra;
}

// a scene run fast has ended: fire any trigger / console command it never got to
function RescueSceneTriggers(SceneManager S)
{
	local int j;
	local MatSubAction SA;

	for (j = 0; j < S.SubActions.Length; j++)
	{
		SA = S.SubActions[j];
		if (SA == None || SA.Status != SASTATUS_Waiting)
			continue;
		if (SubActionTrigger(SA) != None && SubActionTrigger(SA).EventName != '')
		{
			Log("GM: cine rescues skipped scene trigger "$SubActionTrigger(SA).EventName);
			SA.Status = SASTATUS_Expired;
			S.TriggerEvent(SubActionTrigger(SA).EventName, S, None);
		}
		else if (SubActionConsoleCommand(SA) != None && SubActionConsoleCommand(SA).Command != "")
		{
			Log("GM: cine rescues skipped scene command "$SubActionConsoleCommand(SA).Command);
			SA.Status = SASTATUS_Expired;
			PC.ConsoleCommand(SubActionConsoleCommand(SA).Command);
		}
	}
}

// at high speed a line's end and its timed actions can expire in one frame and the game drops
// the actions (an NPC stays paused forever): fire the leftovers when a line moves on
function RescueDroppedActions()
{
	local int i, j;
	local bool bFound;
	local DialogSession S;

	if (DE == None)
		return;
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

function ForceActions(DialogNode N, DialogSession S)
{
	local int i;
	local array<float> A, B, C, D, E;

	Log("GM: cine rescues "$N.NumPendingActions()$" dropped dialogue action(s) from "$N.Name);
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

// ---- sound (ini volume, as U2SkipCutscenes: restored next launch if the game dies muted)

function Mute()
{
	local float Volume;

	if (bMutedByCine || bPendingRestore)
		return;
	Volume = float(PC.ConsoleCommand("get ini:Engine.Engine.AudioDevice SoundVolume"));
	if (Volume <= 0)
		return;
	SavedSoundVolume = Volume;
	bMutedByCine = true;
	SaveConfig();
	PC.ConsoleCommand("set ini:Engine.Engine.AudioDevice SoundVolume 0");
}

function RestoreSound()
{
	if (PC == None)
	{
		bPendingRestore = true;
		return;
	}
	if (SavedSoundVolume > 0)
		PC.ConsoleCommand("set ini:Engine.Engine.AudioDevice SoundVolume "$SavedSoundVolume);
	bMutedByCine = false;
	bPendingRestore = false;
	SaveConfig();
}

// ---- small things

function CineSay(coerce string S)
{
	if (Master != None)
		Master.Say(S);
	else
		Log("GM: "$S);
}

static function string PickS(bool B, string IfTrue, string IfFalse)
{
	if (B)
		return IfTrue;
	return IfFalse;
}

static function string F2(float V)
{
	local int I, Fr;
	local string S;

	if (V < 0)
		return "-"$F2(-V);
	I = int(V * 100 + 0.5);
	Fr = I - (I / 100) * 100;
	S = string(Fr);
	if (Fr < 10)
		S = "0"$S;
	return string(I / 100)$"."$S;
}

event Destroyed()
{
	if (SM != None)
		Unhold();
	if (bMutedByCine)
		RestoreSound();
	Super.Destroyed();
}

defaultproperties
{
	FastSpeed=10.000000
	FastFrom=1.500000
	StepTime=0.100000
	bAutoPause=True
	bResumeOnClose=True
	bPauseMusic=True
	bMuteFast=True
	bAlwaysTick=True
	RemoteRole=ROLE_None
}
