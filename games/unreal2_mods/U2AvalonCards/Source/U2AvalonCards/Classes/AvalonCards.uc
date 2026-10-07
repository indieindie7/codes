//=============================================================================
// U2AvalonCards - dresses the outside of the Avalon command tower (TutA) at
// map load: a landing pad with the game's own dropship on it (real meshes),
// tree clusters and an offshore oil rig (imposter cards, CardSprite).
// Nothing in the map file changes; remove the mutator and it's all gone.
// Every placement is a config value (System\U2AvalonCards.ini), so spots can
// be tuned with "set AvalonCards <var> ..." and "set AvalonCards bRebuild True".
// bSurvey logs a height grid round the tower (land / water / nothing) and the
// sun light, to choose spots: lines start "Cards: grid".
//=============================================================================
class AvalonCards extends Mutator
	config(U2AvalonCards);

var config string Maps;            // which maps get dressed (comma list, lower case)
var config bool bSurvey;
var config float SurveyRadius, SurveyStep;
var config vector SurveyCentre;

var config vector PadSpot;         // Z is found by tracing down (Z here = how high above the ground to start)
var config int PadYaw;
var config float PadScale;
var config string PadMesh;
var config string ShipMesh;
var config float ShipScale, ShipLift;
var config vector ShipOffset;     // from the pad's origin, in the pad's frame (the pad mesh isn't centred)
var config int ShipYaw;

var config vector RigSpot;         // out at sea; Z = extra lift (0 = legs on the water)
var config int RigYaw;
var config float RigSize;          // the card's height in world units

var config vector TreeSpot[8];     // X=0,Y=0 = unused
var config float TreeSize[8];
var config int TreeLook[8];        // which tree picture (0-2)

// kit-bashed scenery from other levels' static meshes, one per line:
//   "Package.Group.Name X Y Yaw Scale Lift CX CY MinZ"
// X,Y = where the mesh's centre goes (Yaw in degrees); it's stood on whatever is
// straight below (land, or TutA's sea surface) by its lowest point, then lifted
// by Lift. CX CY MinZ = the mesh's bounds centre and bottom, in its own units
// (tools\mesh_bounds.py; tools\make_props.py writes these lines).
var config string Props[64];

// rough blocking: plain boxes, one per line: "X Y Yaw SizeX SizeY SizeZ Lift Colour" (world units, Yaw in
// degrees, Colour 0 grey / 1 rust / 2 pale / 3 dark). Each box stands on whatever is under its centre,
// sunk or raised by Lift. A cube blockout is the guide an image model paints the place over.
var config string Blocks[128];

// baked building cards (CardTextures.uc; toolsake_cards.py over toolsuild_buildings.py's models),
// one per line: "Name X Y Yaw Size [Frames] [Lift]". Name = the texture base name (CoolingTower ->
// U2AvalonCards.CoolingTower0..7), X Y = where it stands (on whatever is under it, + Lift), Yaw in
// degrees = where its front faces, Size = the card's height in world units (the building fills 92% of
// the card's larger side), Frames = how many views were baked (8).
var config string Cards[64];

// haze between the view's depth layers (the cinematography report: atmospheric perspective): the zones
// that already use distance fog (the outdoor ones) get HazeStart..HazeEnd in HazeColour; HazeEnd 0 = the
// map's own fog. Every zone's own fog is logged ("Cards: zone").
var config float HazeStart, HazeEnd;
var config color HazeColour;
var config bool bHazeAllZones;

// motion in the window: a static mesh flying a circle (AvalonFlyer); FlyerMesh "" = none.
// FlyerCentre Z = the flight height; FlyerSpeed in units per second (negative = the other way round).
var config string FlyerMesh;
var config vector FlyerCentre;
var config float FlyerRadius, FlyerSpeed, FlyerScale;

var bool bRebuild;
var array<Actor> Made;
var Texture TreeTex[3];
var Texture RigTex[8];

event PostBeginPlay()
{
	Super.PostBeginPlay();
	if (InStr("," $ Maps $ ",", "," $ Locs(MapName()) $ ",") < 0)
		return;
	if (bSurvey)
		Survey();
	Build();
	SetTimer(0.5, true);
}

