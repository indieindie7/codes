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
var config int LeanSign;
var config bool bAILean;            // lean the AI too (off since the 10-10 scope cut: the player only)
var config bool bStrideMatch;       // K4: AI clip rate follows the planted foot (no skating)
var config float StrideGain;
var int StrideAdjusts;            // +1/-1: which way the bone's roll banks (set from a test)

struct Body
{
	var Pawn P;
	var vector LastVel;
	var float Bank, BankVel;        // degrees, degrees/s
	var float Pitch, PitchVel;
	var vector LastFoot;
	var name LastFootBone;
	var bool bLeaning;
	var float ContactMin;            // the slowest the planted foot went in this footfall
	var float ContactSpeed;          // the body's speed then
	var float SlipSum;               // K4: the planted foot's signed slip along the motion, this footfall
	var int SlipN;
	var float Rate;                  // K4: our multiplier on its clip rate (1 = the game's)
	var float BaseF, BaseB, WroteF, WroteB;   // the game's BaseAnimSpeed_F/B, and what we last wrote
};
var array<Body> Bodies;
var ModReact React;
var float SlideSum, SpeedSum, MeterTime, LeanMax;
var int SlideN;
var float SlideSumP, SpeedSumP;      // the same for the player alone
var int SlideNP;
var int LeanRight, LeanWrong;         // lean check: the head tipped toward the inside of the turn, or away

function PostBeginPlay()
{
	Super.PostBeginPlay();
	foreach DynamicActors(class'ModReact', React)
		break;
	Spawn(class'ModAction');     // the player's vault, wall slam and barge
	Spawn(class'ModBody');       // feelings in the body (Seeker arms, hound snarl/cower), hounds on slopes
	Spawn(class'ModFeet');       // native foot IK (K6/K9) and the foot-to-floor meter
	Spawn(class'ModJiggle');     // flesh jiggle on the Seeker infantry (JIGGLE.md)
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
	if (!bAILean && PlayerController(P.Controller) == None)
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
		if (MeterTime > 8 && SlideNP > 0)
			class'ModSettings'.static.Note("moves: player: " $ SlideNP $ " footfalls, mean speed " $ int(SpeedSumP / SlideNP) $ ", planted foot at its slowest " $ int(SlideSumP / SlideNP) $ " units/s (" $ int(100 * SlideSumP / FMax(SpeedSumP, 1)) $ "%)");
		if (MeterTime > 8)
		{
			SlideSumP = 0;
			SpeedSumP = 0;
			SlideNP = 0;
		}
		if (MeterTime > 8 && SlideN > 0)
		{
			class'ModSettings'.static.Note("moves: AI: " $ SlideN $ " footfalls, mean speed " $ int(SpeedSum / SlideN) $ ", planted foot at its slowest " $ int(SlideSum / SlideN) $ " units/s (" $ int(100 * SlideSum / FMax(SpeedSum, 1)) $ "% of the speed), " $ StrideAdjusts $ " stride adjustments, largest bank " $ int(LeanMax) $ " deg; head toward the inside of the turn " $ LeanRight $ ", away " $ LeanWrong);
			MeterTime = 0;
			SlideSum = 0;
			SpeedSum = 0;
			SlideN = 0;
			LeanMax = 0;
		}
	}
}

// K4 stride matching: the game sets each walk mode's clip speed (EonPawn.BaseAnimSpeed_F/_B, the
// speed the clip was made for; the engine plays it at speed / that). A planted foot dragged forward
// over a footfall means the clip runs slow for this speed: raise its rate; dragged back: lower it.
// Our multiplier rides on whatever the game sets (a new mode's value is taken as the new base).
function Stride(int i, float Slip, float Speed)
{
	local EonPawn E;

	E = EonPawn(Bodies[i].P);
	if (E == None || Speed < 80)
		return;
	if (Bodies[i].Rate <= 0)
		Bodies[i].Rate = 1;
	if (E.BaseAnimSpeed_F != Bodies[i].WroteF)
		Bodies[i].BaseF = E.BaseAnimSpeed_F;
	if (E.BaseAnimSpeed_B != Bodies[i].WroteB)
		Bodies[i].BaseB = E.BaseAnimSpeed_B;
	Bodies[i].Rate = FClamp(Bodies[i].Rate * (1 + StrideGain * FClamp(Slip / Speed, -0.5, 0.5)), 0.6, 1.6);
	E.BaseAnimSpeed_F = Bodies[i].BaseF / Bodies[i].Rate;
	E.BaseAnimSpeed_B = Bodies[i].BaseB / Bodies[i].Rate;
	Bodies[i].WroteF = E.BaseAnimSpeed_F;
	Bodies[i].WroteB = E.BaseAnimSpeed_B;
	StrideAdjusts++;
}

// the lower foot is the planted one: how fast it moves over the ground
function Meter(int i, float DeltaTime, float Speed)
{
	local vector L, R, Foot;
	local name Bone;
	local float F;

	if (Speed < 80)
	{
		Bodies[i].LastFootBone = '';
		return;
	}
	L = Bodies[i].P.GetBoneCoords('leftFoot').Origin;
	R = Bodies[i].P.GetBoneCoords('rightFoot').Origin;
	if (L == vect(0,0,0) || R == vect(0,0,0))
		return;                     // no such bones on this skeleton
	if (Abs(L.Z - R.Z) < 3 && Bodies[i].LastFootBone != '')
	{
		// feet level (both down, or crossing): the planted one stays the one it was
		if (Bodies[i].LastFootBone == 'leftFoot')
			Foot = L;
		else
			Foot = R;
		Bone = Bodies[i].LastFootBone;
	}
	else if (L.Z < R.Z)
	{
		Bone = 'leftFoot';
		Foot = L;
	}
	else
	{
		Bone = 'rightFoot';
		Foot = R;
	}
	// one sample per footfall: the slowest the planted (lower) foot moved over the ground while it
	// was the lower one. A foot that grips the floor stops (about 0); a skating one never does.
	if (Bone == Bodies[i].LastFootBone)
	{
		F = VSize((Foot - Bodies[i].LastFoot) * vect(1,1,0)) / DeltaTime;
		Bodies[i].SlipSum += ((Foot - Bodies[i].LastFoot) / DeltaTime) dot Normal(Bodies[i].P.Velocity * vect(1,1,0));
		Bodies[i].SlipN++;
		if (F < Bodies[i].ContactMin)
		{
			Bodies[i].ContactMin = F;
			Bodies[i].ContactSpeed = Speed;
		}
	}
	else
	{
		if (Bodies[i].LastFootBone != '' && Bodies[i].ContactMin < 100000)
		{
			if (PlayerController(Bodies[i].P.Controller) != None)
			{
				SlideSumP += Bodies[i].ContactMin;
				SpeedSumP += Bodies[i].ContactSpeed;
				SlideNP++;
			}
			else
			{
				SlideSum += Bodies[i].ContactMin;
				SpeedSum += Bodies[i].ContactSpeed;
				SlideN++;
			}
		}
		if (bStrideMatch && Bodies[i].SlipN >= 3 && PlayerController(Bodies[i].P.Controller) == None)
			Stride(i, Bodies[i].SlipSum / Bodies[i].SlipN, Speed);
		Bodies[i].ContactMin = 1000000;
		Bodies[i].SlipSum = 0;
		Bodies[i].SlipN = 0;
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
	bSlideMeter=False
	LeanSign=1
	bStrideMatch=True
	StrideGain=0.35
}
