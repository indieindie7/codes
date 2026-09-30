//=============================================================================
// ModMutator - AdventMod's presence inside each level. The menu controller
// lives outside the levels and is never ticked, so anything that has to keep
// happening during play runs from here.
// Loaded by Mutator=AdventMod.ModMutator in [DefaultPlayer] (MyDefUser.ini):
// the game adds that section's keys to every level URL.
//=============================================================================
class ModMutator extends Mutator;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SetTimer(0.5, true);
}

event Timer()
{
	class'ModSettings'.static.ApplyFOV(Level.GetLocalPlayerController());
}

defaultproperties
{
}
