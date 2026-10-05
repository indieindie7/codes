//=============================================================================
// U2Gore - one physics-simulated body part. The engine's own 'Gib' class
// already does fall/bounce/settle; this just adds a lifespan so old gore
// cleans itself up even if U2GoreManager's cap never gets hit, and a bit of
// tumble so a pile of gibs doesn't look identical.
//=============================================================================
class U2Gib extends Gib;

var float SpinRate;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	RotationRate = rot(0,0,0) + rotator(VRand()) * SpinRate;
	LifeSpan = 12.0 + FRand() * 6.0; // staggered so a whole batch doesn't vanish in one frame
}

defaultproperties
{
	SpinRate=40000
	Physics=PHYS_Falling
	RemoteRole=ROLE_None
}
