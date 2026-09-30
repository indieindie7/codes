//=============================================================================
// HoverMutator - puts a HoverBike in front of the player when a map starts.
// Always on maps named HoverTest*; on every map when bSpawnEverywhere=True
// ([U2Hover.HoverMutator] in User.ini).
//=============================================================================
class HoverMutator extends Mutator
	config(User);

var() config bool bSpawnEverywhere;
var() config float PrairieMaxSpeed;   // cruise on Prairie maps (the ride should take a while)
var bool bDone;

function bool WantBike()
{
	return bSpawnEverywhere || Left(Caps(string(Level.Outer)), 9) == "HOVERTEST" || Left(Caps(string(Level.Outer)), 7) == "PRAIRIE";
}

simulated event Tick(float Delta)
{
	local Controller C;
	local vector X, Y, Z, Spot;
	local rotator R;
	local HoverBike B;
	local float Dist;

	if (bDone)
		return;
	if (!WantBike())
	{
		bDone = true;
		Disable('Tick');
		return;
	}
	for (C = Level.ControllerList; C != None; C = C.NextController)
	{
		if (PlayerController(C) == None || C.Pawn == None)
			continue;
		R.Yaw = C.Pawn.Rotation.Yaw;
		GetAxes(R, X, Y, Z);
		// try a few spots in front of the player
		for (Dist = 350; Dist <= 800 && B == None; Dist += 150)
		{
			Spot = C.Pawn.Location + X * Dist + vect(0,0,1) * 60;
			B = Spawn(class'HoverBike', , , Spot, R);
		}
		if (B != None && PrairieMaxSpeed > 0 && Left(Caps(string(Level.Outer)), 7) == "PRAIRIE")
			B.MaxSpeed = PrairieMaxSpeed;
		log("U2Hover: spawned" @ B @ "for" @ C);
		bDone = true;
		Disable('Tick');
		return;
	}
}

defaultproperties
{
	bSpawnEverywhere=False
	PrairieMaxSpeed=1200.000000
}
