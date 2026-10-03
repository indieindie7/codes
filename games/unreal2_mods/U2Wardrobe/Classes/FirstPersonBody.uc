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
var config bool bHandsHoldGun;           // only the gun in the character's hands, no separate first-person gun
var Inventory ShrunkWeapon;               // the weapon whose first-person gun is hidden
var config float StairEase;               // stairs: how fast body and camera catch up with a step (per second)
var config float StairMax;                // the most a step snap is eased over (units)
var float Stair;                          // the height still being eased over (drawn lower/higher than the pawn)
var vector LastLoc;                       // the pawn's location last frame (step snaps)
var config bool bStairLog;                // log each step snap (testing)
var config bool bGunWithCamera;
var config bool bLowerArms;               // in first person the body's arms hold the gun lowered (the animation
                                          // agent's WeaponState locked to AmbientLowered), so the stock aiming
                                          // pose's forearms never cross the view; the first-person gun is shown
var bool bArmsLowered;
var config bool bGunEyeHeight;            // holding a gun: the camera is the game's eye point (the gun stays in place)           // move the first-person gun along with the head camera (WeaponKickOffset)
// leg sync: the leg clip (the agent's AnimAll channel) plays at the rate that keeps the planted foot
// still for your actual speed. Stock clips play at one fixed rate (feet slid: running ~30% too slow,
// backpedalling ~95%, crouch-walking 2.3x). Stride = the clip's planted-foot speed per unit of channel
// rate at DrawScale 1, measured with "hub legs" (U2TestHub); clips not listed keep the stock rate.
struct LegClip
{
	var string Clip;
	var float Stride;
};
var config bool bLegSync;
var config array<LegClip> LegClips;
var config float LegMinScale, LegMaxScale;   // limits, as a multiple of the clip's stock rate
var config bool bLegLog;
var name LegSeq;                              // clip on the leg channel last tick
var float LegStock;                           // the rate the agent gave it
var float LegStride;                          // its stride (0: not listed)
var float LegLogClock;

var config bool bSightCamera;             // holding a gun: the camera behind and above the gun hand (cheek on
                                          // the stock), so the character's own aiming pose shows the gun in
                                          // its hands; the stock pose's forearms no longer cross the view
var config string SightNode;              // the weapon mount node (Unreal II skeletons: handpointR02)
var config float SightBack, SightUp, SightSide; // camera offset from it along the view: back, up, right
var config float SightSmoothing;          // how fast the camera follows the hand (per second; it bobs with the anims)
var config bool bSightLog;                // log the hand and camera (tuning)
var float SightMix;                       // 0 head camera .. 1 sight camera (eased on weapon changes)
var vector SightRel;                      // eased sight camera, relative to the pawn

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
		Stair = 0;
		LastLoc = P.Location;
	}
	if (HeadIsSeparate(P))
		HideHead(P);
	else
		ShowHead(P);
	LowerArms(P, bLowerArms && !bHandsHoldGun);
	if (P.PrePivot != BasePre + Pushed)
		BasePre = P.PrePivot - Pushed;      // someone else (outfit height fit) changed it
	DT = FClamp(Level.TimeSeconds - LastTime, 0, 0.1);
	EaseStairs(P, DT);
	Cam = GameCamera;
	SetLocation(Cam);
	if (!bMoveCamera)
	{
		if (bPushBack)
			PushBack(P, Cam);
		else
			ApplyPush(P);
		return Cam;
	}
	Yaw.Yaw = P.Rotation.Yaw;
	Fwd = vector(Yaw);
	for (i = 0; i < HeadNodes.Length; i++)
	{
		N = P.MeshGetNodeNamed(HeadNodes[i]);
		if (N != 0)
		{
			// where the head would be without our offsets (look-down push and stair easing, as
			// drawn last frame); the camera then rides the stair easing with the body
			Head = P.MeshNodeGetTranslation(N, MESHNODEREL_World) - Pushed;
			Cam.X = Head.X;
			Cam.Y = Head.Y;
			Want = Head.Z + UpOffset - P.Location.Z;
			CamZ += (Want - CamZ) * FMin(1.0, DT * Smoothing);
			Cam.Z = P.Location.Z + CamZ + Stair;
			break;
		}
	}
	// looking down, the drawn body slides back from under the camera: the run cycle's knees
	// came right up into the view (they looked like the back of a head)
	Back += (DownExtra(P) - Back) * FMin(1.0, DT * Smoothing);
	Cam += Fwd * ForwardOffset;
	Cam = SightCamera(P, Cam, DT);
	// holding a gun: the camera is the game's own eye point, which the first-person gun is drawn
	// from. Tested: the gun ignores WeaponKickOffset, so with the camera at the head bone (lower,
	// and ahead of the eye as the aiming pose leans when looking down) the gun sat too high
	// looking ahead and dropped and tilted looking down. The body is still drawn around it.
	if (bGunEyeHeight && P.Weapon != None)
	{
		Cam = GameCamera;
		Cam.Z += Stair;
	}
	LastTime = Level.TimeSeconds;
	Pushed = -Fwd * Back;
	ApplyPush(P);
	SetLocation(Cam);
	return Cam;
}

