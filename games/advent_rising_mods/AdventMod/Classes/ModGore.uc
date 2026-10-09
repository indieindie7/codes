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
var config bool bKarmaFreezeFix;   // native: the engine's own ragdoll freeze sets PHYS_None, not PHYS_Falling (karmafix.c). OFF: tested 2026-10-08, the frozen body loses its ragdoll pose and stands up; the script hold (ModReact) keeps bodies lying
var config bool bHoundRagdolls;    // off: hounds crash the game going limp (levels 03 b and c), cause not found yet. (A config array of skeleton names came up empty in game, and the hounds went limp.)
var KarmaParamsSkel CorpseParams;  // ragdoll settings for corpses the level gave none (a subobject below, so saves can refer to it)
// the solver's settings for every ragdoll we start (KSetSimParams; 0 = the engine's own):
// smaller steps and softer contacts settle bodies with less jitter and sinking
var config float RagdollMaxTimestep, RagdollContactSoftness;
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
var ModSever Severer;              // decapitation and limb loss
var ModMelee Melee;                // melee weapons (the energy blade)
var ModGibAtlas Cards;              // settled gibs turned into floor snapshots
var ModArmor Armor;                // destructible plates on the Seeker soldiers                // flinch, stagger and death ragdolls (fed by ModGoreRules too)
var config bool bBloodCoats;       // blood lands on the characters near a hit: they look bloody
var config int MaxCoats;
var array<ModBloodCoat> Coats;
var Material CoatTex[3], AlienCoatTex[3];
var config bool bDirt;             // dirt and battle damage: grime where the player goes, cracks and craters where things explode
var config int MaxDirt;
var config int MaxRubble;          // loose pieces thrown out by explosions (ModRubble); 0: none
var array<ModRubble> Rubble;
var config float DirtEvery;        // seconds between grime patches around the player
var array<ModBloodDecal> Dirt;
var Material GrimeTex[2], CrackTex[2], RubbleTex, CraterTex;
var float DirtTimer;
var config bool bWounds;           // a shot leaves a wound on the body, where it hit
var config int MaxWounds, WoundsPerBody;
var config bool bBleedTrail;       // the badly wounded leave drops where they go
var config float BleedClot;        // seconds a wound takes to stop dripping
var config int CorpsePulpHits;     // shots into one corpse that pulp it into pieces (0: never)
var config bool bScreenBlood;      // close kills splash the screen
var config float ScreenBloodReach;
var config float BulletScale;      // shots' trails and meshes drawn at this size (the game's are huge)
var array<byte> ShotScaled;        // per Shots entry: its trail has been scaled
var array<float> ShotBlast;        // per Shots entry: its blast radius (0: it doesn't explode)
var array<int> ShotDamage;
var config bool bBlastShake;       // explosions near the player shake the view and the gamepad
var config float BlastShake;       // how hard (1 = as tuned)
var float LastShake;

var Material Splats[4], Sprays[2], Pool, Scorches[3], CasingTex;   // the textures, referenced so the package keeps them
var Material RemainsTex[2];
var Material AlienSplats[4], AlienSprays[2], AlienPool, AlienRemains[2];
var Material PoolFrames[12], AlienPoolFrames[12];   // a pool spreading: frames of an offline fluid run (tools/make_blood_pool.py)
var Material PoolLive[8];                            // live pools: placeholders the d3d8 layer simulates (tools/make_blood_live.py)
var ModBloodDecal LiveOwner[8];
var Material RunLive[8];                             // wall runs: placeholders the d3d8 layer simulates (tools/make_blood_runs.py)
var ModBloodDecal RunOwner[8];
var int NextRun;
var config bool bWallRuns;                           // blood landing on a wall runs down it
var config float RunSize;                            // a run region's width (world units)
var config float RunChance;                          // the share of wall sprays that run
var int NextLive;
var config bool bLivePools;
var config float LivePour, LivePourSecs;            // how much blood a body gives its pool, over how long
var config float RegionSize;                        // a live sheet covers a floor square this wide: every body in it pours into the same sheet (pools run together, prints everywhere in it)
// bloody footprints: whoever walks through blood (a live pool, a fresh floor mark, a body) leaves prints for FootprintSteps steps
var Material FootTex[3], AlienFootTex[3];           // fresh, fading, nearly gone (the right boot)
var Material FootTexL[3], AlienFootTexL[3];         // the left boot, mirrored
var Material Burns[4];                               // a plasma burn cooling: white-hot, orange, ember, soot
var config float BurnChance;                        // the share of wall hits that burn (glow and cool) rather than scorch
var Material WallHoles[6];                           // bullet holes dug into walls: the layer's parallax rule reads their darkness as depth
var config bool bWallHoles;                         // walls take holes (parallax) and lose chips where shots land
var config int ChipCount;                           // chips of wall knocked out per hit (tiny rubble), 0: none
// wall destruction step 2: hits that cluster on a wall knock the plaster away (a breach: a deep
// parallax hole with rebar), bigger again as more land; a blast breaches the wall it reaches
var Material WallBreaches[3];
var config bool bBreaches;
var config int BreachHits, BreachHits2;              // holes within BreachReach that open a breach, and grow it
var config float BreachReach;
var array<vector> HoleAt, HoleNorm;
var array<float> HoleTime;
struct BreachState
{
	var vector Spot, N;
	var int Level;
};
var array<BreachState> Breaches;
var class<Emitter> RockFx, DustFallFx;
var Material DripTex, AlienDripTex;                 // drip streaks a coat pans down after a hit
var config bool bFootprints;
var config int FootprintSteps;      // prints a walker leaves after stepping in blood, fading (8-12 reads well)
var config float FootStride;        // units between prints at walking pace (longer strides when running)
var config float FootGap;           // a foot's offset to the side of the walker's line
var config int MaxFootprints;       // prints at once (they come out of the MaxDecals budget too)
var config float FootFresh;         // seconds a floor splat or pool stays wet enough to step in
struct WetFeet
{
	var Pawn P;
	var int Kind;          // 0 red, 1 purple (the live pools' convention: ModBloodDecal.Stamps passes it)
	var int Left;          // prints still to leave
	var vector LastSpot;
	var bool bRight;
};
var array<WetFeet> Wet;
var array<ModBloodDecal> Prints;    // the footprints down, oldest first (MaxFootprints)
var bool bPrinting;                 // Mark is laying a footprint: not floor blood to step in
// fresh blood on the floor that wets feet: splats and pools as Mark lays them (live regions tell
// ModBloodDecal.Stamps themselves, bodies are the Corpses list)
struct FloorBlood
{
	var vector Spot;
	var float Radius;      // world units
	var int Kind;          // BloodKind: 1 red, 2 purple
	var float Born;
};
var array<FloorBlood> FloorMarks;
var float FeetScan;
// falling drops (ModBloodDrop, a pool of actors reused): from the bleeding points of the wounded
// and the dead, off the lower edge of fresh blood on walls, from goo strings that snap and from
// blood on ceilings; each lands as a tiny splat or into the live pool under it
var config bool bDrips;
var config float DripRate;          // how often drops fall (1 = as tuned, 2 = twice as often)
var config int MaxDrops;            // drops in flight at once (at most 64)
var config float DropSize;          // the sprite's scale (the texture is 32x64)
var config float DripReach;         // drops only this near the player (nobody sees the rest)
var config float DropPour;          // blood a drop adds to a live pool it lands in
var array<ModBloodDrop> Drops;
struct DripSrc
{
	var vector Spot;       // where the drops leave from
	var int Kind;          // BloodKind
	var float Next, EndT; // the next drop; the last (Level.TimeSeconds)
	var float GapMin, GapMax;
	var float Size;        // the splats it leaves
};
var array<DripSrc> DripSrcs;        // at most 24 (the oldest goes)
var array<vector> DropSplats;       // the last drop splats (one per spot: a ceiling's drip lands in one place)
var int DropsThrown, DropsLanded;   // DROPLIST
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
struct Wound
{
	var Pawn P;
	var ModStump M;
	var bool bDied;        // the body was dead with it: gone when the game reuses the pawn
};
var array<Wound> Wounds;
var ModStump LastWound;            // the wound AddWound just made (None: none)
// blood streaks down the bodies (the d3d8 layer's streaks.hpp, streaks=1 in U2Shaders.ini):
// each wound, cut and fresh hit is a bleeding point the layer runs thin rivulets down from,
// straight down in world space whatever the pose, drying with age (SendStreaks)
struct StreakSrc
{
	var Pawn P;
	var Actor M;           // a wound's or cut's stump (it rides its bone), or None: Bone + Rel
	var name Bone;
	var vector Rel;        // the point in the bone's own axes
	var int Kind;          // 1 red, 2 purple (BloodKind)
	var float Born, Str;   // when it began; how hard it bleeds (0.2-1.5)
	var int Seed;          // its rivulets' pattern
	var bool bDied;        // the body was dead with it: gone when the game reuses the pawn
	var float NextDrip;    // a dead body's bleeding point: when it lets the next drop fall (bDrips)
};
var array<StreakSrc> Streaks;
var config bool bBodyStreaks;
var config float StreakLife;       // seconds a bleeding point lasts (it fades out over the last 5)
var config int StreaksPerBody;
var int StreaksSent;               // the slots the layer has been told about
// an opened artery: some wounds spurt in heartbeats for a few seconds, painting what is near
struct Spurt
{
	var Pawn P;
	var ModStump M;
	var int Kind;
	var float T, Next, Life;
};
var array<Spurt> Spurts;
var config float SpurtChance;        // the share of wounds that spurt
var config float SpurtBeat;          // seconds between pulses
var config float SpurtReach;         // how far a pulse carries
// goo strings (the d3d8 layer's strings.hpp, strings=1 in U2Shaders.ini): sticky strands stretched
// between body parts that just came apart (a severed limb and its stump, gib pieces of one body).
// They pull a little on the flying pieces, snap once stretched past their limit (or when old),
// and the layer plays the snap: two halves hanging from the ends, shortening and dripping.
struct GooString
{
	var Actor A, B;        // the ends: actors (gib pieces), or A None: P's bone
	var Pawn P;
	var name Bone;
	var float RA, RB;      // an actor end is pulled in from its centre toward the other end by this
	var int Kind, Slot, Seed;
	var float Thick, Rest, Limit, Born, Life, SnapAt;   // SnapAt < 0: whole
	var float Hold;                                    // seconds it can't break by stretching (but a hard over-stretch)
	var bool bDied;        // P was dead with it: gone when the game reuses the pawn
};
var array<GooString> Goo;
var array<ModGib> GooMade;        // SpawnGibs: the pieces it just threw (for GooGibs)
var int GooSlots[12];              // 1: the layer's slot is taken
var config bool bGooStrings;
var config float GooRestMin, GooRestMax;        // a string's own length (world units, scaled with the body)
var config float GooStretchMin, GooStretchMax;  // it snaps past rest length times this (random between)
var config float GooLifeMin, GooLifeMax;        // ...or after this many seconds
var config float GooThick;                      // its radius (world units)
var config float GooDangle;                     // seconds the snapped halves are drawn before the slot is freed
var config float GooPull;                       // how hard a stretched string pulls on a flying piece
var config float GooHoldMin, GooHoldMax;        // seconds a fresh string holds before it may snap
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
	{
		ClampTex(CoatTex[i]);
		ClampTex(AlienCoatTex[i]);
	}
	for (i = 0; i < 2; i++)
	{
		ClampTex(GrimeTex[i]);
		ClampTex(CrackTex[i]);
	}
	ClampTex(RubbleTex);
	ClampTex(CraterTex);
	for (i = 0; i < 3; i++)
		ClampTex(Scorches[i]);
	// (an unclamped projector texture draws its whole square darkened, not just the mark)
	for (i = 0; i < 6; i++)
		ClampTex(WallHoles[i]);
	for (i = 0; i < 3; i++)
		ClampTex(WallBreaches[i]);
	for (i = 0; i < 4; i++)
		ClampTex(Burns[i]);
	for (i = 0; i < 3; i++)
	{
		ClampTex(FootTex[i]);
		ClampTex(AlienFootTex[i]);
		ClampTex(FootTexL[i]);
		ClampTex(AlienFootTexL[i]);
	}
	Cards = Spawn(class'ModGibAtlas');
	if (Cards != None)
		Cards.Gore = self;
	React = Spawn(class'ModReact');
	React.Gore = self;
	Severer = Spawn(class'ModSever');
	Severer.Gore = self;
	Melee = Spawn(class'ModMelee');
	Armor = Spawn(class'ModArmor');
	Armor.Gore = self;
	Melee.Gore = self;
	R = Spawn(class'ModGoreRules');
	R.Gore = self;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = R;
	else
		Level.Game.GameRulesModifiers.AddGameRules(R);
	class'ModSettings'.static.Note("gore: watching hits");
	if (bKarmaFreezeFix)
		class'ModSettings'.static.NativeCall("KarmaFreezeFix");   // frozen ragdolls stay put instead of falling out of the world
	if (bBodyStreaks)
		class'ModSettings'.static.NativeCall("Blood:streakclear");   // the last level's are gone
	if (bGooStrings)
		class'ModSettings'.static.NativeCall("Blood:stringclear");
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

