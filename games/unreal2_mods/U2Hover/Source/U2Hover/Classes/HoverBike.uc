//=============================================================================
// HoverBike - a drivable hover bike for Unreal II, wearing XVehicles' Manta
// (github.com/SeriousBuggie/XVehicles, CC0). The hover model follows
// XVehicles' HoverCraftPhys: three repulsors trace down to the ground and a
// spring keeps the bike at its hover height; the bike turns to where you look.
//
// Unreal II's engine still has Epic's KVehicle driving support: using the bike
// (Use key, looking at it) puts the player's controller in state PlayerDriving,
// which feeds Throttle/Steering (move keys) and draws the chase camera from
// CamPos. Jump gets out (PlayerDriving's own rule); Alt Fire hops.
//
// Physics is done here in Tick with MoveSmooth, not Karma.
//=============================================================================
class HoverBike extends KVehicle
	placeable;

#exec TEXTURE IMPORT NAME=MantaAtlas FILE=Textures\MantaAtlas.tga GROUP=Skins LODSET=2
#exec AUDIO IMPORT FILE=Sounds\HoverEngine.wav NAME=HoverEngine GROUP=Manta
#exec AUDIO IMPORT FILE=Sounds\HoverJump.wav NAME=HoverJump GROUP=Manta

var() float MaxSpeed;          // top horizontal speed
var() float AccelRate;         // horizontal acceleration while a move key is held
var() float TurnRate;          // yaw units per second while turning to the view
var() float HoverHeight;       // repulsor trace length
var() float HoverGap;          // rest height = HoverHeight - HoverGap
var() float SpringK, SpringDamp;
var() float JumpSpeed;
var() vector Repulsor[3];      // bike-space repulsor points (front, left, right)

var Pawn   DriverPawn;
var int    VehicleYaw;
var bool   bOnGround;
var vector FloorNormal;
var float  LastJumpTime;
var float  NextDebugLog;
var float  NoBoardUntil;

var() class<Projectile> GunProjectile;
var() float  FireInterval;      // seconds between shots (the guns alternate)
var() vector GunOffset;         // bike-space muzzle; Y is mirrored for the other gun
var float  NextShotTime;
var int    GunSide;
var() bool bDebug;
var() string BodyMesh;          // static mesh to wear, loaded at spawn (subclasses swap the look)
var() string BodySkin;          // optional texture for Skins[0], loaded at spawn

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = StaticMesh(DynamicLoadObject(BodyMesh, class'StaticMesh'));
	if (BodySkin != "")
		Skins[0] = Material(DynamicLoadObject(BodySkin, class'Material'));
	VehicleYaw = Rotation.Yaw;
	FloorNormal = vect(0,0,1);
	SetPhysics(PHYS_None);
}

// --- getting in and out ---

function bool IsUsable( optional Actor Other )
{
	return !bIsDriven && !bDeleteMe;
}

function TryToDrive(Pawn Driver)
{
	if (bDebug)
		log("HoverBike: TryToDrive" @ Driver @ "controller" @ Driver.Controller @ "isPlayer" @ Driver.Controller.bIsPlayer
			@ "human" @ Driver.IsHumanControlled() @ "state" @ Driver.Controller.GetStateName());
	Super.TryToDrive(Driver);
}

function OnUse( Actor Other )
{
	local Controller C;
	C = Controller(Other);
	if (bDebug)
		log("HoverBike: OnUse by" @ Other);
	if (C != None && C.Pawn != None)
		TryToDrive(C.Pawn);
}

// walking into the bike also gets you on (not right after getting off)
event Bump( Actor Other )
{
	local Pawn P;
	P = Pawn(Other);
	if (P != None && !bIsDriven && P.IsHumanControlled() && Level.TimeSeconds > NoBoardUntil)
		TryToDrive(P);
}

event KDriverEnter( Pawn Driver )
{
	DriverPawn = Driver;
	Driver.SetCollision(false, false, false);
	Driver.bCollideWorld = false;
	Driver.SetPhysics(PHYS_None);
	Driver.bHidden = true;
	Driver.Velocity = vect(0,0,0);
	// the rider's own gun stays quiet while the bike's guns use the fire button
	if (U2Weapon(Driver.Weapon) != None)
		U2Weapon(Driver.Weapon).bDisableFiring = true;
	VehicleYaw = Rotation.Yaw;
	AmbientSound = Sound'HoverEngine';
}

