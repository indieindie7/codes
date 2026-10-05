//=============================================================================
// Blood on a body: a small projector that paints characters only, placed just
// outside the body where it was hit and looking along the shot. It rides with
// the body: its place is kept in the body's own frame and set again as the
// body moves (a projector has to be re-attached to move its picture), often
// while the body lives, then a few more times as it falls, then it stays.
// Less exact than staining the skin itself (the stain does not follow the
// limbs), but it needs to know nothing about the body's materials.
//=============================================================================
class GoreBodyDecal extends Projector;

var Pawn Body;
var vector Offset;         // from the body's location, in the body's frame
var rotator Aim;           // the projector's rotation, relative to the body's yaw
var float Next;
var float DeadTime;        // seconds since the body died
var int BodyYaw;

// Projector attaches itself at spawn (before it has a texture or a place): not yet
simulated event PostBeginPlay()
{
}

// on P where a shot going Dir hit it at Spot; Size is the stain's width in world units
function Place(Texture Tex, Pawn P, vector Spot, vector Dir, float Size)
{
	local rotator R, Y;

	Body = P;
	ProjTexture = Tex;
	SetDrawScale(Size / 128.0);
	MaxTraceDistance = int(P.CollisionRadius * 2 + 30);
	R = rotator(Dir);
	R.Roll = Rand(65536);
	Y.Yaw = P.Rotation.Yaw;
	BodyYaw = Y.Yaw;
	// start outside the body, on the shooter's side
	Offset = ((Spot - Dir * (P.CollisionRadius + 12)) - P.Location) << Y;
	Aim = R;
	Aim.Yaw -= Y.Yaw;
	Follow();
}

function Follow()
{
	local rotator R, Y;

	Y.Yaw = Body.Rotation.Yaw;
	R = Aim;
	R.Yaw += Y.Yaw;
	SetLocation(Body.Location + (Offset >> Y));
	SetRotation(R);
	DetachProjector(true);
	AttachProjector();
}

event Tick(float DeltaTime)
{
	if (Body == None || Body.bDeleteMe)
	{
		Destroy();
		return;
	}
	if (Body.Health <= 0)
	{
		DeadTime += DeltaTime;
		if (DeadTime > 4)
		{
			Disable('Tick');       // it lies still: the stain stays where it is
			return;
		}
	}
	Next -= DeltaTime;
	if (Next > 0)
		return;
	Next = 0.05;
	Follow();
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
	MaxTraceDistance=80
	bProjectBSP=False
	bProjectTerrain=False
	bProjectStaticMesh=False
	bProjectActor=True
	bProjectParticles=False
	bClipBSP=False
	bClipStaticMesh=False
	bGradient=False
	bHidden=True
	bStatic=False
	RemoteRole=ROLE_None
	LifeSpan=240.000000
}
