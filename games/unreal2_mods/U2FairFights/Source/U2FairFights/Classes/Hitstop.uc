//=============================================================================
// Hitstop - a beat of slow motion, timed in real seconds (game time is
// slowed, so a Timer would stretch with it). Leaves other slow-motion alone.
//=============================================================================
class Hitstop extends Info;

var float RealLeft;
var float Restore;
var bool bActive;

function Start(float RealSeconds, float Dilation)
{
	if (!bActive && Level.TimeDilation != 1.0)
		return;                         // a cutscene skip or the like owns it
	if (!bActive)
	{
		Restore = Level.TimeDilation;
		Level.TimeDilation = Dilation;
		bActive = true;
		Enable('Tick');
		Log("FairFights: hitstop "$RealSeconds$"s at x"$Dilation$" (t="$Level.TimeSeconds$")");
	}
	RealLeft = FMax(RealLeft, RealSeconds);
}

event Tick(float DeltaTime)
{
	if (!bActive)
		return;
	RealLeft -= DeltaTime / FMax(Level.TimeDilation, 0.01);
	if (RealLeft <= 0)
	{
		Level.TimeDilation = Restore;
		bActive = false;
		Disable('Tick');
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
}
