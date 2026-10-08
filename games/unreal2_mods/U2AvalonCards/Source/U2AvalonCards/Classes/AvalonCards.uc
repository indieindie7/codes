//=============================================================================
// U2AvalonCards - dresses the outside of the Avalon command tower (TutA) at
// map load: a landing pad with the game's own dropship on it (real meshes),
// tree clusters and an offshore oil rig (imposter cards, CardSprite).
// Nothing in the map file changes; remove the mutator and it's all gone.
// Every placement is a config value (System\U2AvalonCards.ini), so spots can
// be tuned with "set AvalonCards <var> ..." and "set AvalonCards bRebuild True".
// bSurvey logs a height grid round the tower (land / water / nothing) and the
// sun light, to choose spots: lines start "Cards: grid".
//=============================================================================
class AvalonCards extends Mutator
	config(U2AvalonCards);

var config string Maps;            // which maps get dressed (comma list, lower case)
var config bool bSurvey;
var config float SurveyRadius, SurveyStep;
var config vector SurveyCentre;

var config vector PadSpot;         // Z is found by tracing down (Z here = how high above the ground to start)
var config int PadYaw;
var config float PadScale;
var config string PadMesh;
var config string ShipMesh;
var config float ShipScale, ShipLift;
var config vector ShipOffset;     // from the pad's origin, in the pad's frame (the pad mesh isn't centred)
var config int ShipYaw;

var config vector RigSpot;         // out at sea; Z = extra lift (0 = legs on the water)
var config int RigYaw;
var config float RigSize;          // the card's height in world units

var config vector TreeSpot[8];     // X=0,Y=0 = unused
var config float TreeSize[8];
var config int TreeLook[8];        // which tree picture (0-2)

// kit-bashed scenery from other levels' static meshes, one per line:
//   "Package.Group.Name X Y Yaw Scale Lift CX CY MinZ [Skin] [HalfSize]"  (Skin "-" = the package palette)
// X,Y = where the mesh's centre goes (Yaw in degrees); it's stood on whatever is
// straight below (land, or TutA's sea surface) by its lowest point, then lifted
// by Lift. CX CY MinZ = the mesh's bounds centre and bottom, in its own units
// (tools\mesh_bounds.py; tools\make_props.py writes these lines).
var config string Props[256];      // 256 since 2026-10-08 (shanty ring + factory districts with roads and pipes)

// rough blocking: plain boxes, one per line: "X Y Yaw SizeX SizeY SizeZ Lift Colour" (world units, Yaw in
// degrees, Colour 0 grey / 1 rust / 2 pale / 3 dark). Each box stands on whatever is under its centre,
// sunk or raised by Lift. A cube blockout is the guide an image model paints the place over.
var config string Blocks[128];

// baked building cards (CardTextures.uc; toolsake_cards.py over toolsuild_buildings.py's models),
// one per line: "Name X Y Yaw Size [Frames] [Lift]". Name = the texture base name (CoolingTower ->
// U2AvalonCards.CoolingTower0..7), X Y = where it stands (on whatever is under it, + Lift), Yaw in
// degrees = where its front faces, Size = the card's height in world units (the building fills 92% of
// the card's larger side), Frames = how many views were baked (8).
var config string Cards[64];
// more cards in the same format, written by U2Avalon/tools/motion.py (export_mutator.py owns Cards[]): the
// landmark crane tower and the round-2 concept buildings (A-frame huts, dorm pods, Tin Row shacks)
var config string Extras[48];

// haze between the view's depth layers (the cinematography report: atmospheric perspective): the zones
// that already use distance fog (the outdoor ones) get HazeStart..HazeEnd in HazeColour; HazeEnd 0 = the
// map's own fog. Every zone's own fog is logged ("Cards: zone").
var config float HazeStart, HazeEnd;
var config color HazeColour;
var config bool bHazeAllZones;

// motion in the window: a static mesh flying a circle (AvalonFlyer); FlyerMesh "" = none.
// FlyerCentre Z = the flight height; FlyerSpeed in units per second (negative = the other way round).
var config string FlyerMesh;
var config vector FlyerCentre;
var config float FlyerRadius, FlyerSpeed, FlyerScale;

// plumes over the plant (AvalonPlume), one per line: "X Y Z Kind Width Rise" - Kind 0 smoke, 1 steam,
// 2 flare (flame + light + smoke); Z = the source's height over whatever is under it (a mesh's roof, the
// ground under a card, the sea); Width = the column at the source,
// Rise = how far a puff climbs (world units). Wind = the drift (units/s) for all of them.
var config string Plumes[16];
var config vector Wind;
var config string SmokeTexture, FireTexture, SteamTexture;
var config int SmokeStyle;         // ERenderStyle for dark smoke (6 = STY_Alpha, 5 = Modulated, 3 = Translucent)

// trucks on the roads (AvalonTruck), one per line: "Package.Group.Mesh Scale Speed Path Start Lift" -
// Path = index into Paths[], Start = where along it (0..1). Paths[] = "X Y X Y ..." polylines (the spine).
var config string Trucks[8];
var config string Paths[4];

// the staged reveal: the first time the player comes down below RevealBelowZ (out of the command deck),
// a dropship (FlyerMesh) makes one low pass RevealFrom -> RevealTo with RevealSound. RevealBelowZ 0 = off.
var config float RevealBelowZ, RevealSpeed, RevealScale;
var config vector RevealFrom, RevealTo;
var config string RevealSound;
var bool bRevealed;

