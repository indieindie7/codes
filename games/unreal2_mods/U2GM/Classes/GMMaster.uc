//=============================================================================
// GMMaster - the game master: GM mode, the picked actor, the journal, undo.
//
//   gm [on|off]           GM mode: free camera through walls, no damage (toggles without a word)
//   gm pick [NAME|pawn]   the scenery under the crosshair (looking past characters), a character
//                         (pawn: moved live only), or an actor by name
//   gm info               what is picked
//   gm move DX DY DZ      nudge it (world units)     gm moveto X Y Z | here
//   gm turn DEG           turn it round the vertical  gm scale S
//   gm hide               hide it (a placed mesh is removed)
//   gm spawn N|PATH       palette entry N (gm palette) or a mesh path, under the crosshair,
//                         snapped to the grid and the ground, facing the camera
//   gm palette [add PATH | clear]   the spawn palette (U2GM.ini)
//   gm snap SIZE          grid size (0 = off), gm yawstep DEG
//   gm possess            take over the character under the crosshair; gm release
//   gm freeze             stop everything but the players (again: go on)
//   gm undo / gm redo     the journal's last change, applied to the world at once
//   gm journal            this map's journal lines
//   gm raise R H          terrain under the crosshair up by H within radius R (smooth falloff)
//   gm lower R H          ... down by H
//   gm flatten R          ... to the height under the crosshair
//   gm smooth R           ... smoothed
//                         (terrain lines are applied by the d3d8 fork, gmterrain=1 in U2Shaders.ini)
//
// The fork's panel (gmpanel=1 in U2Shaders.ini, F7) sends commands through System\U2GMPanel.txt,
// which this actor execs every PanelPoll seconds (0.25 s while the panel is open). Each line there
// is "gm q SESSION K CMD": it runs once (K above the last one run, or a new SESSION). Extra
// commands for the panel: gm panel 1|0 (poll fast/slow), gm ray SX SY SZ EX EY EZ (the next
// command aims along this line instead of the crosshair: a click in the world), gm preview X Y Z
// YAW (puts the picked actor there without a journal line: the gizmo's live preview).
// After every command the PanelState config line (U2GM.ini) says what is picked, for the panel.
//
// The world is always the map plus its journal: every edit writes a journal
// line and the world follows; undo and redo change the journal and replay it.
// A map's static actors can't move (bStatic): the first move swaps one for a
// movable copy (GMMesh) and hides the original ("place NAME ...").
// Terrain lines ("terrain raise|lower|flatten|smooth X Y R H", world units:
// centre, radius, height; flatten: H is the target Z; smooth: H is the strength)
// are not replayed here: script can't reach the heightmap. The d3d8 fork
// (u2shaders.hpp, gmterrain=1) watches this ini and applies them natively.
// The journal is shared by all maps: each line starts "@<map family>"
// (TutA_Live3 -> tuta), as in AvalonEditor.
//
// Commit (days 6-7): "gm commit" asks for the journal to be baked into a real map. It saves the
// journal and writes CommitRequest="family stamp map lines" for the watcher (U2GM/tools/gm_commit.py
// --watch), which bakes it with UnrealEd into <Map>_LiveN beside the game; edits are held until it
// answers ("gm commit cancel" lets go). The watcher answers through U2GMPanel.txt, in its own q-line
// session (2^30 and up, kept apart from the panel's): "gm baked STAMP K TEXT" for every line it baked
// (the slot is emptied when it still says TEXT, so the baked map never gets it twice), then "gm
// committed STAMP MAP N" and "gm travel MAP" (ClientTravel, the GM mode and the player's place kept),
// or "gm commitfail STAMP WHY".
//
// Draw (level team, Q27): "gm draw add [X Y Z]" (no point: the hit under the crosshair or the panel's
// ray), "gm draw undo|clear", "gm draw done open|closed [NOTE]" keeps one line in Draws[] (not the
// journal: nothing replays or bakes it): "@family draw D<n> open|closed x1 y1 z1 ... note TEXT",
// logs it and takes a screenshot. At most 40 points (an ini line has to stay under ~1000 chars).
// "gm draw list", "gm draw forget N".
//
// Sketch (the fork's sketch=1, screenshot markup): "gm con big|quick 1|0" comes from UIScripts\Console.ui
// (TriggerEvent lines added by U2GM/tools/sketch_console_ui.py) when the full console or the one-line
// one opens or closes; it only sets con= in PanelState (1 full, 2 one-line, 3 both), which the fork
// reads to show its "Sketch" strip. "gm sketch mark NAME [NOTE]" (sent by the fork's Save as mark)
// logs "GM: SKETCH NAME ..." and, when AvalonCards is loaded, runs "avalon mark NOTE sketch:NAME".
//
// Texture adjust (the fork's panel, "Texture (click to alter)"; source/texedit.hpp): "gm tex HASH REV
// b c g s h sh sm sl sharp" keeps one journal line per texture hash, "@* tex HASH REV ..." ("@*": global,
// keyed by the texture's content, not by map; nothing here replays or bakes it, the fork reads it from
// this ini and re-applies it). It goes through Change like any line, so gm undo / gm redo step through
// it. Undo and redo keep a slot's whole line, family tag included, so "@*" lines come back as they were.
//=============================================================================
class GMMaster extends Info
	config(U2GM);

var config string Ops[256];         // the journal ("@family op ...")
var config string Palette[32];      // spawnable static meshes (Package.Group.Name)
var config float GridSize;          // spawn snap in world units (0 = off)
var config int YawStep;             // spawn and turn snap in degrees
// the d3d8 fork's panel (gmpanel=1): its command file, polled; the last line run; what the panel shows
var config float PanelPoll;         // seconds between reads of PanelFile while the panel is closed (0 = off)
var config string PanelFile;
var config int PanelSession, PanelSeq;
var config string PanelState;           // "seq=S:K on=0 poss=0 frz=0 pick=NAME cls=CLASS mesh=PATH loc=X,Y,Z yaw=D scale=S cam=X,Y,Z
                                        //  view=YAW,PITCH wseq=S:K commit=STAMP:STATE:MAP draw=N con=N"
