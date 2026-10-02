//=============================================================================
// Picks the lights that most strongly light one character and gives each its
// own SSLightShadow. A shadow stays on its light for as long as that light
// remains in the top set, so shadows don't swap and flicker; and the set is
// only re-picked once the character has moved, so a character standing still
// keeps perfectly still shadows. Moving between lamps, shadows fade from one
// light to the next.
//
// Each shadow's darkness follows its light's share of all the light reaching
// the character (lamps in reach plus the zone's ambient light): in a room lit
// from many sides, the other lights fill each shadow in, as they would for
// real, and the baked lighting isn't painted over.
//
// Tunable in User.ini under [U2SoftShadows.SSShadowController].
//=============================================================================
class SSShadowController extends Actor
	config(User);

var config bool bEnabled;        // the whole add-on (the game's own shadows come back when off)
var config int MaxShadows;       // light shadows per character
var config int PlayerMaxShadows; // light shadows for the player's own character
var config float MaxLightDistance;
var config float UpdateFrequency;
var config float ShadowStrength;
var config float FadeRate;
var config int GradientLength;   // longest the feet-to-head fade may reach, in world units
var config float GradientScale;  // fade length as a multiple of the shadow's length: 1 = gone at
                                 // the head's tip, 3 = the tip keeps two thirds (gentle)
var config int SunResolution;    // sun shadow texture size: 64 very soft, 128 soft
var config int LampResolution;   // lamp shadow texture size: 64 very soft, 128 soft (shadows are always soft)
var config float MaxSteepness;   // overhead lamps are tilted to at most this steep (degrees)
var config float MinStrength;    // darkness of the faintest lamp shadow (dim or far lamp), 0-1
var config float FullIntensity;  // lamp brightness x falloff that casts the darkest shadow
var config float CullDistance;   // characters farther than this from the player cast no shadows
var config float UnseenTime;     // nor do characters off screen for this long (seconds)
var config float SunClearance;   // the sun casts when nothing is this close overhead toward it (world units)
var config bool bCameraCull;     // shadows only for characters the camera can see
var config float CullFOVMargin;  // degrees beyond the camera's view cone before a character is dropped
var config float NearDistance;   // within this: every shadow
var config float MidDistance;    // within this: one shadow; beyond: none
var config float RepickDistance; // the light set is re-picked only after moving this far (world units)
var config bool bRespectBaked;   // darkness follows the light's share of all light here (lamps + ambient)
var config float AmbientWeight;  // how much the zone's ambient brightness counts against the lamps
var config float MinShare;       // darkness kept even when a light is a small share of the total, 0-1
var config bool bFitToFloor;     // end the feet-to-head fade where the shadow really lands (stairs, slopes)

var int Allowed;                 // light shadows allowed at the current distance

var SSShadowManager Manager;
var bool bCulled;

var array<SSLightShadow> Shadows;
var array<Actor> Chosen;
var array<float> ChosenPriority;

// the last pick: where, with how many allowed, and how much light there was
var bool bPicked;
var vector PickLoc;
var int PickAllowed;
var int PickVersion;             // the manager's LightsVersion at that pick
var bool bHeld;                  // the last update kept the set (standing still)
var float LastTotalLight;        // lamps in reach + ambient, at the last pick ("how lit is it here")
var float LastAmbient;

function bool IsPlayer()
{
	return Manager != None && Manager.Viewer != None && Pawn(Owner).Controller == Manager.Viewer;
}

function int OwnMax()
{
	if (IsPlayer())
		return Max(PlayerMaxShadows, MaxShadows);
	return MaxShadows;
}

