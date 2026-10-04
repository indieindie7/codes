//=============================================================================
// ModScreenBlood - blood on the "lens": a kill or a body coming apart close to the
// player throws a few splats on the screen, which fade out. ModGore adds them
// (Splash); ModMutator adds this to the player's interactions.
//=============================================================================
class ModScreenBlood extends Interaction;

const MAXSPLATS = 12;

struct Splat
{
	var Material Tex;
	var float X, Y, Size;      // centre (fractions of the screen) and size (of its height)
	var float Age, Life;
};
var Splat Splats[12];
var bool bAdded;               // (default) one per player, for the whole run
var ModScreenBlood Live;       // (default) the one ModGore talks to

event Initialized()
{
	default.bAdded = true;
	default.Live = self;
}

// n splats of this texture, bigger and longer lived with Strength (0..1)
function Splash(Material Tex, int n, float Strength)
{
	local int i, k;

	for (k = 0; k < n; k++)
	{
		// a free slot, or the oldest
		for (i = 0; i < MAXSPLATS; i++)
			if (Splats[i].Tex == None)
				break;
		if (i == MAXSPLATS)
			i = Rand(MAXSPLATS);
		Splats[i].Tex = Tex;
		// toward the edges: the middle of the screen stays readable
		Splats[i].X = 0.5 + (0.2 + 0.28 * FRand()) * (2 * Rand(2) - 1);
		Splats[i].Y = 0.1 + 0.8 * FRand();
		Splats[i].Size = (0.16 + 0.22 * FRand()) * (0.6 + 0.6 * Strength);
		Splats[i].Age = 0;
		Splats[i].Life = 2.5 + 2.5 * FRand() + 2 * Strength;
	}
}

function Tick(float DeltaTime)
{
	local int i;

	for (i = 0; i < MAXSPLATS; i++)
		if (Splats[i].Tex != None)
		{
			Splats[i].Age += DeltaTime;
			if (Splats[i].Age >= Splats[i].Life)
				Splats[i].Tex = None;
		}
}

function PostRender(Canvas C)
{
	local int i;
	local float S, A;

	if (C == None || ViewportOwner == None || ViewportOwner.Actor == None || ViewportOwner.Actor.Level == None
		|| ViewportOwner.Actor.Level.Game == None || ViewportOwner.Actor.Level.Game.IsInFrontEnd)
		return;
	C.Style = 5;    // STY_Alpha
	for (i = 0; i < MAXSPLATS; i++)
	{
		if (Splats[i].Tex == None)
			continue;
		// full for the first third, then fading; the splat runs down a little
		A = FClamp((Splats[i].Life - Splats[i].Age) / (Splats[i].Life * 0.66), 0, 1);
		S = Splats[i].Size * C.ClipY;
		C.SetDrawColor(255, 255, 255);
		C.DrawColor.A = byte(200 * A);
		C.SetPos(Splats[i].X * C.ClipX - S * 0.5,
			Splats[i].Y * C.ClipY - S * 0.5 + Splats[i].Age * 0.012 * C.ClipY);
		C.DrawTile(Splats[i].Tex, S, S * (1 + 0.04 * Splats[i].Age), 0, 0, 128, 128);
	}
}

defaultproperties
{
     bVisible=True
     bRequiresTick=True
     bActive=False
}
