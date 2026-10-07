//=============================================================================
// Dying, not just dead (Soldier of Fortune's hit zones, GTA IV's wounded):
//   - every hit is placed on the body's skeleton: head, neck, chest, belly,
//     groin, arm or leg (the nearest named bone; by height when the mesh has none);
//   - a killing blow to the body (not the head, not an overkill that gibs) can
//     leave the victim dying instead of dead: it drops, lies there twitching,
//     a leg or belly wound drags itself a little way along the floor, and it dies
//     some seconds later, or at once if it is hit again. It is out of the fight
//     the moment it drops (its AI is gone), so the game plays as before: the
//     dying is what a dead enemy does, not a second life;
//   - a neck wound pumps blood (GoreFountain), on the dying and on the dead.
//   - optional (off: they change the fight): a leg hit slows the victim (bLimp).
//
// Unreal II's script can't pose bones (MeshNodeSetRotation is ignored: U2TestHub's
// bend test), so everything is the game's own clips: the death clip played slowly
// for the fall, then its hit clip blended over the upper body for the twitches.
// Which clips a mesh has is learned in play: the first of each mesh to die and be
// hit normally shows them on its animation channel, and from then on its kind can
// be dying ("Grime: learned" lines; ClipOverrides sets them by hand). So the first
// enemy of each kind in a level always dies the stock way.
//
// Console: set GoreDying bDying False | DyingChance 1 | ShootZone 2 (a test: the
// nearest enemy takes a killing hit in that zone: 0 head 1 neck 2 chest 3 belly
// 4 groin 5 arm 6 leg) | bLog True.
//=============================================================================
class GoreDying extends Info
	config(U2Gore);

struct ZoneBone
{
	var string Bone;         // the name after the rig's prefix ("Merc ", "Bip01 ")
	var byte Zone;
};

struct Body
{
	var Pawn P;
	var Controller Killer;
	var class<DamageType> DT;
	var vector HitLoc;
	var byte Zone;
	var int Node;
	var float EndTime, NextTwitch, CrawlUntil;
	var name Twitch;
	var vector CrawlDir;
};

struct LastHit
{
	var Pawn P;
	var vector HitLoc;
	var int Damage;
	var byte Zone;
	var int Node;
};

struct Sample
{
	var Pawn P;
	var float When;
	var name Before;
	var byte Kind;           // 0 a hit, 1 a death
};

var config bool bDying;
var config float DyingChance;
var config float MinDyingTime, MaxDyingTime;
var config int MaxDying;            // at once
var config float DyingReach;        // only this close to the player (nobody sees it further away)
var config int OverkillDamage;      // a bigger killing hit kills outright (gibs)
var config float FallRate;          // the death clip's speed for the fall (slower = sinking down)
var config float TwitchRate, TwitchBlend;
var config string TwitchBone;       // the upper-body bone the twitch clip is blended from
var config bool bCrawl;
var config float CrawlSpeed, CrawlTime;
var config bool bFountains;
var config string FountainTemplate, GreenTemplate;   // ParticleGenerator templates, "" = splats only
var config bool bLimp;
var config float LimpScale, LimpTime;
var config array<string> ClipOverrides;   // "MeshName=DeathClip,HitClip"
var config array<string> Prefixes;
var config array<ZoneBone> ZoneBones;
var config bool bLog;
var int ShootZone;                  // console test (-1 none)

var GoreManager Gore;
var array<Body> Bodies;
var array<LastHit> Hits;
var array<Sample> Samples;
var array<Mesh> LMesh;
var array<name> LDeath, LHit;
var array<Mesh> Surveyed;
var array<Pawn> Limping;
var array<float> LimpUntil, LimpSpeed;
var name TmpName;
var int Taken, Finished, Learned;

static function string ZoneName(byte Z)
{
	switch (Z)
	{
		case 0: return "head";
		case 1: return "neck";
		case 2: return "chest";
		case 3: return "belly";
		case 4: return "groin";
		case 5: return "arm";
		case 6: return "leg";
	}
	return "?";
}

