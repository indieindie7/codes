//=============================================================================
// U2Gore - a blood splat stuck to whatever surface it was spawned against.
// Fades out over its last second of life instead of popping out of existence.
//=============================================================================
class U2BloodDecal extends Decal;

var float FadeStartAge; // seconds after spawn before it starts fading
var float TotalLife;
var float Age;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	DrawScale *= 0.85 + FRand() * 0.3; // varies splat size a little
	SetTimer(0.1, true);
}

event Timer()
{
	Age += 0.1;
	if (Age < FadeStartAge)
		return;

	if (Age >= TotalLife)
	{
		Destroy();
		return;
	}

	ScaleGlow = 1.0 - (Age - FadeStartAge) / (TotalLife - FadeStartAge);
}

defaultproperties
{
	FadeStartAge=8.0
	TotalLife=10.0
	RemoteRole=ROLE_None
}
