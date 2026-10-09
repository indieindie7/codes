//=============================================================================
// ModNeeds - the creatures' needs and the world's advertisements (AI-MINDS-DESIGN.md section 11).
// Trespasser's lesson, the user's reading of it: a state machine oscillates, a Sims needs system
// with commitment doesn't. Over ModMinds' feelings (what just happened to it) this layer gives
// each creature NEEDS, slow clocks that make it want something when nothing is happening:
//   humans   Fatigue, Curiosity, Safety
//   Seekers  Aggression, Fatigue, Curiosity
//   hounds   Hunger, Fatigue, Curiosity, Safety
//   constructs none (and nothing else is adopted)
// and things in the world ADVERTISE what they satisfy, each with a value per need, a radius and
// an expiry: a corpse (feed), a cover spot (hide, from ModMinds.FindCover), a noise or the
// player's last known position (investigate), a pack mate (regroup), a resting place.
// Every DecideEvery each creature scores the ads in reach (need x value x distance falloff); the
// one it is on keeps a commitment bonus and a minimum run, so it finishes what it started. The
// winner is a WANT, a request ModMinds reads (Want(P)); nothing here moves a pawn. Needs reset
// when the creature has stood at the ad's spot for ArriveTime (a corpse feeds it, a noise is
// looked at, a cover spot rests it). The hound pack reads HuntDrive(P) (hunger: a fed pack stalks
// longer, a starved one commits early) and WantsTell(P) (a holding, hungry hound: the croon).
// One per level (ModMutator spawns it, Phase B). Config [AdventMod.ModNeeds]: bNeeds (off until
// verified), bNeedsLog, the rates and values below. ModPilot NEEDSLIST / "mutate needs list" = List().
//=============================================================================
class ModNeeds extends Info
	config(AdventMod);

// needs (slots in Record.V and Advert.Offer)
const N_Hunger = 0;
const N_Fatigue = 1;
const N_Curiosity = 2;
const N_Safety = 3;
const N_Aggression = 4;
const N_Count = 5;
// what an ad is
const A_Corpse = 1;         // a dead pawn: feeds hounds, interests everyone
const A_Cover = 2;          // a cover spot found for one creature (ModMinds.FindCover): safety, rest
const A_Noise = 3;          // a noise, or the player's last known position: curiosity, aggression
const A_Mate = 4;           // a pack mate (virtual: scored from the pack, never posted)
const A_Rest = 5;           // where a tired creature stands, with no enemy about: rest
// what a creature wants (the request ModMinds reads)
const W_None = 0;
const W_Feed = 1;
const W_Rest = 2;
const W_Investigate = 3;
const W_Regroup = 4;
const ADS_MAX = 32;

var config bool bNeeds;             // off = no needs (ModMinds alone)
var config bool bNeedsLog;          // every want, arrival and ad in AdventNative.log
var config float DecideEvery;       // seconds between choices per creature
var config float CommitBonus;       // the want it is on scores this much more (0..1)
var config float MinRun;            // seconds a want runs before another may replace it
var config float WantMin;           // a score below this is no want
var config float HungerRise;        // per second (hounds; 0.0033 = full in five minutes)
var config float FatigueRise;       // per second while running, charging, fighting
var config float FatigueRest;       // per second while standing
var config float CuriosityRise;     // per second while nothing happens
var config float CuriosityRest;     // per second while something does
var config float SafetyRest;        // per second once the fear and the fire have gone
var config float AggressionRise;    // per second while an enemy is known and it isn't charging (Seekers)
var config float CorpseFeed;        // what a corpse offers a hound's hunger (each feeding takes a third of it)
var config float CorpseLife;        // seconds a corpse ad lasts
var config float NoiseLife;         // seconds a noise ad lasts
var config float RestLife;          // seconds a resting place ad lasts
var config float CoverEvery;        // seconds between cover queries per creature
var config float ArriveReach;       // this close to the ad's spot counts as there (world units)
var config float ArriveTime;        // ... for this long, and the need is met
var config float ForceHunger;       // testing: every hound's hunger held at this (-1 = off)
var config float ForceFatigue;      // testing: likewise fatigue
var config float ForceCuriosity;    // testing: likewise curiosity

struct Advert
{
	var int Id;
	var int Kind;                   // A_*
	var vector At;
	var Actor A;                    // what it is (a corpse, a noise's source, a pawn), if anything
	var Pawn Owner;                 // only this creature scores it (its own cover or resting place)
	var float Offer[5];             // what it satisfies, per need (0..1)
	var float Radius;               // how far it can be wanted from
	var float Posted, Expires;
	var string Tag;                 // for the log
};
var array<Advert> Ads;
var int NextId;
var int AdsPosted, AdsExpired, AdsDropped;

