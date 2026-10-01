//=============================================================================
// U2Gore - entry point. Spawns the manager once per level, same pattern as
// U2SoftShadows: mutators only run when hosting, so this rides in via the
// ?Mutator= URL option (Mutator= line in User.ini's [DefaultPlayer] section).
//
// MutatorTakeDamage below is the "no Pawn subclassing needed" integration
// path: every hit passes through here, ahead of Health being applied, via
// GameInfo.NetDamage's mutator chain. UNVERIFIED for Unreal2 specifically -
// this hook (name, signature, whether it's even called) is standard in
// UT2003/UT2004's Mutator.uc, but Unreal2 forked off an earlier, single-
// player-focused build and may not route damage through the mutator chain
// the same way. If it never fires in your game, use U2GoreHookExample.uc's
// Died()/TakeDamage subclass approach instead - slower to wire up (touches
// every Pawn subclass) but only depends on Pawn's own API, which is far
// more likely to be stable across the engine fork.
//=============================================================================
class U2GoreMutator extends Mutator;

var U2GoreManager Manager;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	foreach DynamicActors(class'U2GoreManager', Manager)
		break;
	if (Manager == None)
		Manager = U2GoreManager(Spawn(class'U2GoreManager'));
}

function MutatorTakeDamage(out int ActualDamage, Pawn Victim, Pawn InstigatedBy, out vector HitLocation, out vector Momentum, class<DamageType> DamageType)
{
	local float Overkill;
	local U2HitReactionController HRC;

	if (Manager != None && Victim != None && !Victim.bDeleteMe && ActualDamage > 0)
	{
		Overkill = ActualDamage - Victim.Health;
		Manager.SpawnGoreForDeath(Victim, DamageType, HitLocation, Momentum, Overkill);

		if (Overkill >= 0) // this hit kills - hand the corpse to full ragdoll instead of tracking loose bones
		{
			HRC = Manager.GetHitController(Victim);
			if (HRC != None)
				HRC.GoToFullRagdoll();
		}
		else
			Manager.ReactToNonLethalHit(Victim, HitLocation, Momentum, ActualDamage); // spurt always, stagger only for weak-tier enemies
	}

	if (NextMutator != None)
		NextMutator.MutatorTakeDamage(ActualDamage, Victim, InstigatedBy, HitLocation, Momentum, DamageType);
}

defaultproperties
{
	RemoteRole=ROLE_None
}