function Initialize()
{
	local SSLightShadow S;
	local int i;

	if (Pawn(Owner) == None || Manager == None)
	{
		Destroy();
		return;
	}

	for (i = 0; i < OwnMax(); i++)
	{
		S = Spawn(class'SSLightShadow', Owner,, Owner.Location, Owner.Rotation);
		if (S == None)
			continue;
		// let the character configure it exactly as the game does its own shadow
		Pawn(Owner).InitShadow(S);
		S.InterpolateRate = class'SSLightShadow'.default.InterpolateRate;
		S.MaxLightDistance = MaxLightDistance;
		S.ShadowStrength = ShadowStrength;
		S.FadeRate = FadeRate;
		// the fade is refitted to the shadow's length every frame
		S.MaxGradient = GradientLength;
		S.GradientScale = GradientScale;
		S.SunResolution = SunResolution;
		if (LampResolution > 0)
			S.ShadowResolution = LampResolution;
		S.MaxSteepness = MaxSteepness;
		S.MinStrength = MinStrength;
		S.FullIntensity = FullIntensity;
		S.bFitToFloor = bFitToFloor;
		S.bGradient = true;
		Shadows[Shadows.Length] = S;
	}

	SelectLights();
	// start at a random point in the cycle so controllers don't all update in
	// the same frame; Timer switches to the regular rate
	SetTimer(UpdateFrequency * (0.2 + 0.8 * FRand()), false);
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

// far away or out of sight for a while: no shadows, no light searches. The
// player's own character always keeps them (it's never drawn in first person)
function bool ShouldCull()
{
	local PlayerController V;
	local vector ViewLoc;

	if (Manager.bSuspended)
		return true;
	V = Manager.Viewer;
	if (V == None || Pawn(Owner).Controller == V)
		return false;
	if (V.Pawn != None)
		ViewLoc = V.Pawn.Location;
	else
		ViewLoc = V.Location;
	if (VSize(Owner.Location - ViewLoc) > CullDistance)
		return true;
	if (bCameraCull && OutsideView(V, ViewLoc))
		return true;
	return Level.TimeSeconds - Owner.LastRenderTime > UnseenTime;
}

// how many light shadows this character gets at its distance from the camera:
// all of them close up, one at mid range, none far away
function int TierAllowed()
{
	local PlayerController V;
	local vector ViewLoc;
	local float Dist;

	V = Manager.Viewer;
	if (V == None || Pawn(Owner).Controller == V)
		return OwnMax();
	if (V.Pawn != None)
		ViewLoc = V.Pawn.Location;
	else
		ViewLoc = V.Location;
	Dist = VSize(Owner.Location - ViewLoc);
	if (Dist <= NearDistance)
		return OwnMax();
	if (Dist <= MidDistance)
		return Min(OwnMax(), 1);
	return 0;
}

// outside the camera's view cone (plus a margin, so a shadow can enter the
// frame before its character does). Off-screen characters aren't rendered, so
// LastRenderTime would catch them too, but only after UnseenTime.
function bool OutsideView(PlayerController V, vector ViewLoc)
{
	local vector ToPawn, ViewDir;
	local float Dist, HalfFOV, AngleToPawn, PawnAngle;

	ToPawn = Owner.Location - ViewLoc;
	Dist = VSize(ToPawn);
	if (Dist < Owner.CollisionRadius * 4)
		return false;                                   // right next to the camera
	ViewDir = vector(V.GetViewRotation());
	AngleToPawn = Acos(FClamp((ToPawn / Dist) dot ViewDir, -1, 1)) * 180 / Pi;
	PawnAngle = Atan2(FMax(Owner.CollisionHeight, Owner.CollisionRadius) * 2.0, Dist) * 180 / Pi;
	HalfFOV = V.FovAngle * 0.5;
	// a widescreen view is wider than FovAngle (which is the vertical-ish reference)
	return AngleToPawn - PawnAngle > HalfFOV + CullFOVMargin;
}

// the sun: an engine light set to sunlight, or Unreal II's own SunLight actor
// (native, never flagged LE_Sunlight in script)
static function bool IsSun(Actor A)
{
	return A.LightEffect == LE_Sunlight || A.IsA('SunLight');
}

// a light worth considering at all: switched on and actually bright
static function bool CastsLight(Actor A)
{
	return A.LightType != LT_None && A.LightBrightness > 0 && A.LightRadius > 0 && !A.bUnlit;
}

// how strongly this light lights the character, 0 if not at all: brightness
// times a smooth falloff over the light's reach (the engine's world radius,
// 25 units per LightRadius step)
function float LightScore(Actor A)
{
	local float Dist, Reach, Falloff;

	Dist = VSize(A.Location - Owner.Location);
	if (Dist > MaxLightDistance || Dist < Owner.CollisionRadius)
		return 0;   // too far to matter, or inside the character
	Reach = 25.0 * (A.LightRadius + 1);
	if (Dist >= Reach)
		return 0;
	Falloff = 1.0 - Square(Dist / Reach);
	return A.LightBrightness * Falloff;
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

// sunlight is directional: its actor can sit anywhere (even inside geometry),
// so test the open sky along the sun's direction instead of its position
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

// the zone's ambient light, on the same scale as LightScore
function float AmbientLight()
{
	if (Region.Zone == None)
		return 0;
	return Region.Zone.AmbientBrightness * AmbientWeight;
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

// the current set can stay: the character hasn't moved far, nothing about its
// distance tier changed and every light it casts from still shines
function bool CanHold()
{
	local int i;
	local Actor L;

	if (!bPicked || Allowed != PickAllowed || VSize(Owner.Location - PickLoc) >= RepickDistance)
		return false;
	Manager.RefreshDynamicLights();
	if (Manager.LightsVersion != PickVersion)
		return false;                // a lamp was switched on or off nearby
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
					Shadows[i].SetLight(None);   // fades out, then frees its texture
		}
		return;
	}
	bCulled = false;
	Allowed = TierAllowed();
	bHeld = CanHold();
	if (bHeld)
		return;

	Want = Max(OwnMax(), 1);
	Chosen.Length = 0;
	ChosenPriority.Length = 0;
	LastAmbient = AmbientLight();
	Total = LastAmbient;

	for (i = 0; i < Manager.StaticLights.Length; i++)
	{
		A = Manager.StaticLights[i];
		if (A == None)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
		{
			Total += Score;
			Offer(A, Score, Want);
		}
	}
	Manager.RefreshDynamicLights();
	for (i = 0; i < Manager.DynamicLights.Length; i++)
	{
		A = Manager.DynamicLights[i];
		if (A == None || A.bDeleteMe)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
		{
			Total += Score;
			Offer(A, Score, Want);
		}
	}
	// under open sky the sun always casts, bumping the weakest local light if needed
	if (SunVisible())
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

	// shadows already heading for a chosen light keep it (if the tier allows it)
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
	// give each unclaimed chosen light to a free shadow (only as many as the
	// distance tier allows)
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

event Destroyed()
{
	local int i;

	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None)
			Shadows[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	bEnabled=True
	MaxShadows=3
	PlayerMaxShadows=4
	MaxLightDistance=1300.000000
	UpdateFrequency=0.200000
	ShadowStrength=190.000000
	FadeRate=2.500000
	GradientLength=2048
	GradientScale=3.000000
	SunResolution=128
	LampResolution=128
	MaxSteepness=60.000000
	MinStrength=0.200000
	FullIntensity=128.000000
	CullDistance=3000.000000
	UnseenTime=0.300000
	SunClearance=1000.000000
	bCameraCull=True
	CullFOVMargin=20.000000
	NearDistance=900.000000
	MidDistance=2000.000000
	RepickDistance=32.000000
	bRespectBaked=True
	AmbientWeight=1.000000
	MinShare=0.350000
	bFitToFloor=True
	bHidden=True
	RemoteRole=ROLE_None
}