event KDriverLeave( Pawn Driver )
{
	local vector X, Y, Z, Spot;
	local float Side;
	local int i;

	// step off to the left, right, behind or on top: the first spot in clear
	// line from the bike that the driver fits in (never into a wall)
	GetAxes(rot(0,1,0) * VehicleYaw, X, Y, Z);
	Side = CollisionRadius + Driver.CollisionRadius + 20;
	for (i = 0; i < 4; i++)
	{
		switch (i)
		{
		case 0: Spot = Location - Y * Side; break;
		case 1: Spot = Location + Y * Side; break;
		case 2: Spot = Location - X * Side; break;
		case 3: Spot = Location + vect(0,0,1) * (CollisionHeight + Driver.CollisionHeight + 10); break;
		}
		Spot.Z += 40;
		if (FastTrace(Spot, Location) && Driver.SetLocation(Spot))
			break;
	}
	Driver.bHidden = false;
	if (U2Weapon(Driver.Weapon) != None)
		U2Weapon(Driver.Weapon).bDisableFiring = false;
	Driver.bCollideWorld = true;
	Driver.SetCollision(true, true, true);
	Driver.SetPhysics(PHYS_Falling);
	Driver.Velocity = Velocity;
	DriverPawn = None;
	NoBoardUntil = Level.TimeSeconds + 2.0;
	Throttle = 0;
	Steering = 0;
	AmbientSound = None;
	Super.KDriverLeave(Driver);
}

// --- the guns ---

// Fire is read straight from the controller: PlayerDriving ignores the Fire
// command itself. Shots go where the camera looks: find what's under the
// crosshair, then aim both muzzles at it.
function FireGun(Controller C)
{
	local vector Muzzle, AimFrom, AimAt, HL, HN, X, Y, Z;
	local rotator R;
	local Projectile P;

	NextShotTime = Level.TimeSeconds + FireInterval;
	GunSide = 1 - GunSide;

	R = C.Rotation;
	AimFrom = Location + vect(0,0,1) * 130;
	AimAt = AimFrom + vector(R) * 12000;
	if (Trace(HL, HN, AimAt, AimFrom, true) != None)
		AimAt = HL;

	GetAxes(Rotation, X, Y, Z);
	Muzzle = Location + X * GunOffset.X + Y * GunOffset.Y * (GunSide * 2 - 1) + Z * GunOffset.Z;
	if (!FastTrace(Muzzle, Location))
		Muzzle = Location + Z * GunOffset.Z;

	// the rider owns the bolt: the Skaarj projectile plays its fire sound
	// through its owner pawn
	P = Spawn(GunProjectile, DriverPawn, , Muzzle, rotator(AimAt - Muzzle));
	if (P == None)
		return;
	P.Instigator = DriverPawn;
	P.Velocity = Normal(AimAt - Muzzle) * P.Speed + Velocity;
	if (bDebug)
		log("HoverBike: fire yaw" @ R.Yaw @ "pitch" @ R.Pitch @ "at" @ AimAt);
}

// --- hovering ---

// trace each repulsor down; sets bOnGround / FloorNormal, returns the
// average ground distance under the repulsors
function float CheckGround()
{
	local int i, hits;
	local vector Start, End, HL, HN, P[3];
	local rotator YawOnly;
	local float Dist, Sum;

	YawOnly.Yaw = Rotation.Yaw;
	bOnGround = false;
	for (i = 0; i < 3; i++)
	{
		Start = Location + (Repulsor[i] >> YawOnly);
		End = Start - vect(0,0,1) * HoverHeight;
		P[i] = End;
		if (Trace(HL, HN, End, Start, true, vect(0,0,0), , TRACE_World) != None && HN.Z >= 0.7)
		{
			bOnGround = true;
			P[i] = HL;
			hits++;
			Sum += Start.Z - HL.Z;
		}
		else
			Sum += HoverHeight;
	}
	if (!bOnGround)
	{
		FloorNormal = vect(0,0,1);
		return HoverHeight;
	}
	FloorNormal = Normal((P[1] - P[0]) cross (P[2] - P[0]));
	if (FloorNormal.Z < 0)
		FloorNormal = -FloorNormal;
	if (FloorNormal.Z < 0.5)
		FloorNormal = vect(0,0,1);
	return Sum / 3;
}

// yaw plus the pitch/roll that lays the bike along the ground
function rotator GroundRotation()
{
	local vector F, R;
	local rotator Rot;

	F = vector(rot(0,1,0) * VehicleYaw);
	R = vect(0,0,1) cross F;
	Rot.Yaw = VehicleYaw;
	Rot.Pitch = int(Atan(-(FloorNormal dot F) / FloorNormal.Z) * 10430.378);
	Rot.Roll = int(Atan((FloorNormal dot R) / FloorNormal.Z) * 10430.378);
	return Rot;
}

function int TurnTowards(int Current, int Desired, int MaxStep)
{
	local int Diff;
	Diff = (Desired - Current) & 65535;
	if (Diff > 32768)
		Diff -= 65536;
	if (Diff > MaxStep) Diff = MaxStep;
	else if (Diff < -MaxStep) Diff = -MaxStep;
	return (Current + Diff) & 65535;
}

