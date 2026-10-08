//=============================================================================
// ModMind - one creature's mind (see ModMinds, which owns and drives these).
//   traits   who it is: fixed for its life, from its species plus a little of its own
//            (Courage, Aggression, Discipline, Social, Cunning; 0..1);
//   feelings how it is right now: rise with what happens to it and around it, ebb with
//            time (Fear, Anger, Pressure = being shot at, Stress = what's left of it all);
//   task     what it is doing about it (pinned, in cover, falling back, flanking,
//            charging, circling), set by ModMinds, with its own destination and clock.
// The feelings also steer the game's own AI: the creature gets its own copy of its
// AdventPawnAbilities (the odds the game's Bot rolls in ExecuteAttack) and ModMinds
// moves those odds with the feelings (a scared soldier takes cover and flees more, an
// angry one charges, a pinned one stops shooting).
//=============================================================================
class ModMind extends Object;

// species
const S_Human = 0;
const S_Seeker = 1;
const S_SeekerVet = 2;      // elites, commanders, brutes
const S_Hound = 3;
const S_Construct = 4;      // shock troopers: no fear to speak of
const S_Other = 5;

// tasks
const T_None = 0;
const T_Pinned = 1;         // shot at hard: down, not shooting, in cover if there is any
const T_Cover = 2;          // moving to / holding a cover spot, peeking out to shoot
const T_FallBack = 3;       // scared: back toward the squad or away from the enemy
const T_Flank = 4;          // going round the side along paths
const T_Charge = 5;         // angry: straight at the enemy
const T_Circle = 6;         // a hound taking its place in the pack around the prey
const T_Panic = 7;          // broken: running

var Bot B;
var Pawn P;
var int Species;
var string SpeciesName;

var float Courage, Aggression, Discipline, Social, Cunning;
var float Fear, Anger, Pressure, Stress;

var int Task;
var float TaskTime, TaskLimit;      // seconds in the task, and its time limit
var vector TaskDest;
var float NextDecision;             // Level.TimeSeconds before which no new task is picked
var float NextPin;                  // ... and before which it can't be pinned again (it has to come up some time)
var float LastHit, LastNearMiss, LastLog;
var float HoldUntil;                 // fairness: no shooting before this (just spotted the player)
var float LastSawPlayer;             // when it last had the player in sight
var int AimHeld;                     // fairness: frames its aim was held back (MINDLIST)
var bool bOrderDone;                 // it has acted on the current order
var float LastFlank;                // when it last went round the side (flankers rest after)
var int NearMisses, Hits;
var float CircleAngle;              // T_Circle: where around the prey (radians)

// the abilities: ours (a copy only this pawn uses) and the game's values the feelings start from
var AdventPawnAbilities Own;
var float BaseCover, BaseFlee, BaseCharge, BaseEnrage, BaseDodge, BaseRandomDodge, BaseAttack, BaseCrouch, BaseReaction;
var bool bOwnAbility;
var bool bHeldFire;                 // we switched the bot's fire off (pinned, or no ranged token)
var bool bPinHold;                  // ... because it is pinned
// attack tokens (ModMinds.Deal, after DOOM 2016 and U2FairFights): only creatures fighting the player are
// gated; a ranged token lets it shoot, a melee token lets it charge, leap or strike
var bool bTokenGated, bRangedToken, bMeleeToken;
var float LastRanged, LastMelee;
var float BaseMelee, BaseLeapAttack, BaseChargeAb;
var bool bCrouched;                 // we crouched the pawn

function string Describe()
{
	local string T;

	if (bTokenGated)
	{
		T = " tokens";
		if (bRangedToken)
			T = T $ " R";
		if (bMeleeToken)
			T = T $ " M";
		if (!bRangedToken && !bMeleeToken)
			T = T $ " -";
	}
	return SpeciesName $ " fear " $ Pct(Fear) $ " anger " $ Pct(Anger) $ " pressure " $ Pct(Pressure)
		$ " stress " $ Pct(Stress) $ " task " $ TaskName(Task) $ T;
}

static function string Pct(float F)
{
	return string(int(F * 100 + 0.5));
}

static function string TaskName(int T)
{
	switch (T)
	{
		case T_None: return "none";
		case T_Pinned: return "pinned";
		case T_Cover: return "cover";
		case T_FallBack: return "fallback";
		case T_Flank: return "flank";
		case T_Charge: return "charge";
		case T_Circle: return "circle";
		case T_Panic: return "panic";
	}
	return "?";
}

