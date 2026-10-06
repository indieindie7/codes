//=============================================================================
// ModArmor - destructible armour on the Seeker soldiers, the way the new Wolfenstein
// games do it: every armoured character carries six plates (head, torso, each arm, each
// leg) with points of their own. While a plate holds, a hit on that region loses Absorb
// of its damage to the plate; when the plate's points run out it breaks: chunks fly off,
// the body jerks and staggers, and from then on hits on that region do ExposedBonus
// times their damage (the head more: a broken helmet opens headshots). Explosions hit
// every plate at once and the body in full. ModGoreRules hands every hit through
// Strike() before the flinch and the blood see it, so they react to what got through.
// Phase 2 of three: the numbers, the burst, and the plate itself: the region's piece of the
// character's own mesh (the gib parts) flies off, a little smaller than the limb, in the
// body's skin, no blood. Next: the exposed flesh painted under it (region masks).
//=============================================================================
class ModArmor extends Info
	config(AdventMod);

var config bool bArmor;
var config float PlateHead, PlateTorso, PlateArm, PlateLeg;   // plate points as a share of the character's health
var config float Absorb;            // the share of a hit a holding plate takes
var config float ExposedBonus;      // damage x this on a region whose plate is gone
var config float HeadBonus;         // ...and on a bare head
var config float BlastShare;        // an explosion's damage, as a share, to every plate
var config int Chunks;              // chunks a breaking plate throws
var config int MaxChunks;
var array<string> Armored;          // class name parts of the characters that wear plates (not config: an ini section without the key would empty a config array)
var config bool bArmorLog;

struct ArmorState
{
	var Pawn P;
	var float Plate[6];     // points left: head, torso, left arm, right arm, left leg, right leg
	var float Max[6];
	var byte Broken[6];
};
var array<ArmorState> Bodies;
var name Bones[12];                 // the bones a hit is measured against (ModReact's list)
var int BoneRegion[12];             // ...and the plate each belongs to
var string BonePart[12];            // the gib part (ModGibParts) that flies off as the plate when that bone's plate breaks
var config float PlateScale;        // the flying plate's size against the body part (under 1: a shell, not a limb)
var config float PlateStay;         // seconds a fallen plate lies there before it sinks away
var config bool bPlates;            // the region's own mesh piece flies off (phase 2); off: chunks only
var int LastBone;                   // the bone Region() settled on
var localized string RegionNames[6];
var array<ModRubble> Pieces;
var ModGore Gore;
var float Sweep;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	class'ModSettings'.static.Note("armor: ready (on " $ bArmor $ ", log " $ bArmorLog $ ", " $ Armored.Length $ " armoured classes, absorb " $ Absorb $ ")");
}

function bool Wears(Pawn P)
{
	local int i;
	local string N;

	if (P == None || P.IsHumanControlled() || P.IsA('Vehicle') || P.IsA('Turret'))
		return false;
	N = Caps(string(P.Class.Name));
	for (i = 0; i < Armored.Length; i++)
		if (InStr(N, Caps(Armored[i])) >= 0)
			return true;
	return false;
}

function int Body(Pawn P)
{
	local int i, r;
	local ArmorState S;

	for (i = 0; i < Bodies.Length; i++)
		if (Bodies[i].P == P)
			return i;
	S.P = P;
	S.Max[0] = P.default.Health * PlateHead;
	S.Max[1] = P.default.Health * PlateTorso;
	S.Max[2] = P.default.Health * PlateArm;
	S.Max[3] = P.default.Health * PlateArm;
	S.Max[4] = P.default.Health * PlateLeg;
	S.Max[5] = P.default.Health * PlateLeg;
	for (r = 0; r < 6; r++)
		S.Plate[r] = S.Max[r];
	Bodies[Bodies.Length] = S;
	if (bArmorLog)
		class'ModSettings'.static.Note("armor: " $ P $ " wears plates " $ int(S.Max[0]) $ "/" $ int(S.Max[1]) $ "/" $ int(S.Max[2]) $ "/" $ int(S.Max[4]));
	return Bodies.Length - 1;
}

// the plate under a hit: the region of the bone nearest it (torso when no bone answers)
function int Region(Pawn P, vector HitLocation)
{
	local int i, Best;
	local float D, BestD;
	local coords C;

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
	LastBone = Best;
	if (Best < 0)
		return 1;
	return BoneRegion[Best];
}