function string MapName()
{
	local string S;

	S = string(Level);
	return Left(S, InStr(S, "."));
}

event Timer()
{
	if (bRebuild)
	{
		bRebuild = false;
		Build();
	}
}

// the first solid surface straight down: level geometry, terrain or a static mesh
function bool Ground(vector XY, out vector HitL, out vector HitN)
{
	local Actor A;
	local vector Start, End;

	Start = XY;
	Start.Z = 40000;
	End = XY;
	End.Z = -40000;
	foreach TraceActors(class'Actor', A, HitL, HitN, End, Start)
		if ((A == Level || A.bWorldGeometry || TerrainInfo(A) != None || StaticMeshActor(A) != None) && HitN.Z > 0)
			return true;
	return false;
}

// the water surface under a point (the top of a water volume), or false
function bool WaterTop(vector XY, out float Z)
{
	local CardProbe P;
	local float Lo, Hi, M;
	local int i;

	P = Spawn(class'CardProbe',,, XY);
	if (P == None)
		return false;
	Lo = -20000;
	Hi = 20000;
	P.SetLocation(XY + vect(0,0,1) * (Lo - XY.Z));
	if (P.PhysicsVolume == None || !P.PhysicsVolume.bWaterVolume)
	{
		P.Destroy();
		return false;
	}
	for (i = 0; i < 24; i++)
	{
		M = (Lo + Hi) / 2;
		P.SetLocation(XY + vect(0,0,1) * (M - XY.Z));
		if (P.PhysicsVolume != None && P.PhysicsVolume.bWaterVolume)
			Lo = M;
		else
			Hi = M;
	}
	P.Destroy();
	Z = Lo;
	return true;
}

function Survey()
{
	local float X, Y, WZ;
	local vector P, HitL, HitN;
	local string Row;
	local Light L;

	foreach AllActors(class'Light', L)
		if (L.LightEffect == LE_Sunlight)
			Log("Cards: sun "$L$" rotation "$L.Rotation$" at "$L.Location);
	for (Y = SurveyCentre.Y - SurveyRadius; Y <= SurveyCentre.Y + SurveyRadius; Y += SurveyStep)
	{
		Row = "";
		for (X = SurveyCentre.X - SurveyRadius; X <= SurveyCentre.X + SurveyRadius; X += SurveyStep)
		{
			P.X = X;
			P.Y = Y;
			P.Z = 0;
			if (Ground(P, HitL, HitN))
				Row = Row $ " " $ int(HitL.Z);
			else
				Row = Row $ " -";
			if (WaterTop(P, WZ))
				Row = Row $ "w" $ int(WZ);
		}
		Log("Cards: grid y="$int(Y)$" x0="$int(SurveyCentre.X - SurveyRadius)$" step="$int(SurveyStep)$":"$Row);
	}
}

function Haze()
{
	local ZoneInfo Z;

	foreach AllActors(class'ZoneInfo', Z)
	{
		Log("Cards: zone "$Z$" fog "$Z.bDistanceFog$" "$Z.DistanceFogStart$"-"$Z.DistanceFogEnd$" colour "$Z.DistanceFogColor.R$","$Z.DistanceFogColor.G$","$Z.DistanceFogColor.B);
		if (HazeEnd > 0 && (Z.bDistanceFog || bHazeAllZones))
		{
			Z.bDistanceFog = true;
			Z.DistanceFogStart = HazeStart;
			Z.DistanceFogEnd = HazeEnd;
			Z.DistanceFogColor = HazeColour;
			Log("Cards: haze on "$Z$" "$HazeStart$"-"$HazeEnd);
		}
	}
}

function Fly()
{
	local StaticMesh M;
	local AvalonFlyer F;

	if (FlyerMesh == "")
		return;
	M = StaticMesh(DynamicLoadObject(FlyerMesh, class'StaticMesh', true));
	if (M == None)
	{
		Log("Cards: flyer mesh "$FlyerMesh$" not found");
		return;
	}
	F = Spawn(class'AvalonFlyer',,, FlyerCentre);
	if (F == None)
		return;
	F.Setup(M, FlyerCentre, FlyerRadius, FlyerSpeed, FlyerScale, 0);
	Made[Made.Length] = F;
	Log("Cards: flyer "$FlyerMesh$" round "$FlyerCentre$" r "$FlyerRadius);
}

