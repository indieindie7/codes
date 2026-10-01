//=============================================================================
// UTFlakSlug - the flak alt-fire shell, ported from Unreal Tournament's
// flakslug: lobbed with an upward kick, explodes on impact for radius damage
// and releases a burst of flak chunks. Built on Unreal II's fragment grenade so
// it gets the native explosion effect, sound and scorch decal.
//=============================================================================
class UTFlakSlug extends projectileGrenadeFragment;

#exec MESH IMPORT MESH=flakslugm ANIVFILE=Models\flakslugm_a.3d DATAFILE=Models\flakslugm_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=flakslugm X=0 Y=0 Z=0 YAW=128 PITCH=64
#exec MESH SEQUENCE MESH=flakslugm SEQ=All STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH=flakslugm SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec TEXTURE IMPORT NAME=Jflakslugel1 FILE=Textures\Jflakslugel1.tga GROUP=Skins LODSET=2
#exec MESHMAP SCALE MESHMAP=flakslugm X=0.019 Y=0.019 Z=0.038
#exec MESHMAP SETTEXTURE MESHMAP=flakslugm NUM=1 TEXTURE=Jflakslugel1

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	Velocity = Vector(Rotation) * Speed;
	Velocity.Z += 200;   // UT's lob
}

// explode on anything: players, walls, floor (no bouncing like a grenade)
simulated function ProcessTouch(Actor Other, vector HitLocation)
{
	if (Other != Instigator && UTFlakChunk(Other) == None)
		Explode(HitLocation, Normal(HitLocation - Other.Location));
}

simulated event HitWall(vector HitNormal, actor Wall)
{
	Explode(Location, HitNormal);
}

simulated event Landed(vector HitNormal)
{
	Explode(Location, HitNormal);
}

simulated function ExplodeEx(CheckResult Hit)
{
	local vector Start;

	if (Role == ROLE_Authority)
	{
		Start = Location + 10 * Hit.Normal;
		Spawn(class'UTFlakChunk2',,, Start);
		Spawn(class'UTFlakChunk3',,, Start);
		Spawn(class'UTFlakChunk4',,, Start);
		Spawn(class'UTFlakChunk1',,, Start);
		Spawn(class'UTFlakChunk2',,, Start);
	}
	Super.ExplodeEx(Hit);
}

defaultproperties
{
	Speed=1200.000000
	MaxSpeed=1200.000000
	Damage=70.000000
	DamageRadius=150.000000
	MomentumTransfer=75000
	MyDamageType=Class'U2.DamageTypeThermalExplosiveRound'
	Physics=PHYS_Falling
	bBounce=False
	LifeSpan=6.000000
	DrawType=DT_Mesh
	Mesh=VertMesh'flakslugm'
	StaticMesh=None
	DrawScale=1.000000
	AmbientGlow=67
}
