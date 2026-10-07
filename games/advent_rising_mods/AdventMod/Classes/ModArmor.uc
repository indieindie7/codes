//=============================================================================
// ModArmor - destructible armour on the Seeker soldiers, the way the new Wolfenstein
// games do it: every armoured character carries six plates (head, torso, each arm, each
// leg) with points of their own. While a plate holds, a hit on that region loses Absorb
// of its damage to the plate; when the plate's points run out it breaks: chunks fly off,
// the body jerks and staggers, and from then on hits on that region do ExposedBonus
// times their damage (the head more: a broken helmet opens headshots). Explosions hit
// every plate at once and the body in full. ModGoreRules hands every hit through
// Strike() before the flinch and the blood see it, so they react to what got through.
// All three phases: the numbers and the burst; the plate itself, the region's piece of the
// character's own mesh (the gib parts) flying off a little smaller than the limb in the
// body's skin, no blood; and the flesh under it, the meat texture blended over the skin
// through the region's UV mask (ModArmorTextures, tools/make_armor_masks.py).
//=============================================================================
class ModArmor extends Info
	config(AdventMod);

var config bool bArmor;
var config float PlateHead, PlateTorso, PlateArm, PlateLeg;   // plate points as a share of the character's health (bPreserveTtk off)
// time to kill preserved: a region shot from full health takes the same total damage to
// kill as without armour (the plate only moves damage around in time). With plate P,
// absorb a, bonus B and health H: damage to kill = P/a + (H - P(1-a)/a)/B, which equals H
// when P = a H (B-1) / (B-1+a). Shares under 1 give a lighter plate and a FASTER kill
// through that region (limbs), never a slower one.
var config bool bPreserveTtk;
var config float ShareHead, ShareTorso, ShareArm, ShareLeg;
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
	var Material Top;       // the plain skin the flesh is blended over
	var byte bSkinned;      // the chain is on the body
};
var array<ArmorState> Bodies;
var name Bones[12];                 // the bones a hit is measured against (ModReact's list)
var int BoneRegion[12];             // ...and the plate each belongs to
var string BonePart[12];            // the gib part (ModGibParts) that flies off as the plate when that bone's plate breaks
var config float PlateScale;        // the flying plate's size against the body part (under 1: a shell, not a limb)
var config float PlateStay;         // seconds a fallen plate lies there before it sinks away
var config bool bPlates;            // the region's own mesh piece flies off (phase 2); off: chunks only
var int LastBone;                   // the bone Region() settled on
var config bool bExpose;            // the flesh shows where a plate is gone (phase 3)
var config float ExposeMix;         // how much of the flesh shows through (1: the mask as made)
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
	if (bPreserveTtk)
	{
		S.Max[0] = Neutral(P.default.Health, HeadBonus) * ShareHead;
		S.Max[1] = Neutral(P.default.Health, ExposedBonus) * ShareTorso;
		S.Max[2] = Neutral(P.default.Health, ExposedBonus) * ShareArm;
		S.Max[3] = S.Max[2];
		S.Max[4] = Neutral(P.default.Health, ExposedBonus) * ShareLeg;
		S.Max[5] = S.Max[4];
	}
	else
	{
		S.Max[0] = P.default.Health * PlateHead;
		S.Max[1] = P.default.Health * PlateTorso;
		S.Max[2] = P.default.Health * PlateArm;
		S.Max[3] = P.default.Health * PlateArm;
		S.Max[4] = P.default.Health * PlateLeg;
		S.Max[5] = P.default.Health * PlateLeg;
	}
	for (r = 0; r < 6; r++)
		S.Plate[r] = S.Max[r];
	Bodies[Bodies.Length] = S;
	if (bArmorLog)
		class'ModSettings'.static.Note("armor: " $ P $ " wears plates " $ int(S.Max[0]) $ "/" $ int(S.Max[1]) $ "/" $ int(S.Max[2]) $ "/" $ int(S.Max[4]));
	return Bodies.Length - 1;
}

