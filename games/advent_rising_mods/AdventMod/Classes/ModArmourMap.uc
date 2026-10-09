//=============================================================================
// ModArmourMap - the bone table: for each enemy mesh, its main bones (the 16 with the most
// surface, ordered by surface) and the share of that surface that is armour, by the game's own
// chrome mask (tools/make_armour_data.py; ARMOUR.md "where the plates are"). ModArmor's
// script-side fallback when the native ray test has no data: the hit's nearest bone with a
// share of 0.5 or more counts as armour. Numbers only: no game pixels or geometry here.
// Entry e of mesh m is Bone[m * 16 + e] / Share[m * 16 + e] (flat: the compiler refused the
// static arrays inside a struct literal for three of the meshes).
//=============================================================================
class ModArmourMap extends Object;

const PerMesh = 16;
var string Meshes[9];
var name Bone[144];
var float Share[144];

// (an instance reads its own arrays: the compiler refuses an element of an array this
// large through a context expression, class'X'.default.Bone[i] included)

// the entry for a mesh (the mesh object's name, case-insensitive), or -1
function int Find(Mesh M)
{
	local int i;
	local string N;

	if (M == None)
		return -1;
	N = Caps(string(M.Name));
	for (i = 0; i < 9; i++)
		if (Caps(Meshes[i]) == N)
			return i;
	return -1;
}

function name BoneOf(int e, int i)
{
	if (e < 0 || i < 0 || e * PerMesh + i >= 144)
		return '';
	return Bone[e * PerMesh + i];
}

function float ShareOf(int e, int i)
{
	if (e < 0 || i < 0 || e * PerMesh + i >= 144)
		return 0;
	return Share[e * PerMesh + i];
}