function Build()
{
	local int i;
	local vector HitL, HitN, P;
	local float WZ;
	local CardMesh M;
	local CardSprite S;
	local rotator R;

	for (i = 0; i < Made.Length; i++)
		if (Made[i] != None)
			Made[i].Destroy();
	Made.Length = 0;
	Haze();
	Fly();

	// the landing pad and the dropship on it
	if (PadMesh != "" && Ground(PadSpot, HitL, HitN))
	{
		R.Yaw = PadYaw;
		M = Spawn(class'CardMesh',,, HitL, R);
		if (M != None && M.Show(PadMesh, PadScale))
			Made[Made.Length] = M;
		Log("Cards: pad at "$HitL$" "$M);
		if (ShipMesh != "")
		{
			P = HitL + (ShipOffset >> R) + vect(0,0,1) * ShipLift;
			R.Yaw = ShipYaw;
			M = Spawn(class'CardMesh',,, P, R);
			if (M != None && M.Show(ShipMesh, ShipScale))
				Made[Made.Length] = M;
			Log("Cards: ship at "$P$" "$M);
		}
	}

	// the oil rig: a directional card standing in the sea
	if (RigSize > 0)
	{
		// the picture's base line is 6% above its bottom: centre it 0.44 of its height above the sea
		P = RigSpot;
		// TutA's sea is a plain surface, not a water volume: then the first thing hit straight down
		if (!WaterTop(RigSpot, WZ))
		{
			if (Ground(RigSpot, HitL, HitN))
				WZ = HitL.Z;
			else
				WZ = 0;
		}
		P.Z = WZ + 0.44 * RigSize + RigSpot.Z;
		R.Yaw = RigYaw;
		S = Spawn(class'CardSprite',,, P, R);
		if (S != None)
		{
			for (i = 0; i < 8; i++)
				S.Frames[i] = RigTex[i];
			S.NumFrames = 8;
			// alpha-tested, drawn with the solid things: a translucent card out at sea
			// gets painted over by the (translucent) sea surface
			S.Style = STY_Masked;
			S.SetSize(RigSize);
			Made[Made.Length] = S;
		}
		Log("Cards: rig at "$P$" water "$WZ$" "$S);
	}

	// tree clusters: one picture each (trees look much the same from every side)
	for (i = 0; i < 8; i++)
	{
		if (TreeSpot[i].X == 0 && TreeSpot[i].Y == 0)
			continue;
		if (!Ground(TreeSpot[i], HitL, HitN))
			continue;
		S = Spawn(class'CardSprite',,, HitL + vect(0,0,0.45) * TreeSize[i]);
		if (S != None)
		{
			S.Frames[0] = TreeTex[Clamp(TreeLook[i], 0, 2)];
			S.NumFrames = 1;
			S.SetSize(TreeSize[i]);
			Made[Made.Length] = S;
		}
	}
	for (i = 0; i < ArrayCount(Props); i++)
		if (Props[i] != "")
			PlaceProp(Props[i]);
	for (i = 0; i < ArrayCount(Blocks); i++)
		if (Blocks[i] != "")
			PlaceBlock(Blocks[i]);
	for (i = 0; i < ArrayCount(Cards); i++)
		if (Cards[i] != "")
			PlaceCard(Cards[i]);
	Log("Cards: built "$Made.Length$" things on "$MapName());
}

// the n-th space separated word of S
function string Word(string S, int n)
{
	local int i;

	for (i = 0; i < n; i++)
	{
		if (InStr(S, " ") < 0)
			return "";
		S = Mid(S, InStr(S, " ") + 1);
	}
	if (InStr(S, " ") >= 0)
		S = Left(S, InStr(S, " "));
	return S;
}

function PlaceBlock(string Line)
{
	local vector P, Size, HitL, HitN;
	local rotator R;
	local CardMesh M;

	P.X = float(Word(Line, 0));
	P.Y = float(Word(Line, 1));
	R.Yaw = int(float(Word(Line, 2)) * 65536.0 / 360.0);
	Size.X = float(Word(Line, 3));
	Size.Y = float(Word(Line, 4));
	Size.Z = float(Word(Line, 5));
	if (!Ground(P, HitL, HitN))
		return;
	P.Z = HitL.Z + Size.Z / 2 + float(Word(Line, 6));
	M = Spawn(class'CardMesh',,, P, R);
	if (M != None && M.ShowBlock(Size, int(Word(Line, 7))))
		Made[Made.Length] = M;
}

