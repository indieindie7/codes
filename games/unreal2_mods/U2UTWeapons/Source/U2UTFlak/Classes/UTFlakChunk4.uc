//=============================================================================
// UTFlakChunk4 - flak chunk shape 4 (UT's UTChunk4).
//=============================================================================
class UTFlakChunk4 extends UTFlakChunk;

#exec MESH IMPORT MESH=chunk4M ANIVFILE=Models\chunk4M_a.3d DATAFILE=Models\chunk4M_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=chunk4M X=0 Y=0 Z=0 PITCH=0
#exec MESH SEQUENCE MESH=chunk4M SEQ=All STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH=chunk4M SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec MESHMAP SCALE MESHMAP=chunk4M X=0.03 Y=0.03 Z=0.06

defaultproperties
{
	Mesh=VertMesh'chunk4M'
	DrawType=DT_StaticMesh
	MeshName="U2UTFlakSM.Chunks.chunk4M"
	LifeSpan=3.000000
}
