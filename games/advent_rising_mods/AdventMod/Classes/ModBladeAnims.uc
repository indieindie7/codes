//=============================================================================
// ModBladeAnims - the energy blade's swings: clips generated with Kimodo
// (tools/blade_prompts.txt, tools/kimodo_blade.sh), retargeted onto the human skeleton
// (tools/kimodo_retarget.py) and written as a .psa (tools/make_psa.py ... AnimsBlade).
// ModMelee plays one on an upper-body channel over the game's own punch move, so the
// game keeps its timing, footwork and hit checks while the arm swings the blade.
//=============================================================================
class ModBladeAnims extends Object;

#exec ANIM IMPORT ANIM=ModBladeSwings ANIMFILE=Anims\ModBladeSwings.psa COMPRESS=1 MAXKEYS=999999 IMPORTSEQS=1
#exec ANIM DIGEST ANIM=ModBladeSwings USERAWINFO VERBOSE

var MeshAnimation Swings;

defaultproperties
{
     Swings=MeshAnimation'AdventMod.ModBladeSwings'
}
