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
// From the open-map pacing research (games/research_notes/Open map encounter pacing):
//  CAUSES    reinforcements you can see and answer (OpenSpawner): Izarians crawl out of
//            hive pods at the doors - shoot a pod and its door is shut; Skaarj come down
//            in drop pods - shoot one down before it lands and its Skaarj never arrive
//  SUPPLIES  health / ammo / shield laid out when a place is cleared (the plant, the
//            power station, the pad) - safe rooms on an open map; the optional pocket
//            (the dig pit) pays out the best cache
//  NOBIKE    zones the bike can't go into (the generator shaft, the drainage room while
//            it's full of Izarians): the player is put out on foot at the edge
//  HOLD      the end: the clock only runs while the player is on the pad; waves "t+N"
//            come N seconds into the hold whatever happens; at zero the Marines' dropship
//            comes down and beat After="hold" fires
//  MAXALIVE  never more than this many of the director's enemies at once
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
	var string Kind;
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
	var string Kind;
	var vector At;
};
var config array<OBeat> Beats;
var config array<OWave> Waves;
var config array<OBody> Bodies;
var config array<OProp> Props;
var config array<OThing> Things;
struct OSupply
{
	var vector At;
	var string After;
	var string Items;          // "Package.Class:n,..."
	var string Message;
};
struct ONoBike
{
	var vector At;
	var float Radius;
	var string Encounter;      // "" = always, else only while that encounter is on
};
struct OCam
{
	var string Beat;           // Miller watches this beat through it
	var vector At;
	var int Yaw;
	var string Post;           // no wall near: a mast mesh under it (At - 380 UU)
};
var config array<OCam> Cams;       // the security cameras Miller talks through (the shipped maps' CameraArm1a)
var config string CamMesh;
var config array<OSupply> Supplies;
var config array<ONoBike> NoBike;
var config string HiveMesh, DropMesh, ShipMesh, BurstFX;
var config float HiveScale, DropScale, ShipScale;
var config int HiveHealth, DropHealth, MaxAlive;
var config string HoldBeat;
var config vector HoldAt;
var config float HoldRadius, HoldSeconds;
var config string DialogDirs, Barks;
var config string BarkEncounters;   // barks only in these encounters' fights (Miller sees only the plant), "" = any
var config vector BeaconAt;        // the relay mast's top (the weenie): a red beacon light there (a placed Light crashed LIGHT APPLY)
var config bool bEnabled, bLog;
var config float WaveTimeout, RestAfterFight;
var config float StoryAfterFight, BarkCooldown, FightRadius;   // story waits this long after a fight; barks rotate, at most one per BarkCooldown/4   // the next wave comes after this many seconds anyway; a rest before a new encounter

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
var array<int> SupplyGiven;
var array<OpenSpawner> Hives;      // live hive pods
var array<vector> DeadHives;       // doors whose pod was shot: shut
var array<OpenSpawner> Falling;    // drop pods on the way down
var bool bHolding, bHoldDone, bHoldSeen;
var float HoldT, NextHoldSay, NextBikeSay, LastBarkAt, LastNear;
var string BarksSaid;
var array<Actor> Ears;            // LookTarget0..7: the shipped dialogue plays Miller from these (SoundActor=LookTargetN)

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
	SupplyGiven.Length = Supplies.Length;
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
	if (BeaconAt != vect(0,0,0))
		Beacon();
	PlaceCams();
	PlaceBodies();
	for (i = 0; i < Props.Length; i++)
		SpawnProp(Props[i]);
	for (i = 0; i < Things.Length; i++)
		SpawnThing(Things[i]);
	Log("U2Sanctuary open: "$Beats.Length$" beats, "$Waves.Length$" waves, "$Bodies.Length$" bodies, dialogue "$DialogDirs);
}

