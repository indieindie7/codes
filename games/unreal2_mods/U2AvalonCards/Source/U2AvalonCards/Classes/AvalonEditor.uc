//=============================================================================
// AvalonEditor - live control of any actor in the running map, for AvalonLive
// ("avalon <cmd>"). One actor is "picked" at a time:
//
//   pick                      the actor under the player's crosshair
//   pick NAME                 by name (e.g. StaticMeshActor112)
//   picknear X Y Z [CLASS]    the nearest actor (of CLASS, default StaticMeshActor) to a point
//   move DX DY DZ             nudge it (world units)
//   moveto X Y Z              put it there
//   turn DEG                  turn it round the vertical (degrees)
//   scale S                   its DrawScale
//   hide / show / delete      (a map's own actor can't be deleted: hidden, and its collision off)
//   spawn MESH [X Y Z] [YAW] [SCALE]   a static mesh, at the point under the crosshair if no X Y Z
//   info                      what is picked: class, name, mesh, place
//   list [CLASS] [RADIUS]     the actors round the player (default StaticMeshActor, 3000)
//   journal / forget I        the recorded edits / drop one (applies on the next rebuild)
//
// The map's own static actors can't move at run time (bStatic), so the first
// move/turn/scale swaps one for a movable copy (CardMesh, the same mesh, skins
// and scale) and hides the original. Every edit is written into the journal
// (AvalonCards Ops[]): "place NAME X Y Z YAW SCALE", "hide NAME", "mesh PATH X Y Z
// YAW SCALE". The journal replays on every build (map load, rebuild) and
// "avalon save" keeps it in U2AvalonCards.ini, so a session's edits can be
// baked into the map later (U2Avalon/tools/live_bake.py).
//=============================================================================
class AvalonEditor extends Info;

var AvalonCards Cards;
var Actor Picked;
var string PickedName;      // the journal's name for it: the map actor's name, or "mesh#I"
var array<Actor> Made;      // what the journal replay spawned (copies, new meshes)
var array<string> MadeName; // each one's journal name: the map actor it stands in for, or "mesh#I"

function Say(PlayerController PC, coerce string S)
{
	Log("Cards: edit "$S);
	if (PC != None)
		PC.ClientMessage("[Claude] "$S);
}

function Actor Find(string N)
{
	local Actor A;

	foreach AllActors(class'Actor', A)
		if (string(A.Name) ~= N)
			return A;
	return None;
}

function string Describe(Actor A)
{
	local string S;

	if (A == None)
		return "nothing";
	S = string(A.Class.Name)$" "$A.Name;
	if (A.StaticMesh != None)
		S = S$" mesh "$A.StaticMesh;
	return S$" at "$int(A.Location.X)$" "$int(A.Location.Y)$" "$int(A.Location.Z)$" yaw "$int(A.Rotation.Yaw * 360.0 / 65536.0)$" scale "$A.DrawScale;
}

// ---------------------------------------------------------------- the journal

function int FindOp(string Kind, string N)
{
	local int i;

	for (i = 0; i < ArrayCount(Cards.Ops); i++)
		if (Cards.Word(Cards.Ops[i], 0) == Kind && Cards.Word(Cards.Ops[i], 1) ~= N)
			return i;
	return -1;
}

function int FreeOp()
{
	local int i;

	for (i = 0; i < ArrayCount(Cards.Ops); i++)
		if (Cards.Ops[i] == "")
			return i;
	return -1;
}

function Record(string Kind, string N, string Rest)
{
	local int i;

	i = FindOp(Kind, N);
	if (i < 0)
		i = FreeOp();
	if (i < 0)
	{
		Log("Cards: edit journal full");
		return;
	}
	Cards.Ops[i] = Kind$" "$N$" "$Rest;
}

function string Transform(Actor A)
{
	return int(A.Location.X)$" "$int(A.Location.Y)$" "$int(A.Location.Z)$" "$int(A.Rotation.Yaw * 360.0 / 65536.0)$" "$A.DrawScale;
}

// the picked actor's transform into the journal
function Remember()
{
	local int i;

	if (Picked == None)
		return;
	if (Left(PickedName, 5) == "mesh#")
	{
		i = int(Mid(PickedName, 5));
		Cards.Ops[i] = "mesh "$Picked.StaticMesh$" "$Transform(Picked);
	}
	else
		Record("place", PickedName, Transform(Picked));
}

// ---------------------------------------------------------------- the replay

function Clear()
{
	local int i;

	for (i = 0; i < Made.Length; i++)
		if (Made[i] != None)
			Made[i].Destroy();
	Made.Length = 0;
	MadeName.Length = 0;
	Picked = None;
}

