//=============================================================================
// ModPlayerBlood - blood on the player's own hands, forearms and held weapon, and blood
// drops on the camera's "lens". Both are drawn by the d3d8 layer (d3d8to9-gi: streaks.hpp's
// hands pass, hands=1; lens.hpp, lens=1); this class decides how bloody and when.
//
// Hands: Amount (0..1) rises when the player kills or punches something up close (more for a
// melee hit, a blade in the hand, or a body blown apart), when blood lands on the player (the
// rise of the player's blood coat, ModGore's ModBloodCoat) and when the screen-blood event fires.
// Fresh blood dries over DrySecs and the whole of it wears off over FadeSecs. Each tick the
// layer gets capsules (a segment and a radius) for each arm (elbow to fingertips), the weapons in
// the hands and the energy blade while it is held:
//   Blood:hand K ax ay az bx by bz r sx sy sz wa wb   (world units; side axis in hundredths;
//                                                      weights at the two ends in percent)
//   Blood:hands amount kind wet seed n                (percent, 1 red 2 purple, percent, seed,
//                                                      capsules in use)
// Lens: a bleeding hit within LensNear of the player is sent with its world spot
// ("Blood:lensat x y z strength kind"); the layer measures it from the camera and puts drops on
// the lens if it is within reach (U2Shaders.ini lensparams=, 120 units). ModScreenBlood's splats
// (ModGore.ScreenSplash: kills and gibs close to the player) become "Blood:lens strength kind";
// when the layer takes it (lens=1) the HUD splat is removed (bReplaceScreenBlood), so the lens
// replaces the old HUD overlay; with lens=0 (or an older d3d8.dll) the HUD splats stay.
//
// It is also a GameRules (spawned once per level, it adds itself to the chain): NetDamage sees
// every hit and passes the damage on unchanged.
//=============================================================================
class ModPlayerBlood extends GameRules
	config(AdventMod);

var config bool bHands;               // blood on the hands and weapon (drawn with U2Shaders.ini hands=1)
var config bool bLens;                // blood drops on the lens (drawn with U2Shaders.ini lens=1, post=1)
var config bool bReplaceScreenBlood;  // the lens takes over ModScreenBlood's HUD splats when the layer answers
var config float FadeSecs;            // seconds a full coat of blood on the hands takes to wear off
var config float DrySecs;             // seconds fresh blood takes to dry
var config float ArmRadius;           // the arm capsules' radius (world units)
var config float HandLength;          // fingertips past the hand bone
var config float WeaponRadius, BladeRadius, BladeLength;
var config float KillReach;           // a kill closer than this bloodies the hands
var config float LensNear;            // bleeding hits closer than this to the player go to the layer as lens candidates
var config float CoatShare;           // the share of the player's coat's rise that reaches the hands
var config name HandBones[2];         // right, left
var config name ArmBones[2];          // the forearm bones (their origin is the elbow)
var config bool bLogBones;            // note the bones and the weapon's place once a level (AdventNative.log)

var ModGore Gore;
var float GoreLook;
var Pawn Me;                          // the player's pawn the amount belongs to
var float Amount;                     // 0..1
var int Kind;                         // 1 red, 2 purple
var float LastAdd;                    // Level.TimeSeconds of the last blood
var float LastCoat;                   // the player's coat amount last tick
var float LastLens;
var int Seed;
var int SentCaps;                     // capsules the layer was told about
var bool bSentOff;                    // "hands 0" sent since the last blood
var bool bToldBones;
var float SplatAge[12];               // ModScreenBlood's splats as seen last tick (-1: empty)

event PostBeginPlay()
{
	local int i;

	Super.PostBeginPlay();
	if (Level.Game == None)
		return;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = self;
	else
		Level.Game.GameRulesModifiers.AddGameRules(self);
	for (i = 0; i < 12; i++)
		SplatAge[i] = -1;
	Seed = Rand(1000);
	Kind = 1;
	bSentOff = true;
	// the last level's
	class'ModSettings'.static.NativeCall("Blood:handclear");
	class'ModSettings'.static.NativeCall("Blood:lensclear");
}

