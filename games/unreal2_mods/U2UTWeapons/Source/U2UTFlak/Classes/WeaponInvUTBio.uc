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
	PilotOffset=(X=30.000000,Y=10.000000,Z=-9.000000)
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
