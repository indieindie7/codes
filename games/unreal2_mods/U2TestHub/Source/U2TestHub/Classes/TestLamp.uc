//=============================================================================
// TestLamp - a bright spawnable lamp (U2TestHub) for judging character shadows in a known
// setup (test tool): spawn it near a character and U2SoftShadows picks it up
// as a moving light. Brightness/radius can be changed with the pilot's
// console "set" if needed.
//=============================================================================
class TestLamp extends Actor;

defaultproperties
{
	LightType=LT_Steady
	LightEffect=LE_None
	LightBrightness=220
	LightRadius=24
	LightHue=30
	LightSaturation=200
	bDynamicLight=True
	bHidden=True
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	RemoteRole=ROLE_None
}