struct NeedRec
{
	var Pawn P;
	var int Species;                // ModMind's S_* (0 human, 1 seeker, 2 veteran, 3 hound)
	var float V[5];                 // the needs, 0..1
	var int Wish;                   // W_*
	var int WishId;                 // the ad it wants (-1 none, -2 a pack mate)
	var Actor WishActor;
	var vector WishAt;
	var float WishSince, WishScore;
	var float NearSince;            // when it came within ArriveReach of its want (0 = not there)
	var int AvoidId;                // the ad it has just been satisfied by (not wanted again for a while)
	var float AvoidUntil;
	var float CoverAt;              // when it last asked ModMinds for cover
	var float Deciding;             // the next choice
	var float Quiet;                // seconds since anything happened to it
	var int Fed, Rested, Looked, Regrouped;
};
var array<NeedRec> Recs;
var ModMinds Minds;
var float ScanWait, FindWait;
var int LastShots;                  // ModMinds.Shots seen (new projectiles make noise)
var float NoiseAt;                  // the last shot noise posted

function PostBeginPlay()
{
	Super.PostBeginPlay();
	if (bNeeds)
		class'ModSettings'.static.Note("needs: on (decide every " $ DecideEvery $ " s, commit " $ CommitBonus $ ", run " $ MinRun $ " s, hunger " $ HungerRise $ "/s, fatigue " $ FatigueRise $ "/s, curiosity " $ CuriosityRise $ "/s)");
}

function NeedLog(string S)
{
	if (bNeedsLog)
		class'ModSettings'.static.Note("needs: " $ S);
}

// ---------------------------------------------------------------------------------
// the needs

static function string NeedName(int N)
{
	switch (N)
	{
		case N_Hunger: return "hunger";
		case N_Fatigue: return "fatigue";
		case N_Curiosity: return "curiosity";
		case N_Safety: return "safety";
		case N_Aggression: return "aggression";
	}
	return "?";
}

static function string WantName(int W)
{
	switch (W)
	{
		case W_None: return "nothing";
		case W_Feed: return "feed";
		case W_Rest: return "rest";
		case W_Investigate: return "investigate";
		case W_Regroup: return "regroup";
	}
	return "?";
}

static function string KindName(int K)
{
	switch (K)
	{
		case A_Corpse: return "corpse";
		case A_Cover: return "cover";
		case A_Noise: return "noise";
		case A_Mate: return "mate";
		case A_Rest: return "rest";
	}
	return "?";
}

// which species has which need (a rate of 0 = it has none)
function float Rate(int Species, int N)
{
	switch (N)
	{
		case N_Hunger:
			if (Species == 3/*S_Hound*/)
				return HungerRise;
			return 0;
		case N_Fatigue:
			return FatigueRise;
		case N_Curiosity:
			return CuriosityRise;
		case N_Safety:
			if (Species == 0/*S_Human*/ || Species == 3/*S_Hound*/)
				return 1;
			return 0;
		case N_Aggression:
			if (Species == 1/*S_Seeker*/ || Species == 2/*S_SeekerVet*/)
				return AggressionRise;
			return 0;
	}
	return 0;
}

static function string F2(float V)
{
	local int C;

	C = int(V * 100 + 0.5);
	if (C >= 100)
		return "1.0";
	if (C < 10)
		return ".0" $ C;
	return "." $ C;
}

function int RecordOf(Pawn P)
{
	local int i;

	if (P == None)
		return -1;
	for (i = 0; i < Recs.Length; i++)
		if (Recs[i].P == P)
			return i;
	return -1;
}

function int AdOf(int Id)
{
	local int i;

	if (Id < 0)
		return -1;
	for (i = 0; i < Ads.Length; i++)
		if (Ads[i].Id == Id)
			return i;
	return -1;
}

// the records follow ModMinds' minds: every adopted creature with a species that has needs
function Adopt()
{
	local int i, j;
	local ModMind M;
	local NeedRec R;

	for (i = Recs.Length - 1; i >= 0; i--)
		if (Recs[i].P == None || Recs[i].P.bDeleteMe || Recs[i].P.Health <= 0 || Minds.MindOf(Recs[i].P) == None)
		{
			NeedLog(Recs[i].P.Name $ " released (fed " $ Recs[i].Fed $ ", rested " $ Recs[i].Rested $ ", looked " $ Recs[i].Looked $ ", regrouped " $ Recs[i].Regrouped $ ")");
			Recs.Remove(i, 1);
		}
	for (i = 0; i < Minds.Minds.Length; i++)
	{
		M = Minds.Minds[i];
		if (M.P == None || M.P.Health <= 0 || M.Species >= 4/*S_Construct, S_Other*/)
			continue;
		if (RecordOf(M.P) >= 0)
			continue;
		R.P = M.P;
		R.Species = M.Species;
		for (j = 0; j < N_Count; j++)
			R.V[j] = 0;
		// it has been about a while already: a little of each slow need, so the first minutes aren't all nothing
		if (Rate(R.Species, N_Hunger) > 0)
			R.V[N_Hunger] = 0.2 + 0.2 * FRand();
		R.V[N_Curiosity] = 0.1 * FRand();
		R.Wish = W_None;
		R.WishId = -1;
		R.AvoidId = -1;
		R.Deciding = Level.TimeSeconds + FRand() * DecideEvery;
		Recs[Recs.Length] = R;
		NeedLog("adopted " $ R.P.Name $ " (" $ M.SpeciesName $ ")");
	}
}

