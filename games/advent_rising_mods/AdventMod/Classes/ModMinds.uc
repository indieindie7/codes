//=============================================================================
// ModMinds - creatures with a psychology (AI design: AI-MINDS-DESIGN.md).
// One per level (ModMutator spawns it). Every AI soldier, Seeker and hound gets a
// ModMind: traits from its species plus a little of its own, and feelings (fear,
// anger, pressure from being shot at, stress) that rise with what happens and ebb with
// time. Each tick ModMinds:
//   1. senses for them: shots flying past (the player's projectiles, and the player's
//      aim line while firing), hits and deaths (ModMindRules), the enemy too close,
//      the squad thinning out;
//   2. lets the feelings steer the game's own AI: each creature gets its own copy of
//      its AdventPawnAbilities, whose odds the game's Bot rolls when it picks what to
//      do next (cover, flee, charge, dodge, attack, how quickly it reacts);
//   3. decides, a few times a second and never mid-animation or mid-script:
//      - suppression: pressure past a threshold pins a creature (head down, no
//        shooting) and sends it to cover if any is near; it peeks out again when the
//        pressure ebbs;
//      - cover: a spot the enemy can't see at crouch height but can be shot from with
//        one step sideways, found among the level's path nodes (or the level's own
//        cover points), close, not toward the enemy, not taken by a squad mate;
//      - fear: falls back toward the squad, and the badly broken panic and run;
//      - anger: charges (Seekers enrage, hounds pounce);
//      - the squad: one cunning member at a time goes round the side along paths
//        while the others keep the enemy busy; losses shake a squad (humans fall back
//        together) or enrage it (Seekers, hounds);
//      - hounds hunt as a pack: they take places around the prey before they close in.
// The game's AI still does everything else (aiming, shooting, animation, its own
// scripts); a task the mind gives runs through the Bot's own Do* functions and its
// squad's AssignState, so the game's state locks and scripted sequences win.
// Config [AdventMod.ModMinds]: bMinds (off = the stock AI), bMindLog (every feeling
// and decision in AdventNative.log), the thresholds below.
//=============================================================================
class ModMinds extends Info
	config(AdventMod);

var config bool bMinds;
var config bool bMindLog;
var config float TraitSpread;       // how far one creature's traits stray from its species'
var config float PinPressure;       // pressure that pins (0..1)
var config float FreePressure;      // ... and lets go again
var config float FleeFear;          // fear that makes it fall back
var config float PanicFear;         // ... and run (with low courage)
var config float ChargeAnger;       // anger that makes it charge
var config float CoverReach;        // how far it looks for cover (world units)
var config float NearMissReach;     // how close a shot must pass to count (world units)
var config float FlankEvery;        // seconds between flank orders per squad
var config float HoundCircle;       // how far from the prey hounds circle (world units)

var array<ModMind> Minds;
var ModMindRules Rules;
var float AdoptWait, FlankWait, TokenWait;
var int ShotsAtPlayer, ShotsUntokened;              // projectiles fired by creatures fighting the player (MINDLIST)
var config int RangedTokens;        // creatures that may shoot at the player at once ...
var config int RangedPer;           // ... plus one per this many engaged beyond four
var config int MeleeTokens;         // creatures that may charge, leap or strike at once ...
var config int MeleePer;            // ... plus one per this many engaged beyond four
var config float TokenTime;         // seconds between deals

// shots in flight: where each was last tick (for the segment it flew)
struct Shot
{
	var Projectile Pr;
	var vector Last;
};
var array<Shot> Shots;

// cover spots handed out (one creature per spot)
struct Claim
{
	var vector Spot;
	var ModMind M;
};
var array<Claim> Claims;

function PostBeginPlay()
{
	Super.PostBeginPlay();
	if (!bMinds)
		return;
	Rules = Spawn(class'ModMindRules');
	Rules.Minds = self;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = Rules;
	else
		Level.Game.GameRulesModifiers.AddGameRules(Rules);
	class'ModSettings'.static.Note("minds: on (spread " $ TraitSpread $ ", pin " $ PinPressure $ ", flee " $ FleeFear $ ", charge " $ ChargeAnger $ ")");
}

function Log2(string S)
{
	if (bMindLog)
		class'ModSettings'.static.Note("minds: " $ S);
}

// adopting -------------------------------------------------------------------------

function int SpeciesOf(Pawn P)
{
	if (P.IsA('SeekerDogNative'))
		return 3/*S_Hound*/;
	if (P.IsA('ShockTrooperNative'))
		return 4/*S_Construct*/;
	if (P.IsA('SeekerEliteNative') || P.IsA('SeekerCommander') || P.IsA('SeekerPilot_Brute'))
		return 2/*S_SeekerVet*/;
	if (P.IsA('Seeker'))
		return 1/*S_Seeker*/;
	if (P.IsA('Human') || P.IsA('BountyHunterB') || P.IsA('AurelianNative'))
		return 0/*S_Human*/;
	return 5/*S_Other*/;
}

function ModMind MindOf(Pawn P)
{
	local int i;

	if (P == None)
		return None;
	for (i = 0; i < Minds.Length; i++)
		if (Minds[i].P == P)
			return Minds[i];
	return None;
}

