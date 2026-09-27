//=============================================================================
// Development probe: logs every player weapon's fire modes and its projectiles'
// speeds, so weapon tuning starts from the game's real numbers.
//=============================================================================
class WeaponProbe extends Mutator;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	Dump("weaponInvAssaultRifle");
	Dump("weaponInvDispersion");
	Dump("weaponInvEnergyRifle");
	Dump("weaponInvFlamethrower");
	Dump("weaponInvGrenadeLauncher");
	Dump("weaponInvLaserRifle");
	Dump("weaponInvLeechGun");
	Dump("weaponInvPistol");
	Dump("weaponInvRocketLauncher");
	Dump("weaponInvShotgun");
	Dump("weaponInvSingularityCannon");
	Dump("weaponInvSniperRifle");
	Dump("weaponInvTakkra");
	Dump("weaponInvSkaarjGlove");
	Dump("WeaponInvSMG");
	Dump("weaponInvMindClaw");
}

function DumpProj(string Mode, class<Projectile> P)
{
	if (P == None)
	{
		Log("WeaponProbe:   "$Mode$": no projectile class");
		return;
	}
	Log("WeaponProbe:   "$Mode$": "$P.Name$" Speed="$P.default.Speed$" MaxSpeed="$P.default.MaxSpeed$" Damage="$P.default.Damage$" Radius="$P.default.DamageRadius$" LifeSpan="$P.default.LifeSpan$" Physics="$P.default.Physics);
}

function Dump(string N)
{
	local class<Weapon> W;

	W = class<Weapon>(DynamicLoadObject("U2Weapons."$N, class'Class', true));
	if (W == None)
	{
		Log("WeaponProbe: "$N$" not found");
		return;
	}
	Log("WeaponProbe: "$N$" instant="$W.default.bInstantHit$"/"$W.default.bAltInstantHit$" refire="$W.default.RefireRate$"/"$W.default.AltRefireRate$" aimSpeed="$class<U2Weapon>(W).default.ProjectileSpeed$"/"$class<U2Weapon>(W).default.AltProjectileSpeed);
	DumpProj("primary", W.default.ProjectileClass);
	DumpProj("alt", W.default.AltProjectileClass);
}

defaultproperties
{
	RemoteRole=ROLE_None
}
