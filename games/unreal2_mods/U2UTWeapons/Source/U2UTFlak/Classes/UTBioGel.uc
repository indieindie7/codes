//=============================================================================
// UTBioGel - Unreal Tournament's Bio Rifle gel (UT_BioGel): a lobbed glob of
// toxic goo that sticks to whatever it hits, then bursts after 3 seconds - or
// straight away when something walks into it. Fired by WeaponInvUTBio.
//
// Sizes follow UT's DrawScale (UTScale); the static meshes are exported 100x
// larger, so the actor's DrawScale is UTScale / 100.
//=============================================================================
class UTBioGel extends Projectile;

#exec TEXTURE IMPORT NAME=BioGreen FILE=Textures\BioGreen.tga GROUP=Skins LODSET=2
#exec AUDIO IMPORT FILE=Sounds\BioGelHit.wav    NAME=BioGelHit  GROUP=Bio
#exec AUDIO IMPORT FILE=Sounds\BioExplg02.wav   NAME=BioExplode GROUP=Bio

var float UTScale;        // UT's DrawScale for this gel (2 = a normal shot)
var vector SurfaceNormal;
var bool bOnGround;
var float ExplodeAt;

simulated function SetUTScale(float S)
{
	UTScale = S;
	SetDrawScale(S / 100.0);
}

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = StaticMesh(DynamicLoadObject("U2UTFlakSM.Bio.BioGelFly", class'StaticMesh'));
	SetUTScale(UTScale);
	Velocity = Vector(Rotation) * Speed;
	Velocity.Z += 120;                       // UT's lob
	if (PhysicsVolume.bWaterVolume)
		Velocity *= 0.7;
	RandSpin(100000);
	ExplodeAt = Level.TimeSeconds + 3.0;     // bursts 3s after firing, stuck or not
}

// burst: radius damage scaled by size, like UT
simulated function Burst()
{
	PlaySound(Sound'BioExplode', SLOT_None, 3.0 * UTScale / 2.0);
	if (Role == ROLE_Authority)
	{
		if (Mover(Base) != None && Mover(Base).bDamageTriggered)
			Base.TakeDamage(Damage, Instigator, Location, MomentumTransfer * Normal(Velocity), MyDamageType);
		HurtRadius(Damage * UTScale, FMin(250, UTScale * 75), MyDamageType, MomentumTransfer * UTScale, Location + SurfaceNormal * 8);
	}
	Destroy();
}

simulated event Tick(float DeltaTime)
{
	if (ExplodeAt > 0 && Level.TimeSeconds >= ExplodeAt)
	{
		ExplodeAt = 0;
		Burst();
	}
}

simulated function ProcessTouch(Actor Other, vector HitLocation)
{
	if (UTBioGel(Other) != None)
		return;
	if (Other != Instigator || bOnGround)
		Burst();
}

// stick to the surface as a splat facing out of it
simulated event HitWall(vector HitNormal, actor Wall)
{
	local rotator R;

	if (bOnGround)
		return;
	SetPhysics(PHYS_None);
	MakeNoise(0.3);
	bOnGround = true;
	PlaySound(Sound'BioGelHit');
	SurfaceNormal = HitNormal;
	StaticMesh = StaticMesh(DynamicLoadObject("U2UTFlakSM.Bio.BioGelStuck", class'StaticMesh'));
	bFixedRotationDir = false;
	RotationRate = rot(0, 0, 0);
	R = rotator(HitNormal);
	R.Roll += 32768;
	SetRotation(R);
	if (Mover(Wall) != None)
		SetBase(Wall);
	Landed2();
}

function Landed2();   // hook for UTBioGlob

simulated event Landed(vector HitNormal)
{
	HitWall(HitNormal, None);
}

defaultproperties
{
	UTScale=2.000000
	Speed=840.000000
	MaxSpeed=1500.000000
	Damage=20.000000
	MomentumTransfer=20000
	MyDamageType=Class'U2.DamageTypeBiological'
	LifeSpan=12.000000
	DrawType=DT_StaticMesh
	Skins(0)=Texture'BioGreen'
	Style=STY_Translucent
	bUnlit=True
	AmbientGlow=255
	CollisionRadius=2.000000
	CollisionHeight=2.000000
	bBounce=True
	Physics=PHYS_Falling
	bFixedRotationDir=True
}
