//=============================================================================
// ModArmorTextures - the region masks of the destructible armour (ModArmor phase 3), in
// the skin's UV space, white with the region in the alpha, made by tools/make_armor_masks.py
// from the character's own mesh (the faces of each plate's bones). One texture per SET of
// broken plates (bits: 1 head, 2 torso, 4 arms, 8 legs; left and right limbs share texels
// on these meshes), so the flesh is one Combiner stage over the skin: a combiner inside a
// combiner drew the whole Seeker as a flat colour, and so did a separate mask texture: the
// texture carries the flesh colour AND the region alpha and serves as Material2 and Mask.
//=============================================================================
class ModArmorTextures extends Object;


#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m01 FILE=Textures\armor_seekerinfantry_m01.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m02 FILE=Textures\armor_seekerinfantry_m02.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m03 FILE=Textures\armor_seekerinfantry_m03.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m04 FILE=Textures\armor_seekerinfantry_m04.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m05 FILE=Textures\armor_seekerinfantry_m05.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m06 FILE=Textures\armor_seekerinfantry_m06.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m07 FILE=Textures\armor_seekerinfantry_m07.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m08 FILE=Textures\armor_seekerinfantry_m08.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m09 FILE=Textures\armor_seekerinfantry_m09.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m10 FILE=Textures\armor_seekerinfantry_m10.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m11 FILE=Textures\armor_seekerinfantry_m11.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m12 FILE=Textures\armor_seekerinfantry_m12.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m13 FILE=Textures\armor_seekerinfantry_m13.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m14 FILE=Textures\armor_seekerinfantry_m14.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_m15 FILE=Textures\armor_seekerinfantry_m15.tga GROUP=Armor MIPS=1 ALPHA=1

struct MaskSet
{
	var name Set;                 // the gib set (ModGibParts) the masks belong to
	var Material Meat[16];        // the same with the flesh baked in (colour = meat x region, alpha = region)
};
var array<MaskSet> Sets;

// the bits of a region (ModArmor's order: head, torso, left arm, right arm, left leg, right leg)
static function int RegionBit(int r)
{
	switch (r)
	{
	case 0: return 1;
	case 1: return 2;
	case 2: return 4;
	case 3: return 4;
	}
	return 8;
}

defaultproperties
{
     Sets(0)=(Set=seekerinfantry,Meat[1]=Texture'AdventMod.Armor.Armor_seekerinfantry_m01',Meat[2]=Texture'AdventMod.Armor.Armor_seekerinfantry_m02',Meat[3]=Texture'AdventMod.Armor.Armor_seekerinfantry_m03',Meat[4]=Texture'AdventMod.Armor.Armor_seekerinfantry_m04',Meat[5]=Texture'AdventMod.Armor.Armor_seekerinfantry_m05',Meat[6]=Texture'AdventMod.Armor.Armor_seekerinfantry_m06',Meat[7]=Texture'AdventMod.Armor.Armor_seekerinfantry_m07',Meat[8]=Texture'AdventMod.Armor.Armor_seekerinfantry_m08',Meat[9]=Texture'AdventMod.Armor.Armor_seekerinfantry_m09',Meat[10]=Texture'AdventMod.Armor.Armor_seekerinfantry_m10',Meat[11]=Texture'AdventMod.Armor.Armor_seekerinfantry_m11',Meat[12]=Texture'AdventMod.Armor.Armor_seekerinfantry_m12',Meat[13]=Texture'AdventMod.Armor.Armor_seekerinfantry_m13',Meat[14]=Texture'AdventMod.Armor.Armor_seekerinfantry_m14',Meat[15]=Texture'AdventMod.Armor.Armor_seekerinfantry_m15')
}
