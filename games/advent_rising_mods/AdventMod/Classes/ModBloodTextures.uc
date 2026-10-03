//=============================================================================
// ModBloodTextures - imports the procedural blood decals (Textures\make_blood.py)
// into AdventMod.u, group Blood: AdventMod.Blood.BloodSplat0 and so on.
//=============================================================================
class ModBloodTextures extends Object;

#exec TEXTURE IMPORT NAME=BloodSplat0 FILE=Textures\blood_splat0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSplat1 FILE=Textures\blood_splat1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSplat2 FILE=Textures\blood_splat2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSplat3 FILE=Textures\blood_splat3.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSpray0 FILE=Textures\blood_spray0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSpray1 FILE=Textures\blood_spray1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPool0 FILE=Textures\blood_pool0.tga GROUP=Blood MIPS=1 ALPHA=1

defaultproperties
{
}
