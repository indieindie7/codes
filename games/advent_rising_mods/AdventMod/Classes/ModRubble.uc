//=============================================================================
// ModRubble - a loose piece of rubble thrown out by an explosion (ModGore.BlastMarks): the
// gibs' fake physics (ModGib: thrown, tumbling, a couple of dull bounces, then it lies
// there), with a chunk of rock for a mesh and no blood. Our own meshes and texture
// (tools/make_rubble.py). It lies for a few minutes, then sinks away.
//=============================================================================
class ModRubble extends ModGib;

#exec NEW StaticMesh FILE=Gibs\rubble0.ase NAME=Rubble0 GROUP=Gibs
#exec NEW StaticMesh FILE=Gibs\rubble1.ase NAME=Rubble1 GROUP=Gibs
#exec TEXTURE IMPORT NAME=DirtRock FILE=Textures\dirt_rock.tga GROUP=Dirt MIPS=1

var StaticMesh Shapes[2];

defaultproperties
{
     Shapes(0)=StaticMesh'AdventMod.Gibs.Rubble0'
     Shapes(1)=StaticMesh'AdventMod.Gibs.Rubble1'
     StaticMesh=StaticMesh'AdventMod.Gibs.Rubble0'
     Skins(0)=Texture'AdventMod.Dirt.DirtRock'
     Stay=240.000000
     LifeSpan=300.000000
}
