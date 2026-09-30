//=============================================================================
// U2SoftShadows - gives every live character multi-light shadows (one
// SSShadowController each) in place of the engine's single projector shadow.
// Spawned on each level by SSShadowMutator.
//=============================================================================
class SSShadowManager extends Info;

var array<SSShadowController> Controllers;

// shared by every controller, so a new character costs no level-wide search:
// static lights and the sun are collected once, moving lights once per sweep
var array<Light> StaticLights;
var Actor SunLightActor;
var array<Actor> DynamicLights;
var float DynamicScanTime;
var PlayerController Viewer;
var bool bSuspended;             // switched off for testing (U2TestHub: hub shadows stock|off)

event PostBeginPlay()
{
	local Light L;
	local Actor A;

	Super.PostBeginPlay();
	Log("U2SoftShadows: manager active on "$Level.Title);
	bSuspended = !class'SSShadowController'.default.bEnabled;
	foreach AllActors(class'Light', L)
		if (!class'SSShadowController'.static.IsSun(L) && class'SSShadowController'.static.CastsLight(L))
			StaticLights[StaticLights.Length] = L;
	// the sun isn't always a Light: Unreal II's SunLight is a plain Actor
	foreach AllActors(class'Actor', A)
		if (class'SSShadowController'.static.IsSun(A) && A.LightType != LT_None
			&& (SunLightActor == None || A.LightBrightness > SunLightActor.LightBrightness))
			SunLightActor = A;
	// first sweep after the level's temporary precache pawns are gone
	SetTimer(0.5, true);
}

// moving lights (muzzle flashes, flares, lamps on actors), refreshed at most
// every 0.15 s however many controllers ask; projectiles skipped
// suspend: hand the adopted characters back to the game's own shadow (and
// stop adopting); resume: adopt again on the next sweep. Only characters this
// manager adopted are touched: the game gives some pawns no shadow on purpose.
function SetSuspended(bool bNew)
{
	bSuspended = bNew;
	if (bNew)
		ReleaseAll();
}

// settings changed (options menu): rebuild every adopted character's shadows
// with the new values on the next sweep
function ApplySettings()
{
	ReleaseAll();
	bSuspended = !class'SSShadowController'.default.bEnabled;
}

function ReleaseAll()
{
	local int i;
	local Pawn P;

	for (i = 0; i < Controllers.Length; i++)
	{
		if (Controllers[i] == None)
			continue;
		P = Pawn(Controllers[i].Owner);
		Controllers[i].Destroy();
		if (P != None && !P.bDeleteMe)
		{
			P.bActorShadows = true;      // the game's shadow, or re-adoption, from here
			P.ResetShadows();
		}
	}
	Controllers.Length = 0;
}

function RefreshDynamicLights()
{
	local Actor A;

	if (Level.TimeSeconds - DynamicScanTime >= 0.15 || DynamicScanTime == 0)
	{
		DynamicScanTime = Level.TimeSeconds;
		DynamicLights.Length = 0;
		foreach DynamicActors(class'Actor', A)
			if (A.bDynamicLight && !class'SSShadowController'.static.IsSun(A) && Projectile(A) == None
				&& class'SSShadowController'.static.CastsLight(A))
				DynamicLights[DynamicLights.Length] = A;
	}

}

event Timer()
{
	local Pawn P;
	local int i;
	local bool bHasShadow;
	local Controller C;

	if (Viewer == None || Viewer.bDeleteMe)
	{
		Viewer = None;
		for (C = Level.ControllerList; C != None; C = C.NextController)
			if (PlayerController(C) != None)
			{
				Viewer = PlayerController(C);
				break;
			}
	}

	// drop controllers whose character has gone
	for (i = Controllers.Length - 1; i >= 0; i--)
	{
		if (Controllers[i] == None)
		{
			Controllers.Remove(i, 1);
			continue;
		}
		if (Controllers[i].Owner == None || Controllers[i].Owner.bDeleteMe)
		{
			Controllers[i].Destroy();
			Controllers.Remove(i, 1);
		}
	}

	if (bSuspended)
		return;
	foreach DynamicActors(class'Pawn', P)
	{
		// only real, active characters that the engine would give a shadow to;
		// temporary precache pawns have no controller and are destroyed at once
		if (P.bDeleteMe || P.Controller == None || !P.bActorShadows || P.Mesh == None)
			continue;
		bHasShadow = false;
		for (i = 0; i < Controllers.Length; i++)
			if (Controllers[i].Owner == P)
			{
				bHasShadow = true;
				break;
			}
		if (!bHasShadow)
			Adopt(P);
	}
}

function Adopt(Pawn P)
{
	local SSShadowController C;

	// retire the engine's single shadow so it can't respawn on ResetShadows
	P.bActorShadows = false;
	if (P.ShadowA != None)
	{
		P.ShadowA.Destroy();
		P.ShadowA = None;
	}
	if (P.ShadowB != None)
	{
		P.ShadowB.Destroy();
		P.ShadowB = None;
	}

	C = Spawn(class'SSShadowController', P,, P.Location, P.Rotation);
	if (C == None)
		return;
	C.Instigator = P;
	C.Manager = Self;
	C.Initialize();
	Controllers[Controllers.Length] = C;
	Log("U2SoftShadows: multi-light shadows for "$P.Name$" ("$C.MaxShadows$" max)");
}

defaultproperties
{
	RemoteRole=ROLE_None
}
