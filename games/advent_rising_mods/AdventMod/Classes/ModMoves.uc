//=============================================================================
// ModMoves - characters that carry their weight (report "Agent locomotion and pathfinding",
// slices L0-L2). One per level (ModMinds spawns it). Over the game's own walk and run clips:
//   - lean: the body banks into a turn and leans with a change of speed, from how its velocity
//     bends and changes (centripetal and forward acceleration), sprung so it settles rather than
//     snaps; on the 'spine' bone (the game's clip stays underneath), never on a body ModReact is
//     flinching or on a hound (its spine is the engine's own);
//   - a foot-slide meter: for each walking character, the lower foot counts as planted, and how
//     fast that foot moves over the ground is the slide (0 = the feet grip the floor). Logged every
//     few seconds with the characters' mean speed, to judge whether stride-matching is needed.
// Config [AdventMod.ModMoves]: bLean, LeanGain (1 = the physical bank angle), MaxLean (degrees),
// LeanSpring (how fast the lean follows), bSlideMeter.
//=============================================================================
class ModMoves extends Info
	config(AdventMod);

var config bool bLean;
var config float LeanGain;
var config float MaxLean;           // degrees
var config float LeanSpring;        // 1/s
var config bool bSlideMeter;
var config int LeanSign;            // +1/-1: which way the bone's roll banks (set from a test)

struct Body
{
	var Pawn P;
	var vector LastVel;
	var float Bank, BankVel;        // degrees, degrees/s
	var float Pitch, PitchVel;
	var vector LastFoot;
	var name LastFootBone;
	var bool bLeaning;
};
var array<Body> Bodies;
var ModReact React;
var float SlideSum, SpeedSum, MeterTime, LeanMax;
var int SlideN;
var int LeanRight, LeanWrong;         // lean check: the head tipped toward the inside of the turn, or away

function PostBeginPlay()
{
	Super.PostBeginPlay();
	foreach DynamicActors(class'ModReact', React)
		break;
	class'ModSettings'.static.Note("moves: lean " $ bLean $ " (gain " $ LeanGain $ ", max " $ MaxLean $ "), slide meter " $ bSlideMeter);
}

function int Find(Pawn P)
{
	local int i;

	for (i = 0; i < Bodies.Length; i++)
		if (Bodies[i].P == P)
			return i;
	Bodies.Length = Bodies.Length + 1;
	Bodies[Bodies.Length - 1].P = P;
	Bodies[Bodies.Length - 1].LastVel = P.Velocity;
	return Bodies.Length - 1;
}

function bool Leanable(Pawn P)
{
	if (P == None || P.bDeleteMe || P.Health <= 0 || P.Physics != PHYS_Walking || P.IsA('Vehicle'))
		return false;
	if (P.IsA('SeekerDogNative'))
		return false;               // the hound's spine is the engine's (SetWalkUpright false)
	return P.IsA('Human') || P.IsA('Seeker') || P.IsA('AurelianNative') || P.IsA('BountyHunterB');
}

