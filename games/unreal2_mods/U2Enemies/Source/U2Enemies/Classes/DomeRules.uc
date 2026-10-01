//=============================================================================
// DomeRules - sees every hit (GameRules.NetDamage gets the hit location) and
// turns hits to an Izarian's dome - the upper part of the body - into
// breaches.
//=============================================================================
class DomeRules extends GameRules;

var EnemyMutator Settings;
// breached pawns are few: a short list, not a search of every actor per hit
var array<DomeLeak> Leaks;

function bool IsDomeHit(Pawn P, vector HitLocation)
{
	return HitLocation.Z > P.Location.Z + P.CollisionHeight * 0.45;
}

function DomeLeak LeakOn(Pawn P)
{
	local int i;
	for (i = Leaks.Length - 1; i >= 0; i--)
	{
		if (Leaks[i] == None || Leaks[i].bDeleteMe)
			Leaks.Remove(i, 1);
		else if (Leaks[i].Owner == P)
			return Leaks[i];
	}
	return None;
}

function int NetDamage( int OriginalDamage, int Damage, pawn injured, pawn instigatedBy, vector HitLocation, vector Momentum, class<DamageType> DamageType )
{
	local DomeLeak L;

	if (Settings != None && injured != None && injured.Health > 0 && injured.IsA('U2Izarian')
		&& DamageType != class'DamageTypeDrowned' && Damage > 0 && IsDomeHit(injured, HitLocation))
	{
		Damage = int(Damage * Settings.DomeDamageScale);
		L = LeakOn(injured);
		if (L == None)
		{
			L = Spawn(class'DomeLeak', injured, , HitLocation);
			Leaks[Leaks.Length] = L;
			// a breach either breaks it (panic) or unleashes it (feral)
			if (FRand() < Settings.BreachFeralOdds)
			{
				Settings.MakeFeral(U2PawnBasic(injured));
				L.Start(instigatedBy, Settings.LeakDamagePerSecond, Settings.LeakSeconds, false);
			}
			else
				L.Start(instigatedBy, Settings.LeakDamagePerSecond, Settings.LeakSeconds, FRand() < Settings.PanicOdds);
		}
		else
			L.Widen();                  // another hole: it leaks longer
	}

	if (NextGameRules != None)
		return NextGameRules.NetDamage(OriginalDamage, Damage, injured, instigatedBy, HitLocation, Momentum, DamageType);
	return Damage;
}

defaultproperties
{
}
