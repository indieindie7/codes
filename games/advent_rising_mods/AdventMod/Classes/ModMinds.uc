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
var int ShotsAtPlayer, ShotsUntokened, PlayerHits, PlayerDamage;

// path costs (AI-MINDS-DESIGN.md section 7: the engine's search reads ExtraCost): which path nodes
// the player can see right now, swept a few at a time; a creature's next leg is planned with a cost
// profile for what it is doing (push: shortest; hidden: round what the player sees; flank: round the
// player's front and the squad's own routes; fallback: hidden and away from the player)
var config bool bPathProfiles;
var config int SweepBudget;          // sight traces per tick
var config float ExposeReach;        // how far from the player nodes are checked (world units)
var config int ExposeCost, FrontCost, RouteCost, CloserCost;
var array<NavigationPoint> Nodes;
var array<float> SeenAt;
var array<NavigationPoint> Visible, VisibleNext;
var int SweepAt;
var bool bNodesBuilt;
var string Order;                    // a strategy ordered from outside (pilot MINDORDER; later the director)
var int LegNodes, LegExposed;        // all planned legs: nodes on them, and how many the player could see
var config int RangedTokens;        // creatures that may shoot at the player at once ...
var config int RangedPer;           // ... plus one per this many engaged beyond four
var config int MeleeTokens;         // creatures that may charge, leap or strike at once ...
var config int MeleePer;            // ... plus one per this many engaged beyond four
var config float TokenTime;         // seconds between deals
var config float AcquireGrace;      // seconds a creature waits before its first shot at the player after spotting them
var config float AimMoveRelief;     // how much a fast-moving player throws off the aim (0..1)

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
	Spawn(class'ModMoves');     // lean and the foot-slide meter (they don't need the minds)
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

	if (PlayerController(Injured.Controller) != None && Damage > 0 && MindOf(InstigatedBy) != None)
	{
		PlayerHits++;
		PlayerDamage += Damage;
	}
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