// a pool takes the next live slot (the pool that had it keeps a baked frame)
function GoLive(ModBloodDecal D, float Size, int Kind)
{
	local int K;

	K = NextLive;
	NextLive = (NextLive + 1) % 8;
	if (LiveOwner[K] != None && !LiveOwner[K].bDeleteMe)
		LiveOwner[K].EndLive();
	LiveOwner[K] = D;
	D.Gore = self;
	D.GoLive(K, PoolLive[K], Size, LivePour, LivePourSecs, Kind);
}

// blood landing on a wall runs down it: into the run region already there, or a new one with
// the spot near its top (the slot whose region is farthest from the player is reused)
function WallRun(vector Spot, vector N, int Kind, float Amount)
{
	local int i, K;
	local float U, W, Far, D;
	local vector Down, Across, Center;
	local ModBloodDecal R;

	if (!bWallRuns || Abs(N.Z) > 0.5 || FRand() > RunChance)
		return;
	for (i = 0; i < 8; i++)
		if (RunOwner[i] != None && !RunOwner[i].bDeleteMe && RunOwner[i].RunLocal(Spot, U, W))
		{
			class'ModSettings'.static.NativeCall("Blood:drip " $ RunOwner[i].RunSlot $ " " $ U $ " " $ W $ " " $ Amount $ " " $ Kind);
			return;
		}
	// a new region: the slot that is free, or whose region is farthest from the player
	K = -1;
	for (i = 0; i < 8 && K < 0; i++)
		if (RunOwner[i] == None || RunOwner[i].bDeleteMe)
			K = i;
	if (K < 0 && Level.GetLocalPlayerController() != None && Level.GetLocalPlayerController().Pawn != None)
		for (i = 0; i < 8; i++)
		{
			D = VSize(RunOwner[i].Location - Level.GetLocalPlayerController().Pawn.Location);
			if (D > Far)
			{
				Far = D;
				K = i;
			}
		}
	if (K < 0)
	{
		K = NextRun;
		NextRun = (NextRun + 1) % 8;
	}
	if (RunOwner[K] != None && !RunOwner[K].bDeleteMe)
		RunOwner[K].Destroy();
	// down along the wall, and the region's middle below the spot (blood has the room to run)
	Down = vect(0,0,-1) - N * (vect(0,0,-1) Dot N);
	Down = Normal(Down);
	Across = Normal(N Cross Down);
	Center = Spot + Down * RunSize * 0.3;
	R = Spawn(class'ModBloodDecal',,, Center + N * 16);
	if (R == None)
		return;
	R.Gore = self;
	R.Place(RunLive[K], Center, N, Across, RunSize / 64.0);
	R.GoRun(K, RunLive[K], RunSize, Kind);
	RunOwner[K] = R;
	if (R.RunLocal(Spot, U, W))
		class'ModSettings'.static.NativeCall("Blood:drip " $ K $ " " $ U $ " " $ W $ " " $ Amount $ " " $ Kind);
}

// a body's blood goes into the live region under it; if no region covers the spot, a new one
// is laid there (a free slot, else the region farthest from the player, whose blood is gone)
function bool PourInto(vector Spot, vector N, int Kind)
{
	local int i, K;
	local float D, Far;
	local ModBloodDecal R;
	local Pawn Viewer;

	for (i = 0; i < 8; i++)
		if (LiveOwner[i] != None && !LiveOwner[i].bDeleteMe && LiveOwner[i].LiveSlot >= 0 && LiveOwner[i].PourAt(Spot, LivePour, LivePourSecs, Kind))
			return true;
	K = -1;
	for (i = 0; i < 8; i++)
		if (LiveOwner[i] == None || LiveOwner[i].bDeleteMe || LiveOwner[i].LiveSlot < 0)
		{
			K = i;
			break;
		}
	if (K < 0)
	{
		Viewer = Level.GetLocalPlayerController().Pawn;
		Far = -1;
		for (i = 0; i < 8; i++)
		{
			if (Viewer != None)
				D = VSize(LiveOwner[i].Location - Viewer.Location);
			else
				D = float(i);
			if (D > Far)
			{
				Far = D;
				K = i;
			}
		}
		LiveOwner[K].Destroy();
	}
	R = Mark(PoolLive[K], Spot, N, vect(0,0,0), RegionSize / 128.0);
	if (R == None)
		return false;
	// a region is not a splatter: it lives outside the decal list, or the cap on marks would
	// evict it within seconds and the next body would lay a fresh region beside it
	if (Decals.Length > 0 && Decals[Decals.Length - 1] == R)
		Decals.Remove(Decals.Length - 1, 1);
	LiveOwner[K] = R;
	R.Gore = self;
	R.LifeSpan = 900;
	R.GoLive(K, PoolLive[K], RegionSize, LivePour, LivePourSecs, Kind);
	return true;
}

// the live region (if any) under a spot: gibs and rubble tell it where they lie
function ModBloodDecal RegionAt(vector Spot)
{
	local int i;
	local float U, W;

	for (i = 0; i < 8; i++)
		if (LiveOwner[i] != None && !LiveOwner[i].bDeleteMe && LiveOwner[i].LiveSlot >= 0 && LiveOwner[i].Local(Spot, U, W))
			return LiveOwner[i];
	return None;
}

// a walker has stepped in blood: FootprintSteps prints from here, fading. Kind: 0 red, 1 purple
// (the live pools' convention)
function BloodyFeet(Pawn P, int Kind)
{
	local int i;
	local WetFeet F;

	if (!bFootprints || !bBlood || P == None)
		return;
	for (i = 0; i < Wet.Length; i++)
		if (Wet[i].P == P)
		{
			Wet[i].Left = FootprintSteps;
			Wet[i].Kind = Kind;
			return;
		}
	if (Wet.Length >= 16)
		return;
	F.P = P;
	F.Kind = Kind;
	F.Left = FootprintSteps;
	F.LastSpot = P.Location;
	Wet[Wet.Length] = F;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: bloody feet on " $ P $ " (kind " $ Kind $ ", " $ FootprintSteps $ " steps)");
}

function Material FootTexture(int Kind, int Step, bool bRight)
{
	local int Strength;

	Strength = Clamp(Step * 3 / Max(FootprintSteps, 1), 0, 2);
	if (Kind == 1)
	{
		if (bRight)
			return AlienFootTex[Strength];
		return AlienFootTexL[Strength];
	}
	if (bRight)
		return FootTex[Strength];
	return FootTexL[Strength];
}

// fresh blood on the floor (Mark: splats, sprays, pools): feet that pass through it get bloody.
// Marks close together are one (the bigger radius, the newer time)
function AddFloorBlood(vector Spot, float Radius, int Kind)
{
	local int i;
	local FloorBlood F;

	if (!bFootprints || Kind == 0)
		return;
	for (i = 0; i < FloorMarks.Length; i++)
		if (VSize(FloorMarks[i].Spot - Spot) < 12)
		{
			FloorMarks[i].Radius = FMax(FloorMarks[i].Radius, Radius);
			FloorMarks[i].Born = Level.TimeSeconds;
			FloorMarks[i].Kind = Kind;
			return;
		}
	if (FloorMarks.Length >= 48)
		FloorMarks.Remove(0, 1);
	F.Spot = Spot;
	F.Radius = Radius;
	F.Kind = Kind;
	F.Born = Level.TimeSeconds;
	FloorMarks[FloorMarks.Length] = F;
}

// which blood a mark's texture is: 1 red, 2 purple, 0 not a splat, spray or pool (footprints,
// live placeholders, dirt)
function int MarkKind(Material T)
{
	local int i;

	if (T == None)
		return 0;
	if (T == Pool)
		return 1;
	if (T == AlienPool)
		return 2;
	for (i = 0; i < 4; i++)
	{
		if (T == Splats[i])
			return 1;
		if (T == AlienSplats[i])
			return 2;
	}
	for (i = 0; i < 2; i++)
	{
		if (T == Sprays[i])
			return 1;
		if (T == AlienSprays[i])
			return 2;
	}
	for (i = 0; i < 12; i++)
	{
		if (T == PoolFrames[i])
			return 1;
		if (T == AlienPoolFrames[i])
			return 2;
	}
	return 0;
}

// a few times a second: walkers (the player and everyone else near) whose feet are in fresh floor
// blood or beside a bleeding body get bloody feet; floor blood older than FootFresh has dried
function WetFeetScan()
{
	local Pawn P, Viewer;
	local PlayerController C;
	local vector Feet, D;
	local int i;
	local bool bFound;

	for (i = FloorMarks.Length - 1; i >= 0; i--)
		if (Level.TimeSeconds - FloorMarks[i].Born > FootFresh)
			FloorMarks.Remove(i, 1);
	C = Level.GetLocalPlayerController();
	if (C != None)
		Viewer = C.Pawn;
	ForEach DynamicActors(class'Pawn', P)
	{
		if (P.Health <= 0 || P.bHidden || P.Physics != PHYS_Walking || VSize(P.Velocity) < 20 || P.IsA('Vehicle') || P.IsA('Turret'))
			continue;
		if (Viewer != None && VSize(P.Location - Viewer.Location) > 2500)
			continue;
		Feet = P.Location - vect(0,0,1) * P.CollisionHeight;
		bFound = false;
		for (i = 0; i < FloorMarks.Length; i++)
		{
			D = FloorMarks[i].Spot - Feet;
			if (Abs(D.Z) < 30 && VSize(D * vect(1,1,0)) < FloorMarks[i].Radius * 0.8 + 6)
			{
				BloodyFeet(P, int(FloorMarks[i].Kind == 2));
				bFound = true;
				break;
			}
		}
		if (bFound)
			continue;
		// a body lying there: it has bled all round it
		for (i = 0; i < Corpses.Length; i++)
		{
			if (Corpses[i] == None || Corpses[i] == P || Corpses[i].bDeleteMe || Corpses[i].bHidden || CorpseKind[i] == 0)
				continue;
			D = Corpses[i].Location - P.Location;
			if (Abs(D.Z) < 80 && VSize(D * vect(1,1,0)) < Corpses[i].CollisionRadius + P.CollisionRadius + 10)
			{
				BloodyFeet(P, int(CorpseKind[i] == 2));
				break;
			}
		}
	}
}

