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

var StaticMesh ViewFrames[91];     // UT's BRifle2 animation, one static mesh per frame
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
}

// the pistol's charge state replaces Tick while charging - keep animating
simulated state AltCharging
{
	simulated event Tick(float DeltaTime)
	{
		Super.Tick(DeltaTime);
		TickBioAnim(DeltaTime);
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
