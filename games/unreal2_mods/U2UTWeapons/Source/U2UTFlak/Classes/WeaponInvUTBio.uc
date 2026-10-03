//=============================================================================
// WeaponInvUTBio - Unreal II's Dispersion Pistol wearing Unreal Tournament's
// GES Bio Rifle: primary lobs a gel (UTBioGel) that sticks and bursts; hold
// alt fire to charge a big glob (UTBioGlob) that sprays more gel where it
// lands. Keeps the pistol's recharging ammo and charge-up, so the starting
// weapon still never runs dry.
//
// Like the Flak Cannon and Ripper, UT's vertex-animated model is drawn from
// static meshes (one per animation frame, StaticMeshes\U2UTFlakSM.usx) because
// Unreal II never textures vertex meshes; PlayAnimEx plays UT's sequences.
//=============================================================================
class WeaponInvUTBio extends weaponInvDispersion;

#exec TEXTURE IMPORT NAME=BioAtlas FILE=Textures\BioAtlas.tga GROUP=Skins LODSET=2
#exec AUDIO IMPORT FILE=Sounds\BioGelShot.wav   NAME=BioGelShot   GROUP=Bio
#exec AUDIO IMPORT FILE=Sounds\BioGelLoad.wav   NAME=BioGelLoad   GROUP=Bio
#exec AUDIO IMPORT FILE=Sounds\BioGelSelect.wav NAME=BioGelSelect GROUP=Bio

var StaticMesh ViewFrames[91];
// fire modes (user's design, 2026-10-03): primary = the charged glob (hold, release),
// secondary = the flamethrower's flame stream, burning the player's flamethrower fuel;
// a small pilot flame burns at the muzzle while the gun is held (the flamethrower's igniter)
var bool bPrimaryCharge;
var ParticleGenerator Flame, Pilot;
var float FuelClock;
var() vector FlameOffset, PilotOffset;     // UT's BRifle2 animation, one static mesh per frame
var int AnimFirst, AnimCount;
var float AnimFPS, AnimTime;
var bool bAnimLoop;
var name AfterAnim;                // sequence to settle into when a one-shot ends

// the goo gauge on the tank: a red needle (UTBioNeedle) drawn over the gun, showing the ammo
// left. Per frame of the view animation: the gauge's pivot and axes in the mesh's space
// (canister/build_canister.py writes them), so the needle rides along with every animation
var int CurFrame;
var UTBioNeedle Needle;
var float NeedleShown;                      // smoothed ammo fraction
var() float GaugeSweep;                     // radians either side of straight up
var() vector GaugeSign;                     // mesh space -> actor space (the static mesh import mirrors X)
var vector GaugePivot[91], GaugeX[91], GaugeY[91], GaugeZ[91];

// frames live in StaticMeshes/U2UTFlakSM.usx, loaded by name on first use
simulated function StaticMesh Frame(int i)
{
	local string N;
	if (ViewFrames[i] == None)
	{
		N = string(i);
		if (i < 10)       N = "00"$N;
		else if (i < 100) N = "0"$N;
		ViewFrames[i] = StaticMesh(DynamicLoadObject("U2UTFlakSM.Bio.BioV"$N, class'StaticMesh'));
	}
	CurFrame = i;
	return ViewFrames[i];
}

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = Frame(22);
	Enable('Tick');   // the pistol only ticks while charging; we animate always
}

// PickupAmmoCount=0 means the engine never links ammo: use the pistol's rounds
// (without ammo U2 won't even let you select the weapon)
simulated function LinkAmmo()
{
	if (AmmoType == None && Pawn(Owner) != None)
		AmmoType = Ammunition(Pawn(Owner).FindInventoryType(AmmoName));
}

function GiveTo(Pawn Other, optional bool bDontTryToSwitch)
{
	Super.GiveTo(Other, bDontTryToSwitch);
	LinkAmmo();
}

simulated function bool HasAnyAmmo()
{
	LinkAmmo();
	return Super.HasAnyAmmo();
}

// UT's BRifle2 sequences: start, frames, fps, loops
simulated function bool BioSeq(name Seq, out int First, out int Count, out float FPS, out byte bLoop)
{
	FPS = 30;
	bLoop = 0;
	switch (Seq)
	{
	case 'Select':   First = 0;  Count = 22; FPS = 45; return true;
	case 'Still':    First = 22; Count = 1;  return true;
	case 'Charging': First = 41; Count = 30; return true;
	case 'Loaded':   First = 70; Count = 1;  return true;
	case 'Fire':     First = 72; Count = 9;  return true;
	case 'Down':     First = 80; Count = 10; return true;
	}
	return false;
}

simulated function PlayBio(name Seq, float Rate, name Then)
{
	local byte bLoop;
	if (!BioSeq(Seq, AnimFirst, AnimCount, AnimFPS, bLoop))
		return;
	AnimFPS *= Rate;
	AnimTime = 0;
	bAnimLoop = bLoop != 0;
	AfterAnim = Then;
	StaticMesh = Frame(AnimFirst);
}

simulated function TickBioAnim(float DeltaTime)
{
	local int f;
	if (AnimCount <= 0)
		return;
	AnimTime += DeltaTime;
	f = int(AnimTime * AnimFPS);
	if (f >= AnimCount)
	{
		if (bAnimLoop)
			f = f % AnimCount;
		else if (AfterAnim != '')
		{
			PlayBio(AfterAnim, 1.0, '');
			return;
		}
		else
			f = AnimCount - 1;
	}
	StaticMesh = Frame(AnimFirst + f);
}