function int NetDamage(int OriginalDamage, int Damage, Pawn Injured, Pawn InstigatedBy, vector HitLocation, out vector Momentum, class<DamageType> DamageType)
{
	if (NextGameRules != None)
		Damage = NextGameRules.NetDamage(OriginalDamage, Damage, Injured, InstigatedBy, HitLocation, Momentum, DamageType);
	Watch(Injured, InstigatedBy, HitLocation, Damage, DamageType);
	return Damage;
}

// a hit (before it is taken off the victim's health)
function Watch(Pawn Injured, Pawn Hitter, vector Spot, int Damage, class<DamageType> DamageType)
{
	local PlayerController PC;
	local int K;
	local float D, Gain;
	local string N;
	local bool bMelee;

	if (Damage <= 0 || Injured == None || DamageType == None || !class'ModGore'.default.bBlood)
		return;
	if (!DamageType.default.bCausesBlood || Injured.IsA('Vehicle') || Injured.IsA('Turret'))
		return;
	K = class'ModGore'.static.BloodKind(Injured);
	if (K == 0)
		return;
	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None)
		return;
	if (VSize(Spot - Injured.Location) > Injured.CollisionRadius * 3)
		Spot = Injured.Location;
	// the lens: a bleeding hit near the player (the layer judges it from the camera)
	if (bLens && Injured != PC.Pawn && VSize(Spot - PC.Pawn.Location) < LensNear && Level.TimeSeconds - LastLens > 0.1)
	{
		LastLens = Level.TimeSeconds;
		class'ModSettings'.static.NativeCall("Blood:lensat " $ int(Spot.X) $ " " $ int(Spot.Y) $ " " $ int(Spot.Z)
			$ " " $ FClamp(Damage / 60.0, 0.25, 1.0) $ " " $ K);
	}
	// the hands: the player's own hits up close
	if (!bHands || Injured == PC.Pawn || Hitter != PC.Pawn)
		return;
	D = VSize(Injured.Location - PC.Pawn.Location);
	N = Caps(string(DamageType.Name));
	bMelee = InStr(N, "HANDATTACK") >= 0 || InStr(N, "MELEE") >= 0 || (Gore != None && Gore.Melee != None && Gore.Melee.bInHand);
	if (bMelee && D < KillReach)
		Gain = 0.15 + FClamp(Damage / 200.0, 0, 0.2);
	else if (D < KillReach && Damage >= Injured.Health)
		Gain = 0.05 + 0.25 * (1 - D / KillReach);
	else if (D < KillReach * 0.5)
		Gain = 0.03;
	if (Gain <= 0)
		return;
	if (Damage >= Injured.Health)
	{
		if (bMelee)
			Gain *= 1.6;
		// blown apart (ModGore gibs past this much overkill): it goes everywhere
		if (Damage - Max(Injured.Health, 0) >= class'ModGore'.default.GibOverkill)
			Gain += 0.3 * (1 - D / KillReach);
	}
	AddBlood(Gain, K);
}

function AddBlood(float Gain, int K)
{
	if (Gain <= 0 || K == 0)
		return;
	// the colour of the blood that is most of it
	if (Gain > Amount * 0.5 || Amount < 0.1)
		Kind = K;
	Amount = FMin(1.0, Amount + Gain);
	LastAdd = Level.TimeSeconds;
	bSentOff = false;
}

event Tick(float DeltaTime)
{
	local PlayerController PC;
	local ModGore G;

	PC = Level.GetLocalPlayerController();
	if (PC == None || PC.Pawn == None || Level.Game == None || Level.Game.IsInFrontEnd)
	{
		HandsOff();
		return;
	}
	if (Gore == None || Gore.bDeleteMe)
	{
		Gore = None;
		GoreLook -= DeltaTime;
		if (GoreLook <= 0)
		{
			GoreLook = 1.0;
			ForEach DynamicActors(class'ModGore', G)
			{
				Gore = G;
				break;
			}
		}
	}
	if (PC.Pawn != Me)
	{
		// a new body (respawned, a loaded save): clean hands
		Me = PC.Pawn;
		Amount = 0;
		LastCoat = 0;
		bToldBones = false;
	}
	WatchCoat();
	WatchScreenBlood();
	if (Amount > 0)
		Amount = FMax(0, Amount - DeltaTime / FMax(FadeSecs, 1));
	if (!bHands || Amount <= 0.005 || Me.IsA('Vehicle'))
	{
		HandsOff();
		return;
	}
	SendHands(Me);
}

