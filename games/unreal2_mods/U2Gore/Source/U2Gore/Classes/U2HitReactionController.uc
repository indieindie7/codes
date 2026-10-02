//=============================================================================
// U2Gore - partial/"semi-dynamic" ragdoll. On a hit that's too weak to kill
// but hard enough to matter, the hit bone (and whatever's below it in the
// skeleton) goes physics-driven for LooseDuration while the rest of the body
// keeps playing its normal animation, then blends back. On a lethal hit it
// hands off to the engine's own full PHYS_KarmaRagdoll instead of managing
// individual bones any further.
//
// EnableBonePhysics/DisableBonePhysics below are placeholders - they name
// the intent, not a verified engine call. Driving a single skeletal bone
// with Karma while its neighbors stay animation-driven is engine/version
// specific; check your Unreal2 SDK's Karma bone/constraint setup before
// treating this as more than scaffolding around real logic.
//=============================================================================
class U2HitReactionController extends Info;

struct LooseBone
{
	var name  BoneName;
	var float ExpireTime;
};

var array<LooseBone> Loose;
var float StaggerThreshold; // min single-hit damage that loosens a bone at all
var float LooseDuration;    // seconds a loosened bone stays physics-driven
var bool  bHandedOff;       // true once GoToFullRagdoll() has run; inert after that

// Owner is the Pawn this controller reacts on (set by whoever spawns it,
// see U2GoreManager.GetHitController).

function ReactToHit(vector HitLocation, vector Momentum, int Damage, optional name BoneName)
{
	local int i;

	if (bHandedOff || Damage < StaggerThreshold || Owner == None)
		return;

	// no bone-accurate hit info available (or not wired up yet) - fall back
	// to one representative bone rather than skipping the reaction entirely
	if (BoneName == '')
		BoneName = 'Spine';

	for (i = 0; i < Loose.Length; i++)
		if (Loose[i].BoneName == BoneName)
			break;
	if (i == Loose.Length)
		Loose[i].BoneName = BoneName;
	Loose[i].ExpireTime = Level.TimeSeconds + LooseDuration;

	EnableBonePhysics(BoneName, Momentum);
	SetTimer(0.1, true);
}

event Timer()
{
	local int i;

	for (i = Loose.Length - 1; i >= 0; i--)
	{
		if (Level.TimeSeconds < Loose[i].ExpireTime)
			continue;
		DisableBonePhysics(Loose[i].BoneName);
		Loose.Remove(i, 1);
	}

	if (Loose.Length == 0)
		SetTimer(0, false); // stop ticking once nothing's loose
}

function GoToFullRagdoll()
{
	local int i;

	if (bHandedOff)
		return;
	bHandedOff = true;

	for (i = 0; i < Loose.Length; i++)
		DisableBonePhysics(Loose[i].BoneName); // the full-body ragdoll below owns every bone now
	Loose.Length = 0;
	SetTimer(0, false);

	if (Owner != None)
		Owner.Physics = PHYS_KarmaRagdoll; // Unreal2's own death path may already do this - redundant call is harmless

	Destroy();
}

// --- placeholders: replace with your SDK's real per-bone Karma calls ---

function EnableBonePhysics(name BoneName, vector Impulse)
{
	Log("U2Gore: TODO wire EnableBonePhysics for "$BoneName$" on "$Owner);
}

function DisableBonePhysics(name BoneName)
{
	Log("U2Gore: TODO wire DisableBonePhysics for "$BoneName$" on "$Owner);
}

defaultproperties
{
	StaggerThreshold=15.0
	LooseDuration=2.5
	RemoteRole=ROLE_None
}
