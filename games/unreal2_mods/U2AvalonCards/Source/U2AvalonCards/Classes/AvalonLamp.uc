//=============================================================================
// AvalonLamp - a low recessed wall light at floor level (the user, 2026-10-08:
// "add some lights in the floor corners like they were recessions in the
// wall"): a steady dynamic light (no map rebuild) plus a small warm glow
// sprite set into the wall. Placed by AvalonCards' Lamps[] lines, which trace
// out from a point to the walls round it.
//=============================================================================
class AvalonLamp extends Actor;

var AvalonPuff Glow;

function Setup(float Radius, byte Hue, byte Sat, byte Bright, Texture GlowTex)
{
	LightRadius = Radius;
	LightHue = Hue;
	LightSaturation = Sat;
	LightBrightness = Bright;
	if (GlowTex != None)
	{
		Glow = Spawn(class'AvalonPuff',,, Location);
		if (Glow != None)
		{
			Glow.Texture = GlowTex;
			Glow.Style = STY_Translucent;
			Glow.SetDrawScale(0.35);
		}
	}
}

event Destroyed()
{
	if (Glow != None)
		Glow.Destroy();
	Super.Destroyed();
}

defaultproperties
{
	DrawType=DT_None
	bHidden=False
	bStatic=False
	bNoDelete=False
	bCollideActors=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
	bDynamicLight=True
	LightType=LT_Steady
	LightEffect=LE_None
	LightBrightness=150
	LightHue=28
	LightSaturation=110
	LightRadius=9
}
