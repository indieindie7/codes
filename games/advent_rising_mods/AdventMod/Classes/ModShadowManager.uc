//=============================================================================
// ModShadowManager - gives characters multi-light shadows (one
// ModShadowController each) in place of the game's single shadow from a fixed
// direction (ported from U2SoftShadows' SSShadowManager). Spawned in each level
// by ModMutator when ModSettings.bSoftShadows is set.
// Lights are collected once per level and shared by every controller, so a new
// character costs no level-wide search; moving lights are rescanned at most
// every 0.15 s however many controllers ask.
//=============================================================================
class ModShadowManager extends Info
	config(AdventMod);

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
var config bool bPcssIndoorsOnly;  // contact hardening only while the player is indoors (outdoors it loses the sun shadow)
var float OutdoorTime;             // how long the player has been on the other side of the last switch
var int PcssState;                 // -1 unknown, 0 off, 1 on
var float LastFrameTime;           // newest LastRenderTime seen: what "on screen now" means
var config int NpcShadows;         // how many other characters cast shadows at once: the nearest ones in view
var config bool bCrowdShadows;     // also Advent's simpleAnim crowd actors
var config bool bCrowdActorShadows; // switch their bActorShadows on (without it the engine never draws their shadows; it came with crashes before the FPU fix)
var config float NpcSwapTime;      // a character out of that set this long gives its shadows up
var array<Actor> TurnedOn;          // characters whose bActorShadows we switched on (put back when they leave the pool)

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
	local int i;
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
	for (i = TurnedOn.Length - 1; i >= 0; i--)
		if (TurnedOn[i] == None || TurnedOn[i].bDeleteMe)
			TurnedOn.Remove(i, 1);

	// a few reports for testing: what each adopted character casts from
	ReportTime += 0.5;
	if (ReportTime >= 3.0 && Reports < 6)
	{
		ReportTime = 0;
		Reports++;
		for (i = 0; i < Controllers.Length; i++)
			Note(Controllers[i].Describe());
	}

	if (bPcssIndoorsOnly)
		UpdatePcss();
	if (bSuspended)
		return;
	UpdatePool();
}

// the player always; of the others (characters, and the animated crowd actors Advent fills
// rooms with), the NpcShadows nearest on screen. One that drops out of that set keeps its
// shadows for NpcSwapTime (no flicker at the edge)
function UpdatePool()
{
	local Actor A;
	local Pawn P;
	local array<Actor> Near;
	local array<Actor> Want;
	local array<float> WantDist;
	local float Dist, Newest;
	local int i, k, Npcs;
	local bool bHas;

	foreach DynamicActors(class'Actor', A)
	{
		if (A.bDeleteMe || A.bHidden || A.DrawType != DT_Mesh || A.Mesh == None)
			continue;
		Newest = FMax(Newest, A.LastRenderTime);
		P = Pawn(A);
		if (P != None)
		{
			// the level's temporary precache pawns (no controller, gone within moments) are skipped
			if (P.Controller == None && Level.TimeSeconds < 2.0)
				continue;
			if (Viewer != None && P.Controller == Viewer)
			{
				if (P.bActorShadows && Find(P) < 0)
					Adopt(P);
				continue;
			}
			if (P.Health <= 0)
				continue;
		}
		else if (!bCrowdShadows || !A.IsA('simpleAnim'))
			continue;
		if (class'ModShadowController'.default.bPlayerOnly || NpcShadows <= 0 || Viewer == None)
			continue;
		if (VSize(A.Location - ViewSpot()) <= class'ModShadowController'.default.CullDistance)
			Near[Near.Length] = A;
	}
	// LastRenderTime runs on its own clock in this game: on screen = drawn in the newest frame
	LastFrameTime = Newest;
	for (i = 0; i < Near.Length; i++)
	{
		A = Near[i];
		if (Newest - A.LastRenderTime > 0.3)
			continue;
		Dist = VSize(A.Location - ViewSpot());
		for (k = 0; k < Want.Length; k++)
			if (Dist < WantDist[k])
				break;
		if (k >= NpcShadows)
			continue;
		Want.Insert(k, 1);
		WantDist.Insert(k, 1);
		Want[k] = A;
		WantDist[k] = Dist;
		if (Want.Length > NpcShadows)
		{
			Want.Remove(NpcShadows, 1);
			WantDist.Remove(NpcShadows, 1);
		}
	}

	// characters that left the set: after a while their shadows go
	for (i = Controllers.Length - 1; i >= 0; i--)
	{
		if (Controllers[i].IsPlayer())
			continue;
		bHas = false;
		for (k = 0; k < Want.Length; k++)
			if (Want[k] == Controllers[i].Owner)
				bHas = true;
		if (bHas)
		{
			Controllers[i].OutOfPool = 0;
			Npcs++;
			continue;
		}
		Controllers[i].OutOfPool += 0.5;
		if (Controllers[i].OutOfPool < NpcSwapTime)
		{
			Npcs++;
			continue;
		}
		Note("shadows of " $ Controllers[i].Owner.Name $ " go back to the pool");
		Release(Controllers[i].Owner);
		Controllers[i].Destroy();
		Controllers.Remove(i, 1);
	}
	for (k = 0; k < Want.Length && Npcs < NpcShadows; k++)
		if (Find(Want[k]) < 0)
		{
			// the engine only updates the shadows of actors that have bActorShadows
			if (!Want[k].bActorShadows && (Pawn(Want[k]) != None || bCrowdActorShadows))
			{
				Want[k].bActorShadows = true;
				TurnedOn[TurnedOn.Length] = Want[k];
			}
			Adopt(Want[k]);
			Npcs++;
		}
}