// commit (gm_commit.py --watch)
var config int CommitStamp;             // commits asked for so far
var config string CommitRequest;        // "family stamp map lines" while one is wanted, else ""
var config string CommitStatus;         // "stamp pending|done|failed|cancelled [MAP or why]"
var config int WatchSession, WatchSeq;  // the watcher's q-lines (sessions from 2^30 up)
var config bool bResume, bResumeGM;     // after gm travel: put the player back, GM mode as it was
var config vector ResumeLoc;
var config rotator ResumeRot;
// draw (the level team's notes: edges, areas, routes)
var config string Draws[64];            // "@family draw D<n> open|closed x y z ... note TEXT"
var config int DrawCount;
var config string DrawState;            // the draw in progress, for the panel: "x,y,z x,y,z ..."
var array<vector> DrawPts;
const MaxDrawPts = 40;
const WatchBase = 1073741824;

var PlayerController PC;
var bool bOn;
var bool bWasGod;
var Actor Picked;
var string PickedName;              // the journal's name: a map actor's name or "mesh#K"
var array<Actor> Made;              // what the replay spawned
var array<string> MadeName;         // each one's journal name
var array<Actor> Hid;               // map actors the replay hid
var array<int> UndoAt;              // journal slots changed, newest last
var array<string> UndoWas;          // what each slot said before
var array<int> RedoAt;
var array<string> RedoWas;
var Pawn HomePawn, Taken;           // possession: the player's own body, the one taken over
var Controller TakenAI;
var bool bPanelFast;                // the panel is open: read its file every 0.25 s
var float PanelWait, StateWait;
var bool bRay;                      // gm ray: the next command aims along RayS -> RayE
var vector RayS, RayE;
var bool bConBig, bConQuick;        // the consoles are open (gm con, from Console.ui's triggers)

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(0.25, true);
}

// the panel's command file, and the PanelState line kept fresh (a picked character walks)
event Timer()
{
	if (PC == None)
		return;
	// back where the player was before "gm travel" (a committed map), GM mode as it was
	if (bResume && PC.Pawn != None)
	{
		bResume = false;
		if (bResumeGM)
			SetOn(true);
		PC.Pawn.SetLocation(ResumeLoc);
		PC.SetRotation(ResumeRot);
		SaveConfig();
		Say("on "$MapName()$", back where you were");
	}
	if (PanelPoll > 0 && PanelFile != "")
	{
		PanelWait -= 0.25;
		if (PanelWait <= 0)
		{
			PanelWait = PanelPoll;
			if (bPanelFast)
				PanelWait = 0.25;
			PC.ConsoleCommand("exec "$PanelFile);   // its lines run right here, as typed "gm ..." commands
		}
	}
	StateWait -= 0.25;
	if (StateWait <= 0)
	{
		StateWait = 1.0;
		SaveState();
	}
}

// what the panel shows (written only when it changed)
function SaveState()
{
	local string S;
	local vector E;

	S = "seq="$PanelSession$":"$PanelSeq$" on="$Pick2(bOn, "1", "0")$" poss="$Pick2(Taken != None, "1", "0")$" frz="$Pick2(Level.bPlayersOnly, "1", "0");
	if (Picked == None || Picked.bDeleteMe)
		S = S$" pick=- cls=- mesh=- loc=0,0,0 yaw=0 scale=1";
	else
	{
		S = S$" pick="$PickedName$" cls="$string(Picked.Class.Name);
		if (Picked.StaticMesh != None)
			S = S$" mesh="$Picked.StaticMesh;
		else if (Picked.Mesh != None)
			S = S$" mesh="$Picked.Mesh;
		else
			S = S$" mesh=-";
		S = S$" loc="$Picked.Location.X$","$Picked.Location.Y$","$Picked.Location.Z;
		S = S$" yaw="$((Picked.Rotation.Yaw & 65535) * 360.0 / 65536.0)$" scale="$Picked.DrawScale;
	}
	if (PC != None)
	{
		E = EyeSpot();
		S = S$" cam="$E.X$","$E.Y$","$E.Z;
		S = S$" view="$ViewYaw()$","$ViewPitch();
	}
	S = S$" wseq="$WatchSession$":"$WatchSeq;
	S = S$" commit="$Pick2(CommitStatus == "", "0:none:-", Word(CommitStatus, 0)$":"$Word(CommitStatus, 1)$":"$Pick2(Word(CommitStatus, 2) == "", "-", Word(CommitStatus, 2)));
	S = S$" draw="$DrawPts.Length;
	S = S$" con="$ConState();
	if (S == PanelState)
		return;
	PanelState = S;
	SaveConfig();
}

// where the player looks, whole degrees (yaw 0..359, pitch -90..90)
function int ViewYaw()
{
	return int((PC.Rotation.Yaw & 65535) * 360.0 / 65536.0);
}
function int ViewPitch()
{
	return ((((PC.Rotation.Pitch + 32768) & 65535) - 32768) * 360) / 65536;
}

// 1 the full console, 2 the one-line one, 3 both
function int ConState()
{
	local int N;

	if (bConBig)
		N += 1;
	if (bConQuick)
		N += 2;
	return N;
}

// AvalonCards (U2AvalonCards' mutator) is on this map: "avalon mark" will be heard
function bool AvalonLoaded()
{
	local Actor A;

	foreach DynamicActors(class'Actor', A)
		if (A.IsA('AvalonCards'))
			return true;
	return false;
}

// gm sketch mark NAME [NOTE]: the fork saved System\Sketch\NAME.png (+ NAME.txt); make it a mark
function SketchCmd(string Args)
{
	local string Name, Note;
	local vector E;

	if (Locs(Word(Args, 1)) != "mark" || Word(Args, 2) == "")
	{
		Say("gm sketch mark NAME [NOTE] (sent by the fork's sketch tool: sketch=1, F8)");
		return;
	}
	Name = Word(Args, 2);
	Note = After(Args, 3);
	E = EyeSpot();
	Log("GM: SKETCH "$Name$" map "$MapName()$" eye "$int(E.X)$" "$int(E.Y)$" "$int(E.Z)$" yaw "$ViewYaw()$" pitch "$ViewPitch()$" note "$Note);
	if (AvalonLoaded())
	{
		if (Note != "")
			PC.ConsoleCommand("avalon mark "$Note$" sketch:"$Name);
		else
			PC.ConsoleCommand("avalon mark sketch:"$Name);
		Say("sketch "$Name$" sent as an avalon mark");
	}
	else
		Say("sketch "$Name$" saved and logged (AvalonCards isn't loaded here: no avalon mark)");
}

