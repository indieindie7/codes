//=============================================================================
// HoverPlasma - the hover bike's gun: the Skaarj glove's plasma bolt, fast
// enough to leave a speeding bike, doing energy damage (Skaarj shrug off their
// own plasma type).
//=============================================================================
class HoverPlasma extends ProjectileSkaarjMedium;

// not scaled down on easier difficulties like the Skaarj's own bolts
static function float GetProjectileSpeed( Actor ContextActor )
{
	return default.MaxSpeed;
}

defaultproperties
{
	speed=4500.000000
	MaxSpeed=4500.000000
	Damage=28.000000
	MomentumTransfer=9000.000000
	MyDamageType=Class'U2.DamageTypeEnergyRifle'
	LifeSpan=3.000000
}