function Replay()
{
	local int i;
	local string Op, N;
	local Actor A, C;

	Clear();
	for (i = 0; i < ArrayCount(Cards.Ops); i++)
	{
		Op = Cards.Word(Cards.Ops[i], 0);
		if (Op == "")
			continue;
		N = Cards.Word(Cards.Ops[i], 1);
		if (Op == "hide")
		{
			A = Find(N);
			if (A != None)
				HideActor(A);
		}
		else if (Op == "place")
		{
			A = Find(N);
			if (A == None)
				continue;
			C = CopyOf(A);
			if (C != None)
				Apply(C, Cards.Ops[i], 2);
		}
		else if (Op == "mesh")
		{
			C = SpawnMesh(N, vect(0,0,0));
			if (C != None)
			{
				MadeName[MadeName.Length - 1] = "mesh#"$i;
				Apply(C, Cards.Ops[i], 2);
			}
		}
	}
}

// words From.. of Line are X Y Z YAW SCALE
function Apply(Actor A, string Line, int From)
{
	local vector P;
	local rotator R;

	P.X = float(Cards.Word(Line, From));
	P.Y = float(Cards.Word(Line, From + 1));
	P.Z = float(Cards.Word(Line, From + 2));
	R = A.Rotation;
	R.Yaw = int(float(Cards.Word(Line, From + 3)) * 65536.0 / 360.0);
	A.SetLocation(P);
	A.SetRotation(R);
	if (Cards.Word(Line, From + 4) != "")
		A.SetDrawScale(float(Cards.Word(Line, From + 4)));
}

function HideActor(Actor A)
{
	A.bHidden = True;
	A.SetCollision(False, False, False);
}

// a movable stand-in for a map's static actor: same mesh, skins, scale; the original hidden
function Actor CopyOf(Actor A)
{
	local CardMesh C;
	local int k;

	if (A.StaticMesh == None)
		return None;
	C = Spawn(class'CardMesh',,, A.Location, A.Rotation);
	if (C == None)
		return None;
	C.StaticMesh = A.StaticMesh;
	C.SetDrawType(DT_StaticMesh);
	C.SetDrawScale(A.DrawScale);
	C.SetDrawScale3D(A.DrawScale3D);
	for (k = 0; k < A.Skins.Length; k++)
		C.Skins[k] = A.Skins[k];
	C.SetCollision(True, True, True);
	C.bCollideWorld = False;
	HideActor(A);
	Made[Made.Length] = C;
	MadeName[MadeName.Length] = string(A.Name);
	return C;
}

function Actor SpawnMesh(string Path, vector P)
{
	local CardMesh C;

	C = Spawn(class'CardMesh',,, P);
	if (C == None)
		return None;
	if (!C.Show(Path, 1.0))
		return None;
	C.SetCollision(True, True, True);
	C.bCollideWorld = False;
	Made[Made.Length] = C;
	MadeName[MadeName.Length] = "";
	return C;
}

// the map's original behind a copy (so "pick" on a copy still edits the right journal line)
function bool IsCopy(Actor A)
{
	return CopyIndex(A) >= 0;
}

function int CopyIndex(Actor A)
{
	local int i;

	for (i = 0; i < Made.Length; i++)
		if (Made[i] == A)
			return i;
	return -1;
}

// ---------------------------------------------------------------- the commands

function Actor UnderCrosshair(PlayerController PC, out vector HitL)
{
	local vector S, E, HitN;
	local Actor A;

	if (PC == None || PC.Pawn == None)
		return None;
	S = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	E = S + vector(PC.Rotation) * 60000;
	A = PC.Pawn.Trace(HitL, HitN, E, S, true);
	return A;
}

function SetPicked(Actor A)
{
	Picked = A;
	if (A == None)
		PickedName = "";
	else if (IsCopy(A))
		PickedName = MadeName[CopyIndex(A)];
	else
		PickedName = string(A.Name);
}

// a map actor about to be changed becomes its movable copy (once)
function bool Editable(PlayerController PC)
{
	local Actor C;

	if (Picked == None)
	{
		Say(PC, "nothing picked");
		return false;
	}
	if (Picked.bStatic && !IsCopy(Picked))
	{
		C = CopyOf(Picked);
		if (C == None)
		{
			Say(PC, "can't move "$Picked.Name$" (no static mesh)");
			return false;
		}
		PickedName = string(Picked.Name);
		Picked = C;
	}
	return true;
}