// the storm (AvalonStorm), on the maps in StormMaps only (comma list, lower case; "" = none): fog pulled in
// to StormFogStart..StormFogEnd in StormFogColour, StormDrops rain streaks within StormRadius of the player
// falling at StormFall (units/s, slanted by Wind), the StormRain / StormWind loops, lightning with one of
// StormThunder[] a distance-delay later.
var config string StormMaps;
var config int StormDrops;
var config float StormRadius, StormFall, StormFogStart, StormFogEnd, StormSkyFogEnd;   // StormSkyFogEnd: the sky box's fog (0 = leave the sky)
var config color StormFogColour;
var config string StormRain, StormWind, StormThunder[5];
var config float StormClear, StormRamp, StormHold;   // the cycle in seconds; StormClear 0 = always storm
var config float StormGloom;       // 0..1: how much darker the whole view gets (the sky box takes no fog)
var config vector StormGloomFog;   // the grey added (0..1000 per channel)
var config int StormClouds;        // how many giant puffs in the cloud deck (0 = none)
var config int CloudBanks;         // fair-weather cumulus banks (AvalonClouds; 0 = none)
var config float CloudHeight, CloudSpread;
var config float StormCloudSize;

// the Liandri public address (AvalonPA): loudspeakers at PASpots[] ("X Y Lift": over whatever is under),
// one announcement every PAMinGap..PAMaxGap seconds, PARadius / PAVolume; no spots = off.
var config string PASpots[6];
var config float PAMinGap, PAMaxGap, PARadius, PAVolume;

// the backwater posting (binder: Hawkins's punishment post, Oduya's board, the Thursday power cut):
// RadioSpot = the command room's radio (AvalonRadio, absolute position; X=0,Y=0 = off) with a static bed;
// a brownout in the tower every BrownoutMinGap..BrownoutMaxGap s (AvalonBrownout; 0 = off);
// DecayLamp = the Authority pad's failing light (AvalonFlicker; "X Y Lift", "" = off)
var config vector RadioSpot;
var config float RadioMinGap, RadioMaxGap, RadioVolume;
var config string RadioStatic;
var config vector TowerSpot;
var config float BrownoutMinGap, BrownoutMaxGap, BrownoutDepth;
var config string BrownoutDown, BrownoutUp;
var config string DecayLamp, DecayBuzz;

// live editing (AvalonLive): every LivePoll seconds "exec LiveFile" through the player's console; 0 = off
var config float LivePoll;
// carving (U2Avalon/tools/carve.py): the editor saves a carved copy of the map and sets PendingMap
// ("avalon pending NAME"); the user types "avalon reload" when it suits them, and lands where they stood
var config string PendingMap;
var config vector ReturnLoc;
var config rotator ReturnRot;
var config bool bReturn;
// the live edit journal (AvalonEditor): "place NAME X Y Z YAW SCALE", "hide NAME", "mesh PATH X Y Z YAW SCALE"
var config string Ops[128];
var AvalonEditor Editor;
var config string LiveFile;
var config int LiveSeq;   // the last batch applied (kept: a reload must not run an old batch again)
var bool bLiveRun;        // the batch being read is new
var bool bInFile;         // the live file is being run right now (else: typed or sent by the pilot)
var float LiveWait;
var AvalonStorm LiveStorm;

var bool bRebuild;
var bool bAvalon;          // this map is one of the Avalon maps (Maps): the town and its life are built
var AvalonSet Set;         // this map family's own dressing ([<family> AvalonSet] in the ini)
var AvalonChat Chat;       // the chat hook: the player's chat lines become marks
var array<Actor> Made;
var Texture TreeTex[3];
var Texture RigTex[8];

event PostBeginPlay()
{
	Super.PostBeginPlay();
	// live editing (marks, cards, procedural layouts, undo, carve + reload) works on every map; the town,
	// weather, motion and loudspeakers only on the Avalon maps (Maps)
	bAvalon = InList(Maps, MapName());
	Log("Cards: live on "$MapName()$", avalon "$bAvalon);
	if (bAvalon)
		OpenSet();
	if (bAvalon && bSurvey)
		Survey();
	Build();
	SetTimer(0.5, true);
}

// is the map in a comma list? An entry ending in * matches every map starting with it
function bool InList(string List, string M)
{
	local string E;

	M = Locs(M);
	List = Locs(List);
	while (List != "")
	{
		if (InStr(List, ",") >= 0)
		{
			E = Left(List, InStr(List, ","));
			List = Mid(List, InStr(List, ",") + 1);
		}
		else
		{
			E = List;
			List = "";
		}
		if (E == M || (Right(E, 1) == "*" && Left(M, Len(E) - 1) == Left(E, Len(E) - 1)))
			return true;
	}
	return false;
}

// the map family: the map's name, lower case, without a carved copy's "_liveN" (TutA_Ridge5_Live2 ->
// tuta_ridge5, TutA_Live3 -> tuta)
function string Family()
{
	local string M;

	M = Locs(MapName());
	if (InStr(M, "_live") >= 0)
		M = Left(M, InStr(M, "_live"));
	return M;
}

// this family's dressing: read it if the family has a section, else start the section from the global values
function OpenSet()
{
	Set = new(None, Family()) class'AvalonSet';     // the object's name (a string in U2) = the ini section's
	if (Set == None)
		return;
	if (Set.bUsed)
		FromSet();
	else
	{
		ToSet();
		Set.bUsed = true;
		Set.SaveConfig();
	}
	Log("Cards: dressing from ["$Family()$" AvalonSet], "$Set.Name);
}

