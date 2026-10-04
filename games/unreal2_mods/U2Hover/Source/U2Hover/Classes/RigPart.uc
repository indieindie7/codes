//=============================================================================
// RigPart - one rigid piece of a RigBike (a UT3 vehicle bone's faces as a
// static mesh). Purely visual: no collision, placed by its RigBike every tick.
//=============================================================================
class RigPart extends Actor
	notplaceable;

function SetMesh(StaticMesh M)
{
	StaticMesh = M;
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	bBlockZeroExtentTraces=False
	bBlockNonZeroExtentTraces=False
	bProjTarget=False
	bStatic=False
	bMovable=True
	Physics=PHYS_None
	RemoteRole=ROLE_None
	bUnlit=False
}