// fairness (DOOM: miss more when the player moves; U2FairFights: a beat before the first shot) ----
// The game's Bot walks its aim in from the player's feet to the body over 0.6 s from when it
// starts a burst (StartAimingTime; only at more than 500 units), then adds a fixed +-2.7 deg
// yaw error (its smarter AdjustAimError is never called). So the aim's progress is what we
// can move: a player who runs, dodges or jumps sets it back, as do the creature's own fear and
// pressure; and a creature that has just spotted the player waits AcquireGrace before firing.
function AimFair(ModMind M)
{
	local Pawn Player;
	local float Now, Speed, Move, Cap, Progress;
	local bool bSight;

	Player = M.B.EnemyInfo.Enemy;
	if (!M.bTokenGated || Player == None)
		return;
	Now = Level.TimeSeconds;
	bSight = M.B.bEnemyIsVisible;
	if (bSight)
	{
		// spotted again after 3 s out of sight (or for the first time): a beat before shooting
		if (Now - M.LastSawPlayer > 3)
		{
			M.HoldUntil = Now + AcquireGrace;
			ApplyFire(M);
		}
		M.LastSawPlayer = Now;
	}
	if (M.bHeldFire && Now >= M.HoldUntil)
		ApplyFire(M);           // the beat is over
	if (M.B.StartAimingTime < 0)
		return;                 // not mid-burst
	Speed = VSize(Player.Velocity * vect(1,1,0));
	Move = FClamp((Speed - 250) / 350, 0, 1);
	if (Player.Physics == PHYS_Falling)
		Move = 1;
	Cap = FClamp(1 - AimMoveRelief * Move - 0.4 * M.Fear - 0.3 * M.Pressure, 0.25, 1);
	if (Cap >= 1)
		return;
	Progress = (Now - M.B.StartAimingTime) / 0.6;
	if (Progress > Cap)
	{
		M.B.StartAimingTime = Now - 0.6 * Cap;
		M.AimHeld++;
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

	bBlock = M.bPinHold || (M.bTokenGated && !M.bRangedToken) || (M.bTokenGated && Level.TimeSeconds < M.HoldUntil);
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

// position queries (Crytek TPS / Unreal EQS / Killzone position picking): generate the path nodes
// near the creature, filter, score each on several things at once with cheap tests, then run the
// costly sight traces only on the best few (best first) until one passes. Scores, cover:
//   near the creature (a long run under fire is bad), its preferred range from the enemy, not next
//   to a squad mate (spread out), off the player's current sight (the sweep), further back the
//   more afraid; must then be hidden at crouch height and open one step to a side (to shoot).
// Flank: near the wanted flank point, its preferred range, far round from where the player looks,
// spread from squad mates; must then see the enemy.
const SPOT_K = 8;

function float MateSpacing(ModMind M, vector At)
{
	local int i;
	local float Pen;

	for (i = 0; i < Minds.Length; i++)
		if (Minds[i] != M && Minds[i].B.Squad == M.B.Squad && Minds[i].P != None && VSize(Minds[i].P.Location - At) < 220)
			Pen += 400;
	for (i = 0; i < Claims.Length; i++)
		if (Claims[i].M != M && VSize(Claims[i].Spot - At) < 160)
			Pen += 2000;            // someone's cover spot
	return Pen;
}

// keep the best SPOT_K candidates, best first
static function Keep(NavigationPoint N, float S, out array<NavigationPoint> Top, out array<float> TopS)
{
	local int j;

	for (j = 0; j < Top.Length; j++)
		if (S > TopS[j])
			break;
	if (j >= SPOT_K)
		return;
	Top.Insert(j, 1);
	TopS.Insert(j, 1);
	Top[j] = N;
	TopS[j] = S;
	if (Top.Length > SPOT_K)
	{
		Top.Length = SPOT_K;
		TopS.Length = SPOT_K;
	}
}

function bool FindCover(ModMind M, Pawn Enemy, out vector Spot)
{
	local NavigationPoint N;
	local vector Eye, Side;
	local float D, S, ToEnemyNow, ToEnemy, Pref;
	local int i, Near, Seen, Blind;
	local array<NavigationPoint> Top;
	local array<float> TopS;

	Eye = Enemy.Location + vect(0,0,1) * Enemy.BaseEyeHeight;
	ToEnemyNow = VSize(M.P.Location - Enemy.Location);
	Pref = FClamp((M.P.Ability.PreferredMinRange + M.P.Ability.PreferredMaxRange) * 0.5, 500, 1800);
	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		D = VSize(N.Location - M.P.Location);
		if (D > CoverReach || D < 60)
			continue;
		ToEnemy = VSize(N.Location - Enemy.Location);
		if (ToEnemy < 350 || ToEnemy < ToEnemyNow - 300)
			continue;
		Near++;
		S = 1000 - D * 0.6 - Abs(ToEnemy - Pref) * 0.25 * (1 - M.Fear) + 0.3 * FMin(ToEnemy - ToEnemyNow, 600) * M.Fear - MateSpacing(M, N.Location);
		if (IsVisible(N))
			S -= 300;
		Keep(N, S, Top, TopS);
	}
	for (i = 0; i < Top.Length; i++)
	{
		N = Top[i];
		if (FastTrace(N.Location + vect(0,0,10), Eye))
		{
			Seen++;
			continue;               // the enemy sees it even crouched
		}
		Side = Normal((N.Location - Enemy.Location) cross vect(0,0,1)) * 90;
		if (!FastTrace(N.Location + Side + vect(0,0,40), Eye) && !FastTrace(N.Location - Side + vect(0,0,40), Eye))
		{
			Blind++;
			continue;               // no shot from either side
		}
		Spot = N.Location;
		for (i = Claims.Length - 1; i >= 0; i--)
			if (Claims[i].M == M)
				Claims.Remove(i, 1);
		Claims.Length = Claims.Length + 1;
		Claims[Claims.Length - 1].Spot = Spot;
		Claims[Claims.Length - 1].M = M;
		Log2(M.P.Name $ " cover: " $ Near $ " candidates, picked #" $ (Seen + Blind + 1) $ " of the best " $ Top.Length $ " (score " $ int(TopS[Seen + Blind]) $ ")");
		return true;
	}
	Log2(M.P.Name $ " no cover: " $ Near $ " candidates, best " $ Top.Length $ " traced: " $ Seen $ " in the enemy's sight, " $ Blind $ " with no shot from the side");
	return false;
}

// the next leg along the level's paths toward Dest (or Dest itself when it is in sight)
// the nodes the player can see: a few sight traces a tick, round the list; the visible set is
// the last full sweep plus what this sweep has found so far
function Sweep()
{
	local PlayerController PC;
	local vector Eye;
	local int Traced, Looked, i;
	local NavigationPoint N;

	if (!bNodesBuilt)
	{
		bNodesBuilt = true;
		for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
			Nodes[Nodes.Length] = N;
		SeenAt.Length = Nodes.Length;
		Log2("paths: " $ Nodes.Length $ " nodes in this level");
	}
	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None || Nodes.Length == 0)
		return;
	Eye = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.BaseEyeHeight;
	while (Traced < SweepBudget && Looked < Nodes.Length && Looked < SweepBudget * 8)
	{
		Looked++;
		i = SweepAt;
		SweepAt++;
		if (SweepAt >= Nodes.Length)
		{
			SweepAt = 0;
			Visible = VisibleNext;
			VisibleNext.Length = 0;
		}
		N = Nodes[i];
		if (N == None || VSize(N.Location - PC.Pawn.Location) > ExposeReach)
			continue;
		Traced++;
		if (FastTrace(N.Location + vect(0,0,40), Eye))
		{
			SeenAt[i] = Level.TimeSeconds;
			VisibleNext[VisibleNext.Length] = N;
		}
	}
}

