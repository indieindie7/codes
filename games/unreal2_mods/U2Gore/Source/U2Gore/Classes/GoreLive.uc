//=============================================================================
// A live blood region: a GoreDecal whose texture is one of the placeholders the
// d3d8 layer simulates (BloodLive0..7 on floors = spreading pools, blood.hpp;
// BloodRun0..7 on walls = blood running down, runs.hpp). Ported from AdventMod's
// ModBloodDecal live parts; the commands go out through GoreLink.
// One region per slot; GoreManager hands out the slots (8 of each).
//=============================================================================
#exec TEXTURE IMPORT NAME=BloodLive0 FILE=Textures\BloodLive0.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive1 FILE=Textures\BloodLive1.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive2 FILE=Textures\BloodLive2.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive3 FILE=Textures\BloodLive3.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive4 FILE=Textures\BloodLive4.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive5 FILE=Textures\BloodLive5.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive6 FILE=Textures\BloodLive6.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodLive7 FILE=Textures\BloodLive7.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun0 FILE=Textures\BloodRun0.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun1 FILE=Textures\BloodRun1.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun2 FILE=Textures\BloodRun2.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun3 FILE=Textures\BloodRun3.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun4 FILE=Textures\BloodRun4.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun5 FILE=Textures\BloodRun5.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun6 FILE=Textures\BloodRun6.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP
#exec TEXTURE IMPORT NAME=BloodRun7 FILE=Textures\BloodRun7.tga MIPS=Off UCLAMPMODE=CLAMP VCLAMPMODE=CLAMP

class GoreLive extends GoreDecal;

var GoreLink Link;
var int LiveSlot, RunSlot, Kind;
var float LiveSize, LiveAge, LastStamp;
var vector AxU, AxV;

// a pool region in slot Slot, Size world units across; the floor's slope along the texture's axes
function GoLive(GoreLink L, int Slot, Texture Placeholder, float Size, float Pour, float PourSecs, int K)
{
	local vector X, Y, Z;

	Link = L;
	LiveSlot = Slot;
	RunSlot = -1;
	LiveSize = Size;
	Kind = K;
	ProjTexture = Placeholder;
	GrowTime = 0;
	SetDrawScale(Size / 64.0);              // the placeholders are 64 px
	GetAxes(Rotation, X, Y, Z);
	AxU = Y;
	AxV = Z;
	Link.Send("pool " $ Slot $ " " $ Size $ " " $ AxU.Z $ " " $ AxV.Z $ " " $ K);
	Link.Send("pour " $ Slot $ " 0.5 0.5 " $ Pour $ " " $ PourSecs $ " " $ K);
	DetachProjector(true);
	AttachProjector();
	LifeSpan = 900;
}

// where a world spot falls on the sheet (0..1); false off the region or on another floor
function bool Local(vector Spot, out float U, out float W)
{
	local vector D;

	if (LiveSlot < 0)
		return false;
	D = Spot - Location;
	if (Abs(D.Z) > 60)
		return false;
	U = 0.5 + (D Dot AxU) / LiveSize;
	W = 0.5 + (D Dot AxV) / LiveSize;
	return U > 0.08 && U < 0.92 && W > 0.08 && W < 0.92;
}

// another body in this region: its blood pours in where it lies (pools run together)
function bool PourAt(vector Spot, float Pour, float PourSecs, int K)
{
	local float U, W;

	if (!Local(Spot, U, W))
		return false;
	Link.Send("pour " $ LiveSlot $ " " $ U $ " " $ W $ " " $ Pour $ " " $ PourSecs $ " " $ K);
	return true;
}

// the slot is wanted elsewhere: the layer freezes the pool as it is
function EndLive()
{
	if (LiveSlot >= 0 && Link != None)
		Link.Send("stop " $ LiveSlot);
	LiveSlot = -1;
	Destroy();
}

// a wall region in slot Slot: "down" across the texture from the decal's own axes
function GoRun(GoreLink L, int Slot, Texture Placeholder, float Size, int K)
{
	local vector X, Y, Z;

	Link = L;
	RunSlot = Slot;
	LiveSlot = -1;
	LiveSize = Size;
	Kind = K;
	ProjTexture = Placeholder;
	GrowTime = 0;
	SetDrawScale(Size / 64.0);
	GetAxes(Rotation, X, Y, Z);
	AxU = Y;
	AxV = Z;
	Link.Send("run " $ Slot $ " " $ K $ " " $ (vect(0,0,-1) Dot AxU) $ " " $ (vect(0,0,-1) Dot AxV));
	DetachProjector(true);
	AttachProjector();
	LifeSpan = 600;
}

function bool RunLocal(vector Spot, out float U, out float W)
{
	local vector D, X, Y, Z;

	if (RunSlot < 0)
		return false;
	GetAxes(Rotation, X, Y, Z);
	D = Spot - Location;
	if (Abs((D Dot X) - 16) > 30)               // the projector stands 16 off the wall, looking into it (+X)
		return false;
	U = 0.5 + (D Dot AxU) / LiveSize;
	W = 0.5 + (D Dot AxV) / LiveSize;
	return U > 0.05 && U < 0.95 && W > 0.05 && W < 0.95;
}

function Drip(float U, float W, float Amount)
{
	Link.Send("drip " $ RunSlot $ " " $ U $ " " $ W $ " " $ Amount $ " " $ Kind);
}

function EndRun()
{
	if (RunSlot >= 0 && Link != None)
		Link.Send("rstop " $ RunSlot);
	RunSlot = -1;
	Destroy();
}

// whoever walks through the pool pushes the blood about
event Tick(float DeltaTime)
{
	local Pawn P;
	local vector D, V;
	local float U, W;

	Super.Tick(DeltaTime);
	if (LiveSlot < 0 || Link == None)
		return;
	LiveAge += DeltaTime;
	if (LiveAge - LastStamp < 0.08)
		return;
	LastStamp = LiveAge;
	foreach RadiusActors(class'Pawn', P, LiveSize * 0.75)
	{
		if (P.Physics != PHYS_Walking || VSize(P.Velocity) < 15)
			continue;
		D = P.Location - vect(0,0,1) * P.CollisionHeight - Location;
		if (Abs(D.Z) > 40)
			continue;
		U = 0.5 + (D Dot AxU) / LiveSize;
		W = 0.5 + (D Dot AxV) / LiveSize;
		if (U < -0.1 || U > 1.1 || W < -0.1 || W > 1.1)
			continue;
		V = P.Velocity;
		Link.Send("stamp " $ LiveSlot $ " " $ U $ " " $ W $ " " $ ((V Dot AxU) / LiveSize) $ " " $ ((V Dot AxV) / LiveSize) $ " " $ (P.CollisionRadius * 0.6 / LiveSize));
	}
}

event Destroyed()
{
	if (Link != None)
	{
		if (LiveSlot >= 0)
			Link.Send("stop " $ LiveSlot);
		if (RunSlot >= 0)
			Link.Send("rstop " $ RunSlot);
	}
	Super.Destroyed();
}

defaultproperties
{
	LiveSlot=-1
	RunSlot=-1
	LifeSpan=900.000000
}
