//=============================================================================
// The bridge from U2Gore to the d3d8 layer's live blood (fork gi-cascades acfbd43,
// gorelink=1 in U2Shaders.ini). Unreal II has no native DLL to call, so the layer
// reads this actor's string straight out of the game's memory: it finds the one
// object of class GoreLink in GObjects, finds the string that starts "GL1 ", and
// runs each new batch once (at Present, a frame after this tick).
//   Batch = "GL1 <seq>;<cmd>;<cmd>;..." rewritten every tick; <seq> changes every tick.
// Commands are the layer's U2BloodCommand lines (blood.hpp pools, runs.hpp wall runs):
// one-shot ones go in once (Send), per-tick state would be re-sent every tick.
// The layer only reads; nothing comes back (no "wet").
// Keep this the ONLY string in the class that starts with "GL1 ".
//=============================================================================
class GoreLink extends Info;

var string Batch;                  // what the layer reads
var array<string> Pending;         // commands since the last tick
var int Seq, Sent, Used;
var bool bCleared;

function Send(string Cmd)
{
	// a batch holds at most 16384 characters (the layer cuts at the last ';'): drop the rest
	if (Used + Len(Cmd) + 1 > 15000)
		return;
	Pending[Pending.Length] = Cmd;
	Used += Len(Cmd) + 1;
}

event Tick(float DeltaTime)
{
	local int i;
	local string S;

	if (!bCleared)
	{
		// a new map: whatever the layer still holds from the last one goes
		bCleared = true;
		S = "streakclear;stringclear;handclear;lensclear;";
	}
	for (i = 0; i < Pending.Length; i++)
		S = S $ Pending[i] $ ";";
	Sent += Pending.Length;
	Pending.Length = 0;
	Used = 0;
	Seq++;
	Batch = "GL1 " $ Seq $ ";" $ S;
}

defaultproperties
{
	RemoteRole=ROLE_None
}