function Say(coerce string S)
{
	Log("GM: "$S);
	if (PC != None)
		PC.ClientMessage("[GM] "$S);
}

// ---------------------------------------------------------------- text

static function string Word(string S, int N)
{
	local int k;

	while (Left(S, 1) == " ")
		S = Mid(S, 1);
	for (k = 0; k < N; k++)
	{
		if (InStr(S, " ") < 0)
			return "";
		S = Mid(S, InStr(S, " ") + 1);
		while (Left(S, 1) == " ")
			S = Mid(S, 1);
	}
	if (InStr(S, " ") >= 0)
		S = Left(S, InStr(S, " "));
	return S;
}

// the map's name without "_liveN" (a carved copy keeps the session's edits)
function string Family()
{
	local string M;

	M = Locs(string(Level));
	if (InStr(M, ".") >= 0)
		M = Left(M, InStr(M, "."));
	if (InStr(M, "_live") >= 0)
		M = Left(M, InStr(M, "_live"));
	return M;
}

// the map's own name as it is on disk (TutA_Live3)
function string MapName()
{
	local string M;

	M = string(Level);
	if (InStr(M, ".") >= 0)
		M = Left(M, InStr(M, "."));
	return M;
}

function string GetOp(int k)
{
	if (Word(Ops[k], 0) != ("@"$Family()))
		return "";
	return Mid(Ops[k], InStr(Ops[k], " ") + 1);
}

function SetOp(int k, string L)
{
	if (L == "")
		Ops[k] = "";
	else
		Ops[k] = "@"$Family()$" "$L;
}

function int CountOps()
{
	local int k, n;

	for (k = 0; k < ArrayCount(Ops); k++)
		if (GetOp(k) != "")
			n++;
	return n;
}

function int FindOp(string Kind, string N)
{
	local int k;

	for (k = 0; k < ArrayCount(Ops); k++)
		if (Word(GetOp(k), 0) == Kind && Word(GetOp(k), 1) ~= N)
			return k;
	return -1;
}

function int FreeOp()
{
	local int k;

	for (k = 0; k < ArrayCount(Ops); k++)
		if (Ops[k] == "")
			return k;
	return -1;
}

// a slot after every used one (terrain lines are order dependent: keep them in time order)
function int LastFreeOp()
{
	local int k;

	for (k = ArrayCount(Ops) - 1; k >= 0; k--)
		if (Ops[k] != "")
			break;
	if (k + 1 < ArrayCount(Ops))
		return k + 1;
	return FreeOp();
}

// one journal change: remembered for undo, the redo list dropped, saved
function Change(int k, string L)
{
	if (L == "")
		ChangeRaw(k, "");
	else
		ChangeRaw(k, "@"$Family()$" "$L);
}

// the same with the whole line (its tag included: "@* tex ..." lines); undo keeps whole lines
function ChangeRaw(int k, string Raw)
{
	UndoAt[UndoAt.Length] = k;
	UndoWas[UndoWas.Length] = Ops[k];
	RedoAt.Length = 0;
	RedoWas.Length = 0;
	Ops[k] = Raw;
	SaveConfig();
}

function string Transform(Actor A)
{
	return int(A.Location.X)$" "$int(A.Location.Y)$" "$int(A.Location.Z)$" "$int(A.Rotation.Yaw * 360.0 / 65536.0)$" "$A.DrawScale;
}

function string Describe(Actor A)
{
	local string S;

	if (A == None)
		return "nothing";
	S = string(A.Class.Name)$" "$PickedName;
	if (A.StaticMesh != None)
		S = S$" mesh "$A.StaticMesh;
	return S$" at "$Transform(A);
}

static function int RoundI(float V)
{
	if (V < 0)
		return -int(-V + 0.5);
	return int(V + 0.5);
}

static function string Pick2(bool B, string IfTrue, string IfFalse)
{
	if (B)
		return IfTrue;
	return IfFalse;
}

// ---------------------------------------------------------------- the world from the journal

function Actor Find(string N)
{
	local Actor A;

	foreach AllActors(class'Actor', A)
		if (string(A.Name) ~= N)
			return A;
	return None;
}

function HideActor(Actor A)
{
	A.bHidden = True;
	A.SetCollision(False, False, False);
	Hid[Hid.Length] = A;
}

function GMMesh NewMesh(string Path, string N)
{
	local GMMesh M;

	M = Spawn(class'GMMesh');
	if (M == None)
		return None;
	if (!M.Show(Path))
	{
		M.Destroy();
		return None;
	}
	Made[Made.Length] = M;
	MadeName[MadeName.Length] = N;
	return M;
}

// a movable stand-in for a map's static actor: same mesh, skins and scale; the original hidden
function GMMesh CopyOf(Actor A)
{
	local GMMesh M;
	local int k;

	if (A.StaticMesh == None)
		return None;
	M = Spawn(class'GMMesh',,, A.Location, A.Rotation);
	if (M == None)
		return None;
	M.StaticMesh = A.StaticMesh;
	M.SetDrawType(DT_StaticMesh);
	M.SetDrawScale(A.DrawScale);
	M.SetDrawScale3D(A.DrawScale3D);
	for (k = 0; k < A.Skins.Length; k++)
		M.Skins[k] = A.Skins[k];
	HideActor(A);
	Made[Made.Length] = M;
	MadeName[MadeName.Length] = string(A.Name);
	return M;
}

// words From.. of Line: X Y Z YAW SCALE
function Apply(Actor A, string Line, int From)
{
	local vector P;
	local rotator R;

	P.X = float(Word(Line, From));
	P.Y = float(Word(Line, From + 1));
	P.Z = float(Word(Line, From + 2));
	R = A.Rotation;
	R.Yaw = int(float(Word(Line, From + 3)) * 65536.0 / 360.0);
	A.SetLocation(P);
	A.SetRotation(R);
	if (Word(Line, From + 4) != "")
		A.SetDrawScale(float(Word(Line, From + 4)));
}

