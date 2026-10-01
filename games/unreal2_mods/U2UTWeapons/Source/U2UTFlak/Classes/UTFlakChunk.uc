//=============================================================================
// UTFlakChunk - a flak chunk, ported from Unreal Tournament's UTChunk.
// Fired in a cluster by the primary fire (and released by the slug). Bounces
// off walls losing speed, drops with gravity after the first bounce, and
// visibly cools: its glow texture steps through 12 frames.
//=============================================================================
class UTFlakChunk extends Projectile;

#exec TEXTURE IMPORT NAME=Chunk_a00 FILE=Textures\Chunk_a00.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a01 FILE=Textures\Chunk_a01.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a02 FILE=Textures\Chunk_a02.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a03 FILE=Textures\Chunk_a03.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a04 FILE=Textures\Chunk_a04.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a05 FILE=Textures\Chunk_a05.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a06 FILE=Textures\Chunk_a06.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a07 FILE=Textures\Chunk_a07.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a08 FILE=Textures\Chunk_a08.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a09 FILE=Textures\Chunk_a09.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a10 FILE=Textures\Chunk_a10.tga GROUP=ChunkGlow LODSET=2
#exec TEXTURE IMPORT NAME=Chunk_a11 FILE=Textures\Chunk_a11.tga GROUP=ChunkGlow LODSET=2
#exec AUDIO IMPORT FILE=Sounds\ChunkHit.wav NAME=ChunkHit GROUP=Flak

var Texture AnimFrame[12];
var int Count;
var string MeshName;   // loaded by name on first spawn (see WeaponInvUTFlak.Frame)

simulated event PostBeginPlay()
{
	local rotator RandRot;

	Super.PostBeginPlay();
	if (MeshName != "")   // first call loads it, later ones just find it
		StaticMesh = StaticMesh(DynamicLoadObject(MeshName, class'StaticMesh'));
	SetTimer(0.1, true);
	Skins[0] = AnimFrame[0];
	RandRot = Rotation;
	RandRot.Pitch += FRand() * 2000 - 1000;
	RandRot.Yaw += FRand() * 2000 - 1000;
	RandRot.Roll += FRand() * 2000 - 1000;
	Velocity = Vector(RandRot) * (Speed + (FRand() * 200 - 100));
	if (PhysicsVolume.bWaterVolume)
		Velocity *= 0.65;
}

simulated function ProcessTouch(Actor Other, vector HitLocation)
{
	if (UTFlakChunk(Other) == None && (Physics == PHYS_Falling || Other != Instigator))
	{
		Speed = VSize(Velocity);
		if (Speed > 200)
		{
			if (Role == ROLE_Authority)
				Other.TakeDamage(Damage, Instigator, HitLocation, MomentumTransfer * Velocity / Speed, MyDamageType);
			if (FRand() < 0.5)
				PlaySound(Sound'ChunkHit', SLOT_None, 4.0, , 200);
		}
		Destroy();
	}
}

simulated event Destroyed()
{
	if (class'WeaponInvUTFlak'.default.bDebugLog)
		Log("U2UTFlak: "$Name$" gone after "$(default.LifeSpan - LifeSpan)$"s at "$Location$" speed="$VSize(Velocity)$" phys="$Physics$" skin="$Skins[0]);
	Super.Destroyed();
}

// the chunk cools down: step through the glow frames
simulated event Timer()
{
	Count++;
	Skins[0] = AnimFrame[Count];
	if (Count == 11)
		SetTimer(0.0, false);
}

simulated event Landed(vector HitNormal)
{
	SetPhysics(PHYS_None);
}

simulated event HitWall(vector HitNormal, actor Wall)
{
	if (Mover(Wall) != None && Mover(Wall).bDamageTriggered)
	{
		if (Level.NetMode != NM_Client)
			Wall.TakeDamage(Damage, Instigator, Location, MomentumTransfer * Normal(Velocity), MyDamageType);
		Destroy();
		return;
	}
	if (Physics != PHYS_Falling)
		SetPhysics(PHYS_Falling);
	// reflect off the wall with damping (UT's formula)
	Velocity = 0.8 * ((Velocity dot HitNormal) * HitNormal * (-1.8 + FRand() * 0.8) + Velocity);
	SetRotation(rotator(Velocity));
	Speed = VSize(Velocity);
	if (Speed > 100)
		MakeNoise(0.3);
}

defaultproperties
{
	AnimFrame(0)=Texture'Chunk_a00'
	AnimFrame(1)=Texture'Chunk_a01'
	AnimFrame(2)=Texture'Chunk_a02'
	AnimFrame(3)=Texture'Chunk_a03'
	AnimFrame(4)=Texture'Chunk_a04'
	AnimFrame(5)=Texture'Chunk_a05'
	AnimFrame(6)=Texture'Chunk_a06'
	AnimFrame(7)=Texture'Chunk_a07'
	AnimFrame(8)=Texture'Chunk_a08'
	AnimFrame(9)=Texture'Chunk_a09'
	AnimFrame(10)=Texture'Chunk_a10'
	AnimFrame(11)=Texture'Chunk_a11'
	Speed=2500.000000
	MaxSpeed=2700.000000
	Damage=16.000000
	MomentumTransfer=10000
	MyDamageType=Class'U2.DamageTypePhysical'
	LifeSpan=2.900000
	DrawType=DT_Mesh
	DrawScale=0.004000   // UT 0.4, meshes are exported 100x larger
	AmbientGlow=255
	bUnlit=True
	bBounce=True
	Physics=PHYS_Projectile
}