// the zone of a hit, and the bone it is nearest (0 when placed by height)
function byte ZoneOf(Pawn P, vector HitLoc, out int BestNode)
{
	local int i, j, N;
	local float D, BestD, H;
	local byte Best;
	local bool bFound;

	BestD = 1000000;
	BestNode = 0;
	for (i = 0; i < ZoneBones.Length; i++)
		for (j = 0; j < Prefixes.Length; j++)
		{
			N = P.MeshGetNodeNamed(Prefixes[j] $ ZoneBones[i].Bone);
			if (N == 0)
				continue;
			D = VSize(P.MeshNodeGetTranslation(N, MESHNODEREL_World) - HitLoc);
			if (D < BestD)
			{
				BestD = D;
				Best = ZoneBones[i].Zone;
				BestNode = N;
				bFound = true;
			}
			break;
		}
	if (bFound)
		return Best;
	// no named bones: by height in the collision cylinder (-1 feet .. 1 top of the head)
	H = (HitLoc.Z - P.Location.Z) / FMax(P.CollisionHeight, 1);
	if (H > 0.78) return 0;
	if (H > 0.62) return 1;
	if (H > 0.25) return 2;
	if (H > 0.0)  return 3;
	if (H > -0.15) return 4;
	return 6;
}

// a hit (GoreRules.NetDamage), before it is taken off the victim's health
function NoteHit(Pawn P, Pawn Instigator, vector HitLoc, int Damage, class<DamageType> DT)
{
	local int i, Node;
	local byte Z;
	local LastHit L;

	if (P == None || P.Mesh == None)
		return;
	Survey(P);
	Z = ZoneOf(P, HitLoc, Node);
	if (bLog)
		Log("U2Gore: zone "$P.Name$" "$ZoneName(Z)$" ("$Damage$" damage, health "$P.Health$")");
	for (i = 0; i < Hits.Length; i++)
		if (Hits[i].P == P || Hits[i].P == None || Hits[i].P.bDeleteMe)
			break;
	if (i >= 24)
		i = Rand(24);
	L.P = P;
	L.HitLoc = HitLoc;
	L.Damage = Damage;
	L.Zone = Z;
	L.Node = Node;
	Hits[i] = L;
	// learn the mesh's hit clip from a hit it lives through
	if (Damage < P.Health && LearnedAt(P.Mesh) >= 0 && LHit[LearnedAt(P.Mesh)] == '')
		AddSample(P, 0);
	if (bLimp && Z == 6 && Damage < P.Health && !P.IsRealPlayer())
		Limp(P);
}

function int LastHitOf(Pawn P)
{
	local int i;

	for (i = 0; i < Hits.Length; i++)
		if (Hits[i].P == P)
			return i;
	return -1;
}

// ---- the clips ------------------------------------------------------------------------------
function int LearnedAt(Mesh M)
{
	local int i;

	for (i = 0; i < LMesh.Length; i++)
		if (LMesh[i] == M)
			return i;
	i = LMesh.Length;
	LMesh[i] = M;
	LDeath[i] = '';
	LHit[i] = '';
	Overrides(i);
	return i;
}

// ClipOverrides: "MeshName=DeathClip,HitClip" (names made from text through SetPropertyText)
function Overrides(int i)
{
	local int k, Eq, Comma;
	local string S, Clips;

	for (k = 0; k < ClipOverrides.Length; k++)
	{
		S = ClipOverrides[k];
		Eq = InStr(S, "=");
		if (Eq < 0 || !(Left(S, Eq) ~= string(LMesh[i].Name)))
			continue;
		Clips = Mid(S, Eq + 1);
		Comma = InStr(Clips, ",");
		if (Comma < 0)
			Comma = Len(Clips);
		SetPropertyText("TmpName", Left(Clips, Comma));
		LDeath[i] = TmpName;
		if (Comma < Len(Clips))
		{
			SetPropertyText("TmpName", Mid(Clips, Comma + 1));
			LHit[i] = TmpName;
		}
		Log("U2Gore: clips for "$LMesh[i].Name$" set by hand: death "$LDeath[i]$", hit "$LHit[i]);
	}
}

