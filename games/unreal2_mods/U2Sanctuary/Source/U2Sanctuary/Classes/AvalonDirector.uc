//=============================================================================
// AvalonDirector - OpenDirector's beats, waves and supplies on the Avalon remake
// (TutA_Remake, 2026-10-09): the greybox fights E1-E4 of the redesign plan
// (redesign/2026-10-09/plan.md s.5). Its own config file, U2AvalonFights.ini
// [U2Sanctuary.AvalonDirector], written by U2Avalon/tools/avalon_fights.py.
// Spawned by SanctuaryMutator on any TutA_Remake* map.
//=============================================================================
class AvalonDirector extends OpenDirector
	config(U2AvalonFights);

// a subclass starts from OpenDirector's loaded config (U2Sanctuary.ini): Sanctuary Open's bodies, props, things,
// cameras, no-bike zones, dialogue cuts and beacon would come along unless U2AvalonFights.ini names them. Avalon
// uses only Beats, Waves and Supplies from its own file: the rest is cleared here.
function Start()
{
	Bodies.Length = 0;
	Props.Length = 0;
	Things.Length = 0;
	Cams.Length = 0;
	NoBike.Length = 0;
	Cuts.Length = 0;
	BeaconAt = vect(0,0,0);
	HoldBeat = "";
	Super.Start();
}

defaultproperties
{
}
