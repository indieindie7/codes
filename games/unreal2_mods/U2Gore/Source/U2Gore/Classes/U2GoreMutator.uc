//=============================================================================
// U2Gore - entry point. Spawns the manager once per level, same pattern as
// U2SoftShadows: mutators only run when hosting, so this rides in via the
// ?Mutator= URL option (Mutator= line in User.ini's [DefaultPlayer] section).
//=============================================================================
class U2GoreMutator extends Mutator;

event PostBeginPlay()
{
	local U2GoreManager M;

	Super.PostBeginPlay();
	foreach DynamicActors(class'U2GoreManager', M)
		return;
	Spawn(class'U2GoreManager');
}

defaultproperties
{
	RemoteRole=ROLE_None
}