// the clocks: hunger rises on its own; fatigue with running and fighting, down at rest; curiosity when
// nothing happens, down when something does; safety follows the mind's fear and the fire on it, down
// when they have gone; aggression (Seekers) follows the mind's anger and rises while an enemy is known
function Decay(int i, float DeltaTime)
{
	local ModMind M;
	local Pawn P;
	local float Speed, Top, Want;
	local bool bExerting, bStill, bQuiet;
	local int j;

	P = Recs[i].P;
	M = Minds.MindOf(P);
	if (M == None || M.B == None)
		return;
	Speed = VSize(P.Velocity);
	Top = FMax(P.GroundSpeed, 100);
	bExerting = Speed > 0.55 * Top || M.Task == 5/*T_Charge*/ || M.Task == 9/*T_Skip*/ || M.Kick != 0;
	bStill = Speed < 0.2 * Top && M.Task != 5/*T_Charge*/;
	bQuiet = M.B.EnemyInfo.Enemy == None && Level.TimeSeconds - M.LastHit > 5 && Level.TimeSeconds - M.LastNearMiss > 5;
	if (bQuiet)
		Recs[i].Quiet += DeltaTime;
	else
		Recs[i].Quiet = 0;

	if (Rate(Recs[i].Species, N_Hunger) > 0)
		Recs[i].V[N_Hunger] += HungerRise * DeltaTime;
	if (bExerting)
		Recs[i].V[N_Fatigue] += FatigueRise * DeltaTime;
	else if (bStill)
		Recs[i].V[N_Fatigue] -= FatigueRest * DeltaTime;
	if (bQuiet)
		Recs[i].V[N_Curiosity] += CuriosityRise * DeltaTime;
	else
		Recs[i].V[N_Curiosity] -= CuriosityRest * DeltaTime;
	if (Rate(Recs[i].Species, N_Safety) > 0)
	{
		Want = FMax(M.Fear, 0.7 * M.Pressure);
		if (Want > Recs[i].V[N_Safety])
			Recs[i].V[N_Safety] += (Want - Recs[i].V[N_Safety]) * 2 * DeltaTime;
		else if (M.Task == 1/*T_Pinned*/ || M.Task == 2/*T_Cover*/)
			Recs[i].V[N_Safety] -= 2 * SafetyRest * DeltaTime;      // in cover: the need is being met
		else
			Recs[i].V[N_Safety] -= SafetyRest * DeltaTime;
	}
	if (Rate(Recs[i].Species, N_Aggression) > 0)
	{
		if (M.Anger > Recs[i].V[N_Aggression])
			Recs[i].V[N_Aggression] += (M.Anger - Recs[i].V[N_Aggression]) * DeltaTime;
		if (M.Task == 5/*T_Charge*/)
			Recs[i].V[N_Aggression] -= 0.3 * DeltaTime;             // charging vents it
		else if (M.B.EnemyInfo.Enemy != None)
			Recs[i].V[N_Aggression] += AggressionRise * DeltaTime;
	}
	// testing: needs held at a value
	if (ForceHunger >= 0 && Rate(Recs[i].Species, N_Hunger) > 0)
		Recs[i].V[N_Hunger] = ForceHunger;
	if (ForceFatigue >= 0)
		Recs[i].V[N_Fatigue] = ForceFatigue;
	if (ForceCuriosity >= 0)
		Recs[i].V[N_Curiosity] = ForceCuriosity;
	for (j = 0; j < N_Count; j++)
		Recs[i].V[j] = FClamp(Recs[i].V[j], 0, 1);
}

// ---------------------------------------------------------------------------------
// the advertisements

function int Post(int Kind, vector At, Actor A, Pawn Owner, float Life, float Radius, string Tag)
{
	local Advert Ad;
	local int i, Oldest;

	if (Ads.Length >= ADS_MAX)
	{
		// full: the one expiring soonest goes
		Oldest = 0;
		for (i = 1; i < Ads.Length; i++)
			if (Ads[i].Expires < Ads[Oldest].Expires)
				Oldest = i;
		AdsDropped++;
		Ads.Remove(Oldest, 1);
	}
	Ad.Id = NextId++;
	Ad.Kind = Kind;
	Ad.At = At;
	Ad.A = A;
	Ad.Owner = Owner;
	Ad.Radius = Radius;
	Ad.Posted = Level.TimeSeconds;
	Ad.Expires = Level.TimeSeconds + Life;
	Ad.Tag = Tag;
	for (i = 0; i < N_Count; i++)
		Ad.Offer[i] = 0;
	Ads[Ads.Length] = Ad;
	AdsPosted++;
	return Ads.Length - 1;
}