function vector ViewSpot()
{
	if (Viewer.Pawn != None)
		return Viewer.Pawn.Location;
	return Viewer.Location;
}

function int Find(Actor P)
{
	local int i;

	for (i = 0; i < Controllers.Length; i++)
		if (Controllers[i] != None && Controllers[i].Owner == P)
			return i;
	return -1;
}

function Release(Actor P)
{
	local int i;

	for (i = 0; i < TurnedOn.Length; i++)
		if (TurnedOn[i] == P)
		{
			if (P != None && !P.bDeleteMe)
				P.bActorShadows = false;
			TurnedOn.Remove(i, 1);
			return;
		}
}

// contact hardening indoors only: switched once the player has been outdoors (or back
// indoors) for 4 s, judged by five points, so doorways, beams and window frames don't flicker it
function UpdatePcss()
{
	local int i, Want;

	Want = PcssState;
	for (i = 0; i < Controllers.Length; i++)
		if (Controllers[i] != None && Controllers[i].IsPlayer() && Controllers[i].bPicked)
			Want = int(!Controllers[i].bMostlyOutdoors);
	if (Want == PcssState || Want < 0)
	{
		OutdoorTime = 0;
		return;
	}
	OutdoorTime += 0.5;
	if (OutdoorTime < 4.0 && PcssState >= 0)
		return;
	OutdoorTime = 0;
	PcssState = Want;
	class'ModSettings'.static.NativeCall("Pcss:" $ Want);
}

function Adopt(Actor A)
{
	local ModShadowController C;
	local Pawn P;
	local byte StockDark;

	P = Pawn(A);

	// retire the game's single shadow (and stop it coming back)
	// (bActorShadows stays on: the engine only updates shadows of characters that have it)
	if (P != None && P.Shadow != None)
	{
		Note("stock shadow of " $ P.Name $ ": at " $ (P.Shadow.Location - P.Location) $ " rot " $ P.Shadow.Rotation $ " dir " $ P.Shadow.LightDirection $ " dist " $ P.Shadow.LightDistance
			$ " fov " $ P.Shadow.FOV $ " scale " $ P.Shadow.DrawScale $ " trace " $ P.Shadow.MaxTraceDistance $ " active " $ P.Shadow.bShadowActive $ " blob " $ P.Shadow.bBlobShadow
			$ " root " $ P.Shadow.RootMotion $ " interval " $ P.Shadow.UpdateInterval $ " owner " $ P.Shadow.Owner $ " base " $ P.Shadow.Base $ " physics " $ P.Shadow.Physics $ " tex dark " $ P.Shadow.ShadowTexture.ShadowDarkness);
		// kept but never drawn: with no shadow of its own, the engine stops updating the
		// pawn's other shadow projectors too (measured)
		if (P.Shadow.ShadowTexture != None)
		{
			StockDark = P.Shadow.ShadowTexture.ShadowDarkness;
			P.Shadow.ShadowTexture.ShadowDarkness = 0;
		}
	}
	C = Spawn(class'ModShadowController', A, '', A.Location, A.Rotation);
	if (C == None)
		return;
	C.Manager = Self;
	C.StockDark = StockDark;
	C.Initialize();
	// testing: does the engine only draw the shadow it knows as the pawn's own?
	if (P != None && class'ModShadowController'.default.bDebugOwnShadow && C.Shadows.Length > 0)
		P.Shadow = C.Shadows[0].Proj;
	Controllers[Controllers.Length] = C;
	Note("multi-light shadows for " $ A.Name $ " (" $ C.OwnMax() $ " max) at " $ A.Location $ " collision " $ A.CollisionRadius $ "x" $ A.CollisionHeight $ " drawtype " $ A.DrawType);
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
	bPcssIndoorsOnly=True
	NpcShadows=20
	NpcSwapTime=1.5
	bCrowdShadows=True
	bCrowdActorShadows=True
	PcssState=-1
	RemoteRole=ROLE_None
}