function FromSet()
{
	local int i;

	for (i = 0; i < ArrayCount(Props); i++) Props[i] = Set.Props[i];
	for (i = 0; i < ArrayCount(Blocks); i++) Blocks[i] = Set.Blocks[i];
	for (i = 0; i < ArrayCount(Cards); i++) Cards[i] = Set.Cards[i];
	for (i = 0; i < ArrayCount(Extras); i++) Extras[i] = Set.Extras[i];
	for (i = 0; i < ArrayCount(Plumes); i++) Plumes[i] = Set.Plumes[i];
	for (i = 0; i < ArrayCount(Trucks); i++) Trucks[i] = Set.Trucks[i];
	for (i = 0; i < ArrayCount(Paths); i++) Paths[i] = Set.Paths[i];
	for (i = 0; i < ArrayCount(PASpots); i++) PASpots[i] = Set.PASpots[i];
	RadioSpot = Set.RadioSpot;
	TowerSpot = Set.TowerSpot;
	DecayLamp = Set.DecayLamp;
}

function ToSet()
{
	local int i;

	for (i = 0; i < ArrayCount(Props); i++) Set.Props[i] = Props[i];
	for (i = 0; i < ArrayCount(Blocks); i++) Set.Blocks[i] = Blocks[i];
	for (i = 0; i < ArrayCount(Cards); i++) Set.Cards[i] = Cards[i];
	for (i = 0; i < ArrayCount(Extras); i++) Set.Extras[i] = Extras[i];
	for (i = 0; i < ArrayCount(Plumes); i++) Set.Plumes[i] = Plumes[i];
	for (i = 0; i < ArrayCount(Trucks); i++) Set.Trucks[i] = Trucks[i];
	for (i = 0; i < ArrayCount(Paths); i++) Set.Paths[i] = Paths[i];
	for (i = 0; i < ArrayCount(PASpots); i++) Set.PASpots[i] = PASpots[i];
	Set.RadioSpot = RadioSpot;
	Set.TowerSpot = TowerSpot;
	Set.DecayLamp = DecayLamp;
}

// the global config, and this family's set with it
function SaveAll()
{
	if (Set != None)
	{
		ToSet();
		Set.SaveConfig();
	}
	SaveConfig();
}

function string MapName()
{
	local string S;

	S = string(Level);
	return Left(S, InStr(S, "."));
}

event Timer()
{
	LiveTick();
	if (bRebuild)
	{
		bRebuild = false;
		Build();
	}
	if (bAvalon && !bRevealed && RevealBelowZ != 0)
		CheckReveal();
}

function CheckReveal()
{
	local Controller C;
	local StaticMesh M;
	local AvalonFlyer F;
	local Sound S;

	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None && C.Pawn != None && C.Pawn.Location.Z < RevealBelowZ && C.Pawn.Location.Z > RevealBelowZ - 1500)
		{
			bRevealed = true;
			M = StaticMesh(DynamicLoadObject(FlyerMesh, class'StaticMesh', true));
			if (RevealSound != "")
				S = Sound(DynamicLoadObject(RevealSound, class'Sound', true));
			F = Spawn(class'AvalonFlyer',,, RevealFrom);
			if (F != None && M != None)
				F.Pass(M, RevealFrom, RevealTo, RevealSpeed, RevealScale, S);
			Log("Cards: reveal pass at "$C.Pawn.Location$" "$F);
			return;
		}
}

function Speakers()
{
	local AvalonPA PA;
	local vector P, HitL, HitN;
	local int i;

	for (i = 0; i < ArrayCount(PASpots); i++)
	{
		if (PASpots[i] == "")
			continue;
		if (PA == None)
			PA = Spawn(class'AvalonPA');
		if (PA == None)
			return;
		P.X = float(Word(PASpots[i], 0));
		P.Y = float(Word(PASpots[i], 1));
		P.Z = 0;
		if (Ground(P, HitL, HitN))
			P.Z = HitL.Z;
		P.Z += float(Word(PASpots[i], 2));
		PA.AddSpeaker(P);
	}
	if (PA == None)
		return;
	PA.Begin(PAMinGap, PAMaxGap, PARadius, PAVolume);
	Made[Made.Length] = PA;
	Log("Cards: public address, "$PA.Speakers.Length$" loudspeakers");
}

// ---------------------------------------------------------------- live editing

// give every player the "avalon" command, and read the live file now and then
function LiveTick()
{
	local PlayerController PC;
	local AvalonLive L;
	local int i;
	local bool bHas;
	local vector V;

	if (LivePoll <= 0)
		return;
	PC = Level.PlayerControllerList;
	if (PC == None)
		return;
	// back where the player stood before a reload
	if (bReturn && PC.Pawn != None)
	{
		bReturn = false;
		V = ReturnLoc;
		PC.Pawn.SetLocation(V);
		PC.SetRotation(ReturnRot);
		PC.ClientMessage("[Claude] the carved map, back where you were");
		Log("Cards: live returned the player to "$V);
		SaveAll();
	}
	bHas = false;
	for (i = 0; i < PC.ExecManagers.Length; i++)
		if (AvalonLive(PC.ExecManagers[i]) != None)
			bHas = true;
	if (!bHas)
	{
		L = new(PC) class'AvalonLive';
		L.Cards = Self;
		L.PC = PC;
		PC.ExecManagers[PC.ExecManagers.Length] = L;
		Log("Cards: live editing on, reading "$LiveFile$" every "$LivePoll$" s");
		// the chat: every line the player says becomes a mark (AvalonChat)
		if (Level.Game != None && AvalonChat(Level.Game.BroadcastHandler) == None)
		{
			Chat = Spawn(class'AvalonChat');
			if (Chat != None)
			{
				Chat.Cards = Self;
				Level.Game.BroadcastHandler = Chat;
				Log("Cards: chat lines are marks now");
			}
		}
	}
	LiveWait -= 0.5;
	if (LiveWait > 0)
		return;
	LiveWait = LivePoll;
	bLiveRun = false;
	bInFile = true;
	PC.ConsoleCommand("exec "$LiveFile);      // runs the file's lines right here, synchronously
	bInFile = false;
	if (bLiveRun)
		SaveAll();                          // the session's edits (journal, cards) survive any reload
}

