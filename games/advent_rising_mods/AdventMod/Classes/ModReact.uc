//=============================================================================
// ModReact - how a body takes a hit (ModGoreRules hands it every hit, ModGore
// spawns it):
//   - flinch: the bone nearest the hit jerks away from the shot and eases back
//     (SetBoneRotation over the animation, FlinchTime long);
//   - stagger: a hit of StaggerDamage or more pushes the victim back a step, slows it
//     for StaggerTime and leans its spine away from the hit (SetBoneRotation: a quick
//     lean in, held, eased back over the last part; the meshes have no stagger clip,
//     the Seekers not even a hit clip). Bosses don't stagger;
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
// flesh: the flinch as a damped spring (the bone snaps away, swings back past rest and settles)
// and a ripple into the next bone up the body, a moment later and weaker
var config bool bSpringFlinch;
var config float SpringFreq, SpringDecay, SpringTime, RippleShare, RippleDelay;
var config bool bStagger;
var config int StaggerDamage;
var config float StaggerPush, StaggerSlow, StaggerTime;
var config float StaggerLean;      // rotation units the spine leans away from the hit (65536 = a turn)
var config bool bDeathRagdoll;
var config int MaxRagdolls;
var config float KarmaTimeScale, RagdollTimeScale;   // the level's physics speed (the game ships 0.9 / 1.0; 0 = leave)
var config bool bDeathAnims;       // play a death clip first, ragdoll partway through it
var config float DeathAnimHandoff; // seconds into the clip the body goes limp (a clip without its own time)
var config bool bDeathAnimRagdoll; // go limp partway through a death clip. Off: the clip plays out and the body lies as it ends (a ragdoll begun from a clip crashed the game twice)
var config bool bClipFloor;        // a body in a death clip is kept on the floor under it (stairs, slopes)
struct ClipBody
{
	var Pawn P;
	var vector Pivot;      // its own draw offset, to put back
};
var array<ClipBody> ClipBodies;
var name FloorBones[8];
var config string TestClip;        // testing: always this clip
var name ClipName;                 // a name from a string (SetPropertyText)

var ModGore Gore;
var ModJiggle Jiggle;          // the flesh springs (JIGGLE.md), found when first needed

struct FlinchState
{
	var Pawn P;
	var name Bone;
	var rotator Turn;
	var float T;
	var bool bCorpse;      // on a dead body: not cut short by the death
	var name Bone2;        // the spring flinch's ripple (None: none)
	var rotator Turn2;
	var name Bone3;        // ... and one bone further, weaker and later (the hit travels through the body)
	var rotator Turn3;
};
var array<FlinchState> Flinches;
var array<name> AnimProbed;
var config array<name> ProbeNames;   // ProbeAnims tries these too (an ini list, for surveying a character's set)
// knockdowns: a heavy hit that doesn't kill throws the character down with the game's own
// impact animation (Death_Impact: Seekers and humans both have it), it lies there a moment
// and gets up with GetUp_back / GetUp_front; the spring flinch rides on top
var config bool bKnockdown;
var config int KnockDamage;        // a single hit this big (after the game's scaling) knocks down
var config float KnockChance;      // ...this often
var config float KnockDown, KnockGetUp;   // seconds lying, seconds the get-up takes
var config float KnockPush;
var int Impact;                    // the current hit before armour (ModGoreRules sets it)
struct DownState
{
	var Pawn P;
	var float T, Speed;
	var int Phase;          // 0 falling and lying, 1 getting up
	var name Fall, Up;      // the fall (held on its last frame while lying) and the get-up
	var bool bOwnClips;     // ours (ModHoundAnims): PlayAnim, no lying pose clip
};
var array<DownState> Downs;        // bGoreLog: the classes whose knockdown / get-up animations were listed

