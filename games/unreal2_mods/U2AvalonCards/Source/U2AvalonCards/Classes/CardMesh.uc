//=============================================================================
// A game static mesh placed at run time (the landing pad, the dropship):
// StaticMeshActor is bStatic and can't be spawned, U2Decoration carries a
// mesh too (as U2TestHub's HubMesh does). No collision: it's scenery.
//=============================================================================
class CardMesh extends U2Decoration;

function bool Show(string Path, float Scale)
{
	local StaticMesh M;

	M = StaticMesh(DynamicLoadObject(Path, class'StaticMesh'));
	if (M == None)
	{
		Log("Cards: can't load mesh "$Path);
		Destroy();
		return false;
	}
	StaticMesh = M;
	SetDrawType(DT_StaticMesh);
	SetDrawScale(Scale);
	return true;
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bNoDelete=False
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	bHidden=False
	bAlwaysRelevant=True
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
