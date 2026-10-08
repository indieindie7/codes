//=============================================================================
// GMMaster - the game master: GM mode, the picked actor, the journal, undo.
//
//   gm [on|off]           GM mode: free camera through walls, no damage (toggles without a word)
//   gm pick [NAME]        what's under the crosshair, or an actor by name
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
//
// The world is always the map plus its journal: every edit writes a journal
// line and the world follows; undo and redo change the journal and replay it.
// A map's static actors can't move (bStatic): the first move swaps one for a
// movable copy (GMMesh) and hides the original ("place NAME ...").
// The journal is shared by all maps: each line starts "@<map family>"
// (TutA_Live3 -> tuta), as in AvalonEditor.
//=============================================================================
class GMMaster extends Info
	config(U2GM);

var config string Ops[256];         // the journal ("@family op ...")
var config string Palette[32];      // spawnable static meshes (Package.Group.Name)
var config float GridSize;          // spawn snap in world units (0 = off)
var config int YawStep;             // spawn and turn snap in degrees

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

// one journal change: remembered for undo, the redo list dropped, saved
function Change(int k, string L)
{
	UndoAt[UndoAt.Length] = k;
	UndoWas[UndoWas.Length] = GetOp(k);
	RedoAt.Length = 0;
	RedoWas.Length = 0;
	SetOp(k, L);
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

function Actor UnderCrosshair(out vector HitL, out vector HitN)
{
	local vector S, E;

	S = EyeSpot();
	E = S + vector(PC.Rotation) * 60000;
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
		RedoWas[RedoWas.Length] = GetOp(k);
	}
	else
	{
		k = RedoAt[RedoAt.Length - 1];
		L = RedoWas[RedoWas.Length - 1];
		RedoAt.Length = RedoAt.Length - 1;
		RedoWas.Length = RedoWas.Length - 1;
		UndoAt[UndoAt.Length] = k;
		UndoWas[UndoWas.Length] = GetOp(k);
	}
	SetOp(k, L);
	SaveConfig();
	Replay();
	Say(Pick2(bRedo, "redo", "undo")$": line "$k$" now '"$L$"'");
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

// ---------------------------------------------------------------- the command

function Command(string Args)
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
	if (Cmd == "")
		SetOn(!bOn);
	else if (Cmd == "on" || Cmd == "off")
		SetOn(Cmd == "on");
	else if (Cmd == "help")
	{
		Say("gm [on|off] | pick [NAME] | info | move DX DY DZ | moveto X Y Z|here | turn DEG | scale S | hide");
		Say("gm spawn N|PATH | palette [add PATH|clear] | snap SIZE | yawstep DEG | possess | release | freeze | undo | redo | journal");
	}
	else if (Cmd == "pick")
	{
		if (A1 != "")
			A = Named(A1);
		else
			A = UnderCrosshair(HitL, HitN);
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
	Palette(0)="Terran_DecoM.Crates.Crate1Low"
	RemoteRole=ROLE_None
}
