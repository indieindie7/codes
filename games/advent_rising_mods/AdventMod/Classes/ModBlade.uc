//=============================================================================
// ModBlade - the energy blade: a glowing sword the player picks up and swings with the
// melee key (ModMelee has the rules). One class for both the pickup lying in the level
// (bLying: it turns and bobs) and the blade carried on the player. The mesh and textures
// are our own (tools/make_blade.py). Unlit, so the glow texture is its light, and it
// lights what is around it.
//=============================================================================
class ModBlade extends Actor;

#exec NEW StaticMesh FILE=Gibs\blade.ase NAME=Blade GROUP=Gibs
#exec TEXTURE IMPORT NAME=BladeGlow FILE=Textures\blade_glow.tga GROUP=Blade MIPS=1
#exec TEXTURE IMPORT NAME=BladeHilt FILE=Textures\blade_hilt.tga GROUP=Blade MIPS=1

var bool bLying;
var float Age;
var vector Rest;           // where it lies (it bobs over this)

function Lie(vector Spot)
{
	bLying = true;
	Rest = Spot;
	SetLocation(Spot);
}

event Tick(float DeltaTime)
{
	local rotator R;
	local vector To;

	if (!bLying)
		return;
	Age += DeltaTime;
	R.Yaw = int(Age * 14000) & 65535;
	R.Pitch = 9000;                    // tip up, at a slant
	SetRotation(R);
	To = Rest;
	To.Z += 4 * Sin(Age * 2.5);
	SetLocation(To);
}

defaultproperties
{
     DrawType=DT_StaticMesh
     StaticMesh=StaticMesh'AdventMod.Gibs.Blade'
     Skins(0)=Texture'AdventMod.Blade.BladeHilt'
     Skins(1)=Texture'AdventMod.Blade.BladeGlow'
     bUnlit=True
     AmbientGlow=255
     LightType=LT_Steady
     LightBrightness=160.000000
     LightRadius=7.000000
     LightHue=140
     LightSaturation=90
     bDynamicLight=True
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bHardAttach=True
     bShadowCast=False
     SoundRadius=40.000000
     SoundVolume=50
     RemoteRole=ROLE_None
}