struct StaggerState
{
	var Pawn P;
	var float T, Speed;
	var name Bone;
	var rotator Turn;
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
	// a powered ragdoll: pushed toward a death clip's pose for its first moments
	var bool bPowered;
	var name Clip;
	var float ClipT;
	var vector Start;      // where the body stood when it died, and which way it faced
	var rotator Facing;
	var int Space;         // how the clip's bone positions map to the world (found on the first tick, -1 = not yet)
	var vector Prev[12];   // each part's position last tick (for its velocity)
	var vector RestHips;   // where the hips were a moment ago, and how long they have barely moved
	var float RestT;
};
var array<RagdollState> Ragdolls;
var config float RagdollTime;
// Powered ragdolls (physics plan step 2): a body that dies goes ragdoll at once, and for
// PowerTime seconds each part is pushed toward where the death clip would have it (an
// impulse per tick: a spring on the position error, damped), fading out. The body follows
// the animation while physics handles the floor and the furniture, then goes limp.
var config float RestMove, RestTime;   // a ragdoll whose hips move less than RestMove units for RestTime seconds is at rest
var config bool bPoweredRagdoll;
var config float PowerTime;
var config float PowerSpring;      // per second squared: the pull toward the clip's pose
var config float PowerDamp;        // per second: resists the part's motion
var config float PowerMaxAccel;    // the push is capped (units per second squared)
var name PowerBones[12];           // the ragdoll's parts (tools/make_ka.py, humanMale2)
var float PowerWeights[12];        // their share of the body's mass

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
	if (KarmaTimeScale > 0)
		Level.KarmaTimeScale = KarmaTimeScale;
	if (RagdollTimeScale > 0)
		Level.RagdollTimeScale = RagdollTimeScale;
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
	if (bKnockdown && Max(Damage, Impact) >= KnockDamage && Victim.iBaseTargetingPriority < 255 && FRand() < KnockChance && Knock(Victim, Dir))
		return;
	if (bStagger && Damage >= StaggerDamage && Victim.iBaseTargetingPriority < 255)
		Stagger(Victim, Dir);
}

// down on the floor: the impact animation, a shove along the hit, and the body held there
function bool Knock(Pawn P, vector Dir)
{
	local int i;
	local DownState D;

	if (P.Physics != PHYS_Walking)
		return false;
	for (i = 0; i < Downs.Length; i++)
		if (Downs[i].P == P)
			return false;
	D.P = P;
	D.Speed = P.GroundSpeed;
	if (IsHound(P))
	{
		// the hound's own: thrown onto the side the hit pushes it to
		if (!LinkHound(P))
			return false;
		D.bOwnClips = true;
		D.Fall = 'HoundKnock_L';
		D.Up = 'HoundGetUp_L';
		if ((Dir << P.Rotation).Y > 0)
		{
			D.Fall = 'HoundKnock_R';
			D.Up = 'HoundGetUp_R';
		}
		Downs[Downs.Length] = D;
		if (class'ModSettings'.default.bGoreLog)
			HoundPoseLog(P, -1, P.Rotation);
		P.GroundSpeed = 0;
		P.AnimBlendParams(1, 0.0);
		P.PlayAnim(D.Fall, 1.0, 0.08, 0);
		Dir.Z = 0;
		P.Velocity = Normal(Dir) * KnockPush * 0.6 + vect(0,0,100);
		P.SetPhysics(PHYS_Falling);
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("react: " $ P $ " (hound) knocked down with " $ D.Fall);
		return true;
	}
	if (!P.HasAnim('Death_Impact') || !P.HasAnim('GetUp_back'))
		return false;
	D.Fall = 'Death_Impact';
	// the impact animation falls backwards: getting up from the back; from the front if it has it
	// and the shot came from behind
	D.Up = 'GetUp_back';
	if (P.HasAnim('GetUp_front') && (Dir Dot vector(P.Rotation)) > 0.3)
		D.Up = 'GetUp_front';
	Downs[Downs.Length] = D;
	P.GroundSpeed = 0;
	P.PlayEonAnim(false, 'Death_Impact', 0, 1.0, 0.08);
	Dir.Z = 0;
	P.Velocity = Normal(Dir) * KnockPush + vect(0,0,140);
	P.SetPhysics(PHYS_Falling);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " knocked down (gets up with " $ D.Up $ ")");
	return true;
}