// a footprint: a mark like the others (out of MaxDecals), and at most MaxFootprints of them, so a
// squad tramping through a pool doesn't sweep the rest of the blood away
function PrintAt(Material T, vector Spot, vector N, vector Dir, float Size)
{
	local ModBloodDecal D;

	while (Prints.Length > 0 && (Prints.Length >= MaxFootprints || Prints[0] == None || Prints[0].bDeleteMe))
	{
		if (Prints[0] != None && !Prints[0].bDeleteMe)
			Forget(Prints[0]);
		Prints.Remove(0, 1);
	}
	bPrinting = true;
	D = Mark(T, Spot, N, Dir, Size);
	bPrinting = false;
	if (D != None)
		Prints[Prints.Length] = D;
}

// a mark taken out of the decal list and gone
function Forget(ModBloodDecal D)
{
	local int i;

	for (i = Decals.Length - 1; i >= 0; i--)
		if (Decals[i] == D)
		{
			Decals.Remove(i, 1);
			break;
		}
	D.Destroy();
}

function Material DripMaterial(int Kind)
{
	if (Kind == 2)
		return AlienDripTex;
	return DripTex;
}

// the prints: one a step, a step being FootStride units of travel at walking pace and longer when
// running (up to 1.9x), under alternate feet (FootGap to the side), pointing the way, fading
// over FootprintSteps steps. Steps are counted by distance: the game has no footstep notify
// script can hear, and distance holds for every walker alike.
function WalkPrints()
{
	local int i, Step;
	local Pawn P;
	local vector Side, Foot, HitL, HitN, Dir;
	local float Speed, Stride;

	for (i = Wet.Length - 1; i >= 0; i--)
	{
		P = Wet[i].P;
		if (P == None || P.bDeleteMe || P.Health <= 0 || P.bHidden || Wet[i].Left <= 0)
		{
			Wet.Remove(i, 1);
			continue;
		}
		Speed = VSize(P.Velocity * vect(1,1,0));
		// in the air (a jump, a fall): no prints, and the step starts again on landing
		if (P.Physics != PHYS_Walking)
		{
			Wet[i].LastSpot = P.Location;
			continue;
		}
		Stride = FootStride * FClamp(Speed / FMax(P.GroundSpeed * P.WalkingPct, 80), 1.0, 1.9);
		if (VSize((P.Location - Wet[i].LastSpot) * vect(1,1,0)) < Stride || Speed < 10)
			continue;
		Dir = Normal(P.Velocity * vect(1,1,0));
		Side = Dir Cross vect(0,0,1);
		if (Wet[i].bRight)
			Foot = P.Location + Side * FootGap;
		else
			Foot = P.Location - Side * FootGap;
		Step = FootprintSteps - Wet[i].Left;
		if (Trace(HitL, HitN, Foot - vect(0,0,1) * (P.CollisionHeight + 60), Foot, false) != None && HitN.Z > 0.6)
			PrintAt(FootTexture(Wet[i].Kind, Step, Wet[i].bRight), HitL, HitN, Dir,
				DecalScale * 0.3 * (1.0 - 0.15 * Step / Max(FootprintSteps, 1)));
		Wet[i].Left--;
		Wet[i].bRight = !Wet[i].bRight;
		Wet[i].LastSpot = P.Location;
	}
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
	// a shot that met a plate (ModArmor.Classify, ARMOUR.md) sparks and doesn't bleed (a kill
	// goes on below: the death, its gibs and its pool are the body's, not the plate's)
	if (Armor != None && Armor.bArmourSparks && Armor.LastClass == 2)
	{
		Armor.Sparks(HitLocation, Dir);
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: the hit on " $ Victim $ " met armour: sparks, no blood");
		if (Victim.Health > 0 && Damage < Victim.Health)
			return;
	}
	if (VSize(HitLocation - Victim.Location) > Victim.CollisionRadius * 3)
		HitLocation = Victim.Location;
	// the bigger the hit, the bigger the mark (a pistol ~10-20, a launcher ~100)
	Size = DecalScale * FClamp(0.35 + Damage / 120.0, 0.35, 1.0);

	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: dir " $ Dir $ " from " $ HitLocation $ " texture " $ Sprays[0] $ " floor " $ Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) $ " at " $ HitL);
	// the spray behind the victim, along the shot (a little downward: blood falls)
	Dir = Normal(Dir + vect(0,0,-0.25));
	if (Trace(HitL, HitN, HitLocation + Dir * SprayReach, HitLocation + Dir * Victim.CollisionRadius, false) != None)
	{
		Mark(SprayTex(Victim), HitL, HitN, Dir, Size * (0.8 + 0.6 * VSize(HitL - HitLocation) / SprayReach));
		// on a wall the spray runs down it (WallRun: the d3d8 layer's running drops), and drips
		// off its lower edge when there is air under it
		if (Abs(HitN.Z) < 0.5)
		{
			WallRun(HitL, HitN, int(BloodKind(Victim) == 2), FClamp(Damage / 40.0, 0.35, 1.6));
			WallDrip(HitL, HitN, WallBelow(Size), BloodKind(Victim), 4 + 3 * FRand());
		}
	}
	// drips under the hit
	if (FRand() < 0.85 && Trace(HitL, HitN, HitLocation - vect(0,0,400), HitLocation, false) != None)
		Mark(SplatTex(Victim), HitL + VRand() * vect(1,1,0) * 30, HitN, vect(0,0,0), Size * 0.6);
	if (bBleedTrail && Victim.Health > Damage && !Victim.IsHumanControlled())
		Bleed(Victim, Damage);
	if (bBloodCoats)
		Spatter(Victim, HitLocation, 0.2 + Damage / 150.0, 130);
	LastWound = None;
	if (bWounds && Damage >= 8 && !Victim.IsHumanControlled())
		AddWound(Victim, HitLocation);
	// blood runs down the body from the hit (from the wound, if it got one)
	AddStreak(Victim, HitLocation, LastWound, FClamp(Damage / 40.0, 0.3, 1.5));
	// a pool under a fresh body
	if (Victim.Health <= 0 || Damage >= Victim.Health)
	{
		ScreenSplash(Victim.Location, BloodKind(Victim), 0.3 + FClamp(Damage / 150.0, 0, 0.4));
		if (Melee != None && class'ModTargeting'.static.IsHostile(Victim) && FRand() < Melee.BladeDropChance)
			Melee.Drop(Victim.Location);
		AddDying(Victim);
		// (a blade's kill cuts: it doesn't blow the body apart)
		if (bGibs && !(Severer != None && Severer.bForce) && WantsGib(Victim, Damage, DamageType))
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
	if (bBloodCoats)
		Spatter(P, P.Location, 1.2, 280);
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
	GooMade.Length = 0;
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
		GooMade[GooMade.Length] = G;
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ n $ " gib parts at " $ Feet);
	if (n == 0)
		return 0;
	GooGibs(Kind, K);            // goo strings between neighbouring pieces
	GooMade.Length = 0;
	// a burst of blood all round, and the body gone
	for (i = 0; i < 6; i++)
	{
		V = Normal(VRand() + Dir * 0.6 + vect(0,0,-0.4));
		if (Trace(HitL, HitN, Mid + V * SprayReach * 1.4, Mid, false) != None)
		{
			Mark(KindSpray(Kind), HitL, HitN, V, DecalScale * (0.7 + 0.5 * FRand()));
			if (Abs(HitN.Z) < 0.5)
			{
				WallRun(HitL, HitN, int(Kind == 2), 1.2);
				if (FRand() < 0.5)
					WallDrip(HitL, HitN, WallBelow(DecalScale), Kind, 5 + 3 * FRand());
			}
		}
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
			if (ShotBlast[i] > 0)
				Blast(ShotLoc[i], ShotBlast[i], ShotDamage[i]);
			ShotBlast.Remove(i, 1);
			ShotDamage.Remove(i, 1);
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
		ShotBlast[ShotBlast.Length] = P.DamageInfo.fDamageRadius;
		ShotDamage[ShotDamage.Length] = P.DamageInfo.iDamage;
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
		AddStreak(P, Spot, None, 0.6);
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
	SolverSettings(A);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: " $ A $ " went limp (" $ Skel $ "), physics " $ A.Physics);
}

// the solver's own knobs for one ragdoll (physics-plan.md, step 1)
function SolverSettings(Actor A)
{
	local KSimParams S;

	if (A.Physics != PHYS_KarmaRagdoll)
		return;
	A.KGetSimParams(S);
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: solver for " $ A $ ": step " $ S.MaxTimestep $ " softness " $ S.ContactSoftness $ " penetration " $ S.PenetrationOffset $ "/" $ S.PenetrationScale $ "/" $ S.MaxPenetration $ " epsilon " $ S.Epsilon $ " gamma " $ S.GammaPerSec);
	if (RagdollMaxTimestep > 0)
		S.MaxTimestep = RagdollMaxTimestep;
	if (RagdollContactSoftness > 0)
		S.ContactSoftness = RagdollContactSoftness;
	if (RagdollMaxTimestep > 0 || RagdollContactSoftness > 0)
		A.KSetSimParams(S);
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

// An explosion (a shot with a blast radius went off): near the player the view shakes,
// harder the closer and the bigger, through the game's own camera shake (which its weapon
// explosions leave unused), and the gamepad rumbles.
function Blast(vector Loc, float Radius, int Damage)
{
	local EonPlayerController C;
	local float D, Reach, K, Amp;

	if (bDirt)
		BlastMarks(Loc, Radius);
	if (!bBlastShake)
		return;
	C = EonPlayerController(Level.GetLocalPlayerController());
	if (C == None || C.Pawn == None || C.Camera == None)
		return;
	Reach = FMax(Radius * 4, 1200);
	D = VSize(C.Pawn.Location - Loc);
	if (D >= Reach)
		return;
	K = 1 - D / Reach;
	Amp = BlastShake * (220 + 480 * FClamp(Damage / 150.0, 0, 1)) * K * K;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: blast (radius " $ int(Radius) $ ", damage " $ Damage $ ") " $ int(D) $ " from the player: shake " $ int(Amp));
	// (blasts in a burst don't stack into a seizure)
	if (Amp < 25 || Level.TimeSeconds - LastShake < 0.12)
		return;
	LastShake = Level.TimeSeconds;
	C.Camera.Shake(Amp, Amp, Amp, D / 14490.67, 0.3 + 0.6 * K);
	if (K > 0.6)
		Level.GetRumbleProperties().PlayFeedbackEffect(EERE_ExplosionLarge);
	else if (K > 0.3)
		Level.GetRumbleProperties().PlayFeedbackEffect(EERE_ExplosionMedium);
	else
		Level.GetRumbleProperties().PlayFeedbackEffect(EERE_ExplosionSmall);
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
	// marks only where the player can see them: a fight across the level makes ten impacts a
	// second, which would churn the caps and sweep the marks in front of the player away
	if (Level.GetLocalPlayerController() != None && Level.GetLocalPlayerController().Pawn != None
		&& VSize(HitL - Level.GetLocalPlayerController().Pawn.Location) > 1500)
		return;
	if (bImpacts && A != None && (A == Level || A.bWorldGeometry || A.bStatic) && Pawn(A) == None)
	{
		// a wall or ceiling: the shot digs a hole (the layer's parallax rule makes it read as
		// sunk in) and knocks chips out; floors keep the flat scorch
		if (bWallHoles && HitN.Z < 0.5)
		{
			AddHole(WallHoles[Rand(6)], HitL, HitN, DecalScale * (0.2 + 0.1 * FRand()));
			Chips(HitL, HitN);
			if (bBreaches)
				WallHit(HitL, HitN);
		}
		if (FRand() < BurnChance)
			Burn(HitL, HitN, DecalScale * (0.34 + 0.12 * FRand()));
		else if (!bWallHoles || HitN.Z >= 0.5 || FRand() < 0.5)
			AddHole(Scorches[Rand(3)], HitL, HitN, DecalScale * (0.3 + 0.12 * FRand()));
	}
}

// a hole on a wall: where enough land close together the plaster goes (a breach), and a
// breach grows when more land on it
function WallHit(vector Spot, vector N)
{
	local int i, Count, b;
	local vector Mid;

	// recent holes only (three minutes), at most 80
	for (i = HoleAt.Length - 1; i >= 0; i--)
		if (Level.TimeSeconds - HoleTime[i] > 180)
		{
			HoleAt.Remove(i, 1);
			HoleNorm.Remove(i, 1);
			HoleTime.Remove(i, 1);
		}
	if (HoleAt.Length >= 80)
	{
		HoleAt.Remove(0, 1);
		HoleNorm.Remove(0, 1);
		HoleTime.Remove(0, 1);
	}
	HoleAt[HoleAt.Length] = Spot;
	HoleNorm[HoleNorm.Length] = N;
	HoleTime[HoleTime.Length] = Level.TimeSeconds;
	for (i = 0; i < HoleAt.Length; i++)
		if (VSize(HoleAt[i] - Spot) < BreachReach && (HoleNorm[i] Dot N) > 0.85)
		{
			Count++;
			Mid += HoleAt[i];
		}
	if (Count < BreachHits)
		return;
	Mid /= Count;
	b = -1;
	for (i = 0; i < Breaches.Length; i++)
		if (VSize(Breaches[i].Spot - Mid) < BreachReach * 1.3 && (Breaches[i].N Dot N) > 0.85)
			b = i;
	if (b < 0)
		Breach(Mid, N, 1);
	else if (Breaches[b].Level == 1 && Count >= BreachHits2)
	{
		Breaches[b].Level = 2;
		Breach(Breaches[b].Spot, N, 2);
	}
}

// the plaster knocked away: a deep parallax hole (bigger at level 2), a burst of chips and dust
function Breach(vector Spot, vector N, int Lvl)
{
	local int i;
	local BreachState B;
	local Emitter E;

	AddDirt(WallBreaches[Rand(3)], Spot, N, DecalScale * (Lvl >= 2 ? 0.68 : 0.42) * (0.9 + 0.2 * FRand()), 900);
	for (i = 0; i < 3 * Lvl; i++)
		Chips(Spot, N);
	if (RockFx == None)
		RockFx = class<Emitter>(DynamicLoadObject("EonEffects.fx_Boss_bh3_RockImpact", class'Class', true));
	if (RockFx != None)
	{
		E = Spawn(RockFx,,, Spot + N * 6, rotator(N));
		if (E != None)
		{
			E.SetDrawScale(E.DrawScale * (Lvl >= 2 ? 0.6 : 0.4));
			E.LifeSpan = 4;
		}
	}
	if (Lvl == 1)
	{
		if (Breaches.Length >= 40)
			Breaches.Remove(0, 1);
		B.Spot = Spot;
		B.N = N;
		B.Level = 1;
		Breaches[Breaches.Length] = B;
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("dirt: breach level " $ Lvl $ " at " $ Spot);
}

// chips of wall knocked out by a shot: tiny rubble, out and down, gone within the minute
function Chips(vector Spot, vector N)
{
	local int i;
	local ModRubble R;
	local float K;
	local vector V;

	if (MaxRubble <= 0 || ChipCount <= 0)
		return;
	// only near the player: a fight's hundreds of stray shots would otherwise churn rubble
	// actors nobody sees (the holes themselves are cheap projectors)
	if (Level.GetLocalPlayerController() == None || Level.GetLocalPlayerController().Pawn == None
		|| VSize(Spot - Level.GetLocalPlayerController().Pawn.Location) > 700)
		return;
	for (i = 0; i < ChipCount; i++)
	{
		if (FRand() < 0.3)
			continue;
		while (Rubble.Length > 0 && (Rubble.Length >= MaxRubble || Rubble[0] == None || Rubble[0].bDeleteMe))
		{
			if (Rubble[0] != None && !Rubble[0].bDeleteMe)
				Rubble[0].Destroy();
			Rubble.Remove(0, 1);
		}
		R = Spawn(class'ModRubble',,, Spot + N * 8 + VRand() * 4, RotRand());
		if (R == None)
			continue;
		K = 0.5 + 0.9 * FRand() * FRand();
		R.Gore = self;
		R.SetStaticMesh(R.Shapes[Rand(2)]);
		R.SetDrawScale(K);
		R.Size = vect(1,1,1) * K;
		R.Stay = 25 + 20 * FRand();
		R.LifeSpan = 70;
		V = Normal(N * 1.5 + VRand()) * (90 + 170 * FRand());
		R.Launch(V, PhysicsVolume.Gravity.Z, K * 0.5);
		Rubble[Rubble.Length] = R;
	}
}

// a plasma burn: the spot glows white-hot and cools to soot over a few seconds (the
// decal's frames, three per burn texture, run by its Grow)
function Burn(vector Spot, vector N, float Size)
{
	local ModBloodDecal D;
	local int i;

	D = AddHole(Burns[0], Spot, N, Size);
	if (D == None)
		return;
	for (i = 0; i < 12; i++)
		D.Frames[i] = Burns[Min(i / 3, 3)];
	D.Grow(D.DrawScale, D.DrawScale * 1.12, 2.5 + FRand());
}

event Tick(float DeltaTime)
{
	local int i;
	local int j;
	local vector HitL, HitN, Spot;
	local ModBloodDecal D;

	if (Wet.Length > 0)
		WalkPrints();
	if (bFootprints && bBlood)
	{
		FeetScan -= DeltaTime;
		if (FeetScan <= 0)
		{
			FeetScan = 0.15;
			WetFeetScan();
		}
	}
	if (bDrips && (DripSrcs.Length > 0 || Streaks.Length > 0))
		DripTick();
	CorpseScan -= DeltaTime;
	if (CorpseScan <= 0)
	{
		CorpseScan = 0.5;
		ScanCorpses();
		CheckGibbed();
		CheckWounds();
	}
	TrackShots();
	if (bBodyStreaks)
		SendStreaks();
	if (Goo.Length > 0)
		SendGoo(DeltaTime);
	if (bBleedTrail)
		BleedTrails(DeltaTime);
	Spurts_(DeltaTime);
	if (bDirt)
		Grime(DeltaTime);
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
					// the pool spreads like a liquid: the frames of the fluid run, as it grows
					for (j = 0; j < 12; j++)
					{
						if (BloodKind(Dying[i]) == 2)
							D.Frames[j] = AlienPoolFrames[j];
						else
							D.Frames[j] = PoolFrames[j];
					}
					D.Grow(DecalScale * 0.2, DecalScale * (0.9 + FRand() * 0.4), 5 + FRand() * 3);
					// wet to step in as far as it will spread
					AddFloorBlood(HitL, 38 * D.GrowTo, BloodKind(Dying[i]));
					// or, with the d3d8 layer's live pools, simulated for real: the body pours into the
					// floor region it lies in (a new region if none), and the baked decal goes
					if (bLivePools && PourInto(HitL, HitN, int(BloodKind(Dying[i]) == 2)))
					{
						D.Destroy();
						D = None;
					}
					else
						D.LifeSpan = 300;
				}
			}
		}
		Dying.Remove(i, 1);
		DyingTime.Remove(i, 1);
	}
}