// a dead pawn: hounds feed on it, everyone finds it interesting (ModMindRules.ScoreKill, Phase B;
// until then the corpse scan below finds the bodies)
function PostCorpse(Pawn Dead, vector At)
{
	local int i;

	for (i = 0; i < Ads.Length; i++)
		if (Ads[i].Kind == A_Corpse && (Ads[i].A == Dead || VSize(Ads[i].At - At) < 100))
			return;
	i = Post(A_Corpse, At, Dead, None, CorpseLife, 1600, "corpse of " $ Dead.Name);
	Ads[i].Offer[N_Hunger] = CorpseFeed;
	Ads[i].Offer[N_Curiosity] = 0.25;
	NeedLog("ad: corpse of " $ Dead.Name $ " at " $ int(At.X) $ " " $ int(At.Y) $ " " $ int(At.Z) $ " (feed " $ CorpseFeed $ ")");
}

// a noise (Loud 0..1), or the player's last known position: worth a look, and a Seeker's aggression
// (a noise from the same source within 200 is the same noise, refreshed)
function PostNoise(vector At, float Loud, Actor Source, string Tag)
{
	local int i;

	for (i = 0; i < Ads.Length; i++)
		if (Ads[i].Kind == A_Noise && Ads[i].A == Source && Source != None && VSize(Ads[i].At - At) < 200)
		{
			Ads[i].At = At;
			Ads[i].Expires = Level.TimeSeconds + NoiseLife;
			return;
		}
	i = Post(A_Noise, At, Source, None, NoiseLife, 1000 + 1000 * Loud, Tag);
	Ads[i].Offer[N_Curiosity] = 0.3 + 0.5 * Loud;
	Ads[i].Offer[N_Aggression] = 0.4 * Loud;
	NeedLog("ad: noise " $ Tag $ " at " $ int(At.X) $ " " $ int(At.Y) $ " " $ int(At.Z) $ " (loud " $ F2(Loud) $ ")");
}

// a cover spot for one creature, from ModMinds' own finder (so it is claimed there too)
function PostCover(int i, vector Spot)
{
	local int j;
	local Pawn P;

	P = Recs[i].P;
	for (j = Ads.Length - 1; j >= 0; j--)
		if (Ads[j].Kind == A_Cover && Ads[j].Owner == P)
		{
			if (Recs[i].WishId == Ads[j].Id)
				Recs[i].WishId = -1;        // replaced below: Choose finds the new one
			Ads.Remove(j, 1);
		}
	j = Post(A_Cover, Spot, None, P, CoverEvery + 1.0, 1500, "cover for " $ P.Name);
	Ads[j].Offer[N_Safety] = 0.7;
	Ads[j].Offer[N_Fatigue] = 0.3;
	if (Recs[i].WishId == -1 && Recs[i].Wish == W_Rest)
		Recs[i].WishId = Ads[j].Id;
}

// where a tired creature stands with no enemy about: a place to rest
function PostRest(int i)
{
	local int j;
	local Pawn P;

	P = Recs[i].P;
	for (j = 0; j < Ads.Length; j++)
		if (Ads[j].Kind == A_Rest && Ads[j].Owner == P)
			return;
	j = Post(A_Rest, P.Location, None, P, RestLife, 400, "rest for " $ P.Name);
	Ads[j].Offer[N_Fatigue] = 0.6;
}

function Expire()
{
	local int i;

	for (i = Ads.Length - 1; i >= 0; i--)
		if (Level.TimeSeconds > Ads[i].Expires || (Ads[i].Owner != None && (Ads[i].Owner.bDeleteMe || Ads[i].Owner.Health <= 0)))
		{
			AdsExpired++;
			Ads.Remove(i, 1);
		}
}