static function bool IsBlast(class<DamageType> DamageType)
{
	local string N;

	if (DamageType == None)
		return false;
	N = Caps(string(DamageType.Name));
	return InStr(N, "EXPLOSION") >= 0 || InStr(N, "GRENADE") >= 0 || InStr(N, "LAUNCHER") >= 0 || InStr(N, "MISSLE") >= 0 || InStr(N, "MISSILE") >= 0;
}

// the damage that reaches the body
function int Strike(int Damage, Pawn Injured, Pawn Instigator, vector HitLocation, class<DamageType> DamageType, vector Dir)
{
	local int b, r, Through;
	local float Block, Bonus;

	if (!bArmor || Damage <= 0 || Injured == None || Injured.Health <= 0 || !Wears(Injured))
		return Damage;
	b = Body(Injured);
	if (IsBlast(DamageType))
	{
		// a blast rattles every plate; the body takes the hit in full
		for (r = 0; r < 6; r++)
			if (Bodies[b].Broken[r] == 0)
			{
				Bodies[b].Plate[r] -= Damage * BlastShare;
				if (Bodies[b].Plate[r] <= 0)
				{
					LastBone = RegionBone(r);
					Shatter(b, r, Injured.GetBoneCoords(Bones[LastBone]).Origin, Dir);
				}
			}
		return Damage;
	}
	r = Region(Injured, HitLocation);
	if (Bodies[b].Broken[r] == 0)
	{
		Block = FMin(Bodies[b].Plate[r], Damage * Absorb);
		Bodies[b].Plate[r] -= Block;
		Through = Max(1, Damage - int(Block));
		if (bArmorLog)
			class'ModSettings'.static.Note("armor: " $ Injured $ " " $ RegionNames[r] $ " plate " $ int(Bodies[b].Plate[r]) $ "/" $ int(Bodies[b].Max[r]) $ " took " $ int(Block) $ " of " $ Damage $ ", " $ Through $ " through");
		if (Bodies[b].Plate[r] <= 0)
			Shatter(b, r, HitLocation, Dir);
		return Through;
	}
	Bonus = ExposedBonus;
	if (r == 0)
		Bonus = HeadBonus;
	if (bArmorLog)
		class'ModSettings'.static.Note("armor: " $ Injured $ " bare " $ RegionNames[r] $ ": " $ Damage $ " x " $ Bonus);
	return int(Damage * Bonus);
}