// Blood from a hit lands on the bodies around it: the victim's own, and whoever stands
// within Reach (the player too). Each body has one coat (ModBloodCoat), which gets
// heavier with more blood; the blood's colour is the first bleeder's.
function Spatter(Pawn From, vector Spot, float Amount, float Reach)
{
	local Pawn P;
	local int Kind;

	Kind = BloodKind(From);
	if (Kind == 0 || !bBlood)
		return;
	Amount = FMin(Amount, 1.5);
	AddCoat(From, Amount, Kind);
	ForEach RadiusActors(class'Pawn', P, Reach, Spot)
		if (P != From && !P.bHidden && P.Health > 0 && AdventPawn(P) != None)
			AddCoat(P, Amount * 0.6 * (1 - VSize(P.Location - Spot) / (Reach + P.CollisionRadius + 1)), Kind);
}

function ModBloodCoat CoatOf(Pawn P)
{
	local int i;

	for (i = 0; i < Coats.Length; i++)
		if (Coats[i] != None && !Coats[i].bDeleteMe && Coats[i].Wearer == P)
			return Coats[i];
	return None;
}

function AddCoat(Pawn P, float Amount, int Kind)
{
	local int i, Oldest;
	local ModBloodCoat C;

	if (Amount <= 0.02 || P == None || P.bHidden || P.IsA('Vehicle'))
		return;
	for (i = Coats.Length - 1; i >= 0; i--)
	{
		if (Coats[i] == None || Coats[i].bDeleteMe)
		{
			Coats.Remove(i, 1);
			continue;
		}
		if (Coats[i].Wearer == P)
		{
			Coats[i].More(Amount);
			return;
		}
	}
	if (Coats.Length >= MaxCoats)
	{
		// the lightest coat that isn't the player's makes room
		Oldest = -1;
		for (i = 0; i < Coats.Length; i++)
			if (!Coats[i].Wearer.IsHumanControlled() && (Oldest < 0 || Coats[i].Amount < Coats[Oldest].Amount))
				Oldest = i;
		if (Oldest < 0)
			return;
		Coats[Oldest].Destroy();
		Coats.Remove(Oldest, 1);
	}
	C = Spawn(class'ModBloodCoat',,, P.Location);
	if (C == None)
		return;
	C.Gore = self;
	if (!C.Wear(P, Kind, Amount))
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: no blood coat for " $ P $ ": " $ P.Skins.Length $ " skins, mesh " $ P.Mesh);
		C.Destroy();
		return;
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: blood coat on " $ P $ " (kind " $ Kind $ ", amount " $ Amount $ ", skin " $ C.OwnSkin[0] $ ", " $ C.Slots $ " slots, " $ (Coats.Length + 1) $ " coats)");
	Coats[Coats.Length] = C;
}

function Material CoatMaterial(int Kind, int Level)
{
	if (Kind == 2)
		return AlienCoatTex[Clamp(Level, 0, 2)];
	return CoatTex[Clamp(Level, 0, 2)];
}

// ---- dirt and battle damage --------------------------------------------------------------
// One pool of marks (MaxDirt, the oldest goes first), the same projectors as the blood:
//   - grime: now and then a patch on the floor or at the foot of a wall near the player, so
//     places the player has been through look used;
//   - an explosion leaves a crater where it went off, cracks on the walls around it, and
//     rubble on the floor.
// The d3d layer draws these with its parallax rule where U2Shaders.ini names their textures
// (decal=HASH decal_parallax.hlsl): darker reads as deeper, so cracks and craters sink in.
function ModBloodDecal AddDirt(Material T, vector Spot, vector N, float Size, float Life)
{
	local ModBloodDecal D;

	while (Dirt.Length > 0 && (Dirt.Length >= MaxDirt || Dirt[0] == None || Dirt[0].bDeleteMe))
	{
		if (Dirt[0] != None && !Dirt[0].bDeleteMe)
			Dirt[0].Destroy();
		Dirt.Remove(0, 1);
	}
	D = Spawn(class'ModBloodDecal',,, Spot + N * 16);
	if (D == None)
		return None;
	D.Place(T, Spot, N, vect(0,0,0), Size);
	D.LifeSpan = Life;
	Dirt[Dirt.Length] = D;
	return D;
}

