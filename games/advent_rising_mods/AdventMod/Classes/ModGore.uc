//=============================================================================
// ModGore - procedural blood for AdventMod: one per level (ModMutator spawns it),
// fed every hit by ModGoreRules (GameRules.NetDamage, which Pawn.TakeDamage runs
// for every character through GameInfo.ReduceDamage).
//   - a spray on the wall or floor behind the victim, along the shot, if one is
//     within SprayReach: the bigger the hit, the bigger the spray;
//   - drips on the floor under the hit, sometimes;
//   - a pool spreading under each body, a moment after it falls.
// The marks are ModBloodDecal projectors with procedural textures (Textures\
// make_blood.py, imported by ModBloodTextures). At most MaxDecals at once: the
// oldest goes first. Only damage types that cause blood (DamageType.bCausesBlood)
// and only characters (not vehicles or turrets) bleed, in the colour the game's own
// hit particles give them (its surface table: humans red, Seekers purple, holograms
// and ShockTroopers nothing).
// When the game takes a body away (it fades the oldest when someone else dies, and
// recycles the pawn for its spawners), what's left stays on the floor: a flat mark of
// chunks and bone in the body's blood colour, clutter that costs nothing.
// A body killed by an explosion, or by a hit far past what it had left, comes apart:
// its parts (ModGibParts, cut from the game's own meshes) fly as ModGib, the body is
// hidden until the game recycles the pawn.
//=============================================================================
class ModGore extends Info
	config(AdventMod);

var config bool bBlood;            // the Gameplay page's Blood switch
var config int MaxDecals;
var config float SprayReach;       // how far behind a victim a wall still catches the spray
var config float DecalScale;       // all marks' size
var config bool bImpacts;          // scorch marks where shots hit walls and floors
var config int MaxHoles;
var config bool bCasings;          // the game's shell particles become casings that land and stay
var config int MaxClutter;
var config bool bCorpseShots;      // corpses bleed and twitch when shot
var config float CorpseKick;       // the push a shot gives a ragdoll
var config bool bHoundRagdolls;    // off: hounds crash the game going limp (levels 03 b and c), cause not found yet. (A config array of skeleton names came up empty in game, and the hounds went limp.)
var KarmaParamsSkel CorpseParams;  // ragdoll settings for corpses the level gave none (a subobject below, so saves can refer to it)
var array<Pawn> Corpses;
var float CorpseScan;

var config bool bRemains;          // a body the game takes away leaves remains on the floor
var config int MaxRemains;
var array<vector> CorpseLoc;       // where each corpse lies, and its blood (BloodKind),
var array<int> CorpseKind;         // kept for when the body is gone
var array<ModBloodDecal> Remains;

var config bool bGibs;             // explosions and big overkills blow bodies apart
var config int GibOverkill;        // damage past the victim's health that gibs it
var config int MaxGibs;
var config float GibSpeed;
var array<ModGib> Gibs;
var array<Pawn> Gibbed;            // hidden bodies, shown again when the game reuses the pawn
var array<float> GibbedTime;
var array<Material> SetSkins;      // ModGibParts.Sets' skins, loaded once (their Diffuse)
var Material MeatTex, AlienMeatTex;

var ModReact React;
var ModSever Severer;              // decapitation and limb loss                // flinch, stagger and death ragdolls (fed by ModGoreRules too)
var config bool bBleedTrail;       // the badly wounded leave drops where they go
var config float BleedClot;        // seconds a wound takes to stop dripping
var config int CorpsePulpHits;     // shots into one corpse that pulp it into pieces (0: never)
var config bool bScreenBlood;      // close kills splash the screen
var config float ScreenBloodReach;
var config float BulletScale;      // shots' trails and meshes drawn at this size (the game's are huge)
var array<byte> ShotScaled;        // per Shots entry: its trail has been scaled

var Material Splats[4], Sprays[2], Pool, Scorches[3], CasingTex;   // the textures, referenced so the package keeps them
var Material RemainsTex[2];
var Material AlienSplats[4], AlienSprays[2], AlienPool, AlienRemains[2];   // the same in the Seekers' purple
var array<ModBloodDecal> Decals, Holes, Clutter;
var StaticMesh ShellMesh;          // the game's own shell, taken from its shell particles
var float ShellScale;              // ...and the size those particles draw it at
var array<Pawn> Dying;             // bodies waiting for their pool
var array<float> DyingTime;
var int Hits;
struct Bleeder
{
	var Pawn P;
	var float Rate;        // 0..1: how hard it bleeds
	var float Next;        // seconds to the next drop
};
var array<Bleeder> Bleeders;
struct Pulp
{
	var Pawn P;
	var int Hits;
};
var array<Pulp> Pulps;
var string LastGuns;                // bGoreLog
var array<Actor> Seen;
var array<Projectile> Shots;       // projectiles in flight: where they were and how fast,
var array<vector> ShotLoc, ShotVel;// to find the surface they hit when they vanish

event PostBeginPlay()
{
	local ModGoreRules R;
	local int i;

	Super.PostBeginPlay();
	if (Level.Game == None)
		return;
	// clamped, not tiled: a projector wider than its picture would repeat it
	for (i = 0; i < 4; i++)
	{
		ClampTex(Splats[i]);
		ClampTex(AlienSplats[i]);
	}
	for (i = 0; i < 2; i++)
	{
		ClampTex(Sprays[i]);
		ClampTex(AlienSprays[i]);
	}
	ClampTex(Pool);
	ClampTex(AlienPool);
	for (i = 0; i < 2; i++)
	{
		ClampTex(RemainsTex[i]);
		ClampTex(AlienRemains[i]);
	}
	ClampTex(CasingTex);
	for (i = 0; i < 3; i++)
		ClampTex(Scorches[i]);
	React = Spawn(class'ModReact');
	React.Gore = self;
	Severer = Spawn(class'ModSever');
	Severer.Gore = self;
	R = Spawn(class'ModGoreRules');
	R.Gore = self;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = R;
	else
		Level.Game.GameRulesModifiers.AddGameRules(R);
	class'ModSettings'.static.Note("gore: watching hits");
}


static function ClampTex(Material M)
{
	if (BitmapMaterial(M) != None)
	{
		BitmapMaterial(M).UClampMode = TC_Clamp;
		BitmapMaterial(M).VClampMode = TC_Clamp;
	}
}