function Replay()
{
	local int k;
	local string Op, N;
	local Actor A;

	for (k = 0; k < Made.Length; k++)
		if (Made[k] != None)
			Made[k].Destroy();
	Made.Length = 0;
	MadeName.Length = 0;
	for (k = 0; k < Hid.Length; k++)
		if (Hid[k] != None)
		{
			Hid[k].bHidden = Hid[k].default.bHidden;
			Hid[k].SetCollision(Hid[k].default.bCollideActors, Hid[k].default.bBlockActors, Hid[k].default.bBlockPlayers);
		}
	Hid.Length = 0;
	for (k = 0; k < ArrayCount(Ops); k++)
	{
		Op = Word(GetOp(k), 0);
		N = Word(GetOp(k), 1);
		if (Op == "hide")
		{
			A = Find(N);
			if (A != None)
				HideActor(A);
		}
		else if (Op == "place")
		{
			A = Find(N);
			if (A != None)
			{
				A = CopyOf(A);
				if (A != None)
					Apply(A, GetOp(k), 2);
			}
		}
		else if (Op == "mesh")
		{
			A = NewMesh(N, "mesh#"$k);
			if (A != None)
				Apply(A, GetOp(k), 2);
		}
	}
	// the picked actor again (the replay made new copies)
	if (PickedName != "")
		SetPicked(Named(PickedName));
}

// what a journal name stands for now: our copy or mesh, else the map's actor
function Actor Named(string N)
{
	local int k;

	for (k = 0; k < MadeName.Length; k++)
		if (MadeName[k] ~= N && Made[k] != None)
			return Made[k];
	if (Left(N, 5) == "mesh#")
		return None;
	return Find(N);
}

function SetPicked(Actor A)
{
	local int k;

	Picked = A;
	PickedName = "";
	if (A == None)
		return;
	for (k = 0; k < Made.Length; k++)
		if (Made[k] == A)
			PickedName = MadeName[k];
	if (PickedName == "")
		PickedName = string(A.Name);
}

function bool IsOurs(Actor A)
{
	local int k;

	for (k = 0; k < Made.Length; k++)
		if (Made[k] == A)
			return true;
	return false;
}

// ---------------------------------------------------------------- looking

function vector EyeSpot()
{
	if (PC.Pawn != None)
		return PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	return PC.Location;
}

// what's under the crosshair, looking past characters (they can only move live, not be journalled):
// "gm pick" picks scenery; "gm pick pawn" picks a character
function Actor MeshUnderCrosshair(out vector HitL, out vector HitN)
{
	local vector S, E, D;
	local Actor A, Tracer;
	local int k;

	S = EyeSpot();
	E = S + vector(PC.Rotation) * 60000;
	if (bRay)
	{
		S = RayS;
		E = RayE;
	}
	D = Normal(E - S);
	Tracer = PC.Pawn;
	if (Tracer == None)
		Tracer = self;
	for (k = 0; k < 6; k++)
	{
		A = Tracer.Trace(HitL, HitN, E, S, true);
		if (Pawn(A) == None)
			return A;
		S = HitL + D * (Pawn(A).CollisionRadius * 2 + 8);
	}
	return None;
}

function Actor UnderCrosshair(out vector HitL, out vector HitN)
{
	local vector S, E;

	S = EyeSpot();
	E = S + vector(PC.Rotation) * 60000;
	if (bRay)
	{
		S = RayS;
		E = RayE;
	}
	if (PC.Pawn != None)
		return PC.Pawn.Trace(HitL, HitN, E, S, true);
	return Trace(HitL, HitN, E, S, true);
}

function float Snap(float V, float Step)
{
	if (Step <= 0)
		return V;
	return Step * RoundI(V / Step);
}

// the snapped spot under the crosshair, on whatever is below it
function bool SpawnSpot(out vector P)
{
	local vector HitL, HitN, L2, N2;

	if (UnderCrosshair(HitL, HitN) == None && HitL == vect(0,0,0))
		return false;
	P = HitL + HitN * 4;
	P.X = Snap(P.X, GridSize);
	P.Y = Snap(P.Y, GridSize);
	if (Trace(L2, N2, P - vect(0,0,2048), P + vect(0,0,64), false) != None)
		P.Z = L2.Z;
	return true;
}

// facing the camera, snapped
function int FacingYaw()
{
	local int Deg;

	Deg = int(PC.Rotation.Yaw * 360.0 / 65536.0) + 180;
	if (YawStep > 0)
		Deg = YawStep * RoundI(float(Deg) / YawStep);
	return Deg % 360;
}

// ---------------------------------------------------------------- GM mode

function SetOn(bool B)
{
	local Pawn P;

	P = PC.Pawn;
	if (B == bOn || P == None)
	{
		bOn = B;
		return;
	}
	bOn = B;
	if (bOn)
	{
		bWasGod = PC.bGodMode;
		PC.bGodMode = true;
		P.UnderWaterTime = -1.0;
		P.SetCollision(false, false, false);
		P.bCollideWorld = false;
		PC.bCheatFlying = true;
		PC.GotoState('PlayerFlying');
		Say("GM mode on: fly through walls, 'gm help' for the tools");
	}
	else
	{
		PC.bGodMode = bWasGod;
		PC.bCheatFlying = false;
		P.UnderWaterTime = P.default.UnderWaterTime;
		P.SetCollision(true, true, true);
		P.SetPhysics(PHYS_Walking);
		P.bCollideWorld = true;
		PC.Restart();
		Say("GM mode off");
	}
}

// ---------------------------------------------------------------- edits

// the picked actor ready to change: a map's static actor becomes its movable copy (once)
function bool Editable()
{
	local Actor C;
	local string N;

	if (Picked == None)
	{
		Say("nothing picked (gm pick)");
		return false;
	}
	if (Picked.bStatic && !IsOurs(Picked))
	{
		N = string(Picked.Name);
		C = CopyOf(Picked);
		if (C == None)
		{
			Say("can't move "$N$" (no static mesh)");
			return false;
		}
		Picked = C;
		PickedName = N;
	}
	return true;
}

