//=============================================================================
// SevenSanctuary - a director for Sanctuary's first map (M08A1) that turns its
// opening into a quiet walk through a dead colony, without touching the map:
//
// - the six scripted creatures (three feeding on colonists, three posed for the
//   intro camera) are hidden: the bodies stay, the monsters don't
// - two of the three victims are already dead; the first one you reach is
//   still alive and dies as you arrive
// - the level's own scare sounds (steam, creaks, "something is there",
//   sniffing, calls) are fired one by one as you walk deeper
// - the first Izarian wave is held (hidden, frozen in place) until you enter
//   its area, then released with a tell: one seen far off, calls, then all
//
// Spawned by SevenStory on M08A1. Settings: [U2Seven.SevenSanctuary] in User.ini.
//=============================================================================
class SevenSanctuary extends Info
	config(User);

var() config bool bEnabled;
var() config bool bDyingSurvivor;    // the first victim dies as you arrive (else already dead)
var() config float WaveReleaseY;     // the held wave is released when you get this far in (map Y)
var() config bool bLog;
var() config bool bOpeningCinematic;  // camera over the dead colony once you have control
var() config vector BoardLocation;    // Aida's console in the patrol zone
var SevenBoard Board;
var bool bMissionDone;
var float DoneAt;
var bool bCineStarted;

// designed encounters, editable in User.ini: one line per spawn
struct Encounter
{
	var string Cls;        // pawn class, e.g. U2Pawns.U2Izarian
	var vector Loc;
	var int Yaw;
	var float TriggerY;    // armed once the player's Y drops below this (the level runs down in Y)
	var float Delay;       // seconds after arming
	var int Wave;          // group number, for "when wave N is nearly dead"
	var int WhenWaveDown;  // 0, or a wave that must have at most 1 left alive first
	var string Variant;    // feral, berserker, agile, glimpse, or empty
};
var() config array<Encounter> Encounters;

struct Live
{
	var Pawn P;
	var float DueAt;
	var bool bSpawned;
};
var array<Live> Lives;

struct Scare
{
	var float Y;                     // fired once the player's Y drops below this
	var name Event;
	var bool bDone;
};
var array<Scare> Scares;

var array<Pawn> Hidden;              // the scene creatures
var array<Pawn> Wave;                // the held first wave
var Pawn Survivor;
var bool bSetUp, bReleased, bTell, bSurvivorDone;
var float TellTime, StartTime;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SaveConfig();
	if (!bEnabled)
	{
		Destroy();
		return;
	}
	// the map's scare sounds, in walking order (the level runs from high Y down)
	AddScare(5200, 'Somethingisthere1');
	AddScare(4500, 'CreakNumbertwo');
	AddScare(3700, 'SniffSniff');
	AddScare(3000, 'IzarianMatingCall2');
	AddScare(2300, 'Somethingisthere2');
	AddScare(1900, 'QQQSteamScare1');
	AddScare(1000, 'Izarianhaha1');
	AddScare(300,  'AmbIzarian1');
	StartTime = Level.TimeSeconds;
	Lives.Length = Encounters.Length;
	SetTimer(0.25, true);
}

// ------------------------------------------------------------ the opening

function AddShot(SevenCinematic C, vector From, vector To, int PitchFrom, int YawFrom, int PitchTo, int YawTo, float T, string Title)
{
	local int i;
	i = C.Shots.Length;
	C.Shots.Length = i + 1;
	C.Shots[i].From = From;
	C.Shots[i].To = To;
	C.Shots[i].RotFrom.Pitch = PitchFrom;
	C.Shots[i].RotFrom.Yaw = YawFrom;
	C.Shots[i].RotTo.Pitch = PitchTo;
	C.Shots[i].RotTo.Yaw = YawTo;
	C.Shots[i].Time = T;
	C.Shots[i].Title = Title;
}

function StartOpening(PlayerController PC)
{
	local SevenCinematic C;

	bCineStarted = true;
	C = Spawn(class'SevenCinematic');
	if (C == None)
		return;
	// the level runs down in Y; yaw 49152 looks that way
	AddShot(C, vect(-730,6900,7100), vect(-730,6450,6950), -6500, 49152, -5000, 49152, 9.0, "TitleSanctuary");
	AddShot(C, vect(-1300,5300,6560), vect(-1150,4700,6545), -700, 49152, -900, 47500, 8.0, "TitleElara");
	AddShot(C, vect(-1150,5200,6950), vect(-1120,4500,6900), -3200, 49152, -3800, 50000, 7.0, "");
	C.Start(PC);
	if (bLog)
		Log("SevenSanctuary: opening cinematic started");
}

// ------------------------------------------------------------ missions

