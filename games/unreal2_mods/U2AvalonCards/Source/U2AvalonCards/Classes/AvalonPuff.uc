//=============================================================================
// AvalonPuff - one sprite of an AvalonPlume (smoke, steam or flame). The plume
// moves, grows and fades it; it has no behaviour of its own.
//=============================================================================
class AvalonPuff extends Actor;

// soft puffs with clean (empty) borders: tools\make_puffs.py
#exec TEXTURE IMPORT NAME=SteamPuff FILE=Textures\SteamPuff.tga MIPS=On UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=SmokePuff FILE=Textures\SmokePuff.tga MIPS=On ALPHA=1 UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

var float Age, Life, Size0, Grow, Glow;
var vector Start, Drift;

defaultproperties
{
	DrawType=DT_Sprite
	bStatic=False
	bUnlit=True
	bCollideActors=False
	bBlockActors=False
	bBlockPlayers=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
	Style=STY_Translucent
}