// the rest of S after its first word
function string Rest(string S)
{
	if (InStr(S, " ") < 0)
		return "";
	return Mid(S, InStr(S, " ") + 1);
}

function Live(string S, PlayerController PC)
{
	local string Cmd, Arg, Opts;
	local int i, N;
	local vector V;

	Cmd = Caps(Word(S, 0));
	Arg = Rest(S);
	if (Cmd == "BATCH")
	{
		N = int(Arg);
		bLiveRun = N > LiveSeq;
		if (bLiveRun)
		{
			LiveSeq = N;
			Log("Cards: live batch "$N);
		}
		return;
	}
	// a line from the live file runs only in a new batch; typed (or sent by the pilot) it always runs
	if (bInFile && !bLiveRun)
		return;
	i = int(Word(Arg, 0));
	if (Editor != None && Editor.Command(Cmd, Arg, PC))
	{
		Log("Cards: live "$LiveSeq$" "$S);
		if (!bInFile)
			SaveAll();
		return;
	}
	switch (Cmd)
	{
	case "PENDING":
		PendingMap = Arg;
		SaveAll();
		if (PC != None)
			PC.ClientMessage("[Claude] the carved map is ready: type  avalon reload  when it suits you");
		break;
	case "RELOAD":
		if (PendingMap == "" || PC == None || PC.Pawn == None)
		{
			if (PC != None)
				PC.ClientMessage("[Claude] no carved map waiting");
			break;
		}
		ReturnLoc = PC.Pawn.Location;
		ReturnRot = PC.Rotation;
		bReturn = true;
		Arg = PendingMap;
		PendingMap = "";
		SaveAll();                 // keeps the session's journal and cards too
		// the same options as now (the mutators: the user's, or a test run's)
		Opts = Level.GetLocalURL();
		if (InStr(Opts, "?") >= 0)
			Opts = Mid(Opts, InStr(Opts, "?"));
		else
			Opts = "";
		Log("Cards: live reload into "$Arg$Opts);
		// ClientTravel, not ConsoleCommand("open ..."): an "open" run from the polled AvalonLive.txt (an
		// EXEC inside an EXEC) is dropped silently, so the automatic reload after a carve never happened
		PC.ClientTravel(Arg$Opts, TRAVEL_Absolute, false);
		break;
	case "RAW":
		// any console command, once (a raw line in the file would run on every poll)
		if (PC != None && Caps(Left(Arg, 4)) != "EXEC")
			PC.ConsoleCommand(Arg);
		break;
	case "SAY":
		// as a chat line (the HUD's message area), not only the console (the user talks through the chat)
		if (PC != None)
			PC.TeamMessage(None, "[Claude] "$Arg, 'Say');
		break;
	case "EXTRA":
		if (i >= 0 && i < ArrayCount(Extras))
			Extras[i] = Rest(Arg);
		break;
	case "CARD":
		if (i >= 0 && i < ArrayCount(Cards))
			Cards[i] = Rest(Arg);
		break;
	case "PROP":
		if (i >= 0 && i < ArrayCount(Props))
			Props[i] = Rest(Arg);
		break;
	case "PLUME":
		if (i >= 0 && i < ArrayCount(Plumes))
			Plumes[i] = Rest(Arg);
		break;
	case "TRUCK":
		if (i >= 0 && i < ArrayCount(Trucks))
			Trucks[i] = Rest(Arg);
		break;
	case "HAZE":
		HazeStart = float(Word(Arg, 0));
		HazeEnd = float(Word(Arg, 1));
		HazeColour.R = int(Word(Arg, 2));
		HazeColour.G = int(Word(Arg, 3));
		HazeColour.B = int(Word(Arg, 4));
		break;
	case "WEATHER":
		foreach DynamicActors(class'AvalonStorm', LiveStorm)
		{
			if (Caps(Arg) == "STORM")
				LiveStorm.Force(2);
			else if (Caps(Arg) == "CLEAR")
				LiveStorm.Force(0);
			else
				LiveStorm.Force(-1);
		}
		break;
	case "REBUILD":
		Build();
		break;
	case "SAVE":
		SaveAll();
		break;
	case "WHERE":
		if (PC != None && PC.Pawn != None)
		{
			V = PC.Pawn.Location;
			PC.ClientMessage("[Claude] you are at "$int(V.X)$" "$int(V.Y)$" "$int(V.Z)$" yaw "$int(PC.Rotation.Yaw * 360.0 / 65536.0) % 360);
		}
		break;
	default:
		Log("Cards: live, unknown command "$S);
		return;
	}
	Log("Cards: live "$LiveSeq$" "$S);
	if (!bInFile)
		SaveAll();
}