function Adopt()
{
	local Bot B;
	local ModMind M;
	local int i;
	local bool bKnown;

	// forget the gone; a pawn the game recycled for its spawners is a new creature
	for (i = Minds.Length - 1; i >= 0; i--)
	{
		M = Minds[i];
		if (M.B == None || M.B.bDeleteMe || M.B.Pawn != M.P || M.P == None || M.P.bDeleteMe)
		{
			Release(M);
			Minds.Remove(i, 1);
		}
	}
	foreach DynamicActors(class'Bot', B)
	{
		if (B.Pawn == None || B.Pawn.Health <= 0 || B.Squad == None || B.Pawn.IsA('Vehicle'))
			continue;
		bKnown = false;
		for (i = 0; i < Minds.Length; i++)
			if (Minds[i].B == B)
			{
				bKnown = true;
				break;
			}
		if (bKnown)
			continue;
		M = new(self) class'ModMind';
		M.B = B;
		M.P = B.Pawn;
		M.SetSpecies(SpeciesOf(B.Pawn), TraitSpread);
		M.CircleAngle = FRand() * 6.2832;
		OwnAbility(M);
		Minds[Minds.Length] = M;
		Log2("adopted " $ B.Pawn.Name $ " (" $ M.SpeciesName $ ") courage " $ M.Pct(M.Courage) $ " aggression " $ M.Pct(M.Aggression)
			$ " discipline " $ M.Pct(M.Discipline) $ " social " $ M.Pct(M.Social) $ " cunning " $ M.Pct(M.Cunning));
	}
}

// the pawn's own copy of its abilities (pawns of a class share one by default)
function OwnAbility(ModMind M)
{
	local AdventPawnAbilities A, Copy;
	local int i;
	local string Names;
	local array<string> List;

	A = M.P.Ability;
	if (A == None)
		return;
	if (A.Outer == self)
	{
		M.Own = A;                      // already ours (a recycled pawn)
	}
	else
	{
		Copy = new(self) class'AdventPawnAbilities';
		Names = "SightRadius PeripheralVision PeripheralVisionRotationOffset ReactionTime AwareRange AttackAbility BehaviorAbility IssueOrderAbility CrouchAbility AltFireAbility MeleeAttackAbility RunningAttackAbility FinishingMoveAbility PreferredMinRange PreferredMaxRange ShootAbility SnipeAbility SnipeMinRange SnipeMaxRange MeleeRange ThreatProximity bKeepWeaponAimed bAllowFriendlyFire bCanBeSquadLeader";
		Names = Names $ " bStayWithinFormation bStayNearFormation bCanRemoveStickyGrenade bCanIdle bSquadLeaderHangBack bCrouchIfEnemyTooClose bCelebrateGroupKills CelebrateAbility ThrowGrenadeAbility TauntAbility DesiredLeapSpeed MaxLeapSpeed LeapAbility LeapMinRange LeapMaxRange RandomLeapAbility EnrageAbility StartleAbility CowardAbility PanicAbility WanderAbility LeapAttackAbility LeapAttackOffset LeapAttackMinRange";
		Names = Names $ " LeapAttackMaxRange WallJumpAbility DodgeAbility RandomDodgeAbility BlockingAbility BlockingAttackAbility BlockingTime StalkingAbility StalkingMinRange StalkingMaxRange PacingAbility ChargeAbility RandomChargeAbility StandOnVehicleAbility CoverPointAbility HearingThreshold MaxConfusionTime MaxStunTime FleeAbility InvestigateAbility AirStrafeAttackAbility NearbyActionRadius";
		while (Names != "")
		{
			i = InStr(Names, " ");
			if (i < 0)
			{
				List[List.Length] = Names;
				break;
			}
			List[List.Length] = Left(Names, i);
			Names = Mid(Names, i + 1);
		}
		for (i = 0; i < List.Length; i++)
			Copy.SetPropertyText(List[i], A.GetPropertyText(List[i]));
		M.P.Ability = Copy;
		M.Own = Copy;
		A = Copy;
	}
	M.BaseCover = A.CoverPointAbility;
	M.BaseFlee = A.FleeAbility;
	M.BaseCharge = A.RandomChargeAbility;
	M.BaseEnrage = A.EnrageAbility;
	M.BaseDodge = A.DodgeAbility;
	M.BaseRandomDodge = A.RandomDodgeAbility;
	M.BaseAttack = A.AttackAbility;
	M.BaseCrouch = A.CrouchAbility;
	M.BaseReaction = A.ReactionTime;
	M.BaseMelee = A.MeleeAttackAbility;
	M.BaseLeapAttack = A.LeapAttackAbility;
	M.BaseChargeAb = A.ChargeAbility;
	M.bOwnAbility = true;
}

// a creature leaves: the fire switch and crouch go back, its cover spot is free
function Release(ModMind M)
{
	local int i;

	if (M.B != None && !M.B.bDeleteMe && M.bHeldFire)
		M.B.bDisableTimedFire = false;
	if (M.P != None && !M.P.bDeleteMe && M.bCrouched)
		M.P.ShouldCrouch(false);
	M.bHeldFire = false;
	M.bCrouched = false;
	for (i = Claims.Length - 1; i >= 0; i--)
		if (Claims[i].M == M)
			Claims.Remove(i, 1);
}

// senses ---------------------------------------------------------------------------

