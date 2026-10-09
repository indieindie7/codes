//=============================================================================
// U2Sanctuary: the creative team's redesign of the Sanctuary maps (M08A1, M08A2,
// M08B), placed at map start instead of editing the maps (the mod ships the
// changes, not modified levels). The scenes come from U2Sanctuary.ini, written by
// tools/make_scenes.py from the team's <map>_redesign.json (tools/mapreview.py).
//=============================================================================
class SanctuaryMutator extends Mutator;

event PostBeginPlay()
{
	local SanctuaryDirector D;

	Super.PostBeginPlay();
	// Sanctuary Open (one open map): the shipped maps' beats, fights and story props (OpenDirector)
	if (Left(Caps(string(Level.Outer)), 16) == "PRAIRIESANCTUARY")
		Spawn(class'OpenDirector');
	// the Avalon remake's fights (AvalonDirector, U2AvalonFights.ini)
	if (Left(Caps(string(Level.Outer)), 11) == "TUTA_REMAKE")
		Spawn(class'AvalonDirector');
	foreach DynamicActors(class'SanctuaryDirector', D)
		return;
	Spawn(class'SanctuaryDirector');
}

defaultproperties
{
	RemoteRole=ROLE_None
}
