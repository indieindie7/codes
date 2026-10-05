//=============================================================================
// Entry point for U2Gore in singleplayer: rides in on the ?Mutator= URL option
// (the Mutator= line in User.ini's [DefaultPlayer] section), like the other mods.
//=============================================================================
class GoreMutator extends Mutator;

event PostBeginPlay()
{
	local GoreManager M;

	Super.PostBeginPlay();
	foreach DynamicActors(class'GoreManager', M)
		return;
	Spawn(class'GoreManager');
}

defaultproperties
{
	RemoteRole=ROLE_None
}