// the world's own ads: bodies on the ground (until ScoreKill posts them), the player's last known
// position (for every creature that knows where the player is, as a noise it can go and look at),
// shots fired (a noise where the shooter stands)
function Scan()
{
	local Pawn D;
	local PlayerController PC;
	local int i;
	local bool bKnown;

	foreach DynamicActors(class'Pawn', D)
	{
		if (D.Health > 0 || D.bDeleteMe || D.bHidden || PlayerController(D.Controller) != None || D.IsA('Vehicle'))
			continue;
		PostCorpse(D, D.Location);
	}
	PC = Level.GetLocalPlayerController();
	if (PC != None && PC.Pawn != None)
	{
		for (i = 0; i < Minds.Minds.Length && !bKnown; i++)
			bKnown = Minds.Minds[i].B != None && Minds.Minds[i].B.EnemyInfo.Enemy == PC.Pawn;
		if (bKnown)
			PostNoise(PC.Pawn.Location, 0.5, PC.Pawn, "the player, last known");
	}
	if (Minds.Shots.Length > LastShots && Level.TimeSeconds - NoiseAt > 1.0)
	{
		i = Minds.Shots.Length - 1;
		if (Minds.Shots[i].Pr != None && Minds.Shots[i].Pr.Instigator != None)
		{
			NoiseAt = Level.TimeSeconds;
			PostNoise(Minds.Shots[i].Pr.Instigator.Location, 0.8, Minds.Shots[i].Pr.Instigator, "a shot by " $ Minds.Shots[i].Pr.Instigator.Name);
		}
	}
	LastShots = Minds.Shots.Length;
}

// the ads only one creature can use, found for it: cover when it wants safety or rest and has an
// enemy; a resting place when it is tired and has none
function FindOwn(int i)
{
	local ModMind M;
	local Pawn Enemy;
	local vector Spot;

	M = Minds.MindOf(Recs[i].P);
	if (M == None || M.B == None || Level.TimeSeconds - Recs[i].CoverAt < CoverEvery)
		return;
	Recs[i].CoverAt = Level.TimeSeconds;
	Enemy = M.B.EnemyInfo.Enemy;
	if (Enemy != None)
	{
		if (Recs[i].Species != 3/*S_Hound*/ && (Recs[i].V[N_Safety] > 0.35 || Recs[i].V[N_Fatigue] > 0.5) && Minds.FindCover(M, Enemy, Spot))
			PostCover(i, Spot);
	}
	else if (Recs[i].V[N_Fatigue] > 0.4)
		PostRest(i);
}

// ---------------------------------------------------------------------------------
// the choice

function int WantOfKind(int Kind)
{
	switch (Kind)
	{
		case A_Corpse: return W_Feed;
		case A_Cover: return W_Rest;
		case A_Rest: return W_Rest;
		case A_Noise: return W_Investigate;
		case A_Mate: return W_Regroup;
	}
	return W_None;
}

// how much ad j satisfies creature i from where it stands (0 = out of reach or nothing it needs)
function float ScoreAd(int i, int j)
{
	local float D, Fall, S;
	local int n;

	if (Ads[j].Owner != None && Ads[j].Owner != Recs[i].P)
		return 0;
	if (Ads[j].Id == Recs[i].AvoidId && Level.TimeSeconds < Recs[i].AvoidUntil)
		return 0;
	D = VSize(Ads[j].At - Recs[i].P.Location);
	if (D > Ads[j].Radius)
		return 0;
	Fall = 1 - 0.5 * D / Ads[j].Radius;
	for (n = 0; n < N_Count; n++)
		if (Rate(Recs[i].Species, n) > 0)
			S += Recs[i].V[n] * Ads[j].Offer[n];
	return S * Fall;
}

// the pack mate a hound would regroup with: the nearest living mate of its squad further than 300
// away (an ad that is never posted: the pack would fill the list)
function Pawn Mate(int i, out float Score)
{
	local ModMind M, O;
	local int k;
	local float D, Best;
	local Pawn Pick;

	Score = 0;
	if (Recs[i].Species != 3/*S_Hound*/ || Recs[i].V[N_Safety] < 0.05)
		return None;
	M = Minds.MindOf(Recs[i].P);
	if (M == None || M.B == None || M.B.Squad == None)
		return None;
	Best = 2000;
	for (k = 0; k < Minds.Minds.Length; k++)
	{
		O = Minds.Minds[k];
		if (O == M || O.P == None || O.P.Health <= 0 || O.B == None || O.B.Squad != M.B.Squad)
			continue;
		D = VSize(O.P.Location - M.P.Location);
		if (D > 300 && D < Best)
		{
			Best = D;
			Pick = O.P;
		}
	}
	if (Pick != None)
		Score = Recs[i].V[N_Safety] * 0.6 * (1 - 0.5 * Best / 2000);
	return Pick;
}

function string Describe(int i)
{
	local string S;
	local int n;

	S = "" $ Recs[i].P.Name;
	for (n = 0; n < N_Count; n++)
		if (Rate(Recs[i].Species, n) > 0)
			S = S $ " " $ NeedName(n) $ " " $ F2(Recs[i].V[n]);
	S = S $ " -> " $ WantName(Recs[i].Wish);
	if (Recs[i].Wish != W_None)
	{
		S = S $ " at " $ WishText(i) $ " (score " $ F2(Recs[i].WishScore) $ ", " $ int((Level.TimeSeconds - Recs[i].WishSince) * 10) / 10.0 $ " s)";
	}
	return S;
}

