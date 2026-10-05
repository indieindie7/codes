//=============================================================================
// A game static mesh placed at run time (the landing pad, the dropship):
// StaticMeshActor is bStatic and can't be spawned, U2Decoration carries a
// mesh too (as U2TestHub's HubMesh does). No collision: it's scenery.
//=============================================================================
#exec TEXTURE IMPORT NAME=Block0 FILE=Textures\Block0.tga MIPS=On
#exec TEXTURE IMPORT NAME=Block1 FILE=Textures\Block1.tga MIPS=On
#exec TEXTURE IMPORT NAME=Block2 FILE=Textures\Block2.tga MIPS=On
#exec TEXTURE IMPORT NAME=Block3 FILE=Textures\Block3.tga MIPS=On

class CardMesh extends U2Decoration;

var Texture BlockTex[4];

// a plain coloured box of the given size (world units): a crate mesh stretched, with a flat skin.
// For rough blocking that an image model paints over.
function bool ShowBlock(vector Size, int Colour)
{
	local vector S;

	if (!Show("Terran_DecoM.Crates.Crate1Low", 1.0))
		return false;
	S.X = Size.X / 262.0;
	S.Y = Size.Y / 266.0;
	S.Z = Size.Z / 259.0;
	SetDrawScale3D(S);
	Skins[0] = BlockTex[Clamp(Colour, 0, 3)];
	return true;
}

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
	BlockTex(0)=Texture'Block0'
	BlockTex(1)=Texture'Block1'
	BlockTex(2)=Texture'Block2'
	BlockTex(3)=Texture'Block3'
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
