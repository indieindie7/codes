//=============================================================================
// A key light the director (the creative team's DIRECTOR role) adds: a low warm
// light on the spot where the first creature stands, so the reveal is lit and the
// approach dark (Unreal 1's first Skaarj). A dynamic light: the map's own lights
// are baked.
//=============================================================================
class SanctuaryLight extends Actor;

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
