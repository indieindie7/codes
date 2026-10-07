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
// For remaking an area while the user plays (they point, Claude rebuilds):
//   mark [NOTE]               the player's place and view, what's under the crosshair, and a
//                             screenshot (System\Shot*.bmp): "where I'm looking, remake this"
//   spawn MESH X Y [YAW] [SCALE]        X Y only = stood on the ground there
//   clear X Y R               hide the map's own static meshes within R of X Y (journalled)
//   row CARD X1 Y1 X2 Y2 N SIZE [FACEX FACEY]  N imposter cards along a line
//   scatter CARD X Y R N SIZE [FACEX FACEY]    N imposter cards within R
//                             (cards face FACEX FACEY - default the command room's window)
//   cardat NAME X Y YAW SIZE  an imposter card (U2AvalonCards.NAME0..7, or Pkg.Group.Name) on the ground
//   undo                      take back the last edit of this session
//
// The map's own static actors can't move at run time (bStatic), so the first
// move/turn/scale swaps one for a movable copy (CardMesh, the same mesh, skins
// and scale) and hides the original. Every edit is written into the journal
// (AvalonCards Ops[]): "place NAME X Y Z YAW SCALE", "hide NAME", "mesh PATH X Y Z
// YAW SCALE". The journal replays on every build (map load, rebuild) and
// "avalon save" keeps it in U2AvalonCards.ini, so a session's edits can be
// baked into the map later (U2Avalon/tools/live_bake.py).
//=============================================================================
class AvalonEditor extends Info
	config(U2AvalonCards);

// the user's call (2026-10-07): live edits are procedural generation and imposter cards only, for now.
// The mesh tools (move, turn, scale, hide, show, delete, spawn, clear) stay in the code, off unless
// bMeshEdits is set in U2AvalonCards.ini [U2AvalonCards.AvalonEditor].
var config bool bMeshEdits;

var AvalonCards Cards;
var Actor Picked;
var string PickedName;      // the journal's name for it: the map actor's name, or "mesh#I"
var array<Actor> Made;      // what the journal replay spawned (copies, new meshes)
var array<string> MadeName; // each one's journal name: the map actor it stands in for, or "mesh#I"
var array<int> Undo;        // journal lines written this session, newest last
var array<string> UndoWas;  // what each line said before (to restore)
var int Marks;

function Say(PlayerController PC, coerce string S)
{
	Log("Cards: edit "$S);
	if (PC != None)
		PC.ClientMessage("[Claude] "$S);
}

// a class by name; a bare name is looked for in Engine (StaticMeshActor, Light, ...)
function class<Actor> ClassNamed(string N)
{
	if (N == "")
		return class'StaticMeshActor';
	if (InStr(N, ".") < 0)
		N = "Engine."$N;
	return class<Actor>(DynamicLoadObject(N, class'Class', true));
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
	Push(i);
	Cards.Ops[i] = Kind$" "$N$" "$Rest;
}

// where cards should face: words From, From+1 of Arg, or the command room's window (the tower)
function vector Facing(string Arg, int From)
{
	local vector F;

	if (Cards.Word(Arg, From + 1) != "")
	{
		F.X = float(Cards.Word(Arg, From));
		F.Y = float(Cards.Word(Arg, From + 1));
	}
	else
	{
		F.X = -349;
		F.Y = 1388;
	}
	return F;
}

function int FaceYaw(vector P, vector F)
{
	local rotator R;

	R = rotator(F - P);
	return R.Yaw * 360 / 65536;
}

function Push(int i)
{
	Undo[Undo.Length] = i;
	UndoWas[UndoWas.Length] = Cards.Ops[i];
}

// the ground (terrain, level geometry) under X Y, ignoring meshes (roofs)
function float GroundZ(float X, float Y)
{
	local vector S, E, HitL, HitN;

	S.X = X; S.Y = Y; S.Z = 50000;
	E.X = X; E.Y = Y; E.Z = -50000;
	if (Trace(HitL, HitN, E, S, false) != None)
		return HitL.Z;
	return 0;
}

function int MadeIndex(string N)
{
	local int i;

	for (i = 0; i < MadeName.Length; i++)
		if (MadeName[i] ~= N && Made[i] != None)
			return i;
	return -1;
}

// a new mesh on the journal and in the world
function Actor NewMesh(string Path, vector P, int YawDeg, float Scale)
{
	local Actor A;
	local rotator R;
	local int n;

	n = FreeOp();
	if (n < 0)
		return None;
	A = SpawnMesh(Path, P);
	if (A == None)
		return None;
	R.Yaw = YawDeg * 65536 / 360;
	A.SetRotation(R);
	if (Scale > 0)
		A.SetDrawScale(Scale);
	MadeName[MadeName.Length - 1] = "mesh#"$n;
	Push(n);
	Cards.Ops[n] = "mesh "$A.StaticMesh$" "$Transform(A);
	return A;
}

// an imposter card on the journal and in the world
function Actor NewCard(string Line)
{
	local int n;

	n = FreeOp();
	if (n < 0)
		return None;
	Cards.PlaceCard(Line$" 8");
	if (Cards.Made.Length == 0)
		return None;
	Made[Made.Length] = Cards.Made[Cards.Made.Length - 1];
	MadeName[MadeName.Length] = "card#"$n;
	Push(n);
	Cards.Ops[n] = "card "$Line;
	return Made[Made.Length - 1];
}

