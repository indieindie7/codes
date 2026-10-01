//=============================================================================
// SevenRadio - the invisible radio The Seven's lines play from. It rides
// along with the player and plays on the dialogue sound slot, like the game's
// own voices, but on its own actor so neither cuts the other off.
//=============================================================================
class SevenRadio extends Actor;

function Say(Sound S)
{
	PlaySound(S, SLOT_Dialog, 1.0, false, 4000, 1.0, true);
}

function Follow(Actor A)
{
	if (A != None)
		SetLocation(A.Location);
}

defaultproperties
{
	bHidden=True
	bCollideActors=False
	bCollideWorld=False
	bBlockActors=False
	bBlockPlayers=False
	RemoteRole=ROLE_None
	TransientSoundVolume=1.000000
	TransientSoundRadius=4000.000000
}