// bSightCamera: holding a gun, the camera moves from the head to just behind and above the gun
// hand, along the view, and back to the head when the gun is put away
function vector SightCamera(Pawn P, vector HeadCam, float DT)
{
	local int N;
	local vector Hand, X, Y, Z, Want;
	local bool bGun;

	N = 0;
	bGun = bSightCamera && P.Weapon != None && P.Controller != None;
	if (bGun)
		N = P.MeshGetNodeNamed(SightNode);
	if (N != 0)
	{
		Hand = P.MeshNodeGetTranslation(N, MESHNODEREL_World) - Pushed;
		GetAxes(P.Controller.Rotation, X, Y, Z);
		Want = Hand - X * SightBack + Z * SightUp + Y * SightSide - P.Location;
		if (SightMix <= 0)
			SightRel = Want;
		SightRel += (Want - SightRel) * FMin(1.0, DT * SightSmoothing);
		SightMix = FMin(1, SightMix + DT * 4);
		if (bSightLog)
			Log("FPBody: hand" @ (Hand - P.Location) @ "camera" @ SightRel @ "head" @ (HeadCam - P.Location));
	}
	else
		SightMix = FMax(0, SightMix - DT * 4);
	if (SightMix <= 0)
		return HeadCam;
	return HeadCam + (P.Location + SightRel - HeadCam) * SightMix;
}

// stairs: walking up (or down) a step snaps the pawn's height at once, and the body and camera
// jumped with it. The jump is taken back from the drawn body and eased out over a moment, so
// body and camera glide over the step while collision stays exact. Slopes change height
// steadily with forward movement and are left alone.
function EaseStairs(Pawn P, float DT)
{
	local float DZ, Flat;
	local vector Move;

	Move = P.Location - LastLoc;
	LastLoc = P.Location;
	DZ = Move.Z;
	Move.Z = 0;
	Flat = VSize(Move);
	if (bStairLog && Abs(DZ) > 0.5)
		Log("FPBody: dz" @ DZ @ "flat" @ Flat @ "physics" @ GetEnum(enum'EPhysics', P.Physics) @ "at" @ P.Location);
	if (P.Physics == PHYS_Walking && Flat > 0.3 && Abs(DZ) > 2 && Abs(DZ) > Flat * 1.2 && Abs(DZ) < 60)
	{
		Stair = FClamp(Stair - DZ, -StairMax, StairMax);
		if (bStairLog)
			Log("FPBody: step" @ DZ @ "flat" @ Flat @ "-> easing" @ Stair);
	}
	Stair -= Stair * FMin(1.0, DT * StairEase);
	if (Abs(Stair) < 0.05)
		Stair = 0;
}

// the drawn body's offset from the pawn: look-down push plus the stair easing
function ApplyPush(Pawn P)
{
	Pushed.Z = Stair;
	P.PrePivot = BasePre + Pushed;
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
	ApplyPush(P);
}

// bone scales don't stick when set while the frame is drawn: set them every tick
event Tick(float DeltaTime)
{
	if (Shown != None && !Shown.bDeleteMe)
	{
		SetNodes(Shown, true);
		ShrinkGun(Shown);
		if (bLegSync)
			LegSync(Shown, DeltaTime);
	}
}

function float FindStride(name Seq)
{
	local string S;
	local int i;
	S = string(Seq);
	if (Right(S, 5) ~= "_Hurt")
		S = Left(S, Len(S) - 5);
	for (i = 0; i < LegClips.Length; i++)
		if (LegClips[i].Clip ~= S)
			return LegClips[i].Stride;
	return 0;
}

