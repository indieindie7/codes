// A shot's puff of dust and smoke where it lands on a wall or floor: a soft cloud that drifts
// out of the hole and grows as it fades, and a quick spray of grit. Small and short on purpose:
// a screen full of big see-through smoke is what costs the frame rate (grenade smoke), so these
// stay a hand's width and are gone in about a second and a half.
//
// The smoke texture is the stock game's own (fx_Default_SmokeB's), borrowed when it spawns.
class ModImpactPuff extends Emitter;

var Texture SmokeTex, GritTex;
var byte SmokeU, SmokeV;
var bool bLooked;

static function Texture FindTex(string Name)
{
	local Texture T;
	local array<string> Top, Sub;
	local int i, j;

	// the package's group names (its name table): Human and Seeker, then weapons, explosions, ...
	Top[0] = "";
	Top[1] = "Human.";
	Top[2] = "Seeker.";
	Sub[0] = "";
	Sub[1] = "weapons.";
	Sub[2] = "explosions.";
	Sub[3] = "environmental.";
	Sub[4] = "charred.";
	Sub[5] = "cloud.";
	for (i = 0; i < Top.Length && T == None; i++)
		for (j = 0; j < Sub.Length && T == None; j++)
			T = Texture(DynamicLoadObject("effects_tx." $ Top[i] $ Sub[j] $ Name, class'Texture', true));
	return T;
}

simulated function PostBeginPlay()
{
	local class<Emitter> C;
	local int i;
	local ParticleEmitter P;

	if (!default.bLooked)
	{
		default.bLooked = true;
		// the stock bullet smoke and rock debris sprites (effects_tx); the group they sit in isn't known, so try a few
		default.SmokeTex = FindTex("smokebullet");
		if (default.SmokeTex == None)
			default.SmokeTex = FindTex("smokebullet2");
		if (default.SmokeTex == None)
			default.SmokeTex = FindTex("smoketrans");
		if (default.SmokeTex == None)
			default.SmokeTex = FindTex("smokemist1");
		default.GritTex = FindTex("rockdebris");
		if (default.SmokeTex != None)
		{
			default.SmokeU = 1;
			default.SmokeV = 1;
		}
		C = class<Emitter>(DynamicLoadObject("EonEffects.fx_Default_SmokeB", class'Class', true));
		if (C != None)
			for (i = 0; i < C.default.Emitters.Length && default.SmokeTex == None; i++)
			{
				P = C.default.Emitters[i];
				if (P != None && P.Texture != None)
				{
					default.SmokeTex = P.Texture;
					default.SmokeU = P.TextureUSubdivisions;
					default.SmokeV = P.TextureVSubdivisions;
				}
			}
	}
	for (i = 0; i < Emitters.Length; i++)
		if (Emitters[i] != None && i == 1 && default.GritTex != None)
			Emitters[i].Texture = default.GritTex;
		else if (Emitters[i] != None)
		{
			Emitters[i].Texture = default.SmokeTex;
			Emitters[i].TextureUSubdivisions = default.SmokeU;
			Emitters[i].TextureVSubdivisions = default.SmokeV;
			Emitters[i].UseRandomSubdivision = default.SmokeU * default.SmokeV > 1;
		}
	Super.PostBeginPlay();
}

