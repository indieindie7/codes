//=============================================================================
// ModAction - Gideon moving through the world, in the spirit of Max Payne 3 and Stranglehold
// (research_notes/Third person action movement; no slow motion). The player's pawn class isn't
// ours, so this ticks beside it and reads what it does (physics, the full-body animation,
// how it moved since the last tick), then plays the game's own animations on it:
//   - vault: running at waist-high cover (a knee-height trace hits it, chest height is clear,
//     its top is 30-85 units up and there is room beyond), Gideon hand-plants over it
//     (HandPlant_Mid / HandPlant_High, the pawn's own PlayHopLedge) carried by a hop over it;
//   - slam: a dodge or roll that runs into a wall stops against it: a slam reaction toward the
//     side that hit (R_LevSlam_F/B/L/R), a small bounce off it and a camera jolt;
//   - barge: running into a breakable prop shoulders it out of the way: the game's own kick
//     (KickActor + a hit, so it breaks or tumbles the way the prop is made to), a lean-back on
//     the upper body (r_pushBack) and a little jolt.
// Config [AdventMod.ModAction]: bVault, bSlam, bBarge, bActionLog.
//=============================================================================
class ModAction extends Info
	config(AdventMod);

var config bool bVault, bSlam, bBarge, bActionLog;
var config float VaultSpeed;        // how fast it must run to vault (units/s)
var config float BargeSpeed;
var config int BargeDamage;

var vector LastLoc;
var float Cool, VaultT;
var bool bVaulting;
var vector VaultLand;               // where the vault should come down (logged against where it did)
var int Vaults, Slams, Barges;

function Log2(string S)
{
	if (bActionLog)
		class'ModSettings'.static.Note("action: " $ S);
}

function Tick(float DeltaTime)
{
	local PlayerController PC;
	local Pawn P;
	local vector Moved, Fwd;
	local float Speed;
	local name Anim;
	local float Frame, Rate;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None || DeltaTime <= 0)
		return;
	P = PC.Pawn;
	Moved = (P.Location - LastLoc) / DeltaTime;
	LastLoc = P.Location;
	Moved.Z = 0;
	Speed = VSize(Moved);
	Cool -= DeltaTime;
	if (bVaulting)
	{
		VaultT += DeltaTime;
		if (P.Physics == PHYS_Walking && VaultT > 0.2)
		{
			bVaulting = false;
			P.SetAllowInput(true);
			Jolt(PC, 60, 0.15);
			Log2("vault landed after " $ VaultT $ " s, " $ int(VSize((P.Location - vect(0,0,1) * P.CollisionHeight - VaultLand) * vect(1,1,0))) $ " from the planned spot");
		}
		else if (VaultT > 1.5)
		{
			bVaulting = false;
			P.SetAllowInput(true);
		}
		return;
	}
	if (Cool > 0 || Speed < 50 || P.Health <= 0)
		return;
	Fwd = Normal(Moved);
	P.GetAnimParams(0, Anim, Frame, Rate);
	if (bSlam && IsDodge(Anim) && Speed > 300 && Slam(PC, P, Fwd, Speed))
		return;
	if (P.Physics != PHYS_Walking || P.bIsCrouched)
		return;
	if (bVault && Speed > VaultSpeed && Vault(P, Fwd, Speed))
		return;
	if (bBarge && Speed > BargeSpeed)
		Barge(PC, P, Fwd, Speed);
}

static function bool IsDodge(name A)
{
	local string S;

	S = Caps(string(A));
	return Left(S, 8) == "T_WALK_D" || Left(S, 9) == "T_FORCE_D" || Left(S, 13) == "T_WALKFORCE_D" || Left(S, 8) == "T_ROLL_D";
}

function Jolt(PlayerController PC, float Size, float Seconds)
{
	if (EonPlayerController(PC) != None && EonPlayerController(PC).Camera != None)
		EonPlayerController(PC).Camera.Shake(Size, Size, Size, 0, Seconds);
}

