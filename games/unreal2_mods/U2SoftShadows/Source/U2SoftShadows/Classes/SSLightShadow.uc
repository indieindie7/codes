//=============================================================================
// One shadow cast from one assigned light, built on the engine's own
// ShadowProjector so it uses Unreal II's render path (PreRender/SetRes,
// GetShadowLocation, FrustumOrigin). SquirrelZero's projector was written for
// UT2004 and skips all three, which is why it rendered nothing here.
// Fades out before switching lights and back in afterwards; darkness scales
// with distance to the light.
//=============================================================================
class SSLightShadow extends ShadowProjector;

var Actor AssignedLight;     // light currently casting this shadow
var Actor PendingLight;      // light to switch to once faded out (None = retire)
var bool bSwitchPending;
var float Fade;              // 0..1 visibility
var float FadeRate;          // fade per second
var float ShadowStrength;    // darkness at full strength, 0-255
var float MaxLightDistance;
var bool bFrustumInit;
var ShadowBitmapMaterial LastTexture;
var int SunResolution;       // texture size for sun shadows (lower = softer), 0 = character's own
var float GradientScale;     // >1 leaves some shadow at the head's tip, <1 fades out sooner
var float MaxGradient;       // upper bound on the fade length, in world units

// the light this shadow is heading toward (after any pending switch)
function Actor TargetLight()
{
	if (bSwitchPending)
		return PendingLight;
	return AssignedLight;
}

function SetLight(Actor NewLight)
{
	if (NewLight == TargetLight())
		return;
	if (AssignedLight == None && !bSwitchPending)
	{
		AssignedLight = NewLight;
		Fade = 0;
		return;
	}
	if (NewLight == AssignedLight)
	{
		// switch cancelled: fade back in on the same light
		bSwitchPending = false;
		PendingLight = None;
		return;
	}
	PendingLight = NewLight;
	bSwitchPending = true;
}

function UpdateShadow(optional float DeltaTime)
{
	// the character is gone: never let the engine query its bones again
	if (ShadowActor == None || ShadowActor.bDeleteMe || ShadowActor.Mesh == None)
	{
		DetachProjector(true);
		Destroy();
		return;
	}
	// nothing assigned: no shadow at all (the engine would attach a blob)
	if (AssignedLight == None && !bSwitchPending)
	{
		DetachProjector(true);
		if (ShadowTexture != None)
		{
			ShadowTexture.ShadowActor = None;
			Level.ObjectPool.FreeObject(ShadowTexture);
			ShadowTexture = None;
			ProjTexture = None;
		}
		return;
	}
	Super.UpdateShadow(DeltaTime);
}

function bool CalcPos(float DeltaTime)
{
	local float Pct, Dist, Strength, SinE, Half, FeetDepth, TipDepth, Shift;
	local int WantRes;
	local vector Diff, LightLoc;
	local rotator LightRot;

	// fade bookkeeping: fade out before switching, fade in otherwise
	if (bSwitchPending)
	{
		Fade -= FadeRate * DeltaTime;
		if (Fade <= 0)
		{
			Fade = 0;
			AssignedLight = PendingLight;
			PendingLight = None;
			bSwitchPending = false;
		}
	}
	else if (AssignedLight != None)
		Fade = FMin(1.0, Fade + FadeRate * DeltaTime);

	if (AssignedLight == None)
		return false;

	// engine positioning (ShadowProjector.CalcPos), aimed at our light
	if (ShadowTexture != None)
		SetLocation(ShadowTexture.GetShadowLocation());
	else
	{
		SetLocation(ShadowActor.Location + vect(0,0,5));
		SetRotation(Rotator(Normal(-LightDirection)));
		return true;
	}

	// a freshly allocated texture carries a stale origin from the pool
	if (ShadowTexture != LastTexture)
	{
		LastTexture = ShadowTexture;
		bFrustumInit = false;
		LastLightDistance = -1;
	}

	// softer (lower-res) texture for the sun; only resized while invisible
	if (AssignedLight.LightEffect == LE_Sunlight && SunResolution > 0)
		WantRes = SunResolution;
	else
		WantRes = ShadowResolution;
	if (WantRes > 0 && ShadowTexture.USize != WantRes && (Fade < 0.05 || !bFrustumInit))
	{
		ShadowTexture.SetRes(WantRes);
		LastLightDistance = -1;   // force SetLightDistance to refit DrawScale
	}

	if (AssignedLight.LightEffect == LE_Sunlight)
	{
		Dist = 1024;
		LightRot = AssignedLight.Rotation;
	}
	else
	{
		Diff = Location - AssignedLight.Location;
		Dist = FMin(VSize(Diff), 1024);
		if (Dist > 0)
			LightRot = Rotator(Diff);
		else
			LightRot = AssignedLight.Rotation;
	}
	LightLoc = Location - Vector(LightRot) * Dist;

	// engine-style smoothing of the light origin (turns instead of snapping)
	if (!bFrustumInit)
	{
		ShadowTexture.FrustumOrigin = LightLoc;
		bFrustumInit = true;
	}
	else
	{
		Pct = FMin(1.0, DeltaTime * InterpolateRate);
		ShadowTexture.FrustumOrigin += (LightLoc - ShadowTexture.FrustumOrigin) * Pct;
	}
	Diff = Location - ShadowTexture.FrustumOrigin;
	LightRot = Rotator(Diff);
	SetRotation(LightRot);
	SetLightDistance(VSize(Diff), AssignedLight.LightEffect == LE_Sunlight);
	LightDirection = -Vector(LightRot) * LightDistance;
	ShadowTexture.LightDirection = Normal(LightDirection);
	ShadowTexture.LightDistance = LightDistance;

	// feet-to-head fade: the gradient runs along the projection axis from the
	// projector plane to MaxTraceDistance, so fit it to where this light puts the
	// feet and the head's tip on the ground (flat-ground estimate)
	Half = ShadowActor.CollisionHeight;
	SinE = FMax(-Vector(LightRot).Z, 0.25);
	FeetDepth = Half * SinE;
	TipDepth = 2 * Half / SinE - Half * SinE;
	Shift = 0;
	if (AssignedLight.LightEffect == LE_Sunlight)
	{
		// the sun frustum is nearly parallel, so sliding the projector along its
		// axis to the feet is free and starts the fade right at the feet
		Shift = FeetDepth * 0.85;
		SetLocation(Location + Vector(LightRot) * Shift);
	}
	MaxTraceDistance = int(FClamp((TipDepth - Shift) * GradientScale, Half, MaxGradient));

	// darker when the light is close, lighter far away, scaled by the fade
	if (AssignedLight.LightEffect == LE_Sunlight)
		Strength = 0.8;
	else
		Strength = 0.4 + 0.6 * (1.0 - FClamp(VSize(AssignedLight.Location - ShadowActor.Location) / MaxLightDistance, 0.0, 1.0));
	ShadowTexture.ShadowDarkness = byte(FClamp(ShadowStrength * Strength * Fade, 0, 255));

	return true;
}

defaultproperties
{
	FadeRate=2.500000
	ShadowStrength=190.000000
	MaxLightDistance=1300.000000
	InterpolateRate=4.000000
	bForceFullPolyShadow=True
	bGradient=True
	SunResolution=128
	GradientScale=1.100000
	MaxGradient=600.000000
	GradientTexture=Texture'Engine.GRADIENT_Fade'
	RemoteRole=ROLE_None
}