function Backwater()
{
	local AvalonRadio R;
	local AvalonBrownout B;
	local AvalonFlicker F;
	local AvalonPuff S;
	local vector P, HitL, HitN;

	if (RadioSpot.X != 0 || RadioSpot.Y != 0)
	{
		R = Spawn(class'AvalonRadio');
		if (R != None)
		{
			R.AddSpeaker(RadioSpot);
			S = AvalonPuff(R.Speakers[0]);
			if (S != None && RadioStatic != "")
			{
				S.AmbientSound = Sound(DynamicLoadObject(RadioStatic, class'Sound', true));
				S.SoundVolume = 30;
				S.SoundRadius = 30;
			}
			R.Begin(RadioMinGap, RadioMaxGap, 3000, RadioVolume);
			Made[Made.Length] = R;
		}
	}
	if (BrownoutMinGap > 0)
	{
		B = Spawn(class'AvalonBrownout');
		if (B != None)
		{
			B.Begin(TowerSpot, 2600, TowerSpot.Z, BrownoutMinGap, BrownoutMaxGap, BrownoutDepth,
				Sound(DynamicLoadObject(BrownoutDown, class'Sound', true)), Sound(DynamicLoadObject(BrownoutUp, class'Sound', true)));
			Made[Made.Length] = B;
		}
	}
	if (DecayLamp != "")
	{
		P.X = float(Word(DecayLamp, 0));
		P.Y = float(Word(DecayLamp, 1));
		P.Z = 0;
		if (Ground(P, HitL, HitN))
			P.Z = HitL.Z;
		P.Z += float(Word(DecayLamp, 2));
		F = Spawn(class'AvalonFlicker',,, P);
		if (F != None)
		{
			F.Begin(Sound(DynamicLoadObject(DecayBuzz, class'Sound', true)));
			Made[Made.Length] = F;
		}
	}
	Log("Cards: backwater radio "$R$" brownout "$B$" lamp "$F);
}

function Clouds()
{
	local AvalonClouds C;
	local vector V;

	if (CloudBanks <= 0)
		return;
	V = SurveyCentre;
	V.Z = CloudHeight;
	C = Spawn(class'AvalonClouds',,, V);
	if (C == None)
		return;
	C.Setup(CloudBanks, CloudHeight, CloudSpread, Wind, Texture(DynamicLoadObject(SteamTexture, class'Texture', true)),
		Texture(DynamicLoadObject(SmokeTexture, class'Texture', true)));
	Made[Made.Length] = C;
}

function Storm()
{
	local AvalonStorm St;
	local int i;

	if (!InList(StormMaps, MapName()))
		return;
	St = Spawn(class'AvalonStorm');
	if (St == None)
		return;
	St.Setup(StormDrops, StormRadius, StormFall, Wind, StormFogStart, StormFogEnd, StormFogColour,
		Sound(DynamicLoadObject(StormRain, class'Sound', true)), Sound(DynamicLoadObject(StormWind, class'Sound', true)), StormSkyFogEnd);
	St.Overcast(Texture(DynamicLoadObject(SmokeTexture, class'Texture', true)), StormClouds, StormCloudSize);
	St.Gloom = StormGloom;
	St.Cycle(StormClear, StormRamp, StormHold);
	St.GloomFog = StormGloomFog;
	for (i = 0; i < 5; i++)
		if (StormThunder[i] != "")
			St.AddThunder(Sound(DynamicLoadObject(StormThunder[i], class'Sound', true)));
	Made[Made.Length] = St;
	Log("Cards: storm on "$MapName()$", "$St.Drops.Length$" drops, "$St.NThunder$" thunder sounds");
}

function Motion()
{
	local int i;
	local vector P, HitL, HitN;
	local Texture ST, FT, WT;
	local AvalonPlume Pl;
	local AvalonTruck T;
	local StaticMesh M;

	ST = Texture(DynamicLoadObject(SmokeTexture, class'Texture', true));
	FT = Texture(DynamicLoadObject(FireTexture, class'Texture', true));
	WT = Texture(DynamicLoadObject(SteamTexture, class'Texture', true));
	for (i = 0; i < ArrayCount(Plumes); i++)
	{
		if (Plumes[i] == "")
			continue;
		P.X = float(Word(Plumes[i], 0));
		P.Y = float(Word(Plumes[i], 1));
		P.Z = 0;
		if (Ground(P, HitL, HitN))
			P.Z = HitL.Z;
		P.Z += float(Word(Plumes[i], 2));
		Pl = Spawn(class'AvalonPlume',,, P);
		if (Pl == None)
			continue;
		Pl.Setup(int(Word(Plumes[i], 3)), float(Word(Plumes[i], 4)), float(Word(Plumes[i], 5)), Wind, ST, FT, SmokeStyle, WT);
		Made[Made.Length] = Pl;
		Log("Cards: plume "$Plumes[i]);
	}
	for (i = 0; i < ArrayCount(Trucks); i++)
	{
		if (Trucks[i] == "")
			continue;
		M = StaticMesh(DynamicLoadObject(Word(Trucks[i], 0), class'StaticMesh', true));
		if (M == None || Paths[Clamp(int(Word(Trucks[i], 3)), 0, 3)] == "")
		{
			Log("Cards: truck skipped "$Trucks[i]);
			continue;
		}
		T = Spawn(class'AvalonTruck',,, vect(0,0,0));
		if (T == None)
			continue;
		T.Setup(M, float(Word(Trucks[i], 1)), Paths[Clamp(int(Word(Trucks[i], 3)), 0, 3)], float(Word(Trucks[i], 2)), float(Word(Trucks[i], 4)), float(Word(Trucks[i], 5)));
		Made[Made.Length] = T;
		Log("Cards: truck "$Trucks[i]$" at "$T.Location);
	}
}

// the first solid surface straight down: level geometry, terrain or a static mesh
function bool Ground(vector XY, out vector HitL, out vector HitN)
{
	local Actor A;
	local vector Start, End;

	Start = XY;
	Start.Z = 40000;
	End = XY;
	End.Z = -40000;
	foreach TraceActors(class'Actor', A, HitL, HitN, End, Start)
		if ((A == Level || A.bWorldGeometry || TerrainInfo(A) != None || StaticMeshActor(A) != None) && HitN.Z > 0)
			return true;
	return false;
}