// waist-high cover ahead, running at it: over it
function bool Vault(Pawn P, vector Fwd, float Speed)
{
	local vector Feet, HitLoc, HitNorm, Top, TopNorm, Far;
	local Actor A;
	local float Height, Reach, Rise, G, Vz, Flight;
	local vector Land;

	Feet = P.Location - vect(0,0,1) * P.CollisionHeight;
	Reach = P.CollisionRadius + 45;
	A = Trace(HitLoc, HitNorm, Feet + vect(0,0,35) + Fwd * Reach, Feet + vect(0,0,35), false);
	if (A == None || Abs(HitNorm.Z) > 0.3 || (HitNorm dot Fwd) > -0.5)
		return false;               // nothing ahead at knee height, or not facing it
	if (!FastTrace(Feet + vect(0,0,100) + Fwd * (Reach + 40), Feet + vect(0,0,100)))
		return false;               // a wall, not cover: chest height is blocked too
	// its top, a little past the face
	Far = HitLoc + Fwd * 24;
	if (Trace(Top, TopNorm, Far - vect(0,0,10), Far + vect(0,0,110), false) == None)
		return false;
	Height = Top.Z - Feet.Z;
	if (Height < 30 || Height > 85 || TopNorm.Z < 0.7)
		return false;
	// room to land beyond it
	if (!FastTrace(Top + vect(0,0,1) * (P.CollisionHeight + 20) + Fwd * 120, Top + vect(0,0,1) * (P.CollisionHeight + 20)))
		return false;
	if (EonPawn(P) != None)
	{
		if (Height > 60)
			EonPawn(P).PlayHopLedge(0);
		else
			EonPawn(P).PlayHopLedge(1);
	}
	P.SetAllowInput(false);
	P.SetPhysics(PHYS_Falling);
	// K3 (warping, by velocity): rise just over the top, come down a body's width past the far face,
	// whatever the run-up speed was. Time up to clear the top, then the fall to the landing spot.
	Land = Top + Fwd * (Depth(Top, Fwd, P) + P.CollisionRadius + 30);
	Rise = Height + 25;                                   // the feet clear the top by 25
	G = Abs(P.PhysicsVolume.Gravity.Z);
	if (G < 100)
		G = 950;
	Vz = Sqrt(2 * G * Rise);
	Flight = Vz / G + Sqrt(2 * G * FMax(Rise - (Land.Z - Feet.Z), 1)) / G;
	P.Velocity = Fwd * FClamp(VSize((Land - Feet) * vect(1,1,0)) / Flight, 300, 900) + vect(0,0,1) * Vz;
	bVaulting = true;
	VaultT = 0;
	Cool = 0.8;
	Vaults++;
	Log2("vault over " $ A $ " (top " $ int(Height) $ " up) at speed " $ int(Speed) $ ", landing " $ int(VSize((Land - Feet) * vect(1,1,0))) $ " on in " $ Flight $ " s [" $ Vaults $ "]");
	VaultLand = Land;
	return true;
}

// how deep the cover is along Fwd from a point on its top (to land past its far face)
function float Depth(vector Top, vector Fwd, Pawn P)
{
	local vector HitLoc, HitNorm;
	local float D;

	for (D = 16; D < 160; D += 16)
		if (Trace(HitLoc, HitNorm, Top + Fwd * D - vect(0,0,8), Top + Fwd * D + vect(0,0,40), false) == None)
			return D;               // the top ends here
	return 160;
}

// a dodge running into a wall: it stops against it
function bool Slam(PlayerController PC, Pawn P, vector Fwd, float Speed)
{
	local vector HitLoc, HitNorm, X, Y, Z;
	local Actor A;
	local float F, R;
	local name Anim;

	A = Trace(HitLoc, HitNorm, P.Location + Fwd * (P.CollisionRadius + 30), P.Location, false);
	if (A == None || Abs(HitNorm.Z) > 0.4)
		return false;
	// which side of the body met the wall
	GetAxes(P.Rotation, X, Y, Z);
	F = -HitNorm dot X;
	R = -HitNorm dot Y;
	if (Abs(F) > Abs(R))
	{
		if (F > 0)
			Anim = 'R_LevSlam_F';
		else
			Anim = 'R_LevSlam_B';
	}
	else if (R > 0)
		Anim = 'R_LevSlam_R';
	else
		Anim = 'R_LevSlam_L';
	P.SetPhysics(PHYS_Falling);
	P.Velocity = HitNorm * FMin(Speed * 0.35, 220) + vect(0,0,120);
	if (EonPawn(P) != None)
		EonPawn(P).PlayEonAnim(false, Anim, 0, 1.0);
	Jolt(PC, 250, 0.4);
	Cool = 1.2;
	Slams++;
	Log2("dodge slammed into " $ A $ " at " $ int(Speed) $ ": " $ Anim $ " [" $ Slams $ "]");
	return true;
}

// running into a breakable prop: shoulder it away
function Barge(PlayerController PC, Pawn P, vector Fwd, float Speed)
{
	local DamageableObjects D;
	local vector To;

	foreach RadiusActors(class'DamageableObjects', D, P.CollisionRadius + 90, P.Location)
	{
		To = D.Location - P.Location;
		To.Z = 0;
		if ((Normal(To) dot Fwd) < 0.6)
			continue;               // not in the way
		D.KickActor(Fwd);
		D.TakeDamage(BargeDamage, P, D.Location, Fwd * 30000, class'DamageType');
		if (EonPawn(P) != None)
			EonPawn(P).PlayEonAnim(false, 'r_pushBack', 28, 1.4);
		Jolt(PC, 90, 0.2);
		Cool = 0.5;
		Barges++;
		Log2("barged " $ D $ " at " $ int(Speed) $ " [" $ Barges $ "]");
		return;
	}
}

defaultproperties
{
	bVault=True
	bSlam=True
	bBarge=True
	bActionLog=False
	VaultSpeed=330
	BargeSpeed=380
	BargeDamage=25
}
