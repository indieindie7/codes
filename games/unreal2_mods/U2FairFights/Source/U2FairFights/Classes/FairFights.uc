//=============================================================================
// U2FairFights - "Fair Fights & Punch": the two things players disliked most.
//
// Fair fights (enemies):
//   ReactionDelay   an enemy that has just spotted you can't fire for this long
//   NPCSpreadMul    enemy hitscan spread multiplier (the game gives NPCs the
//                   same pinpoint spread as the player: assault rifle 3 deg)
//   BurstSpread     extra spread (degrees) at the start of a burst, settling
//                   over BurstSettle seconds - the first shots miss, sustained
//                   fire finds you: dodgeable, readable
//   SightRadiusCap  some mercs see 35000 units ("shot from anywhere"); capped
//
// Punch (feedback):
//   KillHitstop     a beat of slow-motion when you kill something (seconds of
//                   real time); HitstopDilation is the speed during it
//   KnockDownScale  lowers the momentum needed to knock an enemy down
//   MaxRagdolls     more simultaneous ragdoll deaths (the game allows 5)
//   BodyTime        bodies stay this long instead of sinking away at once
//
// Add U2FairFights.FairFights to the Mutator= line in User.ini [DefaultPlayer].
// Settings: [U2FairFights.FairFights] in User.ini.
//=============================================================================
class FairFights extends Mutator
	config(User);

var() config bool  bFairFights;
var() config float ReactionDelay;
var() config float NPCSpreadMul;
var() config float BurstSpread;
var() config float BurstSettle;
var() config float SightRadiusCap;
var() config float HitOddsScale;      // the game's own per-shot "try to hit" odds (12-62% by distance), scaled
var() config float AcquireGrace;      // seconds after spotting you during which its odds are reduced (game: 1.0)
var() config float HitGrace;          // seconds after being hurt during which its odds are reduced (game: 0.5)
var() config bool  bTokens;           // attack tokens: only a few enemies may shoot at a time, the rest reposition
var() config int   RangedTokens;      // how many may shoot at once
var() config int   TokensPer;         // one more token for every this many engaged enemies beyond the first few
var() config float TokenTime;         // seconds between re-deals
var float NextDeal;

var() config bool  bPunch;
var() config float KillHitstop;
var() config float HitstopDilation;
var() config float KnockDownScale;
var() config int   MaxRagdolls;
var() config float BodyTime;
var() config float KickScale;         // view kick per shot of your own weapon (0 = off); scaled per weapon below
var() config bool  bHitTick;          // a tick at the crosshair and a click when you hit something
var() config float HitTickTime;
var() config bool  bEnemyTracers;     // a visible line along every enemy hitscan shot

var int LastPlayerAmmo;
var U2Weapon LastPlayerWeapon;
var float LastKickTime;
var ComponentHandle Tick_, KillTick_;
var float TickUntil;
var Sound HitSound, KillSound;

var() config bool  bLog;               // FairFights: lines in Unreal2.log (tests)

struct WatchedNPC
{
	var U2NPCControllerBasic C;
	var Actor LastEnemy;
	var float AcquiredAt;             // when it last got the player as its enemy
	var bool bFirstShotLogged;
	var U2Weapon W;
	var float BaseSpread;             // the weapon's own spread, before us
	var float BurstStart;
	var bool bWasFiring;
	var int LastAmmo;
	var float LastTracer;
	var bool bHolder;
	var float LastToken;
	var float Score;
};
var array<WatchedNPC> NPCs;
var Hitstop Beat;
var float LastCountLog;
var int Tracers;

event PostBeginPlay()
{
	local FairRules R;

	Super.PostBeginPlay();
	SaveConfig();
	if (bPunch && U2GameInfo(Level.Game) != None)
		U2GameInfo(Level.Game).MaxRagdollDeaths = Max(U2GameInfo(Level.Game).MaxRagdollDeaths, MaxRagdolls);
	R = Spawn(class'FairRules');
	R.Settings = Self;
	if (Level.Game.GameRulesModifiers == None)
		Level.Game.GameRulesModifiers = R;
	else
		Level.Game.GameRulesModifiers.AddGameRules(R);
	SetTimer(0.5, true);
	Log("FairFights: active (fair "$bFairFights$", punch "$bPunch$")");
}