function bool Bleeds(Pawn P, class<DamageType> DamageType)
{
	if (!bBlood || P == None || DamageType == None || !DamageType.default.bCausesBlood)
		return false;
	if (P.IsA('Vehicle') || P.IsA('Turret'))
		return false;
	return BloodKind(P) != 0;
}

// the colour of a character's blood, as the game's hit particles have it (the level's
// SurfaceProperties table, read with ModPilot BLOODFX): 1 red (humans, Aurelians and
// anything unlisted), 2 purple (Seekers), 0 none (holograms spark blue, ShockTroopers
// are armour)
static function int BloodKind(Pawn P)
{
	switch (P.GetSurfaceType())
	{
	case EST_Seeker:
	case EST_SeekerBlocking:
		return 2;
	case EST_ShockTrooper:
	case EST_HologramGuyA:
	case EST_HologramGuyB:
	case EST_HologramGuyC:
	case EST_VehicleDefault:
	case EST_Metal:
		return 0;
	}
	return 1;
}

function Material SplatTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return AlienSplats[Rand(4)];
	return Splats[Rand(4)];
}

function Material SprayTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return AlienSprays[Rand(2)];
	return Sprays[Rand(2)];
}

function Material PoolTex(Pawn P)
{
	if (BloodKind(P) == 2)
		return AlienPool;
	return Pool;
}

// a hit: Damage after the game's scaling, the victim still standing or not
function Hit(Pawn Victim, Pawn Instigator, vector HitLocation, vector Momentum, int Damage, class<DamageType> DamageType)
{
	local vector Dir, HitL, HitN;
	local float Size;

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: hit " $ Victim $ " " $ Damage $ " " $ DamageType $ " bleeds " $ Bleeds(Victim, DamageType));
	if (Damage <= 0 || !Bleeds(Victim, DamageType))
		return;
	Hits++;
	if (VSize(Momentum) > 1)
		Dir = Normal(Momentum);
	else if (Instigator != None)
		Dir = Normal(HitLocation - Instigator.Location);
	else
		Dir = vector(Victim.Rotation) * -1;
	if (VSize(HitLocation - Victim.Location) > Victim.CollisionRadius * 3)
		HitLocation = Victim.Location;
	// the bigger the hit, the bigger the mark (a pistol ~10-20, a launcher ~100)
	Size = DecalScale * FClamp(0.35 + Damage / 120.0, 0.35, 1.0);

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: dir " $ Dir $ " from " $ HitLocation $ " texture " $ Sprays[0] $ " floor " $ Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) $ " at " $ HitL);
	// the spray behind the victim, along the shot (a little downward: blood falls)
	Dir = Normal(Dir + vect(0,0,-0.25));
	if (Trace(HitL, HitN, HitLocation + Dir * SprayReach, HitLocation + Dir * Victim.CollisionRadius, false) != None)
		Mark(SprayTex(Victim), HitL, HitN, Dir, Size * (0.8 + 0.6 * VSize(HitL - HitLocation) / SprayReach));
	// drips under the hit
	if (FRand() < 0.85 && Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) != None)
		Mark(SplatTex(Victim), HitL + VRand() * vect(1,1,0) * 30, HitN, vect(0,0,0), Size * 0.6);
	if (bBleedTrail && Victim.Health > Damage && !Victim.IsHumanControlled())
		Bleed(Victim, Damage);
	// a pool under a fresh body
	if (Victim.Health <= 0 || Damage >= Victim.Health)
	{
		ScreenSplash(Victim.Location, BloodKind(Victim), 0.3 + FClamp(Damage / 150.0, 0, 0.4));
		AddDying(Victim);
		if (bGibs && WantsGib(Victim, Damage, DamageType))
			Gib(Victim, Dir, Damage);
		else if (Severer != None)
			Severer.Kill(Victim, HitLocation, Dir, Damage);
	}
}

// an explosion (the game's dmgType_Explosion family, less the push/pull powers that
// throw bodies about) or a hit GibOverkill past what the victim had left
function bool WantsGib(Pawn P, int Damage, class<DamageType> DamageType)
{
	local string N;

	if (P.bHidden || GibSet(P) < 0)
		return false;
	if (Damage - Max(P.Health, 0) >= GibOverkill || DamageType.default.bAlwaysGibs)
		return true;
	N = Caps(string(DamageType.Name));
	if (InStr(N, "PUSH") >= 0 || InStr(N, "PULL") >= 0 || InStr(N, "LEVITATE") >= 0 || InStr(N, "SHATTER") >= 0 || InStr(N, "SPEEDBURST") >= 0 || InStr(N, "SHIELD") >= 0)
		return false;
	return InStr(N, "EXPLOSION") >= 0 || InStr(N, "GRENADE") >= 0 || InStr(N, "LAUNCHER") >= 0 || InStr(N, "ALTFIRE") >= 0 || InStr(N, "MISSLE") >= 0;
}

// which set of parts fits a body: humans the marine's, Seeker soldiers the infantry's
// (not their hounds or shock troopers); -1 none
function int GibSet(Pawn P)
{
	local name Want;
	local int i;
	local string M;

	M = Caps(string(P.Mesh));
	switch (P.GetSurfaceType())
	{
	case EST_Human:
		Want = 'marine';
		break;
	case EST_Seeker:
	case EST_SeekerBlocking:
		if (InStr(M, "HOUND") >= 0 || InStr(M, "SHOCK") >= 0 || InStr(M, "DOG") >= 0)
			return -1;
		Want = 'seekerinfantry';
		break;
	default:
		return -1;
	}
	for (i = 0; i < class'ModGibParts'.default.Sets.Length; i++)
		if (class'ModGibParts'.default.Sets[i].Name == Want)
			return i;
	return -1;
}

function Material SetSkin(int Set)
{
	local Material M;

	while (SetSkins.Length <= Set)
		SetSkins[SetSkins.Length] = None;
	if (SetSkins[Set] == None)
	{
		M = Material(DynamicLoadObject(class'ModGibParts'.default.Sets[Set].Skin, class'Material'));
		// a skin shader is for skinned meshes: the parts wear its plain texture
		if (AdventShaderMaterial(M) != None && AdventShaderMaterial(M).Diffuse != None)
			M = AdventShaderMaterial(M).Diffuse;
		else if (PSSkinShader(M) != None && PSSkinShader(M).Diffuse != None)
			M = PSSkinShader(M).Diffuse;
		SetSkins[Set] = M;
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: gib skin " $ class'ModGibParts'.default.Sets[Set].Name $ " = " $ M);
	}
	return SetSkins[Set];
}

