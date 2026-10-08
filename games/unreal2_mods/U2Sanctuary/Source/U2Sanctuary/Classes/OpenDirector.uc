//=============================================================================
// OpenDirector - Sanctuary Open's story, fights and story props: the shipped
// Sanctuary maps' own beats, imported onto the one open map (open/import_m08.py
// writes them into U2Sanctuary.ini [U2Sanctuary.OpenDirector]).
//
//  BEATS   in order: a beat fires when the player is within its Radius and the beat
//          it comes After has fired ("X!" = after encounter X's last wave is cleared).
//          It plays the original conversations (the game's own voiced lines and
//          subtitles: the dialogue engine loads DialogDirs, then each Topic is a node
//          name - DialogEngine.Initiate, as the maps' AI scripts' dialoginitiate),
//          shows its objective, and starts its encounter
//  WAVES   an encounter's waves come out of the playable areas' spawn-shed doors
//          (Doors "x,y,z;..."), held until the beat starts the encounter
//          (SevenSanctuary's hold and release): "enter" = at the start, "cleared" =
//          when the wave before is all dead, "lasthalf" = when half of it is; Delay
//          seconds after that, with a call from the door first (a tell)
//  BARKS   while a fight is on, now and then one of Miller's camera barks
//  BODIES  the dead colonists, killed where they lie at the start (permanent, and
//          U2Gore pools them); PROPS meshes spawned at run time (the hauler wreck);
//          THINGS actors (the explosive canisters)
// Console: set OpenDirector bLog True. Spawned by SanctuaryMutator on PrairieSanctuary.
//=============================================================================
class OpenDirector extends Info
	config(U2Sanctuary);

struct OBeat
{
	var string Id;
	var vector At;
	var float Radius;
	var string Topics;
	var string Objective;
	var string Encounter;
	var string After;
};
struct OWave
{
	var string Encounter;
	var string Pawns;
	var string Doors;
	var string When;
	var float Delay;
};
struct OBody
{
	var string Class;
	var vector At;
	var int Yaw;
};
struct OProp
{
	var string Mesh;
	var vector At;
	var int Yaw;
	var float Scale;
};
struct OThing
{
	var string Class;
	var vector At;
};
var config array<OBeat> Beats;
var config array<OWave> Waves;
var config array<OBody> Bodies;
var config array<OProp> Props;
var config array<OThing> Things;
var config string DialogDirs, Barks;
var config bool bEnabled, bLog;
var config float WaveTimeout, RestAfterFight;   // the next wave comes after this many seconds anyway; a rest before a new encounter

var array<int> BeatFired;          // 1 when fired
var array<int> WaveState;          // 0 held, 1 armed (timer running), 2 out
var array<float> WaveAt;
var array<Pawn> Alive;             // the director's enemies
var array<int> AliveWave;
var array<int> WaveSpawned;
var array<string> TopicQueue;
var float NextTalk, NextBark;
var name TopicName;
var bool bStarted;
var int Killed;
var float LastClear;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(0.5, true);
}

function PlayerController ThePlayer()
{
	local Controller C;

	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
			return PlayerController(C);
	return None;
}

function Say(string S)
{
	local DialogEngine DE;

	DE = class'DialogEngine'.static.GetInstance(Self);
	if (DE != None)
		class'UIConsole'.static.BroadcastStatusMessage(Self, S, 5.0, DE.SubtitleFont, DE.SubtitleColorOther, , , , "DialogSubtitlesHolder", true, DE.SubtitleBoxWidth);
	Log("U2Sanctuary open: "$S);
}

function Start()
{
	local DialogEngine DE;
	local int i;
	local string Dirs, D;

	bStarted = true;
	BeatFired.Length = Beats.Length;
	WaveState.Length = Waves.Length;
	WaveAt.Length = Waves.Length;
	WaveSpawned.Length = Waves.Length;
	// the original maps' dialogue, on this map
	DE = class'DialogEngine'.static.GetInstance(Self);
	Dirs = DialogDirs;
	while (DE != None && Dirs != "")
	{
		i = InStr(Dirs, ",");
		if (i < 0)
		{
			D = Dirs;
			Dirs = "";
		}
		else
		{
			D = Left(Dirs, i);
			Dirs = Mid(Dirs, i + 1);
		}
		DE.LoadDialogFiles(D);
	}
	PlaceBodies();
	for (i = 0; i < Props.Length; i++)
		SpawnProp(Props[i]);
	for (i = 0; i < Things.Length; i++)
		SpawnThing(Things[i]);
	Log("U2Sanctuary open: "$Beats.Length$" beats, "$Waves.Length$" waves, "$Bodies.Length$" bodies, dialogue "$DialogDirs);
}

