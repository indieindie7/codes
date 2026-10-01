//=============================================================================
// Capsule shadow: one limb's shadow as a soft oval on the floor. The limb is
// the segment between two skeleton nodes (Unreal II's Golem mesh API gives
// their world positions); both ends are projected along the light direction
// onto the floor and a soft oval (fixed texture, no rendering) is laid over
// the result, so the shadow is always soft and costs no silhouette pass.
//=============================================================================
#exec TEXTURE IMPORT NAME=Oval1 FILE=Textures\Oval1.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Oval2 FILE=Textures\Oval2.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Oval3 FILE=Textures\Oval3.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=Oval4 FILE=Textures\Oval4.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

class SSCapsuleShadow extends Projector;

var string NodeA, NodeB;   // the limb's two skeleton nodes
var float Radius;          // limb thickness (world units)
var bool bShown;

function Show(bool bNew)
{
	bShown = bNew;
	if (!bShown)
		DetachProjector(true);
}

// where a point lands on the floor when pushed along the light direction
function vector OnFloor(vector P, vector LightDir, float FloorZ)
{
	local float T;

	if (LightDir.Z > -0.2)
		LightDir.Z = -0.2;              // never flatter than ~12 degrees: the shadow stays finite
	T = (P.Z - FloorZ) / -LightDir.Z;
	return P + LightDir * T;
}

function Update(Pawn P, vector LightDir, float FloorZ)
{
	local int NA, NB;
	local vector A, B, FA, FB, Mid, D;
	local float Len, Aspect;
	local rotator R;

	if (!bShown)
		return;
	NA = P.MeshGetNodeNamed(NodeA);
	NB = P.MeshGetNodeNamed(NodeB);
	if (NA == 0 || NB == 0)
		return;
	A = P.MeshNodeGetTranslation(NA);
	B = P.MeshNodeGetTranslation(NB);
	FA = OnFloor(A, LightDir, FloorZ);
	FB = OnFloor(B, LightDir, FloorZ);
	D = FB - FA;
	D.Z = 0;
	Len = VSize(D);
	Mid = (FA + FB) * 0.5;
	Mid.Z = FloorZ + 24;                // hover above the floor, project 48 down

	// pick the oval whose shape matches the projected limb
	Aspect = (Len + 2 * Radius) / (2 * Radius);
	if (Aspect < 1.5)      ProjTexture = Texture'Oval1';
	else if (Aspect < 2.5) ProjTexture = Texture'Oval2';
	else if (Aspect < 3.5) ProjTexture = Texture'Oval3';
	else                   ProjTexture = Texture'Oval4';

	R.Pitch = -16384;
	if (Len > 1)
		R.Yaw = Rotator(D).Yaw;
	R.Roll = 0;
	DetachProjector(true);
	SetLocation(Mid);
	SetRotation(R);
	// the oval's long axis spans the texture width: fit it to the limb
	SetDrawScale((Len + 2 * Radius) / 128.0);
	MaxTraceDistance = 48;
	AttachProjector();
}

event Destroyed()
{
	DetachProjector(true);
	Super.Destroyed();
}

defaultproperties
{
	ProjTexture=Texture'Oval2'
	MaterialBlendingOp=PB_None
	FrameBufferBlendingOp=PB_Modulate
	FOV=1
	bProjectBSP=True
	bProjectTerrain=True
	bProjectStaticMesh=True
	bProjectActor=False
	bProjectParticles=False
	bClipBSP=True
	bClipStaticMesh=True
	bGradient=False
	bHidden=True
	bStatic=False
	RemoteRole=ROLE_None
}
