//=============================================================================
// AvalonTruck - a static mesh driving a road (scale and motion for the
// command room's view: a truck tells how big a hall is). Follows a polyline of
// X Y points to its end and back, nose along the road, standing on whatever is
// under it (the road slabs, the terrain), pitched with the slope.
// Spawned by AvalonCards (Trucks[] + Paths[] lines).
//=============================================================================
class AvalonTruck extends Actor;

var array<vector> Pts;
var float Speed, Dist, Total, Lift;
var array<float> Cum;
var int Dir;
var float Pause;

function Setup(StaticMesh M, float Scale, string Path, float S, float StartFrac, float L)
{
	local vector P;
	local int i;

	StaticMesh = M;
	SetDrawScale(Scale);
	Speed = S;
	Lift = L;
	Dir = 1;
	while (Path != "")
	{
		P.X = float(Next(Path));
		P.Y = float(Next(Path));
		Pts[Pts.Length] = P;
	}
	Cum[0] = 0;
	for (i = 1; i < Pts.Length; i++)
		Cum[i] = Cum[i - 1] + VSize(Pts[i] - Pts[i - 1]);
	Total = Cum[Pts.Length - 1];
	Dist = Total * FClamp(StartFrac, 0, 1);
	Tick(0);
}

// pops the first word off S
function string Next(out string S)
{
	local string W;
	local int k;

	while (Left(S, 1) == " ")
		S = Mid(S, 1);
	k = InStr(S, " ");
	if (k < 0)
	{
		W = S;
		S = "";
	}
	else
	{
		W = Left(S, k);
		S = Mid(S, k + 1);
	}
	return W;
}

function vector At(float D)
{
	local int i;
	local float t;

	i = 1;
	while (i < Pts.Length - 1 && Cum[i] < D)
		i++;
	t = (D - Cum[i - 1]) / FMax(1, Cum[i] - Cum[i - 1]);
	return Pts[i - 1] + (Pts[i] - Pts[i - 1]) * FClamp(t, 0, 1);
}

function float GroundZ(vector P)
{
	local vector HitL, HitN, S, E;

	S = P;
	S.Z = 40000;
	E = P;
	E.Z = -40000;
	if (Trace(HitL, HitN, E, S, false) != None)
		return HitL.Z;
	return Location.Z;
}

event Tick(float DeltaTime)
{
	local vector A, B;
	local rotator R;

	if (Pts.Length < 2 || StaticMesh == None)
		return;
	if (Pause > 0)
	{
		Pause -= DeltaTime;
		return;
	}
	Dist += Dir * Speed * DeltaTime;
	if (Dist >= Total || Dist <= 0)
	{
		// unloading / loading at the ends, then back
		Dist = FClamp(Dist, 0, Total);
		Dir = -Dir;
		Pause = 6;
	}
	// the axles: a point ahead and one behind, each on the ground
	A = At(Dist + Dir * 150);
	B = At(Dist - Dir * 150);
	A.Z = GroundZ(A);
	B.Z = GroundZ(B);
	R = rotator(A - B);
	R.Roll = 0;
	SetRotation(R);
	SetLocation((A + B) * 0.5 + vect(0,0,1) * Lift);
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bStatic=False
	bAlwaysRelevant=True
	bCollideActors=False
	bBlockActors=False
	bBlockPlayers=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
}
