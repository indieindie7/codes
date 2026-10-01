//=============================================================================
// UTFlakChunk2 - flak chunk shape 2 (UT's UTChunk2).
//=============================================================================
class UTFlakChunk2 extends UTFlakChunk;

#exec MESH IMPORT MESH=chunk2M ANIVFILE=Models\chunk2M_a.3d DATAFILE=Models\chunk2M_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=chunk2M X=0 Y=0 Z=0 PITCH=0
#exec MESH SEQUENCE MESH=chunk2M SEQ=All STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH=chunk2M SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec MESHMAP SCALE MESHMAP=chunk2M X=0.03 Y=0.03 Z=0.06

defaultproperties
{
	Mesh=VertMesh'chunk2M'
	DrawType=DT_StaticMesh
	MeshName="U2UTFlakSM.Chunks.chunk2M"
	LifeSpan=3.100000
}
