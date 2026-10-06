//=============================================================================
// ModMelee - melee weapons (ModGore spawns it). For now one: the energy blade (ModBlade).
//   - Enemies sometimes drop one when they die (BladeDropChance, MaxPickups in a level).
//   - Walking over it picks it up. It rides on the player's back and is in the hand while a
//     melee attack plays; the melee key swings it with the game's own melee moves.
//   - A melee hit with the blade does BladeDamage times the punch's damage, cuts, and on a
//     kill takes off the part it hit (ModSever, no dice). Each hit uses one of BladeCharges;
//     at none the blade burns out.
// The blade stays with the player from level to level (SavedCharges, for the game's run).
// It hums (louder in the hand), whooshes when swung and throws sparks where it hits: the
// game's own sounds and sparks (loaded with this package: a name looked up at run time
// came back None unless the level already had it in memory). The gun in the right hand is hidden
// while the blade is in it.
//=============================================================================
class ModMelee extends Info
	config(AdventMod);

var config bool bBlades;
var config float BladeDropChance;  // per enemy killed
var config int BladeCharges;
var config float BladeDamage;      // times the melee move's own damage
var config int MaxPickups;
var config float PickupReach;
var config rotator HandRot, BackRot;       // how it sits on the hand and on the back
var config name BackBone;                  // the bone it rides on the back (spine2 = lower back, Spine3 = upper)
var config bool bBladeLight;               // the blade lights what is near it
var config vector HandOffset, BackOffset;
var config bool bTestBlade;        // testing: the player starts with one
var Sound Hum, Swing, StrikeSnd;
var class<Emitter> Sparks;
// the swings (ModBladeAnims): played on an upper-body channel over the game's punch move,
// so the move's timing, footwork and hit checks stay the game's while the arm swings the blade
var config bool bSwingAnims;
var config int SwingChannel;       // an animation channel the game doesn't use
var config float SwingRate;
var config name SwingBone;         // the channel's root: the upper body
var name Clips[5];
var int LastClip;
var WeaponBase HiddenGun;          // the gun put away while the blade is in the hand

var ModGore Gore;
var ModBlade Carried;
var Pawn Holder;
var bool bInHand;
var int Charges;
var int SavedCharges;              // (default) the blade the player carries, across levels
var array<ModBlade> Pickups;
var bool bStarted;

function Say(string S)
{
	local PlayerController C;

	C = Level.GetLocalPlayerController();
	if (C != None)
		C.ClientMessage(S);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: " $ S);
}

// a blade humming: quietly on the back or lying, louder in the hand
function SetHum(ModBlade B, bool bLoud)
{
	if (B == None || Hum == None)
		return;
	B.AmbientSound = Hum;
	if (bLoud)
		B.SoundVolume = 150;
	else
		B.SoundVolume = 50;
}

function ShowGun()
{
	if (HiddenGun != None && !HiddenGun.bDeleteMe)
		HiddenGun.bHidden = false;
	HiddenGun = None;
}

// the blade into the player's keeping: a pickup taken (B), or a new one made
function Equip(Pawn P, int n, optional ModBlade B)
{
	if (P == None)
		return;
	if (Carried != None && Carried != B)
		Carried.Destroy();
	if (B == None)
		B = Spawn(class'ModBlade',,, P.Location);
	if (B == None)
		return;
	B.bLying = false;
	B.LifeSpan = 0;
	Carried = B;
	Holder = P;
	Charges = n;
	default.SavedCharges = n;
	Place(false);
}

