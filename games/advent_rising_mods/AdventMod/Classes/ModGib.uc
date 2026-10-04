//=============================================================================
// ModGib - one piece of a body blown apart (ModGore.Gib): a part cut from the
// game's own character mesh (ModGibParts), thrown on the same fake physics as the
// casings (a parabola stepped with traces, no Karma), tumbling, leaving blood
// where it hits. It lies where it stops; after Stay seconds it sinks into a
// stain on the floor and is gone (clutter for free).
//=============================================================================
class ModGib extends Actor;

var ModGore Gore;
var vector Vel;
var float Gravity;
var int Bounces;
var float Radius;          // half its smallest size: how far it sits off the floor
var int Kind;              // its blood (ModGore.BloodKind)
var vector Size;           // the part's size (ModGibParts), scaled
var bool bSettled;
var float StillTime, Stay;

function Launch(vector V, float G, float R)
{
	Vel = V;
	Gravity = G;
	Radius = R;
	RotationRate.Yaw = Rand(80000) - 40000;
	RotationRate.Pitch = Rand(80000) - 40000;
	RotationRate.Roll = Rand(80000) - 40000;
}

// down on the floor on its longest side, turned any way, resting on its thickness
function Settle(vector Floor, vector N)
{
	local rotator R;
	local float Thick;

	bSettled = true;
	RotationRate = rot(0,0,0);
	R.Yaw = Rand(65536);
	if (Size.Z >= Size.X && Size.Z >= Size.Y)
	{
		// long along its own Z (a limb): roll it over onto its side
		R.Roll = 16384 * (1 - 2 * Rand(2));
		Thick = Size.Y;
	}
	else
		Thick = Size.Z;
	SetRotation(R);
	SetLocation(Floor + N * Thick * 0.45);
}

event Tick(float DeltaTime)
{
	local vector From, To, HitL, HitN;
	local rotator R;

	if (bSettled)
	{
		StillTime += DeltaTime;
		if (StillTime > Stay)
		{
			// sinking away: down through the floor over a second, then a stain
			SetLocation(Location - vect(0,0,1) * Radius * 2 * DeltaTime);
			if (StillTime > Stay + 1.0)
			{
				if (Gore != None)
					Gore.GibGone(self);
				Destroy();
			}
		}
		return;
	}
	DeltaTime = FMin(DeltaTime, 0.05);
	From = Location;
	Vel.Z += Gravity * DeltaTime;
	To = From + Vel * DeltaTime;
	if (Trace(HitL, HitN, To + Normal(Vel) * Radius, From, false) != None)
	{
		Bounces++;
		if (Gore != None && VSize(Vel) > 200)
			Gore.GibHit(HitL, HitN, Kind, VSize(Vel));
		// meat doesn't bounce much: keep a fifth of the bounce, half the slide
		Vel = Vel - 2 * (Vel Dot HitN) * HitN;
		Vel = (Vel Dot HitN) * HitN * 0.2 + (Vel - (Vel Dot HitN) * HitN) * 0.5;
		RotationRate = RotationRate * 0.5;
		SetLocation(HitL + HitN * Radius);
		if (HitN.Z > 0.7 && (Bounces >= 3 || VSize(Vel) < 80))
			Settle(HitL, HitN);
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
     Stay=40.000000
     LifeSpan=60.000000
}