function AddSample(Pawn P, byte Kind)
{
	local Sample S;

	S.P = P;
	S.Kind = Kind;
	S.When = Level.TimeSeconds + 0.15 + 0.15 * Kind;
	S.Before = P.MeshAgentGetChannelScriptName(0);
	Samples[Samples.Length] = S;
}

// what the animation channel switched to after the hit or the death: that's the clip
function TakeSamples()
{
	local int i, k;
	local name Now;

	for (i = Samples.Length - 1; i >= 0; i--)
	{
		if (Samples[i].P == None || Samples[i].P.bDeleteMe)
		{
			Samples.Remove(i, 1);
			continue;
		}
		if (Level.TimeSeconds < Samples[i].When)
			continue;
		Now = Samples[i].P.MeshAgentGetChannelScriptName(0);
		k = LearnedAt(Samples[i].P.Mesh);
		if (Now != '' && Now != Samples[i].Before)
		{
			if (Samples[i].Kind == 1 && LDeath[k] == '')
			{
				LDeath[k] = Now;
				Learned++;
				Log("U2Gore: learned "$Samples[i].P.Mesh.Name$" death clip "$Now$" (from "$Samples[i].P.Name$")");
			}
			else if (Samples[i].Kind == 0 && LHit[k] == '')
			{
				LHit[k] = Now;
				Learned++;
				Log("U2Gore: learned "$Samples[i].P.Mesh.Name$" hit clip "$Now$" (from "$Samples[i].P.Name$")");
			}
		}
		else if (bLog)
			Log("U2Gore: "$Samples[i].P.Name$" channel 0 still "$Now$" after the "$Pick(Samples[i].Kind == 1, "death", "hit"));
		Samples.Remove(i, 1);
	}
}

function string Pick(bool b, string T, string F)
{
	if (b)
		return T;
	return F;
}

// once per mesh: the animation agent's actions and channels (names for ClipOverrides)
function Survey(Pawn P)
{
	local int i;
	local string L;

	for (i = 0; i < Surveyed.Length; i++)
		if (Surveyed[i] == P.Mesh)
			return;
	Surveyed[Surveyed.Length] = P.Mesh;
	L = "U2Gore: survey "$P.Mesh.Name$" ("$P.Class.Name$") actions:";
	for (i = 0; i < P.MeshAgentGetActionCount(); i++)
	{
		L = L$" "$P.MeshAgentGetActionName(i);
		if (Len(L) > 900)
		{
			Log(L);
			L = "U2Gore: survey "$P.Mesh.Name$" actions (more):";
		}
	}
	Log(L);
	for (i = 0; i < P.MeshAgentGetChannelCount(); i++)
		Log("U2Gore: survey "$P.Mesh.Name$" channel "$i$" "$P.MeshAgentGetChannelName(i)$" playing "$P.MeshAgentGetChannelScriptName(i));
}

