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
// and only characters (not vehicles or turrets) bleed.
//=============================================================================
class ModGore extends Info
	config(AdventMod);

var config bool bBlood;            // the Gameplay page's Blood switch
var config int MaxDecals;
var config float SprayReach;       // how far behind a victim a wall still catches the spray
var config float DecalScale;       // all marks' size

var Material Splats[4], Sprays[2], Pool;   // the textures, referenced so the package keeps them
var array<ModBloodDecal> Decals;
var array<Pawn> Dying;             // bodies waiting for their pool
var array<float> DyingTime;
var int Hits;

event PostBeginPlay()
{
	local ModGoreRules R;
	local int i;

	Super.PostBeginPlay();
	if (Level.Game == None)
		return;
	// clamped, not tiled: a projector wider than its picture would repeat it
	for (i = 0; i < 4; i++)
		ClampTex(Splats[i]);
	ClampTex(Sprays[0]);
	ClampTex(Sprays[1]);
	ClampTex(Pool);
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
	return true;
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
		Mark(Sprays[Rand(2)], HitL, HitN, Dir, Size * (0.8 + 0.6 * VSize(HitL - HitLocation) / SprayReach));
	// drips under the hit
	if (FRand() < 0.85 && Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) != None)
		Mark(Splats[Rand(4)], HitL + VRand() * vect(1,1,0) * 30, HitN, vect(0,0,0), Size * 0.6);
	// a pool under a fresh body
	if (Victim.Health <= 0 || Damage >= Victim.Health)
		AddDying(Victim);
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

event Tick(float DeltaTime)
{
	local int i;
	local vector HitL, HitN, Spot;
	local ModBloodDecal D;

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
				D = Mark(Pool, HitL, HitN, vect(0,0,0), DecalScale * 0.6);
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
     bBlood=True
     MaxDecals=80
     SprayReach=260.000000
     DecalScale=1.600000
}
