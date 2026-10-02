//=============================================================================
// ModShadowManager - gives characters multi-light shadows (one
// ModShadowController each) in place of the game's single shadow from a fixed
// direction (ported from U2SoftShadows' SSShadowManager). Spawned in each level
// by ModMutator when ModSettings.bSoftShadows is set.
// Lights are collected once per level and shared by every controller, so a new
// character costs no level-wide search; moving lights are rescanned at most
// every 0.15 s however many controllers ask.
//=============================================================================
class ModShadowManager extends Info;

var array<ModShadowController> Controllers;
var array<Light> StaticLights;
var Actor SunLightActor;
var array<Actor> DynamicLights;
var float DynamicScanTime;
var int LightsVersion;           // bumped whenever the set of moving lights changes
var PlayerController Viewer;
var bool bSuspended;
var float ReportTime;
var int Reports;

function Note(string S)
{
	class'ModSettings'.static.Note("softshadows: " $ S);
}

event PostBeginPlay()
{
	local Light L;
	local int Skipped;

	Super.PostBeginPlay();
	foreach AllActors(class'Light', L)
	{
		if (class'ModLightShadow'.static.IsSun(L))
		{
			if (L.LightType != LT_None && (SunLightActor == None || L.LightBrightness > SunLightActor.LightBrightness))
				SunLightActor = L;
		}
		else if (class'ModShadowController'.static.CastsLight(L))
			StaticLights[StaticLights.Length] = L;
		else
			Skipped++;
	}
	Note(StaticLights.Length $ " lamps light characters (" $ Skipped $ " others skipped), sun " $ SunLightActor);
	// first sweep after the level's temporary precache pawns are gone
	SetTimer(0.5, true);
}

// moving lights (flares, lamps on actors). Projectiles and anything short-lived
// (muzzle flashes, sparks: a LifeSpan) are skipped, so gunfire doesn't jerk shadows around
function RefreshDynamicLights()
{
	local Actor A;
	local array<Actor> Found;
	local bool bChanged;
	local int i;

	if (Level.TimeSeconds - DynamicScanTime < 0.15 && DynamicScanTime != 0)
		return;
	DynamicScanTime = Level.TimeSeconds;
	foreach DynamicActors(class'Actor', A)
		if (A.bDynamicLight && !class'ModLightShadow'.static.IsSun(A) && Projectile(A) == None && A.LifeSpan == 0
			&& class'ModShadowController'.static.CastsLight(A))
			Found[Found.Length] = A;
	bChanged = Found.Length != DynamicLights.Length;
	for (i = 0; i < Found.Length && !bChanged; i++)
		bChanged = Found[i] != DynamicLights[i];
	if (bChanged)
	{
		DynamicLights = Found;
		LightsVersion++;
	}
}

event Timer()
{
	local Pawn P;
	local int i;
	local bool bHas;
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
		if (Controllers[i] != None && Controllers[i].Owner != None && !Controllers[i].Owner.bDeleteMe)
			continue;
		if (Controllers[i] != None)
			Controllers[i].Destroy();
		Controllers.Remove(i, 1);
	}

	// a few reports for testing: what each adopted character casts from
	ReportTime += 0.5;
	if (ReportTime >= 3.0 && Reports < 6)
	{
		ReportTime = 0;
		Reports++;
		for (i = 0; i < Controllers.Length; i++)
			Note(Controllers[i].Describe());
	}

	if (bSuspended)
		return;
	foreach DynamicActors(class'Pawn', P)
	{
		// the level's temporary precache pawns (no controller, gone within moments) are skipped
		if (P.bDeleteMe || !P.bActorShadows || P.Mesh == None || (P.Controller == None && Level.TimeSeconds < 2.0))
			continue;
		if (class'ModShadowController'.default.bPlayerOnly && (Viewer == None || P.Controller != Viewer))
			continue;
		bHas = false;
		for (i = 0; i < Controllers.Length; i++)
			if (Controllers[i].Owner == P)
			{
				bHas = true;
				break;
			}
		if (!bHas)
			Adopt(P);
	}
}

function Adopt(Pawn P)
{
	local ModShadowController C;

	// retire the game's single shadow (and stop it coming back)
	// (bActorShadows stays on: the engine only updates shadows of characters that have it)
	if (P.Shadow != None)
	{
		Note("stock shadow of " $ P.Name $ ": at " $ (P.Shadow.Location - P.Location) $ " rot " $ P.Shadow.Rotation $ " dir " $ P.Shadow.LightDirection $ " dist " $ P.Shadow.LightDistance
			$ " fov " $ P.Shadow.FOV $ " scale " $ P.Shadow.DrawScale $ " trace " $ P.Shadow.MaxTraceDistance $ " active " $ P.Shadow.bShadowActive $ " blob " $ P.Shadow.bBlobShadow
			$ " root " $ P.Shadow.RootMotion $ " interval " $ P.Shadow.UpdateInterval $ " owner " $ P.Shadow.Owner $ " base " $ P.Shadow.Base $ " physics " $ P.Shadow.Physics $ " tex dark " $ P.Shadow.ShadowTexture.ShadowDarkness);
		// kept but never drawn: with no shadow of its own, the engine stops updating the
		// pawn's other shadow projectors too (measured)
		if (P.Shadow.ShadowTexture != None)
			P.Shadow.ShadowTexture.ShadowDarkness = 0;
	}
	C = Spawn(class'ModShadowController', P, '', P.Location, P.Rotation);
	if (C == None)
		return;
	C.Manager = Self;
	C.Initialize();
	// testing: does the engine only draw the shadow it knows as the pawn's own?
	if (class'ModShadowController'.default.bDebugOwnShadow && C.Shadows.Length > 0)
		P.Shadow = C.Shadows[0].Proj;
	Controllers[Controllers.Length] = C;
	Note("multi-light shadows for " $ P.Name $ " (" $ C.OwnMax() $ " max)");
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Controllers.Length; i++)
		if (Controllers[i] != None)
			Controllers[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	RemoteRole=ROLE_None
}
