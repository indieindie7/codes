//=============================================================================
// ModTitle - the title menu without the "Plays best on Alienware" screen.
// That screen is not a movie (deleting files doesn't remove it): the title
// menu shows its AlienWare image for 4 seconds between the GlyphX logo and
// the intro. We go straight from that step to the intro before it is drawn.
// Opened instead of Interface.MenuTitle_pc by ModGUIController.
//=============================================================================
class ModTitle extends MenuTitle_pc
	config(AdventMod);

var config bool bLogSequence;    // testing: log each step of the intro sequence
var SEQ_STATES LastState;
var bool bSkippedAlienware;

simulated function Timer()
{
	if (curStateLocal == SEQ_STATES_ALIENWARE_LOGO)
	{
		AlienWare.bVisible = false;
		curStateLocal = SEQ_STATES_INTRO_START;
		if (!bSkippedAlienware && bLogSequence)
			class'ModSettings'.static.Note("title: skipped the Alienware screen");
		bSkippedAlienware = true;
	}
	Super.Timer();
	if (bLogSequence && curStateLocal != LastState)
	{
		LastState = curStateLocal;
		class'ModSettings'.static.Note("title: " $ GetEnum(enum'SEQ_STATES', curStateLocal) $ " (Alienware image visible: " $ AlienWare.bVisible $ ")");
	}
}

defaultproperties
{
     LastState=SEQ_STATES_END
}
