//=============================================================================
// U2Gore - reference only. This is not meant to be spawned or extended
// directly; copy the three pieces below (LastHitMomentum capture, the
// GoreManager lookup, and the Died() call) into your own monster/player
// Pawn subclasses wherever they currently sit in your class hierarchy.
//
// Why TakeDamage is overridden too: stock Pawn.Died(Killer, damageType,
// HitLocation) doesn't carry the hit's Momentum, and by the time Died()
// fires TakeDamage's local Damage variable is gone - so the momentum has to
// be stashed somewhere Died() can still reach it.
//
// -Health as the overkill amount relies on TakeDamage subtracting Damage
// from Health without clamping it to 0 first. Confirm that's still true in
// whatever TakeDamage chain your Pawn actually inherits (some subclasses
// override it and clamp) - if it clamps, track OverkillDamage explicitly
// instead: OverkillDamage = Damage - HealthBeforeThisHit.
//=============================================================================
class U2GoreHookExample extends Pawn
	abstract;

var vector       LastHitMomentum;
var U2GoreManager GoreManager;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	foreach DynamicActors(class'U2GoreManager', GoreManager)
		break;
}

function TakeDamage(int Damage, Pawn instigatedBy, vector HitLocation, vector Momentum, class<DamageType> damageType)
{
	LastHitMomentum = Momentum;
	Super.TakeDamage(Damage, instigatedBy, HitLocation, Momentum, damageType);
}

event Died(Controller Killer, class<DamageType> damageType, vector HitLocation)
{
	if (GoreManager != None)
		GoreManager.SpawnGoreForDeath(Self, damageType, HitLocation, LastHitMomentum, -Health);

	Super.Died(Killer, damageType, HitLocation);
}