function PlaceCard(string Line)
{
	local vector P, HitL, HitN;
	local rotator R;
	local float Size, WZ;
	local int N, k;
	local Texture T;
	local CardSprite S;

	P.X = float(Word(Line, 1));
	P.Y = float(Word(Line, 2));
	R.Yaw = int(float(Word(Line, 3)) * 65536.0 / 360.0);
	Size = float(Word(Line, 4));
	N = Clamp(int(Word(Line, 5)), 1, 16);
	if (Word(Line, 5) == "")
		N = 8;
	// stands on the land, or on TutA's sea surface
	if (!WaterTop(P, WZ))
	{
		if (!Ground(P, HitL, HitN))
		{
			Log("Cards: no ground under card "$Line);
			return;
		}
		WZ = HitL.Z;
	}
	// the picture's base line is 6% above its bottom
	P.Z = WZ + 0.44 * Size + float(Word(Line, 6));
	S = Spawn(class'CardSprite',,, P, R);
	if (S == None)
		return;
	for (k = 0; k < N; k++)
	{
		// a bare name is one of this package's cards; "AvalonSM.Cards.DrillingRigHY" names another package's
		if (InStr(Word(Line, 0), ".") >= 0)
			T = Texture(DynamicLoadObject(Word(Line, 0) $ k, class'Texture'));
		else
			T = Texture(DynamicLoadObject("U2AvalonCards." $ Word(Line, 0) $ k, class'Texture'));
		if (T == None)
		{
			Log("Cards: no texture U2AvalonCards." $ Word(Line, 0) $ k);
			S.Destroy();
			return;
		}
		S.Frames[k] = T;
	}
	S.NumFrames = N;
	S.Style = STY_Masked;
	S.SetSize(Size);
	Made[Made.Length] = S;
	Log("Cards: card "$Word(Line, 0)$" at "$P);
}

function PlaceProp(string Line)
{
	local vector P, C, HitL, HitN;
	local rotator R;
	local float Scale;
	local CardMesh M;

	P.X = float(Word(Line, 1));
	P.Y = float(Word(Line, 2));
	R.Yaw = int(float(Word(Line, 3)) * 65536.0 / 360.0);
	Scale = float(Word(Line, 4));
	C.X = float(Word(Line, 6));
	C.Y = float(Word(Line, 7));
	if (!Ground(P, HitL, HitN))
	{
		Log("Cards: no ground under "$Line);
		return;
	}
	P.Z = HitL.Z - float(Word(Line, 8)) * Scale + float(Word(Line, 5));
	P -= (C * Scale) >> R;
	M = Spawn(class'CardMesh',,, P, R);
	if (M != None && M.Show(Word(Line, 0), Scale))
		Made[Made.Length] = M;
	Log("Cards: prop "$Word(Line, 0)$" at "$P$" ground "$HitL.Z);
}

defaultproperties
{
	Maps="tuta"
	SurveyRadius=30000.000000
	SurveyStep=2500.000000
	SurveyCentre=(X=-349.000000,Y=1388.000000,Z=0.000000)
	PadMesh="Mission_AvalonM.Structuron2.M10_LandingPadNew1a"
	PadScale=1.000000
	ShipMesh="Martins.Dropship.AtlantisDropship"
	ShipScale=1.000000
	ShipLift=40.000000
	RigSize=0.000000
	TreeTex(0)=Texture'Trees0'
	TreeTex(1)=Texture'Trees1'
	TreeTex(2)=Texture'Trees2'
	RigTex(0)=Texture'Rig0'
	RigTex(1)=Texture'Rig1'
	RigTex(2)=Texture'Rig2'
	RigTex(3)=Texture'Rig3'
	RigTex(4)=Texture'Rig4'
	RigTex(5)=Texture'Rig5'
	RigTex(6)=Texture'Rig6'
	RigTex(7)=Texture'Rig7'
	RemoteRole=ROLE_None
}
