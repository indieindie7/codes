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
var config bool bDeathAnims;       // play a death clip first, ragdoll partway through it
var config float DeathAnimHandoff; // seconds into the clip the body goes limp (a clip without its own time)
var config bool bDeathAnimRagdoll; // go limp partway through a death clip. Off: the clip plays out and the body lies as it ends (a ragdoll begun from a clip crashed the game twice)
var config string TestClip;        // testing: always this clip
var name ClipName;                 // a name from a string (SetPropertyText)

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
	var float AnimT;       // >= 0: playing a death clip for this long
	var float Handoff;     // the clip's own time to go limp
	var float Length;      // and how long it runs
	var vector Start;      // testing: where and how the body stood when the clip began
	var rotator Facing;
	var class<DamageType> Type;
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
		// a death the level scripts (plain DamageType, or a pawn mid script sequence: every AI is a
		// ScriptedController, so it's the Scripting state that tells): the
		// level goes on using the body, so it keeps the game's own death (a scripted
		// marine death ragdolled crashed the game in level03sectionb)
		if (DamageType == class'DamageType' || DamageType == None || (Victim.Controller != None && Victim.Controller.IsInState('Scripting')))
		{
			if (class'ModSettings'.default.bGoreLog)
				class'ModSettings'.static.Note("react: " $ Victim $ " dies by script (" $ DamageType $ ", " $ Victim.Controller $ "): no clip, no ragdoll");
			return;
		}
		if (bDeathRagdoll)
			AddDeath(Victim, Dir, HitLocation, DamageType);
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

