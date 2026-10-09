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
var config float HoundCircle;       // how far from the prey hounds circle (world units; packs off)

// hound packs (AI-MINDS-DESIGN.md section 9): roles (holder, flankers, closer), zig-zag legs, pinning
var config bool bHoundPack;         // off: the old circle-then-charge pack
var config bool bHoundLog;          // every role, leg, arrival and commit in AdventNative.log
var config float HoundHold;         // the holder's distance from the prey (world units; it feints +-70 round it)
var config float HoundFlankAngle;   // degrees round the prey from where it looks that flankers go to
var config float HoundSkipLeg;      // a zig-zag leg's length (world units; 0.75..1.25 of it)
var config float HoundSkipAngle;    // ... and its angle off the line to the goal (degrees; +-10)
var config float HoundCommitFront;  // the prey's front cone (degrees): a flanker outside it lets the closer commit
var config float HoundHoldMax;      // seconds a pack holds without a flanker in place before the nearest commits anyway
var config float HoundSkipDodge;    // chance a skip leg is the engine's own dodge (Dodge_L/R), 0..1
var config float HoundPinWall;      // a wall this close behind the prey pins it (world units)
// wall-kicks and leap links (AI-MINDS-DESIGN.md section 10): a hound leaps to a wall, plants, leaps off it
var config bool bHoundWallKick;     // the closer may commit by a wall-kick, a near flanker may skip by one
var config float WallKickRange;     // how far a wall may be to kick off (world units)
var config float WallKickChance;    // chance a commit kicks when a wall fits (a flank leg: half of it), 0..1
var config float WallKickPlant;     // seconds planted on the wall before the leap off
var config float WallKickCool;      // seconds between one hound's kicks
var config bool bWallKickLog;       // every kick, plant, leap off and miss in AdventNative.log
var config bool bLeapLinks;         // wall-kick links built from the path graph at level start (ModLeapLink)
var config int LeapLinksMax;        // at most this many per level (the best savings kept)
var array<ModLeapLink> Links;
var bool bLinksBuilt;
var int LinkAt;                     // the next node whose pairs are looked at (a few a tick)
var int LinkPairs, LinkFits;        // pairs looked at, pairs that fit (before the cap)
var float LinkBuildTime;
var array<float> LinkDist;          // Dijkstra from the node in hand (indexed as Nodes)
var array<NavigationPoint> CandA, CandB;
var array<vector> CandWall, CandNorm;
var array<float> CandRoute, CandRatio;
var array<int> CandTwo;
var float LinkRadius, LinkHeight, LinkSpeed;   // a hound's body and leap speed, for the arcs at build time
var string ArcBlock;                           // what the last ArcClear hit (for the log)
struct PackInfo
{
	var SquadAI S;
	var float RoleAt;               // when roles were last dealt
	var float HoldSince;            // when the current hold began (the last commit, or the engagement)
	var bool bPinned;
	var float LogAt;
	var float CommitAt;             // the pack's last commit
	var int Pins;
};
var int MovesRefused, MovesGiven;    // the squad refused a state change (one a frame): the move is given again next tick
var array<PackInfo> Packs;
// measures (pilot HOUNDTEST, with packs on or off): bites on the player by hounds, when the first came
// after the first hound engaged, how far round from the player's view they came, melee contacts, the
// time hounds stood on two or more sides of the player, legs, arrivals, commits, pins
var float HoundEngagedAt, HoundFirstBite, HoundBiteBearing, HoundTime, TwoSideTime;
var int HoundBites, HoundContacts, HoundDamage, HoundEngaged;
var int LegsGone, ArrivalsGone, CommitsGone;   // ... the counters of hounds that died (their minds are released)
var int KicksGone, KicksPlantedGone, KickLeapsGone, KickBitesGone, LinkUsesGone;

var array<ModMind> Minds;
var ModMindRules Rules;
var ModNeeds Needs;                 // the needs layer (section 11; ModMutator sets it, or Adopt finds it): wants, HuntDrive, the tell
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
	local ModNeeds N;

	if (Needs == None || Needs.bDeleteMe)
	{
		Needs = None;
		foreach DynamicActors(class'ModNeeds', N)
		{
			Needs = N;
			break;
		}
	}
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
	LegsGone += M.LegsSkipped;
	ArrivalsGone += M.FlankArrivals;
	CommitsGone += M.Commits;
	KicksGone += M.Kicks;
	KicksPlantedGone += M.KicksPlanted;
	KickLeapsGone += M.KickLeaps;
	KickBitesGone += M.KickBites;
	LinkUsesGone += M.LinkUses;
	M.LegsSkipped = 0;
	M.FlankArrivals = 0;
	M.Commits = 0;
	M.Kicks = 0;
	M.KicksPlanted = 0;
	M.KickLeaps = 0;
	M.KickBites = 0;
	M.LinkUses = 0;
	// a pawn left planted on a wall (recycled by a spawner) falls
	if (M.Kick == 2 && M.P != None && !M.P.bDeleteMe && M.P.Physics == PHYS_None)
		M.P.SetPhysics(PHYS_Falling);
	M.Kick = 0;
	M.Link = None;
}