// loose pieces knocked out of the surface an explosion went off on: up and outward, more
// and bigger for a bigger blast. Its own pool (MaxRubble, the oldest goes first).
function ThrowRubble(vector Spot, vector N, float Radius)
{
	local int i, Count;
	local ModRubble R;
	local float K;
	local vector V;

	if (MaxRubble <= 0)
		return;
	Count = Clamp(int(Radius / 60.0), 3, 7);
	for (i = 0; i < Count; i++)
	{
		while (Rubble.Length > 0 && (Rubble.Length >= MaxRubble || Rubble[0] == None || Rubble[0].bDeleteMe))
		{
			if (Rubble[0] != None && !Rubble[0].bDeleteMe)
				Rubble[0].Destroy();
			Rubble.Remove(0, 1);
		}
		R = Spawn(class'ModRubble',,, Spot + N * 14 + VRand() * 10, RotRand());
		if (R == None)
			continue;
		K = 3.0 + 6.0 * FRand() * FRand();
		R.Gore = self;
		R.SetStaticMesh(R.Shapes[Rand(2)]);
		R.SetDrawScale(K);
		R.Size = vect(1,1,1) * K;
		R.Stay = 180 + 60 * FRand();
		V = Normal(N * 1.2 + VRand()) * (220 + 380 * FRand());
		R.Launch(V, PhysicsVolume.Gravity.Z, K * 0.5);
		Rubble[Rubble.Length] = R;
	}
}

function BlastMarks(vector Loc, float Radius)
{
	local vector HitL, HitN, Dir;
	local int i;
	local float Reach;
	local bool bBreached;
	local Emitter E;

	Reach = FClamp(Radius * 0.6, 120, 320);
	// the crater: on the nearest surface below, or else straight ahead of nothing (in the air: none)
	if (Trace(HitL, HitN, Loc - vect(0,0,1) * Reach, Loc + vect(0,0,10), false) != None)
	{
		AddDirt(CraterTex, HitL, HitN, DecalScale * FClamp(Radius / 260.0, 0.9, 2.2), 600);
		AddDirt(RubbleTex, HitL + VRand() * vect(1,1,0) * 40, HitN, DecalScale * 1.6, 600);
		ThrowRubble(HitL, HitN, Radius);
	}
	// cracks where the blast reached a wall or the ceiling
	for (i = 0; i < 6; i++)
	{
		Dir = VRand();
		Dir.Z = Dir.Z * 0.5 + 0.2;
		Dir = Normal(Dir);
		if (Trace(HitL, HitN, Loc + Dir * Reach, Loc, false) != None && HitN.Z < 0.7)
		{
			AddDirt(CrackTex[Rand(2)], HitL, HitN, DecalScale * (0.9 + 0.8 * FRand()), 600);
			if (bBreaches && !bBreached && VSize(HitL - Loc) < Reach * 0.7)
			{
				bBreached = true;
				Breach(HitL, HitN, Radius >= 300 ? 2 : 1);
			}
		}
	}
	// dust shaken down from the ceiling over the blast
	if (bBreaches && Trace(HitL, HitN, Loc + vect(0,0,700), Loc, false) != None && HitN.Z < -0.6)
	{
		if (DustFallFx == None)
			DustFallFx = class<Emitter>(DynamicLoadObject("EonEffects.fx_Level_DustFallSm", class'Class', true));
		if (DustFallFx != None)
		{
			E = Spawn(DustFallFx,,, HitL - vect(0,0,8));
			if (E != None)
				E.LifeSpan = 3.5;
		}
	}
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("dirt: blast marks at " $ Loc $ " (" $ Dirt.Length $ " marks)");
}

// grime around the player: a patch on the floor nearby, or where a wall meets the floor
function Grime(float DeltaTime)
{
	local PlayerController C;
	local vector Start, Dir, HitL, HitN, WallL, WallN;

	DirtTimer -= DeltaTime;
	if (DirtTimer > 0)
		return;
	DirtTimer = DirtEvery * (0.6 + 0.8 * FRand());
	C = Level.GetLocalPlayerController();
	if (C == None || C.Pawn == None || VSize(C.Pawn.Velocity) < 50)
		return;                           // only while moving: standing still doesn't pile it up
	Dir = VRand();
	Dir.Z = 0;
	Dir = Normal(Dir);
	Start = C.Pawn.Location + Dir * (150 + 350 * FRand());
	if (!FastTrace(Start, C.Pawn.Location))
	{
		// a wall that way: its foot
		if (Trace(WallL, WallN, Start, C.Pawn.Location, false) == None)
			return;
		Start = WallL + WallN * 14;
	}
	if (Trace(HitL, HitN, Start - vect(0,0,400), Start, false) == None || HitN.Z < 0.6)
		return;
	AddDirt(GrimeTex[Rand(2)], HitL, HitN, DecalScale * (1.2 + 1.4 * FRand()), 900);
}

// a wound on the body: a small lump of meat (ModStump's mesh) riding the bone nearest
// the hit, pulled in to the limb (hits land on the collision cylinder, off the mesh)
function AddWound(Pawn P, vector Spot)
{
	local int i, n, Best, Kind;
	local float D, BestD;
	local coords BC;
	local vector Off, Rel;
	local Wound W;

	Kind = BloodKind(P);
	if (Kind == 0 || React == None || P.bHidden)
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: no wound on " $ P $ " (kind " $ Kind $ ", react " $ React $ ", hidden " $ P.bHidden $ ")");
		return;
	}
	for (i = 0; i < Wounds.Length; i++)
		if (Wounds[i].P == P)
			n++;
	if (n >= WoundsPerBody)
		return;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: wound " $ (n + 1) $ " on " $ P);
	BestD = 1000000;
	Best = -1;
	for (i = 0; i < 12; i++)
	{
		BC = P.GetBoneCoords(React.Bones[i]);
		if (BC.Origin == vect(0,0,0))
			continue;
		D = VSize(BC.Origin - Spot);
		if (D < BestD)
		{
			BestD = D;
			Best = i;
		}
	}
	if (Best < 0)
		return;
	while (Wounds.Length >= MaxWounds)
	{
		if (Wounds[0].M != None)
			Wounds[0].M.Destroy();
		Wounds.Remove(0, 1);
	}
	BC = P.GetBoneCoords(React.Bones[Best]);
	Off = Spot - BC.Origin;
	if (VSize(Off) > 9)
		Off = Normal(Off) * 9;
	W.M = Spawn(class'ModStump',,, BC.Origin + Off);
	if (W.M == None)
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: wound on " $ P $ " did not spawn");
		return;
	}
	W.M.SetDrawScale(1.5 + 1.3 * FRand());
	if (Kind == 2)
		W.M.Skins[0] = AlienMeatTex;
	else
		W.M.Skins[0] = MeatTex;
	if (!P.AttachToBone(W.M, React.Bones[Best]))
	{
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: wound on " $ P $ " did not attach to " $ React.Bones[Best]);
		W.M.Destroy();
		return;
	}
	Rel.X = Off Dot BC.XAxis;
	Rel.Y = Off Dot BC.YAxis;
	Rel.Z = Off Dot BC.ZAxis;
	W.M.SetRelativeLocation(Rel);
	W.P = P;
	Wounds[Wounds.Length] = W;
	LastWound = W.M;
	if (bBlood && FRand() < SpurtChance)
	{
		Spurts.Length = Spurts.Length + 1;
		Spurts[Spurts.Length - 1].P = P;
		Spurts[Spurts.Length - 1].M = W.M;
		Spurts[Spurts.Length - 1].Kind = Kind;
		Spurts[Spurts.Length - 1].Life = 2.5 + 2.0 * FRand();
		Spurts[Spurts.Length - 1].Next = 0.15;
		if (class'ModSettings'.default.bGoreLog)
			class'ModSettings'.static.Note("gore: " $ P $ " has a spurting wound at " $ React.Bones[Best]);
	}
}

// the spurting wounds: a pulse every heartbeat, out from the wound and falling, weaker as it
// runs down; a dead body's last few beats are weaker still
function Spurts_(float DeltaTime)
{
	local int i, k;
	local float Strength, Reach;
	local vector Out, V, HitL, HitN, Fall;

	for (i = Spurts.Length - 1; i >= 0; i--)
	{
		Spurts[i].T += DeltaTime;
		if (Spurts[i].P == None || Spurts[i].P.bDeleteMe || Spurts[i].M == None || Spurts[i].M.bDeleteMe
			|| Spurts[i].T > Spurts[i].Life || Spurts[i].P.bHidden)
		{
			Spurts.Remove(i, 1);
			continue;
		}
		if (Spurts[i].T < Spurts[i].Next)
			continue;
		Spurts[i].Next = Spurts[i].T + SpurtBeat * (0.85 + 0.3 * FRand()) * (Spurts[i].P.Health <= 0 ? 1.4 : 1.0);
		Strength = 1 - Spurts[i].T / Spurts[i].Life;
		if (Spurts[i].P.Health <= 0)
			Strength *= 0.5;
		Reach = SpurtReach * (0.35 + 0.65 * Strength);
		// out of the wound: away from the body's axis, a little up
		Out = Spurts[i].M.Location - Spurts[i].P.Location;
		Out.Z = 0;
		Out = Normal(Normal(Out) + vect(0,0,0.35) + VRand() * 0.25);
		// the jet: where it meets a wall or the floor along a falling arc (two segments)
		V = Spurts[i].M.Location + Out * Reach * 0.5;
		Fall = V + (Out * 0.5 + vect(0,0,-0.6)) * Reach;
		if (Trace(HitL, HitN, V, Spurts[i].M.Location, false) != None
			|| Trace(HitL, HitN, Fall, V, false) != None
			|| Trace(HitL, HitN, Fall - vect(0,0,300), Fall, false) != None)
			Mark(KindSpray(Spurts[i].Kind), HitL, HitN, Out, DecalScale * (0.35 + 0.35 * Strength));
		// droplets beside the jet
		for (k = 0; k < 2; k++)
		{
			V = Spurts[i].M.Location + Normal(Out + VRand() * 0.5) * Reach * (0.3 + 0.4 * FRand());
			if (Trace(HitL, HitN, V - vect(0,0,300), V, false) != None)
				Mark(KindSplat(Spurts[i].Kind), HitL, HitN, vect(0,0,0), DecalScale * 0.12);
		}
	}
}

// a bleeding point on P at Spot: a wound's or cut's stump M, or (None) the nearest bone
function AddStreak(Pawn P, vector Spot, Actor M, float Str)
{
	local int i, n, Best, Oldest, Kind;
	local float D, BestD;
	local coords BC;
	local vector Off;
	local StreakSrc S;

	if (!bBodyStreaks || !bBlood || P == None || P.bDeleteMe || P.bHidden || React == None)
		return;
	Kind = BloodKind(P);
	if (Kind == 0)
		return;
	Oldest = -1;
	for (i = 0; i < Streaks.Length; i++)
	{
		if (Streaks[i].P != P)
			continue;
		n++;
		if (Oldest < 0 || Streaks[i].Born < Streaks[Oldest].Born)
			Oldest = i;
		if (VSize(StreakSpot(i) - Spot) < 6)
		{
			// near one it has: that one bleeds harder
			if (M != None && Streaks[i].M == None)
				Streaks[i].M = M;
			Streaks[i].Str = FMin(1.5, Streaks[i].Str + 0.5 * Str);
			return;
		}
	}
	if (n >= StreaksPerBody && Oldest >= 0)
		Streaks.Remove(Oldest, 1);
	if (Streaks.Length >= 32)
		Streaks.Remove(0, 1);
	S.P = P;
	S.M = M;
	S.Kind = Kind;
	S.Born = Level.TimeSeconds;
	S.Str = FClamp(Str, 0.2, 1.5);
	S.Seed = Rand(65536);
	if (M == None)
	{
		// the nearest bone, the spot pulled in to it (hits land on the collision cylinder)
		BestD = 1000000;
		Best = -1;
		for (i = 0; i < 12; i++)
		{
			BC = P.GetBoneCoords(React.Bones[i]);
			if (BC.Origin == vect(0,0,0))
				continue;
			D = VSize(BC.Origin - Spot);
			if (D < BestD)
			{
				BestD = D;
				Best = i;
			}
		}
		if (Best < 0)
			return;
		BC = P.GetBoneCoords(React.Bones[Best]);
		Off = Spot - BC.Origin;
		if (VSize(Off) > 9)
			Off = Normal(Off) * 9;
		S.Bone = React.Bones[Best];
		S.Rel.X = Off Dot BC.XAxis;
		S.Rel.Y = Off Dot BC.YAxis;
		S.Rel.Z = Off Dot BC.ZAxis;
	}
	Streaks[Streaks.Length] = S;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: streak source on " $ P $ " at " $ S.Bone $ " " $ M $ " (" $ Streaks.Length $ " in all)");
}