// every actor passes through here as it spawns, level-placed ones included
function bool CheckReplacement(Actor Other, out byte bSuperRelevant)
{
	local U2Pawn P;

	P = U2Pawn(Other);
	if (P != None && !P.IsRealPlayer())
	{
		if (bFairFights && SightRadiusCap > 0)
			P.SightRadius = FMin(P.SightRadius, SightRadiusCap);
		if (bPunch)
		{
			P.MinKnockDownMomentumThreshold *= KnockDownScale;
			if (BodyTime > 0)
			{
				P.bQuickCarcassCleanup = false;
				P.TimeBeforeCarcassDestroyed = BodyTime;
			}
		}
	}
	return true;
}

// keep the list of enemy controllers current
event Timer()
{
	local U2NPCControllerBasic C;
	local int i;
	local bool bKnown;

	for (i = NPCs.Length - 1; i >= 0; i--)
		if (NPCs[i].C == None || NPCs[i].C.bDeleteMe || NPCs[i].C.Pawn == None)
			NPCs.Remove(i, 1);
	if (!bFairFights)
		return;
	foreach DynamicActors(class'U2NPCControllerBasic', C)
	{
		if (C.Pawn == None)
			continue;
		bKnown = false;
		for (i = 0; i < NPCs.Length; i++)
			if (NPCs[i].C == C)
			{
				bKnown = true;
				break;
			}
		if (!bKnown)
		{
			i = NPCs.Length;
			NPCs.Length = i + 1;
			NPCs[i].C = C;
			NPCs[i].LastEnemy = None;      // whatever it targets now counts as just spotted
			// the AI decides per shot whether to try to hit or miss on purpose;
			// fewer tries, and longer grace after spotting you or being hurt
			C.TryToHitInstantBaseOddsMin *= HitOddsScale;
			C.TryToHitInstantBaseOddsMax *= HitOddsScale;
			C.TryToHitProjectileBaseOddsMin *= HitOddsScale;
			C.TryToHitProjectileBaseOddsMax *= HitOddsScale;
			C.MaxAffectedByAcquisitionTime = FMax(C.MaxAffectedByAcquisitionTime, AcquireGrace);
			C.MaxAffectedByHitTime = FMax(C.MaxAffectedByHitTime, HitGrace);
		}
	}
	if (bTokens && Level.TimeSeconds >= NextDeal)
	{
		NextDeal = Level.TimeSeconds + TokenTime;
		Deal();
	}
	if (bLog && NPCs.Length > 0 && Level.TimeSeconds - LastCountLog > 5)
	{
		LastCountLog = Level.TimeSeconds;
		Log("FairFights: watching "$NPCs.Length$" enemies, tracer weapons "$Tracers);
	}
	Enable('Tick');
}

