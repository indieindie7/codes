//=============================================================================
// AvalonStorm - weather over the map that comes and goes. Between storms the
// outdoor zones keep the clear haze (AvalonCards Haze*); a storm builds over
// Ramp seconds, holds, and clears again. Its strength (Intensity 0..1) drives:
// the fog pulled in and greyed, a gloom over the whole view (the sky box takes
// no fog), a cloud deck of giant dark puffs round and over the player, rain
// falling round the player (none where a roof is overhead), the rain and wind
// loops, and lightning (only near full strength): a white flash on the screen
// and in the fog, then thunder a few seconds later, nearer = sooner.
// Engine only: zone fog, sprites, PlayerController flash/glow, ambient sounds.
// Spawned and configured by AvalonCards (Storm* keys).
//=============================================================================
class AvalonStorm extends Actor;

#exec TEXTURE IMPORT NAME=RainStreak FILE=Textures\RainStreak.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

var array<AvalonPuff> Drops;
var array<AvalonPuff> Clouds;   // the overcast: giant dark puffs round and over the player, greyed by the fog
var array<vector> CloudAt;
var array<float> CloudScale;   // each puff's full size: it grows in and shrinks away with the storm
var float CloudTurn;
var float Radius, Fall, Top;
var vector Wind;
var array<ZoneInfo> Zones;
var array<float> ClearStart, ClearEnd;    // each zone's own (clear weather) fog
var array<color> ClearColour;
var array<byte> ClearOn;
var float StormStart, StormEnd, SkyEnd;
var color FogColour, FlashColour;
var float NextBolt, ThunderAt, Flash;
var Sound Thunder[5];
var int NThunder;
var Actor WindSnd;
var float Gloom;          // the whole view darkened by this much (0..1) at full strength, and greyed
var vector GloomFog;
var PlayerController Gloomed;
var float GloomOn;        // how much of it is applied now

// the cycle: Clear s of clear weather, Ramp s building, Hold s of storm, Ramp s clearing; Clear 0 = always storm
var float ClearTime, RampTime, HoldTime, PhaseT, Intensity;
var int Phase;
var bool bForced;         // live editing held the weather (Force)

function Setup(int N, float R, float FallSpeed, vector Wd, float FogStart, float FogEnd, color Fog, Sound Rain, Sound WindLoop, float SkyFogEnd)
{
	local int i;
	local AvalonPuff P;
	local ZoneInfo Z;

	Radius = R;
	Fall = FallSpeed;
	Wind = Wd;
	Top = 1400;
	FogColour = Fog;
	StormStart = FogStart;
	StormEnd = FogEnd;
	SkyEnd = SkyFogEnd;
	FlashColour.R = 230;
	FlashColour.G = 235;
	FlashColour.B = 255;
	foreach AllActors(class'ZoneInfo', Z)
		if (Z.bDistanceFog || (Z.IsA('SkyZoneInfo') && SkyFogEnd > 0))
		{
			Zones[Zones.Length] = Z;
			ClearStart[ClearStart.Length] = Z.DistanceFogStart;
			ClearEnd[ClearEnd.Length] = Z.DistanceFogEnd;
			ClearColour[ClearColour.Length] = Z.DistanceFogColor;
			if (Z.bDistanceFog)
				ClearOn[ClearOn.Length] = 1;
			else
				ClearOn[ClearOn.Length] = 0;
		}
	for (i = 0; i < N; i++)
	{
		P = Spawn(class'AvalonPuff',,, Location);
		if (P == None)
			continue;
		P.Texture = Texture'RainStreak';
		P.Style = STY_Translucent;
		P.ScaleGlow = 0.7;
		P.SetDrawScale(2.4);
		Drops[Drops.Length] = P;
		Drop(P, true);
	}
	// the loops: rain on this actor, wind on a second one (one ambient sound per actor)
	AmbientSound = Rain;
	SoundRadius = 255;
	if (WindLoop != None)
	{
		WindSnd = Spawn(class'AvalonPuff',,, Location);
		if (WindSnd != None)
		{
			WindSnd.bHidden = True;
			WindSnd.AmbientSound = WindLoop;
			WindSnd.SoundRadius = 255;
		}
	}
	NextBolt = Level.TimeSeconds + 4;
	Intensity = 1;
	Phase = 2;
}

// Clear 0 = a storm that never ends; otherwise start somewhere in the cycle
function Cycle(float Clear, float Ramp, float Hold)
{
	ClearTime = Clear;
	RampTime = FMax(Ramp, 1);
	HoldTime = FMax(Hold, 1);
	if (Clear <= 0)
		return;
	Phase = Rand(4);
	PhaseT = FRand() * 0.8 * PhaseLength();
}

