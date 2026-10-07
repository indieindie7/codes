//=============================================================================
// ModGibCard - a snapshot of settled gibs lying on the floor (an impostor): a flat quad
// (tools/make_gib_card.py) showing one tile of ModGibAtlas's runtime atlas, unlit (the
// snapshot already has the level's light in it), with a soft ragged edge from its mask.
// ModGibAtlas makes it, takes the snapshot, then raises it to the floor and removes the gibs.
//=============================================================================
class ModGibCard extends Actor;

#exec NEW StaticMesh FILE=Gibs\gib_card.ase NAME=GibCard GROUP=Gibs
#exec TEXTURE IMPORT NAME=GibCardMask FILE=Textures\gib_card_mask.tga GROUP=Gibs MIPS=1 ALPHA=1

var int Tile;
var float Width;          // its size once the snapshot is in
var Material Mask;
var TexScaler Scaler;
var Combiner Comb;
var FinalBlend Final;

defaultproperties
{
     Mask=Texture'AdventMod.Gibs.GibCardMask'
     DrawType=DT_StaticMesh
     StaticMesh=StaticMesh'AdventMod.Gibs.GibCard'
     bUnlit=True
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bProjTarget=False
     bAcceptsProjectors=False
     bStatic=False
     bNoDelete=False
     RemoteRole=ROLE_None
}