event Tick(float DeltaTime)
{
	local int i;
	local U2NPCControllerBasic C;
	local U2Weapon W;
	local float Settle;

	if (bPunch)
		PlayerKick(DeltaTime);
	if (!bFairFights)
		return;
	for (i = 0; i < NPCs.Length; i++)
	{
		C = NPCs[i].C;
		if (C == None || C.Pawn == None)
			continue;

		// just spotted the player: hold fire for a moment
		if (C.GetTarget() != NPCs[i].LastEnemy)
		{
			NPCs[i].LastEnemy = C.GetTarget();
			if (NPCs[i].LastEnemy != None && NPCs[i].LastEnemy.IsRealPlayer())
			{
				NPCs[i].AcquiredAt = Level.TimeSeconds;
				NPCs[i].bFirstShotLogged = false;
				if (ReactionDelay > 0)
					C.BCBlockFiring(ReactionDelay, true);
				if (bLog)
					Log("FairFights: "$C.Pawn.Name$" spotted the player at "$Level.TimeSeconds);
			}
		}

		// hitscan spread: wider than the player's, widest at the start of a burst
		W = U2Weapon(C.Pawn.Weapon);
		if (W != NPCs[i].W)
		{
			NPCs[i].W = W;
			if (W != None)
			{
				NPCs[i].BaseSpread = W.default.TraceSpreadFire;
				if (bEnemyTracers)
					AddTracer(W);
				if (bLog && NPCs[i].BaseSpread > 0)
					Log("FairFights: "$C.Pawn.Name$" "$W.Name$" spread "$NPCs[i].BaseSpread$" -> "$(NPCs[i].BaseSpread * NPCSpreadMul)$" (+"$BurstSpread$" at burst start)");
			}
			NPCs[i].bWasFiring = false;
		}
		if (W != None && NPCs[i].BaseSpread > 0)
		{
			if (W.bFiring || W.bAltFiring)
			{
				if (!NPCs[i].bWasFiring)
					NPCs[i].BurstStart = Level.TimeSeconds;
				NPCs[i].bWasFiring = true;
			}
			else if (NPCs[i].bWasFiring && Level.TimeSeconds - NPCs[i].BurstStart > BurstSettle)
				NPCs[i].bWasFiring = false;
			Settle = 0;
			if (BurstSettle > 0)
				Settle = FClamp(1.0 - (Level.TimeSeconds - NPCs[i].BurstStart) / BurstSettle, 0, 1);
			if (!NPCs[i].bWasFiring)
				Settle = 1;
			W.TraceSpreadFire = NPCs[i].BaseSpread * NPCSpreadMul + BurstSpread * Settle;
		}

	}
}

function PlayerController LocalPC()
{
	local Controller C;
	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None)
			return PlayerController(C);
	return None;
}

// a shot of the player's own weapon (ammo went down): a short camera kick
// sized to the weapon
function PlayerKick(float DeltaTime)
{
	local PlayerController PC;
	local U2Weapon W;
	local int Ammo;
	local float Mag;

	// the crosshair tick times out here too
	if (TickUntil > 0 && Level.TimeSeconds > TickUntil)
	{
		TickUntil = 0;
		if (~Tick_)
			Tick_ = class'UIConsole'.static.DestroyComponent(Tick_);
		if (~KillTick_)
			KillTick_ = class'UIConsole'.static.DestroyComponent(KillTick_);
	}

	if (KickScale <= 0)
		return;
	PC = LocalPC();
	if (PC == None || PC.Pawn == None)
		return;
	W = U2Weapon(PC.Pawn.Weapon);
	if (W != LastPlayerWeapon)
	{
		LastPlayerWeapon = W;
		if (W != None)
			LastPlayerAmmo = W.GetAmmoAmount();
		return;
	}
	if (W == None)
		return;
	Ammo = W.GetAmmoAmount();
	if (Ammo < LastPlayerAmmo && (W.bFiring || W.bAltFiring) && Level.TimeSeconds - LastKickTime > 0.06)
	{
		Mag = KickFor(W) * KickScale;
		if (Mag > 0)
		{
			PC.ShakeView(Mag, 0.12);
			LastKickTime = Level.TimeSeconds;
			if (bLog)
				Log("FairFights: kick "$Mag$" ("$W.Class.Name$")");
		}
	}
	LastPlayerAmmo = Ammo;
}

// kick magnitude by weapon (view offset units)
function float KickFor(U2Weapon W)
{
	local string N;

	N = Caps(string(W.Class.Name));
	if (InStr(N, "FLAME") >= 0 || InStr(N, "LEECH") >= 0 || InStr(N, "TAKKRA") >= 0)
		return 0;                       // continuous / hands-off weapons
	if (InStr(N, "SHOTGUN") >= 0 || InStr(N, "FLAK") >= 0)   return 7;
	if (InStr(N, "ROCKET") >= 0)                              return 9;
	if (InStr(N, "SNIPER") >= 0)                              return 6;
	if (InStr(N, "GRENADE") >= 0)                             return 5;
	if (InStr(N, "SINGULARITY") >= 0)                         return 8;
	if (InStr(N, "ASSAULT") >= 0 || InStr(N, "RIPPER") >= 0)  return 1.6;
	if (InStr(N, "PISTOL") >= 0 || InStr(N, "DISPERSION") >= 0 || InStr(N, "BIO") >= 0) return 1.2;
	return 2;
}

