//=============================================================================
// ModBody - creatures' bodies that show what they feel and stand on the ground they're on
// (report "Dynamic body kinematics and adaptive animation", slices K1, K2, K5). One per level
// (ModMoves spawns it). Write-only layers over the game's clips (bone reads from script are only
// reliable on some skeletons, see the K0 bone test), each a critically damped spring toward a pose
// offset so nothing snaps:
//   - Seekers (four arms): the front pair of arms shows the feelings ModMinds keeps: anger spreads
//     and raises them (a threat display), fear pulls them in and down across the body; the two
//     arms move out of step with each other, so the pair reads as alive;
//   - hounds: anger drops the head forward and opens the jaw (a snarl), fear hunches the neck
//     down and back; and the body pitches to the slope under it (front and back ground traces),
//     on the hips, since the engine owns the hound's spine;
// A body ModReact is flinching keeps its flinch (these layers wait). Config [AdventMod.ModBody]:
// bSeekerArms, bHoundBody, bGroundPitch, PoseGain (1 = as designed), bBodyLog.
//=============================================================================
class ModBody extends Info
	config(AdventMod);

var config bool bSeekerArms, bHoundBody, bGroundPitch, bBodyLog;
var config float PoseGain;
var config float Spring;            // 1/s

struct Pose
{
	var Pawn P;
	var float A[6], V[6];           // spring states: 0..3 pose channels, 4 ground pitch, 5 spare
	var float Phase;                // the off-step arm's delay
};
var array<Pose> Poses;
var ModMinds Minds;
var ModReact React;
var float LogWait;

// K1: one critically damped spring step toward Want (state X with velocity V)
static function SpringTo(out float X, out float V, float Want, float K, float DeltaTime)
{
	V += (K * K * (Want - X) - 2 * K * V) * DeltaTime;
	X += V * DeltaTime;
}

static function int Deg(float D)
{
	return int(D * 182.04);
}

function int Find(Pawn P)
{
	local int i;

	for (i = 0; i < Poses.Length; i++)
		if (Poses[i].P == P)
			return i;
	Poses.Length = Poses.Length + 1;
	Poses[i].P = P;
	Poses[i].Phase = FRand() * 0.4;
	return i;
}

function Tick(float DeltaTime)
{
	local int i;
	local ModMind M;
	local Pawn P;

	if (DeltaTime <= 0 || DeltaTime > 0.2)
		return;
	if (Minds == None)
		foreach DynamicActors(class'ModMinds', Minds)
			break;
	if (React == None)
		foreach DynamicActors(class'ModReact', React)
			break;
	if (Minds == None)
		return;
	for (i = 0; i < Minds.Minds.Length; i++)
	{
		M = Minds.Minds[i];
		P = M.P;
		if (P == None || P.bDeleteMe || P.Health <= 0 || P.Physics == PHYS_KarmaRagdoll)
			continue;
		if (React != None && React.IsFlinching(P))
			continue;
		if (M.Species == 3/*S_Hound*/ && bHoundBody)
			Hound(M, Find(P), DeltaTime);
		else if ((M.Species == 1/*S_Seeker*/ || M.Species == 2/*S_SeekerVet*/) && bSeekerArms)
			Seeker(M, Find(P), DeltaTime);
	}
	for (i = Poses.Length - 1; i >= 0; i--)
		if (Poses[i].P == None || Poses[i].P.bDeleteMe)
			Poses.Remove(i, 1);
}

