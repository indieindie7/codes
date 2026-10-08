//=============================================================================
// ModShadowController - picks the lights that most strongly light one character
// and gives each its own ModLightShadow (ported from U2SoftShadows'
// SSShadowController). A shadow stays on its light for as long as that light is
// in the top set, and the set is only re-picked once the character has moved,
// so a character standing still keeps perfectly still shadows. Moving between
// lamps, shadows fade from one light to the next.
//
// Each shadow's darkness follows its light's share of all the light reaching the
// character (lamps in reach plus the zone's ambient light), so the baked
// lighting isn't painted over.
//
// Tunable in System\AdventMod.ini under [AdventMod.ModShadowController].
//=============================================================================
class ModShadowController extends Actor
	config(AdventMod);

var config bool bPlayerOnly;      // only the player's own character (others within NearDistance/MidDistance get shadows too when off)
var config int MaxShadows;        // light shadows per character
var config int PlayerMaxShadows;  // light shadows for the player's own character
var config float MaxLightDistance;
var config float UpdateFrequency;
var config float ShadowStrength;
var config float FadeRate;
var config int GradientLength;    // longest the feet-to-head fade may reach, in world units
var config float GradientScale;   // fade length as a multiple of the shadow's length
var config float MaxSteepness;    // overhead lamps are tilted to at most this steep (degrees)
var config float MinSteepness;    // low lamps are raised to at least this steep (degrees)
var config float FrustumDistance; // light distance the shadow picture is fitted to, at most
var config float SunStrength;     // darkness of a bright sun's shadow, 0-1
var config float SunFullBrightness; // sun brightness that casts the darkest shadow
var config float MinStrength;     // darkness of the faintest lamp shadow (dim or far lamp), 0-1
var config float FullIntensity;   // lamp brightness x falloff that casts the darkest shadow
var config float CullDistance;    // characters farther than this from the player cast no shadows
var config float UnseenTime;      // nor do characters off screen for this long (seconds)
var config float SunClearance;    // the sun casts when nothing is this close overhead toward it
var config float NearDistance;    // within this: every shadow
var config float MidDistance;     // within this: one shadow; beyond: none
var config float RepickDistance;  // the light set is re-picked only after moving this far
var config bool bRespectBaked;    // darkness follows the light's share of all light here
var config float AmbientWeight;   // how much the zone's ambient brightness counts against the lamps
var config float MinShare;        // darkness kept even when a light is a small share of the total
var config float HoldBonus;        // a light a shadow already casts from counts this much stronger when re-picking (fewer swaps while walking)
var config bool bSunOnlyOutdoors; // under open sky only the sun casts (lamps only indoors)
var config bool bDebugStockDir;   // testing: every shadow's light sits behind the camera (shadow in plain view)
var config bool bDebugOwnShadow;  // testing: register the first shadow as the pawn's own Shadow

var int Allowed;                  // light shadows allowed at the current distance
var ModShadowManager Manager;
var bool bCulled;
var array<ModLightShadow> Shadows;
var array<Actor> Chosen;
var array<float> ChosenPriority;

var bool bPicked;
var vector PickLoc;
var int PickAllowed;
var int PickVersion;
var float LastTotalLight;
var float LastAmbient;
var bool bOutdoors;               // the sun reached this character at the last pick
var bool bMostlyOutdoors;         // most of five points see the sun (the contact-hardening switch)
var byte StockDark;               // the darkness of the game's own shadow, put back when this controller goes
var float OutOfPool;              // seconds this character has been outside the manager's shadow pool

function bool IsPlayer()
{
	return Manager != None && Manager.Viewer != None && Pawn(Owner) != None && Pawn(Owner).Controller == Manager.Viewer;
}

function int OwnMax()
{
	if (IsPlayer())
		return Max(PlayerMaxShadows, MaxShadows);
	return MaxShadows;
}