// designed-spawn kills count toward the active mission; when its condition
// is met, mark it won and go home (M08A1) unless we're already there
function CheckMission(Pawn Player)
{
	local int m, i, Dead, Want;
	local string W, Kind, Arg;
	local vector Goal;

	if (bMissionDone || class'SevenMissions'.default.Active == "")
		return;
	m = class'SevenMissions'.static.Find(class'SevenMissions'.default.Active);
	if (m < 0 || !(class'SevenMissions'.default.Missions[m].Map ~= MapName()))
		return;
	W = class'SevenMissions'.default.Missions[m].Win;
	i = InStr(W, ":");
	Kind = Left(W, i);
	Arg = Mid(W, i + 1);
	if (Kind ~= "kills")
	{
		Want = int(Arg);
		for (i = 0; i < Lives.Length; i++)
			if (Lives[i].bSpawned && (Lives[i].P == None || Lives[i].P.bDeleteMe || Lives[i].P.Health <= 0))
				Dead++;
		if (Dead != class'SevenMissions'.default.Kills)
		{
			class'SevenMissions'.default.Kills = Dead;
			class'SevenMissions'.static.StaticSaveConfig();
		}
		if (Dead < Want)
			return;
	}
	else if (Kind ~= "reach")
	{
		Goal.X = float(Left(Arg, InStr(Arg, ","))); Arg = Mid(Arg, InStr(Arg, ",") + 1);
		Goal.Y = float(Left(Arg, InStr(Arg, ","))); Arg = Mid(Arg, InStr(Arg, ",") + 1);
		Goal.Z = float(Left(Arg, InStr(Arg, ","))); Arg = Mid(Arg, InStr(Arg, ",") + 1);
		if (VSize(Player.Location - Goal) > float(Arg))
			return;
	}
	else if (Kind ~= "survive")
	{
		if (class'SevenMissions'.default.StartedAt == 0)
		{
			class'SevenMissions'.default.StartedAt = Level.TimeSeconds;
			return;
		}
		if (Level.TimeSeconds - class'SevenMissions'.default.StartedAt < float(Arg))
			return;
	}
	bMissionDone = true;
	DoneAt = Level.TimeSeconds;
	class'SevenMissions'.default.Kills = -1;                // won
	class'SevenMissions'.static.StaticSaveConfig();
	Log("SevenSanctuary: mission "$class'SevenMissions'.default.Active$" won");
	if (MapName() ~= "M08A1")
	{
		if (Board != None)
			Board.bDebriefed = false;                       // debrief right here
	}
	else
		SetTimer(3.0, false);                               // a beat, then home
}

function string MapName()
{
	return class'SevenStory'.static.MapOf(Level.GetLocalURL());
}

// ------------------------------------------------------------ encounters

function int WaveAlive(int W)
{
	local int i, N;
	for (i = 0; i < Lives.Length; i++)
		if (Encounters[i].Wave == W && Lives[i].bSpawned && Lives[i].P != None && !Lives[i].P.bDeleteMe && Lives[i].P.Health > 0)
			N++;
	return N;
}

function bool WaveAllSpawned(int W)
{
	local int i;
	for (i = 0; i < Lives.Length; i++)
		if (Encounters[i].Wave == W && !Lives[i].bSpawned)
			return false;
	return true;
}

function RunEncounters(Pawn Player)
{
	local int i;

	for (i = 0; i < Lives.Length; i++)
	{
		if (Lives[i].bSpawned)
			continue;
		if (Lives[i].DueAt == 0)
		{
			if (Player.Location.Y > Encounters[i].TriggerY)
				continue;
			if (Encounters[i].WhenWaveDown > 0
				&& !(WaveAllSpawned(Encounters[i].WhenWaveDown) && WaveAlive(Encounters[i].WhenWaveDown) <= 1))
				continue;
			Lives[i].DueAt = Level.TimeSeconds + FMax(Encounters[i].Delay, 0.01);
		}
		if (Level.TimeSeconds >= Lives[i].DueAt)
		{
			Lives[i].bSpawned = true;
			Lives[i].P = SpawnEncounter(i);
		}
	}
}

