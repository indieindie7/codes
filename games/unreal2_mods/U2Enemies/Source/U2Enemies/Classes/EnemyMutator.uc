//=============================================================================
// EnemyMutator - makes Unreal II's iconic enemies play up to their looks.
//
// bAgileSkaarj: the Skaarj already carry dodge and leap AI that the game
//   holds back. Turned up: jump-dodges, dodging while closing in, faster
//   recovery, more leaps - closer to Unreal's acrobatic Skaarj.
// BerserkerOdds: some light Skaarj are Berserkers - they never fall back or
//   take cover, and close in to leap and slash with their wrist blades.
// FeralOdds: some unarmoured Izarians are feral - the four-armed body let
//   loose: erratic jumping charges, melee in reach, no cover (Rage's mutants).
// bIzarianDomes: the Izarians fight inside liquid-filled suits. A hit to the
//   dome breaches it: extra damage, fluid spraying out, suffocation damage
//   over time, and often panic. Aim for the bubble. (DomeRules / DomeLeak)
//
// Add with ?Mutator=U2Enemies.EnemyMutator or in User.ini's [DefaultPlayer]
// Mutator=. Settings: [U2Enemies.EnemyMutator] in User.ini.
//=============================================================================
class EnemyMutator extends Mutator
	config(User);

var() config bool  bAgileSkaarj;
var() config bool  bIzarianDomes;
var() config float DomeDamageScale;     // damage multiplier for dome hits
var() config float LeakDamagePerSecond; // suffocation once breached
var() config float LeakSeconds;
var() config float PanicOdds;           // chance a breached Izarian panics
var() config float BerserkerOdds;       // chance a light Skaarj is a melee Berserker
var() config float BerserkerSpeed;      // their run speed multiplier
var() config float FeralOdds;           // chance an unarmoured Izarian spawns feral
var() config float BreachFeralOdds;     // chance a breached Izarian goes feral instead of panicking
var() config float FeralSpeed;

struct PendingBoost
{
	var Pawn P;
	var float SpeedMul, HealthMul, ApplyAt;
};
var array<PendingBoost> Boosts;
var bool bDesignedSpawn;            // set by a director around its own spawns: no random variants
var array<Pawn> Ferals;

event PostBeginPlay()
{
	local DomeRules R;

	Super.PostBeginPlay();
	SaveConfig();
	if (bIzarianDomes)
	{
		R = Spawn(class'DomeRules');
		R.Settings = Self;
		if (Level.Game.GameRulesModifiers == None)
			Level.Game.GameRulesModifiers = R;
		else
			Level.Game.GameRulesModifiers.AddGameRules(R);
	}
}

// every actor passes through here as it starts, level-placed ones included
function bool CheckReplacement(Actor Other, out byte bSuperRelevant)
{
	if (bAgileSkaarj && Other.IsA('U2SkaarjBase') && U2PawnBasic(Other) != None)
		MakeAgile(U2PawnBasic(Other));
	// only light Skaarj have the blade set-up for it; level-scripted ones
	// (a Tag or Event wires them to the level) keep their behaviour
	if (!bDesignedSpawn && BerserkerOdds > 0 && Other.IsA('U2SkaarjLight') && U2PawnBasic(Other) != None
		&& Other.Tag == Other.Class.Name && Other.Event == '' && FRand() < BerserkerOdds)
		MakeBerserker(U2PawnBasic(Other));
	if (!bDesignedSpawn && FeralOdds > 0 && Other.IsA('U2Izarian') && U2PawnBasic(Other) != None && IsUnarmoured(Pawn(Other))
		&& Other.Tag == Other.Class.Name && Other.Event == '' && FRand() < FeralOdds)
		MakeFeral(U2PawnBasic(Other));
	return true;
}

// a Berserker never falls back or hides: it closes in, leaps and slashes
function MakeBerserker(U2PawnBasic P)
{
	local int i;

	for (i = 0; i < P.AttackPassiveBehaviors.Length; i++)
		if (P.AttackPassiveBehaviors[i].StateName == 'AttackFallback'
			|| P.AttackPassiveBehaviors[i].StateName == 'AttackMoveToCoverCombat')
			P.AttackPassiveBehaviors[i].bDisabled = true;
	for (i = 0; i < P.AttackPassiveUseCoverBehaviors.Length; i++)
		P.AttackPassiveUseCoverBehaviors[i].bDisabled = true;
	for (i = 0; i < P.AttackPassiveMeleeBehaviors.Length; i++)
		if (P.AttackPassiveMeleeBehaviors[i].StateName == 'AttackFallback')
			P.AttackPassiveMeleeBehaviors[i].bDisabled = true;
	for (i = 0; i < P.AttackActiveMeleeBehaviors.Length; i++)
		P.AttackActiveMeleeBehaviors[i].Odds = 1.0;
	for (i = 0; i < P.AttackActiveMeleeHitBehaviors.Length; i++)
		if (P.AttackActiveMeleeHitBehaviors[i].StateName == 'AttackTacticalRetreatMelee')
			P.AttackActiveMeleeHitBehaviors[i].bDisabled = true;

	P.BaseAggressiveness = FMax(P.BaseAggressiveness, 1.0);
	P.AttackMeleeMinTime = FMax(P.AttackMeleeMinTime, 2.0);
	P.AttackMeleeMaxTime = FMax(P.AttackMeleeMaxTime, 6.0);
	P.LeapToMeleeOdds = 1.0;
	P.LeapHighOdds = 0.7;
	P.LeapDelaySuccess = 0.8;
	P.LeapMaxDamage *= 1.6;
	P.Melee01MaxDamage *= 1.5;
	P.Melee02MaxDamage *= 1.5;
	Boost(P, BerserkerSpeed, 1.25);
}