function TakeBack(PlayerController PC)
{
	local int i, k;
	local string Op, N;
	local Actor A;

	if (Undo.Length == 0)
	{
		Say(PC, "nothing to undo");
		return;
	}
	i = Undo[Undo.Length - 1];
	Op = Cards.Word(Cards.Ops[i], 0);
	N = Cards.Word(Cards.Ops[i], 1);
	if (Op == "mesh" || Op == "card")
	{
		k = MadeIndex(Op$"#"$i);
		if (k >= 0)
			Made[k].Destroy();
	}
	else if (Op == "hide" || Op == "place")
	{
		k = MadeIndex(N);
		if (Op == "place" && k >= 0)
			Made[k].Destroy();
		A = Find(N);
		if (A != None)
		{
			A.bHidden = False;
			A.SetCollision(True, True, True);
		}
	}
	Cards.Ops[i] = UndoWas[UndoWas.Length - 1];
	if (Cards.Ops[i] != "")
		Say(PC, "undo: back to "$Cards.Ops[i]$" (applies on the next rebuild)");
	else
		Say(PC, "undo: "$Op$" "$N);
	Undo.Length = Undo.Length - 1;
	UndoWas.Length = UndoWas.Length - 1;
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
		else if (Op == "card")
		{
			Cards.PlaceCard(Mid(Cards.Ops[i], 5)$" 8");
			if (Cards.Made.Length > 0)
			{
				Made[Made.Length] = Cards.Made[Cards.Made.Length - 1];
				MadeName[MadeName.Length] = "card#"$i;
			}
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
	local vector F;

	if (!bMeshEdits && (Cmd == "MOVE" || Cmd == "MOVETO" || Cmd == "TURN" || Cmd == "SCALE" || Cmd == "HIDE"
		|| Cmd == "SHOW" || Cmd == "DELETE" || Cmd == "SPAWN" || Cmd == "CLEAR"))
	{
		Say(PC, Cmd$" is off: live edits are procedural generation and imposter cards for now");
		return true;
	}
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
		Cls = ClassNamed(Cards.Word(Arg, 3));
		if (Cls == None)
			Cls = class'Actor';
		BestD = 1000000000.0;
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
			if (Cards.Word(Arg, 3) == "" || Cards.Word(Arg, 3) ~= "g")
				P.Z = GroundZ(P.X, P.Y);
			else
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
		Push(n);
		Cards.Ops[n] = "mesh "$A.StaticMesh$" "$Transform(A);
		Say(PC, "spawned "$Describe(A));
		return true;
	case "MARK":
		Marks++;
		if (PC == None || PC.Pawn == None)
			return true;
		A = UnderCrosshair(PC, HitL);
		Log("Cards: edit MARK "$Marks$" at "$int(PC.Pawn.Location.X)$" "$int(PC.Pawn.Location.Y)$" "$int(PC.Pawn.Location.Z)
			$" yaw "$(int(PC.Rotation.Yaw * 360.0 / 65536.0) % 360)$" pitch "$(((PC.Rotation.Pitch + 32768) & 65535) - 32768) * 360 / 65536
			$" looking-at "$int(HitL.X)$" "$int(HitL.Y)$" "$int(HitL.Z)$" "$Describe(A)$" note "$Arg);
		PC.ConsoleCommand("shot");
		Say(PC, "mark "$Marks$" taken: Claude can see this spot now");
		return true;
	case "CLEAR":
		P.X = float(Cards.Word(Arg, 0));
		P.Y = float(Cards.Word(Arg, 1));
		Rad = float(Cards.Word(Arg, 2));
		n = 0;
		foreach AllActors(class'Actor', A)
		{
			if (!A.IsA('StaticMeshActor') || A.bHidden || VSize((A.Location - P) * vect(1,1,0)) > Rad)
				continue;
			Record("hide", string(A.Name), "");
			HideActor(A);
			n++;
		}
		Say(PC, "cleared "$n$" meshes within "$int(Rad)$" of "$int(P.X)$" "$int(P.Y));
		return true;
	case "ROW":
		n = int(Cards.Word(Arg, 5));
		F = Facing(Arg, 7);
		for (i = 0; i < n; i++)
		{
			D = (i + 0.5) / FMax(n, 1);
			P.X = Lerp(D, float(Cards.Word(Arg, 1)), float(Cards.Word(Arg, 3)));
			P.Y = Lerp(D, float(Cards.Word(Arg, 2)), float(Cards.Word(Arg, 4)));
			NewCard(Cards.Word(Arg, 0)$" "$int(P.X)$" "$int(P.Y)$" "$FaceYaw(P, F)$" "$Cards.Word(Arg, 6));
		}
		Say(PC, "row of "$n$" "$Cards.Word(Arg, 0));
		return true;
	case "SCATTER":
		n = int(Cards.Word(Arg, 4));
		Rad = float(Cards.Word(Arg, 3));
		F = Facing(Arg, 6);
		for (i = 0; i < n; i++)
		{
			D = FRand() * 6.2832;
			BestD = Rad * Sqrt(FRand());
			P.X = float(Cards.Word(Arg, 1)) + BestD * Cos(D);
			P.Y = float(Cards.Word(Arg, 2)) + BestD * Sin(D);
			NewCard(Cards.Word(Arg, 0)$" "$int(P.X)$" "$int(P.Y)$" "$FaceYaw(P, F)$" "$Cards.Word(Arg, 5));
		}
		Say(PC, "scattered "$n$" "$Cards.Word(Arg, 0));
		return true;
	case "CARDAT":
		A = NewCard(Arg);
		Say(PC, "card "$Arg$" -> "$A);
		return true;
	case "UNDO":
		TakeBack(PC);
		return true;
	case "LIST":
		Cls = ClassNamed(Cards.Word(Arg, 0));
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
