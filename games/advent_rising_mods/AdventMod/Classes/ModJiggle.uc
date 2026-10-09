//=============================================================================
// ModJiggle - secondary flesh motion on the Seeker infantry (JIGGLE.md). One per level (ModMoves
// spawns it). Every Seeker infantry within range of the player is re-linked to the re-rigged mesh
// (ModJiggleMesh: the stock mesh plus ten J_ leaf bones weighted to flesh only; the armour keeps
// its ordinary bones), and every half second each one is hooked in the DLL ("Jiggle <pawn>
// <class> <n> <bone indices>"): native/jiggle.c turns each J_ bone inside the pose build with a
// damped spring driven by the body's own acceleration and by hits (ModReact's flinch calls Hit).
// The springs per bone come from ModJiggleBones (generated from the soft-body fit), scaled by
// StiffScale / DampScale / Gain here, each overridable per bone through OverK/OverD/OverGain/
// OverMaxDeg (0 = keep the table's).
// Config [AdventMod.ModJiggle]: bJiggle (on since the 2026-10-09 runs, JIGGLE.md), Gain, Range, bJiggleLog
// (the DLL's 5-s amplitude lines), StiffScale, DampScale, HitStrength (rad/s of swing per hit at
// 20 damage), MaxAccel (units/s^2 the driver is clamped to), bRelink (Seeker infantry in range
// get LinkMesh to the jiggle mesh, once each), the Over* arrays.
//=============================================================================
class ModJiggle extends Info
	config(AdventMod);

var config bool bJiggle;
var config float Gain;
var config float Range;
var config bool bJiggleLog;
var config float StiffScale;
var config float DampScale;
var config float HitStrength;
var config float MaxAccel;
var config bool bRelink;
var config float OverK[16];
var config float OverD[16];
var config float OverGain[16];
var config float OverMaxDeg[16];

struct Hooked
{
	var Pawn P;
	var bool bHooked;
	var int Tries;
};
var array<Hooked> Hooks;
var float SweepWait;
var bool bConfigSent, bNativeOk;
var SkeletalMesh JMesh;
var Material Skin;
var MeshAnimation Sets[4];
var int Relinked;

function PostBeginPlay()
{
	Super.PostBeginPlay();
	if (!bJiggle)
		return;
	JMesh = class'ModJiggleMesh'.default.JiggleMesh;
	if (JMesh == None)
	{
		class'ModSettings'.static.Note("jiggle: no jiggle mesh in the package: off");
		return;
	}
	Skin = Material(DynamicLoadObject("seekercharacters_tx.Main.infantry_hsh", class'Material', true));
	Sets[0] = MeshAnimation(DynamicLoadObject("Seekers.Base", class'MeshAnimation', true));
	Sets[1] = MeshAnimation(DynamicLoadObject("Seekers.Reactions", class'MeshAnimation', true));
	Sets[2] = MeshAnimation(DynamicLoadObject("Seekers.Targeting", class'MeshAnimation', true));
	Sets[3] = MeshAnimation(DynamicLoadObject("Seekers.ambient", class'MeshAnimation', true));
	class'ModSettings'.static.Note("jiggle: on (gain " $ Gain $ ", stiff x" $ StiffScale $ ", damp x" $ DampScale $ ", hit " $ HitStrength $ "), mesh " $ JMesh.Name $ ", skin " $ (Skin != None) $ ", sets " $ (Sets[0] != None) $ (Sets[1] != None) $ (Sets[2] != None) $ (Sets[3] != None) $ ", relink " $ bRelink);
}

static function string Eval2(bool B, string T, string F)
{
	if (B)
		return T;
	return F;
}

// the DLL's parameters: once, after the first native answer
function bool SendConfig()
{
	local int i;
	local float K, D, G, M;
	local string Cmd;

	if (!class'ModSettings'.static.NativeCall("JiggleConfig " $ Gain $ " " $ Eval2(bJiggleLog, "1", "0") $ " " $ MaxAccel))
		return false;
	for (i = 0; i < class'ModJiggleBones'.default.Count; i++)
	{
		K = class'ModJiggleBones'.default.K[i] * StiffScale;
		D = class'ModJiggleBones'.default.D[i] * DampScale;
		G = class'ModJiggleBones'.default.Gain[i];
		M = class'ModJiggleBones'.default.MaxDeg[i];
		if (OverK[i] > 0)
			K = OverK[i];
		if (OverD[i] > 0)
			D = OverD[i];
		if (OverGain[i] > 0)
			G = OverGain[i];
		if (OverMaxDeg[i] > 0)
			M = OverMaxDeg[i];
		Cmd = "JiggleBone " $ class'ModJiggleBones'.default.Names[i] $ " " $ K $ " " $ D $ " " $ G $ " " $ M $ " "
			$ class'ModJiggleBones'.default.Lever[i].X $ " " $ class'ModJiggleBones'.default.Lever[i].Y $ " " $ class'ModJiggleBones'.default.Lever[i].Z;
		if (!class'ModSettings'.static.NativeCall(Cmd))
			class'ModSettings'.static.Note("jiggle: the DLL declined " $ Cmd);
	}
	return true;
}

function int Find(Pawn P)
{
	local int i;

	for (i = 0; i < Hooks.Length; i++)
		if (Hooks[i].P == P)
			return i;
	Hooks.Length = Hooks.Length + 1;
	Hooks[Hooks.Length - 1].P = P;
	return Hooks.Length - 1;
}