// where bleeding point i is now
function vector StreakSpot(int i)
{
	local coords BC;

	if (Streaks[i].M != None && !Streaks[i].M.bDeleteMe)
		return Streaks[i].M.Location;
	BC = Streaks[i].P.GetBoneCoords(Streaks[i].Bone);
	return BC.Origin + Streaks[i].Rel.X * BC.XAxis + Streaks[i].Rel.Y * BC.YAxis + Streaks[i].Rel.Z * BC.ZAxis;
}

// every tick: the bleeding points go with their body (removed, blown apart, back to life, or
// old), and the 8 nearest the view (newer ones count as nearer) go to the d3d8 layer, with the
// body's outward direction there (from the hips' vertical line) so it paints only that side
function SendStreaks()
{
	local int i, k, n;
	local int Pick[8];
	local float Score[8];
	local float S, Age, Fade;
	local vector Eye, Spot, Out, Core;
	local PlayerController PC;
	local coords BC;
	local Pawn P;

	for (i = Streaks.Length - 1; i >= 0; i--)
	{
		P = Streaks[i].P;
		if (P != None && !P.bDeleteMe && P.Health <= 0)
			Streaks[i].bDied = true;
		if (P == None || P.bDeleteMe || (Streaks[i].bDied && P.Health > 0)
			|| Level.TimeSeconds - Streaks[i].Born > StreakLife
			|| (Streaks[i].Bone == '' && (Streaks[i].M == None || Streaks[i].M.bDeleteMe)))
			Streaks.Remove(i, 1);
	}
	if (Streaks.Length == 0 && StreaksSent == 0)
		return;
	PC = Level.GetLocalPlayerController();
	if (PC != None && PC.ViewTarget != None)
		Eye = PC.ViewTarget.Location;
	else if (PC != None)
		Eye = PC.Location;
	for (i = 0; i < Streaks.Length; i++)
	{
		if (Streaks[i].P.bHidden)
			continue;                    // blown apart (gibs hide the body)
		S = VSize(StreakSpot(i) - Eye) + 10 * (Level.TimeSeconds - Streaks[i].Born);
		if (n < 8)
		{
			k = n;
			n++;
		}
		else if (S >= Score[7])
			continue;
		else
			k = 7;
		while (k > 0 && Score[k - 1] > S)
		{
			Score[k] = Score[k - 1];
			Pick[k] = Pick[k - 1];
			k--;
		}
		Score[k] = S;
		Pick[k] = i;
	}
	for (k = 0; k < n; k++)
	{
		i = Pick[k];
		P = Streaks[i].P;
		Spot = StreakSpot(i);
		BC = P.GetBoneCoords(React.Bones[0]);
		Core = P.Location;
		if (BC.Origin != vect(0,0,0))
			Core = BC.Origin;
		Out = Spot - Core;
		Out.Z = 0;
		if (VSize(Out) < 1)
			Out = vector(P.Rotation);
		Out.Z = 0;
		Out = Normal(Out);
		Age = Level.TimeSeconds - Streaks[i].Born;
		Fade = FClamp((StreakLife - Age) / 5.0, 0, 1);
		class'ModSettings'.static.NativeCall("Blood:streak " $ k $ " " $ Spot.X $ " " $ Spot.Y $ " " $ Spot.Z $ " " $ Out.X $ " " $ Out.Y
			$ " " $ Streaks[i].Kind $ " " $ Age $ " " $ (Streaks[i].Str * Fade) $ " " $ Streaks[i].Seed);
	}
	if (n != StreaksSent)
	{
		class'ModSettings'.static.NativeCall("Blood:streaks " $ n);
		StreaksSent = n;
	}
}

// a goo string between two ends: actor A (or, with A None, P's bone) and actor B; Thick a
// multiplier on GooThick, K the body's scale. False: no free slot (12 at most)
function bool AddGoo(Actor A, Pawn P, name Bone, Actor B, int Kind, float Thick, float K)
{
	local GooString G;
	local int s;
	local float D;

	if (!bGooStrings || !bBlood || Kind == 0 || B == None || (A == None && (P == None || Bone == '')))
		return false;
	for (s = 0; s < 12; s++)
		if (GooSlots[s] == 0)
			break;
	if (s == 12)
		return false;
	G.A = A;
	G.B = B;
	G.P = P;
	G.Bone = Bone;
	G.Kind = Kind;
	G.Slot = s;
	G.Seed = 1 + Rand(60000);
	G.Thick = GooThick * Thick * FClamp(K, 0.6, 1.6);
	if (ModGib(A) != None)
		G.RA = ModGib(A).Radius * 0.8;
	if (ModGib(B) != None)
		G.RB = ModGib(B).Radius * 0.8;
	G.Born = Level.TimeSeconds;
	G.SnapAt = -1;
	Goo[Goo.Length] = G;
	// the length it rests at: at least what is between the ends now (it starts slack: it hangs)
	D = VSize(GooEnd(Goo.Length - 1, true) - GooEnd(Goo.Length - 1, false));
	Goo[Goo.Length - 1].Rest = FMax(D, (GooRestMin + FRand() * (GooRestMax - GooRestMin)) * FClamp(K, 0.6, 1.6));
	Goo[Goo.Length - 1].Limit = GooStretchMin + FRand() * (GooStretchMax - GooStretchMin);
	Goo[Goo.Length - 1].Hold = GooHoldMin + FRand() * (GooHoldMax - GooHoldMin);
	Goo[Goo.Length - 1].Life = GooLifeMin + FRand() * (GooLifeMax - GooLifeMin);
	GooSlots[s] = 1;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: goo string " $ s $ " from " $ A $ P $ " " $ Bone $ " to " $ B $ ", rest " $ Goo[Goo.Length - 1].Rest $ ", snaps at x" $ Goo[Goo.Length - 1].Limit);
	return true;
}

// where string i's end is now (bB: end B)
function vector GooEnd(int i, bool bB)
{
	local Actor E, O;
	local vector OL;
	local float R;

	if (bB)
	{
		E = Goo[i].B;
		O = Goo[i].A;
		R = Goo[i].RB;
	}
	else
	{
		E = Goo[i].A;
		O = Goo[i].B;
		R = Goo[i].RA;
	}
	if (E == None)
		return Goo[i].P.GetBoneCoords(Goo[i].Bone).Origin;
	if (O != None)
		OL = O.Location;
	else
		OL = Goo[i].P.GetBoneCoords(Goo[i].Bone).Origin;
	if (VSize(OL - E.Location) > R * 2)
		return E.Location + Normal(OL - E.Location) * R;
	return E.Location;
}

// is one of string i's ends gone (or hidden: a body blown apart)?
function bool GooLost(int i)
{
	if (Goo[i].B == None || Goo[i].B.bDeleteMe || Goo[i].B.bHidden)
		return true;
	if (Goo[i].A != None)
		return Goo[i].A.bDeleteMe || Goo[i].A.bHidden;
	return Goo[i].P == None || Goo[i].P.bDeleteMe || Goo[i].P.bHidden;
}

function GooOff(int i)
{
	if (Goo[i].Slot >= 0 && Goo[i].Slot < 12)
		GooSlots[Goo[i].Slot] = 0;
	class'ModSettings'.static.NativeCall("Blood:stringoff " $ Goo[i].Slot);
	Goo.Remove(i, 1);
}

// every tick: stretch, pull, snap, and the live strings' ends to the layer
function SendGoo(float DeltaTime)
{
	local int i;
	local vector EA, EB, Dir, HitL, HitN;
	local float D, Age, Snap;
	local ModGib G;

	for (i = Goo.Length - 1; i >= 0; i--)
	{
		if (Goo[i].P != None && !Goo[i].P.bDeleteMe && Goo[i].P.Health <= 0)
			Goo[i].bDied = true;
		if (Goo[i].A == None && Goo[i].P != None && !Goo[i].P.bDeleteMe && Goo[i].bDied && Goo[i].P.Health > 0)
		{
			GooOff(i);                   // the game brought the body back
			continue;
		}
		if (GooLost(i))
		{
			if (Goo[i].B == None || Goo[i].B.bDeleteMe || (Goo[i].A != None && Goo[i].A.bDeleteMe)
				|| (Goo[i].A == None && (Goo[i].P == None || Goo[i].P.bDeleteMe)))
			{
				GooOff(i);                   // an end is gone
				continue;
			}
			if (Goo[i].SnapAt < 0)
				Goo[i].SnapAt = Level.TimeSeconds;      // hidden, not gone: it snaps
		}
		Age = Level.TimeSeconds - Goo[i].Born;
		if (Goo[i].SnapAt >= 0 && Level.TimeSeconds - Goo[i].SnapAt > GooDangle)
		{
			GooOff(i);
			continue;
		}
		EA = GooEnd(i, false);
		EB = GooEnd(i, true);
		D = VSize(EB - EA);
		if (Goo[i].SnapAt < 0)
		{
			// goo holds a moment before it breaks: under GooHold seconds only a hard over-stretch snaps it,
			// so it shows as a long thinning strand instead of breaking in the first frames of a throw
			if ((D > Goo[i].Rest * Goo[i].Limit && (Age > Goo[i].Hold || D > Goo[i].Rest * Goo[i].Limit * 4)) || Age > Goo[i].Life)
			{
				Goo[i].SnapAt = Level.TimeSeconds;
				if (class'ModSettings'.default.bGoreLog)
					class'ModSettings'.static.Note("gore: goo string " $ Goo[i].Slot $ " snaps at " $ D $ " (rest " $ Goo[i].Rest $ ", age " $ Age $ ")");
				// what it held drips down: a quick run of drops from the middle (they leave the
				// splats), or without drops a small splat under the middle
				if (bDrips)
					AddDripSrc((EA + EB) * 0.5, Goo[i].Kind, 0.05, 0.12, 0.4, 1.6, DecalScale * 0.08);
				else if (Trace(HitL, HitN, (EA + EB) * 0.5 - vect(0,0,400), (EA + EB) * 0.5, false) != None)
					Mark(KindSplat(Goo[i].Kind), HitL, HitN, vect(0,0,0), DecalScale * (0.2 + 0.1 * FRand()));
			}
			else if (D > Goo[i].Rest && GooPull > 0)
			{
				// stretched: it drags on the pieces still flying
				Dir = Normal(EB - EA);
				G = ModGib(Goo[i].B);
				if (G != None && !G.bSettled)
					G.Vel -= Dir * GooPull * (D - Goo[i].Rest) * DeltaTime;
				G = ModGib(Goo[i].A);
				if (G != None && !G.bSettled)
					G.Vel += Dir * GooPull * (D - Goo[i].Rest) * DeltaTime;
			}
		}
		Snap = -1;
		if (Goo[i].SnapAt >= 0)
			Snap = Level.TimeSeconds - Goo[i].SnapAt;
		class'ModSettings'.static.NativeCall("Blood:string " $ Goo[i].Slot $ " " $ EA.X $ " " $ EA.Y $ " " $ EA.Z $ " " $ EB.X $ " " $ EB.Y $ " " $ EB.Z
			$ " " $ Goo[i].Kind $ " " $ Goo[i].Thick $ " " $ Goo[i].Rest $ " " $ Age $ " " $ Snap $ " " $ Goo[i].Seed);
	}
}