// the closest a segment comes to a point
static function float SegmentDistance(vector A, vector B, vector P, out float T)
{
	local vector D;
	local float L2;

	D = B - A;
	L2 = D dot D;
	if (L2 < 1)
	{
		T = 0;
		return VSize(P - A);
	}
	T = FClamp(((P - A) dot D) / L2, 0, 1);
	return VSize(P - (A + D * T));
}

// shots flying past: each projectile's flight since last tick, against every creature
// whose enemy fired it
function SenseShots()
{
	local Projectile Pr;
	local int i, j;
	local bool bSeen;
	local float D, T;
	local ModMind M;
	local array<Shot> Now;
	local Shot S;

	foreach DynamicActors(class'Projectile', Pr)
	{
		if (Pr.Instigator == None || Pr.bDeleteMe)
			continue;
		S.Pr = Pr;
		S.Last = Pr.Location;
		bSeen = false;
		for (j = 0; j < Shots.Length; j++)
			if (Shots[j].Pr == Pr)
			{
				S.Last = Shots[j].Last;
				bSeen = true;
				break;
			}
		if (!bSeen)
		{
			S.Last = Pr.Location - Normal(Pr.Velocity) * 200;   // just fired: the bit it already flew
			M = MindOf(Pr.Instigator);
			if (M != None && M.B.EnemyInfo.Enemy != None && PlayerController(M.B.EnemyInfo.Enemy.Controller) != None)
			{
				ShotsAtPlayer++;
				if (M.bTokenGated && !M.bRangedToken)
				{
					ShotsUntokened++;
					if (bMindLog && ShotsUntokened < 40)
						Log2(M.P.Name $ " fired without a token (state " $ M.B.GetStateName() $ ", fire held " $ M.bHeldFire $ ", task " $ M.TaskName(M.Task) $ ")");
				}
			}
		}
		for (i = 0; i < Minds.Length; i++)
		{
			M = Minds[i];
			if (M.B.EnemyInfo.Enemy != Pr.Instigator || M.P == Pr.Instigator)
				continue;
			D = SegmentDistance(S.Last, Pr.Location, M.P.Location, T);
			if (D < NearMissReach)
			{
				M.NearMiss(1 - D / NearMissReach, Level.TimeSeconds);
				if (bMindLog && Level.TimeSeconds - M.LastLog > 0.5)
				{
					M.LastLog = Level.TimeSeconds;
					Log2(M.P.Name $ " shot past at " $ int(D) $ ": " $ M.Describe());
				}
			}
		}
		S.Last = Pr.Location;
		Now[Now.Length] = S;
	}
	Shots = Now;
}

// the player's aim line while firing (weapons without a projectile, and for everyone
// standing near the line the player is spraying along)
function SenseAim(float DeltaTime)
{
	local PlayerController PC;
	local EonPlayerController E;
	local AdventWeapon W;
	local vector From, To;
	local float D, T;
	local int i;
	local ModMind M;

	PC = Level.GetLocalPlayerController();
	E = EonPlayerController(PC);
	if (E == None || PC.Pawn == None)
		return;
	W = AdventWeapon(PC.Pawn.RightWeapon);
	if (W == None || !W.bIsFiring)
		W = AdventWeapon(PC.Pawn.LeftWeapon);
	if (W == None || !W.bIsFiring)
		return;
	From = PC.Pawn.Location;
	To = From + Normal(E.CurrentAimLocation - From) * 4000;
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (M.B.EnemyInfo.Enemy != PC.Pawn)
			continue;
		D = SegmentDistance(From, To, M.P.Location, T);
		if (D < NearMissReach && T > 0.02)
			M.NearMiss((1 - D / NearMissReach) * DeltaTime * 3, Level.TimeSeconds);   // a stream, per second
	}
}

// ModMindRules: a hit
function Hit(Pawn Injured, Pawn InstigatedBy, int Damage)
{
	local ModMind M;
	local float Share;

	M = MindOf(Injured);
	if (M == None || Damage <= 0)
		return;
	Share = FClamp(Damage / FMax(Injured.default.Health, 1), 0, 1);
	M.Hurt(Share, Level.TimeSeconds);
	Log2(Injured.Name $ " hit for " $ Damage $ ": " $ M.Describe());
}

static function string GoryText(bool bGory)
{
	if (bGory)
		return " (it came apart)";
	return "";
}

// ModMindRules: a death; everyone who saw it feels it
function Death(Pawn Killed, bool bGory)
{
	local int i;
	local ModMind M, Dead;
	local float D;

	if (Killed == None)
		return;
	Dead = MindOf(Killed);
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (M == Dead || M.P.Health <= 0)
			continue;
		D = VSize(M.P.Location - Killed.Location);
		if (D > 2500 || (D > 600 && !FastTrace(Killed.Location, M.P.Location + vect(0,0,40))))
			continue;
		if (Dead != None && M.B.Squad != Dead.B.Squad && D > 1200)
			continue;
		M.SawDeath(Dead != None && Dead.Species == M.Species, bGory, Level.TimeSeconds);
		Log2(M.P.Name $ " saw " $ Killed.Name $ " die" $ GoryText(bGory) $ ": " $ M.Describe());
	}
	if (Dead != None)
	{
		Release(Dead);
		for (i = 0; i < Minds.Length; i++)
			if (Minds[i] == Dead)
			{
				Minds.Remove(i, 1);
				break;
			}
	}
}