function string WishText(int i)
{
	local int j;

	if (Recs[i].WishId == -2 && Recs[i].WishActor != None)
		return "mate " $ Recs[i].WishActor.Name;
	j = AdOf(Recs[i].WishId);
	if (j >= 0)
		return Ads[j].Tag $ " " $ int(VSize(Ads[j].At - Recs[i].P.Location)) $ " away";
	return "(gone)";
}

// every DecideEvery: the best ad in reach wins, the current one with its commitment bonus, and not
// before its minimum run (unless it has gone)
function Choose(int i)
{
	local int j, Best, Cur;
	local float S, BestS, MateS;
	local Pawn MateP;
	local bool bKeep;

	Cur = AdOf(Recs[i].WishId);
	if (Recs[i].WishId == -2 && (Recs[i].WishActor == None || Recs[i].WishActor.bDeleteMe || Pawn(Recs[i].WishActor).Health <= 0))
		Recs[i].WishId = -1;
	bKeep = Recs[i].Wish != W_None && (Cur >= 0 || Recs[i].WishId == -2) && Level.TimeSeconds - Recs[i].WishSince < MinRun;
	Best = -1;
	BestS = 0;
	for (j = 0; j < Ads.Length; j++)
	{
		S = ScoreAd(i, j);
		if (S <= 0)
			continue;
		if (j == Cur)
			S += CommitBonus;
		if (S > BestS)
		{
			BestS = S;
			Best = j;
		}
	}
	MateP = Mate(i, MateS);
	if (MateP != None && Recs[i].WishId == -2)
		MateS += CommitBonus;
	if (MateP != None && MateS > BestS)
	{
		BestS = MateS;
		Best = -2;
	}
	if (BestS < WantMin)
	{
		Best = -1;
		BestS = 0;
	}
	// the current want's spot moves with its actor (a corpse that slid, a mate that ran)
	if (Cur >= 0)
	{
		if (Ads[Cur].A != None && Ads[Cur].Kind == A_Corpse)
			Ads[Cur].At = Ads[Cur].A.Location;
		Recs[i].WishAt = Ads[Cur].At;
		Recs[i].WishScore = BestS;
	}
	else if (Recs[i].WishId == -2 && Recs[i].WishActor != None)
		Recs[i].WishAt = Recs[i].WishActor.Location;
	if (bKeep)
	{
		if ((Best == -2 && Recs[i].WishId == -2) || (Best >= 0 && Ads[Best].Id == Recs[i].WishId))
			Recs[i].WishScore = BestS;
		return;                     // committed
	}
	if (Best == -1)
	{
		if (Recs[i].Wish != W_None)
		{
			NeedLog(Recs[i].P.Name $ " wants nothing now (was " $ WantName(Recs[i].Wish) $ ")");
			Recs[i].Wish = W_None;
			Recs[i].WishId = -1;
			Recs[i].WishActor = None;
			Recs[i].NearSince = 0;
		}
		return;
	}
	if (Best == -2)
	{
		if (Recs[i].WishId == -2 && Recs[i].WishActor == MateP)
		{
			Recs[i].WishScore = BestS;
			return;
		}
		Recs[i].Wish = W_Regroup;
		Recs[i].WishId = -2;
		Recs[i].WishActor = MateP;
		Recs[i].WishAt = MateP.Location;
	}
	else
	{
		if (Ads[Best].Id == Recs[i].WishId)
		{
			Recs[i].WishScore = BestS;
			return;
		}
		Recs[i].Wish = WantOfKind(Ads[Best].Kind);
		Recs[i].WishId = Ads[Best].Id;
		Recs[i].WishActor = Ads[Best].A;
		Recs[i].WishAt = Ads[Best].At;
	}
	Recs[i].WishSince = Level.TimeSeconds;
	Recs[i].WishScore = BestS;
	Recs[i].NearSince = 0;
	NeedLog(Describe(i));
}