// strings between pieces of one body just blown apart: each from a random piece to the one
// that was nearest it on the body (its neighbour), 1-3 of them
function GooGibs(int Kind, float K)
{
	local int n, j, i, Near, Tries;
	local float D, BestD;
	local array<int> Used;

	if (!bGooStrings || GooMade.Length < 2)
		return;
	n = 1 + Rand(3);
	while (n > 0 && Tries < 8)
	{
		Tries++;
		i = Rand(GooMade.Length);
		Near = -1;
		BestD = 1000000;
		for (j = 0; j < GooMade.Length; j++)
		{
			if (j == i || GooMade[j] == None)
				continue;
			D = VSize(GooMade[j].Location - GooMade[i].Location);
			if (D < BestD)
			{
				BestD = D;
				Near = j;
			}
		}
		if (Near < 0 || GooMade[i] == None)
			continue;
		// not the same pair twice
		for (j = 0; j < Used.Length; j += 2)
			if ((Used[j] == i && Used[j + 1] == Near) || (Used[j] == Near && Used[j + 1] == i))
				break;
		if (j < Used.Length)
			continue;
		if (!AddGoo(GooMade[i], None, '', GooMade[Near], Kind, 0.6 + 0.5 * FRand(), K))
			return;
		Used[Used.Length] = i;
		Used[Used.Length] = Near;
		n--;
	}
}

// ModPilot GOOLIST: the live strings
function GooList()
{
	local int i;

	for (i = 0; i < Goo.Length; i++)
		class'ModSettings'.static.Note("goolist: slot " $ Goo[i].Slot $ " " $ Goo[i].A $ Goo[i].P $ " " $ Goo[i].Bone $ " - " $ Goo[i].B
			$ " length " $ VSize(GooEnd(i, true) - GooEnd(i, false)) $ " rest " $ Goo[i].Rest $ " limit x" $ Goo[i].Limit
			$ " age " $ (Level.TimeSeconds - Goo[i].Born) $ " snapped " $ (Goo[i].SnapAt >= 0));
	class'ModSettings'.static.Note("goolist: " $ Goo.Length $ " strings");
}

// wounds go with their body: when it is removed, blown apart or brought back to life
function CheckWounds()
{
	local int i;
	local Pawn P;

	for (i = Wounds.Length - 1; i >= 0; i--)
	{
		P = Wounds[i].P;
		if (P != None && !P.bDeleteMe && P.Health <= 0)
			Wounds[i].bDied = true;
		if (Wounds[i].M == None || P == None || P.bDeleteMe || (Wounds[i].bDied && P.Health > 0))
		{
			if (Wounds[i].M != None)
			{
				if (P != None)
					P.DetachFromBone(Wounds[i].M);
				Wounds[i].M.Destroy();
			}
			Wounds.Remove(i, 1);
			continue;
		}
		if (Wounds[i].M.bHidden != P.bHidden)
			Wounds[i].M.bHidden = P.bHidden;
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
		// with drips: a real drop falls from the wound (it leaves the splat where it lands)
		if (bDrips)
		{
			Bleeders[i].Next /= FMax(DripRate, 0.05);
			if (Drip(BleedSpot(P), P.Velocity * 0.5 + vect(0,0,-20), BloodKind(P), DecalScale * (0.1 + 0.12 * Bleeders[i].Rate)))
				continue;
		}
		if (Trace(HitL, HitN, P.Location - vect(0,0,1) * (P.CollisionHeight + 120), P.Location, false) != None)
			Mark(SplatTex(P), HitL + VRand() * vect(1,1,0) * 14, HitN, vect(0,0,0), DecalScale * (0.14 + 0.16 * Bleeders[i].Rate));
	}
}

// where a living body bleeds from: its newest bleeding point (a wound, a cut or a hit), else
// somewhere on its middle
function vector BleedSpot(Pawn P)
{
	local int i;

	for (i = Streaks.Length - 1; i >= 0; i--)
		if (Streaks[i].P == P && (Streaks[i].Bone != '' || (Streaks[i].M != None && !Streaks[i].M.bDeleteMe)))
			return StreakSpot(i);
	return P.Location + VRand() * vect(1,1,0) * P.CollisionRadius * 0.4;
}

// ---- falling drops -----------------------------------------------------------------------
// a drop falls from Spot with velocity V; false when it can't (drips off, too far from the
// player to be seen, or every drop of the pool already in the air)
function bool Drip(vector Spot, vector V, int Kind, float SplatSize)
{
	local ModBloodDrop D;
	local PlayerController C;

	if (!bDrips || !bBlood || Kind == 0)
		return false;
	C = Level.GetLocalPlayerController();
	if (C == None || C.Pawn == None || VSize(Spot - C.Pawn.Location) > DripReach)
		return false;
	D = FreeDrop();
	if (D == None)
		return false;
	D.Fall(Spot, V, PhysicsVolume.Gravity.Z, Kind, DropSize * (0.75 + 0.5 * FRand()), SplatSize);
	DropsThrown++;
	return true;
}

// a drop not in the air: one from the pool, or a new one while the pool is under MaxDrops
function ModBloodDrop FreeDrop()
{
	local int i;
	local ModBloodDrop D;

	for (i = Drops.Length - 1; i >= 0; i--)
	{
		if (Drops[i] == None || Drops[i].bDeleteMe)
		{
			Drops.Remove(i, 1);
			continue;
		}
		if (!Drops[i].bFlying)
			return Drops[i];
	}
	if (Drops.Length >= Clamp(MaxDrops, 0, 64))
		return None;
	D = Spawn(class'ModBloodDrop',,, Location);
	if (D == None)
		return None;
	D.Gore = self;
	Drops[Drops.Length] = D;
	return D;
}

// a drop came down (ModBloodDrop's trace): into the live pool there, or a tiny splat (one per
// spot: drops falling in one place add to the splat there); nothing on walls
function DropLanded(ModBloodDrop D, vector HitL, vector HitN)
{
	local ModBloodDecal R;
	local int i;

	DropsLanded++;
	if (HitN.Z < 0.5)
		return;
	if (bLivePools)
	{
		R = RegionAt(HitL);
		if (R != None && R.PourAt(HitL, DropPour, 0.25, int(D.Kind == 2)))
			return;
	}
	for (i = 0; i < DropSplats.Length; i++)
		if (VSize(DropSplats[i] - HitL) < 6)
			return;
	if (DropSplats.Length >= 24)
		DropSplats.Remove(0, 1);
	DropSplats[DropSplats.Length] = HitL;
	Mark(KindSplat(D.Kind), HitL, HitN, vect(0,0,0), D.MarkSize);
}

// a place that drips for a while: a drop every GapMin-GapMax seconds (over DripRate) from First
// seconds on, for Life seconds. One source a spot (more blood there keeps it going); at most 24
function AddDripSrc(vector Spot, int Kind, float First, float GapMin, float GapMax, float Life, float Size)
{
	local DripSrc S;
	local int i;

	if (!bDrips || !bBlood || Kind == 0)
		return;
	for (i = 0; i < DripSrcs.Length; i++)
		if (VSize(DripSrcs[i].Spot - Spot) < 10)
		{
			DripSrcs[i].EndT = FMax(DripSrcs[i].EndT, Level.TimeSeconds + Life);
			return;
		}
	if (DripSrcs.Length >= 24)
		DripSrcs.Remove(0, 1);
	S.Spot = Spot;
	S.Kind = Kind;
	S.Next = Level.TimeSeconds + First;
	S.EndT = Level.TimeSeconds + Life;
	S.GapMin = GapMin;
	S.GapMax = GapMax;
	S.Size = Size;
	DripSrcs[DripSrcs.Length] = S;
	if (class'ModSettings'.default.bGoreLog)
		class'ModSettings'.static.Note("gore: drips from " $ Spot $ " for " $ Life $ " s (" $ DripSrcs.Length $ " sources)");
}

// how far under its middle a fresh wall mark of this size (a Mark DrawScale) has blood to drip
// from: a spray covers about 60% of its 128 px square; a running one runs further
function float WallBelow(float Size)
{
	if (bWallRuns)
		return FMax(128 * Size * 0.3, RunSize * 0.7);
	return 128 * Size * 0.3;
}

// fresh blood on a wall: drops leave its lower edge, Below under Spot, a little off the wall.
// None if the floor (or a ledge) comes before that edge, or lies right under it: the blood stops
// there. So it drips where there is air under the blood: a spray high on a wall, a wall over a
// drop, the edge of a walkway.
function WallDrip(vector Spot, vector N, float Below, int Kind, float Life)
{
	local vector Down, Edge, Start, HitL, HitN;

	if (!bDrips || !bBlood || Kind == 0 || Abs(N.Z) > 0.5)
		return;
	Down = Normal(vect(0,0,-1) - N * (vect(0,0,-1) Dot N));
	Start = Spot + N * 3;
	Edge = Start + Down * Below;
	if (Trace(HitL, HitN, Edge, Start, false) != None)
		return;
	if (!FastTrace(Edge - vect(0,0,12), Edge))
		return;
	AddDripSrc(Edge, Kind, 0.8 + 0.8 * FRand(), 0.5, 1.4, Life, DecalScale * 0.07);
}

// every tick: the dripping places, and the dead bodies' bleeding points (fewer drops as they
// clot: a body drains for twice BleedClot). A point lying on the floor bleeds into its pool
// instead: only one with a drop under it drips (a body over a ledge, an arm off a step)
function DripTick()
{
	local int i;
	local float T, Age, Clot, Str;
	local vector Spot;
	local Pawn P;

	T = Level.TimeSeconds;
	for (i = DripSrcs.Length - 1; i >= 0; i--)
	{
		if (T > DripSrcs[i].EndT)
		{
			DripSrcs.Remove(i, 1);
			continue;
		}
		if (T < DripSrcs[i].Next)
			continue;
		DripSrcs[i].Next = T + (DripSrcs[i].GapMin + FRand() * (DripSrcs[i].GapMax - DripSrcs[i].GapMin)) / FMax(DripRate, 0.05);
		Drip(DripSrcs[i].Spot + VRand() * vect(1,1,0) * 1.5, vect(0,0,-15), DripSrcs[i].Kind, DripSrcs[i].Size);
	}
	for (i = 0; i < Streaks.Length; i++)
	{
		P = Streaks[i].P;
		if (P == None || P.bDeleteMe || P.bHidden || P.Health > 0 || T < Streaks[i].NextDrip)
			continue;
		if (Streaks[i].Bone == '' && (Streaks[i].M == None || Streaks[i].M.bDeleteMe))
			continue;
		Age = T - Streaks[i].Born;
		Clot = 1 - Age / FMax(BleedClot * 2, 1);
		if (Clot <= 0.05)
			continue;
		Str = FClamp(Streaks[i].Str / 1.5, 0.15, 1.0) * Clot;
		Streaks[i].NextDrip = T + (0.35 + 2.0 * (1 - Str)) * (0.8 + 0.4 * FRand()) / FMax(DripRate, 0.05);
		Spot = StreakSpot(i);
		if (!FastTrace(Spot - vect(0,0,24), Spot))
			continue;
		Drip(Spot, vect(0,0,-10), Streaks[i].Kind, DecalScale * (0.05 + 0.04 * Str));
	}
}