function bool IsVisible(NavigationPoint N)
{
	local int i;

	for (i = 0; i < Visible.Length; i++)
		if (Visible[i] == N)
			return true;
	for (i = 0; i < VisibleNext.Length; i++)
		if (VisibleNext[i] == N)
			return true;
	return false;
}

// the cost profile for what M is doing (an order from outside overrides): 0 push, 1 hidden,
// 2 flank, 3 fallback
function int ProfileFor(ModMind M)
{
	if (!M.bTokenGated)
		return ProfileOwn(M);      // orders are for those fighting the player
	if (Order == "push")
		return 0;
	if (Order == "hidden")
		return 1;
	if (M.Task == 4/*T_Flank*/ || Order == "flank")
		return 2;
	if (M.Task == 3/*T_FallBack*/ || M.Task == 7/*T_Panic*/ || Order == "fallback")
		return 3;
	if (M.Task == 1/*T_Pinned*/ || M.Task == 2/*T_Cover*/)
		return 1;
	return 0;
}

function int ProfileOwn(ModMind M)
{
	if (M.Task == 4/*T_Flank*/)
		return 2;
	if (M.Task == 3/*T_FallBack*/ || M.Task == 7/*T_Panic*/)
		return 3;
	if (M.Task == 1/*T_Pinned*/ || M.Task == 2/*T_Cover*/)
		return 1;
	return 0;
}

static function string ProfileName(int P)
{
	switch (P)
	{
		case 0: return "push";
		case 1: return "hidden";
		case 2: return "flank";
		case 3: return "fallback";
	}
	return "?";
}