function Pawn SpawnEncounter(int i)
{
	local class<Pawn> C;
	local Pawn P;
	local rotator R, R2;
	local int k;
	local EnemyMutator EM;

	C = class<Pawn>(DynamicLoadObject(Encounters[i].Cls, class'Class'));
	if (C == None)
	{
		Log("SevenSanctuary: no class "$Encounters[i].Cls);
		return None;
	}
	foreach DynamicActors(class'EnemyMutator', EM)
		break;
	R.Yaw = Encounters[i].Yaw;
	if (EM != None)
		EM.bDesignedSpawn = true;
	P = Spawn(C,,, Encounters[i].Loc, R);
	// the exact spot may be taken (a body, a bigger cylinder): try around it
	for (k = 0; k < 16 && P == None; k++)
	{
		R2.Yaw = (k % 8) * 8192;
		P = Spawn(C,,, Encounters[i].Loc + vector(R2) * (90 + 90 * (k / 8)) + vect(0,0,10), R);
	}
	if (EM != None)
		EM.bDesignedSpawn = false;
	if (P == None)
	{
		Log("SevenSanctuary: spawn "$i$" ("$Encounters[i].Cls$") blocked at "$Encounters[i].Loc);
		return None;
	}
	if (EM != None && U2PawnBasic(P) != None)
	{
		if (Encounters[i].Variant ~= "feral")          EM.MakeFeral(U2PawnBasic(P));
		else if (Encounters[i].Variant ~= "berserker") EM.MakeBerserker(U2PawnBasic(P));
		else if (Encounters[i].Variant ~= "agile")     EM.MakeAgile(U2PawnBasic(P));
	}
	if (Encounters[i].Variant ~= "glimpse")
	{
		// seen, not fought: deaf and blind, gone in a few seconds
		P.SightRadius = 0;
		P.HearingThreshold = 0;
		P.LifeSpan = 4;
	}
	if (bLog)
		Log("SevenSanctuary: spawned "$i$" "$P.Name$" ("$Encounters[i].Variant$") wave "$Encounters[i].Wave$" at "$Encounters[i].Loc);
	return P;
}


function AddScare(float Y, name E)
{
	local int i;
	i = Scares.Length;
	Scares.Length = i + 1;
	Scares[i].Y = Y;
	Scares[i].Event = E;
}

function Pawn Player()
{
	local Controller C;
	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None && C.Pawn != None)
			return C.Pawn;
	return None;
}

event Timer()
{
	local Pawn P;
	local int i;

	if (bMissionDone && DoneAt > 0 && Level.TimeSeconds - DoneAt >= 3.0 && !(MapName() ~= "M08A1"))
	{
		DoneAt = 0;
		Level.ServerTravel("M08A1", false);
		return;
	}
	if (!bSetUp)
	{
		// after the level's own scripts have placed and hidden what they hide
		if (Level.TimeSeconds - StartTime >= 3.0)
			SetUp();
		return;
	}
	P = Player();
	if (P == None)
		return;
	if (Board == None && BoardLocation != vect(0,0,0))
		Board = Spawn(class'SevenBoard',,, BoardLocation);
	CheckMission(P);
	if (bOpeningCinematic && !bCineStarted && PlayerController(P.Controller) != None
		&& PlayerController(P.Controller).IsInState('PlayerWalking'))
		StartOpening(PlayerController(P.Controller));
	RunEncounters(P);

	for (i = 0; i < Scares.Length; i++)
		if (!Scares[i].bDone && P.Location.Y < Scares[i].Y)
		{
			Scares[i].bDone = true;
			TriggerEvent(Scares[i].Event, Self, P);
			if (bLog)
				Log("SevenSanctuary: scare "$Scares[i].Event$" at Y="$int(P.Location.Y));
		}

	if (Survivor != None && !bSurvivorDone && VSize(Survivor.Location - P.Location) < 450)
	{
		bSurvivorDone = true;
		KillQuietly(Survivor);
		TriggerEvent('DisHumanDeath1', Self, P);
		if (bLog)
			Log("SevenSanctuary: the survivor dies as the player arrives");
	}

	if (!bReleased)
	{
		if (!bTell && P.Location.Y < WaveReleaseY + 400)
		{
			// the tell: one seen far off, and the calls
			bTell = true;
			TellTime = Level.TimeSeconds;
			if (Wave.Length > 0)
				Show(Wave[Wave.Length - 1]);
			TriggerEvent('Izarianhaha2', Self, P);
			TriggerEvent('IzarianMatingCall1', Self, P);
			if (bLog)
				Log("SevenSanctuary: tell at Y="$int(P.Location.Y));
		}
		if (bTell && (P.Location.Y < WaveReleaseY || Level.TimeSeconds - TellTime > 6))
		{
			bReleased = true;
			for (i = 0; i < Wave.Length; i++)
				Show(Wave[i]);
			if (bLog)
				Log("SevenSanctuary: wave released ("$Wave.Length$") at Y="$int(P.Location.Y));
		}
	}
}

