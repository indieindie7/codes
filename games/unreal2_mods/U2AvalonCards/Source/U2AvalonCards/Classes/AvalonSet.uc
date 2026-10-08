//=============================================================================
// AvalonSet - one Avalon map family's own dressing, so each generated town
// keeps its cards, props and plumes (2026-10-07: building TutA_Ridge5 wrote its
// layout over the TutA session's live edits, and the running game wrote them
// back). Stored per object in U2AvalonCards.ini; U2 names the section after the object
// only, in the name table's spelling: [TutA], [TutA_Ridge5]; a carved copy (TutA_Ridge5_Live2)
// belongs to its parent's family. A family with no section yet starts from the
// global [U2AvalonCards.AvalonCards] values.
//=============================================================================
class AvalonSet extends Object
	config(U2AvalonCards)
	perobjectconfig;

var config bool bUsed;
var config string Lamps[32];
var config string Props[256];      // 256 since 2026-10-08 (shanty ring + factory districts with roads and pipes)
var config string Blocks[128];
var config string Cards[64];
var config string Extras[48];
var config string Plumes[16];
var config string Trucks[8];
var config string Paths[4];
var config string PASpots[6];
var config vector RadioSpot, TowerSpot;
var config string DecayLamp;