// traits from the species, each nudged by up to +-Spread for this one creature
function SetSpecies(int S, float Spread)
{
	Species = S;
	switch (S)
	{
		case S_Human:
			SpeciesName = "human";
			Courage = 0.45; Aggression = 0.45; Discipline = 0.5; Social = 0.75; Cunning = 0.6;
			break;
		case S_Seeker:
			// a cult's foot soldiers: obedient, brave, not clever, shaken more by the
			// enemy's fire than by their own dead
			SpeciesName = "seeker";
			Courage = 0.7; Aggression = 0.65; Discipline = 0.75; Social = 0.35; Cunning = 0.45;
			break;
		case S_SeekerVet:
			SpeciesName = "seeker veteran";
			Courage = 0.85; Aggression = 0.7; Discipline = 0.85; Social = 0.3; Cunning = 0.7;
			break;
		case S_Hound:
			// a pack predator: brave in numbers, quick to rage when the pack is hurt,
			// knows nothing of cover but circles its prey
			SpeciesName = "hound";
			Courage = 0.6; Aggression = 0.9; Discipline = 0.15; Social = 0.9; Cunning = 0.65;
			break;
		case S_Construct:
			SpeciesName = "construct";
			Courage = 1.0; Aggression = 0.6; Discipline = 1.0; Social = 0.0; Cunning = 0.3;
			break;
		default:
			SpeciesName = "other";
			Courage = 0.5; Aggression = 0.5; Discipline = 0.5; Social = 0.5; Cunning = 0.5;
	}
	if (S != S_Construct)
	{
		Courage = FClamp(Courage + (FRand() * 2 - 1) * Spread, 0, 1);
		Aggression = FClamp(Aggression + (FRand() * 2 - 1) * Spread, 0, 1);
		Discipline = FClamp(Discipline + (FRand() * 2 - 1) * Spread, 0, 1);
		Social = FClamp(Social + (FRand() * 2 - 1) * Spread, 0, 1);
		Cunning = FClamp(Cunning + (FRand() * 2 - 1) * Spread, 0, 1);
	}
}

// what happens to it ----------------------------------------------------------------

// a shot went past close (Closeness 0..1: 1 = brushed it)
function NearMiss(float Closeness, float Now)
{
	NearMisses++;
	LastNearMiss = Now;
	Pressure = FMin(1, Pressure + (0.05 + 0.09 * Closeness) * (1.15 - Discipline));
	Fear = FMin(1, Fear + 0.012 * Closeness * (1 - Courage));
	Stress = FMin(1, Stress + 0.008);
}

// it was hit (Share = the damage as a part of its full health)
function Hurt(float Share, float Now)
{
	Hits++;
	LastHit = Now;
	Pressure = FMin(1, Pressure + 0.15 + Share);
	Fear = FMin(1, Fear + (0.03 + Share * 0.8) * (1.1 - Courage));
	Anger = FMin(1, Anger + (0.04 + Share * 0.8) * Aggression);
	Stress = FMin(1, Stress + 0.03 + 0.5 * Share);
}

// one of its own died where it could see (Kin: same species; Gory: came apart)
function SawDeath(bool bKin, bool bGory, float Now)
{
	local float K;

	K = 0.3;
	if (bKin)
		K = 1.0;
	if (bGory)
		K *= 1.6;
	Fear = FMin(1, Fear + K * 0.18 * Social * (1.1 - Courage));
	Anger = FMin(1, Anger + K * 0.25 * Social * Aggression);
	Stress = FMin(1, Stress + 0.12 * K);
}

// the enemy is right on top of it
function Crowded(float DeltaTime)
{
	Fear = FMin(1, Fear + DeltaTime * 0.15 * (1 - Courage));
	Anger = FMin(1, Anger + DeltaTime * 0.2 * Aggression);
}

// time heals: pressure goes in seconds, fear and anger in tens of seconds; the
// squad's strength (Morale 0..1) and its own health steady or shake it
function Ebb(float DeltaTime, float Now, float Morale, float HealthShare)
{
	local float Calm;

	Calm = 1;
	if (Now - LastNearMiss < 1.0 || Now - LastHit < 1.5)
		Calm = 0.2;                     // still being shot at
	Pressure = FMax(0, Pressure - DeltaTime * (0.2 + 0.3 * Discipline) * FMax(Calm, 0.5));
	Fear = FMax(0, Fear - DeltaTime * (0.02 + 0.05 * Courage) * Calm);
	Anger = FMax(0, Anger - DeltaTime * 0.04);
	Stress = FMax(0, Stress - DeltaTime * 0.02);
	// a creature alone and bleeding gets more afraid by itself
	if (HealthShare < 0.4)
		Fear = FMin(1, Fear + DeltaTime * 0.03 * (1 - Courage));
	if (Morale < 0.5)
		Fear = FMin(1, Fear + DeltaTime * 0.03 * (0.5 - Morale) * Social * (1 - Courage));
	// stress lowers the floor fear and pressure can drop to
	Fear = FMax(Fear, Stress * 0.25 * (1 - Courage));
}

defaultproperties
{
}