function PlaceBodies()
{
	local int i;
	local class<Pawn> PC;
	local Pawn P;
	local rotator R;
	local GoreManager G;

	foreach DynamicActors(class'GoreManager', G)
		break;
	for (i = 0; i < Bodies.Length; i++)
	{
		PC = class<Pawn>(DynamicLoadObject(Bodies[i].Class, class'Class', true));
		if (PC == None)
			continue;
		R.Yaw = Bodies[i].Yaw;
		P = Spawn(PC,,, Bodies[i].At, R);
		if (P == None)
			continue;
		if (U2Pawn(P) != None)
		{
			U2Pawn(P).bQuickCarcassCleanup = false;
			U2Pawn(P).TimeBeforeCarcassDestroyed = 0;
		}
		P.TakeDamage(P.Health + 20, None, P.Location + vect(0,0,30), vect(0,0,0), class'DamageType');
		if (G != None)
			G.AddDying(P);
	}
}

function SpawnProp(OProp O)
{
	local SanctuaryCover C;
	local StaticMesh M;
	local rotator R;

	M = StaticMesh(DynamicLoadObject(O.Mesh, class'StaticMesh', true));
	if (M == None)
		return;
	R.Yaw = O.Yaw;
	C = Spawn(class'SanctuaryCover',,, O.At, R);
	if (C == None)
		return;
	C.StaticMesh = M;
	C.SetDrawScale(O.Scale);
	C.SetCollision(false, false, false);
	C.SetCollision(true, true, true);
}

function SpawnThing(OThing O)
{
	local class<Actor> AC;

	AC = class<Actor>(DynamicLoadObject(O.Class, class'Class', true));
	if (AC != None)
		Spawn(AC,,, O.At);
}

function int BeatIndex(string Id)
{
	local int i;

	for (i = 0; i < Beats.Length; i++)
		if (Beats[i].Id ~= Id)
			return i;
	return -1;
}

// "X" = beat X fired; "X!" = beat X fired and its encounter's waves are all out and dead
function bool AfterDone(string A)
{
	local int i;
	local bool bClear;

	if (A == "")
		return true;
	bClear = Right(A, 1) == "!";
	if (bClear)
		A = Left(A, Len(A) - 1);
	i = BeatIndex(A);
	if (i < 0)
		return true;
	if (BeatFired[i] == 0)
		return false;
	return !bClear || EncounterDone(Beats[i].Encounter);
}

function bool EncounterDone(string E)
{
	local int i;

	if (E == "")
		return true;
	for (i = 0; i < Waves.Length; i++)
		if (Waves[i].Encounter ~= E && WaveState[i] != 2)
			return false;
	for (i = 0; i < Alive.Length; i++)
		if (Waves[AliveWave[i]].Encounter ~= E)
			return false;
	return true;
}

function int AliveOf(int W)
{
	local int i, n;

	for (i = 0; i < Alive.Length; i++)
		if (AliveWave[i] == W)
			n++;
	return n;
}

function QueueTopics(string T)
{
	local int i;

	while (T != "")
	{
		i = InStr(T, ",");
		if (i < 0)
		{
			TopicQueue[TopicQueue.Length] = T;
			return;
		}
		TopicQueue[TopicQueue.Length] = Left(T, i);
		T = Mid(T, i + 1);
	}
}

function bool FightOn()
{
	return Alive.Length > 0;
}

