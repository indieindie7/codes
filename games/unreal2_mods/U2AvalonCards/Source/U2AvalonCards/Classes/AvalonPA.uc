//=============================================================================
// AvalonPA - the Liandri public address over the plant (binder/pa_lines.md,
// voiced by U2Avalon/tools/pa_voice.py): every so often one announcement, from
// every loudspeaker at once, heard across the town and faintly from the
// Authority tower. It sells the posting: the island runs on the company's
// clock, and the Authority is a customer and a visitor.
// Spawned and configured by AvalonCards (PA* keys).
//=============================================================================
class AvalonPA extends Actor;

#exec AUDIO IMPORT FILE=Sounds\PA01.wav NAME=PA01
#exec AUDIO IMPORT FILE=Sounds\PA02.wav NAME=PA02
#exec AUDIO IMPORT FILE=Sounds\PA03.wav NAME=PA03
#exec AUDIO IMPORT FILE=Sounds\PA04.wav NAME=PA04
#exec AUDIO IMPORT FILE=Sounds\PA05.wav NAME=PA05
#exec AUDIO IMPORT FILE=Sounds\PA06.wav NAME=PA06
#exec AUDIO IMPORT FILE=Sounds\PA07.wav NAME=PA07
#exec AUDIO IMPORT FILE=Sounds\PA08.wav NAME=PA08
#exec AUDIO IMPORT FILE=Sounds\PA09.wav NAME=PA09
#exec AUDIO IMPORT FILE=Sounds\PA10.wav NAME=PA10
#exec AUDIO IMPORT FILE=Sounds\PA11.wav NAME=PA11
#exec AUDIO IMPORT FILE=Sounds\PA12.wav NAME=PA12

var Sound Lines[12];
var int NumLines;        // how many of Lines[] are used
var array<Actor> Speakers;
var float MinGap, MaxGap, Radius, Volume;
var int Last;

function AddSpeaker(vector P)
{
	local AvalonPuff S;

	S = Spawn(class'AvalonPuff',,, P);
	if (S != None)
	{
		S.bHidden = True;
		Speakers[Speakers.Length] = S;
	}
}

function Begin(float Lo, float Hi, float R, float V)
{
	MinGap = Lo;
	MaxGap = Hi;
	Radius = R;
	Volume = V;
	Last = -1;
	SetTimer(Lo * 0.5 + FRand() * Lo, false);    // the first one soon after the map starts
}

event Timer()
{
	local int i, k;

	k = Rand(NumLines);
	if (k == Last)
		k = (k + 1) % NumLines;
	Last = k;
	for (i = 0; i < Speakers.Length; i++)
		if (Speakers[i] != None)
			Speakers[i].PlaySound(Lines[k], SLOT_None, Volume, false, Radius, 1.0, true);
	SetTimer(MinGap + FRand() * (MaxGap - MinGap), false);
}

event Destroyed()
{
	local int i;

	for (i = 0; i < Speakers.Length; i++)
		if (Speakers[i] != None)
			Speakers[i].Destroy();
}

defaultproperties
{
	Lines(0)=Sound'PA01'
	Lines(1)=Sound'PA02'
	Lines(2)=Sound'PA03'
	Lines(3)=Sound'PA04'
	Lines(4)=Sound'PA05'
	Lines(5)=Sound'PA06'
	Lines(6)=Sound'PA07'
	Lines(7)=Sound'PA08'
	Lines(8)=Sound'PA09'
	Lines(9)=Sound'PA10'
	Lines(10)=Sound'PA11'
	Lines(11)=Sound'PA12'
	NumLines=12
	DrawType=DT_None
	bHidden=True
	bStatic=False
	bCollideActors=False
	bCollideWorld=False
	Physics=PHYS_None
	RemoteRole=ROLE_None
	bAlwaysRelevant=True
}
