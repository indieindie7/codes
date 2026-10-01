//=============================================================================
// U2WeaponTune - faster player projectiles.
//
// Unreal II's energy weapons fire bolts at roughly UT speeds, but the player
// here runs far faster (about 1000 units/s, 2000 sprinting with SOverhaul) on
// bigger maps, so a 1000-speed bolt barely outruns you and enemies sidestep it.
// This scales the speed of projectiles fired BY THE PLAYER only; enemies that
// share a projectile class (e.g. Skaarj bolts) are left alone.
//
// Projectiles are bGameRelevant, so they never pass through the mutator
// relevance check; instead each tick picks up newly spawned player projectiles
// and scales them before they have flown more than a frame.
//
// Tunable in User.ini under [U2WeaponTune.WeaponTune].
//=============================================================================
class WeaponTune extends Mutator
	config(User);

var config float DispersionScale;    // starting energy pistol, primary + charged alt
var config float EnergyRifleScale;   // energy rifle alt (EMP orb)
var config float TakkraScale;        // seeker orbs (they orbit targets with their own steering, so 1.0 by default)
var config float SingularityScale;   // black hole projectile
var config float SkaarjGloveScale;   // Skaarj glove alt bolts
var config float RocketScale;        // rocket launcher (primary + guided alt)
var config float GrenadeScale;       // grenade launcher / SMG grenades
var config bool bLogShots;           // write each tuned shot to Unreal2.log

var array<Projectile> Handled;       // projectiles already looked at
var Projectile Watched[8];           // recent tuned shots, to log their real flight speed
var float WatchedAge[8];

function float ScaleFor(Projectile P)
{
	local string N;

	N = Caps(string(P.Class.Name));
	if (InStr(N, "DISPERSION") >= 0)
		return DispersionScale;
	if (N == "PROJECTILEEMP")
		return EnergyRifleScale;
	if (InStr(N, "TAKKRA") >= 0)
		return TakkraScale;
	if (N == "PROJECTILEBLACKHOLE")
		return SingularityScale;
	if (N == "PROJECTILESKAARJLIGHT")
		return SkaarjGloveScale;
	if (N == "PROJECTILEHEAVYROCKET" || N == "PROJECTILEALTROCKET")
		return RocketScale;
	if (InStr(N, "GRENADE") >= 0)
		return GrenadeScale;
	return 1.0;
}

function bool FiredByPlayer(Projectile P)
{
	local Pawn Shooter;

	Shooter = P.Instigator;
	if (Shooter == None && P.Owner != None)
		Shooter = P.Owner.Instigator;
	return Shooter != None && PlayerController(Shooter.Controller) != None;
}

function bool IsHandled(Projectile P)
{
	local int i;

	for (i = Handled.Length - 1; i >= 0; i--)
	{
		if (Handled[i] == None || Handled[i].bDeleteMe)
			Handled.Remove(i, 1);
		else if (Handled[i] == P)
			return true;
	}
	return false;
}

function Tune(Projectile P)
{
	local float Scale, OldSpeed;
	local int i;

	Scale = ScaleFor(P);
	if (Scale <= 0 || Scale == 1.0)
		return;
	OldSpeed = VSize(P.Velocity);
	P.Speed *= Scale;
	if (P.MaxSpeed > 0)
		P.MaxSpeed *= Scale;
	P.Velocity *= Scale;
	if (P.Acceleration != vect(0,0,0))
		P.Acceleration *= Scale;
	if (bLogShots)
	{
		Log("U2WeaponTune: "$P.Class.Name$" speed "$int(OldSpeed)$" -> "$int(VSize(P.Velocity))$" (x"$Scale$")");
		for (i = 0; i < ArrayCount(Watched); i++)
			if (Watched[i] == None || Watched[i].bDeleteMe)
			{
				Watched[i] = P;
				WatchedAge[i] = 0;
				break;
			}
	}
}

event Tick(float DeltaTime)
{
	local Projectile P;
	local int i;

	foreach DynamicActors(class'Projectile', P)
		if (!P.bDeleteMe && !IsHandled(P))
		{
			Handled[Handled.Length] = P;
			if (FiredByPlayer(P))
				Tune(P);
		}

	// with bLogShots: report how fast tuned shots actually travel a moment later
	if (bLogShots)
		for (i = 0; i < ArrayCount(Watched); i++)
			if (Watched[i] != None)
			{
				WatchedAge[i] += DeltaTime;
				if (Watched[i].bDeleteMe)
					Watched[i] = None;
				else if (WatchedAge[i] >= 0.1)
				{
					Log("U2WeaponTune:   "$Watched[i].Class.Name$" measured flight speed "$int(VSize(Watched[i].Velocity)));
					Watched[i] = None;
				}
			}
}

defaultproperties
{
	DispersionScale=1.800000
	EnergyRifleScale=1.800000
	TakkraScale=1.000000
	SingularityScale=1.500000
	SkaarjGloveScale=1.800000
	RocketScale=1.000000
	GrenadeScale=1.000000
	bLogShots=False
	RemoteRole=ROLE_None
}