function Initialize()
{
	local ModLightShadow S;
	local int i;

	if (Owner == None || Manager == None)
	{
		Destroy();
		return;
	}
	for (i = 0; i < OwnMax(); i++)
	{
		S = Spawn(class'ModLightShadow', None, '', Owner.Location);
		if (S == None)
			continue;
		S.Setup(Owner);
		S.ShadowStrength = ShadowStrength;
		S.FadeRate = FadeRate;
		S.MaxGradient = GradientLength;
		S.GradientScale = GradientScale;
		S.MaxSteepness = MaxSteepness;
		S.MinSteepness = MinSteepness;
		S.MaxLightDistance = FrustumDistance;
		S.MinStrength = MinStrength;
		S.SunStrength = SunStrength;
		S.SunFullBrightness = SunFullBrightness;
		S.FullIntensity = FullIntensity;
		Shadows[Shadows.Length] = S;
	}
	SelectLights();
	// start at a random point in the cycle so controllers don't all update in the same frame
	SetTimer(UpdateFrequency * (0.2 + 0.8 * FRand()), false);
}

event Tick(float DeltaTime)
{
	local int i;

	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None)
			Shadows[i].Step(DeltaTime);
}

event Timer()
{
	if (Owner == None || Owner.bDeleteMe)
	{
		Destroy();
		return;
	}
	if (TimerRate != UpdateFrequency)
		SetTimer(UpdateFrequency, true);
	SelectLights();
}

function vector ViewLocation()
{
	if (Manager.Viewer.Pawn != None)
		return Manager.Viewer.Pawn.Location;
	return Manager.Viewer.Location;
}

// far away or out of sight for a while: no shadows, no light searches. The
// player's own character always keeps them
function bool ShouldCull()
{
	if (Manager.bSuspended)
		return true;
	if (Manager.Viewer == None || IsPlayer())
		return false;
	if (VSize(Owner.Location - ViewLocation()) > CullDistance)
		return true;
	// (LastRenderTime runs on its own clock here: compare with the newest frame's)
	return Manager.LastFrameTime - Owner.LastRenderTime > UnseenTime;
}

function int TierAllowed()
{
	local float Dist;

	if (Manager.Viewer == None || IsPlayer())
		return OwnMax();
	Dist = VSize(Owner.Location - ViewLocation());
	if (Dist <= NearDistance)
		return OwnMax();
	if (Dist <= MidDistance)
		return Min(OwnMax(), 1);
	return 0;
}

// a light worth considering at all: switched on, bright, and lighting characters
static function bool CastsLight(Actor A)
{
	return A.LightType != LT_None && A.LightBrightness > 0 && A.LightRadius > 0 && !A.bUnlit
		&& A.AffectType != AT_AffectWorld;
}

function float LightScore(Actor A)
{
	local float Dist, Reach;

	Dist = VSize(A.Location - Owner.Location);
	if (Dist > MaxLightDistance || Dist < Owner.CollisionRadius)
		return 0;
	Reach = 25.0 * (A.LightRadius + 1);
	if (Dist >= Reach)
		return 0;
	return A.LightBrightness * (1.0 - Square(Dist / Reach));
}

// can the light see the character's chest or knees?
function bool LightReaches(vector LightLoc)
{
	local vector Chest, Knees;

	Chest = Owner.Location;
	Chest.Z += Owner.CollisionHeight * 0.4;
	Knees = Owner.Location;
	Knees.Z -= Owner.CollisionHeight * 0.6;
	return FastTrace(Chest, LightLoc) || FastTrace(Knees, LightLoc);
}

// sunlight is directional: test the open sky along the sun's direction
function bool SunVisible()
{
	local vector ToSun, Head;

	if (Manager.SunLightActor == None)
		return false;
	ToSun = -vector(Manager.SunLightActor.Rotation) * SunClearance;
	Head = Owner.Location;
	Head.Z += Owner.CollisionHeight * 0.8;
	return FastTrace(Owner.Location + ToSun, Owner.Location) || FastTrace(Head + ToSun, Head);
}

