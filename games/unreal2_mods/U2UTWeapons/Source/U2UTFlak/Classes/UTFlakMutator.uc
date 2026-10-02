//=============================================================================
// UTFlakMutator - puts Unreal Tournament's Flak Cannon into Unreal II.
//
// bReplaceGrenadeLauncher (default on): whenever the player gets the grenade
//   launcher or a variant of it (pickup, level start, tutorial, saved
//   inventory), it is swapped for the Flak Cannon: shotgun shells on primary,
//   the launcher's six grenade types on alt fire (middle mouse cycles them;
//   bind MiddleMouse=NextGrenadeType in User.ini).
// bReplaceAssaultRifle (default on): the Assault Rifle becomes UT's Ripper -
//   the rifle's bullets on primary, UT's ricocheting razor disc on alt fire,
//   both using rifle ammo. (The tutorial's own rifle is left alone: its range
//   targets react to its special damage types.)
// bReplaceDispersion (default on): the starting Dispersion Pistol becomes UT's
//   GES Bio Rifle - sticky gel on primary, a charged glob on alt fire, using
//   the pistol's recharging ammo. (The tutorial's pistol is left alone.)
// bReplaceShotgun (default on): there is no shotgun - it becomes the Flak Cannon,
//   which fires its shells (the shells you carry stay yours).
// bGiveOnSpawn (default off): also hand the flak out on every spawn (testing).
//
// Add with ?Mutator=U2UTFlak.UTFlakMutator (or in User.ini's [DefaultPlayer]
// Mutator=). Settings live in User.ini under [U2UTFlak.UTFlakMutator].
//=============================================================================
class UTFlakMutator extends Mutator
	config(User);

var() config bool bReplaceGrenadeLauncher;
var() config bool bGiveOnSpawn;
var() config bool bReplaceAssaultRifle;
var() config bool bReplaceDispersion;
var() config bool bReplaceShotgun;

var Pawn Armed;   // last pawn bGiveOnSpawn handled

event PostBeginPlay()
{
	Super.PostBeginPlay();
	SaveConfig();   // write the settings to User.ini so they can be edited
}

// rename the launcher pickups (the swap itself happens once it's picked up)
function bool CheckReplacement(Actor Other, out byte bSuperRelevant)
{
	if (bReplaceGrenadeLauncher && ClassIsChildOf(Other.Class, class'weaponGrenadeLauncher'))
		weaponGrenadeLauncher(Other).PickupMessage = "You got the Flak Cannon.";
	if (bReplaceAssaultRifle && Other.Class == class'weaponAssaultRifle')
		weaponAssaultRifle(Other).PickupMessage = "You got the Ripper.";
	if (bReplaceShotgun && Other.Class == class'weaponShotgun')
		weaponShotgun(Other).PickupMessage = "You got the Flak Cannon.";
	if (bReplaceDispersion && Other.Class == class'weaponDispersion')
		weaponDispersion(Other).PickupMessage = "You got the GES Bio Rifle.";
	return true;
}

function WeaponInvUTFlak GiveFlak(Pawn P)
{
	local Inventory Inv;

	P.GiveWeapon("U2UTFlak.WeaponInvUTFlak");
	for (Inv = P.Inventory; Inv != None; Inv = Inv.Inventory)
		if (WeaponInvUTFlak(Inv) != None)
		{
			Log("U2UTFlak: gave the Flak Cannon to "$P$" ammo="$WeaponInvUTFlak(Inv).AmmoType);
			return WeaponInvUTFlak(Inv);
		}
	return None;
}

function Inventory FindExact(Pawn P, class<Inventory> C)
{
	local Inventory Inv;
	for (Inv = P.Inventory; Inv != None; Inv = Inv.Inventory)
		if (Inv.Class == C)
			return Inv;
	return None;
}

