//=============================================================================
// HubMesh - a static mesh on a spawnable, collision-free actor (test tool)
//=============================================================================
class HubMesh extends U2Decoration;

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	bHidden=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
