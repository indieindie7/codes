//=============================================================================
// FairRules - sees every hit and every death (GameRules) and tells the
// mutator about the ones that matter: hits on the player, kills by the player.
//=============================================================================
class FairRules extends GameRules;

var FairFights Settings;

function int NetDamage( int OriginalDamage, int Damage, pawn injured, pawn instigatedBy, vector HitLocation, vector Momentum, class<DamageType> DamageType )
{
	if (Settings != None && injured != None && instigatedBy != None && Damage > 0 && instigatedBy != injured)
	{
		if (injured.IsRealPlayer())
			Settings.PlayerHit(instigatedBy, Damage);
		else if (instigatedBy.IsRealPlayer())
			Settings.PlayerHitSomething(injured, false);
	}
	if (NextGameRules != None)
		return NextGameRules.NetDamage(OriginalDamage, Damage, injured, instigatedBy, HitLocation, Momentum, DamageType);
	return Damage;
}

function bool PreventDeath(Pawn Killed, Controller Killer, class<DamageType> damageType, vector HitLocation)
{
	if (Settings != None && Killed != None && Killer != None && Killer.Pawn != None
		&& Killer.Pawn.IsRealPlayer() && !Killed.IsRealPlayer())
		Settings.PlayerKilled(Killed);
	if (Settings != None && Killed != None && Killer != None && Killer.Pawn != None
		&& Killer.Pawn.IsRealPlayer() && !Killed.IsRealPlayer())
		Settings.PlayerHitSomething(Killed, true);
	if (NextGameRules != None)
		return NextGameRules.PreventDeath(Killed, Killer, damageType, HitLocation);
	return false;
}

defaultproperties
{
}