// the body comes apart: each part where it was on the body (scaled to the victim's
// height, turned with it), thrown out from the middle and along the shot
function Gib(Pawn P, vector Dir, int Damage)
{
	local int Set, Kind;
	local float K;
	local vector Feet;
	local class<ModGibParts> T;

	T = class'ModGibParts';
	Set = GibSet(P);
	if (Set < 0)
		return;
	Kind = BloodKind(P);
	// its standing height: a corpse's collision is a low box (a pulped corpse came out half size)
	K = FClamp(2 * FMax(P.CollisionHeight, P.default.CollisionHeight) / T.default.Sets[Set].Height, 0.5, 2.0);
	Feet = P.Location - vect(0,0,1) * P.CollisionHeight;
	if (SpawnGibs(Set, Kind, Feet, P.Rotation.Yaw, K, Dir, Damage) == 0)
		return;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ P $ " comes apart (" $ T.default.Sets[Set].Name $ ", scale " $ K $ ")");
	ScreenSplash(P.Location, Kind, 1.0);
	Hide(P, true);
	Gibbed[Gibbed.Length] = P;
	GibbedTime[GibbedTime.Length] = Level.TimeSeconds;
}

// one set of parts standing at Feet facing Yaw, thrown apart; the number of parts
function int SpawnGibs(int Set, int Kind, vector Feet, int Yaw, float K, vector Dir, int Damage)
{
	local int i, n;
	local float Speed, Push, MinSize;
	local vector Mid, W, V, HitL, HitN;
	local rotator R;
	local ModGib G;
	local class<ModGibParts> T;

	T = class'ModGibParts';
	Mid = Feet + vect(0,0,1) * T.default.Sets[Set].Height * K * 0.55;
	R.Yaw = Yaw - 16384;    // the meshes' forward is their Y
	Speed = GibSpeed * FClamp(0.8 + Damage / 600.0, 0.8, 1.6);
	for (i = 0; i < T.default.Parts.Length; i++)
	{
		if (T.default.Parts[i].Set != T.default.Sets[Set].Name || T.default.Parts[i].Mesh == None)
			continue;
		while (Gibs.Length > 0 && (Gibs.Length >= MaxGibs || Gibs[0] == None || Gibs[0].bDeleteMe))
		{
			if (Gibs[0] != None && !Gibs[0].bDeleteMe)
				Gibs[0].Destroy();
			Gibs.Remove(0, 1);
		}
		W = Feet + ((T.default.Parts[i].Pivot * K) >> R);
		G = Spawn(class'ModGib',,, W, R);
		if (G == None)
			continue;
		n++;
		G.Gore = self;
		G.Kind = Kind;
		G.SetStaticMesh(T.default.Parts[i].Mesh);
		G.SetDrawScale(K);
		G.Skins[0] = SetSkin(Set);
		if (Kind == 2)
			G.Skins[1] = AlienMeatTex;
		else
			G.Skins[1] = MeatTex;
		G.Stay = 30 + 20 * FRand();
		G.Size = T.default.Parts[i].Size * K;
		MinSize = FMin(T.default.Parts[i].Size.X, FMin(T.default.Parts[i].Size.Y, T.default.Parts[i].Size.Z));
		// light parts fly farther than the torso
		Push = FClamp(1.5 - T.default.Parts[i].Mass / 90.0, 0.45, 1.4);
		V = Normal(W - Mid + VRand() * 10) * Speed * Push * (0.6 + 0.8 * FRand()) + Dir * Speed * 0.7 * Push + vect(0,0,1) * Speed * (0.4 + 0.5 * FRand());
		G.Launch(V, PhysicsVolume.Gravity.Z, MinSize * K * 0.5);
		Gibs[Gibs.Length] = G;
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ n $ " gib parts at " $ Feet);
	if (n == 0)
		return 0;
	// a burst of blood all round, and the body gone
	for (i = 0; i < 6; i++)
	{
		V = Normal(VRand() + Dir * 0.6 + vect(0,0,-0.4));
		if (Trace(HitL, HitN, Mid + V * SprayReach * 1.4, Mid, false) != None)
			Mark(KindSpray(Kind), HitL, HitN, V, DecalScale * (0.7 + 0.5 * FRand()));
	}
	if (Trace(HitL, HitN, Mid - vect(0,0,400), Mid, false) != None)
		Mark(KindSplat(Kind), HitL, HitN, vect(0,0,0), DecalScale * 1.1);
	return n;
}

