//=============================================================================
// AutoInput - the player's input with a second pair of hands: while the
// AutoBrain is on, its keys replace the processed axes (at a held key's
// strength) and it sets the view rotation. It wraps the input object it
// replaced, so another mod's input (the pilot's) keeps working underneath.
//=============================================================================
class AutoInput extends PlayerInput
	within PlayerController;

var AutoBrain Brain;
var PlayerInput Inner;      // the input object this one replaced (another mod's, e.g. the pilot's): still run

event PlayerInput(float DeltaTime)
{
	if (Inner != None)
		Inner.PlayerInput(DeltaTime);
	else
		Super.PlayerInput(DeltaTime);
	// after the engine's own scaling: a held key peaks near 24000 in aForward (PlayerController.PlayerMove)
	if (Brain != None && Brain.bOn)
	{
		aTurn = 0;
		aLookUp = 0;
		Brain.Keys(DeltaTime);
	}
}
