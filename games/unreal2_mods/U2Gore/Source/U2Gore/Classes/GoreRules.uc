//=============================================================================
// Sees every hit (GameRules.NetDamage, which Pawn.TakeDamage runs for every
// character) and passes it to the GoreManager and GoreDying (hit zones), and every
// death (GameRules.PreventDeath), which GoreDying may turn into a dying phase.
//=============================================================================
class GoreRules extends GameRules;

var GoreManager Gore;

function int NetDamage( int OriginalDamage, int Damage, pawn injured, pawn instigatedBy, vector HitLocation, vector Momentum, class<DamageType> DamageType )
{
	if (Gore != None && Gore.DyingPhase != None && injured != None && Damage > 0)
		Gore.DyingPhase.NoteHit(injured, instigatedBy, HitLocation, Damage, DamageType);
	if (Gore != None && injured != None && Damage > 0)
		Gore.Hit(injured, instigatedBy, HitLocation, Momentum, Damage, DamageType);
	if (NextGameRules != None)
		return NextGameRules.NetDamage(OriginalDamage, Damage, injured, instigatedBy, HitLocation, Momentum, DamageType);
	return Damage;
}

// a death: GoreDying may keep the victim dying a while instead (out of the fight already)
function bool PreventDeath(Pawn Killed, Controller Killer, class<DamageType> damageType, vector HitLocation)
{
	if (Gore != None && Gore.DyingPhase != None && Gore.DyingPhase.Take(Killed, Killer, damageType, HitLocation))
		return true;
	if (NextGameRules != None)
		return NextGameRules.PreventDeath(Killed, Killer, damageType, HitLocation);
	return false;
}

defaultproperties
{
}