// on the hand for a swing, on the back otherwise
function Place(bool bHand)
{
	if (Carried == None || Holder == None)
		return;
	Holder.DetachFromBone(Carried);
	if (bHand)
	{
		Holder.AttachToBone(Carried, 'righthand');
		Carried.SetRelativeLocation(HandOffset);
		Carried.SetRelativeRotation(HandRot);
		// the gun out of the hand the blade is in (as the game does on its turrets)
		if (Holder.RightWeapon != None && !Holder.RightWeapon.bHidden)
		{
			HiddenGun = Holder.RightWeapon;
			HiddenGun.bHidden = true;
		}
		if (Swing != None)
			Holder.PlaySound(Swing, SLOT_None, 1.0, false, 400, 0.9 + 0.2 * FRand());
		PlaySwing();
	}
	else
	{
		Holder.AttachToBone(Carried, BackBone);
		Carried.SetRelativeLocation(BackOffset);
		Carried.SetRelativeRotation(BackRot);
		ShowGun();
		if (bSwingAnims)
			Holder.AnimBlendParams(SwingChannel, 0.0, 0.2, 0.2);
	}
	bInHand = bHand;
	if (bBladeLight)
		Carried.LightType = LT_Steady;
	else
		Carried.LightType = LT_None;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: blade in hand " $ bHand $ ", right gun " $ Holder.RightWeapon $ " hidden by us " $ HiddenGun);
	SetHum(Carried, bHand);
}

// one of the blade's swings on the upper body, over the punch move the game is playing
function PlaySwing()
{
	local MeshAnimation A;
	local int i, n;

	if (!bSwingAnims || Holder == None)
		return;
	A = class'ModBladeAnims'.default.Swings;
	if (A == None)
		return;
	Holder.LinkSkelAnim(A);
	for (n = 0; n < 5; n++)
		if (Clips[n] == '')
			break;
	if (n == 0)
		return;
	i = Rand(n);
	if (n > 1 && i == LastClip)
		i = (i + 1) % n;
	LastClip = i;
	if (!Holder.HasAnim(Clips[i]))
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("melee: " $ Holder $ " has no swing " $ Clips[i]);
		return;
	}
	Holder.AnimBlendParams(SwingChannel, 1.0, 0.12, 0.2, SwingBone);
	Holder.PlayAnim(Clips[i], SwingRate, 0.08, SwingChannel);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: swing " $ Clips[i] $ " on channel " $ SwingChannel);
}

function BurnOut()
{
	Say("The energy blade burns out.");
	ShowGun();
	if (Carried != None)
	{
		if (Holder != None)
			Holder.DetachFromBone(Carried);
		Carried.Destroy();
	}
	Carried = None;
	Charges = 0;
	default.SavedCharges = 0;
}

// a blade left where an enemy fell
function Drop(vector Spot)
{
	local vector HitL, HitN;
	local ModBlade B;
	local int i;

	if (!bBlades)
		return;
	for (i = Pickups.Length - 1; i >= 0; i--)
		if (Pickups[i] == None || Pickups[i].bDeleteMe || !Pickups[i].bLying)
			Pickups.Remove(i, 1);
	if (Pickups.Length >= MaxPickups)
		return;
	if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20), false) == None)
		return;
	B = Spawn(class'ModBlade',,, HitL + vect(0,0,34));
	if (B == None)
		return;
	B.Lie(HitL + vect(0,0,34));
	if (!bBladeLight)
		B.LightType = LT_None;
	B.LifeSpan = 150;
	SetHum(B, false);
	Pickups[Pickups.Length] = B;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: a blade dropped at " $ B.Location);
}

