//=============================================================================
// SevenBoard - Aida's mission board, in the patrol zone (Sanctuary's first
// map). A usable console: Use calls Aida, who offers the open missions; the
// number keys 1-3 accept one (Use again closes). Accepting starts the
// mission and travels to its map. On return, if the active mission is done,
// Aida debriefs.
//
// Spawned by SevenSanctuary on M08A1 at BoardLocation.
//=============================================================================
class SevenBoard extends Actor;

var SevenStory Story;
var PlayerController PC;
var bool bOpen;
var array<int> Shown;                 // mission indices on the list
var ComponentHandle Prompt_, List_;
var float PromptCheck;
var bool bDebriefed;

function bool IsUsable(optional Actor Other) { return true; }

function OnUse(Actor Other)
{
	if (bOpen)
		Close();
	else
		Open();
}

event PostBeginPlay()
{
	Super.PostBeginPlay();
	foreach DynamicActors(class'SevenStory', Story)
		break;
	SetTimer(0.3, true);
}

event Timer()
{
	local Controller C;
	local float D;

	if (PC == None)
		for (C = Level.ControllerList; C != None; C = C.NextController)
			if (PlayerController(C) != None)
				PC = PlayerController(C);
	if (PC == None || PC.Pawn == None)
		return;

	// back from a mission that's done: the debrief, once
	if (!bDebriefed && class'SevenMissions'.default.Active != "" && Story != None)
	{
		bDebriefed = true;
		Debrief();
	}

	// a prompt when the player is close
	D = VSize(PC.Pawn.Location - Location);
	if (!bOpen && D < 300 && !(~Prompt_))
		Prompt_ = Overlay("BoardPrompt");
	else if ((bOpen || D >= 300) && (~Prompt_))
		Prompt_ = class'UIConsole'.static.DestroyComponent(Prompt_);
	if (bOpen && D > 500)
		Close();
}

function ComponentHandle Overlay(string Name)
{
	local ComponentHandle H;
	H = class'UIConsole'.static.LoadComponent("SevenBoard", Name);
	if (~H)
	{
		class'UIConsole'.static.SetOwner(H, Self);
		class'UIConsole'.static.AddComponent(H);
	}
	return H;
}

function Open()
{
	local int i;
	local string L1, L2, L3;

	Shown = class'SevenMissions'.static.Offered();
	if (Shown.Length > 3)
		Shown.Length = 3;
	bOpen = true;
	if (Story != None)
		Story.Say(99, 0);                    // "I have work for you"
	for (i = 0; i < Shown.Length; i++)
	{
		if (i == 0) L1 = "1  "$class'SevenMissions'.default.Missions[Shown[i]].Title;
		if (i == 1) L2 = "2  "$class'SevenMissions'.default.Missions[Shown[i]].Title;
		if (i == 2) L3 = "3  "$class'SevenMissions'.default.Missions[Shown[i]].Title;
	}
	if (Shown.Length == 0)
		L1 = "Nothing open. Come back later.";
	if (~List_)
		List_ = class'UIConsole'.static.DestroyComponent(List_);
	List_ = class'UIConsole'.static.LoadComponent("SevenBoard", "BoardList:"$L1$"/"$L2$"/"$L3$"/(1-3 to accept, USE to close)");
	if (~List_)
	{
		class'UIConsole'.static.SetOwner(List_, Self);
		class'UIConsole'.static.AddComponent(List_);
	}
	Log("SevenBoard: open, "$Shown.Length$" missions");
}

function Close()
{
	bOpen = false;
	if (~List_)
		List_ = class'UIConsole'.static.DestroyComponent(List_);
}

// the player pressed a number (SevenStory's exec forwards it)
function Choose(int N)
{
	local int m;

	if (!bOpen || N < 1 || N > Shown.Length)
		return;
	m = Shown[N - 1];
	Close();
	if (Story != None)
		Story.Say(99, class'SevenMissions'.default.Missions[m].OfferLine);
	class'SevenMissions'.static.Begin(class'SevenMissions'.default.Missions[m].Id);
	Log("SevenBoard: accepted "$class'SevenMissions'.default.Missions[m].Id);
	// let the line play, then go
	SetTimer(4.0, false);
	GotoState('Departing');
}

state Departing
{
	event Timer()
	{
		local int m;
		m = class'SevenMissions'.static.Find(class'SevenMissions'.default.Active);
		if (m >= 0)
			Level.ServerTravel(class'SevenMissions'.default.Missions[m].Map, false);
	}
}

function Debrief()
{
	local int m;

	m = class'SevenMissions'.static.Find(class'SevenMissions'.default.Active);
	if (m >= 0 && class'SevenMissions'.default.Kills < 0)   // Kills < 0 marks "won" (set by the director)
	{
		Story.Say(99, class'SevenMissions'.default.Missions[m].DoneLine);
		class'SevenMissions'.static.Complete();
	}
	else
		class'SevenMissions'.static.Abandon();
}

event Destroyed()
{
	if (~Prompt_)
		Prompt_ = class'UIConsole'.static.DestroyComponent(Prompt_);
	if (~List_)
		List_ = class'UIConsole'.static.DestroyComponent(List_);
	Super.Destroyed();
}

defaultproperties
{
	DrawType=DT_StaticMesh
	StaticMesh=StaticMesh'Terran_DecoM.Crates.Terran_Console_01'
	bCollideActors=True
	bCollideWorld=False
	bBlockActors=True
	bBlockPlayers=True
	CollisionRadius=40.000000
	CollisionHeight=50.000000
	RemoteRole=ROLE_None
}
