//=============================================================================
// ModFeet - native foot IK (report "Dynamic body kinematics", slices K6 + K9; the hook is
// research/native-animation-hooks.md, hook point 1, built in native/footik.c). One per level
// (ModMoves spawns it). Every half second, each human within range of the player (the pawns
// ModMinds keeps posed) gets its two legs hooked in the DLL: "FootIK <pawn> <class> <left thigh>
// <left calf> <left foot> <right ...>" with the bone indices from MatchRefBone; the DLL then traces
// the floor under each ankle inside the pose build and bends the leg to it. The hook is released
// when the pawn dies, goes ragdoll, leaves the range or stops walking.
// A meter (bFeetMeter) measures what the feet do against the floor, with or without the IK: for
// the lower (planted) foot of every drawn hooked pawn, the ankle's height over the floor traced
// under it, kept apart for flat ground and for slopes/steps (the floor under the foot differs from
// the floor under the pawn by more than SlopeStep). Logged every 8 s, AI and player apart.
// The pelvis (bPelvis): the drawn body is lowered through PrePivot (as a change to it, the game's
// own crouch offset survives) to the lower foot's floor (at most PelvisDrop), so on a step edge or
// a slope the lower foot reaches down and the DLL lifts the other one; the DLL reads the base as
// drawn (Location + PrePivot - the standing CollisionHeight), so the two agree.
// Config [AdventMod.ModFeet]: bFootIK (off until verified), bPlayerFeet, bAIFeet, MaxDrop /
// MaxLift (units the ankle may go down / up from the clip), Gain (1/s, how fast it follows),
// Range, bFeetLog (the DLL's per-pawn lines), bFeetMeter, bPelvis, PelvisDrop, bFootTilt (the
// foot turned level with the floor traced under it, pitch and roll only, at most 25 degrees).
//=============================================================================
class ModFeet extends Info
	config(AdventMod);

var config bool bFootIK;
var config bool bPlayerFeet;
var config bool bAIFeet;
var config float MaxDrop;
var config float MaxLift;
var config float Gain;
var config float Range;
var config bool bFeetLog;
var config bool bFeetMeter;
var config float SlopeStep;
var config bool bPelvis;            // the body lowered (PrePivot) so the lower foot reaches its floor
var config float PelvisDrop;        // at most this much
var config bool bFootTilt;          // the foot tilted to its floor's slope (the DLL's foot stage; the clip's yaw kept)

struct Foot
{
	var Pawn P;
	var bool bHooked;
	var int Tries;
	var float Drop;                 // the body's current drop (taken off PrePivot.Z)
};
var array<Foot> Feet;
var float SweepWait, MeterTime, LastUnderLog;
var bool bConfigSent, bNativeOk;

// the meter: [0] AI flat, [1] AI slope, [2] player flat, [3] player slope
var float GapSum[4], GapMin[4], GapMax[4];
var int GapN[4], Under[4], High[4];

function PostBeginPlay()
{
	local int i;

	Super.PostBeginPlay();
	for (i = 0; i < 4; i++)
	{
		GapMin[i] = 100000;
		GapMax[i] = -100000;
	}
	class'ModSettings'.static.Note("feet: foot IK " $ bFootIK $ " (player " $ bPlayerFeet $ ", AI " $ bAIFeet $ ", drop " $ MaxDrop $ ", lift " $ MaxLift $ ", gain " $ Gain $ "), meter " $ bFeetMeter);
}

function int Find(Pawn P)
{
	local int i;

	for (i = 0; i < Feet.Length; i++)
		if (Feet[i].P == P)
			return i;
	Feet.Length = Feet.Length + 1;
	Feet[Feet.Length - 1].P = P;
	return Feet.Length - 1;
}

// a biped the skeleton of which the DLL can bend: the humans (the Seeker's legs and the hound's
// are their own skeletons: later)
function bool Biped(Pawn P)
{
	if (P == None || P.bDeleteMe || P.Health <= 0 || P.Mesh == None)
		return false;
	if (P.Physics != PHYS_Walking && P.Physics != PHYS_Falling)
		return false;               // never a ragdoll (PHYS_KarmaRagdoll), nor root-motion clips
	if (PlayerController(P.Controller) != None)
		return bPlayerFeet;
	if (!bAIFeet)
		return false;
	return P.IsA('Human') || P.IsA('BountyHunterB') || P.IsA('AurelianNative');
}

function bool Eligible(Pawn P, Pawn Player)
{
	if (!Biped(P))
		return false;
	if (Player != None && P != Player && VSize(P.Location - Player.Location) > Range)
		return false;
	return true;
}

