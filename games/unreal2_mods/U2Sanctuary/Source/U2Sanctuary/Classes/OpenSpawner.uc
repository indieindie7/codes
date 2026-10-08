//=============================================================================
// OpenSpawner - a reinforcement you can see (the open-map pacing research:
// waves need a visible cause, and the player should be able to answer it):
//
//  HIVE  an Acheron alien pod at a spawn-shed door: the Izarians of the
//        encounter crawl out of it. Shoot it and that door is shut.
//  DROP  a drop pod falling on a Skaarj wave's door, lit red on the way down.
//        Shot down in the air, its Skaarj never arrive; landed, it opens and
//        stays as cover.
//  SHIP  the Marines' dropship coming down on the pad at the end of the hold
//        (cannot be hurt).
// Spawned and told what to do by OpenDirector.
//=============================================================================
class OpenSpawner extends Actor;

var OpenDirector Director;
var name Kind;               // 'Hive', 'Drop', 'Ship'
var int Health;
var int Wave;                // DROP: the wave whose pawns it carries
var string Cargo;            // DROP: "Class:n"
var string Encounter;        // HIVE: the encounter it belongs to
var vector LandAt;
var float FallSpeed;
var bool bFalling, bDead;

function Fall(vector Target, float Height, float Speed)
{
	LandAt = Target;
	FallSpeed = Speed;
	bFalling = true;
	SetCollision(true, false, false);
	SetLocation(Target + vect(0,0,1) * Height);
	if (Kind == 'Drop')
	{
		bDynamicLight = true;
		LightType = LT_Pulse;
		LightHue = 10;
		LightSaturation = 40;
		LightBrightness = 255;
		LightRadius = 24;
		LightPeriod = 24;
	}
}

event Tick(float DT)
{
	local vector V;

	if (!bFalling)
		return;
	V = Location;
	V.Z -= FallSpeed * DT;
	if (V.Z <= LandAt.Z)
	{
		bFalling = false;
		SetLocation(LandAt);
		SetCollision(true, true, true);
		bDynamicLight = false;
		LightType = LT_None;
		if (Director != None)
			Director.PodLanded(Self);
		return;
	}
	SetLocation(V);
}

function TakeDamage(int Damage, Pawn EventInstigator, vector HitLocation, vector Momentum, class<DamageType> DamageType)
{
	if (bDead || Kind == 'Ship' || Damage <= 0)
		return;
	// the Izarians don't shoot their own hive
	if (EventInstigator != None && !EventInstigator.IsHumanControlled() && Kind == 'Hive')
		return;
	Health -= Damage;
	if (Health <= 0)
		Burst();
}

function Burst()
{
	local class<Actor> FX;

	bDead = true;
	if (Director != None)
	{
		FX = class<Actor>(DynamicLoadObject(Director.BurstFX, class'Class', true));
		if (FX != None)
			Spawn(FX,,, Location + vect(0,0,60));
		Director.PodBurst(Self);
	}
	Destroy();
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bCollideActors=True
	bBlockActors=True
	bBlockPlayers=True
	bProjTarget=True
	bBlockZeroExtentTraces=True
	bBlockNonZeroExtentTraces=True
	bCollideWorld=False
	CollisionRadius=90.000000
	CollisionHeight=110.000000
	Health=300
	RemoteRole=ROLE_None
}