defaultproperties
{
     Meshes(0)="seekerinfantry"
     Bone(0)=head
     Bone(1)=leftArm
     Share(1)=0.47
     Bone(2)=jaw
     Share(2)=0.01
     Bone(3)=leftForeArm
     Share(3)=0.41
     Bone(4)=hips
     Bone(5)=spine2
     Bone(6)=rightUpLeg
     Bone(7)=righthand
     Bone(8)=lefthand
     Bone(9)=leftUpLeg
     Bone(10)=rightLeg
     Bone(11)=rightArm
     Bone(12)=leftLeg
     Bone(13)=spine
     Bone(14)=leftFoot
     Bone(15)=rightForeArm
     Meshes(1)="SeekerElite"
     Bone(16)=head
     Share(16)=0.07
     Bone(17)=leftForeArm
     Share(17)=0.29
     Bone(18)=jaw
     Share(18)=0.01
     Bone(19)=hips
     Bone(20)=rightArm
     Share(20)=0.13
     Bone(21)=spine2
     Bone(22)=rightUpLeg
     Bone(23)=righthand
     Bone(24)=leftArm
     Bone(25)=lefthand
     Bone(26)=leftUpLeg
     Bone(27)=rightLeg
     Bone(28)=leftLeg
     Bone(29)=spine
     Bone(30)=leftFoot
     Bone(31)=rightForeArm
     Meshes(2)="SeekerCommander"
     Bone(32)=head
     Bone(33)=leftArm
     Share(33)=0.26
     Bone(34)=jaw
     Share(34)=0.01
     Bone(35)=hips
     Bone(36)=leftForeArm
     Share(36)=0.09
     Bone(37)=rightArm
     Share(37)=0.12
     Bone(38)=spine2
     Bone(39)=leftShoulder
     Share(39)=0.07
     Bone(40)=rightUpLeg
     Bone(41)=righthand
     Share(41)=0.01
     Bone(42)=lefthand
     Share(42)=0.01
     Bone(43)=leftUpLeg
     Bone(44)=rightLeg
     Bone(45)=leftLeg
     Bone(46)=spine
     Bone(47)=leftFoot
     Meshes(3)="seekerpilot"
     Bone(48)=head
     Share(48)=0.43
     Bone(49)=leftArm
     Share(49)=0.07
     Bone(50)=jaw
     Bone(51)=rightArm
     Share(51)=0.08
     Bone(52)=hips
     Bone(53)=RightFrontElbow
     Share(53)=0.08
     Bone(54)=LeftFrontElbow
     Share(54)=0.08
     Bone(55)=righthand
     Share(55)=0.04
     Bone(56)=lefthand
     Share(56)=0.04
     Bone(57)=spine2
     Bone(58)=rightForeArm
     Share(58)=0.07
     Bone(59)=leftForeArm
     Share(59)=0.07
     Bone(60)=rightShoulder
     Share(60)=0.06
     Bone(61)=leftShoulder
     Share(61)=0.07
     Bone(62)=rightUpLeg
     Bone(63)=leftUpLeg
     Meshes(4)="SeekerScanner"
     Bone(64)=leftForeArm
     Share(64)=0.71
     Bone(65)=head
     Share(65)=0.37
     Bone(66)=jaw
     Bone(67)=hips
     Bone(68)=spine2
     Bone(69)=leftArm
     Bone(70)=rightUpLeg
     Bone(71)=righthand
     Bone(72)=leftUpLeg
     Bone(73)=rightLeg
     Bone(74)=rightArm
     Bone(75)=leftLeg
     Bone(76)=spine
     Bone(77)=leftFoot
     Bone(78)=neck
     Bone(79)=rightForeArm
     Meshes(5)="seekerhound"
     Bone(80)=head
     Bone(81)=Neck02
     Bone(82)=jaw
     Bone(83)=hips
     Bone(84)=leftUpLeg
     Bone(85)=rightUpLeg
     Bone(86)=leftLeg
     Bone(87)=rightLeg
     Bone(88)=leftFoot
     Bone(89)=rightFoot
     Bone(90)=RightFrontElbow
     Bone(91)=LeftFrontElbow
     Bone(92)=RightFrontThumb02
     Bone(93)=LeftFrontThumb02
     Bone(94)=LeftToes
     Bone(95)=RightToes
     Meshes(6)="seekershocktrooper"
     Bone(96)=jaw
     Bone(97)=RightWrist
     Bone(98)=LeftWrist
     Bone(99)=spine03
     Bone(100)=root
     Bone(101)=LeftBackAnkle
     Share(101)=0.01
     Bone(102)=RightBackAnkle
     Share(102)=0.01
     Bone(103)=Neck02
     Share(103)=0.02
     Bone(104)=LeftBackLeg
     Share(104)=0.01
     Bone(105)=rightArm
     Bone(106)=RightBackLeg
     Share(106)=0.01
     Bone(107)=leftArm
     Bone(108)=JowlLeft
     Bone(109)=spine02
     Bone(110)=RightBackKnee
     Bone(111)=JawLower
     Meshes(7)="kchell"
     Bone(112)=head
     Bone(113)=spine2
     Bone(114)=jaw
     Bone(115)=hips
     Bone(116)=neck
     Bone(117)=leftArm
     Bone(118)=spine1
     Bone(119)=rightArm
     Bone(120)=rightUpLeg
     Bone(121)=righthand
     Bone(122)=lefthand
     Bone(123)=leftUpLeg
     Bone(124)=rightLeg
     Bone(125)=leftLeg
     Bone(126)=leftFoot
     Bone(127)=rightForeArm
     Meshes(8)="specops"
     Bone(128)=spine2
     Share(128)=0.05
     Bone(129)=head
     Bone(130)=leftLeg
     Share(130)=0.01
     Bone(131)=rightLeg
     Share(131)=0.01
     Bone(132)=leftUpLeg
     Share(132)=0.09
     Bone(133)=hips
     Share(133)=0.02
     Bone(134)=rightArm
     Bone(135)=leftArm
     Bone(136)=rightFoot
     Bone(137)=rightUpLeg
     Bone(138)=righthand
     Bone(139)=LeftToes
     Bone(140)=leftFoot
     Bone(141)=lefthand
     Bone(142)=rightForeArm
     Bone(143)=leftForeArm
}
