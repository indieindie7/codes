//=============================================================================
// FirstPersonBody - see your own body in first person, like modern shooters.
//
// A hidden helper that BodyController hands to the renderer as the "view
// actor", so the player's character is drawn in first person (the engine never
// draws the view actor itself). While shown, the character's head and arms are
// shrunk away (every tick: the head would fill the screen, the arms would double
// the first-person weapon's). The camera stays the game's own (eye height, walk
// bob, smoothing): the first-person weapon is placed relative to it, so moving
// the camera put the gun in the wrong place. Instead the drawn body is pushed
// back (PrePivot, drawing only: collision and camera stay) just enough that its
// animated head is behind the camera - the aiming pose leans it forward of the
// game's eye point. Bone shrinking (HideNodes) doesn't take effect on these
// meshes; it is kept in case a model honours it.
//=============================================================================
class FirstPersonBody extends Actor config(U2Wardrobe);

var config float ForwardOffset;      // camera this far ahead of the head bone, horizontally
var config float UpOffset;           // and this far above it (the bone is at the base of the skull)
var config float Smoothing;          // how fast the camera height follows the head (per second)
var config float HeadMargin;          // the head kept this far behind the camera
var config bool bMoveCamera;
var config bool bPushBack;           // push the drawn body back so its head is behind the camera
var config byte HideSpace;           // MeshNodeSetScale space for HideNodes: 0 world, 1 mesh, 2 parent, 3 ref pose         // camera at the head bone instead of the game's eye point (misplaces the weapon)
var config array<string> HeadNodes;  // the head bone (first found is used for the camera)
var config array<string> HideNodes;  // bones shrunk away while shown (head, arms)

var Pawn Shown;                      // the character currently shown (bones shrunk)
var float CamZ;                      // eased camera height, relative to the character
var float LastTime;
var vector BasePre;                  // the character's own PrePivot (height fit etc.)
var vector Pushed;                   // the push-back currently applied on top of it
var float Back;                      // eased push-back distance

function SetNodes(Pawn P, bool bHide)
{
	local int i, N;
	local vector S;

	if (P == None || P.Mesh == None)
		return;
	S = vect(1,1,1);
	if (bHide)
		S = vect(0.02,0.02,0.02);
	for (i = 0; i < HideNodes.Length; i++)
	{
		N = P.MeshGetNodeNamed(HideNodes[i]);
		if (N != 0)
		{
			if (HideSpace == 0)      P.MeshNodeSetScale(N, S, MESHNODEREL_World);
			else if (HideSpace == 1) P.MeshNodeSetScale(N, S, MESHNODEREL_Mesh);
			else if (HideSpace == 3) P.MeshNodeSetScale(N, S, MESHNODEREL_RefPose);
			else                     P.MeshNodeSetScale(N, S, MESHNODEREL_ParentNode);
		}
	}
}

// the camera for this frame: at the head bone (eased in height), a little ahead
function vector Show(Pawn P, vector GameCamera)
{
	local int i, N;
	local vector Head, Cam, Fwd;
	local rotator Yaw;
	local float DT, Want;

	if (Shown != P)
	{
		Hide();
		Shown = P;
		CamZ = GameCamera.Z - P.Location.Z;
		LastTime = Level.TimeSeconds;
		BasePre = P.PrePivot;
		Pushed = vect(0,0,0);
		Back = 0;
	}
	if (P.PrePivot != BasePre + Pushed)
		BasePre = P.PrePivot - Pushed;      // someone else (outfit height fit) changed it
	Cam = GameCamera;
	SetLocation(Cam);
	if (!bMoveCamera)
	{
		if (bPushBack)
			PushBack(P, Cam);
		return Cam;
	}
	for (i = 0; i < HeadNodes.Length; i++)
	{
		N = P.MeshGetNodeNamed(HeadNodes[i]);
		if (N != 0)
		{
			Head = P.MeshNodeGetTranslation(N, MESHNODEREL_World);
			Cam.X = Head.X;
			Cam.Y = Head.Y;
			Want = Head.Z + UpOffset - P.Location.Z;
			DT = FClamp(Level.TimeSeconds - LastTime, 0, 0.1);
			CamZ += (Want - CamZ) * FMin(1.0, DT * Smoothing);
			Cam.Z = P.Location.Z + CamZ;
			break;
		}
	}
	LastTime = Level.TimeSeconds;
	Yaw.Yaw = P.Rotation.Yaw;
	Fwd = vector(Yaw);
	Cam += Fwd * ForwardOffset;
	SetLocation(Cam);
	return Cam;
}

// push the drawn body back until its head is HeadMargin behind the camera
function PushBack(Pawn P, vector Cam)
{
	local int i, N;
	local vector Head, Fwd;
	local rotator Yaw;
	local float Need, DT;

	Yaw.Yaw = P.Rotation.Yaw;
	Fwd = vector(Yaw);
	for (i = 0; i < HeadNodes.Length; i++)
	{
		N = P.MeshGetNodeNamed(HeadNodes[i]);
		if (N != 0)
		{
			Head = P.MeshNodeGetTranslation(N, MESHNODEREL_World) - Pushed;   // where it would be unpushed
			Need = FMax(0, ((Head - Cam) dot Fwd) + HeadMargin);
			DT = FClamp(Level.TimeSeconds - LastTime, 0, 0.1);
			Back += (Need - Back) * FMin(1.0, DT * Smoothing);
			break;
		}
	}
	LastTime = Level.TimeSeconds;
	Pushed = -Fwd * Back;
	P.PrePivot = BasePre + Pushed;
}

// bone scales don't stick when set while the frame is drawn: set them every tick
event Tick(float DeltaTime)
{
	if (Shown != None && !Shown.bDeleteMe)
		SetNodes(Shown, true);
}

function Hide()
{
	if (Shown != None && !Shown.bDeleteMe)
	{
		SetNodes(Shown, false);
		if (Shown.PrePivot == BasePre + Pushed)
			Shown.PrePivot = BasePre;
	}
	Pushed = vect(0,0,0);
	Shown = None;
}

event Destroyed()
{
	Hide();
	Super.Destroyed();
}

defaultproperties
{
	ForwardOffset=4.000000
	UpOffset=6.000000
	Smoothing=12.000000
	bMoveCamera=False
	HeadMargin=10.000000
	bPushBack=True
	HideSpace=2
	HeadNodes(0)="Merc Head"
	HeadNodes(1)="Bip01 Head"
	HideNodes(0)="Merc Head"
	HideNodes(1)="Merc L UpperArm"
	HideNodes(2)="Merc R UpperArm"
	HideNodes(3)="Bip01 Head"
	HideNodes(4)="Bip01 L UpperArm"
	HideNodes(5)="Bip01 R UpperArm"
	bHidden=True
	RemoteRole=ROLE_None
	Physics=PHYS_None
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
}
