//=============================================================================
// ModLightShadow - one character shadow cast from one light (ported from
// U2SoftShadows' SSLightShadow).
// The shadow itself is a plain engine ShadowProjector (Proj): Advent's engine
// places and aims those natively from ShadowActor and LightDirection, following
// the character's root bone, but it does NOT do that for script subclasses of
// ShadowProjector (measured: a subclass stays at its spawn rotation). So this
// class is a helper that steers its projector every frame (Step, called by the
// controller): the direction from its light, the light's distance, the darkness
// and the feet-to-head fade. It fades out before switching lights and back in
// afterwards; darkness eases toward the controller's TargetShare (this light's
// share of all the light at the character).
//=============================================================================
class ModLightShadow extends Info;

var ShadowProjector Proj;    // the engine shadow this helper steers
var Actor ShadowActor;       // the character
var Actor AssignedLight;     // light currently casting this shadow
var Actor PendingLight;      // light to switch to once faded out (None = retire)
var bool bSwitchPending;
var float Fade;              // 0..1 visibility
var float FadeRate;          // fade per second
var float ShadowStrength;    // darkness at full strength, 0-255
var float GradientScale;     // >1 leaves some shadow at the head's tip, <1 fades out sooner
var float MaxGradient;       // upper bound on the fade length, in world units
var float MaxSteepness;      // steepest a lamp may shine down, in degrees (overhead lamps are tilted
                             // so the shadow falls out from under the body where it can be seen)
var float MinSteepness;      // shallowest a lamp may shine down, in degrees: a low lamp's shadow is
                             // so long that the silhouette is spread thin and barely shows
var float MaxLightDistance;  // light distance used for the frustum, at most (closer = the silhouette fills more of the picture)
var float SunStrength;       // darkness of a bright sun's shadow, 0-1 (outdoors: one shadow)
var float SunFullBrightness; // sun brightness that casts the darkest shadow; a dimmer sun casts a lighter one
var float MinStrength;       // darkness of the faintest lamp shadow, relative to the darkest (0-1)
var float FullIntensity;     // lamp intensity (brightness x falloff) that casts the darkest shadow
var float InterpolateRate;   // how fast the direction turns toward a moving light (per second)
var float LightShare;        // this light's share of the light here (darkness scale), eased toward
var float TargetShare;       // the controller's latest value
var vector SmoothDir;        // light -> character direction actually used, eased toward the light's
var float SetDistance;       // the LightDistance InitShadow last fitted the frustum to

// makes the engine shadow, set up as Actor.InitShadowInfo does the game's own detailed shadow
function Setup(Actor Who)
{
	ShadowActor = Who;
	Proj = Spawn(class'ShadowProjector', None, '', Who.Location);
	if (Proj == None)
		return;
	Proj.ShadowActor = Who;
	Proj.CreateShadow();
	Proj.bBlobShadow = false;
	Proj.RootMotion = true;
	Proj.UpdateInterval = 0;
	Proj.LightDirection = Normal(vect(1,1,3));
	Proj.LightDistance = 380;
	Proj.InitShadow();
	Proj.bGradient = true;
	Hide();
}

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
		SmoothDir = vect(0,0,0);
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

static function bool IsSun(Actor A)
{
	return A.LightEffect == LE_Sunlight || A.IsA('Sunlight');
}

// a lamp almost straight above casts its shadow under the feet, hidden by the
// body: lean the direction (light -> character) so it's never steeper than MaxSteepness
function vector TiltOverhead(vector Dir)
{
	local rotator R;
	local int P, Limit;

	R = Rotator(Dir);
	P = R.Pitch & 65535;
	if (P > 32768)
		P -= 65536;                 // -16384 = straight down
	Limit = int(MaxSteepness * 65536.0 / 360.0);
	if (P < -Limit)
		R.Pitch = -Limit;
	Limit = int(MinSteepness * 65536.0 / 360.0);
	if (P > -Limit)
		R.Pitch = -Limit;
	return Vector(R);
}

// how strongly a lamp lights the character: brightness times a smooth falloff
// over its reach (25 units per LightRadius step)
function float LampIntensity(Actor L)
{
	local float Dist, Reach;

	Reach = 25.0 * (L.LightRadius + 1);
	Dist = VSize(L.Location - ShadowActor.Location);
	if (Dist >= Reach)
		return 0;
	return L.LightBrightness * (1.0 - Square(Dist / Reach));
}

