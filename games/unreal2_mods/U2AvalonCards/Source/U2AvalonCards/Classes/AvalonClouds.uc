//=============================================================================
// AvalonClouds - fair-weather cumulus over the island (the user, 2026-10-07:
// "can we do volumetric clouds or imposter cards procedurally"). Each bank
// is a cluster of soft sprites: a flat, darker base (SmokePuff, alpha) and a
// heaped, bright top (SteamPuff, additive), so the bank reads as a lit volume
// and shows parallax as the player moves. The banks drift with the wind and
// wrap round the island; the storm's own deck (AvalonStorm) covers them when
// it builds.
//=============================================================================
class AvalonClouds extends Info;

var array<AvalonPuff> Puffs;
var array<vector> Offset;      // each puff's place in its bank
var array<int> BankOf;
var array<vector> Bank;        // bank centres
var vector Drift;
var float Spread;

function Setup(int N, float Height, float InSpread, vector Wind, Texture Top, Texture Base)
{
	local int b, k, n2;
	local vector C, O;
	local AvalonPuff P, H;
	local float R, S;

	Spread = InSpread;
	Drift = Wind * 0.6;
	Drift.Z = 0;
	for (b = 0; b < N; b++)
	{
		C.X = Location.X + (FRand() * 2 - 1) * Spread;
		C.Y = Location.Y + (FRand() * 2 - 1) * Spread;
		C.Z = Height + FRand() * 2500;
		Bank[b] = C;
		R = 4000 + FRand() * 4000;                  // the bank's half width
		n2 = 14 + Rand(8);
		for (k = 0; k < n2; k++)
		{
			// a dome: wide flat base, puffs heaping up toward the middle
			O.X = (FRand() * 2 - 1) * R;
			O.Y = (FRand() * 2 - 1) * R * 0.6;
			O.Z = (1 - Abs(O.X) / R) * R * 0.55 * FRand();
			S = (1.6 - Abs(O.X) / R) * R / 128.0 * (0.8 + 0.4 * FRand());
			P = Spawn(class'AvalonPuff',,, C + O);
			if (P == None)
				continue;
			// Q34 (2026-10-08, the research: "light each bank as one volume"): every puff is the same soft alpha
			// shape, shaded by its height in the bank - a dark flat base rising to a pale top (MSFS 2004 / Crysis 1
			// gradient shading) - instead of each puff carrying its own dark base and bright top; a few additive
			// highlights sit only on the upper heap
			if (Base != None)
			{
				P.Texture = Base;
				P.Style = STY_Alpha;
				P.ScaleGlow = 0.55 + 1.5 * FClamp(O.Z / (R * 0.55), 0, 1);
				if (O.Z < R * 0.12)
					S *= 1.15;
			}
			else
			{
				P.Texture = Top;
				P.Style = STY_Translucent;
			}
			if (Top != None && Base != None && O.Z > R * 0.3 && FRand() < 0.3)
			{
				H = Spawn(class'AvalonPuff',,, C + O + vect(0,0,1) * R * 0.08);
				if (H != None)
				{
					H.Texture = Top;
					H.Style = STY_Translucent;
					H.ScaleGlow = 0.18;
					H.SetDrawScale(S * 0.7);
					Puffs[Puffs.Length] = H;
					Offset[Offset.Length] = O + vect(0,0,1) * R * 0.08;
					BankOf[BankOf.Length] = b;
				}
			}
			P.SetDrawScale(S);
			Puffs[Puffs.Length] = P;
			Offset[Offset.Length] = O;
			BankOf[BankOf.Length] = b;
		}
	}
	Log("Cards: clouds "$N$" banks, "$Puffs.Length$" puffs at "$int(Height));
}

event Tick(float DeltaTime)
{
	local int b, i;
	local vector C;

	for (b = 0; b < Bank.Length; b++)
	{
		C = Bank[b] + Drift * DeltaTime;
		// wrap round the island so the sky never empties
		if (C.X > Location.X + Spread) C.X -= 2 * Spread;
		if (C.X < Location.X - Spread) C.X += 2 * Spread;
		if (C.Y > Location.Y + Spread) C.Y -= 2 * Spread;
		if (C.Y < Location.Y - Spread) C.Y += 2 * Spread;
		Bank[b] = C;
	}
	for (i = 0; i < Puffs.Length; i++)
		if (Puffs[i] != None)
			Puffs[i].SetLocation(Bank[BankOf[i]] + Offset[i]);
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Puffs.Length; i++)
		if (Puffs[i] != None)
			Puffs[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
	bHidden=True
	RemoteRole=ROLE_None
}
