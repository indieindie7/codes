//=============================================================================
// AvalonLive - the "avalon" console command: live editing while the user plays.
//
// The AvalonCards mutator runs "exec AvalonLive.txt" (System folder) every
// couple of seconds through the player's console. Claude writes that file
// (U2Avalon/tools/live.py): a first line "avalon batch N", then commands. A
// batch runs once: the mutator remembers the last N and ignores old ones, so
// the file can stay there. On a new map the last batch applies again, so the
// edits survive a reload; "avalon save" writes them into U2AvalonCards.ini.
//
//   avalon batch N                 start batch N (older or equal: skip the rest)
//   avalon say TEXT                a message on the player's screen
//   avalon extra I LINE            Extras[I] = LINE (a card: "Name X Y Yaw Size [Frames] [Lift]")
//   avalon card I LINE             Cards[I] = LINE
//   avalon prop I LINE             Props[I] = LINE (a static mesh, see AvalonCards.Props)
//   avalon plume I LINE            Plumes[I] = LINE
//   avalon truck I LINE            Trucks[I] = LINE
//   avalon haze START END R G B    the clear-weather fog
//   avalon weather storm|clear|cycle   force the storm on / off, or back to its cycle
//   avalon rebuild                 tear down and rebuild everything the mutator made
//   avalon save                    write the current values into U2AvalonCards.ini
//   avalon where                   log and show the player's position (to place things)
//   avalon raw CONSOLE COMMAND     any console command, once (set, hub, slomo, summon...)
//   avalon pick / picknear / move / moveto / turn / scale / hide / show / delete / spawn / info /
//          list / journal / forget  - live control of any actor: see AvalonEditor
//
// It is added to the player's ExecManagers (as U2TestHub's HubCommands is).
//=============================================================================
class AvalonLive extends Object;

var AvalonCards Cards;
var PlayerController PC;

exec function Avalon(optional string Args)
{
	if (Cards != None)
		Cards.Live(Args, PC);
}
