//=============================================================================
// GMLight - a light from the journal ("light X Y Z BRIGHT HUE SAT RADIUS"): a GM's
// own, an accepted co-GM proposal or the Sanctuary director's key light. At run
// time a dynamic light (the map's own are baked); gm commit bakes it into the map
// as a real Light (tools/gm_commit.py light_block).
//=============================================================================
class GMLight extends Actor;

function Set(float Bright, float Hue, float Sat, float Radius)
{
	LightBrightness = Bright;
	LightHue = Hue;
	LightSaturation = Sat;
	LightRadius = Radius;
}

defaultproperties
{
	bHidden=True
	bStatic=False
	bNoDelete=False
	bMovable=True
	bDynamicLight=True
	LightType=LT_Steady
	LightEffect=LE_None
	LightBrightness=150
	LightRadius=24
	LightHue=24
	LightSaturation=110
	RemoteRole=ROLE_None
}