// no light: nothing drawn. Only the darkness goes to 0: detaching the projector or
// clearing bShadowActive stops the engine updating it (measured)
function Hide()
{
	if (Proj != None && Proj.ShadowTexture != None)
		Proj.ShadowTexture.ShadowDarkness = 0;
}

// called every frame by the controller
function Step(float DeltaTime)
{
	local vector ToChar;
	local float Dist, Strength, SinE, Half, TipDepth, Pct;

	if (ShadowActor == None || ShadowActor.bDeleteMe || Proj == None)
	{
		Destroy();
		return;
	}

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
			SmoothDir = vect(0,0,0);
		}
	}
	else if (AssignedLight != None)
		Fade = FMin(1.0, Fade + FadeRate * DeltaTime);

	if (AssignedLight == None || Proj.ShadowTexture == None)
	{
		Hide();
		return;
	}

	// direction from the light to the character (the sun: its own direction)
	if (IsSun(AssignedLight))
	{
		ToChar = Vector(AssignedLight.Rotation);
		Dist = MaxLightDistance;
	}
	else
	{
		ToChar = ShadowActor.Location - AssignedLight.Location;
		Dist = FClamp(VSize(ToChar), 200, MaxLightDistance);
		ToChar = TiltOverhead(Normal(ToChar));
	}
	if (class'ModShadowController'.default.bDebugStockDir)
	{
		// testing: a low light (20 degrees up) behind and to the right of the camera, so
		// the shadow stretches far ahead and to the left, onto floor the camera sees
		ToChar = Vector(Level.GetLocalPlayerController().GetViewRotation());
		ToChar.Z = 0;
		ToChar = Normal(ToChar) + (vect(1,0,0) * ToChar.Y - vect(0,1,0) * ToChar.X);   // ahead + left
		ToChar = Normal(Normal(ToChar) * 0.94 - vect(0,0,0.34));
		Dist = 380;
	}
	// turn smoothly instead of snapping when the character walks past a lamp
	if (VSize(SmoothDir) < 0.5)
		SmoothDir = ToChar;
	else
	{
		Pct = FMin(1.0, DeltaTime * InterpolateRate);
		SmoothDir = Normal(SmoothDir + (ToChar - SmoothDir) * Pct);
	}
	// LightDirection points from the character toward the light
	Proj.LightDirection = -SmoothDir;
	Proj.ShadowTexture.LightDirection = Proj.LightDirection;
	// refit the frustum (FOV, DrawScale) only when the distance really changed
	if (Abs(Dist - SetDistance) > 48)
	{
		Proj.LightDistance = Dist;
		SetDistance = Dist;
		Proj.InitShadow();
	}

	// feet-to-head fade: past the head's tip on flat ground
	// (the stock shadow uses 350, which fades most of a long shadow away)
	Half = ShadowActor.CollisionHeight;
	if (Half < 20)
		Half = 44;   // crowd actors without collision: a person's height
	SinE = FMax(SmoothDir.Z * -1, 0.25);
	TipDepth = 2 * Half / SinE - Half * SinE;
	Proj.MaxTraceDistance = int(FClamp(TipDepth * GradientScale, Half, MaxGradient));

	// darker when the light is close and bright, lighter far away, scaled by the fade
	// the other lights (and the ambient light) fill the shadow in
	LightShare += (TargetShare - LightShare) * FMin(1.0, DeltaTime * 6.0);
	if (IsSun(AssignedLight))
		// one shadow under open sky, as strong as the sun is bright (a dim or setting sun casts a
		// lighter one)
		Strength = SunStrength * FClamp(AssignedLight.LightBrightness / SunFullBrightness, 0.4, 1.0);
	else
		Strength = (MinStrength + (1.0 - MinStrength) * FClamp(LampIntensity(AssignedLight) / FullIntensity, 0.0, 1.0)) * LightShare;
	Proj.ShadowTexture.ShadowDarkness = byte(FClamp(ShadowStrength * Strength * Fade, 0, 255));
}

event Destroyed()
{
	if (Proj != None)
		Proj.Destroy();
	Super.Destroyed();
}

defaultproperties
{
	FadeRate=2.500000
	ShadowStrength=200.000000
	GradientScale=3.000000
	MaxGradient=2048.000000
	MaxSteepness=60.000000
	MinSteepness=35.000000
	SunStrength=1.000000
	SunFullBrightness=200.000000
	MaxLightDistance=600.000000
	MinStrength=0.200000
	FullIntensity=128.000000
	InterpolateRate=12.000000
	LightShare=1.000000
	TargetShare=1.000000
	SetDistance=-1000.000000
	RemoteRole=ROLE_None
}
