//=============================================================================
// WeaponInvUTFlak - Unreal Tournament's Flak Cannon in Unreal II.
//
// A shotgun and grenade launcher in one, replacing Unreal II's launcher:
//   primary  - UT's cluster of 8 bouncing flak chunks; uses shotgun shells
//   alt fire - fires the selected Unreal II grenade (contact), using that
//              grenade type's ammo: frag, toxic, incendiary, smoke,
//              concussion or EMP
//   NextGrenadeType (bind to a key, e.g. MiddleMouse=NextGrenadeType)
//            - cycles to the next grenade type you have ammo for
// Built on Unreal II's shotgun for its clip/HUD handling, with UT99's
// first-person model, sounds and chunks.
//
// UT's model is a vertex-animated mesh, but Unreal II never textures vertex
// meshes and animates weapons through Legend's Golem system. So every UT
// animation frame was converted into a static mesh (StaticMeshes/U2UTFlakSM.usx,
// built in UnrealEd from ASE files by make_import_script.py), the four skins
// were packed into one atlas, and PlayAnimEx plays UT's sequences by swapping
// frames. Weapon timing in Unreal II runs on FireTime/SelectTime/... timers,
// not animation events, so nothing else changes.
//=============================================================================
class WeaponInvUTFlak extends weaponInvShotgun
	config(User);

// first-person model: UT's flakm, sequences renamed to Unreal II's anim names
// Unreal II's renderer never textures vertex meshes, so the first-person model
// is drawn from static meshes (one per UT animation frame, built by UnrealEd from
// ASE files - see make_import_script.py) with the four UT skins in one atlas.
#exec TEXTURE IMPORT NAME=FlakAtlas FILE=Textures\FlakAtlas.tga GROUP=Skins LODSET=2
#exec MESH IMPORT MESH=flakm ANIVFILE=Models\flakm_a.3d DATAFILE=Models\flakm_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=flakm X=40 Y=0 Z=0 YAW=64 ROLL=124 PITCH=128
#exec MESH SEQUENCE MESH=flakm SEQ=All        STARTFRAME=0  NUMFRAMES=96
#exec MESH SEQUENCE MESH=flakm SEQ=SelectAnim STARTFRAME=0  NUMFRAMES=30 RATE=48
#exec MESH SEQUENCE MESH=flakm SEQ=Loading    STARTFRAME=30 NUMFRAMES=15
#exec MESH SEQUENCE MESH=flakm SEQ=Reload     STARTFRAME=30 NUMFRAMES=15
#exec MESH SEQUENCE MESH=flakm SEQ=Idle       STARTFRAME=45 NUMFRAMES=1
#exec MESH SEQUENCE MESH=flakm SEQ=Still      STARTFRAME=45 NUMFRAMES=1
#exec MESH SEQUENCE MESH=flakm SEQ=Fire       STARTFRAME=46 NUMFRAMES=10
#exec MESH SEQUENCE MESH=flakm SEQ=AltFire    STARTFRAME=57 NUMFRAMES=10 RATE=24
#exec MESH SEQUENCE MESH=flakm SEQ=Sway       STARTFRAME=80 NUMFRAMES=2
#exec MESH SEQUENCE MESH=flakm SEQ=DownAnim   STARTFRAME=82 NUMFRAMES=10
#exec TEXTURE IMPORT NAME=Flak_t1 FILE=Textures\Flak_t1.tga GROUP=Skins LODSET=2
#exec TEXTURE IMPORT NAME=Flak_t2 FILE=Textures\Flak_t2.tga GROUP=Skins LODSET=2
#exec TEXTURE IMPORT NAME=Flak_t3 FILE=Textures\Flak_t3.tga GROUP=Skins LODSET=2
#exec TEXTURE IMPORT NAME=Flak_t4 FILE=Textures\Flak_t4.tga GROUP=Skins LODSET=2
#exec MESHMAP SCALE MESHMAP=flakm X=0.007 Y=0.003 Z=0.014
#exec MESHMAP SETTEXTURE MESHMAP=flakm NUM=0 TEXTURE=Flak_t1
#exec MESHMAP SETTEXTURE MESHMAP=flakm NUM=1 TEXTURE=Flak_t2
#exec MESHMAP SETTEXTURE MESHMAP=flakm NUM=2 TEXTURE=Flak_t3
#exec MESHMAP SETTEXTURE MESHMAP=flakm NUM=3 TEXTURE=Flak_t4
#exec MESHMAP SETTEXTURE MESHMAP=flakm NUM=4 TEXTURE=Flak_t1

