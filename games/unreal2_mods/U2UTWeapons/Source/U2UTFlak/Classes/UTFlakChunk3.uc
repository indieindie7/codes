//=============================================================================
// UTFlakChunk3 - flak chunk shape 3 (UT's UTChunk3).
//=============================================================================
class UTFlakChunk3 extends UTFlakChunk;

#exec MESH IMPORT MESH=chunk3M ANIVFILE=Models\chunk3M_a.3d DATAFILE=Models\chunk3M_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=chunk3M X=0 Y=0 Z=0 PITCH=0
#exec MESH SEQUENCE MESH=chunk3M SEQ=All STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH=chunk3M SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec MESHMAP SCALE MESHMAP=chunk3M X=0.03 Y=0.03 Z=0.06

defaultproperties
{
	Mesh=VertMesh'chunk3M'
	DrawType=DT_StaticMesh
	MeshName="U2UTFlakSM.Chunks.chunk3M"
}
