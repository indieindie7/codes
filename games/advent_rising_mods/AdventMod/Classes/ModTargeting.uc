//=============================================================================
// ModTargeting - fixes to the game's lock-on, run by ModMutator twice a second.
//
// Weapons on the ground: the lock-on (native, EonPlayerController.GetBestTarget)
// asks every actor Actor.GetTargetingPriority(); a dropped AdventWeapon answers its
// iBaseTargetingPriority, 1, in every state (it has no ETargetType, so the rule that
// keeps weapons for the pull and levitate powers never applies). Enemies answer 150,
// so a weapon wins whenever no enemy is near the reticle, and the lock (and the
// combat camera with it) jumps to a gun on the floor in the middle of a fight.
// Ammo needs no target (walking over a weapon takes its ammo), so while a hostile
// is alive within CombatRange, weapons farther than PickupReach from the player
// answer 0, which takes them off the list; close ones stay, to swap guns mid-fight.
//=============================================================================
class ModTargeting extends Info;

var array<AdventWeapon> Hidden;     // the weapons we took off the list...
var array<byte> HiddenPriority;     // ...and what they answered before
var bool bCombat;
var Actor LastTarget, LastUnder;     // bTargetLog

function Update(PlayerController PC)
{
	local AdventWeapon W;
	local Pawn P;
	local bool bWant;
	local int i, n;

	if (class'ModSettings'.default.bTargetLog && EonPlayerController(PC) != None && EonPlayerController(PC).CurrentTarget.Target != LastTarget)
	{
		LastTarget = EonPlayerController(PC).CurrentTarget.Target;
		class'ModSettings'.static.Note("targeting: lock-on " $ LastTarget);
	}
	if (class'ModSettings'.default.bTargetLog && EonPlayerController(PC) != None && EonPlayerController(PC).ActorUnderCrossHair != LastUnder)
	{
		LastUnder = EonPlayerController(PC).ActorUnderCrossHair;
		class'ModSettings'.static.Note("targeting: under the crosshair " $ LastUnder $ " (state " $ LastUnder.GetStateName() $ ", priority " $ LastUnder.iBaseTargetingPriority $ ")");
	}
	if (!class'ModSettings'.default.bCombatPickupFilter || PC == None || PC.Pawn == None)
	{
		ShowAll();
		return;
	}
	bWant = class'ModSettings'.default.bDebugCombat;
	ForEach DynamicActors(class'Pawn', P)
	{
		if (IsHostile(P) && VSize(P.Location - PC.Pawn.Location) < class'ModSettings'.default.CombatRange)
		{
			bWant = true;
			break;
		}
	}
	if (bWant != bCombat)
	{
		bCombat = bWant;
		if (bCombat)
			class'ModSettings'.static.Note("targeting: combat, weapons on the ground off the lock-on list");
		else
			class'ModSettings'.static.Note("targeting: no enemies near, weapons on the ground back on the lock-on list");
	}
	if (!bCombat)
	{
		ShowAll();
		return;
	}
	// let close ones back in
	for (i = Hidden.Length - 1; i >= 0; i--)
	{
		W = Hidden[i];
		if (W == None || W.bDeleteMe || W.Owner != None || VSize(W.Location - PC.Pawn.Location) <= class'ModSettings'.default.PickupReach)
		{
			if (W != None && !W.bDeleteMe)
				W.iBaseTargetingPriority = HiddenPriority[i];
			Hidden.Remove(i, 1);
			HiddenPriority.Remove(i, 1);
		}
	}
	ForEach DynamicActors(class'AdventWeapon', W)
	{
		if (W.Owner != None || W.iBaseTargetingPriority == 0 || VSize(W.Location - PC.Pawn.Location) <= class'ModSettings'.default.PickupReach)
			continue;
		Hidden[Hidden.Length] = W;
		HiddenPriority[HiddenPriority.Length] = W.iBaseTargetingPriority;
		W.iBaseTargetingPriority = 0;
		n++;
	}
	if (n > 0)
		class'ModSettings'.static.Note("targeting: " $ n $ " more weapons on the ground off the lock-on list (" $ Hidden.Length $ " in all)");
}

// the same test the game uses to keep a pawn off the lock-on list, the other way round
static function bool IsHostile(Pawn P)
{
	return P != None && P.Health > 0 && P.Controller != None && !P.IsHumanControlled() && !P.Controller.IsAmbientTeam() && !P.Controller.IsGoodGuyTeam() && P.ETargetType == ETT_Pawn;
}

function ShowAll()
{
	local int i;

	for (i = 0; i < Hidden.Length; i++)
		if (Hidden[i] != None && !Hidden[i].bDeleteMe)
			Hidden[i].iBaseTargetingPriority = HiddenPriority[i];
	Hidden.Length = 0;
	HiddenPriority.Length = 0;
}

event Destroyed()
{
	ShowAll();
	Super.Destroyed();
}

defaultproperties
{
}