// third-person model (in the character's hand)
#exec MESH IMPORT MESH=FlakHand ANIVFILE=Models\FlakHand_a.3d DATAFILE=Models\FlakHand_d.3d X=0 Y=0 Z=0
#exec MESH ORIGIN MESH=FlakHand X=20 Y=-230 Z=-55 YAW=-64 ROLL=0 PITCH=0
#exec MESH SEQUENCE MESH=FlakHand SEQ=All   STARTFRAME=0 NUMFRAMES=10
#exec MESH SEQUENCE MESH=FlakHand SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH=FlakHand SEQ=Fire  STARTFRAME=1 NUMFRAMES=9 RATE=40.0
#exec TEXTURE IMPORT NAME=Flak_t FILE=Textures\Flak_t.tga GROUP=Skins LODSET=2
#exec MESHMAP SCALE MESHMAP=FlakHand X=0.04 Y=0.04 Z=0.08
#exec MESHMAP SETTEXTURE MESHMAP=FlakHand NUM=1 TEXTURE=Flak_t

#exec AUDIO IMPORT FILE=Sounds\shot1.wav    NAME=FlakShot     GROUP=Flak
#exec AUDIO IMPORT FILE=Sounds\Explode1.wav NAME=FlakAltShot  GROUP=Flak
#exec AUDIO IMPORT FILE=Sounds\load1.wav    NAME=FlakLoad     GROUP=Flak
#exec AUDIO IMPORT FILE=Sounds\pdown.wav    NAME=FlakSelect   GROUP=Flak
#exec AUDIO IMPORT FILE=Sounds\Hidraul2.wav NAME=FlakHydraulic GROUP=Flak

var float LoadingAt;   // when to start the post-shot "Loading" (pump) animation
var StaticMesh ViewFrames[100];        // UT's flakm animation, one static mesh per frame
var int AnimFirst, AnimCount;          // playing sequence (frames)
var float AnimFPS, AnimTime;
var bool bAnimLoop;

var() config bool bDebugLog;
var float NextDebugLog;
var bool bTutorialAltFireEvent;   // replaced the tutorial's launcher: report alt-fire like it did
var int iGrenade;                 // selected grenade type (ammoInvGrenade.GrenadeIndex)
var Ammunition ShellAmmo;         // primary ammo; AmmoType is switched to a grenade only while alt-firing
var() sound ChangeGrenadeSound;

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
		ViewFrames[i] = StaticMesh(DynamicLoadObject("U2UTFlakSM.View.FlakV"$N, class'StaticMesh'));
	}
	return ViewFrames[i];
}

simulated event PostBeginPlay()
{
	Super.PostBeginPlay();
	StaticMesh = Frame(45);
}


// UT's flakm sequences: start frame, frame count, frames per second
simulated function bool FlakSeq(name Seq, out int First, out int Count, out float FPS)
{
	FPS = 30;
	switch (Seq)
	{
	case 'SelectAnim': First = 0;  Count = 30; FPS = 48; return true;
	case 'Loading':
	case 'Reload':     First = 30; Count = 15; return true;
	case 'Idle':
	case 'Still':      First = 45; Count = 1;  return true;
	case 'Fire':       First = 46; Count = 10; return true;
	case 'AltFire':    First = 57; Count = 10; FPS = 24; return true;
	case 'Sway':       First = 80; Count = 2;  return true;
	case 'DownAnim':   First = 82; Count = 10; return true;
	}
	return false;
}

simulated function PlayFlak(name Seq, float Rate)
{
	if (!FlakSeq(Seq, AnimFirst, AnimCount, AnimFPS))
		return;
	AnimFPS *= Rate;
	AnimTime = 0;
	StaticMesh = Frame(AnimFirst);
}

// step the frame animation; ends on its last frame, then settles to idle
simulated function TickFlakAnim(float DeltaTime)
{
	local int f;
	if (AnimCount <= 0)
		return;
	AnimTime += DeltaTime;
	f = int(AnimTime * AnimFPS);
	if (f >= AnimCount)
	{
		f = AnimCount - 1;
		if (AnimFirst != 82 && AnimFirst != 45)   // held down stays down
		{
			AnimFirst = 45; AnimCount = 1; AnimTime = 0; f = 0;
		}
	}
	StaticMesh = Frame(AnimFirst + f);
}
// Unreal II animates weapons through Golem; this model is a classic vertex mesh
simulated function PlayAnimEx(name Sequence)
{
	LastTriggeredAnim = Sequence;
	switch (Sequence)
	{
	case 'FireLastDown':
	case 'FireLastReload':
		Sequence = 'Fire';
		break;
	case 'AltFireLastDown':
	case 'AltFireLastReload':
		Sequence = 'AltFire';
		break;
	case 'ReloadUnloaded':
		Sequence = 'Reload';
		break;
	}
	switch (Sequence)
	{
	case 'Fire':
		PlayFlak('Fire', 0.9);
		LoadingAt = Level.TimeSeconds + (10.0 / 30.0) / 0.9;   // then pump, like UT
		break;
	case 'AltFire':
		PlayFlak('AltFire', 1.3);
		LoadingAt = Level.TimeSeconds + (10.0 / 24.0) / 1.3;
		break;
	default:
		PlayFlak(Sequence, 1.0);
		LoadingAt = 0;
	}
}

