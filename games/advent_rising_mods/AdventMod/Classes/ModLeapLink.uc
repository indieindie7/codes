//=============================================================================
// ModLeapLink - a wall-kick link between two path nodes (AI-MINDS-DESIGN.md section 10).
// Not a NavigationPoint: the editor's path graph is untouched. ModMinds builds these once per
// level from the graph (BuildLinks, the report's Rule 1): two nodes close as the crow flies
// whose walk route is a long detour, with a wall beside the straight line that a hound can
// kick off (the wall's normal in the band the stock WallJumpBegin takes), and both arcs
// (A -> wall, wall -> B) clear of the world for a hound's body. A hound whose route passes A
// then B walks to A, leaps to Wall, plants, and leaps off to B (ModMinds.LinkKick), instead
// of the detour. The actor sits at the plant point (hidden), so the pilot and a debug view
// can list and draw them.
//=============================================================================
class ModLeapLink extends Actor;

var NavigationPoint A, B;
var vector Wall;            // the plant point: the wall's hit point, out by the hound's radius
var vector Normal;          // the wall's normal there
var float Straight;         // |AB|
var float Route;            // the walk route's length A -> B (0: none within the cutoff)
var bool bTwoWay;           // B -> A passes as well (the same wall)
var int Uses;               // legs that went through it

function string Describe()
{
	local string S;

	S = A.Name $ " -> " $ B.Name $ " straight " $ int(Straight) $ " route ";
	if (Route <= 0)
		S = S $ "none";
	else
		S = S $ int(Route) $ " (x" $ (int(Route / FMax(Straight, 1) * 10) / 10.0) $ ")";
	S = S $ " wall " $ int(VSize(Wall - A.Location)) $ " from A, n.z " $ (int(Normal.Z * 100) / 100.0);
	if (bTwoWay)
		S = S $ " two-way";
	return S $ " used " $ Uses;
}

defaultproperties
{
	bHidden=True
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	RemoteRole=ROLE_None
	bStatic=False
	bNoDelete=False
}