// ---- dying ----------------------------------------------------------------------------------
// GoreRules.PreventDeath: true = this one is dying, not dead (yet)
function bool Take(Pawn P, Controller Killer, class<DamageType> DT, vector HitLocation)
{
	local int h, k, i;
	local Body B;
	local PlayerController PC;
	local bool bNear;

	if (P == None || P.Mesh == None)
		return false;
	for (i = 0; i < Bodies.Length; i++)
		if (Bodies[i].P == P)
		{
			// a dying body hit again (or its time is up): dead now, the game's own way
			Bodies.Remove(i, 1);
			Finished++;
			return false;
		}
	h = LastHitOf(P);
	k = LearnedAt(P.Mesh);
	// the game's own death this time: learn its clip, and a neck wound still pumps
	if (!bDying || P.IsRealPlayer() || P.Controller == None || class'GoreManager'.static.BloodKind(P) == 0
		|| h < 0 || Hits[h].Zone == 0 || Hits[h].Damage > OverkillDamage || LDeath[k] == ''
		|| Bodies.Length >= MaxDying || FRand() > DyingChance)
	{
		if (LDeath[k] == '')
			AddSample(P, 1);
		if (h >= 0 && Hits[h].Zone == 1 && bFountains)
			Fountain(P, Hits[h].Node, 1.0);
		if (bLog && h >= 0)
			Log("U2Gore: "$P.Name$" dies the stock way (zone "$ZoneName(Hits[h].Zone)$", death clip known "$(LDeath[k] != '')$")");
		return false;
	}
	foreach DynamicActors(class'PlayerController', PC)
		if (PC.Pawn != None && VSize(PC.Pawn.Location - P.Location) < DyingReach)
			bNear = true;
	if (!bNear)
		return false;

	B.P = P;
	B.Killer = Killer;
	B.DT = DT;
	B.HitLoc = HitLocation;
	B.Zone = Hits[h].Zone;
	B.Node = Hits[h].Node;
	B.EndTime = Level.TimeSeconds + MinDyingTime + FRand() * (MaxDyingTime - MinDyingTime);
	B.NextTwitch = Level.TimeSeconds + 1.2 + FRand();
	B.Twitch = LHit[k];
	if (bCrawl && (B.Zone == 3 || B.Zone == 6))
	{
		B.CrawlUntil = Level.TimeSeconds + 1.5 + CrawlTime;
		B.CrawlDir = vector(P.Rotation);
		B.CrawlDir.Z = 0;
		B.CrawlDir = Normal(B.CrawlDir);
	}
	// out of the fight: no AI (it stands still as a model would: U2TestHub's dummies), the
	// agent's channels ours. Listed first: if the engine kills a pawn whose controller goes,
	// Take sees it here and lets that death through.
	Bodies[Bodies.Length] = B;
	P.Health = 1;
	if (P.Controller != None)
		P.Controller.Destroy();
	if (P == None || P.bDeleteMe || P.Health <= 0)
	{
		Log("U2Gore: "$P$" died when its AI was removed: the dying phase can't work this way");
		return false;
	}
	P.Velocity = vect(0,0,0);
	P.Acceleration = vect(0,0,0);
	P.MeshAgentEnableChannel(0, false);
	P.PlayAnim(LDeath[k], FallRate, 0.2, 0);
	if (B.Twitch != '' && P.MeshAgentGetChannelCount() > 1)
	{
		P.MeshAgentEnableChannel(1, false);
		SetPropertyText("TmpName", TwitchBone);
		P.AnimBlendParams(1, TwitchBlend, 0.2, 0.2, TmpName);
	}
	else
		Bodies[Bodies.Length - 1].Twitch = '';
	if (bFountains && B.Zone == 1)
		Fountain(P, B.Node, 1.0);
	else if (bFountains && B.Zone == 2)
		Fountain(P, B.Node, 0.6);
	Taken++;
	Log("U2Gore: "$P.Name$" dying ("$ZoneName(B.Zone)$" wound, "$int(B.EndTime - Level.TimeSeconds)$" s, death clip "$LDeath[k]$", twitch "$B.Twitch$")");
	return true;
}

function Fountain(Pawn P, int Node, float Strength)
{
	local GoreFountain F;
	local string T;

	if (Gore == None)
		return;
	F = Spawn(class'GoreFountain', self,, P.Location);
	if (F == None)
		return;
	T = FountainTemplate;
	if (class'GoreManager'.static.BloodKind(P) == 2)
		T = GreenTemplate;
	F.Setup(P, Node, class'GoreManager'.static.BloodKind(P), Gore, Strength, T);
}

