//=============================================================================
// One blood mark on a wall or floor: a projector pointed into the surface that
// multiplies it 2x (PB_Modulate), so the textures are 50% grey where there is
// no blood. Ported from AdventMod's ModBloodDecal; the projector settings are
// U2Grime's GrimeSpot, which are known to work in Unreal II.
// GoreManager spawns them, caps how many there are and grows the pools.
// Characters are never painted (bProjectActor off).
//=============================================================================
#exec TEXTURE IMPORT NAME=BloodSplat0 FILE=Textures\BloodSplat0.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodSplat1 FILE=Textures\BloodSplat1.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodSplat2 FILE=Textures\BloodSplat2.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodSplat3 FILE=Textures\BloodSplat3.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodSpray0 FILE=Textures\BloodSpray0.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodSpray1 FILE=Textures\BloodSpray1.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodPool0 FILE=Textures\BloodPool0.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorSplat0 FILE=Textures\IchorSplat0.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorSplat1 FILE=Textures\IchorSplat1.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorSplat2 FILE=Textures\IchorSplat2.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorSplat3 FILE=Textures\IchorSplat3.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorSpray0 FILE=Textures\IchorSpray0.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorSpray1 FILE=Textures\IchorSpray1.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=IchorPool0 FILE=Textures\IchorPool0.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

class GoreDecal extends Projector;

var float GrowFrom, GrowTo, GrowTime, GrowAge;   // a pool spreading out (GrowTime 0 = no growth)

// Projector attaches itself at spawn (before it has a texture or a place): not yet
simulated event PostBeginPlay()
{
}

// on the surface at Spot with normal N, the texture's +X along Along (a spray's direction);
// Size is the mark's width in world units
function Place(Texture Tex, vector Spot, vector N, vector Along, float Size)
{
	local rotator R;
	local vector X, Y, Z, A;

	ProjTexture = Tex;
	SetDrawScale(Size / 128.0);
	SetLocation(Spot + N * 16);
	// the projector looks along its X axis: into the surface; its Y axis is the texture's
	// +X, turned to the shot's direction across the surface (or anywhere, for a round splat)
	R = rotator(-N);
	GetAxes(R, X, Y, Z);
	if (VSize(Along) > 0.1)
	{
		// (this engine's Atan takes one number: a rotator's yaw is the two-number one)
		A.X = Along Dot Y;
		A.Y = Along Dot -Z;
		R.Roll = rotator(A).Yaw;
	}
	else
		R.Roll = Rand(65536);
	SetRotation(R);
	DetachProjector(true);
	AttachProjector();
}

// a pool: from width From to width To over Seconds
function Grow(float From, float To, float Seconds)
{
	GrowFrom = From / 128.0;
	GrowTo = To / 128.0;
	GrowTime = Seconds;
	GrowAge = 0;
	SetDrawScale(GrowFrom);
	DetachProjector(true);
	AttachProjector();
}

event Tick(float DeltaTime)
{
	local float T;

	if (GrowTime <= 0)
		return;
	GrowAge += DeltaTime;
	// re-projecting costs a little: a few steps a second is smooth enough for a pool
	if (GrowAge < GrowTime && int(GrowAge * 6) == int((GrowAge - DeltaTime) * 6))
		return;
	T = FMin(GrowAge / GrowTime, 1);
	T = 1 - (1 - T) * (1 - T);     // fast at first, settling
	SetDrawScale(GrowFrom + (GrowTo - GrowFrom) * T);
	DetachProjector(true);
	AttachProjector();
	if (GrowAge >= GrowTime)
		GrowTime = 0;
}

event Destroyed()
{
	DetachProjector(true);
	Super.Destroyed();
}

defaultproperties
{
	ProjTexture=Texture'BloodSplat0'
	MaterialBlendingOp=PB_None
	FrameBufferBlendingOp=PB_Modulate
	FOV=1
	MaxTraceDistance=40
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
	LifeSpan=180.000000
}