event Tick(float Delta)
{
	local vector X, Y, Z, Dir, Flat;
	local float Height, Err, Speed;
	local Controller C;

	Delta = FMin(Delta, 0.05);

	Height = CheckGround();

	// the spring holds the hover height; gravity takes over off the ground
	Velocity.Z += PhysicsVolume.Gravity.Z * Delta;
	if (bOnGround && Level.TimeSeconds - LastJumpTime > 0.4)
	{
		Err = (HoverHeight - HoverGap) - Height;
		Velocity.Z += (Err * SpringK - Velocity.Z * SpringDamp) * Delta;
	}

	if (DriverPawn != None)
		C = DriverPawn.Controller;

	if (C != None)
	{
		VehicleYaw = TurnTowards(VehicleYaw, C.Rotation.Yaw, int(TurnRate * Delta));
		if (C.bAltFire != 0 && bOnGround && Level.TimeSeconds - LastJumpTime > 1.0)
		{
			LastJumpTime = Level.TimeSeconds;
			Velocity.Z += JumpSpeed;
			PlaySound(Sound'HoverJump', SLOT_None, 1.5);
		}
		if (C.bFire != 0 && Level.TimeSeconds >= NextShotTime)
			FireGun(C);
	}

	GetAxes(rot(0,1,0) * VehicleYaw, X, Y, Z);
	Dir = X * Throttle - Y * Steering;
	if (VSize(Dir) > 0.01)
		Velocity += Normal(Dir) * AccelRate * Delta;

	// brake along the bike when no throttle, kill sideways slide when not strafing
	if (Abs(Throttle) < 0.01)
		Velocity -= X * (X dot Velocity) * FMin(1, 1.2 * Delta);
	if (Abs(Steering) < 0.01)
		Velocity -= Y * (Y dot Velocity) * FMin(1, 4 * Delta);

	Flat = Velocity;
	Flat.Z = 0;
	Speed = VSize(Flat);
	if (Speed > MaxSpeed)
	{
		Flat *= MaxSpeed / Speed;
		Velocity.X = Flat.X;
		Velocity.Y = Flat.Y;
	}

	if (!MoveSmooth(Velocity * Delta) && Velocity.Z < 0)
		Velocity.Z = 0;   // resting on something: don't build up speed into it
	SetRotation(GroundRotation());

	if (DriverPawn != None)
		DriverPawn.SetLocation(Location + vect(0,0,1) * 40);
	SoundPitch = 56 + int(40 * FMin(1, Speed / MaxSpeed));

	if (bDebug && Level.TimeSeconds > NextDebugLog)
	{
		NextDebugLog = Level.TimeSeconds + 0.5;
		log("HoverBike: z" @ int(Location.Z) @ "h" @ int(Height) @ "ground" @ bOnGround @ "n" @ FloorNormal
			@ "vel" @ Velocity @ "thr" @ Throttle @ "str" @ Steering @ "driver" @ DriverPawn);
	}
}

defaultproperties
{
	MaxSpeed=2500.000000
	AccelRate=2200.000000
	TurnRate=40000.000000
	HoverHeight=160.000000
	HoverGap=50.000000
	SpringK=60.000000
	SpringDamp=9.000000
	JumpSpeed=730.000000
	GunProjectile=Class'HoverPlasma'
	FireInterval=0.160000
	GunOffset=(X=110.000000,Y=55.000000,Z=5.000000)
	Repulsor(0)=(X=95.000000,Z=-7.000000)
	Repulsor(1)=(X=-10.000000,Y=80.000000,Z=-7.000000)
	Repulsor(2)=(X=-10.000000,Y=-80.000000,Z=-7.000000)
	CamPos(0)=(X=0.000000,Y=0.000000,Z=90.000000,W=0.000000)
	CamPos(1)=(X=0.000000,Y=0.000000,Z=110.000000,W=400.000000)
	CamPos(2)=(X=0.000000,Y=0.000000,Z=130.000000,W=560.000000)
	CamPos(3)=(X=0.000000,Y=0.000000,Z=160.000000,W=800.000000)
	CamPosIndex=2
	Physics=PHYS_None
	DrawType=DT_StaticMesh
	DrawScale=0.010000
	Skins(0)=Texture'MantaAtlas'
	CollisionRadius=92.000000
	CollisionHeight=46.000000
	bCollideActors=True
	bBlockActors=True
	bBlockPlayers=True
	bBlockZeroExtentTraces=True
	bBlockNonZeroExtentTraces=True
	bCollideWorld=True
	bProjTarget=True
	bDirectional=True
	SoundRadius=160.000000
	SoundVolume=220
	SoundPitch=64
	RemoteRole=ROLE_None
	bDebug=False
	BodyMesh="U2HoverSM.Manta.MantaBody"
}