// at the ad's spot for ArriveTime: the need is met. A corpse is eaten a bite at a time (a third of
// its offer per feeding) and goes when there is nothing left; a noise looked at is done with; cover
// and a resting place stay (the clocks fall there anyway); a mate reached is regrouped with.
function Arrive(int i, float DeltaTime)
{
	local int j, n;
	local float D;
	local string S;

	if (Recs[i].Wish == W_None)
		return;
	D = VSize((Recs[i].WishAt - Recs[i].P.Location) * vect(1,1,0));
	if (D > ArriveReach)
	{
		Recs[i].NearSince = 0;
		return;
	}
	if (Recs[i].NearSince == 0)
	{
		Recs[i].NearSince = Level.TimeSeconds;
		return;
	}
	if (Level.TimeSeconds - Recs[i].NearSince < ArriveTime)
		return;
	j = AdOf(Recs[i].WishId);
	S = Recs[i].P.Name $ " " $ WantName(Recs[i].Wish) $ " done at " $ WishText(i) $ ":";
	if (Recs[i].WishId == -2)
	{
		Recs[i].V[N_Safety] = FMax(0, Recs[i].V[N_Safety] - 0.4);
		Recs[i].Regrouped++;
	}
	else if (j >= 0)
	{
		for (n = 0; n < N_Count; n++)
			Recs[i].V[n] = FMax(0, Recs[i].V[n] - Ads[j].Offer[n]);
		switch (Ads[j].Kind)
		{
			case A_Corpse:
				Recs[i].Fed++;
				Ads[j].Offer[N_Hunger] -= CorpseFeed / 3;
				if (Ads[j].Offer[N_Hunger] < 0.05)
				{
					S = S $ " nothing left of it;";
					Ads[j].Expires = 0;
				}
				break;
			case A_Noise:
				Recs[i].Looked++;
				Ads[j].Expires = 0;
				break;
			case A_Cover:
			case A_Rest:
				Recs[i].Rested++;
				break;
		}
		Recs[i].AvoidId = Ads[j].Id;
		Recs[i].AvoidUntil = Level.TimeSeconds + 15;
	}
	for (n = 0; n < N_Count; n++)
		if (Rate(Recs[i].Species, n) > 0)
			S = S $ " " $ NeedName(n) $ " " $ F2(Recs[i].V[n]);
	NeedLog(S);
	Recs[i].Wish = W_None;
	Recs[i].WishId = -1;
	Recs[i].WishActor = None;
	Recs[i].NearSince = 0;
	Recs[i].Deciding = Level.TimeSeconds + DecideEvery;
}

// ---------------------------------------------------------------------------------
// what ModMinds and the pack read

// the creature's request: W_None, or W_Feed / W_Rest / W_Investigate / W_Regroup with where and what
function int Want(Pawn P, out vector At, out Actor Target)
{
	local int i;

	i = RecordOf(P);
	if (i < 0)
		return W_None;
	At = Recs[i].WishAt;
	Target = Recs[i].WishActor;
	return Recs[i].Wish;
}

// seconds it has been on its want (ModMinds: a request younger than MinRun is one it is committed to)
function float WantAge(Pawn P)
{
	local int i;

	i = RecordOf(P);
	if (i < 0 || Recs[i].Wish == W_None)
		return 0;
	return Level.TimeSeconds - Recs[i].WishSince;
}

function float NeedOf(Pawn P, int N)
{
	local int i;

	i = RecordOf(P);
	if (i < 0 || N < 0 || N >= N_Count)
		return 0;
	return Recs[i].V[N];
}

// the pack's hunting drive from hunger: 0.2 (just fed: it stalks, holds long, commits only from
// the side) to 1 (starved: it commits early, from in front). No record (needs off, not a hound):
// 0.6, which leaves the pack's cone and hold as they were.
function float HuntDrive(Pawn P)
{
	local int i;

	i = RecordOf(P);
	if (i < 0 || Recs[i].Species != 3/*S_Hound*/)
		return 0.6;
	return 0.2 + 0.8 * Recs[i].V[N_Hunger];
}

// the stalk tell: a hound holding the front (or alone) with its hunger up: the croon before the leap
function bool WantsTell(Pawn P)
{
	local int i;
	local ModMind M;

	i = RecordOf(P);
	if (i < 0 || Recs[i].Species != 3/*S_Hound*/ || Recs[i].V[N_Hunger] < 0.6)
		return false;
	M = Minds.MindOf(P);
	return M != None && (M.Role == 1/*R_Holder*/ || M.Role == 4/*R_Skirmisher*/) && M.Task != 5/*T_Charge*/;
}

// ModMinds (Phase B): the want was acted on and reached, or given up (a fight broke out)
function Satisfied(Pawn P)
{
	local int i;

	i = RecordOf(P);
	if (i >= 0 && Recs[i].Wish != W_None && Recs[i].NearSince == 0)
		Recs[i].NearSince = Level.TimeSeconds - ArriveTime;
}

function GiveUp(Pawn P, string Why)
{
	local int i;

	i = RecordOf(P);
	if (i < 0 || Recs[i].Wish == W_None)
		return;
	NeedLog(Recs[i].P.Name $ " gives up " $ WantName(Recs[i].Wish) $ " (" $ Why $ ")");
	Recs[i].AvoidId = Recs[i].WishId;
	Recs[i].AvoidUntil = Level.TimeSeconds + 6;
	Recs[i].Wish = W_None;
	Recs[i].WishId = -1;
	Recs[i].WishActor = None;
	Recs[i].NearSince = 0;
}

// ---------------------------------------------------------------------------------