// the feelings steer the game's odds ----------------------------------------------

function Steer(ModMind M)
{
	local AdventPawnAbilities A;

	A = M.Own;
	if (A == None || !M.bOwnAbility)
		return;
	A.CoverPointAbility = FClamp(M.BaseCover + 0.6 * M.Pressure + 0.4 * M.Fear, 0, 1);
	A.FleeAbility = FClamp(M.BaseFlee + 0.5 * FMax(0, M.Fear - 0.5) * (1 - M.Courage), 0, 1);
	A.RandomChargeAbility = FClamp(M.BaseCharge + 0.35 * M.Anger * M.Aggression - 0.3 * M.Fear, 0, 1);
	A.EnrageAbility = FClamp(M.BaseEnrage + 0.5 * M.Anger, 0, 1);
	A.DodgeAbility = FClamp(M.BaseDodge + 0.4 * M.Pressure, 0, 1);
	A.RandomDodgeAbility = FClamp(M.BaseRandomDodge + 0.25 * M.Pressure, 0, 1);
	A.AttackAbility = FClamp(M.BaseAttack * (1 - 0.5 * M.Fear) + 0.2 * M.Anger, 0, 1);
	A.CrouchAbility = FClamp(M.BaseCrouch + 0.5 * M.Pressure, 0, 1);
	// fear and stress slow its reactions, anger quickens them
	A.ReactionTime = FMax(0.05, M.BaseReaction * (1 + 0.8 * M.Fear + 0.5 * M.Stress - 0.4 * M.Anger));
	// no melee token: no strikes, leaps or charges from the game's own dice either
	if (M.bTokenGated && !M.bMeleeToken)
	{
		A.MeleeAttackAbility = 0;
		A.LeapAttackAbility = 0;
		A.ChargeAbility = 0;
		A.RandomChargeAbility = 0;
	}
	else
	{
		A.MeleeAttackAbility = M.BaseMelee;
		A.LeapAttackAbility = M.BaseLeapAttack;
		A.ChargeAbility = M.BaseChargeAb;
	}
}

// decisions -----------------------------------------------------------------------

// busy with something the mind mustn't cut into
function bool Busy(ModMind M)
{
	local Bot B;

	B = M.B;
	if (B.bLockState || B.CheckScriptingReactionLevel_Ignore() || B.IsInState('Scripting'))
		return true;
	if (B.IsInState('Dying') || B.IsInState('Dead') || B.IsInState('MeleeAttack') || B.IsInState('Leap') || B.IsInState('LeapAttack')
		|| B.IsInState('LeapOffWall') || B.IsInState('RandomLeap') || B.IsInState('Stunned') || B.IsInState('Grabbed') || B.IsInState('Carried')
		|| B.IsInState('SimpleAnim') || B.IsInState('Disabled') || B.IsInState('RidingIdle') || B.IsInState('RidingEngaged')
		|| B.IsInState('StandingOnVehicleAttack') || B.IsInState('Talking') || B.IsInState('Listen') || B.IsInState('FinishAnimState')
		|| B.IsInState('WaitForInputState') || B.IsInState('Nothing') || B.IsInState('RemoveStickyGrenade') || B.IsInState('OnFireFlee')
		|| B.IsInState('Confused') || B.IsInState('BackToBackFighting') || B.IsInState('Protected') || B.IsInState('TeleportCloserToPlayer')
		|| B.IsInState('Block') || B.IsInState('BlockingAttack') || B.IsInState('Startled') || B.IsInState('Enrage') || B.IsInState('Taunt'))
		return true;
	return M.P.Physics == PHYS_Falling || M.P.Physics == PHYS_KarmaRagdoll;
}

function SetTask(ModMind M, int T, float Limit, string Why)
{
	M.Task = T;
	M.TaskTime = 0;
	M.TaskLimit = Limit;
	Log2(M.P.Name $ " -> " $ M.TaskName(T) $ " (" $ Why $ "): " $ M.Describe());
}

// pinned: head down, no shooting
function HoldFire(ModMind M, bool bHold)
{
	M.bPinHold = bHold;
	ApplyFire(M);
}

// the bot's fire switch: off while pinned, or while it fights the player without a ranged token
function ApplyFire(ModMind M)
{
	local bool bBlock;

	bBlock = M.bPinHold || (M.bTokenGated && !M.bRangedToken);
	if (bBlock != M.bHeldFire)
	{
		M.B.bDisableTimedFire = bBlock;
		M.bHeldFire = bBlock;
		if (bBlock)
			M.B.StopFiring();
	}
}

function Crouch(ModMind M, bool bDown)
{
	if (bDown != M.bCrouched && M.Species != 3/*S_Hound*/)
	{
		M.P.ShouldCrouch(bDown);
		M.bCrouched = bDown;
	}
}