// the knocked-down: kept down (the AI would start another animation), then up again
function Downed(float DeltaTime)
{
	local int i;
	local Pawn P;
	local name Anim;
	local float Frame, Rate;

	for (i = Downs.Length - 1; i >= 0; i--)
	{
		P = Downs[i].P;
		if (P == None || P.bDeleteMe || P.Health <= 0)
		{
			Downs.Remove(i, 1);
			continue;
		}
		Downs[i].T += DeltaTime;
		P.GroundSpeed = 0;
		P.Acceleration = vect(0,0,0);
		P.GetAnimParams(0, Anim, Frame, Rate);
		if (Downs[i].bOwnClips)
		{
			// ours: the fall's last frame is the lying pose; the AI starting something else
			// gets the pose back at once
			if (Downs[i].Phase == 0)
			{
				if (Anim != Downs[i].Fall)
				{
					P.PlayAnim(Downs[i].Fall, 1.0, 0.05, 0);
					P.SetAnimFrame(0.99, 0);
				}
				if (class'ModSettings'.default.bGoreLog && int(Downs[i].T * 2.5) != int((Downs[i].T - DeltaTime) * 2.5))
					HoundPoseLog(P, Downs[i].T, P.Rotation);
				if (Downs[i].T >= KnockDown)
				{
					Downs[i].Phase = 1;
					Downs[i].T = 0;
					P.PlayAnim(Downs[i].Up, 1.0, 0.1, 0);
				}
			}
			else
			{
				if (Anim != Downs[i].Up && Downs[i].T < KnockGetUp * 0.8)
					P.PlayAnim(Downs[i].Up, 1.0, 0.1, 0);
				if (Downs[i].T >= KnockGetUp)
				{
					P.GroundSpeed = Downs[i].Speed;
					Downs.Remove(i, 1);
				}
			}
			continue;
		}
		if (Downs[i].Phase == 0)
		{
			// lying: hold the impact animation's last frame if the AI or the animation moved on
			if (Anim != 'Death_Impact' && Anim != 'Death_Impact_B_Pose')
				P.PlayEonAnim(false, 'Death_Impact', 0, 1.0, 0.05);
			else if (Frame > 0.98 && P.HasAnim('Death_Impact_B_Pose'))
				P.PlayEonAnim(true, 'Death_Impact_B_Pose', 0, 1.0, 0.1);
			if (Downs[i].T >= KnockDown)
			{
				Downs[i].Phase = 1;
				Downs[i].T = 0;
				P.PlayEonAnim(false, Downs[i].Up, 0, 1.0, 0.15);
			}
		}
		else
		{
			if (Anim != Downs[i].Up && Downs[i].T < KnockGetUp * 0.8)
				P.PlayEonAnim(false, Downs[i].Up, 0, 1.0, 0.1);
			if (Downs[i].T >= KnockGetUp)
			{
				P.GroundSpeed = Downs[i].Speed;
				Downs.Remove(i, 1);
			}
		}
	}
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

	// the flesh swings away from the hit (ModJiggle, JIGGLE.md)
	if (!bCorpse)
	{
		if (Jiggle == None)
			foreach DynamicActors(class'ModJiggle', Jiggle)
				break;
		if (Jiggle != None)
			Jiggle.Hit(P, Dir, Damage);
	}
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
	if (class'ModSettings'.default.bGoreLog)
		ProbeAnims(P);
	for (i = Flinches.Length - 1; i >= 0; i--)
		if (Flinches[i].P == P)
		{
			P.SetBoneRotation(Flinches[i].Bone, rot(0,0,0), 0, 0);
			if (Flinches[i].Bone2 != '')
				P.SetBoneRotation(Flinches[i].Bone2, rot(0,0,0), 0, 0);
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
	if (bSpringFlinch)
	{
		// up the spine chain (hips .. head = Bones 0..5); a limb hit shakes the chest a little
		if (Best < 5)
			F.Bone2 = Bones[Best + 1];
		else if (Best > 5)
			F.Bone2 = Bones[3];
		if (F.Bone2 != '')
			F.Turn2 = F.Turn * (Best > 5 ? RippleShare * 0.5 : RippleShare);
		// a third bone up the spine chain, the ripple's share again (hips .. head = Bones 0..5)
		if (Best < 4)
			F.Bone3 = Bones[Best + 2];
		else if (Best > 5)
			F.Bone3 = Bones[1];
		if (F.Bone3 != '')
			F.Turn3 = F.Turn2 * RippleShare;
	}
	Flinches[Flinches.Length] = F;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " flinches at " $ F.Bone $ " " $ F.Turn);
}

// ModMoves: is this body in a spring flinch (then the spine is ours, not the lean's)
function bool IsFlinching(Pawn P)
{
	local int i;

	for (i = 0; i < Flinches.Length; i++)
		if (Flinches[i].P == P)
			return true;
	return false;
}

// which knockdown / get-up / stun animations a character type has (for the knockdown work)
function ProbeAnims(Pawn P)
{
	local int i;
	local string Have;
	local name Try[18];

	for (i = 0; i < AnimProbed.Length; i++)
		if (AnimProbed[i] == P.Class.Name)
			return;
	AnimProbed[AnimProbed.Length] = P.Class.Name;
	Try[0] = 'GetUp_front'; Try[1] = 'GetUp_Back'; Try[2] = 'GetUp_attack'; Try[3] = 'Death_Impact';
	Try[4] = 'Death_ImpactF'; Try[5] = 'Death_Impact_B_Pose'; Try[6] = 'Stun_Hit'; Try[7] = 'Stun_Hit_Idle';
	Try[8] = 'bar_hit'; Try[9] = 'T_ROLL_DFront'; Try[10] = 'Throw_End'; Try[11] = 'Hit_Front';
	Try[12] = 'Hit_Back'; Try[13] = 'KnockBack'; Try[14] = 'Knockdown'; Try[15] = 'Stagger';
	Try[16] = 'Thrown'; Try[17] = 'Fall';
	for (i = 0; i < 18; i++)
		if (P.HasAnim(Try[i]))
			Have = Have $ " " $ Try[i];
	for (i = 0; i < ProbeNames.Length; i++)
	{
		if (P.HasAnim(ProbeNames[i]))
			Have = Have $ " " $ ProbeNames[i];
		if (Len(Have) > 300)
		{
			class'ModSettings'.static.Note("react: " $ P.Class.Name $ " has" $ Have);
			Have = "";
		}
	}
	class'ModSettings'.static.Note("react: " $ P.Class.Name $ " has" $ Have);
}

