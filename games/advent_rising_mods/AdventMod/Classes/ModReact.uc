//=============================================================================
// ModReact - how a body takes a hit (ModGoreRules hands it every hit, ModGore
// spawns it):
//   - flinch: the bone nearest the hit jerks away from the shot and eases back
//     (SetBoneRotation over the animation, FlinchTime long);
//   - stagger: a hit of StaggerDamage or more pushes the victim back a step and
//     slows it for StaggerTime (bosses don't stagger);
//   - ragdoll on death: the body goes limp at the killing blow. The PC release
//     ships no KarmaData\*.ka ragdoll skeletons; AdventMod brings its own
//     (KarmaData\Advent.ka from tools/make_ka.py, installed by build.ps1).
//   - a corpse shot twitches: the bone nearest the hit jerks (CorpseFlinch).
// Only characters the AI drives; not the player, vehicles or turrets.
//=============================================================================
class ModReact extends Info
	config(AdventMod);

var config bool bFlinch;
var config float FlinchAngle;      // rotation units for a 40-damage hit
var config float FlinchTime;
var config bool bStagger;
var config int StaggerDamage;
var config float StaggerPush, StaggerSlow, StaggerTime;
var config bool bDeathRagdoll;
var config int MaxRagdolls;

var ModGore Gore;

struct FlinchState
{
	var Pawn P;
	var name Bone;
	var rotator Turn;
	var float T;
	var bool bCorpse;      // on a dead body: not cut short by the death
};
var array<FlinchState> Flinches;

struct StaggerState
{
	var Pawn P;
	var float T, Speed;
};
var array<StaggerState> Staggers;

// a body in ragdoll: where its floor was when it fell. Some floors (static meshes
// without Karma collision) don't stop a ragdoll, and a body that drops out of the
// world is destroyed, which leaves its squad a member short (the waves stall). So a
// ragdoll is frozen (KFreezeRagdoll) as soon as it reaches its floor height, once it
// stops moving, or after RagdollTime. Its "floating body" check (which reads the
// ragdoll as floating and erases it at once) is kept off meanwhile.
struct RagdollState
{
	var Pawn P;
	var float FloorZ, T;
	var bool bFrozen;      // still watched: the engine may switch it to falling
};
var array<RagdollState> Ragdolls;
var config float RagdollTime;

struct DeathState
{
	var Pawn P;
	var vector Dir, Spot;
	var float T;
};
var array<DeathState> Deaths;

var name Bones[12];                // bones humans and Seekers both have

event PostBeginPlay()
{
	Super.PostBeginPlay();
	if (Level.MaxRagdolls < MaxRagdolls)
		Level.MaxRagdolls = MaxRagdolls;
}

function bool Reacts(Pawn P)
{
	return P != None && !P.bDeleteMe && !P.bHidden && !P.IsHumanControlled() && !P.IsA('Vehicle') && !P.IsA('Turret') && AdventPawn(P) != None;
}

function Hit(Pawn Victim, vector HitLocation, vector Momentum, int Damage, class<DamageType> DamageType, vector ShotDir)
{
	local vector Dir;

	if (!Reacts(Victim) || Damage <= 0)
		return;
	Dir = ShotDir;
	if (VSize(Momentum) > 1)
		Dir = Normal(Momentum);
	if (Victim.Health <= 0 || Damage >= Victim.Health)
	{
		if (bDeathRagdoll)
			AddDeath(Victim, Dir, HitLocation);
		return;
	}
	if (bFlinch)
		Flinch(Victim, HitLocation, Dir, Damage, false);
	if (bStagger && Damage >= StaggerDamage && Victim.iBaseTargetingPriority < 255)
		Stagger(Victim, Dir);
}

// a corpse hit: a twitch, a little stronger than a living flinch
function CorpseFlinch(Pawn P, vector HitLocation, vector Dir)
{
	if (bFlinch && P != None && !P.bHidden)
		Flinch(P, HitLocation, Dir, 70, true);
}