// blood landing on the player (ModGore's coat on the player's pawn grows): some on the hands
function WatchCoat()
{
	local ModBloodCoat C;

	if (Gore == None)
		return;
	C = Gore.CoatOf(Me);
	if (C == None)
	{
		LastCoat = 0;
		return;
	}
	if (C.Amount > LastCoat + 0.01)
		AddBlood((C.Amount - LastCoat) * CoatShare, C.Kind);
	LastCoat = C.Amount;
}

// ModScreenBlood's splats (ModGore.ScreenSplash): each new one is the lens's too; when the layer
// takes it, the HUD splat goes
function WatchScreenBlood()
{
	local ModScreenBlood B;
	local int i, n, K;
	local float Size;
	local byte bNew[12];             // (bool arrays aren't allowed)

	B = class'ModScreenBlood'.default.Live;
	if (B == None)
		return;
	K = 1;
	for (i = 0; i < 12; i++)
	{
		if (B.SplatTex(i) == None)
		{
			SplatAge[i] = -1;
			continue;
		}
		// new: the slot was empty, or its age went back (a fresh splat in an old slot)
		if (SplatAge[i] < 0 || B.SplatAge(i) < SplatAge[i])
		{
			bNew[i] = 1;
			n++;
			Size = FMax(Size, B.SplatSize(i));
			if (InStr(Caps(string(B.SplatTex(i).Name)), "ALIEN") >= 0)
				K = 2;
		}
		SplatAge[i] = B.SplatAge(i);
	}
	if (n == 0)
		return;
	if (bHands)
		AddBlood(0.04 * n, K);
	if (!bLens)
		return;
	// (ModScreenBlood: size = (0.16..0.38) x (0.6 + 0.6 strength) of the screen's height)
	if (class'ModSettings'.static.NativeCall("Blood:lens " $ FClamp(0.2 + 0.12 * n + Size, 0.25, 1.0) $ " " $ K) && bReplaceScreenBlood)
	{
		for (i = 0; i < 12; i++)
			if (bNew[i] != 0)
			{
				B.DropSplat(i);
				SplatAge[i] = -1;
			}
	}
}

function HandsOff()
{
	if (bSentOff)
		return;
	class'ModSettings'.static.NativeCall("Blood:hands 0 " $ Kind $ " 0 " $ Seed $ " 0");
	bSentOff = true;
	SentCaps = 0;
}

// the capsules: each arm (elbow to fingertips), the weapons in the hands, the blade
function SendHands(Pawn P)
{
	local int n, s;
	local coords H, F;
	local vector A, B, X, Y, Z, Tip;
	local WeaponBase W;
	local float Wet;

	if (bLogBones && !bToldBones)
		LogBones(P);
	for (s = 0; s < 2; s++)
	{
		H = P.GetBoneCoords(HandBones[s]);
		F = P.GetBoneCoords(ArmBones[s]);
		if (H.Origin == vect(0,0,0) || F.Origin == vect(0,0,0) || VSize(H.Origin - F.Origin) < 1)
			continue;
		Tip = H.Origin + Normal(H.Origin - F.Origin) * HandLength;
		// thin up the forearm, full on the hand
		SendCap(n, F.Origin, Tip, ArmRadius, H.YAxis, 0.35, 1.0);
		n++;
	}
	for (s = 0; s < 2 && n < 5; s++)
	{
		if (s == 0)
			W = P.RightWeapon;
		else
			W = P.LeftWeapon;
		if (W == None || W.bHidden || W.Base != P || (W.AttachmentBone != HandBones[0] && W.AttachmentBone != HandBones[1]))
			continue;
		// grip to muzzle: the muzzle is the weapon's fire point (AdventWeapon), else a guess
		GetAxes(W.Rotation, X, Y, Z);
		A = W.Location;
		B = A + X * 16;
		if (AdventWeapon(W) != None)
		{
			Tip = A + AdventWeapon(W).WeaponFirePointOffset.X * X + AdventWeapon(W).WeaponFirePointOffset.Y * Y + AdventWeapon(W).WeaponFirePointOffset.Z * Z;
			if (VSize(Tip - A) > 4 && VSize(Tip - A) < 120)
				B = Tip;
		}
		SendCap(n, A, B, WeaponRadius, Y, 0.9, 0.25);
		n++;
	}
	if (n < 5 && Gore != None && Gore.Melee != None && Gore.Melee.bInHand && Gore.Melee.Carried != None)
	{
		// the energy blade: along its X (a guess; bLogBones notes its axes)
		GetAxes(Gore.Melee.Carried.Rotation, X, Y, Z);
		A = Gore.Melee.Carried.Location;
		SendCap(n, A, A + X * BladeLength, BladeRadius, Y, 1.0, 0.6);
		n++;
	}
	Wet = FClamp(1 - (Level.TimeSeconds - LastAdd) / FMax(DrySecs, 1), 0, 1);
	class'ModSettings'.static.NativeCall("Blood:hands " $ int(Amount * 100) $ " " $ Kind $ " " $ int(Wet * 100) $ " " $ Seed $ " " $ n);
	SentCaps = n;
	bSentOff = false;
}