// creatures near the player are animated every tick with a fresh pose (research/native-animation-
// hooks.md: pawns unseen for 5 s tick every other frame, stasis stops them, and their bones then read
// wrong), so the body layers and bone reads see what is drawn; far ones go back to the engine's thrift
function KeepPosed()
{
	local PlayerController PC;
	local int i;
	local bool bNear;
	local Pawn P;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return;
	for (i = 0; i < Minds.Length; i++)
	{
		P = Minds[i].P;
		if (P == None || P.bDeleteMe)
			continue;
		bNear = VSize(P.Location - PC.Pawn.Location) < 3500;
		P.bForceVisible = bNear;
		P.bCanSkipFrames = !bNear;
		if (bNear)
			P.bStasis = false;
	}
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
		if (MindOf(InstigatedBy).Species == 3/*S_Hound*/)
			HoundBite(MindOf(InstigatedBy), Injured, Damage);
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
	if (M.Kick != 0)
		return true;            // mid wall-kick (KickTick owns it)
	// a strike or leap state the game left hanging (seen on spawned hounds: MeleeAttack or LeapAttack for 10-30 s,
	// on the ground, far from the enemy) is not busy: the next task given re-assigns the state
	if ((B.IsInState('MeleeAttack') || B.IsInState('LeapAttack') || B.IsInState('Leap')) && Level.TimeSeconds - B.LastStateChangeTime > 2.5
		&& M.P.Physics == PHYS_Walking && B.EnemyInfo.Enemy != None && VSize(B.EnemyInfo.Enemy.Location - M.P.Location) > 250)
		return false;
	if (B.IsInState('Dying') || B.IsInState('Dead') || B.IsInState('MeleeAttack') || B.IsInState('Leap') || B.IsInState('LeapAttack')
		|| B.IsInState('LeapOffWall') || B.IsInState('RandomLeap') || B.IsInState('Stunned') || B.IsInState('Grabbed') || B.IsInState('Carried')
		|| B.IsInState('SimpleAnim') || B.IsInState('Disabled') || B.IsInState('RidingIdle') || B.IsInState('RidingEngaged')
		|| B.IsInState('StandingOnVehicleAttack') || B.IsInState('Talking') || B.IsInState('Listen') || B.IsInState('FinishAnimState')
		|| B.IsInState('WaitForInputState') || B.IsInState('Nothing') || B.IsInState('RemoveStickyGrenade') || B.IsInState('OnFireFlee')
		|| B.IsInState('Confused') || B.IsInState('BackToBackFighting') || B.IsInState('Protected') || B.IsInState('TeleportCloserToPlayer')
		|| B.IsInState('Block') || B.IsInState('BlockingAttack') || B.IsInState('Startled') || B.IsInState('Enrage') || B.IsInState('Taunt')
		|| B.IsInState('Dodge'))
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
function BuildNodes()
{
	local NavigationPoint N;

	if (bNodesBuilt)
		return;
	bNodesBuilt = true;
	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
		Nodes[Nodes.Length] = N;
	SeenAt.Length = Nodes.Length;
	Log2("paths: " $ Nodes.Length $ " nodes in this level");
}

function Sweep()
{
	local PlayerController PC;
	local vector Eye;
	local int Traced, Looked, i;
	local NavigationPoint N;

	BuildNodes();
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
	local ModLeapLink L;
	local int Rev;

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
	// a hound whose route detours past a wall-kick link takes the link: walk to its near end, then the
	// kick (LinkKick, from Decide's leg handling) lands it at the far end and the leg goes on from there
	M.Link = None;
	if (bLeapLinks && M.Species == 3/*S_Hound*/ && M.Kick == 0 && Links.Length > 0 && Step != None)
	{
		L = LinkOnRoute(M, Dest, Rev);
		if (L != None)
		{
			M.Link = L;
			M.bLinkReverse = Rev != 0;
			N = L.A;
			if (Rev != 0)
				N = L.B;
			KickLog(M.P.Name $ " takes link " $ L.A.Name $ " -> " $ L.B.Name $ IfText(Rev != 0, " (reverse)", "") $ " on its " $ ProfileName(Profile) $ " leg, " $ int(VSize(N.Location - M.P.Location)) $ " to its near end");
			return N.Location;
		}
	}
	// the first node on the route is often the one it stands on: then the next one
	if (Step != None && VSize((Step.Location - M.P.Location) * vect(1,1,0)) < 120 && M.B.RouteCache[1] != None)
		Step = M.B.RouteCache[1];
	if (Step != None)
		return Step.Location;
	return Dest;
}

// a move for the bot, checked: SquadAI.AssignState refuses a second state change in the same frame
// (the game's own WhatToDoNext often ran first), so a move that did not take is given again next tick
// (the state is only given again every 0.4 s: giving it every tick restarts its MoveTo before it can step)
function bool Go(ModMind M, name Why, vector Dest)
{
	if (Level.TimeSeconds < M.ReissueAt)
		return false;
	M.ReissueAt = Level.TimeSeconds + 0.4;
	M.LegDest = Dest;
	M.B.bShouldWalk = false;
	M.B.DoMoveToDestination(Why, Dest);
	MovesGiven++;
	if (Going(M))
		return true;
	MovesRefused++;
	return false;
}

// on our leg (the engine moves Destination's height to the pawn's, so only the plan is compared)
function bool Going(ModMind M)
{
	return M.B.IsInState('MoveToDestination') && VSize((M.B.Destination - M.LegDest) * vect(1,1,0)) < 60;
}

function Decide(ModMind M, float DeltaTime)
{
	local Pawn Enemy;
	local vector Spot, Away, At;
	local float Now;
	local int W;
	local Actor Target;

	if (M.Kick != 0)
	{
		KickTick(M, DeltaTime);
		return;
	}
	Now = Level.TimeSeconds;
	Enemy = M.B.EnemyInfo.Enemy;
	M.TaskTime += DeltaTime;

	// tasks running out or done (a want ends with its time, a hit, an enemy appearing for anyone but a
	// hound, and for a hound the prey close or the melee token in its mouth: the fight is on again)
	if (M.Task != 0/*T_None*/)
	{
		if (M.TaskTime > M.TaskLimit || (Enemy == None && M.Task != 10/*T_Want*/)
			|| (M.Task == 1/*T_Pinned*/ && M.Pressure < FreePressure)
			|| (M.Task == 3/*T_FallBack*/ && M.Fear < FleeFear - 0.25)
			|| (M.Task == 5/*T_Charge*/ && M.Anger < ChargeAnger - 0.3 && M.Role != 3/*R_Closer*/)
			|| (M.Task == 10/*T_Want*/ && (Now - M.LastHit < 1.0 || M.Pressure > FreePressure
				|| (Enemy != None && (M.Species != 3/*S_Hound*/ || M.bMeleeToken || VSize(Enemy.Location - M.P.Location) < 900)))))
		{
			Log2(M.P.Name $ " done with " $ M.TaskName(M.Task) $ " after " $ int(M.TaskTime) $ " s");
			if (M.Task == 4/*T_Flank*/)
				M.LastFlank = Now;      // the rest counts from the end of a flank
			if (M.Task == 1/*T_Pinned*/ || M.Task == 2/*T_Cover*/)
				Crouch(M, false);
			if (M.Task == 1/*T_Pinned*/)
				M.NextPin = Now + 3 + 3 * M.Courage;   // up again to fight before it can be pinned again
			if (M.Task == 10/*T_Want*/ && Needs != None)
				Needs.GiveUp(M.P, "task over");
			HoldFire(M, false);
			M.Task = 0/*T_None*/;
			M.NextDecision = Now + 0.5;
		}
	}
	if (Busy(M))
		return;
	if (Enemy == None && M.Task != 10/*T_Want*/ && Needs == None)
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
			else if (!Going(M))
				Go(M, 'Mind_ToCover', NextLeg(M, M.TaskDest));
			return;
		case 9/*T_Skip*/:
			// a zig-zag leg: done when it is there, or the move ended (or never started); then a short dwell
			// and the pack gives the next one (HoundPack)
			if (VSize((M.P.Location - M.TaskDest) * vect(1,1,0)) < 90 || (M.TaskTime > 0.25 && !Going(M) && !M.bSkipDodge))
			{
				M.Task = 0/*T_None*/;
				M.LegAt = Now + 0.1 + 0.2 * FRand();
				M.B.DoWait('Mind_SkipDwell', 0.25);
			}
			else if (!M.bSkipDodge && !Going(M))
				Go(M, 'Mind_Skip', M.TaskDest);
			return;
		case 3/*T_FallBack*/:
		case 4/*T_Flank*/:
		case 8/*T_Advance*/:
		case 6/*T_Circle*/:
		case 10/*T_Want*/:
			if (VSize((M.P.Location - M.TaskDest) * vect(1,1,0)) < 140)
			{
				if (M.Task == 6/*T_Circle*/)
				{
					// in place: now the pack closes in
					SetTask(M, 5/*T_Charge*/, 4, "pack in place");
					M.B.DoCharge('Mind_PackCharge', Enemy);
					return;
				}
				if (M.Task == 10/*T_Want*/ && Needs != None)
					Needs.Satisfied(M.P);    // there: ModNeeds meets the need (it feeds, looks, rests)
				Log2(M.P.Name $ " reached its " $ M.TaskName(M.Task) $ " spot");
				if (M.Task == 4/*T_Flank*/)
					M.LastFlank = Level.TimeSeconds;
				M.Task = 0/*T_None*/;
				M.Link = None;
				M.B.DoWait('Mind_Arrived', 0.6);
			}
			else if (M.Link != None && LinkKick(M))
				return;
			else if (!Going(M))
			{
				Go(M, 'Mind_Leg', NextLeg(M, M.TaskDest));
				if (bMindLog && M.TaskTime - M.LastLog > 2)
				{
					M.LastLog = M.TaskTime;
					Log2(M.P.Name $ " " $ M.TaskName(M.Task) $ " leg, " $ int(VSize(M.P.Location - M.TaskDest)) $ " to go");
				}
			}
			return;
		case 5/*T_Charge*/:
			// a closer's charge the game dropped (or refused, one state change a frame) is given again
			if (M.Role == 3/*R_Closer*/ && Now > M.ReissueAt && !M.B.IsInState('Charge') && !M.B.IsInState('Dodge'))
			{
				M.ReissueAt = Now + 0.5;
				M.B.DoCharge('Mind_PackCommit', Enemy);
			}
			return;
		case 7/*T_Panic*/:
			return;
	}

	if (Now < M.NextDecision)
		return;
	M.NextDecision = Now + 0.4 + FRand() * 0.4;

	// needs (ModNeeds, section 11): a calm creature with nothing to do acts on its want; a hound may feed or
	// regroup in a lull (the prey far, no melee token), never while it commits or charges
	if (Needs != None && M.Task == 0/*T_None*/ && M.Role != 3/*R_Closer*/
		&& M.Pressure < FreePressure && M.Fear < FleeFear && M.Anger < ChargeAnger
		&& (Enemy == None || (M.Species == 3/*S_Hound*/ && !M.bMeleeToken && VSize(Enemy.Location - M.P.Location) > 900)))
	{
		W = Needs.Want(M.P, At, Target);
		if (W != 0)
		{
			M.TaskDest = At;
			SetTask(M, 10/*T_Want*/, 8, "wants to " $ Needs.WantName(W) $ " " $ int(VSize(At - M.P.Location)) $ " away");
			HoldFire(M, false);
			if (W == 2/*W_Rest*/ && VSize((At - M.P.Location) * vect(1,1,0)) < 140)
				M.B.DoWait('Mind_Rest', 2.0);
			else
				M.B.DoMoveToDestination('Mind_Want', NextLeg(M, At));
			return;
		}
	}
	if (Enemy == None)
		return;

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
		else if (M.Species == 3/*S_Hound*/ && bHoundPack && M.Role != 0)
		{
			// a frightened hound breaks off to the pack's rear
			Away = PackCentre(M);
			Away = Away + Normal((Away - Enemy.Location) * vect(1,1,0)) * 500;
			M.TaskDest = Away;
			M.Role = 0;
			SetTask(M, 3/*T_FallBack*/, 6, "afraid, to the pack's rear");
			M.B.DoMoveToDestination('Mind_PackRear', NextLeg(M, Away));
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
		if (M.Species == 3/*S_Hound*/ && HoundEngagedAt == 0)
			HoundEngagedAt = Now;
		// melee: the angry and the hounds; not the scared; a pack hound only as its closer
		if (bAsks && M.Fear < 0.6 && !(bHoundPack && M.Species == 3/*S_Hound*/ && M.Role != 0 && M.Role != 3/*R_Closer*/))
		{
			S = 100 * FMin(Now - M.LastMelee, 20) - 0.5 * D + 600 * M.Anger * M.Aggression;
			if (bSight)
				S += 400;
			if (M.Species == 3/*S_Hound*/)
				S += 300;
			if (M.Role == 3/*R_Closer*/)
				S += 1500;
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

		// hounds: roles, zig-zag legs, pinning (packs on); or places round the prey, then a charge (off)
		if (Hounds >= 1 && bHoundPack)
			HoundPack(S, i, Enemy, Hounds);
		else if (Hounds >= 2)
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

// hound packs (AI-MINDS-DESIGN.md section 9) -----------------------------------------------------
// A pack of hounds fighting the player stops beelining. Roles are facts each hound reads (Horizon's
// group agent): the HOLDER keeps the front at HoundHold, feinting in and out, and never commits first;
// the FLANKERS go wide to +-HoundFlankAngle round the prey (out of its view, along the paths with the
// flank cost profile, to a scored spot); the CLOSER is the one that commits the leap: a flanker
// outside the prey's front cone, or the holder when the prey is pinned (a wall close behind it), or
// the nearest when the hold has run too long. Inside 600 units every move is a zig-zag of short legs
// (SkipLeg). A lone hound is a SKIRMISHER: it holds and skips, and commits when the prey is pinned or
// the hold runs out. Fear (Decide) breaks a hound off to the pack's rear; anger shortens the hold and
// narrows the front cone. Only the closer holds the melee token while it commits.

function HoundLog(string S)
{
	if (bHoundLog || bMindLog)
		class'ModSettings'.static.Note("hounds: " $ S);
}

function int PackOf(SquadAI S)
{
	local int i;

	for (i = 0; i < Packs.Length; i++)
		if (Packs[i].S == S)
			return i;
	Packs.Length = Packs.Length + 1;
	Packs[i].S = S;
	Packs[i].HoldSince = Level.TimeSeconds;
	return i;
}

// where the prey looks (its controller's view, flat) and, if it is moving, which way
function PreyFrame(Pawn Prey, out vector Facing, out vector Moving)
{
	local PlayerController PC;

	PC = PlayerController(Prey.Controller);
	if (PC != None)
		Facing = Normal(Vector(PC.Rotation) * vect(1,1,0));
	else
		Facing = Normal(Vector(Prey.Rotation) * vect(1,1,0));
	Moving = vect(0,0,0);
	if (VSize(Prey.Velocity * vect(1,1,0)) > 80)
		Moving = Normal(Prey.Velocity * vect(1,1,0));
}

// degrees round from where the prey looks to At: 0 straight ahead, 180 behind; + to its left, - to its right
function float Bearing(Pawn Prey, vector Facing, vector At)
{
	local vector To;
	local float A;

	To = Normal((At - Prey.Location) * vect(1,1,0));
	A = Acos(FClamp(To dot Facing, -1, 1)) * 57.2958;
	if ((Facing cross To).Z < 0)
		A = -A;
	return A;
}

static function vector Turned(vector V, float Degrees)
{
	local vector R;
	local float C, S;

	C = Cos(Degrees * 0.0174533);
	S = Sin(Degrees * 0.0174533);
	R.X = V.X * C - V.Y * S;
	R.Y = V.X * S + V.Y * C;
	R.Z = 0;
	return R;
}

function vector PackCentre(ModMind M)
{
	local int i, N;
	local vector C;

	for (i = 0; i < Minds.Length; i++)
		if (Minds[i].Species == 3/*S_Hound*/ && Minds[i].B.Squad == M.B.Squad && Minds[i].P.Health > 0)
		{
			C += Minds[i].P.Location;
			N++;
		}
	if (N == 0)
		return M.P.Location;
	return C / N;
}

// solid floor under At, not a drop from where M stands
function bool FloorUnder(ModMind M, vector At)
{
	local vector HitLoc, HitNorm;

	if (Trace(HitLoc, HitNorm, At - vect(0,0,1) * (M.P.CollisionHeight + 120), At + vect(0,0,20), false) == None)
		return false;
	return HitLoc.Z > M.P.Location.Z - M.P.CollisionHeight - 70;
}

// one zig-zag leg toward Goal: HoundSkipLeg long, HoundSkipAngle off the line, left and right by turns,
// to a point clear of walls and drops and not into the prey's teeth; now and then the engine's own
// dodge (Dodge_L/R root motion) instead of a run. Blocked both ways: straight at the goal, never a stall.
function SkipLeg(ModMind M, vector Goal, Pawn Prey)
{
	local vector To, Dir, End;
	local float Len, A;
	local int Try;

	To = (Goal - M.P.Location) * vect(1,1,0);
	if (VSize(To) < 50)
		To = Normal((M.P.Location - Prey.Location) * vect(1,1,0)) cross vect(0,0,1);   // there already: sidestep
	To = Normal(To);
	if (M.SkipSide == 0)
		M.SkipSide = 1;
	M.SkipSide = -M.SkipSide;
	M.SkipCount++;
	for (Try = 0; Try < 2; Try++)
	{
		A = (HoundSkipAngle + FRand() * 20 - 10) * M.SkipSide;
		if (Try == 1)
			A = -A;
		Dir = Turned(To, A);
		Len = HoundSkipLeg * (0.75 + 0.5 * FRand());
		End = M.P.Location + Dir * Len;
		if (VSize((End - Prey.Location) * vect(1,1,0)) < 230)
			continue;
		if (!FastTrace(End, M.P.Location) || !FloorUnder(M, End))
			continue;
		M.TaskDest = End;
		M.LegsSkipped++;
		M.bSkipDodge = false;
		SetTask(M, 9/*T_Skip*/, 1.2, "skip " $ int(A) $ " deg, " $ int(Len));
		if (HoundSkipDodge > 0 && FRand() < HoundSkipDodge && Level.TimeSeconds - M.B.LastDodgeTime > 2 && M.B.DoDodgeDir('Mind_SkipDodge', End))
		{
			M.bSkipDodge = true;
			return;
		}
		Go(M, 'Mind_Skip', End);
		return;
	}
	M.TaskDest = Goal;
	SetTask(M, 9/*T_Skip*/, 1.5, "skip blocked, straight");
	Go(M, 'Mind_SkipStraight', NextLeg(M, Goal));
}

// a flanker's spot: a path node near Want, at about HoundHold from the prey, far round from where the
// prey looks, not next to another hound (MateSpacing); the best few must have a straight run from
// the node to the prey (so the leap can come from there)
function vector HoundFlankSpot(ModMind M, vector Want, Pawn Prey, vector Facing)
{
	local NavigationPoint N;
	local float D, S, Off;
	local int i;
	local array<NavigationPoint> Top;
	local array<float> TopS;

	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		D = VSize(N.Location - Want);
		if (D > 800)
			continue;
		Off = Abs(Bearing(Prey, Facing, N.Location));
		S = 1000 - D * 0.6 - Abs(VSize(N.Location - Prey.Location) - HoundHold * 1.1) * 0.4 - MateSpacing(M, N.Location);
		if (Off > HoundCommitFront * 0.5)
			S += 300;           // out of its view cone
		S += Off * 2;
		Keep(N, S, Top, TopS);
	}
	for (i = 0; i < Top.Length; i++)
		if (FastTrace(Prey.Location, Top[i].Location + vect(0,0,30)))
		{
			HoundLog(M.P.Name $ " flank spot #" $ (i + 1) $ " of " $ Top.Length $ " (score " $ int(TopS[i]) $ "), " $ int(VSize(Top[i].Location - Want)) $ " from the wanted point");
			return Top[i].Location;
		}
	return Want;
}

// the closer: takes the pack's melee token and goes
function HoundCommit(ModMind M, Pawn Prey, string Why)
{
	local int i;

	for (i = 0; i < Minds.Length; i++)
		if (Minds[i] != M && Minds[i].Species == 3/*S_Hound*/ && Minds[i].B.Squad == M.B.Squad && Minds[i].Role != 3/*R_Closer*/)
			Minds[i].bMeleeToken = false;
	M.Role = 3/*R_Closer*/;
	M.RoleSince = Level.TimeSeconds;
	M.bMeleeToken = true;
	M.LastMelee = Level.TimeSeconds;
	M.Commits++;
	M.LastCommit = Level.TimeSeconds;
	M.ReissueAt = Level.TimeSeconds + 0.5;
	Steer(M);
	SetTask(M, 5/*T_Charge*/, 4, "commit: " $ Why);
	HoundLog(M.P.Name $ " commits (" $ Why $ "), " $ int(VSize(M.P.Location - Prey.Location)) $ " from the prey");
	// by a wall when one fits: the leap at the prey comes off it; the charge follows the landing (Decide
	// gives it again when the kick ends)
	if (FRand() < WallKickChance && TryKick(M, Prey.Location, PreyLeapTarget(M, Prey), true, "commit"))
		return;
	M.B.DoCharge('Mind_PackCommit', Prey);
}

// the pack's thinking, once per squad per tick (from Squads)
function HoundPack(SquadAI S, int First, Pawn Prey, int Hounds)
{
	local int j, Pk, Side, Behind, Closers, Pack;
	local ModMind O, Holder, Pick;
	local array<ModMind> Members;
	local float Now, B, Best, D, Hold, Front, AngerMax, Drive;
	local vector Facing, Moving, Want, Back, HitLoc, HitNorm;
	local bool bHurt, bPinned, bCommit, bNewRoles;
	local string Why;

	Now = Level.TimeSeconds;
	for (j = First; j < Minds.Length; j++)
	{
		O = Minds[j];
		if (O.B.Squad != S || O.Species != 3/*S_Hound*/ || O.P.Health <= 0 || O.B.EnemyInfo.Enemy == None)
			continue;
		if (O.Task == 10/*T_Want*/)
			continue;               // feeding or regrouping in a lull (ModNeeds): out of the roles until it is done
		Members[Members.Length] = O;
		if ((Now - O.LastHit < 1.0 && O.Role != 3/*R_Closer*/) || O.Role == 0)
			bHurt = true;           // deal roles now: one is hurt, or one has none (its charge just ended)
		if (O.Task == 5/*T_Charge*/ && O.Role == 3/*R_Closer*/)
			Closers++;
		AngerMax = FMax(AngerMax, O.Anger);
		if (Needs != None)
			Drive += Needs.HuntDrive(O.P);
	}
	Pack = Members.Length;
	if (Pack == 0)
		return;
	// the hunting drive (ModNeeds: hunger): 1 without the needs layer; a fed pack (0.2) holds longer and
	// commits only from well round the side, a starved one (1) commits early and from nearer the front
	if (Needs != None)
		Drive = Drive / Pack;
	else
		Drive = 0.6;                // half hungry: the stock cone and hold
	Pk = PackOf(S);
	PreyFrame(Prey, Facing, Moving);

	// roles: every 1.5 s, or at once when one is hurt (a hurt holder drops to a flank) or has none
	if (Now - Packs[Pk].RoleAt > 1.5 || bHurt)
	{
		Packs[Pk].RoleAt = Now;
		for (j = 0; j < Pack; j++)
			if (Members[j].Role == 3/*R_Closer*/ && Members[j].Task != 5/*T_Charge*/)
				Members[j].Role = 0;
		if (Pack == 1)
		{
			O = Members[0];
			if (O.Role != 4/*R_Skirmisher*/ && O.Role != 3/*R_Closer*/)
			{
				O.Role = 4/*R_Skirmisher*/;
				O.RoleSince = Now;
				HoundLog(O.P.Name $ " alone: skirmisher");
			}
		}
		else
		{
			// the holder: nearest the prey's front; the current one keeps it while it is still in front and unhurt
			Best = 100000;
			for (j = 0; j < Pack; j++)
			{
				O = Members[j];
				if (O.Role == 3/*R_Closer*/ || O.Fear > FleeFear)
					continue;
				B = Abs(Bearing(Prey, Facing, O.P.Location));
				D = B + VSize(O.P.Location - Prey.Location) * 0.05;
				if (O.Role == 1/*R_Holder*/ && B < 60 && Now - O.LastHit > 1.0)
					D -= 40;
				if (D < Best)
				{
					Best = D;
					Holder = O;
				}
			}
			if (Holder != None && Holder.Role != 1/*R_Holder*/)
			{
				Holder.Role = 1/*R_Holder*/;
				Holder.RoleSince = Now;
				Holder.SkipCount = 0;
				bNewRoles = true;
			}
			// the rest flank, sides by turns so the prey has a hound on each side when there are three
			Side = 0;
			for (j = 0; j < Pack; j++)
			{
				O = Members[j];
				if (O == Holder || O.Role == 3/*R_Closer*/)
					continue;
				if (O.Role != 2/*R_Flanker*/)
				{
					O.Role = 2/*R_Flanker*/;
					O.RoleSince = Now;
					O.bInPlace = false;
					bNewRoles = true;
					B = Bearing(Prey, Facing, O.P.Location);
					if (Side == 0)
					{
						O.FlankSide = 1;
						if (B < 0)
							O.FlankSide = -1;
					}
					else
						O.FlankSide = -Side;
				}
				Side = O.FlankSide;
			}
		}
		if (bNewRoles)
		{
			Why = "";
			for (j = 0; j < Pack; j++)
				Why = Why $ " " $ Members[j].P.Name $ "=" $ Members[j].RoleName(Members[j].Role);
			HoundLog("roles (" $ Pack $ " hounds):" $ Why);
		}
	}
	if (Holder == None)
		for (j = 0; j < Pack; j++)
			if (Members[j].Role == 1/*R_Holder*/ || Members[j].Role == 4/*R_Skirmisher*/)
				Holder = Members[j];

	// the prey pinned: a wall close behind it (behind its movement, or away from the holder)
	Back = -Moving;
	if (Moving == vect(0,0,0))
	{
		if (Holder != None)
			Back = Normal((Prey.Location - Holder.P.Location) * vect(1,1,0));
		else
			Back = -Facing;
	}
	bPinned = Trace(HitLoc, HitNorm, Prey.Location + Back * HoundPinWall, Prey.Location, false) != None;
	if (bPinned != Packs[Pk].bPinned)
	{
		Packs[Pk].bPinned = bPinned;
		if (bPinned)
		{
			Packs[Pk].Pins++;
			HoundLog("pin: a wall " $ int(VSize(HitLoc - Prey.Location)) $ " behind the prey");
		}
		else
			HoundLog("pin: the prey is free again");
	}

	// commit? a flanker outside the prey's front cone (narrower the angrier the pack), or the prey pinned,
	// or the hold has run too long (shorter the angrier)
	Front = HoundCommitFront * 0.5 * (1 - 0.3 * AngerMax) * (1.3 - 0.5 * Drive);   // drive 0.2: x1.2, 0.6: x1, 1: x0.8
	Hold = HoundHoldMax * (1 - 0.6 * AngerMax) * (1.6 - Drive);                     // drive 0.2: x1.4, 0.6: x1, 1: x0.6
	Best = 0;
	for (j = 0; j < Pack; j++)
	{
		O = Members[j];
		if (O.Role != 2/*R_Flanker*/ || Busy(O) || O.Fear > FleeFear)
			continue;
		B = Abs(Bearing(Prey, Facing, O.P.Location));
		D = VSize(O.P.Location - Prey.Location);
		if (B > Front && D < 750 && Now - O.LastCommit > 3)
		{
			Behind++;
			if (B > Best)
			{
				Best = B;
				Pick = O;
			}
		}
	}
	if ((Closers == 0 || (bPinned && Pack >= 3 && Closers < 2)) && Now - Packs[Pk].CommitAt > 1.5)
	{
		if (Pick != None)
		{
			bCommit = true;
			Why = "flanker " $ int(Best) $ " deg round";
		}
		else if (bPinned && Holder != None && !Busy(Holder) && Holder.Fear <= FleeFear && Holder.Task != 5/*T_Charge*/
			&& Now - Holder.LastCommit > 3 && VSize(Holder.P.Location - Prey.Location) < 750)
		{
			Pick = Holder;
			bCommit = true;
			Why = "the prey is pinned";
		}
		else if (Now - Packs[Pk].HoldSince > Hold)
		{
			Best = 100000;
			for (j = 0; j < Pack; j++)
			{
				O = Members[j];
				if (O.Role == 3/*R_Closer*/ || Busy(O) || O.Fear > FleeFear || Now - O.LastCommit < 3)
					continue;
				D = VSize(O.P.Location - Prey.Location);
				if (D < Best)
				{
					Best = D;
					Pick = O;
				}
			}
			if (Pick != None && Best < 900)
			{
				bCommit = true;
				Why = "held " $ int(Now - Packs[Pk].HoldSince) $ " s";
			}
			else
				Packs[Pk].HoldSince += 2;      // nobody near enough yet: the hold goes on
		}
		if (bCommit)
		{
			Packs[Pk].HoldSince = Now;
			Packs[Pk].CommitAt = Now;
			HoundCommit(Pick, Prey, Why);
		}
	}

	// each hound's next move
	for (j = 0; j < Pack; j++)
	{
		O = Members[j];
		if (O.Task != 0/*T_None*/ || Busy(O) || Now < O.LegAt || O.Fear > FleeFear)
			continue;
		D = VSize((O.P.Location - Prey.Location) * vect(1,1,0));
		switch (O.Role)
		{
		case 1/*R_Holder*/:
		case 4/*R_Skirmisher*/:
			// the front: a ring round the prey at HoundHold, feinting in (even legs) and out (odd)
			Want = Prey.Location + Normal((O.P.Location - Prey.Location) * vect(1,1,0)) * (HoundHold + 70 - 140 * (O.SkipCount % 2));
			// the stalk tell (ModNeeds): a hungry holder croons before the pack commits (the sound comes later)
			if (Needs != None && Now - O.TellAt > 4 && Needs.WantsTell(O.P))
			{
				O.TellAt = Now;
				HoundLog(O.P.Name $ " croons (hunger " $ int(Needs.NeedOf(O.P, 0) * 100) $ ", drive " $ int(Drive * 100) $ ")");
			}
			if (D > 600)
			{
				O.TaskDest = Want;
				SetTask(O, 8/*T_Advance*/, 5, "to the front");
				Go(O, 'Mind_PackFront', NextLeg(O, Want));
			}
			else
				SkipLeg(O, Want, Prey);
			break;
		case 2/*R_Flanker*/:
			// round the prey to +-HoundFlankAngle from where it looks; far: a path leg to a scored spot
			// (the flank profile keeps it out of the prey's view); near: zig-zag legs; in place: keep the
			// angle as the prey turns and moves
			B = Bearing(Prey, Facing, O.P.Location);
			Want = Prey.Location + Turned(Facing, HoundFlankAngle * O.FlankSide) * HoundHold * 1.1;
			if (!O.bInPlace && Abs(B) > HoundFlankAngle - 35 && D < 700)
			{
				O.bInPlace = true;
				O.FlankArrivals++;
				HoundLog(O.P.Name $ " in place on the prey's flank, " $ int(B) $ " deg round, " $ int(D) $ " away");
			}
			if (D > 600 || (!O.bInPlace && Abs(B) < 45 && D > 400))
			{
				Want = HoundFlankSpot(O, Want, Prey, Facing);
				O.TaskDest = Want;
				SetTask(O, 4/*T_Flank*/, 6, "flank leg " $ O.FlankSide);
				Go(O, 'Mind_PackFlank', NextLeg(O, Want));
			}
			else if (FRand() < WallKickChance * 0.5 && TryKick(O, O.P.Location + Normal((O.P.Location - Prey.Location) * vect(1,1,0)) * 300, Want, false, "flank"))
			{
				// off a wall on its outer side, landing at its flank spot
				O.TaskDest = Want;
				SetTask(O, 4/*T_Flank*/, 3, "flank kick");
			}
			else
				SkipLeg(O, Want, Prey);
			break;
		case 3/*R_Closer*/:
			// its charge is over: back to the pack's roles at the next deal
			O.Role = 0;
			break;
		}
	}
	if (bHoundLog && Now - Packs[Pk].LogAt > 2)
	{
		Packs[Pk].LogAt = Now;
		Why = "";
		for (j = 0; j < Pack; j++)
		{
			O = Members[j];
			Why = Why $ " " $ O.P.Name $ " " $ O.RoleName(O.Role) $ "/" $ O.TaskName(O.Task) $ " " $ int(VSize(O.P.Location - Prey.Location)) $ "@" $ int(Bearing(Prey, Facing, O.P.Location));
		}
		HoundLog("pack of " $ Pack $ ", " $ Behind $ " behind the front cone, pinned " $ bPinned $ ", held " $ int(Now - Packs[Pk].HoldSince) $ " of " $ int(Hold) $ " s, drive " $ int(Drive * 100) $ ":" $ Why);
	}
}

// wall-kicks and leap links (AI-MINDS-DESIGN.md section 10) --------------------------------------
// The RAGE hopper's move, the stock Seeker chain (TryLeapToWall -> Leap -> CheckWallJump -> WallJumpBegin
// -> WallJumpEnd -> RequestLeapOffWall) driven from script for hounds: a leap to a point on a wall along
// an arc swept clear for the body, a short plant on the wall (PHYS_None, turned at the target, the hips
// pitched up in its leap crouch), then a leap off it at the prey (a leap attack, so it bites on contact)
// or to a spot (a flanker's place, a link's far end). The engine's own wall test (Seeker.CheckWallJump,
// which the hound inherits) is kept out of it: it plays the upright Seekers' WallJump clips, which fold
// the hound wrong, and its leap off goes where the engine likes.

function KickLog(string S)
{
	if (bWallKickLog || bHoundLog || bMindLog)
		class'ModSettings'.static.Note("wallkick: " $ S);
}

static function string IfText(bool bCond, string T, string F)
{
	if (bCond)
		return T;
	return F;
}

function float Gravity(Actor A)
{
	local float G;

	G = 0;
	if (A != None && A.PhysicsVolume != None)
		G = Abs(A.PhysicsVolume.Gravity.Z);
	if (G < 100)
		G = 3000;               // the game's default (PhysicsVolume Gravity Z = -3000)
	return G;
}

// the ballistic velocity from From to To at about Speed over the ground: closed form by time, as
// ModAction's vault (the flight time from the ground distance, the rise from the time and the drop)
static function vector Arc(vector From, vector To, float Speed, float G, out float Flight)
{
	local vector V;
	local float Dist;

	Dist = VSize((To - From) * vect(1,1,0));
	Flight = FMax(Dist / FMax(Speed, 100), 0.25);
	V = (To - From) * vect(1,1,0) / Flight;
	V.Z = (To.Z - From.Z) / Flight + 0.5 * G * Flight;
	return V;
}

static function vector ArcAt(vector From, vector V, float G, float T)
{
	return From + V * T - vect(0,0,1) * (0.5 * G * T * T);
}

// the body swept along the arc, clear of the world (Doom 3's TestTrajectory: a few segments)
function bool ArcClear(vector From, vector V, float G, float Flight, vector Extent)
{
	local int i;
	local vector Prev, Next, HitLoc, HitNorm;
	local Actor A;

	// (the last segment stops short of the landing: touching the floor there is the landing itself)
	Prev = From;
	for (i = 1; i <= 6; i++)
	{
		Next = ArcAt(From, V, G, Flight * FMin(i / 6.0, 0.9));
		A = Trace(HitLoc, HitNorm, Next, Prev, false, Extent);
		if (A != None)
		{
			ArcBlock = A.Name $ " on segment " $ i $ " (n.z " $ (int(HitNorm.Z * 100) / 100.0) $ ", " $ int(VSize(HitLoc - From)) $ " out, " $ int(HitLoc.Z - From.Z) $ " up)";
			return false;
		}
		Prev = Next;
	}
	return true;
}

// what counts as a wall to kick off: the level, or a static blocking thing (a static mesh, a prop)
static function bool IsWall(Actor A)
{
	return A != None && (A.bWorldGeometry || (A.bStatic && A.bBlockActors) || A.IsA('StaticMeshActor'));
}

function float LeapSpeed(ModMind M)
{
	local float S;

	S = 0;
	if (M.P.Ability != None)
		S = M.P.Ability.DesiredLeapSpeed;
	if (S < 300)
		S = 1000;
	return S;
}

static function vector BodyExtent(float Radius, float Height)
{
	return vect(1,1,0) * (Radius * 0.7) + vect(0,0,1) * (Height * 0.5);
}

// a wall to kick off: within WallKickRange, 45 then 70 degrees either side of the line from M toward
// Toward (the line pitched up 16 degrees, as the stock TryLeapToWall aims, so the plant is above the
// hound), world geometry, its normal in the band the stock WallJumpBegin takes (-0.17..0.5) and facing
// the target, with the arc to the plant point and the arc off it to Target both clear for the body
function bool FindKickWall(ModMind M, vector Toward, vector Target, out vector Wall, out vector Norm, out vector V1, out float Flight1)
{
	local vector Dir, Aim, HitLoc, HitNorm, Plant, V2, Extent;
	local int Side, Try;
	local float Angle, D, G, Flight2;
	local Actor A;
	local string Why;

	Dir = Normal((Toward - M.P.Location) * vect(1,1,0));
	if (Dir == vect(0,0,0))
		return false;
	Extent = BodyExtent(M.P.CollisionRadius, M.P.CollisionHeight);
	G = Gravity(M.P);
	Side = 1;
	if (FRand() < 0.5)
		Side = -1;
	for (Try = 0; Try < 8; Try++)
	{
		// 45 then 70 degrees, each pitched up 16 degrees then flat
		Angle = 45;
		if (Try % 4 >= 2)
			Angle = 70;
		if (Try % 2 == 1)
			Side = -Side;
		Aim = Turned(Dir, Angle * Side);
		if (Try < 4)
			Aim = Normal(Aim + vect(0,0,1) * 0.3);
		A = Trace(HitLoc, HitNorm, M.P.Location + Aim * WallKickRange, M.P.Location, false);
		Why = Why $ " " $ int(Angle * Side) $ IfText(Try < 4, "up", "flat") $ ":";
		if (A == None)
		{
			Why = Why $ "nothing";
			continue;
		}
		if (!IsWall(A))
		{
			Why = Why $ A.Name $ " (not a wall)";
			continue;
		}
		D = VSize(HitLoc - M.P.Location);
		if (HitNorm.Z < -0.17 || HitNorm.Z > 0.5)
		{
			Why = Why $ "slope " $ (int(HitNorm.Z * 100) / 100.0) $ " at " $ int(D);
			continue;
		}
		if (D < 250)
		{
			Why = Why $ "too near " $ int(D);     // (the hound is 60 wide: nearer than this is a hop, not a leap)
			continue;
		}
		Plant = HitLoc + HitNorm * (M.P.CollisionRadius + 8);
		if ((HitNorm dot Normal(Target - Plant)) <= 0)
		{
			Why = Why $ "faces away at " $ int(D);   // the leap off must go out from the wall (the stock RequestLeapOffWall's rule)
			continue;
		}
		if (VSize((Target - Plant) * vect(1,1,0)) < 100 || VSize(Target - Plant) > WallKickRange * 1.3)
		{
			Why = Why $ "target " $ int(VSize(Target - Plant)) $ " from the wall";
			continue;
		}
		V1 = Arc(M.P.Location, Plant, LeapSpeed(M), G, Flight1);
		if (!ArcClear(M.P.Location, V1, G, Flight1, Extent))
		{
			Why = Why $ "arc in blocked at " $ int(D) $ " by " $ ArcBlock;
			continue;
		}
		V2 = Arc(Plant, Target, LeapSpeed(M), G, Flight2);
		if (!ArcClear(Plant, V2, G, Flight2, Extent))
		{
			Why = Why $ "arc out blocked at " $ int(D) $ " by " $ ArcBlock;
			continue;
		}
		Wall = Plant;
		Norm = HitNorm;
		return true;
	}
	KickLog(M.P.Name $ " walls:" $ Why);
	return false;
}

// the leap itself, as the stock Seeker launches at the end of its pre-jump clip (startSeekerPhysicalJump:
// Velocity = jumpVelocity, PHYS_Falling, DidJump), without the clip: the root-motion pre-jump would hang
// the hound mid-air at the wall, and the engine re-aims a non-attack jump at the bot's Target, so that is
// put aside for the call. A leap attack keeps the Target (the prey) so the engine may re-aim at it and the
// air attack bites on contact.
function bool Launch(ModMind M, vector V, bool bAttack)
{
	local Seeker S;
	local Actor OldTarget;

	S = Seeker(M.P);
	if (S == None)
		return false;
	S.wallJumps = 4;                // the engine's own wall-jump test refuses (it resets on landing)
	S.bIsRunningJump = true;        // its running-leap apex and landing clips
	S.bIsLeapAttacking = bAttack;
	S.jumpVelocity = V;
	OldTarget = M.B.Target;
	if (!bAttack)
		M.B.Target = None;
	S.startSeekerPhysicalJump();
	if (!bAttack)
		M.B.Target = OldTarget;
	return M.P.Physics == PHYS_Falling;
}

// where a leap attack at the prey goes (as the stock LeapAttack state aims: a little ahead, up to its chest)
function vector PreyLeapTarget(ModMind M, Pawn Prey)
{
	local vector T;

	T = Prey.Location + Prey.Velocity * 0.25;
	if (M.P.Ability == None || M.P.Ability.LeapAttackOffset == 0)
		T.Z += Prey.CollisionHeight * 0.5;
	return T;
}

// the kick begins: the hound leaps to Wall along V1 (the arc swept clear), to kick off toward Target
function bool StartKick(ModMind M, vector Wall, vector Norm, vector V1, float Flight1, vector Target, bool bAttack, string Why)
{
	local float Now;

	Now = Level.TimeSeconds;
	if (M.P.Physics != PHYS_Walking || !M.P.bAllowInput)
	{
		KickLog(M.P.Name $ " can't kick (" $ Why $ "): physics " $ M.P.Physics $ ", input " $ M.P.bAllowInput);
		return false;
	}
	M.B.Destination = Wall;
	M.P.SetRotation(rotator((Wall - M.P.Location) * vect(1,1,0)));
	if (!Launch(M, V1, false))
	{
		KickLog(M.P.Name $ " jump refused (" $ Why $ ")");
		return false;
	}
	M.B.DoWait('Mind_WallKick', Flight1 + WallKickPlant + 1.5);   // (refused in the same frame as another change: harmless, the kick runs from KickTick)
	M.Kick = 1;
	M.KickTime = 0;
	M.KickFlight = Flight1;
	M.KickWall = Wall;
	M.KickNormal = Norm;
	M.KickTarget = Target;
	M.bKickAttack = bAttack;
	M.KickAt = Now;
	M.Kicks++;
	KickLog(M.P.Name $ " kicks (" $ Why $ "): wall " $ int(VSize(Wall - M.P.Location)) $ " away, n.z " $ (int(Norm.Z * 100) / 100.0) $ ", " $ (int(Flight1 * 100) / 100.0) $ " s to it, then " $ int(VSize(Target - Wall)) $ " off it");
	return true;
}

// a kick at the prey (a closer) or to a spot (a flanker): the wall is found first; bForce (the pilot) ignores the switch and cooldown
function bool TryKick(ModMind M, vector Toward, vector Target, bool bAttack, string Why, optional bool bForce)
{
	local vector Wall, Norm, V1;
	local float Flight1, Now;

	Now = Level.TimeSeconds;
	if (M.Species != 3/*S_Hound*/ || M.Kick != 0 || M.P.Health <= 0)
		return false;
	if (!bForce && (!bHoundWallKick || Now - M.KickAt < WallKickCool))
		return false;
	if (!FindKickWall(M, Toward, Target, Wall, Norm, V1, Flight1))
	{
		M.KickAt = Now - WallKickCool + 1.0;     // another look in a second
		KickLog(M.P.Name $ " no wall (" $ Why $ ")");
		return false;
	}
	return StartKick(M, Wall, Norm, V1, Flight1, Target, bAttack, Why);
}

// the kick, tick by tick (Decide hands over while M.Kick != 0)
function KickTick(ModMind M, float DeltaTime)
{
	local vector HitLoc, HitNorm;
	local float D, Now;
	local bool bAtWall;

	Now = Level.TimeSeconds;
	M.KickTime += DeltaTime;
	if (M.P.Health <= 0 || M.P.Physics == PHYS_KarmaRagdoll)
	{
		KickEnd(M, "down");
		return;
	}
	switch (M.Kick)
	{
	case 1:
		// flying to the wall
		if (M.P.Physics == PHYS_Walking && M.KickTime > 0.1)
		{
			KickEnd(M, "landed short, " $ int(VSize(M.P.Location - M.KickWall)) $ " from the wall");
			return;
		}
		if (M.P.Physics != PHYS_Falling && (M.P.Physics != PHYS_RootMotion || M.KickTime > M.KickFlight + 0.4))
		{
			KickEnd(M, "physics changed to " $ M.P.Physics);
			return;
		}
		D = VSize(M.P.Location - M.KickWall);
		bAtWall = D < M.P.CollisionRadius + 30;
		// or past the apex and touching the wall (the stock CheckWallJump's trace)
		if (!bAtWall && M.P.Velocity.Z < 30 && M.KickTime > M.KickFlight * 0.5
			&& Trace(HitLoc, HitNorm, M.P.Location - M.KickNormal * (M.P.CollisionRadius + 20), M.P.Location, false) != None)
			bAtWall = true;
		if (bAtWall)
			KickPlant(M, D);
		else if (M.KickTime > M.KickFlight + 0.4)
			KickEnd(M, "missed the wall, " $ int(D) $ " off");
		break;
	case 2:
		// planted
		if (M.KickTime >= WallKickPlant)
			KickLeapOff(M);
		break;
	case 3:
		// leaping off: done on landing
		if ((M.P.Physics == PHYS_Walking && M.KickTime > 0.15) || M.KickTime > 2.5 || (M.P.Physics != PHYS_Falling && M.P.Physics != PHYS_Walking && M.P.Physics != PHYS_RootMotion))
		{
			KickLog(M.P.Name $ " landed after " $ (int(M.KickTime * 100) / 100.0) $ " s, " $ int(VSize((M.P.Location - M.KickTarget) * vect(1,1,0))) $ " from the target");
			if (M.Link != None)
			{
				M.Link.Uses++;
				M.LinkUses++;
				M.Link = None;
			}
			M.Kick = 0;
			M.LegAt = Now + 0.2;
			M.ReissueAt = Now;      // a closer's charge is given again at once (Decide), a leg goes on from here
			if (M.bKickAttack && M.Task == 5/*T_Charge*/)
				M.TaskTime = 0;     // the charge gets its full time after the leap
		}
		break;
	}
}

// on the wall: still, snapped to the plant point, turned at the target, crouched for the push-off
function KickPlant(ModMind M, float D)
{
	local rotator R;

	M.P.SetPhysics(PHYS_None);
	M.P.Velocity = vect(0,0,0);
	M.P.Acceleration = vect(0,0,0);
	if (D < 130)
		M.P.SetLocation(M.KickWall);    // (fails against the wall: then it plants where it is)
	R = rotator((M.KickTarget - M.P.Location) * vect(1,1,0));
	M.P.SetRotation(R);
	M.P.DesiredRotation = R;
	M.B.DesiredRotation = R;
	// the push-off pose: nose up (the hips pitched; ModBody leaves the hips alone while it is not walking)
	// and its leap crouch clip
	// (no clip: the end of the Seeker's pre-jump clips launches its own jump, so the pose is the hips alone)
	R = rot(0,0,0);
	R.Pitch = 6400;
	M.P.SetBoneRotation('hips', R, 0, 1);
	KickLog(M.P.Name $ " planted after " $ (int(M.KickTime * 100) / 100.0) $ " s, " $ int(D) $ " from the spot");
	M.Kick = 2;
	M.KickTime = 0;
	M.KicksPlanted++;
}

// off the wall: at the prey (a leap attack, re-aimed at it now) or to the spot
function KickLeapOff(ModMind M)
{
	local vector Target, V;
	local float Flight, G;
	local bool bOk;
	local Pawn Prey;

	M.P.SetBoneRotation('hips', rot(0,0,0), 0, 0);
	Target = M.KickTarget;
	Prey = M.B.EnemyInfo.Enemy;
	if (M.bKickAttack && Prey != None && Prey.Health > 0 && VSize(Prey.Location - M.P.Location) < WallKickRange * 1.5)
		Target = PreyLeapTarget(M, Prey);
	G = Gravity(M.P);
	V = Arc(M.P.Location, Target, LeapSpeed(M), G, Flight);
	M.P.SetPhysics(PHYS_Walking);
	M.B.Destination = Target;
	M.P.SetRotation(rotator((Target - M.P.Location) * vect(1,1,0)));
	bOk = Launch(M, V, M.bKickAttack);
	if (!bOk)
	{
		M.P.SetPhysics(PHYS_Falling);
		KickEnd(M, "leap off refused");
		return;
	}
	M.Kick = 3;
	M.KickTime = 0;
	M.KickLeaps++;
	M.KickLeapAt = Level.TimeSeconds;
	KickLog(M.P.Name $ " leaps off " $ IfText(M.bKickAttack, "at the prey", "to its spot") $ ", " $ int(VSize(Target - M.P.Location)) $ " away, " $ (int(Flight * 100) / 100.0) $ " s");
}

function KickEnd(ModMind M, string Why)
{
	if (M.P.Physics == PHYS_None)
		M.P.SetPhysics(PHYS_Falling);
	M.P.SetBoneRotation('hips', rot(0,0,0), 0, 0);
	M.Kick = 0;
	M.Link = None;
	M.LegAt = Level.TimeSeconds + 0.3;
	M.ReissueAt = Level.TimeSeconds;
	KickLog(M.P.Name $ " " $ Why);
}

// pilot WALLKICK: the hound nearest the player kicks off a wall at it now, if one fits
function string ForceKick()
{
	local PlayerController PC;
	local ModMind M, Best;
	local int i;
	local float D, BestD;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return "no player";
	BestD = 100000;
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (M.Species != 3/*S_Hound*/ || M.P.Health <= 0)
			continue;
		D = VSize(M.P.Location - PC.Pawn.Location);
		if (D < BestD)
		{
			BestD = D;
			Best = M;
		}
	}
	if (Best == None)
		return "no hound";
	KickLog(Best.P.Name $ " around it: " $ Around(Best.P));
	if (TryKick(Best, PC.Pawn.Location, PreyLeapTarget(Best, PC.Pawn), true, "pilot", true))
		return Best.P.Name $ " kicks from " $ int(BestD);
	return Best.P.Name $ " at " $ int(BestD) $ ": no kick (see wallkick: lines)";
}

// what the flat traces hit round P, every 45 degrees (the pilot's WALLKICK)
function string Around(Pawn P)
{
	local int i;
	local vector Dir, HitLoc, HitNorm;
	local Actor A;
	local string S;

	for (i = 0; i < 8; i++)
	{
		Dir = Turned(vect(1,0,0), i * 45);
		A = Trace(HitLoc, HitNorm, P.Location + Dir * WallKickRange, P.Location, false);
		S = S $ " " $ (i * 45) $ ":";
		if (A == None)
			S = S $ "-";
		else
			S = S $ A.Name $ "@" $ int(VSize(HitLoc - P.Location)) $ "/" $ (int(HitNorm.Z * 100) / 100.0);
	}
	return S;
}

// leap links (the report's Rule 1), built once per level from the path graph, a few nodes a tick: two
// nodes within 1.5 x WallKickRange whose walk route is 2.5 x the straight line or more (Dijkstra over
// the ReachSpecs with that cutoff), a wall beside the straight line (traced from its midpoint to either
// side, a hound's height up) whose normal fits the wall-kick band and faces the far node, and both arcs
// clear for a hound's body. The best LeapLinksMax by saving are kept; two-way when the reverse arcs pass.
function BuildLinks()
{
	local int i, j, k, Budget, Idx;
	local NavigationPoint A, B;
	local float D, Route, Ratio, T0;
	local vector Wall, Norm;
	local int Two;
	local class<Pawn> Hound;
	local string S;

	T0 = 0;
	BuildNodes();
	if (LinkAt == 0)
	{
		LinkDist.Length = Nodes.Length;
		Hound = class<Pawn>(DynamicLoadObject("EonCharacters.SeekerDog", class'Class'));
		LinkRadius = 34;
		LinkHeight = 40;
		LinkSpeed = 1000;
		if (Hound != None)
		{
			LinkRadius = Hound.default.CollisionRadius;
			LinkHeight = Hound.default.CollisionHeight;
			if (Hound.default.Ability != None && Hound.default.Ability.DesiredLeapSpeed >= 300)
				LinkSpeed = Hound.default.Ability.DesiredLeapSpeed;
		}
	}
	// the nodes stamped with their index (visitedWeight: the engine's own search rewrites it, so each slice stamps again)
	for (i = 0; i < Nodes.Length; i++)
		if (Nodes[i] != None)
			Nodes[i].visitedWeight = i;
	Budget = 3;
	while (Budget > 0 && LinkAt < Nodes.Length)
	{
		A = Nodes[LinkAt];
		Idx = LinkAt;
		LinkAt++;
		if (A == None || A.bBlocked)
			continue;
		Budget--;
		Dijkstra(A, 2.5 * 1.5 * WallKickRange);
		for (j = 0; j < Nodes.Length; j++)
		{
			B = Nodes[j];
			if (B == None || B == A || B.bBlocked)
				continue;
			D = VSize(B.Location - A.Location);
			if (D < 250 || D > 1.5 * WallKickRange || Abs(B.Location.Z - A.Location.Z) > 160)
				continue;
			// a link the other way round already (it was tested two-way then)
			for (k = 0; k < CandA.Length; k++)
				if (CandA[k] == B && CandB[k] == A)
					break;
			if (k < CandA.Length)
				continue;
			LinkPairs++;
			Route = LinkDist[j];
			if (Route >= 0 && Route < 2.5 * D)
				continue;
			if (!LinkWall(A, B, Wall, Norm, Two))
				continue;
			LinkFits++;
			Ratio = 99;
			if (Route > 0)
				Ratio = Route / D;
			// kept sorted by saving, at most LeapLinksMax
			for (k = 0; k < CandA.Length; k++)
				if (Ratio > CandRatio[k])
					break;
			if (k >= LeapLinksMax)
				continue;
			CandA.Insert(k, 1);
			CandB.Insert(k, 1);
			CandWall.Insert(k, 1);
			CandNorm.Insert(k, 1);
			CandRoute.Insert(k, 1);
			CandRatio.Insert(k, 1);
			CandTwo.Insert(k, 1);
			CandA[k] = A;
			CandB[k] = B;
			CandWall[k] = Wall;
			CandNorm[k] = Norm;
			CandRoute[k] = Route;
			CandRatio[k] = Ratio;
			CandTwo[k] = Two;
			if (CandA.Length > LeapLinksMax)
			{
				CandA.Length = LeapLinksMax;
				CandB.Length = LeapLinksMax;
				CandWall.Length = LeapLinksMax;
				CandNorm.Length = LeapLinksMax;
				CandRoute.Length = LeapLinksMax;
				CandRatio.Length = LeapLinksMax;
				CandTwo.Length = LeapLinksMax;
			}
		}
	}
	if (LinkAt < Nodes.Length)
		return;
	// done: the links placed (hidden actors at their plant points) and listed once
	bLinksBuilt = true;
	for (k = 0; k < CandA.Length; k++)
	{
		Links[k] = Spawn(class'ModLeapLink',,, CandWall[k]);
		if (Links[k] == None)
			continue;
		Links[k].A = CandA[k];
		Links[k].B = CandB[k];
		Links[k].Wall = CandWall[k];
		Links[k].Normal = CandNorm[k];
		Links[k].Straight = VSize(CandB[k].Location - CandA[k].Location);
		Links[k].Route = CandRoute[k];
		Links[k].bTwoWay = CandTwo[k] != 0;
	}
	for (k = Links.Length - 1; k >= 0; k--)
		if (Links[k] == None)
			Links.Remove(k, 1);
	CandA.Length = 0;
	CandB.Length = 0;
	CandWall.Length = 0;
	CandNorm.Length = 0;
	CandRoute.Length = 0;
	CandRatio.Length = 0;
	CandTwo.Length = 0;
	LinkDist.Length = 0;
	S = "leaplinks: " $ Links.Length $ " links from " $ Nodes.Length $ " nodes (" $ LinkPairs $ " pairs looked at, " $ LinkFits $ " fit, cap " $ LeapLinksMax $ ", hound " $ int(LinkRadius) $ "x" $ int(LinkHeight) $ " at " $ int(LinkSpeed) $ ")";
	class'ModSettings'.static.Note(S);
	if (Links.Length > 0)
		class'ModSettings'.static.Note("leaplinks: " $ LinkList());
}

// the walk route's length from From to every node within Cutoff (LinkDist, -1 beyond it), over the ReachSpecs
function Dijkstra(NavigationPoint From, float Cutoff)
{
	local array<NavigationPoint> Open;
	local array<float> OpenD;
	local int i, Best, k, Idx;
	local NavigationPoint N, E;
	local float D;

	for (i = 0; i < LinkDist.Length; i++)
		LinkDist[i] = -1;
	Open[0] = From;
	OpenD[0] = 0;
	while (Open.Length > 0)
	{
		Best = 0;
		for (i = 1; i < Open.Length; i++)
			if (OpenD[i] < OpenD[Best])
				Best = i;
		N = Open[Best];
		D = OpenD[Best];
		Open.Remove(Best, 1);
		OpenD.Remove(Best, 1);
		Idx = N.visitedWeight;
		if (Idx < 0 || Idx >= Nodes.Length || Nodes[Idx] != N || LinkDist[Idx] >= 0)
			continue;
		LinkDist[Idx] = D;
		for (k = 0; k < N.PathList.Length; k++)
		{
			E = N.PathList[k].End;
			if (E == None || E.bBlocked || D + N.PathList[k].Distance > Cutoff)
				continue;
			Idx = E.visitedWeight;
			if (Idx < 0 || Idx >= Nodes.Length || Nodes[Idx] != E || LinkDist[Idx] >= 0)
				continue;
			Open[Open.Length] = E;
			OpenD[OpenD.Length] = D + N.PathList[k].Distance;
		}
	}
}

// a wall beside the line A-B a hound could kick off between them (see BuildLinks); Two: 1 when B -> A passes too
function bool LinkWall(NavigationPoint A, NavigationPoint B, out vector Wall, out vector Norm, out int Two)
{
	local vector Mid, Perp, HitLoc, HitNorm, Plant, V, Extent;
	local int Side;
	local float G, Flight;
	local Actor Hit;

	Mid = (A.Location + B.Location) * 0.5 + vect(0,0,1) * LinkHeight;
	Perp = Normal((B.Location - A.Location) cross vect(0,0,1));
	if (Perp == vect(0,0,0))
		return false;
	Extent = BodyExtent(LinkRadius, LinkHeight);
	G = Gravity(A);
	for (Side = -1; Side <= 1; Side += 2)
	{
		Hit = Trace(HitLoc, HitNorm, Mid + Perp * (Side * 0.6 * WallKickRange), Mid, false);
		if (!IsWall(Hit))
			continue;
		if (HitNorm.Z < -0.17 || HitNorm.Z > 0.5)
			continue;
		if (VSize(HitLoc - Mid) < 60)
			continue;
		Plant = HitLoc + HitNorm * (LinkRadius + 8);
		if ((HitNorm dot Normal(B.Location - Plant)) < 0.1)
			continue;
		V = Arc(A.Location, Plant, LinkSpeed, G, Flight);
		if (!ArcClear(A.Location, V, G, Flight, Extent))
			continue;
		V = Arc(Plant, B.Location, LinkSpeed, G, Flight);
		if (!ArcClear(Plant, V, G, Flight, Extent))
			continue;
		Wall = Plant;
		Norm = HitNorm;
		Two = 0;
		if ((HitNorm dot Normal(A.Location - Plant)) >= 0.1)
		{
			V = Arc(B.Location, Plant, LinkSpeed, G, Flight);
			if (ArcClear(B.Location, V, G, Flight, Extent))
			{
				V = Arc(Plant, A.Location, LinkSpeed, G, Flight);
				Two = int(ArcClear(Plant, V, G, Flight, Extent));
			}
		}
		return true;
	}
	return false;
}

// a link the hound's planned route (RouteCache) goes through: its near end within the first few nodes
// and its far end later on, or the rest of the route from the near end more than twice the way via the wall
function ModLeapLink LinkOnRoute(ModMind M, vector Dest, out int Rev)
{
	local int i, j, k, p, iA;
	local ModLeapLink L;
	local NavigationPoint A, B, N, Last;
	local float Remaining, Via;

	for (k = 0; k < Links.Length; k++)
	{
		L = Links[k];
		if (L == None || L.A == None || L.B == None)
			continue;
		for (p = 0; p < 2; p++)
		{
			if (p == 1 && !L.bTwoWay)
				break;
			A = L.A;
			B = L.B;
			if (p == 1)
			{
				A = L.B;
				B = L.A;
			}
			iA = -1;
			for (i = 0; i < 4; i++)
				if (M.B.RouteCache[i] == A)
				{
					iA = i;
					break;
				}
			if (iA < 0)
				continue;
			Rev = p;
			for (j = iA + 2; j < 16; j++)
				if (M.B.RouteCache[j] == B)
					return L;
			Remaining = 0;
			Last = A;
			for (j = iA; j < 15; j++)
			{
				N = NavigationPoint(M.B.RouteCache[j + 1]);
				if (N == None)
					break;
				Remaining += VSize(N.Location - Last.Location);
				Last = N;
			}
			Remaining += VSize(Dest - Last.Location);
			Via = VSize(L.Wall - A.Location) + VSize(B.Location - L.Wall) + VSize(Dest - B.Location);
			if (Remaining > 2 * Via)
				return L;
		}
	}
	return None;
}

// at a planned link's near end: the kick to its far end (the arc checked again now)
function bool LinkKick(ModMind M)
{
	local NavigationPoint A, B;
	local vector V1;
	local float F1, G;
	local ModLeapLink L;

	L = M.Link;
	A = L.A;
	B = L.B;
	if (M.bLinkReverse)
	{
		A = L.B;
		B = L.A;
	}
	if (VSize((M.P.Location - A.Location) * vect(1,1,0)) > 110 || M.P.Physics != PHYS_Walking)
		return false;
	G = Gravity(M.P);
	V1 = Arc(M.P.Location, L.Wall, LeapSpeed(M), G, F1);
	if (!ArcClear(M.P.Location, V1, G, F1, BodyExtent(M.P.CollisionRadius, M.P.CollisionHeight)))
	{
		KickLog(M.P.Name $ " link " $ L.A.Name $ " -> " $ L.B.Name $ ": the arc is blocked now, walking");
		M.Link = None;
		return false;
	}
	if (!StartKick(M, L.Wall, L.Normal, V1, F1, B.Location, false, "link " $ L.A.Name $ " -> " $ L.B.Name))
	{
		M.Link = None;
		return false;
	}
	return true;
}

// pilot LEAPLINKS
function string LinkList()
{
	local int k;
	local string S;

	if (!bLeapLinks || !bHoundWallKick)
		return "off";
	if (!bLinksBuilt)
		return "building, node " $ LinkAt $ " of " $ Nodes.Length;
	S = Links.Length $ " links";
	for (k = 0; k < Links.Length; k++)
		if (Links[k] != None)
			S = S $ " | #" $ (k + 1) $ " " $ Links[k].Describe();
	return S;
}

// a hound bit the player (ModMindRules, through Hit)
function HoundBite(ModMind M, Pawn Player, int Damage)
{
	local vector Facing, Moving;
	local float B;

	HoundBites++;
	HoundDamage += Damage;
	if (M.KickLeapAt > 0 && Level.TimeSeconds - M.KickLeapAt < 1.5)
		M.KickBites++;
	if (HoundFirstBite == 0 && HoundEngagedAt > 0)
		HoundFirstBite = Level.TimeSeconds - HoundEngagedAt;
	PreyFrame(Player, Facing, Moving);
	B = Abs(Bearing(Player, Facing, M.P.Location));
	HoundBiteBearing += B;
	HoundLog(M.P.Name $ " bit the player for " $ Damage $ " from " $ int(B) $ " deg round (" $ M.RoleName(M.Role) $ ")");
}

// the measures: time hounds stood on two or more sides of the player (front, back, left, right, within
// 900), and melee contacts (a hound striking or leaping within reach, whether or not it hurt)
function SidesTick(float DeltaTime)
{
	local PlayerController PC;
	local int i, Sides, Side, N;
	local int Taken[4];
	local float B;
	local vector Facing, Moving;
	local ModMind M;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return;
	PreyFrame(PC.Pawn, Facing, Moving);
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (M.Species != 3/*S_Hound*/ || !M.bTokenGated || M.P.Health <= 0)
			continue;
		if (VSize(M.P.Location - PC.Pawn.Location) > 900)
			continue;
		N++;
		B = Bearing(PC.Pawn, Facing, M.P.Location);
		if (Abs(B) < 45)
			Side = 0;
		else if (Abs(B) > 135)
			Side = 1;
		else if (B > 0)
			Side = 2;
		else
			Side = 3;
		Taken[Side] = 1;
		// a contact: in a strike or leap state within reach of the player, counted once per second
		if (VSize(M.P.Location - PC.Pawn.Location) < 200 && Level.TimeSeconds - M.LastLog > 1.0
			&& (M.B.IsInState('MeleeAttack') || M.B.IsInState('LeapAttack') || M.B.IsInState('Leap')))
		{
			M.LastLog = Level.TimeSeconds;
			HoundContacts++;
		}
	}
	if (N == 0)
		return;
	HoundEngaged = Max(HoundEngaged, N);
	HoundTime += DeltaTime;
	Sides = Taken[0] + Taken[1] + Taken[2] + Taken[3];
	if (Sides >= 2)
		TwoSideTime += DeltaTime;
}