// the front arms: anger spreads and lifts them, fear tucks them across the body
function Seeker(ModMind M, int i, float DeltaTime)
{
	local float Spread, Lift, Lag;
	local rotator R;

	Spread = PoseGain * (28 * M.Anger - 18 * M.Fear);
	Lift = PoseGain * (22 * M.Anger - 14 * M.Fear);
	// the left arm follows the right a moment late (its spring is slower)
	Lag = 1.0 / (1.0 + Poses[i].Phase * 4);
	SpringTo(Poses[i].A[0], Poses[i].V[0], Spread, Spring, DeltaTime);
	SpringTo(Poses[i].A[1], Poses[i].V[1], Lift, Spring, DeltaTime);
	SpringTo(Poses[i].A[2], Poses[i].V[2], Spread, Spring * Lag, DeltaTime);
	SpringTo(Poses[i].A[3], Poses[i].V[3], Lift, Spring * Lag, DeltaTime);
	R.Yaw = Deg(Poses[i].A[0]);
	R.Pitch = Deg(Poses[i].A[1]);
	R.Roll = 0;
	M.P.SetBoneRotation('RightFrontArm', R, 0, 1);
	R.Yaw = Deg(-Poses[i].A[2]);
	R.Pitch = Deg(Poses[i].A[3]);
	M.P.SetBoneRotation('LeftFrontArm', R, 0, 1);
	Note(M, "arms spread " $ int(Poses[i].A[0]) $ " lift " $ int(Poses[i].A[1]));
}

// the hound: snarl or hunch, and pitch to the ground
function Hound(ModMind M, int i, float DeltaTime)
{
	local float HeadDown, Jaw, Pitch, Front, Back;
	local vector X, Y, Z, HitLoc, HitNorm;
	local rotator R;

	HeadDown = PoseGain * (18 * M.Anger + 14 * M.Fear);
	Jaw = PoseGain * 25 * FMax(M.Anger - 0.3, 0);
	SpringTo(Poses[i].A[0], Poses[i].V[0], HeadDown, Spring, DeltaTime);
	SpringTo(Poses[i].A[1], Poses[i].V[1], Jaw, Spring * 1.5, DeltaTime);
	// fear pulls the neck back too (a cower), anger pushes it forward
	SpringTo(Poses[i].A[2], Poses[i].V[2], PoseGain * (10 * M.Anger - 16 * M.Fear), Spring, DeltaTime);
	R = rot(0,0,0);
	R.Pitch = Deg(-Poses[i].A[0]);
	M.P.SetBoneRotation('Neck02', R, 0, 1);
	R.Pitch = Deg(-Poses[i].A[1]);
	M.P.SetBoneRotation('jaw', R, 0, 1);
	if (bGroundPitch && M.P.Physics == PHYS_Walking)
	{
		// the ground's height under the front and the back legs
		GetAxes(M.P.Rotation, X, Y, Z);
		X.Z = 0;
		X = Normal(X);
		Front = Ground(M.P.Location + X * 45, M.P);
		Back = Ground(M.P.Location - X * 45, M.P);
		Pitch = 0;
		if (Front > -100000 && Back > -100000)
			Pitch = FClamp(Atan(Front - Back, 90.0) * 57.2958, -25, 25);
		SpringTo(Poses[i].A[4], Poses[i].V[4], Pitch, Spring, DeltaTime);
		R = rot(0,0,0);
		R.Pitch = Deg(Poses[i].A[4]);
		M.P.SetBoneRotation('hips', R, 0, 1);
	}
	Note(M, "head down " $ int(Poses[i].A[0]) $ " jaw " $ int(Poses[i].A[1]) $ " ground pitch " $ int(Poses[i].A[4]));
}

function float Ground(vector At, Pawn P)
{
	local vector HitLoc, HitNorm;

	if (Trace(HitLoc, HitNorm, At - vect(0,0,1) * (P.CollisionHeight + 80), At + vect(0,0,30), false) == None)
		return -1000000;
	return HitLoc.Z;
}

function Note(ModMind M, string S)
{
	if (bBodyLog && Level.TimeSeconds > LogWait)
	{
		LogWait = Level.TimeSeconds + 2;
		class'ModSettings'.static.Note("body: " $ M.P.Name $ " (" $ M.SpeciesName $ ", anger " $ M.Pct(M.Anger) $ " fear " $ M.Pct(M.Fear) $ "): " $ S);
	}
}

defaultproperties
{
	bSeekerArms=True
	bHoundBody=True
	bGroundPitch=True
	bBodyLog=False
	PoseGain=1.0
	Spring=6
}
