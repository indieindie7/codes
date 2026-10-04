//=============================================================================
// ModDeathAnims - imports the death clips (ModReact plays one, then the body goes
// ragdoll partway through). The .psa is written at build time by tools/make_psa.py
// from the game's own skeleton (bone names and offsets), so it isn't in the repo.
//=============================================================================
class ModDeathAnims extends Object;

#exec ANIM IMPORT ANIM=ModDeaths ANIMFILE=Anims\ModDeaths.psa COMPRESS=1 MAXKEYS=999999 IMPORTSEQS=1
#exec ANIM DIGEST ANIM=ModDeaths USERAWINFO VERBOSE

var MeshAnimation Deaths;

defaultproperties
{
     Deaths=MeshAnimation'AdventMod.ModDeaths'
}