// once the level's actors exist: sort the Izarians and the victims
function SetUp()
{
	local Pawn P, Start;
	local float D, Best;
	local int i;
	local array<Pawn> Victims;

	bSetUp = true;
	Start = Player();
	foreach DynamicActors(class'Pawn', P)
	{
		if (P.IsRealPlayer() || P.Health <= 0)
			continue;
		if (P.IsA('U2Izarian'))
		{
			if (P.Health >= 999 || P.Event == 'Camerasafe')
			{
				Hide(P);                                // scene creature: gone
				Hidden[Hidden.Length] = P;
			}
			else if (P.Location.Y < -900 && P.Location.Y > -5000 && !P.bHidden)
			{
				Hide(P);                                // first wave (the part that starts visible): held
				Wave[Wave.Length] = P;
			}
		}
	}
	// the victims: live civilians next to a hidden creature
	foreach DynamicActors(class'Pawn', P)
	{
		if (P.IsRealPlayer() || P.Health <= 0 || !IsCivilian(P))
			continue;
		for (i = 0; i < Hidden.Length; i++)
			if (Hidden[i] != None && VSize(Hidden[i].Location - P.Location) < 400)
			{
				Victims[Victims.Length] = P;
				break;
			}
	}
	// the one nearest the landing site stays alive for the player to find
	Best = 1e9;
	for (i = 0; i < Victims.Length; i++)
	{
		D = 0;
		if (Start != None)
			D = VSize(Victims[i].Location - Start.Location);
		if (bDyingSurvivor && D < Best)
		{
			Best = D;
			Survivor = Victims[i];
		}
	}
	for (i = 0; i < Victims.Length; i++)
		if (Victims[i] != Survivor)
			KillQuietly(Victims[i]);
	if (bLog)
		Log("SevenSanctuary: hid "$Hidden.Length$" scene creatures, holding "$Wave.Length$" wave Izarians, "$Victims.Length$" victims, survivor "$Survivor);
}

function bool IsCivilian(Pawn P)
{
	local string C;
	C = string(P.Class);
	return InStr(C, "Civilian") >= 0 || InStr(C, "Colonist") >= 0;
}

function Hide(Pawn P)
{
	P.bHidden = true;
	P.SetCollision(false, false, false);
	P.SetPhysics(PHYS_None);
}

function Show(Pawn P)
{
	if (P == None || P.bDeleteMe || !P.bHidden)
		return;
	P.bHidden = false;
	P.SetCollision(true, true, true);
	P.SetPhysics(PHYS_Walking);
}

// a death without gibs: small hits, then a direct death for scripted pawns
// that ignore damage
function KillQuietly(Pawn P)
{
	local int k;
	for (k = 0; k < 4 && P != None && P.Health > 0 && !P.bDeleteMe; k++)
		P.TakeDamage(P.Health + 10, None, P.Location, vect(0,0,0), class'DamageType');
	if (P != None && P.Health > 0 && !P.bDeleteMe)
	{
		P.Health = 0;
		P.Died(None, class'DamageType', P.Location, vect(0,0,0));
	}
}

defaultproperties
{
	bEnabled=True
	bDyingSurvivor=True
	WaveReleaseY=-700.000000
	bLog=True
	bOpeningCinematic=True
	BoardLocation=(X=-900,Y=5700,Z=6480)
	// the glimpse: a feral sprints across the trail far ahead, gone before you can shoot
	Encounters(0)=(Cls="U2Pawns.U2Izarian",Loc=(X=-1100,Y=2900,Z=6160),Yaw=49152,TriggerY=4600,Delay=0.5,Wave=0,Variant="glimpse")
	// the interiors: two ferals once the tableaux are reached
	Encounters(1)=(Cls="U2Pawns.U2Izarian",Loc=(X=1897,Y=1575,Z=5791),Yaw=32768,TriggerY=1400,Delay=2.0,Wave=1,Variant="feral")
	Encounters(2)=(Cls="U2Pawns.U2Izarian",Loc=(X=539,Y=1642,Z=5607),Yaw=32768,TriggerY=1400,Delay=3.5,Wave=1,Variant="feral")
	// the yard: the level's own wave, then the elite
	Encounters(3)=(Cls="U2Pawns.U2SkaarjLight",Loc=(X=-1153,Y=-3180,Z=5835),Yaw=16384,TriggerY=-1400,Delay=1.0,Wave=2,Variant="berserker")
	// the far structures: two agile Skaarj high up, a feral low
	Encounters(4)=(Cls="U2Pawns.U2SkaarjLight",Loc=(X=-432,Y=-7495,Z=7480),Yaw=16384,TriggerY=-6500,Delay=0.5,Wave=3,Variant="agile")
	Encounters(5)=(Cls="U2Pawns.U2SkaarjLight",Loc=(X=-596,Y=-7919,Z=7480),Yaw=16384,TriggerY=-6500,Delay=2.0,Wave=3,Variant="agile")
	Encounters(6)=(Cls="U2Pawns.U2Izarian",Loc=(X=-941,Y=-4285,Z=7468),Yaw=16384,TriggerY=-6500,Delay=3.0,Wave=3,Variant="feral")
	RemoteRole=ROLE_None
}
