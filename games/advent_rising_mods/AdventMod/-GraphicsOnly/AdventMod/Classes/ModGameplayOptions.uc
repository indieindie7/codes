//=============================================================================
// ModGameplayOptions - "Gameplay" (one press from Options): difficulty (the stock page's
// choice, as one cycling row), a finer difficulty on top of it (damage dealt and taken),
// boss tuning, a faster run while no enemy is near (the slow opening hours), and the
// game's own Levitate Objects switch. ModTargeting applies the damage settings to each
// level twice a second; ModInput applies the exploring speed. Difficulty and Levitate are
// the game's own saved options (Controller.OptionsData, saved when Options closes).
//=============================================================================
class ModGameplayOptions extends MenuPauseOptionsBase;

var localized string LstrDifficulty, LstrBossDealt, LstrBossTaken, LstrExplore, LstrLevitate, LstrDealt, LstrTaken;
var localized string DifficultyNames[4];
var float BossSteps[6], ExploreSteps[4];
var int Difficulty;

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 5;
	NumSliders = 2;
	Labels[0].Caption = LstrDifficulty;
	Labels[1].Caption = LstrBossDealt;
	Labels[2].Caption = LstrBossTaken;
	Labels[3].Caption = LstrExplore;
	Labels[4].Caption = LstrLevitate;
	Labels[5].Caption = LstrDealt;
	Labels[6].Caption = LstrTaken;
	Button0.bActNormal = true;
	Button0.OnClick = DifficultyClick;
	Button1.bActNormal = true;
	Button1.OnClick = BossDealtClick;
	Button2.bActNormal = true;
	Button2.OnClick = BossTakenClick;
	Button3.bActNormal = true;
	Button3.OnClick = ExploreClick;
	Slider0.MinValue = 25;
	Slider0.MaxValue = 300;
	Slider0.bIntSlider = true;
	Slider0.OnChange = DealtChange;
	Slider1.MinValue = 25;
	Slider1.MaxValue = 300;
	Slider1.bIntSlider = true;
	Slider1.OnChange = TakenChange;
}

function SetupInitalPositions()
{
	Super.SetupInitalPositions();
	Slider0.SetAssociatedLabel(Labels[5]);
	Slider1.SetAssociatedLabel(Labels[6]);
	class'ModPanel'.static.AddTo(self);
}

function SetLocalGuiOptions(bool Reset)
{
	if (Reset)
	{
		class'ModSettings'.default.DamageDealt = 1;
		class'ModSettings'.default.DamageTaken = 1;
		class'ModSettings'.default.BossDamageDealt = 1;
		class'ModSettings'.default.BossDamageTaken = 1;
		class'ModSettings'.default.ExploreSpeed = 1.25;
		class'ModSettings'.static.StaticSaveConfig();
		Difficulty = 1;
		Button4.SetValueB(true);
	}
	else
	{
		Difficulty = Clamp(Controller.OptionsData.Difficulty, 0, 3);
		Button4.SetValue(Controller.OptionsData.LevitateObjects);
	}
	Slider0.SetValue(int(class'ModSettings'.default.DamageDealt * 100 + 0.5));
	Slider1.SetValue(int(class'ModSettings'.default.DamageTaken * 100 + 0.5));
	Refresh();
}

function UpdateLocalGameOptions()
{
	Controller.OptionsData.Difficulty = Difficulty;
	Controller.OptionsData.LevitateObjects = Button4.GetValue();
}

static function string Pct(float F)
{
	return int(F * 100 + 0.5) $ "%";
}

// the buttons that cycle through values show the value instead of On/Off
function Refresh()
{
	Button0.Caption = DifficultyNames[Difficulty];
	Button1.Caption = Pct(class'ModSettings'.default.BossDamageDealt);
	Button2.Caption = Pct(class'ModSettings'.default.BossDamageTaken);
	Button3.Caption = Pct(class'ModSettings'.default.ExploreSpeed);
	Labels[5].Caption = LstrDealt $ ": " $ int(Slider0.Value) $ "%";
	Labels[6].Caption = LstrTaken $ ": " $ int(Slider1.Value) $ "%";
}

// the next value of a cycle after Cur (the first one if Cur isn't in it)
static function float NextStep(float Cur, float S0, float S1, float S2, float S3, float S4, float S5, int Count)
{
	local float S[6];
	local int i;

	S[0] = S0; S[1] = S1; S[2] = S2; S[3] = S3; S[4] = S4; S[5] = S5;
	for (i = 0; i < Count; i++)
		if (Abs(S[i] - Cur) < 0.01)
			return S[(i + 1) % Count];
	return S[0];
}

// Easy, Normal, Hard, and Ultra once the game has been finished (as the stock page)
function bool DifficultyClick(GUIComponent Sender)
{
	local int n;

	n = 3;
	if (Controller.OptionsData.FinishedGame == 1)
		n = 4;
	Difficulty = (Difficulty + 1) % n;
	Controller.OptionsData.Difficulty = Difficulty;
	Refresh();
	return false;
}

function bool BossDealtClick(GUIComponent Sender)
{
	class'ModSettings'.default.BossDamageDealt = NextStep(class'ModSettings'.default.BossDamageDealt, BossSteps[0], BossSteps[1], BossSteps[2], BossSteps[3], BossSteps[4], BossSteps[5], 6);
	class'ModSettings'.static.StaticSaveConfig();
	Refresh();
	return false;
}

function bool BossTakenClick(GUIComponent Sender)
{
	class'ModSettings'.default.BossDamageTaken = NextStep(class'ModSettings'.default.BossDamageTaken, BossSteps[0], BossSteps[1], BossSteps[2], BossSteps[3], BossSteps[4], BossSteps[5], 6);
	class'ModSettings'.static.StaticSaveConfig();
	Refresh();
	return false;
}

function bool ExploreClick(GUIComponent Sender)
{
	class'ModSettings'.default.ExploreSpeed = NextStep(class'ModSettings'.default.ExploreSpeed, ExploreSteps[0], ExploreSteps[1], ExploreSteps[2], ExploreSteps[3], 0, 0, 4);
	class'ModSettings'.static.StaticSaveConfig();
	Refresh();
	return false;
}

function DealtChange(GUIComponent Sender)
{
	class'ModSettings'.default.DamageDealt = Slider0.Value / 100.0;
	class'ModSettings'.static.StaticSaveConfig();
	Refresh();
}

function TakenChange(GUIComponent Sender)
{
	class'ModSettings'.default.DamageTaken = Slider1.Value / 100.0;
	class'ModSettings'.static.StaticSaveConfig();
	Refresh();
}

defaultproperties
{
     LstrLabelTitle="Gameplay"
     LstrDifficulty="Difficulty"
     LstrBossDealt="Damage You Deal to Bosses"
     LstrBossTaken="Damage Bosses Deal to You"
     LstrExplore="Running Speed (no enemies near)"
     LstrLevitate="Levitate Objects"
     LstrDealt="Damage You Deal"
     LstrTaken="Damage You Take"
     DifficultyNames(0)="Easy"
     DifficultyNames(1)="Normal"
     DifficultyNames(2)="Hard"
     DifficultyNames(3)="Ultra"
     BossSteps(0)=0.5
     BossSteps(1)=0.75
     BossSteps(2)=1.0
     BossSteps(3)=1.5
     BossSteps(4)=2.0
     BossSteps(5)=3.0
     ExploreSteps(0)=1.0
     ExploreSteps(1)=1.15
     ExploreSteps(2)=1.25
     ExploreSteps(3)=1.4
}