function Finish(int i)
{
	local Pawn P;

	P = Bodies[i].P;
	if (P == None || P.bDeleteMe || P.Health <= 0)
	{
		Bodies.Remove(i, 1);
		return;
	}
	if (bLog)
		Log("U2Gore: "$P.Name$" dies after its time");
	// Take sees it in Bodies and lets this death through
	P.TakeDamage(P.Health + 5, None, Bodies[i].HitLoc, vect(0,0,0), Bodies[i].DT);
	if (P != None && !P.bDeleteMe && P.Health > 0)
	{
		P.Health = 0;
		P.Died(Bodies[i].Killer, Bodies[i].DT, Bodies[i].HitLoc, vect(0,0,0));
	}
	for (i = 0; i < Bodies.Length; i++)
		if (Bodies[i].P == P)
		{
			Bodies.Remove(i, 1);
			break;
		}
}

function DyingTick(float DeltaTime)
{
	local int i;
	local Pawn P;
	local vector Next, HitL, HitN;

	for (i = Bodies.Length - 1; i >= 0; i--)
	{
		P = Bodies[i].P;
		if (P == None || P.bDeleteMe || P.Health <= 0)
		{
			Bodies.Remove(i, 1);
			continue;
		}
		if (Level.TimeSeconds >= Bodies[i].EndTime)
		{
			Finish(i);
			continue;
		}
		P.Velocity = vect(0,0,0);
		P.Acceleration = vect(0,0,0);
		if (Bodies[i].Twitch != '' && Level.TimeSeconds >= Bodies[i].NextTwitch)
		{
			P.PlayAnim(Bodies[i].Twitch, TwitchRate * (0.8 + 0.4 * FRand()), 0.3, 1);
			Bodies[i].NextTwitch = Level.TimeSeconds + 1.0 + 1.8 * FRand();
		}
		// a leg or belly wound drags itself along the floor, slowly, while it can
		if (Bodies[i].CrawlUntil > Level.TimeSeconds && Level.TimeSeconds > Bodies[i].CrawlUntil - CrawlTime)
		{
			Next = P.Location + Bodies[i].CrawlDir * CrawlSpeed * DeltaTime;
			if (Trace(HitL, HitN, Next + Bodies[i].CrawlDir * P.CollisionRadius, P.Location, false) != None
				|| Trace(HitL, HitN, Next - vect(0,0,1) * (P.CollisionHeight + 24), Next, false) == None
				|| !P.SetLocation(Next))
				Bodies[i].CrawlUntil = 0;
		}
	}
}

// ---- limping (bLimp, off by default) -----------------------------------------------------------
function Limp(Pawn P)
{
	local int i;

	for (i = 0; i < Limping.Length; i++)
		if (Limping[i] == P)
		{
			LimpUntil[i] = Level.TimeSeconds + LimpTime;
			return;
		}
	Limping[i] = P;
	LimpSpeed[i] = P.GroundSpeed;
	LimpUntil[i] = Level.TimeSeconds + LimpTime;
	P.GroundSpeed *= LimpScale;
}

function Limps()
{
	local int i;

	for (i = Limping.Length - 1; i >= 0; i--)
		if (Limping[i] == None || Limping[i].bDeleteMe || Level.TimeSeconds >= LimpUntil[i])
		{
			if (Limping[i] != None && !Limping[i].bDeleteMe)
				Limping[i].GroundSpeed = LimpSpeed[i];
			Limping.Remove(i, 1);
			LimpUntil.Remove(i, 1);
			LimpSpeed.Remove(i, 1);
		}
}