function bool Hook(int i)
{
	local Pawn P;
	local int LT, LC, LF, RT, RC, RF;
	local string Cmd;

	P = Feet[i].P;
	LT = P.MatchRefBone('leftUpLeg');
	LC = P.MatchRefBone('leftLeg');
	LF = P.MatchRefBone('leftFoot');
	RT = P.MatchRefBone('rightUpLeg');
	RC = P.MatchRefBone('rightLeg');
	RF = P.MatchRefBone('rightFoot');
	if (LT < 1 || LC < 1 || LF < 1 || RT < 1 || RC < 1 || RF < 1)
	{
		if (bFeetLog)
			class'ModSettings'.static.Note("feet: " $ P.Name $ " has no leg bones (" $ LT $ " " $ LC $ " " $ LF $ " / " $ RT $ " " $ RC $ " " $ RF $ ")");
		Feet[i].Tries = 100;        // not this skeleton
		return false;
	}
	// the mesh instance exists once the pawn has been posed: a bone read makes sure
	P.GetBoneCoords('leftFoot');
	Cmd = "FootIK " $ P.Name $ " " $ P.Class.Name $ " " $ LT $ " " $ LC $ " " $ LF $ " " $ RT $ " " $ RC $ " " $ RF $ " " $ int(P.default.CollisionHeight);
	if (!class'ModSettings'.static.NativeCall(Cmd))
	{
		Feet[i].Tries++;
		if (bFeetLog && Feet[i].Tries <= 2)
			class'ModSettings'.static.Note("feet: the DLL declined " $ Cmd);
		return false;
	}
	Feet[i].bHooked = true;
	Feet[i].Drop = 0;
	if (bFeetLog)
		class'ModSettings'.static.Note("feet: hooked " $ P.Name);
	return true;
}

function Release(int i)
{
	if (Feet[i].bHooked && Feet[i].P != None && !Feet[i].P.bDeleteMe)
	{
		class'ModSettings'.static.NativeCall("FootIKOff " $ Feet[i].P.Name $ " " $ Feet[i].P.Class.Name);
		Feet[i].P.PrePivot.Z += Feet[i].Drop;
	}
	Feet[i].bHooked = false;
	Feet[i].Drop = 0;
}

function Sweep()
{
	local PlayerController PC;
	local Pawn P, Player;
	local int i;

	PC = Level.GetLocalPlayerController();
	if (PC != None)
		Player = PC.Pawn;
	if (!bConfigSent)
	{
		bNativeOk = class'ModSettings'.static.NativeCall("FootIKConfig " $ MaxDrop $ " " $ MaxLift $ " " $ Gain $ " " $ Eval2(bFeetLog, "1", "0") $ " " $ Eval2(bFootTilt, "1", "0"));
		bConfigSent = true;
		if (!bNativeOk)
		{
			class'ModSettings'.static.Note("feet: the DLL has no foot IK (an engine export is missing, see the footik lines): off");
			return;
		}
	}
	if (!bNativeOk)
		return;
	foreach DynamicActors(class'Pawn', P)
	{
		if (!Eligible(P, Player))
			continue;
		i = Find(P);
		if (!Feet[i].bHooked && Feet[i].Tries < 5)
			Hook(i);
	}
	for (i = Feet.Length - 1; i >= 0; i--)
	{
		if (Feet[i].P == None || Feet[i].P.bDeleteMe)
		{
			Feet.Remove(i, 1);      // its directors went with its mesh instance
			continue;
		}
		if (Feet[i].bHooked && !Eligible(Feet[i].P, Player))
		{
			Release(i);
			Feet[i].Tries = 0;
			if (!Biped(Feet[i].P) && Feet[i].P.Health <= 0)
				Feet.Remove(i, 1);
		}
	}
}