// outdoors for the contact-hardening switch: most of five points round the character see the sun
// (one ray flickered under beams and window frames: 18 switches in 45 s on level03sectionb)
function bool MostlyOutdoors()
{
	local vector ToSun, Side, P;
	local int i, n;

	if (Manager.SunLightActor == None)
		return false;
	ToSun = -vector(Manager.SunLightActor.Rotation) * SunClearance;
	Side = Normal(ToSun Cross vect(0,0,1)) * 80;
	for (i = 0; i < 5; i++)
	{
		P = Owner.Location;
		P.Z += Owner.CollisionHeight * 0.8 * (i % 2);   // (% is a float operator in UnrealScript)
		if (i >= 2)
			P += Side * (float(i) - 3.0) + vect(0,0,1) * Owner.CollisionHeight * 0.4;
		if (FastTrace(P + ToSun, P))
			n++;
	}
	return n >= 3;
}

function float AmbientLight()
{
	if (Owner.Region.Zone == None)
		return 0;
	return Owner.Region.Zone.AmbientBrightness * AmbientWeight;
}

function Offer(Actor L, float Priority, int Want)
{
	local int i, k;

	for (i = 0; i < Chosen.Length; i++)
		if (Chosen[i] == L)
			return;
	for (k = 0; k < Chosen.Length; k++)
		if (Priority > ChosenPriority[k])
			break;
	if (k >= Want)
		return;
	Chosen.Insert(k, 1);
	ChosenPriority.Insert(k, 1);
	Chosen[k] = L;
	ChosenPriority[k] = Priority;
	if (Chosen.Length > Want)
	{
		Chosen.Remove(Want, Chosen.Length - Want);
		ChosenPriority.Remove(Want, ChosenPriority.Length - Want);
	}
}

// a light one of this character's shadows already casts from (or is fading to)
function bool IsHeld(Actor L)
{
	local int i;

	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None && Shadows[i].TargetLight() == L)
			return true;
	return false;
}

// the current set can stay: the character hasn't moved far, its distance tier is
// the same and every light it casts from still shines
function bool CanHold()
{
	local int i;
	local Actor L;

	if (!bPicked || Allowed != PickAllowed || VSize(Owner.Location - PickLoc) >= RepickDistance)
		return false;
	Manager.RefreshDynamicLights();
	if (Manager.LightsVersion != PickVersion)
		return false;
	for (i = 0; i < Shadows.Length; i++)
	{
		if (Shadows[i] == None)
			continue;
		L = Shadows[i].TargetLight();
		if (L != None && (L.bDeleteMe || !CastsLight(L)))
			return false;
	}
	return true;
}

function SelectLights()
{
	local int i, j, Want;
	local Actor A;
	local float Score, Total, Share;
	local array<int> Held;
	local bool bFound;

	if (Owner == None || Manager == None)
		return;
	SetLocation(Owner.Location);

	if (ShouldCull())
	{
		if (!bCulled)
		{
			bCulled = true;
			bPicked = false;
			for (i = 0; i < Shadows.Length; i++)
				if (Shadows[i] != None)
					Shadows[i].SetLight(None);
		}
		return;
	}
	bCulled = false;
	Allowed = TierAllowed();
	if (CanHold())
		return;

	Want = Max(OwnMax(), 1);
	Chosen.Length = 0;
	ChosenPriority.Length = 0;
	LastAmbient = AmbientLight();
	Total = LastAmbient;
	bOutdoors = SunVisible();
	bMostlyOutdoors = MostlyOutdoors();

	for (i = 0; i < Manager.StaticLights.Length && !(bOutdoors && bSunOnlyOutdoors); i++)
	{
		A = Manager.StaticLights[i];
		if (A == None)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
		{
			Total += Score;
			Offer(A, Score * (IsHeld(A) ? HoldBonus : 1.0), Want);
		}
	}
	Manager.RefreshDynamicLights();
	for (i = 0; i < Manager.DynamicLights.Length && !(bOutdoors && bSunOnlyOutdoors); i++)
	{
		A = Manager.DynamicLights[i];
		if (A == None || A.bDeleteMe)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
		{
			Total += Score;
			Offer(A, Score * (IsHeld(A) ? HoldBonus : 1.0), Want);
		}
	}
	// under open sky the sun always casts, bumping the weakest local light if needed
	if (bOutdoors)
	{
		Score = Manager.SunLightActor.LightBrightness;
		Total += Score;
		if (Chosen.Length >= Want)
		{
			Chosen.Remove(Want - 1, Chosen.Length - (Want - 1));
			ChosenPriority.Remove(Want - 1, ChosenPriority.Length - (Want - 1));
		}
		Chosen[Chosen.Length] = Manager.SunLightActor;
		ChosenPriority[ChosenPriority.Length] = Score;
	}
	LastTotalLight = Total;

	// shadows already heading for a chosen light keep it
	for (i = 0; i < Shadows.Length; i++)
	{
		Held[i] = -1;
		if (Shadows[i] == None || i >= Allowed)
			continue;
		for (j = 0; j < Chosen.Length; j++)
			if (Shadows[i].TargetLight() == Chosen[j])
			{
				Held[i] = j;
				break;
			}
	}
	// give each unclaimed chosen light to a free shadow
	for (j = 0; j < Min(Chosen.Length, Allowed); j++)
	{
		bFound = false;
		for (i = 0; i < Shadows.Length; i++)
			if (Held[i] == j)
			{
				bFound = true;
				break;
			}
		if (bFound)
			continue;
		for (i = 0; i < Shadows.Length; i++)
			if (Shadows[i] != None && Held[i] == -1 && i < Allowed)
			{
				Shadows[i].SetLight(Chosen[j]);
				Held[i] = j;
				break;
			}
	}
	// shadows left without a light fade out; the others get their light's share
	for (i = 0; i < Shadows.Length; i++)
	{
		if (Shadows[i] == None)
			continue;
		if (Held[i] == -1)
		{
			Shadows[i].SetLight(None);
			continue;
		}
		Share = 1.0;
		if (bRespectBaked && Total > 0)
			Share = MinShare + (1.0 - MinShare) * FClamp(ChosenPriority[Held[i]] / Total, 0, 1);
		Shadows[i].TargetShare = Share;
	}

	bPicked = true;
	PickLoc = Owner.Location;
	PickAllowed = Allowed;
	PickVersion = Manager.LightsVersion;
}

