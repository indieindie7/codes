//=============================================================================
// ModJiggleMesh - the Seeker infantry re-rigged with ten jiggle bones (JIGGLE.md). The .psk is
// written at build time by tools/jiggle_rig.py from the game's own mesh (so it isn't in the
// repo; build.ps1 copies it from Documents\AdventRising_meshes\jiggle into <game>\AdventMod\Meshes).
// Same points, faces, UVs and material slot as Seekers.seekerinfantry, the same 78 bones in the
// same order plus J_Belly, J_Chest, J_Hump, J_Throat, J_ArmR, J_ArmL, J_FrontArmR, J_FrontArmL,
// J_ThighR, J_ThighL as leaves at their parents' joints; the origin and rotation are the stock
// mesh's (origin 0 -89 0, yaw -64 roll 64 in 1/256 turns, scale 1, the bounding box, all read
// from seekers.ukx; the first import without SCALE came out with scale 0 and a zero box). The
// importer negates Y and reverses the winding, so the .psk it gets is pre-flipped
// (seekerinfantry_jiggle_import.psk) and the stock data comes out the other side.
// The game's animation sets (Seekers.Base, Reactions, Targeting and the mesh's own ambient set)
// have no track for the J_ bones, so those sit at the reference pose until the DLL turns them.
//=============================================================================
class ModJiggleMesh extends Object;

#exec MESH MODELIMPORT MESH=SeekerInfantryJ MODELFILE=Meshes\seekerinfantry_jiggle.psk LODSTYLE=10
#exec MESH ORIGIN MESH=SeekerInfantryJ X=0 Y=-89 Z=0 PITCH=0 YAW=-64 ROLL=64
#exec MESHMAP SCALE MESHMAP=SeekerInfantryJ X=1 Y=1 Z=1
#exec MESH BOUNDINGBOX MESH=SeekerInfantryJ XMIN=-130 YMIN=-290 ZMIN=-60 XMAX=112 YMAX=30 ZMAX=80

var SkeletalMesh JiggleMesh;

defaultproperties
{
     JiggleMesh=SkeletalMesh'AdventMod.SeekerInfantryJ'
}
