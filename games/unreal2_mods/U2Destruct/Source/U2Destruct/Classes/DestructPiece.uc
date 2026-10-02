//=============================================================================
// DestructPiece - a movable stand-in for a map prop: same mesh, place, size and
// skins, solid like the original. StaticMeshActor is bStatic and can't be
// spawned, so this carries the mesh the way U2TestHub's HubMesh does. It spawns
// without collision (so the original can't block the spawn) and Copy() turns it on.
//=============================================================================
class DestructPiece extends U2Decoration;

// skins aren't copied: most props use their mesh's own materials, and the probe logs
// the original's Skins so a prop that overrides them can be spotted
function Copy(StaticMeshActor From)
{
	StaticMesh = From.StaticMesh;
	SetDrawType(DT_StaticMesh);
	SetDrawScale(From.DrawScale);
	SetDrawScale3D(From.DrawScale3D);
	SetCollision(true, true, true);
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bCollideActors=False
	bBlockActors=False
	bBlockPlayers=False
	bBlockZeroExtentTraces=True
	bCollideWorld=False
	bHidden=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
