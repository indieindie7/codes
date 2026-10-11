//=============================================================================
// ModGoreRules - hands every hit to ModReact (flinch, stagger, death ragdoll) and ModGore. GameRules.NetDamage runs for each
// character's hit (Pawn.TakeDamage -> GameInfo.ReduceDamage); the damage itself
// passes on unchanged.
//=============================================================================
class ModGoreRules extends GameRules;

var ModGore Gore;

function int NetDamage(int OriginalDamage, int Damage, Pawn Injured, Pawn InstigatedBy, vector HitLocation, out vector Momentum, class<DamageType> DamageType)
{
	if (NextGameRules != None)
		Damage = NextGameRules.NetDamage(OriginalDamage, Damage, Injured, InstigatedBy, HitLocation, Momentum, DamageType);
	// (a melee hit with the energy blade does more, and cuts)
	if (Gore != None && Gore.Melee != None)
		Damage = Gore.Melee.Strike(Damage, Injured, InstigatedBy, HitLocation, DamageType);
	// (the hit as it landed, before any plate took part of it: what knocks a body down)
	if (Gore != None && Gore.React != None)
		Gore.React.Impact = Damage;
	// (where on the skin the shot landed: armour or flesh, from the mesh's own triangles; the
	// damage x ArmourFactor on armour. ModGore.Hit then sparks instead of bleeding.)
	if (Gore != None && Gore.Armor != None && Injured != None)
	{
		if (InstigatedBy != None)
			Damage = Gore.Armor.Classify(Damage, Injured, HitLocation, Normal(HitLocation - InstigatedBy.Location));
		else
			Damage = Gore.Armor.Classify(Damage, Injured, HitLocation, Normal(Momentum));
	}
	// (a plate takes part of a hit on it until it breaks; a bare region takes more)
	if (Gore != None && Gore.Armor != None)
	{
		if (InstigatedBy != None)
			Damage = Gore.Armor.Strike(Damage, Injured, InstigatedBy, HitLocation, DamageType, Normal(HitLocation - InstigatedBy.Location));
		else
			Damage = Gore.Armor.Strike(Damage, Injured, InstigatedBy, HitLocation, DamageType, Normal(Momentum));
	}
	if (Gore != None && Gore.React != None)
	{
		if (InstigatedBy != None)
			Gore.React.Hit(Injured, HitLocation, Momentum, Damage, DamageType, Normal(HitLocation - InstigatedBy.Location));
		else
			Gore.React.Hit(Injured, HitLocation, Momentum, Damage, DamageType, vect(0,0,0));
	}
	if (Gore != None)
		Gore.Hit(Injured, InstigatedBy, HitLocation, Momentum, Damage, DamageType);
	return Damage;
}

defaultproperties
{
}