// ModGoreRules: every hit passes here first. A melee move by the blade's holder becomes a
// blade strike. Returns the damage to deal.
function int Strike(int Damage, Pawn Injured, Pawn By, vector Spot, class<DamageType> Type)
{
	local vector Dir;
	local Emitter E;

	if (Carried == None || By == None || By != Holder || Injured == None || Injured == By || Type == None || Damage <= 0)
		return Damage;
	if (Left(Caps(string(Type.Name)), 16) != "DAMAGEHANDATTACK")
		return Damage;
	Damage = int(Damage * BladeDamage);
	Dir = Normal(Injured.Location - By.Location);
	if (Sparks != None)
	{
		E = Spawn(Sparks,,, Spot - Dir * 6, rotator(-Dir));
		if (E != None)
			E.LifeSpan = 1.5;
	}
	if (StrikeSnd != None)
		Injured.PlaySound(StrikeSnd, SLOT_None, 1.0, false, 600, 0.9 + 0.25 * FRand());
	if (Gore != None)
	{
		Gore.CutBlood(Spot, Dir, Gore.BloodKind(Injured));
		if (Gore.Severer != None)
			Gore.Severer.bForce = true;      // a kill by this hit takes the part off (and isn't blown apart)
	}
	Charges--;
	default.SavedCharges = Charges;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: blade strike on " $ Injured $ " (" $ Type.Name $ "), damage " $ Damage $ ", " $ Charges $ " left (fx " $ Hum $ " " $ Swing $ " " $ StrikeSnd $ " " $ Sparks $ ", gun hidden " $ HiddenGun $ ")");
	if (Charges <= 0)
		BurnOut();
	else if (Charges == 5)
		Say("Energy blade: 5 strikes left.");
	return Damage;
}

event Tick(float DeltaTime)
{
	local PlayerController C;
	local Pawn P;
	local int i;

	if (!bBlades)
		return;
	C = Level.GetLocalPlayerController();
	if (C == None || C.Pawn == None)
		return;
	P = C.Pawn;
	if (!bStarted)
	{
		bStarted = true;
		if (bTestBlade && default.SavedCharges <= 0)
			default.SavedCharges = BladeCharges;
	}
	if (P.Health <= 0)
	{
		// lost with the player's life
		ShowGun();
		if (Carried != None)
		{
			Carried.Destroy();
			Carried = None;
			default.SavedCharges = 0;
		}
		return;
	}
	// a new level or a new body: the blade the player had
	if (default.SavedCharges > 0 && (Carried == None || Carried.bDeleteMe || Holder != P))
	{
		Carried = None;
		Equip(P, default.SavedCharges);
	}
	if (Carried != None)
	{
		if (P.AnimIsInGroup(0, 'attack') != bInHand)
			Place(!bInHand);
		return;
	}
	// none carried: one lying close by is taken
	for (i = Pickups.Length - 1; i >= 0; i--)
	{
		if (Pickups[i] == None || Pickups[i].bDeleteMe)
		{
			Pickups.Remove(i, 1);
			continue;
		}
		if (VSize(Pickups[i].Location - P.Location) < PickupReach + P.CollisionRadius)
		{
			Equip(P, BladeCharges, Pickups[i]);
			Pickups.Remove(i, 1);
			Say("Energy blade: " $ BladeCharges $ " strikes. The melee key swings it.");
			return;
		}
	}
}

event Destroyed()
{
	local int i;

	ShowGun();
	for (i = 0; i < Pickups.Length; i++)
		if (Pickups[i] != None)
			Pickups[i].Destroy();
	if (Carried != None)
		Carried.Destroy();
	Super.Destroyed();
}

defaultproperties
{
     bBlades=True
     BladeDropChance=0.150000
     BladeCharges=15
     BladeDamage=5.000000
     MaxPickups=3
     PickupReach=60.000000
     Hum=Sound'power.EnergyBlast.energy_loop'
     Swing=Sound'fx.misc.koroem_whoosh'
     StrikeSnd=Sound'fx.misc.sparks_burst'
     Sparks=Class'EonEffects.fx_Default_Sparks'
     BackRot=(Pitch=0,Yaw=16384,Roll=12000)
     BackOffset=(X=0.000000,Y=-10.000000,Z=-6.000000)
     BackBone=Spine3
     bBladeLight=True
     bSwingAnims=True
     SwingChannel=9
     SwingRate=1.250000
     SwingBone=spine1
     Clips(0)=BladeSlashR
     Clips(1)=BladeSlashL
     Clips(2)=BladeOverhead


}
