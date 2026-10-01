//=============================================================================
// FirstPersonBody - see your own body in first person, like modern shooters.
//
// The engine never draws the actor the camera views from, so in first person
// the player's character is invisible. This actor becomes that view instead:
// it sits at the character's eyes - taken from the head bone, so it follows the
// animation (the aiming pose leans the head forward of the game's eye point) -
// a little ahead of the face, and turns with the player's aim. The character is
// drawn - legs, body and arms when you look down - and its own head stays behind
// the camera. The first-person weapon is still drawn by the controller.
//
// Only in plain first person: third person, cutscene cameras and anything
// else that takes the view are left alone.
//=============================================================================
class FirstPersonBody extends Actor config(U2Wardrobe);

var config float ForwardOffset;     // camera this far ahead of the head bone (keeps the face behind it)
var config float UpOffset;          // and this far above it (the head bone sits at the base of the skull)
var config array<string> HeadNodes; // the head bone's name (first found is used)

var PlayerController PC;
var Pawn Body;                      // the character being shown (and whose head is hidden)
var bool bActive;

function Start(PlayerController InPC)
{
	PC = InPC;
	Enable('Tick');
}

// where the eyes are: the head bone in world space, or the game's eye point
function vector EyeLocation(Pawn P)
{
	local int i, N;

	for (i = 0; i < HeadNodes.Length; i++)
	{
		N = P.MeshGetNodeNamed(HeadNodes[i]);
		if (N != 0)
			return P.MeshNodeGetTranslation(N, MESHNODEREL_World) + vect(0,0,1) * UpOffset;
	}
	return P.Location + P.EyePosition();
}

// shrink the head away (or give it back), so the camera at the eyes isn't inside it
function SetHead(Pawn P, bool bHide)
{
	local int i, N;
	local vector S;

	if (P == None || P.Mesh == None)
		return;
	S = vect(1,1,1);
	if (bHide)
		S = vect(0.02,0.02,0.02);
	for (i = 0; i < HeadNodes.Length; i++)
	{
		N = P.MeshGetNodeNamed(HeadNodes[i]);
		if (N != 0)
		{
			P.MeshNodeSetScale(N, S, MESHNODEREL_ParentNode);
			return;
		}
	}
}

function Release()
{
	if (Body != None)
		SetHead(Body, false);
	if (bActive && PC != None && PC.ViewTarget == Self)
		PC.SetViewTarget(PC.Pawn);
	bActive = false;
	Body = None;
}

event Tick(float DeltaTime)
{
	local vector Eye, Fwd;
	local rotator Yaw;

	if (PC == None || PC.bDeleteMe)
	{
		Destroy();
		return;
	}
	// a new character (respawn, level change, outfit) or a dead one: start over
	if (Body != None && (Body != PC.Pawn || Body.bDeleteMe || Body.Health <= 0))
		Release();
	if (PC.Pawn == None || PC.Pawn.Health <= 0 || PC.bBehindView)
	{
		Release();
		return;
	}
	// someone else has the view (a cutscene camera, a turret, a vehicle): stay out of it
	if (PC.ViewTarget != PC.Pawn && PC.ViewTarget != Self)
	{
		Release();
		return;
	}

	Body = PC.Pawn;
	Eye = EyeLocation(Body);
	Yaw.Yaw = PC.Rotation.Yaw;
	Fwd = vector(Yaw);
	SetLocation(Eye + Fwd * ForwardOffset);
	SetRotation(PC.Rotation);
	SetHead(Body, true);
	if (PC.ViewTarget != Self)
		PC.SetViewTarget(Self);
	bActive = true;
}

event Destroyed()
{
	Release();
	Super.Destroyed();
}

defaultproperties
{
	ForwardOffset=3.000000
	UpOffset=6.000000
	HeadNodes(0)="Merc Head"
	HeadNodes(1)="Bip01 Head"
	bHidden=True
	RemoteRole=ROLE_None
	Physics=PHYS_None
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
}