// the bone nearest the hit, turned away from the shot (into the pawn's own frame)
function Flinch(Pawn P, vector HitLocation, vector Dir, int Damage, optional bool bCorpse)
{
	local int i, Best;
	local float D, BestD;
	local vector L;
	local coords C;
	local FlinchState F;
	local float A;

	BestD = 1000000;
	Best = -1;
	for (i = 0; i < 12; i++)
	{
		C = P.GetBoneCoords(Bones[i]);
		if (C.Origin == vect(0,0,0))
			continue;
		D = VSize(C.Origin - HitLocation);
		if (D < BestD)
		{
			BestD = D;
			Best = i;
		}
	}
	if (Best < 0)
		return;
	for (i = Flinches.Length - 1; i >= 0; i--)
		if (Flinches[i].P == P)
		{
			P.SetBoneRotation(Flinches[i].Bone, rot(0,0,0), 0, 0);
			Flinches.Remove(i, 1);
		}
	A = FlinchAngle * FClamp(Damage / 40.0, 0.4, 1.6);
	L = Dir << P.Rotation;
	F.P = P;
	F.bCorpse = bCorpse;
	F.Bone = Bones[Best];
	F.Turn.Pitch = int(-L.X * A);
	F.Turn.Roll = int(L.Y * A);
	F.Turn.Yaw = int((FRand() - 0.5) * A * 0.4);
	Flinches[Flinches.Length] = F;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " flinches at " $ F.Bone $ " " $ F.Turn);
}

function Stagger(Pawn P, vector Dir)
{
	local int i;
	local StaggerState S;

	Dir.Z = 0;
	if (P.Physics == PHYS_Walking)
		P.Velocity += Normal(Dir) * StaggerPush;
	for (i = 0; i < Staggers.Length; i++)
		if (Staggers[i].P == P)
		{
			Staggers[i].T = 0;
			return;
		}
	S.P = P;
	S.Speed = P.GroundSpeed;
	Staggers[Staggers.Length] = S;
	P.GroundSpeed = S.Speed * StaggerSlow;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " staggers");
}

function AddDeath(Pawn P, vector Dir, vector Spot)
{
	local int i;
	local DeathState S;

	for (i = 0; i < Deaths.Length; i++)
		if (Deaths[i].P == P)
			return;
	S.P = P;
	S.Dir = Dir;
	S.Spot = Spot;
	Deaths[Deaths.Length] = S;
}

event Tick(float DeltaTime)
{
	local int i;
	local float Alpha;
	local Pawn P;

	for (i = Flinches.Length - 1; i >= 0; i--)
	{
		P = Flinches[i].P;
		Flinches[i].T += DeltaTime;
		if (P == None || P.bDeleteMe)
		{
			Flinches.Remove(i, 1);
			continue;
		}
		if (Flinches[i].T >= FlinchTime || (P.Health <= 0 && !Flinches[i].bCorpse))
		{
			P.SetBoneRotation(Flinches[i].Bone, rot(0,0,0), 0, 0);
			Flinches.Remove(i, 1);
			continue;
		}
		// a snap in (60 ms), then easing back
		if (Flinches[i].T < 0.06)
			Alpha = Flinches[i].T / 0.06;
		else
			Alpha = 1 - (Flinches[i].T - 0.06) / (FlinchTime - 0.06);
		Alpha = Alpha * Alpha * (3 - 2 * Alpha);
		P.SetBoneRotation(Flinches[i].Bone, Flinches[i].Turn, 0, Alpha);
	}
	for (i = Staggers.Length - 1; i >= 0; i--)
	{
		P = Staggers[i].P;
		Staggers[i].T += DeltaTime;
		if (P == None || P.bDeleteMe)
		{
			Staggers.Remove(i, 1);
			continue;
		}
		if (Staggers[i].T >= StaggerTime || P.Health <= 0)
		{
			P.GroundSpeed = Staggers[i].Speed;
			Staggers.Remove(i, 1);
		}
	}
	// a killing blow: once the pawn is in its death state, limp
	for (i = Deaths.Length - 1; i >= 0; i--)
	{
		P = Deaths[i].P;
		Deaths[i].T += DeltaTime;
		if (P == None || P.bDeleteMe || P.bHidden || P.Physics == PHYS_KarmaRagdoll || Deaths[i].T > 0.6 || P.Health > 0 && Deaths[i].T > 0.2)
		{
			Deaths.Remove(i, 1);
			continue;
		}
		if (P.IsInState('Dying') && Gore != None)
		{
			Gore.Limp(P, Deaths[i].Dir, Deaths[i].Spot);
			if (P.Physics == PHYS_KarmaRagdoll)
				AddRagdoll(P);
			Deaths.Remove(i, 1);
		}
	}
	WatchRagdolls(DeltaTime);
}

