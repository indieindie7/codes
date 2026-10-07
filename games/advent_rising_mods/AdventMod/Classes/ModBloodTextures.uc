//=============================================================================
// ModBloodTextures - imports the procedural blood decals (Textures\make_blood.py)
// into AdventMod.u, group Blood: AdventMod.Blood.BloodSplat0 and so on (Alien*: the
// Seekers' purple).
//=============================================================================
class ModBloodTextures extends Object;

#exec TEXTURE IMPORT NAME=BloodSplat0 FILE=Textures\blood_splat0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSplat1 FILE=Textures\blood_splat1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSplat2 FILE=Textures\blood_splat2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSplat3 FILE=Textures\blood_splat3.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSpray0 FILE=Textures\blood_spray0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodSpray1 FILE=Textures\blood_spray1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPool0 FILE=Textures\blood_pool0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienSplat0 FILE=Textures\alien_splat0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienSplat1 FILE=Textures\alien_splat1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienSplat2 FILE=Textures\alien_splat2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienSplat3 FILE=Textures\alien_splat3.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienSpray0 FILE=Textures\alien_spray0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienSpray1 FILE=Textures\alien_spray1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPool0 FILE=Textures\alien_pool0.tga GROUP=Blood MIPS=1 ALPHA=1
// pools that spread like a liquid: frames of an offline shallow-water run (tools/make_blood_pool.py)
// footprints out of a pool and drip streaks on a hit body (tools/make_blood_marks.py)
#exec TEXTURE IMPORT NAME=FootprintH0 FILE=Textures\footprint_h0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintH1 FILE=Textures\footprint_h1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintH2 FILE=Textures\footprint_h2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintA0 FILE=Textures\footprint_a0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintA1 FILE=Textures\footprint_a1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintA2 FILE=Textures\footprint_a2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintHL0 FILE=Textures\footprint_hl0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintHL1 FILE=Textures\footprint_hl1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintHL2 FILE=Textures\footprint_hl2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintAL0 FILE=Textures\footprint_al0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintAL1 FILE=Textures\footprint_al1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=FootprintAL2 FILE=Textures\footprint_al2.tga GROUP=Blood MIPS=1 ALPHA=1
// plasma burns on walls: four frames from white-hot to cold soot (tools/make_blood_marks.py)
#exec TEXTURE IMPORT NAME=Burn0 FILE=Textures\burn0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Burn1 FILE=Textures\burn1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Burn2 FILE=Textures\burn2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Burn3 FILE=Textures\burn3.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DripsH FILE=Textures\drips_h.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DripsA FILE=Textures\drips_a.tga GROUP=Blood MIPS=1 ALPHA=1
// live pools: placeholders the d3d8 layer swaps for its simulated sheets (tools/make_blood_live.py)
#exec TEXTURE IMPORT NAME=BloodLive0 FILE=Textures\blood_live0.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive1 FILE=Textures\blood_live1.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive2 FILE=Textures\blood_live2.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive3 FILE=Textures\blood_live3.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive4 FILE=Textures\blood_live4.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive5 FILE=Textures\blood_live5.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive6 FILE=Textures\blood_live6.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodLive7 FILE=Textures\blood_live7.tga GROUP=Blood MIPS=0 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF0 FILE=Textures\blood_pool_f00.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF1 FILE=Textures\blood_pool_f01.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF2 FILE=Textures\blood_pool_f02.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF3 FILE=Textures\blood_pool_f03.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF4 FILE=Textures\blood_pool_f04.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF5 FILE=Textures\blood_pool_f05.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF6 FILE=Textures\blood_pool_f06.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF7 FILE=Textures\blood_pool_f07.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF8 FILE=Textures\blood_pool_f08.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF9 FILE=Textures\blood_pool_f09.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF10 FILE=Textures\blood_pool_f10.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodPoolF11 FILE=Textures\blood_pool_f11.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF0 FILE=Textures\alien_pool_f00.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF1 FILE=Textures\alien_pool_f01.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF2 FILE=Textures\alien_pool_f02.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF3 FILE=Textures\alien_pool_f03.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF4 FILE=Textures\alien_pool_f04.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF5 FILE=Textures\alien_pool_f05.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF6 FILE=Textures\alien_pool_f06.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF7 FILE=Textures\alien_pool_f07.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF8 FILE=Textures\alien_pool_f08.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF9 FILE=Textures\alien_pool_f09.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF10 FILE=Textures\alien_pool_f10.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienPoolF11 FILE=Textures\alien_pool_f11.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodRemains0 FILE=Textures\blood_remains0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodRemains1 FILE=Textures\blood_remains1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienRemains0 FILE=Textures\alien_remains0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienRemains1 FILE=Textures\alien_remains1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodMeat FILE=Textures\blood_meat.tga GROUP=Blood MIPS=1
#exec TEXTURE IMPORT NAME=AlienMeat FILE=Textures\alien_meat.tga GROUP=Blood MIPS=1
#exec TEXTURE IMPORT NAME=Scorch0 FILE=Textures\scorch0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Scorch1 FILE=Textures\scorch1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Scorch2 FILE=Textures\scorch2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=Casing0 FILE=Textures\casing0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodCoat0 FILE=Textures\blood_coat0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodCoat1 FILE=Textures\blood_coat1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodCoat2 FILE=Textures\blood_coat2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienCoat0 FILE=Textures\alien_coat0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienCoat1 FILE=Textures\alien_coat1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienCoat2 FILE=Textures\alien_coat2.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DirtGrime0 FILE=Textures\dirt_grime0.tga GROUP=Dirt MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DirtGrime1 FILE=Textures\dirt_grime1.tga GROUP=Dirt MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DirtCrack0 FILE=Textures\dirt_crack0.tga GROUP=Dirt MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DirtCrack1 FILE=Textures\dirt_crack1.tga GROUP=Dirt MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DirtRubble0 FILE=Textures\dirt_rubble0.tga GROUP=Dirt MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=DirtCrater1 FILE=Textures\dirt_crater1.tga GROUP=Dirt MIPS=1 ALPHA=1

defaultproperties
{
}
