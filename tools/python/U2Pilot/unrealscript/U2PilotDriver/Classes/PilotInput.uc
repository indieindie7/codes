//=============================================================================
// Replaces the player's PlayerInput so the pilot can "hold keys" from inside
// the game: the engine fills the input axes from the real keyboard every
// frame, then calls PlayerInput(); adding our values here is exactly what a
// held key would do, without Windows input or window focus.
//=============================================================================
class PilotInput extends PlayerInput within PlayerController;

var float Forward, Strafe;      // -1..1, like holding W/S and A/D
var bool bHoldFire, bHoldAltFire, bHoldJump;
var name HoldButton;          // a byte button on the controller to hold (e.g. bLeanLeft)
var byte WantRun, WantCrouch;   // Walking key (bRun) / crouch; set via the public setters

event PlayerInput(float DeltaTime)
{
	if (GetRunFlag() != WantRun)
		SetRunFlag(WantRun);
	if (GetDuckFlag() != WantCrouch)
		SetDuckFlag(WantCrouch);   // also changes the pawn's stance
	// the same raw values the default key bindings (Axis ... Speed=300) produce
	aBaseY += 300.0 * Forward;
	aStrafe += 300.0 * Strafe;
	if (bHoldFire)
		bFire = 1;
	if (bHoldAltFire)
		bAltFire = 1;
	if (bHoldJump)
		aUp = 300.0;
	if (HoldButton != '')
		Outer.SetPropertyText(string(HoldButton), "1");
	Super.PlayerInput(DeltaTime);
}

defaultproperties
{
	WantRun=0
}
