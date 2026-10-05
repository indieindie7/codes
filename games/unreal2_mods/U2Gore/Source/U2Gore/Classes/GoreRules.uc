//=============================================================================
// Sees every hit (GameRules.NetDamage, which Pawn.TakeDamage runs for every
// character) and passes it to the GoreManager.
//=============================================================================
class GoreRules extends GameRules;

var GoreManager Gore;

function int NetDamage( int OriginalDamage, int Damage, pawn injured, pawn instigatedBy, vector HitLocation, vector Momentum, class<DamageType> DamageType )
{
	if (Gore != None && injured != None && Damage > 0)
		Gore.Hit(injured, instigatedBy, HitLocation, Momentum, Damage, DamageType);
	if (NextGameRules != None)
		return NextGameRules.NetDamage(OriginalDamage, Damage, injured, instigatedBy, HitLocation, Momentum, DamageType);
	return Damage;
}

defaultproperties
{
}
