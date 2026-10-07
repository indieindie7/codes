//=============================================================================
// ModArmorPlate - one armour plate worn on a bone (the armour rebuild, ARMOUR.md): our own
// mesh and metal texture (tools/make_plates.py), attached with AttachToBone so it follows the
// animation, scaled to the character. ModArmor places it from the body's facing when the
// character is first seen, swaps to the dented texture when the plate is down to half, and
// on a break detaches it and throws a loose copy (ModRubble's fake physics).
//=============================================================================
class ModArmorPlate extends Actor;

#exec NEW StaticMesh FILE=Gibs\plate_chest.ase NAME=PlateChest GROUP=Armor
#exec NEW StaticMesh FILE=Gibs\plate_helmet.ase NAME=PlateHelmet GROUP=Armor
#exec NEW StaticMesh FILE=Gibs\plate_shoulder.ase NAME=PlateShoulder GROUP=Armor
#exec NEW StaticMesh FILE=Gibs\plate_thigh.ase NAME=PlateThigh GROUP=Armor
#exec TEXTURE IMPORT NAME=PlateMetal FILE=Textures\plate_metal.tga GROUP=Armor MIPS=1
#exec TEXTURE IMPORT NAME=PlateDented FILE=Textures\plate_dented.tga GROUP=Armor MIPS=1

var Pawn Wearer;
var int Region;            // ModArmor's region (0 head .. 5 right leg)
var name Bone;
var bool bDented;
var StaticMesh Shapes[4];  // chest, helmet, shoulder, thigh
var Material Metal, Dented;

defaultproperties
{
     Shapes(0)=StaticMesh'AdventMod.Armor.PlateChest'
     Shapes(1)=StaticMesh'AdventMod.Armor.PlateHelmet'
     Shapes(2)=StaticMesh'AdventMod.Armor.PlateShoulder'
     Shapes(3)=StaticMesh'AdventMod.Armor.PlateThigh'
     Metal=Texture'AdventMod.Armor.PlateMetal'
     Dented=Texture'AdventMod.Armor.PlateDented'
     DrawType=DT_StaticMesh
     StaticMesh=StaticMesh'AdventMod.Armor.PlateChest'
     Skins(0)=Texture'AdventMod.Armor.PlateMetal'
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bProjTarget=False
     bAcceptsProjectors=False
     bStatic=False
     bNoDelete=False
     bHardAttach=True
     bUnlit=False
     RemoteRole=ROLE_None
}
