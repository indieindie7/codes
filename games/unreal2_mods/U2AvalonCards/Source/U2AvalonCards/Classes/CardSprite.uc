//=============================================================================
// An imposter card: a camera-facing sprite that shows one of NumFrames
// pictures of an object baked from around it (tools\bake_cards.py), the one
// taken from the side the camera is on now. Frame k was baked with the
// camera at k*360/NumFrames degrees round the object, clockwise seen from
// above (the way Unreal's yaw turns), starting in front (the card's yaw).
// One frame = a plain billboard (trees).
//=============================================================================
#exec TEXTURE IMPORT NAME=Trees0 FILE=Textures\Trees0.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Trees1 FILE=Textures\Trees1.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Trees2 FILE=Textures\Trees2.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig0 FILE=Textures\Rig0.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig1 FILE=Textures\Rig1.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig2 FILE=Textures\Rig2.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig3 FILE=Textures\Rig3.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig4 FILE=Textures\Rig4.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig5 FILE=Textures\Rig5.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig6 FILE=Textures\Rig6.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Rig7 FILE=Textures\Rig7.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

class CardSprite extends Actor;

var Texture Frames[16];
var int NumFrames;
var int Shown;

// Size = the card's height in world units (the pictures are square)
function SetSize(float Size)
{
	if (Frames[0] != None)
		SetDrawScale(Size / Frames[0].VSize);
	Shown = -1;
	Texture = Frames[0];
	Tick(0);
}

function vector Eye()
{
	local Controller C;

	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
		{
			if (C.Pawn != None)
				return C.Pawn.Location + vect(0,0,1) * C.Pawn.EyeHeight;
			return C.Location;
		}
	return Location;
}

event Tick(float DeltaTime)
{
	local vector D;
	local int Rel, k;

	if (NumFrames <= 1)
		return;
	D = Eye() - Location;
	Rel = (rotator(D).Yaw - Rotation.Yaw) & 65535;
	k = int(float(Rel) * NumFrames / 65536.0 + 0.5) % NumFrames;
	if (k != Shown)
	{
		Shown = k;
		Texture = Frames[k];
	}
}

defaultproperties
{
	DrawType=DT_Sprite
	Style=STY_Alpha
	bUnlit=True
	bStatic=False
	bNoDelete=False
	bHidden=False
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	bAlwaysRelevant=True
	Physics=PHYS_None
	RemoteRole=ROLE_None
	NumFrames=1
}
