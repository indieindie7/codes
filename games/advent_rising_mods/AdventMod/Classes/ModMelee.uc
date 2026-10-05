//=============================================================================
// ModMelee - melee weapons (ModGore spawns it). For now one: the energy blade (ModBlade).
//   - Enemies sometimes drop one when they die (BladeDropChance, MaxPickups in a level).
//   - Walking over it picks it up. It rides on the player's back and is in the hand while a
//     melee attack plays; the melee key swings it with the game's own melee moves.
//   - A melee hit with the blade does BladeDamage times the punch's damage, cuts, and on a
//     kill takes off the part it hit (ModSever, no dice). Each hit uses one of BladeCharges;
//     at none the blade burns out.
// The blade stays with the player from level to level (SavedCharges, for the game's run).
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
var config vector HandOffset, BackOffset;
var config bool bTestBlade;        // testing: the player starts with one

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
	}
	else
	{
		Holder.AttachToBone(Carried, 'spine2');
		Carried.SetRelativeLocation(BackOffset);
		Carried.SetRelativeRotation(BackRot);
	}
	bInHand = bHand;
}

function BurnOut()
{
	Say("The energy blade burns out.");
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
	B.LifeSpan = 150;
	Pickups[Pickups.Length] = B;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: a blade dropped at " $ B.Location);
}

// ModGoreRules: every hit passes here first. A melee move by the blade's holder becomes a
// blade strike. Returns the damage to deal.
function int Strike(int Damage, Pawn Injured, Pawn By, vector Spot, class<DamageType> Type)
{
	local vector Dir;

	if (Carried == None || By == None || By != Holder || Injured == None || Injured == By || Type == None || Damage <= 0)
		return Damage;
	if (Left(Caps(string(Type.Name)), 16) != "DAMAGEHANDATTACK")
		return Damage;
	Damage = int(Damage * BladeDamage);
	Dir = Normal(Injured.Location - By.Location);
	if (Gore != None)
	{
		Gore.CutBlood(Spot, Dir, Gore.BloodKind(Injured));
		if (Gore.Severer != None)
			Gore.Severer.bForce = true;      // a kill by this hit takes the part off (and isn't blown apart)
	}
	Charges--;
	default.SavedCharges = Charges;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("melee: blade strike on " $ Injured $ " (" $ Type.Name $ "), damage " $ Damage $ ", " $ Charges $ " left");
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
     BackRot=(Pitch=-12000,Yaw=16384,Roll=0)
     BackOffset=(X=0.000000,Y=-8.000000,Z=-10.000000)
}
