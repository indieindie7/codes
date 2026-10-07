//=============================================================================
// ModHoundAnims - the Seeker hound's own knockdowns, get-ups and deaths, keyed by hand for
// its four-legged skeleton (tools/make_hound_clips.py, written as a .psa by tools/make_psa.py
// at build time). The game links the whole Seeker animation set to the hound as well, so it
// "has" the upright Seekers' Death_Impact and GetUp clips, which fold its body wrong;
// ModReact plays these instead.
//=============================================================================
class ModHoundAnims extends Object;

#exec ANIM IMPORT ANIM=ModHound ANIMFILE=Anims\ModHound.psa COMPRESS=1 MAXKEYS=999999 IMPORTSEQS=1
#exec ANIM DIGEST ANIM=ModHound USERAWINFO VERBOSE

var MeshAnimation Clips;

defaultproperties
{
     Clips=MeshAnimation'AdventMod.ModHound'
}
