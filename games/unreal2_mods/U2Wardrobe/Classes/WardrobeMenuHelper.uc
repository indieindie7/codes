//=============================================================================
// WardrobeMenuHelper - the "Character Model" dropdown on Options > MISC.
// The menu script binds a U2Selector to three calls on a helper object:
// Accessor (the list), Modifier (pick one) and CurrentText (what's picked).
// Picking saves the choice in System\U2Wardrobe.ini and, in a level, puts it
// on at once (the player and Dalton's cutscene stand-ins).
// Registered in the menu script itself ([WardrobeMenuHelper] RegisterObj).
//=============================================================================
class WardrobeMenuHelper extends UIHelper;

function array<string> GetOutfitList()
{
	return class'WardrobeMutator'.default.Labels;
}

function string GetOutfit()
{
	if (class'WardrobeMutator'.default.Outfit == "")
		return class'WardrobeMutator'.default.Labels[0];
	return class'WardrobeMutator'.default.Outfit;
}

function SetOutfit(string L)
{
	local WardrobeMutator M;
	local PlayerController PC;

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
}
