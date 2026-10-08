//=============================================================================
// An invisible point GoreManager moves about to ask the level what volume a spot
// is in (moving an actor sets its PhysicsVolume): no blood marks under water
// (ADVENT-GORE-HANDOFF.md: projectors land on the floor under the water).
//=============================================================================
class GoreProbe extends Info;

defaultproperties
{
	bHidden=True
	bCollideActors=False
	bCollideWorld=False
	RemoteRole=ROLE_None
}
