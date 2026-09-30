//=============================================================================
// SevenMissions - the chapter's mission state, kept in User.ini so it lives
// across level loads: which missions exist, which are done, which is running.
//
// A mission is a map plus a win condition; on that map SevenSanctuary (or a
// later director) runs the encounter table and reports kills and arrivals
// here. When the condition is met, Aida debriefs and the player is sent back
// to the patrol zone (Sanctuary's first map).
//
// Missions are config, so the list can be edited in User.ini.
//=============================================================================
class SevenMissions extends Object
	config(User);

struct Mission
{
	var string Id;
	var string Title;        // shown on Aida's board
	var string Map;
	var string Win;          // kills:N | reach:X,Y,Z,R | survive:SECONDS
	var int Unlock;          // missions that must be done first (count)
	var int OfferLine;       // SevenScript cue Aida speaks when offering it (episode 99)
	var int DoneLine;        // cue on completion
};
var config array<Mission> Missions;
var config string Active;    // mission id in progress, "" for none
var config string Done;      // comma-separated ids
var config int Kills;        // progress of the active mission
var config float StartedAt;  // level time it started (survive)

static function bool IsDone(string Id)
{
	return InStr(","$default.Done$",", ","$Id$",") >= 0;
}

static function int DoneCount()
{
	local int i, N;
	for (i = 0; i < default.Missions.Length; i++)
		if (IsDone(default.Missions[i].Id))
			N++;
	return N;
}

static function int Find(string Id)
{
	local int i;
	for (i = 0; i < default.Missions.Length; i++)
		if (default.Missions[i].Id ~= Id)
			return i;
	return -1;
}

// the missions Aida can offer now
static function array<int> Offered()
{
	local array<int> R;
	local int i;
	for (i = 0; i < default.Missions.Length; i++)
		if (!IsDone(default.Missions[i].Id) && default.Missions[i].Unlock <= DoneCount())
			R[R.Length] = i;
	return R;
}

static function Begin(string Id)
{
	default.Active = Id;
	default.Kills = 0;
	default.StartedAt = 0;
	StaticSaveConfig();
}

static function Complete()
{
	if (default.Active != "" && !IsDone(default.Active))
	{
		if (default.Done == "")
			default.Done = default.Active;
		else
			default.Done = default.Done$","$default.Active;
	}
	default.Active = "";
	default.Kills = 0;
	StaticSaveConfig();
}

static function Abandon()
{
	default.Active = "";
	default.Kills = 0;
	StaticSaveConfig();
}

static function ResetAll()
{
	default.Active = "";
	default.Done = "";
	default.Kills = 0;
	StaticSaveConfig();
}

defaultproperties
{
	Missions(0)=(Id="yard",Title="Clear the landing yard",Map="M08A1",Win="kills:6",Unlock=0,OfferLine=1,DoneLine=6)
	Missions(1)=(Id="walkways",Title="Sweep the upper walkways",Map="M08A1",Win="kills:4",Unlock=1,OfferLine=2,DoneLine=7)
	Missions(2)=(Id="nest",Title="Strike: the nest under the colony",Map="M08A2",Win="kills:8",Unlock=1,OfferLine=3,DoneLine=8)
	Missions(3)=(Id="marsh",Title="The hunt in the marsh",Map="MM_Marsh",Win="kills:8",Unlock=2,OfferLine=4,DoneLine=9)
	Missions(4)=(Id="log",Title="Isaak's log",Map="M08B",Win="reach:0,0,0,400",Unlock=3,OfferLine=5,DoneLine=10)
}
