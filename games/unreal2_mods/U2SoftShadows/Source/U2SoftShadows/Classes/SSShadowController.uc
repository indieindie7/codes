//=============================================================================
// Picks the lights that most strongly light one character and gives each its
// own SSLightShadow. A shadow stays on its light for as long as that light
// remains in the top set, so shadows don't swap and flicker.
//
// Tunable in User.ini under [U2SoftShadows.SSShadowController].
//=============================================================================
class SSShadowController extends Actor
	config(User);

var config int MaxShadows;
var config float MaxLightDistance;
var config float UpdateFrequency;
var config float ShadowStrength;
var config float FadeRate;
var config int GradientLength;   // longest the feet-to-head fade may stretch, in world units
var config float GradientScale;  // fade length relative to the shadow (lower = stronger fade)
var config int SunResolution;    // sun shadow texture size: 64 very soft, 128 soft, 256 sharp
var config int LightResolution;  // lamp shadow texture size, 0 = character's own (512/256)
var config float CullDistance;   // characters farther than this from the player cast no shadows
var config float UnseenTime;     // nor do characters off screen for this long (seconds)

var SSShadowManager Manager;
var bool bCulled;

var array<SSLightShadow> Shadows;
var array<Actor> Chosen;
var array<float> ChosenPriority;

function Initialize()
{
	local SSLightShadow S;
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
		if (LightResolution > 0)
			S.ShadowResolution = LightResolution;
		S.bGradient = true;
		Shadows[Shadows.Length] = S;
	}

	SelectLights();
	// start at a random point in the cycle so controllers don't all update in
	// the same frame; Timer switches to the regular rate
	SetTimer(UpdateFrequency * (0.2 + 0.8 * FRand()), false);
}

event Tick(float DeltaTime)
{
	if (Owner == None || Owner.bDeleteMe)
		Destroy();
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

	V = Manager.Viewer;
	if (V == None || Pawn(Owner).Controller == V)
		return false;
	if (V.Pawn != None)
		ViewLoc = V.Pawn.Location;
	else
		ViewLoc = V.Location;
	if (VSize(Owner.Location - ViewLoc) > CullDistance)
		return true;
	return Level.TimeSeconds - Owner.LastRenderTime > UnseenTime;
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
	ToSun = -vector(Manager.SunLightActor.Rotation) * 16384;
	Head = Owner.Location;
	Head.Z += Owner.CollisionHeight * 0.8;
	return FastTrace(Owner.Location + ToSun, Owner.Location) || FastTrace(Head + ToSun, Head);
}

function Offer(Actor L, float Priority)
{
	local int i, k;

	for (i = 0; i < Chosen.Length; i++)
		if (Chosen[i] == L)
			return;
	for (k = 0; k < Chosen.Length; k++)
		if (Priority > ChosenPriority[k])
			break;
	if (k >= MaxShadows)
		return;
	Chosen.Insert(k, 1);
	ChosenPriority.Insert(k, 1);
	Chosen[k] = L;
	ChosenPriority[k] = Priority;
	if (Chosen.Length > MaxShadows)
	{
		Chosen.Remove(MaxShadows, Chosen.Length - MaxShadows);
		ChosenPriority.Remove(MaxShadows, ChosenPriority.Length - MaxShadows);
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
		}
		return;
	}
	bCulled = false;

	Chosen.Length = 0;
	ChosenPriority.Length = 0;

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

	// shadows already heading for a chosen light keep it
	for (i = 0; i < Shadows.Length; i++)
	{
		Held[i] = -1;
		if (Shadows[i] == None)
			continue;
		for (j = 0; j < Chosen.Length; j++)
			if (Shadows[i].TargetLight() == Chosen[j])
			{
				Held[i] = j;
				break;
			}
	}
	// give each unclaimed chosen light to a free shadow
	for (j = 0; j < Chosen.Length; j++)
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
	MaxShadows=3
	MaxLightDistance=1300.000000
	UpdateFrequency=0.200000
	ShadowStrength=190.000000
	FadeRate=2.500000
	GradientLength=600
	GradientScale=1.100000
	SunResolution=128
	LightResolution=0
	CullDistance=3000.000000
	UnseenTime=1.000000
	bHidden=True
	RemoteRole=ROLE_None
}
