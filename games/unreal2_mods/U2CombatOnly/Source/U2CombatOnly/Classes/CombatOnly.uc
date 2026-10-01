//=============================================================================
// CombatOnly - Unreal II as a chain of combat missions.
//
// bSkipTutorial (default on): a new game (CS_Titles / the tutorial) starts
//   straight at the first combat mission, Sanctuary. Every mission map hands
//   out its own loadout, so nothing is missing.
// bSkipIntermissions (default on): the Atlantis hub and the arrival/departure
//   cutscene maps (PA_* / PD_*) between missions are skipped. If a travel to
//   one is caught before it starts, the destination is rewritten; otherwise
//   the mod moves on as soon as that map begins (Atlantis: at level start,
//   since the hub freezes every mod's Tick).
//
// The campaign order comes from the game's own Mission Log (U2Menus.ui).
// Add with ?Mutator=U2CombatOnly.CombatOnly or in User.ini's [DefaultPlayer]
// Mutator=. Settings: [U2CombatOnly.CombatOnly] in User.ini.
//=============================================================================
class CombatOnly extends Mutator
	config(User);

var() config bool bSkipTutorial;
var() config bool bSkipIntermissions;

var string LastSeenURL;   // NextURL we already looked at
var bool bJumped;         // this level already sent us on

event PostBeginPlay()
{
	local string Dest;

	Super.PostBeginPlay();
	SaveConfig();

	// Atlantis freezes every mod's Tick (only the player runs), so decide now:
	// the level still processes a travel requested this early
	if (AtlantisGameInfo(Level.Game) != None)
	{
		Dest = Redirect(Level.GetLocalURL());
		if (Dest != "")
		{
			bJumped = true;
			Log("U2CombatOnly: Atlantis after mission "$AtlantisGameInfo(Level.Game).LastMissionCompleted$", going to "$Dest);
			Level.ServerTravel(Dest, false);
		}
	}
}

// map part of a travel URL ("PD_Hell?foo=1" -> "PD_HELL")
static function string MapOf(string URL)
{
	local int i;
	i = InStr(URL, "?");
	if (i >= 0)
		URL = Left(URL, i);
	i = InStr(URL, ".");            // "M01a.un2"
	if (i >= 0)
		URL = Left(URL, i);
	return Caps(URL);
}

static function int IntOption(string URL, string Key)
{
	local int i;
	i = InStr(Caps(URL), Caps(Key)$"=");
	if (i < 0)
		return -1;
	return int(Mid(URL, i + Len(Key) + 1));
}

// where a travel to URL should really go ("" = leave it alone)
function string Redirect(string URL)
{
	local string M;

	M = MapOf(URL);
	if (bSkipTutorial)
		switch (M)
		{
		case "CS_TITLES":        // new game: titles -> tutorial -> Avalon -> Atlantis
		case "TUTA":
		case "TUTB":
		case "PD_AVALON":
			return "M08A1";
		}
	if (!bSkipIntermissions)
		return "";
	switch (M)
	{
	// arrival cutscenes -> their mission
	case "PA_SANCTUARY": return "M08A1";
	case "PA_HELL":      return "M01a";
	case "PA_ACHERON":   return "M06_Acheron";
	case "PA_JANUS":     return "M09a";
	case "PA_AVALONB":   return "M10_Avalon";
	// departure cutscenes -> the mission after the Atlantis stop
	case "PD_SANCTUARY": return "MM_Marsh";
	case "PD_HELL":      return AfterAtlantis(2);
	case "PD_ACHERON":   return AfterAtlantis(8);
	case "PD_SULFERON":  return AfterAtlantis(5);
	case "PD_NAKOJA":    return AfterAtlantis(9);
	case "ATLANTIS":
		// Atlantis strips MissionCompleted from its URL once loaded; ask it instead
		if (IntOption(URL, "MissionCompleted") < 0 && AtlantisGameInfo(Level.Game) != None)
			return AfterAtlantis(AtlantisGameInfo(Level.Game).LastMissionCompleted);
		return AfterAtlantis(IntOption(URL, "MissionCompleted"));
	}
	return "";
}

// Atlantis?MissionCompleted=N -> the next mission (the Mission Log's order)
function string AfterAtlantis(int N)
{
	switch (N)
	{
	case 0:  return "M08A1";               // Sanctuary
	case 1:  return "M01a";                // Hell
	case 2:  return "M06_Acheron";         // Acheron
	case 8:  return "MM_Waterfront";
	case 4:  return "M06_Obolus";
	case 6:  return "MM_Sulferon_Assault"; // Sulferon
	case 5:  return "M09a";                // Janus
	case 7:  return "M03a1";               // Na Koja Abad
	case 9:  return "M03b1";
	case 10: return "M10_Avalon";          // Avalon
	}
	return "";
}

event Tick(float DeltaTime)
{
	local string Dest;
	local Controller C;

	// 1. a travel is pending: rewrite it before the next map loads
	if (Level.NextURL != "" && Level.NextURL != LastSeenURL)
	{
		LastSeenURL = Level.NextURL;
		Dest = Redirect(Level.NextURL);
		if (Dest != "" && MapOf(Dest) != MapOf(Level.NextURL))
		{
			Log("U2CombatOnly: "$Level.NextURL$" -> "$Dest);
			Level.NextURL = Dest;
			LastSeenURL = Dest;
		}
		return;
	}

	// 2. we're on a skipped map anyway (loaded directly or from a save): move on
	if (bJumped || Level.NextURL != "")
		return;
	Dest = Redirect(Level.GetLocalURL());

	if (Dest == "")
		return;
	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
		{
			bJumped = true;
			Log("U2CombatOnly: on "$Level.GetLocalURL()$", going to "$Dest);
			Level.ServerTravel(Dest, false);
			return;
		}
}

defaultproperties
{
	bSkipTutorial=True
	bSkipIntermissions=True
	RemoteRole=ROLE_None
}
