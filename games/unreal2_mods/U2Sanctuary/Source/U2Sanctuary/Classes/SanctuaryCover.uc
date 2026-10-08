//=============================================================================
// A piece of cover the LEVEL DESIGNER role asked for at an arena with too little:
// one of the map's own crates (the remix rule: the level keeps its own look),
// blocking players and creatures. The AI's cover nodes don't know it.
//=============================================================================
class SanctuaryCover extends Actor;

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bNoDelete=False
	bCollideActors=True
	bBlockActors=True
	bBlockPlayers=True
	bBlockZeroExtentTraces=True
	bBlockNonZeroExtentTraces=True
	bProjTarget=True
	bShadowCast=True
	RemoteRole=ROLE_None
}