// live editing: P = 2 the storm now, 0 clear now (held until Force(-1) puts the cycle back)
function Force(int P)
{
	if (P < 0)
	{
		bForced = false;
		return;
	}
	bForced = true;
	Phase = P;
	PhaseT = 0;
}

function float PhaseLength()
{
	switch (Phase)
	{
	case 0: return ClearTime;
	case 2: return HoldTime;
	}
	return RampTime;
}

// the cloud deck: a ring low round the horizon and a lid overhead, so the sky box's painted sun and
// blue sky are covered (the sky box takes no fog). Each puff keeps its place relative to the player.
function Overcast(Texture T, int N, float Size)
{
	local int i;
	local AvalonPuff P;
	local vector O;
	local float A;

	for (i = 0; i < N; i++)
	{
		A = 6.2832 * i / N + FRand() * 0.2;
		if (i % 3 == 2)
		{
			O.X = 6000 * Cos(A);            // the lid
			O.Y = 6000 * Sin(A);
			O.Z = 7500 + FRand() * 1500;
		}
		else
		{
			O.X = 15000 * Cos(A);           // the ring
			O.Y = 15000 * Sin(A);
			O.Z = 1500 + FRand() * 4500;
		}
		P = Spawn(class'AvalonPuff',,, Location + O);
		if (P == None)
			continue;
		P.Texture = T;
		P.Style = STY_Alpha;
		P.SetDrawScale(Size * (0.8 + 0.4 * FRand()) / 128.0);
		CloudScale[Clouds.Length] = P.DrawScale;
		Clouds[Clouds.Length] = P;
		CloudAt[CloudAt.Length] = O;
	}
}

function AddThunder(Sound S)
{
	if (S != None && NThunder < 5)
		Thunder[NThunder++] = S;
}

// where the camera is: the local player's view
function vector Eye()
{
	local PlayerController PC;

	PC = Level.PlayerControllerList;
	if (PC != None && PC.Pawn != None)
		return PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	if (PC != None)
		return PC.Location;
	return Location;
}

// a drop back to the top of the column round the eye (anywhere in it on the first fill); hidden
// when something is overhead (indoors, under a deck) or the storm is too light for it
function Drop(AvalonPuff P, bool bAnyHeight)
{
	local vector E, S;
	local float A, D;

	E = Eye();
	A = FRand() * 6.2832;
	D = Radius * Sqrt(FRand());
	S = E;
	S.X += D * Cos(A);
	S.Y += D * Sin(A);
	S.Z += Top;
	if (bAnyHeight)
		S.Z -= FRand() * Top * 1.8;
	P.SetLocation(S);
	P.Start = S;
	P.bHidden = FRand() > Intensity || !FastTrace(S + vect(0,0,6000), S);
}

event Tick(float DeltaTime)
{
	local int i;
	local AvalonPuff P;
	local vector E, M;
	local float F;
	local rotator Spin;

	E = Eye();
	SetLocation(E);
	Weather(DeltaTime);
	if (WindSnd != None)
		WindSnd.SetLocation(E);
	// the cloud deck turns slowly round the player (the clouds move with the wind); the deck thins
	// out as the storm clears
	CloudTurn += DeltaTime * 0.004;
	Spin.Yaw = int(CloudTurn * 10430.4);      // radians -> rotator units
	for (i = 0; i < Clouds.Length; i++)
		if (Clouds[i] != None)
		{
			Clouds[i].SetLocation(E + (CloudAt[i] >> Spin));
			// the user (2026-10-07): clouds vanished too abruptly - each puff now grows in and shrinks
			// away over a quarter of the storm's rise (about 40 s with a 3 min ramp) instead of popping
			F = FClamp((Intensity * 1.15 - (i + 0.5) / Clouds.Length) * 4.0, 0, 1);
			Clouds[i].bHidden = F <= 0.02;
			if (!Clouds[i].bHidden)
				Clouds[i].SetDrawScale(CloudScale[i] * (0.3 + 0.7 * F));
		}
	M = Wind;
	M.Z = -Fall;
	for (i = 0; i < Drops.Length; i++)
	{
		P = Drops[i];
		if (P == None)
			continue;
		P.SetLocation(P.Location + M * DeltaTime);
		if (P.Location.Z < E.Z - Top * 0.8 || VSize((P.Location - E) * vect(1,1,0)) > Radius * 1.2)
			Drop(P, false);
	}
	// lightning, only in the thick of it: a flash now, the thunder later
	if (Level.TimeSeconds >= NextBolt)
	{
		if (Intensity > 0.75)
			Bolt();
		NextBolt = Level.TimeSeconds + 7 + FRand() * 14;
	}
	F = 0;
	if (Flash > 0)
	{
		Flash -= DeltaTime;
		F = FClamp(Flash / 0.35, 0, 1);
		if (FRand() < 0.15)
			F *= 0.3;                             // the flicker of a real bolt
	}
	SetFog(F);
	if (ThunderAt > 0 && Level.TimeSeconds >= ThunderAt)
	{
		ThunderAt = 0;
		if (NThunder > 0)
			PlaySound(Thunder[Rand(NThunder)], SLOT_None, 2.0, false, 60000);
	}
}

