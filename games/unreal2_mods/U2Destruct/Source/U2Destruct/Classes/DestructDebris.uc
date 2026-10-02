//=============================================================================
// DestructDebris - a broken-off chunk: a prop's mesh that is thrown, falls, bounces off the
// world, spins and comes to rest. Unreal II switched rigid-body Karma off ("physKarma: This
// physics type is obsolete in U2 829"), so this is the classic way: PHYS_Falling for gravity,
// bBounce so hitting the world calls HitWall, and the bounce worked out here.
//=============================================================================
class DestructDebris extends Actor;

var() float Bounciness;      // how much speed is kept along the bounce (0-1)
var() float Friction;        // how much sliding speed is kept on each bounce (0-1)
var() float RestSpeed;       // below this speed after a bounce it settles
var int Bounces;

// mesh and size, and the throw
function Launch(StaticMesh M, float Scale, vector Throw)
{
	StaticMesh = M;
	SetDrawType(DT_StaticMesh);
	SetDrawScale(Scale);
	Velocity = Throw;
	RotationRate = RotRand(true);
	SetPhysics(PHYS_Falling);
}

event HitWall(vector HitNormal, Actor Wall)
{
	local vector Along, Across;

	Bounces++;
	// split the speed into into-the-surface and along-it, bounce the first, slow the second
	Across = HitNormal * (Velocity dot HitNormal);
	Along = Velocity - Across;
	Velocity = Along * Friction - Across * Bounciness;
	RotationRate = RotationRate * Bounciness;
	if (VSize(Velocity) < RestSpeed && HitNormal.Z > 0.7)
		Settle();
}

event Landed(vector HitNormal)
{
	HitWall(HitNormal, None);
}

function Settle()
{
	SetPhysics(PHYS_None);
	Velocity = vect(0,0,0);
	RotationRate = rot(0,0,0);
	bBounce = False;
}

defaultproperties
{
	DrawType=DT_StaticMesh
	Physics=PHYS_None
	bBounce=True
	bFixedRotationDir=True
	bRotateToDesired=False
	bCollideWorld=True
	bCollideActors=False
	bBlockActors=False
	bBlockPlayers=False
	CollisionRadius=12
	CollisionHeight=12
	Bounciness=0.45
	Friction=0.7
	RestSpeed=40
	LifeSpan=30
	RemoteRole=ROLE_None
}