function LegSync(Pawn P, float DT)
{
	local name Seq;
	local float Frame, Rate, Blend, Want, Speed;
	local vector Flat;

	P.GetAnimParams(0, Seq, Frame, Rate, Blend);
	if (Seq != LegSeq)
	{
		LegSeq = Seq;              // the agent just started this clip: its rate is the stock one
		LegStock = Rate;
		LegStride = FindStride(Seq) * P.DrawScale;
	}
	if (LegStride <= 0 || LegStock <= 0 || P.Physics != PHYS_Walking)
		return;
	Flat = P.Velocity;
	Flat.Z = 0;
	Speed = VSize(Flat);
	Want = FClamp(Speed / LegStride, LegStock * LegMinScale, LegStock * LegMaxScale);
	P.AnimRate = Want;
	if (bLegLog)
	{
		LegLogClock += DT;
		if (LegLogClock >= 0.5)
		{
			LegLogClock = 0;
			Log("FirstPersonBody: legs "$Seq$" speed "$int(Speed)$" stock "$LegStock$" -> "$Want);
		}
	}
}

// back to the agent's own rate for the clip playing
function LegRestore(Pawn P)
{
	local name Seq;
	local float Frame, Rate, Blend;
	if (P == None || P.bDeleteMe || LegSeq == '')
		return;
	P.GetAnimParams(0, Seq, Frame, Rate, Blend);
	if (Seq == LegSeq && LegStock > 0)
		P.AnimRate = LegStock;
	LegSeq = '';
}

// bHandsHoldGun: the character's hands hold the gun. Unreal II draws the held (third-person)
// gun from the weapon's ThirdPersonMesh, which can't be hidden (None crashes the shadow code,
// ThirdPersonScale isn't used), so the separate first-person gun is the one hidden: shrunk to
// nothing through its DrawScale, given back from the class default (a save can't keep it)
function ShrinkGun(Pawn P)
{
	local Inventory W;

	if (!bHandsHoldGun)
		return;
	if (P != None)
		W = P.Weapon;
	if (W != ShrunkWeapon)
	{
		RestoreGun();
		ShrunkWeapon = W;
	}
	if (W != None && W.DrawScale != 0.0001)
		W.SetDrawScale(0.0001);
}

function RestoreGun()
{
	if (ShrunkWeapon != None && !ShrunkWeapon.bDeleteMe)
		ShrunkWeapon.SetDrawScale(ShrunkWeapon.default.DrawScale);
	ShrunkWeapon = None;
}

// lock (or free) the animation agent's WeaponState input at AmbientLowered: the game's own
// animation controller can't change it while it is locked
function LowerArms(Pawn P, bool bOn)
{
	if (P == None || bOn == bArmsLowered)
		return;
	bArmsLowered = bOn;
	P.MeshAgentSetInputLock('WeaponState', false);
	if (bOn)
	{
		P.MeshAgentSetInputCurValue('WeaponState', 'AmbientLowered');
		P.MeshAgentSetInputLock('WeaponState', true);
	}
	else
		P.MeshAgentSetInputCurValue('WeaponState', 'Ambient');
}

function Hide()
{
	if (Shown != None && !Shown.bDeleteMe)
	{
		LowerArms(Shown, false);
		LegRestore(Shown);
	}
	ShowHead(Shown);
	RestoreGun();
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
	bHandsHoldGun=False
	StairEase=10.000000
	bSightCamera=False
	bGunWithCamera=True
	bGunEyeHeight=True
	bLowerArms=True
	bLegSync=True
	LegMinScale=0.400000
	LegMaxScale=2.500000
	LegClips(0)=(Clip="A_S_RunFrwd",Stride=164.9)
	LegClips(1)=(Clip="A_S_RunBack",Stride=126.2)
	LegClips(2)=(Clip="A_S_RunLeft",Stride=190.5)
	LegClips(3)=(Clip="A_S_RunRght",Stride=213.7)
	LegClips(4)=(Clip="A_S_WalkFrwd",Stride=87.4)
	LegClips(5)=(Clip="A_S_WalkBack",Stride=90.0)
	LegClips(6)=(Clip="A_S_WalkLeft",Stride=88.3)
	LegClips(7)=(Clip="A_S_WalkRght",Stride=89.8)
	LegClips(8)=(Clip="A_D_WalkFrwd",Stride=31.4)
	LegClips(9)=(Clip="A_D_WalkBack",Stride=36.0)
	SightNode="handpointR02"
	SightBack=26.000000
	SightUp=9.000000
	SightSide=-3.000000
	SightSmoothing=14.000000
	StairMax=40.000000
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
