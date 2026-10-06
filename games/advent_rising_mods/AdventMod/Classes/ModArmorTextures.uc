//=============================================================================
// ModArmorTextures - the region masks of the destructible armour (ModArmor phase 3):
// one per plate, in the skin's UV space, white with the region in the alpha, made by
// tools/make_armor_masks.py from the character's own mesh (the faces of each plate's
// bones). ModArmor blends the flesh over the skin through the mask of a broken plate.
//=============================================================================
class ModArmorTextures extends Object;

#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_head FILE=Textures\armor_seekerinfantry_head.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_torso FILE=Textures\armor_seekerinfantry_torso.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_l_arm FILE=Textures\armor_seekerinfantry_l_arm.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_r_arm FILE=Textures\armor_seekerinfantry_r_arm.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_l_leg FILE=Textures\armor_seekerinfantry_l_leg.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_r_leg FILE=Textures\armor_seekerinfantry_r_leg.tga GROUP=Armor MIPS=1 ALPHA=1

struct MaskSet
{
	var name Set;                 // the gib set (ModGibParts) the masks belong to
	var Material Masks[6];        // head, torso, left arm, right arm, left leg, right leg
};
var array<MaskSet> Sets;

defaultproperties
{
     Sets(0)=(Set=seekerinfantry,Masks[0]=Texture'AdventMod.Armor.Armor_seekerinfantry_head',Masks[1]=Texture'AdventMod.Armor.Armor_seekerinfantry_torso',Masks[2]=Texture'AdventMod.Armor.Armor_seekerinfantry_l_arm',Masks[3]=Texture'AdventMod.Armor.Armor_seekerinfantry_r_arm',Masks[4]=Texture'AdventMod.Armor.Armor_seekerinfantry_l_leg',Masks[5]=Texture'AdventMod.Armor.Armor_seekerinfantry_r_leg')
}
