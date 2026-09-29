//=============================================================================
// UTFlakChunk1 - flak chunk shape 1 (UT's UTChunk1).
//=============================================================================
class UTFlakChunk1 extends UTFlakChunk;

#exec MESH IMPORT MESH=chunkM ANIVFILE=Models\chunkM_a.3d DATAFILE=Models\chunkM_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=chunkM X=0 Y=0 Z=0 PITCH=0
#exec MESH SEQUENCE MESH=chunkM SEQ=All STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH=chunkM SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec MESHMAP SCALE MESHMAP=chunkM X=0.03 Y=0.03 Z=0.06

defaultproperties
{
	Mesh=VertMesh'chunkM'
	DrawType=DT_StaticMesh
	MeshName="U2UTFlakSM.Chunks.chunkM"
}