// each tick, for the drawn bipeds: the floor under both feet. The meter takes the lower
// (planted) foot's ankle height over its floor; the pelvis drop lowers the drawn body so the
// lower foot's floor is reached (the DLL then lifts the other foot to its own floor).
function Feel(float DeltaTime)
{
	local int i, k;
	local Pawn P;
	local vector L, R, F, HitLoc, HitNorm;
	local float Gap, Base, GL, GR, Want, Step, NewDrop;
	local bool bL, bR;

	for (i = 0; i < Feet.Length; i++)
	{
		P = Feet[i].P;
		if (P == None || P.bDeleteMe || P.Physics != PHYS_Walking || Level.TimeSeconds - P.LastRenderTime > 0.1)
			continue;
		L = P.GetBoneCoords('leftFoot').Origin;
		R = P.GetBoneCoords('rightFoot').Origin;
		if (L == vect(0,0,0) || R == vect(0,0,0))
			continue;
		Base = P.Location.Z + P.PrePivot.Z + Feet[i].Drop - P.default.CollisionHeight;   // where the clip stands (crouched: Location down, PrePivot up)
		bL = Trace(HitLoc, HitNorm, L - vect(0,0,150), L + vect(0,0,60), false) != None && HitLoc.Z < L.Z + 59;
		GL = HitLoc.Z;
		bR = Trace(HitLoc, HitNorm, R - vect(0,0,150), R + vect(0,0,60), false) != None && HitLoc.Z < R.Z + 59;
		GR = HitLoc.Z;
		// the pelvis: down to the lower foot's floor, never up, eased. Applied as a change to
		// PrePivot, never as a value: the game moves PrePivot itself (a crouch lowers Location by
		// the height difference and raises PrePivot by it, so the mesh stays where it stood)
		if (bFootIK && bPelvis && Feet[i].bHooked)
		{
			Want = 0;
			if (bL && bR)
				Want = FClamp(Base - FMin(GL, GR), 0, PelvisDrop);
			else if (bL)
				Want = FClamp(Base - GL, 0, PelvisDrop);
			else if (bR)
				Want = FClamp(Base - GR, 0, PelvisDrop);
			Step = FMin(1, Gain * DeltaTime);
			NewDrop = Feet[i].Drop + (Want - Feet[i].Drop) * Step;
			if (Abs(NewDrop) < 0.05)
				NewDrop = 0;
			P.PrePivot.Z -= NewDrop - Feet[i].Drop;
			Feet[i].Drop = NewDrop;
		}
		if (!bFeetMeter)
			continue;
		if (!bL || !bR)
			continue;
		// a step or a slope: the two feet's floors differ
		k = 0;
		if (Abs(GL - GR) > SlopeStep)
			k = 1;
		if (L.Z < R.Z)
		{
			F = L;
			Gap = L.Z - GL;
		}
		else
		{
			F = R;
			Gap = R.Z - GR;
		}
		if (PlayerController(P.Controller) != None)
			k += 2;
		GapSum[k] += Gap;
		GapN[k]++;
		GapMin[k] = FMin(GapMin[k], Gap);
		GapMax[k] = FMax(GapMax[k], Gap);
		if (Gap < 0)
			Under[k]++;
		if (Gap > 25)
			High[k]++;
		if (bFeetLog && Gap < -5 && Level.TimeSeconds - LastUnderLog > 2)
		{
			LastUnderLog = Level.TimeSeconds;
			class'ModSettings'.static.Note("feet: " $ P.Name $ " ankle " $ int(-Gap) $ " under its floor at " $ P.Location $ " (feet " $ L $ " / " $ R $ ", floors " $ int(GL) $ " / " $ int(GR) $ ", base " $ int(Base) $ ", height " $ P.CollisionHeight $ "/" $ P.default.CollisionHeight $ ", pivot " $ P.PrePivot $ ", drop " $ Feet[i].Drop $ ", " $ P.Physics $ " crouched " $ P.bIsCrouched $ " speed " $ int(VSize(P.Velocity)) $ ")");
		}
	}
}

function Report()
{
	local int k;
	local string S;

	S = "feet: ankle over the floor under it (lower foot, drawn pawns, IK " $ bFootIK $ ", pelvis " $ bPelvis $ "):";
	for (k = 0; k < 4; k++)
	{
		if (GapN[k] == 0)
			continue;
		S = S $ " " $ Eval2(k >= 2, "player", "AI") $ " " $ Eval2(k % 2 == 1, "slope/step", "flat") $ " n=" $ GapN[k] $ " mean " $ int(GapSum[k] / GapN[k]) $ " (" $ int(GapMin[k]) $ ".." $ int(GapMax[k]) $ ") under " $ (100 * Under[k] / GapN[k]) $ "% high " $ (100 * High[k] / GapN[k]) $ "%;";
		GapSum[k] = 0;
		GapN[k] = 0;
		GapMin[k] = 100000;
		GapMax[k] = -100000;
		Under[k] = 0;
		High[k] = 0;
	}
	class'ModSettings'.static.Note(S);
}

static function string Eval2(bool B, string T, string F)
{
	if (B)
		return T;
	return F;
}

function Tick(float DeltaTime)
{
	if (DeltaTime <= 0 || DeltaTime > 0.2)
		return;
	if (bFootIK)
	{
		SweepWait -= DeltaTime;
		if (SweepWait <= 0)
		{
			SweepWait = 0.5;
			Sweep();
		}
	}
	if (bFeetMeter && !bFootIK)
	{
		// the hooked list doubles as the list of bipeds measured (with the IK off, the same sweep
		// without hooking)
		SweepWait -= DeltaTime;
		if (SweepWait <= 0)
		{
			SweepWait = 0.5;
			ListOnly();
		}
	}
	if (bFeetMeter || (bFootIK && bPelvis))
		Feel(DeltaTime);
	if (bFeetMeter)
	{
		MeterTime += DeltaTime;
		if (MeterTime > 8)
		{
			MeterTime = 0;
			Report();
		}
	}
}

// the meter's list when nothing is hooked
function ListOnly()
{
	local PlayerController PC;
	local Pawn P, Player;
	local int i;

	PC = Level.GetLocalPlayerController();
	if (PC != None)
		Player = PC.Pawn;
	foreach DynamicActors(class'Pawn', P)
		if (Eligible(P, Player))
			Find(P);
	for (i = Feet.Length - 1; i >= 0; i--)
		if (Feet[i].P == None || Feet[i].P.bDeleteMe)
			Feet.Remove(i, 1);
}

defaultproperties
{
	bFootIK=True
	bPlayerFeet=True
	bAIFeet=True
	MaxDrop=12
	MaxLift=35
	Gain=10
	Range=3500
	bFeetLog=False
	bFeetMeter=False
	SlopeStep=4
	bPelvis=True
	PelvisDrop=30
	bFootTilt=True
}
