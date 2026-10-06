//=============================================================================
// ModBloodDecal - one blood mark on a wall or floor: an orthographic projector
// (FOV 0: its size is the texture's times DrawScale) pointed into the surface.
// It multiplies the surface 2x (UE2's projector modulate; its alpha-blend path
// falls through into that and came out pink): the textures are 50% grey where
// there's no blood.
// ModGore spawns them, caps how many there are, and grows the pools under the
// dead. Characters are never painted (bProjectActor off).
//=============================================================================
class ModBloodDecal extends Projector;

var float GrowFrom, GrowTo, GrowTime, GrowAge;   // a pool spreading out (GrowTime 0 = no growth)
var Material Frames[12];                         // a spreading pool's texture over time (None = keep the one it has)
var int Frame;
// a LIVE pool: the texture is a placeholder the d3d8 layer swaps for a sheet it simulates
// (blood.hpp; commands through AdventNative "Blood:..."): the blood spreads for real, runs
// down the floor's slope and is kicked about by whoever steps in it
var int LiveSlot;                                // -1: not live
var float LiveSize;                              // the pool's width in world units
var vector AxU, AxV;                             // the texture's axes in the world
var float LiveAge, LastStampT;
var int LiveKind;                                // 0 red, 1 purple
var ModGore Gore;

// Projector attaches itself at spawn (before it has a texture or a place): not yet
simulated event PostBeginPlay()
{
}

// on the surface at Spot with normal N, the texture's +X along Along (a spray's direction)
function Place(Material Tex, vector Spot, vector N, vector Along, float Size)
{
	local rotator R;
	local vector X, Y, Z;

	ProjTexture = Tex;
	SetDrawScale(Size);
	SetLocation(Spot + N * 16);
	// the projector looks along its X axis: into the surface; its Y axis is the texture's
	// +X, turned to the shot's direction across the surface (or anywhere, for a round splat)
	R = rotator(-N);
	GetAxes(R, X, Y, Z);
	if (VSize(Along) > 0.1)
		R.Roll = int(Atan(Along Dot -Z, Along Dot Y) * 32768.0 / Pi);
	else
		R.Roll = Rand(65536);
	SetRotation(R);
	DetachProjector(true);
	AttachProjector();
}

// this pool goes live in slot Slot (the d3d8 layer simulates it): Size world units across
function GoLive(int Slot, Material Placeholder, float Size, float Pour, float PourSecs, int Kind)
{
	local vector X, Y, Z;

	LiveSlot = Slot;
	LiveSize = Size;
	LiveKind = Kind;
	ProjTexture = Placeholder;
	GrowTime = 0;
	// the placeholder is 64 px; the projector's size is the texture's times DrawScale
	SetDrawScale(Size / 64.0);
	GetAxes(Rotation, X, Y, Z);
	AxU = Y;
	AxV = Z;
	// the floor's slope along the texture axes: the axes lie in the floor, so their Z is the rise
	class'ModSettings'.static.NativeCall("Blood:pool " $ Slot $ " " $ Size $ " " $ AxU.Z $ " " $ AxV.Z $ " " $ Kind);
	class'ModSettings'.static.NativeCall("Blood:pour " $ Slot $ " 0.5 0.5 " $ Pour $ " " $ PourSecs);
	DetachProjector(true);
	AttachProjector();
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: live pool slot " $ Slot $ " at " $ Location $ " size " $ Size $ " slope " $ AxU.Z $ " " $ AxV.Z);
}

// the slot is wanted elsewhere: the pool keeps a baked final frame instead
function EndLive()
{
	if (LiveSlot < 0)
		return;
	class'ModSettings'.static.NativeCall("Blood:stop " $ LiveSlot);
	LiveSlot = -1;
	if (Frames[11] != None)
	{
		ProjTexture = Frames[11];
		SetDrawScale(LiveSize / 128.0);
		DetachProjector(true);
		AttachProjector();
	}
}

// whoever moves through the pool pushes the blood about
function Stamps(float DeltaTime)
{
	local Pawn P;
	local vector D, V;
	local float U, W, R;

	LiveAge += DeltaTime;
	if (LiveAge - LastStampT < 0.08)
		return;
	LastStampT = LiveAge;
	foreach DynamicActors(class'Pawn', P)
	{
		if (P.Physics != PHYS_Walking && P.Physics != PHYS_Falling)
			continue;
		D = P.Location - vect(0,0,1) * P.CollisionHeight - Location;
		if (Abs(D.Z) > 40 || VSize(P.Velocity) < 15)
			continue;
		U = 0.5 + (D Dot AxU) / LiveSize;
		W = 0.5 + (D Dot AxV) / LiveSize;
		if (U < -0.1 || U > 1.1 || W < -0.1 || W > 1.1)
			continue;
		V = P.Velocity;
		R = P.CollisionRadius * 0.6 / LiveSize;
		class'ModSettings'.static.NativeCall("Blood:stamp " $ LiveSlot $ " " $ U $ " " $ W $ " " $ ((V Dot AxU) / LiveSize) $ " " $ ((V Dot AxV) / LiveSize) $ " " $ R);
		// standing in the blood: bloody feet for a while (footprints)
		if (Gore != None && class'ModSettings'.static.NativeCall("Blood:wet " $ LiveSlot $ " " $ U $ " " $ W))
			Gore.BloodyFeet(P, LiveKind);
	}
}

// a pool: from Size*From to Size*To over Seconds
function Grow(float From, float To, float Seconds)
{
	GrowFrom = From;
	GrowTo = To;
	GrowTime = Seconds;
	GrowAge = 0;
	if (Frames[0] != None)
	{
		Frame = 0;
		ProjTexture = Frames[0];
	}
	SetDrawScale(From);
	DetachProjector(true);
	AttachProjector();
}

event Destroyed()
{
	if (LiveSlot >= 0)
		class'ModSettings'.static.NativeCall("Blood:stop " $ LiveSlot);
	Super.Destroyed();
}

event Tick(float DeltaTime)
{
	local float T;

	if (LiveSlot >= 0)
		Stamps(DeltaTime);
	if (GrowTime <= 0)
		return;
	GrowAge += DeltaTime;
	// re-projecting costs a little: a few steps a second is smooth enough for a pool
	if (GrowAge < GrowTime && int(GrowAge * 6) == int((GrowAge - DeltaTime) * 6))
		return;
	T = FMin(GrowAge / GrowTime, 1);
	T = 1 - (1 - T) * (1 - T);     // fast at first, settling
	SetDrawScale(GrowFrom + (GrowTo - GrowFrom) * T);
	// the fluid run's frames: the pool's shape spreads, not just its size
	if (Frames[int(T * 11)] != None && int(T * 11) != Frame)
	{
		Frame = int(T * 11);
		ProjTexture = Frames[Frame];
	}
	DetachProjector(true);
	AttachProjector();
	if (GrowAge >= GrowTime)
		GrowTime = 0;
}

defaultproperties
{
     LiveSlot=-1
     FrameBufferBlendingOp=PB_Modulate
     FOV=0
     MaxTraceDistance=40
     bProjectActor=False
     bProjectParticles=False
     bClipBSP=True
     bClipStaticMesh=True
     bProjectOnParallelBSP=True
     bStatic=False
     bLevelStatic=False
     bNoDelete=False
     bHidden=True
     LifeSpan=180.000000
}
