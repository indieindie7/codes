//=============================================================================
// One piece of clutter: a copy of a small prop's static mesh, with no collision
// (nobody gets stuck on it, the AI ignores it, shots pass through), carried the
// way U2TestHub's HubMesh and U2Destruct's DestructPiece carry meshes.
// Walking into it kicks it: it hops away, spins, bounces off the world like
// U2Destruct's debris (Karma is off in Unreal II) and settles flat again.
//=============================================================================
class GrimeProp extends U2Decoration;

var float Radius;            // footprint radius, world units
var float Lift;              // mesh pivot above its lowest point
var rotator Rest;            // pitch and roll it lies at (yaw is free)
var vector Away;              // away from the wall it was put against (for views)
var float NextKick;
var int Kicks;
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
	// the cylinder only matters while kicked: its bottom is the mesh's lowest point
	SetCollisionSize(FClamp(Radius * 0.6, 3, 20), FMax(Lift, 2));
}

function Kick(vector PushVel)
{
	local rotator Spin;

	if (Level.TimeSeconds < NextKick)
		return;
	NextKick = Level.TimeSeconds + 0.6;
	Kicks++;
	PushVel.Z = 0;
	Velocity = PushVel * 0.55 + vect(0,0,1) * (90 + 70 * FRand());
	Spin.Yaw = (Rand(2) * 2 - 1) * (20000 + Rand(30000));
	RotationRate = Spin;
	// lift the cylinder clear of the floor before it collides (it is at least 2 high,
	// a flat prop's pivot can be lower than that)
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
	R = Rest;
	R.Yaw = Rotation.Yaw;
	SetRotation(R);
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
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