// one gib piece by its part name ("head", "l_lowerarm"...) of a set, thrown from Spot
function ModGib ThrowPart(int Set, int Kind, string Part, vector Spot, int Yaw, float K, vector V)
{
	local class<ModGibParts> T;
	local int i;
	local ModGib G;
	local rotator R;
	local float MinSize;
	local string Want;

	T = class'ModGibParts';
	Want = Caps(string(T.default.Sets[Set].Name) $ "_" $ Part);
	for (i = 0; i < T.default.Parts.Length; i++)
	{
		if (T.default.Parts[i].Set != T.default.Sets[Set].Name || T.default.Parts[i].Mesh == None)
			continue;
		if (Caps(string(T.default.Parts[i].Mesh.Name)) != Want)
			continue;
		while (Gibs.Length > 0 && (Gibs.Length >= MaxGibs || Gibs[0] == None || Gibs[0].bDeleteMe))
		{
			if (Gibs[0] != None && !Gibs[0].bDeleteMe)
				Gibs[0].Destroy();
			Gibs.Remove(0, 1);
		}
		R.Yaw = Yaw - 16384;
		G = Spawn(class'ModGib',,, Spot, R);
		if (G == None)
			return None;
		G.Gore = self;
		G.Kind = Kind;
		G.SetStaticMesh(T.default.Parts[i].Mesh);
		G.SetDrawScale(K);
		G.Skins[0] = SetSkin(Set);
		if (Kind == 2)
			G.Skins[1] = AlienMeatTex;
		else
			G.Skins[1] = MeatTex;
		G.Stay = 30 + 20 * FRand();
		G.Size = T.default.Parts[i].Size * K;
		MinSize = FMin(T.default.Parts[i].Size.X, FMin(T.default.Parts[i].Size.Y, T.default.Parts[i].Size.Z));
		G.Launch(V, PhysicsVolume.Gravity.Z, MinSize * K * 0.5);
		Gibs[Gibs.Length] = G;
		return G;
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: no gib part " $ Want);
	return None;
}

// blood from a fresh cut: sprays along the shot and around, drips below
function CutBlood(vector Spot, vector Dir, int Kind)
{
	local int i;
	local vector V, HitL, HitN;

	if (!bBlood || Kind == 0)
		return;
	for (i = 0; i < 3; i++)
	{
		V = Normal(Dir * (i == 0 ? 1.0 : 0.3) + VRand() * 0.6 + vect(0,0,-0.3));
		if (Trace(HitL, HitN, Spot + V * SprayReach, Spot, false) != None)
			Mark(KindSpray(Kind), HitL, HitN, V, DecalScale * (0.6 + 0.3 * FRand()));
	}
	if (Trace(HitL, HitN, Spot - vect(0,0,400), Spot, false) != None)
		Mark(KindSplat(Kind), HitL, HitN, vect(0,0,0), DecalScale * 0.7);
}

function Hide(Pawn P, bool bHide)
{
	local int i;

	P.bHidden = bHide;
	for (i = 0; i < P.Attached.Length; i++)
		if (P.Attached[i] != None)
			P.Attached[i].bHidden = bHide;
}

// a gibbed body shown again once the game brings the pawn back
function CheckGibbed()
{
	local int i;

	for (i = Gibbed.Length - 1; i >= 0; i--)
	{
		if (Gibbed[i] == None || Gibbed[i].bDeleteMe)
		{
			Gibbed.Remove(i, 1);
			GibbedTime.Remove(i, 1);
		}
		else if (Level.TimeSeconds - GibbedTime[i] > 1.0 && Gibbed[i].Health > 0)
		{
			Hide(Gibbed[i], false);
			Gibbed.Remove(i, 1);
			GibbedTime.Remove(i, 1);
		}
	}
}

// a part thrown hard against something
function GibHit(vector Spot, vector N, int Kind, float Speed)
{
	if (bBlood && Kind != 0)
		Mark(KindSplat(Kind), Spot, N, vect(0,0,0), DecalScale * FClamp(Speed / 1600.0, 0.2, 0.5));
}

// a part that has lain long enough sinks into a stain
function GibGone(ModGib G)
{
	local vector HitL, HitN;

	if (bBlood && G.Kind != 0 && Trace(HitL, HitN, G.Location - vect(0,0,100), G.Location + vect(0,0,20), false) != None)
		Mark(KindSplat(G.Kind), HitL, HitN, vect(0,0,0), DecalScale * 0.35);
}

function Material KindSplat(int Kind)
{
	if (Kind == 2)
		return AlienSplats[Rand(4)];
	return Splats[Rand(4)];
}

function Material KindSpray(int Kind)
{
	if (Kind == 2)
		return AlienSprays[Rand(2)];
	return Sprays[Rand(2)];
}

function AddDying(Pawn P)
{
	local int i;

	for (i = 0; i < Dying.Length; i++)
		if (Dying[i] == P)
			return;
	Dying[Dying.Length] = P;
	DyingTime[DyingTime.Length] = Level.TimeSeconds + 1.2 + FRand() * 0.6;
}

// projectiles: a new one from the player's gun is a shot (a casing); a vanished one hit
// something (a bullet hole where its last step meets a surface)
function TrackShots()
{
	local Projectile P;
	local int i;
	local bool bKnown;

	for (i = Shots.Length - 1; i >= 0; i--)
	{
		if (Shots[i] == None || Shots[i].bDeleteMe)
		{
			ShotGone(ShotLoc[i], ShotVel[i]);
			Shots.Remove(i, 1);
			ShotLoc.Remove(i, 1);
			ShotVel.Remove(i, 1);
			ShotScaled.Remove(i, 1);
		}
		else
		{
			if (ShotScaled[i] != 1)
				ShrinkShot(i);
			ShotThroughCorpses(ShotLoc[i], Shots[i].Location);
			ShotLoc[i] = Shots[i].Location;
			ShotVel[i] = Shots[i].Velocity;
		}
	}
	if (class'ModSettings'.default.bGoreLog)
		LogGuns();
	if (bCasings)
		FindShells();
	ForEach DynamicActors(class'Projectile', P)
	{
		bKnown = false;
		for (i = 0; i < Shots.Length; i++)
			if (Shots[i] == P)
			{
				bKnown = true;
				break;
			}
		if (bKnown)
			continue;
		Shots[Shots.Length] = P;
		ShotLoc[ShotLoc.Length] = P.Location;
		ShotVel[ShotVel.Length] = P.Velocity;
		ShotScaled[ShotScaled.Length] = 0;
		ShrinkShot(Shots.Length - 1);
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: shot " $ P.Class $ " owner " $ P.Owner $ " instigator " $ P.Instigator $ " speed " $ int(VSize(P.Velocity)));
	}
}

// a shot drawn smaller: its mesh at once, its trail (spawned a moment after the shot)
// as soon as it's there. Grenades and rockets keep their size.
function ShrinkShot(int i)
{
	local EonProjectile P;

	P = EonProjectile(Shots[i]);
	if (P == None || BulletScale >= 0.99 || P.IsA('GrenadeProjectile'))
	{
		ShotScaled[i] = 1;
		return;
	}
	if (ShotScaled[i] == 0)
	{
		P.SetDrawScale(P.DrawScale * BulletScale);
		ShotScaled[i] = 2;
	}
	if (P.Trail != None)
	{
		P.Trail.Scale(BulletScale);
		if (P.TrailSmoke != None)
			P.TrailSmoke.Scale(BulletScale);
		ShotScaled[i] = 1;
	}
}

function LogGuns()
{
	local Pawn P;
	local string S;

	P = Level.GetLocalPlayerController().Pawn;
	if (P == None)
		return;
	if (AdventWeapon(P.RightWeapon) != None)
		S = "right " $ P.RightWeapon.Class $ " " $ P.RightWeapon.GetStateName() $ " clip " $ AdventWeapon(P.RightWeapon).AmmoAmount[0].fCurrentClipAmmo $ "/" $ AdventWeapon(P.RightWeapon).AmmoAmount[1].fCurrentClipAmmo $ " shots " $ AdventWeapon(P.RightWeapon).iCurShotCount $ " burst " $ AdventWeapon(P.RightWeapon).iCurBurstCount $ " sound " $ AdventWeapon(P.RightWeapon).fLastFireSoundTime $ " effect " $ AdventWeapon(P.RightWeapon).fLastEffectTime $ " stop " $ AdventWeapon(P.RightWeapon).fStopFireTime;
	if (AdventWeapon(P.LeftWeapon) != None)
		S = S $ " left " $ P.LeftWeapon.Class $ " " $ P.LeftWeapon.GetStateName() $ " clip " $ AdventWeapon(P.LeftWeapon).AmmoAmount[0].fCurrentClipAmmo $ "/" $ AdventWeapon(P.LeftWeapon).AmmoAmount[1].fCurrentClipAmmo;
	if (S != LastGuns)
		class'ModSettings'.static.Note("gore: guns " $ S);
	LastGuns = S;
	LogNewActors(P);
}

// the game's shell particles (fx_HumanBlaster_Shells and the like, one burst per shot):
// each becomes one ModCasing thrown the same way, and the particles go
function FindShells()
{
	local Emitter E;
	local ModCasing C;
	local vector Dir;
	local int i;

	ForEach DynamicActors(class'Emitter', E)
	{
		if (E.Tag == 'ModShell' || InStr(Caps(string(E.Class.Name)), "_SHELLS") < 0)
			continue;
		E.Tag = 'ModShell';
		for (i = 0; i < E.Emitters.Length && ShellMesh == None; i++)
			if (MeshEmitter(E.Emitters[i]) != None)
			{
				ShellMesh = MeshEmitter(E.Emitters[i]).StaticMesh;
				ShellScale = (E.Emitters[i].StartSizeRange.X.Min + E.Emitters[i].StartSizeRange.X.Max) / 2;
			}
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: shells " $ E.Class $ " at " $ E.Location $ " mesh " $ ShellMesh $ " scale " $ ShellScale);
		C = Spawn(class'ModCasing',,, E.Location, RotRand());
		if (C == None)
			continue;
		C.Gore = self;
		C.SetStaticMesh(ShellMesh);
		C.SetDrawScale(FClamp(ShellScale, 0.02, 2));
		if (E.Skins.Length > 0)
			C.Skins[0] = E.Skins[0];
		Dir = vector(E.Rotation);
		C.Launch(Dir * (120 + 80 * FRand()) + vect(0,0,1) * (160 + 80 * FRand()) + VRand() * 30, PhysicsVolume.Gravity.Z * 0.6);
		E.Kill();
	}
}

// a settled casing, flattened into a mark on the floor
function AddClutter(vector Spot, int Yaw)
{
	local vector HitL, HitN;
	local ModBloodDecal D;
	local rotator R;

	if (Trace(HitL, HitN, Spot - vect(0,0,40), Spot + vect(0,0,10), false) == None)
		return;
	while (Clutter.Length > 0 && (Clutter.Length >= MaxClutter || Clutter[0] == None || Clutter[0].bDeleteMe))
	{
		if (Clutter[0] != None && !Clutter[0].bDeleteMe)
			Clutter[0].Destroy();
		Clutter.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, HitL + HitN * 16);
	if (D == None)
		return;
	R.Yaw = Yaw;
	D.Place(CasingTex, HitL, HitN, vector(R), 0.22);
	D.LifeSpan = 600;
	Clutter[Clutter.Length] = D;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: casing settled at " $ HitL $ " (" $ Clutter.Length $ " on the floor)");
}

// the dead lying around (refreshed twice a second): Health gone, in the Dying state.
// A body leaving the list (the game fades it, recycles the pawn for a spawner, or
// destroys it) leaves its remains where it last lay.
function ScanCorpses()
{
	local Pawn P;
	local int i;
	local bool bKnown;

	for (i = Corpses.Length - 1; i >= 0; i--)
	{
		P = Corpses[i];
		if (P == None || P.bDeleteMe || P.Health > 0 || !P.IsInState('Dying') || (P.bAllowAlphaFading && !P.default.bAllowAlphaFading))
		{
			if (class'ModSettings'.default.bGoreLog)
				class'ModSettings'.static.Note("gore: a body is taken (" $ P $ "), remains at " $ CorpseLoc[i] $ " kind " $ CorpseKind[i]);
			if (bRemains && CorpseKind[i] != 0)
				AddRemains(CorpseLoc[i], CorpseKind[i]);
			Corpses.Remove(i, 1);
			CorpseLoc.Remove(i, 1);
			CorpseKind.Remove(i, 1);
		}
		else
			CorpseLoc[i] = P.Location;
	}
	ForEach DynamicActors(class'Pawn', P)
	{
		if (P.Health > 0 || P.IsHumanControlled() || P.bDeleteMe || !P.IsInState('Dying'))
			continue;
		if ((P.bAllowAlphaFading && !P.default.bAllowAlphaFading) || P.bHidden)
			continue;
		bKnown = false;
		for (i = 0; i < Corpses.Length; i++)
			if (Corpses[i] == P)
			{
				bKnown = true;
				break;
			}
		if (!bKnown)
		{
			Corpses[Corpses.Length] = P;
			CorpseLoc[CorpseLoc.Length] = P.Location;
			CorpseKind[CorpseKind.Length] = BloodKind(P);
		}
	}
}

// remains, flat on the floor under where the body lay, turned any way
function AddRemains(vector Spot, int Kind)
{
	local vector HitL, HitN;
	local ModBloodDecal D;
	local rotator R;
	local Material T;

	if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20), false) == None || HitN.Z < 0.6)
		return;
	while (Remains.Length > 0 && (Remains.Length >= MaxRemains || Remains[0] == None || Remains[0].bDeleteMe))
	{
		if (Remains[0] != None && !Remains[0].bDeleteMe)
			Remains[0].Destroy();
		Remains.Remove(0, 1);
	}
	if (Kind == 2)
		T = AlienRemains[Rand(2)];
	else
		T = RemainsTex[Rand(2)];
	D = Spawn(class'ModBloodDecal',,, HitL + HitN * 16);
	if (D == None)
		return;
	R.Yaw = Rand(65536);
	D.Place(T, HitL, HitN, vector(R), DecalScale * (1.1 + 0.25 * FRand()));
	D.LifeSpan = 600;
	Remains[Remains.Length] = D;
}