simulated event Tick(float DeltaTime)
{
	Super.Tick(DeltaTime);
	TickFlakAnim(DeltaTime);
	if (LoadingAt > 0 && Level.TimeSeconds >= LoadingAt)
	{
		LoadingAt = 0;
		PlayFlak('Loading', 0.7);
		if (Owner != None)
			Owner.PlaySound(CockingSound, SLOT_None, 0.5);
	}
	if (bDebugLog && Level.TimeSeconds >= NextDebugLog && Pawn(Owner) != None)
	{
		NextDebugLog = Level.TimeSeconds + 1.0;
		Log("U2UTFlak: debug state="$GetStateName()$" loc-eye="$((Location - Owner.Location - vect(0,0,1) * Pawn(Owner).EyeHeight) << Pawn(Owner).GetViewRotation())
			$" rot="$Rotation$" hidden="$bHidden$" drawtype="$DrawType$" mesh="$Mesh$" scale="$DrawScale$" smesh="$StaticMesh$" animfirst="$AnimFirst$" count="$AnimCount$" t="$AnimTime$" fps="$AnimFPS
			$" ammo="$AmmoType$" clip="$GetClipSize()$" pressing="$Pawn(Owner).PressingFire());
	}
}

// --- ammo: shells for the primary, grenade ammo for the alt fire ----------

simulated function Ammunition GetShells()
{
	if (ShellAmmo == None || ShellAmmo.bDeleteMe || ShellAmmo.Owner != Owner)
	{
		ShellAmmo = None;
		if (Pawn(Owner) != None)
			ShellAmmo = Ammunition(Pawn(Owner).FindInventoryType(AmmoName));
	}
	return ShellAmmo;
}

simulated function ammoInvGrenade GetGrenade(int Index)
{
	local Inventory Inv;
	if (Owner == None)
		return None;
	for (Inv = Owner.Inventory; Inv != None; Inv = Inv.Inventory)
		if (ammoInvGrenade(Inv) != None && ammoInvGrenade(Inv).GrenadeIndex == Index && !Inv.bDeleteMe)
			return ammoInvGrenade(Inv);
	return None;
}

simulated function bool HasGrenades(int Index)
{
	local ammoInvGrenade G;
	G = GetGrenade(Index);
	return G != None && G.AmmoAmount > 0;
}

// selected type if it has ammo, else the next one that does (-1: none at all)
simulated function int PickGrenade(int Start)
{
	local int i;
	for (i = 0; i < 6; i++)
		if (HasGrenades((Start + i) % 6))
			return (Start + i) % 6;
	return -1;
}

simulated function RestoreShells()
{
	if (GetShells() != None)
		AmmoType = ShellAmmo;
}

simulated function bool HasAmmo()
{
	return (GetShells() != None && ShellAmmo.AmmoAmount > 0) || PickGrenade(0) >= 0;
}

simulated function bool HasAnyAmmo()
{
	return HasAmmo();
}

// the grenade ran out: go back to shells instead of switching weapons
simulated function ChangeAmmoType()
{
	RestoreShells();
}

function ShowGrenade()
{
	local ammoInvGrenade G;
	G = GetGrenade(iGrenade);
	if (Instigator != None && Instigator.IsRealPlayer())
	{
		if (G != None && G.AmmoAmount > 0)
			class'UIConsole'.static.BroadcastStatusMessage(Self, G.ItemName$" ("$G.AmmoAmount$")");
		else
			class'UIConsole'.static.BroadcastStatusMessage(Self, "No grenades");
	}
}

// middle mouse (bound in User.ini): next grenade type you have ammo for
exec function NextGrenadeType()
{
	local int i;
	i = PickGrenade(iGrenade + 1);
	if (i >= 0)
	{
		iGrenade = i;
		if (Owner != None)
			Owner.PlaySound(ChangeGrenadeSound, SLOT_None, 0.8);
	}
	ShowGrenade();
}

simulated function Fire()
{
	RestoreShells();
	if (bDebugLog)
		Log("U2UTFlak: Fire() state="$GetStateName()$" pressing="$Pawn(Owner).PressingFire()$" hasammo="$HasAmmo());
	if (ShellAmmo == None || ShellAmmo.AmmoAmount <= 0)
		return;   // out of shells: grenades are still on the right button
	Super.Fire();
}