// ModPilot DROPLIST: the drops in the air and the dripping places
function DropList()
{
	local int i, n;

	for (i = 0; i < Drops.Length; i++)
		if (Drops[i] != None && Drops[i].bFlying)
		{
			n++;
			if (n <= 8)
				class'ModSettings'.static.Note("droplist: drop at " $ Drops[i].Location $ " vel " $ Drops[i].Vel $ " kind " $ Drops[i].Kind $ " age " $ Drops[i].Age);
		}
	for (i = 0; i < DripSrcs.Length; i++)
		class'ModSettings'.static.Note("droplist: source " $ DripSrcs[i].Spot $ " kind " $ DripSrcs[i].Kind $ " next in " $ (DripSrcs[i].Next - Level.TimeSeconds) $ " ends in " $ (DripSrcs[i].EndT - Level.TimeSeconds));
	class'ModSettings'.static.Note("droplist: " $ n $ " in the air, " $ Drops.Length $ " made (max " $ MaxDrops $ "), " $ DripSrcs.Length $ " sources, "
		$ Bleeders.Length $ " bleeders, " $ Streaks.Length $ " bleeding points, thrown " $ DropsThrown $ " landed " $ DropsLanded $ ", drips " $ bDrips);
}

// ModPilot STEPLIST: the wet feet and the fresh floor blood they can step in
function StepList()
{
	local int i;

	for (i = 0; i < Wet.Length; i++)
		class'ModSettings'.static.Note("steplist: " $ Wet[i].P $ " kind " $ Wet[i].Kind $ " prints left " $ Wet[i].Left $ " at " $ Wet[i].P.Location);
	for (i = 0; i < FloorMarks.Length; i++)
		class'ModSettings'.static.Note("steplist: floor blood " $ FloorMarks[i].Spot $ " radius " $ int(FloorMarks[i].Radius) $ " kind " $ FloorMarks[i].Kind $ " age " $ int(Level.TimeSeconds - FloorMarks[i].Born));
	class'ModSettings'.static.Note("steplist: " $ Wet.Length $ " wet walkers, " $ FloorMarks.Length $ " wet floor marks, " $ Prints.Length $ " prints (max " $ MaxFootprints $ "), "
		$ Corpses.Length $ " bodies, " $ Decals.Length $ " marks, footprints " $ bFootprints);
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
	local int K;

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
	if (!bPrinting && (bDrips || bFootprints))
	{
		K = MarkKind(T);
		// blood on a ceiling or an overhang drips for a while
		if (K != 0 && N.Z < -0.5)
			AddDripSrc(Spot + N * 2, K, 0.5 + FRand(), 1.5, 4.0, 20, DecalScale * 0.09);
		// fresh blood on the floor wets the feet that pass through (not the tiny drop splats)
		if (K != 0 && N.Z > 0.6 && Size >= 0.25)
			AddFloorBlood(Spot, 38 * Size, K);
	}
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
	if (Melee != None)
		Melee.Destroy();
	for (i = 0; i < Coats.Length; i++)
		if (Coats[i] != None)
			Coats[i].Destroy();
	for (i = 0; i < Dirt.Length; i++)
		if (Dirt[i] != None)
			Dirt[i].Destroy();
	for (i = 0; i < Drops.Length; i++)
		if (Drops[i] != None)
			Drops[i].Destroy();
	Super.Destroyed();
}

defaultproperties
{
     bKarmaFreezeFix=False
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
     PoolLive(0)=Texture'AdventMod.Blood.BloodLive0'
     PoolLive(1)=Texture'AdventMod.Blood.BloodLive1'
     PoolLive(2)=Texture'AdventMod.Blood.BloodLive2'
     PoolLive(3)=Texture'AdventMod.Blood.BloodLive3'
     PoolLive(4)=Texture'AdventMod.Blood.BloodLive4'
     PoolLive(5)=Texture'AdventMod.Blood.BloodLive5'
     PoolLive(6)=Texture'AdventMod.Blood.BloodLive6'
     PoolLive(7)=Texture'AdventMod.Blood.BloodLive7'
     bLivePools=True
     bWallRuns=True
     RunSize=150.000000
     RunChance=0.800000
     RunLive(0)=Texture'AdventMod.Blood.BloodRun0'
     RunLive(1)=Texture'AdventMod.Blood.BloodRun1'
     RunLive(2)=Texture'AdventMod.Blood.BloodRun2'
     RunLive(3)=Texture'AdventMod.Blood.BloodRun3'
     RunLive(4)=Texture'AdventMod.Blood.BloodRun4'
     RunLive(5)=Texture'AdventMod.Blood.BloodRun5'
     RunLive(6)=Texture'AdventMod.Blood.BloodRun6'
     RunLive(7)=Texture'AdventMod.Blood.BloodRun7'
     FootTex(0)=Texture'AdventMod.Blood.FootprintH0'
     FootTex(1)=Texture'AdventMod.Blood.FootprintH1'
     FootTex(2)=Texture'AdventMod.Blood.FootprintH2'
     AlienFootTex(0)=Texture'AdventMod.Blood.FootprintA0'
     AlienFootTex(1)=Texture'AdventMod.Blood.FootprintA1'
     AlienFootTex(2)=Texture'AdventMod.Blood.FootprintA2'
     FootTexL(0)=Texture'AdventMod.Blood.FootprintHL0'
     FootTexL(1)=Texture'AdventMod.Blood.FootprintHL1'
     FootTexL(2)=Texture'AdventMod.Blood.FootprintHL2'
     AlienFootTexL(0)=Texture'AdventMod.Blood.FootprintAL0'
     AlienFootTexL(1)=Texture'AdventMod.Blood.FootprintAL1'
     AlienFootTexL(2)=Texture'AdventMod.Blood.FootprintAL2'
     DripTex=Texture'AdventMod.Blood.DripsH'
     AlienDripTex=Texture'AdventMod.Blood.DripsA'
     bFootprints=True
     FootprintSteps=10
     FootStride=45.000000
     FootGap=7.000000
     MaxFootprints=40
     FootFresh=90.000000
     bDrips=True
     DripRate=1.000000
     MaxDrops=24
     DropSize=0.150000
     DripReach=2000.000000
     DropPour=0.040000
     LivePour=1.400000
     LivePourSecs=2.600000
     RegionSize=640.000000
     PoolFrames(0)=Texture'AdventMod.Blood.BloodPoolF0'
     PoolFrames(1)=Texture'AdventMod.Blood.BloodPoolF1'
     PoolFrames(2)=Texture'AdventMod.Blood.BloodPoolF2'
     PoolFrames(3)=Texture'AdventMod.Blood.BloodPoolF3'
     PoolFrames(4)=Texture'AdventMod.Blood.BloodPoolF4'
     PoolFrames(5)=Texture'AdventMod.Blood.BloodPoolF5'
     PoolFrames(6)=Texture'AdventMod.Blood.BloodPoolF6'
     PoolFrames(7)=Texture'AdventMod.Blood.BloodPoolF7'
     PoolFrames(8)=Texture'AdventMod.Blood.BloodPoolF8'
     PoolFrames(9)=Texture'AdventMod.Blood.BloodPoolF9'
     PoolFrames(10)=Texture'AdventMod.Blood.BloodPoolF10'
     PoolFrames(11)=Texture'AdventMod.Blood.BloodPoolF11'
     AlienPoolFrames(0)=Texture'AdventMod.Blood.AlienPoolF0'
     AlienPoolFrames(1)=Texture'AdventMod.Blood.AlienPoolF1'
     AlienPoolFrames(2)=Texture'AdventMod.Blood.AlienPoolF2'
     AlienPoolFrames(3)=Texture'AdventMod.Blood.AlienPoolF3'
     AlienPoolFrames(4)=Texture'AdventMod.Blood.AlienPoolF4'
     AlienPoolFrames(5)=Texture'AdventMod.Blood.AlienPoolF5'
     AlienPoolFrames(6)=Texture'AdventMod.Blood.AlienPoolF6'
     AlienPoolFrames(7)=Texture'AdventMod.Blood.AlienPoolF7'
     AlienPoolFrames(8)=Texture'AdventMod.Blood.AlienPoolF8'
     AlienPoolFrames(9)=Texture'AdventMod.Blood.AlienPoolF9'
     AlienPoolFrames(10)=Texture'AdventMod.Blood.AlienPoolF10'
     AlienPoolFrames(11)=Texture'AdventMod.Blood.AlienPoolF11'
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
     Burns(0)=Texture'AdventMod.Blood.Burn0'
     Burns(1)=Texture'AdventMod.Blood.Burn1'
     Burns(2)=Texture'AdventMod.Blood.Burn2'
     Burns(3)=Texture'AdventMod.Blood.Burn3'
     BurnChance=0.35
     WallHoles(0)=Texture'AdventMod.Dirt.WallHole0'
     WallHoles(1)=Texture'AdventMod.Dirt.WallHole1'
     WallHoles(2)=Texture'AdventMod.Dirt.WallHole2'
     WallHoles(3)=Texture'AdventMod.Dirt.WallHole3'
     WallHoles(4)=Texture'AdventMod.Dirt.WallHole4'
     WallHoles(5)=Texture'AdventMod.Dirt.WallHole5'
     bWallHoles=True
     bBreaches=True
     BreachHits=3
     BreachHits2=7
     BreachReach=28.000000
     WallBreaches(0)=Texture'AdventMod.Dirt.WallBreach0'
     WallBreaches(1)=Texture'AdventMod.Dirt.WallBreach1'
     WallBreaches(2)=Texture'AdventMod.Dirt.WallBreach2'
     ChipCount=2
     CasingTex=Texture'AdventMod.Blood.Casing0'
     bCasings=True
     MaxClutter=150
     bCorpseShots=True
     bBloodCoats=True
     MaxCoats=10
     CoatTex(0)=Texture'AdventMod.Blood.BloodCoat0'
     CoatTex(1)=Texture'AdventMod.Blood.BloodCoat1'
     CoatTex(2)=Texture'AdventMod.Blood.BloodCoat2'
     AlienCoatTex(0)=Texture'AdventMod.Blood.AlienCoat0'
     AlienCoatTex(1)=Texture'AdventMod.Blood.AlienCoat1'
     AlienCoatTex(2)=Texture'AdventMod.Blood.AlienCoat2'
     bDirt=True
     MaxDirt=60
     MaxRubble=30
     DirtEvery=2.500000
     GrimeTex(0)=Texture'AdventMod.Dirt.DirtGrime0'
     GrimeTex(1)=Texture'AdventMod.Dirt.DirtGrime1'
     CrackTex(0)=Texture'AdventMod.Dirt.DirtCrack0'
     CrackTex(1)=Texture'AdventMod.Dirt.DirtCrack1'
     RubbleTex=Texture'AdventMod.Dirt.DirtRubble0'
     CraterTex=Texture'AdventMod.Dirt.DirtCrater1'
     bWounds=True
     bBodyStreaks=True
     StreakLife=60.000000
     StreaksPerBody=4
     bGooStrings=True
     GooRestMin=18.000000
     GooRestMax=30.000000
     GooStretchMin=2.500000
     GooStretchMax=5.000000
     GooLifeMin=6.000000
     GooLifeMax=12.000000
     GooThick=2.400000
     GooDangle=3.200000
     GooPull=14.000000
     GooHoldMin=0.500000
     GooHoldMax=1.800000
     MaxWounds=48
     WoundsPerBody=5
     SpurtChance=0.350000
     SpurtBeat=0.550000
     SpurtReach=150.000000
     bBlastShake=True
     BlastShake=1.000000
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
     RagdollMaxTimestep=0.016000
     RagdollContactSoftness=0.000000
     bImpacts=True
     MaxHoles=160
     bBlood=True
     MaxDecals=80
     SprayReach=260.000000
     DecalScale=1.600000
}
