//=============================================================================
// ModBloodDrop - one falling drop of blood (ModGore's drips): a small sprite on
// fake physics like the casings and gibs (gravity, a trace each tick for where it
// lands, no collision with anything, pawns included). ModGore keeps a pool of
// them (MaxDrops) and reuses them: a drop that lands (or falls too long) is only
// hidden until ModGore throws it again, so dripping makes no garbage.
// On landing it tells ModGore (DropLanded): a tiny splat, or blood into the live
// pool under it. The sprite is our own art (tools/make_blood_drops.py): a round
// drop, swapped for a thin streak while it falls fast.
//=============================================================================
class ModBloodDrop extends Actor;

#exec TEXTURE IMPORT NAME=BloodDrop0 FILE=Textures\blood_drop0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=BloodDrop1 FILE=Textures\blood_drop1.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienDrop0 FILE=Textures\alien_drop0.tga GROUP=Blood MIPS=1 ALPHA=1
#exec TEXTURE IMPORT NAME=AlienDrop1 FILE=Textures\alien_drop1.tga GROUP=Blood MIPS=1 ALPHA=1

var ModGore Gore;
var vector Vel;
var float Gravity;
var int Kind;              // its blood (ModGore.BloodKind: 1 red, 2 purple)
var float MarkSize;        // the splat it leaves (a DrawScale for ModGore.Mark)
var float Age;
var bool bFlying;          // false: idle in ModGore's pool, hidden
var bool bFast;            // drawn as the streak
var Material DropTex[2], AlienDropTex[2];

// thrown from Spot: V its starting velocity, G the gravity, Size the sprite's scale
function Fall(vector Spot, vector V, float G, int K, float Size, float SplatSize)
{
	SetLocation(Spot);
	Vel = V;
	Gravity = G;
	Kind = K;
	MarkSize = SplatSize;
	Age = 0;
	bFast = false;
	Texture = Pick(false);
	SetDrawScale(Size);
	bHidden = false;
	bFlying = true;
}

function Material Pick(bool bStreak)
{
	if (Kind == 2)
		return AlienDropTex[int(bStreak)];
	return DropTex[int(bStreak)];
}

// back into the pool
function Rest()
{
	bFlying = false;
	bHidden = true;
	Vel = vect(0,0,0);
}

event Tick(float DeltaTime)
{
	local vector From, To, HitL, HitN;

	if (!bFlying)
		return;
	DeltaTime = FMin(DeltaTime, 0.05);
	Age += DeltaTime;
	// fell out of the world, or into something the traces miss: give it back
	if (Age > 4.0)
	{
		Rest();
		return;
	}
	From = Location;
	Vel.Z = FMax(Vel.Z + Gravity * DeltaTime, -1800);
	To = From + Vel * DeltaTime;
	if (Trace(HitL, HitN, To, From, false) != None)
	{
		if (Gore != None)
			Gore.DropLanded(self, HitL, HitN);
		Rest();
		return;
	}
	SetLocation(To);
	// fast: the streak; the swap only when it changes (a texture set each tick costs nothing, but stays tidy)
	if (bFast != (Vel.Z < -380))
	{
		bFast = !bFast;
		Texture = Pick(bFast);
	}
}

defaultproperties
{
     DropTex(0)=Texture'AdventMod.Blood.BloodDrop0'
     DropTex(1)=Texture'AdventMod.Blood.BloodDrop1'
     AlienDropTex(0)=Texture'AdventMod.Blood.AlienDrop0'
     AlienDropTex(1)=Texture'AdventMod.Blood.AlienDrop1'
     Texture=Texture'AdventMod.Blood.BloodDrop0'
     DrawType=DT_Sprite
     Style=STY_Alpha
     bUnlit=False
     bHidden=True
     Physics=PHYS_None
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bShadowCast=False
     bAcceptsProjectors=False
     RemoteRole=ROLE_None
     DrawScale=0.150000
}
