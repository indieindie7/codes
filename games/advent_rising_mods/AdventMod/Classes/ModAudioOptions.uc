//=============================================================================
// ModAudioOptions - the Audio Options page with the Dialogue Volume slider the
// game has a saved setting and a caption for, but never showed (the stock page
// always passes 1.0).
//=============================================================================
class ModAudioOptions extends MenuPauseOptionsAudio;

function ApplyVolumes()
{
	Controller.ViewportOwner.Actor.SetSoundVolumes(Slider0.Value, Slider1.Value * Slider1.Value, Slider2.Value);
}

function PreSetInitalPositions()
{
	Super.PreSetInitalPositions();
	NumSliders = 3;
	Labels[3].Caption = LstrDialogueVolume;
	Slider2.OnChange = RealTimeAudioUpdateDialog;
}

function SetupInitalPositions()
{
	local int i;

	Super.SetupInitalPositions();
	for (i = 0; i < NumSliders; i++)
		Sliders[i].SetAssociatedLabel(Labels[NumBools + i]);
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
		Slider2.SetValue(1.0);
	else
		Slider2.SetValue(Controller.OptionsData.DialogueVolume);
	Super.SetLocalGuiOptions(Reset);
	if (!MyPlayerController.Level.Game.IsInFrontEnd)
		ApplyVolumes();
}

function ReStoreCurrentVolumeLevels()
{
	Controller.ViewportOwner.Actor.SetSoundVolumes(CurSoundVol, CurMusicVol, Controller.OptionsData.DialogueVolume);
}

function UpdateLocalGameOptions()
{
	Super.UpdateLocalGameOptions();
	Controller.OptionsData.DialogueVolume = Slider2.Value;
	ApplyVolumes();
}

function RealTimeAudioUpdateSound(GUIComponent Sender)
{
	ApplyVolumes();
	Controller.PlayClick(1);
}

function RealTimeAudioUpdateMusic(GUIComponent Sender)
{
	ApplyVolumes();
	Controller.PlayClick(1);
}

function RealTimeAudioUpdateDialog(GUIComponent Sender)
{
	ApplyVolumes();
	Controller.PlayClick(1);
}

function SliderImage2PreFocus()
{
	ApplyVolumes();
}

defaultproperties
{
}