// the spring's displacement at time T: a 50 ms snap out, then a decaying swing through rest
function float Spring(float T)
{
	if (T <= 0)
		return 0;
	if (T < 0.05)
		return T / 0.05;
	T -= 0.05;
	return Exp(-T * SpringDecay) * Cos(T * SpringFreq * 6.2831853);
}

function Stagger(Pawn P, vector Dir)
{
	local int i;
	local StaggerState S;
	local vector L;

	Dir.Z = 0;
	if (P.Physics == PHYS_Walking)
		P.Velocity += Normal(Dir) * StaggerPush;
	// the lean: the spine bone (Bones[1]) turned away from the hit, the flinch's convention
	L = Normal(Dir) << P.Rotation;
	for (i = 0; i < Staggers.Length; i++)
		if (Staggers[i].P == P)
		{
			Staggers[i].T = 0;
			Staggers[i].Turn.Pitch = int(-L.X * StaggerLean);
			Staggers[i].Turn.Roll = int(L.Y * StaggerLean);
			return;
		}
	S.P = P;
	S.Speed = P.GroundSpeed;
	S.Bone = Bones[1];
	S.Turn.Pitch = int(-L.X * StaggerLean);
	S.Turn.Roll = int(L.Y * StaggerLean);
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

	if (Downs.Length > 0)
		Downed(DeltaTime);

	for (i = Flinches.Length - 1; i >= 0; i--)
	{
		P = Flinches[i].P;
		Flinches[i].T += DeltaTime;
		if (P == None || P.bDeleteMe)
		{
			Flinches.Remove(i, 1);
			continue;
		}
		if (Flinches[i].T >= (bSpringFlinch ? SpringTime : FlinchTime) || (P.Health <= 0 && !Flinches[i].bCorpse))
		{
			P.SetBoneRotation(Flinches[i].Bone, rot(0,0,0), 0, 0);
			if (Flinches[i].Bone2 != '')
				P.SetBoneRotation(Flinches[i].Bone2, rot(0,0,0), 0, 0);
			if (Flinches[i].Bone3 != '')
				P.SetBoneRotation(Flinches[i].Bone3, rot(0,0,0), 0, 0);
			Flinches.Remove(i, 1);
			continue;
		}
		if (bSpringFlinch)
		{
			if (Flinches[i].Bone3 != '')
				P.SetBoneRotation(Flinches[i].Bone3, Flinches[i].Turn3 * Spring(Flinches[i].T - 2 * RippleDelay), 0, 1);
			P.SetBoneRotation(Flinches[i].Bone, Flinches[i].Turn * Spring(Flinches[i].T), 0, 1);
			if (Flinches[i].Bone2 != '')
				P.SetBoneRotation(Flinches[i].Bone2, Flinches[i].Turn2 * Spring(Flinches[i].T - RippleDelay), 0, 1);
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
			P.SetBoneRotation(Staggers[i].Bone, rot(0,0,0), 0, 0);
			Staggers.Remove(i, 1);
			continue;
		}
		// lean in over 80 ms, hold, ease back over the last 40 % of StaggerTime
		if (Staggers[i].T < 0.08)
			Alpha = Staggers[i].T / 0.08;
		else if (Staggers[i].T > StaggerTime * 0.6)
			Alpha = 1 - (Staggers[i].T - StaggerTime * 0.6) / (StaggerTime * 0.4);
		else
			Alpha = 1;
		Alpha = Alpha * Alpha * (3 - 2 * Alpha);
		P.SetBoneRotation(Staggers[i].Bone, Staggers[i].Turn * Alpha, 0, 1);
	}
	// a killing blow: once the pawn is in its death state, limp
	for (i = Deaths.Length - 1; i >= 0; i--)
	{
		P = Deaths[i].P;
		Deaths[i].T += DeltaTime;
		if (P == None || P.bDeleteMe || P.bHidden || P.Physics == PHYS_KarmaRagdoll || (Deaths[i].T > 0.6 && Deaths[i].AnimT < 0 && Deaths[i].AnimT > -50) || P.Health > 0 && Deaths[i].T > 0.2)
		{
			Deaths.Remove(i, 1);
			continue;
		}
		if (Deaths[i].AnimT < -50)
		{
			// testing: the pose a while after the clip ended
			Deaths[i].AnimT -= DeltaTime;
			if (Deaths[i].AnimT < -103)
			{
				class'ModSettings'.static.Note("react: 3 s after the clip " $ P $ " hips over floor " $ OverFloor(P, 'hips') $ " head " $ OverFloor(P, 'head'));
				Deaths.Remove(i, 1);
			}
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
			if (IsHound(P))
				StopTracking(P);
			if (class'ModSettings'.default.bGoreLog && IsHound(P) && int(Deaths[i].AnimT * 2.5) != int((Deaths[i].AnimT + DeltaTime) * 2.5))
				HoundPoseLog(P, Deaths[i].AnimT, Deaths[i].Facing);
			Deaths[i].AnimT += DeltaTime;
			if (bClipFloor)
				OnFloor(P, Deaths[i].AnimT > Deaths[i].Length - 0.4, DeltaTime);
			if (Deaths[i].AnimT < Deaths[i].Handoff)
				continue;
			if (!bDeathAnimRagdoll || IsHound(P))
			{
				// the clip plays out; the body stays in its last pose
				if (Deaths[i].AnimT >= Deaths[i].Length + 0.5)
				{
					if (class'ModSettings'.default.bGoreLog)
						class'ModSettings'.static.Note("react: clip over for " $ P $ ", hips over floor " $ OverFloor(P, 'hips') $ " animating " $ P.IsAnimating());
					Deaths[i].AnimT = -100;
				}
				continue;
			}
		}
		else if (P.IsInState('Dying') && bPoweredRagdoll && Gore != None && DeathAnim(P, Deaths[i].Spot, Deaths[i].Dir, Deaths[i].Type, Deaths[i].Length, true) > 0)
		{
			// a powered ragdoll: limp now, pushed toward the clip's pose for a moment
			Deaths[i].Start = P.Location;
			Deaths[i].Facing = P.Rotation;
			Gore.Limp(P, Deaths[i].Dir, Deaths[i].Spot);
			if (P.Physics == PHYS_KarmaRagdoll)
			{
				AddRagdoll(P);
				Ragdolls[Ragdolls.Length - 1].bPowered = true;
				Ragdolls[Ragdolls.Length - 1].Clip = ClipName;
				Ragdolls[Ragdolls.Length - 1].Start = Deaths[i].Start;
				Ragdolls[Ragdolls.Length - 1].Facing = Deaths[i].Facing;
				Ragdolls[Ragdolls.Length - 1].Space = -1;
				if (class'ModSettings'.default.bGoreLog)
					class'ModSettings'.static.Note("react: " $ P $ " powered ragdoll toward " $ ClipName);
			}
			Deaths.Remove(i, 1);
			continue;
		}
		else if (P.IsInState('Dying') && bDeathAnims)
		{
			Deaths[i].Handoff = DeathAnim(P, Deaths[i].Spot, Deaths[i].Dir, Deaths[i].Type, Deaths[i].Length);
			if (Deaths[i].Handoff > 0)
			{
				AddClipBody(P);
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
	// a pawn the game brings back gets its own draw offset back
	for (i = ClipBodies.Length - 1; i >= 0; i--)
	{
		P = ClipBodies[i].P;
		if (P == None || P.bDeleteMe)
			ClipBodies.Remove(i, 1);
		else if (P.Health > 0)
		{
			P.PrePivot = ClipBodies[i].Pivot;
			ClipBodies.Remove(i, 1);
		}
	}
}

function AddClipBody(Pawn P)
{
	local int i;
	local ClipBody B;

	for (i = 0; i < ClipBodies.Length; i++)
		if (ClipBodies[i].P == P)
			return;
	B.P = P;
	B.Pivot = P.PrePivot;
	ClipBodies[ClipBodies.Length] = B;
}

// The clip moves the body as on flat ground. On stairs or a slope parts of it would sink
// in: the body is drawn higher by as much as its lowest part is under the floor there
// (at once), and once it lies still, lower if all of it hangs in the air (slowly).
function OnFloor(Pawn P, bool bSettled, float DeltaTime)
{
	local int i;
	local float Low, H;
	local vector O, HitL, HitN, Pivot;

	Low = 1000;
	for (i = 0; i < 8; i++)
	{
		O = P.GetBoneCoords(FloorBones[i]).Origin;
		if (O == vect(0,0,0))
			continue;
		if (Trace(HitL, HitN, O - vect(0,0,150), O + vect(0,0,60), false) == None)
			continue;
		H = O.Z - HitL.Z;
		if (H < Low)
			Low = H;
	}
	if (Low > 900)
		return;
	Pivot = P.PrePivot;
	// bones are inside the body: a bone 3 over the floor has its flesh on it
	if (Low < 3)
		Pivot.Z += FMin(3 - Low, 40);
	else if (bSettled && Low > 9)
		Pivot.Z -= FMin(Low - 9, 60 * DeltaTime);
	else
		return;
	P.PrePivot = Pivot;
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

// testing: a hinge's bend, in degrees, and which way it bends in the hips' frame (the hips'
// Z axis is the body's forward; knees should bend "back", elbows "fwd")
function string Hinge(Pawn P, name Top, name Mid, name End)
{
	local vector A, B, Fwd;
	local float Deg;

	A = Normal(P.GetBoneCoords(Mid).Origin - P.GetBoneCoords(Top).Origin);
	B = Normal(P.GetBoneCoords(End).Origin - P.GetBoneCoords(Mid).Origin);
	Fwd = P.GetBoneCoords('hips').ZAxis;
	Deg = Acos(FClamp(A Dot B, -1, 1)) * 57.3;
	if (Deg < 8)
		return int(Deg) $ "";
	return int(Deg) $ class'ModPilot'.static.Eval2(((B - A) Dot Fwd) < 0, "back", "fwd");
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
function float DeathAnim(Pawn P, vector Spot, vector Dir, class<DamageType> Type, out float Length, optional bool bPickOnly)
{
	local MeshAnimation A;
	local class<ModDeathClips> T;
	local string Zone;
	local int i, n, Pick;
	local float Handoff;

	if (IsHound(P))
		return HoundDeath(P, Spot, Dir, Type, Length, bPickOnly);
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
	if (bPickOnly)
		return Handoff;          // the clip is chosen (ClipName) and linked, not played
	P.AnimBlendParams(1, 0.0);
	P.PlayAnim(ClipName, 1.0, 0.1, 0);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " plays " $ ClipName $ " (" $ Zone $ "), limp in " $ Handoff $ " s");
	return Handoff;
}

// testing: the hound's bones relative to its hips in the frame it died in (X forward, Y right,
// Z up), to set against the clip's own pose (tools/clip_sheet.py)
function HoundPoseLog(Pawn P, float T, rotator Facing)
{
	local name B[7];
	local int i;
	local vector H, V;
	local string Out;

	B[0] = 'spine2'; B[1] = 'Neck02'; B[2] = 'head'; B[3] = 'LeftFrontFoot'; B[4] = 'RightFrontFoot'; B[5] = 'LeftToes'; B[6] = 'RightToes';
	H = P.GetBoneCoords('hips').Origin;
	for (i = 0; i < 7; i++)
	{
		V = (P.GetBoneCoords(B[i]).Origin - H) << Facing;
		Out = Out $ " " $ B[i] $ " " $ int(V.X) $ "," $ int(V.Y) $ "," $ int(V.Z);
	}
	class'ModSettings'.static.Note("react: hound pose t " $ T $ " hips over floor " $ OverFloor(P, 'hips') $ " draw " $ P.DrawScale $ " " $ P.DrawScale3D $ " pivot " $ P.PrePivot $ Out);
}

// the AI's head and spine tracking (EonPawn: it turns the neck toward what the hound looks at)
// outlives the death and bent the dead hound's neck into the floor: off, and the bones let go
function StopTracking(Pawn P)
{
	local name B[6];
	local int i;

	P.SetPropertyText("bAllowHeadTracking", "False");
	// and whatever the game's own death plays on the blend channels over ours
	for (i = 1; i < 12; i++)
		P.AnimBlendParams(i, 0.0);
	B[0] = 'spine'; B[1] = 'spine1'; B[2] = 'spine2'; B[3] = 'neck'; B[4] = 'Neck02'; B[5] = 'head';
	for (i = 0; i < 6; i++)
	{
		P.SetBoneDirection(B[i], rot(0,0,0), vect(0,0,0), 0.0);
		P.SetBoneRotation(B[i], rot(0,0,0), 0, 0.0);
	}
}

function bool IsHound(Pawn P)
{
	return P != None && InStr(Caps(string(P.Mesh)), "HOUND") >= 0;
}

function bool LinkHound(Pawn P)
{
	local MeshAnimation A;

	A = class'ModHoundAnims'.default.Clips;
	if (A == None)
		return false;
	P.LinkSkelAnim(A);
	return P.HasAnim('HoundDie_Front');
}

// the hound's death (ModHoundAnims): over backwards from a blast, nose first from the front,
// otherwise onto the side the shot pushes it to. It plays out and the body keeps its last
// pose (no ragdoll: hounds going limp crashed the game, see ModGore.bHoundRagdolls)
function float HoundDeath(Pawn P, vector Spot, vector Dir, class<DamageType> Type, out float Length, bool bPickOnly)
{
	local vector L;

	if (bPickOnly || !LinkHound(P))
		return 0;
	StopTracking(P);
	L = Dir << P.Rotation;
	Length = 1.5;
	if (DeathZone(P, Spot, Dir, Type) == "blast")
	{
		ClipName = 'HoundDie_Blast';
		Length = 1.7;
	}
	else if (L.X < -0.6)
		ClipName = 'HoundDie_Front';
	else if (L.Y > 0)
		ClipName = 'HoundDie_R';
	else
		ClipName = 'HoundDie_L';
	if (TestClip != "")
		SetPropertyText("ClipName", TestClip);
	P.AnimBlendParams(1, 0.0);
	P.PlayAnim(ClipName, 1.0, 0.08, 0);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("react: " $ P $ " (hound) plays " $ ClipName);
	return Length + 1;            // past its end: it never goes limp
}

// where the clip puts a part at this moment, in the world: the clip's positions come in
// one of a few spaces (found on the first tick by which one matches the body as it died)
function vector ClipSpot(Pawn P, int i, int b, int Space)
{
	local vector Raw;

	Raw = P.GetBoneLocationAtFrame(Ragdolls[i].Clip, PowerBones[b], Ragdolls[i].ClipT, false);
	switch (Space)
	{
		case 0: return Ragdolls[i].Start + (Raw >> Ragdolls[i].Facing);                 // the body's frame
		case 1: return Ragdolls[i].Start + Raw;                                          // unrotated, at the body
		case 2: return Raw;                                                              // the world already
		default: return Ragdolls[i].Start + (vect(0,0,0) + Raw.Z * vect(1,0,0) + Raw.X * vect(0,1,0) - Raw.Y * vect(0,0,1)) >> Ragdolls[i].Facing;   // mesh axes (-Y up, Z forward)
	}
}

// a body that has barely moved for RestTime: at rest (KIsAwake() is no use here)
function bool AtRest(int i, float Dt)
{
	local vector Hips;

	Hips = Ragdolls[i].P.GetBoneCoords('hips').Origin;
	if (VSize(Hips - Ragdolls[i].RestHips) > RestMove)
	{
		Ragdolls[i].RestHips = Hips;
		Ragdolls[i].RestT = 0;
		return false;
	}
	Ragdolls[i].RestT += Dt;
	return Ragdolls[i].RestT >= RestTime;
}

// the powered ragdoll's push, each tick while it lasts
function Steer(int i, float Dt)
{
	local Pawn P;
	local int b, sp, Best, n;
	local float M, Fade, Err, BestErr, E;
	local vector Cur, Tgt, Vel, J;
	local string Line;

	P = Ragdolls[i].P;
	if (Dt <= 0 || P == None)
		return;
	M = P.KGetSkelMass();
	if (M <= 0)
		M = 1;
	if (Ragdolls[i].Space < 0)
	{
		// the first tick: the body still stands as the clip's first frame does, which tells
		// the space the clip's positions are in
		BestErr = 1000000000.0;
		for (sp = 0; sp < 4; sp++)
		{
			Err = 0;
			for (b = 0; b < 12; b++)
				if (PowerBones[b] != '')
					Err += VSize(ClipSpot(P, i, b, sp) - P.GetBoneCoords(PowerBones[b]).Origin);
			Line = Line $ " " $ int(Err / 12);
			if (Err < BestErr)
			{
				BestErr = Err;
				Best = sp;
			}
		}
		Ragdolls[i].Space = Best;
		for (b = 0; b < 12; b++)
			if (PowerBones[b] != '')
				Ragdolls[i].Prev[b] = P.GetBoneCoords(PowerBones[b]).Origin;
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("react: powered " $ P $ " clip " $ Ragdolls[i].Clip $ ", mean errors by space" $ Line $ " -> space " $ Best $ ", mass " $ M);
		return;
	}
	Ragdolls[i].ClipT += Dt;
	Fade = FClamp(1 - Ragdolls[i].T / PowerTime, 0, 1);
	P.KWake();   // a sleeping ragdoll ignores impulses
	for (b = 0; b < 12; b++)
	{
		if (PowerBones[b] == '')
			continue;
		Cur = P.GetBoneCoords(PowerBones[b]).Origin;
		Tgt = ClipSpot(P, i, b, Ragdolls[i].Space);
		Vel = (Cur - Ragdolls[i].Prev[b]) / Dt;
		Ragdolls[i].Prev[b] = Cur;
		J = (Tgt - Cur) * PowerSpring - Vel * PowerDamp;
		if (VSize(J) > PowerMaxAccel)
			J = Normal(J) * PowerMaxAccel;
		J = J * (Fade * M * PowerWeights[b] * Dt);
		P.KAddImpulse(J, Cur, PowerBones[b]);
		E += VSize(Tgt - Cur);
		n++;
	}
	if (class'ModSettings'.default.bGoreLog && n > 0 && int(Ragdolls[i].T * 10) != int((Ragdolls[i].T + Dt) * 10))
		class'ModSettings'.static.Note("react: powered " $ P $ " t " $ Ragdolls[i].T $ " mean error " $ int(E / n) $ " fade " $ Fade);
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
		if (Ragdolls[i].bPowered && Ragdolls[i].T < PowerTime)
			Steer(i, DeltaTime);
		// testing: how the ragdoll falls, twice a second
		if (class'ModSettings'.default.bGoreLog && int(Ragdolls[i].T * 2) != int((Ragdolls[i].T + DeltaTime) * 2))
			class'ModSettings'.static.Note("react: ragdoll " $ P $ " t " $ Ragdolls[i].T $ " hips " $ int(P.GetBoneCoords('hips').Origin.Z - Ragdolls[i].FloorZ) $ " head " $ int(P.GetBoneCoords('head').Origin.Z - Ragdolls[i].FloorZ) $ " over floor, awake " $ P.KIsAwake() $ "; knees " $ Hinge(P, 'leftUpLeg', 'leftLeg', 'leftFoot') $ " " $ Hinge(P, 'rightUpLeg', 'rightLeg', 'rightFoot') $ ", elbows " $ Hinge(P, 'leftArm', 'leftForeArm', 'lefthand') $ " " $ Hinge(P, 'rightArm', 'rightForeArm', 'righthand'));
		Ragdolls[i].T += DeltaTime;
		Low = FMin(P.GetBoneCoords('hips').Origin.Z, P.GetBoneCoords('head').Origin.Z);
		Why = "";
		// not in its first moments: a body handed over from a death clip starts low
		// (kneeling), and its bones read wrong for a tick or two
		if (Low < Ragdolls[i].FloorZ + 2 && Ragdolls[i].T > 2.0)
			Why = "at its floor";
		else if (Ragdolls[i].T > 0.8 && AtRest(i, DeltaTime))
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
     bSpringFlinch=True
     bKnockdown=True
     KnockDamage=30
     KnockChance=0.5
     KnockDown=1.300000
     KnockGetUp=1.400000
     KnockPush=260.000000
     SpringFreq=3.200000
     SpringDecay=5.500000
     SpringTime=0.900000
     RippleShare=0.550000
     RippleDelay=0.070000
     bStagger=True
     StaggerDamage=40
     StaggerPush=380.000000
     StaggerSlow=0.350000
     StaggerTime=0.600000
     StaggerLean=5500.000000
     bDeathRagdoll=True
     bDeathAnims=True
     bClipFloor=True
     FloorBones(0)=hips
     FloorBones(1)=head
     FloorBones(2)=leftFoot
     FloorBones(3)=rightFoot
     FloorBones(4)=leftLeg
     FloorBones(5)=rightLeg
     FloorBones(6)=lefthand
     FloorBones(7)=righthand
     DeathAnimHandoff=0.900000
     RestMove=6.000000
     RestTime=0.400000
     PowerTime=0.700000
     PowerSpring=80.000000
     PowerDamp=12.000000
     PowerMaxAccel=3000.000000
     PowerBones(0)=hips
     PowerBones(1)=spine1
     PowerBones(2)=Spine3
     PowerBones(3)=head
     PowerBones(4)=leftArm
     PowerBones(5)=leftForeArm
     PowerBones(6)=rightArm
     PowerBones(7)=rightForeArm
     PowerBones(8)=leftUpLeg
     PowerBones(9)=leftLeg
     PowerBones(10)=rightUpLeg
     PowerBones(11)=rightLeg
     PowerWeights(0)=0.166667
     PowerWeights(1)=0.142857
     PowerWeights(2)=0.166667
     PowerWeights(3)=0.071429
     PowerWeights(4)=0.035714
     PowerWeights(5)=0.023810
     PowerWeights(6)=0.035714
     PowerWeights(7)=0.023810
     PowerWeights(8)=0.107143
     PowerWeights(9)=0.059524
     PowerWeights(10)=0.107143
     PowerWeights(11)=0.059524
     MaxRagdolls=12
     KarmaTimeScale=1.000000
     RagdollTimeScale=0.850000
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
