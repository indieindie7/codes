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
//
// Difficulty (the Gameplay page): the level's own per-difficulty multipliers
// (LevelInfo.X_DamageMultiplier for the player's hits, X_HealthMultiplier for
// the hits the player takes, applied in Actor.ProcessTakeDamage) scaled by
// DamageDealt / DamageTaken, and by the boss settings too while a boss (a
// hostile with the top lock-on priority, 255) is alive within twice CombatRange.
// Bosses' own health is left alone: their health bars and fight phases read it
// against its default.
//=============================================================================
class ModTargeting extends Info;

var array<AdventWeapon> Hidden;     // the weapons we took off the list...
var array<byte> HiddenPriority;     // ...and what they answered before
var bool bCombat;
var bool bLevelSaved, bBossNear;
var Range Orig[8];                  // the level's multipliers as it set them: damage Easy/Normal/Hard/God, health the same
var Actor LastTarget, LastUnder;     // bTargetLog

function Update(PlayerController PC)
{
	local AdventWeapon W;
	local Pawn P;
	local bool bWant, bBoss;
	local int i, n;
	local float D;

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
	if (PC == None || PC.Pawn == None)
	{
		ShowAll();
		return;
	}
	bWant = class'ModSettings'.default.bDebugCombat;
	bBoss = false;
	ForEach DynamicActors(class'Pawn', P)
	{
		if (!IsHostile(P))
			continue;
		D = VSize(P.Location - PC.Pawn.Location);
		if (D < class'ModSettings'.default.CombatRange)
			bWant = true;
		if (P.iBaseTargetingPriority >= 255 && D < 2 * class'ModSettings'.default.CombatRange)
			bBoss = true;
	}
	class'ModSettings'.default.bInCombat = bWant;
	if (bBoss != bBossNear)
	{
		bBossNear = bBoss;
		class'ModSettings'.static.Note("difficulty: boss " $ Eval3(bBossNear, "near, boss settings on", "gone, boss settings off"));
	}
	Difficulty();
	if (!class'ModSettings'.default.bCombatPickupFilter)
	{
		bCombat = false;
		ShowAll();
		return;
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

static function string Eval3(bool B, string T, string F)
{
	if (B)
		return T;
	return F;
}

// the level's damage multipliers = its own x the Gameplay page's settings
function Difficulty()
{
	local float Dealt, Taken, S;
	local LevelInfo L;

	L = Level;
	if (!bLevelSaved)
	{
		// what LevelInfo.PostBeginPlay made of them: the class defaults / the level's
		// DifficultyGlobalScalar (not the current values: a saved game may carry ours)
		bLevelSaved = true;
		S = 1 / FMax(L.DifficultyGlobalScalar, 0.0001);
		Orig[0] = Scaled(L.default.Easy_DamageMultiplier, S);  Orig[1] = Scaled(L.default.Normal_DamageMultiplier, S);
		Orig[2] = Scaled(L.default.Hard_DamageMultiplier, S);  Orig[3] = Scaled(L.default.God_DamageMultiplier, S);
		Orig[4] = Scaled(L.default.Easy_HealthMultiplier, S);  Orig[5] = Scaled(L.default.Normal_HealthMultiplier, S);
		Orig[6] = Scaled(L.default.Hard_HealthMultiplier, S);  Orig[7] = Scaled(L.default.God_HealthMultiplier, S);
		class'ModSettings'.static.Note("difficulty: level scalar " $ L.DifficultyGlobalScalar $ ", normal damage x" $ Orig[1].Min $ ", normal health x" $ Orig[5].Min);
	}
	Dealt = class'ModSettings'.default.DamageDealt;
	Taken = class'ModSettings'.default.DamageTaken;
	if (bBossNear)
	{
		Dealt *= class'ModSettings'.default.BossDamageDealt;
		Taken *= class'ModSettings'.default.BossDamageTaken;
	}
	Dealt = FMax(Dealt, 0.01);
	Taken = FMax(Taken, 0.01);
	// damage the player takes is divided by the health multiplier
	L.Easy_DamageMultiplier = Scaled(Orig[0], Dealt);
	L.Normal_DamageMultiplier = Scaled(Orig[1], Dealt);
	L.Hard_DamageMultiplier = Scaled(Orig[2], Dealt);
	L.God_DamageMultiplier = Scaled(Orig[3], Dealt);
	L.Easy_HealthMultiplier = Scaled(Orig[4], 1 / Taken);
	L.Normal_HealthMultiplier = Scaled(Orig[5], 1 / Taken);
	L.Hard_HealthMultiplier = Scaled(Orig[6], 1 / Taken);
	L.God_HealthMultiplier = Scaled(Orig[7], 1 / Taken);
}

static function Range Scaled(Range R, float F)
{
	R.Min *= F;
	R.Max *= F;
	return R;
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
	if (bLevelSaved)
	{
		Level.Easy_DamageMultiplier = Orig[0];  Level.Normal_DamageMultiplier = Orig[1];
		Level.Hard_DamageMultiplier = Orig[2];  Level.God_DamageMultiplier = Orig[3];
		Level.Easy_HealthMultiplier = Orig[4];  Level.Normal_HealthMultiplier = Orig[5];
		Level.Hard_HealthMultiplier = Orig[6];  Level.God_HealthMultiplier = Orig[7];
	}
	Super.Destroyed();
}

defaultproperties
{
}