// the grenade launcher, or a variant of it (the tutorial has its own)
function Weapon FindLauncher(Pawn P)
{
	local Inventory Inv;
	for (Inv = P.Inventory; Inv != None; Inv = Inv.Inventory)
		if (weaponInvGrenadeLauncher(Inv) != None && !Inv.bDeleteMe)
			return Weapon(Inv);
	return None;
}

function ReplaceLauncher(PlayerController PC, Pawn P, Weapon GL)
{
	local WeaponInvUTFlak Flak;

	Flak = WeaponInvUTFlak(FindExact(P, class'WeaponInvUTFlak'));
	if (Flak == None)
		Flak = GiveFlak(P);
	if (Flak == None)
		return;

	// holding (or bringing up) the launcher: switch to the flak first and
	// remove the launcher once it's been put away
	if (P.Weapon == GL || P.PendingWeapon == GL)
	{
		if (P.PendingWeapon != Flak)
			PC.GetWeapon(class'WeaponInvUTFlak');
		return;
	}

	// the tutorial's launcher tells the level when you alt-fire (its "switch
	// grenade type" lesson waits for that); the flak's alt-fire takes over
	if (GL.IsA('WeaponTutorialInvGrenadeLauncher'))
		Flak.bTutorialAltFireEvent = true;

	P.DeleteInventory(GL);
	GL.Destroy();
	Log("U2UTFlak: replaced the grenade launcher with the Flak Cannon");
}

// swap a U2 weapon for its UT version (which takes over the same ammo, still in
// the inventory): give the new one, switch to it if the old one is in hand,
// then remove the old one once it's been put away
function ReplaceWeapon(PlayerController PC, Pawn P, Weapon Old, class<Weapon> NewClass)
{
	local Weapon NewW;

	NewW = Weapon(FindExact(P, NewClass));
	if (NewW == None)
	{
		P.GiveWeapon(string(NewClass));
		NewW = Weapon(FindExact(P, NewClass));
		if (NewW == None)
			return;
		Log("U2UTFlak: gave "$NewW.ItemName$" to "$P);
	}
	if (P.Weapon == Old || P.PendingWeapon == Old)
	{
		if (P.PendingWeapon != NewW)
			PC.GetWeapon(NewClass);
		return;
	}
	P.DeleteInventory(Old);
	Old.Destroy();
	Log("U2UTFlak: replaced "$Old.Class.Name$" with "$NewW.ItemName);
}

event Tick(float DeltaTime)
{
	local Controller C;
	local Pawn P;
	local Weapon GL, AR, DP, SG;

	for (C = Level.ControllerList; C != None; C = C.NextController)
	{
		P = C.Pawn;
		if (PlayerController(C) == None || P == None || P.Health <= 0)
			continue;

		if (bGiveOnSpawn && P != Armed)
		{
			Armed = P;
			if (FindExact(P, class'WeaponInvUTFlak') == None)
				GiveFlak(P);
		}

		if (bReplaceGrenadeLauncher)
		{
			GL = FindLauncher(P);
			if (GL != None)
				ReplaceLauncher(PlayerController(C), P, GL);
		}

		if (bReplaceAssaultRifle)
		{
			AR = Weapon(FindExact(P, class'weaponInvAssaultRifle'));
			if (AR != None)
				ReplaceWeapon(PlayerController(C), P, AR, class'WeaponInvUTRipper');
		}

		if (bReplaceShotgun)
		{
			SG = Weapon(FindExact(P, class'weaponInvShotgun'));
			if (SG != None)
				ReplaceWeapon(PlayerController(C), P, SG, class'WeaponInvUTFlak');
		}

		if (bReplaceDispersion)
		{
			DP = Weapon(FindExact(P, class'weaponInvDispersion'));
			if (DP != None)
				ReplaceWeapon(PlayerController(C), P, DP, class'WeaponInvUTBio');
		}
	}
}

defaultproperties
{
	bReplaceGrenadeLauncher=True
	bGiveOnSpawn=False
	bReplaceAssaultRifle=True
	bReplaceDispersion=True
	bReplaceShotgun=True
	RemoteRole=ROLE_None
}