// a cover spot near M from Enemy: hidden at crouch height, open one step to the side,
// close to M, not much nearer the enemy, nobody else's
function bool FindCover(ModMind M, Pawn Enemy, out vector Spot)
{
	local NavigationPoint N;
	local vector Eye, Side, Here;
	local float D, Score, Best, ToEnemyNow, ToEnemy;
	local int i;
	local bool bTaken;
	local int Near, Seen, Blind;

	Eye = Enemy.Location + vect(0,0,1) * Enemy.BaseEyeHeight;
	ToEnemyNow = VSize(M.P.Location - Enemy.Location);
	Best = -1;
	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		D = VSize(N.Location - M.P.Location);
		if (D > CoverReach || D < 60)
			continue;
		Near++;
		ToEnemy = VSize(N.Location - Enemy.Location);
		if (ToEnemy < 350 || ToEnemy < ToEnemyNow - 300)
			continue;
		// hidden at crouch height (the spot's own height, a little up)
		if (FastTrace(N.Location + vect(0,0,10), Eye))
		{
			Seen++;
			continue;
		}
		// open one step to a side, standing
		Side = Normal((N.Location - Enemy.Location) cross vect(0,0,1)) * 90;
		if (!FastTrace(N.Location + Side + vect(0,0,40), Eye) && !FastTrace(N.Location - Side + vect(0,0,40), Eye))
		{
			Blind++;
			continue;
		}
		bTaken = false;
		for (i = 0; i < Claims.Length; i++)
			if (Claims[i].M != M && VSize(Claims[i].Spot - N.Location) < 120)
				bTaken = true;
		if (bTaken)
			continue;
		Score = 1000 - D + 0.25 * FMin(ToEnemy - ToEnemyNow, 600) * M.Fear;
		if (Score > Best)
		{
			Best = Score;
			Here = N.Location;
		}
	}
	if (Best < 0)
	{
		Log2(M.P.Name $ " no cover: " $ Near $ " nodes near, " $ Seen $ " in the enemy's sight, " $ Blind $ " with no shot from the side");
		return false;
	}
	Spot = Here;
	for (i = Claims.Length - 1; i >= 0; i--)
		if (Claims[i].M == M)
			Claims.Remove(i, 1);
	Claims.Length = Claims.Length + 1;
	Claims[Claims.Length - 1].Spot = Spot;
	Claims[Claims.Length - 1].M = M;
	return true;
}

// the next leg along the level's paths toward Dest (or Dest itself when it is in sight)
function vector NextLeg(ModMind M, vector Dest)
{
	local Actor Step;

	if (FastTrace(Dest, M.P.Location))
		return Dest;
	Step = M.B.FindPathTo(Dest);
	// the first node on the route is often the one it stands on: then the next one
	if (Step != None && VSize((Step.Location - M.P.Location) * vect(1,1,0)) < 120 && M.B.RouteCache[1] != None)
		Step = M.B.RouteCache[1];
	if (Step != None)
		return Step.Location;
	return Dest;
}