// the water surface under a point (the top of a water volume), or false
function bool WaterTop(vector XY, out float Z)
{
	local CardProbe P;
	local float Lo, Hi, M;
	local int i;

	P = Spawn(class'CardProbe',,, XY);
	if (P == None)
		return false;
	Lo = -20000;
	Hi = 20000;
	P.SetLocation(XY + vect(0,0,1) * (Lo - XY.Z));
	if (P.PhysicsVolume == None || !P.PhysicsVolume.bWaterVolume)
	{
		P.Destroy();
		return false;
	}
	for (i = 0; i < 24; i++)
	{
		M = (Lo + Hi) / 2;
		P.SetLocation(XY + vect(0,0,1) * (M - XY.Z));
		if (P.PhysicsVolume != None && P.PhysicsVolume.bWaterVolume)
			Lo = M;
		else
			Hi = M;
	}
	P.Destroy();
	Z = Lo;
	return true;
}

function Survey()
{
	local float X, Y, WZ;
	local vector P, HitL, HitN;
	local string Row;
	local Light L;

	foreach AllActors(class'Light', L)
		if (L.LightEffect == LE_Sunlight)
			Log("Cards: sun "$L$" rotation "$L.Rotation$" at "$L.Location);
	for (Y = SurveyCentre.Y - SurveyRadius; Y <= SurveyCentre.Y + SurveyRadius; Y += SurveyStep)
	{
		Row = "";
		for (X = SurveyCentre.X - SurveyRadius; X <= SurveyCentre.X + SurveyRadius; X += SurveyStep)
		{
			P.X = X;
			P.Y = Y;
			P.Z = 0;
			if (Ground(P, HitL, HitN))
				Row = Row $ " " $ int(HitL.Z);
			else
				Row = Row $ " -";
			if (WaterTop(P, WZ))
				Row = Row $ "w" $ int(WZ);
		}
		Log("Cards: grid y="$int(Y)$" x0="$int(SurveyCentre.X - SurveyRadius)$" step="$int(SurveyStep)$":"$Row);
	}
}

function Haze()
{
	local ZoneInfo Z;

	foreach AllActors(class'ZoneInfo', Z)
	{
		Log("Cards: zone "$Z$" fog "$Z.bDistanceFog$" "$Z.DistanceFogStart$"-"$Z.DistanceFogEnd$" colour "$Z.DistanceFogColor.R$","$Z.DistanceFogColor.G$","$Z.DistanceFogColor.B);
		if (HazeEnd > 0 && (Z.bDistanceFog || bHazeAllZones))
		{
			Z.bDistanceFog = true;
			Z.DistanceFogStart = HazeStart;
			Z.DistanceFogEnd = HazeEnd;
			Z.DistanceFogColor = HazeColour;
			Log("Cards: haze on "$Z$" "$HazeStart$"-"$HazeEnd);
		}
	}
}

function Fly()
{
	local StaticMesh M;
	local AvalonFlyer F;

	if (FlyerMesh == "")
		return;
	M = StaticMesh(DynamicLoadObject(FlyerMesh, class'StaticMesh', true));
	if (M == None)
	{
		Log("Cards: flyer mesh "$FlyerMesh$" not found");
		return;
	}
	F = Spawn(class'AvalonFlyer',,, FlyerCentre);
	if (F == None)
		return;
	F.Setup(M, FlyerCentre, FlyerRadius, FlyerSpeed, FlyerScale, 0);
	Made[Made.Length] = F;
	Log("Cards: flyer "$FlyerMesh$" round "$FlyerCentre$" r "$FlyerRadius);
}

function Build()
{
	local int i;
	local vector HitL, HitN, P;
	local float WZ;
	local CardMesh M;
	local CardSprite S;
	local rotator R;

	if (!bAvalon)
	{
		// any other map: just the live edits recorded for it
		if (Editor == None)
			Editor = Spawn(class'AvalonEditor');
		if (Editor != None)
		{
			Editor.Cards = Self;
			Editor.Replay();
		}
		return;
	}
	for (i = 0; i < Made.Length; i++)
		if (Made[i] != None)
			Made[i].Destroy();
	Made.Length = 0;
	Haze();
	Fly();
	Motion();
	Storm();
	Clouds();
	Speakers();
	Backwater();

	// the landing pad and the dropship on it
	if (PadMesh != "" && Ground(PadSpot, HitL, HitN))
	{
		R.Yaw = PadYaw;
		M = Spawn(class'CardMesh',,, HitL, R);
		if (M != None && M.Show(PadMesh, PadScale))
			Made[Made.Length] = M;
		Log("Cards: pad at "$HitL$" "$M);
		if (ShipMesh != "")
		{
			P = HitL + (ShipOffset >> R) + vect(0,0,1) * ShipLift;
			R.Yaw = ShipYaw;
			M = Spawn(class'CardMesh',,, P, R);
			if (M != None && M.Show(ShipMesh, ShipScale))
				Made[Made.Length] = M;
			Log("Cards: ship at "$P$" "$M);
		}
	}

	// the oil rig: a directional card standing in the sea
	if (RigSize > 0)
	{
		// the picture's base line is 6% above its bottom: centre it 0.44 of its height above the sea
		P = RigSpot;
		// TutA's sea is a plain surface, not a water volume: then the first thing hit straight down
		if (!WaterTop(RigSpot, WZ))
		{
			if (Ground(RigSpot, HitL, HitN))
				WZ = HitL.Z;
			else
				WZ = 0;
		}
		P.Z = WZ + 0.44 * RigSize + RigSpot.Z;
		R.Yaw = RigYaw;
		S = Spawn(class'CardSprite',,, P, R);
		if (S != None)
		{
			for (i = 0; i < 8; i++)
				S.Frames[i] = RigTex[i];
			S.NumFrames = 8;
			// alpha-tested, drawn with the solid things: a translucent card out at sea
			// gets painted over by the (translucent) sea surface
			S.Style = STY_Masked;
			S.SetSize(RigSize);
			Made[Made.Length] = S;
		}
		Log("Cards: rig at "$P$" water "$WZ$" "$S);
	}

	// tree clusters: one picture each (trees look much the same from every side)
	for (i = 0; i < 8; i++)
	{
		if (TreeSpot[i].X == 0 && TreeSpot[i].Y == 0)
			continue;
		if (!Ground(TreeSpot[i], HitL, HitN))
			continue;
		S = Spawn(class'CardSprite',,, HitL + vect(0,0,0.45) * TreeSize[i]);
		if (S != None)
		{
			S.Frames[0] = TreeTex[Clamp(TreeLook[i], 0, 2)];
			S.NumFrames = 1;
			S.SetSize(TreeSize[i]);
			Made[Made.Length] = S;
		}
	}
	for (i = 0; i < ArrayCount(Props); i++)
		if (Props[i] != "")
			PlaceProp(Props[i]);
	for (i = 0; i < ArrayCount(Blocks); i++)
		if (Blocks[i] != "")
			PlaceBlock(Blocks[i]);
	for (i = 0; i < ArrayCount(Cards); i++)
		if (Cards[i] != "")
			PlaceCard(Cards[i]);
	for (i = 0; i < ArrayCount(Extras); i++)
		if (Extras[i] != "")
			PlaceCard(Extras[i]);
	if (Editor == None)
		Editor = Spawn(class'AvalonEditor');
	if (Editor != None)
	{
		Editor.Cards = Self;
		Editor.Replay();
	}
	Log("Cards: built "$Made.Length$" things on "$MapName());
}

