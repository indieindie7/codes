//=============================================================================
// DomeLeak - a breached Izarian dome: fluid sprays out and the Izarian
// suffocates (drowning damage) until the suit is empty. Uses the game's own
// blood-trail effect for Izarians.
//=============================================================================
class DomeLeak extends Info;

var Pawn Breacher;
var float DamagePerTick, EndTime;
var bool bPanic;
var ParticleSalamander Stream;

function Start(Pawn Instigator, float PerSecond, float Seconds, bool bWillPanic)
{
	Breacher = Instigator;
	DamagePerTick = PerSecond * 0.5;
	EndTime = Level.TimeSeconds + Seconds;
	bPanic = bWillPanic;
	Spray();
	Spray();
	SetTimer(0.5, true);
	if (bPanic)
		Panic();
}

function Widen()
{
	EndTime += 3.0;
	Spray();
}

function vector DomeSpot()
{
	return Owner.Location + vect(0,0,1) * Pawn(Owner).CollisionHeight * 0.75;
}

// the Izarians' own body fluid (their gib set's blood trail), streaming out
// of the dome for as long as it leaks
function Spray()
{
	local ParticleSalamander Template;

	if (Owner == None)
		return;
	if (Stream == None)
	{
		Template = ParticleSalamander(DynamicLoadObject("Blood.ParticleSalamander6", class'ParticleSalamander'));
		if (Template != None)
			Stream = ParticleSalamander(class'ParticleGenerator'.static.CreateNew(Self, Template, DomeSpot()));
		if (Stream != None)
		{
			Stream.Trigger(Self, Pawn(Owner));
			Stream.SetBase(Owner);
		}
	}
	if (Stream != None)
		Stream.SetLocation(DomeSpot());
}

event Destroyed()
{
	if (Stream != None)
	{
		Stream.ParticleDestroy();
		Stream = None;
	}
	Super.Destroyed();
}

// the game's own panic: the Izarian breaks off and flails around
function Panic()
{
	local U2NPCControllerBase C;
	C = U2NPCControllerBase(Pawn(Owner).Controller);
	if (C != None && C.CanPanic(Breacher, DomeSpot(), DamagePerTick, class'DamageTypeDrowned', vect(0,0,0)))
		C.HandlePanic();
}

event Timer()
{
	local Pawn P;

	P = Pawn(Owner);
	if (P == None || P.bDeleteMe || P.Health <= 0 || Level.TimeSeconds > EndTime)
	{
		Destroy();
		return;
	}
	Spray();
	P.TakeDamage(int(DamagePerTick), Breacher, DomeSpot(), vect(0,0,0), class'DamageTypeDrowned');
}

defaultproperties
{
	RemoteRole=ROLE_None
}
