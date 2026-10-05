//=============================================================================
// A photo gallery of static meshes, to pick kit-bash pieces from: each mesh
// in Items[] is put in front of a fixed camera, scaled to fill the same part
// of the view (from its bounding box), turned three-quarters to the camera
// and lit by the map's sun, and a screenshot ("shot") is taken.
// Items come from tools\mesh_bounds.py: "Package.Group.Name minX minY minZ
// maxX maxY maxZ", in System\U2AvalonCards.ini [U2AvalonCards.CardGallery].
// Starts when bGo turns True ("set CardGallery bGo True" once the cutscene
// is over), logs "Gallery: shot <n> <path> <size>" per picture and "Gallery:
// done" at the end.
//=============================================================================
class CardGallery extends Mutator
	config(U2AvalonCards);

var config string Items[600];
var config vector CamSpot;
var config int CamYaw, CamPitch, Turn;
var config float Dist, FitRadius, Interval;
var config int Start;              // first item (to finish a run that was cut short)

var bool bGo;
var int Next, Phase, Shots;
var CardProbe Cam;
var CardMesh M;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	Next = Start;
	Shots = Start;
	SetTimer(Interval, true);
}

function PlayerController Player()
{
	local Controller C;

	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
			return PlayerController(C);
	return None;
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

event Timer()
{
	local PlayerController PC;
	local rotator R, MR;
	local vector Lo, Hi, C, T;
	local float S;

	if (!bGo)
		return;
	PC = Player();
	if (PC == None)
		return;
	if (Cam == None)
	{
		R.Yaw = CamYaw;
		R.Pitch = CamPitch;
		Cam = Spawn(class'CardProbe',,, CamSpot, R);
		Cam.SetRotation(R);
		PC.SetViewTarget(Cam);
		PC.bBehindView = false;
		Log("Gallery: camera "$Cam$" at "$CamSpot);
	}
	PC.SetViewTarget(Cam);
	if (Phase == 1)
	{
		PC.ConsoleCommand("shot");
		Shots++;
		Log("Gallery: shot "$Shots$" "$Word(Items[Next], 0)$" "$int(float(Word(Items[Next], 4)) - float(Word(Items[Next], 1)))$"x"
			$int(float(Word(Items[Next], 5)) - float(Word(Items[Next], 2)))$"x"
			$int(float(Word(Items[Next], 6)) - float(Word(Items[Next], 3))));
		Next++;
		Phase = 0;
		return;
	}
	if (M != None)
		M.Destroy();
	while (Next < ArrayCount(Items) && Items[Next] == "")
		Next++;
	if (Next >= ArrayCount(Items))
	{
		Log("Gallery: done, "$Shots$" shots");
		bGo = false;
		return;
	}
	Lo.X = float(Word(Items[Next], 1)); Lo.Y = float(Word(Items[Next], 2)); Lo.Z = float(Word(Items[Next], 3));
	Hi.X = float(Word(Items[Next], 4)); Hi.Y = float(Word(Items[Next], 5)); Hi.Z = float(Word(Items[Next], 6));
	C = (Lo + Hi) / 2;
	S = FitRadius / FMax(VSize(Hi - Lo) / 2, 1);
	R.Yaw = CamYaw;
	R.Pitch = CamPitch;
	T = CamSpot + vector(R) * Dist;
	MR.Yaw = CamYaw + 32768 + Turn;
	M = Spawn(class'CardMesh',,, T - ((C * S) >> MR), MR);
	if (M == None || !M.Show(Word(Items[Next], 0), S))
	{
		Log("Gallery: can't show "$Items[Next]);
		M = None;
		Next++;
		return;
	}
	Phase = 1;
}

defaultproperties
{
	CamSpot=(X=8000.000000,Y=-20000.000000,Z=3000.000000)
	CamYaw=57472
	CamPitch=-1000
	Turn=6000
	Dist=3000.000000
	FitRadius=1300.000000
	Interval=0.600000
	RemoteRole=ROLE_None
}