function Decide(ModMind M, float DeltaTime)
{
	local Pawn Enemy;
	local vector Spot, Away;
	local float Now;

	Now = Level.TimeSeconds;
	Enemy = M.B.EnemyInfo.Enemy;
	M.TaskTime += DeltaTime;

	// tasks running out or done
	if (M.Task != 0/*T_None*/)
	{
		if (M.TaskTime > M.TaskLimit || Enemy == None
			|| (M.Task == 1/*T_Pinned*/ && M.Pressure < FreePressure)
			|| (M.Task == 3/*T_FallBack*/ && M.Fear < FleeFear - 0.25)
			|| (M.Task == 5/*T_Charge*/ && M.Anger < ChargeAnger - 0.3))
		{
			Log2(M.P.Name $ " done with " $ M.TaskName(M.Task) $ " after " $ int(M.TaskTime) $ " s");
			if (M.Task == 1/*T_Pinned*/ || M.Task == 2/*T_Cover*/)
				Crouch(M, false);
			if (M.Task == 1/*T_Pinned*/)
				M.NextPin = Now + 3 + 3 * M.Courage;   // up again to fight before it can be pinned again
			HoldFire(M, false);
			M.Task = 0/*T_None*/;
			M.NextDecision = Now + 0.5;
		}
	}
	if (Enemy == None || Busy(M))
		return;

	// keep tasks going: re-issue a move the game's AI dropped
	switch (M.Task)
	{
		case 1/*T_Pinned*/:
		case 2/*T_Cover*/:
			// in cover: head down while the pressure is high, up to shoot when it ebbs
			if (VSize((M.P.Location - M.TaskDest) * vect(1,1,0)) < 90 || M.TaskDest == vect(0,0,0))
			{
				HoldFire(M, M.Pressure > PinPressure);
				Crouch(M, M.Pressure > FreePressure);
				if (!M.B.IsInState('Wait'))
					M.B.DoWait('Mind_HoldCover', 1.0);
			}
			else if (!M.B.IsInState('MoveToDestination'))
				M.B.DoMoveToDestination('Mind_ToCover', NextLeg(M, M.TaskDest));
			return;
		case 3/*T_FallBack*/:
		case 4/*T_Flank*/:
		case 6/*T_Circle*/:
			if (VSize((M.P.Location - M.TaskDest) * vect(1,1,0)) < 140)
			{
				if (M.Task == 6/*T_Circle*/)
				{
					// in place: now the pack closes in
					SetTask(M, 5/*T_Charge*/, 4, "pack in place");
					M.B.DoCharge('Mind_PackCharge', Enemy);
					return;
				}
				Log2(M.P.Name $ " reached its " $ M.TaskName(M.Task) $ " spot");
				M.Task = 0/*T_None*/;
				M.B.DoWait('Mind_Arrived', 0.6);
			}
			else if (!M.B.IsInState('MoveToDestination'))
			{
				M.B.bShouldWalk = false;
				M.B.DoMoveToDestination('Mind_Leg', NextLeg(M, M.TaskDest));
				if (bMindLog && M.TaskTime - M.LastLog > 2)
				{
					M.LastLog = M.TaskTime;
					Log2(M.P.Name $ " " $ M.TaskName(M.Task) $ " leg, " $ int(VSize(M.P.Location - M.TaskDest)) $ " to go");
				}
			}
			return;
		case 5/*T_Charge*/:
		case 7/*T_Panic*/:
			return;
	}

	if (Now < M.NextDecision)
		return;
	M.NextDecision = Now + 0.4 + FRand() * 0.4;

	// broken: run
	if (M.Fear > PanicFear && M.Courage < 0.45 && M.Species != 4/*S_Construct*/)
	{
		SetTask(M, 7/*T_Panic*/, 4 + 4 * FRand(), "broken");
		HoldFire(M, false);
		if (M.Species == 0/*S_Human*/)
			M.B.DoPanic('Mind_Panic');
		else
			M.B.DoFlee('Mind_Flee');
		return;
	}
	// pinned: down and into cover
	if (M.Pressure > PinPressure && Now > M.NextPin && M.Species != 3/*S_Hound*/ && M.Species != 4/*S_Construct*/)
	{
		HoldFire(M, true);
		Crouch(M, true);
		if (FindCover(M, Enemy, Spot))
		{
			M.TaskDest = Spot;
			SetTask(M, 1/*T_Pinned*/, 6 + 4 * M.Discipline, "suppressed, cover at " $ int(VSize(Spot - M.P.Location)));
			M.B.DoMoveToDestination('Mind_ToCover', NextLeg(M, Spot));
		}
		else
		{
			M.TaskDest = vect(0,0,0);
			SetTask(M, 1/*T_Pinned*/, 1.5 + 1.5 * (1 - M.Discipline), "suppressed, no cover");
			M.B.DoWait('Mind_Pinned', 1.0);
		}
		return;
	}
	// scared: back off toward the squad, or into cover further away
	if (M.Fear > FleeFear && M.Species != 4/*S_Construct*/)
	{
		HoldFire(M, false);
		if (M.Species != 3/*S_Hound*/ && FindCover(M, Enemy, Spot) && VSize(Spot - Enemy.Location) > VSize(M.P.Location - Enemy.Location))
		{
			M.TaskDest = Spot;
			SetTask(M, 2/*T_Cover*/, 8, "afraid, cover further back");
			M.B.DoMoveToDestination('Mind_FearCover', NextLeg(M, Spot));
		}
		else
		{
			Away = M.P.Location + Normal(M.P.Location - Enemy.Location) * 600;
			if (M.B.Squad != None && M.B.Squad.FormationCenter() != None && M.B.Squad.FormationCenter() != M.P)
				Away = M.B.Squad.FormationCenter().Location;
			M.TaskDest = Away;
			SetTask(M, 3/*T_FallBack*/, 6, "afraid, falling back");
			M.B.DoMoveToDestination('Mind_FallBack', NextLeg(M, Away));
		}
		return;
	}
	// angry: at it
	if (M.Anger > ChargeAnger && M.Aggression > 0.45 && M.Fear < 0.6 && (M.bMeleeToken || !M.bTokenGated))
	{
		SetTask(M, 5/*T_Charge*/, 5, "enraged");
		HoldFire(M, false);
		if ((M.Species == 1/*S_Seeker*/ || M.Species == 2/*S_SeekerVet*/) && M.B.DoEnrage('Mind_Enrage', Enemy))
			return;
		M.B.DoCharge('Mind_Charge', Enemy);
		return;
	}
	// hurt or under fire, and cover-minded: take cover before it has to
	if (M.Species != 3/*S_Hound*/ && M.Species != 4/*S_Construct*/
		&& (M.Pressure > 0.35 || M.P.Health < 0.5 * M.P.default.Health) && FRand() < 0.5 * M.Cunning + 0.3 * M.Fear)
	{
		if (FindCover(M, Enemy, Spot))
		{
			M.TaskDest = Spot;
			SetTask(M, 2/*T_Cover*/, 7, "taking cover early");
			M.B.DoMoveToDestination('Mind_EarlyCover', NextLeg(M, Spot));
		}
	}
}