function bool Alive(Pawn P)
{
	if (P == None || P.bDeleteMe || P.Health <= 0 || P.Mesh == None)
		return false;
	return P.Physics == PHYS_Walking || P.Physics == PHYS_Falling || P.Physics == PHYS_RootMotion;
}

// a Seeker infantry on the stock mesh: the jiggle mesh instead. Actor.Mesh is const, so the class
// default can't be swapped: every Seeker infantry in range gets LinkMesh once (bKeepAnim), its
// animation sets linked again and the skin set
function bool Relink(Pawn P)
{
	local int i;

	if (!bRelink || !P.IsA('SeekerInfantry') || Caps(string(P.Mesh.Name)) != "SEEKERINFANTRY")
		return false;
	P.LinkMesh(JMesh, true);
	for (i = 0; i < 4; i++)
		if (Sets[i] != None)
			P.LinkSkelAnim(Sets[i]);
	Relinked++;
	if (bJiggleLog)
		class'ModSettings'.static.Note("jiggle: " $ P.Name $ " relinked to the jiggle mesh");
	return true;
}

function bool Hook(int i)
{
	local Pawn P;
	local int b, n, Idx;
	local string Cmd;

	P = Hooks[i].P;
	if (P.Skins.Length == 0 && Skin != None)
	{
		P.Skins.Length = 1;
		P.Skins[0] = Skin;
	}
	Cmd = "";
	n = 0;
	for (b = 0; b < class'ModJiggleBones'.default.Count; b++)
	{
		Idx = P.MatchRefBone(class'ModJiggleBones'.default.Names[b]);
		if (Idx < 1)
			continue;
		Cmd = Cmd $ " " $ Idx;
		n++;
	}
	if (n == 0)
	{
		Hooks[i].Tries = 100;       // not this skeleton
		return false;
	}
	P.GetBoneCoords('spine');       // the instance exists once posed
	Cmd = "Jiggle " $ P.Name $ " " $ P.Class.Name $ " " $ n $ Cmd;
	if (!class'ModSettings'.static.NativeCall(Cmd))
	{
		Hooks[i].Tries++;
		if (bJiggleLog && Hooks[i].Tries <= 2)
			class'ModSettings'.static.Note("jiggle: the DLL declined " $ Cmd);
		return false;
	}
	Hooks[i].bHooked = true;
	if (bJiggleLog)
		class'ModSettings'.static.Note("jiggle: hooked " $ P.Name $ " (" $ n $ " bones)");
	return true;
}

function Release(int i)
{
	if (Hooks[i].bHooked && Hooks[i].P != None && !Hooks[i].P.bDeleteMe)
		class'ModSettings'.static.NativeCall("JiggleOff " $ Hooks[i].P.Name $ " " $ Hooks[i].P.Class.Name);
	Hooks[i].bHooked = false;
}

function Sweep()
{
	local Pawn P, Player;
	local PlayerController PC;
	local int i;
	local bool bWant;

	if (!bConfigSent)
	{
		bNativeOk = SendConfig();
		bConfigSent = bNativeOk;
		if (!bNativeOk)
			return;
	}
	PC = Level.GetLocalPlayerController();
	if (PC != None)
		Player = PC.Pawn;
	foreach DynamicActors(class'Pawn', P)
	{
		if (!Alive(P) || PlayerController(P.Controller) != None)
			continue;
		if (P.Mesh != JMesh)
		{
			if (Player == None || VSize(P.Location - Player.Location) <= Range)
				Relink(P);
			continue;
		}
		i = Find(P);
		bWant = Player == None || VSize(P.Location - Player.Location) <= Range;
		if (bWant && !Hooks[i].bHooked && Hooks[i].Tries < 5)
			Hook(i);
		else if (!bWant && Hooks[i].bHooked)
			Release(i);
	}
	for (i = Hooks.Length - 1; i >= 0; i--)
	{
		if (Hooks[i].P == None || Hooks[i].P.bDeleteMe)
		{
			Hooks.Remove(i, 1);
			continue;
		}
		if (Hooks[i].bHooked && !Alive(Hooks[i].P))
			Release(i);
	}
}

// a hit: the flesh swings away from it (ModReact.Flinch)
function Hit(Pawn P, vector Dir, int Damage)
{
	local int i;

	if (!bJiggle || !bNativeOk)
		return;
	for (i = 0; i < Hooks.Length; i++)
		if (Hooks[i].P == P && Hooks[i].bHooked)
		{
			Dir = Normal(Dir);
			class'ModSettings'.static.NativeCall("JiggleHit " $ P.Name $ " " $ P.Class.Name $ " " $ Dir.X $ " " $ Dir.Y $ " " $ Dir.Z $ " " $ (HitStrength * FClamp(Damage / 20.0, 0.3, 2.0)));
			return;
		}
}

function Tick(float DeltaTime)
{
	if (!bJiggle || JMesh == None)
		return;
	SweepWait -= DeltaTime;
	if (SweepWait <= 0)
	{
		SweepWait = 0.5;
		Sweep();
	}
}

defaultproperties
{
     bJiggle=True
     Gain=1.000000
     Range=3500.000000
     bJiggleLog=False
     StiffScale=1.000000
     DampScale=1.000000
     HitStrength=2.000000
     MaxAccel=30000.000000
     bRelink=True
}