// pilot HOUNDTEST: every hound fighting the player, its role, distance and bearing
function string HoundReport()
{
	local PlayerController PC;
	local int i;
	local string S;
	local vector Facing, Moving;
	local ModMind M;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return "no player";
	PreyFrame(PC.Pawn, Facing, Moving);
	S = "player weapon " $ PC.Pawn.RightWeapon $ ", moves " $ MovesGiven $ " refused " $ MovesRefused;
	for (i = 0; i < Minds.Length; i++)
	{
		M = Minds[i];
		if (M.Species != 3/*S_Hound*/ || M.P.Health <= 0)
			continue;
		S = S $ " | " $ M.P.Name $ " " $ M.RoleName(M.Role) $ " " $ M.TaskName(M.Task) $ " dist " $ int(VSize(M.P.Location - PC.Pawn.Location))
			$ " bearing " $ int(Bearing(PC.Pawn, Facing, M.P.Location)) $ " fear " $ M.Pct(M.Fear) $ " anger " $ M.Pct(M.Anger) $ " legs " $ M.LegsSkipped $ " arrivals " $ M.FlankArrivals $ " commits " $ M.Commits;
		if (M.bMeleeToken)
			S = S $ " M";
		if (M.Kick != 0)
			S = S $ " kick" $ M.Kick;
		S = S $ " kicks " $ M.Kicks $ "/" $ M.KicksPlanted $ "/" $ M.KickLeaps;
		S = S $ " [" $ M.B.GetStateName() $ " lock " $ M.B.bLockState $ " phys " $ M.P.Physics $ " stasis " $ M.P.bStasis $ "/" $ M.B.Squad.bStasis $ " sees " $ M.B.bEnemyIsVisible $ " dest " $ int(VSize(M.B.Destination - M.P.Location)) $ " route " $ M.B.RouteCache[0] $ "]";
	}
	return S;
}