function Tick(float DeltaTime)
{
	local int i;
	local ModMinds Found;

	if (!bNeeds)
		return;
	if (Minds == None || Minds.bDeleteMe)
	{
		Minds = None;
		foreach DynamicActors(class'ModMinds', Found)
		{
			Minds = Found;
			break;
		}
		if (Minds == None)
			return;
	}
	ScanWait -= DeltaTime;
	if (ScanWait <= 0)
	{
		ScanWait = 1.0;
		Adopt();
		Expire();
		Scan();
	}
	for (i = 0; i < Recs.Length; i++)
	{
		if (Recs[i].P == None || Recs[i].P.Health <= 0)
			continue;
		Decay(i, DeltaTime);
		if (Level.TimeSeconds >= Recs[i].Deciding)
		{
			Recs[i].Deciding = Level.TimeSeconds + DecideEvery;
			FindOwn(i);
			Choose(i);
		}
		Arrive(i, DeltaTime);
	}
}

// ModPilot NEEDSLIST and "mutate needs list": every creature's needs and want, then the ads
function string List()
{
	local int i;
	local string S;

	S = Recs.Length $ " creatures, " $ Ads.Length $ " ads (" $ AdsPosted $ " posted, " $ AdsExpired $ " expired, " $ AdsDropped $ " dropped for room)";
	for (i = 0; i < Recs.Length; i++)
		class'ModSettings'.static.Note("needslist: " $ Describe(i) $ " fed " $ Recs[i].Fed $ " rested " $ Recs[i].Rested $ " looked " $ Recs[i].Looked $ " regrouped " $ Recs[i].Regrouped $ " quiet " $ int(Recs[i].Quiet) $ " s");
	for (i = 0; i < Ads.Length; i++)
		class'ModSettings'.static.Note("needslist: ad " $ Ads[i].Id $ " " $ KindName(Ads[i].Kind) $ " " $ Ads[i].Tag $ " at " $ int(Ads[i].At.X) $ " " $ int(Ads[i].At.Y) $ " " $ int(Ads[i].At.Z)
			$ " offers hunger " $ F2(Ads[i].Offer[N_Hunger]) $ " fatigue " $ F2(Ads[i].Offer[N_Fatigue]) $ " curiosity " $ F2(Ads[i].Offer[N_Curiosity]) $ " safety " $ F2(Ads[i].Offer[N_Safety]) $ " aggression " $ F2(Ads[i].Offer[N_Aggression])
			$ " radius " $ int(Ads[i].Radius) $ " expires in " $ int(Ads[i].Expires - Level.TimeSeconds) $ " s");
	return S;
}

// console "mutate needs <cmd>" (ModMutator.Mutate, Phase B): list | on | off | log on|off |
// hunger V | fatigue V | curiosity V (-1 = free) | noise (a noise at the player, loud)
function string Command(string Cmd)
{
	local string Arg;
	local int i;
	local PlayerController PC;

	i = InStr(Cmd, " ");
	if (i >= 0)
	{
		Arg = Mid(Cmd, i + 1);
		Cmd = Left(Cmd, i);
	}
	Cmd = Caps(Cmd);
	if (Cmd == "LIST")
		return List();
	if (Cmd == "ON")
	{
		bNeeds = true;
		return "on";
	}
	if (Cmd == "OFF")
	{
		bNeeds = false;
		return "off";
	}
	if (Cmd == "LOG")
	{
		bNeedsLog = Caps(Arg) == "ON";
		return "log " $ bNeedsLog;
	}
	if (Cmd == "HUNGER")
	{
		ForceHunger = float(Arg);
		return "hunger held at " $ ForceHunger;
	}
	if (Cmd == "FATIGUE")
	{
		ForceFatigue = float(Arg);
		return "fatigue held at " $ ForceFatigue;
	}
	if (Cmd == "CURIOSITY")
	{
		ForceCuriosity = float(Arg);
		return "curiosity held at " $ ForceCuriosity;
	}
	if (Cmd == "NOISE")
	{
		PC = Level.GetLocalPlayerController();
		if (PC == None || PC.Pawn == None)
			return "no player";
		PostNoise(PC.Pawn.Location, 1.0, None, "a noise made by the pilot");
		return "noise at the player";
	}
	return "needs: list | on | off | log on|off | hunger V | fatigue V | curiosity V | noise";
}

defaultproperties
{
	bNeeds=False
	bNeedsLog=False
	DecideEvery=0.5
	CommitBonus=0.25
	MinRun=3
	WantMin=0.12
	HungerRise=0.0033
	FatigueRise=0.025
	FatigueRest=0.02
	CuriosityRise=0.0167
	CuriosityRest=0.05
	SafetyRest=0.03
	AggressionRise=0.02
	CorpseFeed=0.6
	CorpseLife=90
	NoiseLife=8
	RestLife=10
	CoverEvery=3
	ArriveReach=160
	ArriveTime=1.5
	ForceHunger=-1
	ForceFatigue=-1
	ForceCuriosity=-1
}
