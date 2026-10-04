//=============================================================================
// ModStump - the meat cap on the body where a limb or head was cut off (ModSever):
// a small lumpy blob (Meshes\stump.ase, tools/make_stump.py) attached to the bone above
// the cut. It goes when the pawn does, or when the game brings the pawn back to life.
//=============================================================================
class ModStump extends Actor;

#exec NEW StaticMesh FILE=Gibs\stump.ase NAME=Stump GROUP=Gibs

defaultproperties
{
     DrawType=DT_StaticMesh
     StaticMesh=StaticMesh'AdventMod.Gibs.Stump'
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bHardAttach=True
     RemoteRole=ROLE_None
}