// ---- the console test: a killing hit in a zone on the nearest enemy ------------------------------
function TestShot(int Z)
{
	local PlayerController PC;
	local Pawn P, Best;
	local float D, BestD;
	local int i, j, N;
	local vector Spot;

	foreach DynamicActors(class'PlayerController', PC)
		break;
	if (PC == None || PC.Pawn == None)
		return;
	// the nearest fighting enemy; when there is none, the nearest dying one (a finishing hit)
	BestD = 2000;
	foreach DynamicActors(class'Pawn', P)
		if (P != PC.Pawn && P.Health > 0 && P.Controller != None)
		{
			D = VSize(P.Location - PC.Pawn.Location);
			if (D < BestD)
			{
				BestD = D;
				Best = P;
			}
		}
	for (i = 0; Best == None && i < Bodies.Length; i++)
		if (Bodies[i].P != None && !Bodies[i].P.bDeleteMe)
			Best = Bodies[i].P;
	if (Best == None)
	{
		Log("U2Gore: test shot: no enemy within 2000");
		return;
	}
	Spot = Best.Location;
	for (i = 0; i < ZoneBones.Length && Spot == Best.Location; i++)
		if (ZoneBones[i].Zone == Z)
			for (j = 0; j < Prefixes.Length; j++)
			{
				N = Best.MeshGetNodeNamed(Prefixes[j] $ ZoneBones[i].Bone);
				if (N != 0)
				{
					Spot = Best.MeshNodeGetTranslation(N, MESHNODEREL_World);
					break;
				}
			}
	Log("U2Gore: test shot at "$Best.Name$"'s "$ZoneName(Z));
	Best.TakeDamage(Best.Health + 5, PC.Pawn, Spot, Normal(Best.Location - PC.Pawn.Location) * 3000, class'DamageType');
}

event Tick(float DeltaTime)
{
	if (ShootZone >= 0)
	{
		TestShot(ShootZone);
		ShootZone = -1;
	}
	if (Samples.Length > 0)
		TakeSamples();
	if (Bodies.Length > 0)
		DyingTick(DeltaTime);
	if (Limping.Length > 0)
		Limps();
}

defaultproperties
{
	bDying=True
	DyingChance=0.600000
	MinDyingTime=4.000000
	MaxDyingTime=9.000000
	MaxDying=3
	DyingReach=2500.000000
	OverkillDamage=120
	FallRate=0.600000
	TwitchRate=0.450000
	TwitchBlend=0.400000
	TwitchBone="Merc Spine1"
	bCrawl=True
	CrawlSpeed=10.000000
	CrawlTime=4.000000
	bFountains=True
	FountainTemplate=""
	GreenTemplate="Blood.ParticleSalamander6"
	bLimp=False
	LimpScale=0.600000
	LimpTime=5.000000
	Prefixes(0)="Merc "
	Prefixes(1)="Bip01 "
	Prefixes(2)="Marine "
	ZoneBones(0)=(Bone="Head",Zone=0)
	ZoneBones(1)=(Bone="Neck",Zone=1)
	ZoneBones(2)=(Bone="Spine2",Zone=2)
	ZoneBones(3)=(Bone="Spine1",Zone=2)
	ZoneBones(4)=(Bone="Spine",Zone=3)
	ZoneBones(5)=(Bone="Pelvis",Zone=4)
	ZoneBones(6)=(Bone="L UpperArm",Zone=5)
	ZoneBones(7)=(Bone="R UpperArm",Zone=5)
	ZoneBones(8)=(Bone="L Forearm",Zone=5)
	ZoneBones(9)=(Bone="R Forearm",Zone=5)
	ZoneBones(10)=(Bone="L Hand",Zone=5)
	ZoneBones(11)=(Bone="R Hand",Zone=5)
	ZoneBones(12)=(Bone="L Thigh",Zone=6)
	ZoneBones(13)=(Bone="R Thigh",Zone=6)
	ZoneBones(14)=(Bone="L Calf",Zone=6)
	ZoneBones(15)=(Bone="R Calf",Zone=6)
	ZoneBones(16)=(Bone="L Foot",Zone=6)
	ZoneBones(17)=(Bone="R Foot",Zone=6)
	ShootZone=-1
	bHidden=True
	RemoteRole=ROLE_None
}
