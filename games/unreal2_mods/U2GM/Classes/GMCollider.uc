//=============================================================================
// GMCollider - "gm collide R H": an invisible cylinder that blocks players and
// actors, so geometry added or swapped without the editor (GM meshes, the
// fork's mesh swaps) can be walked on and bumped into. A journal line
// "collide X Y Z R H"; several approximate any shape (Avalon Q69, 2026-10-08).
//=============================================================================
class GMCollider extends Actor;

function Set(float R, float H)
{
	SetCollisionSize(FMax(R, 8), FMax(H, 8));
}

defaultproperties
{
	DrawType=DT_None
	bHidden=True
	bStatic=False
	bNoDelete=False
	bCollideActors=True
	bBlockActors=True
	bBlockPlayers=True
	bBlockZeroExtentTraces=True
	bBlockNonZeroExtentTraces=True
	bCollideWorld=False
	CollisionRadius=64
	CollisionHeight=64
	RemoteRole=ROLE_None
}