// Unreal II's weapon code asks for Golem animations; map them onto UT's
simulated function PlayAnimEx(name Sequence)
{
	LastTriggeredAnim = Sequence;
	switch (Sequence)
	{
	case 'SelectAnim':   PlayBio('Select', 1.0, 'Still'); return;
	case 'DownAnim':     PlayBio('Down', 1.0, '');        return;
	case 'Fire':
	case 'AltFire':      PlayBio('Fire', 1.0, 'Still');   return;
	case 'AltFireStart': PlayBio('Charging', 1.0, 'Loaded'); return;
	}
}

simulated event Tick(float DeltaTime)
{
	Super.Tick(DeltaTime);
	TickBioAnim(DeltaTime);
	LinkAmmo();
	UpdatePilot();
	TickGauge(DeltaTime);
}

// ---- the ammo gauge ------------------------------------------------------------------------
simulated function TickGauge(float DeltaTime)
{
	local float F;
	if (AmmoType != None && AmmoType.MaxAmmo > 0)
		F = FClamp(float(AmmoType.AmmoAmount) / float(AmmoType.MaxAmmo), 0, 1);
	NeedleShown += (F - NeedleShown) * FMin(1.0, DeltaTime * 6.0);
}

simulated function vector GaugeVec(vector V)
{
	V.X *= GaugeSign.X;
	V.Y *= GaugeSign.Y;
	V.Z *= GaugeSign.Z;
	return V;
}

simulated function DrawWeapon(Canvas Canvas)
{
	Super.DrawWeapon(Canvas);
	DrawGauge(Canvas);
}

// the needle sits on the gauge's pivot in this frame and turns about the gauge's axis:
// straight up = half full, GaugeSweep either side = empty / full
simulated function DrawGauge(Canvas Canvas)
{
	local float A, C, S;
	local vector X, Y, Z, NY, NZ;
	if (Needle == None)
	{
		Needle = Spawn(class'UTBioNeedle', Self);
		if (Needle == None)
			return;
	}
	A = (NeedleShown * 2.0 - 1.0) * GaugeSweep;
	C = Cos(A);
	S = Sin(A);
	X = GaugeVec(GaugeX[CurFrame]);
	Y = GaugeVec(GaugeY[CurFrame]);
	Z = GaugeVec(GaugeZ[CurFrame]);
	NY = Y * C + Z * S;
	NZ = Z * C - Y * S;
	Needle.SetDrawScale(DrawScale);
	Needle.SetLocation(Location + ((GaugeVec(GaugePivot[CurFrame]) * DrawScale) >> Rotation));
	Needle.SetRotation(OrthoRotation(X >> Rotation, NY >> Rotation, NZ >> Rotation));
	Canvas.DrawActor(Needle, false, false, ActorFOV);
}

// the flamethrower's fuel, if the player carries it
simulated function Ammunition Fuel()
{
	if (Pawn(Owner) == None)
		return None;
	return Ammunition(Pawn(Owner).FindInventoryType(class'ammoInvFlamethrower'));
}

// where the gun points: the eye and the view rotation, offset to the muzzle
simulated function GetMuzzle(vector Offset, out vector L, out rotator R)
{
	local Pawn P;
	P = Pawn(Owner);
	R = P.GetViewRotation();
	L = P.Location + P.EyePosition() + (Offset >> R);
}

simulated function ParticleGenerator MakeFx(string Name)
{
	local ParticleGenerator G;
	local ParticleGenerator Template;
	Template = ParticleGenerator(DynamicLoadObject(Name, class'ParticleGenerator', true));
	if (Template == None)
		return None;
	G = class'ParticleGenerator'.static.CreateNew(Self, Template, Location);
	if (G != None)
		G.bOn = false;
	return G;
}

// the flamethrower's own pilot light: a small particle flame its mesh mounts at "Pilot";
// copied from a flamethrower the player carries (its attachments exist once it was held)
simulated function ParticleGenerator FindFlamePilot()
{
	local Inventory I;
	local array<Actor> A;
	for (I = Pawn(Owner).Inventory; I != None; I = I.Inventory)
		if (I.IsA('weaponInvFlamethrower'))
		{
			I.MeshGetAttachments("Pilot", A);
			if (A.Length > 0 && ParticleGenerator(A[0]) != None)
				return ParticleGenerator(A[0]);
		}
	return None;
}

// the pilot flame burns while the gun is out
simulated function UpdatePilot()
{
	local vector L;
	local rotator R;
	local bool bHeld;
	bHeld = Pawn(Owner) != None && Pawn(Owner).Weapon == Self && Pawn(Owner).Health > 0 && !PhysicsVolume.bWaterVolume;
	if (bHeld && Pilot == None && FindFlamePilot() != None)
	{
		Pilot = class'ParticleGenerator'.static.CreateNew(Self, FindFlamePilot(), Location);
		if (Pilot != None)
			Pilot.SetDrawScale(0.25);
	}
	if (Pilot == None)
		return;
	Pilot.bOn = bHeld;
	if (bHeld)
	{
		GetMuzzle(PilotOffset, L, R);
		Pilot.SetLocation(L);
		Pilot.SetRotation(R);
	}
}

// primary: start charging a glob (the pistol's alt fire), released with the primary button
simulated function Fire()
{
	if (Pawn(Owner) == None || !Pawn(Owner).PressingFire() || bDisableFiring)
		return;
	bFiring = false;
	bAltFiring = true;
	if (U2Ammo(AmmoType) != None && !U2Ammo(AmmoType).ReloadRequired(1))
	{
		if (PreSetAimingParameters(true, bAltInstantHit, TraceSpreadAltFire, AltProjectileClass, bAltWarnTarget, bRecommendAltSplashDamage))
		{
			bPrimaryCharge = true;
			EverywhereAltFire();
		}
	}
	else if (HasAmmo())
		Reload();
}