function SendCap(int K, vector A, vector B, float R, vector Side, float WA, float WB)
{
	class'ModSettings'.static.NativeCall("Blood:hand " $ K $ " " $ int(A.X) $ " " $ int(A.Y) $ " " $ int(A.Z)
		$ " " $ int(B.X) $ " " $ int(B.Y) $ " " $ int(B.Z) $ " " $ R
		$ " " $ int(Side.X * 100) $ " " $ int(Side.Y * 100) $ " " $ int(Side.Z * 100)
		$ " " $ int(WA * 100) $ " " $ int(WB * 100));
}

// once a level: which of the arm bones the player's mesh has, and where the weapons sit
function LogBones(Pawn P)
{
	local int s;
	local coords C;
	local vector X, Y, Z;
	local WeaponBase W;

	bToldBones = true;
	class'ModSettings'.static.Note("playerblood: mesh " $ P.Mesh $ " at " $ P.Location);
	for (s = 0; s < 2; s++)
	{
		C = P.GetBoneCoords(HandBones[s]);
		class'ModSettings'.static.Note("playerblood: bone " $ HandBones[s] $ " at " $ (C.Origin - P.Location) $ " x " $ C.XAxis $ " y " $ C.YAxis);
		C = P.GetBoneCoords(ArmBones[s]);
		class'ModSettings'.static.Note("playerblood: bone " $ ArmBones[s] $ " at " $ (C.Origin - P.Location));
		if (s == 0)
			W = P.RightWeapon;
		else
			W = P.LeftWeapon;
		if (W != None)
		{
			GetAxes(W.Rotation, X, Y, Z);
			C = P.GetBoneCoords(HandBones[s]);
			class'ModSettings'.static.Note("playerblood: weapon " $ W $ " on " $ W.AttachmentBone $ " hidden " $ W.bHidden
				$ ", " $ (W.Location - C.Origin) $ " from the hand, x " $ X);
			if (AdventWeapon(W) != None)
				class'ModSettings'.static.Note("playerblood: its fire point " $ AdventWeapon(W).WeaponFirePointOffset);
		}
	}
}

event Destroyed()
{
	HandsOff();
	Super.Destroyed();
}

defaultproperties
{
     bHands=True
     bLens=True
     bReplaceScreenBlood=True
     FadeSecs=150.000000
     DrySecs=45.000000
     ArmRadius=5.500000
     HandLength=8.000000
     WeaponRadius=4.500000
     BladeRadius=3.500000
     BladeLength=30.000000
     KillReach=200.000000
     LensNear=300.000000
     CoatShare=0.500000
     HandBones(0)=rightHand
     HandBones(1)=leftHand
     ArmBones(0)=rightForeArm
     ArmBones(1)=leftForeArm
     bLogBones=True
}