event Timer()
{
	local PlayerController PC;
	local int i, j;
	local bool bReady;

	if (!bEnabled)
		return;
	PC = ThePlayer();
	if (PC == None || PC.Pawn == None)
		return;
	if (!bStarted)
		Start();
	// the dead leave the list
	for (i = Alive.Length - 1; i >= 0; i--)
		if (Alive[i] == None || Alive[i].bDeleteMe || Alive[i].Health <= 0)
		{
			Alive.Remove(i, 1);
			AliveWave.Remove(i, 1);
			Killed++;
			if (Alive.Length == 0)
				LastClear = Level.TimeSeconds;
		}
	// beats
	for (i = 0; i < Beats.Length; i++)
	{
		if (BeatFired[i] != 0 || !AfterDone(Beats[i].After))
			continue;
		if (VSize((PC.Pawn.Location - Beats[i].At) * vect(1,1,0)) > Beats[i].Radius)
			continue;
		BeatFired[i] = 1;
		if (bLog)
			Log("U2Sanctuary open: beat "$Beats[i].Id);
		QueueTopics(Beats[i].Topics);
		if (Beats[i].Objective != "")
			Say("Objective: "$Beats[i].Objective);
		for (j = 0; j < Waves.Length; j++)
			if (Waves[j].Encounter ~= Beats[i].Encounter && Waves[j].When ~= "enter" && WaveState[j] == 0)
			{
				WaveState[j] = 1;
				// a rest after the last fight before a new encounter comes out (30-45 s, L4D's Relax)
				WaveAt[j] = FMax(Level.TimeSeconds + Waves[j].Delay, LastClear + RestAfterFight);
			}
	}
	// waves that follow other waves
	for (j = 1; j < Waves.Length; j++)
	{
		if (WaveState[j] != 0 || !(Waves[j].Encounter ~= Waves[j - 1].Encounter) || WaveState[j - 1] != 2)
			continue;
		// (pacing research: the next wave at 25-50 % alive, or after 60 s whatever happens)
		bReady = (Waves[j].When ~= "cleared" && AliveOf(j - 1) == 0) ||
			(Waves[j].When ~= "lasthalf" && AliveOf(j - 1) * 2 <= WaveSpawned[j - 1]) ||
			Level.TimeSeconds - WaveAt[j - 1] > WaveTimeout;
		if (bReady)
		{
			WaveState[j] = 1;
			WaveAt[j] = Level.TimeSeconds + Waves[j].Delay;
		}
	}
	for (j = 0; j < Waves.Length; j++)
		if (WaveState[j] == 1 && Level.TimeSeconds >= WaveAt[j])
			Release(j, PC.Pawn);
	// the conversations, one at a time
	if (TopicQueue.Length > 0 && Level.TimeSeconds >= NextTalk && !class'DialogEngine'.static.IsAlreadyTalking(PC.Pawn))
	{
		SetPropertyText("TopicName", TopicQueue[0]);
		class'DialogEngine'.static.Initiate(PC.Pawn, None, TopicName);
		if (bLog)
			Log("U2Sanctuary open: talk "$TopicQueue[0]);
		TopicQueue.Remove(0, 1);
		NextTalk = Level.TimeSeconds + 1.5;
	}
	// a bark now and then while a fight is on
	if (FightOn() && TopicQueue.Length == 0 && Level.TimeSeconds >= NextBark && Barks != "")
	{
		NextBark = Level.TimeSeconds + 14 + FRand() * 10;
		if (FRand() < 0.6)
			QueueTopics(PickBark());
	}
}

function string PickBark()
{
	local array<string> B;
	local string T;
	local int i;

	T = Barks;
	while (T != "")
	{
		i = InStr(T, ",");
		if (i < 0)
		{
			B[B.Length] = T;
			break;
		}
		B[B.Length] = Left(T, i);
		T = Mid(T, i + 1);
	}
	return B[Rand(B.Length)];
}

// a wave comes out of its doors: "Class:n,Class:n" round the doors "x,y,z;x,y,z"
function Release(int W, Pawn Target)
{
	local array<vector> D;
	local string S, Item, Cls;
	local int i, n, k, made;
	local vector V, Off;
	local class<Pawn> PCl;
	local Pawn P;
	local rotator R;

	WaveState[W] = 2;
	S = Waves[W].Doors;
	while (S != "")
	{
		i = InStr(S, ";");
		if (i < 0)
		{
			Item = S;
			S = "";
		}
		else
		{
			Item = Left(S, i);
			S = Mid(S, i + 1);
		}
		V.X = float(Left(Item, InStr(Item, ",")));
		Item = Mid(Item, InStr(Item, ",") + 1);
		V.Y = float(Left(Item, InStr(Item, ",")));
		V.Z = float(Mid(Item, InStr(Item, ",") + 1));
		D[D.Length] = V;
	}
	if (D.Length == 0)
		return;
	S = Waves[W].Pawns;
	while (S != "")
	{
		i = InStr(S, ",");
		if (i < 0)
		{
			Item = S;
			S = "";
		}
		else
		{
			Item = Left(S, i);
			S = Mid(S, i + 1);
		}
		Cls = Left(Item, InStr(Item, ":"));
		n = int(Mid(Item, InStr(Item, ":") + 1));
		PCl = class<Pawn>(DynamicLoadObject("U2Pawns."$Cls, class'Class', true));
		if (PCl == None)
			continue;
		for (k = 0; k < n; k++)
		{
			V = D[(made + k) % D.Length];
			Off = VRand() * vect(1,1,0) * (80 + 70 * k);
			R = rotator(Target.Location - V);
			R.Pitch = 0;
			P = Spawn(PCl,,, V + Off, R);
			if (P == None)
				P = Spawn(PCl,,, V + vect(0,0,120), R);
			if (P == None)
				continue;
			Alive[Alive.Length] = P;
			AliveWave[AliveWave.Length] = W;
			WaveSpawned[W] = WaveSpawned[W] + 1;
			if (k == 0 && Cls == "U2Izarian")
				P.PlaySound(Sound(DynamicLoadObject("U2Izarian.Retreat1", class'Sound', true)), SLOT_Talk, 2.0);
		}
		made += n;
	}
	if (bLog)
		Log("U2Sanctuary open: wave "$W$" ("$Waves[W].Encounter$": "$Waves[W].Pawns$") out, "$WaveSpawned[W]$" spawned");
}

defaultproperties
{
	bEnabled=True
	WaveTimeout=60.000000
	RestAfterFight=30.000000
	LastClear=-1000.000000
	RemoteRole=ROLE_None
}
