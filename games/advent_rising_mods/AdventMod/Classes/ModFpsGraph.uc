//=============================================================================
// ModFpsGraph - a debugging overlay: the last few seconds of frame times as a
// graph in the top-left corner, with the current, average and worst frame
// rate. Off unless ModSettings.bFpsGraph (a development switch: the release
// ini leaves it off); ModMutator adds it to the player's interactions.
// Bars are frame times: the green line is 60 fps (16.7 ms), the yellow one 30.
//=============================================================================
class ModFpsGraph extends Interaction;

const SAMPLES = 240;

var float Times[240];      // a ring of frame times, seconds
var int Head, Count;
var float Shown;           // the numbers update a few times a second, so they can be read
var string Line;
var bool bAdded;           // (default) one per player, for the whole run

event Initialized()
{
	default.bAdded = true;
}

function Tick(float DeltaTime)
{
	if (ViewportOwner != None && ViewportOwner.Actor != None && ViewportOwner.Actor.Level.TimeDilation > 0)
		DeltaTime /= ViewportOwner.Actor.Level.TimeDilation;    // real time, not game time
	Times[Head] = DeltaTime;
	Head = (Head + 1) % SAMPLES;
	Count = Min(Count + 1, SAMPLES);
}

// this engine's SetDrawColor takes no alpha
static function Col(Canvas C, byte R, byte G, byte B, byte A)
{
	C.SetDrawColor(R, G, B);
	C.DrawColor.A = A;
}

function PostRender(Canvas C)
{
	local int i, n;
	local float X0, Y0, W, H, BarW, T, Sum, Worst, Ms;

	// levels only, with the HUD's fonts loaded (at the title the canvas has none:
	// drawing text there crashed the game)
	if (!class'ModSettings'.default.bFpsGraph || Count == 0 || C == None || C.SmallFont == None
		|| ViewportOwner == None || ViewportOwner.Actor == None || ViewportOwner.Actor.Level == None
		|| ViewportOwner.Actor.Level.Game == None || ViewportOwner.Actor.Level.Game.IsInFrontEnd)
		return;
	W = 360;
	H = 90;
	X0 = 12;
	Y0 = 12;
	BarW = W / SAMPLES;
	// the panel
	C.Style = 5;    // STY_Alpha
	Col(C, 0, 0, 0, 150);
	C.SetPos(X0 - 4, Y0 - 4);
	C.DrawTile(Texture'Engine.WhiteSquareTexture', W + 8, H + 26, 0, 0, 2, 2);
	// 60 and 30 fps lines (the graph's top is 50 ms)
	Col(C, 60, 200, 60, 200);
	C.SetPos(X0, Y0 + H - H * 16.7 / 50.0);
	C.DrawTile(Texture'Engine.WhiteSquareTexture', W, 1, 0, 0, 2, 2);
	Col(C, 220, 200, 40, 200);
	C.SetPos(X0, Y0 + H - H * 33.3 / 50.0);
	C.DrawTile(Texture'Engine.WhiteSquareTexture', W, 1, 0, 0, 2, 2);
	// the frames, oldest on the left
	for (i = 0; i < Count; i++)
	{
		n = (Head - Count + i + SAMPLES) % SAMPLES;
		T = Times[n];
		Sum += T;
		Worst = FMax(Worst, T);
		Ms = FMin(T * 1000.0, 50.0);
		if (Ms <= 17.5)
			Col(C, 80, 220, 80, 220);
		else if (Ms <= 34)
			Col(C, 230, 200, 50, 220);
		else
			Col(C, 230, 60, 50, 230);
		C.SetPos(X0 + (SAMPLES - Count + i) * BarW, Y0 + H - H * Ms / 50.0);
		C.DrawTile(Texture'Engine.WhiteSquareTexture', FMax(BarW, 1), H * Ms / 50.0, 0, 0, 2, 2);
	}
	if (ViewportOwner.Actor.Level.TimeSeconds - Shown > 0.25 || Line == "")
	{
		Shown = ViewportOwner.Actor.Level.TimeSeconds;
		n = (Head - 1 + SAMPLES) % SAMPLES;
		Line = "fps " $ int(1.0 / FMax(Times[n], 0.0001)) $ "   avg " $ int(Count / FMax(Sum, 0.0001)) $ "   worst " $ int(1.0 / FMax(Worst, 0.0001)) $ " (" $ int(Worst * 1000) $ " ms)";
	}
	C.Font = C.SmallFont;
	Col(C, 255, 255, 255, 255);
	C.SetPos(X0, Y0 + H + 4);
	C.DrawText(Line, false);
}

defaultproperties
{
     bVisible=True
     bRequiresTick=True
     bActive=False
}