// a shot's path from A to B through a body: closest approach to the body's axis, within its width
function ShotThroughCorpses(vector A, vector B)
{
	local int i;
	local Pawn P;
	local vector D, C, Q, Dir;
	local float T, L, R;

	if (!bCorpseShots || Corpses.Length == 0)
		return;
	D = B - A;
	L = VSize(D);
	if (L < 1)
		return;
	Dir = D / L;
	for (i = 0; i < Corpses.Length; i++)
	{
		P = Corpses[i];
		if (P == None || P.bDeleteMe)
			continue;
		C = P.Location;
		T = FClamp((C - A) Dot Dir, 0, L);
		Q = A + Dir * T;
		R = FMax(P.CollisionRadius, 30) * 1.3;
		if (VSize((Q - C) * vect(1,1,0)) > R || Q.Z > C.Z + 25 || Q.Z < C.Z - P.CollisionHeight - 15)
			continue;
		CorpseHit(P, Q, Dir);
		return;
	}
}

function CorpseHit(Pawn P, vector Spot, vector Dir)
{
	local vector HitL, HitN;

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: corpse hit " $ P $ " physics " $ P.Physics $ " at " $ Spot);
	// it bleeds like the living do (they don't reach NetDamage any more: Dying.TakeDamage
	// doesn't pass hits on)
	if (bBlood && BloodKind(P) != 0)
	{
		if (Trace(HitL, HitN, Spot + Normal(Dir + vect(0,0,-0.4)) * SprayReach, Spot, false) != None)
			Mark(SprayTex(P), HitL, HitN, Dir, DecalScale * 0.6);
		if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,10), false) != None)
			Mark(SplatTex(P), HitL + VRand() * vect(1,1,0) * 20, HitN, vect(0,0,0), DecalScale * 0.45);
	}
	if (P.LifeSpan > 0)
		P.LifeSpan += 0.2;
	if (Severer != None)
		Severer.CorpseHit(P, Spot, Dir);
	if (PulpHit(P, Dir))
		return;
	// no ragdolls in this release (no KarmaData): the body twitches instead
	if (P.Physics == PHYS_KarmaRagdoll)
		P.KAddImpulse(Dir * CorpseKick, Spot);
	else if (React != None)
		React.CorpseFlinch(P, Spot, Dir);
}