// Miller's cameras, and the actors his lines play from: spawned first on a map that has none, so they are
// named LookTarget0..7 as in the shipped maps (the dialogue finds its SoundActor by name)
function PlaceCams()
{
	local class<Actor> LT;
	local StaticMesh M;
	local SanctuaryCover C;
	local rotator R;
	local int i, k;

	LT = class<Actor>(DynamicLoadObject("U2Dialog.LookTarget", class'Class', true));
	if (LT == None)
		LT = class<Actor>(DynamicLoadObject("Engine.LookTarget", class'Class', true));
	for (i = 0; i < 8 && LT != None; i++)
		Ears[i] = Spawn(LT,,, Location);
	if (bLog && Ears.Length > 0)
		Log("U2Sanctuary open: "$Ears.Length$" ears, first "$Ears[0].Name);
	M = StaticMesh(DynamicLoadObject(CamMesh, class'StaticMesh', true));
	for (i = 0; i < Cams.Length && M != None; i++)
	{
		for (k = 0; k < i; k++)
			if (VSize(Cams[k].At - Cams[i].At) < 10)
				break;
		if (k < i)
			continue;        // one camera serves several beats
		R.Yaw = Cams[i].Yaw;
		C = Spawn(class'SanctuaryCover',,, Cams[i].At, R);
		if (C == None)
			continue;
		C.StaticMesh = M;
		C.SetCollision(false, false, false);
		C.bDynamicLight = true;
		if (Cams[i].Post != "")
			SpawnProp(MakeProp(Cams[i].Post, Cams[i].At - vect(0,0,380), Cams[i].Yaw));
	}
}

// a beat with a camera: Miller's voice comes from that camera now
function CamFor(string Id)
{
	local int i, k;

	for (i = 0; i < Cams.Length; i++)
		if (Cams[i].Beat ~= Id)
		{
			for (k = 0; k < Ears.Length; k++)
				if (Ears[k] != None)
					Ears[k].SetLocation(Cams[i].At);
			return;
		}
}

