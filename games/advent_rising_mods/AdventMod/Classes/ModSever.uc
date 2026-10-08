//=============================================================================
// ModSever - decapitation and limb loss (ModGore spawns it and hands it kills and
// corpse hits):
//   - a killing blow that doesn't blow the body apart takes off the part nearest
//     the hit: the head (DecapChance), an arm or a leg from the joint hit down
//     (LimbChance);
//   - a corpse shot SeverHits times in the same limb loses it.
// The part is hidden with SetBoneScale(0) (its bone and all below it) and the
// matching gib piece (ModGibParts, cut from the game's own mesh, meat on the cut)
// flies off along the shot, with a spurt of blood from the cut. Humans and Seeker
// soldiers (the sets ModGibParts has). The pawn gets its bones back when the game
// brings it back to life (it reuses its dead).
//=============================================================================
class ModSever extends Info
	config(AdventMod);

var config bool bSever;
var config float DecapChance, LimbChance;
var config int SeverDamage;        // the killing blow at least this much
var config int SeverHits;          // corpse hits in one limb that take it off
var config float SeverReach;       // how near a hit must be to a joint to count
var config bool bStumps;           // a meat cap on the body where the part came off
var name AboveName;                // a name from a string (SetPropertyText)

var ModGore Gore;
var bool bForce;                   // the next killing blow cuts for certain (a blade's strike, ModMelee)

// a joint that can be cut: the bone hidden, and the gib pieces that fly ("upper,lower")
struct Cut
{
	var name Bone;
	var string Parts;
	var bool bHead;
	var string Above;      // the bone the stump cap rides on: the first of these the mesh has
	var float Cap;         // the cap's radius
};
var array<Cut> Cuts;

struct Severed
{
	var Pawn P;
	var name Bone;
	var int Slot;
	var ModStump Cap;
};
var array<Severed> Done;

struct CorpseCount
{
	var Pawn P;
	var name Bone;
	var int Hits;
};
var array<CorpseCount> Counts;

// the joint nearest a hit, within SeverReach; -1 none (or a bone the mesh lacks)
function int NearestCut(Pawn P, vector Spot)
{
	local int i, Best;
	local float D, BestD;
	local vector Missing, O;

	Missing = P.GetBoneCoords('AdventModNoSuchBone').Origin;
	Best = -1;
	BestD = SeverReach;
	for (i = 0; i < Cuts.Length; i++)
	{
		O = P.GetBoneCoords(Cuts[i].Bone).Origin;
		if (VSize(O - Missing) < 0.01)
			continue;
		// a limb's hit zone is the bone and the stretch below it (hits land along it)
		D = VSize(O - Spot);
		if (D < BestD)
		{
			BestD = D;
			Best = i;
		}
	}
	return Best;
}

function bool IsSevered(Pawn P, name Bone)
{
	local int i;

	for (i = 0; i < Done.Length; i++)
		if (Done[i].P == P && Done[i].Bone == Bone)
			return true;
	return false;
}

// a killing blow
function Kill(Pawn P, vector Spot, vector Dir, int Damage)
{
	local int c;
	local bool bSure;

	bSure = bForce;
	bForce = false;
	if (!bSever || P == None || P.bHidden || (Damage < SeverDamage && !bSure) || Gore.GibSet(P) < 0)
		return;
	c = NearestCut(P, Spot);
	if (c < 0 && bSure)
	{
		// a blade always finds something: the head
		for (c = 0; c < Cuts.Length; c++)
			if (Cuts[c].bHead)
				break;
		if (c == Cuts.Length)
			c = -1;
	}
	if (c < 0 || IsSevered(P, Cuts[c].Bone))
		return;
	if (!bSure && FRand() > (Cuts[c].bHead ? DecapChance : LimbChance))
		return;
	Sever(P, c, Dir);
}

