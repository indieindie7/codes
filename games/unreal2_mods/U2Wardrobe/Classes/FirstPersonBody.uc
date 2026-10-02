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

// the head drawn invisible: black, added to the screen (adds nothing)
#exec TEXTURE IMPORT NAME=Black FILE=Textures\Black.tga GROUP=UI MIPS=OFF

var config float ForwardOffset;      // camera this far ahead of the head bone, horizontally
var config float UpOffset;           // and this far above it (the bone is at the base of the skull)
var config float Smoothing;          // how fast the camera height follows the head (per second)
var config float HeadMargin;          // the head kept this far behind the camera
var config float DownPush;            // looking down, the body goes back this much more (the head is right under the camera)
var config float DownStart, DownFull; // from this pitch down (degrees) to full DownPush at this one
var config bool bMoveCamera;
var config bool bPushBack;           // push the drawn body back so its head is behind the camera
var config byte HideSpace;           // MeshNodeSetScale space for HideNodes: 0 world, 1 mesh, 2 parent, 3 ref pose         // camera at the head bone instead of the game's eye point (misplaces the weapon)
var config bool bHideHead;            // outfits with their own head material: draw it invisible
var config int HeadSkin;              // that material's slot (UT2004 imports: 0 body, 1 head)
var config float HeadlessMargin;      // push-back when the head is hidden (only the neck to clear)
var config float HeadlessDownPush;    // and looking down, so the chest doesn't fill the view
var config array<string> HeadInBody;  // meshes whose head shares a material with the body (Dalton's)
var config array<string> HeadNodes;  // the head bone (first found is used for the camera)
var config array<string> HideNodes;  // bones shrunk away while shown (head, arms)

var Pawn Shown;                      // the character currently shown (bones shrunk)
var float CamZ;                      // eased camera height, relative to the character
var float LastTime;
var vector BasePre;                  // the character's own PrePivot (height fit etc.)
var vector Pushed;                   // the push-back currently applied on top of it
var float Back;                      // eased push-back distance
var FinalBlend Invisible;
var array<Material> SavedSkins;          // the character's own skins while its head is hidden
var bool bHeadHidden;

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
	if (HeadIsSeparate(P))
		HideHead(P);
	else
		ShowHead(P);
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

// can this character's head be hidden by its material?
function bool HeadIsSeparate(Pawn P)
{
	local int i;
	local string M;

	if (!bHideHead || P.Mesh == None)
		return false;
	M = string(P.Mesh);
	for (i = 0; i < HeadInBody.Length; i++)
		if (M ~= HeadInBody[i])
			return false;
	return true;
}

function HideHead(Pawn P)
{
	local int i;

	if (bHeadHidden)
		return;
	if (Invisible == None)
	{
		Invisible = new(None) class'FinalBlend';
		Invisible.Material = Texture'Black';
		Invisible.FrameBufferBlending = FB_Brighten;
		Invisible.ZWrite = false;
	}
	SavedSkins.Length = P.Skins.Length;
	for (i = 0; i < P.Skins.Length; i++)
		SavedSkins[i] = P.Skins[i];
	if (P.Skins.Length <= HeadSkin)
		P.Skins.Length = HeadSkin + 1;
	P.Skins[HeadSkin] = Invisible;
	bHeadHidden = true;
}

function ShowHead(Pawn P)
{
	local int i;

	if (!bHeadHidden)
		return;
	bHeadHidden = false;
	if (P == None || P.bDeleteMe)
		return;
	P.Skins.Length = SavedSkins.Length;
	for (i = 0; i < SavedSkins.Length; i++)
		P.Skins[i] = SavedSkins[i];
}

// how far down the player looks, as extra push-back: looking straight down the
// head is under the camera, inside the view (the beret filled the screen)
function float DownExtra(Pawn P)
{
	local int Pitch;
	local float Deg;

	if (P.Controller == None)
		return 0;
	Pitch = P.Controller.Rotation.Pitch & 65535;
	if (Pitch > 32768)
		Pitch -= 65536;
	Deg = -float(Pitch) * 360.0 / 65536.0;      // degrees below the horizon
	return DownPush * FClamp((Deg - DownStart) / FMax(1, DownFull - DownStart), 0, 1);
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
			if (bHeadHidden)
				Need = FMax(0, ((Head - Cam) dot Fwd) + HeadlessMargin + DownExtra(P) * HeadlessDownPush / FMax(1, DownPush));
			else
				Need = FMax(0, ((Head - Cam) dot Fwd) + HeadMargin + DownExtra(P));
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
	ShowHead(Shown);
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
	DownPush=18.000000
	bHideHead=True
	HeadSkin=1
	HeadlessMargin=0.000000
	HeadlessDownPush=14.000000
	HeadInBody(0)="GlmCharactersG.PlayerGame"
	HeadInBody(1)="GlmCharactersG.PlayerAtlantis"
	DownStart=25.000000
	DownFull=70.000000
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
