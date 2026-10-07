//=============================================================================
// AvalonRadio - the open channel in the Authority's command room
// (binder/radio_lines.md, voiced by U2Avalon/tools/pa_voice.py): Oduya's
// traffic board only ever shows company flights, and the radio makes the
// player hear it - pilots who don't need the tower, the Sector relay
// cancelling things, the dock raising Vask's fee. A quiet static bed between.
// Spawned and configured by AvalonCards (Radio* keys).
//=============================================================================
class AvalonRadio extends AvalonPA;

#exec AUDIO IMPORT FILE=Sounds\RADIO01.wav NAME=RADIO01
#exec AUDIO IMPORT FILE=Sounds\RADIO02.wav NAME=RADIO02
#exec AUDIO IMPORT FILE=Sounds\RADIO03.wav NAME=RADIO03
#exec AUDIO IMPORT FILE=Sounds\RADIO04.wav NAME=RADIO04
#exec AUDIO IMPORT FILE=Sounds\RADIO05.wav NAME=RADIO05
#exec AUDIO IMPORT FILE=Sounds\RADIO06.wav NAME=RADIO06
#exec AUDIO IMPORT FILE=Sounds\RADIO07.wav NAME=RADIO07
#exec AUDIO IMPORT FILE=Sounds\RADIO08.wav NAME=RADIO08
#exec AUDIO IMPORT FILE=Sounds\RADIO09.wav NAME=RADIO09
#exec AUDIO IMPORT FILE=Sounds\RADIO10.wav NAME=RADIO10

defaultproperties
{
	Lines(0)=Sound'RADIO01'
	Lines(1)=Sound'RADIO02'
	Lines(2)=Sound'RADIO03'
	Lines(3)=Sound'RADIO04'
	Lines(4)=Sound'RADIO05'
	Lines(5)=Sound'RADIO06'
	Lines(6)=Sound'RADIO07'
	Lines(7)=Sound'RADIO08'
	Lines(8)=Sound'RADIO09'
	Lines(9)=Sound'RADIO10'
	NumLines=10
}