function Tick(float DeltaTime)
{
	local Pawn P;
	local int i;
	local vector Acc, Dir, Right;
	local float Speed, Lat, Fwd, Want, WantP;
	local rotator R;

	if (DeltaTime <= 0 || DeltaTime > 0.2)
		return;
	if (React == None)
		foreach DynamicActors(class'ModReact', React)
			break;
	foreach DynamicActors(class'Pawn', P)
	{
		if (!Leanable(P))
			continue;
		i = Find(P);
		Speed = VSize(P.Velocity * vect(1,1,0));
		// (a skeleton is only posed when it is drawn: measure the ones on screen)
		if (bSlideMeter && Level.TimeSeconds - P.LastRenderTime < 0.1)
			Meter(i, DeltaTime, Speed);
		if (!bLean)
			continue;
		// acceleration of the body over the ground: across the motion banks, along it pitches
		Acc = (P.Velocity - Bodies[i].LastVel) / DeltaTime;
		Acc.Z = 0;
		Bodies[i].LastVel = P.Velocity;
		Want = 0;
		WantP = 0;
		if (Speed > 60)
		{
			Dir = Normal(P.Velocity * vect(1,1,0));
			Right = Dir cross vect(0,0,1);
			Lat = Acc dot Right;
			Fwd = Acc dot Dir;
			// the bank a runner takes: atan(lateral acceleration / gravity), in degrees
			Want = FClamp(Atan(Lat, 950.0) * 57.2958 * LeanGain, -MaxLean, MaxLean);
			WantP = FClamp(Atan(Fwd, 950.0) * 57.2958 * LeanGain * 0.6, -MaxLean * 0.5, MaxLean * 0.5);
		}
		// critically damped spring toward the wanted lean
		Bodies[i].BankVel += (LeanSpring * LeanSpring * (Want - Bodies[i].Bank) - 2 * LeanSpring * Bodies[i].BankVel) * DeltaTime;
		Bodies[i].Bank += Bodies[i].BankVel * DeltaTime;
		Bodies[i].PitchVel += (LeanSpring * LeanSpring * (WantP - Bodies[i].Pitch) - 2 * LeanSpring * Bodies[i].PitchVel) * DeltaTime;
		Bodies[i].Pitch += Bodies[i].PitchVel * DeltaTime;
		LeanMax = FMax(LeanMax, Abs(Bodies[i].Bank));
		if (React != None && React.IsFlinching(P))
			continue;               // its spring flinch has the spine now
		if (Abs(Bodies[i].Bank) < 0.2 && Abs(Bodies[i].Pitch) < 0.2)
		{
			if (Bodies[i].bLeaning)
			{
				P.SetBoneRotation('spine', rot(0,0,0), 0, 0);
				Bodies[i].bLeaning = false;
			}
			continue;
		}
		R.Pitch = int(-Bodies[i].Pitch * 182.04);
		R.Roll = int(LeanSign * Bodies[i].Bank * 182.04);
		R.Yaw = 0;
		P.SetBoneRotation('spine', R, 0, 1);
		Bodies[i].bLeaning = true;
		// check (the bone's roll axis isn't documented): with a clear bank, the head should sit off
		// the hips toward the inside of the turn (the side the body accelerates to)
		if (Abs(Bodies[i].Bank) > 4 && Speed > 150 && Level.TimeSeconds - P.LastRenderTime < 0.1)
		{
			if (((P.GetBoneCoords('head').Origin - P.GetBoneCoords('hips').Origin) dot Right) * Bodies[i].Bank > 0)
				LeanRight++;
			else
				LeanWrong++;
		}
	}
	// forget the gone
	for (i = Bodies.Length - 1; i >= 0; i--)
		if (Bodies[i].P == None || Bodies[i].P.bDeleteMe)
			Bodies.Remove(i, 1);
	if (bSlideMeter)
	{
		MeterTime += DeltaTime;
		if (MeterTime > 8 && SlideN > 0)
		{
			class'ModSettings'.static.Note("moves: " $ SlideN $ " walking samples, mean speed " $ int(SpeedSum / SlideN) $ ", planted foot slides " $ int(SlideSum / SlideN) $ " units/s (" $ int(100 * SlideSum / FMax(SpeedSum, 1)) $ "% of the speed), largest bank " $ int(LeanMax) $ " deg; head toward the inside of the turn " $ LeanRight $ ", away " $ LeanWrong);
			MeterTime = 0;
			SlideSum = 0;
			SpeedSum = 0;
			SlideN = 0;
			LeanMax = 0;
		}
	}
}

// the lower foot is the planted one: how fast it moves over the ground
function Meter(int i, float DeltaTime, float Speed)
{
	local vector L, R, Foot;
	local name Bone;

	if (Speed < 80)
	{
		Bodies[i].LastFootBone = '';
		return;
	}
	L = Bodies[i].P.GetBoneCoords('leftFoot').Origin;
	R = Bodies[i].P.GetBoneCoords('rightFoot').Origin;
	if (L == vect(0,0,0) || R == vect(0,0,0))
		return;                     // no such bones on this skeleton
	if (Abs(L.Z - R.Z) < 3)
	{
		Bodies[i].LastFootBone = '';  // both down or in the cross-over: unclear
		return;
	}
	if (L.Z < R.Z)
	{
		Bone = 'leftFoot';
		Foot = L;
	}
	else
	{
		Bone = 'rightFoot';
		Foot = R;
	}
	if (Bone == Bodies[i].LastFootBone)
	{
		SlideSum += VSize((Foot - Bodies[i].LastFoot) * vect(1,1,0)) / DeltaTime;
		SpeedSum += Speed;
		SlideN++;
	}
	Bodies[i].LastFootBone = Bone;
	Bodies[i].LastFoot = Foot;
}

defaultproperties
{
	bLean=True
	LeanGain=1.0
	MaxLean=12
	LeanSpring=9
	bSlideMeter=True
	LeanSign=1
}
