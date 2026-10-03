//=============================================================================
// HubBend - "hub bend NODE pitch yaw roll [space]": rotates one bone of your
// character every tick with MeshNodeSetRotation (the test of whether script can
// pose Unreal II's skeletal meshes at all: bone scaling has no effect on them).
// space: 0 world, 1 mesh, 2 parent node (default), 3 relative to the ref pose.
// Logs the bone's rotation before and after the first set. "hub bend off" stops.
//=============================================================================
class HubBend extends Info;

var Pawn Target;
var string NodeName;
var rotator Turn;
var byte Space;
var int Node;
var bool bLogged;

function Setup(Pawn P, string N, rotator R, byte S)
{
	Target = P;
	NodeName = N;
	Turn = R;
	Space = S;
	Node = 0;
	bLogged = false;
	if (Target != None)
		Node = Target.MeshGetNodeNamed(NodeName);
	Log("Hub: bend "$NodeName$" node "$Node$" turn "$Turn$" space "$Space);
}

function rotator Get()
{
	if (Space == 0) return Target.MeshNodeGetRotation(Node, MESHNODEREL_World);
	if (Space == 1) return Target.MeshNodeGetRotation(Node, MESHNODEREL_Mesh);
	if (Space == 3) return Target.MeshNodeGetRotation(Node, MESHNODEREL_RefPose);
	return Target.MeshNodeGetRotation(Node, MESHNODEREL_ParentNode);
}

event Tick(float DeltaTime)
{
	local rotator Before;

	if (Target == None || Target.bDeleteMe || Node == 0)
		return;
	if (!bLogged)
		Before = Get();
	if (Space == 0)      Target.MeshNodeSetRotation(Node, Turn, MESHNODEREL_World);
	else if (Space == 1) Target.MeshNodeSetRotation(Node, Turn, MESHNODEREL_Mesh);
	else if (Space == 3) Target.MeshNodeSetRotation(Node, Turn, MESHNODEREL_RefPose);
	else                 Target.MeshNodeSetRotation(Node, Turn, MESHNODEREL_ParentNode);
	if (!bLogged)
	{
		bLogged = true;
		Log("Hub: bend "$NodeName$" rotation before "$Before$" after set "$Get());
	}
}

defaultproperties
{
	bAlwaysTick=True
}