function vector NextLeg(ModMind M, vector Dest)
{
	local Actor Step;
	local int Profile, i, k, j, Seen;
	local array<NavigationPoint> Raised;
	local array<int> Old;
	local PlayerController PC;
	local vector Facing, ToNode;
	local NavigationPoint N;
	local int Cost;
	local ModMind O;

	Profile = 0;
	if (bPathProfiles)
		Profile = ProfileFor(M);
	if (FastTrace(Dest, M.P.Location) && (Profile == 0 || VSize(Dest - M.P.Location) < 600))
		return Dest;
	PC = Level.GetLocalPlayerController();
	// raise the costs for this one search, and put them back right after it
	if (Profile != 0 && PC != None && PC.Pawn != None)
	{
		Facing = Normal(Vector(PC.Rotation) * vect(1,1,0));
		for (i = 0; i < Visible.Length; i++)
		{
			N = Visible[i];
			if (N == None)
				continue;
			Cost = ExposeCost;
			ToNode = Normal((N.Location - PC.Pawn.Location) * vect(1,1,0));
			if (Profile == 2 && (ToNode dot Facing) > 0.5)
				Cost += FrontCost;
			if (Profile == 3 && VSize(N.Location - PC.Pawn.Location) < VSize(M.P.Location - PC.Pawn.Location))
				Cost += CloserCost;
			Raised[Raised.Length] = N;
			Old[Old.Length] = N.ExtraCost;
			N.ExtraCost += Cost;
		}
		// a flanker keeps off its squad mates' routes (they hold the front)
		if (Profile == 2)
			for (j = 0; j < Minds.Length; j++)
			{
				O = Minds[j];
				if (O == M || O.B.Squad != M.B.Squad)
					continue;
				for (k = 0; k < 16; k++)
				{
					N = NavigationPoint(O.B.RouteCache[k]);
					if (N == None)
						continue;
					Raised[Raised.Length] = N;
					Old[Old.Length] = N.ExtraCost;
					N.ExtraCost += RouteCost;
				}
			}
	}
	Step = M.B.FindPathTo(Dest);
	for (i = Raised.Length - 1; i >= 0; i--)
		Raised[i].ExtraCost = Old[i];
	// what the plan exposes (all legs, for MINDLIST; the first one of each task in the log)
	for (k = 0; k < 16; k++)
	{
		N = NavigationPoint(M.B.RouteCache[k]);
		if (N == None)
			continue;
		LegNodes++;
		if (IsVisible(N))
		{
			LegExposed++;
			Seen++;
		}
	}
	if (bMindLog && M.TaskTime < 0.5)
		Log2(M.P.Name $ " plans a " $ ProfileName(Profile) $ " leg: " $ Seen $ " of its route's nodes in the player's sight (" $ Raised.Length $ " costs raised)");
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
			if (M.Task == 4/*T_Flank*/)
				M.LastFlank = Now;      // the rest counts from the end of a flank
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
		case 8/*T_Advance*/:
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
				if (M.Task == 4/*T_Flank*/)
					M.LastFlank = Level.TimeSeconds;
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
	// ordered to fall back: everyone fighting the player does, once per order
	if (Order == "fallback" && M.bTokenGated && !M.bOrderDone)
	{
		M.bOrderDone = true;
		Away = M.P.Location + Normal(M.P.Location - Enemy.Location) * 800;
		if (M.B.Squad != None && M.B.Squad.FormationCenter() != None && M.B.Squad.FormationCenter() != M.P)
			Away = M.B.Squad.FormationCenter().Location + Normal(M.B.Squad.FormationCenter().Location - Enemy.Location) * 400;
		M.TaskDest = Away;
		SetTask(M, 3/*T_FallBack*/, 8, "ordered to fall back");
		M.B.DoMoveToDestination('Mind_OrderFallBack', NextLeg(M, Away));
		return;
	}
	// ordered to push: those not already on something close in to their near range, along paths
	if (Order == "push" && M.bTokenGated && M.Task == 0/*T_None*/ && M.Fear < FleeFear
		&& VSize(M.P.Location - Enemy.Location) > FMax(M.P.Ability.PreferredMinRange, 450) + 250)
	{
		M.TaskDest = Enemy.Location + Normal(M.P.Location - Enemy.Location) * FMax(M.P.Ability.PreferredMinRange, 450);
		SetTask(M, 8/*T_Advance*/, 7, "ordered to push");
		M.B.bShouldWalk = false;
		M.B.DoMoveToDestination('Mind_Advance', NextLeg(M, M.TaskDest));
		return;
	}
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
		&& (Order != "push" || !M.bTokenGated)
		&& (M.Pressure > 0.35 || M.P.Health < 0.5 * M.P.default.Health || (Order == "hidden" && M.bTokenGated))
		&& (FRand() < 0.5 * M.Cunning + 0.3 * M.Fear || ((Order == "hidden" && M.bTokenGated) && FRand() < 0.6)))
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
			if (Enemy == None || PlayerController(O.B.EnemyInfo.Enemy.Controller) != None)
				Enemy = O.B.EnemyInfo.Enemy;   // the player, if anyone in the squad fights the player
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
		if ((!bFlanking || Order == "flank") && Pick != None && (Engaged >= 2 || Order == "flank") && FlankWait <= 0 && (Pick.Cunning > 0.45 || Order == "flank") && (FRand() < Pick.Cunning || Order == "flank"))
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
				if (Order == "flank")
					FlankWait = FlankEvery / 3;
			}
		}
	}
}