function string HoundStats()
{
	local int i, Legs, Arrivals, Commits, Pins, Kicks, Planted, Leaps, KBites, Used;
	local string S;

	Legs = LegsGone;
	Arrivals = ArrivalsGone;
	Commits = CommitsGone;
	Kicks = KicksGone;
	Planted = KicksPlantedGone;
	Leaps = KickLeapsGone;
	KBites = KickBitesGone;
	Used = LinkUsesGone;
	for (i = 0; i < Minds.Length; i++)
		if (Minds[i].Species == 3/*S_Hound*/)
		{
			Legs += Minds[i].LegsSkipped;
			Arrivals += Minds[i].FlankArrivals;
			Commits += Minds[i].Commits;
			Kicks += Minds[i].Kicks;
			Planted += Minds[i].KicksPlanted;
			Leaps += Minds[i].KickLeaps;
			KBites += Minds[i].KickBites;
			Used += Minds[i].LinkUses;
		}
	for (i = 0; i < Packs.Length; i++)
		Pins += Packs[i].Pins;
	S = "pack " $ bHoundPack $ ", hounds at most " $ HoundEngaged $ ", first bite ";
	if (HoundBites == 0)
		S = S $ "none";
	else
		S = S $ "at " $ (int(HoundFirstBite * 10) / 10.0) $ " s";
	S = S $ ", bites " $ HoundBites $ " for " $ HoundDamage;
	if (HoundBites > 0)
		S = S $ " (mean bearing " $ int(HoundBiteBearing / HoundBites) $ " deg)";
	S = S $ ", contacts " $ HoundContacts $ ", two sides " $ (int(TwoSideTime * 10) / 10.0) $ " of " $ (int(HoundTime * 10) / 10.0) $ " s";
	if (HoundTime > 0)
		S = S $ " (" $ int(100 * TwoSideTime / HoundTime) $ "%)";
	S = S $ ", legs skipped " $ Legs $ ", flank arrivals " $ Arrivals $ ", commits " $ Commits $ ", pins " $ Pins $ ", moves " $ MovesGiven $ " refused " $ MovesRefused;
	return S $ ", wallkick " $ bHoundWallKick $ ", wallkicks " $ Kicks $ " planted " $ Planted $ " leaps " $ Leaps $ " kickbites " $ KBites $ ", links " $ Links.Length $ " used " $ Used;
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
		KeepPosed();
	}
	FlankWait -= DeltaTime;
	if (bLeapLinks && bHoundWallKick && !bLinksBuilt)
		BuildLinks();       // a few nodes a tick, from the first tick of the level
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
	SidesTick(DeltaTime);
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
	bHoundPack=True
	bHoundLog=False
	HoundHold=380
	HoundFlankAngle=120
	HoundSkipLeg=200
	HoundSkipAngle=45
	HoundCommitFront=120
	HoundHoldMax=6
	HoundSkipDodge=0.3
	HoundPinWall=300
	bHoundWallKick=True
	WallKickRange=700
	WallKickChance=0.6
	WallKickPlant=0.15
	WallKickCool=4
	bWallKickLog=False
	bLeapLinks=True
	LeapLinksMax=40
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
