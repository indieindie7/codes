//=============================================================================
// AvalonChat - talk to Claude through the in-game text chat instead of the
// console (the user, 2026-10-08: the console stays hidden; the chat line is
// part of normal play). In single player every line the player says becomes
// an "avalon mark" note (with its screenshot, like a typed mark), and still
// shows in the chat as usual. Claude's "say" replies come back as chat lines.
//=============================================================================
class AvalonChat extends BroadcastHandler;

var AvalonCards Cards;

function Broadcast(Actor Sender, coerce string Msg, optional name Type)
{
	local PlayerController PC;

	Super.Broadcast(Sender, Msg, Type);
	PC = PlayerController(Sender);
	if (PC == None || Cards == None || Msg == "")
		return;
	if (Type == 'Say' || Type == 'TeamSay')
	{
		// a line already starting with "avalon " is a command; anything else is a note
		if (Left(Caps(Msg), 7) == "AVALON ")
			Cards.Live(Mid(Msg, 7), PC);
		else
			Cards.Live("mark "$Msg, PC);
	}
}

function BroadcastTeam(Controller Sender, coerce string Msg, optional name Type)
{
	Broadcast(Sender, Msg, Type);
}