// the n-th space separated word of S
function string Word(string S, int n)
{
	local int i;

	for (i = 0; i < n; i++)
	{
		if (InStr(S, " ") < 0)
			return "";
		S = Mid(S, InStr(S, " ") + 1);
	}
	if (InStr(S, " ") >= 0)
		S = Left(S, InStr(S, " "));
	return S;
}

function PlaceBlock(string Line)
{
	local vector P, Size, HitL, HitN;
	local rotator R;
	local CardMesh M;

	P.X = float(Word(Line, 0));
	P.Y = float(Word(Line, 1));
	R.Yaw = int(float(Word(Line, 2)) * 65536.0 / 360.0);
	Size.X = float(Word(Line, 3));
	Size.Y = float(Word(Line, 4));
	Size.Z = float(Word(Line, 5));
	if (!Ground(P, HitL, HitN))
		return;
	P.Z = HitL.Z + Size.Z / 2 + float(Word(Line, 6));
	M = Spawn(class'CardMesh',,, P, R);
	if (M != None && M.ShowBlock(Size, int(Word(Line, 7))))
		Made[Made.Length] = M;
}

function PlaceCard(string Line)
{
	local vector P, HitL, HitN;
	local rotator R;
	local float Size, WZ;
	local int N, k;
	local Texture T;
	local CardSprite S;

	P.X = float(Word(Line, 1));
	P.Y = float(Word(Line, 2));
	R.Yaw = int(float(Word(Line, 3)) * 65536.0 / 360.0);
	Size = float(Word(Line, 4));
	N = Clamp(int(Word(Line, 5)), 1, 16);
	if (Word(Line, 5) == "")
		N = 8;
	// stands on the land, or on TutA's sea surface
	if (!WaterTop(P, WZ))
	{
		if (!Ground(P, HitL, HitN))
		{
			Log("Cards: no ground under card "$Line);
			return;
		}
		WZ = HitL.Z;
	}
	// the picture's base line is 6% above its bottom
	P.Z = WZ + 0.44 * Size + float(Word(Line, 6));
	S = Spawn(class'CardSprite',,, P, R);
	if (S == None)
		return;
	for (k = 0; k < N; k++)
	{
		// a bare name is one of this package's cards; "AvalonSM.Cards.DrillingRigHY" names another package's
		if (InStr(Word(Line, 0), ".") >= 0)
			T = Texture(DynamicLoadObject(Word(Line, 0) $ k, class'Texture'));
		else
			T = Texture(DynamicLoadObject("U2AvalonCards." $ Word(Line, 0) $ k, class'Texture'));
		if (T == None)
		{
			Log("Cards: no texture U2AvalonCards." $ Word(Line, 0) $ k);
			S.Destroy();
			return;
		}
		S.Frames[k] = T;
	}
	S.NumFrames = N;
	S.Style = STY_Masked;
	S.SetSize(Size);
	Made[Made.Length] = S;
	Log("Cards: card "$Word(Line, 0)$" at "$P);
}

