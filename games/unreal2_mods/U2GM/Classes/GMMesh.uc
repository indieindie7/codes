//=============================================================================
// GMMesh - a static mesh the GM placed or moved. StaticMeshActor is bStatic
// and can't be spawned, U2Decoration carries a mesh (as AvalonCards' CardMesh).
//=============================================================================
class GMMesh extends U2Decoration;

function bool Show(string Path)
{
	local StaticMesh M;

	M = StaticMesh(DynamicLoadObject(Path, class'StaticMesh', true));
	if (M == None)
	{
		Log("GM: can't load mesh "$Path);
		return false;
	}
	StaticMesh = M;
	SetDrawType(DT_StaticMesh);
	return true;
}

defaultproperties
{
	DrawType=DT_StaticMesh
	// meshes spawned at run time get almost none of the map's baked light and read black (AvalonCards' CardMesh)
	AmbientGlow=70
	bStatic=False
	bNoDelete=False
	bCollideActors=True
	bBlockActors=True
	bBlockPlayers=True
	bCollideWorld=False
	bHidden=False
	bAlwaysRelevant=True
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
