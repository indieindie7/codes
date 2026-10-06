//=============================================================================
// ModArmorTextures - the region masks of the destructible armour (ModArmor phase 3), in
// the skin's UV space, white with the region in the alpha, made by tools/make_armor_masks.py
// from the character's own mesh (the faces of each plate's bones). One texture per SET of
// broken plates (bits: 1 head, 2 torso, 4 arms, 8 legs; left and right limbs share texels
// on these meshes), so the flesh is one Combiner stage over the skin: a combiner inside a
// combiner drew the whole Seeker as a flat colour.
//=============================================================================
class ModArmorTextures extends Object;

#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c01 FILE=Textures\armor_seekerinfantry_c01.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c02 FILE=Textures\armor_seekerinfantry_c02.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c03 FILE=Textures\armor_seekerinfantry_c03.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c04 FILE=Textures\armor_seekerinfantry_c04.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c05 FILE=Textures\armor_seekerinfantry_c05.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c06 FILE=Textures\armor_seekerinfantry_c06.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c07 FILE=Textures\armor_seekerinfantry_c07.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c08 FILE=Textures\armor_seekerinfantry_c08.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c09 FILE=Textures\armor_seekerinfantry_c09.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c10 FILE=Textures\armor_seekerinfantry_c10.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c11 FILE=Textures\armor_seekerinfantry_c11.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c12 FILE=Textures\armor_seekerinfantry_c12.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c13 FILE=Textures\armor_seekerinfantry_c13.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c14 FILE=Textures\armor_seekerinfantry_c14.tga GROUP=Armor MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Armor_seekerinfantry_c15 FILE=Textures\armor_seekerinfantry_c15.tga GROUP=Armor MIPS=1 ALPHA=1

struct MaskSet
{
	var name Set;                 // the gib set (ModGibParts) the masks belong to
	var Material Combos[16];      // by the broken-plate bits (0 unused)
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
     Sets(0)=(Set=seekerinfantry,Combos[1]=Texture'AdventMod.Armor.Armor_seekerinfantry_c01',Combos[2]=Texture'AdventMod.Armor.Armor_seekerinfantry_c02',Combos[3]=Texture'AdventMod.Armor.Armor_seekerinfantry_c03',Combos[4]=Texture'AdventMod.Armor.Armor_seekerinfantry_c04',Combos[5]=Texture'AdventMod.Armor.Armor_seekerinfantry_c05',Combos[6]=Texture'AdventMod.Armor.Armor_seekerinfantry_c06',Combos[7]=Texture'AdventMod.Armor.Armor_seekerinfantry_c07',Combos[8]=Texture'AdventMod.Armor.Armor_seekerinfantry_c08',Combos[9]=Texture'AdventMod.Armor.Armor_seekerinfantry_c09',Combos[10]=Texture'AdventMod.Armor.Armor_seekerinfantry_c10',Combos[11]=Texture'AdventMod.Armor.Armor_seekerinfantry_c11',Combos[12]=Texture'AdventMod.Armor.Armor_seekerinfantry_c12',Combos[13]=Texture'AdventMod.Armor.Armor_seekerinfantry_c13',Combos[14]=Texture'AdventMod.Armor.Armor_seekerinfantry_c14',Combos[15]=Texture'AdventMod.Armor.Armor_seekerinfantry_c15')
}
