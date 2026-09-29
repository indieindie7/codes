//=============================================================================
// UTRazorDisc - Unreal Tournament's Ripper blade (Razor2): a spinning razor
// disc that ricochets off walls up to 6 times and does 3.5x damage on a
// head-height hit. Fired by the Ripper's alt fire (WeaponInvUTRipper).
//=============================================================================
class UTRazorDisc extends Projectile;

#exec TEXTURE IMPORT NAME=RazSkin FILE=Textures\RazSkin.tga GROUP=Skins LODSET=2
#exec AUDIO IMPORT FILE=Sounds\StartBlade.wav NAME=StartBlade GROUP=Ripper
#exec AUDIO IMPORT FILE=Sounds\BladeHit.wav   NAME=BladeHit   GROUP=Ripper
#exec AUDIO IMPORT FILE=Sounds\BladeThunk.wav NAME=BladeThunk GROUP=Ripper
#exec AUDIO IMPORT FILE=Sounds\RazorHum.wav   NAME=RazorHum   GROUP=Ripper

var int NumWallHits;
var bool bCanHitInstigator;

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = StaticMesh(DynamicLoadObject("U2UTFlakSM.Ripper.RipBlade", class'StaticMesh'));
	Velocity = Vector(Rotation) * Speed;   // forward only, like UT
	SetTimer(0.2, false);
	SoundPitch = 200 + 50 * FRand();
	if (class'WeaponInvUTFlak'.default.bDebugLog)
		Log("U2UTFlak: disc spawned at "$Location$" vel="$Velocity$" instigator="$Instigator);
}

simulated event Destroyed()
{
	if (class'WeaponInvUTFlak'.default.bDebugLog)
		Log("U2UTFlak: disc gone after "$(default.LifeSpan - LifeSpan)$"s at "$Location$" bounces="$NumWallHits);
	Super.Destroyed();
}

// after a moment (or the first bounce) the disc can cut its thrower too
simulated event Timer()
{
	bCanHitInstigator = true;
}

simulated function ProcessTouch(Actor Other, vector HitLocation)
{
	if (UTRazorDisc(Other) != None || (Other == Instigator && !bCanHitInstigator))
		return;
	if (Role == ROLE_Authority)
	{
		if (Pawn(Other) != None && HitLocation.Z - Other.Location.Z > 0.62 * Other.CollisionHeight)
			Other.TakeDamage(3.5 * Damage, Instigator, HitLocation, MomentumTransfer * Normal(Velocity), MyDamageType);   // head: decapitated
		else
			Other.TakeDamage(Damage, Instigator, HitLocation, MomentumTransfer * Normal(Velocity), MyDamageType);
	}
	if (Pawn(Other) != None)
		PlaySound(Sound'BladeThunk', SLOT_Misc, 2.0);
	else
		PlaySound(Sound'BladeHit', SLOT_Misc, 2.0);
	Destroy();
}

simulated event HitWall(vector HitNormal, actor Wall)
{
	local vector Vel2D, Norm2D;

	bCanHitInstigator = true;
	PlaySound(Sound'BladeHit', SLOT_Misc, 2.0);
	if (Mover(Wall) != None && Mover(Wall).bDamageTriggered)
	{
		if (Role == ROLE_Authority)
			Wall.TakeDamage(Damage, Instigator, Location, MomentumTransfer * Normal(Velocity), MyDamageType);
		Destroy();
		return;
	}
	NumWallHits++;
	SetTimer(0, false);
	MakeNoise(0.3);
	if (NumWallHits > 6)
	{
		Destroy();
		return;
	}
	if (NumWallHits == 1)
	{
		// straight into a wall: nudge the bounce so it doesn't come right back (UT)
		Vel2D = Velocity;
		Vel2D.Z = 0;
		Norm2D = HitNormal;
		Norm2D.Z = 0;
		Norm2D = Normal(Norm2D);
		Vel2D = Normal(Vel2D);
		if ((Vel2D dot Norm2D) < -0.999)
		{
			HitNormal = Normal(HitNormal + 0.6 * Vel2D);
			Norm2D = HitNormal;
			Norm2D.Z = 0;
			Norm2D = Normal(Norm2D);
			if ((Vel2D dot Norm2D) < -0.999)
				HitNormal = Normal(HitNormal + vect(0.05, 0.05, 0));
		}
	}
	Velocity -= 2 * (Velocity dot HitNormal) * HitNormal;
	SetRotation(rotator(Velocity));
}

defaultproperties
{
	Speed=1300.000000
	MaxSpeed=1300.000000
	Damage=30.000000
	MomentumTransfer=15000
	MyDamageType=Class'U2.DamageTypePhysical'
	LifeSpan=6.000000
	DrawType=DT_StaticMesh
	Skins(0)=Texture'RazSkin'
	DrawScale=0.010000   // UT 1.0, meshes are exported 100x larger
	bUnlit=True
	AmbientGlow=167
	AmbientSound=Sound'RazorHum'
	SoundRadius=12
	SoundVolume=255
	SoundPitch=200
	bBounce=True
	Physics=PHYS_Projectile
	bFixedRotationDir=True
	RotationRate=(Yaw=300000)   // spin (UT played a spin animation)
}
