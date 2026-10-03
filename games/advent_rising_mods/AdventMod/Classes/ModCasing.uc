//=============================================================================
// ModCasing - a spent shell that flies on its own fake physics (no Karma): a
// parabola stepped with traces, a bounce or two off whatever it meets (part of
// the speed kept, the rest lost to friction), then it lies still and, a moment
// later, turns into a flat mark on the floor (ModGore.AddClutter) and is gone:
// a 3D object only while it moves, clutter for free after that (the way
// Project Zomboid flattens its dead into sprites). Spawned by ModGore where the
// game's own shell particles appear.
//=============================================================================
class ModCasing extends Actor;

var ModGore Gore;
var vector Vel;
var float Gravity;
var int Bounces;
var float StillTime;
var bool bSettled;

function Launch(vector V, float G)
{
	Vel = V;
	Gravity = G;
	RotationRate.Yaw = 30000 + Rand(60000);
	RotationRate.Pitch = 20000 + Rand(40000);
	RotationRate.Roll = Rand(30000);
}

event Tick(float DeltaTime)
{
	local vector From, To, HitL, HitN;
	local float Into;
	local rotator R;

	if (bSettled)
	{
		StillTime += DeltaTime;
		if (StillTime > 1.5)
		{
			if (Gore != None)
				Gore.AddClutter(Location, Rotation.Yaw);
			Destroy();
		}
		return;
	}
	DeltaTime = FMin(DeltaTime, 0.05);
	From = Location;
	Vel.Z += Gravity * DeltaTime;
	To = From + Vel * DeltaTime;
	if (Trace(HitL, HitN, To, From, false) != None)
	{
		Bounces++;
		// reflect, keep a third of the bounce and most of the slide
		Into = Vel Dot HitN;
		Vel = (Vel - 2 * Into * HitN);
		Vel = (Vel Dot HitN) * HitN * 0.35 + (Vel - (Vel Dot HitN) * HitN) * 0.6;
		SetLocation(HitL + HitN * 1.5);
		if (HitN.Z > 0.7 && (Bounces >= 3 || VSize(Vel) < 60))
		{
			// lying on its side on the floor, along a random heading
			bSettled = true;
			R.Yaw = Rotation.Yaw;
			R.Pitch = 16384;
			SetRotation(R);
			RotationRate = rot(0,0,0);
		}
		return;
	}
	SetLocation(To);
	R = Rotation + RotationRate * DeltaTime;
	SetRotation(R);
}

defaultproperties
{
     DrawType=DT_StaticMesh
     Physics=PHYS_None
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bUnlit=False
     bShadowCast=False
     RemoteRole=ROLE_None
     LifeSpan=8.000000
     DrawScale=1.000000
}
