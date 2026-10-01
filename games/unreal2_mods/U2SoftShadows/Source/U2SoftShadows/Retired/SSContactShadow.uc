//=============================================================================
// Contact shadow: a soft dark patch on the floor right under a character,
// which grounds it wherever the lights are. A fixed soft round texture
// projected straight down and multiplied onto the floor (like a decal), so
// nothing is rendered per frame. It fades out as the character leaves the
// floor (the projector's gradient runs from the feet down).
//=============================================================================
#exec TEXTURE IMPORT NAME=ContactBlob FILE=Textures\ContactBlob.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=ContactBlob50 FILE=Textures\ContactBlob50.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=ContactBlob25 FILE=Textures\ContactBlob25.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

class SSContactShadow extends Projector;

var float SizeScale;     // patch width relative to the character's collision diameter
var bool bShown;
var vector LastSpot;
var float MaxLift;         // hidden once the feet are this high above the floor
var int LiftStep;          // 0 on the floor, 1 lifting, 2 high, 3 hidden

function Show(bool bNewShown)
{
	bShown = bNewShown;
	if (!bShown)
		DetachProjector(true);
	else
		LastSpot = vect(0,0,0);   // re-attach on the next tick
}

event Tick(float DeltaTime)
{
	local Pawn P;
	local vector Spot, Feet, HitLoc, HitNorm;
	local float Lift;
	local int Step;

	P = Pawn(Owner);
	if (P == None || P.bDeleteMe)
	{
		DetachProjector(true);
		Destroy();
		return;
	}
	if (!bShown)
		return;

	// how far the feet are off the floor: the patch lightens and spreads as
	// the character lifts (a jump), and goes once it is well clear
	Feet = P.Location;
	Feet.Z -= P.CollisionHeight;
	if (Trace(HitLoc, HitNorm, Feet - vect(0,0,1) * MaxLift, Feet + vect(0,0,8), false) != None)
		Lift = FMax(0, Feet.Z - HitLoc.Z);
	else
		Lift = MaxLift;
	if (Lift < MaxLift * 0.15)      Step = 0;
	else if (Lift < MaxLift * 0.45) Step = 1;
	else if (Lift < MaxLift)        Step = 2;
	else                            Step = 3;
	if (Step != LiftStep)
	{
		LiftStep = Step;
		if (Step == 0)      ProjTexture = Texture'ContactBlob';
		else if (Step == 1) ProjTexture = Texture'ContactBlob50';
		else if (Step == 2) ProjTexture = Texture'ContactBlob25';
		LastSpot = vect(0,0,0);         // re-attach with the new texture
	}
	if (Step == 3)
	{
		DetachProjector(true);
		LastSpot = vect(0,0,0);
		return;
	}

	// sit just above the floor under the feet, reach a little below it
	Spot = P.Location;
	Spot.Z = Feet.Z - Lift + 24;
	MaxTraceDistance = 48;
	SetDrawScale(P.CollisionRadius * 2.0 * SizeScale * (1.0 + Lift / MaxLift) / 128.0);

	// re-project only when the character has moved a little
	if (VSize(Spot - LastSpot) > 1.0)
	{
		DetachProjector(true);
		SetLocation(Spot);
		AttachProjector();
		LastSpot = Spot;
	}
}

event Destroyed()
{
	DetachProjector(true);
	Super.Destroyed();
}

defaultproperties
{
	ProjTexture=Texture'ContactBlob'
	MaterialBlendingOp=PB_None
	FrameBufferBlendingOp=PB_Modulate
	FOV=1
	SizeScale=2.200000
	MaxLift=90.000000
	bProjectBSP=True
	bProjectTerrain=True
	bProjectStaticMesh=True
	bProjectActor=False
	bProjectParticles=False
	bClipBSP=True
	bClipStaticMesh=True
	bGradient=False
	GradientTexture=Texture'Engine.GRADIENT_Fade'
	Rotation=(Pitch=-16384)
	bHidden=True
	bStatic=False
	RemoteRole=ROLE_None
}
