//=============================================================================
// WeaponInvUTRipper - Unreal II's Assault Rifle wearing Unreal Tournament's
// Ripper: the Assault Rifle's own bullets on primary fire, and UT's
// ricocheting razor disc (UTRazorDisc) on alt fire, using Assault Rifle ammo.
//
// Like the Flak Cannon, UT's vertex-animated model is drawn from static meshes
// (one per animation frame, StaticMeshes\U2UTFlakSM.usx) because Unreal II
// never textures vertex meshes; PlayAnimEx plays UT's sequences by swapping
// frames. The five UT skins are packed into one atlas.
//=============================================================================
class WeaponInvUTRipper extends weaponInvAssaultRifle;

#exec TEXTURE IMPORT NAME=RipperAtlas FILE=Textures\RipperAtlas.tga GROUP=Skins LODSET=2
#exec AUDIO IMPORT FILE=Sounds\RipperSelect.wav NAME=RipperSelect GROUP=Ripper

var StaticMesh ViewFrames[75];     // UT's Razor2 animation, one static mesh per frame
var int AnimFirst, AnimCount;      // playing sequence (frames)
var float AnimFPS, AnimTime;
var bool bAnimLoop;
var bool bRaiseAfterDown;          // reload: lower the gun, then bring it back up

// the frames live in StaticMeshes/U2UTFlakSM.usx and are loaded by name the
// first time they're shown - nothing references that package directly, so
// levels without these guns never load it
simulated function StaticMesh Frame(int i)
{
	local string N;
	if (ViewFrames[i] == None)
	{
		N = string(i);
		if (i < 10)       N = "00"$N;
		else if (i < 100) N = "0"$N;
		ViewFrames[i] = StaticMesh(DynamicLoadObject("U2UTFlakSM.Ripper.RipV"$N, class'StaticMesh'));
	}
	return ViewFrames[i];
}

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = Frame(47);
}


// UT's Razor2 sequences: start frame, frame count, frames per second, loops
simulated function bool RipSeq(name Seq, out int First, out int Count, out float FPS, out byte bLoop)
{
	FPS = 30;
	bLoop = 0;
	switch (Seq)
	{
	case 'SelectAnim': First = 0;  Count = 30; FPS = 40; return true;
	case 'Fire':       First = 32; Count = 15; return true;   // launching a blade
	case 'Load':       First = 42; Count = 5;  return true;
	case 'Idle':       First = 47; Count = 19; bLoop = 1; return true;
	case 'DownAnim':   First = 67; Count = 6;  return true;
	}
	return false;
}

simulated function PlayRip(name Seq, float Rate)
{
	local byte bLoop;
	if (!RipSeq(Seq, AnimFirst, AnimCount, AnimFPS, bLoop))
		return;
	AnimFPS *= Rate;
	AnimTime = 0;
	bAnimLoop = bLoop != 0;
	StaticMesh = Frame(AnimFirst);
}

// step the frame animation; one-shot sequences settle into the idle loop
simulated function TickRipAnim(float DeltaTime)
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
		else if (AnimFirst == 67)      // lowered
		{
			f = AnimCount - 1;
			if (bRaiseAfterDown)
			{
				bRaiseAfterDown = false;
				PlayRip('SelectAnim', 1.0);
				return;
			}
		}
		else
		{
			PlayRip('Idle', 1.0);
			return;
		}
	}
	StaticMesh = Frame(AnimFirst + f);
}

// Unreal II's weapon code asks for Golem animations; map them onto UT's
simulated function PlayAnimEx(name Sequence)
{
	LastTriggeredAnim = Sequence;
	switch (Sequence)
	{
	case 'Fire':                 // the rifle's bullets: the model stays on its idle
	case 'FireEnd':
	case 'FireLastDown':
	case 'FireLastReload':
		return;
	case 'AltFire':
	case 'AltFireLastDown':
	case 'AltFireLastReload':
		PlayRip('Fire', 1.4);
		return;
	case 'Reload':
	case 'ReloadUnloaded':
		bRaiseAfterDown = true;
		PlayRip('DownAnim', 0.5);
		return;
	}
	PlayRip(Sequence, 1.0);
}

simulated event Tick(float DeltaTime)
{
	Super.Tick(DeltaTime);
	TickRipAnim(DeltaTime);
	LinkAmmo();
}

// the Ripper takes over the rifle's ammo (PickupAmmoCount=0, so the engine
// never links any): hook it up to the Assault Rifle rounds being carried. With
// none carried (the Ripper given on its own) it brings a rifle's worth itself,
// else it showed 000 and reloading hit a None
simulated function LinkAmmo()
{
	if (AmmoType != None && !AmmoType.bDeleteMe || Pawn(Owner) == None)
		return;
	AmmoType = Ammunition(Pawn(Owner).FindInventoryType(AmmoName));
	if (AmmoType == None && Role == ROLE_Authority)
	{
		PickupAmmoCount = class'weaponInvAssaultRifle'.default.PickupAmmoCount;
		GiveAmmo(Pawn(Owner));
		PickupAmmoCount = 0;
	}
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

simulated function Reload()
{
	LinkAmmo();
	if (AmmoType != None)
		Super.Reload();
}

// a disc costs 3 rounds (the rifle's own alt fire cost 5)
simulated function int GetAltFireAmmoUsed() { return 3; }

defaultproperties
{
	DrawType=DT_StaticMesh
	bUnlit=True
	Skins(0)=Texture'RipperAtlas'
	// UT draws the Ripper at PlayerViewOffset (3.0,-1.6,-2.4), PlayerViewScale 1.4;
	// Unreal II's near clip needs it 10x bigger and further away (same look),
	// and the meshes are exported 100x larger.
	DrawScale=0.140000
	PlayerViewOffset=(X=30.000000,Y=16.000000,Z=-24.000000)
	FirstPersonOffset=(X=0.000000,Y=0.000000,Z=0.000000)
	FireOffset=(X=30.000000,Y=8.000000,Z=-8.000000)
	AltProjectileClass=Class'UTRazorDisc'
	bAltInstantHit=False
	AltFireSound=Sound'U2UTFlak.Ripper.StartBlade'
	SelectSound=Sound'RipperSelect'
	AltFireTime=0.700000
	FlashSkin=None
	ItemName="Ripper"
	PickupAmmoCount=0   // takes over the Assault Rifle's ammo; no bonus pack
}
