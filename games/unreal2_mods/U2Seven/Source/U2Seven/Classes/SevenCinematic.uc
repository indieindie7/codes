//=============================================================================
// SevenCinematic - a small cutscene: the player's view is handed to this
// actor, which glides through a list of shots (from/to positions and
// rotations over a duration), while the story's radio lines play as usual.
// The player is held still; Fire or Jump skips. A title card can be shown.
//
// Shots are given by whoever starts it (SevenSanctuary for the opening).
//=============================================================================
class SevenCinematic extends Actor;

struct Shot
{
	var vector From, To;
	var rotator RotFrom, RotTo;
	var float Time;
	var string Title;        // shown for this shot (empty: none)
};
var array<Shot> Shots;

var PlayerController PC;
var int Current;
var float ShotStart;
var bool bRunning;
var ComponentHandle Title_;
var string TitleShown;
var bool bHadHud;

function Start(PlayerController InPC)
{
	PC = InPC;
	if (PC == None || PC.Pawn == None || Shots.Length == 0)
	{
		Destroy();
		return;
	}
	bRunning = true;
	Current = -1;
	// hold the player: no walking, no firing, no HUD
	PC.Pawn.SetPhysics(PHYS_None);
	PC.Pawn.Velocity = vect(0,0,0);
	if (U2Weapon(PC.Pawn.Weapon) != None)
		U2Weapon(PC.Pawn.Weapon).bDisableFiring = true;
	bHadHud = Level.Game.bDisplayHud;
	Level.Game.bDisplayHud = false;
	PC.SetViewTarget(Self);
	NextShot();
	Log("SevenCinematic: started, "$Shots.Length$" shots");
}

function NextShot()
{
	Current++;
	if (Current >= Shots.Length)
	{
		Finish();
		return;
	}
	ShotStart = Level.TimeSeconds;
	SetLocation(Shots[Current].From);
	SetRotation(Shots[Current].RotFrom);
	ShowTitle(Shots[Current].Title);
}

function ShowTitle(string T)
{
	if (T == TitleShown)
		return;
	if (~Title_)
		Title_ = class'UIConsole'.static.DestroyComponent(Title_);
	TitleShown = T;
	if (T == "")
		return;
	Title_ = class'UIConsole'.static.LoadComponent("SevenCine", T);
	if (~Title_)
	{
		class'UIConsole'.static.SetOwner(Title_, Self);
		class'UIConsole'.static.AddComponent(Title_);
	}
}

event Tick(float DeltaTime)
{
	local float A;
	local rotator R;

	if (!bRunning || PC == None || PC.Pawn == None)
		return;
	// skip
	if (PC.bFire != 0 || PC.bPressedJump)
	{
		Finish();
		return;
	}
	A = FClamp((Level.TimeSeconds - ShotStart) / FMax(Shots[Current].Time, 0.01), 0, 1);
	A = A * A * (3 - 2 * A);                                  // ease in and out
	SetLocation(Shots[Current].From + (Shots[Current].To - Shots[Current].From) * A);
	R = Shots[Current].RotFrom;
	R.Pitch += int((Shots[Current].RotTo.Pitch - Shots[Current].RotFrom.Pitch) * A);
	R.Yaw += int((Shots[Current].RotTo.Yaw - Shots[Current].RotFrom.Yaw) * A);
	SetRotation(R);
	if (Level.TimeSeconds - ShotStart >= Shots[Current].Time)
		NextShot();
}

function Finish()
{
	bRunning = false;
	ShowTitle("");
	if (PC != None)
	{
		PC.SetViewTarget(None);
		if (PC.Pawn != None)
		{
			PC.Pawn.SetPhysics(PHYS_Walking);
			if (U2Weapon(PC.Pawn.Weapon) != None)
				U2Weapon(PC.Pawn.Weapon).bDisableFiring = false;
		}
	}
	Level.Game.bDisplayHud = bHadHud;
	Log("SevenCinematic: finished at shot "$Current);
	Destroy();
}

event Destroyed()
{
	if (~Title_)
		Title_ = class'UIConsole'.static.DestroyComponent(Title_);
	Super.Destroyed();
}

defaultproperties
{
	bHidden=True
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
