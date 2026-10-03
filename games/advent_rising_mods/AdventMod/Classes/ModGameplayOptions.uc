//=============================================================================
// ModGameplayOptions - "Gameplay", opened from Game Options: a finer difficulty
// than Easy/Normal/Hard, boss tuning on top of it, and a faster run while no
// enemy is near (the slow opening hours). ModTargeting applies the damage
// settings to each level twice a second; ModInput applies the exploring speed.
//=============================================================================
class ModGameplayOptions extends MenuPauseOptionsBase;

var localized string LstrBossDealt, LstrBossTaken, LstrExplore, LstrDealt, LstrTaken;
var float BossSteps[6], ExploreSteps[4];

function PlayerController GetPC()
{
	return Controller.ViewportOwner.Actor;
}

function PreSetInitalPositions()
{
	NumBools = 3;
	NumSliders = 2;
	Labels[0].Caption = LstrBossDealt;
	Labels[1].Caption = LstrBossTaken;
	Labels[2].Caption = LstrExplore;
	Labels[3].Caption = LstrDealt;
	Labels[4].Caption = LstrTaken;
	Button0.bActNormal = true;
	Button0.OnClick = BossDealtClick;
	Button1.bActNormal = true;
	Button1.OnClick = BossTakenClick;
	Button2.bActNormal = true;
	Button2.OnClick = ExploreClick;
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
	Slider0.SetAssociatedLabel(Labels[3]);
	Slider1.SetAssociatedLabel(Labels[4]);
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
	}
	Slider0.SetValue(int(class'ModSettings'.default.DamageDealt * 100 + 0.5));
	Slider1.SetValue(int(class'ModSettings'.default.DamageTaken * 100 + 0.5));
	Refresh();
}

static function string Pct(float F)
{
	return int(F * 100 + 0.5) $ "%";
}

// the buttons that cycle through values show the value instead of On/Off
function Refresh()
{
	Button0.Caption = Pct(class'ModSettings'.default.BossDamageDealt);
	Button1.Caption = Pct(class'ModSettings'.default.BossDamageTaken);
	Button2.Caption = Pct(class'ModSettings'.default.ExploreSpeed);
	Labels[3].Caption = LstrDealt $ ": " $ int(Slider0.Value) $ "%";
	Labels[4].Caption = LstrTaken $ ": " $ int(Slider1.Value) $ "%";
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
     LstrBossDealt="Damage You Deal to Bosses"
     LstrBossTaken="Damage Bosses Deal to You"
     LstrExplore="Running Speed (no enemies near)"
     LstrDealt="Damage You Deal"
     LstrTaken="Damage You Take"
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
