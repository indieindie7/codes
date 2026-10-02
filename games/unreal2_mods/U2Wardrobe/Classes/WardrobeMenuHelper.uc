//=============================================================================
// WardrobeMenuHelper - the "Character Model" dropdown on Options > MISC.
// The menu script binds a U2Selector to three calls on a helper object:
// Accessor (the list), Modifier (pick one) and CurrentText (what's picked).
// Picking saves the choice in System\U2Wardrobe.ini and, in a level, puts it
// on at once (the player and Dalton's cutscene stand-ins).
// Registered in the menu script itself ([WardrobeMenuHelper] RegisterObj).
//=============================================================================
class WardrobeMenuHelper extends UIHelper;

// the outfits' portraits beside the dropdown (Textures\Portraits.tga, made by
// make_portraits.py; the menu script cuts it into WardrobePic0..N): the menu
// shows portrait N on the event "WardrobePortraitN"
#exec TEXTURE IMPORT NAME=Portraits FILE=Textures\Portraits.tga GROUP=UI MIPS=OFF ALPHA=1

var int Shown;                       // the portrait last asked for (-1: none yet)

function ShowPortrait(string L)
{
	local int i;

	for (i = 0; i < class'WardrobeMutator'.default.Labels.Length; i++)
		if (class'WardrobeMutator'.default.Labels[i] ~= L)
			break;
	if (i >= class'WardrobeMutator'.default.Labels.Length)
		i = 0;
	if (i == Shown)
		return;
	Shown = i;
	class'UIConsole'.static.SendEvent("WardrobePortrait"$i);
}

function array<string> GetOutfitList()
{
	return class'WardrobeMutator'.default.Labels;
}

function string GetOutfit()
{
	local string L;

	L = class'WardrobeMutator'.default.Outfit;
	if (L == "")
		L = class'WardrobeMutator'.default.Labels[0];
	ShowPortrait(L);         // the page asks for this when shown: start on the right picture
	return L;
}

function SetOutfit(string L)
{
	local WardrobeMutator M;
	local PlayerController PC;

	ShowPortrait(L);
	PC = GetPlayerOwner();
	if (PC != None)
		foreach PC.DynamicActors(class'WardrobeMutator', M)
		{
			M.Wear(L, PC);          // saves too
			return;
		}
	// no level running (main menu): just remember it for the next one
	class'WardrobeMutator'.default.Outfit = L;
	class'WardrobeMutator'.static.StaticSaveConfig();
}

defaultproperties
{
	Shown=-1
}