// one line for the log: what this character casts from
function string Describe()
{
	local int i;
	local string S;

	S = Owner.Name $ ": light here " $ int(LastTotalLight) $ " (ambient " $ int(LastAmbient) $ ")";
	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None && Shadows[i].AssignedLight != None)
			S = S $ " | " $ Shadows[i].AssignedLight.Name $ " share " $ Left(string(Shadows[i].LightShare), 4) $ " dark " $ Shadows[i].Proj.ShadowTexture.ShadowDarkness $ " fade " $ Shadows[i].Proj.MaxTraceDistance
				$ " at " $ (Shadows[i].Proj.Location - Owner.Location) $ " rot " $ Shadows[i].Proj.Rotation $ " dir " $ Shadows[i].Proj.LightDirection $ " dist " $ int(Shadows[i].Proj.LightDistance)
				$ " fov " $ Shadows[i].Proj.FOV $ " active " $ Shadows[i].Proj.bShadowActive;
	return S;
}

event Destroyed()
{
	local int i;

	// soft shadows switched off (Graphics page): the game's own shadow comes back
	if (StockDark > 0 && Pawn(Owner) != None && Pawn(Owner).Shadow != None && Pawn(Owner).Shadow.ShadowTexture != None)
		Pawn(Owner).Shadow.ShadowTexture.ShadowDarkness = StockDark;

	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None)
			Shadows[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	bPlayerOnly=False
	MaxShadows=1
	PlayerMaxShadows=4
	MaxLightDistance=1300.000000
	UpdateFrequency=0.200000
	ShadowStrength=175.000000
	FadeRate=5.000000
	HoldBonus=1.300000
	GradientLength=2048
	GradientScale=3.000000
	MaxSteepness=60.000000
	MinSteepness=35.000000
	FrustumDistance=600.000000
	MinStrength=0.500000
	SunStrength=1.000000
	SunFullBrightness=200.000000
	FullIntensity=128.000000
	CullDistance=3000.000000
	UnseenTime=0.300000
	SunClearance=1000.000000
	NearDistance=900.000000
	MidDistance=2000.000000
	RepickDistance=32.000000
	bRespectBaked=True
	bSunOnlyOutdoors=True
	AmbientWeight=1.000000
	MinShare=0.450000
	bHidden=True
	RemoteRole=ROLE_None
}