// the picked actor's transform into the journal
function Remember()
{
	local int k;

	if (Left(PickedName, 5) == "mesh#")
	{
		k = int(Mid(PickedName, 5));
		Change(k, "mesh "$Picked.StaticMesh$" "$Transform(Picked));
	}
	else if (IsOurs(Picked))
	{
		k = FindOp("place", PickedName);
		if (k < 0)
			k = FreeOp();
		if (k < 0)
		{
			Say("journal full");
			return;
		}
		Change(k, "place "$PickedName$" "$Transform(Picked));
	}
	else
		Say("(moved live only: "$PickedName$" isn't a static mesh, so it isn't journalled)");
}

function TakeBack(bool bRedo)
{
	local int k;
	local string L;

	if ((!bRedo && UndoAt.Length == 0) || (bRedo && RedoAt.Length == 0))
	{
		Say("nothing to "$Pick2(bRedo, "redo", "undo"));
		return;
	}
	if (!bRedo)
	{
		k = UndoAt[UndoAt.Length - 1];
		L = UndoWas[UndoWas.Length - 1];
		UndoAt.Length = UndoAt.Length - 1;
		UndoWas.Length = UndoWas.Length - 1;
		RedoAt[RedoAt.Length] = k;
		RedoWas[RedoWas.Length] = Ops[k];
	}
	else
	{
		k = RedoAt[RedoAt.Length - 1];
		L = RedoWas[RedoWas.Length - 1];
		RedoAt.Length = RedoAt.Length - 1;
		RedoWas.Length = RedoWas.Length - 1;
		UndoAt[UndoAt.Length] = k;
		UndoWas[UndoWas.Length] = Ops[k];
	}
	Ops[k] = L;
	SaveConfig();
	Replay();
	Say(Pick2(bRedo, "redo", "undo")$": line "$k$" now '"$L$"'");
}

// gm tex HASH REV b c g s h sh sm sl sharp (the fork's texture panel): one "@* tex" slot per hash
function TexCmd(string Args)
{
	local int k;
	local string H;

	H = Locs(Word(Args, 0));
	if (Len(H) != 8 || Word(Args, 10) == "")
	{
		Say("gm tex HASH REV b c g s h sh sm sl sharp (sent by the fork's panel: Texture, Save)");
		return;
	}
	for (k = 0; k < ArrayCount(Ops); k++)
		if (Word(Ops[k], 0) == "@*" && Word(Ops[k], 1) == "tex" && Word(Ops[k], 2) ~= H)
			break;
	if (k >= ArrayCount(Ops))
		k = FreeOp();
	if (k < 0)
	{
		Say("journal full");
		return;
	}
	ChangeRaw(k, "@* tex "$H$" "$After(Args, 1));
	Say("texture "$H$" rev "$Word(Args, 1)$" saved (line "$k$"; gm undo takes it back)");
}

function Possess()
{
	local vector HitL, HitN;
	local Pawn P;

	if (Taken != None)
	{
		Say("already possessing "$Taken$" (gm release)");
		return;
	}
	P = Pawn(UnderCrosshair(HitL, HitN));
	if (P == None || P == PC.Pawn)
	{
		Say("no character under the crosshair");
		return;
	}
	SetOn(false);
	HomePawn = PC.Pawn;
	Taken = P;
	TakenAI = P.Controller;
	if (TakenAI != None)
	{
		TakenAI.Pawn = None;
		TakenAI.GotoState('');
	}
	PC.UnPossess();
	PC.Possess(P);
	Say("possessing "$P$" (gm release to go back)");
}

function Release()
{
	local Pawn P;

	if (Taken == None)
	{
		Say("not possessing anyone");
		return;
	}
	P = Taken;
	Taken = None;
	PC.UnPossess();
	if (TakenAI != None && P.Health > 0)
		TakenAI.Possess(P);
	if (HomePawn != None && HomePawn.Health > 0)
		PC.Possess(HomePawn);
	Say("back in your own body");
}

function SpawnFromPalette(string What)
{
	local string Path;
	local vector P;
	local int k;
	local Actor A;

	Path = What;
	if (What != "" && string(int(What)) == What)
		Path = Palette[Clamp(int(What), 0, ArrayCount(Palette) - 1)];
	if (Path == "")
	{
		Say("spawn what? 'gm palette' lists the meshes, or give Package.Group.Name");
		return;
	}
	if (!SpawnSpot(P))
	{
		Say("nothing under the crosshair to put it on");
		return;
	}
	k = FreeOp();
	if (k < 0)
	{
		Say("journal full");
		return;
	}
	Change(k, "mesh "$Path$" "$int(P.X)$" "$int(P.Y)$" "$int(P.Z)$" "$FacingYaw()$" 1");
	Replay();
	A = Named("mesh#"$k);
	if (A == None)
	{
		SetOp(k, "");
		UndoAt.Length = UndoAt.Length - 1;
		UndoWas.Length = UndoWas.Length - 1;
		SaveConfig();
		Say("couldn't place "$Path);
		return;
	}
	SetPicked(A);
	Say("placed "$Describe(A));
}

// a terrain brush stroke at the crosshair: one journal line, applied by the d3d8 fork
function TerrainBrush(string Kind, float R, float H)
{
	local vector HitL, HitN;
	local Actor A;
	local int k;
	local string L;

	if (R <= 0)
	{
		Say("gm "$Kind$" needs a radius (world units), e.g. gm "$Kind$" 512"$Pick2(Kind == "raise" || Kind == "lower", " 256", ""));
		return;
	}
	A = UnderCrosshair(HitL, HitN);
	if (A == None || !A.IsA('TerrainInfo'))
	{
		Say("aim at terrain (under the crosshair: "$Pick2(A == None, "nothing", string(A.Name))$")");
		return;
	}
	if (Kind == "flatten")
		H = HitL.Z;
	else if (Kind == "smooth")
		H = 1;
	else if (H <= 0)
	{
		Say("gm "$Kind$" R H: H is how far (world units, > 0)");
		return;
	}
	k = LastFreeOp();
	if (k < 0)
	{
		Say("journal full");
		return;
	}
	L = "terrain "$Kind$" "$int(HitL.X)$" "$int(HitL.Y)$" "$int(R)$" "$int(H);
	Change(k, L);
	Say(L$" (line "$k$"; the d3d8 fork applies it if gmterrain=1)");
}