// attack tokens (DOOM 2016's token pools, U2FairFights' dealer): every TokenTime the creatures
// fighting the player are ranked and the best few get a ranged token (they may shoot) and a
// melee token (they may charge, leap, strike); the others keep moving and taking cover. Feelings
// decide who asks: the pinned, panicking and afraid ask for nothing, anger asks for melee,
// calm in sight of the player asks to shoot; waiting long raises the claim (everyone gets a
// turn), being in sight of the player raises it most (an on-screen creature takes the turn
// of one the player can't see).
function Deal()
{
	local int i, j, Engaged, RangedN, MeleeN, GivenR, GivenM;
	local Pawn Player;
	local ModMind M;
	local array<ModMind> RankR, RankM;
	local array<float> ScoreR, ScoreM;
	local float S, D, Now;
	local bool bSight, bAsks;
	local string NamesR, NamesM;

	Now = Level.TimeSeconds;
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		Player = M.B.EnemyInfo.Enemy;
		if (M.P.Health <= 0 || Player == None || PlayerController(Player.Controller) == None)
		{
			if (M.bTokenGated)
			{
				M.bTokenGated = false;
				M.bRangedToken = false;
				M.bMeleeToken = false;
				ApplyFire(M);
			}
			continue;
		}
		M.bTokenGated = true;
		Engaged++;
		D = VSize(Player.Location - M.P.Location);
		bSight = FastTrace(Player.Location, M.P.Location + vect(0,0,1) * M.P.BaseEyeHeight);
		bAsks = M.Fear < FleeFear && M.Task != 1/*T_Pinned*/ && M.Task != 7/*T_Panic*/ && M.Task != 3/*T_FallBack*/;
		// ranged
		if (bAsks && M.Species != 3/*S_Hound*/)
		{
			S = 100 * FMin(Now - M.LastRanged, 20) - 0.2 * D + 300 * M.Anger - 400 * M.Fear;
			if (bSight)
				S += 800;
			for (j = 0; j < RankR.Length; j++)
				if (S > ScoreR[j])
					break;
			RankR.Insert(j, 1);
			ScoreR.Insert(j, 1);
			RankR[j] = M;
			ScoreR[j] = S;
		}
		// melee: the angry and the hounds; not the scared
		if (bAsks && M.Fear < 0.6)
		{
			S = 100 * FMin(Now - M.LastMelee, 20) - 0.5 * D + 600 * M.Anger * M.Aggression;
			if (bSight)
				S += 400;
			if (M.Species == 3/*S_Hound*/)
				S += 300;
			for (j = 0; j < RankM.Length; j++)
				if (S > ScoreM[j])
					break;
			RankM.Insert(j, 1);
			ScoreM.Insert(j, 1);
			RankM[j] = M;
			ScoreM[j] = S;
		}
		M.bRangedToken = false;
		M.bMeleeToken = false;
	}
	if (Engaged == 0)
		return;
	RangedN = RangedTokens;
	if (RangedPer > 0 && Engaged > 4)
		RangedN += (Engaged - 4) / RangedPer;
	MeleeN = MeleeTokens;
	if (MeleePer > 0 && Engaged > 4)
		MeleeN += (Engaged - 4) / MeleePer;
	for (j = 0; j < RankR.Length && GivenR < RangedN; j++)
	{
		RankR[j].bRangedToken = true;
		RankR[j].LastRanged = Now;
		GivenR++;
		NamesR = NamesR $ " " $ RankR[j].P.Name;
	}
	for (j = 0; j < RankM.Length && GivenM < MeleeN; j++)
	{
		RankM[j].bMeleeToken = true;
		RankM[j].LastMelee = Now;
		GivenM++;
		NamesM = NamesM $ " " $ RankM[j].P.Name;
	}
	for (i = 0; i < Minds.Length; i++)
		if (Minds[i].bTokenGated)
			ApplyFire(Minds[i]);
	Log2("tokens: " $ Engaged $ " fighting the player; ranged " $ GivenR $ "/" $ RangedN $ ":" $ NamesR $ "; melee " $ GivenM $ "/" $ MeleeN $ ":" $ NamesM);
}

// the squad: a flanker now and then, morale after losses, hound packs
function Squads()
{
	local int i, j, Engaged, Hounds;
	local ModMind M, Pick, O;
	local float Best, Score, Side;
	local SquadAI S;
	local vector Centre, ToSquad, Target;
	local Pawn Enemy;
	local bool bFlanking;

	for (i = 0; i < Minds.Length; i++)
	{
		S = Minds[i].B.Squad;
		if (S == None)
			continue;
		// once per squad: only the first mind of each squad does the squad's thinking
		for (j = 0; j < i; j++)
			if (Minds[j].B.Squad == S)
				break;
		if (j < i)
			continue;
		Engaged = 0;
		Hounds = 0;
		bFlanking = false;
		Centre = vect(0,0,0);
		Enemy = None;
		Pick = None;
		Best = 0;
		for (j = i; j < Minds.Length; j++)
		{
			O = Minds[j];
			if (O.B.Squad != S || O.B.EnemyInfo.Enemy == None)
				continue;
			Enemy = O.B.EnemyInfo.Enemy;
			Engaged++;
			Centre += O.P.Location;
			if (O.Species == 3/*S_Hound*/)
				Hounds++;
			if (O.Task == 4/*T_Flank*/)
				bFlanking = true;
			Score = O.Cunning * (1 - O.Fear) * (1 - O.Pressure);
			if (O.Task == 0/*T_None*/ && O.Species != 3/*S_Hound*/ && Score > Best && !Busy(O) && Level.TimeSeconds - O.LastFlank > 12)
			{
				Best = Score;
				Pick = O;
			}
		}
		if (Engaged == 0 || Enemy == None)
			continue;
		// the player's allies follow the player (their own formation logic): squads that fight the player only
		if (PlayerController(Enemy.Controller) == None)
			continue;
		Centre /= Engaged;

		// hounds: a pack takes places around the prey, then closes in
		if (Hounds >= 2)
		{
			for (j = i; j < Minds.Length; j++)
			{
				O = Minds[j];
				if (O.B.Squad != S || O.Species != 3/*S_Hound*/ || O.Task != 0/*T_None*/ || Busy(O) || O.B.EnemyInfo.Enemy == None)
					continue;
				if (VSize(O.P.Location - Enemy.Location) < HoundCircle * 0.7)
					continue;           // already close: let it bite
				O.CircleAngle += 0.6 * (FRand() - 0.5);
				Target = Enemy.Location + HoundCircle * (vect(1,0,0) * Cos(O.CircleAngle) + vect(0,1,0) * Sin(O.CircleAngle));
				O.TaskDest = Target;
				SetTask(O, 6/*T_Circle*/, 5, "pack circling");
				O.B.DoMoveToDestination('Mind_Circle', NextLeg(O, Target));
			}
		}

		// one flanker at a time: round the side along paths, at its preferred range
		if (!bFlanking && Pick != None && Engaged >= 2 && FlankWait <= 0 && Pick.Cunning > 0.45 && FRand() < Pick.Cunning)
		{
			ToSquad = Normal((Centre - Enemy.Location) * vect(1,1,0));
			Side = 1;
			if (FRand() < 0.5)
				Side = -1;
			Target = Enemy.Location + (ToSquad * Cos(1.3) + (ToSquad cross vect(0,0,1)) * Side * Sin(1.3)) * FClamp(VSize(Pick.P.Location - Enemy.Location), 450, 900);
			Target = FlankSpot(Pick, Target, Enemy);
			if (Target != vect(0,0,0))
			{
				Pick.TaskDest = Target;
				Pick.LastFlank = Level.TimeSeconds;
				SetTask(Pick, 4/*T_Flank*/, 15, "flanking (" $ Engaged $ " engaged)");
				Pick.B.bShouldWalk = false;   // flankers run
				Pick.B.DoMoveToDestination('Mind_Flank', NextLeg(Pick, Target));
				FlankWait = FlankEvery;
			}
		}
	}
}