// secondary: the flame stream, while the button is held and there is fuel
simulated function AltFire()
{
	local Ammunition A;
	if (Pawn(Owner) == None || !Pawn(Owner).PressingAltFire() || bDisableFiring)
		return;
	A = Fuel();
	if (A == None || A.AmmoAmount <= 0 || PhysicsVolume.bWaterVolume)
		return;
	GotoState('Flaming');
}

simulated state Flaming
{
	ignores Fire, AltFire;

	simulated event BeginState()
	{
		if (Flame == None)
			Flame = MakeFx("Flamethrower_Effects.ParticleSalamander1");
		if (Flame != None)
			Flame.bOn = true;
		AmbientSound = Sound'U2WeaponsA.FlameThrower.FT_FireLoop';
		PlaySound(Sound'U2WeaponsA.FlameThrower.FT_Select', SLOT_None, 1.0);
		FuelClock = 0;
		Enable('Tick');
	}

	simulated event EndState()
	{
		if (Flame != None)
			Flame.bOn = false;
		AmbientSound = None;
		PlaySound(Sound'U2WeaponsA.FlameThrower.FT_FireEnd', SLOT_None, 1.0);
	}

	simulated event Tick(float DeltaTime)
	{
		local vector L;
		local rotator R;
		local Ammunition A;

		TickBioAnim(DeltaTime);
		UpdatePilot();
		A = Fuel();
		if (Pawn(Owner) == None || !Pawn(Owner).PressingAltFire() || A == None || A.AmmoAmount <= 0 || PhysicsVolume.bWaterVolume)
		{
			GotoState('Idle');
			return;
		}
		GetMuzzle(FlameOffset, L, R);
		if (Flame != None)
		{
			Flame.SetLocation(L);
			Flame.SetRotation(R);
		}
		FuelClock += DeltaTime;
		while (FuelClock >= 0.1)          // 10 fuel a second: a full 400 tank burns 40 s
		{
			FuelClock -= 0.1;
			A.UseAmmo(1);
		}
	}
}

simulated event Destroyed()
{
	if (Flame != None)
		Flame.Destroy();
	if (Pilot != None)
		Pilot.Destroy();
	if (Needle != None)
		Needle.Destroy();
	Super.Destroyed();
}

// the pistol's charge state replaces Tick while charging - keep animating
simulated state AltCharging
{
	// released with whichever button started it (primary now, see Fire)
	simulated event Tick(float DeltaTime)
	{
		local bool bHeld;
		TickBioAnim(DeltaTime);
		UpdatePilot();
		TickGauge(DeltaTime);
		if (bPrimaryCharge)
			bHeld = Pawn(Owner).PressingFire();
		else
			bHeld = Pawn(Owner).PressingAltFire();
		if (!bHeld)
		{
			bPrimaryCharge = false;
			if (Role == ROLE_Authority)
				Super(U2Weapon).AuthorityAltFire();
			Super(U2Weapon).EverywhereAltFire();
			FireMode = FM_AltFire;
		}
		AltEnergyTimer -= DeltaTime;
		while (AltEnergyTimer <= 0)
		{
			AltEnergyTimer += default.AltEnergyTimer;
			IncAltEnergy();
		}
	}
	simulated event EndState()
	{
		Super.EndState();
		Enable('Tick');   // the pistol switches Tick off here
	}
}

// keep UT's gel sound for the glob (the pistol swaps in its own alt-fire sounds)
simulated function NotifyPlaySoundSlot(string Slot)
{
	Super(U2Weapon).NotifyPlaySoundSlot(Slot);
}

// alt fire: a glob sized by the charge (the pistol's AltEnergy)
function Projectile ProjectileFire(class<projectile> ProjClass)
{
	local Projectile P;
	if (ProjClass == AltProjectileClass)
	{
		P = Super(U2Weapon).ProjectileFire(class'UTBioGlob');
		if (UTBioGlob(P) != None)
			UTBioGlob(P).SetCharge(float(AltEnergy) / float(MaxAltEnergy));
		return P;
	}
	return Super(U2Weapon).ProjectileFire(ProjClass);
}

