//=============================================================================
// ModGoreRules - hands every hit to ModGore. GameRules.NetDamage runs for each
// character's hit (Pawn.TakeDamage -> GameInfo.ReduceDamage); the damage itself
// passes on unchanged.
//=============================================================================
class ModGoreRules extends GameRules;

var ModGore Gore;

function int NetDamage(int OriginalDamage, int Damage, Pawn Injured, Pawn InstigatedBy, vector HitLocation, out vector Momentum, class<DamageType> DamageType)
{
	if (NextGameRules != None)
		Damage = NextGameRules.NetDamage(OriginalDamage, Damage, Injured, InstigatedBy, HitLocation, Momentum, DamageType);
	if (Gore != None)
		Gore.Hit(Injured, InstigatedBy, HitLocation, Momentum, Damage, DamageType);
	return Damage;
}

defaultproperties
{
}
