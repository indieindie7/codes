//=============================================================================
// SevenProp - a static mesh placed by a director at level start (big meshes
// such as the crashed ship fail to import into generated maps, but draw fine
// when spawned). Collides so the player can't walk through it; usable if a
// director wires OnUse.
//=============================================================================
class SevenProp extends U2Decoration;

var SevenBoard Board;              // when set, Use opens Aida's board

function bool IsUsable(optional Actor Other) { return Board != None; }

function OnUse(Actor Other)
{
	if (Board != None)
		Board.OnUse(Other);
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bCollideActors=True
	bCollideWorld=False
	bBlockActors=True
	bBlockPlayers=True
	bHidden=False
	Physics=PHYS_None
	CollisionRadius=300.000000
	CollisionHeight=200.000000
	RemoteRole=ROLE_None
}