// the plate goes: chunks fly from the hit, the body jerks and staggers
function Shatter(int b, int r, vector HitLocation, vector Dir)
{
	local int i, Set;
	local ModRubble Piece;
	local vector V;
	local float K;
	local Pawn P;

	Bodies[b].Broken[r] = 1;
	Bodies[b].Plate[r] = 0;
	P = Bodies[b].P;
	if (bArmorLog || class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("armor: " $ P $ " loses its " $ RegionNames[r] $ " plate");
	Set = -1;
	if (Gore != None)
		Set = Gore.GibSet(P);
	if (bPlates && Set >= 0)
		Plate(P, Set, HitLocation, Dir);
	for (i = 0; i < Chunks; i++)
	{
		while (Pieces.Length > 0 && (Pieces.Length >= MaxChunks || Pieces[0] == None || Pieces[0].bDeleteMe))
		{
			if (Pieces[0] != None && !Pieces[0].bDeleteMe)
				Pieces[0].Destroy();
			Pieces.Remove(0, 1);
		}
		Piece = Spawn(class'ModRubble',,, HitLocation + VRand() * 6, RotRand());
		if (Piece == None)
			continue;
		K = 1.2 + 1.6 * FRand();
		Piece.Gore = Gore;
		Piece.SetStaticMesh(Piece.Shapes[Rand(2)]);
		Piece.SetDrawScale(K);
		if (Set >= 0 && Gore != None)
			Piece.Skins[0] = Gore.SetSkin(Set);
		Piece.Size = vect(1,1,1) * K;
		Piece.Stay = 40 + 30 * FRand();
		// away from the shot, up and out
		V = Normal(Dir * 1.4 + VRand() + vect(0,0,0.8)) * (160 + 220 * FRand());
		Piece.Launch(V, PhysicsVolume.Gravity.Z, K * 0.5);
		Pieces[Pieces.Length] = Piece;
	}
	if (Gore != None && Gore.React != None)
	{
		Gore.React.Flinch(P, HitLocation, Dir, 140);
		if (Gore.React.bStagger)
			Gore.React.Stagger(P, Dir);
	}
}

// a bone of the region (the first in the table), for a plate broken by a blast
function int RegionBone(int r)
{
	local int i;

	for (i = 0; i < 12; i++)
		if (BoneRegion[i] == r)
			return i;
	return 0;
}

// the plate itself: the region's part cut from the character's own mesh (the gib parts),
// a little smaller than the limb so it reads as a shell, in the body's skin on every face,
// thrown from the bone away from the shot; no blood, and it sinks away sooner than a gib
function Plate(Pawn P, int Set, vector HitLocation, vector Dir)
{
	local ModGib G;
	local float K;
	local vector Spot, V;
	local string Part;

	if (LastBone < 0 || Gore == None)
		return;
	Part = BonePart[LastBone];
	if (Part == "")
		return;
	Spot = P.GetBoneCoords(Bones[LastBone]).Origin;
	if (Spot == vect(0,0,0))
		Spot = HitLocation;
	K = FClamp(2 * FMax(P.CollisionHeight, P.default.CollisionHeight) / class'ModGibParts'.default.Sets[Set].Height, 0.5, 2.0);
	V = Normal(Dir * 1.2 + VRand() * 0.5 + vect(0,0,0.7)) * (200 + 160 * FRand());
	G = Gore.ThrowPart(Set, 0, Part, Spot + Normal(Dir) * 8, P.Rotation.Yaw, K * PlateScale, V);
	if (G == None)
		return;
	G.Skins[1] = G.Skins[0];
	G.Stay = PlateStay * (0.8 + 0.4 * FRand());
	if (bArmorLog)
		class'ModSettings'.static.Note("armor: plate " $ Part $ " flies from " $ Bones[LastBone]);
}

// how many plates a body still has (the pilot's log, and later a HUD hint)
function int PlatesLeft(Pawn P)
{
	local int i, r, n;

	for (i = 0; i < Bodies.Length; i++)
		if (Bodies[i].P == P)
			for (r = 0; r < 6; r++)
				if (Bodies[i].Broken[r] == 0)
					n++;
	return n;
}

event Tick(float DeltaTime)
{
	local int i;

	Sweep -= DeltaTime;
	if (Sweep > 0)
		return;
	Sweep = 3;
	for (i = Bodies.Length - 1; i >= 0; i--)
		if (Bodies[i].P == None || Bodies[i].P.bDeleteMe || Bodies[i].P.Health <= 0)
			Bodies.Remove(i, 1);
}

defaultproperties
{
     bArmor=True
     PlateHead=0.2
     PlateTorso=0.5
     PlateArm=0.25
     PlateLeg=0.3
     Absorb=0.7
     ExposedBonus=1.5
     HeadBonus=2.0
     BlastShare=0.4
     Chunks=2
     MaxChunks=40
     bPlates=True
     PlateScale=0.9
     PlateStay=18.0
     Armored(0)="SeekerInfantry"
     Armored(1)="SeekerElite"
     Armored(2)="SeekerCommander"
     Armored(3)="SeekerPilot"
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
     BoneRegion(0)=1
     BoneRegion(1)=1
     BoneRegion(2)=1
     BoneRegion(3)=1
     BoneRegion(4)=0
     BoneRegion(5)=0
     BoneRegion(6)=3
     BoneRegion(7)=3
     BoneRegion(8)=2
     BoneRegion(9)=2
     BoneRegion(10)=5
     BoneRegion(11)=4
     BonePart(0)="torso_lower"
     BonePart(1)="torso_lower"
     BonePart(2)="torso_upper"
     BonePart(3)="torso_upper"
     BonePart(4)="head"
     BonePart(5)="head"
     BonePart(6)="r_upperarm"
     BonePart(7)="r_lowerarm"
     BonePart(8)="l_upperarm"
     BonePart(9)="l_lowerarm"
     BonePart(10)="r_upperleg"
     BonePart(11)="l_upperleg"
     RegionNames(0)="head"
     RegionNames(1)="torso"
     RegionNames(2)="left arm"
     RegionNames(3)="right arm"
     RegionNames(4)="left leg"
     RegionNames(5)="right leg"
}
