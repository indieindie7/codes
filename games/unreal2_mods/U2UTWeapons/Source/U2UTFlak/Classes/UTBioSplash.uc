//=============================================================================
// UTBioSplash - a small gel sprayed out when a charged glob lands (UT's
// BioSplash).
//=============================================================================
class UTBioSplash extends UTBioGel;

simulated function ProcessTouch(Actor Other, vector HitLocation)
{
	if (UTBioGlob(Other) != None)
		return;
	Super.ProcessTouch(Other, HitLocation);
}

defaultproperties
{
	Speed=300.000000
}
