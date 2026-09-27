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

var array<SSLightShadow> Shadows;
var array<Light> LightList;
var Light SunLightActor;
var array<Actor> Chosen;
var array<float> ChosenPriority;

function Initialize()
{
	local Light L;
	local SSLightShadow S;
	local int i;

	if (Pawn(Owner) == None)
	{
		Destroy();
		return;
	}

	// static lights never move, so collect them once; the sun is kept apart
	foreach AllActors(class'Light', L)
	{
		if (L.LightEffect != LE_Sunlight)
		{
			if (CastsLight(L))
				LightList[LightList.Length] = L;
		}
		else if (SunLightActor == None || L.LightBrightness > SunLightActor.LightBrightness)
			SunLightActor = L;
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
	SetTimer(UpdateFrequency, true);
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
	SelectLights();
}

// a light worth considering at all: switched on and actually bright
function bool CastsLight(Actor A)
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

	if (SunLightActor == None)
		return false;
	ToSun = -vector(SunLightActor.Rotation) * 16384;
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

	if (Owner == None)
		return;
	SetLocation(Owner.Location);

	Chosen.Length = 0;
	ChosenPriority.Length = 0;

	for (i = 0; i < LightList.Length; i++)
	{
		A = LightList[i];
		if (A == None)
			continue;
		Score = LightScore(A);
		if (Score > 0 && LightReaches(A.Location))
			Offer(A, Score);
	}
	// moving lights (muzzle flashes, flares, lamps on actors); projectiles skipped
	foreach DynamicActors(class'Actor', A)
	{
		if (!A.bDynamicLight || A.LightEffect == LE_Sunlight || Projectile(A) != None || !CastsLight(A))
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
		Chosen[Chosen.Length] = SunLightActor;
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
	bHidden=True
	RemoteRole=ROLE_None
}