function bool Command(string Cmd, string Arg, PlayerController PC)
{
	local Actor A, Best;
	local vector P, HitL;
	local rotator R;
	local float D, BestD, Rad;
	local int i, n;
	local class<Actor> Cls;

	switch (Cmd)
	{
	case "PICK":
		if (Arg != "")
			SetPicked(Find(Arg));
		else
			SetPicked(UnderCrosshair(PC, HitL));
		Say(PC, "picked "$Describe(Picked));
		return true;
	case "PICKNEAR":
		P.X = float(Cards.Word(Arg, 0));
		P.Y = float(Cards.Word(Arg, 1));
		P.Z = float(Cards.Word(Arg, 2));
		Cls = class'StaticMeshActor';
		if (Cards.Word(Arg, 3) != "")
			Cls = class<Actor>(DynamicLoadObject(Cards.Word(Arg, 3), class'Class', true));
		if (Cls == None)
			Cls = class'Actor';
		BestD = 1e9;
		foreach AllActors(Cls, A)
		{
			if (A.bHidden && !IsCopy(A))
				continue;
			D = VSize(A.Location - P);
			if (D < BestD)
			{
				BestD = D;
				Best = A;
			}
		}
		SetPicked(Best);
		Say(PC, "picked "$Describe(Picked));
		return true;
	case "INFO":
		Say(PC, Describe(Picked));
		return true;
	case "MOVE":
	case "MOVETO":
	case "TURN":
	case "SCALE":
		if (!Editable(PC))
			return true;
		if (Cmd == "MOVE")
		{
			P.X = float(Cards.Word(Arg, 0));
			P.Y = float(Cards.Word(Arg, 1));
			P.Z = float(Cards.Word(Arg, 2));
			Picked.SetLocation(Picked.Location + P);
		}
		else if (Cmd == "MOVETO")
		{
			P.X = float(Cards.Word(Arg, 0));
			P.Y = float(Cards.Word(Arg, 1));
			P.Z = float(Cards.Word(Arg, 2));
			Picked.SetLocation(P);
		}
		else if (Cmd == "TURN")
		{
			R = Picked.Rotation;
			R.Yaw += int(float(Arg) * 65536.0 / 360.0);
			Picked.SetRotation(R);
		}
		else
			Picked.SetDrawScale(float(Arg));
		Remember();
		Say(PC, Cmd$" -> "$Describe(Picked));
		return true;
	case "HIDE":
	case "DELETE":
		if (Picked == None)
			return true;
		if (Left(PickedName, 5) == "mesh#")
			Cards.Ops[int(Mid(PickedName, 5))] = "";
		else
		{
			i = FindOp("place", PickedName);
			if (i >= 0)
				Cards.Ops[i] = "";
			Record("hide", PickedName, "");
			A = Find(PickedName);
			if (A != None)
				HideActor(A);
		}
		if (IsCopy(Picked) || !Picked.bStatic)
			Picked.Destroy();
		else
			HideActor(Picked);
		Say(PC, "hid "$PickedName);
		SetPicked(None);
		return true;
	case "SHOW":
		if (PickedName == "")
			return true;
		i = FindOp("hide", PickedName);
		if (i >= 0)
			Cards.Ops[i] = "";
		A = Find(PickedName);
		if (A != None)
		{
			A.bHidden = False;
			A.SetCollision(True, True, True);
		}
		Say(PC, "showing "$PickedName);
		return true;
	case "SPAWN":
		n = FreeOp();
		if (n < 0)
			return true;
		if (Cards.Word(Arg, 1) != "")
		{
			P.X = float(Cards.Word(Arg, 1));
			P.Y = float(Cards.Word(Arg, 2));
			P.Z = float(Cards.Word(Arg, 3));
		}
		else
			UnderCrosshair(PC, P);
		A = SpawnMesh(Cards.Word(Arg, 0), P);
		if (A == None)
		{
			Say(PC, "no mesh "$Cards.Word(Arg, 0));
			return true;
		}
		R.Yaw = int(float(Cards.Word(Arg, 4)) * 65536.0 / 360.0);
		A.SetRotation(R);
		if (Cards.Word(Arg, 5) != "")
			A.SetDrawScale(float(Cards.Word(Arg, 5)));
		MadeName[MadeName.Length - 1] = "mesh#"$n;
		SetPicked(A);
		Cards.Ops[n] = "mesh "$A.StaticMesh$" "$Transform(A);
		Say(PC, "spawned "$Describe(A));
		return true;
	case "LIST":
		Cls = class'StaticMeshActor';
		if (Cards.Word(Arg, 0) != "")
			Cls = class<Actor>(DynamicLoadObject(Cards.Word(Arg, 0), class'Class', true));
		Rad = 3000;
		if (Cards.Word(Arg, 1) != "")
			Rad = float(Cards.Word(Arg, 1));
		if (Cls == None || PC == None || PC.Pawn == None)
			return true;
		n = 0;
		foreach AllActors(Cls, A)
			if (VSize(A.Location - PC.Pawn.Location) < Rad && n < 60)
			{
				Log("Cards: edit list "$Describe(A));
				n++;
			}
		Say(PC, n$" "$Cls.Name$" within "$int(Rad)$" (see the log)");
		return true;
	case "JOURNAL":
		for (i = 0; i < ArrayCount(Cards.Ops); i++)
			if (Cards.Ops[i] != "")
				Log("Cards: edit journal "$i$" "$Cards.Ops[i]);
		return true;
	case "FORGET":
		i = int(Arg);
		if (i >= 0 && i < ArrayCount(Cards.Ops))
			Cards.Ops[i] = "";
		return true;
	}
	return false;
}

defaultproperties
{
	RemoteRole=ROLE_None
}