// a feral Izarian: the four-armed body behind the soldier AI, let loose -
// erratic jumping charges, melee whenever it's in reach, never hides
function MakeFeral(U2PawnBasic P)
{
	local int i;
	local name S;

	if (P == None || IsFeral(P))
		return;
	Ferals[Ferals.Length] = P;
	for (i = 0; i < P.AttackActiveBehaviors.Length; i++)
	{
		S = P.AttackActiveBehaviors[i].StateName;
		if (S == 'AttackClose')          P.AttackActiveBehaviors[i].Odds = 0.9;
		else if (S == 'AttackTacticalMove') P.AttackActiveBehaviors[i].Odds = 0.3;
		else                             P.AttackActiveBehaviors[i].bDisabled = true;
	}
	for (i = 0; i < P.AttackPassiveBehaviors.Length; i++)
		if (P.AttackPassiveBehaviors[i].StateName != 'AttackStationary')
			P.AttackPassiveBehaviors[i].bDisabled = true;
	// keep one entry (standing its ground) so the AI always has a choice
	for (i = 0; i < P.AttackPassiveUseCoverBehaviors.Length; i++)
		if (P.AttackPassiveUseCoverBehaviors[i].StateName != 'AttackStationary')
			P.AttackPassiveUseCoverBehaviors[i].bDisabled = true;
	for (i = 0; i < P.AttackPassiveMeleeBehaviors.Length; i++)
		if (P.AttackPassiveMeleeBehaviors[i].StateName == 'AttackFallback')
			P.AttackPassiveMeleeBehaviors[i].bDisabled = true;
	for (i = 0; i < P.AttackActiveMeleeBehaviors.Length; i++)
		P.AttackActiveMeleeBehaviors[i].Odds = 1.0;

	P.MeleeOdds = 1.0;
	P.MeleeRange = FMax(P.MeleeRange, 60);
	P.BaseAggressiveness = FMax(P.BaseAggressiveness, 1.0);
	P.bJumpy = true;
	P.JumpyOdds = 0.6;
	P.bJumpDodges = true;
	P.RandomCloseDodgeOdds = FMax(P.RandomCloseDodgeOdds, 0.5);
	Boost(P, FeralSpeed, 1.0);
}

function bool IsFeral(Pawn P)
{
	local int i;
	for (i = 0; i < Ferals.Length; i++)
		if (Ferals[i] == P)
			return true;
	return false;
}

// speed and health are set again by the game once a pawn has spawned
// (difficulty scaling), so boosts are applied a tick later
function Boost(Pawn P, float SpeedMul, float HealthMul)
{
	local int i;
	i = Boosts.Length;
	Boosts.Length = i + 1;
	Boosts[i].P = P;
	Boosts[i].SpeedMul = SpeedMul;
	Boosts[i].HealthMul = HealthMul;
	Boosts[i].ApplyAt = Level.TimeSeconds + 0.1;
	Enable('Tick');
}

event Tick(float DeltaTime)
{
	local int i;

	for (i = Boosts.Length - 1; i >= 0; i--)
	{
		if (Boosts[i].P == None || Boosts[i].P.bDeleteMe)
			Boosts.Remove(i, 1);
		else if (Level.TimeSeconds >= Boosts[i].ApplyAt)
		{
			Boosts[i].P.GroundSpeed *= Boosts[i].SpeedMul;
			Boosts[i].P.Health = int(Boosts[i].P.Health * Boosts[i].HealthMul);
			Boosts.Remove(i, 1);
		}
	}
	for (i = Ferals.Length - 1; i >= 0; i--)
		if (Ferals[i] == None || Ferals[i].bDeleteMe)
			Ferals.Remove(i, 1);
	if (Boosts.Length == 0)
		Disable('Tick');
}

function bool IsUnarmoured(Pawn P)
{
	local string M;
	M = string(P.Mesh);
	return InStr(M, "NoArmor") >= 0 || InStr(M, "Bald") >= 0;
}

function MakeAgile(U2PawnBasic P)
{
	P.bJumpDodges = true;               // off in the stock game
	P.DodgeProjectileOdds = 1.0;
	P.DodgeInsteadofStrafeOdds = 1.0;
	P.RandomCloseDodgeOdds = FMax(P.RandomCloseDodgeOdds, 0.5);
	P.PostDodgeDelay = FMin(P.PostDodgeDelay, 0.35);
	P.JumpyOdds = FMax(P.JumpyOdds, 0.3);
	P.LeapHighOdds = FMax(P.LeapHighOdds, 0.5);
	P.LeapDelaySuccess *= 0.5;
	P.LeapDelayFailure *= 0.5;
}

defaultproperties
{
	bAgileSkaarj=True
	bIzarianDomes=True
	DomeDamageScale=1.500000
	LeakDamagePerSecond=10.000000
	LeakSeconds=8.000000
	PanicOdds=0.700000
	BerserkerOdds=0.350000
	BerserkerSpeed=1.250000
	FeralOdds=0.300000
	BreachFeralOdds=0.500000
	FeralSpeed=1.400000
	RemoteRole=ROLE_None
}
