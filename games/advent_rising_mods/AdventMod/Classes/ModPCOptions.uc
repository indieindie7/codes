//=============================================================================
// ModPCOptions - the Graphics Options page with real resolutions: the stock
// list is 640x480 to 1600x1200 (4:3 only). Ours is the five largest common
// sizes that fit the screen, plus whatever the game is running at.
//=============================================================================
class ModPCOptions extends MenuPCOptions;

var string Candidates[7];

function PreSetInitalPositions()
{
	local int i, n, First;

	Super.PreSetInitalPositions();
	// how many candidates fit (they are in ascending order)
	for (n = 0; n < ArrayCount(Candidates); n++)
		if (!class'ModSettings'.static.NativeCall("Fits:" $ Candidates[n]))
			break;
	if (n == 0)
		n = 1;
	First = Max(0, n - ArrayCount(Resolution.ListCaptions));
	for (i = First; i < n; i++)
		Resolution.ListCaptions[i - First] = Candidates[i];
	Resolution.MaxValue = n - First;
}

function SetLocalGuiOptions(bool Reset)
{
	local string Cur;
	local int i, Found;

	Super.SetLocalGuiOptions(Reset);
	// the stock code picks a list entry by width thresholds of its own list
	Cur = Controller.ViewportOwner.Actor.ConsoleCommand("GETCURRENTRES");
	Found = -1;
	for (i = 0; i < Resolution.MaxValue; i++)
		if (Resolution.ListCaptions[i] ~= Cur)
			Found = i;
	if (Found < 0)
	{
		// an unlisted size (e.g. a resized or borderless window): show it in the first slot
		Found = 0;
		Resolution.ListCaptions[0] = Cur;
	}
	Resolution.SetValue(Found);
	if (!Reset)
		OldRes = Found;
}

defaultproperties
{
     Candidates(0)="1024x768"
     Candidates(1)="1280x720"
     Candidates(2)="1366x768"
     Candidates(3)="1600x900"
     Candidates(4)="1920x1080"
     Candidates(5)="2560x1440"
     Candidates(6)="3840x2160"
}