function AddRagdoll(Pawn P)
{
	local RagdollState R;
	local vector HitL, HitN;
	local Actor Floor;

	R.P = P;
	R.FloorZ = P.Location.Z - P.CollisionHeight;
	Floor = Trace(HitL, HitN, P.Location - vect(0,0,1) * (P.CollisionHeight + 300), P.Location, false);
	if (Floor != None)
		R.FloorZ = HitL.Z;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " ragdoll over " $ Floor $ " (" $ Floor.Class $ ", static mesh " $ Floor.StaticMesh $ ")");
	Ragdolls[Ragdolls.Length] = R;
	if (AdventPawn(P) != None)
		AdventPawn(P).shouldCheckForQuickDeadFade = false;
}

function WatchRagdolls(float DeltaTime)
{
	local int i;
	local Pawn P;
	local float Low;
	local string Why;

	for (i = Ragdolls.Length - 1; i >= 0; i--)
	{
		P = Ragdolls[i].P;
		// gone, or the game took the body back (recycled for a squad)
		if (P == None || P.bDeleteMe || P.Health > 0 || !P.IsInState('Dying'))
		{
			Ragdolls.Remove(i, 1);
			continue;
		}
		if (AdventPawn(P) != None)
			AdventPawn(P).shouldCheckForQuickDeadFade = false;
		// a frozen ragdoll (ours, or the engine's own once it comes to rest) is left
		// PHYS_Falling with no world collision: it would drop through the floor and out
		// of the world. Nothing moves it: it stays where it lies.
		if (P.Physics == PHYS_Falling && !P.bCollideWorld)
		{
			P.SetPhysics(PHYS_None);
			P.Velocity = vect(0,0,0);
			if (class'ModSettings'.default.bGoreLog && !Ragdolls[i].bFrozen)
				class'ModSettings'.static.Note("react: " $ P $ " held in place (frozen ragdoll was falling)");
			Ragdolls[i].bFrozen = true;
			continue;
		}
		if (Ragdolls[i].bFrozen || P.Physics != PHYS_KarmaRagdoll)
			continue;
		Ragdolls[i].T += DeltaTime;
		Low = FMin(P.GetBoneCoords('hips').Origin.Z, P.GetBoneCoords('head').Origin.Z);
		Why = "";
		if (Low < Ragdolls[i].FloorZ + 2)
			Why = "at its floor";
		else if (Ragdolls[i].T > 0.8 && !P.KIsAwake())
			Why = "at rest";
		else if (Ragdolls[i].T > RagdollTime)
			Why = "time";
		if (Why == "")
			continue;
		P.KFreezeRagdoll();
		if (P.Physics == PHYS_Falling && !P.bCollideWorld)
		{
			P.SetPhysics(PHYS_None);
			P.Velocity = vect(0,0,0);
		}
		Ragdolls[i].bFrozen = true;
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("react: " $ P $ " ragdoll frozen (" $ Why $ ", " $ Ragdolls[i].T $ " s, low " $ int(Low - Ragdolls[i].FloorZ) $ " over floor), physics now " $ P.Physics);
	}
}

defaultproperties
{
     RagdollTime=4.000000
     bFlinch=True
     FlinchAngle=4500.000000
     FlinchTime=0.300000
     bStagger=True
     StaggerDamage=40
     StaggerPush=260.000000
     StaggerSlow=0.350000
     StaggerTime=0.450000
     bDeathRagdoll=True
     MaxRagdolls=8
     Bones(0)=hips
     Bones(1)=spine
     Bones(2)=spine1
     Bones(3)=spine2
     Bones(4)=neck
     Bones(5)=head
     Bones(6)=rightArm
     Bones(7)=rightForeArm
     Bones(8)=leftArm
     Bones(9)=leftForeArm
     Bones(10)=rightUpLeg
     Bones(11)=leftUpLeg
}
