//=============================================================================
// Entry point for U2SoftShadows in singleplayer. ServerActors are only spawned
// when hosting, so the add-on rides in on the ?Mutator= URL option instead,
// supplied by a Mutator= line in User.ini's [DefaultPlayer] section.
//=============================================================================
class SSShadowMutator extends Mutator;

event PostBeginPlay()
{
	local SSShadowManager M;

	Super.PostBeginPlay();
	foreach DynamicActors(class'SSShadowManager', M)
		return;
	Spawn(class'SSShadowManager');
}

defaultproperties
{
	RemoteRole=ROLE_None
}