// a body still in its death pose goes ragdoll, pushed along the shot (its species' own
// ragdoll skeleton, AdventPawn.RagdollOverride; the engine allows MaxRagdolls at a time)
function Limp(Pawn P, vector Dir, vector Spot)
{
	local AdventPawn A;
	local KarmaParamsSkel K;
	local string Skel;

	A = AdventPawn(P);
	if (A == None)
		return;
	// only from an ordinary death: not mid-leap or scripted movement, not stuck in a wall
	// (a hound dying as it jumps through a window crashed the game)
	if (!RagdollSafe(A))
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: " $ A $ " not ragdolled: physics " $ A.Physics $ " state " $ A.GetStateName() $ " in a wall " $ InWall(A));
		return;
	}
	Skel = RagdollSkeleton(A);
	if (Skel == "")
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: " $ A $ " (" $ A.Mesh $ ") fits no ragdoll skeleton, keeps its death animation");
		return;
	}
	A.KMakeRagdollAvailable();
	if (!A.KIsRagdollAvailable())
		return;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: limp " $ A $ " physics " $ A.Physics $ " state " $ A.GetStateName() $ " had KParams " $ A.KParams $ class'ModPilot'.static.Eval2(KarmaParamsSkel(A.KParams) != None, " enabled " $ KarmaParamsSkel(A.KParams).KStartEnabled $ " drop " $ KarmaParamsSkel(A.KParams).KVelDropBelowThreshold $ " upright " $ KarmaParamsSkel(A.KParams).bKStayUpright $ " skel " $ KarmaParamsSkel(A.KParams).KSkeleton, ""));
	if (KarmaParamsSkel(A.KParams) == None)
		A.KParams = CorpseParams;
	K = KarmaParamsSkel(A.KParams);
	if (K == None)
		return;
	K.KSkeleton = Skel;
	K.KStartLinVel = Dir * 250 + vect(0,0,60);
	K.KStartAngVel = VRand() * 3000;
	K.KShotStart = Spot - Dir;
	K.KShotEnd = Spot + Dir * 100;
	K.KShotStrength = CorpseKick;
	A.KSetBlockKarma(true);
	A.SetPhysics(PHYS_KarmaRagdoll);
	A.StopAnimating(true);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ A $ " went limp (" $ Skel $ "), physics " $ A.Physics);
}

function bool RagdollSafe(Pawn P)
{
	if (P.Physics != PHYS_Walking && P.Physics != PHYS_Falling && P.Physics != PHYS_RootMotion && P.Physics != PHYS_None)
		return false;
	if (P.Base != None && Pawn(P.Base) != None)
		return false;
	return !InWall(P);
}

// the body's middle inside solid geometry: short traces up and down from it both blocked
function bool InWall(Pawn P)
{
	local vector Up;

	Up = vect(0,0,1) * FMin(P.CollisionHeight * 0.5, 30);
	return !FastTrace(P.Location + Up, P.Location) && !FastTrace(P.Location - Up, P.Location);
}

// the ragdoll skeleton (KarmaData\Advent.ka, listed in ModRagdollBones) whose every
// bone this body's mesh has: the one it asks for first, then any other. "" if none
// fits: a ragdoll part with no bone crashes the game (Seeker hounds ask for "seeker"
// but have no upper arms), and a skeleton the file doesn't have freezes the body.
function string RagdollSkeleton(AdventPawn A)
{
	local class<ModRagdollBones> T;
	local int i;

	T = class'ModRagdollBones';
	for (i = 0; i < T.default.Skeletons.Length; i++)
		if (T.default.Skeletons[i].Name ~= A.RagdollOverride && FitsSkeleton(A, i))
			return Allowed(T.default.Skeletons[i].Name);
	for (i = 0; i < T.default.Skeletons.Length; i++)
		if (!(T.default.Skeletons[i].Name ~= A.RagdollOverride) && FitsSkeleton(A, i))
			return Allowed(T.default.Skeletons[i].Name);
	return "";
}

// "" for a skeleton switched off
function string Allowed(string Skel)
{
	if (!bHoundRagdolls && Skel ~= "seekerhound")
		return "";
	return Skel;
}