function Beacon()
{
	local SanctuaryLight L;

	L = Spawn(class'SanctuaryLight',,, BeaconAt);
	if (L == None)
		return;
	L.LightHue = 0;
	L.LightSaturation = 30;
	L.LightBrightness = 255;
	L.LightRadius = 40;
	L.LightEffect = LE_None;
	L.LightType = LT_Pulse;
	L.LightPeriod = 48;
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
		PC = class<Pawn>(DynamicLoadObject(Bodies[i].Kind, class'Class', true));
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

function OProp MakeProp(string Mesh, vector At, int Yaw)
{
	local OProp O;

	O.Mesh = Mesh;
	O.At = At;
	O.Yaw = Yaw;
	O.Scale = 1.0;
	return O;
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

	AC = class<Actor>(DynamicLoadObject(O.Kind, class'Class', true));
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
	if (A ~= "hold")
		return bHoldDone && (BeatIndex(HoldBeat) < 0 || EncounterDone(Beats[BeatIndex(HoldBeat)].Encounter));
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
	for (i = 0; i < Falling.Length; i++)
		if (Falling[i] != None && Waves[Falling[i].Wave].Encounter ~= E)
			return false;
	return true;
}

function bool EncounterOn(string E)
{
	local int i;

	for (i = 0; i < Waves.Length; i++)
		if (Waves[i].Encounter ~= E && WaveState[i] != 0)
			return !EncounterDone(E);
	return false;
}

function bool IsTimed(int W)
{
	return Left(Waves[W].When, 2) ~= "t+";
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

function bool BarkFight()
{
	local int i;

	if (BarkEncounters == "")
		return FightOn();
	for (i = 0; i < Alive.Length; i++)
		if (InStr(","$Caps(BarkEncounters)$",", ","$Caps(Waves[AliveWave[i]].Encounter)$",") >= 0)
			return true;
	return false;
}

// a fight the player is in: one of the director's enemies within FightRadius (stragglers left alive across the map
// don't hold the story back forever)
function bool FightNear(PlayerController PC)
{
	local int i;

	for (i = 0; i < Alive.Length; i++)
		if (Alive[i] != None && VSize((Alive[i].Location - PC.Pawn.Location) * vect(1,1,0)) < FightRadius)
		{
			LastNear = Level.TimeSeconds;
			return true;
		}
	return false;
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
	local string T;

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
		CamFor(Beats[i].Id);
		if (HoldBeat != "" && Beats[i].Id ~= HoldBeat)
		{
			bHolding = true;
			HoldT = 0;
		}
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
		if (IsTimed(j))
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
	if (bHolding)
		Hold(PC);
	for (j = 0; j < Waves.Length; j++)
	{
		if (WaveState[j] != 1)
			continue;
		if (Waves[j].When ~= "enter" && !FightNear(PC) && Talking(PC))
		{
			WaveAt[j] = FMax(WaveAt[j], Level.TimeSeconds + Waves[j].Delay);
			continue;
		}
		if (Level.TimeSeconds >= WaveAt[j])
			Release(j, PC.Pawn);
	}
	Supply();
	KeepOffBike(PC);
	// the conversations, one at a time; story waits for a quiet moment (dialogue heuristics rule 15:
	// no story under fire - it plays StoryAfterFight seconds after the last enemy falls), barks ("~") don't wait
	if (TopicQueue.Length > 0 && Level.TimeSeconds >= NextTalk && !class'DialogEngine'.static.IsAlreadyTalking(PC.Pawn)
		&& (Left(TopicQueue[0], 1) == "~" || (!FightNear(PC) && Level.TimeSeconds >= LastNear + StoryAfterFight)))
	{
		SetPropertyText("TopicName", Mid(TopicQueue[0], int(Left(TopicQueue[0], 1) == "~")));
		class'DialogEngine'.static.Initiate(PC.Pawn, None, TopicName);
		if (bLog)
			Log("U2Sanctuary open: talk "$TopicQueue[0]);
		TopicQueue.Remove(0, 1);
		NextTalk = Level.TimeSeconds + 1.5;
	}
	// a bark now and then while a fight is on
	if (BarkFight() && TopicQueue.Length == 0 && Level.TimeSeconds >= NextBark && Barks != "")
	{
		NextBark = Level.TimeSeconds + 14 + FRand() * 10;
		T = PickBark();
		if (FRand() < 0.6 && T != "")
			TopicQueue[TopicQueue.Length] = "~"$T;
	}
}

// talk is on (a conversation playing or queued): a beat's "enter" waves wait for it (talk, then the fight)
function bool Talking(PlayerController PC)
{
	return TopicQueue.Length > 0 || class'DialogEngine'.static.IsAlreadyTalking(PC.Pawn);
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
	// the bag: the barks not said yet; when it's empty, all again (but never the last one twice)
	for (i = B.Length - 1; i >= 0; i--)
		if (InStr(","$BarksSaid$",", ","$B[i]$",") >= 0)
			B.Remove(i, 1);
	if (B.Length == 0)
	{
		BarksSaid = "";
		return "";
	}
	if (Level.TimeSeconds < LastBarkAt + BarkCooldown / 4)
		return "";
	T = B[Rand(B.Length)];
	BarksSaid = BarksSaid$","$T;
	LastBarkAt = Level.TimeSeconds;
	return T;
}

// a wave comes out of its doors: "Class:n,Class:n" round the doors "x,y,z;x,y,z".
// Izarians crawl out of the doors' hive pods (a door whose pod was shot is shut);
// Skaarj come down in drop pods on the doors
function Release(int W, Pawn Target)
{
	local array<vector> D, HD;
	local string S, Item, Cls;
	local int i, n, k, made;
	local vector V;
	local class<Pawn> PCl;
	local OpenSpawner H;

	WaveState[W] = 2;
	WaveAt[W] = Level.TimeSeconds;
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
		if (Left(Cls, 8) ~= "U2Skaarj" && DropMesh != "")
		{
			for (k = 0; k < n; k++)
				if (Alive.Length + Falling.Length < MaxAlive)
					DropPod(W, Cls, D[(made + k) % D.Length] + Normal(VRand() * vect(1,1,0)) * 250);
			made += n;
			continue;
		}
		// the hive pods at the doors
		HD.Length = 0;
		for (i = 0; i < D.Length; i++)
		{
			H = HiveAt(D[i]);
			if (H != None)
				HD[HD.Length] = H.Location;
		}
		if (HD.Length == 0)
		{
			if (bLog)
				Log("U2Sanctuary open: wave "$W$" "$Cls$" - every hive shut");
			continue;
		}
		for (k = 0; k < n; k++)
		{
			if (Alive.Length + Falling.Length >= MaxAlive)
				break;
			V = HD[(made + k) % HD.Length];
			if (SpawnFoe(PCl, V + Normal(VRand() * vect(1,1,0)) * (230 + 60 * k) + vect(0,0,100), W, Target) != None && k == 0 && Cls == "U2Izarian")
				PlaySoundAt(V, "U2Izarian.Retreat1");
		}
		made += n;
	}
	if (bLog)
		Log("U2Sanctuary open: wave "$W$" ("$Waves[W].Encounter$": "$Waves[W].Pawns$") out, "$WaveSpawned[W]$" spawned, "$Falling.Length$" pods falling");
}

function PlaySoundAt(vector V, string Snd)
{
	local Sound S;
	local int i;

	S = Sound(DynamicLoadObject(Snd, class'Sound', true));
	if (S == None)
		return;
	for (i = 0; i < Hives.Length; i++)
		if (Hives[i] != None && VSize(Hives[i].Location - V) < 10)
		{
			Hives[i].PlaySound(S, SLOT_Talk, 2.0);
			return;
		}
	PlaySound(S, SLOT_Talk, 2.0);
}

function Pawn SpawnFoe(class<Pawn> PCl, vector V, int W, Pawn Target)
{
	local Pawn P;
	local rotator R;

	R = rotator(Target.Location - V);
	R.Pitch = 0;
	P = Spawn(PCl,,, V, R);
	if (P == None)
		P = Spawn(PCl,,, V + vect(0,0,120), R);
	if (P == None)
		return None;
	Alive[Alive.Length] = P;
	AliveWave[AliveWave.Length] = W;
	WaveSpawned[W] = WaveSpawned[W] + 1;
	return P;
}

// the live hive pod at a door, made the first time the door is used; None if it was shot
function OpenSpawner HiveAt(vector Door)
{
	local int i;
	local OpenSpawner H;
	local StaticMesh M;
	local rotator R;

	for (i = 0; i < DeadHives.Length; i++)
		if (VSize((DeadHives[i] - Door) * vect(1,1,0)) < 300)
			return None;
	for (i = 0; i < Hives.Length; i++)
		if (Hives[i] != None && VSize((Hives[i].Location - Door) * vect(1,1,0)) < 300)
			return Hives[i];
	if (HiveMesh == "")
		return SpawnHiveless(Door);
	M = StaticMesh(DynamicLoadObject(HiveMesh, class'StaticMesh', true));
	R.Yaw = Rand(65536);
	H = Spawn(class'OpenSpawner',,, Door - vect(0,0,120), R);
	if (H == None)
		return None;
	H.Director = Self;
	H.Kind = 'Hive';
	H.Health = HiveHealth;
	if (M != None)
		H.StaticMesh = M;
	H.SetDrawScale(HiveScale);
	Hives[Hives.Length] = H;
	return H;
}

// no hive mesh set: the door itself (the old behaviour), as a marker that can't be shot
function OpenSpawner SpawnHiveless(vector Door)
{
	local OpenSpawner H;

	H = Spawn(class'OpenSpawner',,, Door);
	if (H != None)
	{
		H.Director = Self;
		H.Kind = 'Ship';
		H.bHidden = true;
		H.SetCollision(false, false, false);
		Hives[Hives.Length] = H;
	}
	return H;
}

function DropPod(int W, string Cls, vector Door)
{
	local OpenSpawner P;
	local StaticMesh M;
	local rotator R;

	M = StaticMesh(DynamicLoadObject(DropMesh, class'StaticMesh', true));
	R.Yaw = Rand(65536);
	P = Spawn(class'OpenSpawner',,, Door + vect(0,0,5000), R);
	if (P == None)
		return;
	P.Director = Self;
	P.Kind = 'Drop';
	P.Health = DropHealth;
	P.Wave = W;
	P.Cargo = Cls;
	if (M != None)
		P.StaticMesh = M;
	P.SetDrawScale(DropScale);
	P.Fall(Door - vect(0,0,120), 5000, 900);
	Falling[Falling.Length] = P;
}

function PodLanded(OpenSpawner S)
{
	local int i;
	local class<Pawn> PCl;
	local PlayerController PC;

	for (i = Falling.Length - 1; i >= 0; i--)
		if (Falling[i] == S)
			Falling.Remove(i, 1);
	PC = ThePlayer();
	if (S.Kind == 'Ship')
	{
		Say("The Marines' dropship is down. Get aboard.");
		return;
	}
	if (S.Kind != 'Drop' || PC == None || PC.Pawn == None)
		return;
	PCl = class<Pawn>(DynamicLoadObject("U2Pawns."$S.Cargo, class'Class', true));
	if (PCl != None)
		SpawnFoe(PCl, S.Location + Normal(PC.Pawn.Location - S.Location) * vect(1,1,0) * 260 + vect(0,0,140), S.Wave, PC.Pawn);
	if (bLog)
		Log("U2Sanctuary open: drop pod landed, "$S.Cargo);
}

function PodBurst(OpenSpawner S)
{
	local int i;

	for (i = Falling.Length - 1; i >= 0; i--)
		if (Falling[i] == S)
		{
			Falling.Remove(i, 1);
			Say("Drop pod shot down.");
		}
	for (i = Hives.Length - 1; i >= 0; i--)
		if (Hives[i] == S)
		{
			Hives.Remove(i, 1);
			DeadHives[DeadHives.Length] = S.Location + vect(0,0,120);
			Say("Hive pod destroyed - nothing more comes out of that one.");
		}
	if (bLog)
		Log("U2Sanctuary open: "$S.Kind$" burst");
}

// the timed hold at the pad: the clock runs only while the player is on it
function Hold(PlayerController PC)
{
	local int j, Left_;
	local float T;
	local bool bOn;
	local OpenSpawner Ship;
	local StaticMesh M;
	local rotator R;

	bOn = VSize((PC.Pawn.Location - HoldAt) * vect(1,1,0)) < HoldRadius;
	if (bOn && !Talking(PC))      // the clock waits while the story talks (writer: talk, then the fight)
	{
		HoldT += 0.5;
		bHoldSeen = true;
	}
	for (j = 0; j < Waves.Length; j++)
		if (WaveState[j] == 0 && IsTimed(j) && HoldT >= float(Mid(Waves[j].When, 2)))
		{
			WaveState[j] = 1;
			WaveAt[j] = Level.TimeSeconds + Waves[j].Delay;
		}
	Left_ = int(HoldSeconds - HoldT + 0.5);
	if (Level.TimeSeconds >= NextHoldSay)
	{
		if (!bOn && bHoldSeen)
		{
			Say("Get back to the pad - the dropship won't land on an empty pad.");
			NextHoldSay = Level.TimeSeconds + 8;
		}
		else if (bOn && Left_ > 0 && (int(Left_ % 30) == 0 || Left_ == 10))
		{
			Say("Dropship ETA "$(Left_ / 60)$":"$Right("0"$int(Left_ % 60), 2)$" - hold the pad.");
			NextHoldSay = Level.TimeSeconds + 1.5;
		}
	}
	if (HoldT < HoldSeconds)
		return;
	bHolding = false;
	bHoldDone = true;
	// whatever of the hold hasn't come out stays away
	for (j = 0; j < Waves.Length; j++)
		if (WaveState[j] == 0 && IsTimed(j))
			WaveState[j] = 2;
	Say("Dropship inbound!");
	M = StaticMesh(DynamicLoadObject(ShipMesh, class'StaticMesh', true));
	if (M == None)
		return;
	R.Yaw = Rand(65536);
	Ship = Spawn(class'OpenSpawner',,, HoldAt + vect(0,0,6000), R);
	if (Ship == None)
		return;
	Ship.Director = Self;
	Ship.Kind = 'Ship';
	Ship.StaticMesh = M;
	Ship.SetDrawScale(ShipScale);
	Ship.bProjTarget = false;
	Ship.Fall(HoldAt + vect(1900,0,250), 5700, 600);
}

// cleared places lay out supplies (safe rooms on an open map)
function Supply()
{
	local int i, k, n, c;
	local string S, Item;
	local class<Actor> AC;
	local SanctuaryLight L;
	local vector V;

	for (i = 0; i < Supplies.Length; i++)
	{
		if (SupplyGiven[i] != 0 || !AfterDone(Supplies[i].After))
			continue;
		SupplyGiven[i] = 1;
		S = Supplies[i].Items;
		while (S != "")
		{
			k = InStr(S, ",");
			if (k < 0)
			{
				Item = S;
				S = "";
			}
			else
			{
				Item = Left(S, k);
				S = Mid(S, k + 1);
			}
			AC = class<Actor>(DynamicLoadObject(Left(Item, InStr(Item, ":")), class'Class', true));
			n = int(Mid(Item, InStr(Item, ":") + 1));
			for (k = 0; k < n && AC != None; k++)
			{
				V.X = Cos(c * 1.1) * (110 + 25 * c);
				V.Y = Sin(c * 1.1) * (110 + 25 * c);
				Spawn(AC,,, Supplies[i].At + V);
				c++;
			}
		}
		L = Spawn(class'SanctuaryLight',,, Supplies[i].At + vect(0,0,220));
		if (L != None)
		{
			L.LightHue = 90;
			L.LightSaturation = 60;
			L.LightBrightness = 200;
			L.LightRadius = 14;
			L.LightEffect = LE_None;
		}
		if (Supplies[i].Message != "")
			Say(Supplies[i].Message);
		if (bLog)
			Log("U2Sanctuary open: supply "$i$" out ("$c$" items)");
	}
}

// bike-free zones: put the player out on foot at the edge
function KeepOffBike(PlayerController PC)
{
	local int i;
	local KVehicle B;

	if (!PC.IsInState('PlayerDriving'))
		return;
	for (i = 0; i < NoBike.Length; i++)
	{
		if (NoBike[i].Encounter != "" && !EncounterOn(NoBike[i].Encounter))
			continue;
		if (VSize((PC.Pawn.Location - NoBike[i].At) * vect(1,1,0)) > NoBike[i].Radius)
			continue;
		B = KVehicle(PC.Pawn.ControlledActor);
		PC.GotoState('PlayerWalking');
		if (B != None)
			B.Velocity = vect(0,0,0);
		if (Level.TimeSeconds >= NextBikeSay)
		{
			Say("Too tight for the bike - on foot from here.");
			NextBikeSay = Level.TimeSeconds + 6;
		}
		return;
	}
}

defaultproperties
{
	bEnabled=True
	WaveTimeout=60.000000
	RestAfterFight=30.000000
	LastClear=-1000.000000
	MaxAlive=12
	StoryAfterFight=3.000000
	FightRadius=4000.000000
	LastNear=-1000.000000
	BarkCooldown=120.000000
	LastBarkAt=-1000.000000
	HiveHealth=300
	DropHealth=450
	HiveScale=1.000000
	DropScale=1.000000
	ShipScale=1.000000
	HoldRadius=2400.000000
	HoldSeconds=150.000000
	BurstFX="U2Weapons.RL_Explosion"
	RemoteRole=ROLE_None
}