// a shot into a corpse: SeverHits in the same limb take it off
function CorpseHit(Pawn P, vector Spot, vector Dir)
{
	local int c, i;
	local CorpseCount N;

	if (!bSever || P == None || P.bHidden || Gore.GibSet(P) < 0)
		return;
	c = NearestCut(P, Spot);
	if (c < 0 || IsSevered(P, Cuts[c].Bone))
		return;
	for (i = 0; i < Counts.Length; i++)
		if (Counts[i].P == P && Counts[i].Bone == Cuts[c].Bone)
			break;
	if (i == Counts.Length)
	{
		N.P = P;
		N.Bone = Cuts[c].Bone;
		Counts[Counts.Length] = N;
	}
	Counts[i].Hits++;
	if (Counts[i].Hits >= SeverHits)
		Sever(P, c, Dir);
}

function Sever(Pawn P, int c, vector Dir)
{
	local Severed S;
	local int i, Set, Kind, n;
	local float K;
	local vector Spot, V;
	local string Parts, Part;
	local class<Emitter> Spurt;
	local Emitter E;

	Set = Gore.GibSet(P);
	Kind = Gore.BloodKind(P);
	K = FClamp(2 * P.CollisionHeight / class'ModGibParts'.default.Sets[Set].Height, 0.5, 2.0);
	Spot = P.GetBoneCoords(Cuts[c].Bone).Origin;
	S.P = P;
	S.Bone = Cuts[c].Bone;
	S.Slot = c;
	if (bStumps)
		S.Cap = Stump(P, c, Spot, Kind, K);
	Gore.AddStreak(P, Spot, S.Cap, 1.5);     // blood runs down from the cut
	Done[Done.Length] = S;
	P.SetBoneScale(c, 0.0, Cuts[c].Bone);
	// the piece (or pieces: an arm cut at the shoulder throws upper and lower arm)
	Parts = Cuts[c].Parts;
	while (Parts != "")
	{
		i = InStr(Parts, ",");
		if (i < 0)
		{
			Part = Parts;
			Parts = "";
		}
		else
		{
			Part = Left(Parts, i);
			Parts = Mid(Parts, i + 1);
		}
		V = Normal(Dir + VRand() * 0.3) * (260 + 160 * FRand()) + vect(0,0,1) * (180 + 120 * FRand());
		if (Gore.ThrowPart(Set, Kind, Part, Spot + VRand() * 4 + vect(0,0,1) * 6 * n, P.Rotation.Yaw, K, V) != None)
			n++;
	}
	// a spurt from the cut: the game's own blood burst for this body, and blood around
	Gore.CutBlood(Spot, Dir, Kind);
	if (Kind == 2)
		Spurt = class<Emitter>(DynamicLoadObject("EonEffects.fx_person_bulletS", class'Class'));
	else
		Spurt = class<Emitter>(DynamicLoadObject("EonEffects.fx_person_Bullet_Blood", class'Class'));
	if (Spurt != None)
	{
		E = Spawn(Spurt,,, Spot, rotator(Dir + vect(0,0,0.5)));
		if (E != None)
			E.SetBase(P);
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("sever: " $ P $ " loses " $ Cuts[c].Bone $ " (" $ Cuts[c].Parts $ ", " $ n $ " pieces)");
}

// the meat cap where the part was: on the bone above the cut, at the cut
function ModStump Stump(Pawn P, int c, vector Spot, int Kind, float K)
{
	local ModStump M;
	local string List, One;
	local int i;
	local vector Missing, D, Rel;
	local coords BC;

	Missing = P.GetBoneCoords('AdventModNoSuchBone').Origin;
	List = Cuts[c].Above;
	while (List != "")
	{
		i = InStr(List, ",");
		if (i < 0)
		{
			One = List;
			List = "";
		}
		else
		{
			One = Left(List, i);
			List = Mid(List, i + 1);
		}
		SetPropertyText("AboveName", One);
		BC = P.GetBoneCoords(AboveName);
		if (VSize(BC.Origin - Missing) > 0.01)
			break;
		One = "";
	}
	if (One == "")
		return None;
	M = Spawn(class'ModStump',,, Spot);
	if (M == None)
		return None;
	M.SetDrawScale(Cuts[c].Cap * K);
	if (Kind == 2)
		M.Skins[0] = Gore.AlienMeatTex;
	else
		M.Skins[0] = Gore.MeatTex;
	if (!P.AttachToBone(M, AboveName))
	{
		M.Destroy();
		return None;
	}
	// where the cut is, in that bone's own axes
	D = Spot - BC.Origin;
	Rel.X = D Dot BC.XAxis;
	Rel.Y = D Dot BC.YAxis;
	Rel.Z = D Dot BC.ZAxis;
	M.SetRelativeLocation(Rel);
	return M;
}

// bones back for a pawn the game reuses (it comes back to life with its whole body)
event Tick(float DeltaTime)
{
	local int i;

	for (i = Done.Length - 1; i >= 0; i--)
	{
		if (Done[i].P == None || Done[i].P.bDeleteMe)
		{
			if (Done[i].Cap != None)
				Done[i].Cap.Destroy();
			Done.Remove(i, 1);
			continue;
		}
		if (Done[i].P.Health > 0)
		{
			Done[i].P.SetBoneScale(Done[i].Slot, 1.0, Done[i].Bone);
			if (Done[i].Cap != None)
			{
				Done[i].P.DetachFromBone(Done[i].Cap);
				Done[i].Cap.Destroy();
			}
			Done.Remove(i, 1);
			continue;
		}
		// a body blown apart or faded takes its caps with it
		if (Done[i].Cap != None && Done[i].Cap.bHidden != Done[i].P.bHidden)
			Done[i].Cap.bHidden = Done[i].P.bHidden;
	}
	for (i = Counts.Length - 1; i >= 0; i--)
		if (Counts[i].P == None || Counts[i].P.bDeleteMe || Counts[i].P.Health > 0)
			Counts.Remove(i, 1);
}

defaultproperties
{
     bSever=True
     DecapChance=0.850000
     LimbChance=0.500000
     SeverDamage=20
     SeverHits=3
     SeverReach=40.000000
     bStumps=True
     Cuts(0)=(Bone=head,Parts="head",bHead=True,Above="Neck02,neck",Cap=6.5)
     Cuts(1)=(Bone=leftArm,Parts="l_upperarm,l_lowerarm",Above="leftShoulder",Cap=5.5)
     Cuts(2)=(Bone=leftForeArm,Parts="l_lowerarm",Above="leftArm",Cap=4.5)
     Cuts(3)=(Bone=rightArm,Parts="r_upperarm,r_lowerarm",Above="rightShoulder",Cap=5.5)
     Cuts(4)=(Bone=rightForeArm,Parts="r_lowerarm",Above="rightArm",Cap=4.5)
     Cuts(5)=(Bone=leftUpLeg,Parts="l_upperleg,l_lowerleg",Above="hips",Cap=8.0)
     Cuts(6)=(Bone=leftLeg,Parts="l_lowerleg",Above="leftUpLeg",Cap=6.0)
     Cuts(7)=(Bone=rightUpLeg,Parts="r_upperleg,r_lowerleg",Above="hips",Cap=8.0)
     Cuts(8)=(Bone=rightLeg,Parts="r_lowerleg",Above="rightUpLeg",Cap=6.0)
     Cuts(9)=(Bone=LeftFrontArm,Parts="l_front_upper,l_front_lower",Above="LeftFrontShoulder",Cap=6.0)
     Cuts(10)=(Bone=LeftFrontElbow,Parts="l_front_lower",Above="LeftFrontArm",Cap=5.0)
     Cuts(11)=(Bone=RightFrontArm,Parts="r_front_upper,r_front_lower",Above="RightFrontShoulder",Cap=6.0)
     Cuts(12)=(Bone=RightFrontElbow,Parts="r_front_lower",Above="RightFrontArm",Cap=5.0)
}