// the player hit something: a click and a tick at the crosshair
function PlayerHitSomething(Pawn Victim, bool bKill)
{
	local PlayerController PC;

	if (!bPunch || !bHitTick)
		return;
	PC = LocalPC();
	if (PC == None || PC.Pawn == None)
		return;
	if (bKill && KillSound != None)
		PC.Pawn.PlaySound(KillSound, SLOT_Interface, 0.8);
	else if (HitSound != None)
		PC.Pawn.PlaySound(HitSound, SLOT_Interface, 0.5);
	if (bKill)
	{
		if (~Tick_)
			Tick_ = class'UIConsole'.static.DestroyComponent(Tick_);
		if (!(~KillTick_))
		{
			KillTick_ = class'UIConsole'.static.LoadComponent("FairFights", "KillTick");
			if (~KillTick_)
			{
				class'UIConsole'.static.SetOwner(KillTick_, Self);
				class'UIConsole'.static.AddComponent(KillTick_);
			}
		}
	}
	else if (!(~Tick_) && !(~KillTick_))
	{
		Tick_ = class'UIConsole'.static.LoadComponent("FairFights", "HitTick");
		if (~Tick_)
		{
			class'UIConsole'.static.SetOwner(Tick_, Self);
			class'UIConsole'.static.AddComponent(Tick_);
		}
	}
	TickUntil = Level.TimeSeconds + HitTickTime;
	if (bLog)
		Log("FairFights: tick kill="$bKill$" shown="$((~Tick_) || (~KillTick_)));
	Enable('Tick');
}

// give an enemy hitscan weapon the sniper rifle's tracer as an extra
// weapon effect: the weapon's own code then draws a line along every shot
// (the assault rifle already updates such a tracer; it just has none)
function AddTracer(U2Weapon W)
{
	local int i;

	if (W == None || !W.bInstantHit)
		return;
	for (i = 0; i < W.DecoEffects.Length; i++)
		if (W.DecoEffects[i].Particles != None && PulseLineGenerator(W.DecoEffects[i].Particles) != None)
			return;                         // already has a line tracer (sniper rifle)
	i = W.DecoEffects.Length;
	if (i != 1)
		return;                             // the rifle's UpdateTracer reads DecoEffects[1]
	W.DecoEffects.Length = 2;
	W.DecoEffects[1].AnimSequence = 'Fire';
	W.DecoEffects[1].DecoClass = class'PulseLineGenerator';
	W.DecoEffects[1].Particles = PulseLineGenerator'SniperTracer.PulseLineGenerator1';
	W.DecoEffects[1].MountNode = "#Muzzleflash";
	W.DecoEffects[1].bTriggerUpdateOnly = true;
	W.DecoEffects[1].bRequiresWorldZBuffer = true;
	W.ConstructDeco(1);
	Tracers++;
}