// a bone the mesh doesn't have comes back where the root is, as a made-up name does
function bool FitsSkeleton(Pawn P, int S)
{
	local class<ModRagdollBones> T;
	local vector Missing;
	local int i;
	local name B;

	T = class'ModRagdollBones';
	Missing = P.GetBoneCoords('AdventModNoSuchBone').Origin;
	for (i = 0; i < T.default.Skeletons[S].Count; i++)
	{
		B = T.default.Bones[T.default.Skeletons[S].First + i];
		if (i > 0 && VSize(P.GetBoneCoords(B).Origin - Missing) < 0.01)
			return false;
	}
	return true;
}

// testing: actors the player's gun or pawn just made (what marks a shot)
function LogNewActors(Pawn P)
{
	local Actor A;
	local int i;
	local bool bKnown;

	ForEach DynamicActors(class'Actor', A)
	{
		if (A.Owner == None || (A.Owner != P.RightWeapon && A.Owner != P && A.Owner != P.LeftWeapon && A.Instigator != P))
			continue;
		if (A == P.RightWeapon || A == P.LeftWeapon || A == P.Controller)
			continue;
		bKnown = false;
		for (i = 0; i < Seen.Length; i++)
			if (Seen[i] == A)
			{
				bKnown = true;
				break;
			}
		if (bKnown)
			continue;
		Seen[Seen.Length] = A;
		class'ModSettings'.static.Note("gore: new " $ A.Class $ " owner " $ A.Owner $ " at " $ A.Location $ " t " $ Level.TimeSeconds);
	}
}

function ShotGone(vector Loc, vector Vel)
{
	local vector HitL, HitN;
	local Actor A;

	ShotThroughCorpses(Loc, Loc + Vel * 0.1);

	A = Trace(HitL, HitN, Loc + Vel * 0.1, Loc - Normal(Vel) * 20, false);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: shot gone at " $ Loc $ " hit " $ A $ " at " $ HitL);
	// a scorch on walls, floors and level meshes; nothing on characters (they bleed instead)
	if (bImpacts && A != None && (A == Level || A.bWorldGeometry || A.bStatic) && Pawn(A) == None)
		AddHole(Scorches[Rand(3)], HitL, HitN, DecalScale * (0.3 + 0.12 * FRand()));
}

event Tick(float DeltaTime)
{
	local int i;
	local vector HitL, HitN, Spot;
	local ModBloodDecal D;

	CorpseScan -= DeltaTime;
	if (CorpseScan <= 0)
	{
		CorpseScan = 0.5;
		ScanCorpses();
		CheckGibbed();
	}
	TrackShots();
	if (bBleedTrail)
		BleedTrails(DeltaTime);
	for (i = Dying.Length - 1; i >= 0; i--)
	{
		if (Dying[i] != None && !Dying[i].bDeleteMe && Level.TimeSeconds < DyingTime[i])
			continue;
		if (Dying[i] != None && !Dying[i].bDeleteMe)
		{
			// where the body lies: ragdolls move their mesh, not always the actor; the
			// actor is still the best guess the script has
			Spot = Dying[i].Location;
			if (Trace(HitL, HitN, Spot - vect(0,0,300), Spot + vect(0,0,20), false) != None && HitN.Z > 0.6)
			{
				D = Mark(PoolTex(Dying[i]), HitL, HitN, vect(0,0,0), DecalScale * 0.6);
				if (D != None)
				{
					D.Grow(DecalScale * 0.2, DecalScale * (0.9 + FRand() * 0.4), 5 + FRand() * 3);
					D.LifeSpan = 300;
				}
			}
		}
		Dying.Remove(i, 1);
		DyingTime.Remove(i, 1);
	}
}

// a wound that drips: the harder the hit against what the victim can take, the more
function Bleed(Pawn P, int Damage)
{
	local int i;
	local Bleeder B;
	local float Add;

	if (BloodKind(P) == 0)
		return;
	Add = Damage / (0.3 * FMax(P.default.Health, 100));
	for (i = 0; i < Bleeders.Length; i++)
		if (Bleeders[i].P == P)
		{
			Bleeders[i].Rate = FMin(Bleeders[i].Rate + Add, 1.0);
			return;
		}
	if (Bleeders.Length >= 16)
		return;
	B.P = P;
	B.Rate = FMin(Add, 1.0);
	B.Next = 0.3;
	Bleeders[Bleeders.Length] = B;
}

// drops under the wounded, fewer as the wound clots; none from the dead (they pool)
function BleedTrails(float DeltaTime)
{
	local int i;
	local Pawn P;
	local vector HitL, HitN;

	for (i = Bleeders.Length - 1; i >= 0; i--)
	{
		P = Bleeders[i].P;
		Bleeders[i].Rate -= DeltaTime / BleedClot;
		if (P == None || P.bDeleteMe || P.Health <= 0 || P.bHidden || Bleeders[i].Rate <= 0.05)
		{
			Bleeders.Remove(i, 1);
			continue;
		}
		Bleeders[i].Next -= DeltaTime;
		if (Bleeders[i].Next > 0)
			continue;
		// a drop every 0.25 s at the worst, every 1.5 s when nearly clotted
		Bleeders[i].Next = 0.25 + 1.25 * (1 - Bleeders[i].Rate) + 0.2 * FRand();
		if (Trace(HitL, HitN, P.Location - vect(0,0,1) * (P.CollisionHeight + 120), P.Location, false) != None)
			Mark(SplatTex(P), HitL + VRand() * vect(1,1,0) * 14, HitN, vect(0,0,0), DecalScale * (0.14 + 0.16 * Bleeders[i].Rate));
	}
}

// shots into a corpse add up: CorpsePulpHits of them and it comes apart
function bool PulpHit(Pawn P, vector Dir)
{
	local int i;
	local Pulp N;

	if (CorpsePulpHits <= 0 || !bGibs || P.bHidden || GibSet(P) < 0)
		return false;
	for (i = Pulps.Length - 1; i >= 0; i--)
		if (Pulps[i].P == None || Pulps[i].P.bDeleteMe || Pulps[i].P.Health > 0)
			Pulps.Remove(i, 1);
	for (i = 0; i < Pulps.Length; i++)
		if (Pulps[i].P == P)
			break;
	if (i == Pulps.Length)
	{
		N.P = P;
		Pulps[Pulps.Length] = N;
	}
	Pulps[i].Hits++;
	if (Pulps[i].Hits < CorpsePulpHits)
		return false;
	Pulps.Remove(i, 1);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ P $ " pulped by shots");
	Gib(P, Dir, 80);
	return true;
}

