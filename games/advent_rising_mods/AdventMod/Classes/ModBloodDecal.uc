//=============================================================================
// ModBloodDecal - one blood mark on a wall or floor: an orthographic projector
// (FOV 0: its size is the texture's times DrawScale) pointed into the surface.
// It multiplies the surface 2x (UE2's projector modulate; its alpha-blend path
// falls through into that and came out pink): the textures are 50% grey where
// there's no blood.
// ModGore spawns them, caps how many there are, and grows the pools under the
// dead. Characters are never painted (bProjectActor off).
//=============================================================================
class ModBloodDecal extends Projector;

var float GrowFrom, GrowTo, GrowTime, GrowAge;   // a pool spreading out (GrowTime 0 = no growth)

// Projector attaches itself at spawn (before it has a texture or a place): not yet
simulated event PostBeginPlay()
{
}

// on the surface at Spot with normal N, the texture's +X along Along (a spray's direction)
function Place(Material Tex, vector Spot, vector N, vector Along, float Size)
{
	local rotator R;
	local vector X, Y, Z;

	ProjTexture = Tex;
	SetDrawScale(Size);
	SetLocation(Spot + N * 16);
	// the projector looks along its X axis: into the surface; its Y axis is the texture's
	// +X, turned to the shot's direction across the surface (or anywhere, for a round splat)
	R = rotator(-N);
	GetAxes(R, X, Y, Z);
	if (VSize(Along) > 0.1)
		R.Roll = int(Atan(Along Dot -Z, Along Dot Y) * 32768.0 / Pi);
	else
		R.Roll = Rand(65536);
	SetRotation(R);
	DetachProjector(true);
	AttachProjector();
}

// a pool: from Size*From to Size*To over Seconds
function Grow(float From, float To, float Seconds)
{
	GrowFrom = From;
	GrowTo = To;
	GrowTime = Seconds;
	GrowAge = 0;
	SetDrawScale(From);
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

defaultproperties
{
     FrameBufferBlendingOp=PB_Modulate
     FOV=0
     MaxTraceDistance=40
     bProjectActor=False
     bProjectParticles=False
     bClipBSP=True
     bClipStaticMesh=True
     bProjectOnParallelBSP=True
     bStatic=False
     bLevelStatic=False
     bNoDelete=False
     bHidden=True
     LifeSpan=180.000000
}
