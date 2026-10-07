//=============================================================================
// AvalonPlume - motion over the plant: a column of sprites rising from a stack
// (the cinematography report: "smoke, flare, birds, ship, trucks" - a still
// view reads as a living place once something in it moves). Kinds:
//   0 smoke  - dark, slow, long-lived, leaning with the wind
//   1 steam  - white (additive), faster, short-lived: the cooling towers
//   2 flare  - a flickering flame with a dynamic light, and a smoke wisp over it
// Each puff is recycled at the source when it dies, so the count never grows.
// Spawned and configured by AvalonCards (Plumes[] lines).
//=============================================================================
class AvalonPlume extends Actor;

var int Kind;
var float Width;           // the column's width at the source (world units)
var float Rise;            // how far a puff climbs over its life
var vector Wind;           // drift, units per second
var array<AvalonPuff> Puffs;
var AvalonPlume Wisp;      // a flare's smoke

function Setup(int K, float W, float R, vector Wd, Texture SmokeTex, Texture FireTex, byte SmokeStyle, Texture SteamTex)
{
	local int i, N;
	local AvalonPuff P;

	Kind = K;
	Width = FMax(W, 50);
	Rise = FMax(R, 100);
	Wind = Wd;
	N = 18;
	if (Kind == 1)
		N = 14;
	if (Kind == 2)
		N = 10;
	for (i = 0; i < N; i++)
	{
		P = Spawn(class'AvalonPuff',,, Location);
		if (P == None)
			continue;
		if (Kind == 2)
		{
			P.Texture = FireTex;
			P.Style = STY_Translucent;
		}
		else
		{
			// smokestill08 (smoke) carries its shape in alpha only (white RGB): additive would draw a white
			// square, so it is alpha blended; the steam texture has the shape in its colour (black
			// round it) and is added, which keeps it white at a distance
			if (Kind == 1 && SteamTex != None)
			{
				P.Texture = SteamTex;
				P.Style = STY_Translucent;
			}
			else
			{
				P.Texture = SmokeTex;
				P.Style = StyleOf(SmokeStyle);
			}
		}
		Puffs[Puffs.Length] = P;
		Respawn(P);
		P.Age = P.Life * i / N;      // start spread along the column, not all at the source
	}
	if (Kind == 2)
	{
		// the flame lights what is round it (a dynamic light: no rebuild)
		LightType = LT_Flicker;
		LightEffect = LE_None;
		LightBrightness = 220;
		LightHue = 22;
		LightSaturation = 40;
		LightRadius = 48;
		bDynamicLight = True;
		Wisp = Spawn(class'AvalonPlume',,, Location + vect(0,0,1) * Width * 1.5);
		if (Wisp != None)
			Wisp.Setup(0, Width * 0.6, Rise * 0.7, Wd, SmokeTex, FireTex, SmokeStyle, SteamTex);
	}
	else
		LightType = LT_None;
}

function ERenderStyle StyleOf(byte S)
{
	switch (S)
	{
	case 3: return STY_Translucent;
	case 4: return STY_Brighten;
	case 5: return STY_Modulated;
	case 2: return STY_Masked;
	}
	return STY_Alpha;
}

function Respawn(AvalonPuff P)
{
	local float J;

	J = Width * 0.25;
	P.Age = 0;
	P.Start = Location + vect(1,0,0) * (FRand() - 0.5) * J + vect(0,1,0) * (FRand() - 0.5) * J;
	switch (Kind)
	{
	case 0:
		P.Life = 10 + 6 * FRand();
		P.Size0 = Width;
		P.Grow = 3.0;
		P.Glow = 0.8;
		break;
	case 1:
		P.Life = 6 + 3 * FRand();
		P.Size0 = Width;
		P.Grow = 2.2;
		P.Glow = 0.5;
		break;
	default:
		P.Life = 0.5 + 0.4 * FRand();
		P.Size0 = Width * (0.7 + 0.5 * FRand());
		P.Grow = 0.4;
		P.Glow = 1.0;
	}
	P.Drift = Wind * (0.8 + 0.4 * FRand());
	P.Drift.Z = Rise / P.Life * (0.8 + 0.4 * FRand());
}

event Tick(float DeltaTime)
{
	local int i;
	local AvalonPuff P;
	local float T, F;
	local vector D;

	for (i = 0; i < Puffs.Length; i++)
	{
		P = Puffs[i];
		if (P == None)
			continue;
		P.Age += DeltaTime;
		if (P.Age >= P.Life)
			Respawn(P);
		T = P.Age / P.Life;
		// rises fast at first, then spreads and slows (a plume, not a rocket); the wind carries it sideways
		D = P.Drift;
		D.Z = 0;
		P.SetLocation(P.Start + D * P.Age + vect(0,0,1) * P.Drift.Z * P.Life * T * (2 - T));
		P.SetDrawScale(P.Size0 * (1 + P.Grow * T) / 128.0);
		F = FMin(1, T / 0.12) * (1 - T);
		P.ScaleGlow = P.Glow * F * 1.3;
	}
	if (Kind == 2)
		LightBrightness = 180 + Rand(75);
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Puffs.Length; i++)
		if (Puffs[i] != None)
			Puffs[i].Destroy();
	if (Wisp != None)
		Wisp.Destroy();
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
