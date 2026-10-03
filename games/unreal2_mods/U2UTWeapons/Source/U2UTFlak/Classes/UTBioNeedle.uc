//=============================================================================
// UTBioNeedle - the red pointer of the Bio Rifle's goo gauge. Never drawn in the
// world (bHidden); WeaponInvUTBio draws it on top of the first-person gun each
// frame, turned by how much ammo is left.
//=============================================================================
class UTBioNeedle extends Actor;

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = StaticMesh(DynamicLoadObject("U2UTFlakSM.Bio.BioNeedle", class'StaticMesh'));
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bHidden=True
	RemoteRole=ROLE_None
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	bUnlit=True
	Skins(0)=Texture'BioAtlas'
	DrawScale=0.100000
}
