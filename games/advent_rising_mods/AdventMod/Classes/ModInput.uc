//=============================================================================
// ModInput - the player's input with ModPilot's "held keys" added, so a test
// script can play the game from inside it, without Windows input or focus.
// The engine fills the input axes from the real keyboard every frame and then
// calls PlayerInput(); adding our values here is exactly what a held key does.
// ModSettings.Startup selects it (PlayerController.InputClass) when a pilot
// script is set; the state comes from ModPilot's class defaults.
//=============================================================================
class ModInput extends PlayerInput within PlayerController;

var bool bAnnounced;

event PlayerInput(float DeltaTime)
{
	if (!bAnnounced)
	{
		bAnnounced = true;
		class'ModSettings'.static.Note("pilot: ModInput is the input of " $ Outer);
	}
	if (class'ModPilot'.default.bActive)
	{
		// the default bindings' axis speeds (MoveForward = Axis aBaseY Speed=+1200, ...)
		aBaseY += 1200.0 * class'ModPilot'.default.Forward;
		aStrafe += 1200.0 * class'ModPilot'.default.Strafe;
		aUp += 1200.0 * class'ModPilot'.default.Up;
		// turning like the mouse does (the camera system owns the view rotation)
		aTurn += class'ModPilot'.default.TurnAxis;
		aLookUp += class'ModPilot'.default.LookAxis;
		if (class'ModPilot'.default.bHoldFire)
			bFire = 1;
		if (class'ModPilot'.default.bHoldFavoriteFire)
			bFavoriteFire = 1;
		if (class'ModPilot'.default.bHoldWalk)
			bRun = 1;
	}
	Super.PlayerInput(DeltaTime);
}

defaultproperties
{
}