// ---------------------------------------------------------------- commit (days 6-7)

function bool CommitPending()
{
	return Word(CommitStatus, 1) == "pending";
}

// "gm commit": the journal saved, a request for the watcher; "gm commit cancel" drops it
function Commit(string A1)
{
	if (A1 ~= "cancel")
	{
		if (!CommitPending())
		{
			Say("no commit running");
			return;
		}
		CommitStatus = Word(CommitStatus, 0)$" cancelled";
		CommitRequest = "";
		SaveConfig();
		Say("commit cancelled: edits are open again (a bake already running still saves its map, nobody travels to it)");
		return;
	}
	if (CommitPending())
	{
		Say("commit "$Word(CommitStatus, 0)$" is still running ('gm commit cancel' drops it)");
		return;
	}
	if (CountOps() == 0)
	{
		Say("nothing to commit: no journal lines on "$Family());
		return;
	}
	if (Taken != None)
		Release();
	CommitStamp++;
	CommitRequest = Family()$" "$CommitStamp$" "$MapName()$" "$CountOps();
	CommitStatus = CommitStamp$" pending";
	SaveConfig();
	Log("GM: commit request "$CommitRequest);
	Say("commit "$CommitStamp$": "$CountOps()$" journal lines on "$MapName()$" go to UnrealEd (gm_commit.py --watch); edits wait until it's done");
}

// the watcher baked journal slot K (it said TEXT): emptied, so the baked map doesn't get it twice
function Baked(int Stamp, int K, string Text)
{
	if (Stamp != CommitStamp || K < 0 || K >= ArrayCount(Ops))
	{
		Log("GM: baked "$Stamp$" "$K$" ignored (commit "$CommitStamp$")");
		return;
	}
	if (GetOp(K) ~= Text)
	{
		Ops[K] = "";
		Log("GM: baked line "$K$": "$Text);
	}
	else
		Log("GM: baked line "$K$" kept: it now says '"$GetOp(K)$"', the bake had '"$Text$"'");
}

function Committed(int Stamp, string M, int N)
{
	if (Stamp != CommitStamp)
		return;
	CommitStatus = Stamp$" done "$M;
	CommitRequest = "";
	// the commit is a checkpoint: undo can't reach into the baked map
	UndoAt.Length = 0;
	UndoWas.Length = 0;
	RedoAt.Length = 0;
	RedoWas.Length = 0;
	SaveConfig();
	Say("commit "$Stamp$": "$N$" lines baked into "$M);
}

function CommitFailed(int Stamp, string Why)
{
	if (Stamp != CommitStamp)
		return;
	CommitStatus = Stamp$" failed "$Why;
	CommitRequest = "";
	SaveConfig();
	Say("commit "$Stamp$" failed: "$Why$" (the journal is unchanged, edits are open again)");
}

// "gm travel MAP": ClientTravel ("open" from an exec'd file is dropped), same URL options, and the
// player put back where they stood with GM mode as it was
function Travel(string M)
{
	local string Opts;

	if (M == "")
	{
		Say("gm travel MAP");
		return;
	}
	if (Taken != None)
		Release();
	if (PC.Pawn != None)
	{
		ResumeLoc = PC.Pawn.Location;
		ResumeRot = PC.Rotation;
		bResume = true;
		bResumeGM = bOn;
	}
	SaveConfig();
	Opts = Level.GetLocalURL();
	if (InStr(Opts, "?") >= 0)
		Opts = Mid(Opts, InStr(Opts, "?"));
	else
		Opts = "";
	Log("GM: travel to "$M$Opts);
	PC.ClientTravel(M$Opts, TRAVEL_Absolute, false);
}

// ---------------------------------------------------------------- draw (Q27)

function UpdateDrawState()
{
	local int k;
	local string S;

	for (k = 0; k < DrawPts.Length; k++)
	{
		if (k > 0)
			S = S$" ";
		S = S$int(DrawPts[k].X)$","$int(DrawPts[k].Y)$","$int(DrawPts[k].Z);
	}
	if (S != DrawState)
	{
		DrawState = S;
		SaveConfig();
	}
}