function PlaceProp(string Line)
{
	local vector P, C, HitL, HitN, Q;
	local rotator R;
	local float Scale, Ext, G;
	local CardMesh M;
	local Texture Skin;
	local string Pkg;
	local int k;

	P.X = float(Word(Line, 1));
	P.Y = float(Word(Line, 2));
	R.Yaw = int(float(Word(Line, 3)) * 65536.0 / 360.0);
	Scale = float(Word(Line, 4));
	C.X = float(Word(Line, 6));
	C.Y = float(Word(Line, 7));
	if (!Ground(P, HitL, HitN))
	{
		Log("Cards: no ground under "$Line);
		return;
	}
	// the lowest ground under the footprint, not under the centre: on a slope the base sinks into the uphill
	// side instead of floating over the downhill one (the user, 2026-10-08: "not look like the base is floating")
	G = HitL.Z;
	P.Z = HitL.Z;
	// word 10 = the footprint's half size in mesh units (the tools' bounds.json; StaticMesh has no script bounds)
	Ext = 250;
	if (Word(Line, 10) != "")
		Ext = float(Word(Line, 10));
	Ext *= 0.8 * Scale;
	if (Ext > 0)
	{
		for (k = 0; k < 8; k++)
		{
			Q = P;
			Q.X += Ext * Cos(k * 0.7854);
			Q.Y += Ext * Sin(k * 0.7854);
			if (Ground(Q, HitL, HitN))
				G = FMin(G, HitL.Z);
		}
	}
	// but never deeper than 15% of the footprint below the centre's ground: on a peak the lowest point was
	// ~50 m down the mountain and the crane tower sank into it (2026-10-08)
	G = FMax(G, P.Z - 0.15 * Ext);
	P.Z = G - float(Word(Line, 8)) * Scale + float(Word(Line, 5));
	P -= (C * Scale) >> R;
	M = Spawn(class'CardMesh',,, P, R);
	if (M != None && M.Show(Word(Line, 0), Scale))
	{
		// its colours: word 9 names a skin, else the mesh's own package palette (AvalonSM.Pal.Pal,
		// AvalonSM2.Pal.Pal2): the generated meshes carry no material of their own (make_avalon sets Skins too)
		Pkg = Word(Line, 0);
		Pkg = Left(Pkg, InStr(Pkg, "."));
		if (Word(Line, 9) != "" && Word(Line, 9) != "-")
			Skin = Texture(DynamicLoadObject(Word(Line, 9), class'Texture', true));
		else
		{
			Skin = Texture(DynamicLoadObject(Pkg$".Pal.Pal", class'Texture', true));
			if (Skin == None)
				Skin = Texture(DynamicLoadObject(Pkg$".Pal.Pal2", class'Texture', true));
		}
		if (Skin != None)
			M.Skins[0] = Skin;
		Made[Made.Length] = M;
	}
	Log("Cards: prop "$Word(Line, 0)$" at "$P$" ground "$G$" skin "$Skin);
}

defaultproperties
{
	Maps="tuta"
	SurveyRadius=30000.000000
	SurveyStep=2500.000000
	SurveyCentre=(X=-349.000000,Y=1388.000000,Z=0.000000)
	PadMesh="Mission_AvalonM.Structuron2.M10_LandingPadNew1a"
	PadScale=1.000000
	ShipMesh="Martins.Dropship.AtlantisDropship"
	ShipScale=1.000000
	ShipLift=40.000000
	RigSize=0.000000
	TreeTex(0)=Texture'Trees0'
	TreeTex(1)=Texture'Trees1'
	TreeTex(2)=Texture'Trees2'
	RigTex(0)=Texture'Rig0'
	RigTex(1)=Texture'Rig1'
	RigTex(2)=Texture'Rig2'
	RigTex(3)=Texture'Rig3'
	RigTex(4)=Texture'Rig4'
	RigTex(5)=Texture'Rig5'
	RigTex(6)=Texture'Rig6'
	RigTex(7)=Texture'Rig7'
	SmokeTexture="U2AvalonCards.SmokePuff"
	FireTexture="SpecialFX.Fire.fireball_tw018"
	SteamTexture="U2AvalonCards.SteamPuff"
	SmokeStyle=6
	RevealSpeed=3000.000000
	PAMinGap=45.000000
	LivePoll=2.000000
	LiveFile="AvalonLive.txt"
	RadioSpot=(X=-349.000000,Y=1388.000000,Z=4330.000000)
	RadioMinGap=50.000000
	RadioMaxGap=120.000000
	RadioVolume=1.200000
	RadioStatic="U2Ambient2A.Transmissions.transmission_static_loop_1"
	TowerSpot=(X=-349.000000,Y=1388.000000,Z=3300.000000)
	BrownoutMinGap=480.000000
	BrownoutMaxGap=900.000000
	BrownoutDepth=0.550000
	BrownoutDown="U2Ambient2A.Generator.generator_power_dwn_1"
	BrownoutUp="U2Ambient2A.Generator.building_power_up_1"
	DecayLamp="1330 279 450"
	DecayBuzz="U2AmbientA.Electric.Elecsparksloop0"
	StormClear=300.000000
	StormRamp=60.000000
	StormHold=240.000000
	PAMaxGap=110.000000
	PARadius=16000.000000
	PAVolume=2.000000
	StormDrops=320
	StormClouds=30
	CloudBanks=14
	CloudHeight=11000.000000
	CloudSpread=60000.000000
	StormCloudSize=16000.000000
	StormGloom=0.400000
	StormGloomFog=(X=45,Y=50,Z=60)
	StormSkyFogEnd=900.000000
	StormRadius=1600.000000
	StormFall=2600.000000
	StormFogStart=600.000000
	StormFogEnd=26000.000000
	StormFogColour=(R=78,G=84,B=92,A=255)
	StormRain="U2AmbientA.MiscEnv.Iceyrain_03"
	StormWind="U2AmbientA.MiscEnv.Blusterywindloop_04"
	StormThunder(0)="U2AmbientA.MiscEnv.Thunder_01"
	StormThunder(1)="U2AmbientA.MiscEnv.Thunder_02"
	StormThunder(2)="U2AmbientA.MiscEnv.Thunder_03"
	StormThunder(3)="U2AmbientA.MiscEnv.Thunder04R"
	StormThunder(4)="U2AmbientA.MiscEnv.Thunder_05"
	RevealScale=1.000000
	RemoteRole=ROLE_None
}