function AddDeath(Pawn P, vector Dir, vector Spot, class<DamageType> Type)
{
	local int i;
	local DeathState S;

	for (i = 0; i < Deaths.Length; i++)
		if (Deaths[i].P == P)
			return;
	S.P = P;
	S.Dir = Dir;
	S.Spot = Spot;
	S.AnimT = -1;
	S.Type = Type;
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
		if (P == None || P.bDeleteMe || P.bHidden || P.Physics == PHYS_KarmaRagdoll || (Deaths[i].T > 0.6 && Deaths[i].AnimT < 0) || P.Health > 0 && Deaths[i].T > 0.2)
		{
			Deaths.Remove(i, 1);
			continue;
		}
		if (Deaths[i].AnimT >= 0)
		{
			// the game's "floating body" check takes a body mid clip for one to erase
			// (it faded standing up as the ragdoll began)
			if (AdventPawn(P) != None)
				AdventPawn(P).shouldCheckForQuickDeadFade = false;
			// testing: where the clip put the limbs, in the body's own frame (X forward,
			// Z up), just before the handoff
			if (class'ModSettings'.default.bGoreLog && Deaths[i].AnimT < Deaths[i].Handoff - 0.1 && Deaths[i].AnimT + DeltaTime >= Deaths[i].Handoff - 0.1)
				PoseLog(P);
			// testing: how the clip moves the body (the actor, and the hips over it), in
			// the frame the body died in, five times a second
			if (class'ModSettings'.default.bGoreLog && int(Deaths[i].AnimT * 5) != int((Deaths[i].AnimT + DeltaTime) * 5))
				class'ModSettings'.static.Note("react: move " $ P $ " t " $ Deaths[i].AnimT $ " actor " $ ((P.Location - Deaths[i].Start) << Deaths[i].Facing) $ " hips " $ ((P.GetBoneCoords('hips').Origin - Deaths[i].Start) << Deaths[i].Facing) $ " physics " $ P.Physics $ " hips over floor " $ OverFloor(P, 'hips') $ " head " $ OverFloor(P, 'head') $ " actor " $ int(P.Location.Z - P.GetBoneCoords('hips').Origin.Z + OverFloor(P, 'hips')) $ " collision " $ P.CollisionHeight);
			Deaths[i].AnimT += DeltaTime;
			if (Deaths[i].AnimT < Deaths[i].Handoff)
				continue;
			if (!bDeathAnimRagdoll)
			{
				// the clip plays out; the body stays in its last pose
				if (Deaths[i].AnimT >= Deaths[i].Length + 0.5)
					Deaths.Remove(i, 1);
				continue;
			}
		}
		else if (P.IsInState('Dying') && bDeathAnims)
		{
			Deaths[i].Handoff = DeathAnim(P, Deaths[i].Spot, Deaths[i].Dir, Deaths[i].Type, Deaths[i].Length);
			if (Deaths[i].Handoff > 0)
			{
				Deaths[i].Start = P.Location;
				Deaths[i].Facing = P.Rotation;
				Deaths[i].AnimT = 0;
				continue;
			}
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

// how high a bone is over the floor under it
function int OverFloor(Pawn P, name Bone)
{
	local vector O, HitL, HitN;

	O = P.GetBoneCoords(Bone).Origin;
	if (Trace(HitL, HitN, O - vect(0,0,400), O + vect(0,0,30), false) == None)
		return 999;
	return int(O.Z - HitL.Z);
}

function string Rel(Pawn P, name A, name B)
{
	local vector V;

	V = (P.GetBoneCoords(B).Origin - P.GetBoneCoords(A).Origin) << P.Rotation;
	return string(A) $ "->" $ string(B) $ " " $ int(V.X) $ "," $ int(V.Y) $ "," $ int(V.Z);
}

function PoseLog(Pawn P)
{
	class'ModSettings'.static.Note("react: pose " $ P $ ": " $ Rel(P, 'hips', 'head') $ " | " $ Rel(P, 'hips', 'leftUpLeg') $ " | " $ Rel(P, 'leftUpLeg', 'leftLeg') $ " | " $ Rel(P, 'leftLeg', 'leftFoot') $ " | " $ Rel(P, 'rightUpLeg', 'rightLeg') $ " | " $ Rel(P, 'rightLeg', 'rightFoot') $ " | " $ Rel(P, 'leftArm', 'lefthand') $ " | " $ Rel(P, 'rightArm', 'righthand') $ " | hips over feet " $ int(P.GetBoneCoords('hips').Origin.Z - P.GetBoneCoords('leftFoot').Origin.Z));
}

// which kind of death clip a killing blow asks for (ModDeathClips' zones): a blast, a
// shot in the back, or the part of the body hit
function string DeathZone(Pawn P, vector Spot, vector Dir, class<DamageType> Type)
{
	local string N;
	local int i, Best;
	local float D, BestD;
	local coords C;
	local vector X, Y, Z;

	if (Type != None)
	{
		N = Caps(string(Type.Name));
		if (InStr(N, "EXPLOSION") >= 0 || InStr(N, "GRENADE") >= 0 || InStr(N, "LAUNCHER") >= 0 || InStr(N, "MISSLE") >= 0)
			return "blast";
	}
	GetAxes(P.Rotation, X, Y, Z);
	BestD = 1000000;
	Best = -1;
	for (i = 0; i < 12; i++)
	{
		C = P.GetBoneCoords(Bones[i]);
		if (C.Origin == vect(0,0,0))
			continue;
		D = VSize(C.Origin - Spot);
		if (D < BestD)
		{
			BestD = D;
			Best = i;
		}
	}
	if (Best < 0)
		return "chest";
	N = Caps(string(Bones[Best]));
	if (N == "HEAD" || N == "NECK")
		return "head";
	if (InStr(N, "LEG") >= 0)
	{
		if (Left(N, 4) == "LEFT")
			return "legleft";
		return "legright";
	}
	// the torso from behind
	if ((Dir Dot X) > 0.3)
		return "back";
	if (InStr(N, "ARM") >= 0)
	{
		if (Left(N, 4) == "LEFT")
			return "shoulderleft";
		return "shoulderright";
	}
	if (N == "HIPS" || N == "SPINE")
		return "gut";
	return "chest";
}

// a death clip (ModDeathAnims) on a body with the human skeleton: one for the hit's
// zone, at random. Returns when the body should go limp (seconds in), 0 if none plays.
function float DeathAnim(Pawn P, vector Spot, vector Dir, class<DamageType> Type, out float Length)
{
	local MeshAnimation A;
	local class<ModDeathClips> T;
	local string Zone;
	local int i, n, Pick;
	local float Handoff;

	if (AdventPawn(P) == None || Gore == None || Gore.RagdollSkeleton(AdventPawn(P)) != "humanMale2")
		return 0;
	A = class'ModDeathAnims'.default.Deaths;
	if (A == None)
		return 0;
	P.LinkSkelAnim(A);
	T = class'ModDeathClips';
	Handoff = DeathAnimHandoff;
	Length = 4;
	if (TestClip != "")
		SetPropertyText("ClipName", TestClip);
	else
	{
		Zone = DeathZone(P, Spot, Dir, Type);
		for (i = 0; i < T.default.Clips.Length; i++)
			if (T.default.Clips[i].Zone == Zone)
				n++;
		if (n == 0)
		{
			// none for this hit: any clip
			Zone = "";
			n = T.default.Clips.Length;
		}
		if (n == 0)
			return 0;
		Pick = Rand(n);
		for (i = 0; i < T.default.Clips.Length; i++)
			if (Zone == "" || T.default.Clips[i].Zone == Zone)
			{
				if (Pick == 0)
					break;
				Pick--;
			}
		ClipName = T.default.Clips[i].Clip;
		Handoff = T.default.Clips[i].Handoff;
		Length = T.default.Clips[i].Length;
	}
	if (!P.HasAnim(ClipName))
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("react: " $ P $ " (" $ P.Mesh $ ") has no death clip " $ ClipName);
		return 0;
	}
	P.AnimBlendParams(1, 0.0);
	P.PlayAnim(ClipName, 1.0, 0.1, 0);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " plays " $ ClipName $ " (" $ Zone $ "), limp in " $ Handoff $ " s");
	return Handoff;
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
		// testing: how the ragdoll falls, twice a second
		if (class'ModSettings'.default.bGoreLog && int(Ragdolls[i].T * 2) != int((Ragdolls[i].T + DeltaTime) * 2))
			class'ModSettings'.static.Note("react: ragdoll " $ P $ " t " $ Ragdolls[i].T $ " hips " $ int(P.GetBoneCoords('hips').Origin.Z - Ragdolls[i].FloorZ) $ " head " $ int(P.GetBoneCoords('head').Origin.Z - Ragdolls[i].FloorZ) $ " over floor, awake " $ P.KIsAwake());
		Ragdolls[i].T += DeltaTime;
		Low = FMin(P.GetBoneCoords('hips').Origin.Z, P.GetBoneCoords('head').Origin.Z);
		Why = "";
		// not in its first moments: a body handed over from a death clip starts low
		// (kneeling), and its bones read wrong for a tick or two
		if (Low < Ragdolls[i].FloorZ + 2 && Ragdolls[i].T > 0.3)
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
     DeathAnimHandoff=0.900000
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
