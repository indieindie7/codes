//=============================================================================
// An invisible actor moved about to ask the engine which volume a point is in
// (AvalonCards.WaterTop: is it under the sea?).
//=============================================================================
class CardProbe extends Actor;

defaultproperties
{
	bHidden=True
	bStatic=False
	bNoDelete=False
	bCollideActors=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
