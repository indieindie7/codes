//=============================================================================
// UTBioGlob - the Bio Rifle's charged shot (UT's BioGlob): a bigger, slower
// gel that sprays smaller splash gels around where it lands. Its size (and
// damage and burst radius) grows with the charge.
//=============================================================================
class UTBioGlob extends UTBioGel;

var int NumSplash;

// called by the weapon: Pct = charge 0..1 (UT: DrawScale 1 + 0.8 x charge up to ~4)
function SetCharge(float Pct)
{
	SetUTScale(1.0 + 3.2 * FClamp(Pct, 0, 1));
}

function Landed2()
{
	local int i;
	local vector Start;

	if (UTScale > 1)
		NumSplash = int(2 * UTScale) - 1;
	SetUTScale(FMin(UTScale, 3.0));
	for (i = 0; i < NumSplash; i++)
	{
		Start = Location + 5 * SurfaceNormal + 4 * VRand();
		Spawn(class'UTBioSplash', Instigator,, Start, rotator(Start - Location + SurfaceNormal * 4));
	}
}

defaultproperties
{
	Speed=700.000000
	Damage=75.000000
	MomentumTransfer=30000
}