function DrawCmd(string Args)
{
	local string Sub, Kind, Note, L;
	local vector V, HitL, HitN;
	local Actor A;
	local int k, n;

	Sub = Locs(Word(Args, 1));
	if (Sub == "add")
	{
		if (DrawPts.Length >= MaxDrawPts)
		{
			Say("a draw holds at most "$MaxDrawPts$" points: gm draw done open|closed");
			return;
		}
		if (Word(Args, 2) != "")
		{
			V.X = float(Word(Args, 2)); V.Y = float(Word(Args, 3)); V.Z = float(Word(Args, 4));
		}
		else
		{
			A = UnderCrosshair(HitL, HitN);
			if (A == None && HitL == vect(0,0,0))
			{
				Say("draw: nothing under the crosshair");
				return;
			}
			V = HitL;
		}
		DrawPts[DrawPts.Length] = V;
		UpdateDrawState();
		Say("draw point "$DrawPts.Length$" at "$int(V.X)$" "$int(V.Y)$" "$int(V.Z));
	}
	else if (Sub == "undo")
	{
		if (DrawPts.Length > 0)
			DrawPts.Length = DrawPts.Length - 1;
		UpdateDrawState();
		Say("draw: "$DrawPts.Length$" points");
	}
	else if (Sub == "clear")
	{
		DrawPts.Length = 0;
		UpdateDrawState();
		Say("draw cleared");
	}
	else if (Sub == "done")
	{
		Kind = Locs(Word(Args, 2));
		if (Kind != "open" && Kind != "closed")
		{
			Say("gm draw done open|closed [note]");
			return;
		}
		if (DrawPts.Length < 2 || (Kind == "closed" && DrawPts.Length < 3))
		{
			Say("draw: "$DrawPts.Length$" points is too few for "$Kind);
			return;
		}
		for (k = 0; k < ArrayCount(Draws); k++)
			if (Draws[k] == "")
				break;
		if (k >= ArrayCount(Draws))
		{
			Say("draw slots full ("$ArrayCount(Draws)$"): gm draw forget N");
			return;
		}
		DrawCount++;
		L = "draw D"$DrawCount$" "$Kind;
		for (n = 0; n < DrawPts.Length; n++)
			L = L$" "$int(DrawPts[n].X)$" "$int(DrawPts[n].Y)$" "$int(DrawPts[n].Z);
		Note = After(Args, 3);
		if (Note != "")
		{
			// an ini line stays under ~1000 characters
			if (Len(L) + 6 + Len(Note) + Len(Family()) + 2 > 1000)
				Note = Left(Note, Max(0, 1000 - Len(L) - Len(Family()) - 8));
			L = L$" note "$Note;
		}
		Draws[k] = "@"$Family()$" "$L;
		DrawPts.Length = 0;
		UpdateDrawState();
		SaveConfig();
		Log("GM: "$L$" (map "$MapName()$", slot "$k$")");
		if (PC != None)
			PC.ConsoleCommand("shot");
		Say("draw D"$DrawCount$" kept ("$Kind$"), screenshot taken");
	}
	else if (Sub == "list")
	{
		for (k = 0; k < ArrayCount(Draws); k++)
			if (Word(Draws[k], 0) == ("@"$Family()))
				Say(Left(Mid(Draws[k], InStr(Draws[k], " ") + 1), 200));
		Say(DrawPts.Length$" points in the draw being made");
	}
	else if (Sub == "forget")
	{
		for (k = 0; k < ArrayCount(Draws); k++)
			if (Word(Draws[k], 0) == ("@"$Family()) && Word(Draws[k], 2) ~= ("D"$Word(Args, 2)))
			{
				Draws[k] = "";
				SaveConfig();
				Say("draw D"$Word(Args, 2)$" forgotten");
				return;
			}
		Say("no draw D"$Word(Args, 2)$" on "$Family());
	}
	else
		Say("gm draw add [X Y Z] | undo | clear | done open|closed [note] | list | forget N");
}

// ---------------------------------------------------------------- the command

// the rest of S after its first N words
static function string After(string S, int N)
{
	local int k;

	while (Left(S, 1) == " ")
		S = Mid(S, 1);
	for (k = 0; k < N; k++)
	{
		if (InStr(S, " ") < 0)
			return "";
		S = Mid(S, InStr(S, " ") + 1);
		while (Left(S, 1) == " ")
			S = Mid(S, 1);
	}
	return S;
}

function Command(string Args)
{
	RunOne(Args);
	SaveState();
}

function RunOne(string Args)
{
	local string Cmd, Rest;
	local int S, K;

	Cmd = Locs(Word(Args, 0));
	if (Cmd == "q")
	{
		// a line of the panel's file: runs once
		S = int(Word(Args, 1));
		K = int(Word(Args, 2));
		if (S >= WatchBase)
		{
			// the commit watcher's lines (gm_commit.py): their own session and count
			if (S == WatchSession && K <= WatchSeq)
				return;
			WatchSession = S;
			WatchSeq = K;
		}
		else
		{
			if (S == PanelSession && K <= PanelSeq)
				return;
			PanelSession = S;
			PanelSeq = K;
		}
		Rest = After(Args, 3);
		if (Locs(Word(Rest, 0)) != "q")
			RunOne(Rest);
		return;
	}
	DoCommand(Args);
	if (Cmd != "ray" && Cmd != "con")
		bRay = false;
}