// the path node nearest Want that can see the enemy
function vector FlankSpot(ModMind M, vector Want, Pawn Enemy)
{
	local NavigationPoint N;
	local float D, Best;
	local vector Here, Eye;

	Eye = Enemy.Location + vect(0,0,1) * Enemy.BaseEyeHeight;
	Best = 700;
	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		D = VSize(N.Location - Want);
		if (D >= Best)
			continue;
		if (!FastTrace(N.Location + vect(0,0,50), Eye))
			continue;
		Best = D;
		Here = N.Location;
	}
	if (Best >= 700)
		return vect(0,0,0);
	return Here;
}

// a squad that lost half its number: humans fall back together, Seekers and hounds rage
function SquadMorale(ModMind M, out float Share)
{
	local SquadAI S;
	local int Start, Lost;

	S = M.B.Squad;
	Share = 1;
	if (S == None)
		return;
	Start = Max(S.iOrigDesiredSquadSize, 1);
	Lost = S.SquadMembersKilled;
	Share = FClamp(1 - float(Lost) / float(Start + Lost), 0, 1);
}

function Tick(float DeltaTime)
{
	local int i;
	local ModMind M;
	local float Morale, Health;

	if (!bMinds)
		return;
	AdoptWait -= DeltaTime;
	if (AdoptWait <= 0)
	{
		AdoptWait = 1.0;
		Adopt();
	}
	FlankWait -= DeltaTime;
	if (Minds.Length == 0)
		return;
	SenseShots();
	SenseAim(DeltaTime);
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (M.B == None || M.P == None || M.P.Health <= 0)
			continue;
		if (M.B.EnemyInfo.Enemy != None && M.B.DistanceToEnemy > 0 && M.B.DistanceToEnemy < 250)
			M.Crowded(DeltaTime);
		SquadMorale(M, Morale);
		Health = FClamp(M.P.Health / FMax(M.P.default.Health, 1), 0, 1);
		M.Ebb(DeltaTime, Level.TimeSeconds, Morale, Health);
		// a squad bled to half: the shaken get more afraid, the fanatic and the pack angrier
		if (Morale < 0.5)
		{
			if (M.Species == 1/*S_Seeker*/ || M.Species == 2/*S_SeekerVet*/ || M.Species == 3/*S_Hound*/)
				M.Anger = FMin(1, M.Anger + DeltaTime * 0.05 * M.Social);
		}
		Steer(M);
		Decide(M, DeltaTime);
	}
	TokenWait -= DeltaTime;
	if (TokenWait <= 0)
	{
		TokenWait = TokenTime;
		Deal();
	}
	Squads();
}

// ModPilot's MINDLIST
function string List()
{
	local int i;
	local string S;

	S = Minds.Length $ " minds, " $ ShotsAtPlayer $ " shots at the player so far (" $ ShotsUntokened $ " without a token)";
	for (i = 0; i < Minds.Length; i++)
		S = S $ " | " $ Minds[i].P.Name $ " " $ Minds[i].Describe() $ " misses " $ Minds[i].NearMisses $ " hits " $ Minds[i].Hits;
	return S;
}

defaultproperties
{
	bMinds=True
	bMindLog=False
	TraitSpread=0.15
	PinPressure=0.7
	FreePressure=0.35
	FleeFear=0.7
	PanicFear=0.92
	ChargeAnger=0.75
	CoverReach=1200
	NearMissReach=220
	FlankEvery=6
	HoundCircle=550
	RangedTokens=2
	RangedPer=4
	MeleeTokens=2
	MeleePer=6
	TokenTime=2
}