// out of the wall along its normal N, spread sideways; Tint is the dust's colour (0-255)
function Aim(vector N, color Tint, float Size)
{
	local int i, c;
	local float Lo, Hi, Spread;

	for (i = 0; i < Emitters.Length; i++)
	{
		if (Emitters[i] == None)
			continue;
		Lo = i == 0 ? 15.0 : 60.0;
		Hi = i == 0 ? 45.0 : 160.0;
		Spread = i == 0 ? 12.0 : 50.0;
		Emitters[i].StartVelocityRange.X.Min = N.X * Lo - Spread;
		Emitters[i].StartVelocityRange.X.Max = N.X * Hi + Spread;
		Emitters[i].StartVelocityRange.Y.Min = N.Y * Lo - Spread;
		Emitters[i].StartVelocityRange.Y.Max = N.Y * Hi + Spread;
		Emitters[i].StartVelocityRange.Z.Min = N.Z * Lo - Spread;
		Emitters[i].StartVelocityRange.Z.Max = N.Z * Hi + Spread;
		// set, not scaled: if the engine shares the emitters between puffs, scaling would add up
		Emitters[i].StartSizeRange.X.Min = (i == 0 ? 6.0 : 1.0) * Size;
		Emitters[i].StartSizeRange.X.Max = (i == 0 ? 9.0 : 1.8) * Size;
		for (c = 0; c < Emitters[i].ColorScale.Length; c++)
		{
			Emitters[i].ColorScale[c].Color.R = Tint.R;
			Emitters[i].ColorScale[c].Color.G = Tint.G;
			Emitters[i].ColorScale[c].Color.B = Tint.B;
		}
	}
}

defaultproperties
{
	Begin Object Class=SpriteEmitter Name=PuffSmoke
		UseColorScale=True
		ColorScale(0)=(RelativeTime=0.000000,Color=(R=110,G=105,B=98,A=0))
		ColorScale(1)=(RelativeTime=0.120000,Color=(R=110,G=105,B=98,A=160))
		ColorScale(2)=(RelativeTime=1.000000,Color=(R=110,G=105,B=98,A=0))
		MaxParticles=3
		RespawnDeadParticles=False
		AutomaticInitialSpawning=False
		InitialParticlesPerSecond=2000.000000
		StartLocationRange=(X=(Min=-2.000000,Max=2.000000),Y=(Min=-2.000000,Max=2.000000),Z=(Min=-2.000000,Max=2.000000))
		Acceleration=(Z=10.000000)
		VelocityLossRange=(X=(Min=2.500000,Max=3.000000),Y=(Min=2.500000,Max=3.000000),Z=(Min=2.500000,Max=3.000000))
		SpinParticles=True
		StartSpinRange=(X=(Min=0.000000,Max=1.000000))
		SpinsPerSecondRange=(X=(Min=-0.150000,Max=0.150000))
		UseSizeScale=True
		UseRegularSizeScale=False
		SizeScale(0)=(RelativeTime=0.000000,RelativeSize=0.500000)
		SizeScale(1)=(RelativeTime=1.000000,RelativeSize=2.300000)
		StartSizeRange=(X=(Min=6.000000,Max=9.000000))
		LifetimeRange=(Min=1.000000,Max=1.500000)
		DrawStyle=PTDS_AlphaBlend
		Name="PuffSmoke"
	End Object
	Emitters(0)=SpriteEmitter'PuffSmoke'
	Begin Object Class=SpriteEmitter Name=PuffGrit
		UseColorScale=True
		ColorScale(0)=(RelativeTime=0.000000,Color=(R=110,G=105,B=98,A=200))
		ColorScale(1)=(RelativeTime=1.000000,Color=(R=110,G=105,B=98,A=0))
		MaxParticles=6
		RespawnDeadParticles=False
		AutomaticInitialSpawning=False
		InitialParticlesPerSecond=2000.000000
		Acceleration=(Z=-400.000000)
		VelocityLossRange=(X=(Min=1.000000,Max=1.500000),Y=(Min=1.000000,Max=1.500000),Z=(Min=1.000000,Max=1.500000))
		StartSizeRange=(X=(Min=1.000000,Max=1.800000))
		LifetimeRange=(Min=0.300000,Max=0.550000)
		DrawStyle=PTDS_AlphaBlend
		Name="PuffGrit"
	End Object
	Emitters(1)=SpriteEmitter'PuffGrit'
	AutoDestroy=True
	bNoDelete=False
	LifeSpan=3.000000
}