// alt fire: a contact grenade of the selected type, paid for straight from
// that grenade type's ammo. The weapon's AmmoType stays on the shells the whole
// time, so the HUD always shows shells and a grenade never triggers a shell
// reload (or looks like it refilled them).
simulated function AltFire()
{
	local int i;
	local ammoInvGrenade G;

	if (!Pawn(Owner).PressingAltFire() || bDisableFiring)
		return;
	RestoreShells();
	i = PickGrenade(iGrenade);
	if (i < 0)
	{
		ShowGrenade();
		return;
	}
	if (i != iGrenade)
	{
		iGrenade = i;
		ShowGrenade();   // the selected type ran out: say what's loaded now
	}
	G = GetGrenade(iGrenade);
	AltProjectileClass = G.ProjectileClass;
	bFiring = false;
	bAltFiring = true;
	if (!PreSetAimingParameters(true, false, TraceSpreadAltFire, AltProjectileClass, bAltWarnTarget, bRecommendAltSplashDamage))
		return;
	if (Role == ROLE_Authority)
	{
		G.Reload();          // grenades load straight from the pack
		G.UseAmmo(1);
		AuthorityAltFire();  // fires AltProjectileClass; uses no shells (GetAltFireAmmoUsed = 0)
	}
	EverywhereAltFire();
	if (bDebugLog)
		Log("U2UTFlak: AltFire grenade="$G$" left="$G.AmmoAmount$" shells="$ShellAmmo.AmmoAmount);
	if (bTutorialAltFireEvent)
		TriggerEvent('GLAltFire', Self, Pawn(Owner));
}

// grenades are paid for in AltFire, not from the shells
simulated function int GetAltFireAmmoUsed() { return 0; }

simulated state AltFiring
{
	simulated event EndState()
	{
		Super.EndState();
		RestoreShells();
	}
}

// primary fire: UT's cluster of 8 chunks
function Projectile ProjectileFire(class<Projectile> ProjClass)
{
	local vector Start, X, Y, Z;
	local Projectile First;

	if (ProjClass != ProjectileClass)
		return Super.ProjectileFire(ProjClass);

	Pawn(Owner).MakeNoise(Pawn(Owner).SoundDampening);
	AdjustedAim = Pawn(Owner).GetAimRotation();
	GetAxes(AdjustedAim, X, Y, Z);
	Start = ProjectileFireStartLocation;
	First = Spawn(class'UTFlakChunk1', Self,, Start, AdjustedAim);
	Spawn(class'UTFlakChunk2', Self,, Start - Z, AdjustedAim);
	Spawn(class'UTFlakChunk3', Self,, Start + 2 * Y + Z, AdjustedAim);
	Spawn(class'UTFlakChunk4', Self,, Start - Y, AdjustedAim);
	Spawn(class'UTFlakChunk1', Self,, Start + 2 * Y - Z, AdjustedAim);
	Spawn(class'UTFlakChunk2', Self,, Start, AdjustedAim);
	Spawn(class'UTFlakChunk3', Self,, Start + Y - Z, AdjustedAim);
	Spawn(class'UTFlakChunk4', Self,, Start + 2 * Y + Z, AdjustedAim);
	if (bDebugLog)
		Log("U2UTFlak: flak burst from "$Start$" first="$First$" aim="$AdjustedAim);
	return First;
}

defaultproperties
{
	Mesh=VertMesh'flakm'
	DrawType=DT_StaticMesh
	bUnlit=True
	ThirdPersonMesh=VertMesh'FlakHand'
	ProjectileClass=Class'UTFlakChunk1'
	AltProjectileClass=Class'U2Weapons.projectileGrenadeFragment'
	bInstantHit=False
	bAltInstantHit=False
	FireSound=Sound'FlakShot'
	AltFireSound=Sound'U2WeaponsA.GrenadeLauncher.GL_Fire'
	ChangeGrenadeSound=Sound'U2WeaponsA.GrenadeLauncher.GL_Reload'
	CockingSound=Sound'FlakLoad'
	SelectSound=Sound'FlakSelect'
	FireTime=0.900000
	AltFireTime=1.100000
	FlashSkin=None
	ItemName="Flak Cannon"
	AmmoName=Class'U2Weapons.ammoInvShotgun'
	PickupAmmoCount=16
	ReloadTime=1.500000
	InventoryGroup=3
	GroupOffset=3
	FirstPersonOffset=(X=0.000000,Y=0.000000,Z=0.000000)
	FireOffset=(X=30.000000,Y=8.000000,Z=-10.000000)
	bDebugLog=False
	// UT draws this ~5-unit model right at the eye (PlayerViewOffset 1.5,-1,-1.65,
	// PlayerViewScale 1.2); Unreal II's near clip plane cuts that off, so it's
	// drawn 10x bigger and 10x further away, which looks exactly the same.
	DrawScale=0.120000   // 12 (UT 1.2 x 10), meshes are exported 100x larger
	PlayerViewOffset=(X=15.000000,Y=10.000000,Z=-16.500000)
	Skins(0)=Texture'FlakAtlas'
}
