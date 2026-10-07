//=============================================================================
// AvalonFlicker - a failing lamp: the Authority's landing pad light, the only
// Authority hardware outside the tower, left to die (binder: Vask "treats it
// like a border", parts at company prices). A dynamic light that is on, then
// stutters, then goes out for a while, with a buzz of sparks.
// Spawned and configured by AvalonCards (Decay* keys).
//=============================================================================
class AvalonFlicker extends Actor;

var float NextChange;
var int Mode;               // 0 on, 1 stutter, 2 dead

function Begin(Sound Buzz)
{
	AmbientSound = Buzz;
	SoundVolume = 120;
	SoundRadius = 40;
	NextChange = Level.TimeSeconds + 2;
}

event Tick(float DeltaTime)
{
	if (Level.TimeSeconds >= NextChange)
	{
		Mode = Rand(3);
		if (Mode == 0)
			NextChange = Level.TimeSeconds + 1 + FRand() * 4;
		else if (Mode == 1)
			NextChange = Level.TimeSeconds + 0.5 + FRand() * 2;
		else
			NextChange = Level.TimeSeconds + 2 + FRand() * 8;
	}
	if (Mode == 0)
		LightBrightness = 170;
	else if (Mode == 1)
		LightBrightness = 30 + Rand(180);
	else
		LightBrightness = 0;
	if (Mode == 2)
		SoundVolume = 0;
	else
		SoundVolume = 120;
}

defaultproperties
{
	DrawType=DT_None
	bHidden=False
	bStatic=False
	bCollideActors=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
	bDynamicLight=True
	LightType=LT_Steady
	LightEffect=LE_None
	LightBrightness=170
	LightHue=30
	LightSaturation=150
	LightRadius=24
}
