//=============================================================================
// FrameProbe - measures where the game stutters. Logs every frame longer than
// HitchTime (with what was going on) and, once a second, the frame rate and
// the number of pawns and shadow projectors. Test tool; only runs when added
// to the URL: ?Mutator=U2Hover.FrameProbe
//=============================================================================
class FrameProbe extends Mutator;

var float HitchTime;
var float SecondStart, Worst;
var int Frames, Hitches;

function string Counts()
{
	local Pawn P;
	local Projector Pr;
	local int NP, NS;
	foreach DynamicActors(class'Pawn', P)
		NP++;
	foreach DynamicActors(class'Projector', Pr)
		NS++;
	return "pawns="$NP$" projectors="$NS;
}

event Tick(float DeltaTime)
{
	// DeltaTime is game time; undo slow-motion so this is real frame time
	local float Real;
	Real = DeltaTime / FMax(Level.TimeDilation, 0.01);

	Frames++;
	Worst = FMax(Worst, Real);
	if (Real > HitchTime)
	{
		Hitches++;
		log("FrameProbe: HITCH "$int(Real * 1000)$"ms at t="$Level.TimeSeconds$" "$Counts());
	}
	if (Level.TimeSeconds - SecondStart >= 1.0)
	{
		log("FrameProbe: t="$int(Level.TimeSeconds)$" fps="$Frames$" worst="$int(Worst * 1000)$"ms "$Counts());
		SecondStart = Level.TimeSeconds;
		Frames = 0;
		Worst = 0;
	}
}

defaultproperties
{
	HitchTime=0.100000
	RemoteRole=ROLE_None
}
