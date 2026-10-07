//=============================================================================
// One piece of clutter: a copy of a small prop's static mesh, carried the way
// U2TestHub's HubMesh and U2Destruct's DestructPiece carry meshes. Nobody gets
// stuck on it and the AI ignores it (it blocks no pawn), but shots hit it: it
// stops zero-extent traces (hitscan) and touches projectiles, so weapons call
// TakeDamage on it like on any prop.
// Walking into it kicks it: it hops away, spins, bounces off the world like
// U2Destruct's debris (Karma is off in Unreal II) and settles flat again.
// Shooting it breaks it (Black-style): it is replaced by shards of its own mesh
// thrown out along the shot, which bounce, settle and lie there a while, plus a
// dust puff and a sound when the clutter has them (GrimeClutter.DustTemplate,
// BreakSound).
//=============================================================================
class GrimeProp extends U2Decoration;

var float Radius;            // footprint radius, world units
var float Lift;              // mesh pivot above its lowest point
var rotator Rest;            // pitch and roll it lies at (yaw is free)
var vector Away;             // away from the wall it was put against (for views)
var float NextKick;
var int Kicks;
var bool bShard;             // a broken-off piece: never kicked, never broken again
var GrimeClutter Clutter;    // who placed it (for the break effects and the count)
var() float Bounciness;      // how much speed is kept along a bounce (0-1)
var() float Friction;        // how much sliding speed is kept on each bounce (0-1)
var() float RestSpeed;       // below this speed after a bounce it settles

function Setup(StaticMesh M, float Scale, vector Scale3D, float NewRadius, float NewLift, Actor Source)
{
	local int i;

	StaticMesh = M;
	SetDrawType(DT_StaticMesh);
	SetDrawScale(Scale);
	SetDrawScale3D(Scale3D);
	if (Source != None)
		for (i = 0; i < Source.Skins.Length; i++)
			Skins[i] = Source.Skins[i];
	Radius = NewRadius;
	Lift = NewLift;
	Rest = Rotation;
	// the cylinder: what shots hit, and what bounces while kicked (its bottom is the mesh's
	// lowest point)
	SetCollisionSize(FClamp(Radius * 0.8, 3, 24), FMax(Lift, 2));
}

function Kick(vector PushVel)
{
	local rotator Spin;

	if (bShard || Level.TimeSeconds < NextKick)
		return;
	NextKick = Level.TimeSeconds + 0.6;
	Kicks++;
	PushVel.Z = 0;
	Velocity = PushVel * 0.55 + vect(0,0,1) * (90 + 70 * FRand());
	Spin.Yaw = (Rand(2) * 2 - 1) * (20000 + Rand(30000));
	RotationRate = Spin;
	Fly();
}

// start moving: the cylinder lifted clear of the floor before it collides (it is at least
// 2 high, a flat prop's pivot can be lower than that)
function Fly()
{
	SetLocation(Location + vect(0,0,1) * (CollisionHeight - Lift + 1));
	bCollideWorld = true;
	SetPhysics(PHYS_Falling);
}

event HitWall(vector HitNormal, Actor Wall)
{
	local vector Along, Across;

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
	local rotator R;

	SetPhysics(PHYS_None);
	Velocity = vect(0,0,0);
	RotationRate = rot(0,0,0);
	bCollideWorld = false;
	SetLocation(Location - vect(0,0,1) * (CollisionHeight - Lift));
	if (bShard)
		return;                                 // shards lie as they fell
	R = Rest;
	R.Yaw = Rotation.Yaw;
	SetRotation(R);
}

// a shot (hitscan through the cylinder, or a projectile touching it)
function TakeDamage(int Damage, Pawn EventInstigator, vector HitLocation, vector Momentum, class<DamageType> DamageType)
{
	if (bShard || Clutter == None)
		return;
	if (Damage < Clutter.BreakDamage)
		return;
	if (VSize(Momentum) < 1)
		Momentum = Normal(Location - HitLocation) * 100;
	Clutter.Broken++;
	Clutter.BrokenByDamage++;
	Log("Grime: "$StaticMesh$" broken by "$Damage$" "$DamageType$" damage from "$EventInstigator);
	Shatter(Normal(Momentum));
}

// replaced by shards of its own mesh, thrown along Dir
function Shatter(vector Dir)
{
	local int i, n;
	local GrimeProp S;
	local float K;
	local vector Squash, Throw;
	local rotator Spin;

	n = Clutter.ShardCount;
	Dir.Z = 0;
	for (i = 0; i < n; i++)
	{
		S = Spawn(class'GrimeProp', Owner,, Location + vect(0,0,1) * (CollisionHeight * 0.5) + VRand() * Radius * 0.4, RotRand());
		if (S == None)
			continue;
		K = 0.3 + 0.25 * FRand();
		Squash.X = 0.6 + 0.6 * FRand();
		Squash.Y = 0.6 + 0.6 * FRand();
		Squash.Z = 0.5 + 0.6 * FRand();
		S.bShard = true;
		S.Clutter = Clutter;
		S.Setup(StaticMesh, DrawScale * K, Squash, Radius * K, Lift * K, self);
		S.SetCollision(false, false, false);    // shards don't catch shots
		S.LifeSpan = Clutter.ShardLife * (0.7 + 0.6 * FRand());
		Throw = Normal(Dir * 1.2 + VRand()) * (120 + 160 * FRand());
		Throw.Z = Abs(Throw.Z) + 100 + 120 * FRand();
		S.Velocity = Throw;
		Spin.Pitch = (Rand(2) * 2 - 1) * (30000 + Rand(40000));
		Spin.Yaw = (Rand(2) * 2 - 1) * (30000 + Rand(40000));
		S.RotationRate = Spin;
		S.Fly();
	}
	Clutter.BreakEffects(Location + vect(0,0,1) * CollisionHeight * 0.5, Dir);
	Destroy();
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bCollideActors=True
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	bBlockZeroExtentTraces=True
	bBlockNonZeroExtentTraces=False
	bProjTarget=True
	bBounce=True
	bFixedRotationDir=True
	bRotateToDesired=False
	bHidden=False
	Physics=PHYS_None
	Bounciness=0.35
	Friction=0.6
	RestSpeed=50
	RemoteRole=ROLE_None
}