defaultproperties
{
	DrawType=DT_StaticMesh
	bUnlit=True
	Skins(0)=Texture'BioAtlas'
	// UT: PlayerViewOffset (1.7,-0.85,-0.95), scale 1.0 -> 10x bigger and
	// further away for Unreal II's near clip; meshes are exported 100x larger
	DrawScale=0.100000
	PlayerViewOffset=(X=17.000000,Y=8.500000,Z=-9.500000)
	FirstPersonOffset=(X=0.000000,Y=0.000000,Z=0.000000)
	FireOffset=(X=25.000000,Y=9.000000,Z=-6.000000)
	FlameOffset=(X=40.000000,Y=9.000000,Z=-8.000000)
	PilotOffset=(X=40.000000,Y=6.000000,Z=-3.500000)
	GaugeSweep=2.300000
	GaugeSign=(X=-1.000000,Y=1.000000,Z=1.000000)
	// generated by canister/build_canister.py (gauge_pivots.txt)
	GaugePivot(0)=(X=43.670,Y=-38.144,Z=-29.410)
	GaugeX(0)=(X=0.4236,Y=0.9017,Z=0.0873)
	GaugeY(0)=(X=-0.9052,Y=0.4176,Z=0.0791)
	GaugeZ(0)=(X=0.0349,Y=-0.1125,Z=0.9930)
	GaugePivot(1)=(X=43.670,Y=-38.144,Z=-29.410)
	GaugeX(1)=(X=0.4236,Y=0.9017,Z=0.0873)
	GaugeY(1)=(X=-0.9052,Y=0.4176,Z=0.0791)
	GaugeZ(1)=(X=0.0349,Y=-0.1125,Z=0.9930)
	GaugePivot(2)=(X=42.795,Y=-28.250,Z=-17.067)
	GaugeX(2)=(X=0.4496,Y=0.8930,Z=0.0193)
	GaugeY(2)=(X=-0.8908,Y=0.4467,Z=0.0831)
	GaugeZ(2)=(X=0.0657,Y=-0.0545,Z=0.9964)
	GaugePivot(3)=(X=42.555,Y=-18.713,Z=-4.995)
	GaugeX(3)=(X=0.4694,Y=0.8813,Z=-0.0546)
	GaugeY(3)=(X=-0.8769,Y=0.4725,Z=0.0879)
	GaugeZ(3)=(X=0.1033,Y=0.0066,Z=0.9946)
	GaugePivot(4)=(X=42.832,Y=-9.227,Z=6.162)
	GaugeX(4)=(X=0.4841,Y=0.8647,Z=-0.1339)
	GaugeY(4)=(X=-0.8630,Y=0.4971,Z=0.0900)
	GaugeZ(4)=(X=0.1444,Y=0.0720,Z=0.9869)
	GaugePivot(5)=(X=43.380,Y=-0.178,Z=16.243)
	GaugeX(5)=(X=0.4957,Y=0.8421,Z=-0.2123)
	GaugeY(5)=(X=-0.8482,Y=0.5220,Z=0.0899)
	GaugeZ(5)=(X=0.1865,Y=0.1355,Z=0.9731)
	GaugePivot(6)=(X=44.212,Y=8.301,Z=25.559)
	GaugeX(6)=(X=0.5041,Y=0.8144,Z=-0.2876)
	GaugeY(6)=(X=-0.8323,Y=0.5470,Z=0.0899)
	GaugeZ(6)=(X=0.2305,Y=0.1940,Z=0.9535)
	GaugePivot(7)=(X=45.022,Y=16.170,Z=33.452)
	GaugeX(7)=(X=0.5124,Y=0.7804,Z=-0.3584)
	GaugeY(7)=(X=-0.8149,Y=0.5735,Z=0.0837)
	GaugeZ(7)=(X=0.2709,Y=0.2492,Z=0.9298)
	GaugePivot(8)=(X=45.794,Y=22.955,Z=40.433)
	GaugeX(8)=(X=0.5224,Y=0.7429,Z=-0.4185)
	GaugeY(8)=(X=-0.7956,Y=0.6013,Z=0.0743)
	GaugeZ(8)=(X=0.3068,Y=0.2942,Z=0.9052)
	GaugePivot(9)=(X=46.269,Y=28.546,Z=46.364)
	GaugeX(9)=(X=0.5369,Y=0.7026,Z=-0.4670)
	GaugeY(9)=(X=-0.7726,Y=0.6318,Z=0.0624)
	GaugeZ(9)=(X=0.3389,Y=0.3273,Z=0.8820)
	GaugePivot(10)=(X=46.418,Y=32.748,Z=51.660)
	GaugeX(10)=(X=0.5596,Y=0.6615,Z=-0.4991)
	GaugeY(10)=(X=-0.7450,Y=0.6654,Z=0.0466)
	GaugeZ(10)=(X=0.3630,Y=0.3458,Z=0.8653)
	GaugePivot(11)=(X=46.025,Y=35.459,Z=56.166)
	GaugeX(11)=(X=0.5917,Y=0.6209,Z=-0.5141)
	GaugeY(11)=(X=-0.7117,Y=0.7019,Z=0.0286)
	GaugeZ(11)=(X=0.3786,Y=0.3490,Z=0.8572)
	GaugePivot(12)=(X=45.111,Y=36.145,Z=59.827)
	GaugeX(12)=(X=0.6357,Y=0.5792,Z=-0.5103)
	GaugeY(12)=(X=-0.6697,Y=0.7426,Z=0.0086)
	GaugeZ(12)=(X=0.3839,Y=0.3363,Z=0.8599)
	GaugePivot(13)=(X=43.773,Y=34.778,Z=62.562)
	GaugeX(13)=(X=0.6897,Y=0.5348,Z=-0.4882)
	GaugeY(13)=(X=-0.6181,Y=0.7860,Z=-0.0123)
	GaugeZ(13)=(X=0.3771,Y=0.3103,Z=0.8726)
	GaugePivot(14)=(X=42.044,Y=31.859,Z=64.496)
	GaugeX(14)=(X=0.7494,Y=0.4862,Z=-0.4495)
	GaugeY(14)=(X=-0.5568,Y=0.8301,Z=-0.0303)
	GaugeZ(14)=(X=0.3584,Y=0.2729,Z=0.8928)
	GaugePivot(15)=(X=39.942,Y=28.026,Z=65.353)
	GaugeX(15)=(X=0.8094,Y=0.4318,Z=-0.3980)
	GaugeY(15)=(X=-0.4867,Y=0.8725,Z=-0.0433)
	GaugeZ(15)=(X=0.3285,Y=0.2287,Z=0.9164)
	GaugePivot(16)=(X=37.720,Y=23.881,Z=65.594)
	GaugeX(16)=(X=0.8663,Y=0.3705,Z=-0.3352)
	GaugeY(16)=(X=-0.4091,Y=0.9111,Z=-0.0504)
	GaugeZ(16)=(X=0.2867,Y=0.1808,Z=0.9408)
	GaugePivot(17)=(X=35.318,Y=19.986,Z=64.925)
	GaugeX(17)=(X=0.9152,Y=0.3032,Z=-0.2657)
	GaugeY(17)=(X=-0.3276,Y=0.9434,Z=-0.0520)
	GaugeZ(17)=(X=0.2349,Y=0.1346,Z=0.9627)
	GaugePivot(18)=(X=32.873,Y=16.621,Z=63.568)
	GaugeX(18)=(X=0.9541,Y=0.2300,Z=-0.1919)
	GaugeY(18)=(X=-0.2429,Y=0.9690,Z=-0.0462)
	GaugeZ(18)=(X=0.1753,Y=0.0907,Z=0.9803)
	GaugePivot(19)=(X=30.636,Y=14.252,Z=61.954)
	GaugeX(19)=(X=0.9808,Y=0.1529,Z=-0.1208)
	GaugeY(19)=(X=-0.1580,Y=0.9869,Z=-0.0337)
	GaugeZ(19)=(X=0.1141,Y=0.0522,Z=0.9921)
	GaugePivot(20)=(X=28.551,Y=13.343,Z=59.947)
	GaugeX(20)=(X=0.9956,Y=0.0755,Z=-0.0548)
	GaugeY(20)=(X=-0.0765,Y=0.9969,Z=-0.0176)
	GaugeZ(20)=(X=0.0533,Y=0.0217,Z=0.9983)
	GaugePivot(21)=(X=26.799,Y=13.992,Z=58.000)
	GaugeX(21)=(X=1.0000,Y=0.0000,Z=0.0000)
	GaugeY(21)=(X=-0.0000,Y=1.0000,Z=0.0001)
	GaugeZ(21)=(X=-0.0000,Y=-0.0001,Z=1.0000)
	GaugePivot(22)=(X=26.800,Y=14.000,Z=58.000)
	GaugeX(22)=(X=1.0000,Y=0.0000,Z=0.0000)
	GaugeY(22)=(X=-0.0000,Y=1.0000,Z=0.0000)
	GaugeZ(22)=(X=-0.0000,Y=0.0000,Z=1.0000)
	GaugePivot(23)=(X=26.800,Y=14.000,Z=58.000)
	GaugeX(23)=(X=1.0000,Y=0.0000,Z=0.0000)
	GaugeY(23)=(X=-0.0000,Y=1.0000,Z=0.0000)
	GaugeZ(23)=(X=-0.0000,Y=0.0000,Z=1.0000)
	GaugePivot(24)=(X=26.800,Y=14.000,Z=58.000)
	GaugeX(24)=(X=1.0000,Y=0.0000,Z=0.0000)
	GaugeY(24)=(X=-0.0000,Y=1.0000,Z=0.0000)
	GaugeZ(24)=(X=-0.0000,Y=0.0000,Z=1.0000)
	GaugePivot(25)=(X=26.795,Y=14.011,Z=58.001)
	GaugeX(25)=(X=1.0000,Y=-0.0000,Z=0.0000)
	GaugeY(25)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(25)=(X=-0.0000,Y=0.0001,Z=1.0000)
	GaugePivot(26)=(X=26.795,Y=14.011,Z=58.001)
	GaugeX(26)=(X=1.0000,Y=-0.0000,Z=0.0000)
	GaugeY(26)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(26)=(X=-0.0000,Y=0.0001,Z=1.0000)
	GaugePivot(27)=(X=26.795,Y=14.011,Z=58.001)
	GaugeX(27)=(X=1.0000,Y=-0.0000,Z=0.0000)
	GaugeY(27)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(27)=(X=-0.0000,Y=0.0001,Z=1.0000)
	GaugePivot(28)=(X=26.795,Y=14.011,Z=58.001)
	GaugeX(28)=(X=1.0000,Y=-0.0000,Z=0.0000)
	GaugeY(28)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(28)=(X=-0.0000,Y=0.0001,Z=1.0000)
	GaugePivot(29)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(29)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(29)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(29)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(30)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(30)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(30)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(30)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(31)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(31)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(31)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(31)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(32)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(32)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(32)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(32)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(33)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(33)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(33)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(33)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(34)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(34)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(34)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(34)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(35)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(35)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(35)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(35)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(36)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(36)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(36)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(36)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(37)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(37)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(37)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(37)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(38)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(38)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(38)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(38)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(39)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(39)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(39)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(39)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(40)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(40)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(40)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(40)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(41)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(41)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(41)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(41)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(42)=(X=26.821,Y=14.009,Z=57.997)
	GaugeX(42)=(X=1.0000,Y=-0.0001,Z=-0.0002)
	GaugeY(42)=(X=0.0001,Y=1.0000,Z=-0.0001)
	GaugeZ(42)=(X=0.0002,Y=0.0001,Z=1.0000)
	GaugePivot(43)=(X=26.882,Y=14.004,Z=57.988)
	GaugeX(43)=(X=1.0000,Y=-0.0005,Z=-0.0007)
	GaugeY(43)=(X=0.0005,Y=1.0000,Z=-0.0001)
	GaugeZ(43)=(X=0.0007,Y=0.0001,Z=1.0000)
	GaugePivot(44)=(X=26.983,Y=13.997,Z=57.973)
	GaugeX(44)=(X=1.0000,Y=-0.0010,Z=-0.0015)
	GaugeY(44)=(X=0.0010,Y=1.0000,Z=-0.0001)
	GaugeZ(44)=(X=0.0015,Y=0.0001,Z=1.0000)
	GaugePivot(45)=(X=27.119,Y=13.987,Z=57.953)
	GaugeX(45)=(X=1.0000,Y=-0.0017,Z=-0.0025)
	GaugeY(45)=(X=0.0017,Y=1.0000,Z=-0.0001)
	GaugeZ(45)=(X=0.0025,Y=0.0001,Z=1.0000)
	GaugePivot(46)=(X=27.278,Y=13.975,Z=57.929)
	GaugeX(46)=(X=1.0000,Y=-0.0025,Z=-0.0038)
	GaugeY(46)=(X=0.0025,Y=1.0000,Z=-0.0002)
	GaugeZ(46)=(X=0.0038,Y=0.0002,Z=1.0000)
	GaugePivot(47)=(X=27.467,Y=13.961,Z=57.901)
	GaugeX(47)=(X=1.0000,Y=-0.0034,Z=-0.0053)
	GaugeY(47)=(X=0.0034,Y=1.0000,Z=-0.0002)
	GaugeZ(47)=(X=0.0053,Y=0.0002,Z=1.0000)
	GaugePivot(48)=(X=27.677,Y=13.946,Z=57.870)
	GaugeX(48)=(X=1.0000,Y=-0.0045,Z=-0.0070)
	GaugeY(48)=(X=0.0045,Y=1.0000,Z=-0.0002)
	GaugeZ(48)=(X=0.0070,Y=0.0002,Z=1.0000)
	GaugePivot(49)=(X=27.915,Y=13.928,Z=57.834)
	GaugeX(49)=(X=0.9999,Y=-0.0057,Z=-0.0089)
	GaugeY(49)=(X=0.0057,Y=1.0000,Z=-0.0003)
	GaugeZ(49)=(X=0.0090,Y=0.0002,Z=1.0000)
	GaugePivot(50)=(X=28.166,Y=13.910,Z=57.797)
	GaugeX(50)=(X=0.9999,Y=-0.0070,Z=-0.0110)
	GaugeY(50)=(X=0.0070,Y=1.0000,Z=-0.0003)
	GaugeZ(50)=(X=0.0110,Y=0.0003,Z=0.9999)
	GaugePivot(51)=(X=28.435,Y=13.890,Z=57.757)
	GaugeX(51)=(X=0.9999,Y=-0.0084,Z=-0.0132)
	GaugeY(51)=(X=0.0084,Y=1.0000,Z=-0.0004)
	GaugeZ(51)=(X=0.0132,Y=0.0003,Z=0.9999)
	GaugePivot(52)=(X=28.711,Y=13.870,Z=57.716)
	GaugeX(52)=(X=0.9998,Y=-0.0098,Z=-0.0154)
	GaugeY(52)=(X=0.0098,Y=1.0000,Z=-0.0005)
	GaugeZ(52)=(X=0.0154,Y=0.0003,Z=0.9999)
	GaugePivot(53)=(X=29.001,Y=13.848,Z=57.673)
	GaugeX(53)=(X=0.9998,Y=-0.0113,Z=-0.0178)
	GaugeY(53)=(X=0.0113,Y=0.9999,Z=-0.0005)
	GaugeZ(53)=(X=0.0178,Y=0.0003,Z=0.9998)
	GaugePivot(54)=(X=29.297,Y=13.826,Z=57.629)
	GaugeX(54)=(X=0.9997,Y=-0.0128,Z=-0.0202)
	GaugeY(54)=(X=0.0128,Y=0.9999,Z=-0.0006)
	GaugeZ(54)=(X=0.0202,Y=0.0004,Z=0.9998)
	GaugePivot(55)=(X=29.598,Y=13.804,Z=57.584)
	GaugeX(55)=(X=0.9996,Y=-0.0144,Z=-0.0227)
	GaugeY(55)=(X=0.0144,Y=0.9999,Z=-0.0007)
	GaugeZ(55)=(X=0.0227,Y=0.0004,Z=0.9997)
	GaugePivot(56)=(X=29.902,Y=13.782,Z=57.539)
	GaugeX(56)=(X=0.9996,Y=-0.0160,Z=-0.0252)
	GaugeY(56)=(X=0.0160,Y=0.9999,Z=-0.0008)
	GaugeZ(56)=(X=0.0252,Y=0.0004,Z=0.9997)
	GaugePivot(57)=(X=30.206,Y=13.759,Z=57.494)
	GaugeX(57)=(X=0.9995,Y=-0.0176,Z=-0.0278)
	GaugeY(57)=(X=0.0175,Y=0.9998,Z=-0.0009)
	GaugeZ(57)=(X=0.0278,Y=0.0004,Z=0.9996)
	GaugePivot(58)=(X=30.504,Y=13.737,Z=57.449)
	GaugeX(58)=(X=0.9994,Y=-0.0191,Z=-0.0302)
	GaugeY(58)=(X=0.0191,Y=0.9998,Z=-0.0010)
	GaugeZ(58)=(X=0.0303,Y=0.0004,Z=0.9995)
	GaugePivot(59)=(X=30.793,Y=13.716,Z=57.406)
	GaugeX(59)=(X=0.9993,Y=-0.0207,Z=-0.0327)
	GaugeY(59)=(X=0.0207,Y=0.9998,Z=-0.0011)
	GaugeZ(59)=(X=0.0327,Y=0.0004,Z=0.9995)
	GaugePivot(60)=(X=31.074,Y=13.695,Z=57.364)
	GaugeX(60)=(X=0.9991,Y=-0.0222,Z=-0.0350)
	GaugeY(60)=(X=0.0221,Y=0.9998,Z=-0.0012)
	GaugeZ(60)=(X=0.0350,Y=0.0004,Z=0.9994)
	GaugePivot(61)=(X=31.337,Y=13.676,Z=57.325)
	GaugeX(61)=(X=0.9990,Y=-0.0236,Z=-0.0372)
	GaugeY(61)=(X=0.0235,Y=0.9997,Z=-0.0013)
	GaugeZ(61)=(X=0.0373,Y=0.0004,Z=0.9993)
	GaugePivot(62)=(X=31.590,Y=13.657,Z=57.288)
	GaugeX(62)=(X=0.9989,Y=-0.0249,Z=-0.0394)
	GaugeY(62)=(X=0.0249,Y=0.9997,Z=-0.0014)
	GaugeZ(62)=(X=0.0394,Y=0.0004,Z=0.9992)
	GaugePivot(63)=(X=31.826,Y=13.640,Z=57.253)
	GaugeX(63)=(X=0.9988,Y=-0.0262,Z=-0.0414)
	GaugeY(63)=(X=0.0261,Y=0.9997,Z=-0.0015)
	GaugeZ(63)=(X=0.0414,Y=0.0004,Z=0.9991)
	GaugePivot(64)=(X=32.038,Y=13.624,Z=57.221)
	GaugeX(64)=(X=0.9987,Y=-0.0273,Z=-0.0432)
	GaugeY(64)=(X=0.0273,Y=0.9996,Z=-0.0015)
	GaugeZ(64)=(X=0.0432,Y=0.0004,Z=0.9991)
	GaugePivot(65)=(X=32.226,Y=13.610,Z=57.193)
	GaugeX(65)=(X=0.9986,Y=-0.0283,Z=-0.0448)
	GaugeY(65)=(X=0.0283,Y=0.9996,Z=-0.0016)
	GaugeZ(65)=(X=0.0448,Y=0.0004,Z=0.9990)
	GaugePivot(66)=(X=32.376,Y=13.599,Z=57.171)
	GaugeX(66)=(X=0.9985,Y=-0.0291,Z=-0.0461)
	GaugeY(66)=(X=0.0291,Y=0.9996,Z=-0.0017)
	GaugeZ(66)=(X=0.0461,Y=0.0003,Z=0.9989)
	GaugePivot(67)=(X=32.506,Y=13.590,Z=57.151)
	GaugeX(67)=(X=0.9984,Y=-0.0298,Z=-0.0472)
	GaugeY(67)=(X=0.0298,Y=0.9996,Z=-0.0017)
	GaugeZ(67)=(X=0.0472,Y=0.0003,Z=0.9989)
	GaugePivot(68)=(X=32.607,Y=13.582,Z=57.136)
	GaugeX(68)=(X=0.9984,Y=-0.0304,Z=-0.0481)
	GaugeY(68)=(X=0.0303,Y=0.9995,Z=-0.0018)
	GaugeZ(68)=(X=0.0481,Y=0.0003,Z=0.9988)
	GaugePivot(69)=(X=32.674,Y=13.577,Z=57.126)
	GaugeX(69)=(X=0.9983,Y=-0.0308,Z=-0.0486)
	GaugeY(69)=(X=0.0307,Y=0.9995,Z=-0.0018)
	GaugeZ(69)=(X=0.0487,Y=0.0003,Z=0.9988)
	GaugePivot(70)=(X=32.697,Y=13.576,Z=57.123)
	GaugeX(70)=(X=0.9983,Y=-0.0309,Z=-0.0488)
	GaugeY(70)=(X=0.0308,Y=0.9995,Z=-0.0018)
	GaugeZ(70)=(X=0.0489,Y=0.0003,Z=0.9988)
	GaugePivot(71)=(X=32.697,Y=13.576,Z=57.123)
	GaugeX(71)=(X=0.9983,Y=-0.0309,Z=-0.0488)
	GaugeY(71)=(X=0.0308,Y=0.9995,Z=-0.0018)
	GaugeZ(71)=(X=0.0489,Y=0.0003,Z=0.9988)
	GaugePivot(72)=(X=71.379,Y=37.023,Z=30.245)
	GaugeX(72)=(X=0.8719,Y=-0.1177,Z=-0.4754)
	GaugeY(72)=(X=-0.0483,Y=0.9453,Z=-0.3226)
	GaugeZ(72)=(X=0.4874,Y=0.3042,Z=0.8185)
	GaugePivot(73)=(X=83.378,Y=35.526,Z=7.664)
	GaugeX(73)=(X=0.8786,Y=-0.1124,Z=-0.4642)
	GaugeY(73)=(X=-0.0445,Y=0.9484,Z=-0.3139)
	GaugeZ(73)=(X=0.4755,Y=0.2964,Z=0.8283)
	GaugePivot(74)=(X=87.068,Y=33.504,Z=-1.949)
	GaugeX(74)=(X=0.8933,Y=-0.1010,Z=-0.4379)
	GaugeY(74)=(X=-0.0367,Y=0.9547,Z=-0.2952)
	GaugeZ(74)=(X=0.4479,Y=0.2798,Z=0.8492)
	GaugePivot(75)=(X=83.997,Y=30.954,Z=-1.084)
	GaugeX(75)=(X=0.9152,Y=-0.0840,Z=-0.3941)
	GaugeY(75)=(X=-0.0255,Y=0.9640,Z=-0.2647)
	GaugeZ(75)=(X=0.4021,Y=0.2523,Z=0.8801)
	GaugePivot(76)=(X=76.147,Y=28.313,Z=7.096)
	GaugeX(76)=(X=0.9392,Y=-0.0647,Z=-0.3372)
	GaugeY(76)=(X=-0.0144,Y=0.9738,Z=-0.2270)
	GaugeZ(76)=(X=0.3431,Y=0.2181,Z=0.9136)
	GaugePivot(77)=(X=65.230,Y=25.327,Z=19.677)
	GaugeX(77)=(X=0.9614,Y=-0.0453,Z=-0.2713)
	GaugeY(77)=(X=-0.0044,Y=0.9837,Z=-0.1800)
	GaugeZ(77)=(X=0.2750,Y=0.1743,Z=0.9455)
	GaugePivot(78)=(X=52.981,Y=22.322,Z=33.517)
	GaugeX(78)=(X=0.9794,Y=-0.0281,Z=-0.1998)
	GaugeY(78)=(X=0.0019,Y=0.9915,Z=-0.1301)
	GaugeZ(78)=(X=0.2018,Y=0.1270,Z=0.9712)
	GaugePivot(79)=(X=41.371,Y=19.324,Z=46.372)
	GaugeX(79)=(X=0.9918,Y=-0.0146,Z=-0.1272)
	GaugeY(79)=(X=0.0040,Y=0.9965,Z=-0.0834)
	GaugeZ(79)=(X=0.1280,Y=0.0822,Z=0.9884)
	GaugePivot(80)=(X=31.970,Y=16.544,Z=55.437)
	GaugeX(80)=(X=0.9983,Y=-0.0053,Z=-0.0577)
	GaugeY(80)=(X=0.0031,Y=0.9993,Z=-0.0379)
	GaugeZ(80)=(X=0.0579,Y=0.0376,Z=0.9976)
	GaugePivot(81)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(81)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(81)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(81)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(82)=(X=26.792,Y=14.011,Z=58.001)
	GaugeX(82)=(X=1.0000,Y=-0.0000,Z=0.0001)
	GaugeY(82)=(X=0.0000,Y=1.0000,Z=-0.0001)
	GaugeZ(82)=(X=-0.0001,Y=0.0001,Z=1.0000)
	GaugePivot(83)=(X=26.076,Y=7.961,Z=56.623)
	GaugeX(83)=(X=0.9878,Y=0.1558,Z=0.0029)
	GaugeY(83)=(X=-0.1559,Y=0.9875,Z=0.0233)
	GaugeZ(83)=(X=0.0007,Y=-0.0235,Z=0.9997)
	GaugePivot(84)=(X=26.480,Y=3.396,Z=53.955)
	GaugeX(84)=(X=0.9499,Y=0.3123,Z=0.0100)
	GaugeY(84)=(X=-0.3124,Y=0.9488,Z=0.0459)
	GaugeZ(84)=(X=0.0048,Y=-0.0467,Z=0.9989)
	GaugePivot(85)=(X=28.017,Y=0.429,Z=49.500)
	GaugeX(85)=(X=0.8857,Y=0.4637,Z=0.0221)
	GaugeY(85)=(X=-0.4640,Y=0.8832,Z=0.0675)
	GaugeZ(85)=(X=0.0118,Y=-0.0701,Z=0.9975)
	GaugePivot(86)=(X=30.897,Y=-0.371,Z=43.610)
	GaugeX(86)=(X=0.7967,Y=0.6033,Z=0.0366)
	GaugeY(86)=(X=-0.6040,Y=0.7924,Z=0.0859)
	GaugeZ(86)=(X=0.0228,Y=-0.0906,Z=0.9956)
	GaugePivot(87)=(X=35.052,Y=1.155,Z=36.650)
	GaugeX(87)=(X=0.6860,Y=0.7256,Z=0.0547)
	GaugeY(87)=(X=-0.7267,Y=0.6794,Z=0.1014)
	GaugeZ(87)=(X=0.0364,Y=-0.1093,Z=0.9933)
	GaugePivot(88)=(X=40.415,Y=5.466,Z=28.456)
	GaugeX(88)=(X=0.5581,Y=0.8264,Z=0.0745)
	GaugeY(88)=(X=-0.8280,Y=0.5487,Z=0.1155)
	GaugeZ(88)=(X=0.0545,Y=-0.1261,Z=0.9905)
	GaugePivot(89)=(X=46.913,Y=12.530,Z=18.656)
	GaugeX(89)=(X=0.4177,Y=0.9034,Z=0.0966)
	GaugeY(89)=(X=-0.9055,Y=0.4052,Z=0.1258)
	GaugeZ(89)=(X=0.0745,Y=-0.1400,Z=0.9873)
	GaugePivot(90)=(X=54.206,Y=22.817,Z=7.103)
	GaugeX(90)=(X=0.2690,Y=0.9558,Z=0.1189)
	GaugeY(90)=(X=-0.9583,Y=0.2532,Z=0.1323)
	GaugeZ(90)=(X=0.0964,Y=-0.1496,Z=0.9840)
	ProjectileClass=Class'UTBioGel'
	AltProjectileClass=Class'UTBioGlob'
	FireSound=Sound'BioGelShot'
	AltFireSound=Sound'BioGelShot'
	CockingSound=Sound'BioGelLoad'
	SelectSound=Sound'BioGelSelect'
	FlashSkin=None
	PickupAmmoCount=0   // takes over the Dispersion Pistol's recharging ammo
	ItemName="GES Bio Rifle"
	InventoryGroup=1     // key 1, first (where the shotgun was)
	GroupOffset=1
}
