//=============================================================================
// Entry point for U2Grime in singleplayer: rides in on the ?Mutator= URL option
// (the Mutator= line in User.ini's [DefaultPlayer] section), like the other mods.
//=============================================================================
class GrimeMutator extends Mutator;

event PostBeginPlay()
{
	local GrimeManager M;

	Super.PostBeginPlay();
	foreach DynamicActors(class'GrimeManager', M)
		return;
	Spawn(class'GrimeManager');
}

defaultproperties
{
	RemoteRole=ROLE_None
}