function DoCommand(string Args)
{
	local string Cmd, A1;
	local vector V, HitL, HitN;
	local rotator R;
	local int k, n;
	local Actor A;

	if (PC == None)
		return;
	Cmd = Locs(Word(Args, 0));
	A1 = Word(Args, 1);
	// while a commit bakes the journal, the journal must stay what the watcher read
	if (CommitPending() && (Cmd == "move" || Cmd == "moveto" || Cmd == "turn" || Cmd == "scale" || Cmd == "hide"
		|| Cmd == "spawn" || Cmd == "raise" || Cmd == "lower" || Cmd == "flatten" || Cmd == "smooth"
		|| Cmd == "undo" || Cmd == "redo" || Cmd == "preview"))
	{
		Say("commit "$Word(CommitStatus, 0)$" is baking the journal: edits wait until it's done ('gm commit cancel' to edit now)");
		return;
	}
	if (Cmd == "")
		SetOn(!bOn);
	else if (Cmd == "commit")
		Commit(A1);
	else if (Cmd == "baked")
		Baked(int(A1), int(Word(Args, 2)), After(Args, 3));
	else if (Cmd == "committed")
		Committed(int(A1), Word(Args, 2), int(Word(Args, 3)));
	else if (Cmd == "commitfail")
		CommitFailed(int(A1), After(Args, 2));
	else if (Cmd == "travel")
		Travel(A1);
	else if (Cmd == "draw")
		DrawCmd(Args);
	else if (Cmd == "con")
	{
		// Console.ui's triggers (tools/sketch_console_ui.py): silent, only PanelState's con= changes
		if (A1 ~= "big")
			bConBig = Word(Args, 2) == "1";
		else if (A1 ~= "quick")
			bConQuick = Word(Args, 2) == "1";
	}
	else if (Cmd == "sketch")
		SketchCmd(Args);
	else if (Cmd == "tex")
		TexCmd(After(Args, 1));
	else if (Cmd == "on" || Cmd == "off")
		SetOn(Cmd == "on");
	else if (Cmd == "help")
	{
		Say("gm [on|off] | pick [NAME] | info | move DX DY DZ | moveto X Y Z|here | turn DEG | scale S | hide");
		Say("gm spawn N|PATH | palette [add PATH|clear] | snap SIZE | yawstep DEG | possess | release | freeze | undo | redo | journal");
		Say("gm raise R H | lower R H | flatten R | smooth R  (terrain at the crosshair, radius R, height H)");
		Say("the d3d8 fork's panel (F7) also sends: gm panel 1|0 | ray SX SY SZ EX EY EZ | preview X Y Z YAW");
		Say("gm commit [cancel] (bake into <map>_LiveN: gm_commit.py --watch) | travel MAP");
		Say("gm draw add [X Y Z] | undo | clear | done open|closed [NOTE] | list | forget N");
		Say("gm sketch mark NAME [NOTE] (the fork's sketch tool) | con big|quick 1|0 (Console.ui's triggers)");
		Say("gm tex HASH REV b c g s h sh sm sl sharp (the fork's texture panel; a global '@* tex' journal line)");
	}
	else if (Cmd == "panel")
	{
		bPanelFast = A1 == "1";
		PanelWait = 0;
	}
	else if (Cmd == "ray")
	{
		RayS.X = float(A1); RayS.Y = float(Word(Args, 2)); RayS.Z = float(Word(Args, 3));
		RayE.X = float(Word(Args, 4)); RayE.Y = float(Word(Args, 5)); RayE.Z = float(Word(Args, 6));
		bRay = true;
	}
	else if (Cmd == "preview")
	{
		// the gizmo's live preview: moved and turned, no journal line (the drag's end sends moveto / turn)
		if (!Editable())
			return;
		V.X = float(A1); V.Y = float(Word(Args, 2)); V.Z = float(Word(Args, 3));
		Picked.SetLocation(V);
		R = Picked.Rotation;
		R.Yaw = int(float(Word(Args, 4)) * 65536.0 / 360.0);
		Picked.SetRotation(R);
	}
	else if (Cmd == "pick")
	{
		if (A1 != "")
			A = Named(A1);
		else if (A1 ~= "pawn")
			A = UnderCrosshair(HitL, HitN);
		else
			A = MeshUnderCrosshair(HitL, HitN);
		if (A == Level || (A != None && A.IsA('TerrainInfo')))
			A = None;
		SetPicked(A);
		Say("picked "$Describe(Picked));
	}
	else if (Cmd == "info")
		Say("picked "$Describe(Picked)$"; "$CountOps()$" journal lines on "$Family()$", GM mode "$bOn);
	else if (Cmd == "move" || Cmd == "moveto" || Cmd == "turn" || Cmd == "scale")
	{
		if (!Editable())
			return;
		if (Cmd == "move")
		{
			V.X = float(A1); V.Y = float(Word(Args, 2)); V.Z = float(Word(Args, 3));
			Picked.SetLocation(Picked.Location + V);
		}
		else if (Cmd == "moveto" && A1 ~= "here")
		{
			if (SpawnSpot(V))
				Picked.SetLocation(V);
		}
		else if (Cmd == "moveto")
		{
			V.X = float(A1); V.Y = float(Word(Args, 2)); V.Z = float(Word(Args, 3));
			Picked.SetLocation(V);
		}
		else if (Cmd == "turn")
		{
			R = Picked.Rotation;
			R.Yaw += int(float(A1) * 65536.0 / 360.0);
			Picked.SetRotation(R);
		}
		else
			Picked.SetDrawScale(FMax(0.05, float(A1)));
		Remember();
		Say(Describe(Picked));
	}
	else if (Cmd == "hide")
	{
		if (Picked == None)
		{
			Say("nothing picked");
			return;
		}
		if (Left(PickedName, 5) == "mesh#")
			Change(int(Mid(PickedName, 5)), "");
		else if (Picked.bStatic || IsOurs(Picked))
		{
			k = FindOp("place", PickedName);
			if (k >= 0)
				Change(k, "hide "$PickedName);
			else
			{
				k = FreeOp();
				if (k < 0)
				{
					Say("journal full");
					return;
				}
				Change(k, "hide "$PickedName);
			}
		}
		else
		{
			Picked.bHidden = true;
			Picked.SetCollision(false, false, false);
			Say("hid "$PickedName$" live only (not a static mesh, not journalled)");
			return;
		}
		Say("hid "$PickedName);
		SetPicked(None);
		Replay();
	}
	else if (Cmd == "spawn")
		SpawnFromPalette(A1);
	else if (Cmd == "raise" || Cmd == "lower" || Cmd == "flatten" || Cmd == "smooth")
		TerrainBrush(Cmd, float(A1), float(Word(Args, 2)));
	else if (Cmd == "palette")
	{
		if (A1 ~= "add")
		{
			for (k = 0; k < ArrayCount(Palette); k++)
				if (Palette[k] == "")
				{
					Palette[k] = Word(Args, 2);
					SaveConfig();
					Say("palette "$k$": "$Palette[k]);
					return;
				}
			Say("palette full");
		}
		else if (A1 ~= "clear")
		{
			for (k = 0; k < ArrayCount(Palette); k++)
				Palette[k] = "";
			SaveConfig();
			Say("palette cleared");
		}
		else
		{
			for (k = 0; k < ArrayCount(Palette); k++)
				if (Palette[k] != "")
				{
					Say(k$": "$Palette[k]);
					n++;
				}
			if (n == 0)
				Say("the palette is empty: gm palette add Package.Group.Name");
		}
	}
	else if (Cmd == "snap")
	{
		GridSize = FMax(0, float(A1));
		SaveConfig();
		Say("grid "$GridSize);
	}
	else if (Cmd == "yawstep")
	{
		YawStep = Max(0, int(A1));
		SaveConfig();
		Say("yaw step "$YawStep);
	}
	else if (Cmd == "possess")
		Possess();
	else if (Cmd == "release")
		Release();
	else if (Cmd == "freeze")
	{
		Level.bPlayersOnly = !Level.bPlayersOnly;
		Say(Pick2(Level.bPlayersOnly, "frozen (gm freeze again to go on)", "the world goes on"));
	}
	else if (Cmd == "undo")
		TakeBack(false);
	else if (Cmd == "redo")
		TakeBack(true);
	else if (Cmd == "journal")
	{
		for (k = 0; k < ArrayCount(Ops); k++)
			if (GetOp(k) != "")
				Say(k$": "$GetOp(k));
		Say(CountOps()$" lines on "$Family());
	}
	else
		Say("unknown: "$Cmd$" ('gm help')");
}

defaultproperties
{
	GridSize=32
	YawStep=15
	PanelPoll=2.0
	PanelFile="U2GMPanel.txt"
	Palette(0)="Terran_DecoM.Crates.Crate1Low"
	RemoteRole=ROLE_None
}
