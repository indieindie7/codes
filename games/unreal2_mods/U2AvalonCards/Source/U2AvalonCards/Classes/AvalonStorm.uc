//=============================================================================
// AvalonStorm - a storm over the map: the outdoor zones' fog pulled in and
// darkened, rain falling round the player (recycled streaks, none where a roof
// is overhead), rain and wind loops, and lightning: a white flash on the
// screen and in the fog, then thunder a few seconds later, nearer = sooner.
// Engine only: zone fog, sprites, PlayerController.ClientFlash, ambient
// sounds. Spawned and configured by AvalonCards (Storm* keys).
//=============================================================================
class AvalonStorm extends Actor;

#exec TEXTURE IMPORT NAME=RainStreak FILE=Textures\RainStreak.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

var array<AvalonPuff> Drops;
var array<AvalonPuff> Clouds;   // the overcast: giant dark puffs round and over the player, greyed by the fog
var array<vector> CloudAt;
var float CloudTurn;
var float Radius, Fall, Top;
var vector Wind;
var array<ZoneInfo> Zones;
var array<color> ZoneColour;
var color FogColour, FlashColour;
var float NextBolt, ThunderAt, Flash;
var Sound Thunder[5];
var int NThunder;
var Actor WindSnd;
var float Gloom;          // the whole view darkened by this much (0..1) and greyed: the sky box ignores fog
var vector GloomFog;
var PlayerController Gloomed;

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
	FlashColour.R = 230;
	FlashColour.G = 235;
	FlashColour.B = 255;
	foreach AllActors(class'ZoneInfo', Z)
		if (Z.bDistanceFog)
		{
			Z.DistanceFogStart = FogStart;
			Z.DistanceFogEnd = FogEnd;
			Z.DistanceFogColor = Fog;
			Zones[Zones.Length] = Z;
		}
		else if (Z.IsA('SkyZoneInfo') && SkyFogEnd > 0)
		{
			// the sky box is a small room seen from its middle: fog it nearly through to grey
			// (the painted sun and blue sky would say "fine weather" over everything else)
			Z.bDistanceFog = True;
			Z.DistanceFogStart = 0;
			Z.DistanceFogEnd = SkyFogEnd;
			Z.DistanceFogColor = Fog;
			Zones[Zones.Length] = Z;
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
	SoundVolume = 190;
	SoundRadius = 255;
	if (WindLoop != None)
	{
		WindSnd = Spawn(class'AvalonPuff',,, Location);
		if (WindSnd != None)
		{
			WindSnd.bHidden = True;
			WindSnd.AmbientSound = WindLoop;
			WindSnd.SoundVolume = 160;
			WindSnd.SoundRadius = 255;
		}
	}
	NextBolt = Level.TimeSeconds + 4;
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
// when something is overhead (indoors, under a deck)
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
	P.bHidden = !FastTrace(S + vect(0,0,6000), S);
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
	// the storm light over the whole view (PlayerController's constant glow), once per player controller
	if (Gloom > 0 && Level.PlayerControllerList != None && Level.PlayerControllerList != Gloomed)
	{
		Gloomed = Level.PlayerControllerList;
		Gloomed.ClientAdjustGlow(-Gloom, GloomFog);
	}
	if (WindSnd != None)
		WindSnd.SetLocation(E);
	// the cloud deck turns slowly round the player (the clouds move with the wind)
	CloudTurn += DeltaTime * 0.004;
	Spin.Yaw = int(CloudTurn * 10430.4);      // radians -> rotator units
	for (i = 0; i < Clouds.Length; i++)
		if (Clouds[i] != None)
			Clouds[i].SetLocation(E + (CloudAt[i] >> Spin));
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
	// lightning: a flash now, the thunder later
	if (Level.TimeSeconds >= NextBolt)
	{
		Bolt();
		NextBolt = Level.TimeSeconds + 7 + FRand() * 14;
	}
	if (Flash > 0)
	{
		Flash -= DeltaTime;
		F = FClamp(Flash / 0.35, 0, 1);
		if (FRand() < 0.15)
			F *= 0.3;                             // the flicker of a real bolt
		SetFog(F);
	}
	if (ThunderAt > 0 && Level.TimeSeconds >= ThunderAt)
	{
		ThunderAt = 0;
		if (NThunder > 0)
			PlaySound(Thunder[Rand(NThunder)], SLOT_None, 2.0, false, 60000);
	}
}

function SetFog(float F)
{
	local int i;
	local color C;

	C.R = FogColour.R + (FlashColour.R - FogColour.R) * F;
	C.G = FogColour.G + (FlashColour.G - FogColour.G) * F;
	C.B = FogColour.B + (FlashColour.B - FogColour.B) * F;
	for (i = 0; i < Zones.Length; i++)
		if (Zones[i] != None)
			Zones[i].DistanceFogColor = C;
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

	if (Gloomed != None)
		Gloomed.ClientAdjustGlow(Gloom, -GloomFog);
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