// blood on the screen from something bloody close to the player (ModScreenBlood)
function ScreenSplash(vector Spot, int Kind, float Strength)
{
	local PlayerController C;
	local ModScreenBlood B;
	local float D;

	B = class'ModScreenBlood'.default.Live;
	if (!bScreenBlood || !bBlood || Kind == 0 || B == None)
		return;
	C = Level.GetLocalPlayerController();
	if (C == None || C.Pawn == None)
		return;
	D = VSize(Spot - C.Pawn.Location);
	if (D > ScreenBloodReach)
		return;
	Strength *= 1 - 0.6 * D / ScreenBloodReach;
	B.Splash(KindSplat(Kind), 1 + int(Strength * 4), Strength);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: screen blood, strength " $ Strength $ " from " $ int(D) $ " away");
}

function ModBloodDecal AddHole(Material T, vector Spot, vector N, float Size)
{
	local ModBloodDecal D;

	while (Holes.Length > 0 && (Holes.Length >= MaxHoles || Holes[0] == None || Holes[0].bDeleteMe))
	{
		if (Holes[0] != None && !Holes[0].bDeleteMe)
			Holes[0].Destroy();
		Holes.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, Spot + N * 16);
	if (D == None)
		return None;
	D.Place(T, Spot, N, vect(0,0,0), Size);
	Holes[Holes.Length] = D;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ T.Name $ " at " $ Spot $ " (" $ Holes.Length $ " holes)");
	return D;
}

function ModBloodDecal Mark(Material T, vector Spot, vector N, vector Along, float Size)
{
	local ModBloodDecal D;

	if (class'ModSettings'.default.DebugDecalTexture != "")
		T = Material(DynamicLoadObject(class'ModSettings'.default.DebugDecalTexture, class'Material'));
	if (T == None)
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: no texture");
		return None;
	}
	while (Decals.Length > 0 && (Decals.Length >= MaxDecals || Decals[0] == None || Decals[0].bDeleteMe))
	{
		if (Decals[0] != None && !Decals[0].bDeleteMe)
			Decals[0].Destroy();
		Decals.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, Spot + N * 16);
	if (D == None)
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: the decal didn't spawn");
		return None;
	}
	D.Place(T, Spot, N, Along, Size);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ T.Name $ " at " $ Spot $ " normal " $ N $ " size " $ Size $ " (" $ Decals.Length + 1 $ " marks)");
	Decals[Decals.Length] = D;
	return D;
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Decals.Length; i++)
		if (Decals[i] != None)
			Decals[i].Destroy();
	for (i = 0; i < Holes.Length; i++)
		if (Holes[i] != None)
			Holes[i].Destroy();
	for (i = 0; i < Clutter.Length; i++)
		if (Clutter[i] != None)
			Clutter[i].Destroy();
	for (i = 0; i < Remains.Length; i++)
		if (Remains[i] != None)
			Remains[i].Destroy();
	for (i = 0; i < Gibs.Length; i++)
		if (Gibs[i] != None)
			Gibs[i].Destroy();
	if (Severer != None)
		Severer.Destroy();
	Super.Destroyed();
}

defaultproperties
{
     Splats(0)=Texture'AdventMod.Blood.BloodSplat0'
     Splats(1)=Texture'AdventMod.Blood.BloodSplat1'
     Splats(2)=Texture'AdventMod.Blood.BloodSplat2'
     Splats(3)=Texture'AdventMod.Blood.BloodSplat3'
     Sprays(0)=Texture'AdventMod.Blood.BloodSpray0'
     Sprays(1)=Texture'AdventMod.Blood.BloodSpray1'
     Pool=Texture'AdventMod.Blood.BloodPool0'
     AlienSplats(0)=Texture'AdventMod.Blood.AlienSplat0'
     AlienSplats(1)=Texture'AdventMod.Blood.AlienSplat1'
     AlienSplats(2)=Texture'AdventMod.Blood.AlienSplat2'
     AlienSplats(3)=Texture'AdventMod.Blood.AlienSplat3'
     AlienSprays(0)=Texture'AdventMod.Blood.AlienSpray0'
     AlienSprays(1)=Texture'AdventMod.Blood.AlienSpray1'
     AlienPool=Texture'AdventMod.Blood.AlienPool0'
     RemainsTex(0)=Texture'AdventMod.Blood.BloodRemains0'
     RemainsTex(1)=Texture'AdventMod.Blood.BloodRemains1'
     AlienRemains(0)=Texture'AdventMod.Blood.AlienRemains0'
     AlienRemains(1)=Texture'AdventMod.Blood.AlienRemains1'
     bRemains=True
     MeatTex=Texture'AdventMod.Blood.BloodMeat'
     AlienMeatTex=Texture'AdventMod.Blood.AlienMeat'
     bGibs=True
     BulletScale=0.550000
     GibOverkill=60
     MaxGibs=60
     GibSpeed=380.000000
     MaxRemains=40
     Scorches(0)=Texture'AdventMod.Blood.Scorch0'
     Scorches(1)=Texture'AdventMod.Blood.Scorch1'
     Scorches(2)=Texture'AdventMod.Blood.Scorch2'
     CasingTex=Texture'AdventMod.Blood.Casing0'
     bCasings=True
     MaxClutter=150
     bCorpseShots=True
     bBleedTrail=True
     BleedClot=14.000000
     CorpsePulpHits=10
     bScreenBlood=True
     ScreenBloodReach=260.000000
     CorpseKick=8000.000000
     Begin Object Class=KarmaParamsSkel Name=CorpseRagdoll
         KConvulseSpacing=(Max=2.200000)
         KLinearDamping=0.150000
         KAngularDamping=0.050000
         KBuoyancy=1.000000
         KStartEnabled=True
         KVelDropBelowThreshold=50.000000
         bHighDetailOnly=False
         bClientOnly=True
         bKDoubleTickRate=True
         bKStayUpright=False
         bKAllowRotate=False
         bDestroyOnWorldPenetrate=False
         bDoSafetime=True
         KFriction=0.600000
         KImpactThreshold=500.000000
     End Object
     CorpseParams=KarmaParamsSkel'AdventMod.ModGore.CorpseRagdoll'
     bImpacts=True
     MaxHoles=60
     bBlood=True
     MaxDecals=80
     SprayReach=260.000000
     DecalScale=1.600000
}