// attack tokens: of the enemies engaging the player, the best placed few may
// shoot for the next TokenTime; the others hold fire (and keep repositioning,
// their movement isn't touched). Turns rotate: waiting counts toward the score.
function Deal()
{
	local int i, j, Engaged, Tokens, Given;
	local Pawn Player;
	local vector Eye;
	local array<int> Order;
	local string Names;

	Player = None;
	for (i = 0; i < NPCs.Length; i++)
	{
		NPCs[i].Score = -1;
		if (NPCs[i].C == None || NPCs[i].C.Pawn == None || NPCs[i].C.Pawn.Health <= 0 || NPCs[i].C.Pawn.Weapon == None)
			continue;
		if (NPCs[i].LastEnemy == None || !NPCs[i].LastEnemy.IsRealPlayer())
			continue;
		Player = Pawn(NPCs[i].LastEnemy);
		Engaged++;
		Eye = NPCs[i].C.Pawn.Location + vect(0,0,1) * NPCs[i].C.Pawn.BaseEyeHeight;
		NPCs[i].Score = (Level.TimeSeconds - NPCs[i].LastToken) * 100 - VSize(Player.Location - Eye) * 0.2;
		if (FastTrace(Player.Location, Eye))
			NPCs[i].Score += 800;
		// insertion into Order, best first
		for (j = 0; j < Order.Length; j++)
			if (NPCs[i].Score > NPCs[Order[j]].Score)
				break;
		Order.Insert(j, 1);
		Order[j] = i;
	}
	if (Engaged == 0)
		return;
	Tokens = RangedTokens;
	if (TokensPer > 0 && Engaged > 4)
		Tokens += (Engaged - 4) / TokensPer;
	for (j = 0; j < Order.Length; j++)
	{
		i = Order[j];
		if (Given < Tokens)
		{
			Given++;
			if (!NPCs[i].bHolder)
				NPCs[i].C.BCBlockFiring(0.05, false);   // may fire from now on
			NPCs[i].bHolder = true;
			NPCs[i].LastToken = Level.TimeSeconds;
			Names = Names$" "$NPCs[i].C.Pawn.Name;
		}
		else
		{
			NPCs[i].C.BCBlockFiring(TokenTime + 0.6, true);
			NPCs[i].bHolder = false;
		}
	}
	if (bLog)
		Log("FairFights: tokens "$Given$" of "$Engaged$" engaged at "$Level.TimeSeconds$":"$Names);
}

// a hit on the player: for the log, how long after being spotted the first one lands
function PlayerHit(Pawn instigatedBy, int Damage)
{
	local int i;

	if (!bLog)
		return;
	for (i = 0; i < NPCs.Length; i++)
		if (NPCs[i].C != None && NPCs[i].C.Pawn == instigatedBy)
		{
			if (!NPCs[i].bFirstShotLogged)
			{
				NPCs[i].bFirstShotLogged = true;
				Log("FairFights: first hit by "$instigatedBy.Name$" "$(Level.TimeSeconds - NPCs[i].AcquiredAt)$"s after spotting, damage "$Damage$" t="$Level.TimeSeconds$" token="$NPCs[i].bHolder);
			}
			else
				Log("FairFights: hit by "$instigatedBy.Name$" damage "$Damage$" t="$Level.TimeSeconds$" token="$NPCs[i].bHolder);
			return;
		}
	Log("FairFights: hit by "$instigatedBy$" damage "$Damage);
}

// the player killed something: a beat of slow motion
function PlayerKilled(Pawn Killed)
{
	if (!bPunch || KillHitstop <= 0)
		return;
	if (Beat == None)
		Beat = Spawn(class'Hitstop');
	Beat.Start(KillHitstop, HitstopDilation);
}

defaultproperties
{
	bFairFights=True
	ReactionDelay=0.600000
	NPCSpreadMul=1.500000
	BurstSpread=3.000000
	BurstSettle=1.200000
	SightRadiusCap=6000.000000
	HitOddsScale=0.700000
	AcquireGrace=1.500000
	HitGrace=0.800000
	bTokens=True
	RangedTokens=2
	TokensPer=4
	TokenTime=2.000000
	bPunch=True
	KillHitstop=0.070000
	HitstopDilation=0.250000
	KnockDownScale=0.600000
	MaxRagdolls=12
	BodyTime=90.000000
	KickScale=1.000000
	bHitTick=True
	HitTickTime=0.120000
	bEnemyTracers=True
	HitSound=Sound'UISounds.MouseDown'
	KillSound=Sound'UISounds.MousePowerdown'
	bLog=True
	RemoteRole=ROLE_None
}
