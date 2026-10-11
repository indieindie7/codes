//=============================================================================
// ModMindRules - hands hits and deaths to ModMinds (the creatures' feelings). The
// damage itself passes on unchanged.
//=============================================================================
class ModMindRules extends GameRules;

var ModMinds Minds;

function int NetDamage(int OriginalDamage, int Damage, Pawn Injured, Pawn InstigatedBy, vector HitLocation, out vector Momentum, class<DamageType> DamageType)
{
	if (NextGameRules != None)
		Damage = NextGameRules.NetDamage(OriginalDamage, Damage, Injured, InstigatedBy, HitLocation, Momentum, DamageType);
	if (Minds != None && Injured != None)
		Minds.Hit(Injured, InstigatedBy, Damage);
	return Damage;
}

function ScoreKill(Controller Killer, Controller Killed)
{
	if (NextGameRules != None)
		NextGameRules.ScoreKill(Killer, Killed);
	if (Minds != None && Killed != None && Killed.Pawn != None)
	{
		if (Minds.Needs != None)
			Minds.Needs.PostCorpse(Killed.Pawn, Killed.Pawn.Location);   // a corpse: hounds feed on it (ModNeeds)
		Minds.Death(Killed.Pawn, Killed.Pawn.bHidden);
	}
}

defaultproperties
{
}
