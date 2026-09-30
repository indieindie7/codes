//=============================================================================
// Picks the lights that most strongly light one character and gives each its
// own SSLightShadow. A shadow stays on its light for as long as that light
// remains in the top set, so shadows don't swap and flicker.
//
// Tunable in User.ini under [U2SoftShadows.SSShadowController].
//=============================================================================
class SSShadowController extends Actor
	config(User);

var config bool bEnabled;        // the whole add-on (the game's own shadows come back when off)
var config int MaxShadows;
var config float MaxLightDistance;
var config float UpdateFrequency;
var config float ShadowStrength;
var config float FadeRate;
var config int GradientLength;   // longest the feet-to-head fade may reach, in world units
var config float GradientScale;  // fade length as a multiple of the shadow's length: 1 = gone at
                                 // the head's tip, 3 = the tip keeps two thirds (gentle)
var config int SunResolution;    // sun shadow texture size: 64 very soft, 128 soft, 256 sharp
var config int LampResolution;   // lamp shadow texture size: 64 very soft, 128 soft (shadows are always soft)
var config float MaxSteepness;   // overhead lamps are tilted to at most this steep (degrees)
var config float MinStrength;    // darkness of the faintest lamp shadow (dim or far lamp), 0-1
var config float FullIntensity;  // lamp brightness x falloff that casts the darkest shadow
var config float CullDistance;   // characters farther than this from the player cast no shadows
var config float UnseenTime;     // nor do characters off screen for this long (seconds)
var config float SunClearance;   // the sun casts when nothing is this close overhead toward it (world units)
var config bool bCameraCull;     // shadows only for characters the camera can see
var config float CullFOVMargin;  // degrees beyond the camera's view cone before a character is dropped
var config float NearDistance;   // within this: every shadow (and capsules, if on)
var config float MidDistance;    // within this: one light shadow + contact; beyond: contact only

var int Allowed;                 // light shadows allowed at the current distance
var config bool bContactShadow;  // a soft dark patch on the floor under the feet
var config bool bHardToSoft;     // a sharper copy of the strongest light's shadow at the feet, fading fast
var config int SharpResolution;  // its texture size (256 crisp)
var config float SharpScale;     // how far it reaches, as a fraction of the shadow's length
var config float SharpStrength;  // its darkness relative to the soft shadow
var config bool bPerLightSoftness; // lamp shadows a little crisper from bright near lamps, softer from dim far ones
var config bool bWeightedPick;   // pick lights at random, weighted by strength, instead of always the strongest
var config float HoldFraction;   // a light already casting keeps its place while at least this strong vs the best

var array<Actor> Cands;          // this update's candidate lights and scores (weighted pick)
var array<float> CandScore;

var SSLightShadow Sharp;
var config bool bCapsules;       // experiment: per-limb soft ovals from the strongest light
var array<SSCapsuleShadow> Capsules;

var SSContactShadow Contact;

var SSShadowManager Manager;
var bool bCulled;

var array<SSLightShadow> Shadows;
var array<Actor> Chosen;
var array<float> ChosenPriority;

function Initialize()
{
	local SSLightShadow S;
	local rotator Down;
	local int i;

	if (Pawn(Owner) == None)
	{
		Destroy();
		return;
	}

	if (Manager == None)
	{
		Destroy();
		return;
	}

	for (i = 0; i < MaxShadows; i++)
	{
		S = Spawn(class'SSLightShadow', Owner,, Owner.Location, Owner.Rotation);
		if (S == None)
			continue;
		// let the character configure it exactly as SOverhaul does its own shadow
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
		S.bPerLightSoftness = bPerLightSoftness;
		S.bGradient = true;
		Shadows[Shadows.Length] = S;
	}

	if (bHardToSoft)
	{
		Sharp = Spawn(class'SSLightShadow', Owner,, Owner.Location, Owner.Rotation);
		if (Sharp != None)
		{
			Pawn(Owner).InitShadow(Sharp);
			Sharp.InterpolateRate = class'SSLightShadow'.default.InterpolateRate;
			Sharp.MaxLightDistance = MaxLightDistance;
			Sharp.ShadowStrength = ShadowStrength;
			Sharp.FadeRate = FadeRate;
			Sharp.MaxGradient = GradientLength;
			Sharp.MaxSteepness = MaxSteepness;
			Sharp.MinStrength = MinStrength;
			Sharp.FullIntensity = FullIntensity;
			Sharp.bSharp = true;
			Sharp.bBlurShadow = false;      // the one crisp copy; everything else stays blurred
			Sharp.SharpResolution = SharpResolution;
			Sharp.ShadowResolution = SharpResolution;
			Sharp.SharpScale = SharpScale;
			Sharp.SharpStrength = SharpStrength;
			Sharp.bGradient = true;
		}
	}
	if (bCapsules)
	{
		AddCapsule("Merc Pelvis", "Merc Neck", 17);
		AddCapsule("Merc Neck", "Merc Head", 10);
		AddCapsule("Merc L Thigh", "Merc L Calf", 9);
		AddCapsule("Merc R Thigh", "Merc R Calf", 9);
		AddCapsule("Merc L Calf", "Merc L Foot", 8);
		AddCapsule("Merc R Calf", "Merc R Foot", 8);
		AddCapsule("Merc L UpperArm", "Merc L Forearm", 7);
		AddCapsule("Merc R UpperArm", "Merc R Forearm", 7);
		AddCapsule("Merc L Forearm", "Merc L Hand", 6);
		AddCapsule("Merc R Forearm", "Merc R Hand", 6);
		Enable('Tick');
	}
	if (bContactShadow)
	{
		Down.Pitch = -16384;
		Contact = Spawn(class'SSContactShadow', Owner,, Owner.Location, Down);
		if (Contact != None)
			Contact.Show(true);
	}

	SelectLights();
	// start at a random point in the cycle so controllers don't all update in
	// the same frame; Timer switches to the regular rate
	SetTimer(UpdateFrequency * (0.2 + 0.8 * FRand()), false);
}

