//=============================================================================
// One patch of dust: a soft texture projected straight down and multiplied onto
// the floor (PB_Modulate is twice the texture, so its mid-grey border leaves the
// floor unchanged). Nothing is rendered per frame beyond the projected polygons.
// Stage 0 is the strongest look; walking over the patch steps it lighter, and
// past the last stage it is gone (see GrimeManager.Scuff).
//=============================================================================
#exec TEXTURE IMPORT NAME=Dust00 FILE=Textures\Dust00.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Dust01 FILE=Textures\Dust01.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Dust02 FILE=Textures\Dust02.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Dust10 FILE=Textures\Dust10.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Dust11 FILE=Textures\Dust11.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Dust12 FILE=Textures\Dust12.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

class GrimeSpot extends Projector;

var Texture Looks[6];        // shape * 3 + stage
var int Shape;               // 0 clumpy, 1 gritty
var int Stage;               // 0 strongest .. 2 faintest, 3 = walked away
var float Size;              // width on the floor, world units
var float Score;             // how dusty this spot should be (0-1), from GrimeManager
var float Wear;              // walking over it adds to this; each whole step = one level lighter
var vector Foot;             // the floor point at the wall's foot
var vector WallNormal;       // horizontal, pointing out of the wall into the room
var float Lift;              // projector height above the floor

function Place(vector NewFoot, vector NewWall, float NewScore, float NewSize, int NewStage)
{
	local rotator R;

	Foot = NewFoot;
	WallNormal = NewWall;
	Score = NewScore;
	Size = NewSize;
	Stage = NewStage;
	Shape = Rand(2);
	R.Pitch = -16384;
	R.Yaw = Rand(65536);
	SetRotation(R);
	SetLocation(Foot + vect(0,0,1) * Lift);
	MaxTraceDistance = int(Lift + 16);
	Show(true);
}

function Show(bool bShow)
{
	DetachProjector(true);
	if (!bShow || Stage > 2)
		return;
	ProjTexture = Looks[Shape * 3 + Stage];
	SetDrawScale(Size / 128.0);
	AttachProjector();
}

// one more step of wear: lighter, or gone after the faintest stage
function Step(bool bShown)
{
	Stage++;
	Show(bShown);
}

event Destroyed()
{
	DetachProjector(true);
	Super.Destroyed();
}

defaultproperties
{
	Looks(0)=Texture'Dust00'
	Looks(1)=Texture'Dust01'
	Looks(2)=Texture'Dust02'
	Looks(3)=Texture'Dust10'
	Looks(4)=Texture'Dust11'
	Looks(5)=Texture'Dust12'
	ProjTexture=Texture'Dust00'
	MaterialBlendingOp=PB_None
	FrameBufferBlendingOp=PB_Modulate
	FOV=1
	Lift=24.000000
	MaxTraceDistance=40
	bProjectBSP=True
	bProjectTerrain=False
	bProjectStaticMesh=True
	bProjectActor=False
	bProjectParticles=False
	bClipBSP=True
	bClipStaticMesh=True
	bGradient=False
	Rotation=(Pitch=-16384)
	bHidden=True
	bStatic=False
	RemoteRole=ROLE_None
}
