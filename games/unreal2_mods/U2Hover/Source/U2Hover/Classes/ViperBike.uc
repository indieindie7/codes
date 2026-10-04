//=============================================================================
// ViperBike - the HoverBike wearing UT3's Necris Viper (VH_NecrisManta).
// Same hover physics and guns; only the look and the size differ.
// Mesh and skin live in StaticMeshes\U2HoverSM.usx (group Viper), imported by
// U2Hover\import_ut3.py from the UT3 extract (Epic's art: private, not shipped).
//=============================================================================
class ViperBike extends HoverBike
	placeable;

defaultproperties
{
	BodyMesh="U2HoverSM.Viper.ViperBody"
	BodySkin="U2HoverSM.Viper.ViperSkin"
	DrawScale=1.000000
	CollisionRadius=110.000000
	CollisionHeight=42.000000
	bNoStaticMeshCollide=True   // the imported mesh has no collision BSP: use the cylinder (board by walking into it)
	GunOffset=(X=120.000000,Y=50.000000,Z=0.000000)
	Repulsor(0)=(X=110.000000,Z=-7.000000)
	Repulsor(1)=(X=-60.000000,Y=55.000000,Z=-7.000000)
	Repulsor(2)=(X=-60.000000,Y=-55.000000,Z=-7.000000)
}
