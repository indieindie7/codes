//=============================================================================
// ModAudioOptions - the Audio Options page with the Dialogue Volume slider the
// game has a saved setting and a caption for, but never showed (the stock page
// always passes 1.0), and the controller's Vibration switch (from the stock Game Options
// page; it belongs with feedback).
//=============================================================================
class ModAudioOptions extends MenuPauseOptionsAudio;

var localized string LstrVibration;

function ApplyVolumes()
{
	Controller.ViewportOwner.Actor.SetSoundVolumes(Slider0.Value, Slider1.Value * Slider1.Value, Slider2.Value);
}

function PreSetInitalPositions()
{
	Super.PreSetInitalPositions();
	NumBools = 2;
	NumSliders = 3;
	// rows are toggles first, then sliders: the stock slider captions move down one
	Labels[4].Caption = LstrDialogueVolume;
	Labels[3].Caption = LstrMusicVolume;
	Labels[2].Caption = LstrSoundFXVolume;
	Labels[1].Caption = LstrVibration;
	Slider2.OnChange = RealTimeAudioUpdateDialog;
}

function SetupInitalPositions()
{
	local int i;

	Super.SetupInitalPositions();
	for (i = 0; i < NumSliders; i++)
		Sliders[i].SetAssociatedLabel(Labels[NumBools + i]);
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
	{
		Slider2.SetValue(1.0);
		Button1.SetValueB(false);
	}
	else
	{
		Slider2.SetValue(Controller.OptionsData.DialogueVolume);
		Button1.SetValue(Controller.OptionsData.Rumble);
	}
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
	Controller.OptionsData.Rumble = Button1.GetValue();
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
     LstrVibration="Controller Vibration"
}