// the cycle, and what the strength sets: the loops' volume and the gloom over the view
function Weather(float DeltaTime)
{
	local float G;

	if (bForced)
	{
		// ease toward the forced state over a few seconds
		if (Phase == 2)
			Intensity = FMin(1, Intensity + DeltaTime / 8);
		else
			Intensity = FMax(0, Intensity - DeltaTime / 8);
	}
	else if (ClearTime > 0)
	{
		PhaseT += DeltaTime;
		if (PhaseT >= PhaseLength())
		{
			PhaseT = 0;
			Phase = (Phase + 1) % 4;
			Log("Cards: weather phase "$Phase);
		}
		switch (Phase)
		{
		case 0: Intensity = 0; break;
		case 1: Intensity = PhaseT / RampTime; break;
		case 2: Intensity = 1; break;
		case 3: Intensity = 1 - PhaseT / RampTime; break;
		}
		Intensity = Intensity * Intensity * (3 - 2 * Intensity);    // smoothstep: eases in and out
	}
	SoundVolume = int(190 * Intensity);
	if (WindSnd != None)
		WindSnd.SoundVolume = int(60 + 120 * Intensity);
	// the gloom: PlayerController's constant glow, adjusted by the change since last time
	if (Level.PlayerControllerList != Gloomed)
	{
		Gloomed = Level.PlayerControllerList;
		GloomOn = 0;
	}
	if (Gloomed != None)
	{
		G = Gloom * Intensity;
		if (Abs(G - GloomOn) > 0.005)
		{
			Gloomed.ClientAdjustGlow(-(G - GloomOn), GloomFog * ((G - GloomOn) / FMax(Gloom, 0.001)));
			GloomOn = G;
		}
	}
}

// each zone's fog between its clear weather and the storm's, and the lightning's white on top
function SetFog(float Flsh)
{
	local int i;
	local color C, S;
	local float W;

	W = Intensity;
	for (i = 0; i < Zones.Length; i++)
	{
		if (Zones[i] == None)
			continue;
		S = FogColour;
		if (Zones[i].IsA('SkyZoneInfo'))
		{
			Zones[i].bDistanceFog = W > 0.05 || ClearOn[i] == 1;
			Zones[i].DistanceFogStart = ClearStart[i] * (1 - W);
			Zones[i].DistanceFogEnd = Lerp(W, FMax(ClearEnd[i], SkyEnd * 20), SkyEnd);
		}
		else
		{
			Zones[i].DistanceFogStart = Lerp(W, ClearStart[i], StormStart);
			Zones[i].DistanceFogEnd = Lerp(W, ClearEnd[i], StormEnd);
		}
		C.R = ClearColour[i].R + (S.R - ClearColour[i].R) * W;
		C.G = ClearColour[i].G + (S.G - ClearColour[i].G) * W;
		C.B = ClearColour[i].B + (S.B - ClearColour[i].B) * W;
		C.R = C.R + (FlashColour.R - C.R) * Flsh;
		C.G = C.G + (FlashColour.G - C.G) * Flsh;
		C.B = C.B + (FlashColour.B - C.B) * Flsh;
		Zones[i].DistanceFogColor = C;
	}
}

function Bolt()
{
	local Controller C;
	local float Dist;

	Flash = 0.35;
	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
			PlayerController(C).ClientFlash(-0.2, vect(700,700,800));
	// a strike 1-6 km off: sound travels ~340 m/s
	Dist = 1000 + FRand() * 5000;
	ThunderAt = Level.TimeSeconds + Dist / 340.0;
}

event Destroyed()
{
	local int i;

	if (Gloomed != None && GloomOn > 0)
		Gloomed.ClientAdjustGlow(GloomOn, -GloomFog * (GloomOn / FMax(Gloom, 0.001)));
	for (i = 0; i < Drops.Length; i++)
		if (Drops[i] != None)
			Drops[i].Destroy();
	for (i = 0; i < Clouds.Length; i++)
		if (Clouds[i] != None)
			Clouds[i].Destroy();
	if (WindSnd != None)
		WindSnd.Destroy();
}

defaultproperties
{
	DrawType=DT_None
	bHidden=False
	bStatic=False
	bCollideActors=False
	bBlockActors=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
	bAlwaysRelevant=True
}
