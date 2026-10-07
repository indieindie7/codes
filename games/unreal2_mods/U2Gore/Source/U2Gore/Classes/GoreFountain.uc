//=============================================================================
// A wound that keeps pumping (Soldier of Fortune's neck fountains): it rides on
// one bone of the body, and every heartbeat throws a squirt of blood that lands
// on the floor ahead of it as a fresh splat, weaker each beat until it stops.
// The game's blood particles stream from it too when a template is set
// (GoreDying.FountainTemplate for red, GreenTemplate for green blood).
//=============================================================================
class GoreFountain extends Info;

var Pawn Body;
var int Node;                // the bone it rides on (0: the body's middle)
var int Kind;                // 1 red, 2 green
var float Strength;          // 1 at the start, the beats weaken it
var float NextBeat;
var GoreManager Gore;
var ParticleGenerator Stream;
var() float Beat;            // seconds between beats
var() float Fade;            // strength kept per beat
var() float Reach;           // how far the strongest squirt lands from the wound

function Setup(Pawn P, int N, int K, GoreManager G, float S, string Template)
{
	local ParticleGenerator T;

	Body = P;
	Node = N;
	Kind = K;
	Gore = G;
	Strength = S;
	NextBeat = Level.TimeSeconds + 0.2;
	if (Template != "")
	{
		T = ParticleGenerator(DynamicLoadObject(Template, class'ParticleGenerator'));
		if (T != None)
			Stream = class'ParticleGenerator'.static.CreateNew(self, T, Wound());
		if (Stream != None)
			Stream.Trigger(self, None);
	}
}

function vector Wound()
{
	if (Body == None)
		return Location;
	if (Node != 0)
		return Body.MeshNodeGetTranslation(Node, MESHNODEREL_World);
	return Body.Location;
}

event Tick(float DeltaTime)
{
	local vector W, Dir, HitL, HitN;

	if (Body == None || Body.bDeleteMe || Strength < 0.12)
	{
		Destroy();
		return;
	}
	W = Wound();
	SetLocation(W);
	if (Stream != None)
		Stream.SetLocation(W);
	if (Level.TimeSeconds < NextBeat)
		return;
	NextBeat = Level.TimeSeconds + Beat * (0.85 + 0.3 * FRand());
	// a squirt: out from the body's middle, up a little, landing ahead on the floor
	Dir = W - Body.Location;
	Dir.Z = 0;
	if (VSize(Dir) < 1)
		Dir = VRand();
	Dir = Normal(Normal(Dir) + VRand() * 0.35);
	if (Gore != None && Gore.Surface(HitL, HitN, W + Dir * Reach * Strength - vect(0,0,300), W + Dir * Reach * Strength * 0.5))
	{
		if (Kind == 2)
			Gore.Mark(Gore.IchorSplats[Rand(4)], HitL, HitN, Dir, Gore.DecalSize * (0.25 + 0.3 * Strength));
		else
			Gore.Mark(Gore.Splats[Rand(4)], HitL, HitN, Dir, Gore.DecalSize * (0.25 + 0.3 * Strength));
	}
	Strength *= Fade;
}

event Destroyed()
{
	if (Stream != None)
	{
		Stream.ParticleDestroy();
		Stream = None;
	}
	Super.Destroyed();
}

defaultproperties
{
	Beat=0.550000
	Fade=0.880000
	Reach=70.000000
	bHidden=True
	RemoteRole=ROLE_None
}