// the plate points that leave the damage-to-kill through a region unchanged
function float Neutral(float Health, float Bonus)
{
	if (Bonus <= 1.0 || Absorb <= 0)
		return 0;
	return Absorb * Health * (Bonus - 1.0) / (Bonus - 1.0 + Absorb);
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
	if (bExpose && Set >= 0)
		Expose(b, r, Set);
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

// the flesh under the broken plates: ONE Combiner stage blends the meat texture over the
// plain skin through the mask of the set of broken plates (ModArmorTextures, from the mesh's
// own UVs; the renderer draws a combiner inside a combiner as a flat colour, so one stage
// and a pre-combined mask). It goes into skin slot 0; a blood coat on the body comes off
// first (its multiply would be a second stage), and the coat won't come back on a
// Combiner skin (ModBloodCoat.PlainOf).
function Expose(int b, int r, int Set)
{
	local Pawn P;
	local int i, k, Entry, Bits;
	local Material Base;
	local Combiner C;
	local ModBloodCoat Coat;
	local class<ModArmorTextures> T;

	P = Bodies[b].P;
	T = class'ModArmorTextures';
	for (i = 0; i < T.default.Sets.Length; i++)
		if (T.default.Sets[i].Set == class'ModGibParts'.default.Sets[Set].Name)
			break;
	if (i >= T.default.Sets.Length)
		return;
	for (k = 0; k < 6; k++)
		if (Bodies[b].Broken[k] != 0)
			Bits = Bits | T.static.RegionBit(k);
	if (Bits <= 0 || Bits > 15 || T.default.Sets[i].Meat[Bits] == None)
		return;
	Coat = Gore.CoatOf(P);
	if (Bodies[b].Top == None)
	{
		// the plain skin: what the body wears (under its coat), or the mesh's own material (ModSkins)
		if (Coat != None && Coat.Mix[0] != None)
			Base = Coat.Mix[0].Material1;
		else if (P.Skins.Length > 0 && P.Skins[0] != None)
			Base = class'ModBloodCoat'.static.PlainOf(P.Skins[0]);
		else
		{
			Entry = class'ModSkins'.static.Find(P.Mesh);
			if (Entry >= 0 && class'ModSkins'.default.Meshes[Entry].Skin[0] != "")
				Base = class'ModBloodCoat'.static.PlainOf(Material(DynamicLoadObject(class'ModSkins'.default.Meshes[Entry].Skin[0], class'Material')));
		}
		if (Base == None)
		{
			if (bArmorLog)
				class'ModSettings'.static.Note("armor: " $ P $ " has no skin to expose");
			return;
		}
		Bodies[b].Top = Base;
	}
	if (Coat != None)
		Coat.Destroy();               // puts the body's own skins back; ours goes on over them
	C = new(None) class'Combiner';
	C.Material1 = Bodies[b].Top;
	// the meat-baked texture is Material2 and Mask at once (a separate mask drew a flat colour)
	C.Material2 = T.default.Sets[i].Meat[Bits];
	C.Mask = T.default.Sets[i].Meat[Bits];
	C.CombineOperation = CO_AlphaBlend_With_Mask;
	C.AlphaOperation = AO_Use_Alpha_From_Material1;
	P.Skins[0] = C;
	Bodies[b].bSkinned = 1;
	if (bArmorLog)
		class'ModSettings'.static.Note("armor: " $ P $ " shows flesh (plates " $ Bits $ ", coat " $ Coat $ ")");
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
     bArmor=False
     PlateHead=0.2
     PlateTorso=0.5
     PlateArm=0.25
     PlateLeg=0.3
     bPreserveTtk=True
     ShareHead=1.0
     ShareTorso=1.0
     ShareArm=0.6
     ShareLeg=0.6
     Absorb=0.7
     ExposedBonus=1.5
     HeadBonus=2.0
     BlastShare=0.4
     Chunks=2
     MaxChunks=40
     bPlates=True
     bExpose=True
     ExposeMix=1.0
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
