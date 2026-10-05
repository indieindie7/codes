//=============================================================================
// ModScreenBlood - blood on the "lens": a kill or a body coming apart close to the
// player throws a few splats on the screen, which fade out. ModGore adds them
// (Splash); ModMutator adds this to the player's interactions.
// It also draws the energy blade's strikes left (ModMelee), a row of pips low on the screen.
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
var int BladeShown;            // the blade's strikes when last drawn
var float BladeFlash;          // >0: a strike was just used (the row is bright)

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

	if (class'ModMelee'.default.SavedCharges != BladeShown)
	{
		BladeShown = class'ModMelee'.default.SavedCharges;
		BladeFlash = 1.0;
	}
	else if (BladeFlash > 0)
		BladeFlash -= DeltaTime * 2;
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
	DrawBlade(C);
}

// the energy blade's strikes: a pip each, the used ones dim, the last five red
function DrawBlade(Canvas C)
{
	local int i, Total, Have;
	local float W, H, Gap, X0, Y0, Lit;

	Have = class'ModMelee'.default.SavedCharges;
	Total = Max(class'ModMelee'.default.BladeCharges, Have);
	if (Have <= 0 || Total > 40)
		return;
	H = C.ClipY * 0.022;
	W = C.ClipY * 0.007;
	Gap = W * 0.8;
	X0 = C.ClipX * 0.5 - (Total * (W + Gap) - Gap) * 0.5;
	Y0 = C.ClipY * 0.925;
	Lit = FClamp(BladeFlash, 0, 1);
	C.Style = 5;
	for (i = 0; i < Total; i++)
	{
		if (i >= Have)
			C.SetDrawColor(40, 60, 70);
		else if (Have <= 5)
			C.SetDrawColor(255, 70 + 120 * Lit, 50 + 120 * Lit);
		else
			C.SetDrawColor(60 + 195 * Lit, 220 + 35 * Lit, 255);
		C.DrawColor.A = 190;
		C.SetPos(X0 + i * (W + Gap), Y0);
		C.DrawTile(Texture'Engine.WhiteSquareTexture', W, H, 0, 0, 2, 2);
	}
}

defaultproperties
{
     bVisible=True
     bRequiresTick=True
     bActive=False
}