event Tick(float DeltaTime)
{
	if (Owner == None || Owner.bDeleteMe)
	{
		Destroy();
		return;
	}
	if (Capsules.Length > 0 && !bCulled && Allowed >= MaxShadows)
		UpdateCapsules();
	else if (Capsules.Length > 0 && Capsules[0] != None && Capsules[0].bShown)
		HideCapsules();
}

function HideCapsules()
{
	local int i;
	for (i = 0; i < Capsules.Length; i++)
		if (Capsules[i] != None)
			Capsules[i].Show(false);
}

function AddCapsule(string A, string B, float R)
{
	local SSCapsuleShadow C;

	C = Spawn(class'SSCapsuleShadow', Owner,, Owner.Location);
	if (C == None)
		return;
	C.NodeA = A;
	C.NodeB = B;
	C.Radius = R;
	C.Show(true);
	Capsules[Capsules.Length] = C;
}

// every frame: the strongest chosen light's direction and the floor under the
// character, then each limb's oval
function UpdateCapsules()
{
	local Actor L;
	local vector Dir, HitLoc, HitNorm;
	local float FloorZ;
	local int i;

	if (Chosen.Length == 0)
	{
		for (i = 0; i < Capsules.Length; i++)
			if (Capsules[i] != None && Capsules[i].bShown)
				Capsules[i].Show(false);
		return;
	}
	L = Chosen[0];
	if (IsSun(L))
		Dir = vector(L.Rotation);
	else
		Dir = Normal(Owner.Location - L.Location);
	if (Trace(HitLoc, HitNorm, Owner.Location - vect(0,0,400), Owner.Location, false) != None)
		FloorZ = HitLoc.Z;
	else
		FloorZ = Owner.Location.Z - Owner.CollisionHeight;
	for (i = 0; i < Capsules.Length; i++)
		if (Capsules[i] != None)
		{
			if (!Capsules[i].bShown)
				Capsules[i].Show(true);
			Capsules[i].Update(Pawn(Owner), Dir, FloorZ);
		}
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
// all of them close up, one at mid range, none (contact only) far away
function int TierAllowed()
{
	local PlayerController V;
	local vector ViewLoc;
	local float Dist;

	V = Manager.Viewer;
	if (V == None || Pawn(Owner).Controller == V)
		return MaxShadows;
	if (V.Pawn != None)
		ViewLoc = V.Pawn.Location;
	else
		ViewLoc = V.Location;
	Dist = VSize(Owner.Location - ViewLoc);
	if (Dist <= NearDistance)
		return MaxShadows;
	if (Dist <= MidDistance)
		return Min(MaxShadows, 1);
	return 0;
}

// weighted random choice of Max(MaxShadows,1) lights from the candidates
// (probability proportional to strength), keeping any light a shadow already
// casts from while it is still at least HoldFraction of the best. Different
// characters in the same room get different, still plausible, light sets and
// a character's set doesn't churn.
function WeightedPick()
{
	local int i, j, Want;
	local float Best, Total, R;
	local Actor L;

	Want = Max(MaxShadows, 1);
	for (i = 0; i < CandScore.Length; i++)
		Best = FMax(Best, CandScore[i]);
	// keep what's already casting, if still strong enough
	for (i = 0; i < Shadows.Length && Chosen.Length < Want; i++)
	{
		if (Shadows[i] == None)
			continue;
		L = Shadows[i].TargetLight();
		for (j = 0; j < Cands.Length; j++)
			if (Cands[j] == L && CandScore[j] >= Best * HoldFraction)
			{
				Chosen[Chosen.Length] = L;
				ChosenPriority[ChosenPriority.Length] = CandScore[j];
				Cands.Remove(j, 1);
				CandScore.Remove(j, 1);
				break;
			}
	}
	// fill the rest at random, weighted by strength
	while (Chosen.Length < Want && Cands.Length > 0)
	{
		Total = 0;
		for (j = 0; j < CandScore.Length; j++)
			Total += CandScore[j];
		R = FRand() * Total;
		for (j = 0; j < CandScore.Length; j++)
		{
			R -= CandScore[j];
			if (R <= 0 || j == CandScore.Length - 1)
				break;
		}
		Chosen[Chosen.Length] = Cands[j];
		ChosenPriority[ChosenPriority.Length] = CandScore[j];
		Cands.Remove(j, 1);
		CandScore.Remove(j, 1);
	}
	// strongest first: the sharp copy and the capsules follow Chosen[0]
	for (i = 0; i < Chosen.Length; i++)
		for (j = i + 1; j < Chosen.Length; j++)
			if (ChosenPriority[j] > ChosenPriority[i])
			{
				L = Chosen[i]; Chosen[i] = Chosen[j]; Chosen[j] = L;
				R = ChosenPriority[i]; ChosenPriority[i] = ChosenPriority[j]; ChosenPriority[j] = R;
			}
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

function Offer(Actor L, float Priority)
{
	local int i, k;

	if (bWeightedPick)
	{
		for (i = 0; i < Cands.Length; i++)
			if (Cands[i] == L)
				return;
		Cands[Cands.Length] = L;
		CandScore[CandScore.Length] = Priority;
		return;
	}

	for (i = 0; i < Chosen.Length; i++)
		if (Chosen[i] == L)
			return;
	for (k = 0; k < Chosen.Length; k++)
		if (Priority > ChosenPriority[k])
			break;
	if (k >= Max(MaxShadows, 1))
		return;         // always rank at least the best light (the capsules and the sharp copy use it)
	Chosen.Insert(k, 1);
	ChosenPriority.Insert(k, 1);
	Chosen[k] = L;
	ChosenPriority[k] = Priority;
	if (Chosen.Length > Max(MaxShadows, 1))
	{
		Chosen.Remove(Max(MaxShadows, 1), Chosen.Length - Max(MaxShadows, 1));
		ChosenPriority.Remove(Max(MaxShadows, 1), ChosenPriority.Length - Max(MaxShadows, 1));
	}
}

function SelectLights()
{
	local int i, j;
	local Actor A;
	local float Score;
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
			for (i = 0; i < Shadows.Length; i++)
				if (Shadows[i] != None)
					Shadows[i].SetLight(None);   // fades out, then frees its texture
			if (Contact != None)
				Contact.Show(false);
			if (Sharp != None)
				Sharp.SetLight(None);
		}
		return;
	}
	if (bCulled && Contact != None)
		Contact.Show(true);
	bCulled = false;
	Allowed = TierAllowed();

	Chosen.Length = 0;
	ChosenPriority.Length = 0;
	Cands.Length = 0;
	CandScore.Length = 0;

	for (i = 0; i < Manager.StaticLights.Length; i++)
	{
		A = Manager.StaticLights[i];
		if (A == None)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
			Offer(A, Score);
	}
	Manager.RefreshDynamicLights();
	for (i = 0; i < Manager.DynamicLights.Length; i++)
	{
		A = Manager.DynamicLights[i];
		if (A == None || A.bDeleteMe)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
			Offer(A, Score);
	}
	if (bWeightedPick)
		WeightedPick();
	// under open sky the sun always casts, bumping the weakest local light if needed
	if (SunVisible())
	{
		if (Chosen.Length >= MaxShadows)
		{
			Chosen.Remove(MaxShadows - 1, Chosen.Length - (MaxShadows - 1));
			ChosenPriority.Remove(MaxShadows - 1, ChosenPriority.Length - (MaxShadows - 1));
		}
		Chosen[Chosen.Length] = Manager.SunLightActor;
	}

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
			if (Shadows[i] != None && Held[i] == -1)
			{
				Shadows[i].SetLight(Chosen[j]);
				Held[i] = j;
				break;
			}
	}
	// shadows left without a light fade out
	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None && Held[i] == -1)
			Shadows[i].SetLight(None);
	// the sharp copy follows the strongest chosen light (near tier only)
	if (Sharp != None)
	{
		if (Chosen.Length > 0 && Allowed >= MaxShadows)
			Sharp.SetLight(Chosen[0]);
		else
			Sharp.SetLight(None);
	}
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Shadows.Length; i++)
		if (Shadows[i] != None)
			Shadows[i].Destroy();
	if (Contact != None)
		Contact.Destroy();
	if (Sharp != None)
		Sharp.Destroy();
	for (i = 0; i < Capsules.Length; i++)
		if (Capsules[i] != None)
			Capsules[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	bEnabled=True
	MaxShadows=3
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
	bContactShadow=True
	bHardToSoft=True
	bPerLightSoftness=False
	bWeightedPick=False
	HoldFraction=0.500000
	bCapsules=False
	SharpResolution=256
	SharpScale=0.700000
	SharpStrength=1.000000
	bHidden=True
	RemoteRole=ROLE_None
}