// the flank spot: near Want, at its range from the enemy, far round from where the player looks,
// spread from squad mates, and it must see the enemy (traced on the best few only)
function vector FlankSpot(ModMind M, vector Want, Pawn Enemy)
{
	local NavigationPoint N;
	local float D, S, Pref, Off;
	local vector Eye, Facing;
	local int i;
	local PlayerController PC;
	local array<NavigationPoint> Top;
	local array<float> TopS;

	Eye = Enemy.Location + vect(0,0,1) * Enemy.BaseEyeHeight;
	Pref = FClamp((M.P.Ability.PreferredMinRange + M.P.Ability.PreferredMaxRange) * 0.5, 500, 1400);
	PC = PlayerController(Enemy.Controller);
	if (PC != None)
		Facing = Normal(Vector(PC.Rotation) * vect(1,1,0));
	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		D = VSize(N.Location - Want);
		if (D > 900)
			continue;
		S = 1000 - D * 0.5 - Abs(VSize(N.Location - Enemy.Location) - Pref) * 0.3 - MateSpacing(M, N.Location);
		if (PC != None)
		{
			Off = Acos(FClamp(Normal((N.Location - Enemy.Location) * vect(1,1,0)) dot Facing, -1, 1)) * 57.2958;
			S += Off * 4;           // round the side or behind the player's view
		}
		Keep(N, S, Top, TopS);
	}
	for (i = 0; i < Top.Length; i++)
		if (FastTrace(Top[i].Location + vect(0,0,50), Eye))
		{
			Log2(M.P.Name $ " flank spot: picked #" $ (i + 1) $ " of the best " $ Top.Length $ " (score " $ int(TopS[i]) $ ")");
			return Top[i].Location;
		}
	return vect(0,0,0);
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
	Sweep();                // (also with bPathProfiles off: MINDLIST measures what plans expose)
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
		AimFair(M);
	}
	TokenWait -= DeltaTime;
	if (TokenWait <= 0)
	{
		TokenWait = TokenTime;
		Deal();
	}
	Squads();
}

// a strategy from outside: push, hidden, flank, fallback ("" or none = the creatures' own)
function SetOrder(string S)
{
	local int i;

	if (S == "none")
		S = "";
	Order = S;
	for (i = 0; i < Minds.Length; i++)
		Minds[i].bOrderDone = false;
	if (Order != "")
		class'ModSettings'.static.Note("minds: order " $ Order);
	else
		class'ModSettings'.static.Note("minds: order none (their own)");
}

// where the creatures fighting the player stand: how many, how far on average, how many the
// player can see, how far round from where the player looks (degrees, 0 = straight ahead),
// and how many are on a task (for checking that orders move them)
function string Formation()
{
	local PlayerController PC;
	local int i, N, Seen, OnTask;
	local float Dist, Angle;
	local vector Eye, Facing, To;
	local ModMind M;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return "formation: no player";
	Eye = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.BaseEyeHeight;
	Facing = Normal(Vector(PC.Rotation) * vect(1,1,0));
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (!M.bTokenGated || M.P.Health <= 0)
			continue;
		N++;
		To = (M.P.Location - PC.Pawn.Location) * vect(1,1,0);
		Dist += VSize(To);
		Angle += Acos(FClamp(Normal(To) dot Facing, -1, 1)) * 57.2958;
		if (FastTrace(M.P.Location + vect(0,0,30), Eye))
			Seen++;
		if (M.Task != 0)
			OnTask++;
	}
	if (N == 0)
		return "formation: none fighting the player";
	return "formation: " $ N $ " fighting the player, mean distance " $ int(Dist / N) $ ", " $ Seen $ " in sight, mean " $ int(Angle / N) $ " deg off the player's view, " $ OnTask $ " on a task";
}

// ModPilot's MINDLIST
function string List()
{
	local int i;
	local string S;

	S = Formation() $ " || " $ Minds.Length $ " minds, " $ ShotsAtPlayer $ " shots at the player so far (" $ ShotsUntokened $ " without a token), player hit " $ PlayerHits $ " times for " $ PlayerDamage $ ", legs " $ LegExposed $ " of " $ LegNodes $ " nodes in sight, order " $ Order;
	for (i = 0; i < Minds.Length; i++)
		S = S $ " | " $ Minds[i].P.Name $ " " $ Minds[i].Describe() $ " misses " $ Minds[i].NearMisses $ " hits " $ Minds[i].Hits $ " aimheld " $ Minds[i].AimHeld;
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
	FlankEvery=10
	HoundCircle=550
	RangedTokens=2
	RangedPer=4
	MeleeTokens=2
	MeleePer=6
	TokenTime=2
	bPathProfiles=True
	SweepBudget=120
	ExposeReach=4000
	ExposeCost=2000
	FrontCost=4000
	RouteCost=800
	CloserCost=1500
	AcquireGrace=0.6
	AimMoveRelief=0.5
}
